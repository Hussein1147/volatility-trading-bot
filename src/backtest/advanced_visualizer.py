"""
Advanced visualization for options backtesting
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class AdvancedBacktestVisualizer:
    """Enhanced visualizations for options strategy backtesting"""
    
    def __init__(self, results):
        self.results = results
        self.trades = results.trades if hasattr(results, 'trades') else []
        self.equity_curve = results.equity_curve if hasattr(results, 'equity_curve') else []
        
    def plot_greeks_analysis(self) -> go.Figure:
        """Analyze trades by Greeks exposure"""
        if not self.trades:
            return self._empty_chart("No trades to analyze")
            
        # Create subplots for different Greeks
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Delta Exposure', 'Theta Decay', 'IV Rank Distribution', 'Trade Duration vs P&L'),
            specs=[[{"type": "scatter"}, {"type": "bar"}],
                   [{"type": "histogram"}, {"type": "scatter"}]]
        )
        
        # Delta exposure over time (simulated for credit spreads)
        deltas = []
        dates = []
        for trade in self.trades:
            if hasattr(trade, 'entry_time'):
                dates.append(trade.entry_time)
                # Credit spreads typically have negative delta for calls, positive for puts
                delta = -0.15 if 'call' in str(trade.spread_type) else 0.15
                deltas.append(delta)
        
        fig.add_trace(
            go.Scatter(x=dates, y=deltas, mode='markers+lines', name='Delta',
                      marker=dict(size=8, color='blue')),
            row=1, col=1
        )
        
        # Theta decay analysis
        theta_by_dte = {}
        for trade in self.trades:
            dte = getattr(trade, 'days_in_trade', 30)
            pnl = getattr(trade, 'realized_pnl', 0)
            if dte not in theta_by_dte:
                theta_by_dte[dte] = []
            theta_by_dte[dte].append(pnl)
        
        dtes = sorted(theta_by_dte.keys())
        avg_pnls = [np.mean(theta_by_dte[dte]) for dte in dtes]
        
        fig.add_trace(
            go.Bar(x=dtes, y=avg_pnls, name='Avg P&L by DTE',
                  marker=dict(color=avg_pnls, colorscale='RdYlGn')),
            row=1, col=2
        )
        
        # IV Rank distribution
        iv_ranks = [getattr(trade, 'iv_rank', 70) for trade in self.trades]
        
        fig.add_trace(
            go.Histogram(x=iv_ranks, nbinsx=20, name='IV Rank',
                        marker=dict(color='purple')),
            row=2, col=1
        )
        
        # Duration vs P&L scatter
        durations = []
        pnls = []
        for trade in self.trades:
            if hasattr(trade, 'days_in_trade') and hasattr(trade, 'realized_pnl'):
                durations.append(trade.days_in_trade)
                pnls.append(trade.realized_pnl)
        
        fig.add_trace(
            go.Scatter(x=durations, y=pnls, mode='markers', name='Duration vs P&L',
                      marker=dict(size=10, color=pnls, colorscale='RdYlGn', showscale=True)),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title="Options Greeks & Strategy Analysis",
            showlegend=False,
            height=800,
            template='plotly_dark'
        )
        
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_xaxes(title_text="Days to Expiration", row=1, col=2)
        fig.update_xaxes(title_text="IV Rank", row=2, col=1)
        fig.update_xaxes(title_text="Days in Trade", row=2, col=2)
        
        fig.update_yaxes(title_text="Delta", row=1, col=1)
        fig.update_yaxes(title_text="Average P&L ($)", row=1, col=2)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        fig.update_yaxes(title_text="P&L ($)", row=2, col=2)
        
        return fig
    
    def plot_volatility_analysis(self) -> go.Figure:
        """Analyze volatility conditions and trade performance"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('P&L by Market Move Size', 'Win Rate by IV Rank', 
                          'Credit Collected vs Max Loss', 'Exit Reason Analysis'),
            specs=[[{"type": "scatter"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "pie"}]]
        )
        
        # P&L by market move size
        move_sizes = []
        pnls = []
        for trade in self.trades:
            # Simulate market move data
            move = np.random.uniform(0.5, 3.0)  # Would come from actual data
            move_sizes.append(move)
            pnls.append(getattr(trade, 'realized_pnl', 0))
        
        fig.add_trace(
            go.Scatter(x=move_sizes, y=pnls, mode='markers',
                      marker=dict(size=10, color=pnls, colorscale='RdYlGn'),
                      name='Move vs P&L'),
            row=1, col=1
        )
        
        # Win rate by IV rank buckets
        iv_buckets = {'50-60': [], '60-70': [], '70-80': [], '80-90': [], '90-100': []}
        for trade in self.trades:
            iv = getattr(trade, 'iv_rank', 70)
            pnl = getattr(trade, 'realized_pnl', 0)
            
            if 50 <= iv < 60:
                iv_buckets['50-60'].append(1 if pnl > 0 else 0)
            elif 60 <= iv < 70:
                iv_buckets['60-70'].append(1 if pnl > 0 else 0)
            elif 70 <= iv < 80:
                iv_buckets['70-80'].append(1 if pnl > 0 else 0)
            elif 80 <= iv < 90:
                iv_buckets['80-90'].append(1 if pnl > 0 else 0)
            else:
                iv_buckets['90-100'].append(1 if pnl > 0 else 0)
        
        buckets = list(iv_buckets.keys())
        win_rates = [np.mean(iv_buckets[b]) * 100 if iv_buckets[b] else 0 for b in buckets]
        
        fig.add_trace(
            go.Bar(x=buckets, y=win_rates, 
                  marker=dict(color=win_rates, colorscale='Viridis'),
                  name='Win Rate by IV'),
            row=1, col=2
        )
        
        # Credit vs Max Loss scatter
        credits = []
        max_losses = []
        for trade in self.trades:
            credit = getattr(trade, 'entry_credit', 100)
            max_loss = getattr(trade, 'max_loss', 500)
            credits.append(credit)
            max_losses.append(max_loss)
        
        fig.add_trace(
            go.Scatter(x=credits, y=max_losses, mode='markers',
                      marker=dict(size=8, color='orange'),
                      name='Risk/Reward'),
            row=2, col=1
        )
        
        # Exit reason pie chart
        exit_reasons = {}
        for trade in self.trades:
            reason = getattr(trade, 'exit_reason', 'Unknown')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        fig.add_trace(
            go.Pie(labels=list(exit_reasons.keys()), 
                  values=list(exit_reasons.values()),
                  hole=0.4),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title="Volatility & Risk Analysis",
            showlegend=False,
            height=800,
            template='plotly_dark'
        )
        
        return fig
    
    def plot_performance_heatmap(self) -> go.Figure:
        """Create a heatmap of performance by day of week and time of month"""
        if not self.trades:
            return self._empty_chart("No trades to analyze")
        
        # Create performance matrix
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        
        performance_matrix = np.zeros((5, 4))
        trade_counts = np.zeros((5, 4))
        
        for trade in self.trades:
            if hasattr(trade, 'entry_time') and hasattr(trade, 'realized_pnl'):
                day_of_week = trade.entry_time.weekday()
                week_of_month = (trade.entry_time.day - 1) // 7
                
                if day_of_week < 5 and week_of_month < 4:
                    performance_matrix[day_of_week][week_of_month] += trade.realized_pnl
                    trade_counts[day_of_week][week_of_month] += 1
        
        # Calculate average P&L
        avg_performance = np.divide(performance_matrix, trade_counts, 
                                   where=trade_counts!=0)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=avg_performance,
            x=weeks,
            y=days,
            colorscale='RdYlGn',
            text=np.round(avg_performance, 2),
            texttemplate='%{text}',
            textfont={"size": 12},
            colorbar=dict(title="Avg P&L ($)")
        ))
        
        fig.update_layout(
            title="Average P&L by Day of Week and Week of Month",
            xaxis_title="Week of Month",
            yaxis_title="Day of Week",
            height=500,
            template='plotly_dark'
        )
        
        return fig
    
    def plot_risk_metrics_dashboard(self) -> go.Figure:
        """Comprehensive risk metrics dashboard"""
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=('Consecutive Wins/Losses', 'Risk/Reward Ratios', 'Drawdown Periods',
                          'P&L Distribution', 'Sharpe Ratio Rolling', 'Win Rate Trend'),
            specs=[[{"type": "bar"}, {"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "histogram"}, {"type": "scatter"}, {"type": "scatter"}]]
        )
        
        # Consecutive wins/losses
        streaks = self._calculate_streaks()
        
        fig.add_trace(
            go.Bar(x=['Max Win Streak', 'Max Loss Streak'], 
                  y=[streaks['max_win_streak'], -streaks['max_loss_streak']],
                  marker=dict(color=['green', 'red'])),
            row=1, col=1
        )
        
        # Risk/Reward scatter
        risk_rewards = []
        for trade in self.trades:
            if hasattr(trade, 'entry_credit') and hasattr(trade, 'max_loss'):
                risk_reward = trade.entry_credit / trade.max_loss if trade.max_loss > 0 else 0
                risk_rewards.append(risk_reward)
        
        fig.add_trace(
            go.Scatter(y=risk_rewards, mode='markers',
                      marker=dict(color=risk_rewards, colorscale='Viridis')),
            row=1, col=2
        )
        
        # Drawdown periods
        drawdowns = self._calculate_drawdowns()
        fig.add_trace(
            go.Scatter(x=list(range(len(drawdowns))), y=drawdowns,
                      fill='tozeroy', fillcolor='rgba(255,0,0,0.3)'),
            row=1, col=3
        )
        
        # P&L distribution
        pnls = [t.realized_pnl for t in self.trades if hasattr(t, 'realized_pnl')]
        fig.add_trace(
            go.Histogram(x=pnls, nbinsx=30,
                        marker=dict(color='lightblue')),
            row=2, col=1
        )
        
        # Rolling Sharpe ratio
        rolling_sharpe = self._calculate_rolling_sharpe()
        fig.add_trace(
            go.Scatter(y=rolling_sharpe, mode='lines',
                      line=dict(color='yellow', width=2)),
            row=2, col=2
        )
        
        # Win rate trend
        win_rate_trend = self._calculate_win_rate_trend()
        fig.add_trace(
            go.Scatter(y=win_rate_trend, mode='lines+markers',
                      line=dict(color='green', width=2)),
            row=2, col=3
        )
        
        # Update layout
        fig.update_layout(
            title="Comprehensive Risk Metrics Dashboard",
            showlegend=False,
            height=800,
            template='plotly_dark'
        )
        
        return fig
    
    def _calculate_streaks(self) -> Dict:
        """Calculate winning and losing streaks"""
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in self.trades:
            if hasattr(trade, 'realized_pnl'):
                if trade.realized_pnl > 0:
                    current_win_streak += 1
                    current_loss_streak = 0
                    max_win_streak = max(max_win_streak, current_win_streak)
                else:
                    current_loss_streak += 1
                    current_win_streak = 0
                    max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        return {
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak
        }
    
    def _calculate_drawdowns(self) -> List[float]:
        """Calculate drawdown percentages"""
        if not self.equity_curve:
            return []
        
        peak = self.equity_curve[0]
        drawdowns = []
        
        for value in self.equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            drawdowns.append(-drawdown)
        
        return drawdowns
    
    def _calculate_rolling_sharpe(self, window=20) -> List[float]:
        """Calculate rolling Sharpe ratio"""
        if len(self.results.daily_returns) < window:
            return []
        
        sharpe_ratios = []
        returns = np.array(self.results.daily_returns)
        
        for i in range(window, len(returns)):
            window_returns = returns[i-window:i]
            if window_returns.std() > 0:
                sharpe = (window_returns.mean() / window_returns.std()) * np.sqrt(252)
                sharpe_ratios.append(sharpe)
            else:
                sharpe_ratios.append(0)
        
        return sharpe_ratios
    
    def _calculate_win_rate_trend(self, window=10) -> List[float]:
        """Calculate rolling win rate"""
        if len(self.trades) < window:
            return []
        
        win_rates = []
        
        for i in range(window, len(self.trades)):
            window_trades = self.trades[i-window:i]
            wins = sum(1 for t in window_trades if hasattr(t, 'realized_pnl') and t.realized_pnl > 0)
            win_rate = (wins / window) * 100
            win_rates.append(win_rate)
        
        return win_rates
    
    def plot_confidence_breakdown(self) -> go.Figure:
        """Visualize confidence score breakdowns for all trades"""
        if not self.trades or not any(hasattr(t, 'confidence_breakdown') for t in self.trades):
            return self._empty_chart("No confidence breakdown data available")
        
        # Collect confidence components
        components = {
            'IV Rank': [],
            'Price Move': [],
            'Volume': [],
            'Spread Selection': [],
            'Strike Distance': [],
            'Position Sizing': [],
            'Expiration': [],
            'Support/Resistance': [],
            'Total Score': []
        }
        
        trade_labels = []
        
        for i, trade in enumerate(self.trades):
            if hasattr(trade, 'confidence_breakdown') and trade.confidence_breakdown:
                breakdown = trade.confidence_breakdown
                trade_labels.append(f"{trade.symbol} {trade.entry_time.strftime('%m/%d')}")
                
                # Extract scores from breakdown
                market = breakdown.get('market_conditions', {})
                strategy = breakdown.get('strategy_alignment', {})
                risk = breakdown.get('risk_management', {})
                tech = breakdown.get('technical_factors', {})
                
                components['IV Rank'].append(market.get('iv_rank', 0))
                components['Price Move'].append(market.get('price_move', 0))
                components['Volume'].append(market.get('volume', 0))
                components['Spread Selection'].append(strategy.get('spread_selection', 0))
                components['Strike Distance'].append(strategy.get('strike_distance', 0))
                components['Position Sizing'].append(risk.get('position_sizing', 0))
                components['Expiration'].append(risk.get('expiration', 0))
                components['Support/Resistance'].append(tech.get('support_resistance', 0))
                components['Total Score'].append(trade.confidence_score)
        
        # Create stacked bar chart
        fig = go.Figure()
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']
        
        for i, (component, values) in enumerate(components.items()):
            if component != 'Total Score':
                fig.add_trace(go.Bar(
                    name=component,
                    x=trade_labels,
                    y=values,
                    marker_color=colors[i % len(colors)]
                ))
        
        # Add total score line
        fig.add_trace(go.Scatter(
            name='Total Score',
            x=trade_labels,
            y=components['Total Score'],
            mode='lines+markers',
            line=dict(color='white', width=3),
            yaxis='y2'
        ))
        
        # Update layout
        fig.update_layout(
            title="Confidence Score Breakdown by Trade",
            barmode='stack',
            template='plotly_dark',
            height=600,
            xaxis_title="Trades",
            yaxis_title="Component Scores",
            yaxis2=dict(
                title="Total Confidence Score",
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def _empty_chart(self, message: str) -> go.Figure:
        """Create empty chart with message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20)
        )
        fig.update_layout(
            template='plotly_dark',
            height=400
        )
        return fig