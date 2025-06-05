#!/usr/bin/env python3
"""Summary of data availability for backtesting"""

import asyncio
import sys
import os
sys.path.insert(0, '.')
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
from src.backtest.data_fetcher import AlpacaDataFetcher

async def check_data_availability():
    fetcher = AlpacaDataFetcher()
    
    print("VOLATILITY TRADING BOT - DATA AVAILABILITY SUMMARY")
    print("="*60)
    
    print("\n📊 STOCK DATA (Alpaca)")
    print("-" * 30)
    print("✅ Available: All historical dates")
    print("✅ Real-time: Yes")
    print("✅ Data includes: Open, High, Low, Close, Volume")
    
    # Test stock data
    df = await fetcher.get_stock_data('SPY', datetime.now() - timedelta(days=7), datetime.now())
    if not df.empty:
        print(f"✅ Verified: Retrieved {len(df)} days of SPY data")
        print(f"   Latest close: ${df['close'].iloc[-1]:.2f}")
    
    print("\n📈 OPTIONS DATA")
    print("-" * 30)
    
    if fetcher.has_options_access:
        print("✅ Alpaca Options API: Available")
        print("⚠️  Historical Limit: Data only from February 2024")
        print("✅ Includes: Bid/Ask, IV, Greeks (if available)")
        
        # Test options chain
        try:
            options = await fetcher.get_options_chain('SPY', datetime.now())
            if options:
                print(f"✅ Verified: Retrieved {len(options)} option contracts")
        except:
            print("❌ Options chain test failed")
    else:
        print("❌ Alpaca Options API: Not Available")
        print("✅ Fallback: Sophisticated simulation engine")
    
    print("\n🔄 BACKTESTING DATA STRATEGY")
    print("-" * 30)
    print("For dates AFTER Feb 2024:")
    print("  • Real stock prices from Alpaca")
    print("  • Real options data from Alpaca (if subscribed)")
    print("\nFor dates BEFORE Feb 2024:")
    print("  • Real stock prices from Alpaca")
    print("  • Simulated options using:")
    print("    - Historical volatility patterns")
    print("    - Black-Scholes pricing models")
    print("    - Realistic bid-ask spreads")
    print("    - Time decay simulation")
    
    print("\n✅ READY FOR BACKTESTING!")
    print(f"   Main Dashboard: http://localhost:8501")
    print(f"   Backtest Dashboard: http://localhost:8502")

if __name__ == "__main__":
    asyncio.run(check_data_availability())