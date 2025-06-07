"""
Visualization tools for backtesting results
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict
from src.backtest.backtest_engine import BacktestResults, BacktestTrade

class BacktestVisualizer:
    """Create visualizations for backtest results"""
    
    def __init__(self, results: BacktestResults):
        self.results = results
        
    def plot_equity_curve(self) -> go.Figure:
        """Plot the equity curve over time"""
        fig = go.Figure()
        
        # Add equity curve
        fig.add_trace(go.Scatter(
            x=list(range(len(self.results.equity_curve))),
            y=self.results.equity_curve,
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#2979FF', width=2)
        ))
        
        # Add initial capital line
        fig.add_hline(
            y=self.results.equity_curve[0],
            line_dash="dash",
            line_color="gray",
            annotation_text="Initial Capital"
        )
        
        # Highlight drawdown periods
        peak = self.results.equity_curve[0]
        drawdown_start = None
        
        for i, value in enumerate(self.results.equity_curve):
            if value > peak:
                if drawdown_start is not None:
                    # End of drawdown
                    fig.add_vrect(
                        x0=drawdown_start,
                        x1=i,
                        fillcolor="red",
                        opacity=0.1,
                        layer="below",
                        line_width=0
                    )
                    drawdown_start = None
                peak = value
            elif drawdown_start is None and value < peak * 0.98:  # 2% drawdown threshold
                drawdown_start = i
                
        fig.update_layout(
            title="Portfolio Equity Curve",
            xaxis_title="Trading Days",
            yaxis_title="Portfolio Value ($)",
            template="plotly_dark",
            hovermode='x unified',
            height=500
        )
        
        return fig
        
    def plot_returns_distribution(self) -> go.Figure:
        """Plot the distribution of trade returns"""
        if not self.results.trades:
            return go.Figure()
            
        returns = [(t.realized_pnl / t.entry_credit * 100) if t.entry_credit > 0 else 0 
                  for t in self.results.trades]
        
        fig = go.Figure()
        
        # Add histogram
        fig.add_trace(go.Histogram(
            x=returns,
            nbinsx=30,
            name='Trade Returns',
            marker_color='#2979FF',
            opacity=0.7
        ))
        
        # Add vertical lines for mean and median
        mean_return = np.mean(returns)
        median_return = np.median(returns)
        
        fig.add_vline(x=mean_return, line_dash="dash", line_color="green",
                     annotation_text=f"Mean: {mean_return:.1f}%")
        fig.add_vline(x=median_return, line_dash="dash", line_color="yellow",
                     annotation_text=f"Median: {median_return:.1f}%")
        fig.add_vline(x=0, line_color="red", annotation_text="Break Even")
        
        fig.update_layout(
            title="Distribution of Trade Returns",
            xaxis_title="Return (%)",
            yaxis_title="Frequency",
            template="plotly_dark",
            showlegend=False,
            height=400
        )
        
        return fig
        
    def plot_monthly_returns(self) -> go.Figure:
        """Plot monthly returns heatmap"""
        if not self.results.trades:
            return go.Figure()
            
        # Create monthly returns data
        monthly_pnl = {}
        for trade in self.results.trades:
            if trade.exit_time:
                month_key = trade.exit_time.strftime('%Y-%m')
                monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + trade.realized_pnl
                
        # Convert to DataFrame
        months = sorted(monthly_pnl.keys())
        if not months:
            return go.Figure()
            
        # Create matrix for heatmap
        years = sorted(set(m[:4] for m in months))
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        z_data = []
        for year in years:
            year_data = []
            for month_num in range(1, 13):
                month_key = f"{year}-{month_num:02d}"
                year_data.append(monthly_pnl.get(month_key, 0))
            z_data.append(year_data)
            
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=month_names,
            y=years,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f"${val:.0f}" for val in row] for row in z_data],
            texttemplate="%{text}",
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title="Monthly P&L Heatmap",
            xaxis_title="Month",
            yaxis_title="Year",
            template="plotly_dark",
            height=300
        )
        
        return fig
        
    def plot_win_loss_analysis(self) -> go.Figure:
        """Plot win/loss analysis"""
        if not self.results.trades:
            return go.Figure()
            
        # Separate wins and losses
        wins = [t for t in self.results.trades if t.realized_pnl > 0]
        losses = [t for t in self.results.trades if t.realized_pnl <= 0]
        
        # Create subplots
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Win/Loss Distribution', 'Average P&L by Exit Reason'),
            specs=[[{'type': 'pie'}, {'type': 'bar'}]]
        )
        
        # Pie chart
        fig.add_trace(
            go.Pie(
                labels=['Wins', 'Losses'],
                values=[len(wins), len(losses)],
                marker_colors=['#00C853', '#D50000'],
                textinfo='label+percent+value'
            ),
            row=1, col=1
        )
        
        # Bar chart by exit reason
        exit_reasons = {}
        for trade in self.results.trades:
            reason = trade.exit_reason
            if reason not in exit_reasons:
                exit_reasons[reason] = {'count': 0, 'total_pnl': 0}
            exit_reasons[reason]['count'] += 1
            exit_reasons[reason]['total_pnl'] += trade.realized_pnl
            
        reasons = list(exit_reasons.keys())
        avg_pnl = [exit_reasons[r]['total_pnl'] / exit_reasons[r]['count'] for r in reasons]
        counts = [exit_reasons[r]['count'] for r in reasons]
        
        fig.add_trace(
            go.Bar(
                x=reasons,
                y=avg_pnl,
                marker_color=['#00C853' if pnl > 0 else '#D50000' for pnl in avg_pnl],
                text=[f"${pnl:.0f}<br>({cnt} trades)" for pnl, cnt in zip(avg_pnl, counts)],
                textposition='auto'
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            template="plotly_dark",
            showlegend=False,
            height=400
        )
        
        # Add axes labels for the bar chart
        fig.update_xaxes(title_text="Exit Reason", row=1, col=2)
        fig.update_yaxes(title_text="Average P&L ($)", row=1, col=2)
        
        return fig
        
    def plot_trade_timeline(self) -> go.Figure:
        """Plot timeline of trades with P&L"""
        if not self.results.trades:
            return go.Figure()
            
        df_trades = pd.DataFrame([
            {
                'Entry': t.entry_time,
                'Exit': t.exit_time,
                'Symbol': t.symbol,
                'P&L': t.realized_pnl,
                'Type': t.spread_type
            }
            for t in self.results.trades if t.exit_time
        ])
        
        if df_trades.empty:
            return go.Figure()
            
        fig = go.Figure()
        
        # Add scatter plot of trades
        fig.add_trace(go.Scatter(
            x=df_trades['Exit'],
            y=df_trades['P&L'],
            mode='markers',
            marker=dict(
                size=10,
                color=df_trades['P&L'],
                colorscale='RdYlGn',
                cmid=0,
                showscale=True,
                colorbar=dict(title="P&L ($)")
            ),
            text=[f"{row['Symbol']}<br>{row['Type']}<br>${row['P&L']:.2f}" 
                  for _, row in df_trades.iterrows()],
            hovertemplate='%{text}<br>Exit: %{x}<extra></extra>'
        ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        # Add cumulative P&L line
        df_trades_sorted = df_trades.sort_values('Exit')
        df_trades_sorted['Cumulative P&L'] = df_trades_sorted['P&L'].cumsum()
        
        fig.add_trace(go.Scatter(
            x=df_trades_sorted['Exit'],
            y=df_trades_sorted['Cumulative P&L'],
            mode='lines',
            name='Cumulative P&L',
            line=dict(color='#FFB300', width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title="Trade Timeline and P&L",
            xaxis_title="Date",
            yaxis_title="Individual Trade P&L ($)",
            yaxis2=dict(
                title="Cumulative P&L ($)",
                overlaying='y',
                side='right'
            ),
            template="plotly_dark",
            hovermode='x unified',
            height=500
        )
        
        return fig
        
    def create_performance_summary(self) -> Dict[str, any]:
        """Create performance summary cards data"""
        return {
            'total_return': (self.results.equity_curve[-1] - self.results.equity_curve[0]) / self.results.equity_curve[0] * 100 if self.results.equity_curve else 0,
            'sharpe_ratio': self.results.sharpe_ratio,
            'max_drawdown': self.results.max_drawdown_pct,
            'win_rate': self.results.win_rate,
            'profit_factor': self.results.profit_factor,
            'total_trades': self.results.total_trades,
            'avg_win': self.results.avg_win,
            'avg_loss': self.results.avg_loss,
            'avg_days_in_trade': self.results.avg_days_in_trade,
            'best_trade': max([t.realized_pnl for t in self.results.trades]) if self.results.trades else 0,
            'worst_trade': min([t.realized_pnl for t in self.results.trades]) if self.results.trades else 0,
            'total_pnl': self.results.total_pnl
        }
    
    def get_trade_summary(self) -> pd.DataFrame:
        """Get trade summary as DataFrame"""
        if not self.results.trades:
            return pd.DataFrame()
        
        trades_data = []
        for trade in self.results.trades:
            trades_data.append({
                'Entry Time': trade.entry_time,
                'Exit Time': trade.exit_time,
                'Symbol': trade.symbol,
                'Type': trade.spread_type,
                'Short Strike': trade.short_strike,
                'Long Strike': trade.long_strike,
                'Contracts': trade.contracts,
                'Entry Credit': trade.entry_credit,
                'Exit Cost': trade.exit_cost,
                'P&L': trade.realized_pnl,
                'Days in Trade': trade.days_in_trade,
                'Exit Reason': trade.exit_reason
            })
        
        return pd.DataFrame(trades_data)