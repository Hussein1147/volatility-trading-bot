"""
Synthetic option pricing using Black-Scholes model
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SyntheticOptionPricer:
    """
    Black-Scholes based option pricer for synthetic pricing in backtests
    """
    
    def __init__(self, risk_free_rate: float = 0.0):
        """
        Initialize synthetic pricer
        
        Args:
            risk_free_rate: Risk-free rate (default 0 as specified)
        """
        self.r = risk_free_rate
        self._iv_cache: Dict[str, float] = {}
        
    def price_spread(self, 
                    date: pd.Timestamp,
                    underlying_price: float,
                    strikes: Tuple[int, int],
                    expiry: pd.Timestamp,
                    iv: float) -> float:
        """
        Price a credit spread using Black-Scholes
        
        Args:
            date: Current date
            underlying_price: Current price of underlying
            strikes: (short_strike, long_strike) tuple
            expiry: Expiration date
            iv: Implied volatility (as decimal, e.g., 0.20 for 20%)
            
        Returns:
            Net credit/debit of the spread (positive for credit)
        """
        # Calculate time to expiry
        T = (expiry - date).days / 365.0
        
        if T <= 0:
            # Expired - calculate intrinsic value
            return self._intrinsic_value_spread(underlying_price, strikes)
            
        # Unpack strikes
        short_strike, long_strike = strikes
        
        # Determine spread type based on strikes
        # For put credit spreads: sell higher strike, buy lower strike
        # For call credit spreads: sell lower strike, buy higher strike
        # This ensures we receive a net credit
        option_type = 'put'  # We'll determine this based on the intended spread type
        
        # Check if this is intended as a put or call spread
        # Put spread: short strike > long strike (e.g., short 518, long 517)
        # Call spread: short strike < long strike (e.g., short 522, long 523)
        if short_strike > long_strike:
            option_type = 'put'
        else:
            option_type = 'call'
            
        # Price both legs
        short_price = self._black_scholes_price(
            S=underlying_price,
            K=short_strike,
            T=T,
            sigma=iv,
            option_type=option_type
        )
        
        long_price = self._black_scholes_price(
            S=underlying_price,
            K=long_strike,
            T=T,
            sigma=iv,
            option_type=option_type
        )
        
        # Credit spread: we sell short and buy long
        # Net credit is positive when we receive money
        net_credit = short_price - long_price
        
        return net_credit
    
    def calc_delta(self,
                   date: pd.Timestamp,
                   underlying_price: float,
                   strikes: Tuple[int, int],
                   expiry: pd.Timestamp,
                   iv: float) -> Tuple[float, float]:
        """
        Calculate deltas for both legs of a spread
        
        Returns:
            (short_delta, long_delta) tuple
        """
        T = (expiry - date).days / 365.0
        
        if T <= 0:
            # Expired
            return (0.0, 0.0)
            
        short_strike, long_strike = strikes
        
        # Determine option type (same logic as price_spread)
        if short_strike > long_strike:
            option_type = 'put'
        else:
            option_type = 'call'
            
        # Calculate deltas
        short_delta = self._black_scholes_delta(
            S=underlying_price,
            K=short_strike,
            T=T,
            sigma=iv,
            option_type=option_type
        )
        
        long_delta = self._black_scholes_delta(
            S=underlying_price,
            K=long_strike,
            T=T,
            sigma=iv,
            option_type=option_type
        )
        
        return (short_delta, long_delta)
    
    def cache_iv(self, symbol: str, iv: float) -> None:
        """Cache IV for a symbol to avoid recomputation"""
        self._iv_cache[symbol] = iv
        
    def get_cached_iv(self, symbol: str) -> Optional[float]:
        """Get cached IV for a symbol"""
        return self._iv_cache.get(symbol)
    
    def _black_scholes_price(self,
                            S: float,
                            K: float,
                            T: float,
                            sigma: float,
                            option_type: str) -> float:
        """
        Calculate Black-Scholes option price
        
        Args:
            S: Spot price
            K: Strike price
            T: Time to expiry in years
            sigma: Volatility
            option_type: 'call' or 'put'
        """
        if T <= 0:
            # Expired - return intrinsic value
            if option_type == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
                
        # Calculate d1 and d2
        d1 = (np.log(S / K) + (self.r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Calculate option price
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-self.r * T) * norm.cdf(d2)
        else:  # put
            price = K * np.exp(-self.r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
        return price
    
    def _black_scholes_delta(self,
                            S: float,
                            K: float,
                            T: float,
                            sigma: float,
                            option_type: str) -> float:
        """
        Calculate Black-Scholes delta
        
        Returns:
            Delta (-1 to 1)
        """
        if T <= 0:
            # Expired
            if option_type == 'call':
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0
                
        # Calculate d1
        d1 = (np.log(S / K) + (self.r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        
        # Calculate delta
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:  # put
            delta = -norm.cdf(-d1)
            
        return delta
    
    def _intrinsic_value_spread(self,
                               underlying_price: float,
                               strikes: Tuple[int, int]) -> float:
        """
        Calculate intrinsic value of an expired spread
        
        Returns:
            Net value (positive for profit)
        """
        short_strike, long_strike = strikes
        
        if short_strike > long_strike:
            # Put spread: short higher strike, long lower strike
            short_value = max(short_strike - underlying_price, 0)
            long_value = max(long_strike - underlying_price, 0)
        else:
            # Call spread: short lower strike, long higher strike
            short_value = max(underlying_price - short_strike, 0)
            long_value = max(underlying_price - long_strike, 0)
            
        # For a credit spread at expiration:
        # We collected premium initially (positive)
        # At expiration, we owe the intrinsic value difference
        # Net obligation = what we owe on short - what we collect from long
        net_obligation = short_value - long_value
        
        # Return negative of obligation (positive if we keep money, negative if we pay)
        return -net_obligation
    
    def estimate_iv_from_market_conditions(self,
                                         symbol: str,
                                         vix: Optional[float] = None,
                                         historical_vol: Optional[float] = None) -> float:
        """
        Estimate IV based on market conditions
        
        Args:
            symbol: Underlying symbol
            vix: Current VIX level
            historical_vol: 30-day realized volatility
            
        Returns:
            Estimated IV as decimal
        """
        # Check cache first
        cached_iv = self.get_cached_iv(symbol)
        if cached_iv is not None:
            return cached_iv
            
        # Use historical vol if available
        if historical_vol is not None:
            iv = historical_vol
        # Otherwise use VIX as proxy
        elif vix is not None:
            # Adjust VIX for specific symbols
            adjustments = {
                'SPY': 1.0,
                'QQQ': 1.2,  # Tech is more volatile
                'IWM': 1.3,  # Small caps more volatile
                'DIA': 0.9,  # Blue chips less volatile
            }
            adjustment = adjustments.get(symbol, 1.1)
            iv = (vix / 100) * adjustment
        else:
            # Default fallback
            iv = 0.20  # 20% volatility
            
        # Cache the result
        self.cache_iv(symbol, iv)
        
        return iv