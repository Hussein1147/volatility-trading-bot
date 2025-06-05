#!/usr/bin/env python3
"""
Simple test to check if we can get options data
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest
from dotenv import load_dotenv

load_dotenv()

# Use paper trading keys
api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING') or os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING') or os.getenv('ALPACA_SECRET_KEY')

print("=== TESTING OPTIONS DATA ACCESS ===\n")

# Test 1: Get option contracts
print("1. Getting option contracts from Trading API...")
trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

request = GetOptionContractsRequest(
    underlying_symbols=['SPY'],
    expiration_date_gte=(datetime.now() + timedelta(days=7)).date(),
    expiration_date_lte=(datetime.now() + timedelta(days=14)).date(),
    status='active',
    limit=5
)

try:
    contracts = list(trading_client.get_option_contracts(request))
    print(f"✓ Found contracts (raw response has {len(contracts)} items)")
    
    # Extract actual contracts
    if contracts and isinstance(contracts[0], tuple):
        _, contract_list = contracts[0]
        print(f"✓ Extracted {len(contract_list)} contracts")
        
        if contract_list:
            first = contract_list[0]
            print(f"\nFirst contract:")
            print(f"  Symbol: {first.get('symbol')}")
            print(f"  Strike: ${first.get('strike_price')}")
            print(f"  Type: {first.get('type')}")
            print(f"  Expiry: {first.get('expiration_date')}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Get option quotes
print("\n2. Getting option quotes from Data API...")
data_client = OptionHistoricalDataClient(api_key=api_key, secret_key=secret_key)

# Use a known option symbol
test_symbol = "SPY250609C00580000"  # SPY June 9 2025 $580 Call
print(f"Testing with symbol: {test_symbol}")

try:
    quote_request = OptionLatestQuoteRequest(symbol_or_symbols=test_symbol)
    quotes = data_client.get_option_latest_quote(quote_request)
    
    if test_symbol in quotes:
        quote = quotes[test_symbol]
        print(f"✓ Got quote:")
        print(f"  Bid: ${quote.bid_price} x {quote.bid_size}")
        print(f"  Ask: ${quote.ask_price} x {quote.ask_size}")
        print(f"  Mid: ${(quote.bid_price + quote.ask_price) / 2:.2f}")
    else:
        print(f"✗ No quote found for {test_symbol}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n=== SUMMARY ===")
print("The backtest system should be using REAL options data for dates after Feb 2024")
print("For earlier dates, it uses simulated data")