"""
Credit spread strategy implementation with short-dated options support
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import numpy as np


class CreditSpreadStrategy:
    """Credit spread options strategy with configurable DTE targeting"""
    
    def __init__(
        self,
        dte_target: int = 9,
        delta_target: float = 0.16,
        strike_width: float = 1.0,
    ):
        """
        Initialize credit spread strategy
        
        Args:
            dte_target: Target days to expiration (default 9)
            delta_target: Target delta for short strike selection
            strike_width: Width between strikes in dollars
        """
        self.dte_target = dte_target
        self.delta_target = delta_target
        self.strike_width = strike_width
    
    def select_expiry(self, current_date: datetime) -> datetime:
        """
        Select the nearest Friday expiry >= dte_target days away
        
        Args:
            current_date: Current date for expiry calculation
            
        Returns:
            Expiry date (Friday)
        """
        # Start from tomorrow to avoid same-day expiry
        check_date = current_date + timedelta(days=1)
        
        while True:
            # If it's a Friday and >= dte_target days away
            if check_date.weekday() == 4 and (check_date - current_date).days >= self.dte_target:
                return check_date.replace(hour=16, minute=0, second=0, microsecond=0)
            check_date += timedelta(days=1)
    
    def calculate_strikes(
        self,
        current_price: float,
        spread_type: str,
        delta: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate short and long strikes for the spread
        
        Args:
            current_price: Current underlying price
            spread_type: 'put_credit' or 'call_credit'
            delta: Optional delta override
            
        Returns:
            Tuple of (short_strike, long_strike)
        """
        if spread_type == 'put_credit':
            # Put credit spread: sell higher strike, buy lower
            short_strike = round(current_price * (1 - self.delta_target))
            long_strike = short_strike - self.strike_width
        else:
            # Call credit spread: sell lower strike, buy higher
            short_strike = round(current_price * (1 + self.delta_target))
            long_strike = short_strike + self.strike_width
            
        return (short_strike, long_strike)