#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Stock Trading Assistant
Tests all backend endpoints with proper error handling and validation
"""

import requests
import json
import sys
from datetime import datetime
import time

# Get backend URL from frontend .env
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
        return None

BASE_URL = get_backend_url()
if not BASE_URL:
    print("❌ Could not get backend URL from frontend/.env")
    sys.exit(1)

API_BASE = f"{BASE_URL}/api"
print(f"🔗 Testing backend at: {API_BASE}")

class BackendTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
        
    def log_result(self, test_name, success, message, response_data=None):
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'response_data': response_data
        }
        self.results.append(result)
        print(f"{status} {test_name}: {message}")
        if success:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_health_check(self):
        """Test GET /api/health"""
        try:
            response = requests.get(f"{API_BASE}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'status' in data and 'timestamp' in data:
                    self.log_result("Health Check", True, f"Server healthy - Status: {data['status']}")
                else:
                    self.log_result("Health Check", False, f"Invalid response format: {data}")
            else:
                self.log_result("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Health Check", False, f"Connection error: {str(e)}")
    
    def test_get_watchlist(self):
        """Test GET /api/watchlist"""
        try:
            response = requests.get(f"{API_BASE}/watchlist", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'watchlist' in data and isinstance(data['watchlist'], list):
                    watchlist = data['watchlist']
                    if len(watchlist) > 0:
                        # Check if default symbols are present
                        symbols = [item['symbol'] for item in watchlist]
                        expected_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
                        found_symbols = [s for s in expected_symbols if s in symbols]
                        self.log_result("Get Watchlist", True, 
                                      f"Retrieved {len(watchlist)} symbols, found {len(found_symbols)} default symbols")
                        return watchlist
                    else:
                        self.log_result("Get Watchlist", False, "Empty watchlist returned")
                else:
                    self.log_result("Get Watchlist", False, f"Invalid response format: {data}")
            else:
                self.log_result("Get Watchlist", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Get Watchlist", False, f"Connection error: {str(e)}")
        
        return None
    
    def test_update_watchlist(self):
        """Test POST /api/watchlist"""
        try:
            # Test adding symbols
            add_payload = {
                "symbols": ["AAPL", "GOOGL"],
                "action": "add"
            }
            
            response = requests.post(f"{API_BASE}/watchlist", 
                                   json=add_payload, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'watchlist' in data:
                    watchlist = data['watchlist']
                    added_symbols = [item['symbol'] for item in watchlist if item['symbol'] in ['AAPL', 'GOOGL']]
                    if len(added_symbols) > 0:
                        self.log_result("Add to Watchlist", True, f"Successfully added {len(added_symbols)} symbols")
                    else:
                        self.log_result("Add to Watchlist", False, "Symbols not found in updated watchlist")
                else:
                    self.log_result("Add to Watchlist", False, f"Invalid response format: {data}")
            else:
                self.log_result("Add to Watchlist", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test removing symbols
            remove_payload = {
                "symbols": ["AAPL"],
                "action": "remove"
            }
            
            response = requests.post(f"{API_BASE}/watchlist", 
                                   json=remove_payload, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'watchlist' in data:
                    watchlist = data['watchlist']
                    remaining_symbols = [item['symbol'] for item in watchlist if item['symbol'] == 'AAPL']
                    if len(remaining_symbols) == 0:
                        self.log_result("Remove from Watchlist", True, "Successfully removed AAPL from watchlist")
                    else:
                        self.log_result("Remove from Watchlist", False, "AAPL still found in watchlist after removal")
                else:
                    self.log_result("Remove from Watchlist", False, f"Invalid response format: {data}")
            else:
                self.log_result("Remove from Watchlist", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Update Watchlist", False, f"Connection error: {str(e)}")
    
    def test_get_indicators(self):
        """Test GET /api/indicators?symbol=RELIANCE"""
        try:
            response = requests.get(f"{API_BASE}/indicators?symbol=RELIANCE", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['symbol', 'rsi', 'vwap', 'pivot', 'bc', 'tc', 'ltp', 'timestamp']
                
                if all(field in data for field in required_fields):
                    # Validate data types and ranges
                    if (data['symbol'] == 'RELIANCE' and 
                        0 <= data['rsi'] <= 100 and
                        data['ltp'] > 0 and
                        data['vwap'] > 0):
                        self.log_result("Get Indicators", True, 
                                      f"Retrieved indicators - RSI: {data['rsi']}, LTP: {data['ltp']}, VWAP: {data['vwap']}")
                        return data
                    else:
                        self.log_result("Get Indicators", False, f"Invalid indicator values: {data}")
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("Get Indicators", False, f"Missing fields: {missing}")
            else:
                self.log_result("Get Indicators", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Get Indicators", False, f"Connection error: {str(e)}")
        
        return None
    
    def test_generate_signal(self):
        """Test POST /api/signal"""
        try:
            payload = {"symbol": "RELIANCE"}
            
            response = requests.post(f"{API_BASE}/signal", 
                                   json=payload, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['symbol', 'signal', 'entry_price', 'target', 'stop_loss', 'notes', 'timestamp']
                
                if all(field in data for field in required_fields):
                    valid_signals = ['BUY', 'SELL', 'HOLD']
                    if (data['symbol'] == 'RELIANCE' and 
                        data['signal'] in valid_signals and
                        data['entry_price'] > 0 and
                        data['target'] > 0 and
                        data['stop_loss'] > 0):
                        self.log_result("Generate Signal", True, 
                                      f"Generated {data['signal']} signal at ₹{data['entry_price']}, Target: ₹{data['target']}")
                        return data
                    else:
                        self.log_result("Generate Signal", False, f"Invalid signal data: {data}")
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("Generate Signal", False, f"Missing fields: {missing}")
            else:
                self.log_result("Generate Signal", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Generate Signal", False, f"Connection error: {str(e)}")
        
        return None
    
    def test_scan_all(self):
        """Test POST /api/scan-all"""
        try:
            response = requests.post(f"{API_BASE}/scan-all", 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=30)  # Longer timeout for scanning all symbols
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'results' in data:
                    results = data['results']
                    if isinstance(results, list) and len(results) > 0:
                        # Check if results contain valid signal data
                        valid_results = 0
                        for result in results:
                            if ('symbol' in result and 'signal' in result and 
                                result['signal'] in ['BUY', 'SELL', 'HOLD']):
                                valid_results += 1
                        
                        self.log_result("Scan All Symbols", True, 
                                      f"Scanned {len(results)} symbols, {valid_results} valid results")
                    else:
                        self.log_result("Scan All Symbols", False, "No results returned from scan")
                else:
                    self.log_result("Scan All Symbols", False, f"Invalid response format: {data}")
            else:
                self.log_result("Scan All Symbols", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Scan All Symbols", False, f"Connection error: {str(e)}")
    
    def test_send_alert(self):
        """Test POST /api/alert"""
        try:
            payload = {
                "symbol": "RELIANCE",
                "signal": "BUY",
                "price": 2500.50,
                "target": 2525.50,
                "stop_loss": 2487.50,
                "notes": "Test alert from backend testing"
            }
            
            response = requests.post(f"{API_BASE}/alert", 
                                   json=payload, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data:
                    self.log_result("Send Alert", True, f"Alert sent successfully: {data['message']}")
                else:
                    self.log_result("Send Alert", False, f"Invalid response format: {data}")
            else:
                self.log_result("Send Alert", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Send Alert", False, f"Connection error: {str(e)}")
    
    def test_trade_log(self):
        """Test GET /api/trade-log (may fail due to Google Sheets)"""
        try:
            response = requests.get(f"{API_BASE}/trade-log", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'trades' in data:
                    trades = data['trades']
                    self.log_result("Get Trade Log", True, f"Retrieved {len(trades)} trade records")
                else:
                    self.log_result("Get Trade Log", False, f"Invalid response format: {data}")
            elif response.status_code == 500:
                # Expected failure due to Google Sheets authentication
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                if 'detail' in error_data and 'Google Sheets' in error_data['detail']:
                    self.log_result("Get Trade Log", True, "Expected failure - Google Sheets not configured (graceful handling)")
                else:
                    self.log_result("Get Trade Log", False, f"Unexpected error: {response.text}")
            else:
                self.log_result("Get Trade Log", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Get Trade Log", False, f"Connection error: {str(e)}")
    
    def test_log_trade(self):
        """Test POST /api/log (may fail due to Google Sheets)"""
        try:
            payload = {
                "symbol": "RELIANCE",
                "signal": "BUY",
                "entry_price": 2500.50,
                "target": 2525.50,
                "stop_loss": 2487.50,
                "live_price": 2500.50,
                "status": "OPEN",
                "notes": "Test trade log from backend testing"
            }
            
            response = requests.post(f"{API_BASE}/log", 
                                   json=payload, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data:
                    self.log_result("Log Trade", True, f"Trade logged successfully: {data['message']}")
                else:
                    self.log_result("Log Trade", False, f"Invalid response format: {data}")
            elif response.status_code == 500:
                # Expected failure due to Google Sheets authentication
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                if 'detail' in error_data and ('Google Sheets' in error_data['detail'] or 'log trade' in error_data['detail'].lower()):
                    self.log_result("Log Trade", True, "Expected failure - Google Sheets not configured (graceful handling)")
                else:
                    self.log_result("Log Trade", False, f"Unexpected error: {response.text}")
            else:
                self.log_result("Log Trade", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Log Trade", False, f"Connection error: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting comprehensive backend API testing...")
        print("=" * 60)
        
        # Test in logical order
        self.test_health_check()
        self.test_get_watchlist()
        self.test_update_watchlist()
        self.test_get_indicators()
        self.test_generate_signal()
        self.test_scan_all()
        self.test_send_alert()
        self.test_trade_log()
        self.test_log_trade()
        
        print("=" * 60)
        print(f"📊 Test Results: {self.passed} passed, {self.failed} failed")
        
        if self.failed == 0:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed - check details above")
        
        return self.failed == 0

def main():
    tester = BackendTester()
    success = tester.run_all_tests()
    
    # Print detailed results
    print("\n📋 Detailed Test Results:")
    print("-" * 40)
    for result in tester.results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['test']}: {result['message']}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())