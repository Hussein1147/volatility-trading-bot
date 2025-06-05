#!/usr/bin/env python3
"""
Test if Alpaca provides Greeks data for options
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionSnapshotRequest, OptionChainRequest
from dotenv import load_dotenv

load_dotenv()

async def test_alpaca_greeks():
    """Check what option data Alpaca provides"""
    print("Testing Alpaca Options Data Fields...")
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ Missing Alpaca API credentials")
        return
        
    try:
        client = OptionHistoricalDataClient(api_key, secret_key)
        
        # Get options chain for SPY
        exp_date_min = datetime.now() + timedelta(days=30)
        exp_date_max = datetime.now() + timedelta(days=45)
        
        request = OptionChainRequest(
            underlying_symbol='SPY',
            expiration_date_gte=exp_date_min.strftime('%Y-%m-%d'),
            expiration_date_lte=exp_date_max.strftime('%Y-%m-%d')
        )
        
        print("\nFetching SPY options chain...")
        chain_data = client.get_option_chain(request)
        
        if chain_data:
            # Get first option to inspect
            first_symbol = next(iter(chain_data))
            snapshot = chain_data[first_symbol]
            
            print(f"\nOption Symbol: {first_symbol}")
            print(f"Snapshot type: {type(snapshot)}")
            
            # Check what attributes are available
            print("\nAvailable attributes:")
            for attr in dir(snapshot):
                if not attr.startswith('_'):
                    try:
                        value = getattr(snapshot, attr)
                        if value is not None and not callable(value):
                            print(f"  {attr}: {value}")
                    except:
                        pass
                        
            # Specifically check for Greeks
            print("\n🔍 Greeks Check:")
            greeks = ['delta', 'gamma', 'theta', 'vega', 'rho']
            for greek in greeks:
                if hasattr(snapshot, greek):
                    value = getattr(snapshot, greek)
                    print(f"  ✅ {greek}: {value}")
                else:
                    print(f"  ❌ {greek}: NOT AVAILABLE")
                    
            # Check if Greeks are in a nested structure
            if hasattr(snapshot, 'greeks'):
                print("\n  📊 Found 'greeks' attribute:")
                print(f"     {snapshot.greeks}")
                
        else:
            print("❌ No options data returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_alpaca_greeks())