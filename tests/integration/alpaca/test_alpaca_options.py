#!/usr/bin/env python3
"""Test Alpaca Options API access"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, '.')
load_dotenv()

def test_options_api():
    from alpaca.data.historical import OptionHistoricalDataClient
    from alpaca.data.requests import OptionChainRequest, OptionBarsRequest, OptionSnapshotRequest
    from alpaca.data.timeframe import TimeFrame
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    print("Testing Alpaca Options API\n" + "="*50)
    
    try:
        # Initialize client
        print("1. Initializing options client...")
        client = OptionHistoricalDataClient(api_key, secret_key)
        print("   ✅ Options client initialized")
        
        # Test 1: Get options chain
        print("\n2. Testing options chain request...")
        try:
            chain_request = OptionChainRequest(
                underlying_symbol='SPY',
                expiration_date_gte=(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                expiration_date_lte=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            )
            
            chain = client.get_option_chain(chain_request)
            print(f"   ✅ Retrieved {len(chain)} option contracts")
            
            # Show sample contract
            if chain:
                sample_symbol = list(chain.keys())[0]
                sample = chain[sample_symbol]
                print(f"\n   Sample contract: {sample_symbol}")
                print(f"   Strike: ${sample.strike_price}")
                print(f"   Expiration: {sample.expiration_date}")
                if sample.latest_quote:
                    print(f"   Bid: ${sample.latest_quote.bid_price}")
                    print(f"   Ask: ${sample.latest_quote.ask_price}")
                
        except Exception as e:
            print(f"   ❌ Options chain error: {e}")
            
        # Test 2: Get historical bars
        print("\n3. Testing historical options bars...")
        try:
            # Get a specific option symbol for testing
            # SPY option format: SPY251219C00650000 (SPY Dec 19 2025 Call $650)
            bars_request = OptionBarsRequest(
                symbol_or_symbols='SPY241206C00590000',  # Adjust based on current date
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=5)
            )
            
            bars = client.get_option_bars(bars_request)
            if bars:
                print(f"   ✅ Retrieved option bars")
                df = bars.df
                if not df.empty:
                    print(f"   Data points: {len(df)}")
                    print("\n   Latest bar:")
                    print(df.tail(1))
            else:
                print("   ℹ️  No bars data available")
                
        except Exception as e:
            print(f"   ❌ Options bars error: {e}")
            
        # Test 3: Get options snapshot
        print("\n4. Testing options snapshot...")
        try:
            snapshot_request = OptionSnapshotRequest(
                symbol_or_symbols='SPY241206C00590000'  # Adjust based on current date
            )
            
            snapshots = client.get_option_snapshot(snapshot_request)
            if snapshots:
                print(f"   ✅ Retrieved snapshot data")
                for symbol, snapshot in snapshots.items():
                    print(f"\n   Symbol: {symbol}")
                    if snapshot.latest_quote:
                        print(f"   Bid: ${snapshot.latest_quote.bid_price}")
                        print(f"   Ask: ${snapshot.latest_quote.ask_price}")
                    if hasattr(snapshot, 'greeks') and snapshot.greeks:
                        print(f"   Greeks - Delta: {snapshot.greeks.delta}")
            else:
                print("   ℹ️  No snapshot data available")
                
        except Exception as e:
            print(f"   ❌ Snapshot error: {e}")
            
    except Exception as e:
        print(f"\n❌ Failed to initialize options client: {e}")
        print("\nThis might mean:")
        print("- You need an Alpaca subscription that includes options data")
        print("- Your API keys don't have options permissions")
        print("- The options API endpoint is not accessible")

if __name__ == "__main__":
    test_options_api()