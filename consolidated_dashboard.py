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

class FullAutomatedBot:
    def __init__(self, bot_settings=None):
        self.trade_manager = EnhancedTradeManager()
        self.is_running = False
        # Use passed settings or defaults if session state is not available
        settings = bot_settings or {
            'symbols': ['SPY', 'QQQ', 'IWM', 'DIA'],
            'min_price_move': 1.5,
            'min_iv_rank': 70,
            'scan_interval': 300,
            'confidence_threshold': 70
        }
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
        try:
            if hasattr(st.session_state, 'bot_logs'):
                st.session_state.bot_logs.append(log_entry)
                if len(st.session_state.bot_logs) > 50:
                    st.session_state.bot_logs = st.session_state.bot_logs[-50:]
        except:
            pass
        print(log_entry)
    
    def add_market_scan(self, scan_data):
        """Add market scan data for analysis view"""
        scan_entry = {
            'timestamp': datetime.now(),
            'data': scan_data
        }
        try:
            if hasattr(st.session_state, 'market_scans'):
                st.session_state.market_scans.append(scan_entry)
                if len(st.session_state.market_scans) > 20:
                    st.session_state.market_scans = st.session_state.market_scans[-20:]
        except:
            pass
    
    def add_analysis(self, symbol, market_data, analysis, decision):
        """Add Claude analysis for display"""
        analysis_entry = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'market_data': market_data,
            'claude_analysis': analysis,
            'bot_decision': decision
        }
        try:
            if hasattr(st.session_state, 'bot_analysis'):
                st.session_state.bot_analysis.append(analysis_entry)
                if len(st.session_state.bot_analysis) > 10:
                    st.session_state.bot_analysis = st.session_state.bot_analysis[-10:]
        except:
            pass
    
    async def get_market_data(self, symbol):
        """Get current market data and calculate IV metrics"""
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
            
            # Calculate IV rank using real options data from Algo Trader Plus subscription
            try:
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
                model="claude-3-sonnet-20240229",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
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
            
            spread_width = abs(analysis['long_strike'] - analysis['short_strike'])
            max_loss = (spread_width * 100 - analysis['expected_credit']) * analysis['contracts']
            
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
                'probability_profit': 75,
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
                market_data = await self.get_market_data(symbol)
                if not market_data:
                    continue
                
                scan_results.append(market_data)
                self.log(f"📊 {symbol}: ${market_data['current_price']:.2f} ({market_data['percent_change']:+.2f}%) IV:{market_data['iv_rank']:.0f}")
                
                if (abs(market_data['percent_change']) >= self.min_price_move and 
                    market_data['iv_rank'] >= self.min_iv_rank):
                    
                    self.log(f"🚨 VOLATILITY SPIKE: {symbol} moved {market_data['percent_change']:.2f}% with IV rank {market_data['iv_rank']:.0f}")
                    
                    analysis = await self.analyze_with_claude(market_data)
                    
                    if analysis and analysis.get('should_trade') and analysis.get('confidence', 0) >= self.confidence_threshold:
                        decision = f"EXECUTE TRADE - Confidence: {analysis.get('confidence')}%"
                        
                        trade = await self.execute_trade_from_analysis(symbol, analysis, market_data)
                        if trade:
                            decision += f" - Trade ID: {trade.trade_id}"
                            if not self.trade_manager.is_monitoring:
                                await self.trade_manager.start_monitoring()
                    elif analysis:
                        decision = f"NO TRADE - Confidence: {analysis.get('confidence', 0)}% (below {self.confidence_threshold}% threshold)"
                    else:
                        decision = "NO TRADE - Analysis failed"
                    
                    self.add_analysis(symbol, market_data, analysis, decision)
                    
                    if analysis:
                        self.log(f"🤖 Claude Decision: {decision}")
                
            except Exception as e:
                self.log(f"Error scanning {symbol}: {e}")
        
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
                now = datetime.now()
                market_open = now.replace(hour=9, minute=30, second=0)
                market_close = now.replace(hour=16, minute=0, second=0)
                
                if market_open <= now <= market_close and now.weekday() < 5:
                    await self.scan_and_trade()
                    await self.trade_manager.monitor_all_trades()
                else:
                    self.log("💤 Market closed - bot sleeping...")
                
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
    try:
        # Get settings safely from session state
        bot_settings = getattr(st.session_state, 'bot_settings', {
            'symbols': ['SPY', 'QQQ', 'IWM', 'DIA'],
            'min_price_move': 1.5,
            'min_iv_rank': 70,
            'scan_interval': 300,
            'confidence_threshold': 70
        })
        bot = FullAutomatedBot(bot_settings)
        st.session_state.full_bot = bot
        asyncio.run(bot.run_bot())
    except Exception as e:
        print(f"Bot worker error: {e}")

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
    st.title("Volatility Trading Bot")
    
    # Market status and time
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    is_market_open = market_open <= now <= market_close and now.weekday() < 5
    
    # Status bar
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        market_status = "🟢 Market Open" if is_market_open else "🔴 Market Closed"
        st.info(f"{market_status} | {now.strftime('%I:%M %p ET')}")
    
    with col2:
        if st.session_state.bot_active:
            st.success("Bot Active")
        else:
            st.warning("Bot Inactive")
    
    summary = st.session_state.trade_manager.get_trade_summary()
    
    with col3:
        st.metric("Open Trades", summary['open_trades'])
    
    with col4:
        st.metric("Unrealized P&L", f"${summary['unrealized_pnl']:.2f}", 
                  delta=f"{summary['unrealized_pnl']:.2f}" if summary['unrealized_pnl'] != 0 else None,
                  delta_color="normal" if summary['unrealized_pnl'] >= 0 else "inverse")
    
    # Control buttons
    st.subheader("Trading Controls")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Start Bot", disabled=st.session_state.bot_active, use_container_width=True):
            if start_full_bot():
                st.success("Bot started!")
                st.rerun()
    
    with col2:
        if st.button("Stop Bot", disabled=not st.session_state.bot_active, use_container_width=True):
            stop_full_bot()
            st.success("Bot stopped!")
            st.rerun()
    
    with col3:
        if st.button("Start Monitor", disabled=st.session_state.monitoring_active, use_container_width=True):
            if start_monitoring():
                st.success("Monitoring started!")
                st.rerun()
    
    with col4:
        if st.button("Refresh", use_container_width=True):
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Trades", "Settings"])
    
    with tab1:
        # Key metrics
        st.subheader("Portfolio Overview")
        metrics_cols = st.columns(4)
        
        tm = st.session_state.trade_manager
        win_rate = 0
        closed_trades = getattr(tm, 'closed_trades', [])
        if closed_trades:
            wins = sum(1 for t in closed_trades if t.realized_pnl > 0)
            win_rate = (wins / len(closed_trades)) * 100
        
        with metrics_cols[0]:
            st.metric("Win Rate", f"{win_rate:.1f}%")
        
        with metrics_cols[1]:
            daily_pnl = sum(t.unrealized_pnl for t in tm.active_trades if t.entry_time.date() == datetime.now().date())
            st.metric("Today's P&L", f"${daily_pnl:.2f}")
        
        with metrics_cols[2]:
            avg_credit = summary['total_credit'] / summary['open_trades'] if summary['open_trades'] > 0 else 0
            st.metric("Avg Credit", f"${avg_credit:.2f}")
        
        with metrics_cols[3]:
            total_volume = summary['open_trades'] + len(closed_trades)
            st.metric("Total Trades", total_volume)
        
        # Latest AI Analysis
        if st.session_state.bot_analysis:
            st.subheader("Latest AI Analysis")
            latest = st.session_state.bot_analysis[-1]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Symbol:** {latest['symbol']}")
                st.write(f"**Price:** ${latest['market_data']['current_price']:.2f}")
                st.write(f"**Change:** {latest['market_data']['percent_change']:+.2f}%")
                st.write(f"**IV Rank:** {latest['market_data']['iv_rank']:.1f}")
            
            with col2:
                st.write(f"**Decision:** {latest['bot_decision']}")
                if latest['claude_analysis']:
                    st.write(f"**Confidence:** {latest['claude_analysis'].get('confidence', 0)}%")
                    st.write(f"**Reasoning:** {latest['claude_analysis'].get('reasoning', 'N/A')}")
        
        # Activity Log
        if st.session_state.bot_logs:
            with st.expander("Activity Log", expanded=True):
                log_text = "\\n".join(reversed(st.session_state.bot_logs[-10:]))
                st.text_area("Recent Activity", value=log_text, height=200, label_visibility="collapsed")
    
    with tab2:
        # Active Trades
        st.subheader("Active Positions")
        
        if tm.active_trades:
            trades_data = []
            for trade in tm.active_trades:
                exp_date = datetime.strptime(trade.short_leg.expiration_date, '%Y-%m-%d')
                dte = (exp_date.date() - datetime.now().date()).days
                
                trades_data.append({
                    'Symbol': trade.symbol,
                    'Type': trade.spread_type.replace('_', ' ').title(),
                    'Strikes': f"${trade.short_leg.strike_price:.0f}/${trade.long_leg.strike_price:.0f}",
                    'Qty': trade.contracts,
                    'Credit': f"${trade.entry_credit:.2f}",
                    'P&L': f"${trade.unrealized_pnl:.2f}",
                    'DTE': dte,
                    'Status': trade.status
                })
            
            df = pd.DataFrame(trades_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                total_credit = sum(t.entry_credit for t in tm.active_trades)
                st.metric("Total Credit", f"${total_credit:.2f}")
            with col2:
                total_pnl = sum(t.unrealized_pnl for t in tm.active_trades)
                st.metric("Total P&L", f"${total_pnl:.2f}")
            with col3:
                avg_dte = sum((datetime.strptime(t.short_leg.expiration_date, '%Y-%m-%d').date() - datetime.now().date()).days for t in tm.active_trades) / len(tm.active_trades)
                st.metric("Avg DTE", f"{avg_dte:.1f} days")
        else:
            st.info("No active trades")
    
    with tab3:
        # Settings
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
            
            st.success("Settings saved!")
    
    # Auto-refresh
    if st.session_state.monitoring_active or st.session_state.bot_active:
        time.sleep(5)
        st.rerun()

# Always run main function when dashboard is loaded
if __name__ == "__main__":
    main()
else:
    # Also run when imported by streamlit
    main()