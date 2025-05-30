import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import asyncio
import os
from typing import Dict, List, Any

# Database imports
from database import DatabaseManager
from sqlalchemy import text

# Configure Streamlit
st.set_page_config(
    page_title="Volatility Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class TradingBotDashboard:
    def __init__(self):
        # Initialize database connection
        database_url = os.getenv('DATABASE_URL', 'postgresql://bot_user:bot_password@postgres:5432/trading_bot')
        self.db = DatabaseManager(database_url)
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Fetch all dashboard data"""
        async with self.db.get_session() as session:
            # Get performance summary
            perf_result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(realized_pnl) as total_pnl,
                    AVG(realized_pnl) as avg_pnl,
                    MAX(realized_pnl) as best_trade,
                    MIN(realized_pnl) as worst_trade,
                    MAX(account_balance) as current_balance
                FROM trades 
                WHERE status = 'closed'
                AND entry_time >= CURRENT_DATE - INTERVAL '30 days'
            """))
            performance = dict(perf_result.first()._mapping) if perf_result.first() else {}
            
            # Get open trades
            open_trades_result = await session.execute(text("""
                SELECT * FROM trades 
                WHERE status = 'open' 
                ORDER BY entry_time DESC
            """))
            open_trades = [dict(row._mapping) for row in open_trades_result]
            
            # Get recent trades
            recent_trades_result = await session.execute(text("""
                SELECT * FROM trades 
                WHERE status = 'closed'
                ORDER BY exit_time DESC 
                LIMIT 20
            """))
            recent_trades = [dict(row._mapping) for row in recent_trades_result]
            
            # Get daily performance
            daily_perf_result = await session.execute(text("""
                SELECT date, daily_pnl, cumulative_pnl, total_trades, win_rate, account_balance
                FROM performance_metrics 
                WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY date ASC
            """))
            daily_performance = [dict(row._mapping) for row in daily_perf_result]
            
            # Get market snapshots
            market_data_result = await session.execute(text("""
                SELECT symbol, current_price, percent_change, iv_rank, timestamp
                FROM market_snapshots 
                WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 day'
                ORDER BY timestamp DESC
            """))
            market_snapshots = [dict(row._mapping) for row in market_data_result]
            
            # Get recent alerts
            alerts_result = await session.execute(text("""
                SELECT alert_type, message, created_at
                FROM alerts 
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                ORDER BY created_at DESC 
                LIMIT 10
            """))
            alerts = [dict(row._mapping) for row in alerts_result]
            
            return {
                'performance': performance,
                'open_trades': open_trades,
                'recent_trades': recent_trades,
                'daily_performance': daily_performance,
                'market_snapshots': market_snapshots,
                'alerts': alerts
            }
    
    def render_performance_metrics(self, performance: Dict[str, Any]):
        """Render performance metrics cards"""
        col1, col2, col3, col4 = st.columns(4)
        
        total_trades = performance.get('total_trades', 0) or 0
        winning_trades = performance.get('winning_trades', 0) or 0
        total_pnl = performance.get('total_pnl', 0) or 0
        current_balance = performance.get('current_balance', 10000) or 10000
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        with col1:
            st.metric(
                label="Total P&L (30d)",
                value=f"${total_pnl:.2f}",
                delta=f"{(total_pnl/10000)*100:.2f}%" if total_pnl != 0 else "0%"
            )
        
        with col2:
            st.metric(
                label="Win Rate",
                value=f"{win_rate:.1f}%",
                delta=f"{winning_trades}/{total_trades} trades"
            )
        
        with col3:
            st.metric(
                label="Total Trades",
                value=str(total_trades),
                delta="30 days"
            )
        
        with col4:
            st.metric(
                label="Account Balance",
                value=f"${current_balance:.2f}",
                delta=f"${total_pnl:.2f}" if total_pnl != 0 else None
            )
    
    def render_pnl_chart(self, daily_performance: List[Dict[str, Any]]):
        """Render P&L chart"""
        if not daily_performance:
            st.info("No performance data available yet.")
            return
        
        df = pd.DataFrame(daily_performance)
        df['date'] = pd.to_datetime(df['date'])
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Cumulative P&L', 'Daily P&L'),
            vertical_spacing=0.1
        )
        
        # Cumulative P&L
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['cumulative_pnl'],
                mode='lines+markers',
                name='Cumulative P&L',
                line=dict(color='#1f77b4', width=2)
            ),
            row=1, col=1
        )
        
        # Daily P&L
        colors = ['green' if x >= 0 else 'red' for x in df['daily_pnl']]
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['daily_pnl'],
                name='Daily P&L',
                marker_color=colors
            ),
            row=2, col=1
        )
        
        fig.update_layout(height=600, showlegend=False)
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
        fig.update_yaxes(title_text="Daily P&L ($)", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_open_trades(self, open_trades: List[Dict[str, Any]]):
        """Render open trades table"""
        if not open_trades:
            st.info("No open trades currently.")
            return
        
        df = pd.DataFrame(open_trades)
        
        # Format columns for display
        display_cols = [
            'symbol', 'spread_type', 'short_strike', 'long_strike', 
            'contracts', 'credit_received', 'max_loss', 'probability_profit',
            'confidence_score', 'entry_time'
        ]
        
        df_display = df[display_cols].copy()
        df_display['entry_time'] = pd.to_datetime(df_display['entry_time']).dt.strftime('%Y-%m-%d %H:%M')
        df_display['short_strike'] = df_display['short_strike'].apply(lambda x: f"${x:.2f}")
        df_display['long_strike'] = df_display['long_strike'].apply(lambda x: f"${x:.2f}")
        df_display['credit_received'] = df_display['credit_received'].apply(lambda x: f"${x:.2f}")
        df_display['max_loss'] = df_display['max_loss'].apply(lambda x: f"${x:.2f}")
        df_display['probability_profit'] = df_display['probability_profit'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "symbol": "Symbol",
                "spread_type": "Type",
                "short_strike": "Short Strike",
                "long_strike": "Long Strike",
                "contracts": "Contracts",
                "credit_received": "Credit",
                "max_loss": "Max Loss",
                "probability_profit": "Prob Profit",
                "confidence_score": "Confidence",
                "entry_time": "Entry Time"
            }
        )
    
    def render_market_overview(self, market_snapshots: List[Dict[str, Any]]):
        """Render market overview"""
        if not market_snapshots:
            st.info("No recent market data available.")
            return
        
        # Get latest snapshot for each symbol
        df = pd.DataFrame(market_snapshots)
        latest_data = df.groupby('symbol').first().reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Price changes
            fig = px.bar(
                latest_data,
                x='symbol',
                y='percent_change',
                title='Current Day Price Changes',
                color='percent_change',
                color_continuous_scale=['red', 'white', 'green']
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # IV Rank
            fig = px.bar(
                latest_data,
                x='symbol',
                y='iv_rank',
                title='Implied Volatility Rank',
                color='iv_rank',
                color_continuous_scale='Blues'
            )
            fig.add_hline(y=70, line_dash="dash", line_color="red", 
                         annotation_text="Min IV Rank (70)")
            st.plotly_chart(fig, use_container_width=True)
    
    def render_trade_history(self, recent_trades: List[Dict[str, Any]]):
        """Render recent trade history"""
        if not recent_trades:
            st.info("No closed trades available.")
            return
        
        df = pd.DataFrame(recent_trades)
        
        # Format for display
        display_cols = [
            'symbol', 'spread_type', 'contracts', 'credit_received', 
            'realized_pnl', 'entry_time', 'exit_time'
        ]
        
        df_display = df[display_cols].copy()
        df_display['entry_time'] = pd.to_datetime(df_display['entry_time']).dt.strftime('%m-%d %H:%M')
        df_display['exit_time'] = pd.to_datetime(df_display['exit_time']).dt.strftime('%m-%d %H:%M')
        df_display['credit_received'] = df_display['credit_received'].apply(lambda x: f"${x:.2f}")
        df_display['realized_pnl'] = df_display['realized_pnl'].apply(lambda x: f"${x:.2f}")
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "symbol": "Symbol",
                "spread_type": "Type",
                "contracts": "Contracts",
                "credit_received": "Credit",
                "realized_pnl": "P&L",
                "entry_time": "Entry",
                "exit_time": "Exit"
            }
        )
    
    def render_alerts(self, alerts: List[Dict[str, Any]]):
        """Render recent alerts"""
        if not alerts:
            st.info("No recent alerts.")
            return
        
        for alert in alerts[:5]:  # Show latest 5 alerts
            alert_time = alert['created_at'].strftime('%Y-%m-%d %H:%M')
            
            if alert['alert_type'] == 'trade_executed':
                st.success(f"🚀 {alert_time}: {alert['message']}")
            elif alert['alert_type'] == 'profit_target':
                st.success(f"💰 {alert_time}: {alert['message']}")
            elif alert['alert_type'] == 'stop_loss':
                st.error(f"⚠️ {alert_time}: {alert['message']}")
            else:
                st.info(f"ℹ️ {alert_time}: {alert['message']}")

