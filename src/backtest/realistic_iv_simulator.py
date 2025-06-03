"""
More realistic IV rank simulation based on market conditions
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional

class RealisticIVSimulator:
    """Simulate IV rank based on market conditions and historical patterns"""
    
    def __init__(self):
        # Known high IV events (for backtesting)
        self.high_iv_events = {
            # 2025 events
            datetime(2025, 3, 19): "FOMC meeting",          # Fed decision
            datetime(2025, 4, 15): "Tax deadline",          # Annual volatility
            datetime(2025, 1, 31): "Tech earnings",         # Major earnings
            
            # 2024 events
            datetime(2024, 11, 5): "Election uncertainty",  # Presidential election
            datetime(2024, 10, 31): "Tech earnings",        # Major earnings week
            datetime(2024, 8, 5): "Market selloff",         # August volatility
            datetime(2024, 4, 15): "Tax deadline",          # Annual volatility
            datetime(2024, 3, 20): "FOMC meeting",          # Fed decision
            
            # Add earnings seasons (end of each quarter)
            datetime(2025, 1, 25): "Q4 earnings",
            datetime(2025, 4, 25): "Q1 earnings",
            datetime(2024, 10, 25): "Q3 earnings",
        }
        
        # Base IV levels by symbol
        self.base_iv = {
            'SPY': 15,
            'QQQ': 18,
            'IWM': 20,
            'DIA': 14
        }
    
    def calculate_iv_rank(self, symbol: str, date: datetime, 
                         price_move: float, volume_ratio: float = 1.0) -> Dict[str, float]:
        """
        Calculate realistic IV rank based on multiple factors
        
        Args:
            symbol: Stock symbol
            date: Current date
            price_move: Daily price change percentage
            volume_ratio: Current volume / average volume
            
        Returns:
            Dict with iv_rank and confidence
        """
        
        # Start with base IV for the symbol
        base = self.base_iv.get(symbol, 16)
        current_iv = base
        
        # Factor 1: Price move magnitude (biggest factor)
        move_multiplier = 1.0
        abs_move = abs(price_move)
        
        if abs_move > 3.0:
            move_multiplier = 3.0  # Extreme move
            current_iv *= 2.5
        elif abs_move > 2.0:
            move_multiplier = 2.5  # Large move
            current_iv *= 2.0
        elif abs_move > 1.5:
            move_multiplier = 2.0  # Significant move (our threshold)
            current_iv *= 1.8  # This should push IV rank above 70
        elif abs_move > 1.0:
            move_multiplier = 1.5  # Notable move
            current_iv *= 1.5
        else:
            move_multiplier = 0.8  # Small move
            current_iv *= 0.9
        
        # Factor 2: Known events
        event_premium = 0
        for event_date, event_name in self.high_iv_events.items():
            days_to_event = abs((date - event_date).days)
            if days_to_event <= 5:  # Within 5 days of event
                event_premium = max(event_premium, 30 - days_to_event * 5)
                
        # Factor 3: Volume surge (indicates unusual activity)
        if volume_ratio > 2.0:
            current_iv *= 1.2
        elif volume_ratio > 1.5:
            current_iv *= 1.1
            
        # Factor 4: Day of week (Monday/Friday slightly higher)
        if date.weekday() in [0, 4]:  # Monday or Friday
            current_iv *= 1.05
            
        # Factor 5: VIX regime (simulated)
        # In real backtesting, you'd use actual VIX data
        vix_level = self._estimate_vix(date, abs_move)
        if vix_level > 25:
            current_iv *= 1.3
        elif vix_level > 20:
            current_iv *= 1.15
        elif vix_level < 12:
            current_iv *= 0.85
            
        # Add event premium
        current_iv += event_premium
        
        # Calculate IV rank
        # Simulate 52-week range based on symbol
        if symbol == 'SPY':
            iv_low, iv_high = 10, 35
        elif symbol == 'QQQ':
            iv_low, iv_high = 12, 40
        elif symbol == 'IWM':
            iv_low, iv_high = 15, 45
        else:
            iv_low, iv_high = 12, 38
            
        # Ensure current IV is within reasonable bounds
        current_iv = max(iv_low, min(current_iv, iv_high * 1.2))
        
        # Calculate rank
        iv_rank = ((current_iv - iv_low) / (iv_high - iv_low)) * 100
        iv_rank = max(0, min(100, iv_rank))
        
        # Add some noise for realism
        iv_rank += np.random.normal(0, 3)
        iv_rank = max(0, min(100, iv_rank))
        
        # Confidence in our estimate
        confidence = min(95, 50 + move_multiplier * 20)
        
        return {
            'iv_rank': iv_rank,
            'current_iv': current_iv,
            'confidence': confidence,
            'factors': {
                'price_move_impact': move_multiplier,
                'event_premium': event_premium,
                'vix_estimate': vix_level
            }
        }
    
    def _estimate_vix(self, date: datetime, recent_move: float) -> float:
        """Estimate VIX level based on date and recent moves"""
        # Base VIX around 15-16
        base_vix = 15.5
        
        # Add for recent volatility
        base_vix += recent_move * 2
        
        # Seasonal adjustments
        month = date.month
        if month in [9, 10]:  # September/October historically volatile
            base_vix += 2
        elif month in [12, 7]:  # December/July typically calmer
            base_vix -= 1
            
        # Add noise
        base_vix += np.random.normal(0, 1.5)
        
        return max(10, min(40, base_vix))