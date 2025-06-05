#!/usr/bin/env python3
"""Test if we can actually fetch real data from Alpaca"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, '.')
load_dotenv()

async def test_alpaca_data():
    from src.backtest.data_fetcher import AlpacaDataFetcher
    
    fetcher = AlpacaDataFetcher()
    
    # Test 1: Check if we have API credentials
    print("1. Checking API credentials...")
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if api_key and secret_key:
        print(f"   ✅ API Key: {api_key[:10]}...")
        print(f"   ✅ Secret Key: {secret_key[:10]}...")
    else:
        print("   ❌ Missing API credentials")
        return
    
    # Test 2: Fetch real stock data
    print("\n2. Testing stock data fetch...")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        df = await fetcher.get_stock_data('SPY', start_date, end_date)
        
        if not df.empty:
            print(f"   ✅ Retrieved {len(df)} days of SPY stock data")
            print(f"   Latest close: ${df['close'].iloc[-1]:.2f}")
            print(f"   Date range: {df.index[0].date()} to {df.index[-1].date()}")
            print(f"   Sample data:")
            print(df.tail(3)[['open', 'high', 'low', 'close', 'volume']])
        else:
            print("   ❌ No stock data retrieved")
    except Exception as e:
        print(f"   ❌ Error fetching stock data: {e}")
    
    # Test 3: Check options data availability
    print("\n3. Testing options data availability...")
    print(f"   Options client available: {fetcher.has_options_access}")
    
    # Test 4: Try to get options chain (will likely use simulation)
    print("\n4. Testing options chain fetch...")
    try:
        options_data = await fetcher.get_options_chain('SPY', datetime.now(), dte_min=7, dte_max=30)
        
        if options_data:
            print(f"   ✅ Retrieved {len(options_data)} option contracts")
            # Check if this is real or simulated data
            if any('delta' in opt for opt in options_data[:5]):
                print(f"   ℹ️  Using SIMULATED options data (contains delta field)")
            else:
                print(f"   ℹ️  Using REAL Alpaca options data")
            
            # Show sample
            sample = options_data[0]
            print(f"   Sample contract: {sample['symbol']}")
            print(f"   Strike: ${sample['strike']}, Type: {sample['type']}")
            print(f"   Bid: ${sample['bid']}, Ask: ${sample['ask']}")
        else:
            print("   ❌ No options data retrieved")
    except Exception as e:
        print(f"   ❌ Error fetching options data: {e}")
    
    # Test 5: Find historical volatility events
    print("\n5. Finding volatility events in last 90 days...")
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        events = await fetcher.find_volatility_events('SPY', start_date, end_date, min_move=1.5)
        
        if events:
            print(f"   ✅ Found {len(events)} volatility events")
            for event in events[-3:]:  # Show last 3
                print(f"   - {event['date']}: {event['symbol']} moved {event['percent_change']:.2f}% (IV Rank: {event['iv_rank']:.1f})")
        else:
            print("   ℹ️  No significant volatility events found")
    except Exception as e:
        print(f"   ❌ Error finding volatility events: {e}")

if __name__ == "__main__":
    print("Testing Alpaca Data Access\n" + "="*50)
    asyncio.run(test_alpaca_data())