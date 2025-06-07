"""
Delta-based strike selection for professional options trading
"""

from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
from src.core.greeks_calculator import GreeksCalculator

logger = logging.getLogger(__name__)

class DeltaStrikeSelector:
    """
    Select option strikes based on target delta (0.15 for professional strategy)
    """
    
    def __init__(self, target_delta: float = 0.15):
        """
        Initialize strike selector
        
        Args:
            target_delta: Target delta for short strikes (default 0.15)
        """
        self.target_delta = target_delta
        self.greeks_calc = GreeksCalculator()
        
        # Strike increments for different symbols
        self.strike_increments = {
            'SPY': 1.0,
            'QQQ': 1.0,
            'IWM': 1.0,
            'DIA': 1.0,
            'XLE': 0.5,
            'XLK': 1.0,
            # Default for others
            'DEFAULT': 1.0
        }
        
    def select_spread_strikes(self,
                            symbol: str,
                            spot_price: float,
                            spread_type: str,
                            dte: int,
                            volatility: float,
                            spread_width: float = 5.0,
                            options_chain: Optional[List[Dict]] = None) -> Tuple[float, float]:
        """
        Select short and long strikes for a credit spread
        
        Args:
            symbol: Underlying symbol
            spot_price: Current price
            spread_type: 'put_credit' or 'call_credit'
            dte: Days to expiration
            volatility: Implied volatility (as decimal)
            spread_width: Desired spread width in dollars
            options_chain: Optional list of available strikes
            
        Returns:
            (short_strike, long_strike) tuple
        """
        
        # Get strike increment for this symbol
        strike_increment = self.strike_increments.get(symbol, self.strike_increments['DEFAULT'])
        
        # Convert DTE to years
        time_to_expiry = self.greeks_calc.days_to_years(dte)
        
        # Determine option type
        option_type = 'put' if spread_type == 'put_credit' else 'call'
        
        # Find short strike at target delta
        short_strike = self.greeks_calc.find_strike_by_delta(
            spot_price=spot_price,
            target_delta=self.target_delta,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            option_type=option_type,
            strike_increment=strike_increment
        )
        
        if short_strike is None:
            # Fallback to percentage-based selection
            logger.warning(f"Could not find strike at {self.target_delta} delta, using fallback")
            short_strike = self._fallback_strike_selection(
                spot_price, spread_type, volatility, dte
            )
        
        # Calculate long strike based on spread width
        if spread_type == 'put_credit':
            long_strike = short_strike - spread_width
        else:  # call_credit
            long_strike = short_strike + spread_width
            
        # Round to strike increment
        long_strike = round(long_strike / strike_increment) * strike_increment
        
        # Validate strikes if chain provided
        if options_chain:
            short_strike, long_strike = self._validate_strikes_against_chain(
                short_strike, long_strike, spread_type, options_chain
            )
            
        # Calculate actual deltas for logging
        short_delta = self.greeks_calc.calculate_delta(
            spot_price=spot_price,
            strike_price=short_strike,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            option_type=option_type
        )
        
        long_delta = self.greeks_calc.calculate_delta(
            spot_price=spot_price,
            strike_price=long_strike,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            option_type=option_type
        )
        
        logger.info(f"{symbol} {spread_type}: Selected strikes ${short_strike}/{long_strike} "
                   f"with deltas {short_delta:.3f}/{long_delta:.3f}")
        
        return short_strike, long_strike
    
    def _fallback_strike_selection(self, 
                                 spot_price: float,
                                 spread_type: str,
                                 volatility: float,
                                 dte: int) -> float:
        """
        Fallback strike selection using standard deviations
        """
        # Calculate 1-sigma move
        daily_vol = volatility / np.sqrt(252)
        expected_move = spot_price * daily_vol * np.sqrt(dte)
        
        # Target 1.5 standard deviations
        if spread_type == 'put_credit':
            return spot_price - (1.5 * expected_move)
        else:  # call_credit
            return spot_price + (1.5 * expected_move)
    
    def _validate_strikes_against_chain(self,
                                      short_strike: float,
                                      long_strike: float,
                                      spread_type: str,
                                      options_chain: List[Dict]) -> Tuple[float, float]:
        """
        Validate and adjust strikes based on available options chain
        """
        # Extract available strikes
        available_strikes = sorted(list(set(
            opt['strike'] for opt in options_chain 
            if opt['type'] == ('put' if 'put' in spread_type else 'call')
        )))
        
        if not available_strikes:
            return short_strike, long_strike
            
        # Find closest available strikes
        short_strike = min(available_strikes, key=lambda x: abs(x - short_strike))
        long_strike = min(available_strikes, key=lambda x: abs(x - long_strike))
        
        # Ensure minimum spread width
        if abs(short_strike - long_strike) < 1.0:
            if spread_type == 'put_credit':
                # Find next lower strike for long
                lower_strikes = [s for s in available_strikes if s < short_strike]
                if lower_strikes:
                    long_strike = max(lower_strikes)
            else:  # call_credit
                # Find next higher strike for long
                higher_strikes = [s for s in available_strikes if s > short_strike]
                if higher_strikes:
                    long_strike = min(higher_strikes)
                    
        return short_strike, long_strike
    
    def calculate_spread_greeks(self,
                              spot_price: float,
                              short_strike: float,
                              long_strike: float,
                              dte: int,
                              volatility: float,
                              spread_type: str,
                              contracts: int = 1) -> Dict[str, float]:
        """
        Calculate net Greeks for a credit spread
        
        Returns:
            Dictionary with net delta, gamma, theta, vega
        """
        time_to_expiry = self.greeks_calc.days_to_years(dte)
        option_type = 'put' if 'put' in spread_type else 'call'
        
        # Calculate Greeks for short option (we sell this)
        short_greeks = self.greeks_calc.calculate_all_greeks(
            spot_price=spot_price,
            strike_price=short_strike,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            option_type=option_type
        )
        
        # Calculate Greeks for long option (we buy this)
        long_greeks = self.greeks_calc.calculate_all_greeks(
            spot_price=spot_price,
            strike_price=long_strike,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            option_type=option_type
        )
        
        # Net Greeks (short - long) multiplied by contracts and 100
        multiplier = contracts * 100
        
        net_greeks = {
            'delta': (short_greeks['delta'] - long_greeks['delta']) * multiplier,
            'gamma': (short_greeks['gamma'] - long_greeks['gamma']) * multiplier,
            'theta': (short_greeks['theta'] - long_greeks['theta']) * multiplier,
            'vega': (short_greeks['vega'] - long_greeks['vega']) * multiplier,
            'short_delta': short_greeks['delta'],
            'long_delta': long_greeks['delta']
        }
        
        return net_greeks
    
    def find_optimal_width(self,
                         symbol: str,
                         spot_price: float,
                         spread_type: str,
                         dte: int,
                         volatility: float,
                         min_credit_ratio: float = 0.20) -> float:
        """
        Find optimal spread width to achieve minimum credit ratio (credit/width)
        
        Args:
            min_credit_ratio: Minimum credit as percentage of width (default 20%)
            
        Returns:
            Optimal spread width in dollars
        """
        strike_increment = self.strike_increments.get(symbol, 1.0)
        
        # Test different widths
        test_widths = [3, 5, 7, 10, 15, 20]
        
        for width in test_widths:
            # This would need actual option pricing to be accurate
            # For now, use a simple approximation
            credit_estimate = self._estimate_spread_credit(
                spot_price, width, volatility, dte, spread_type
            )
            
            credit_ratio = credit_estimate / (width * 100)
            
            if credit_ratio >= min_credit_ratio:
                return width
                
        # Default to $5 wide
        return 5.0
    
    def _estimate_spread_credit(self,
                              spot_price: float,
                              width: float,
                              volatility: float,
                              dte: int,
                              spread_type: str) -> float:
        """
        Rough estimate of spread credit (would need real option prices)
        """
        # Very rough approximation
        # Credit decreases with width and increases with volatility
        base_credit = spot_price * volatility * np.sqrt(dte/365) * 0.15
        width_factor = 5.0 / width  # Normalize to $5 spread
        
        return base_credit * width_factor * 100  # Convert to dollars

# Import numpy for calculations
import numpy as np