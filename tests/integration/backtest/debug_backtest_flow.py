#!/usr/bin/env python3
"""
Debug why trades aren't being executed
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry

# Track all activities
all_activities = []

def activity_callback(entry: ActivityLogEntry):
    all_activities.append(entry)
    print(f"[{entry.timestamp.strftime('%H:%M:%S')}] {entry.type.upper()}: {entry.message}")

def progress_callback(current: int, total: int, message: str):
    print(f"Progress: {current}/{total} - {message}")

async def debug_backtest():
    print("=== BACKTEST DEBUG ===\n")
    
    # Simple config
    config = BacktestConfig(
        start_date=datetime(2024, 11, 5),
        end_date=datetime(2024, 11, 6),  # Just 2 days
        symbols=['SPY'],
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=70,  # Original strategy
        min_price_move=1.5,  # Original strategy  
        confidence_threshold=70,
        commission_per_contract=0.65,
        use_real_data=True
    )
    
    # Create engine
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    # First test data fetching directly
    print("\n=== TESTING DATA FETCH ===")
    from src.backtest.data_fetcher import AlpacaDataFetcher
    
    fetcher = AlpacaDataFetcher()
    test_date = datetime(2024, 11, 5)
    
    # Test if we can get any data
    vol_data = await fetcher.get_historical_volatility_data('SPY', test_date)
    print(f"Direct fetch test: {vol_data}")
    
    # Run backtest
    results = await engine.run_backtest()
    
    print("\n=== ACTIVITY ANALYSIS ===")
    
    # Count activities by type
    spike_count = sum(1 for a in all_activities if "spike detected" in a.message)
    claude_count = sum(1 for a in all_activities if "Sending" in a.message and "Claude" in a.message)
    trade_count = sum(1 for a in all_activities if a.type == "trade")
    reject_count = sum(1 for a in all_activities if "rejected" in a.message)
    
    print(f"\nVolatility spikes detected: {spike_count}")
    print(f"Sent to Claude for analysis: {claude_count}")
    print(f"Trades executed: {trade_count}")
    print(f"Trades rejected: {reject_count}")
    
    # Check for issues
    if spike_count > 0 and claude_count == 0:
        print("\n❌ PROBLEM: Volatility spikes detected but nothing sent to Claude!")
        print("This means either:")
        print("1. Price moves are below min_price_move (1.5%)")
        print("2. IV Rank is below min_iv_rank (70)")
        
        # Find the spike activities and check their data
        for activity in all_activities:
            if "Real data" in activity.message:
                print(f"\n{activity.message}")
    
    # Check timing
    start_time = all_activities[0].timestamp if all_activities else None
    end_time = all_activities[-1].timestamp if all_activities else None
    
    if start_time and end_time:
        duration = (end_time - start_time).total_seconds()
        print(f"\nBacktest duration: {duration:.1f} seconds")
        
        if duration < 60 and claude_count > 4:
            print("⚠️ WARNING: Backtest too fast for rate limiting!")

if __name__ == "__main__":
    asyncio.run(debug_backtest())