#!/usr/bin/env python3
"""
Test Alpaca API authentication and permissions
"""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient

load_dotenv()

def test_alpaca_auth():
    """Test Alpaca API authentication and check permissions"""
    
    print("=== TESTING ALPACA API AUTHENTICATION ===\n")
    
    # Check environment variables
    # Try paper trading keys first, then fall back to regular keys
    api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING') or os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING') or os.getenv('ALPACA_SECRET_KEY')
    
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    print(f"Secret Key present: {'Yes' if secret_key else 'No'}")
    
    if api_key:
        print(f"API Key (first 10 chars): {api_key[:10]}...")
    
    if not api_key or not secret_key:
        print("\nERROR: Missing API credentials!")
        return
    
    print("\n1. Testing Trading Client (Paper Trading)...")
    try:
        trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=True
        )
        
        # Get account info
        account = trading_client.get_account()
        print(f"✓ Account Status: {account.status}")
        print(f"✓ Buying Power: ${float(account.buying_power):,.2f}")
        print(f"✓ Cash: ${float(account.cash):,.2f}")
        print(f"✓ Pattern Day Trader: {account.pattern_day_trader}")
        print(f"✓ Options Trading Level: {getattr(account, 'options_trading_level', 'Not Available')}")
        print(f"✓ Options Approved: {getattr(account, 'options_approved_level', 'Not Available')}")
        
    except Exception as e:
        print(f"✗ Trading Client Error: {e}")
    
    print("\n2. Testing Stock Data Client...")
    try:
        stock_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )
        
        # Test fetching SPY quote
        from alpaca.data.requests import StockLatestQuoteRequest
        request = StockLatestQuoteRequest(symbol_or_symbols="SPY")
        quotes = stock_client.get_stock_latest_quote(request)
        
        spy_quote = quotes["SPY"]
        print(f"✓ SPY Latest Quote:")
        print(f"  Bid: ${spy_quote.bid_price} x {spy_quote.bid_size}")
        print(f"  Ask: ${spy_quote.ask_price} x {spy_quote.ask_size}")
        
    except Exception as e:
        print(f"✗ Stock Data Client Error: {e}")
    
    print("\n3. Testing Options Permissions...")
    try:
        # Check if we can access options endpoints
        from alpaca.trading.requests import GetOptionContractsRequest
        
        # Try to get a single options contract
        request = GetOptionContractsRequest(
            underlying_symbols=["SPY"],
            status="active",
            limit=1
        )
        
        contracts = trading_client.get_option_contracts(request)
        print(f"✓ Options Access: ENABLED")
        print(f"✓ Found {len(contracts)} option contracts")
        
    except Exception as e:
        print(f"✗ Options Access: DISABLED")
        print(f"  Error: {e}")
        
        if "unauthorized" in str(e).lower():
            print("\n  ⚠️  Your Alpaca account does not have options trading enabled.")
            print("  ⚠️  To enable options trading:")
            print("     1. Log into your Alpaca account")
            print("     2. Go to Account Settings")
            print("     3. Apply for options trading")
            print("     4. Wait for approval (usually 1-2 business days)")
            print("\n  ℹ️  The backtesting system will use simulated options data.")
    
    print("\n4. Checking Environment...")
    print(f"✓ Paper Trading URL: https://paper-api.alpaca.markets")
    print(f"✓ Live Trading URL: https://api.alpaca.markets")
    
    # Check .env file
    if os.path.exists('.env'):
        print(f"✓ .env file found")
        with open('.env', 'r') as f:
            lines = f.readlines()
            alpaca_vars = [line.strip() for line in lines if 'ALPACA' in line and not line.startswith('#')]
            print(f"✓ Found {len(alpaca_vars)} Alpaca-related variables")
    else:
        print(f"✗ .env file not found")
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_alpaca_auth()