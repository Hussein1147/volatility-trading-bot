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
from enhanced_trade_manager import EnhancedTradeManager, TradeManagementRules, OptionContract
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(
    page_title="Volatility Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern dark theme CSS
st.markdown("""
<style>
    /* Dark theme colors inspired by Webull/Robinhood */
    .stApp {
        background-color: #0a0a0a;
        color: #ffffff;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1a1a1a;
    }
    
    /* Metrics styling */
    [data-testid="metric-container"] {
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #00c805;
        color: #000000;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #00ff00;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,255,0,0.3);
    }
    
    /* Danger buttons */
    .stButton > button[kind="secondary"] {
        background-color: #ff3860;
        color: #ffffff;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 4px;
    }
    
    /* DataFrame styling */
    .dataframe {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1a1a1a;
        padding: 10px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #2a2a2a;
        color: #888888;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #00c805 !important;
        color: #000000 !important;
    }
    
    /* Success/Error styling */
    .stSuccess {
        background-color: rgba(0, 200, 5, 0.1);
        border: 1px solid #00c805;
        color: #00c805;
    }
    
    .stError {
        background-color: rgba(255, 56, 96, 0.1);
        border: 1px solid #ff3860;
        color: #ff3860;
    }
    
    .stWarning {
        background-color: rgba(255, 193, 7, 0.1);
        border: 1px solid #ffc107;
        color: #ffc107;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        background-color: #2a2a2a;
        color: #ffffff;
        border: 1px solid #3a3a3a;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff;
    }
    
    /* Plotly charts dark theme */
    .js-plotly-plot .plotly {
        background-color: #1a1a1a !important;
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

class FullAutomatedBot:
    def __init__(self):
        self.trade_manager = EnhancedTradeManager()
        self.is_running = False
        # Use settings from session state if available
        settings = getattr(st.session_state, 'bot_settings', {})
        self.symbols = settings.get('symbols', ['SPY', 'QQQ', 'IWM', 'DIA'])
        self.min_price_move = settings.get('min_price_move', 1.5)  # 1.5% minimum move
        self.min_iv_rank = settings.get('min_iv_rank', 70)  # Minimum IV rank
        self.scan_interval = settings.get('scan_interval', 300)  # 5 minutes
        self.confidence_threshold = settings.get('confidence_threshold', 70)
        self.last_scan_time = None
        
    def log(self, message):
        """Add log message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        st.session_state.bot_logs.append(log_entry)
        # Keep only last 50 logs
        if len(st.session_state.bot_logs) > 50:
            st.session_state.bot_logs = st.session_state.bot_logs[-50:]
        print(log_entry)  # Also print to console
    
    def add_market_scan(self, scan_data):
        """Add market scan data for analysis view"""
        scan_entry = {
            'timestamp': datetime.now(),
            'data': scan_data
        }
        st.session_state.market_scans.append(scan_entry)
        # Keep only last 20 scans
        if len(st.session_state.market_scans) > 20:
            st.session_state.market_scans = st.session_state.market_scans[-20:]
    
    def add_analysis(self, symbol, market_data, analysis, decision):
        """Add Claude analysis for display"""
        analysis_entry = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'market_data': market_data,
            'claude_analysis': analysis,
            'bot_decision': decision
        }
        st.session_state.bot_analysis.append(analysis_entry)
        # Keep only last 10 analyses
        if len(st.session_state.bot_analysis) > 10:
            st.session_state.bot_analysis = st.session_state.bot_analysis[-10:]
    
    async def get_market_data(self, symbol):
        """Get current market data and calculate IV metrics"""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
            from alpaca.data.timeframe import TimeFrame
            
            # Get current price
            data_client = StockHistoricalDataClient(
                api_key=os.getenv('ALPACA_API_KEY'),
                secret_key=os.getenv('ALPACA_SECRET_KEY')
            )
            
            quotes = data_client.get_stock_latest_quote(
                StockQuotesRequest(symbol_or_symbols=symbol)
            )
            current_price = float(quotes[symbol].ask_price)
            
            # Get today's bars for % change
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
            
            # Calculate IV rank using real options data from Algo Trader Plus subscription
            try:
                # Get real options data to calculate actual IV rank
                exp_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
                options_data = await self.trade_manager.get_real_time_options_data(symbol, exp_date)
                
                if options_data:
                    # Calculate IV rank from real options data
                    iv_values = [opt.implied_volatility for opt in options_data if opt.implied_volatility > 0]
                    if iv_values:
                        current_iv = np.mean(iv_values)
                        iv_rank = min(100, current_iv * 400)  # Convert to rank scale
                        self.log(f"   Using REAL options data: {len(options_data)} contracts, avg IV: {current_iv:.2%}")
                    else:
                        iv_rank = min(100, abs(percent_change) * 20 + np.random.uniform(40, 80))
                        self.log(f"   Real options data available but no IV values")
                else:
                    iv_rank = min(100, abs(percent_change) * 20 + np.random.uniform(40, 80))
                    self.log(f"   Using simulated IV data (fallback)")
            except Exception as iv_error:
                iv_rank = min(100, abs(percent_change) * 20 + np.random.uniform(40, 80))
                self.log(f"   IV calculation error: {str(iv_error)[:50]}...")
            
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
                model="claude-4-sonnet-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\\{.*\\}', response.content[0].text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                return analysis
            else:
                self.log(f"Could not parse Claude response for {market_data['symbol']}")
                return None
                
        except Exception as e:
            self.log(f"Error analyzing with Claude: {e}")
            return None
    
    async def execute_trade_from_analysis(self, symbol, analysis, market_data):
        """Execute a trade based on Claude's analysis"""
        try:
            if not analysis or not analysis.get('should_trade'):
                return None
            
            # Calculate trade parameters
            spread_width = abs(analysis['long_strike'] - analysis['short_strike'])
            max_loss = (spread_width * 100 - analysis['expected_credit']) * analysis['contracts']
            
            # Create option contracts (simulated for demo)
            exp_date = (datetime.now() + timedelta(days=analysis['expiration_days'])).strftime('%Y-%m-%d')
            
            short_leg = OptionContract(
                symbol=f"{symbol}_{exp_date}_{analysis['spread_type'][0].upper()}{int(analysis['short_strike']):08d}",
                strike_price=analysis['short_strike'],
                expiration_date=exp_date,
                option_type="call" if "call" in analysis['spread_type'] else "put",
                bid_price=analysis['expected_credit'] / analysis['contracts'] + 0.1,
                ask_price=analysis['expected_credit'] / analysis['contracts'] + 0.2,
                volume=100, open_interest=500,
                delta=0.25, gamma=0.1, theta=-0.04, vega=0.15, implied_volatility=0.28
            )
            
            long_leg = OptionContract(
                symbol=f"{symbol}_{exp_date}_{analysis['spread_type'][0].upper()}{int(analysis['long_strike']):08d}",
                strike_price=analysis['long_strike'],
                expiration_date=exp_date,
                option_type="call" if "call" in analysis['spread_type'] else "put",
                bid_price=0.8, ask_price=0.9,
                volume=80, open_interest=300,
                delta=0.15, gamma=0.08, theta=-0.02, vega=0.12, implied_volatility=0.25
            )
            
            trade_data = {
                'symbol': symbol,
                'strategy_type': 'automated_credit_spread',
                'spread_type': analysis['spread_type'],
                'short_leg': short_leg,
                'long_leg': long_leg,
                'contracts': analysis['contracts'],
                'entry_credit': analysis['expected_credit'],
                'max_loss': max_loss,
                'probability_profit': 75,  # Could calculate based on strikes
                'confidence_score': analysis['confidence'],
                'claude_reasoning': analysis['reasoning']
            }
            
            trade = await self.trade_manager.add_trade(trade_data)
            
            self.log(f"✅ EXECUTED TRADE: {analysis['spread_type']} on {symbol}")
            self.log(f"   Strikes: ${analysis['short_strike']:.0f}/${analysis['long_strike']:.0f}")
            self.log(f"   Credit: ${analysis['expected_credit']:.2f}, Contracts: {analysis['contracts']}")
            self.log(f"   Confidence: {analysis['confidence']}% - {analysis['reasoning'][:50]}...")
            
            return trade
            
        except Exception as e:
            self.log(f"Error executing trade: {e}")
            return None
    
    async def scan_and_trade(self):
        """Main scanning and trading loop"""
        self.log("🔍 Starting market scan...")
        scan_results = []
        
        for symbol in self.symbols:
            try:
                # Get market data
                market_data = await self.get_market_data(symbol)
                if not market_data:
                    continue
                
                scan_results.append(market_data)
                self.log(f"📊 {symbol}: ${market_data['current_price']:.2f} ({market_data['percent_change']:+.2f}%) IV:{market_data['iv_rank']:.0f}")
                
                # Check if significant move
                if (abs(market_data['percent_change']) >= self.min_price_move and 
                    market_data['iv_rank'] >= self.min_iv_rank):
                    
                    self.log(f"🚨 VOLATILITY SPIKE: {symbol} moved {market_data['percent_change']:.2f}% with IV rank {market_data['iv_rank']:.0f}")
                    
                    # Analyze with Claude
                    analysis = await self.analyze_with_claude(market_data)
                    
                    # Determine bot decision
                    if analysis and analysis.get('should_trade') and analysis.get('confidence', 0) >= self.confidence_threshold:
                        decision = f"EXECUTE TRADE - Confidence: {analysis.get('confidence')}%"
                        
                        # Execute trade
                        trade = await self.execute_trade_from_analysis(symbol, analysis, market_data)
                        if trade:
                            decision += f" - Trade ID: {trade.trade_id}"
                            # Start monitoring this trade
                            if not self.trade_manager.is_monitoring:
                                await self.trade_manager.start_monitoring()
                    elif analysis:
                        decision = f"NO TRADE - Confidence: {analysis.get('confidence', 0)}% (below 70% threshold)"
                    else:
                        decision = "NO TRADE - Analysis failed"
                    
                    # Store analysis for display
                    self.add_analysis(symbol, market_data, analysis, decision)
                    
                    if analysis:
                        self.log(f"🤖 Claude Decision: {decision}")
                
            except Exception as e:
                self.log(f"Error scanning {symbol}: {e}")
        
        # Store scan data
        self.add_market_scan(scan_results)
        
        self.last_scan_time = datetime.now()
        self.log(f"✅ Scan complete - Next scan in {self.scan_interval} seconds")
    
    async def run_bot(self):
        """Main bot loop"""
        self.is_running = True
        self.log("🚀 FULL AUTOMATED BOT STARTED")
        self.log(f"   Monitoring: {', '.join(self.symbols)}")
        self.log(f"   Min Move: {self.min_price_move}% | Min IV: {self.min_iv_rank}")
        
        while self.is_running:
            try:
                # Check if market hours
                now = datetime.now()
                market_open = now.replace(hour=9, minute=30, second=0)
                market_close = now.replace(hour=16, minute=0, second=0)
                
                if market_open <= now <= market_close and now.weekday() < 5:
                    # Market is open - scan for opportunities
                    await self.scan_and_trade()
                    
                    # Also run trade monitoring
                    await self.trade_manager.monitor_all_trades()
                else:
                    self.log("💤 Market closed - bot sleeping...")
                
                # Wait before next scan
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self.log(f"❌ Bot error: {e}")
                await asyncio.sleep(60)
        
        self.log("🛑 Bot stopped")
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False
        self.trade_manager.stop_monitoring()

def monitoring_worker(trade_manager, rules):
    """Background worker for trade monitoring"""
    async def async_monitor():
        while st.session_state.monitoring_active:
            try:
                # Only monitor during market hours
                now = datetime.now()
                market_open = now.replace(hour=9, minute=30, second=0)
                market_close = now.replace(hour=16, minute=0, second=0)
                
                if market_open <= now <= market_close and now.weekday() < 5:
                    await trade_manager.monitor_all_trades()
                    st.session_state.last_monitoring_check = datetime.now()
                
                # Wait for next check
                await asyncio.sleep(rules.monitoring_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(60)
    
    # Run the async monitor
    asyncio.run(async_monitor())

def start_monitoring():
    """Start monitoring in background thread"""
    if not st.session_state.monitoring_active:
        st.session_state.monitoring_active = True
        st.session_state.monitoring_thread = threading.Thread(
            target=monitoring_worker,
            args=(st.session_state.trade_manager, st.session_state.trade_manager.rules),
            daemon=True
        )
        st.session_state.monitoring_thread.start()
        return True
    return False

def stop_monitoring():
    """Stop monitoring"""
    st.session_state.monitoring_active = False
    if st.session_state.monitoring_thread:
        st.session_state.monitoring_thread = None
    return True

def bot_worker():
    """Background worker for the full bot"""
    bot = FullAutomatedBot()
    st.session_state.full_bot = bot
    asyncio.run(bot.run_bot())

def start_full_bot():
    """Start the complete automated bot"""
    if not st.session_state.bot_active:
        st.session_state.bot_active = True
        st.session_state.bot_thread = threading.Thread(target=bot_worker, daemon=True)
        st.session_state.bot_thread.start()
        return True
    return False

def stop_full_bot():
    """Stop the complete automated bot"""
    if st.session_state.full_bot:
        st.session_state.full_bot.stop()
    st.session_state.bot_active = False
    return True

def main():
    # Modern header with custom styling
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h1 style='font-size: 2.5em; font-weight: 300; margin: 0; background: linear-gradient(90deg, #00c805 0%, #00ff00 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                Volatility Trading Terminal
            </h1>
            <p style='color: #888; font-size: 1.1em; margin-top: 10px;'>Professional Options Trading Platform</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Status bar
    status_cols = st.columns([1, 1, 1, 1, 1])
    
    # Market Status
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    is_market_open = market_open <= now <= market_close and now.weekday() < 5
    
    with status_cols[0]:
        market_icon = "🟢" if is_market_open else "🔴"
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background: #1a1a1a; border-radius: 8px;'>
            <div style='font-size: 0.8em; color: #888;'>MARKET</div>
            <div style='font-size: 1.2em; font-weight: 600;'>{market_icon} {'OPEN' if is_market_open else 'CLOSED'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with status_cols[1]:
        bot_icon = "🟢" if st.session_state.bot_active else "⚫"
        bot_status = "ACTIVE" if st.session_state.bot_active else "INACTIVE"
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background: #1a1a1a; border-radius: 8px;'>
            <div style='font-size: 0.8em; color: #888;'>BOT STATUS</div>
            <div style='font-size: 1.2em; font-weight: 600;'>{bot_icon} {bot_status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with status_cols[2]:
        monitor_icon = "🟢" if st.session_state.monitoring_active else "⚫"
        monitor_status = "ON" if st.session_state.monitoring_active else "OFF"
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background: #1a1a1a; border-radius: 8px;'>
            <div style='font-size: 0.8em; color: #888;'>MONITORING</div>
            <div style='font-size: 1.2em; font-weight: 600;'>{monitor_icon} {monitor_status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    summary = st.session_state.trade_manager.get_trade_summary()
    
    with status_cols[3]:
        pnl_color = "#00c805" if summary['unrealized_pnl'] >= 0 else "#ff3860"
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background: #1a1a1a; border-radius: 8px;'>
            <div style='font-size: 0.8em; color: #888;'>UNREALIZED P&L</div>
            <div style='font-size: 1.2em; font-weight: 600; color: {pnl_color}'>${summary['unrealized_pnl']:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with status_cols[4]:
        st.markdown(f"""
        <div style='text-align: center; padding: 10px; background: #1a1a1a; border-radius: 8px;'>
            <div style='font-size: 0.8em; color: #888;'>TIME</div>
            <div style='font-size: 1.2em; font-weight: 600;'>{now.strftime('%H:%M:%S')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Initialize bot settings in session state if not present
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
    
    # Control Panel
    control_container = st.container()
    with control_container:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Trading controls in a modern card
            st.markdown("""
            <div style='background: #1a1a1a; padding: 20px; border-radius: 10px; border: 1px solid #2a2a2a;'>
                <h3 style='margin: 0 0 15px 0; color: #fff;'>🎮 Trading Controls</h3>
            </div>
            """, unsafe_allow_html=True)
            
            control_cols = st.columns(4)
            
            with control_cols[0]:
                if st.button("▶️ Start Bot", disabled=st.session_state.bot_active, use_container_width=True):
                    if start_full_bot():
                        st.success("✅ Bot started!")
                        st.rerun()
            
            with control_cols[1]:
                if st.button("⏸️ Stop Bot", disabled=not st.session_state.bot_active, use_container_width=True, type="secondary"):
                    stop_full_bot()
                    st.success("⏹️ Bot stopped!")
                    st.rerun()
            
            with control_cols[2]:
                if st.button("▶️ Monitor", disabled=st.session_state.monitoring_active, use_container_width=True):
                    if start_monitoring():
                        st.success("✅ Monitoring started!")
                        st.rerun()
            
            with control_cols[3]:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
        
        with col2:
            # Quick stats card
            st.markdown("""
            <div style='background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%); padding: 20px; border-radius: 10px; border: 1px solid #00c805;'>
                <h3 style='margin: 0 0 15px 0; color: #00c805;'>📊 Portfolio Stats</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.metric("Active Trades", summary["open_trades"], 
                      delta=f"{summary['open_trades']} positions" if summary['open_trades'] > 0 else None)
            st.metric("Total Credit", f"${summary['total_credit']:.2f}")
            
            pnl_delta = f"{'+' if summary['unrealized_pnl'] >= 0 else ''}{summary['unrealized_pnl']:.2f}"
            st.metric("Unrealized P&L", f"${summary['unrealized_pnl']:.2f}", delta=pnl_delta,
                     delta_color="normal" if summary['unrealized_pnl'] >= 0 else "inverse")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Dashboard", "🤖 AI Analysis", "📊 Active Trades", "🔍 Market Scanner", "📝 Trade Entry", "⚙️ Settings"])
    
    with tab1:
        # Dashboard Overview
        metrics_cols = st.columns(4)
        
        # Calculate additional metrics
        tm = st.session_state.trade_manager
        win_rate = 0
        closed_trades = getattr(tm, 'closed_trades', [])
        if closed_trades:
            wins = sum(1 for t in closed_trades if t.realized_pnl > 0)
            win_rate = (wins / len(closed_trades)) * 100
        
        with metrics_cols[0]:
            st.markdown("""
            <div style='background: #1a1a1a; padding: 20px; border-radius: 10px; text-align: center;'>
                <div style='font-size: 0.9em; color: #888; margin-bottom: 5px;'>WIN RATE</div>
                <div style='font-size: 2em; font-weight: bold; color: #00c805;'>{:.1f}%</div>
            </div>
            """.format(win_rate), unsafe_allow_html=True)
        
        with metrics_cols[1]:
            daily_pnl = sum(t.unrealized_pnl for t in tm.active_trades if t.entry_time.date() == datetime.now().date())
            pnl_color = "#00c805" if daily_pnl >= 0 else "#ff3860"
            st.markdown(f"""
            <div style='background: #1a1a1a; padding: 20px; border-radius: 10px; text-align: center;'>
                <div style='font-size: 0.9em; color: #888; margin-bottom: 5px;'>TODAY'S P&L</div>
                <div style='font-size: 2em; font-weight: bold; color: {pnl_color};'>${daily_pnl:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metrics_cols[2]:
            avg_credit = summary['total_credit'] / summary['open_trades'] if summary['open_trades'] > 0 else 0
            st.markdown(f"""
            <div style='background: #1a1a1a; padding: 20px; border-radius: 10px; text-align: center;'>
                <div style='font-size: 0.9em; color: #888; margin-bottom: 5px;'>AVG CREDIT</div>
                <div style='font-size: 2em; font-weight: bold; color: #ffc107;'>${avg_credit:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metrics_cols[3]:
            closed_trades_count = len(getattr(tm, 'closed_trades', []))
            total_volume = summary['open_trades'] + closed_trades_count
            st.markdown(f"""
            <div style='background: #1a1a1a; padding: 20px; border-radius: 10px; text-align: center;'>
                <div style='font-size: 0.9em; color: #888; margin-bottom: 5px;'>TOTAL TRADES</div>
                <div style='font-size: 2em; font-weight: bold; color: #17a2b8;'>{total_volume}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Performance Chart
        closed_trades = getattr(tm, 'closed_trades', [])
        if tm.active_trades or closed_trades:
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📈 Performance Overview")
            
            # Create performance data
            dates = []
            cumulative_pnl = []
            current_total = 0
            
            # Add closed trades
            for trade in sorted(closed_trades, key=lambda x: x.exit_time if hasattr(x, 'exit_time') else x.entry_time):
                if hasattr(trade, 'exit_time'):
                    dates.append(trade.exit_time)
                    current_total += trade.realized_pnl
                    cumulative_pnl.append(current_total)
            
            # Add current P&L
            if dates or tm.active_trades:
                dates.append(datetime.now())
                current_total += summary['unrealized_pnl']
                cumulative_pnl.append(current_total)
            
            if dates:
                fig = go.Figure()
                
                # Add the main line
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=cumulative_pnl,
                    mode='lines+markers',
                    name='Cumulative P&L',
                    line=dict(color='#00c805', width=3),
                    marker=dict(size=8),
                    fill='tozeroy',
                    fillcolor='rgba(0, 200, 5, 0.1)'
                ))
                
                # Add zero line
                fig.add_hline(y=0, line_dash="dash", line_color="#666")
                
                # Update layout for dark theme
                fig.update_layout(
                    template="plotly_dark",
                    height=400,
                    showlegend=False,
                    xaxis_title="Time",
                    yaxis_title="P&L ($)",
                    hovermode='x unified',
                    plot_bgcolor='#1a1a1a',
                    paper_bgcolor='#1a1a1a',
                    font=dict(color='#ffffff')
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Bot Activity Logs
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📋 Activity Logs", expanded=False):
            if st.session_state.bot_logs:
                # Show logs in reverse order (newest first)
                log_text = "\\n".join(reversed(st.session_state.bot_logs[-20:]))  # Last 20 logs
                st.text_area("Bot Logs", value=log_text, height=300, label_visibility="collapsed")
            else:
                st.info("No bot activity yet. Start the bot to see live logs.")
    
    with tab2:
        # AI Analysis Tab
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h2 style='color: #00c805;'>🤖 AI Trading Intelligence</h2>
            <p style='color: #888;'>Real-time market analysis powered by Claude 4</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.bot_analysis:
            for i, analysis in enumerate(reversed(st.session_state.bot_analysis[-5:])):
                with st.expander(f"🎯 {analysis['symbol']} Analysis - {analysis['timestamp'].strftime('%H:%M:%S')}", expanded=i==0):
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📊 Market Data:**")
                        market = analysis['market_data']
                        st.write(f"• Price: ${market['current_price']:.2f}")
                        st.write(f"• Change: {market['percent_change']:+.2f}%")
                        st.write(f"• IV Rank: {market['iv_rank']:.1f}")
                        st.write(f"• Volume: {market.get('volume', 'N/A'):,}")
                    
                    with col2:
                        st.markdown("**🤖 Bot Decision:**")
                        decision_color = "🟢" if "EXECUTE" in analysis['bot_decision'] else "🟡"
                        st.write(f"{decision_color} {analysis['bot_decision']}")
                    
                    if analysis['claude_analysis']:
                        st.markdown("**🧠 Claude 4 Analysis:**")
                        claude = analysis['claude_analysis']
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Confidence", f"{claude.get('confidence', 0)}%")
                        with col2:
                            st.metric("Action", claude.get('spread_type', 'N/A').replace('_', ' ').title() if claude.get('should_trade') else 'No Trade')
                        with col3:
                            if claude.get('should_trade'):
                                st.metric("Trade", "✅ YES")
                            else:
                                st.metric("Trade", "❌ NO")
                        
                        if claude.get('reasoning'):
                            st.info(f"💭 **Reasoning:** {claude['reasoning']}")
                        
                        if claude.get('should_trade'):
                            st.success(f"""
                            **📋 Trade Plan:**
                            • Strategy: {claude.get('spread_type', 'N/A').replace('_', ' ').title()}
                            • Short Strike: ${claude.get('short_strike', 0):.0f}
                            • Long Strike: ${claude.get('long_strike', 0):.0f}
                            • Contracts: {claude.get('contracts', 0)}
                            • Expected Credit: ${claude.get('expected_credit', 0):.2f}
                            • Expiration: {claude.get('expiration_days', 0)} days
                            """)
        else:
            st.info("🔍 No Claude analyses yet. Start the bot to see AI decision-making in real-time!")
    
    with tab3:
        # Active Trades Tab
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h2 style='color: #00c805;'>📊 Active Positions</h2>
            <p style='color: #888;'>Real-time monitoring of all open trades</p>
        </div>
        """, unsafe_allow_html=True)
        
        if tm.active_trades:
            trades_data = []
            
            for trade in tm.active_trades:
                # Calculate current status
                exp_date = datetime.strptime(trade.short_leg.expiration_date, '%Y-%m-%d')
                dte = (exp_date.date() - datetime.now().date()).days
                
                # Color coding for status
                status_color = "🟢" if trade.status == "OPEN" else "🟡" if trade.status == "CLOSING" else "🔴"
                
                trades_data.append({
                    'ID': trade.trade_id.split('_')[-1][:8],  # Shortened ID
                    'Symbol': trade.symbol,
                    'Type': trade.spread_type.replace('_', ' ').title(),
                    'Short': f"${trade.short_leg.strike_price:.0f}",
                    'Long': f"${trade.long_leg.strike_price:.0f}",
                    'Contracts': trade.contracts,
                    'Entry Credit': f"${trade.entry_credit:.2f}",
                    'Current P&L': f"${trade.unrealized_pnl:.2f}",
                    'Target': f"${trade.profit_target:.2f}",
                    'Stop': f"${-trade.stop_loss_target:.2f}",
                    'DTE': dte,
                    'Status': f"{status_color} {trade.status}",
                    'Entry': trade.entry_time.strftime('%m-%d %H:%M')
                })
            
            df = pd.DataFrame(trades_data)
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Quick Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                total_credit = sum(t.entry_credit for t in tm.active_trades)
                st.metric("Total Credit Collected", f"${total_credit:.2f}")
            with col2:
                total_pnl = sum(t.unrealized_pnl for t in tm.active_trades)
                st.metric("Total Unrealized P&L", f"${total_pnl:.2f}")
            with col3:
                avg_dte = sum((datetime.strptime(t.short_leg.expiration_date, '%Y-%m-%d').date() - datetime.now().date()).days for t in tm.active_trades) / len(tm.active_trades)
                st.metric("Average DTE", f"{avg_dte:.1f} days")
            
            # Trade Performance Chart
            if len(trades_data) > 1:
                st.subheader("📈 Trade Performance Chart")
                
                pnl_data = [t.unrealized_pnl for t in tm.active_trades]
                symbols = [t.symbol for t in tm.active_trades]
                
                fig = px.bar(
                    x=symbols,
                    y=pnl_data,
                    title="Current P&L by Trade",
                    labels={'x': 'Symbol', 'y': 'P&L ($)'},
                    color=pnl_data,
                    color_continuous_scale=['red', 'white', 'green']
                )
                
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                fig.update_layout(
                    template="plotly_dark",
                    plot_bgcolor='#1a1a1a',
                    paper_bgcolor='#1a1a1a',
                    font=dict(color='#ffffff')
                )
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.info("📭 No active trades. Start the bot or add a trade manually to begin.")
    
    with tab4:
        # Market Scanner Tab
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h2 style='color: #00c805;'>🔍 Market Scanner</h2>
            <p style='color: #888;'>Real-time volatility and opportunity detection</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.market_scans:
            latest_scan = st.session_state.market_scans[-1]
            st.markdown(f"**Latest Scan:** {latest_scan['timestamp'].strftime('%H:%M:%S')}")
            
            scan_df = pd.DataFrame(latest_scan['data'])
            if not scan_df.empty:
                scan_df['Price'] = scan_df['current_price'].apply(lambda x: f"${x:.2f}")
                scan_df['Change %'] = scan_df['percent_change'].apply(lambda x: f"{x:+.2f}%")
                scan_df['IV Rank'] = scan_df['iv_rank'].apply(lambda x: f"{x:.0f}")
                
                display_cols = ['symbol', 'Price', 'Change %', 'IV Rank', 'volume']
                st.dataframe(scan_df[display_cols], use_container_width=True, hide_index=True)
                
                # Volatility alerts
                alerts = scan_df[abs(scan_df['percent_change']) >= 1.5]
                if not alerts.empty:
                    st.warning(f"🚨 **Volatility Alerts:** {len(alerts)} symbols with moves ≥1.5%")
                    for _, row in alerts.iterrows():
                        st.write(f"• {row['symbol']}: {row['percent_change']:+.2f}% (IV: {row['iv_rank']:.0f})")
        else:
            st.info("📊 No market scans yet. Bot will scan every 5 minutes during market hours.")
    
    with tab5:
        # Trade Entry Tab
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h2 style='color: #00c805;'>📝 Manual Trade Entry</h2>
            <p style='color: #888;'>Add trades manually to test the monitoring system</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            entry_symbol = st.selectbox("Symbol", ["SPY", "QQQ", "IWM", "DIA"], key="entry")
            entry_spread_type = st.selectbox("Spread Type", ["Call Credit", "Put Credit"])
            entry_contracts = st.number_input("Contracts", 1, 10, 2)
        
        with col2:
            entry_short_strike = st.number_input("Short Strike", value=450.0, step=1.0)
            entry_long_strike = st.number_input("Long Strike", value=455.0, step=1.0)
            entry_expiration = st.date_input("Expiration", value=datetime.now().date() + timedelta(days=14), key="entry_exp")
        
        with col3:
            entry_credit = st.number_input("Credit Received", value=125.0, step=5.0)
            entry_max_loss = st.number_input("Max Loss", value=375.0, step=25.0)
            entry_prob_profit = st.slider("Probability of Profit %", 50, 90, 75)
        
        if st.button("✅ Execute Trade", use_container_width=True):
            try:
                # Create option contracts
                short_leg = OptionContract(
                    symbol=f"{entry_symbol}_{datetime.now().strftime('%y%m%d')}C{int(entry_short_strike):08d}",
                    strike_price=entry_short_strike,
                    expiration_date=entry_expiration.strftime('%Y-%m-%d'),
                    option_type="call" if "Call" in entry_spread_type else "put",
                    bid_price=2.5, ask_price=2.6, volume=100, open_interest=500,
                    delta=0.3, gamma=0.1, theta=-0.05, vega=0.2, implied_volatility=0.25
                )
                
                long_leg = OptionContract(
                    symbol=f"{entry_symbol}_{datetime.now().strftime('%y%m%d')}C{int(entry_long_strike):08d}",
                    strike_price=entry_long_strike,
                    expiration_date=entry_expiration.strftime('%Y-%m-%d'),
                    option_type="call" if "Call" in entry_spread_type else "put",
                    bid_price=1.2, ask_price=1.3, volume=80, open_interest=300,
                    delta=0.2, gamma=0.08, theta=-0.03, vega=0.15, implied_volatility=0.22
                )
                
                trade_data = {
                    'symbol': entry_symbol,
                    'strategy_type': 'credit_spread',
                    'spread_type': entry_spread_type.lower().replace(' ', '_'),
                    'short_leg': short_leg,
                    'long_leg': long_leg,
                    'contracts': entry_contracts,
                    'entry_credit': entry_credit,
                    'max_loss': entry_max_loss,
                    'probability_profit': entry_prob_profit,
                    'confidence_score': 80,
                    'claude_reasoning': f"Manual {entry_spread_type} spread on {entry_symbol}"
                }
                
                trade = asyncio.run(tm.add_trade(trade_data))
                st.success(f"✅ Trade executed! ID: {trade.trade_id[:8]}")
                st.info(f"Targets set - Profit: ${trade.profit_target:.2f} | Stop: ${trade.stop_loss_target:.2f}")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)[:50]}...")
    
    with tab6:
        # Settings Tab
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h2 style='color: #00c805;'>⚙️ Bot Settings & Configuration</h2>
            <p style='color: #888;'>Configure your trading bot parameters</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Bot Configuration Section
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Bot Configuration")
            
            # Symbols to monitor
            new_symbols = st.multiselect(
                "Symbols to Monitor",
                ["SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"],
                default=st.session_state.bot_settings['symbols'],
                help="Select which symbols the bot should monitor for volatility"
            )
            
            # Minimum price move
            new_min_move = st.slider(
                "Minimum Price Move %",
                0.5, 5.0, 
                st.session_state.bot_settings['min_price_move'], 
                0.1,
                help="Minimum percentage move to trigger analysis"
            )
            
            # Minimum IV rank
            new_min_iv = st.slider(
                "Minimum IV Rank",
                50, 90,
                st.session_state.bot_settings['min_iv_rank'],
                5,
                help="Minimum implied volatility rank for trade entry"
            )
            
            # Scan interval
            new_scan_interval = st.slider(
                "Scan Interval (seconds)",
                60, 600,
                st.session_state.bot_settings['scan_interval'],
                30,
                help="How often to scan the market for opportunities"
            )
            
            # Confidence threshold
            new_confidence = st.slider(
                "AI Confidence Threshold %",
                50, 90,
                st.session_state.bot_settings['confidence_threshold'],
                5,
                help="Minimum Claude confidence score to execute trades"
            )
        
        with col2:
            st.subheader("💰 Risk Management")
            
            # Trade Management Rules
            tm = st.session_state.trade_manager
            rules = tm.rules
            
            # Profit target
            new_profit_target = st.slider(
                "Profit Target %",
                20, 80,
                int(rules.profit_target_percent * 100),
                5,
                help="Close trades at X% of maximum profit"
            ) / 100
            
            # Stop loss
            new_stop_loss = st.slider(
                "Stop Loss %",
                50, 100,
                int(rules.stop_loss_percent * 100),
                5,
                help="Close trades at X% of maximum loss"
            ) / 100
            
            # Time stop
            new_time_stop = st.slider(
                "Time Stop (DTE)",
                1, 10,
                rules.time_stop_dte,
                1,
                help="Close all trades at X days to expiration"
            )
            
            # Max contracts
            new_max_contracts = st.number_input(
                "Max Contracts per Trade",
                1, 20,
                st.session_state.bot_settings['max_contracts'],
                help="Maximum number of contracts per trade"
            )
            
            # Max daily loss
            new_daily_loss = st.number_input(
                "Max Daily Loss $",
                100, 5000,
                int(rules.max_daily_loss),
                50,
                help="Stop all trading if daily loss exceeds this"
            )
            
            # Account balance
            new_balance = st.number_input(
                "Account Balance $",
                10000, 1000000,
                st.session_state.bot_settings['account_balance'],
                1000,
                help="Total account balance for position sizing"
            )
        
        # Apply Settings Button
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 Save Settings", use_container_width=True):
            # Update bot settings
            st.session_state.bot_settings['symbols'] = new_symbols
            st.session_state.bot_settings['min_price_move'] = new_min_move
            st.session_state.bot_settings['min_iv_rank'] = new_min_iv
            st.session_state.bot_settings['scan_interval'] = new_scan_interval
            st.session_state.bot_settings['confidence_threshold'] = new_confidence
            st.session_state.bot_settings['max_contracts'] = new_max_contracts
            st.session_state.bot_settings['account_balance'] = new_balance
            
            # Update trade manager rules
            rules.profit_target_percent = new_profit_target
            rules.stop_loss_percent = new_stop_loss
            rules.time_stop_dte = new_time_stop
            rules.max_daily_loss = float(new_daily_loss)
            
            # Update the bot if it's running
            if st.session_state.full_bot:
                bot = st.session_state.full_bot
                bot.symbols = new_symbols
                bot.min_price_move = new_min_move
                bot.min_iv_rank = new_min_iv
                bot.scan_interval = new_scan_interval
                bot.trade_manager.rules = rules
                
                # Update account balance
                bot.trade_manager.account_balance = new_balance
            
            st.success("✅ Settings saved successfully!")
            
            # Show current settings summary
            st.info(f"""
            **Current Configuration:**
            - Monitoring: {', '.join(new_symbols)}
            - Price Move: {new_min_move}% | IV Rank: {new_min_iv}
            - Scan Every: {new_scan_interval}s | AI Confidence: {new_confidence}%
            - Profit/Stop: {int(new_profit_target*100)}%/{int(new_stop_loss*100)}%
            - Time Stop: {new_time_stop} DTE | Max Daily Loss: ${new_daily_loss}
            """)
        
        # Current Rules Display
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📄 Current Exit Rules")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success(f"""
            **💰 Profit Target**
            {rules.profit_target_percent:.0%} of max profit
            
            Example: $125 credit  
            → Close at ${125 * rules.profit_target_percent:.2f}
            """)
        
        with col2:
            st.warning(f"""
            **🛑 Stop Loss**
            {rules.stop_loss_percent:.0%} of max loss
            
            Example: $375 max loss  
            → Stop at ${375 * rules.stop_loss_percent:.2f} loss
            """)
        
        with col3:
            st.error(f"""
            **⏰ Time Stop**
            Close at {rules.time_stop_dte} DTE
            
            Prevents assignment risk  
            regardless of P&L
            """)
        
        # API Status Section
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🔌 API Status")
        
        api_cols = st.columns(3)
        
        with api_cols[0]:
            alpaca_status = "🟢 Connected" if os.getenv('ALPACA_API_KEY') else "🔴 Not Set"
            st.metric("Alpaca API", alpaca_status)
        
        with api_cols[1]:
            claude_status = "🟢 Connected" if os.getenv('ANTHROPIC_API_KEY') else "🔴 Not Set"
            st.metric("Claude API", claude_status)
        
        with api_cols[2]:
            if st.button("🔄 Test Connections"):
                with st.spinner("Testing API connections..."):
                    try:
                        # Test Alpaca
                        account = tm.trading_client.get_account()
                        st.success(f"✅ Alpaca: Connected (Balance: ${float(account.cash):.2f})")
                    except Exception as e:
                        st.error(f"❌ Alpaca: {str(e)[:50]}...")
                    
                    try:
                        # Test Claude
                        test_response = asyncio.run(tm.anthropic.messages.create(
                            model="claude-3-sonnet-20240229",
                            max_tokens=10,
                            messages=[{"role": "user", "content": "Say 'OK'"}]
                        ))
                        st.success("✅ Claude: Connected")
                    except Exception as e:
                        st.error(f"❌ Claude: {str(e)[:50]}...")
    
    # Footer
    st.markdown("---")
    st.caption("""
    🤖 **Automated Features**: Real-time P&L tracking, profit targets, stop losses, time stops, Claude AI analysis
    📊 **Options Data**: Live quotes and greeks from Alpaca Algo Trader Plus subscription
    🔧 **Fully Customizable**: Adjust all rules in the Settings tab
    """)
    
    # Auto-refresh for real-time updates
    if st.session_state.monitoring_active or st.session_state.bot_active:
        time.sleep(5)  # Refresh every 5 seconds when active
        st.rerun()

if __name__ == "__main__":
    main()