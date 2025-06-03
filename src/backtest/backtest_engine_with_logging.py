"""
Enhanced backtesting engine with activity logging
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
import logging
from decimal import Decimal
import time
import json
import os

from src.core.trade_manager import EnhancedTradeManager, TradeManagementRules, OptionContract
from anthropic import AsyncAnthropic
from src.backtest.realistic_iv_simulator import RealisticIVSimulator
from src.backtest.tastytrade_api import TastyTradeDataFetcher

logger = logging.getLogger(__name__)

@dataclass
class ActivityLogEntry:
    """Single activity log entry"""
    timestamp: datetime
    type: str  # 'info', 'trade', 'warning', 'error'
    message: str
    details: Optional[Dict] = None

class BacktestEngineWithLogging:
    """Backtesting engine with activity logging"""
    
    def __init__(self, config, activity_callback=None, progress_callback=None):
        self.config = config
        self.trade_manager = EnhancedTradeManager(paper_trading=True)
        self.anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.current_capital = config.initial_capital
        self.open_positions = {}
        self.results = None  # Will be initialized as BacktestResults
        
        # Import here to avoid circular import
        from src.backtest.backtest_engine import BacktestResults, BacktestTrade
        self.BacktestResults = BacktestResults
        self.BacktestTrade = BacktestTrade
        
        self.results = BacktestResults()
        self.results.equity_curve.append(self.current_capital)
        
        # Rate limiting
        self.last_api_calls = []
        self.max_api_calls_per_minute = 4
        self.api_call_window = 60
        
        # Callbacks
        self.activity_callback = activity_callback
        self.progress_callback = progress_callback
        
        # Activity log
        self.activity_log = []
        
        # Progress tracking
        self.total_days = 0
        self.current_day = 0
        
        # IV simulator and TastyTrade fetcher
        self.iv_simulator = RealisticIVSimulator()
        self.tastytrade_fetcher = None  # Initialize on first use
        
        # Check if TastyTrade credentials are available
        if os.getenv('TASTYTRADE_USERNAME') and os.getenv('TASTYTRADE_PASSWORD'):
            self.use_tastytrade = True
            self.log_activity("info", "TastyTrade credentials found - will use real IV data")
        else:
            self.use_tastytrade = False
            self.log_activity("info", "No TastyTrade credentials - using simulated IV data")
        
    def log_activity(self, type: str, message: str, details: Optional[Dict] = None):
        """Log an activity"""
        entry = ActivityLogEntry(
            timestamp=datetime.now(),
            type=type,
            message=message,
            details=details
        )
        self.activity_log.append(entry)
        
        # Call callback if provided
        if self.activity_callback:
            self.activity_callback(entry)
            
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
            
    async def run_backtest(self):
        """Run complete backtest with logging"""
        self.log_activity("info", f"Starting backtest from {self.config.start_date.strftime('%Y-%m-%d')} to {self.config.end_date.strftime('%Y-%m-%d')}")
        self.log_activity("info", f"Symbols: {', '.join(self.config.symbols)}")
        self.log_activity("info", f"Initial capital: ${self.config.initial_capital:,.2f}")
        
        # Calculate total trading days
        current_date = self.config.start_date
        while current_date <= self.config.end_date:
            if current_date.weekday() < 5:
                self.total_days += 1
            current_date += timedelta(days=1)
            
        self.log_activity("info", f"Total trading days to process: {self.total_days}")
        
        # Process each day
        current_date = self.config.start_date
        self.current_day = 0
        
        while current_date <= self.config.end_date:
            if current_date.weekday() < 5:
                self.current_day += 1
                self.update_progress(
                    self.current_day, 
                    self.total_days, 
                    f"Processing {current_date.strftime('%Y-%m-%d')}"
                )
                
                await self._process_trading_day(current_date)
                
            current_date += timedelta(days=1)
            
        # Close remaining positions
        self.log_activity("info", "Closing all remaining positions at end of backtest")
        await self._close_all_positions(self.config.end_date)
        
        # Calculate metrics
        self._calculate_metrics()
        
        self.log_activity("info", f"Backtest completed! Total P&L: ${self.results.total_pnl:,.2f}")
        self.update_progress(self.total_days, self.total_days, "Backtest completed!")
        
        return self.results
        
    async def _process_trading_day(self, date: datetime):
        """Process a single trading day"""
        # Scan for opportunities
        for symbol in self.config.symbols:
            market_data = await self._get_historical_data(symbol, date)
            if market_data:
                signal = await self._analyze_opportunity(symbol, market_data, date)
                if signal:
                    await self._execute_trade(signal, date)
                    
        # Manage existing positions
        await self._manage_positions(date)
        
        # Update equity curve
        total_value = self._calculate_portfolio_value(date)
        self.results.equity_curve.append(total_value)
        
        # Calculate daily return
        if len(self.results.equity_curve) > 1:
            daily_return = (self.results.equity_curve[-1] - self.results.equity_curve[-2]) / self.results.equity_curve[-2]
            self.results.daily_returns.append(daily_return)
            
    async def _get_historical_data(self, symbol: str, date: datetime) -> Optional[Dict]:
        """Get historical market data from Alpaca"""
        from src.backtest.data_fetcher import AlpacaDataFetcher
        
        if not hasattr(self, 'data_fetcher'):
            self.data_fetcher = AlpacaDataFetcher()
            self.log_activity("info", f"Initialized Alpaca data fetcher (real data from {self.data_fetcher.OPTIONS_DATA_START_DATE.date()} onwards)")
        
        # Get real stock data - need wider range for volatility calculation
        start_date = date - timedelta(days=30)  # Need historical data for volatility
        end_date = date + timedelta(days=1)
        
        try:
            df = await self.data_fetcher.get_stock_data(symbol, start_date, end_date)
            
            if df.empty:
                return None
            
            # Always reset index since Alpaca returns MultiIndex
            df_reset = df.reset_index()
            
            # Filter for our symbol if multi-index includes symbol
            if 'symbol' in df_reset.columns:
                df_symbol = df_reset[df_reset['symbol'] == symbol]
            else:
                df_symbol = df_reset
            
            # Convert timestamp to date for filtering
            df_symbol = df_symbol.copy()
            df_symbol['date'] = pd.to_datetime(df_symbol['timestamp']).dt.date
            day_data = df_symbol[df_symbol['date'] == date.date()]
            
            if day_data.empty:
                return None
                
            day_data = day_data.iloc[0]
            
            # Calculate metrics
            percent_change = day_data['percent_change']
            
            # Try to get real IV rank from TastyTrade first
            iv_rank = None
            
            if self.use_tastytrade:
                try:
                    if not self.tastytrade_fetcher:
                        self.tastytrade_fetcher = TastyTradeDataFetcher()
                    
                    # Get real IV rank
                    real_iv_rank = await self.tastytrade_fetcher.get_iv_rank(symbol, date)
                    
                    if real_iv_rank is not None:
                        iv_rank = real_iv_rank
                        self.log_activity("info", f"Using real IV rank from TastyTrade: {iv_rank:.1f}")
                except Exception as e:
                    self.log_activity("warning", f"TastyTrade API error: {str(e)}")
            
            # Fall back to simulation if needed
            if iv_rank is None:
                # Get volume ratio for IV calculation
                avg_volume = df_reset['volume'].rolling(20).mean().iloc[-1] if len(df_reset) > 20 else day_data['volume']
                volume_ratio = day_data['volume'] / avg_volume if avg_volume > 0 else 1.0
                
                # Use realistic IV simulator
                iv_sim = self.iv_simulator.calculate_iv_rank(
                    symbol=symbol,
                    date=date,
                    price_move=percent_change,
                    volume_ratio=volume_ratio
                )
                iv_rank = iv_sim['iv_rank']
            
            self.log_activity("info", f"Real data: {symbol} moved {percent_change:.2f}% on {date.date()}, IV Rank: {iv_rank:.1f}")
            
            # Check if it's a significant move
            if abs(percent_change) < self.config.min_price_move:
                return None
            
            # It's a volatility spike!
            self.log_activity("info", f"Volatility spike detected in {symbol}: {percent_change:.2f}%")
            
            return {
                'symbol': symbol,
                'date': date,
                'current_price': float(day_data['close']),
                'percent_change': percent_change,
                'volume': int(day_data['volume']),
                'iv_rank': iv_rank,
                'iv_percentile': iv_rank + 5  # Simple estimate
            }
            
        except Exception as e:
            self.log_activity("warning", f"Error fetching real data for {symbol} on {date.date()}: {str(e)}")
            # Add debug info
            import traceback
            self.log_activity("warning", f"Traceback: {traceback.format_exc()}")
            return None
        
    async def _wait_for_rate_limit(self):
        """Wait if necessary to avoid hitting rate limits"""
        current_time = time.time()
        
        # Remove old API calls
        self.last_api_calls = [t for t in self.last_api_calls 
                              if current_time - t < self.api_call_window]
        
        # Check if we need to wait
        if len(self.last_api_calls) >= self.max_api_calls_per_minute:
            wait_time = self.api_call_window - (current_time - self.last_api_calls[0]) + 1
            if wait_time > 0:
                self.log_activity("warning", f"Rate limit reached, waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                
                # Clean up old calls after waiting
                current_time = time.time()
                self.last_api_calls = [t for t in self.last_api_calls 
                                      if current_time - t < self.api_call_window]
        
        # Record this API call
        self.last_api_calls.append(current_time)
        
    async def _analyze_opportunity(self, symbol: str, market_data: Dict, date: datetime) -> Optional[Dict]:
        """Analyze if conditions are met for a trade"""
        if abs(market_data['percent_change']) < self.config.min_price_move:
            return None
            
        if market_data['iv_rank'] < self.config.min_iv_rank:
            return None
            
        # Use Claude for analysis
        self.log_activity("info", f"Sending {symbol} to Claude AI for analysis...")
        analysis = await self._claude_analysis(market_data)
        
        if analysis and analysis['confidence'] >= self.config.confidence_threshold:
            self.log_activity("info", f"Claude recommends: {analysis['spread_type']} spread for {symbol}")
            return {
                'symbol': symbol,
                'date': date,
                'market_data': market_data,
                'analysis': analysis
            }
            
        return None
        
    async def _claude_analysis(self, market_data: Dict) -> Optional[Dict]:
        """Get Claude's analysis"""
        await self._wait_for_rate_limit()
        
        prompt = f"""
        Analyze this volatility spike for a credit spread opportunity:
        
        Symbol: {market_data['symbol']}
        Current Price: ${market_data['current_price']:.2f}
        Today's Move: {market_data['percent_change']:.2f}%
        Volume: {market_data['volume']:,}
        IV Rank: {market_data['iv_rank']:.1f}
        IV Percentile: {market_data['iv_percentile']:.1f}
        
        Account Balance: ${self.current_capital:.2f}
        Max Risk per Trade: {self.config.max_risk_per_trade * 100}%
        
        Strategy Rules:
        1. If big move DOWN: Sell CALL credit spread above resistance
        2. If big move UP: Sell PUT credit spread below support
        3. Target 1.5-2 standard deviations from current price
        4. Use 14-30 DTE for best theta decay
        5. Position size based on max ${self.current_capital * self.config.max_risk_per_trade:.0f} risk
        
        IMPORTANT POSITION SIZING:
        - Max risk allowed: ${self.current_capital * self.config.max_risk_per_trade:.0f}
        - For a $5 wide spread: Max loss = $500 per contract
        - Therefore: Maximum contracts = {int(self.current_capital * self.config.max_risk_per_trade / 500)}
        - Always use 1-2 contracts maximum to stay within risk limits
        
        Provide analysis in JSON format:
        {{
            "should_trade": true/false,
            "spread_type": "call_credit" or "put_credit",
            "short_strike": price,
            "long_strike": price,
            "expiration_days": number,
            "contracts": number,
            "expected_credit": amount per contract,
            "probability_profit": percentage,
            "confidence": 0-100,
            "reasoning": "explanation"
        }}
        """
        
        try:
            response = await self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                if analysis.get('should_trade'):
                    return analysis
                    
        except Exception as e:
            self.log_activity("error", f"Claude analysis error: {str(e)}")
            
        return None
        
    async def _execute_trade(self, signal: Dict, date: datetime):
        """Execute a backtest trade"""
        analysis = signal['analysis']
        symbol = signal['symbol']
        
        # Calculate trade details
        spread_width = abs(analysis['long_strike'] - analysis['short_strike'])
        credit_per_contract = analysis['expected_credit']
        suggested_contracts = analysis['contracts']
        
        # Calculate max loss per contract
        max_loss_per_contract = (spread_width - credit_per_contract) * 100
        
        # Calculate maximum contracts we can afford based on risk
        max_risk_dollars = self.current_capital * self.config.max_risk_per_trade
        max_contracts = int(max_risk_dollars / max_loss_per_contract) if max_loss_per_contract > 0 else 0
        
        # Use the lesser of suggested contracts or max affordable
        contracts = min(suggested_contracts, max_contracts)
        
        if contracts == 0:
            self.log_activity("warning", f"Trade rejected: Cannot afford even 1 contract within risk limit")
            return
            
        # Recalculate with actual contracts
        total_credit = credit_per_contract * contracts * 100
        max_loss = max_loss_per_contract * contracts
        
        # Double check
        if max_loss > max_risk_dollars:
            self.log_activity("warning", f"Trade rejected: Max loss ${max_loss:.2f} exceeds risk limit ${max_risk_dollars:.2f}")
            return
            
        self.log_activity("info", f"Position sized to {contracts} contracts (max loss: ${max_loss:.2f})")
            
        # Create trade
        trade = self.BacktestTrade(
            entry_time=date,
            symbol=symbol,
            spread_type=analysis['spread_type'],
            short_strike=analysis['short_strike'],
            long_strike=analysis['long_strike'],
            contracts=contracts,
            entry_credit=total_credit,
            max_profit=total_credit,
            max_loss=max_loss
        )
        
        # Store trade
        trade_id = f"{symbol}_{date.strftime('%Y%m%d_%H%M%S')}"
        self.open_positions[trade_id] = trade
        
        self.log_activity("trade", 
            f"OPENED: {symbol} {analysis['spread_type']} {analysis['short_strike']}/{analysis['long_strike']} "
            f"x{contracts} for ${total_credit:.2f} credit",
            {"trade_id": trade_id, "max_loss": max_loss}
        )
        
    async def _manage_positions(self, current_date: datetime):
        """Manage open positions"""
        positions_to_close = []
        
        for trade_id, trade in self.open_positions.items():
            days_in_trade = (current_date - trade.entry_time).days
            
            # Simulate P&L
            time_decay_pct = min(days_in_trade / 30, 0.8)
            market_impact = np.random.normal(0, 0.1)
            
            if trade.spread_type == 'call_credit':
                directional_impact = -market_impact if market_impact < 0 else market_impact * 0.5
            else:
                directional_impact = -market_impact if market_impact > 0 else market_impact * 0.5
                
            pnl_pct = time_decay_pct + directional_impact
            current_pnl = trade.entry_credit * pnl_pct
            
            # Check exit conditions
            exit_reason = None
            
            if current_pnl >= trade.entry_credit * 0.35:  # Take profit at 35% of credit
                exit_reason = "Profit Target"
            elif current_pnl <= -trade.entry_credit * 0.75:  # Stop loss at 75% of credit
                exit_reason = "Stop Loss"
                current_pnl = -trade.entry_credit * 0.75
            elif days_in_trade >= 21:  # Close at 21 DTE
                exit_reason = "Time Stop"
                
            if exit_reason:
                trade.exit_time = current_date
                trade.exit_reason = exit_reason
                trade.realized_pnl = current_pnl - (self.config.commission_per_contract * trade.contracts * 2)
                trade.days_in_trade = days_in_trade
                
                # Ensure we have all required attributes
                if not hasattr(trade, 'spread_type'):
                    trade.spread_type = 'credit_spread'
                positions_to_close.append(trade_id)
                
                self.log_activity("trade",
                    f"CLOSED: {trade.symbol} {trade.spread_type} - {exit_reason} - P&L: ${trade.realized_pnl:.2f}",
                    {"trade_id": trade_id, "days_in_trade": days_in_trade}
                )
                
        # Close positions
        for trade_id in positions_to_close:
            trade = self.open_positions.pop(trade_id)
            self.results.trades.append(trade)
            self.current_capital += trade.realized_pnl
            
            # Update results
            self.results.total_trades += 1
            if trade.realized_pnl > 0:
                self.results.winning_trades += 1
                self.results.gross_profit += trade.realized_pnl
            else:
                self.results.losing_trades += 1
                self.results.gross_loss += abs(trade.realized_pnl)
                
    async def _close_all_positions(self, date: datetime):
        """Close all remaining positions"""
        for trade_id, trade in list(self.open_positions.items()):
            trade.exit_time = date
            trade.exit_reason = "Backtest End"
            trade.days_in_trade = (date - trade.entry_time).days
            # Assume we can close at 50% of credit for positions still open
            trade.realized_pnl = trade.entry_credit * 0.5 - (self.config.commission_per_contract * trade.contracts * 2)
            
            self.log_activity("trade",
                f"CLOSED: {trade.symbol} {trade.spread_type} - Backtest End - P&L: ${trade.realized_pnl:.2f}",
                {"trade_id": trade_id, "days_in_trade": trade.days_in_trade}
            )
            
            self.results.trades.append(trade)
            self.current_capital += trade.realized_pnl
            
            # Update results metrics
            self.results.total_trades += 1
            if trade.realized_pnl > 0:
                self.results.winning_trades += 1
                self.results.gross_profit += trade.realized_pnl
            else:
                self.results.losing_trades += 1
                self.results.gross_loss += abs(trade.realized_pnl)
            
        self.open_positions.clear()
        
    def _calculate_portfolio_value(self, date: datetime) -> float:
        """Calculate total portfolio value"""
        total_value = self.current_capital
        
        for trade in self.open_positions.values():
            days_in_trade = (date - trade.entry_time).days
            time_decay_pct = min(days_in_trade / 30, 0.8)
            unrealized_pnl = trade.entry_credit * time_decay_pct * 0.5
            total_value += unrealized_pnl
            
        return total_value
        
    def _calculate_metrics(self):
        """Calculate final metrics"""
        if not self.results.trades:
            return
            
        # Basic metrics
        self.results.total_pnl = sum(t.realized_pnl for t in self.results.trades)
        self.results.win_rate = (self.results.winning_trades / self.results.total_trades * 100) if self.results.total_trades > 0 else 0
        
        # Average win/loss
        winning_trades = [t for t in self.results.trades if t.realized_pnl > 0]
        losing_trades = [t for t in self.results.trades if t.realized_pnl <= 0]
        
        self.results.avg_win = np.mean([t.realized_pnl for t in winning_trades]) if winning_trades else 0
        self.results.avg_loss = np.mean([t.realized_pnl for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        if self.results.gross_loss > 0:
            self.results.profit_factor = self.results.gross_profit / self.results.gross_loss
        else:
            self.results.profit_factor = float('inf') if self.results.gross_profit > 0 else 0
            
        # Average days in trade
        self.results.avg_days_in_trade = np.mean([t.days_in_trade for t in self.results.trades])
        
        # Calculate drawdown
        peak = self.config.initial_capital
        max_dd = 0
        max_dd_pct = 0
        
        for value in self.results.equity_curve:
            if value > peak:
                peak = value
            dd = peak - value
            dd_pct = dd / peak * 100
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
                
        self.results.max_drawdown = max_dd
        self.results.max_drawdown_pct = max_dd_pct
        
        # Sharpe ratio
        if self.results.daily_returns:
            returns_array = np.array(self.results.daily_returns)
            if len(returns_array) > 1 and returns_array.std() > 0:
                self.results.sharpe_ratio = (returns_array.mean() / returns_array.std()) * np.sqrt(252)
            else:
                self.results.sharpe_ratio = 0