def main():
    st.title("📈 Volatility Trading Bot Dashboard")
    st.markdown("---")
    
    dashboard = TradingBotDashboard()
    
    # Sidebar
    st.sidebar.title("Navigation")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=True)
    
    if auto_refresh:
        # Auto refresh every 30 seconds
        import time
        time.sleep(30)
        st.experimental_rerun()
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.experimental_rerun()
    
    # Time filter
    time_filter = st.sidebar.selectbox(
        "Time Period",
        ["Last 7 days", "Last 30 days", "Last 90 days"],
        index=1
    )
    
    # Load data
    try:
        with st.spinner("Loading dashboard data..."):
            data = asyncio.run(dashboard.get_dashboard_data())
        
        # Performance Overview
        st.header("📊 Performance Overview")
        dashboard.render_performance_metrics(data['performance'])
        
        st.markdown("---")
        
        # Charts section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📈 P&L Performance")
            dashboard.render_pnl_chart(data['daily_performance'])
        
        with col2:
            st.subheader("🚨 Recent Alerts")
            dashboard.render_alerts(data['alerts'])
        
        st.markdown("---")
        
        # Market Overview
        st.header("🌍 Market Overview")
        dashboard.render_market_overview(data['market_snapshots'])
        
        st.markdown("---")
        
        # Trades section
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔴 Open Trades")
            dashboard.render_open_trades(data['open_trades'])
        
        with col2:
            st.subheader("📋 Recent Trade History")
            dashboard.render_trade_history(data['recent_trades'])
        
        # Footer
        st.markdown("---")
        st.markdown(
            f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Open Trades: {len(data['open_trades'])} | "
            f"Total Trades (30d): {data['performance'].get('total_trades', 0)}*"
        )
        
    except Exception as e:
        st.error(f"Error loading dashboard data: {e}")
        st.info("Make sure the database is running and accessible.")

if __name__ == "__main__":
    main()