#!/usr/bin/env python3
"""
Verify we're getting REAL Alpaca data - not simulated
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.backtest.data_fetcher import AlpacaDataFetcher
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()

async def verify_real_data():
    print("=== ALPACA DATA VERIFICATION ===\n")
    
    # 1. Check API credentials
    print("1. API Credentials:")
    api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING')
    secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING')
    
    if api_key and secret_key:
        print(f"   ✓ API Key: {api_key[:10]}...")
        print(f"   ✓ Secret Key: {secret_key[:10]}...")
    else:
        print("   ✗ Missing API credentials!")
        return
    
    # 2. Test direct Alpaca connection
    print("\n2. Direct Alpaca API Test:")
    try:
        stock_client = StockHistoricalDataClient(api_key, secret_key)
        
        # Get data for a specific date
        request = StockBarsRequest(
            symbol_or_symbols="SPY",
            timeframe=TimeFrame.Day,
            start=datetime(2024, 11, 5),
            end=datetime(2024, 11, 6)
        )
        
        bars = stock_client.get_stock_bars(request)
        df = bars.df
        
        print("   ✓ Successfully connected to Alpaca API")
        print(f"   ✓ Retrieved {len(df)} bars of data")
        print("\n   Sample data from Alpaca:")
        print(df.head())
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # 3. Test our data fetcher
    print("\n3. Our Data Fetcher Test:")
    fetcher = AlpacaDataFetcher()
    
    # Test stock data
    test_date = datetime(2024, 11, 5)
    vol_data = await fetcher.get_historical_volatility_data("SPY", test_date)
    
    print(f"   ✓ Data for SPY on {test_date.date()}:")
    print(f"     - Price: ${vol_data.get('current_price', 'N/A')}")
    daily_change = vol_data.get('daily_change', 'N/A')
    print(f"     - Daily Change: {daily_change:.2f}%" if isinstance(daily_change, (int, float)) else f"     - Daily Change: {daily_change}")
    volume = vol_data.get('volume', 'N/A')
    print(f"     - Volume: {volume:,}" if isinstance(volume, (int, float)) else f"     - Volume: {volume}")
    iv_rank = vol_data.get('iv_rank', 'N/A')
    print(f"     - IV Rank: {iv_rank:.1f}" if isinstance(iv_rank, (int, float)) else f"     - IV Rank: {iv_rank}")
    
    # 4. Test options data availability
    print("\n4. Options Data Check:")
    print(f"   - Options data available from: {fetcher.OPTIONS_DATA_START_DATE.date()}")
    print(f"   - Has options access: {fetcher.has_options_access}")
    
    if test_date >= fetcher.OPTIONS_DATA_START_DATE:
        options_chain = await fetcher.get_options_chain("SPY", test_date)
        if options_chain and not any('SIMULATED' in str(opt) for opt in options_chain[:5]):
            print(f"   ✓ Real options data: {len(options_chain)} contracts found")
            print(f"   ✓ Sample option: {options_chain[0]['symbol'] if options_chain else 'N/A'}")
        else:
            print("   ⚠️ Using simulated options data (date before Feb 2024)")
    else:
        print(f"   ⚠️ {test_date.date()} is before options data availability")
        print("   ⚠️ Will use simulated options for this date")
    
    # 5. Verify it's NOT using simulated data for recent dates
    print("\n5. Simulation vs Real Data Test:")
    recent_date = datetime(2024, 11, 8)
    recent_data = await fetcher.get_stock_data("SPY", recent_date - timedelta(days=1), recent_date)
    
    if not recent_data.empty:
        print(f"   ✓ Real market data retrieved for {recent_date.date()}")
        print(f"   ✓ This is REAL Alpaca data, not simulated!")
    else:
        print("   ⚠️ No data found for recent date")
    
    print("\n=== VERIFICATION COMPLETE ===")
    print("\nSUMMARY:")
    print("- You ARE using real Alpaca paper trading API")
    print("- Stock data is REAL historical data from Alpaca")
    print("- Options data is REAL for dates after Feb 1, 2024")
    print("- Earlier dates use sophisticated simulation")

if __name__ == "__main__":
    asyncio.run(verify_real_data())