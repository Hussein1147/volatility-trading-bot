#!/usr/bin/env python3
"""
Test fetching PUT options specifically
"""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.trading.enums import ContractType
from datetime import datetime, timedelta

load_dotenv()

# Use paper trading keys
api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING') or os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING') or os.getenv('ALPACA_SECRET_KEY')

trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)

# Get PUT options for SPY
request = GetOptionContractsRequest(
    underlying_symbols=['SPY'],
    expiration_date_gte=(datetime.now() + timedelta(days=7)).date(),
    expiration_date_lte=(datetime.now() + timedelta(days=14)).date(),
    status='active',
    type=ContractType.PUT,  # Specifically request PUTs
    limit=10
)

print("Fetching SPY PUT options...")
contracts = list(trading_client.get_option_contracts(request))

print(f"\nFound {len(contracts)} PUT contracts:")

# Debug what we're getting
if contracts:
    print(f"First item type: {type(contracts[0])}")
    if isinstance(contracts[0], tuple):
        print(f"Tuple length: {len(contracts[0])}")
        for i, item in enumerate(contracts[0]):
            print(f"  Item {i}: {type(item)} - {item}")
            if hasattr(item, 'symbol'):
                contract = item
                print(f"\n{contract.symbol}:")
                print(f"  Strike: ${contract.strike_price}")
                print(f"  Expiry: {contract.expiration_date}")
                print(f"  Type: {contract.type}")
                print(f"  Open Interest: {contract.open_interest}")