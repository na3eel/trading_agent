from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import schedule
import threading
import time
import pandas as pd
import numpy as np
import requests
import json
import pyotp
from SmartApi import SmartConnect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Stock Trading Assistant API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configuration
class Config:
    SMART_API_KEY = os.getenv("SMART_API_KEY", "YOUR_SMART_API_KEY")
    SMART_SECRET_KEY = os.getenv("SMART_SECRET_KEY", "YOUR_SMART_SECRET_KEY")
    CLIENT_ID = os.getenv("CLIENT_ID", "YOUR_CLIENT_ID")
    PASSWORD = os.getenv("PASSWORD", "YOUR_PASSWORD")
    TOTP_SECRET = os.getenv("TOTP_SECRET", "YOUR_TOTP_SECRET")
    GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "/path/to/saadalgotrading-424c20af8525.json")
    NTFY_TOPIC = os.getenv("NTFY_TOPIC", "trade-alerts")
    SHEET_NAME = "Trade Tracker"

# Models
class WatchlistItem(BaseModel):
    symbol: str
    instrument_token: str

class WatchlistRequest(BaseModel):
    symbols: List[str]
    action: str = "add"  # add or remove

class IndicatorData(BaseModel):
    symbol: str
    rsi: float
    vwap: float
    pivot: float
    bc: float
    tc: float
    ltp: float
    timestamp: datetime

class SignalRequest(BaseModel):
    symbol: str

class SignalResponse(BaseModel):
    symbol: str
    signal: str
    entry_price: float
    target: float
    stop_loss: float
    notes: str
    timestamp: datetime

class LogRequest(BaseModel):
    symbol: str
    signal: str
    entry_price: float
    target: float
    stop_loss: float
    live_price: float
    status: str = "OPEN"
    notes: str = ""

class AlertRequest(BaseModel):
    symbol: str
    signal: str
    price: float
    target: float
    stop_loss: float
    notes: str

# SmartAPI Client
class SmartAPIClient:
    def __init__(self):
        self.smart_api = None
        self.session_token = None
        
    def authenticate(self):
        try:
            self.smart_api = SmartConnect(api_key=Config.SMART_API_KEY)
            
            # Generate TOTP
            totp = pyotp.TOTP(Config.TOTP_SECRET)
            totp_token = totp.now()
            
            # Login
            data = self.smart_api.generateSession(Config.CLIENT_ID, Config.PASSWORD, totp_token)
            
            if data['status']:
                self.session_token = data['data']['jwtToken']
                self.smart_api.setAccessToken(self.session_token)
                logger.info("SmartAPI authentication successful")
                return True
            else:
                logger.error(f"SmartAPI authentication failed: {data['message']}")
                return False
                
        except Exception as e:
            logger.error(f"SmartAPI authentication error: {str(e)}")
            return False
    
    def get_ltp(self, exchange: str, symbol_token: str):
        try:
            if not self.smart_api:
                self.authenticate()
            
            data = self.smart_api.ltpData(exchange, symbol_token, symbol_token)
            if data['status']:
                return float(data['data'][symbol_token]['ltp'])
            return None
        except Exception as e:
            logger.error(f"Error fetching LTP for {symbol_token}: {str(e)}")
            return None
    
    def get_historical_data(self, exchange: str, symbol_token: str, from_date: str, to_date: str, interval: str):
        try:
            if not self.smart_api:
                self.authenticate()
            
            data = self.smart_api.getCandleData({
                "exchange": exchange,
                "symboltoken": symbol_token,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            })
            
            if data['status']:
                return data['data']
            return None
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol_token}: {str(e)}")
            return None

# Indicator Calculator
class IndicatorCalculator:
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    @staticmethod
    def calculate_vwap(prices: List[float], volumes: List[float]) -> float:
        if len(prices) != len(volumes) or len(prices) == 0:
            return 0.0
        
        price_volume = [p * v for p, v in zip(prices, volumes)]
        return round(sum(price_volume) / sum(volumes), 2)
    
    @staticmethod
    def calculate_cpr(high: float, low: float, close: float) -> Dict[str, float]:
        pivot = (high + low + close) / 3
        bc = (high + low) / 2
        tc = (pivot - bc) + pivot
        
        return {
            'pivot': round(pivot, 2),
            'bc': round(bc, 2),
            'tc': round(tc, 2)
        }

