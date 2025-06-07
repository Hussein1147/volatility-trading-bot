#!/usr/bin/env python3
"""
Test delta calculation and strike selection
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.strike_selector import DeltaStrikeSelector
from src.core.greeks_calculator import GreeksCalculator

def test_delta_calculation():
    """Test delta calculation and strike selection"""
    print("\n" + "="*60)
    print("Testing Delta Calculation and Strike Selection")
    print("="*60 + "\n")
    
    # Initialize components
    strike_selector = DeltaStrikeSelector(target_delta=0.15)
    greeks_calc = GreeksCalculator()
    
    # Test parameters
    symbol = 'SPY'
    spot_price = 450.0
    
    print(f"Symbol: {symbol}")
    print(f"Spot Price: ${spot_price:.2f}")
    print(f"Target Delta: 0.15 (85% probability of profit)\n")
    
    # Test different scenarios
    test_cases = [
        {"volatility": 0.15, "dte": 45, "label": "Normal market (15% vol, 45 DTE)"},
        {"volatility": 0.25, "dte": 45, "label": "Elevated vol (25% vol, 45 DTE)"},
        {"volatility": 0.35, "dte": 45, "label": "High vol (35% vol, 45 DTE)"},
        {"volatility": 0.25, "dte": 14, "label": "Income-Pop (25% vol, 14 DTE)"},
        {"volatility": 0.25, "dte": 7, "label": "Weekly (25% vol, 7 DTE)"}
    ]
    
    for test in test_cases:
        print(f"\n{test['label']}")
        print("-" * 50)
        
        # Test PUT credit spread
        put_short, put_long = strike_selector.select_spread_strikes(
            symbol=symbol,
            spot_price=spot_price,
            spread_type='put_credit',
            dte=test['dte'],
            volatility=test['volatility'],
            spread_width=5.0
        )
        
        # Calculate actual delta
        time_to_expiry = greeks_calc.days_to_years(test['dte'])
        put_delta = greeks_calc.calculate_delta(
            spot_price=spot_price,
            strike_price=put_short,
            time_to_expiry=time_to_expiry,
            volatility=test['volatility'],
            option_type='put'
        )
        
        # Calculate all Greeks
        put_greeks = greeks_calc.calculate_all_greeks(
            spot_price=spot_price,
            strike_price=put_short,
            time_to_expiry=time_to_expiry,
            volatility=test['volatility'],
            option_type='put'
        )
        
        print(f"PUT Credit Spread:")
        print(f"  Short Strike: ${put_short:.2f}")
        print(f"  Long Strike: ${put_long:.2f}")
        print(f"  Spread Width: ${put_long - put_short:.2f}")
        print(f"  Distance from spot: ${spot_price - put_short:.2f} ({((spot_price - put_short)/spot_price)*100:.1f}%)")
        print(f"  Greeks for short strike:")
        print(f"    Delta: {put_greeks['delta']:.3f} (target was -0.15)")
        print(f"    Gamma: {put_greeks['gamma']:.4f}")
        print(f"    Theta: ${put_greeks['theta']:.2f}/day")
        print(f"    Vega: ${put_greeks['vega']:.2f}")
        
        # Test CALL credit spread
        call_short, call_long = strike_selector.select_spread_strikes(
            symbol=symbol,
            spot_price=spot_price,
            spread_type='call_credit',
            dte=test['dte'],
            volatility=test['volatility'],
            spread_width=5.0
        )
        
        call_greeks = greeks_calc.calculate_all_greeks(
            spot_price=spot_price,
            strike_price=call_short,
            time_to_expiry=time_to_expiry,
            volatility=test['volatility'],
            option_type='call'
        )
        
        print(f"\nCALL Credit Spread:")
        print(f"  Short Strike: ${call_short:.2f}")
        print(f"  Long Strike: ${call_long:.2f}")
        print(f"  Spread Width: ${call_long - call_short:.2f}")
        print(f"  Distance from spot: ${call_short - spot_price:.2f} ({((call_short - spot_price)/spot_price)*100:.1f}%)")
        print(f"  Greeks for short strike:")
        print(f"    Delta: {call_greeks['delta']:.3f} (target was 0.15)")
        print(f"    Gamma: {call_greeks['gamma']:.4f}")
        print(f"    Theta: ${call_greeks['theta']:.2f}/day")
        print(f"    Vega: ${call_greeks['vega']:.2f}")
    
    # Test edge cases
    print("\n\n" + "="*60)
    print("Testing Edge Cases")
    print("="*60 + "\n")
    
    # Very short DTE
    print("1. Very short DTE (1 day):")
    try:
        put_short, put_long = strike_selector.select_spread_strikes(
            symbol=symbol,
            spot_price=spot_price,
            spread_type='put_credit',
            dte=1,
            volatility=0.25,
            spread_width=5.0
        )
        print(f"   Put spread: ${put_short}/{put_long}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Very high volatility
    print("\n2. Very high volatility (100% annualized):")
    put_short, put_long = strike_selector.select_spread_strikes(
        symbol=symbol,
        spot_price=spot_price,
        spread_type='put_credit',
        dte=45,
        volatility=1.0,
        spread_width=5.0
    )
    print(f"   Put spread: ${put_short}/{put_long}")
    print(f"   Distance from spot: ${spot_price - put_short:.2f} ({((spot_price - put_short)/spot_price)*100:.1f}%)")
    
    print("\n" + "="*60)
    print("Delta Calculation Test Complete")
    print("="*60)

if __name__ == "__main__":
    test_delta_calculation()