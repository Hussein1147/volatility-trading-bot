#!/usr/bin/env python3
"""
Separate Streamlit dashboard for backtesting volatility trading strategies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import json
from src.backtest.backtest_engine import BacktestEngine, BacktestConfig, BacktestResults
from src.backtest.data_fetcher import AlpacaDataFetcher
from src.backtest.visualizer import BacktestVisualizer

# Page config
st.set_page_config(
    page_title="Volatility Trading Bot - Backtesting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply same dark theme as main dashboard
st.markdown("""
<style>
    /* Dark theme colors - matching main dashboard */
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
    
    .stWarning {
        background-color: rgba(255, 179, 0, 0.1);
        border: 1px solid #FFB300;
        color: #FFB300;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #E0E0E0;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #252A38;
    }
    
    /* Input fields */
    .stDateInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: #252A38;
        color: #E0E0E0;
        border: 1px solid #3A3F51;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None
    
if 'backtest_running' not in st.session_state:
    st.session_state.backtest_running = False
    
if 'backtest_config' not in st.session_state:
    st.session_state.backtest_config = None

async def run_backtest_async(config: BacktestConfig, progress_placeholder, status_placeholder, activity_placeholder):
    """Run backtest asynchronously with progress tracking"""
    # Keep last N activities
    activities = []
    max_activities = 20
    
    async def progress_callback(progress):
        # Update progress bar
        progress_placeholder.progress(progress.progress_percent, text=f"Progress: {progress.progress_percent:.1%}")
        
        # Update status text
        status_placeholder.text(progress.get_status_message())
        
        # Add activity if there's a new trade message
        if progress.message:
            timestamp = progress.current_date.strftime('%Y-%m-%d %H:%M') if progress.current_date else ''
            activities.append({
                'time': timestamp,
                'message': progress.message
            })
            
            # Keep only last N activities
            if len(activities) > max_activities:
                activities.pop(0)
            
            # Update activity log with scrollable content
            activity_html = '<div style="background-color: #1e1e1e; padding: 10px; border-radius: 5px; height: 300px; overflow-y: auto;">'
            for activity in reversed(activities):
                if activity['time']:
                    activity_html += f'<div style="color: #888; font-size: 0.9em;">[{activity["time"]}]</div>'
                activity_html += f'<div style="color: #e0e0e0; margin-bottom: 10px;">{activity["message"]}</div>'
            activity_html += '</div>'
            
            activity_placeholder.markdown(activity_html, unsafe_allow_html=True)
    
    engine = BacktestEngine(config, progress_callback=progress_callback)
    results = await engine.run_backtest()
    return results

