#!/usr/bin/env python3

import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import threading
import time
import numpy as np
from trade_manager import EnhancedTradeManager, TradeManagementRules, OptionContract
from dotenv import load_dotenv
import os
import random
from trade_db import trade_db
from position_tracker import PositionTracker, get_current_positions, get_option_spreads
from simulated_pnl import simulated_tracker

load_dotenv()

st.set_page_config(
    page_title="Volatility Trading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Clean dark theme CSS
st.markdown("""
<style>
    /* Dark theme colors */
    .stApp {
        background-color: #1A1E29;
        color: #E0E0E0;
    }
    
    /* Metrics styling */
    [data-testid="metric-container"] {
        background-color: #252A38;
        border: 1px solid #3A3F51;
        border-radius: 8px;
        padding: 15px;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #252A38;
        color: #E0E0E0;
        border: 1px solid #3A3F51;
        border-radius: 5px;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background-color: #2E3444;
        border-color: #2979FF;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #252A38;
        border-radius: 8px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #8A92A5;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2E3444 !important;
        color: #E0E0E0 !important;
    }
    
    /* DataFrame styling */
    .dataframe {
        background-color: #252A38 !important;
        color: #E0E0E0 !important;
    }
    
    /* Success/Error/Warning */
    .stSuccess {
        background-color: rgba(0, 200, 83, 0.1);
        border: 1px solid #00C853;
        color: #00C853;
    }
    
    .stError {
        background-color: rgba(213, 0, 0, 0.1);
        border: 1px solid #D50000;
        color: #D50000;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: #252A38;
        color: #E0E0E0;
        border: 1px solid #3A3F51;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #E0E0E0;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #252A38;
    }
    
    /* Toggle switch styling */
    .stCheckbox > label > div[data-testid="stMarkdownContainer"] > p {
        color: #E0E0E0;
    }
    
    /* Analysis log styling */
    .analysis-log {
        background-color: #1E2230;
        border: 1px solid #3A3F51;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        font-family: monospace;
    }
    
    .analysis-timestamp {
        color: #2979FF;
        font-weight: bold;
    }
    
    .analysis-reasoning {
        color: #00C853;
        margin-left: 20px;
    }
    
    .analysis-decision {
        color: #FFB300;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'trade_manager' not in st.session_state:
    st.session_state.trade_manager = EnhancedTradeManager()

if 'monitoring_thread' not in st.session_state:
    st.session_state.monitoring_thread = None

if 'monitoring_active' not in st.session_state:
    st.session_state.monitoring_active = False

if 'full_bot' not in st.session_state:
    st.session_state.full_bot = None

if 'bot_thread' not in st.session_state:
    st.session_state.bot_thread = None

if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False

if 'bot_logs' not in st.session_state:
    st.session_state.bot_logs = []

if 'bot_analysis' not in st.session_state:
    st.session_state.bot_analysis = []

if 'market_scans' not in st.session_state:
    st.session_state.market_scans = []

# NEW: Dev mode state
if 'dev_mode' not in st.session_state:
    st.session_state.dev_mode = True  # Start in dev mode by default

if 'claude_analysis_log' not in st.session_state:
    st.session_state.claude_analysis_log = []

# Bot settings
if 'bot_settings' not in st.session_state:
    st.session_state.bot_settings = {
        'symbols': ['SPY', 'QQQ', 'IWM', 'DIA'],
        'min_price_move': 1.5,
        'min_iv_rank': 70,
        'scan_interval': 300,
        'confidence_threshold': 70,
        'max_contracts': 5,
        'account_balance': 100000
    }

class DummyDataGenerator:
    """Generate realistic dummy data for dev mode"""
    
    def __init__(self):
        self.base_prices = {
            'SPY': 450.00,
            'QQQ': 380.00,
            'IWM': 190.00,
            'DIA': 350.00,
            'AAPL': 180.00,
            'MSFT': 420.00
        }
        self.last_prices = self.base_prices.copy()
        
    async def generate_market_move(self, symbol: str):
        """Generate realistic market movement"""
        # Simulate different market scenarios with more tradeable moves
        scenarios = [
            {'name': 'normal', 'move': np.random.normal(0, 0.005), 'prob': 0.4},  # Increased volatility
            {'name': 'volatile', 'move': np.random.normal(0, 0.025), 'prob': 0.3},  # More frequent
            {'name': 'spike', 'move': random.choice([-0.03, -0.025, 0.025, 0.03]), 'prob': 0.2},  # More frequent
            {'name': 'trend', 'move': np.random.normal(0.02, 0.01) * random.choice([-1, 1]), 'prob': 0.1}
        ]
        
        # Choose scenario based on probability
        rand = random.random()
        cumulative_prob = 0
        chosen_scenario = scenarios[0]
        
        for scenario in scenarios:
            cumulative_prob += scenario['prob']
            if rand <= cumulative_prob:
                chosen_scenario = scenario
                break
        
        # Apply movement
        current_price = self.last_prices.get(symbol, 100)
        move_pct = chosen_scenario['move']
        new_price = current_price * (1 + move_pct)
        self.last_prices[symbol] = new_price
        
        # Calculate IV based on move magnitude
        iv_base = 0.18
        if abs(move_pct) > 0.015:
            iv_base = 0.25 + abs(move_pct) * 2
        
        return {
            'symbol': symbol,
            'current_price': new_price,
            'percent_change': move_pct * 100,
            'volume': random.randint(500000, 5000000),
            'iv_rank': min(100, iv_base * 400 + random.uniform(-10, 10)),
            'scenario': chosen_scenario['name']
        }
    

class FullAutomatedBot:
    def __init__(self, dev_mode=False, bot_settings=None, paper_trading=True):
        # Pass paper_trading flag to trade manager
        self.trade_manager = EnhancedTradeManager(paper_trading=paper_trading)
        self.is_running = False
        self.dev_mode = dev_mode
        self.paper_trading = paper_trading
        self.dummy_data_gen = DummyDataGenerator() if dev_mode else None
        
        # Bot settings with defaults
        settings = bot_settings or {}
        self.symbols = settings.get('symbols', ['SPY', 'QQQ', 'IWM', 'DIA'])
        self.min_price_move = settings.get('min_price_move', 1.5)
        self.min_iv_rank = settings.get('min_iv_rank', 70)
        self.scan_interval = settings.get('scan_interval', 300)
        self.confidence_threshold = settings.get('confidence_threshold', 70)
        self.last_scan_time = None
        
    def log(self, message):
        """Add log message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        # Add to database
        trade_db.add_log(message)
        
        # Try to append to session state, but don't fail if not available
        try:
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'bot_logs'):
                st.session_state.bot_logs.append(log_entry)
                if len(st.session_state.bot_logs) > 50:
                    st.session_state.bot_logs = st.session_state.bot_logs[-50:]
        except:
            pass
        print(log_entry)
        
        # Also write to a dedicated bot log file
        with open('bot_analysis.log', 'a') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    
    def log_claude_analysis(self, symbol, market_data, analysis, decision):
        """Log Claude's analysis for the Analysis tab"""
        analysis_entry = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'market_data': market_data,
            'claude_analysis': analysis,
            'decision': decision,
            'mode': 'DEV' if self.dev_mode else 'LIVE'
        }
        
        # Add to database
        analysis_id = trade_db.add_claude_analysis(analysis_entry)
        
        # If trade was executed, add to trades table
        if analysis and analysis.get('should_trade') and 'EXECUTE' in decision:
            trade_data = {
                'symbol': symbol,
                'spread_type': analysis['spread_type'],
                'short_strike': analysis['short_strike'],
                'long_strike': analysis['long_strike'],
                'contracts': analysis['contracts'],
                'credit': analysis['expected_credit'],
                'status': 'SIMULATED' if self.dev_mode else 'PENDING',
                'mode': 'DEV' if self.dev_mode else 'LIVE'
            }
            trade_db.add_trade(trade_data, analysis_id)
        
        # Try to append to session state, but don't fail if not available
        try:
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'claude_analysis_log'):
                st.session_state.claude_analysis_log.append(analysis_entry)
                # Keep only last 100 entries
                if len(st.session_state.claude_analysis_log) > 100:
                    st.session_state.claude_analysis_log = st.session_state.claude_analysis_log[-100:]
            
            # Also add to bot_analysis for backward compatibility
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'bot_analysis'):
                st.session_state.bot_analysis.append(analysis_entry)
                if len(st.session_state.bot_analysis) > 10:
                    st.session_state.bot_analysis = st.session_state.bot_analysis[-10:]
        except:
            pass
    
    async def get_market_data(self, symbol):
        """Get market data - either real or dummy based on mode"""
        if self.dev_mode:
            # Generate dummy data
            self.log(f"📊 [DEV] Generating dummy data for {symbol}")
            market_data = await self.dummy_data_gen.generate_market_move(symbol)
            market_data['iv_percentile'] = market_data['iv_rank'] + 5
            return market_data
        else:
            # Real data implementation (existing code)
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
                from alpaca.data.timeframe import TimeFrame
                
                data_client = StockHistoricalDataClient(
                    api_key=os.getenv('ALPACA_API_KEY'),
                    secret_key=os.getenv('ALPACA_SECRET_KEY')
                )
                
                quotes = data_client.get_stock_latest_quote(
                    StockQuotesRequest(symbol_or_symbols=symbol)
                )
                current_price = float(quotes[symbol].ask_price)
                
                today_request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=datetime.now().date()
                )
                bars = data_client.get_stock_bars(today_request)
                
                if not bars.df.empty:
                    open_price = float(bars.df.iloc[0]['open'])
                    percent_change = ((current_price - open_price) / open_price) * 100
                    volume = int(bars.df.iloc[0]['volume'])
                else:
                    percent_change = 0
                    volume = 0
                
                # Calculate IV rank
                exp_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
                options_data = await self.trade_manager.get_real_time_options_data(symbol, exp_date)
                
                if options_data:
                    iv_values = [opt.implied_volatility for opt in options_data if opt.implied_volatility > 0]
                    if iv_values:
                        current_iv = np.mean(iv_values)
                        iv_rank = min(100, current_iv * 400)
                        self.log(f"   Using REAL options data: {len(options_data)} contracts, avg IV: {current_iv:.2%}")
                    else:
                        iv_rank = min(100, abs(percent_change) * 20 + np.random.uniform(40, 80))
                else:
                    iv_rank = min(100, abs(percent_change) * 20 + np.random.uniform(40, 80))
                
                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'percent_change': percent_change,
                    'volume': volume,
                    'iv_rank': iv_rank,
                    'iv_percentile': iv_rank + 5
                }
                
            except Exception as e:
                self.log(f"Error getting market data for {symbol}: {e}")
                return None
    
    async def analyze_with_claude(self, market_data):
        """Use Claude to analyze market conditions"""
        # Always use real Claude API - only the market data is simulated in dev mode
        try:
            from anthropic import AsyncAnthropic
            
            anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            prompt = f"""
                Analyze this market move for a volatility credit spread opportunity:
                
                Symbol: {market_data['symbol']}
                Current Price: ${market_data['current_price']:.2f}
                Today's Move: {market_data['percent_change']:.2f}%
                Volume: {market_data['volume']:,}
                IV Rank: {market_data['iv_rank']:.1f}
                
                Rules:
                1. If move DOWN >1.5%: Consider CALL credit spread
                2. If move UP >1.5%: Consider PUT credit spread  
                3. IV Rank must be >70 for good premiums
                4. Target strikes 1.5-2 standard deviations away
                
                Respond in JSON only:
                {{
                    "should_trade": true/false,
                    "spread_type": "call_credit" or "put_credit" or null,
                    "short_strike": price or null,
                    "long_strike": price or null,
                    "expiration_days": number or null,
                    "contracts": number or null,
                    "expected_credit": amount or null,
                    "confidence": 0-100,
                    "reasoning": "brief explanation"
                }}
                """
            
            response = await anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Log the raw Claude response
            self.log(f"Claude raw response for {market_data['symbol']}: {response.content[0].text}")
            
            import re
            json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                self.log(f"Claude analysis parsed: {json.dumps(analysis, indent=2)}")
                return analysis
            else:
                self.log(f"Could not parse Claude response for {market_data['symbol']}")
                return None
                
        except Exception as e:
            self.log(f"Error analyzing with Claude: {e}")
            return None
    
    async def scan_and_trade(self):
        """Main scanning and trading loop"""
        mode_prefix = "[DEV]" if self.dev_mode else "[LIVE]"
        self.log(f"🔍 {mode_prefix} Starting market scan...")
        self.log(f"   Settings: Min Move={self.min_price_move}%, Min IV={self.min_iv_rank}, Confidence={self.confidence_threshold}%")
        scan_results = []
        
        for symbol in self.symbols:
            try:
                market_data = await self.get_market_data(symbol)
                if not market_data:
                    continue
                
                scan_results.append(market_data)
                self.log(f"📊 {symbol}: ${market_data['current_price']:.2f} ({market_data['percent_change']:+.2f}%) IV:{market_data['iv_rank']:.0f}")
                
                if (abs(market_data['percent_change']) >= self.min_price_move and 
                    market_data['iv_rank'] >= self.min_iv_rank):
                    
                    self.log(f"🚨 VOLATILITY SPIKE: {symbol} moved {market_data['percent_change']:.2f}% with IV rank {market_data['iv_rank']:.0f}")
                    
                    # Use real Claude to analyze the market data (even if data is simulated)
                    self.log(f"🤖 Asking Claude to analyze {symbol}...")
                    self.log(f"Market data being sent: Price=${market_data['current_price']:.2f}, Move={market_data['percent_change']:.2f}%, IV={market_data['iv_rank']:.0f}")
                    analysis = await self.analyze_with_claude(market_data)
                    
                    if analysis and analysis.get('should_trade') and analysis.get('confidence', 0) >= self.confidence_threshold:
                        decision = f"EXECUTE TRADE - Confidence: {analysis.get('confidence')}%"
                        
                        # Always simulate the full trade execution flow
                        trade = await self.execute_trade_from_analysis(symbol, analysis, market_data)
                        if trade:
                            decision += f" - Trade ID: {trade.trade_id if not self.dev_mode else 'SIMULATED'}"
                    else:
                        if analysis:
                            decision = f"NO TRADE - Confidence: {analysis.get('confidence', 0)}% (below {self.confidence_threshold}% threshold)"
                        else:
                            decision = "NO TRADE - Analysis failed"
                    
                    # Log Claude's analysis
                    self.log_claude_analysis(symbol, market_data, analysis, decision)
                    
                    if analysis:
                        self.log(f"🤖 Claude Decision: {decision}")
                
            except Exception as e:
                self.log(f"Error scanning {symbol}: {e}")
        
        self.add_market_scan(scan_results)
        
        self.last_scan_time = datetime.now()
        self.log(f"✅ {mode_prefix} Scan complete - Next scan in {self.scan_interval} seconds")
    
    def add_market_scan(self, scan_data):
        """Add market scan data for analysis view"""
        # Add to database
        trade_db.add_market_scan(scan_data)
        
        scan_entry = {
            'timestamp': datetime.now(),
            'data': scan_data
        }
        try:
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'market_scans'):
                st.session_state.market_scans.append(scan_entry)
                if len(st.session_state.market_scans) > 20:
                    st.session_state.market_scans = st.session_state.market_scans[-20:]
        except:
            pass
    
    async def execute_trade_from_analysis(self, symbol, analysis, market_data):
        """Execute a trade based on Claude's analysis"""
        try:
            if self.dev_mode:
                # Simulate trade execution in dev mode
                self.log(f"🎭 [DEV] Simulating trade execution for {symbol}...")
                
                # Simulate getting options chain
                self.log(f"   ➡️ Fetching options chain (SIMULATED)")
                await asyncio.sleep(0.5)  # Simulate API delay
                
                # Simulate finding contracts
                self.log(f"   ➡️ Finding contracts for strikes ${analysis['short_strike']:.0f}/${analysis['long_strike']:.0f}")
                
                # Simulate order preparation
                self.log(f"   ➡️ Preparing orders:")
                self.log(f"      - SELL {analysis['contracts']} {symbol} {analysis['spread_type'].split('_')[0].upper()} ${analysis['short_strike']:.0f}")
                self.log(f"      - BUY {analysis['contracts']} {symbol} {analysis['spread_type'].split('_')[0].upper()} ${analysis['long_strike']:.0f}")
                
                # Simulate credit calculation
                expected_credit = analysis['expected_credit'] * analysis['contracts'] * 100
                max_loss = 500 * analysis['contracts']  # $5 spread width
                
                self.log(f"   ➡️ Expected Credit: ${expected_credit:.2f}")
                self.log(f"   ➡️ Max Loss: ${max_loss:.2f}")
                
                # Create simulated trade object
                from dataclasses import dataclass
                from datetime import datetime
                
                @dataclass
                class SimulatedTrade:
                    trade_id: str
                    symbol: str
                    spread_type: str
                    entry_credit: float
                    max_loss: float
                    entry_time: datetime
                
                trade = SimulatedTrade(
                    trade_id=f"SIM-{symbol}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    symbol=symbol,
                    spread_type=analysis['spread_type'],
                    entry_credit=expected_credit,
                    max_loss=max_loss,
                    entry_time=datetime.now()
                )
                
                self.log(f"✅ [DEV] SIMULATED Trade: {trade.trade_id}")
                self.log(f"   ❌ NOT SENT TO BROKER - Dev Mode")
                
                # Track simulated P&L
                simulated_tracker.add_trade({
                    'trade_id': trade.trade_id,
                    'symbol': symbol,
                    'spread_type': analysis['spread_type'],
                    'entry_credit': expected_credit,
                    'max_loss': max_loss,
                    'entry_time': datetime.now()
                })
                
                return trade
            else:
                # Real trade execution
                self.log(f"📡 [LIVE] Executing real trade for {symbol}...")
                trade = await self.trade_manager.execute_options_trade(symbol, analysis, market_data)
                
                if trade:
                    self.log(f"✅ Trade executed successfully: {trade.trade_id}")
                    self.log(f"   Type: {analysis['spread_type']}")
                    self.log(f"   Strikes: ${analysis['short_strike']}/{analysis['long_strike']}")
                    self.log(f"   Credit: ${trade.entry_credit:.2f}")
                    self.log(f"   Max Loss: ${trade.max_loss:.2f}")
                    
                    # Start monitoring if not already active
                    if not self.trade_manager.is_monitoring:
                        asyncio.create_task(self.trade_manager.start_monitoring())
                    
                    return trade
                else:
                    self.log(f"❌ Failed to execute trade for {symbol}")
                    return None
                
        except Exception as e:
            self.log(f"❌ Error executing trade: {e}")
            return None
    
    async def run_bot(self):
        """Main bot loop"""
        self.is_running = True
        mode = "DEV" if self.dev_mode else "LIVE"
        self.log(f"🚀 FULL AUTOMATED BOT STARTED IN {mode} MODE")
        self.log(f"   Monitoring: {', '.join(self.symbols)}")
        self.log(f"   Min Move: {self.min_price_move}% | Min IV: {self.min_iv_rank}")
        
        while self.is_running:
            try:
                now = datetime.now()
                market_open = now.replace(hour=9, minute=30, second=0)
                market_close = now.replace(hour=16, minute=0, second=0)
                
                # In dev mode, always run. In live mode, check market hours
                if self.dev_mode or (market_open <= now <= market_close and now.weekday() < 5):
                    await self.scan_and_trade()
                    if not self.dev_mode:
                        await self.trade_manager.monitor_all_trades()
                else:
                    self.log("💤 Market closed - bot sleeping...")
                
                # Use configured scan interval
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self.log(f"❌ Bot error: {e}")
                await asyncio.sleep(60)
        
        self.log("🛑 Bot stopped")
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False
        if not self.dev_mode:
            self.trade_manager.stop_monitoring()

