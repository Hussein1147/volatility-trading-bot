"""
Backtesting Dashboard V2 with Activity Log and Progress Bar
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
from collections import deque

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry
from src.backtest.backtest_visualizer import BacktestVisualizer

st.set_page_config(
    page_title="Volatility Trading Backtest V2",
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
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None
if 'backtest_config' not in st.session_state:
    st.session_state.backtest_config = None
if 'backtest_running' not in st.session_state:
    st.session_state.backtest_running = False
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = deque(maxlen=100)  # Keep last 100 entries
if 'progress' not in st.session_state:
    st.session_state.progress = {"current": 0, "total": 0, "message": ""}

def format_activity_entry(entry: ActivityLogEntry) -> str:
    """Format activity log entry for display"""
    time_str = entry.timestamp.strftime("%H:%M:%S")
    icon = {
        "info": "ℹ️",
        "trade": "💰",
        "warning": "⚠️",
        "error": "❌"
    }.get(entry.type, "📝")
    
    return f"{time_str} {icon} {entry.message}"

async def run_backtest_with_logging(config: BacktestConfig):
    """Run backtest with activity logging and progress tracking"""
    
    # Clear previous activity log
    st.session_state.activity_log.clear()
    
    # Callback for activity updates
    def activity_callback(entry: ActivityLogEntry):
        st.session_state.activity_log.append(entry)
    
    # Callback for progress updates
    def progress_callback(current: int, total: int, message: str):
        st.session_state.progress = {
            "current": current,
            "total": total,
            "message": message
        }
    
    # Create engine with callbacks
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    # Run backtest
    results = await engine.run_backtest()
    
    return results, list(engine.activity_log)

def main():
    st.title("📊 Volatility Trading Backtest V2")
    st.markdown("Enhanced backtesting with real-time activity log and progress tracking")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Backtest Configuration")
        
        # Tips
        with st.expander("💡 Quick Start", expanded=True):
            st.markdown("""
            **For a 1-2 minute test:**
            - Date Range: Last 30 days
            - Symbols: SPY only
            - Min Price Move: 2.5%
            - Min IV Rank: 80
            
            **Watch the activity log** below for real-time updates!
            """)
        
        # Date range
        st.subheader("📅 Date Range")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=30),
                max_value=datetime.now()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now(),
                max_value=datetime.now()
            )
            
        # Symbol selection
        st.subheader("🎯 Symbols")
        available_symbols = ['SPY', 'QQQ', 'IWM', 'DIA']
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
        
        st.subheader("📊 Strategy Parameters")
        min_iv_rank = st.slider(
            "Min IV Rank",
            min_value=50,
            max_value=90,
            value=70,
            step=5
        )
        
        min_price_move = st.slider(
            "Min Price Move (%)",
            min_value=1.0,
            max_value=5.0,
            value=1.5,
            step=0.5
        )
        
        confidence_threshold = st.slider(
            "Min Confidence (%)",
            min_value=50,
            max_value=90,
            value=70,
            step=5
        )
        
        # Run button
        if st.button("🚀 Run Backtest", type="primary", use_container_width=True):
            if not symbols:
                st.error("Please select at least one symbol")
            else:
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
                    use_real_data=True
                )
                st.session_state.backtest_config = config
                st.session_state.backtest_running = True
                st.session_state.progress = {"current": 0, "total": 0, "message": "Initializing..."}
    
    # Main area
    if st.session_state.backtest_running:
        st.header("🔄 Backtest in Progress")
        
        # Progress section
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Progress bar
            progress_placeholder = st.empty()
            
        with col2:
            # Stats
            stats_placeholder = st.empty()
        
        # Activity log section
        st.subheader("📋 Activity Log")
        log_placeholder = st.empty()
        
        # Run backtest
        async def run_backtest():
            results, full_log = await run_backtest_with_logging(st.session_state.backtest_config)
            return results, full_log
        
        # Create event loop and run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Start backtest task
        task = loop.create_task(run_backtest())
        
        # Update UI while running
        while not task.done():
            # Update progress bar
            progress = st.session_state.progress
            if progress["total"] > 0:
                progress_value = progress["current"] / progress["total"]
                progress_text = f"Day {progress['current']}/{progress['total']} - {progress['message']}"
                progress_placeholder.progress(progress_value, text=progress_text)
                
                # Update stats
                with stats_placeholder.container():
                    st.metric("Progress", f"{progress_value*100:.1f}%")
                    trades_count = sum(1 for entry in st.session_state.activity_log if entry.type == "trade" and "OPENED" in entry.message)
                    st.metric("Trades", trades_count)
            else:
                progress_placeholder.progress(0.0, text="Initializing backtest...")
            
            # Update activity log
            if st.session_state.activity_log:
                with log_placeholder.container():
                    log_html = '<div class="activity-log">'
                    for entry in reversed(list(st.session_state.activity_log)[-20:]):  # Show last 20 entries
                        css_class = f"log-{entry.type}"
                        formatted = format_activity_entry(entry)
                        log_html += f'<div class="{css_class}">{formatted}</div>'
                    log_html += '</div>'
                    st.markdown(log_html, unsafe_allow_html=True)
            
            # Small delay to allow UI updates
            time.sleep(0.1)
        
        # Get results
        results, full_log = loop.run_until_complete(task)
        
        # Clear progress
        progress_placeholder.empty()
        stats_placeholder.empty()
        
        # Save results
        st.session_state.backtest_results = results
        st.session_state.backtest_running = False
        
        # Success message
        st.success("✅ Backtest completed!")
        st.balloons()
        
        # Show final activity log
        st.subheader("📋 Complete Activity Log")
        with st.expander("View full log", expanded=False):
            for entry in full_log[-50:]:  # Show last 50 entries
                st.text(format_activity_entry(entry))
    
    # Display results
    if st.session_state.backtest_results and not st.session_state.backtest_running:
        results = st.session_state.backtest_results
        visualizer = BacktestVisualizer(results)
        
        # Performance summary
        st.header("📊 Performance Summary")
        
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
                delta=f"{summary['winning_trades']}/{summary['total_trades']}"
            )
            
        with col5:
            st.metric(
                "Profit Factor",
                f"{summary['profit_factor']:.2f}",
                delta="Ratio"
            )
            
        with col6:
            st.metric(
                "Avg Days/Trade",
                f"{summary['avg_days_in_trade']:.1f}",
                delta="Days"
            )
        
        # Charts
        st.header("📈 Performance Charts")
        
        # Equity curve
        st.subheader("Portfolio Value Over Time")
        fig_equity = visualizer.plot_equity_curve()
        st.plotly_chart(fig_equity, use_container_width=True, key="equity_curve_v2")
        
        # Monthly returns and distribution
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Monthly Returns Heatmap")
            fig_monthly = visualizer.plot_monthly_returns()
            if fig_monthly:
                st.plotly_chart(fig_monthly, use_container_width=True, key="monthly_returns_v2")
            else:
                st.info("Not enough data for monthly returns")
                
        with col2:
            st.subheader("Returns Distribution")
            fig_returns = visualizer.plot_returns_distribution()
            st.plotly_chart(fig_returns, use_container_width=True, key="returns_dist_v2")
        
        # Trade analysis
        st.header("🔍 Trade Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_win_loss = visualizer.plot_win_loss_distribution()
            st.plotly_chart(fig_win_loss, use_container_width=True, key="win_loss_v2")
            
        with col2:
            fig_pnl_time = visualizer.plot_pnl_by_trade_duration()
            st.plotly_chart(fig_pnl_time, use_container_width=True, key="pnl_time_v2")
        
        # Trade log
        st.header("📋 Trade Log")
        
        if results.trades:
            trades_df = visualizer.get_trade_summary()
            
            # Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_symbol = st.selectbox(
                    "Filter by Symbol",
                    ["All"] + sorted(trades_df['Symbol'].unique()),
                    key="symbol_filter_v2"
                )
                
            with col2:
                filter_type = st.selectbox(
                    "Filter by Type",
                    ["All", "call_credit", "put_credit"],
                    key="type_filter_v2"
                )
                
            with col3:
                filter_outcome = st.selectbox(
                    "Filter by Outcome",
                    ["All", "Winners", "Losers"],
                    key="outcome_filter_v2"
                )
            
            # Apply filters
            filtered_df = trades_df.copy()
            
            if filter_symbol != "All":
                filtered_df = filtered_df[filtered_df['Symbol'] == filter_symbol]
                
            if filter_type != "All":
                filtered_df = filtered_df[filtered_df['Type'] == filter_type]
                
            if filter_outcome == "Winners":
                filtered_df = filtered_df[filtered_df['P&L'].str.replace('$', '').str.replace(',', '').astype(float) > 0]
            elif filter_outcome == "Losers":
                filtered_df = filtered_df[filtered_df['P&L'].str.replace('$', '').str.replace(',', '').astype(float) <= 0]
            
            st.dataframe(filtered_df, use_container_width=True)
            
            # Download button
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Trade Log",
                data=csv,
                file_name=f"backtest_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No trades were executed during the backtest period")

if __name__ == "__main__":
    main()