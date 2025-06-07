"""
Comprehensive backtesting engine for volatility trading strategies
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any, Literal
from dataclasses import dataclass, field
import logging
from decimal import Decimal
import time

from src.core.trade_manager import EnhancedTradeManager, TradeManagementRules, OptionContract
from src.data.trade_db import trade_db
import os
import json
from src.backtest.backtest_progress import BacktestProgress
from src.backtest.data_fetcher import AlpacaDataFetcher
from src.core.position_sizer import DynamicPositionSizer
from src.core.strike_selector import DeltaStrikeSelector
from src.backtest.ai_provider import create_ai_provider
from src.strategies.credit_spread import CreditSpreadStrategy

logger = logging.getLogger(__name__)

@dataclass
class ActivityLogEntry:
    """Activity log entry for dashboard"""
    timestamp: datetime
    type: str  # 'info', 'trade', 'warning', 'error', 'analysis'
    message: str
    details: Optional[Dict] = None

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
    dte_target: int = 9  # Target days to expiration
    force_exit_days: int = 7  # Exit with this many days remaining
    
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
    book_type: str = "PRIMARY"  # PRIMARY or INCOME_POP
    expiration_days: int = 45  # DTE at entry
    entry_delta: Optional[float] = None  # Delta at entry
    
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
    
    def __init__(self, config: BacktestConfig, progress_callback=None, ai_provider=None, activity_callback=None,
                 method: Literal["live", "synthetic"] = "live", 
                 tier_targets: List[float] = None, 
                 contracts_by_tier: List[float] = None,
                 force_exit_days: int = 21,
                 synthetic_pricing: bool = False,
                 delta_target: float = 0.16):
        self.config = config
        self.trade_manager = EnhancedTradeManager(paper_trading=True)
        
        # Initialize AI provider (Gemini or Claude)
        self.ai_provider = ai_provider or create_ai_provider()
        
        self.current_capital = config.initial_capital
        self.open_positions: Dict[str, BacktestTrade] = {}
        self.results = BacktestResults()
        self.results.equity_curve.append(self.current_capital)
        self.progress_callback = progress_callback
        self.activity_callback = activity_callback
        self.progress = BacktestProgress()
        
        # Synthetic pricing configuration
        self.method = method
        self.synthetic_pricing = synthetic_pricing or (method == "synthetic")
        self.tier_targets = tier_targets or [0.50, 0.75, -2.50]  # Return-Boost v1: higher stop loss
        self.contracts_by_tier = contracts_by_tier or [0.4, 0.4, 0.2]
        self.force_exit_days = force_exit_days
        self.delta_target = delta_target
        
        # Initialize synthetic pricer if needed
        if self.synthetic_pricing:
            from src.engines.synthetic_pricer import SyntheticOptionPricer
            self.synthetic_pricer = SyntheticOptionPricer()
        else:
            self.synthetic_pricer = None
        
        # Initialize data fetcher for real historical data
        self.data_fetcher = AlpacaDataFetcher()
        
        # Initialize dynamic position sizer
        self.position_sizer = DynamicPositionSizer(self.current_capital)
        
        # Initialize delta-based strike selector
        self.strike_selector = DeltaStrikeSelector(target_delta=delta_target)
        
        # Initialize credit spread strategy for short-dated options
        self.credit_spread_strategy = CreditSpreadStrategy(dte_target=config.dte_target, delta_target=delta_target)
        
        # Rate limiting for API (5 requests per minute)
        self.last_api_calls = []
        self.max_api_calls_per_minute = 4  # Keep it under 5 to be safe
        self.api_call_window = 60  # seconds
        
        # Track partial closes
        self.partial_closes: Dict[str, List[Dict]] = {}
        
        # Track all analyses for saving
        self.all_analyses: List[Dict] = []
        
    def _calculate_simple_pnl(self, trade: BacktestTrade, days_in_trade: int) -> float:
        """Simple P&L calculation based on time decay and random market impact"""
        time_decay_pct = min(days_in_trade / 30, 0.8)  # Up to 80% time decay in 30 days
        
        # Random market impact
        market_impact = np.random.normal(0, 0.1)  # 10% std dev
        
        # Calculate directional impact
        if trade.spread_type == 'call_credit':
            # Calls lose value as price drops
            directional_impact = -market_impact if market_impact < 0 else market_impact * 0.5
        else:
            # Puts lose value as price rises  
            directional_impact = -market_impact if market_impact > 0 else market_impact * 0.5
            
        pnl_pct = time_decay_pct + directional_impact
        return trade.entry_credit * pnl_pct
        
    def _log_activity(self, type: str, message: str, details: Dict = None):
        """Log activity for dashboard display"""
        if self.activity_callback:
            entry = ActivityLogEntry(
                timestamp=datetime.now(),
                type=type,
                message=message,
                details=details
            )
            self.activity_callback(entry)
        
    async def run_backtest(self) -> BacktestResults:
        """Run complete backtest"""
        logger.info(f"Starting backtest from {self.config.start_date} to {self.config.end_date}")
        logger.info(f"Symbols: {', '.join(self.config.symbols)}")
        logger.info(f"Initial capital: ${self.config.initial_capital:,.2f}")
        logger.info(f"Pricing method: {'Synthetic' if self.synthetic_pricing else 'Real data'}")
        
        self._log_activity('info', f"Starting AI-powered backtest with Claude Sonnet 4")
        self._log_activity('info', f"Period: {self.config.start_date.date()} to {self.config.end_date.date()}")
        self._log_activity('info', f"Symbols: {', '.join(self.config.symbols)}")
        self._log_activity('info', f"Initial capital: ${self.config.initial_capital:,.2f}")
        self._log_activity('info', f"Pricing method: {'Synthetic Black-Scholes' if self.synthetic_pricing else 'Real options data'}")
        
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
        total_days = 0
        
        # Count total trading days first
        temp_date = self.config.start_date
        while temp_date <= self.config.end_date:
            if temp_date.weekday() < 5:
                total_days += 1
            temp_date += timedelta(days=1)
            
        self.progress.total_days = total_days
        current_day = 0
        
        while current_date <= self.config.end_date:
            # Skip weekends
            if current_date.weekday() < 5:
                current_day += 1
                self.progress.current_day = current_day
                self.progress.current_date = current_date
                self.progress.message = f"Processing {current_date.strftime('%Y-%m-%d')}"
                
                if self.progress_callback:
                    self.progress_callback(self.progress)
                    
                await self._process_trading_day(current_date)
                
            current_date += timedelta(days=1)
            
        # Close any remaining positions
        await self._close_all_positions(self.config.end_date)
        
        # Calculate final metrics
        self._calculate_metrics()
        
        # Final summary log
        self._log_activity('info', f"Backtest completed: {self.results.total_trades} trades, ${self.results.total_pnl:.2f} P&L", {
            'total_trades': self.results.total_trades,
            'winning_trades': self.results.winning_trades,
            'losing_trades': self.results.losing_trades,
            'total_pnl': self.results.total_pnl,
            'win_rate': self.results.win_rate,
            'sharpe_ratio': self.results.sharpe_ratio,
            'pricing_method': 'synthetic' if self.synthetic_pricing else 'real'
        })
        
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
                
            # Handle MultiIndex from Alpaca (symbol, timestamp)
            if isinstance(df.index, pd.MultiIndex):
                # Reset index to get timestamp as a column
                df = df.reset_index()
                # Filter for our symbol if needed
                if 'symbol' in df.columns:
                    df = df[df['symbol'] == symbol]
                # Set timestamp as index
                df.set_index('timestamp', inplace=True)
            
            # Find the closest trading day to our target date
            df.index = pd.to_datetime(df.index)
            
            # Make target_date timezone-aware if the index is timezone-aware
            if df.index.tz is not None:
                target_date = pd.Timestamp(date.date()).tz_localize('UTC')
            else:
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
                if vol_data and 'iv_rank' in vol_data and not pd.isna(vol_data['iv_rank']):
                    iv_rank = float(vol_data['iv_rank'])
                    logger.debug(f"Using real IV rank for {symbol}: {iv_rank:.1f}")
                else:
                    # Fallback calculation
                    realized_vol = day_data.get('realized_vol', 20)
                    if pd.isna(realized_vol):
                        realized_vol = 20  # Default to 20% if NaN
                    iv_rank = min(max(realized_vol * 3, 50), 100)
                
                # Get technical indicators
                sma_20 = day_data.get('sma_20', day_data['close'])
                rsi_14 = day_data.get('rsi_14', 50.0)
                
                # If synthetic pricing, cache IV for the symbol
                if self.synthetic_pricing and self.synthetic_pricer:
                    # Estimate IV from volatility data
                    if vol_data and 'current_iv' in vol_data:
                        iv = vol_data['current_iv'] / 100  # Convert to decimal
                    else:
                        iv = realized_vol / 100 if 'realized_vol' in day_data else 0.20
                    self.synthetic_pricer.cache_iv(symbol, iv)
                
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
            self._log_activity('error', f"Data fetch error for {symbol} on {date}: {str(e)}", {
                'symbol': symbol,
                'date': str(date),
                'error': str(e)
            })
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
            self.progress_callback(self.progress)
            
        iv_rank_str = f"{market_data['iv_rank']:.0f}" if not pd.isna(market_data['iv_rank']) else "N/A"
        self._log_activity('analysis', f"Volatility event detected: {symbol} moved {market_data['percent_change']:.1f}% with IV rank {iv_rank_str}")
        
        # Use Claude for analysis (same as live trading)
        analysis = await self._claude_analysis(market_data)
        
        # Store analysis for database
        analysis_record = {
            'timestamp': date,
            'symbol': symbol,
            'current_price': market_data['current_price'],
            'percent_change': market_data['percent_change'],
            'volume': market_data['volume'],
            'iv_rank': market_data['iv_rank'],
            'should_trade': False,
            'confidence': 0,
            'reasoning': 'No analysis available'
        }
        
        if analysis:
            analysis_record.update({
                'should_trade': analysis['confidence'] >= self.config.confidence_threshold,
                'confidence': analysis.get('confidence', 0),
                'spread_type': analysis.get('spread_type'),
                'reasoning': analysis.get('reasoning', 'No reasoning provided')
            })
            
        # Store analysis record for later
        self.pending_analysis = analysis_record
        
        if analysis and analysis['confidence'] >= self.config.confidence_threshold:
            self.progress.message = f"✨ Found opportunity: {symbol} {analysis['spread_type']}"
            if self.progress_callback:
                self.progress_callback(self.progress)
            return {
                'symbol': symbol,
                'date': date,
                'market_data': market_data,
                'analysis': analysis
            }
        else:
            # Save analysis even if no trade (confidence too low or no analysis)
            if hasattr(self, 'pending_analysis') and self.pending_analysis:
                self.all_analyses.append(self.pending_analysis)
                self.pending_analysis = None
            
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
        
    async def _claude_analysis(self, market_data: Dict) -> Optional[Dict]:
        """Get Claude's analysis of the trading opportunity"""
        # Rate limit check
        await self._wait_for_rate_limit()
        
        prompt = f"""
        You are a professional options trader analyzing a potential volatility trade opportunity.
        
        Market Data:
        - Symbol: {market_data['symbol']}
        - Price: ${market_data['current_price']}
        - Day's Move: {market_data['percent_change']}%
        - IV Rank: {market_data['iv_rank']}
        - SMA(20): ${market_data['sma_20']}
        - RSI(14): {market_data['rsi_14']}
        
        Based on this data, should we enter a credit spread trade? If yes, what type?
        
        Consider:
        - For negative moves with high IV: put credit spreads may benefit from mean reversion
        - For positive moves with high IV: call credit spreads may benefit from resistance levels
        - RSI extremes: <30 oversold (favor puts), >70 overbought (favor calls)
        - Price vs SMA: Below SMA with bounce potential (puts), Above SMA extended (calls)
        
        Respond with a confidence score (0-100) and reasoning.
        Also recommend:
        1. Spread type (put_credit or call_credit)
        2. Strike width ($1, $2, $5, etc)
        3. Days to expiration (30-60 days)
        4. Risk/reward assessment
        
        Format your response as JSON with keys:
        - confidence (integer 0-100)
        - spread_type (string: "put_credit" or "call_credit")
        - strike_width (number)
        - dte (integer)
        - reasoning (string)
        """
        
        try:
            response = await self.ai_provider.analyze_trade(prompt)
            self.last_api_calls.append(time.time())
            
            # AI provider already returns parsed JSON dict
            if response:
                return {
                    'confidence': response.get('confidence', 0),
                    'spread_type': response.get('spread_type', 'put_credit'),
                    'reasoning': response.get('reasoning', 'No reasoning provided')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            return None
            
    async def _execute_trade(self, signal: Dict, date: datetime):
        """Execute a trade based on signal"""
        symbol = signal['symbol']
        market_data = signal['market_data']
        analysis = signal['analysis']
        
        # Get price for strike calculation
        current_price = market_data['current_price']
        
        # Select strikes based on delta target or simple percentage OTM
        if self.synthetic_pricing:
            # For synthetic pricing, use delta-based selection if we have the pricer
            from src.core.greeks_calculator import GreeksCalculator
            calc = GreeksCalculator()
            
            # Estimate IV for the symbol
            iv = self.synthetic_pricer.get_cached_iv(symbol) or 0.25
            
            # Find strikes at target delta
            if analysis['spread_type'] == 'put_credit':
                # Put credit spread: sell put closer to money, buy put further OTM
                # Short strike at -delta_target (e.g., -0.16 delta)
                try:
                    short_strike = calc.find_strike_by_delta(
                        spot_price=current_price, 
                        target_delta=-self.delta_target,  # Negative for puts
                        time_to_expiry=45/365,  # 45 DTE
                        volatility=iv,
                        option_type='put',
                        strike_increment=1.0
                    )
                    
                    if short_strike is None:
                        # Fallback to percentage-based selection
                        short_strike = round(current_price * 0.97)  # 3% OTM
                        logger.warning(f"Delta-based strike selection failed for {symbol}, using 3% OTM: ${short_strike}")
                        
                    long_strike = short_strike - 1.0  # Long strike is $1 lower (further OTM)
                    # Ensure proper ordering for put credit spread
                    # For puts: we sell the higher strike and buy the lower strike
                    if long_strike > short_strike:
                        short_strike, long_strike = long_strike, short_strike
                except Exception as e:
                    logger.error(f"Error in strike selection for {symbol}: {e}")
                    # Fallback to simple percentage-based selection
                    short_strike = round(current_price * 0.97)  # 3% OTM
                    long_strike = short_strike - 1.0
            else:
                # Call credit spread: sell call closer to money, buy call further OTM
                # Short strike at delta_target (e.g., 0.16 delta)
                try:
                    short_strike = calc.find_strike_by_delta(
                        spot_price=current_price,
                        target_delta=self.delta_target,
                        time_to_expiry=45/365,  # 45 DTE
                        volatility=iv,
                        option_type='call',
                        strike_increment=1.0
                    )
                    
                    if short_strike is None:
                        # Fallback to percentage-based selection
                        short_strike = round(current_price * 1.03)  # 3% OTM
                        logger.warning(f"Delta-based strike selection failed for {symbol}, using 3% OTM: ${short_strike}")
                        
                    long_strike = short_strike + 1.0  # Long strike is $1 higher (further OTM)
                except Exception as e:
                    logger.error(f"Error in strike selection for {symbol}: {e}")
                    # Fallback to simple percentage-based selection
                    short_strike = round(current_price * 1.03)  # 3% OTM
                    long_strike = short_strike + 1.0
        else:
            # Original selection logic for real data
            short_strike = await self.strike_selector.select_strike(
                symbol, current_price, market_data.get('iv_rank', 50), 
                analysis['spread_type'], date
            )
            long_strike = short_strike - 1 if analysis['spread_type'] == 'put_credit' else short_strike + 1
        
        # Round strikes
        short_strike = round(short_strike)
        long_strike = round(long_strike)
        
        # Default Greeks and pricing
        real_greeks = None
        credit_per_contract = 0.35  # Default
        max_loss_per_contract = 0.65  # Default
        
        # Try to get real options data unless using synthetic
        if not self.synthetic_pricing:
            # Existing real data fetching logic
            real_options = await self.data_fetcher.get_historical_options_data(
                symbol, date, days_to_expiry=45
            )
            
            if real_options and 'options_chains' in real_options:
                for chain in real_options['options_chains']:
                    if chain.get('short_strike') == short_strike and chain.get('long_strike') == long_strike:
                        # Real options data should provide credit in dollars per contract
                        credit_per_contract = chain.get('credit', 0.35) * 100  # Convert if needed
                        max_loss_per_contract = (abs(long_strike - short_strike) * 100) - credit_per_contract
                        real_greeks = {
                            'short_delta': chain.get('short_delta', -0.15),
                            'long_delta': chain.get('long_delta', -0.05),
                            'net_delta': chain.get('net_delta', -0.10)
                        }
                        break
        else:
            # Use synthetic pricing
            expiry = date + timedelta(days=45)
            iv = self.synthetic_pricer.get_cached_iv(symbol) or 0.25
            
            # Price the spread
            spread_price = self.synthetic_pricer.price_spread(
                date=pd.Timestamp(date),
                underlying_price=current_price,
                strikes=(short_strike, long_strike),
                expiry=pd.Timestamp(expiry),
                iv=iv
            )
            
            # Calculate deltas
            short_delta, long_delta = self.synthetic_pricer.calc_delta(
                date=pd.Timestamp(date),
                underlying_price=current_price,
                strikes=(short_strike, long_strike),
                expiry=pd.Timestamp(expiry),
                iv=iv
            )
            
            # Spread price from synthetic pricer is already in dollars per share
            # Convert to dollars per contract (multiply by 100)
            credit_per_contract = spread_price * 100  # Convert to dollars per contract
            credit_per_contract = max(1.0, credit_per_contract)  # Minimum $1 credit per contract
            max_loss_per_contract = (abs(long_strike - short_strike) * 100) - credit_per_contract
            real_greeks = {
                'short_delta': short_delta,
                'long_delta': long_delta,
                'net_delta': short_delta + long_delta
            }
        
        # Get position sizing from Claude with confidence weighting
        sizing = await self._claude_position_size(market_data, analysis)
        base_risk_pct = sizing.get('risk_percentage', 0.03)
        
        # IV-aware dynamic sizing (Return-Boost v1)
        iv_rank = market_data.get('iv_rank', 50)
        iv_boost = max(1.0, min(2.0, iv_rank / 50.0))  # 50 → 1×, 90 → 1.8×, cap 2×
        
        # Apply boost and cap at 8%
        risk_pct = base_risk_pct * iv_boost
        risk_pct = min(risk_pct, 0.08) if risk_pct < 1 else min(risk_pct, 8.0)  # Handle both decimal and percentage
        
        # Calculate contracts based on risk
        if risk_pct < 1:  # If it's a decimal (0.03), convert to percentage
            risk_pct = risk_pct * 100
            
        risk_amount = self.current_capital * (risk_pct / 100)
        contracts = int(risk_amount / max_loss_per_contract)  # max_loss already in dollars
        
        logger.info(f"IV-aware sizing: IV={iv_rank:.0f}, boost={iv_boost:.1f}×, risk={risk_pct:.1%}")
        
        # Select expiry using credit spread strategy (Return-Boost v1: short-dated options)
        expiry_date = self.credit_spread_strategy.select_expiry(date)
        expiration_days = (expiry_date - date).days
        
        # Determine book type based on confidence
        book_type = 'PRIMARY' if sizing.get('confidence_score', 0) >= 70 else 'INCOME_POP'
        
        # Ensure minimum 1 contract
        contracts = max(1, min(contracts, 20))  # Between 1 and 20 contracts
        logger.info(f"Calculated {contracts} contracts based on {risk_pct:.1%} risk ({sizing.get('confidence_score', 0)}% confidence)")
        
        # Get current open positions for portfolio tracking
        current_positions = list(self.open_positions.values())
        
        # Calculate actual values with sized position
        total_credit = credit_per_contract * contracts  # Already in dollars per contract
        max_loss = max_loss_per_contract * contracts
        
        # Update capital for position sizer
        self.position_sizer.update_account_balance(self.current_capital)
        
        # Store entry credit for tiered exit tracking
        entry_credit = total_credit
        
        # Create trade record with Claude's recommendations
        trade = BacktestTrade(
            entry_time=date,
            symbol=symbol,
            spread_type=analysis['spread_type'],
            short_strike=short_strike,
            long_strike=long_strike,
            contracts=contracts,
            entry_credit=entry_credit,
            max_profit=total_credit,
            max_loss=max_loss,
            confidence_score=sizing.get('confidence_score', 0),
            confidence_breakdown=sizing.get('confidence_factors', {}),
            book_type=book_type,
            expiration_days=expiration_days,
            entry_delta=real_greeks.get('short_delta', -0.15) if real_greeks else -0.15
        )
        
        # Update pending analysis with strike info and append to all_analyses
        if hasattr(self, 'pending_analysis') and self.pending_analysis:
            self.pending_analysis['short_strike'] = short_strike
            self.pending_analysis['long_strike'] = long_strike
            self.pending_analysis['contracts'] = contracts
            self.pending_analysis['expected_credit'] = total_credit
            self.pending_analysis['spread_type'] = analysis['spread_type']
            self.all_analyses.append(self.pending_analysis)
            self.pending_analysis = None
        
        # Store in open positions
        trade_id = f"{symbol}_{date.strftime('%Y%m%d_%H%M%S')}"
        self.open_positions[trade_id] = trade
        
        # Log the trade with Claude's analysis
        confidence_score = sizing.get('confidence_score', 0)
        risk_pct = sizing.get('risk_percentage', 0.03)
        
        # Determine confidence tier
        if confidence_score >= 90:
            confidence_tier = "Very High (8%)"
        elif confidence_score >= 80:
            confidence_tier = "High (5%)"
        elif confidence_score >= 70:
            confidence_tier = "Standard (3%)"
        else:
            confidence_tier = "Below threshold"
            
        logger.info(f"BACKTEST TRADE: {symbol} {analysis['spread_type']} "
                   f"{short_strike}/{long_strike} (delta {self.delta_target:.2f} targets) "
                   f"x{contracts} for ${total_credit:.2f} credit | "
                   f"Expiry: {expiry_date.strftime('%Y-%m-%d')} ({expiration_days} DTE) | "
                   f"Confidence: {confidence_score}% ({confidence_tier}) | "
                   f"Risk: {risk_pct*100 if risk_pct < 1 else risk_pct:.1f}% | "
                   f"Pricing: {'Synthetic' if self.synthetic_pricing else 'Real'}")
        
        if real_greeks:
            logger.info(f"  → Greeks: Δ {real_greeks['short_delta']:.3f}/{real_greeks['long_delta']:.3f}, Net Δ: {real_greeks['net_delta']:.3f}")
        
        # Update progress with trade info
        self.progress.trades_completed += 1
        self.progress.message = f"💰 OPENED: {symbol} {analysis['spread_type']} @ ${total_credit:.2f} | {confidence_tier}"
        if self.progress_callback:
            self.progress_callback(self.progress)
            
        # Log to activity
        self._log_activity('trade', f"OPENED: {symbol} {analysis['spread_type']} {short_strike}/{long_strike} x{contracts}", {
            'symbol': symbol,
            'strategy': analysis['spread_type'],
            'strikes': f"{short_strike}/{long_strike}",
            'contracts': contracts,
            'credit': total_credit,
            'confidence': confidence_score,
            'confidence_tier': confidence_tier,
            'pricing_method': 'synthetic' if self.synthetic_pricing else 'real',
            'ai_reasoning': analysis.get('reasoning', '')[:200]  # First 200 chars of AI reasoning
        })
        
    async def _manage_positions(self, current_date: datetime):
        """Manage open positions - check for exits"""
        positions_to_close = []
        
        for trade_id, trade in self.open_positions.items():
            days_in_trade = (current_date - trade.entry_time).days
            
            # Skip management on entry day to avoid immediate stops
            if days_in_trade == 0:
                continue
            
            # Calculate current P&L
            if self.synthetic_pricing and self.synthetic_pricer:
                # Get current underlying price
                df = await self.data_fetcher.get_stock_data(trade.symbol, current_date, current_date + timedelta(days=1))
                if not df.empty:
                    # Handle MultiIndex
                    if isinstance(df.index, pd.MultiIndex):
                        df = df.reset_index()
                        if 'symbol' in df.columns:
                            df = df[df['symbol'] == trade.symbol]
                        df.set_index('timestamp', inplace=True)
                    
                    current_price = df['close'].iloc[-1] if not df.empty else trade.entry_time  # fallback
                    
                    # Get IV from cache or estimate
                    iv = self.synthetic_pricer.get_cached_iv(trade.symbol) or 0.25
                    
                    # Calculate expiry date
                    expiry = trade.entry_time + timedelta(days=trade.expiration_days)
                    
                    # Price the spread using synthetic pricer
                    current_spread_price = self.synthetic_pricer.price_spread(
                        date=pd.Timestamp(current_date),
                        underlying_price=current_price,
                        strikes=(trade.short_strike, trade.long_strike),
                        expiry=pd.Timestamp(expiry),
                        iv=iv
                    )
                    
                    # P&L = entry credit - cost to close
                    # current_spread_price is what we'd receive to open the same spread now
                    # To close our short spread, we need to buy it back
                    cost_to_close = current_spread_price * 100 * trade.contracts
                    
                    # P&L = what we received - what we pay to close
                    current_pnl = trade.entry_credit - cost_to_close
                else:
                    # If no current price data, use entry price with some random walk
                    current_price = trade.entry_time  # This was meant to be a price, let's fix
                    # Use a simple random walk from entry price
                    price_at_entry = (trade.short_strike + trade.long_strike) / 2
                    volatility = self.synthetic_pricer.get_cached_iv(trade.symbol) or 0.25
                    daily_vol = volatility / np.sqrt(252)
                    price_change = np.random.normal(0, daily_vol * np.sqrt(days_in_trade))
                    current_price = price_at_entry * (1 + price_change)
                    
                    # Now calculate with synthetic pricer
                    expiry = trade.entry_time + timedelta(days=trade.expiration_days)
                    current_spread_price = self.synthetic_pricer.price_spread(
                        date=pd.Timestamp(current_date),
                        underlying_price=current_price,
                        strikes=(trade.short_strike, trade.long_strike),
                        expiry=pd.Timestamp(expiry),
                        iv=volatility
                    )
                    cost_to_close = current_spread_price * 100 * trade.contracts
                    current_pnl = trade.entry_credit - cost_to_close
            else:
                # Not using synthetic pricing - use simple calculation
                current_pnl = self._calculate_simple_pnl(trade, days_in_trade)
            
            # Check exit conditions with enhanced rules
            exit_reason = None
            contracts_to_close = 0
            
            # Calculate P&L percentage for scaling rules
            pnl_percentage = current_pnl / trade.max_profit if trade.max_profit > 0 else 0
            remaining_dte = trade.expiration_days - days_in_trade
            
            # HARD STOPS (apply to all positions)
            # 1. Stop loss at tier_targets[2] (default -150%) of credit received
            # For a credit spread, max loss is when we lose 150% of the credit we received
            # e.g., if we received $100 credit, stop at -$150 loss
            if current_pnl <= -abs(trade.entry_credit * abs(self.tier_targets[2])):
                exit_reason = f"Stop Loss ({self.tier_targets[2]*100:.0f}%)"
                current_pnl = -abs(trade.entry_credit * abs(self.tier_targets[2]))  # Cap loss
                contracts_to_close = trade.contracts
                
            # 2. Delta stop at 0.30 (would need real-time Greeks)
            # TODO: Implement when Greeks monitoring is available
            
            # SCALING EXITS (if no hard stop hit)
            elif trade.contracts >= 3:
                # Implement scaling exits for larger positions
                
                # Check what we've already closed
                closed_history = self.partial_closes.get(trade_id, [])
                total_closed = sum(h['contracts'] for h in closed_history)
                remaining_contracts = trade.contracts - total_closed
                
                if remaining_contracts > 0:
                    # Check tier targets
                    if pnl_percentage >= 0.90:  # 90-100% of max profit
                        exit_reason = "Profit Target (90%+)"
                        contracts_to_close = remaining_contracts  # Close all remaining
                        
                    elif pnl_percentage >= self.tier_targets[1] and not any(h['tier'] >= 2 for h in closed_history):
                        # tier_targets[1] (default 75%) - close contracts_by_tier[1] of original
                        exit_reason = f"Profit Target ({self.tier_targets[1]*100:.0f}%)"
                        contracts_to_close = int(trade.contracts * self.contracts_by_tier[1])
                        contracts_to_close = min(contracts_to_close, remaining_contracts)
                        
                        # Record partial close
                        if contracts_to_close < remaining_contracts:
                            if trade_id not in self.partial_closes:
                                self.partial_closes[trade_id] = []
                            self.partial_closes[trade_id].append({
                                'date': current_date,
                                'contracts': contracts_to_close,
                                'pnl_per_contract': current_pnl / trade.contracts,
                                'tier': 2,
                                'reason': exit_reason
                            })
                        
                    elif pnl_percentage >= self.tier_targets[0] and not any(h['tier'] >= 1 for h in closed_history):
                        # tier_targets[0] (default 50%) - close contracts_by_tier[0] of original
                        exit_reason = f"Profit Target ({self.tier_targets[0]*100:.0f}%)"
                        contracts_to_close = int(trade.contracts * self.contracts_by_tier[0])
                        contracts_to_close = min(contracts_to_close, remaining_contracts)
                        
                        # Record partial close
                        if contracts_to_close < remaining_contracts:
                            if trade_id not in self.partial_closes:
                                self.partial_closes[trade_id] = []
                            self.partial_closes[trade_id].append({
                                'date': current_date,
                                'contracts': contracts_to_close,
                                'pnl_per_contract': current_pnl / trade.contracts,
                                'tier': 1,
                                'reason': exit_reason
                            })
                        
                    elif remaining_dte <= self.force_exit_days:  # Time stop
                        exit_reason = f"Time Stop ({self.force_exit_days} DTE)"
                        contracts_to_close = remaining_contracts
                    
            else:  # CONTRACTS < 3 - simple exit rules
                # Different targets for Income-Pop vs Primary
                if trade.book_type == 'INCOME_POP':
                    if pnl_percentage >= 0.25:  # 25% for Income-Pop
                        exit_reason = "Profit Target (25%)"
                        contracts_to_close = trade.contracts
                    # No time stop for Income-Pop - let expire
                else:
                    if pnl_percentage >= self.tier_targets[0]:  # Use first tier target
                        exit_reason = f"Profit Target ({self.tier_targets[0]*100:.0f}%)"
                        contracts_to_close = trade.contracts
                        
                    elif remaining_dte <= self.force_exit_days:  # Time stop for Primary only
                        exit_reason = f"Time Stop ({self.force_exit_days} DTE)"
                        contracts_to_close = trade.contracts
                
            if exit_reason and contracts_to_close > 0:
                trade.exit_time = current_date
                trade.exit_reason = exit_reason
                trade.realized_pnl = current_pnl - (self.config.commission_per_contract * trade.contracts * 2)
                trade.days_in_trade = days_in_trade
                positions_to_close.append(trade_id)
                
                # Log with scaling info if applicable
                if trade.contracts >= 3:
                    logger.info(f"CLOSING: {trade.symbol} {trade.spread_type} - {exit_reason} - "
                              f"P&L: ${trade.realized_pnl:.2f} ({pnl_percentage:.0%} of max) - "
                              f"Closed {contracts_to_close}/{trade.contracts} contracts - "
                              f"Pricing: {'Synthetic' if self.synthetic_pricing else 'Real'}")
                else:
                    logger.info(f"CLOSING: {trade.symbol} {trade.spread_type} - {exit_reason} - "
                              f"P&L: ${trade.realized_pnl:.2f} - "
                              f"Pricing: {'Synthetic' if self.synthetic_pricing else 'Real'}")
                
                # Update progress with close info
                pnl_emoji = "✅" if trade.realized_pnl > 0 else "❌"
                self.progress.message = f"{pnl_emoji} CLOSED: {trade.symbol} {trade.spread_type} - {exit_reason} - P&L: ${trade.realized_pnl:.2f}"
                if self.progress_callback:
                    self.progress_callback(self.progress)
                    
                # Log to activity
                self._log_activity('trade', f"CLOSED: {trade.symbol} {trade.spread_type} - {exit_reason}", {
                    'symbol': trade.symbol,
                    'strategy': trade.spread_type,
                    'exit_reason': exit_reason,
                    'pnl': trade.realized_pnl,
                    'days_in_trade': days_in_trade,
                    'contracts': trade.contracts,
                    'pricing_method': 'synthetic' if self.synthetic_pricing else 'real'
                })
                
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
                'Exit Reason': trade.exit_reason,
                'Pricing': 'Synthetic' if self.synthetic_pricing else 'Real'
            })
            
        return pd.DataFrame(trades_data)
        
    async def _claude_position_size(self, market_data: Dict, analysis: Dict) -> Dict:
        """Get position sizing recommendation from Claude"""
        # Implementation should follow the pattern from _claude_analysis
        # For now, return default sizing
        return {
            'confidence_score': analysis.get('confidence', 70),
            'risk_percentage': 0.03,  # 3% default
            'confidence_factors': {
                'iv_rank': market_data['iv_rank'],
                'price_move': abs(market_data['percent_change']),
                'technical_alignment': 'neutral'
            }
        }

# Parameter defaults for external configuration
DEFAULTS = dict(
    synthetic_pricing=True,
    delta_target=0.16,
    tier_targets=[0.50, 0.75, -1.50],  # +50%, +75%, -150% loss
    contracts_by_tier=[0.4, 0.4, 0.2],
    force_exit_days=21,
)