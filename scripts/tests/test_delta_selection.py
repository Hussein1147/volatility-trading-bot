#!/usr/bin/env python3
"""
Test delta-based strike selection with real Greeks data
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.backtest.data_fetcher import AlpacaDataFetcher
from src.core.strike_selector import DeltaStrikeSelector
from src.core.greeks_calculator import GreeksCalculator

async def test_delta_selection():
    """Test delta-based strike selection"""
    print("\n" + "="*60)
    print("Testing Delta-Based Strike Selection (0.15 Delta Target)")
    print("="*60 + "\n")
    
    # Initialize components
    data_fetcher = AlpacaDataFetcher()
    strike_selector = DeltaStrikeSelector(target_delta=0.15)
    greeks_calc = GreeksCalculator()
    
    # Test parameters
    symbol = 'SPY'
    test_date = datetime(2024, 11, 1)  # Recent date for Alpaca data
    spot_price = 450.0  # Approximate SPY price
    
    print(f"Symbol: {symbol}")
    print(f"Date: {test_date.strftime('%Y-%m-%d')}")
    print(f"Spot Price: ${spot_price:.2f}")
    print(f"Target Delta: 0.15\n")
    
    # Test different volatility scenarios
    test_cases = [
        {"iv_rank": 30, "volatility": 0.15, "label": "Low IV"},
        {"iv_rank": 50, "volatility": 0.20, "label": "Normal IV"},
        {"iv_rank": 75, "volatility": 0.30, "label": "High IV"},
        {"iv_rank": 90, "volatility": 0.40, "label": "Very High IV"}
    ]
    
    for test in test_cases:
        print(f"\n{test['label']} (IV Rank: {test['iv_rank']}, Vol: {test['volatility']*100:.0f}%)")
        print("-" * 40)
        
        # Test PUT credit spread
        put_short, put_long = strike_selector.select_spread_strikes(
            symbol=symbol,
            spot_price=spot_price,
            spread_type='put_credit',
            dte=45,
            volatility=test['volatility'],
            spread_width=5.0
        )
        
        # Calculate actual deltas
        time_to_expiry = greeks_calc.days_to_years(45)
        put_delta = greeks_calc.calculate_delta(
            spot_price=spot_price,
            strike_price=put_short,
            time_to_expiry=time_to_expiry,
            volatility=test['volatility'],
            option_type='put'
        )
        
        print(f"PUT Credit Spread:")
        print(f"  Short Strike: ${put_short:.2f} (Δ = {put_delta:.3f})")
        print(f"  Long Strike: ${put_long:.2f}")
        print(f"  Distance from spot: ${spot_price - put_short:.2f} ({((spot_price - put_short)/spot_price)*100:.1f}%)")
        
        # Test CALL credit spread
        call_short, call_long = strike_selector.select_spread_strikes(
            symbol=symbol,
            spot_price=spot_price,
            spread_type='call_credit',
            dte=45,
            volatility=test['volatility'],
            spread_width=5.0
        )
        
        call_delta = greeks_calc.calculate_delta(
            spot_price=spot_price,
            strike_price=call_short,
            time_to_expiry=time_to_expiry,
            volatility=test['volatility'],
            option_type='call'
        )
        
        print(f"\nCALL Credit Spread:")
        print(f"  Short Strike: ${call_short:.2f} (Δ = {call_delta:.3f})")
        print(f"  Long Strike: ${call_long:.2f}")
        print(f"  Distance from spot: ${call_short - spot_price:.2f} ({((call_short - spot_price)/spot_price)*100:.1f}%)")
    
    # Test with real options data
    print("\n\n" + "="*60)
    print("Testing with Real Options Data")
    print("="*60 + "\n")
    
    # Get real options chain
    options_chain = await data_fetcher.get_options_chain(
        symbol=symbol,
        date=test_date,
        dte_min=40,
        dte_max=50
    )
    
    if options_chain:
        print(f"✓ Retrieved {len(options_chain)} options from data source")
        
        # Check if we have Greeks
        options_with_greeks = [opt for opt in options_chain if opt.get('delta') is not None]
        
        if options_with_greeks:
            print(f"✓ Found {len(options_with_greeks)} options with real Greeks")
            
            # Find options close to 0.15 delta
            put_options = [opt for opt in options_with_greeks if opt['type'] == 'put' and opt['delta'] is not None]
            put_options.sort(key=lambda x: abs(abs(x['delta']) - 0.15))
            
            if put_options:
                best_put = put_options[0]
                print(f"\nClosest PUT to 0.15 delta:")
                print(f"  Strike: ${best_put['strike']:.2f}")
                print(f"  Delta: {best_put['delta']:.3f}")
                print(f"  Bid/Ask: ${best_put['bid']:.2f}/${best_put['ask']:.2f}")
                if best_put.get('gamma'):
                    print(f"  Other Greeks: γ={best_put['gamma']:.4f}, θ={best_put.get('theta', 'N/A')}, ν={best_put.get('vega', 'N/A')}")
        else:
            print("✗ No real Greeks found in options data")
            
            # Show sample option without Greeks
            sample = options_chain[0] if options_chain else None
            if sample:
                print(f"\nSample option (no Greeks):")
                print(f"  Symbol: {sample['symbol']}")
                print(f"  Strike: ${sample['strike']:.2f}")
                print(f"  Type: {sample['type']}")
                print(f"  Bid/Ask: ${sample['bid']:.2f}/${sample['ask']:.2f}")
    else:
        print("✗ No options data available")
    
    print("\n" + "="*60)
    print("Delta Selection Test Complete")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_delta_selection())