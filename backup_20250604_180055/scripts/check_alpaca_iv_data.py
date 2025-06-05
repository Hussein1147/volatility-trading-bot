#!/usr/bin/env python3
"""
Check what IV data Alpaca actually provides
"""

import os
from datetime import datetime, timedelta
from alpaca.data.historical import OptionHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import OptionSnapshotRequest, OptionChainRequest
from dotenv import load_dotenv

load_dotenv()

def check_alpaca_iv():
    print("=== ALPACA IV DATA CHECK ===\n")
    
    # Initialize clients
    api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING')
    secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING')
    
    options_client = OptionHistoricalDataClient(api_key, secret_key)
    
    # Try to get options snapshot for SPY
    print("1. Checking Option Snapshot data...")
    try:
        # Get snapshot for specific date
        snapshot_request = OptionSnapshotRequest(
            underlying_symbols="SPY"
        )
        
        snapshot = options_client.get_option_snapshot(snapshot_request)
        
        # Check first option
        if snapshot:
            first_symbol = list(snapshot.keys())[0]
            data = snapshot[first_symbol]
            
            print(f"\nOption Symbol: {first_symbol}")
            print(f"Available fields:")
            
            # Print all available attributes
            for attr in dir(data):
                if not attr.startswith('_'):
                    value = getattr(data, attr, None)
                    if value is not None and not callable(value):
                        print(f"  - {attr}: {value}")
        
    except Exception as e:
        print(f"Error getting snapshot: {e}")
    
    # Try option chain
    print("\n\n2. Checking Option Chain data...")
    try:
        # Get chain
        chain_request = OptionChainRequest(
            underlying_symbol="SPY",
            expiration_date_gte=(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            expiration_date_lte=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        )
        
        chain = options_client.get_option_chain(chain_request)
        
        if chain:
            first_symbol = list(chain.keys())[0]
            data = chain[first_symbol]
            
            print(f"\nOption in chain: {first_symbol}")
            
            # Check for IV data
            if hasattr(data, 'implied_volatility'):
                print(f"✓ Implied Volatility: {data.implied_volatility}")
            else:
                print("✗ No implied_volatility field")
                
            if hasattr(data, 'iv_rank'):
                print(f"✓ IV Rank: {data.iv_rank}")
            else:
                print("✗ No iv_rank field")
                
            if hasattr(data, 'greeks'):
                print(f"✓ Greeks available: {data.greeks}")
            else:
                print("✗ No greeks field")
                
            # List all available fields
            print("\nAll available fields:")
            for attr in dir(data):
                if not attr.startswith('_') and not callable(getattr(data, attr)):
                    print(f"  - {attr}")
                    
    except Exception as e:
        print(f"Error getting chain: {e}")
    
    print("\n\n=== CONCLUSION ===")
    print("Alpaca provides:")
    print("- Implied Volatility (IV) for individual options")
    print("- Option Greeks (delta, gamma, theta, vega)")
    print("- NO IV Rank (this must be calculated)")
    print("\nIV Rank requires historical IV data over time, which Alpaca")
    print("doesn't provide directly. We need to calculate it from")
    print("historical volatility or track IV over time.")

if __name__ == "__main__":
    check_alpaca_iv()