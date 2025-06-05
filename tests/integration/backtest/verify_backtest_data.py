#!/usr/bin/env python3
"""
Quick verification that backtest uses real Alpaca data
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from datetime import datetime, timedelta
from src.backtest.data_fetcher import AlpacaDataFetcher

async def verify_data_source():
    fetcher = AlpacaDataFetcher()
    
    # Test with a recent date (should use real data)
    test_date = datetime(2024, 11, 1)
    
    print(f"Testing data fetch for {test_date.date()}...")
    print(f"Alpaca options cutoff date: {fetcher.OPTIONS_DATA_START_DATE.date()}")
    
    # Check if options client initialized
    print(f"Has options access: {fetcher.has_options_access}")
    
    # Get options chain
    options = await fetcher.get_options_chain("SPY", test_date, dte_min=7, dte_max=14)
    
    print(f"\nFetched {len(options)} option contracts")
    
    if options and len(options) > 0:
        sample = options[0]
        print(f"\nSample contract:")
        print(f"  Symbol: {sample.get('symbol')}")
        print(f"  Strike: ${sample.get('strike')}")
        print(f"  Type: {sample.get('type')}")
        print(f"  Bid: ${sample.get('bid')}")
        print(f"  Ask: ${sample.get('ask')}")
        
        # Check if it's real or simulated
        if 'delta' in sample:
            print(f"\n✗ Data source: SIMULATED (contains Greeks)")
        else:
            print(f"\n✓ Data source: REAL ALPACA DATA")

if __name__ == "__main__":
    asyncio.run(verify_data_source())