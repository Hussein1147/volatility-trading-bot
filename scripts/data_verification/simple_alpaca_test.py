#!/usr/bin/env python3
"""
Simple test to verify Alpaca data fetching
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from datetime import datetime, timedelta
from src.backtest.data_fetcher import AlpacaDataFetcher
import pandas as pd

async def test_data_fetch():
    print("=== SIMPLE ALPACA DATA TEST ===\n")
    
    fetcher = AlpacaDataFetcher()
    
    # Test dates
    test_date = datetime(2024, 11, 5)  # A specific trading day
    symbol = "SPY"
    
    print(f"Testing data fetch for {symbol} on {test_date.date()}")
    
    # Get stock data
    df = await fetcher.get_stock_data(symbol, test_date - timedelta(days=1), test_date + timedelta(days=1))
    
    print(f"\nDataFrame info:")
    print(f"  Shape: {df.shape}")
    print(f"  Index type: {type(df.index)}")
    print(f"  Columns: {list(df.columns)}")
    
    if not df.empty:
        print(f"\nFirst few rows:")
        print(df.head())
        
        # Show how to access the data
        if isinstance(df.index, pd.MultiIndex):
            print(f"\nMultiIndex levels: {df.index.names}")
            # Reset index to work with it
            df_reset = df.reset_index()
            print(f"\nAfter reset_index columns: {list(df_reset.columns)}")
            
            # Filter for our date
            if 'timestamp' in df_reset.columns:
                df_reset['date'] = pd.to_datetime(df_reset['timestamp']).dt.date
                day_data = df_reset[df_reset['date'] == test_date.date()]
                
                if not day_data.empty:
                    print(f"\nData for {test_date.date()}:")
                    print(day_data[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'percent_change']])
                    
                    # Show the percent change
                    for _, row in day_data.iterrows():
                        print(f"\n{row['symbol']} on {row['date']}:")
                        print(f"  Open: ${row['open']:.2f}")
                        print(f"  Close: ${row['close']:.2f}")
                        print(f"  Change: {row['percent_change']:.2f}%")
                        print(f"  Volume: {row['volume']:,}")
        else:
            print("\nSingle index DataFrame")
            # Filter for date
            dates = pd.to_datetime(df.index).date
            day_data = df[dates == test_date.date()]
            if not day_data.empty:
                print(f"\nData for {test_date.date()}:")
                print(day_data)
    
    return not df.empty

if __name__ == "__main__":
    result = asyncio.run(test_data_fetch())
    print(f"\nTest {'PASSED' if result else 'FAILED'}")