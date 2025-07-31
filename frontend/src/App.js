import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Login Component
const Login = ({ onLogin }) => {
  const handleLogin = () => {
    // Simple login simulation
    onLogin();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center">
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Stock Trading Assistant</h1>
          <p className="text-white/80">Your Intraday Trading Companion</p>
        </div>
        
        <div className="space-y-6">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-500/20 rounded-full mb-4">
              <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">Real-time Market Analysis</h2>
            <p className="text-white/70 text-sm">RSI, VWAP, CPR indicators with smart buy/sell signals</p>
          </div>
          
          <button
            onClick={handleLogin}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 transform hover:scale-105"
          >
            Enter Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const [watchlist, setWatchlist] = useState([]);
  const [indicators, setIndicators] = useState({});
  const [signals, setSignals] = useState({});
  const [tradeLog, setTradeLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [activeTab, setActiveTab] = useState('watchlist');

  // Fetch watchlist
  const fetchWatchlist = async () => {
    try {
      const response = await axios.get(`${API}/watchlist`);
      setWatchlist(response.data.watchlist);
    } catch (error) {
      console.error('Error fetching watchlist:', error);
    }
  };

  // Fetch indicators for a symbol
  const fetchIndicators = async (symbol) => {
    try {
      const response = await axios.get(`${API}/indicators?symbol=${symbol}`);
      setIndicators(prev => ({
        ...prev,
        [symbol]: response.data
      }));
    } catch (error) {
      console.error(`Error fetching indicators for ${symbol}:`, error);
    }
  };

  // Generate signal for a symbol
  const generateSignal = async (symbol) => {
    try {
      const response = await axios.post(`${API}/signal`, { symbol });
      setSignals(prev => ({
        ...prev,
        [symbol]: response.data
      }));
    } catch (error) {
      console.error(`Error generating signal for ${symbol}:`, error);
    }
  };

  // Add symbol to watchlist
  const addSymbol = async () => {
    if (!newSymbol.trim()) return;
    
    try {
      await axios.post(`${API}/watchlist`, {
        symbols: [newSymbol.toUpperCase()],
        action: 'add'
      });
      setNewSymbol('');
      fetchWatchlist();
    } catch (error) {
      console.error('Error adding symbol:', error);
    }
  };

  // Remove symbol from watchlist
  const removeSymbol = async (symbol) => {
    try {
      await axios.post(`${API}/watchlist`, {
        symbols: [symbol],
        action: 'remove'
      });
      fetchWatchlist();
      
      // Clean up indicators and signals
      setIndicators(prev => {
        const newIndicators = { ...prev };
        delete newIndicators[symbol];
        return newIndicators;
      });
      setSignals(prev => {
        const newSignals = { ...prev };
        delete newSignals[symbol];
        return newSignals;
      });
    } catch (error) {
      console.error('Error removing symbol:', error);
    }
  };

  // Scan all symbols
  const scanAllSymbols = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/scan-all`);
      
      // Update signals with results
      const newSignals = {};
      response.data.results.forEach(result => {
        newSignals[result.symbol] = result;
      });
      setSignals(newSignals);
      
      // Fetch updated indicators
      for (const item of watchlist) {
        await fetchIndicators(item.symbol);
      }
      
      // Fetch trade log
      fetchTradeLog();
      
      alert(`Scan completed! Generated ${response.data.results.length} signals`);
    } catch (error) {
      console.error('Error scanning symbols:', error);
      alert('Error during scan. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch trade log
  const fetchTradeLog = async () => {
    try {
      const response = await axios.get(`${API}/trade-log`);
      setTradeLog(response.data.trades || []);
    } catch (error) {
      console.error('Error fetching trade log:', error);
    }
  };

  // Initialize data
  useEffect(() => {
    fetchWatchlist();
    fetchTradeLog();
  }, []);

  // Fetch indicators when watchlist changes
  useEffect(() => {
    watchlist.forEach(item => {
      fetchIndicators(item.symbol);
    });
  }, [watchlist]);

  const getSignalColor = (signal) => {
    switch (signal) {
      case 'BUY': return 'text-green-600 bg-green-100';
      case 'SELL': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-lg border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-2 rounded-lg">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Trading Assistant</h1>
                <p className="text-sm text-gray-600">Intraday Market Analysis</p>
              </div>
            </div>
            
            <div className="flex space-x-4">
              <button
                onClick={scanAllSymbols}
                disabled={loading}
                className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all duration-200 disabled:opacity-50"
              >
                {loading ? 'Scanning...' : 'Scan All'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex">
              {['watchlist', 'signals', 'tradelog'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-4 px-6 text-sm font-medium border-b-2 ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab === 'watchlist' && 'Watchlist & Indicators'}
                  {tab === 'signals' && 'Trading Signals'}
                  {tab === 'tradelog' && 'Trade Log'}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Watchlist Tab */}
        {activeTab === 'watchlist' && (
          <div className="space-y-6">
            {/* Add Symbol */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Add New Symbol</h2>
              <div className="flex space-x-4">
                <input
                  type="text"
                  value={newSymbol}
                  onChange={(e) => setNewSymbol(e.target.value)}
                  placeholder="Enter symbol (e.g., RELIANCE)"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  onKeyPress={(e) => e.key === 'Enter' && addSymbol()}
                />
                <button
                  onClick={addSymbol}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  Add Symbol
                </button>
              </div>
            </div>

            {/* Watchlist Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {watchlist.map((item) => (
                <div key={item.symbol} className="bg-white rounded-lg shadow-sm p-6 border">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{item.symbol}</h3>
                      <p className="text-sm text-gray-600">Token: {item.instrument_token}</p>
                    </div>
                    <button
                      onClick={() => removeSymbol(item.symbol)}
                      className="text-red-500 hover:text-red-700 p-1"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  {indicators[item.symbol] && (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">LTP:</span>
                          <span className="font-semibold ml-2">₹{indicators[item.symbol].ltp}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">RSI:</span>
                          <span className={`font-semibold ml-2 ${
                            indicators[item.symbol].rsi < 30 ? 'text-green-600' : 
                            indicators[item.symbol].rsi > 70 ? 'text-red-600' : 'text-gray-900'
                          }`}>
                            {indicators[item.symbol].rsi}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-600">VWAP:</span>
                          <span className="font-semibold ml-2">₹{indicators[item.symbol].vwap}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Pivot:</span>
                          <span className="font-semibold ml-2">₹{indicators[item.symbol].pivot}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">BC:</span>
                          <span className="font-semibold ml-2">₹{indicators[item.symbol].bc}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">TC:</span>
                          <span className="font-semibold ml-2">₹{indicators[item.symbol].tc}</span>
                        </div>
                      </div>

                      {signals[item.symbol] && (
                        <div className="mt-4 pt-4 border-t">
                          <div className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${getSignalColor(signals[item.symbol].signal)}`}>
                            {signals[item.symbol].signal}
                          </div>
                          {signals[item.symbol].signal !== 'HOLD' && (
                            <div className="mt-2 text-sm text-gray-600">
                              <div>Target: ₹{signals[item.symbol].target}</div>
                              <div>Stop Loss: ₹{signals[item.symbol].stop_loss}</div>
                            </div>
                          )}
                        </div>
                      )}

                      <button
                        onClick={() => generateSignal(item.symbol)}
                        className="w-full mt-4 bg-gray-100 hover:bg-gray-200 text-gray-800 py-2 rounded-lg text-sm font-medium transition-colors"
                      >
                        Generate Signal
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Signals Tab */}
        {activeTab === 'signals' && (
          <div className="bg-white rounded-lg shadow-sm">
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold text-gray-900">Trading Signals</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entry Price</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stop Loss</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Notes</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(signals).map(([symbol, signal]) => (
                    <tr key={symbol}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{symbol}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSignalColor(signal.signal)}`}>
                          {signal.signal}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹{signal.entry_price}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹{signal.target}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹{signal.stop_loss}</td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">{signal.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {Object.keys(signals).length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  No signals generated yet. Click "Scan All" to generate signals for all symbols.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Trade Log Tab */}
        {activeTab === 'tradelog' && (
          <div className="bg-white rounded-lg shadow-sm">
            <div className="p-6 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">Trade Log</h2>
              <button
                onClick={fetchTradeLog}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Refresh
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entry</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stop Loss</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tradeLog.map((trade, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {new Date(trade.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{trade.symbol}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSignalColor(trade.signal)}`}>
                          {trade.signal}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹{trade.entry_price}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹{trade.target}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">₹{trade.stop_loss}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          trade.status === 'OPEN' ? 'text-blue-600 bg-blue-100' : 'text-gray-600 bg-gray-100'
                        }`}>
                          {trade.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {tradeLog.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  No trades logged yet. Generate signals to start logging trades.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Main App Component
const App = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  return (
    <div className="App">
      {!isLoggedIn ? (
        <Login onLogin={handleLogin} />
      ) : (
        <Dashboard />
      )}
    </div>
  );
};

export default App;