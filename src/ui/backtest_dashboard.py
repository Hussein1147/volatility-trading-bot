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

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry
from src.backtest.visualizer import BacktestVisualizer
from src.backtest.advanced_visualizer import AdvancedBacktestVisualizer

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
        "error": "❌"
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
    
    def progress_callback(current: int, total: int, message: str):
        st.session_state.current_progress = {
            "current": current,
            "total": total,
            "message": message
        }
        
        # Update progress display
        if total > 0:
            progress_value = current / total
            progress_text = f"Day {current}/{total} - {message}"
            progress_container.progress(progress_value, text=progress_text)
        else:
            progress_container.progress(0.0, text="Initializing...")
    
    # Create engine with callbacks
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    # Run backtest
    results = await engine.run_backtest()
    
    # Store results
    st.session_state.backtest_results = results
    
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
                value=datetime(2024, 11, 1).date(),
                max_value=datetime.now().date()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime(2024, 11, 8).date(),
                max_value=datetime.now().date()
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
        
        # Run button
        run_clicked = st.button("🚀 Run Backtest", type="primary", use_container_width=True)
    
    # Main area
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
                use_real_data=True
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

if __name__ == "__main__":
    main()