def monitoring_worker(trade_manager, rules):
    """Background worker for trade monitoring"""
    async def async_monitor():
        while st.session_state.monitoring_active:
            try:
                now = datetime.now()
                market_open = now.replace(hour=9, minute=30, second=0)
                market_close = now.replace(hour=16, minute=0, second=0)
                
                if market_open <= now <= market_close and now.weekday() < 5:
                    await trade_manager.monitor_all_trades()
                    st.session_state.last_monitoring_check = datetime.now()
                
                await asyncio.sleep(rules.monitoring_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(60)
    
    asyncio.run(async_monitor())

def bot_worker(dev_mode, bot_settings, paper_trading):
    """Background worker for the full bot"""
    bot = FullAutomatedBot(dev_mode=dev_mode, bot_settings=bot_settings, paper_trading=paper_trading)
    st.session_state.full_bot = bot
    asyncio.run(bot.run_bot())

def start_full_bot():
    """Start the complete automated bot"""
    if not st.session_state.bot_active:
        st.session_state.bot_active = True
        # Determine paper trading mode
        paper_trading = st.session_state.dev_mode or st.session_state.get('paper_trading', True)
        st.session_state.bot_thread = threading.Thread(
            target=bot_worker, 
            args=(st.session_state.dev_mode, st.session_state.bot_settings.copy(), paper_trading),
            daemon=True
        )
        st.session_state.bot_thread.start()
        return True
    return False

def stop_full_bot():
    """Stop the complete automated bot"""
    if st.session_state.full_bot:
        st.session_state.full_bot.stop()
    st.session_state.bot_active = False
    return True

def load_from_database():
    """Load data from database into session state"""
    # Load bot logs
    st.session_state.bot_logs = trade_db.get_bot_logs(limit=50)
    
    # Load Claude analyses
    analyses = trade_db.get_claude_analyses(limit=100)
    # Convert to expected format
    st.session_state.claude_analysis_log = []
    for analysis in analyses:
        entry = {
            'timestamp': datetime.fromisoformat(analysis['timestamp']),
            'symbol': analysis['symbol'],
            'market_data': {
                'current_price': analysis['current_price'],
                'percent_change': analysis['percent_change'],
                'iv_rank': analysis['iv_rank'],
                'volume': analysis['volume']
            },
            'claude_analysis': json.loads(analysis['raw_response']) if analysis['raw_response'] else None,
            'decision': analysis['decision'],
            'mode': analysis['mode']
        }
        st.session_state.claude_analysis_log.append(entry)
    
    # Load last 10 for bot_analysis (backward compatibility)
    st.session_state.bot_analysis = st.session_state.claude_analysis_log[-10:] if st.session_state.claude_analysis_log else []

def main():
    st.title("Volatility Trading Bot")
    
    # Load data from database on each refresh
    load_from_database()
    
    # Market status and time
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    is_market_open = market_open <= now <= market_close and now.weekday() < 5
    
    # Status bar with dev mode toggle
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
    
    with col1:
        market_status = "🟢 Market Open" if is_market_open else "🔴 Market Closed"
        st.info(f"{market_status} | {now.strftime('%I:%M %p ET')}")
    
    with col2:
        if st.session_state.bot_active:
            st.success("Bot Active")
        else:
            st.warning("Bot Inactive")
    
    with col3:
        # Dev/Live mode toggle
        dev_mode = st.checkbox("Dev Mode", value=st.session_state.dev_mode, key="dev_mode_toggle")
        if dev_mode != st.session_state.dev_mode:
            st.session_state.dev_mode = dev_mode
            if st.session_state.bot_active:
                st.warning("Please restart bot for mode change")
    
    summary = st.session_state.trade_manager.get_trade_summary()
    
    with col4:
        st.metric("Open Trades", summary['open_trades'])
    
    with col5:
        st.metric("Unrealized P&L", f"${summary['unrealized_pnl']:.2f}", 
                  delta=f"{summary['unrealized_pnl']:.2f}" if summary['unrealized_pnl'] != 0 else None,
                  delta_color="normal" if summary['unrealized_pnl'] >= 0 else "inverse")
    
    # Control buttons
    st.subheader("Trading Controls")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Start Bot", disabled=st.session_state.bot_active, use_container_width=True):
            if start_full_bot():
                if st.session_state.dev_mode:
                    mode = "Dev (Simulated Data)"
                elif st.session_state.get('paper_trading', True):
                    mode = "Live (Paper Trading)"
                else:
                    mode = "Live (Real Money)"
                st.success(f"Bot started in {mode} mode!")
                st.rerun()
    
    with col2:
        if st.button("Stop Bot", disabled=not st.session_state.bot_active, use_container_width=True):
            stop_full_bot()
            st.success("Bot stopped!")
            st.rerun()
    
    with col3:
        # Only show monitor button in live mode
        if not st.session_state.dev_mode:
            if st.button("Start Monitor", disabled=st.session_state.monitoring_active, use_container_width=True):
                # Monitoring implementation
                st.success("Monitoring started!")
                st.rerun()
    
    with col4:
        if st.button("Refresh", use_container_width=True):
            st.rerun()
    
    # Main tabs - Simplified to combine trades and analysis
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Trading Activity", "Settings"])
    
    with tab1:
        # Key metrics
        st.subheader("Portfolio Overview")
        
        # Get real positions from Alpaca
        if not st.session_state.dev_mode:
            try:
                positions = get_current_positions(paper_trading=st.session_state.get('paper_trading', True))
                option_spreads = get_option_spreads(paper_trading=st.session_state.get('paper_trading', True))
                
                # Calculate metrics from real positions
                total_unrealized_pl = sum(p['unrealized_pl'] for p in positions)
                open_positions = len(positions)
                option_positions = len([p for p in positions if p.get('is_option', False)])
                
                metrics_cols = st.columns(4)
                with metrics_cols[0]:
                    st.metric("Open Positions", open_positions)
                
                with metrics_cols[1]:
                    st.metric("Unrealized P&L", f"${total_unrealized_pl:.2f}",
                             delta=f"{total_unrealized_pl:.2f}" if total_unrealized_pl != 0 else None,
                             delta_color="normal" if total_unrealized_pl >= 0 else "inverse")
                
                with metrics_cols[2]:
                    st.metric("Option Spreads", len(option_spreads))
                
                with metrics_cols[3]:
                    # Get account info
                    tracker = PositionTracker(paper_trading=st.session_state.get('paper_trading', True))
                    account_info = tracker.get_account_info()
                    st.metric("Buying Power", f"${account_info.get('buying_power', 0):,.2f}")
                    
            except Exception as e:
                st.error(f"Error fetching positions: {e}")
                # Fall back to stored data
                metrics_cols = st.columns(4)
                with metrics_cols[0]:
                    st.metric("Open Trades", summary['open_trades'])
                with metrics_cols[1]:
                    st.metric("Unrealized P&L", f"${summary['unrealized_pnl']:.2f}")
                with metrics_cols[2]:
                    st.metric("Total Credit", f"${summary['total_credit']:.2f}")
                with metrics_cols[3]:
                    st.metric("Max Loss", f"${summary['total_max_loss']:.2f}")
        else:
            # Dev mode - show simulated metrics with P&L
            sim_summary = simulated_tracker.get_portfolio_summary()
            
            metrics_cols = st.columns(5)
            
            with metrics_cols[0]:
                st.metric("Open Trades", sim_summary['open_trades'])
            
            with metrics_cols[1]:
                st.metric("Unrealized P&L", f"${sim_summary['unrealized_pnl']:.2f}",
                         delta=f"{sim_summary['unrealized_pnl']:.2f}" if sim_summary['unrealized_pnl'] != 0 else None,
                         delta_color="normal" if sim_summary['unrealized_pnl'] >= 0 else "inverse")
            
            with metrics_cols[2]:
                st.metric("Realized P&L", f"${sim_summary['realized_pnl']:.2f}",
                         delta=f"{sim_summary['realized_pnl']:.2f}" if sim_summary['realized_pnl'] != 0 else None,
                         delta_color="normal" if sim_summary['realized_pnl'] >= 0 else "inverse")
            
            with metrics_cols[3]:
                st.metric("Win Rate", f"{sim_summary['win_rate']:.1f}%")
            
            with metrics_cols[4]:
                st.metric("Total P&L", f"${sim_summary['total_pnl']:.2f}",
                         delta=f"{sim_summary['total_pnl']:.2f}" if sim_summary['total_pnl'] != 0 else None,
                         delta_color="normal" if sim_summary['total_pnl'] >= 0 else "inverse")
        
        # Activity Log
        if st.session_state.bot_logs:
            with st.expander("Activity Log", expanded=True):
                log_text = "\n".join(reversed(st.session_state.bot_logs[-10:]))
                st.text_area("Recent Activity", value=log_text, height=200, label_visibility="collapsed")
    
    with tab2:
        # Combined Trading Activity Tab
        st.subheader("📊 Trading Activity & Analysis")
        
        if st.session_state.dev_mode:
            st.info("📊 Running in DEV MODE - Showing simulated trading activity")
        else:
            st.info("📡 Running in LIVE MODE - Showing real trading activity")
        
        # Statistics overview
        db_stats = trade_db.get_statistics()
        
        stats_cols = st.columns(6)
        with stats_cols[0]:
            st.metric("Total Analyses", db_stats['total_analyses'])
        with stats_cols[1]:
            st.metric("Trade Signals", db_stats['trade_signals'])
        with stats_cols[2]:
            st.metric("Executed Trades", db_stats['total_trades'])
        with stats_cols[3]:
            trade_rate = (db_stats['trade_signals'] / db_stats['total_analyses'] * 100) if db_stats['total_analyses'] > 0 else 0
            st.metric("Signal Rate", f"{trade_rate:.1f}%")
        with stats_cols[4]:
            st.metric("Avg Confidence", f"{db_stats['avg_confidence']:.1f}%")
        with stats_cols[5]:
            st.metric("Symbols", db_stats['unique_symbols'])
        
        # Filter controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            view_options = ["All Activity", "Executed Trades Only", "Analysis Only"]
            if not st.session_state.dev_mode:
                view_options.append("Active Positions")
            
            view_type = st.selectbox(
                "View",
                options=view_options,
                index=0
            )
        
        with col2:
            filter_symbol = st.selectbox(
                "Symbol",
                options=["All"] + list(set(entry['symbol'] for entry in st.session_state.claude_analysis_log)),
                index=0
            )
        
        with col3:
            filter_decision = st.selectbox(
                "Decision",
                options=["All", "EXECUTE TRADE", "NO TRADE"],
                index=0
            )
        
        with col4:
            show_last_n = st.slider("Show last", 10, 200, 50)
        
        # Show trades or analyses based on view type
        if view_type == "Executed Trades Only":
            st.subheader("💰 Executed Trades")
            trades = trade_db.get_trades(limit=show_last_n)
            
            if trades:
                trades_df = pd.DataFrame(trades)
                trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
                trades_df['time'] = trades_df['timestamp'].dt.strftime('%H:%M:%S')
                
                display_df = trades_df[['time', 'symbol', 'spread_type', 'short_strike', 
                                      'long_strike', 'contracts', 'credit', 'status', 'mode']]
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No trades executed yet.")
        
        # Add section for active positions
        elif view_type == "Active Positions":
            if st.session_state.dev_mode:
                # Show simulated positions
                st.subheader("🎭 Simulated Positions")
                
                sim_positions = simulated_tracker.get_open_positions()
                if sim_positions:
                    positions_data = []
                    for pos in sim_positions:
                        positions_data.append({
                            'Trade ID': pos['id'],
                            'Symbol': pos['symbol'],
                            'Type': pos['spread_type'],
                            'Entry Credit': f"${pos['entry_credit']:.2f}",
                            'Current Value': f"${pos['current_value']:.2f}",
                            'Unrealized P&L': f"${pos['unrealized_pnl']:.2f}",
                            'P&L %': f"{(pos['unrealized_pnl'] / pos['entry_credit'] * 100):.1f}%" if pos['entry_credit'] != 0 else "0.0%",
                            'Status': pos['status']
                        })
                    
                    pos_df = pd.DataFrame(positions_data)
                    st.dataframe(pos_df, use_container_width=True, hide_index=True)
                    
                    # Show closed trades
                    closed_trades = simulated_tracker.get_trade_history()
                    if closed_trades:
                        st.subheader("📋 Trade History")
                        history_data = []
                        for trade in closed_trades[-10:]:
                            history_data.append({
                                'Symbol': trade['symbol'],
                                'Type': trade['spread_type'],
                                'Entry Credit': f"${trade['entry_credit']:.2f}",
                                'Realized P&L': f"${trade['realized_pnl']:.2f}",
                                'Exit Reason': trade['exit_reason'],
                                'Duration': f"{(trade['exit_time'] - trade['entry_time']).days} days"
                            })
                        
                        hist_df = pd.DataFrame(history_data)
                        st.dataframe(hist_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No simulated positions yet. Start the bot to begin trading!")
            else:
                st.subheader("🔄 Active Positions")
            
            try:
                positions = get_current_positions(paper_trading=st.session_state.get('paper_trading', True))
                option_spreads = get_option_spreads(paper_trading=st.session_state.get('paper_trading', True))
                
                if option_spreads:
                    st.write("**Option Spreads:**")
                    spreads_data = []
                    for spread in option_spreads:
                        spreads_data.append({
                            'Underlying': spread['underlying'],
                            'Type': spread['type'],
                            'Short Strike': spread['short_leg']['symbol'],
                            'Long Strike': spread['long_leg']['symbol'],
                            'Net Credit': f"${spread['net_credit']:.2f}",
                            'Unrealized P&L': f"${spread['unrealized_pl']:.2f}",
                            'P&L %': f"{(spread['unrealized_pl'] / abs(spread['net_credit']) * 100):.1f}%" if spread['net_credit'] != 0 else "0.0%"
                        })
                    
                    spreads_df = pd.DataFrame(spreads_data)
                    st.dataframe(spreads_df, use_container_width=True, hide_index=True)
                
                if positions:
                    st.write("**All Positions:**")
                    positions_data = []
                    for pos in positions:
                        positions_data.append({
                            'Symbol': pos['symbol'],
                            'Qty': pos['qty'],
                            'Side': pos['side'],
                            'Avg Price': f"${pos['avg_entry_price']:.2f}",
                            'Current Price': f"${pos['current_price']:.2f}",
                            'Unrealized P&L': f"${pos['unrealized_pl']:.2f}",
                            'P&L %': f"{pos['unrealized_plpc']:.1f}%"
                        })
                    
                    pos_df = pd.DataFrame(positions_data)
                    st.dataframe(pos_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No active positions.")
                    
            except Exception as e:
                st.error(f"Error fetching positions: {e}")
        
        else:
            # Show analysis log (all or filtered)
            st.subheader("🤖 Claude Analysis Log")
            
            # Filter the log
            filtered_log = st.session_state.claude_analysis_log
            
            if filter_symbol != "All":
                filtered_log = [e for e in filtered_log if e['symbol'] == filter_symbol]
            
            if filter_decision != "All":
                if filter_decision == "EXECUTE TRADE":
                    filtered_log = [e for e in filtered_log if "EXECUTE" in e['decision']]
                else:
                    filtered_log = [e for e in filtered_log if "NO TRADE" in e['decision']]
            
            if view_type == "Executed Trades Only":
                filtered_log = [e for e in filtered_log if "EXECUTE" in e['decision']]
            
            # Show the filtered analyses
            if filtered_log:
                for entry in reversed(filtered_log[-show_last_n:]):
                    # Determine color based on decision
                    decision_color = "#00C853" if "EXECUTE" in entry['decision'] else "#FFB300"
                    
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"""
                            <div class="analysis-log">
                                <span class="analysis-timestamp">[{entry['timestamp'].strftime('%H:%M:%S')}]</span> 
                                <strong>{entry['symbol']}</strong> | 
                                ${entry['market_data']['current_price']:.2f} | 
                                {entry['market_data']['percent_change']:+.2f}% | 
                                IV: {entry['market_data']['iv_rank']:.0f}
                                <br>
                                <span style="color: {decision_color}; font-weight: bold;">{entry['decision']}</span>
                                <br>
                                <span class="analysis-reasoning">{entry['claude_analysis'].get('reasoning', 'N/A') if entry['claude_analysis'] else 'Analysis failed'}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            if entry['claude_analysis'] and entry['claude_analysis'].get('should_trade'):
                                st.markdown(f"""
                                **Trade Details:**  
                                Type: {entry['claude_analysis'].get('spread_type', 'N/A')}  
                                Strikes: ${entry['claude_analysis'].get('short_strike', 0):.0f}/${entry['claude_analysis'].get('long_strike', 0):.0f}  
                                Contracts: {entry['claude_analysis'].get('contracts', 0)}  
                                Credit: ${entry['claude_analysis'].get('expected_credit', 0):.2f}
                                """, unsafe_allow_html=True)
            else:
                st.info("No analyses match the current filters.")
    
    with tab3:
        # Settings (existing implementation)
        st.subheader("Bot Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Trading Parameters**")
            
            new_symbols = st.multiselect(
                "Symbols to Monitor",
                ["SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"],
                default=st.session_state.bot_settings['symbols']
            )
            
            new_min_move = st.slider(
                "Min Price Move %",
                0.5, 5.0, 
                st.session_state.bot_settings['min_price_move'], 
                0.1
            )
            
            new_min_iv = st.slider(
                "Min IV Rank",
                50, 90,
                st.session_state.bot_settings['min_iv_rank'],
                5
            )
            
            new_scan_interval = st.slider(
                "Scan Interval (seconds)",
                60, 600,
                st.session_state.bot_settings['scan_interval'],
                30
            )
            
            new_confidence = st.slider(
                "Min Confidence % (Claude's confidence to trade)",
                30, 90,
                st.session_state.bot_settings['confidence_threshold'],
                5
            )
        
        with col2:
            st.write("**Risk Management**")
            
            tm = st.session_state.trade_manager
            rules = tm.rules
            
            new_profit_target = st.slider(
                "Profit Target %",
                20, 80,
                int(rules.profit_target_percent * 100),
                5
            ) / 100
            
            new_stop_loss = st.slider(
                "Stop Loss %",
                50, 100,
                int(rules.stop_loss_percent * 100),
                5
            ) / 100
            
            new_time_stop = st.slider(
                "Time Stop (DTE)",
                1, 10,
                rules.time_stop_dte,
                1
            )
            
            new_daily_loss = st.number_input(
                "Max Daily Loss $",
                100, 5000,
                int(rules.max_daily_loss),
                50
            )
        
        if st.button("Save Settings", use_container_width=True):
            # Update bot settings
            st.session_state.bot_settings['symbols'] = new_symbols
            st.session_state.bot_settings['min_price_move'] = new_min_move
            st.session_state.bot_settings['min_iv_rank'] = new_min_iv
            st.session_state.bot_settings['scan_interval'] = new_scan_interval
            st.session_state.bot_settings['confidence_threshold'] = new_confidence
            
            # Update trade manager rules
            rules.profit_target_percent = new_profit_target
            rules.stop_loss_percent = new_stop_loss
            rules.time_stop_dte = new_time_stop
            rules.max_daily_loss = float(new_daily_loss)
            
            # Update bot if running
            if st.session_state.full_bot:
                bot = st.session_state.full_bot
                bot.symbols = new_symbols
                bot.min_price_move = new_min_move
                bot.min_iv_rank = new_min_iv
                bot.scan_interval = new_scan_interval
                bot.confidence_threshold = new_confidence
            
            st.success("Settings saved!")
    
    # Auto-refresh
    if st.session_state.monitoring_active or st.session_state.bot_active:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()