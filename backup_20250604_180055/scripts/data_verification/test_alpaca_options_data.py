#!/usr/bin/env python3
"""
Test script to pull real Alpaca options data and save to file for verification
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.trading.enums import AssetClass, ContractType
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

load_dotenv()

def test_alpaca_options():
    """Test fetching real options data from Alpaca"""
    
    # Initialize Alpaca client with paper trading keys
    api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING') or os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING') or os.getenv('ALPACA_SECRET_KEY')
    
    trading_client = TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=True  # Use paper trading
    )
    
    # Output file
    output_file = "alpaca_options_data_dump.txt"
    
    with open(output_file, 'w') as f:
        f.write("=== ALPACA OPTIONS DATA TEST ===\n")
        f.write(f"Timestamp: {datetime.now()}\n")
        f.write(f"Environment: Paper Trading\n\n")
        
        # Test symbols
        symbols = ['SPY', 'QQQ']
        
        for symbol in symbols:
            f.write(f"\n{'='*50}\n")
            f.write(f"SYMBOL: {symbol}\n")
            f.write(f"{'='*50}\n")
            
            try:
                # Get options chain for next 30 days, but skip today
                expiration_date_gte = (datetime.now() + timedelta(days=1)).date()
                expiration_date_lte = (datetime.now() + timedelta(days=30)).date()
                
                f.write(f"\nFetching options contracts from {expiration_date_gte} to {expiration_date_lte}\n")
                
                # Get all option contracts
                request = GetOptionContractsRequest(
                    underlying_symbols=[symbol],
                    expiration_date_gte=expiration_date_gte,
                    expiration_date_lte=expiration_date_lte,
                    status='active'
                )
                
                contracts_response = trading_client.get_option_contracts(request)
                
                # Get the actual contracts from the response
                if hasattr(contracts_response, 'option_contracts'):
                    contracts = contracts_response.option_contracts
                else:
                    # Try different ways to access the contracts
                    contracts = []
                    for item in contracts_response:
                        if hasattr(item, 'symbol'):
                            contracts.append(item)
                        elif isinstance(item, tuple) and len(item) > 1:
                            contracts.append(item[1])
                
                f.write(f"Total contracts found: {len(contracts)}\n\n")
                
                # Debug first contract
                if contracts:
                    f.write(f"First contract type: {type(contracts[0])}\n")
                    if hasattr(contracts[0], '__dict__'):
                        f.write(f"First contract attributes: {contracts[0].__dict__.keys()}\n\n")
                
                # Group by expiration date
                expirations = {}
                for contract in contracts:
                    if hasattr(contract, 'expiration_date'):
                        exp_date = contract.expiration_date
                    else:
                        f.write(f"Contract missing expiration_date: {contract}\n")
                        continue
                    if exp_date not in expirations:
                        expirations[exp_date] = {'calls': [], 'puts': []}
                    
                    if contract.type == ContractType.CALL:
                        expirations[exp_date]['calls'].append(contract)
                    else:
                        expirations[exp_date]['puts'].append(contract)
                
                # Display first 3 expiration dates
                for i, (exp_date, options) in enumerate(sorted(expirations.items())[:3]):
                    f.write(f"\nExpiration: {exp_date}\n")
                    f.write(f"Calls: {len(options['calls'])}, Puts: {len(options['puts'])}\n")
                    
                    # Show sample calls
                    f.write("\nSample CALL contracts:\n")
                    for call in sorted(options['calls'], key=lambda x: x.strike_price)[:5]:
                        f.write(f"  {call.symbol}: Strike ${call.strike_price}, ")
                        f.write(f"Open Interest: {call.open_interest}, ")
                        f.write(f"Close: ${call.close_price if call.close_price else 'N/A'}\n")
                    
                    # Show sample puts
                    f.write("\nSample PUT contracts:\n")
                    for put in sorted(options['puts'], key=lambda x: x.strike_price)[:5]:
                        f.write(f"  {put.symbol}: Strike ${put.strike_price}, ")
                        f.write(f"Open Interest: {put.open_interest}, ")
                        f.write(f"Close: ${put.close_price if put.close_price else 'N/A'}\n")
                    
                # Get quotes for a few contracts
                if contracts:
                    f.write(f"\n\nFetching quotes for sample contracts...\n")
                    sample_contracts = contracts[:3]
                    
                    for contract in sample_contracts:
                        try:
                            # Get latest quote
                            from alpaca.data.historical import OptionHistoricalDataClient
                            from alpaca.data.requests import OptionLatestQuoteRequest
                            
                            data_client = OptionHistoricalDataClient(
                                api_key=api_key,
                                secret_key=secret_key
                            )
                            
                            quote_request = OptionLatestQuoteRequest(
                                symbol_or_symbols=contract.symbol
                            )
                            quotes = data_client.get_option_latest_quote(quote_request)
                            
                            if contract.symbol in quotes:
                                quote = quotes[contract.symbol]
                                f.write(f"\n{contract.symbol}:\n")
                                f.write(f"  Type: {contract.type}\n")
                                f.write(f"  Strike: ${contract.strike_price}\n")
                                f.write(f"  Expiry: {contract.expiration_date}\n")
                                f.write(f"  Bid: ${quote.bid_price} x {quote.bid_size}\n")
                                f.write(f"  Ask: ${quote.ask_price} x {quote.ask_size}\n")
                                f.write(f"  Mid: ${(quote.bid_price + quote.ask_price) / 2:.2f}\n")
                                
                        except Exception as e:
                            f.write(f"\n  Error getting quote for {contract.symbol}: {str(e)}\n")
                
            except Exception as e:
                f.write(f"\nError fetching options for {symbol}: {str(e)}\n")
                f.write(f"Error type: {type(e).__name__}\n")
                import traceback
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
        
        f.write(f"\n\n=== TEST COMPLETE ===\n")
        f.write(f"Data saved to: {output_file}\n")
    
    print(f"Options data test complete. Results saved to: {output_file}")
    return output_file

if __name__ == "__main__":
    test_alpaca_options()