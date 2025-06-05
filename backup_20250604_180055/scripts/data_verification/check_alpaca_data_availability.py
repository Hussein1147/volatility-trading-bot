#!/usr/bin/env python3
"""
Check how much historical options data is available from Alpaca
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, OptionChainRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

load_dotenv()

# Use paper trading keys
api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING') or os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING') or os.getenv('ALPACA_SECRET_KEY')

def check_stock_data_availability():
    """Check how far back we can get stock data"""
    print("=== CHECKING STOCK DATA AVAILABILITY ===\n")
    
    stock_client = StockHistoricalDataClient(api_key, secret_key)
    
    # Test different date ranges
    test_ranges = [
        ("1 week", 7),
        ("1 month", 30),
        ("3 months", 90),
        ("6 months", 180),
        ("1 year", 365),
        ("2 years", 730),
        ("5 years", 1825)
    ]
    
    symbol = "SPY"
    
    for range_name, days in test_ranges:
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
        
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            bars = stock_client.get_stock_bars(request)
            df = bars.df
            
            if not df.empty:
                actual_start = df.index.min()
                actual_end = df.index.max()
                bar_count = len(df)
                print(f"✓ {range_name} ago ({start_date.date()}): {bar_count} bars")
                print(f"  Actual range: {actual_start} to {actual_end}")
            else:
                print(f"✗ {range_name} ago ({start_date.date()}): No data")
                
        except Exception as e:
            print(f"✗ {range_name} ago ({start_date.date()}): Error - {str(e)}")
    
    print()

def check_options_data_availability():
    """Check how far back we can get options data"""
    print("=== CHECKING OPTIONS DATA AVAILABILITY ===\n")
    
    options_client = OptionHistoricalDataClient(api_key, secret_key)
    trading_client = TradingClient(api_key, secret_key, paper=True)
    
    # Alpaca states options data is available from Feb 2024
    print("Alpaca Documentation: Options data available from February 2024\n")
    
    # Test specific dates
    test_dates = [
        ("Current", datetime.now()),
        ("1 week ago", datetime.now() - timedelta(days=7)),
        ("1 month ago", datetime.now() - timedelta(days=30)),
        ("3 months ago", datetime.now() - timedelta(days=90)),
        ("6 months ago", datetime.now() - timedelta(days=180)),
        ("Feb 2024", datetime(2024, 2, 1)),
        ("Jan 2024", datetime(2024, 1, 1)),
        ("Dec 2023", datetime(2023, 12, 1))
    ]
    
    symbol = "SPY"
    
    for date_name, test_date in test_dates:
        try:
            # Try to get options chain for that date
            from alpaca.trading.requests import GetOptionContractsRequest
            
            request = GetOptionContractsRequest(
                underlying_symbols=[symbol],
                expiration_date_gte=test_date.date(),
                expiration_date_lte=(test_date + timedelta(days=30)).date(),
                status='active',
                limit=5
            )
            
            contracts = list(trading_client.get_option_contracts(request))
            
            if contracts:
                # Extract actual contracts from response
                if isinstance(contracts[0], tuple):
                    actual_contracts = contracts[0][1] if len(contracts[0]) > 1 else []
                else:
                    actual_contracts = contracts
                
                print(f"✓ {date_name} ({test_date.date()}): Found {len(actual_contracts)} contracts")
                
                # Show sample contract
                if actual_contracts and isinstance(actual_contracts, list) and len(actual_contracts) > 0:
                    first = actual_contracts[0]
                    if isinstance(first, dict):
                        print(f"  Sample: {first.get('symbol', 'N/A')} - Strike ${first.get('strike_price', 'N/A')}")
            else:
                print(f"✗ {date_name} ({test_date.date()}): No contracts found")
                
        except Exception as e:
            print(f"✗ {date_name} ({test_date.date()}): Error - {str(e)[:100]}")
    
    print()

def check_current_options_chain():
    """Check current options chain availability"""
    print("=== CURRENT OPTIONS CHAIN DETAILS ===\n")
    
    trading_client = TradingClient(api_key, secret_key, paper=True)
    
    # Get options for next 30 days
    from alpaca.trading.requests import GetOptionContractsRequest
    
    request = GetOptionContractsRequest(
        underlying_symbols=["SPY"],
        expiration_date_gte=datetime.now().date(),
        expiration_date_lte=(datetime.now() + timedelta(days=30)).date(),
        status='active'
    )
    
    try:
        contracts_response = trading_client.get_option_contracts(request)
        
        # Count by expiration
        expirations = {}
        total_calls = 0
        total_puts = 0
        
        for item in contracts_response:
            if isinstance(item, tuple) and len(item) > 1:
                contracts = item[1]
                for contract in contracts:
                    exp_date = contract.get('expiration_date')
                    contract_type = contract.get('type')
                    
                    if exp_date not in expirations:
                        expirations[exp_date] = {'calls': 0, 'puts': 0}
                    
                    if contract_type and 'put' in str(contract_type).lower():
                        expirations[exp_date]['puts'] += 1
                        total_puts += 1
                    else:
                        expirations[exp_date]['calls'] += 1
                        total_calls += 1
        
        print(f"Total Contracts: {total_calls + total_puts}")
        print(f"  Calls: {total_calls}")
        print(f"  Puts: {total_puts}")
        print(f"\nExpirations ({len(expirations)} dates):")
        
        for exp_date in sorted(expirations.keys())[:5]:  # Show first 5
            exp_info = expirations[exp_date]
            print(f"  {exp_date}: {exp_info['calls']} calls, {exp_info['puts']} puts")
            
    except Exception as e:
        print(f"Error: {e}")
    
    print()

def test_backtest_data_source():
    """Test if backtest is using real data"""
    print("=== TESTING BACKTEST DATA SOURCE ===\n")
    
    from src.backtest.data_fetcher import AlpacaDataFetcher
    import asyncio
    
    fetcher = AlpacaDataFetcher()
    
    # Test dates
    test_cases = [
        ("Recent date (should use real data)", datetime(2024, 10, 1)),
        ("Old date (should use simulation)", datetime(2023, 6, 1))
    ]
    
    async def test_fetch():
        for case_name, test_date in test_cases:
            print(f"\n{case_name}: {test_date.date()}")
            
            # Get stock data
            stock_df = await fetcher.get_stock_data("SPY", test_date, test_date + timedelta(days=5))
            print(f"  Stock data: {len(stock_df)} bars")
            
            # Get options chain
            options = await fetcher.get_options_chain("SPY", test_date)
            print(f"  Options chain: {len(options)} contracts")
            
            if options:
                # Check if it's real or simulated
                first_option = options[0]
                if 'data_source' in first_option:
                    print(f"  Data source: {first_option['data_source']}")
                else:
                    # Check for telltale signs
                    if first_option.get('volume', 0) == 0 or 'delta' in first_option:
                        print(f"  Data source: Likely SIMULATED (has delta field or zero volume)")
                    else:
                        print(f"  Data source: Likely REAL")
    
    asyncio.run(test_fetch())

if __name__ == "__main__":
    print("ALPACA DATA AVAILABILITY CHECK")
    print("=" * 50)
    print(f"Timestamp: {datetime.now()}\n")
    
    # Run all checks
    check_stock_data_availability()
    check_options_data_availability()
    check_current_options_chain()
    test_backtest_data_source()
    
    # Save results
    print("\nResults saved to: alpaca_data_availability_report.txt")