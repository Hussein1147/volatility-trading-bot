"""
AI-Powered Backtesting Dashboard using Claude Sonnet 4
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

from src.backtest.backtest_engine import BacktestConfig, BacktestEngine
from src.backtest.visualizer import BacktestVisualizer
from src.data.backtest_db import backtest_db

st.set_page_config(
    page_title="AI-Powered Backtest (Claude Sonnet 4)",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for modern look
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        color: #808495;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: white;
        border-bottom: 2px solid #007AFF;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1E1E1E 0%, #2D2D2D 100%);
        border: 1px solid #3A3F51;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .ai-badge {
        background: linear-gradient(135deg, #007AFF 0%, #0051D5 100%);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None
if 'backtest_running' not in st.session_state:
    st.session_state.backtest_running = False

async def run_backtest_async(config, progress_container):
    """Run backtest asynchronously with progress updates"""
    
    # Progress callback
    def progress_callback(progress):
        if hasattr(progress, 'percentage'):
            progress_value = progress.percentage / 100.0
            progress_text = f"{progress.message} ({progress.percentage:.1f}%)"
        else:
            progress_value = 0.5
            progress_text = progress.message if hasattr(progress, 'message') else "Processing..."
        
        progress_container.progress(progress_value, text=progress_text)
    
    # Create AI-powered engine
    st.info("🤖 Initializing Claude Sonnet 4 for intelligent trade analysis...")
    engine = BacktestEngine(config, progress_callback=progress_callback)
    
    # Run backtest
    results = await engine.run_backtest()
    
    # Store results
    if results and results.total_trades > 0:
        backtest_db.save_result(config, results)
    
    return results

def main():
    st.title("🤖 AI-Powered Backtesting Dashboard")
    st.markdown('<div class="ai-badge">Powered by Claude Sonnet 4</div>', unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Date range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=180),
                max_value=datetime.now()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now(),
                max_value=datetime.now()
            )
        
        # Symbol selection
        available_symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'TLT', 'GLD', 'XLE', 'XLF']
        symbols = st.multiselect(
            "Symbols",
            options=available_symbols,
            default=['SPY', 'QQQ', 'IWM']
        )
        
        # Capital and risk
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000
        )
        
        max_risk_per_trade = st.slider(
            "Max Risk per Trade (%)",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5
        )
        
        # Strategy parameters
        st.subheader("Strategy Parameters")
        
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
        
        # AI Information
        st.markdown("---")
        st.subheader("🤖 AI Configuration")
        st.info("Using Claude Sonnet 4 for intelligent trade analysis based on TradeBrain-V professional rules")
        
        # Run button
        run_clicked = st.button("🚀 Run AI Backtest", type="primary", use_container_width=True)
    
    # Main area
    if run_clicked and not st.session_state.backtest_running:
        if not symbols:
            st.error("Please select at least one symbol")
        else:
            st.session_state.backtest_running = True
            
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
            
            st.header("🔄 Running AI-Powered Backtest")
            
            # Progress bar
            progress_container = st.empty()
            
            # Run backtest
            results = asyncio.run(run_backtest_async(config, progress_container))
            
            st.session_state.backtest_results = results
            st.session_state.backtest_running = False
            
            # Clear progress
            progress_container.empty()
            
            if results and results.total_trades > 0:
                st.success(f"✅ Backtest complete! Claude analyzed {results.total_trades} trading opportunities.")
            else:
                st.warning("No trades were executed. This is normal if no volatility events met the criteria.")
    
    # Display results
    if st.session_state.backtest_results:
        results = st.session_state.backtest_results
        
        st.header("📊 Backtest Results")
        
        # Key metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric(
                "Total P&L",
                f"${results.total_pnl:,.2f}",
                delta=f"{(results.total_pnl/config.initial_capital)*100:.1f}%" if 'config' in locals() else None
            )
        
        with col2:
            st.metric(
                "Total Trades",
                f"{results.total_trades}",
                delta=None
            )
        
        with col3:
            st.metric(
                "Win Rate",
                f"{results.win_rate:.1f}%",
                delta=None
            )
        
        with col4:
            st.metric(
                "Profit Factor",
                f"{results.profit_factor:.2f}",
                delta=None
            )
        
        with col5:
            st.metric(
                "Max Drawdown",
                f"${results.max_drawdown:,.0f}",
                delta=f"{results.max_drawdown_pct:.1f}%",
                delta_color="inverse"
            )
        
        with col6:
            st.metric(
                "Sharpe Ratio",
                f"{results.sharpe_ratio:.2f}",
                delta=None
            )
        
        # Visualizations
        if results.equity_curve:
            st.header("📈 Performance Charts")
            
            # Create visualizer
            visualizer = BacktestVisualizer(results)
            
            # Equity curve
            fig_equity = visualizer.plot_equity_curve()
            st.plotly_chart(fig_equity, use_container_width=True)
            
            # Trade details
            if results.trades:
                st.header("📋 Recent Trades (AI Decisions)")
                
                # Convert trades to dataframe
                trades_data = []
                for trade in results.trades[-10:]:  # Last 10 trades
                    trades_data.append({
                        'Date': trade.entry_time.strftime('%Y-%m-%d'),
                        'Symbol': trade.symbol,
                        'Strategy': trade.spread_type,
                        'Confidence': f"{trade.confidence_score}%",
                        'Contracts': trade.contracts,
                        'P&L': f"${trade.realized_pnl:.2f}",
                        'Exit': trade.exit_reason
                    })
                
                trades_df = pd.DataFrame(trades_data)
                st.dataframe(trades_df, use_container_width=True)
                
                # AI Analysis Summary
                st.header("🧠 AI Analysis Summary")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Strategy Distribution")
                    strategy_counts = {}
                    for trade in results.trades:
                        strategy = trade.spread_type
                        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                    
                    if strategy_counts:
                        fig_strategies = px.pie(
                            values=list(strategy_counts.values()),
                            names=list(strategy_counts.keys()),
                            title="Strategies Used by AI"
                        )
                        st.plotly_chart(fig_strategies, use_container_width=True)
                
                with col2:
                    st.subheader("Confidence Distribution")
                    confidence_scores = [trade.confidence_score for trade in results.trades]
                    if confidence_scores:
                        fig_confidence = px.histogram(
                            x=confidence_scores,
                            nbins=20,
                            title="AI Confidence Scores",
                            labels={'x': 'Confidence Score (%)', 'y': 'Count'}
                        )
                        st.plotly_chart(fig_confidence, use_container_width=True)
        
        else:
            st.info("No trades to display. Try adjusting the parameters or date range.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "This backtest uses **Claude Sonnet 4** to analyze market conditions and make trading decisions "
        "based on the TradeBrain-V professional options strategy. All decisions are made by AI without "
        "hardcoded rules."
    )

if __name__ == "__main__":
    main()