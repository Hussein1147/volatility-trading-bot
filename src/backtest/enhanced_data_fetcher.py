"""
Enhanced data fetcher that combines multiple sources for comprehensive historical data
- Alpaca: Options chains and pricing
- TastyTrade: IV rank and volatility metrics
- Yahoo Finance: Stock price data fallback
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import os
import asyncio
import yfinance as yf
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest, OptionChainRequest, OptionSnapshotRequest
)
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv

# Import our TastyTrade integration
from .tastytrade_api import TastyTradeDataFetcher
from .tastytrade_iv_fetcher import get_historical_iv_rank

logger = logging.getLogger(__name__)
load_dotenv()

class EnhancedDataFetcher:
    """Enhanced data fetcher combining multiple sources"""
    
    # Data availability dates
    ALPACA_OPTIONS_START = datetime(2024, 2, 1)
    HISTORICAL_DATA_START = datetime(2020, 1, 1)
    
    def __init__(self):
        # Initialize Alpaca clients
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        self.stock_client = StockHistoricalDataClient(api_key, secret_key)
        
        try:
            self.options_client = OptionHistoricalDataClient(api_key, secret_key)
            self.has_options_access = True
            logger.info("Alpaca options client initialized")
        except Exception as e:
            logger.warning(f"Options client init failed: {e}")
            self.has_options_access = False
            
        # Initialize TastyTrade fetcher for IV data
        self.tastytrade_fetcher = TastyTradeDataFetcher()
        
        # Cache for expensive operations
        self._cache = {}
        
    async def get_market_data(self, symbol: str, date: datetime) -> Optional[Dict]:
        """
        Get comprehensive market data for a symbol on a specific date
        Combines stock price, options data, and IV metrics
        """
        cache_key = f"{symbol}_{date.strftime('%Y-%m-%d')}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            # Get stock data
            stock_data = await self._get_stock_data(symbol, date)
            if not stock_data:
                return None
                
            # Get IV rank from TastyTrade or historical data
            iv_rank = await self._get_iv_rank(symbol, date)
            
            # Get options chain if available
            options_data = None
            if date >= self.ALPACA_OPTIONS_START and self.has_options_access:
                options_data = await self._get_options_chain(symbol, date)
                
            # Combine all data
            market_data = {
                **stock_data,
                'iv_rank': iv_rank,
                'iv_percentile': iv_rank + 5 if iv_rank else 50,  # Estimate if not available
                'has_real_options': options_data is not None,
                'options_chain': options_data
            }
            
            # Cache the result
            self._cache[cache_key] = market_data
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol} on {date}: {e}")
            return None
            
    async def _get_stock_data(self, symbol: str, date: datetime) -> Optional[Dict]:
        """Get stock price data"""
        try:
            # Try Alpaca first
            end_date = date + timedelta(days=1)
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=date,
                end=end_date
            )
            
            bars = self.stock_client.get_stock_bars(request)
            
            if symbol in bars and len(bars[symbol]) > 0:
                bar = bars[symbol][0]
                
                # Calculate daily price move
                percent_change = ((bar.close - bar.open) / bar.open) * 100
                
                return {
                    'symbol': symbol,
                    'date': date,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': int(bar.volume),
                    'current_price': float(bar.close),
                    'percent_change': percent_change,
                    'daily_range': float(bar.high - bar.low),
                    'volatility': abs(percent_change)  # Simple volatility proxy
                }
                
        except Exception as e:
            logger.warning(f"Alpaca stock data failed, trying Yahoo: {e}")
            
        # Fallback to Yahoo Finance
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=date, end=date + timedelta(days=1))
            
            if not hist.empty:
                row = hist.iloc[0]
                percent_change = ((row['Close'] - row['Open']) / row['Open']) * 100
                
                return {
                    'symbol': symbol,
                    'date': date,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'current_price': float(row['Close']),
                    'percent_change': percent_change,
                    'daily_range': float(row['High'] - row['Low']),
                    'volatility': abs(percent_change)
                }
                
        except Exception as e:
            logger.error(f"Yahoo Finance fallback also failed: {e}")
            
        return None
        
    async def _get_iv_rank(self, symbol: str, date: datetime) -> float:
        """Get IV rank from available sources"""
        
        # First check historical database
        historical_iv = get_historical_iv_rank(symbol, date)
        if historical_iv is not None:
            return historical_iv
            
        # For recent dates, try TastyTrade API
        if date >= datetime.now() - timedelta(days=30):
            try:
                iv_rank = await self.tastytrade_fetcher.get_iv_rank(symbol, date)
                if iv_rank is not None:
                    return iv_rank
            except Exception as e:
                logger.warning(f"TastyTrade IV fetch failed: {e}")
                
        # Fall back to estimation based on volatility
        return self._estimate_iv_rank(symbol, date)
        
    def _estimate_iv_rank(self, symbol: str, date: datetime) -> float:
        """Estimate IV rank based on historical volatility patterns"""
        try:
            # Get 30 days of historical data
            ticker = yf.Ticker(symbol)
            end_date = date
            start_date = date - timedelta(days=30)
            
            hist = ticker.history(start=start_date, end=end_date)
            
            if len(hist) < 10:
                return 50.0  # Default middle value
                
            # Calculate daily returns
            returns = hist['Close'].pct_change().dropna()
            
            # Calculate realized volatility (annualized)
            realized_vol = returns.std() * np.sqrt(252) * 100
            
            # Map to IV rank (rough estimation)
            # Low vol = low IV rank, high vol = high IV rank
            if realized_vol < 10:
                return 20
            elif realized_vol < 15:
                return 40
            elif realized_vol < 20:
                return 60
            elif realized_vol < 30:
                return 75
            else:
                return 85
                
        except Exception as e:
            logger.warning(f"IV rank estimation failed: {e}")
            return 50.0
            
    async def _get_options_chain(self, symbol: str, date: datetime) -> Optional[Dict]:
        """Get options chain from Alpaca"""
        if not self.has_options_access:
            return None
            
        try:
            # Get options chain for 14-45 DTE
            request = OptionChainRequest(
                underlying_symbol=symbol,
                expiration_date_gte=date + timedelta(days=14),
                expiration_date_lte=date + timedelta(days=45)
            )
            
            chain = self.options_client.get_option_chain(request)
            
            # Process and structure the chain data
            options_by_expiry = {}
            
            for option in chain:
                expiry = option.expiration_date
                
                if expiry not in options_by_expiry:
                    options_by_expiry[expiry] = {
                        'calls': {},
                        'puts': {},
                        'expiration': expiry,
                        'dte': (expiry - date).days
                    }
                    
                option_data = {
                    'symbol': option.symbol,
                    'strike': float(option.strike_price),
                    'bid': float(option.bid_price) if option.bid_price else 0,
                    'ask': float(option.ask_price) if option.ask_price else 0,
                    'mid': (float(option.bid_price or 0) + float(option.ask_price or 0)) / 2,
                    'volume': int(option.volume) if option.volume else 0,
                    'open_interest': int(option.open_interest) if option.open_interest else 0,
                    'implied_volatility': float(option.implied_volatility) if option.implied_volatility else 0.25
                }
                
                if option.option_type == 'CALL':
                    options_by_expiry[expiry]['calls'][option.strike_price] = option_data
                else:
                    options_by_expiry[expiry]['puts'][option.strike_price] = option_data
                    
            return options_by_expiry
            
        except Exception as e:
            logger.error(f"Error fetching options chain: {e}")
            return None
            
    async def get_options_for_spread(
        self, 
        symbol: str, 
        date: datetime, 
        spread_type: str,
        target_delta: float = 0.30,
        dte_target: int = 21
    ) -> Optional[Dict]:
        """
        Get specific options for a spread trade
        Returns short and long strike options
        """
        
        market_data = await self.get_market_data(symbol, date)
        if not market_data:
            return None
            
        current_price = market_data['current_price']
        
        # If we have real options data, use it
        if market_data.get('options_chain'):
            return self._select_spread_from_chain(
                market_data['options_chain'],
                current_price,
                spread_type,
                target_delta,
                dte_target
            )
            
        # Otherwise, simulate the spread
        return self._simulate_spread_options(
            symbol,
            current_price,
            market_data['iv_rank'],
            spread_type,
            target_delta,
            dte_target
        )
        
    def _select_spread_from_chain(
        self,
        options_chain: Dict,
        current_price: float,
        spread_type: str,
        target_delta: float,
        dte_target: int
    ) -> Optional[Dict]:
        """Select optimal strikes from real options chain"""
        
        # Find best expiration
        best_expiry = None
        best_dte_diff = float('inf')
        
        for expiry, data in options_chain.items():
            dte_diff = abs(data['dte'] - dte_target)
            if dte_diff < best_dte_diff:
                best_dte_diff = dte_diff
                best_expiry = expiry
                
        if not best_expiry:
            return None
            
        expiry_data = options_chain[best_expiry]
        
        # Select strikes based on spread type
        if spread_type == 'call_credit':
            # Sell call spread above current price
            strikes = sorted([s for s in expiry_data['calls'].keys() if s > current_price])
            
            if len(strikes) < 2:
                return None
                
            # Short strike ~1.5 std dev out
            target_short = current_price * 1.02  # Rough approximation
            short_strike = min(strikes, key=lambda x: abs(x - target_short))
            
            # Long strike $5 wider
            long_strike = short_strike + 5
            
        else:  # put_credit
            # Sell put spread below current price
            strikes = sorted([s for s in expiry_data['puts'].keys() if s < current_price], reverse=True)
            
            if len(strikes) < 2:
                return None
                
            # Short strike ~1.5 std dev out
            target_short = current_price * 0.98
            short_strike = min(strikes, key=lambda x: abs(x - target_short))
            
            # Long strike $5 wider
            long_strike = short_strike - 5
            
        # Get option data
        option_type = 'calls' if spread_type == 'call_credit' else 'puts'
        short_option = expiry_data[option_type].get(short_strike)
        long_option = expiry_data[option_type].get(long_strike)
        
        if not short_option or not long_option:
            return None
            
        # Calculate spread metrics
        credit = short_option['mid'] - long_option['mid']
        
        return {
            'short_strike': short_strike,
            'long_strike': long_strike,
            'short_option': short_option,
            'long_option': long_option,
            'credit': credit,
            'expiration': best_expiry,
            'dte': expiry_data['dte'],
            'spread_width': abs(long_strike - short_strike)
        }
        
    def _simulate_spread_options(
        self,
        symbol: str,
        current_price: float,
        iv_rank: float,
        spread_type: str,
        target_delta: float,
        dte: int
    ) -> Dict:
        """Simulate options spread when real data not available"""
        
        # Base IV from IV rank
        base_iv = 0.15 + (iv_rank / 100) * 0.35  # 15% to 50% IV range
        
        # Volatility smile adjustment
        otm_iv_mult = 1.1 if iv_rank > 70 else 1.05
        
        if spread_type == 'call_credit':
            # Call spread above market
            short_strike = current_price * (1 + 0.02)  # 2% OTM
            long_strike = short_strike + 5
            
            # Simulate prices using Black-Scholes approximation
            short_iv = base_iv * otm_iv_mult
            short_price = self._black_scholes_call(
                current_price, short_strike, 0.05, dte/365, short_iv
            )
            
            long_iv = base_iv * otm_iv_mult * 1.02  # Further OTM = higher IV
            long_price = self._black_scholes_call(
                current_price, long_strike, 0.05, dte/365, long_iv
            )
            
        else:  # put_credit
            # Put spread below market
            short_strike = current_price * (1 - 0.02)  # 2% OTM
            long_strike = short_strike - 5
            
            short_iv = base_iv * otm_iv_mult
            short_price = self._black_scholes_put(
                current_price, short_strike, 0.05, dte/365, short_iv
            )
            
            long_iv = base_iv * otm_iv_mult * 1.02
            long_price = self._black_scholes_put(
                current_price, long_strike, 0.05, dte/365, long_iv
            )
            
        credit = short_price - long_price
        
        return {
            'short_strike': round(short_strike, 0),
            'long_strike': round(long_strike, 0),
            'short_option': {
                'strike': short_strike,
                'mid': short_price,
                'implied_volatility': short_iv
            },
            'long_option': {
                'strike': long_strike,
                'mid': long_price,
                'implied_volatility': long_iv
            },
            'credit': credit,
            'dte': dte,
            'spread_width': 5,
            'is_simulated': True
        }
        
    def _black_scholes_call(self, S, K, r, T, sigma):
        """Simple Black-Scholes call pricing"""
        from scipy.stats import norm
        
        d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
        
    def _black_scholes_put(self, S, K, r, T, sigma):
        """Simple Black-Scholes put pricing"""
        from scipy.stats import norm
        
        d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        
        return K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)


# Test the enhanced fetcher
async def test_enhanced_fetcher():
    """Test the enhanced data fetcher"""
    print("Testing Enhanced Data Fetcher...")
    
    fetcher = EnhancedDataFetcher()
    
    # Test dates
    test_cases = [
        ('SPY', datetime(2024, 11, 5)),  # Recent with Alpaca options
        ('SPY', datetime(2023, 10, 15)), # Before Alpaca options
        ('QQQ', datetime(2024, 8, 5)),   # Known high volatility date
    ]
    
    for symbol, date in test_cases:
        print(f"\n{symbol} on {date.strftime('%Y-%m-%d')}:")
        
        # Get market data
        data = await fetcher.get_market_data(symbol, date)
        
        if data:
            print(f"  Price: ${data['current_price']:.2f}")
            print(f"  Daily Move: {data['percent_change']:.2f}%")
            print(f"  IV Rank: {data['iv_rank']:.1f}")
            print(f"  Has Real Options: {data['has_real_options']}")
            
            # Test getting a spread
            spread = await fetcher.get_options_for_spread(
                symbol, date, 'put_credit' if data['percent_change'] > 0 else 'call_credit'
            )
            
            if spread:
                print(f"  Suggested Spread: {spread['short_strike']}/{spread['long_strike']}")
                print(f"  Credit: ${spread['credit']:.2f}")
                print(f"  DTE: {spread['dte']}")
        else:
            print("  No data available")


if __name__ == "__main__":
    asyncio.run(test_enhanced_fetcher())