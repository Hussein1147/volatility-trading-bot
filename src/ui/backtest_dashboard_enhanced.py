"""
Enhanced Backtesting Dashboard with Real-time Progress
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
from concurrent.futures import ThreadPoolExecutor
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import BacktestEngine, BacktestConfig, BacktestResults
from backtest.backtest_visualizer import BacktestVisualizer

st.set_page_config(
    page_title="Volatility Trading Backtest (Enhanced)",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None
if 'backtest_config' not in st.session_state:
    st.session_state.backtest_config = None
if 'backtest_running' not in st.session_state:
    st.session_state.backtest_running = False
if 'progress' not in st.session_state:
    st.session_state.progress = {"current": 0, "total": 0, "message": "", "trades": 0}

def update_progress(current_day, total_days, message="", trades_completed=0):
    """Update progress in session state"""
    st.session_state.progress = {
        "current": current_day,
        "total": total_days,
        "message": message,
        "trades": trades_completed
    }

async def run_backtest_with_progress(config: BacktestConfig):
    """Run backtest with progress updates"""
    engine = BacktestEngine(config)
    
    # Calculate total trading days
    total_days = 0
    current_date = config.start_date
    while current_date <= config.end_date:
        if current_date.weekday() < 5:  # Weekday
            total_days += 1
        current_date += timedelta(days=1)
    
    # Reset date for actual run
    current_date = config.start_date
    day_count = 0
    
    # Override the run_backtest method to add progress updates
    original_process_day = engine._process_trading_day
    
    async def process_day_with_progress(date):
        nonlocal day_count
        day_count += 1
        
        # Update progress
        trades_count = len(engine.results.trades)
        message = f"Processing {date.strftime('%Y-%m-%d')} | {trades_count} trades completed"
        
        if engine.last_api_calls and len(engine.last_api_calls) >= engine.max_api_calls_per_minute:
            message += " | ⏱️ Rate limited"
            
        update_progress(day_count, total_days, message, trades_count)
        
        # Call original method
        return await original_process_day(date)
    
    engine._process_trading_day = process_day_with_progress
    
    # Run the backtest
    results = await engine.run_backtest()
    
    return results

async def run_backtest_async(config: BacktestConfig):
    """Wrapper to run backtest asynchronously"""
    return await run_backtest_with_progress(config)

def main():
    st.title("📊 Volatility Trading Backtest (Enhanced)")
    st.markdown("Test historical performance of volatility trading strategies with real-time progress")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Backtest Configuration")
        
        # Tips at the top
        with st.expander("💡 Quick Tips", expanded=True):
            st.markdown("""
            **For a quick test (1-2 min):**
            - Use last 30 days
            - Select only SPY
            - Set Min Price Move to 2.5%
            - Set Min IV Rank to 80
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
        
        st.subheader("🎯 Trade Management")
        use_real_data = st.checkbox("Use Real Market Data", value=True)
        commission = st.number_input(
            "Commission per Contract ($)",
            min_value=0.0,
            max_value=2.0,
            value=0.65,
            step=0.05
        )
        
        # Run backtest button
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
                    commission_per_contract=commission,
                    use_real_data=use_real_data
                )
                st.session_state.backtest_config = config
                st.session_state.backtest_running = True
                st.session_state.progress = {"current": 0, "total": 0, "message": "Starting...", "trades": 0}
                
    # Main area
    if st.session_state.backtest_running:
        st.info("🔄 Running backtest...")
        
        # Progress bar
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Create a container for the progress updates
        with st.container():
            # Run backtest in a separate thread to allow UI updates
            def run_backtest_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(run_backtest_async(st.session_state.backtest_config))
                st.session_state.backtest_results = results
                st.session_state.backtest_running = False
            
            # Start backtest in background
            thread = threading.Thread(target=run_backtest_thread)
            thread.start()
            
            # Update progress bar while running
            while st.session_state.backtest_running:
                progress = st.session_state.progress
                
                if progress["total"] > 0:
                    pct = progress["current"] / progress["total"]
                    progress_placeholder.progress(pct, text=f"Day {progress['current']}/{progress['total']}")
                    
                    # Status message
                    status_msg = progress["message"]
                    if "Rate limited" in status_msg:
                        status_placeholder.warning(f"⏱️ {status_msg}")
                    else:
                        status_placeholder.info(f"📊 {status_msg}")
                else:
                    progress_placeholder.progress(0, text="Initializing...")
                    
                time.sleep(0.1)  # Update every 100ms
            
            # Wait for thread to complete
            thread.join()
            
            # Clear progress indicators
            progress_placeholder.empty()
            status_placeholder.empty()
            
            st.success("✅ Backtest completed!")
            st.balloons()
            
    # Display results (same as before)
    if st.session_state.backtest_results:
        results = st.session_state.backtest_results
        visualizer = BacktestVisualizer(results)
        
        # Performance summary metrics
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
        st.plotly_chart(fig_equity, use_container_width=True, key="equity_curve_enhanced")
        
        # Monthly returns heatmap
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Monthly Returns Heatmap")
            fig_monthly = visualizer.plot_monthly_returns()
            if fig_monthly:
                st.plotly_chart(fig_monthly, use_container_width=True, key="monthly_returns_enhanced")
            else:
                st.info("Not enough data for monthly returns")
                
        with col2:
            st.subheader("Returns Distribution")
            fig_returns = visualizer.plot_returns_distribution()
            st.plotly_chart(fig_returns, use_container_width=True, key="returns_dist_enhanced")
            
        # Trade analysis
        st.header("🔍 Trade Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_win_loss = visualizer.plot_win_loss_distribution()
            st.plotly_chart(fig_win_loss, use_container_width=True, key="win_loss_enhanced")
            
        with col2:
            fig_pnl_time = visualizer.plot_pnl_by_trade_duration()
            st.plotly_chart(fig_pnl_time, use_container_width=True, key="pnl_time_enhanced")
            
        # Trade log
        st.header("📋 Trade Log")
        
        if results.trades:
            df_trades = visualizer.get_trade_summary()
            
            # Add filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_symbol = st.selectbox(
                    "Filter by Symbol",
                    ["All"] + sorted(df_trades['Symbol'].unique())
                )
                
            with col2:
                filter_type = st.selectbox(
                    "Filter by Type",
                    ["All", "call_credit", "put_credit"]
                )
                
            with col3:
                filter_outcome = st.selectbox(
                    "Filter by Outcome",
                    ["All", "Winners", "Losers"]
                )
                
            # Apply filters
            filtered_df = df_trades.copy()
            
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