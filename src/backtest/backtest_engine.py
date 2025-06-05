"""
Comprehensive backtesting engine for volatility trading strategies
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging
from decimal import Decimal
import time

from src.core.trade_manager import EnhancedTradeManager, TradeManagementRules, OptionContract
from src.data.trade_db import trade_db
from anthropic import AsyncAnthropic
import os
import json
from src.backtest.backtest_progress import BacktestProgress
from src.backtest.data_fetcher import AlpacaDataFetcher
from src.core.position_sizer import DynamicPositionSizer
from src.core.strike_selector import DeltaStrikeSelector

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    start_date: datetime
    end_date: datetime
    symbols: List[str]
    initial_capital: float = 100000
    max_risk_per_trade: float = 0.02
    min_iv_rank: float = 40
    min_price_move: float = 1.5
    confidence_threshold: int = 70
    commission_per_contract: float = 0.65
    use_real_data: bool = True
    
@dataclass
class BacktestTrade:
    """Track individual backtest trades"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = ""
    spread_type: str = ""
    short_strike: float = 0
    long_strike: float = 0
    contracts: int = 0
    entry_credit: float = 0
    exit_cost: float = 0
    realized_pnl: float = 0
    max_profit: float = 0
    max_loss: float = 0
    exit_reason: str = ""
    days_in_trade: int = 0
    confidence_score: int = 0
    confidence_breakdown: Optional[Dict] = None
    
