#!/usr/bin/env python3
"""
Test fetching OPTIONS data specifically
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from datetime import datetime, timedelta
from src.backtest.data_fetcher import AlpacaDataFetcher

async def test_options_fetch():
    print("=== TESTING OPTIONS DATA FETCH ===\n")
    
    fetcher = AlpacaDataFetcher()
    print(f"Options data available from: {fetcher.OPTIONS_DATA_START_DATE}")
    print(f"Has options access: {fetcher.has_options_access}\n")
    
    # Test date after Feb 2024 (when Alpaca options data is available)
    test_date = datetime(2024, 11, 5)
    symbol = "SPY"
    
    print(f"Fetching options chain for {symbol} on {test_date.date()}")
    print("Looking for options expiring 7-14 days out\n")
    
    # Get options chain
    options = await fetcher.get_options_chain(symbol, test_date, dte_min=7, dte_max=14)
    
    print(f"Retrieved {len(options)} option contracts")
    
    if options and len(options) > 0:
        # Check if it's real or simulated
        first_option = options[0]
        
        print(f"\nFirst option contract:")
        for key, value in first_option.items():
            print(f"  {key}: {value}")
        
        # Check data source
        if 'delta' in first_option:
            print(f"\n⚠️  DATA SOURCE: SIMULATED (contains Greeks)")
        else:
            print(f"\n✅ DATA SOURCE: REAL ALPACA OPTIONS DATA")
        
        # Show some call and put examples
        calls = [opt for opt in options if opt['type'] == 'call'][:3]
        puts = [opt for opt in options if opt['type'] == 'put'][:3]
        
        print(f"\nSample CALL options:")
        for call in calls:
            print(f"  {call['symbol']}: Strike ${call['strike']}, Bid ${call['bid']}, Ask ${call['ask']}")
            
        print(f"\nSample PUT options:")
        for put in puts:
            print(f"  {put['symbol']}: Strike ${put['strike']}, Bid ${put['bid']}, Ask ${put['ask']}")
    else:
        print("No options data retrieved")
    
    # Test with a date before options data availability
    print(f"\n\nTesting with date before Feb 2024:")
    old_date = datetime(2023, 11, 5)
    old_options = await fetcher.get_options_chain(symbol, old_date, dte_min=7, dte_max=14)
    
    print(f"Retrieved {len(old_options)} option contracts for {old_date.date()}")
    if old_options:
        print(f"Data source: {'SIMULATED' if 'delta' in old_options[0] else 'REAL'}")

if __name__ == "__main__":
    asyncio.run(test_options_fetch())