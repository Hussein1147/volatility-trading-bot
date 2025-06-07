"""
Simple Backtesting Dashboard using Streamlit's native async support
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
import sys
import time
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.backtest.backtest_engine import BacktestConfig, BacktestEngine, ActivityLogEntry
from src.backtest.visualizer import BacktestVisualizer
from src.backtest.advanced_visualizer import AdvancedBacktestVisualizer
from src.data.backtest_db import backtest_db

st.set_page_config(
    page_title="Volatility Trading Backtest",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* Activity log styling */
    .activity-log {
        background-color: #1E1E1E;
        border: 1px solid #3A3F51;
        border-radius: 8px;
        padding: 10px;
        max-height: 400px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 12px;
    }
    
    .log-info { color: #4CAF50; }
    .log-trade { color: #2196F3; }
    .log-warning { color: #FF9800; }
    .log-error { color: #F44336; }
    .log-analysis { color: #9C27B0; }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = []
if 'current_progress' not in st.session_state:
    st.session_state.current_progress = {"current": 0, "total": 0, "message": ""}

def format_activity_entry(entry: ActivityLogEntry) -> str:
    """Format activity log entry for display"""
    time_str = entry.timestamp.strftime("%H:%M:%S")
    icon = {
        "info": "ℹ️",
        "trade": "💰",
        "warning": "⚠️",
        "error": "❌",
        "analysis": "🔍"
    }.get(entry.type, "📝")
    
    return f"{time_str} {icon} {entry.message}"

async def run_backtest_async(config: BacktestConfig, progress_container, log_container):
    """Run backtest with live updates"""
    
    # Clear previous results
    st.session_state.activity_log = []
    st.session_state.current_progress = {"current": 0, "total": 0, "message": "Initializing..."}
    
    # Callbacks for live updates
    def activity_callback(entry: ActivityLogEntry):
        st.session_state.activity_log.append(entry)
        
        # Update log display
        with log_container:
            # Clear and redraw
            log_container.empty()
            if st.session_state.activity_log:
                log_html = '<div class="activity-log">'
                for log_entry in reversed(st.session_state.activity_log[-20:]):  # Show last 20
                    css_class = f"log-{log_entry.type}"
                    formatted = format_activity_entry(log_entry)
                    log_html += f'<div class="{css_class}">{formatted}</div>'
                log_html += '</div>'
                st.markdown(log_html, unsafe_allow_html=True)
    
    def progress_callback(progress):
        # Handle both old-style (3 args) and new-style (BacktestProgress object) callbacks
        if hasattr(progress, 'current_day'):
            # New style - BacktestProgress object
            st.session_state.current_progress = {
                "current": progress.current_day,
                "total": progress.total_days,
                "message": progress.message or progress.get_status_message()
            }
            
            if progress.total_days > 0:
                progress_value = progress.progress_percent
                progress_text = progress.message or progress.get_status_message()
                progress_container.progress(progress_value, text=progress_text)
            else:
                progress_container.progress(0.0, text="Initializing...")
        else:
            # Old style - 3 arguments (for backward compatibility)
            # This shouldn't happen with new BacktestEngine
            progress_container.progress(0.5, text="Processing...")
    
    # Get pricing parameters from session state
    synthetic_pricing = st.session_state.get('synthetic_pricing', True)
    delta_target = st.session_state.get('delta_target', 0.16)
    tier_targets = st.session_state.get('tier_targets', [0.50, 0.75, -1.50])
    contracts_by_tier = st.session_state.get('contracts_by_tier', [0.4, 0.4, 0.2])
    force_exit_days = st.session_state.get('force_exit_days', 21)
    
    # Create engine with AI-powered decisions (Claude Sonnet 4)
    engine = BacktestEngine(
        config,
        progress_callback=progress_callback,
        activity_callback=activity_callback,
        synthetic_pricing=synthetic_pricing,
        delta_target=delta_target,
        tier_targets=tier_targets,
        contracts_by_tier=contracts_by_tier,
        force_exit_days=force_exit_days
    )
    
    # Run backtest
    results = await engine.run_backtest()
    
    # Store results
    st.session_state.backtest_results = results
    
    # Save to database if we have results
    if results and results.total_trades > 0:
        from src.data.backtest_db import backtest_db
        run_id = backtest_db.save_backtest_run(config, results, notes="AI-powered backtest")
        st.session_state.last_run_id = run_id
        
        # Save all analyses from the engine
        if hasattr(engine, 'all_analyses'):
            for analysis in engine.all_analyses:
                backtest_db.save_analysis(
                    run_id=run_id,
                    timestamp=analysis['timestamp'],
                    symbol=analysis['symbol'],
                    market_data={
                        'current_price': analysis['current_price'],
                        'percent_change': analysis['percent_change'],
                        'volume': analysis['volume'],
                        'iv_rank': analysis['iv_rank']
                    },
                    analysis={
                        'should_trade': analysis['should_trade'],
                        'spread_type': analysis.get('spread_type'),
                        'short_strike': analysis.get('short_strike'),
                        'long_strike': analysis.get('long_strike'),
                        'contracts': analysis.get('contracts'),
                        'expected_credit': analysis.get('expected_credit'),
                        'confidence': analysis['confidence'],
                        'reasoning': analysis['reasoning']
                    }
                )
        
        # Store run_id in results for later reference
        results.run_id = run_id
    
    return results

def main():
    st.title("📊 Volatility Trading Backtest")
    st.markdown("Simple dashboard with real-time activity logging")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Backtest Configuration")
        
        # Tips
        with st.expander("💡 Quick Start", expanded=True):
            st.markdown("""
            **For a quick test:**
            - Date Range: Nov 1-8, 2024
            - Symbols: SPY only
            - Min Price Move: 0.3%
            - Min IV Rank: 30
            
            **Watch the activity log** for real-time Claude AI analysis!
            """)
        
        # Date range
        st.subheader("📅 Date Range")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime(2024, 8, 1).date(),
                max_value=datetime.now().date()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime(2024, 8, 31).date(),
                max_value=datetime.now().date()
            )
            
        # Validate dates
        if start_date >= end_date:
            st.error("❌ End date must be after start date!")
            st.stop()
            
        # Symbol selection
        st.subheader("🎯 Symbols")
        available_symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLE', 'XLK']
        symbols = st.multiselect(
            "Select symbols to backtest",
            available_symbols,
            default=['SPY']
        )
        
        # Capital and risk
        st.subheader("💰 Capital & Risk")
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000
        )
        
        max_risk_per_trade = st.slider(
            "Max Risk per Trade (%)",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5
        )
        
        # Short-dated options configuration
        st.subheader("📊 Options Configuration")
        dte_target = st.slider(
            "Target DTE (days)",
            min_value=7,
            max_value=21,
            value=9,
            help="Target days to expiration for new trades. Nearest Friday >= target will be selected."
        )
        
        # Force exit adjustment based on DTE
        if dte_target <= 10:
            force_exit_default = 7
        else:
            force_exit_default = 21
        
        force_exit_days = st.number_input(
            "Force Exit (DTE)",
            min_value=1,
            max_value=21,
            value=force_exit_default,
            help=f"Exit positions with {force_exit_default} days remaining (adjusted for short-dated options)"
        )
        
        # IV-aware sizing info
        st.info(
            "💡 **IV-Aware Sizing**: Position size increases with IV rank\n"
            "- IV 50 → 1.0× base size\n"
            "- IV 90 → 1.8× base size\n"
            "- Hard cap at 8% of equity"
        )
        
        st.subheader("📊 Strategy Parameters")
        min_iv_rank = st.slider(
            "Min IV Rank",
            min_value=30,
            max_value=90,
            value=40,
            step=5
        )
        
        min_price_move = st.slider(
            "Min Price Move (%)",
            min_value=0.5,
            max_value=5.0,
            value=1.5,
            step=0.1
        )
        
        confidence_threshold = st.slider(
            "Min Confidence (%)",
            min_value=50,
            max_value=90,
            value=70,
            step=5
        )
        
        st.subheader("💰 Pricing Options")
        synthetic_pricing = st.checkbox(
            "Use Synthetic Pricing",
            value=True,
            help="Use Black-Scholes model for option pricing instead of real market data"
        )
        
        if synthetic_pricing:
            st.info("🔬 Prices will be derived from proxy Black-Scholes calculations")
            
            delta_target = st.slider(
                "Target Delta",
                min_value=0.10,
                max_value=0.30,
                value=0.16,
                step=0.01,
                help="Delta target for strike selection (0.16 = 16% ITM probability)"
            )
        else:
            delta_target = 0.16
            
        # Advanced exit rules (expandable)
        with st.expander("🎯 Enhanced Exit Rules (Return-Boost v1)"):
            st.markdown("**New tiered exit targets for improved returns:**")
            st.write("- **Tier 1 (40% contracts)**: Exit at +50% of credit received")
            st.write("- **Tier 2 (40% contracts)**: Exit at +75% of credit received")
            st.write("- **Stop Loss**: -250% of credit (allows more room)")
            st.write("- **Final 20% contracts**: Ride to +150% potential profit")
            st.info("💡 The enhanced -250% stop allows the final portion to capture larger moves")
            
            col1, col2 = st.columns(2)
            with col1:
                tier1_target = st.number_input(
                    "Tier 1 Target (%)",
                    min_value=20,
                    max_value=100,
                    value=50,
                    step=5,
                    help="First profit target as % of max profit"
                )
                tier2_target = st.number_input(
                    "Tier 2 Target (%)",
                    min_value=tier1_target,
                    max_value=100,
                    value=75,
                    step=5,
                    help="Second profit target as % of max profit"
                )
                stop_loss = st.number_input(
                    "Stop Loss (%)",
                    min_value=-300,
                    max_value=-50,
                    value=-250,
                    step=10,
                    help="Stop loss as % of credit received (negative)"
                )
                
            with col2:
                tier1_contracts = st.slider(
                    "Tier 1 Contracts (%)",
                    min_value=10,
                    max_value=70,
                    value=40,
                    step=10,
                    help="% of contracts to close at Tier 1"
                )
                tier2_contracts = st.slider(
                    "Tier 2 Contracts (%)",
                    min_value=10,
                    max_value=70,
                    value=40,
                    step=10,
                    help="% of contracts to close at Tier 2"
                )
        
        # Run button
        run_clicked = st.button("🚀 Run Backtest", type="primary", use_container_width=True)
    
    # Main area with tabs
    tab1, tab2 = st.tabs(["🚀 Run Backtest", "📚 Saved Results"])
    
    with tab1:
        if run_clicked:
            if not symbols:
                st.error("Please select at least one symbol")
            else:
                # Create config
                config = BacktestConfig(
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    symbols=symbols,
                    initial_capital=initial_capital,
                    max_risk_per_trade=max_risk_per_trade/100,
                    min_iv_rank=min_iv_rank,
                    min_price_move=min_price_move,
                    confidence_threshold=confidence_threshold,
                    commission_per_contract=0.65,
                    use_real_data=True,
                    dte_target=dte_target,
                    force_exit_days=force_exit_days
                )
                
                st.header("🔄 Running Backtest")
                
                # Progress section
                col1, col2 = st.columns([3, 1])
                with col1:
                    progress_container = st.empty()
                with col2:
                    stats_container = st.empty()
                
                # Activity log section
                st.subheader("📋 Activity Log")
                log_container = st.empty()
                
                # Store pricing parameters in session state
                st.session_state['synthetic_pricing'] = synthetic_pricing
                st.session_state['delta_target'] = delta_target if synthetic_pricing else 0.16
                
                # Store exit rule parameters if expanded
                if 'tier1_target' in locals():
                    st.session_state['tier_targets'] = [
                        tier1_target / 100,
                        tier2_target / 100,
                        stop_loss / 100
                    ]
                    st.session_state['contracts_by_tier'] = [
                        tier1_contracts / 100,
                        tier2_contracts / 100,
                        1 - (tier1_contracts + tier2_contracts) / 100
                    ]
                    st.session_state['force_exit_days'] = force_exit_days
                else:
                    # Use defaults from Return-Boost v1
                    st.session_state['tier_targets'] = [0.50, 0.75, -2.50]
                    st.session_state['contracts_by_tier'] = [0.4, 0.4, 0.2]
                    st.session_state['force_exit_days'] = force_exit_days
                    
                # Run backtest
                asyncio.run(run_backtest_async(config, progress_container, log_container))
                
                # Show completion
                st.success("✅ Backtest completed!")
        
        # Display results if available
        if st.session_state.backtest_results:
            results = st.session_state.backtest_results
            visualizer = BacktestVisualizer(results)
            
            # Performance summary
            st.header("📊 Performance Summary")
            
            # Show pricing method indicator
            if hasattr(results, 'trades') and results.trades:
                # Check if any trades used synthetic pricing
                synthetic_used = st.session_state.get('synthetic_pricing', False)
                if synthetic_used:
                    st.info("🔬 Results calculated using **synthetic Black-Scholes pricing**")
                else:
                    st.success("📈 Results calculated using **real market data**")
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            summary = visualizer.create_performance_summary()
            
            with col1:
                st.metric(
                    "Total Return",
                    f"{summary['total_return']:.2f}%",
                    delta=f"${summary['total_pnl']:.2f}"
                )
            
            with col2:
                st.metric(
                    "Sharpe Ratio",
                    f"{summary['sharpe_ratio']:.2f}",
                    delta="Annualized"
                )
            
            with col3:
                st.metric(
                    "Max Drawdown",
                f"{summary['max_drawdown']:.2f}%",
                delta=None,
                delta_color="inverse"
            )
            
            with col4:
                st.metric(
                    "Win Rate",
                    f"{summary['win_rate']:.1f}%",
                    delta=f"{summary['total_trades']} trades"
                )
            
            with col5:
                st.metric(
                    "Avg Win",
                    f"${summary['avg_win']:.2f}",
                    delta=None
                )
            
            with col6:
                st.metric(
                    "Avg Loss",
                    f"${summary['avg_loss']:.2f}",
                    delta=None,
                    delta_color="inverse"
                )
            
            # Visualizations
            st.header("📈 Performance Charts")
            
            # Equity curve
            fig_equity = visualizer.plot_equity_curve()
            st.plotly_chart(fig_equity, use_container_width=True, key="equity_curve")
            
            # Monthly returns and distribution
            col1, col2 = st.columns(2)
            
            with col1:
                fig_monthly = visualizer.plot_monthly_returns()
                st.plotly_chart(fig_monthly, use_container_width=True, key="monthly_returns")
            
            with col2:
                fig_dist = visualizer.plot_returns_distribution()
                st.plotly_chart(fig_dist, use_container_width=True, key="returns_dist")
            
            # Win/Loss Analysis and Trade Timeline
            st.header("📊 Trade Performance Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_winloss = visualizer.plot_win_loss_analysis()
                st.plotly_chart(fig_winloss, use_container_width=True, key="win_loss_analysis")
            
            with col2:
                fig_timeline = visualizer.plot_trade_timeline()
                st.plotly_chart(fig_timeline, use_container_width=True, key="trade_timeline")
            
            # Advanced Analysis
            advanced_viz = AdvancedBacktestVisualizer(results)
            
            # Greeks and Strategy Analysis
            st.header("🎯 Options Greeks & Strategy Analysis")
            fig_greeks = advanced_viz.plot_greeks_analysis()
            st.plotly_chart(fig_greeks, use_container_width=True, key="greeks_analysis")
            
            # Volatility Analysis
            st.header("📈 Volatility & Trade Conditions")
            fig_volatility = advanced_viz.plot_volatility_analysis()
            st.plotly_chart(fig_volatility, use_container_width=True, key="volatility_analysis")
            
            # Performance Heatmap
            st.header("🔥 Performance Heatmap")
            fig_heatmap = advanced_viz.plot_performance_heatmap()
            st.plotly_chart(fig_heatmap, use_container_width=True, key="performance_heatmap")
            
            # Risk Metrics Dashboard
            st.header("⚠️ Risk Metrics Dashboard")
            fig_risk = advanced_viz.plot_risk_metrics_dashboard()
            st.plotly_chart(fig_risk, use_container_width=True, key="risk_metrics")
            
            # Confidence Score Breakdown
            st.header("🎯 Confidence Score Analysis")
            fig_confidence = advanced_viz.plot_confidence_breakdown()
            st.plotly_chart(fig_confidence, use_container_width=True, key="confidence_breakdown")
            
            # Trade analysis
            st.header("📊 Trade Analysis")
            
            if results.trades:
                trade_df = pd.DataFrame([
                {
                    'Date': trade.entry_time,
                    'Symbol': trade.symbol,
                    'Type': trade.spread_type,
                    'Strikes': f"{trade.short_strike}/{trade.long_strike}",
                    'Contracts': trade.contracts,
                    'Credit': f"${trade.entry_credit:.2f}",
                    'P&L': f"${trade.realized_pnl:.2f}",
                    'Days': trade.days_in_trade,
                    'Confidence': f"{getattr(trade, 'confidence_score', 0)}%",
                    'Exit': trade.exit_reason if trade.exit_reason else "Open"
                }
                    for trade in results.trades
                ])
                
                st.dataframe(trade_df, use_container_width=True)
            else:
                st.info("No trades were executed during the backtest period.")
            
            # Show complete activity log
            with st.expander("📋 Complete Activity Log", expanded=False):
                for entry in st.session_state.activity_log:
                    st.text(format_activity_entry(entry))
                
            # Debug section
            with st.expander("🔍 Debug Info", expanded=False):
                col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Trades in results", len(results.trades))
                st.metric("Total trades metric", results.total_trades)
                
            with col2:
                opened_count = sum(1 for entry in st.session_state.activity_log if 'OPENED:' in entry.message)
                closed_count = sum(1 for entry in st.session_state.activity_log if 'CLOSED:' in entry.message)
                st.metric("OPENED in log", opened_count)
                st.metric("CLOSED in log", closed_count)
                
            with col3:
                trades_with_exit = sum(1 for t in results.trades if t.exit_time is not None)
                st.metric("Trades with exit_time", trades_with_exit)
                st.metric("Still open", opened_count - closed_count)
            
            # Show first few trades
            if results.trades:
                st.subheader("Sample Trades")
                sample_data = []
                for i, trade in enumerate(results.trades[:10]):
                    sample_data.append({
                        'Symbol': trade.symbol,
                        'Type': trade.spread_type if hasattr(trade, 'spread_type') else 'N/A',
                        'Entry': trade.entry_time.strftime('%Y-%m-%d') if trade.entry_time else 'N/A',
                        'Exit': trade.exit_time.strftime('%Y-%m-%d') if trade.exit_time else 'NONE',
                        'P&L': f"${trade.realized_pnl:.2f}" if hasattr(trade, 'realized_pnl') else 'N/A',
                        'Exit Reason': trade.exit_reason if hasattr(trade, 'exit_reason') else 'N/A'
                    })
                st.dataframe(pd.DataFrame(sample_data))
    
    # Saved Results Tab
    with tab2:
        st.header("📚 Saved Backtest Results")
        
        # Get saved runs
        saved_runs = backtest_db.get_backtest_runs(limit=20)
        
        if not saved_runs:
            st.info("No saved backtest results yet. Run a backtest to save results!")
        else:
            # Run selector
            st.subheader("Select a Backtest Run")
            
            # Create display options
            run_options = {}
            for run in saved_runs:
                timestamp = datetime.fromisoformat(run['run_timestamp'])
                config = json.loads(run['config'])
                label = f"{timestamp.strftime('%Y-%m-%d %H:%M')} | {', '.join(config['symbols'])} | P&L: ${run['total_pnl']:.2f}"
                run_options[label] = run['run_id']
            
            selected_label = st.selectbox("Choose a run to analyze:", list(run_options.keys()))
            selected_run_id = run_options[selected_label]
            
            # Load selected run
            run_data = next(r for r in saved_runs if r['run_id'] == selected_run_id)
            
            # Display run summary
            st.subheader("📊 Run Summary")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.metric("Total P&L", f"${run_data['total_pnl']:.2f}")
            with col2:
                st.metric("Win Rate", f"{run_data['win_rate']:.1f}%")
            with col3:
                st.metric("Sharpe Ratio", f"{run_data['sharpe_ratio']:.2f}")
            with col4:
                st.metric("Max Drawdown", f"{run_data['max_drawdown_pct']:.1f}%")
            with col5:
                st.metric("Total Trades", run_data['total_trades'])
            with col6:
                st.metric("Profit Factor", f"{run_data['profit_factor']:.2f}")
            
            # Configuration details
            with st.expander("🔧 Configuration", expanded=False):
                config = json.loads(run_data['config'])
                st.json(config)
            
            # Load trades and analyses
            trades = backtest_db.get_run_trades(selected_run_id)
            analyses = backtest_db.get_run_analyses(selected_run_id)
            
            # Tabs for detailed analysis
            analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["Trades", "Claude Analyses", "Confidence Analysis"])
            
            with analysis_tab1:
                st.subheader("📈 Trade Details")
                if trades:
                    trades_df = pd.DataFrame(trades)
                    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
                    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
                    
                    # Format for display
                    display_df = trades_df[[
                        'entry_time', 'symbol', 'spread_type', 'short_strike',
                        'long_strike', 'contracts', 'entry_credit', 'realized_pnl',
                        'exit_reason', 'days_in_trade', 'confidence_score'
                    ]]
                    
                    st.dataframe(display_df, use_container_width=True)
                    
                    # P&L distribution
                    st.subheader("P&L Distribution")
                    fig = px.histogram(trades_df, x='realized_pnl', nbins=20,
                                     title="Trade P&L Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No trades found for this run")
            
            with analysis_tab2:
                st.subheader("🤖 Claude's Analyses")
                if analyses:
                    # Filter for actual trade signals
                    trade_analyses = [a for a in analyses if a['should_trade']]
                    
                    st.metric("Total Analyses", len(analyses))
                    st.metric("Trade Signals", len(trade_analyses))
                    
                    # Show recent analyses
                    for analysis in analyses[-10:]:
                        timestamp = datetime.fromisoformat(analysis['timestamp'])
                        with st.expander(f"{analysis['symbol']} - {timestamp.strftime('%H:%M:%S')} - Confidence: {analysis['confidence']}%"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Price:** ${analysis['current_price']:.2f}")
                                st.write(f"**Change:** {analysis['percent_change']:.2f}%")
                                st.write(f"**IV Rank:** {analysis['iv_rank']:.1f}")
                            with col2:
                                if analysis['should_trade']:
                                    st.write(f"**Decision:** TRADE")
                                    st.write(f"**Type:** {analysis['spread_type']}")
                                    st.write(f"**Strikes:** ${analysis['short_strike']}/{analysis['long_strike']}")
                                else:
                                    st.write(f"**Decision:** NO TRADE")
                            
                            st.write(f"**Reasoning:** {analysis['reasoning']}")
                else:
                    st.info("No analyses found for this run")
            
            with analysis_tab3:
                st.subheader("🎯 Confidence Score Analysis")
                if trades:
                    confidence_df = backtest_db.get_confidence_analysis(selected_run_id)
                    
                    if not confidence_df.empty:
                        # Confidence vs P&L scatter
                        fig = px.scatter(confidence_df, x='confidence_score', y='realized_pnl',
                                       color='exit_reason', title="Confidence Score vs P&L")
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Average P&L by confidence range
                        confidence_df['confidence_range'] = pd.cut(confidence_df['confidence_score'],
                                                                  bins=[0, 60, 70, 80, 90, 100],
                                                                  labels=['<60', '60-70', '70-80', '80-90', '90-100'])
                        
                        avg_by_confidence = confidence_df.groupby('confidence_range', observed=False)['realized_pnl'].agg(['mean', 'count'])
                        
                        st.subheader("Average P&L by Confidence Range")
                        st.dataframe(avg_by_confidence)
                    else:
                        st.info("No confidence data available")
                else:
                    st.info("No trades to analyze")
            
            # Compare multiple runs
            st.subheader("📊 Compare Multiple Runs")
            if len(saved_runs) > 1:
                compare_runs = st.multiselect(
                    "Select runs to compare:",
                    [r['run_id'] for r in saved_runs],
                    default=[selected_run_id],
                    format_func=lambda x: next((label for label, rid in run_options.items() if rid == x), f"Run {x}")
                )
                
                if len(compare_runs) > 1:
                    comparison_df = backtest_db.get_performance_comparison(compare_runs)
                    
                    # Performance metrics comparison
                    metrics_fig = go.Figure()
                    
                    metrics = ['total_pnl', 'win_rate', 'sharpe_ratio', 'max_drawdown_pct']
                    for metric in metrics:
                        metrics_fig.add_trace(go.Bar(
                            name=metric.replace('_', ' ').title(),
                            x=comparison_df['run_id'].astype(str),
                            y=comparison_df[metric]
                        ))
                    
                    metrics_fig.update_layout(barmode='group', title="Performance Comparison")
                    st.plotly_chart(metrics_fig, use_container_width=True)

if __name__ == "__main__":
    main()