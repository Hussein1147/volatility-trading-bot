"""
Options Greeks calculator for delta-based strike selection
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GreeksCalculator:
    """
    Calculate options Greeks using Black-Scholes model
    Used primarily for delta-based strike selection
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize Greeks calculator
        
        Args:
            risk_free_rate: Annual risk-free rate (default 5%)
        """
        self.risk_free_rate = risk_free_rate
        
    def calculate_delta(self, 
                       spot_price: float,
                       strike_price: float,
                       time_to_expiry: float,
                       volatility: float,
                       option_type: str = 'put',
                       dividend_yield: float = 0.0) -> float:
        """
        Calculate option delta using Black-Scholes
        
        Args:
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (annualized)
            option_type: 'call' or 'put'
            dividend_yield: Annual dividend yield
            
        Returns:
            Delta value (-1 to 1)
        """
        
        if time_to_expiry <= 0:
            # Expired option
            if option_type == 'call':
                return 1.0 if spot_price > strike_price else 0.0
            else:
                return -1.0 if spot_price < strike_price else 0.0
                
        # Calculate d1
        d1 = (np.log(spot_price / strike_price) + 
              (self.risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * time_to_expiry) / \
             (volatility * np.sqrt(time_to_expiry))
        
        # Calculate delta
        if option_type == 'call':
            delta = np.exp(-dividend_yield * time_to_expiry) * norm.cdf(d1)
        else:  # put
            delta = -np.exp(-dividend_yield * time_to_expiry) * norm.cdf(-d1)
            
        return delta
    
    def find_strike_by_delta(self,
                           spot_price: float,
                           target_delta: float,
                           time_to_expiry: float,
                           volatility: float,
                           option_type: str = 'put',
                           strike_increment: float = 1.0,
                           max_iterations: int = 50) -> Optional[float]:
        """
        Find the strike price that gives approximately the target delta
        
        Args:
            spot_price: Current price of underlying
            target_delta: Target delta (e.g., -0.15 for 15 delta put)
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            option_type: 'call' or 'put'
            strike_increment: Minimum strike increment (e.g., $1 for SPY)
            max_iterations: Maximum iterations for search
            
        Returns:
            Strike price closest to target delta, or None if not found
        """
        
        # Convert positive delta to negative for puts
        if option_type == 'put' and target_delta > 0:
            target_delta = -target_delta
            
        # Check for valid inputs
        if pd.isna(spot_price) or pd.isna(volatility) or pd.isna(time_to_expiry):
            logger.error(f"Invalid inputs: spot_price={spot_price}, volatility={volatility}, time_to_expiry={time_to_expiry}")
            return None
            
        # Initial guess based on rough approximation
        if option_type == 'put':
            # For puts, start below spot
            strike_guess = spot_price * (1 - abs(target_delta) * volatility * np.sqrt(time_to_expiry))
        else:
            # For calls, start above spot
            strike_guess = spot_price * (1 + abs(target_delta) * volatility * np.sqrt(time_to_expiry))
            
        # Round to strike increment
        strike_guess = round(strike_guess / strike_increment) * strike_increment
        
        # Binary search for the best strike
        best_strike = strike_guess
        best_delta_diff = float('inf')
        
        # Search range
        search_range = int(spot_price * 0.2 / strike_increment)  # 20% range
        
        for offset in range(-search_range, search_range + 1):
            strike = strike_guess + (offset * strike_increment)
            
            if strike <= 0:
                continue
                
            delta = self.calculate_delta(
                spot_price=spot_price,
                strike_price=strike,
                time_to_expiry=time_to_expiry,
                volatility=volatility,
                option_type=option_type
            )
            
            delta_diff = abs(delta - target_delta)
            
            if delta_diff < best_delta_diff:
                best_delta_diff = delta_diff
                best_strike = strike
                
            # If we found exact match, return early
            if delta_diff < 0.001:
                break
                
        # Log the result
        actual_delta = self.calculate_delta(
            spot_price=spot_price,
            strike_price=best_strike,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            option_type=option_type
        )
        
        logger.info(f"Found strike ${best_strike:.2f} with delta {actual_delta:.3f} "
                   f"(target was {target_delta:.3f})")
        
        return best_strike
    
    def calculate_all_greeks(self,
                           spot_price: float,
                           strike_price: float,
                           time_to_expiry: float,
                           volatility: float,
                           option_type: str = 'put') -> Dict[str, float]:
        """
        Calculate all Greeks for an option
        
        Returns:
            Dictionary with delta, gamma, theta, vega, rho
        """
        
        if time_to_expiry <= 0:
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }
            
        # Calculate d1 and d2
        d1 = (np.log(spot_price / strike_price) + 
              (self.risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / \
             (volatility * np.sqrt(time_to_expiry))
        
        d2 = d1 - volatility * np.sqrt(time_to_expiry)
        
        # Calculate Greeks
        if option_type == 'call':
            delta = norm.cdf(d1)
            theta = (-spot_price * norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry)) -
                    self.risk_free_rate * strike_price * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2))
            rho = strike_price * time_to_expiry * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2)
        else:  # put
            delta = -norm.cdf(-d1)
            theta = (-spot_price * norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry)) +
                    self.risk_free_rate * strike_price * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2))
            rho = -strike_price * time_to_expiry * np.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2)
            
        # Greeks that are the same for calls and puts
        gamma = norm.pdf(d1) / (spot_price * volatility * np.sqrt(time_to_expiry))
        vega = spot_price * norm.pdf(d1) * np.sqrt(time_to_expiry)
        
        # Convert theta to daily
        theta = theta / 365
        
        # Convert vega to percentage points
        vega = vega / 100
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }
    
    def days_to_years(self, days: int) -> float:
        """Convert days to years for Black-Scholes calculations"""
        return days / 365.0
    
    def estimate_iv_from_vix(self, vix: float, dte: int) -> float:
        """
        Estimate implied volatility from VIX for a given DTE
        
        Args:
            vix: Current VIX level
            dte: Days to expiration
            
        Returns:
            Estimated IV as decimal (e.g., 0.25 for 25%)
        """
        # VIX is 30-day volatility, adjust for different DTEs
        # This is a simplified approximation
        time_factor = np.sqrt(30 / max(dte, 1))
        return (vix / 100) * time_factor