# Google Sheets Logger
class GoogleSheetsLogger:
    def __init__(self):
        self.sheet = None
        self.credentials_path = Config.GOOGLE_SHEETS_CREDENTIALS_PATH
        
    def authenticate(self):
        try:
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Google Sheets credentials file not found: {self.credentials_path}")
                return False
                
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_path, scope)
            client = gspread.authorize(creds)
            self.sheet = client.open(Config.SHEET_NAME).sheet1
            
            # Ensure headers exist
            headers = ['timestamp', 'symbol', 'signal', 'entry_price', 'target', 'stop_loss', 'live_price', 'status', 'notes']
            if not self.sheet.row_values(1):
                self.sheet.insert_row(headers, 1)
            
            logger.info("Google Sheets authentication successful")
            return True
        except Exception as e:
            logger.error(f"Google Sheets authentication error: {str(e)}")
            return False
    
    def log_trade(self, log_data: LogRequest):
        try:
            if not self.sheet:
                if not self.authenticate():
                    return False
            
            row = [
                datetime.now(timezone.utc).isoformat(),
                log_data.symbol,
                log_data.signal,
                log_data.entry_price,
                log_data.target,
                log_data.stop_loss,
                log_data.live_price,
                log_data.status,
                log_data.notes
            ]
            
            self.sheet.append_row(row)
            logger.info(f"Trade logged for {log_data.symbol}")
            return True
        except Exception as e:
            logger.error(f"Error logging trade: {str(e)}")
            return False

