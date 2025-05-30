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
    page_title="Complete Volatility Trading Bot",
    page_icon="🚀",
    layout="wide"
)

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
        self.symbols = ['SPY', 'QQQ', 'IWM', 'DIA']
        self.min_price_move = 1.5  # 1.5% minimum move
        self.min_iv_rank = 70  # Minimum IV rank
        self.scan_interval = 300  # 5 minutes
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
                    if analysis and analysis.get('should_trade') and analysis.get('confidence', 0) >= 70:
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
    st.title("🚀 Complete Volatility Trading Bot Dashboard")
    st.markdown("**Real-time Options Trading with AI Analysis & Automated Management**")
    st.markdown("---")
    
    # Sidebar Controls
    st.sidebar.title("🎛️ Trade Management Controls")
    
    # Trade Management Rules
    st.sidebar.subheader("📋 Management Rules")
    
    tm = st.session_state.trade_manager
    rules = tm.rules
    
    # Customizable rules
    new_profit_target = st.sidebar.slider(
        "Profit Target %", 0.2, 0.8, rules.profit_target_percent, 0.05,
        help="Close trades at X% of maximum profit"
    )
    
    new_stop_loss = st.sidebar.slider(
        "Stop Loss %", 0.5, 1.0, rules.stop_loss_percent, 0.05,
        help="Close trades at X% of maximum loss"
    )
    
    new_time_stop = st.sidebar.slider(
        "Time Stop (DTE)", 1, 10, rules.time_stop_dte, 1,
        help="Close all trades at X days to expiration"
    )
    
    new_interval = st.sidebar.slider(
        "Check Interval (seconds)", 30, 300, rules.monitoring_interval, 30,
        help="How often to check trade conditions"
    )
    
    new_daily_loss = st.sidebar.slider(
        "Max Daily Loss $", 100, 1000, int(rules.max_daily_loss), 50,
        help="Stop all trading if daily loss exceeds this"
    )
    
    # Update rules if changed
    rules.profit_target_percent = new_profit_target
    rules.stop_loss_percent = new_stop_loss
    rules.time_stop_dte = new_time_stop
    rules.monitoring_interval = new_interval
    rules.max_daily_loss = float(new_daily_loss)
    
    # Monitoring Controls
    st.sidebar.subheader("🔍 Monitoring")
    
    if st.sidebar.button("▶️ Start Monitoring", disabled=st.session_state.monitoring_active):
        if start_monitoring():
            st.sidebar.success("✅ Monitoring started in background!")
            st.rerun()
    
    if st.sidebar.button("⏹️ Stop Monitoring", disabled=not st.session_state.monitoring_active):
        stop_monitoring()
        st.sidebar.success("⏹️ Monitoring stopped!")
        st.rerun()
    
    if st.sidebar.button("🔄 Manual Check"):
        with st.spinner("Checking all trades..."):
            try:
                asyncio.run(tm.monitor_all_trades())
                st.sidebar.success("✅ Manual check complete!")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
    
    # Main Dashboard - Bot Controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Start Full Bot", disabled=st.session_state.bot_active):
            if start_full_bot():
                st.success("✅ Full automated bot started!")
                st.rerun()
    
    with col2:
        if st.button("🛑 Stop Bot", disabled=not st.session_state.bot_active):
            stop_full_bot()
            st.success("⏹️ Bot stopped!")
            st.rerun()
    
    with col3:
        status = "🟢 RUNNING" if st.session_state.bot_active else "🔴 STOPPED"
        st.metric("Bot Status", status)
    
    # Dashboard Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    summary = tm.get_trade_summary()
    
    with col1:
        st.metric("Active Trades", summary["open_trades"])
    with col2:
        st.metric("Total Credit", f"${summary['total_credit']:.2f}")
    with col3:
        st.metric("Unrealized P&L", f"${summary['unrealized_pnl']:.2f}")
    with col4:
        monitoring_status = "🟢 Active" if st.session_state.monitoring_active else "🔴 Stopped"
        st.metric("Monitoring", monitoring_status)
    
    # Monitoring Status
    if st.session_state.monitoring_active:
        last_check = getattr(st.session_state, 'last_monitoring_check', None)
        if last_check:
            st.success(f"🔍 Monitoring active - Last check: {last_check.strftime('%H:%M:%S')}")
        else:
            st.info("🔍 Monitoring started - Waiting for first check...")
    
    # Real-time Options Data Section
    st.subheader("📊 Real-Time Options Data Testing")
    
    col1, col2 = st.columns(2)
    
    with col1:
        test_symbol = st.selectbox("Test Options Data", ["SPY", "QQQ", "IWM", "DIA"])
        test_expiration = st.date_input("Expiration", value=datetime.now().date() + timedelta(days=14))
    
    with col2:
        if st.button("🔍 Get Options Chain"):
            with st.spinner(f"Fetching options data for {test_symbol}..."):
                try:
                    options_data = asyncio.run(tm.get_real_time_options_data(
                        test_symbol, 
                        test_expiration.strftime('%Y-%m-%d')
                    ))
                    
                    if options_data:
                        df = pd.DataFrame([{
                            'Strike': opt.strike_price,
                            'Type': opt.option_type.upper(),
                            'Bid': f"${opt.bid_price:.2f}",
                            'Ask': f"${opt.ask_price:.2f}",
                            'Volume': opt.volume,
                            'Delta': f"{opt.delta:.3f}",
                            'Theta': f"{opt.theta:.3f}",
                            'IV': f"{opt.implied_volatility:.1%}"
                        } for opt in options_data[:20]])  # Show first 20
                        
                        st.dataframe(df, use_container_width=True)
                        st.success(f"✅ Loaded {len(options_data)} option contracts with REAL DATA")
                    else:
                        st.warning("⚠️ Using simulated data - check Algo Trader Plus subscription")
                        
                except Exception as e:
                    st.error(f"❌ Error fetching options data: {e}")
    
    # Trade Entry Simulation
    st.subheader("📝 Add New Trade (Manual Entry)")
    st.info("💡 Add trades to test the automated monitoring system")
    
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
    
    if st.button("➕ Add Trade to Monitoring"):
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
            st.success(f"✅ Added trade {trade.trade_id} to monitoring!")
            st.info(f"📊 Profit target: ${trade.profit_target:.2f} | Stop loss: ${trade.stop_loss_target:.2f}")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error adding trade: {e}")
    
    # Analysis Tabs
    st.subheader("🤖 Bot Intelligence & Analysis")
    
    tab1, tab2, tab3 = st.tabs(["🧠 Claude Analysis", "📊 Market Scans", "📋 Activity Logs"])
    
    with tab1:
        st.markdown("**Real-time AI Analysis from Claude 4**")
        
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
                            st.metric("Action", claude.get('recommended_action', 'N/A'))
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
    
    with tab2:
        st.markdown("**Market Scanning Results**")
        
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
    
    with tab3:
        st.markdown("**Real-time Bot Activity**")
        
        if st.session_state.bot_logs:
            # Show logs in reverse order (newest first)
            log_text = "\\n".join(reversed(st.session_state.bot_logs[-20:]))  # Last 20 logs
            st.text_area("Bot Logs", value=log_text, height=300)
        else:
            st.info("No bot activity yet. Start the bot to see live logs.")
    
    # Active Trades Table
    st.subheader("📊 Active Trades with Real-Time Monitoring")
    
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
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("📭 No active trades. Add a trade above or start the bot to begin automated trading.")
    
    # Exit Conditions Reference
    st.subheader("🎯 Current Exit Rules")
    
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
    
    # Footer with auto-refresh
    st.markdown("---")
    
    # Market Status
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    is_market_open = market_open <= now <= market_close and now.weekday() < 5
    
    col1, col2, col3 = st.columns(3)
    with col1:
        market_status = "🟢 OPEN" if is_market_open else "🔴 CLOSED"
        st.metric("Market", market_status)
    with col2:
        st.metric("Current Time", now.strftime('%H:%M:%S'))
    with col3:
        if st.session_state.full_bot and st.session_state.full_bot.last_scan_time:
            last_scan = st.session_state.full_bot.last_scan_time.strftime('%H:%M:%S')
        else:
            last_scan = "Not yet"
        st.metric("Last Scan", last_scan)
    
    # Auto-refresh for real-time updates
    if st.session_state.monitoring_active or st.session_state.bot_active:
        time.sleep(5)  # Refresh every 5 seconds when active
        st.rerun()
    
    st.caption("""
    🤖 **Automated Features**: Real-time P&L tracking, profit targets, stop losses, time stops, Claude AI analysis
    📊 **Options Data**: Live quotes and greeks from Alpaca Algo Trader Plus subscription
    🔧 **Fully Customizable**: Adjust all rules in the sidebar
    """)

if __name__ == "__main__":
    main()