@dataclass
class BacktestResults:
    """Comprehensive backtest results"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0
    gross_profit: float = 0
    gross_loss: float = 0
    max_drawdown: float = 0
    max_drawdown_pct: float = 0
    sharpe_ratio: float = 0
    profit_factor: float = 0
    win_rate: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    avg_days_in_trade: float = 0
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)

class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, config: BacktestConfig, progress_callback=None):
        self.config = config
        self.trade_manager = EnhancedTradeManager(paper_trading=True)
        self.anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.current_capital = config.initial_capital
        self.open_positions: Dict[str, BacktestTrade] = {}
        self.results = BacktestResults()
        self.results.equity_curve.append(self.current_capital)
        self.progress_callback = progress_callback
        self.progress = BacktestProgress()
        
        # Initialize data fetcher for real historical data
        self.data_fetcher = AlpacaDataFetcher()
        
        # Initialize dynamic position sizer
        self.position_sizer = DynamicPositionSizer(self.current_capital)
        
        # Rate limiting for Claude API (5 requests per minute)
        self.last_api_calls = []
        self.max_api_calls_per_minute = 4  # Keep it under 5 to be safe
        self.api_call_window = 60  # seconds
        
    async def run_backtest(self) -> BacktestResults:
        """Run complete backtest"""
        logger.info(f"Starting backtest from {self.config.start_date} to {self.config.end_date}")
        logger.info(f"Symbols: {', '.join(self.config.symbols)}")
        logger.info(f"Initial capital: ${self.config.initial_capital:,.2f}")
        
        # Log data sources being used
        logger.info("Real data sources configured:")
        if hasattr(self.data_fetcher, 'tastytrade_fetcher') and self.data_fetcher.tastytrade_fetcher.api.username:
            logger.info("  ✓ TastyTrade: IV Rank data")
        if hasattr(self.data_fetcher, 'polygon_fetcher') and self.data_fetcher.polygon_fetcher.api_key:
            logger.info("  ✓ Polygon: Historical options data")
        if self.data_fetcher.has_options_access:
            logger.info("  ✓ Alpaca: Recent options data with Greeks")
        
        # Generate trading days
        current_date = self.config.start_date
        
        while current_date <= self.config.end_date:
            # Skip weekends
            if current_date.weekday() < 5:
                await self._process_trading_day(current_date)
                
            current_date += timedelta(days=1)
            
        # Close any remaining positions
        await self._close_all_positions(self.config.end_date)
        
        # Calculate final metrics
        self._calculate_metrics()
        
        return self.results
        
    async def _process_trading_day(self, date: datetime):
        """Process a single trading day"""
        # Morning scan for new opportunities
        for symbol in self.config.symbols:
            market_data = await self._get_historical_data(symbol, date)
            if market_data:
                signal = await self._analyze_opportunity(symbol, market_data, date)
                if signal:
                    await self._execute_trade(signal, date)
        
        # Check existing positions
        await self._manage_positions(date)
        
        # Update equity curve
        total_value = self._calculate_portfolio_value(date)
        self.results.equity_curve.append(total_value)
        
        # Calculate daily return
        if len(self.results.equity_curve) > 1:
            daily_return = (self.results.equity_curve[-1] - self.results.equity_curve[-2]) / self.results.equity_curve[-2]
            self.results.daily_returns.append(daily_return)
            
    async def _get_historical_data(self, symbol: str, date: datetime) -> Optional[Dict]:
        """Get historical market data for a symbol on a specific date"""
        try:
            # Get real stock data for the date range around this date
            start_date = date - timedelta(days=30)  # Get 30 days for technical indicators
            end_date = date + timedelta(days=1)
            
            df = await self.data_fetcher.get_stock_data(symbol, start_date, end_date)
            
            if df.empty:
                logger.warning(f"No stock data available for {symbol} on {date}")
                return None
                
            # Find the closest trading day to our target date
            df.index = pd.to_datetime(df.index)
            target_date = pd.to_datetime(date.date())
            
            # Get the closest date that's <= target_date
            available_dates = df.index[df.index <= target_date]
            if len(available_dates) == 0:
                return None
                
            closest_date = available_dates.max()
            day_data = df.loc[closest_date]
            
            # Check if this is a significant move worth trading
            percent_change = day_data['percent_change']
            volume = day_data['volume']
            
            # Only return data for significant moves (like volatility events)
            if abs(percent_change) >= self.config.min_price_move:
                # Get real volatility data including IV rank from TastyTrade
                vol_data = await self.data_fetcher.get_historical_volatility_data(
                    symbol, date, lookback_days=365
                )
                
                # Use real IV rank if available, otherwise use calculated value
                if vol_data and 'iv_rank' in vol_data:
                    iv_rank = vol_data['iv_rank']
                    logger.debug(f"Using real IV rank for {symbol}: {iv_rank:.1f}")
                else:
                    # Fallback calculation
                    realized_vol = day_data.get('realized_vol', 20)
                    iv_rank = min(max(realized_vol * 3, 50), 100)
                
                # Get technical indicators
                sma_20 = day_data.get('sma_20', day_data['close'])
                rsi_14 = day_data.get('rsi_14', 50.0)
                
                return {
                    'symbol': symbol,
                    'date': date,
                    'current_price': float(day_data['close']),
                    'percent_change': float(percent_change),
                    'volume': int(volume),
                    'iv_rank': float(iv_rank),
                    'iv_percentile': float(iv_rank + 5),
                    'high': float(day_data['high']),
                    'low': float(day_data['low']),
                    'open': float(day_data['open']),
                    'sma_20': float(sma_20),
                    'rsi_14': float(rsi_14)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} on {date}: {e}")
            return None
        
    async def _analyze_opportunity(self, symbol: str, market_data: Dict, date: datetime) -> Optional[Dict]:
        """Analyze if conditions are met for a trade"""
        if abs(market_data['percent_change']) < self.config.min_price_move:
            return None
            
        if market_data['iv_rank'] < self.config.min_iv_rank:
            return None
            
        # Update progress for analysis
        self.progress.message = f"🔍 Analyzing {symbol} volatility event..."
        if self.progress_callback:
            await self.progress_callback(self.progress)
        
        # Use Claude for analysis (same as live trading)
        analysis = await self._claude_analysis(market_data)
        
        if analysis and analysis['confidence'] >= self.config.confidence_threshold:
            self.progress.message = f"✨ Found opportunity: {symbol} {analysis['spread_type']}"
            if self.progress_callback:
                await self.progress_callback(self.progress)
            return {
                'symbol': symbol,
                'date': date,
                'market_data': market_data,
                'analysis': analysis
            }
            
        return None
        
    async def _wait_for_rate_limit(self):
        """Wait if necessary to avoid hitting rate limits"""
        current_time = time.time()
        
        # Remove API calls older than the window
        self.last_api_calls = [t for t in self.last_api_calls 
                              if current_time - t < self.api_call_window]
        
        # If we've hit the limit, wait
        if len(self.last_api_calls) >= self.max_api_calls_per_minute:
            wait_time = self.api_call_window - (current_time - self.last_api_calls[0]) + 1
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                # Clean up old calls after waiting
                current_time = time.time()
                self.last_api_calls = [t for t in self.last_api_calls 
                                      if current_time - t < self.api_call_window]
        
        # Record this API call
        self.last_api_calls.append(current_time)
    
    async def _claude_analysis(self, market_data: Dict) -> Optional[Dict]:
        """Get Claude's analysis for the trade"""
        # Wait for rate limit if necessary
        await self._wait_for_rate_limit()
        
        prompt = f"""
        Analyze this volatility spike for a credit spread opportunity:
        
        Symbol: {market_data['symbol']}
        Current Price: ${market_data['current_price']:.2f}
        Today's Move: {market_data['percent_change']:.2f}%
        Volume: {market_data['volume']:,}
        IV Rank: {market_data['iv_rank']:.1f}
        IV Percentile: {market_data['iv_percentile']:.1f}
        
        Technical Indicators:
        20-day SMA: ${market_data.get('sma_20', market_data['current_price']):.2f}
        14-day RSI: {market_data.get('rsi_14', 50):.1f}
        Price vs SMA: {"Above" if market_data['current_price'] > market_data.get('sma_20', market_data['current_price']) else "Below"} SMA
        
        Account Balance: ${self.current_capital:.2f}
        Max Risk per Trade: {self.config.max_risk_per_trade * 100}%
        
        IMPORTANT Directional Filter Rules:
        - PUT CREDIT SPREADS: ONLY if price > SMA AND RSI > 50
        - CALL CREDIT SPREADS: ONLY if price < SMA AND RSI < 50
        - If conditions don't match, DO NOT TRADE
        
        Strategy Rules:
        1. Check directional filters FIRST - if they don't match, set should_trade = false
        2. If filters pass and big move DOWN: Sell CALL credit spread above resistance
        3. If filters pass and big move UP: Sell PUT credit spread below support
        4. Target 15 delta for short strike (approximately 85% probability of profit)
        5. Use 40-50 DTE for primary book, 7-14 DTE only if IV Rank >= 80
        6. Calculate confidence score based on multiple factors
        
        Confidence Scoring (start at 50, add/subtract):
        - IV Rank 40-60: +5, 60-80: +10, 80+: +15
        - Price move 1.5-2%: +5, 2-3%: +10, 3%+: +15
        - Volume above average: +5
        - Directional alignment strong: +10
        - Strike distance good (1.5-2 SD): +10
        - DTE in sweet spot (40-50): +5
        - Subtract for risks: earnings nearby -10, major support/resistance breach -5
        
        Provide analysis in JSON format:
        {{
            "should_trade": true/false,
            "spread_type": "call_credit" or "put_credit",
            "short_strike": price,
            "long_strike": price,
            "expiration_days": number,
            "expected_credit": amount per contract,
            "spread_width": strike difference,
            "probability_profit": percentage,
            "confidence": 0-100,
            "confidence_factors": {{
                "iv_rank_score": number,
                "price_move_score": number,
                "volume_score": number,
                "directional_score": number,
                "strike_distance_score": number,
                "dte_score": number,
                "risk_deductions": number,
                "total": number
            }},
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
            # Look for JSON block, handling nested braces
            content = response.content[0].text
            
            # Try to find JSON between ```json markers first
            json_code_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_code_match:
                json_str = json_code_match.group(1)
            else:
                # Fall back to finding the outermost JSON object
                # Count braces to find complete JSON
                start = content.find('{')
                if start == -1:
                    return None
                    
                brace_count = 0
                end = start
                for i in range(start, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                
                json_str = content[start:end]
            
            try:
                analysis = json.loads(json_str)
                logger.info(f"Claude analysis successful: should_trade={analysis.get('should_trade')}, confidence={analysis.get('confidence')}")
                if analysis.get('should_trade'):
                    return analysis
                else:
                    logger.info(f"Claude rejected trade: {analysis.get('reasoning', 'No reasoning provided')}")
                    return None
            except json.JSONDecodeError as je:
                logger.error(f"JSON decode error: {je}")
                logger.error(f"Attempted to parse: {json_str[:200]}...")
                logger.error(f"Full response: {response.content[0].text}")
                    
        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            # Log the raw response for debugging
            if 'response' in locals():
                logger.error(f"Raw Claude response: {response.content[0].text[:500]}")
            
        return None
        
    async def _execute_trade(self, signal: Dict, date: datetime):
        """Execute a backtest trade with dynamic position sizing"""
        analysis = signal['analysis']
        symbol = signal['symbol']
        market_data = signal['market_data']
        
        # Try to get real options data for the strikes
        options_chain = await self.data_fetcher.get_options_chain(
            symbol, date, 
            analysis['expiration_days'] - 5,
            analysis['expiration_days'] + 5
        )
        
        # Look for actual option prices if available
        real_credit = None
        if options_chain:
            # Find options matching our strikes
            short_opt = next((opt for opt in options_chain 
                            if opt['strike'] == analysis['short_strike'] 
                            and opt['type'] == analysis['spread_type'].replace('_credit', '')), None)
            long_opt = next((opt for opt in options_chain 
                           if opt['strike'] == analysis['long_strike'] 
                           and opt['type'] == analysis['spread_type'].replace('_credit', '')), None)
            
            if short_opt and long_opt:
                real_credit = short_opt['mid'] - long_opt['mid']
                logger.debug(f"Using real option prices: short=${short_opt['mid']:.2f}, long=${long_opt['mid']:.2f}, credit=${real_credit:.2f}")
        
        # Calculate spread details
        spread_width = analysis.get('spread_width', abs(analysis['long_strike'] - analysis['short_strike']))
        credit_per_contract = real_credit if real_credit else analysis['expected_credit']
        max_loss_per_contract = (spread_width * 100) - credit_per_contract
        
        # Determine book type based on DTE
        expiration_days = analysis['expiration_days']
        if expiration_days >= 40:
            book_type = 'PRIMARY'
        elif 7 <= expiration_days <= 14 and market_data['iv_rank'] >= 80:
            book_type = 'INCOME_POP'
        else:
            book_type = 'PRIMARY'  # Default
        
        # Get current open positions for risk calculation
        current_positions = list(self.open_positions.values())
        
        # Use dynamic position sizing based on confidence
        position_size = self.position_sizer.calculate_position_size(
            confidence=analysis['confidence'],
            max_loss_per_contract=max_loss_per_contract,
            book_type=book_type,
            current_positions=current_positions
        )
        
        # Check if we got any contracts
        if position_size.contracts == 0:
            logger.info(f"Position sizing returned 0 contracts for {symbol} - skipping trade")
            return
        
        # Calculate actual values with sized position
        contracts = position_size.contracts
        total_credit = credit_per_contract * contracts * 100
        max_loss = position_size.total_max_loss
        
        # Update capital for position sizer
        self.position_sizer.update_account_balance(self.current_capital)
        
        # Create trade record
        trade = BacktestTrade(
            entry_time=date,
            symbol=symbol,
            spread_type=analysis['spread_type'],
            short_strike=analysis['short_strike'],
            long_strike=analysis['long_strike'],
            contracts=contracts,
            entry_credit=total_credit,
            max_profit=total_credit,
            max_loss=max_loss,
            confidence_score=analysis.get('confidence', 0),
            confidence_breakdown=analysis.get('confidence_factors', analysis.get('confidence_breakdown', None))
        )
        
        # Store in open positions
        trade_id = f"{symbol}_{date.strftime('%Y%m%d_%H%M%S')}"
        self.open_positions[trade_id] = trade
        
        # Log the trade
        logger.info(f"BACKTEST TRADE: {symbol} {analysis['spread_type']} "
                   f"{analysis['short_strike']}/{analysis['long_strike']} "
                   f"x{contracts} for ${total_credit:.2f} credit | "
                   f"Confidence: {analysis['confidence']}% ({position_size.confidence_tier}) | "
                   f"Risk: {position_size.risk_percentage:.1%}")
        
        # Update progress with trade info
        self.progress.trades_completed += 1
        self.progress.message = f"💰 OPENED: {symbol} {analysis['spread_type']} @ ${total_credit:.2f} | {position_size.confidence_tier}"
        if self.progress_callback:
            await self.progress_callback(self.progress)
        
    async def _manage_positions(self, current_date: datetime):
        """Manage open positions - check for exits"""
        positions_to_close = []
        
        for trade_id, trade in self.open_positions.items():
            days_in_trade = (current_date - trade.entry_time).days
            
            # Simulate P&L based on time decay and market moves
            time_decay_pct = min(days_in_trade / 30, 0.8)  # Up to 80% time decay in 30 days
            
            # Random market impact
            market_impact = np.random.normal(0, 0.1)  # 10% std dev
            
            # Calculate current P&L
            if trade.spread_type == 'call_credit':
                # Calls lose value as price drops
                directional_impact = -market_impact if market_impact < 0 else market_impact * 0.5
            else:
                # Puts lose value as price rises  
                directional_impact = -market_impact if market_impact > 0 else market_impact * 0.5
                
            pnl_pct = time_decay_pct + directional_impact
            current_pnl = trade.entry_credit * pnl_pct
            
            # Check exit conditions
            exit_reason = None
            
            # Profit target: 50% of max profit (professional strategy)
            if current_pnl >= trade.max_profit * 0.50:
                exit_reason = "Profit Target"
                
            # Stop loss: 100% of credit received (max loss scenario)
            elif current_pnl <= -trade.entry_credit:
                exit_reason = "Stop Loss"
                current_pnl = -trade.max_loss  # Limit to max loss
                
            # Time stop: Close if less than 7 DTE
            elif days_in_trade >= 23:  # Assuming 30 DTE trades
                exit_reason = "Time Stop"
                
            if exit_reason:
                trade.exit_time = current_date
                trade.exit_reason = exit_reason
                trade.realized_pnl = current_pnl - (self.config.commission_per_contract * trade.contracts * 2)
                trade.days_in_trade = days_in_trade
                positions_to_close.append(trade_id)
                
                logger.info(f"CLOSING: {trade.symbol} {trade.spread_type} - {exit_reason} - P&L: ${trade.realized_pnl:.2f}")
                
                # Update progress with close info
                pnl_emoji = "✅" if trade.realized_pnl > 0 else "❌"
                self.progress.message = f"{pnl_emoji} CLOSED: {trade.symbol} {trade.spread_type} - {exit_reason} - P&L: ${trade.realized_pnl:.2f}"
                if self.progress_callback:
                    await self.progress_callback(self.progress)
                
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
        """Close all remaining positions at end of backtest"""
        for trade_id, trade in list(self.open_positions.items()):
            trade.exit_time = date
            trade.exit_reason = "Backtest End"
            trade.days_in_trade = (date - trade.entry_time).days
            
            # Assume we can close at 50% of credit
            trade.realized_pnl = trade.entry_credit * 0.5 - (self.config.commission_per_contract * trade.contracts * 2)
            
            self.results.trades.append(trade)
            self.current_capital += trade.realized_pnl
            
        self.open_positions.clear()
        
    def _calculate_portfolio_value(self, date: datetime) -> float:
        """Calculate total portfolio value including open positions"""
        total_value = self.current_capital
        
        # Add unrealized P&L from open positions
        for trade in self.open_positions.values():
            days_in_trade = (date - trade.entry_time).days
            time_decay_pct = min(days_in_trade / 30, 0.8)
            unrealized_pnl = trade.entry_credit * time_decay_pct * 0.5  # Conservative estimate
            total_value += unrealized_pnl
            
        return total_value
        
    def _calculate_metrics(self):
        """Calculate final performance metrics"""
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
        
        # Sharpe ratio (simplified - assuming 0% risk-free rate)
        if self.results.daily_returns:
            returns_array = np.array(self.results.daily_returns)
            if len(returns_array) > 1 and returns_array.std() > 0:
                self.results.sharpe_ratio = (returns_array.mean() / returns_array.std()) * np.sqrt(252)
            else:
                self.results.sharpe_ratio = 0
                
    def get_trade_summary(self) -> pd.DataFrame:
        """Get summary of all trades as DataFrame"""
        if not self.results.trades:
            return pd.DataFrame()
            
        trades_data = []
        for trade in self.results.trades:
            trades_data.append({
                'Entry Date': trade.entry_time.strftime('%Y-%m-%d'),
                'Exit Date': trade.exit_time.strftime('%Y-%m-%d') if trade.exit_time else '',
                'Symbol': trade.symbol,
                'Type': trade.spread_type,
                'Strikes': f"{trade.short_strike}/{trade.long_strike}",
                'Contracts': trade.contracts,
                'Entry Credit': f"${trade.entry_credit:.2f}",
                'P&L': f"${trade.realized_pnl:.2f}",
                'P&L %': f"{(trade.realized_pnl / trade.entry_credit * 100):.1f}%" if trade.entry_credit > 0 else "0%",
                'Days': trade.days_in_trade,
                'Exit Reason': trade.exit_reason
            })
            
        return pd.DataFrame(trades_data)