# Notification Service
class NotificationService:
    @staticmethod
    def send_alert(alert_data: AlertRequest):
        try:
            message = f"📈 {alert_data.signal} signal on {alert_data.symbol} at ₹{alert_data.price}. Target: ₹{alert_data.target}, SL: ₹{alert_data.stop_loss}. {alert_data.notes}"
            
            response = requests.post(
                f"https://ntfy.sh/{Config.NTFY_TOPIC}",
                data=message.encode('utf-8'),
                headers={"Title": "Trading Alert"}
            )
            
            if response.status_code == 200:
                logger.info(f"Alert sent for {alert_data.symbol}")
                return True
            else:
                logger.error(f"Failed to send alert: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
            return False

# Initialize services
smart_api_client = SmartAPIClient()
indicator_calculator = IndicatorCalculator()
sheets_logger = GoogleSheetsLogger()
notification_service = NotificationService()

# Default watchlist with instrument tokens (NSE)
DEFAULT_WATCHLIST = [
    {"symbol": "RELIANCE", "instrument_token": "2885"},
    {"symbol": "TCS", "instrument_token": "11536"},
    {"symbol": "INFY", "instrument_token": "1594"},
    {"symbol": "HDFCBANK", "instrument_token": "1333"},
    {"symbol": "ICICIBANK", "instrument_token": "4963"}
]

# In-memory watchlist storage (in production, use database)
watchlist_storage = DEFAULT_WATCHLIST.copy()

# Trading logic
class TradingEngine:
    @staticmethod
    def generate_signal(indicators: Dict[str, float]) -> Dict[str, Any]:
        rsi = indicators['rsi']
        vwap = indicators['vwap']
        price = indicators['ltp']
        tc = indicators['tc']
        bc = indicators['bc']
        
        signal = "HOLD"
        notes = "No clear signal"
        
        if rsi < 30 and price > vwap and price > tc:
            signal = "BUY"
            notes = f"RSI oversold ({rsi:.2f}), price above VWAP and TC"
        elif rsi > 70 and price < vwap and price < bc:
            signal = "SELL"
            notes = f"RSI overbought ({rsi:.2f}), price below VWAP and BC"
        
        # Calculate target and stop loss
        if signal == "BUY":
            target = round(price * 1.01, 2)  # 1% profit
            stop_loss = round(price * 0.995, 2)  # 0.5% loss
        elif signal == "SELL":
            target = round(price * 0.99, 2)  # 1% profit (short)
            stop_loss = round(price * 1.005, 2)  # 0.5% loss
        else:
            target = price
            stop_loss = price
        
        return {
            'signal': signal,
            'entry_price': price,
            'target': target,
            'stop_loss': stop_loss,
            'notes': notes
        }

trading_engine = TradingEngine()

# API Endpoints
@api_router.get("/watchlist")
async def get_watchlist():
    """Get current watchlist symbols and instrument tokens"""
    return {"watchlist": watchlist_storage}

@api_router.post("/watchlist")
async def update_watchlist(request: WatchlistRequest):
    """Add or remove symbols from watchlist"""
    global watchlist_storage
    
    if request.action == "add":
        for symbol in request.symbols:
            # In a real implementation, you'd look up the instrument token
            if not any(item['symbol'] == symbol for item in watchlist_storage):
                watchlist_storage.append({
                    "symbol": symbol,
                    "instrument_token": f"dummy_{symbol}"  # Placeholder
                })
    elif request.action == "remove":
        watchlist_storage = [item for item in watchlist_storage if item['symbol'] not in request.symbols]
    
    return {"message": f"Watchlist updated", "watchlist": watchlist_storage}

@api_router.get("/indicators")
async def get_indicators(symbol: str):
    """Fetch latest indicators for a symbol"""
    try:
        # Find symbol in watchlist
        symbol_info = next((item for item in watchlist_storage if item['symbol'] == symbol), None)
        if not symbol_info:
            raise HTTPException(status_code=404, detail="Symbol not found in watchlist")
        
        # In a real implementation, fetch actual market data
        # For demo purposes, generate mock data
        import random
        
        # Mock LTP
        base_price = random.uniform(100, 3000)
        ltp = round(base_price + random.uniform(-50, 50), 2)
        
        # Mock historical data for RSI calculation
        prices = [base_price + random.uniform(-20, 20) for _ in range(30)]
        prices.append(ltp)
        
        # Calculate indicators
        rsi = indicator_calculator.calculate_rsi(prices)
        
        # Mock VWAP
        volumes = [random.uniform(1000, 10000) for _ in range(len(prices))]
        vwap = indicator_calculator.calculate_vwap(prices, volumes)
        
        # Mock previous day's data for CPR
        prev_high = base_price + random.uniform(10, 30)
        prev_low = base_price - random.uniform(10, 30)
        prev_close = base_price + random.uniform(-15, 15)
        
        cpr = indicator_calculator.calculate_cpr(prev_high, prev_low, prev_close)
        
        result = IndicatorData(
            symbol=symbol,
            rsi=rsi,
            vwap=vwap,
            pivot=cpr['pivot'],
            bc=cpr['bc'],
            tc=cpr['tc'],
            ltp=ltp,
            timestamp=datetime.now(timezone.utc)
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching indicators for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/signal")
async def generate_signal(request: SignalRequest):
    """Generate trading signal for a symbol"""
    try:
        # Get indicators
        indicators_data = await get_indicators(request.symbol)
        
        # Convert to dict for trading engine
        indicators = {
            'rsi': indicators_data.rsi,
            'vwap': indicators_data.vwap,
            'ltp': indicators_data.ltp,
            'tc': indicators_data.tc,
            'bc': indicators_data.bc
        }
        
        # Generate signal
        signal_data = trading_engine.generate_signal(indicators)
        
        result = SignalResponse(
            symbol=request.symbol,
            signal=signal_data['signal'],
            entry_price=signal_data['entry_price'],
            target=signal_data['target'],
            stop_loss=signal_data['stop_loss'],
            notes=signal_data['notes'],
            timestamp=datetime.now(timezone.utc)
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating signal for {request.symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/log")
async def log_trade(log_data: LogRequest):
    """Log trade to Google Sheet"""
    try:
        success = sheets_logger.log_trade(log_data)
        if success:
            return {"message": "Trade logged successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to log trade")
    except Exception as e:
        logger.error(f"Error logging trade: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/alert")
async def send_alert(alert_data: AlertRequest):
    """Send notification via ntfy.sh"""
    try:
        success = notification_service.send_alert(alert_data)
        if success:
            return {"message": "Alert sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send alert")
    except Exception as e:
        logger.error(f"Error sending alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/scan-all")
async def scan_all_symbols():
    """Scan all watchlist symbols and generate signals"""
    results = []
    
    for item in watchlist_storage:
        try:
            # Generate signal for each symbol
            signal_request = SignalRequest(symbol=item['symbol'])
            signal_response = await generate_signal(signal_request)
            
            # Log if signal is not HOLD
            if signal_response.signal != "HOLD":
                log_request = LogRequest(
                    symbol=signal_response.symbol,
                    signal=signal_response.signal,
                    entry_price=signal_response.entry_price,
                    target=signal_response.target,
                    stop_loss=signal_response.stop_loss,
                    live_price=signal_response.entry_price,
                    status="OPEN",
                    notes=signal_response.notes
                )
                await log_trade(log_request)
                
                # Send alert
                alert_request = AlertRequest(
                    symbol=signal_response.symbol,
                    signal=signal_response.signal,
                    price=signal_response.entry_price,
                    target=signal_response.target,
                    stop_loss=signal_response.stop_loss,
                    notes=signal_response.notes
                )
                await send_alert(alert_request)
            
            results.append(signal_response)
            
        except Exception as e:
            logger.error(f"Error scanning {item['symbol']}: {str(e)}")
            continue
    
    return {"message": f"Scanned {len(results)} symbols", "results": results}

@api_router.get("/trade-log")
async def get_trade_log():
    """Get trade log from Google Sheets"""
    try:
        if not sheets_logger.sheet:
            if not sheets_logger.authenticate():
                raise HTTPException(status_code=500, detail="Failed to authenticate with Google Sheets")
        
        # Get all records
        records = sheets_logger.sheet.get_all_records()
        return {"trades": records}
        
    except Exception as e:
        logger.error(f"Error fetching trade log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

# Background Tasks (placeholder - in production use celery or similar)
def schedule_tasks():
    """Schedule periodic tasks"""
    # Pre-market scan at 09:00 IST
    schedule.every().day.at("03:30").do(lambda: asyncio.create_task(scan_all_symbols()))  # UTC time
    
    # Live tracking every minute from 09:15 to 15:30 IST
    # This would need more sophisticated scheduling in production
    
    # End-of-day summary at 15:45 IST
    schedule.every().day.at("10:15").do(lambda: logger.info("End of day summary placeholder"))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Stock Trading Assistant API")
    
    # Try to authenticate services
    smart_api_client.authenticate()
    sheets_logger.authenticate()
    
    # Start background scheduler
    schedule_tasks()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}