def main():
    st.title("📊 Volatility Trading Strategy Backtesting")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Backtest Configuration")
        
        st.subheader("📅 Date Range")
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=365),
                max_value=datetime.now().date()
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now().date(),
                max_value=datetime.now().date()
            )
            
        # Check if using real options data
        if start_date >= datetime(2024, 2, 1).date():
            st.success("✅ Real Alpaca options data available")
        else:
            st.warning("⚠️ Using simulated options data (pre-Feb 2024)")
        
        st.subheader("📈 Symbols")
        symbols = st.multiselect(
            "Select Symbols",
            ["SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"],
            default=["SPY", "QQQ", "IWM", "DIA"]
        )
        
        st.subheader("💰 Capital & Risk")
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=10000,
            max_value=1000000,
            value=100000,
            step=10000
        )
        
        max_risk = st.slider(
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
                    max_risk_per_trade=max_risk / 100,
                    min_iv_rank=min_iv_rank,
                    min_price_move=min_price_move,
                    confidence_threshold=confidence_threshold,
                    commission_per_contract=commission,
                    use_real_data=use_real_data
                )
                st.session_state.backtest_config = config
                st.session_state.backtest_running = True
                
    # Main area
    if st.session_state.backtest_running:
        st.info("🔄 Running backtest... This may take several minutes.")
        
        # Create two columns for progress and activity
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.subheader("📊 Progress")
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            # Initial progress bar
            progress_placeholder.progress(0.0, text="Progress: 0.0%")
            status_placeholder.text("Initializing backtest...")
            
            # Add progress information
            with st.expander("ℹ️ What's happening", expanded=False):
                st.write("- 📊 Processing volatility events in historical data")
                st.write("- 🤖 Claude AI analyzing each opportunity")
                st.write("- ⏱️ Rate limited to 4 requests/minute to avoid API errors")
                st.write("- 💰 Simulating trade execution and management")
                st.write("- 📈 Tracking P&L and performance metrics")
        
        with col2:
            st.subheader("📋 Activity Log")
            activity_placeholder = st.empty()
            
            # Initial empty activity log
            activity_placeholder.markdown(
                '<div style="background-color: #1e1e1e; padding: 10px; border-radius: 5px; height: 300px; overflow-y: auto; color: #888;">Waiting for activity...</div>',
                unsafe_allow_html=True
            )
            
        # Add a note about rate limiting
        st.warning("⚠️ Note: To avoid API rate limits, the backtest processes opportunities slowly. A full year backtest may take 5-10 minutes depending on market volatility.")
        
        # Run backtest with progress tracking
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_backtest_async(
            st.session_state.backtest_config,
            progress_placeholder,
            status_placeholder,
            activity_placeholder
        ))
        
        st.session_state.backtest_results = results
        st.session_state.backtest_running = False
        st.success("✅ Backtest completed!")
        st.balloons()
            
    # Display results
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
                delta=f"{results.winning_trades}/{results.total_trades} trades"
            )
            
        with col5:
            st.metric(
                "Profit Factor",
                f"{summary['profit_factor']:.2f}",
                delta="Gross Profit/Loss"
            )
            
        with col6:
            st.metric(
                "Total Trades",
                results.total_trades,
                delta=f"Avg {summary['avg_days_in_trade']:.1f} days"
            )
            
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Equity Curve", "📊 Trade Analysis", "📋 Trade Details", "📉 Risk Analysis"])
        
        with tab1:
            st.subheader("Portfolio Equity Curve")
            fig_equity = visualizer.plot_equity_curve()
            st.plotly_chart(fig_equity, use_container_width=True, key="equity_curve")
            
            # Monthly returns heatmap
            st.subheader("Monthly Returns Heatmap")
            fig_monthly = visualizer.plot_monthly_returns()
            st.plotly_chart(fig_monthly, use_container_width=True, key="monthly_returns")
            
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Returns Distribution")
                fig_returns = visualizer.plot_returns_distribution()
                st.plotly_chart(fig_returns, use_container_width=True, key="returns_dist")
                
            with col2:
                st.subheader("Win/Loss Analysis")
                fig_winloss = visualizer.plot_win_loss_analysis()
                st.plotly_chart(fig_winloss, use_container_width=True, key="win_loss")
                
            # Trade timeline
            st.subheader("Trade Timeline")
            fig_timeline = visualizer.plot_trade_timeline()
            st.plotly_chart(fig_timeline, use_container_width=True, key="trade_timeline")
            
        with tab3:
            st.subheader("All Trades")
            
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average Win", f"${summary['avg_win']:.2f}")
            with col2:
                st.metric("Average Loss", f"${abs(summary['avg_loss']):.2f}")
            with col3:
                st.metric("Best Trade", f"${summary['best_trade']:.2f}")
            with col4:
                st.metric("Worst Trade", f"${summary['worst_trade']:.2f}")
                
            # Trade details table
            trades_df = visualizer.get_trade_summary()
            if not trades_df.empty:
                st.dataframe(
                    trades_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "P&L": st.column_config.NumberColumn(
                            "P&L",
                            format="$%.2f",
                        ),
                        "Entry Credit": st.column_config.NumberColumn(
                            "Entry Credit",
                            format="$%.2f",
                        )
                    }
                )
                
                # Download trades
                csv = trades_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Trade Details",
                    data=csv,
                    file_name=f"backtest_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No trades to display")
                
        with tab4:
            st.subheader("Risk Metrics")
            
            # Risk metrics
            col1, col2 = st.columns(2)
            
            with col1:
                # Calculate consecutive wins
                if results.trades:
                    wins = pd.Series([t.realized_pnl > 0 for t in results.trades])
                    win_groups = wins.groupby((wins != wins.shift()).cumsum())
                    max_wins = max([len(list(g)) for k, g in win_groups if list(g)[0]], default=0)
                    
                    losses = pd.Series([t.realized_pnl <= 0 for t in results.trades])
                    loss_groups = losses.groupby((losses != losses.shift()).cumsum())
                    max_losses = max([len(list(g)) for k, g in loss_groups if list(g)[0]], default=0)
                else:
                    max_wins = 0
                    max_losses = 0
                    
                st.metric("Max Consecutive Wins", max_wins)
                st.metric("Max Consecutive Losses", max_losses)
                
            with col2:
                st.metric("Average Risk per Trade", f"${st.session_state.backtest_config.initial_capital * st.session_state.backtest_config.max_risk_per_trade:.2f}")
                st.metric("Risk-Reward Ratio", f"{abs(summary['avg_win'] / summary['avg_loss']):.2f}" if summary['avg_loss'] != 0 else "N/A")
                
            # Drawdown analysis
            st.subheader("Drawdown Analysis")
            
            # Calculate drawdown series
            equity_series = pd.Series(results.equity_curve)
            rolling_max = equity_series.expanding().max()
            drawdown = (equity_series - rolling_max) / rolling_max * 100
            
            import plotly.graph_objects as go
            
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=list(range(len(drawdown))),
                y=drawdown,
                fill='tozeroy',
                mode='lines',
                name='Drawdown %',
                line=dict(color='#D50000', width=1),
                fillcolor='rgba(213, 0, 0, 0.3)'
            ))
            
            fig_dd.update_layout(
                title="Drawdown Over Time",
                xaxis_title="Trading Days",
                yaxis_title="Drawdown (%)",
                template="plotly_dark",
                height=400
            )
            
            st.plotly_chart(fig_dd, use_container_width=True, key="drawdown_chart")
            
    else:
        # Welcome message
        st.info("👈 Configure your backtest parameters in the sidebar and click 'Run Backtest' to begin")
        
        # Information about backtesting
        with st.expander("ℹ️ About Backtesting", expanded=True):
            st.markdown("""
            ### What is Backtesting?
            
            Backtesting allows you to test your volatility trading strategy on historical data to evaluate its performance
            before risking real capital.
            
            ### Key Features:
            
            - **Historical Data**: Uses real Alpaca market data (from Feb 2024) or simulated data for earlier periods
            - **Realistic Simulation**: Includes commissions, slippage, and time decay
            - **Claude AI Integration**: Same analysis engine as live trading
            - **Comprehensive Metrics**: Sharpe ratio, drawdown, win rate, and more
            - **Visual Analysis**: Interactive charts to understand strategy performance
            
            ### Important Notes:
            
            - Past performance does not guarantee future results
            - Alpaca options data is only available from February 2024 onwards
            - Simulated data for earlier periods is based on historical volatility patterns
            - Always validate results with paper trading before going live
            """)

if __name__ == "__main__":
    main()