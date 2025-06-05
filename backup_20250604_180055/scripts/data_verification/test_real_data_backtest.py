#!/usr/bin/env python3
"""
Test backtest with REAL Alpaca data
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from datetime import datetime, timedelta
from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry
from dotenv import load_dotenv

load_dotenv()

async def test_real_data():
    print("=== TESTING BACKTEST WITH REAL ALPACA DATA ===\n")
    
    # Activity tracking
    activity_log = []
    
    def activity_callback(entry: ActivityLogEntry):
        activity_log.append(entry)
        print(f"[ACTIVITY] {entry.timestamp.strftime('%H:%M:%S')} - {entry.type}: {entry.message}")
    
    def progress_callback(current: int, total: int, message: str):
        if total > 0:
            print(f"[PROGRESS] Day {current}/{total} ({current/total*100:.1f}%) - {message}")
        else:
            print(f"[PROGRESS] {message}")
    
    # Use a recent date range where we should have real data
    config = BacktestConfig(
        start_date=datetime(2024, 11, 1),  # After Alpaca options data availability
        end_date=datetime(2024, 11, 8),    # One week
        symbols=['SPY', 'QQQ'],
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=50,      # Lower threshold to see more activity
        min_price_move=0.5,  # Lower threshold to catch more real moves
        confidence_threshold=60,
        commission_per_contract=0.65,
        use_real_data=True
    )
    
    print(f"Config: {config.start_date.date()} to {config.end_date.date()}")
    print(f"Symbols: {config.symbols}")
    print(f"Using REAL Alpaca data\n")
    
    # Create engine
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    # Run backtest
    try:
        results = await engine.run_backtest()
        
        print(f"\n=== RESULTS ===")
        print(f"Total activity log entries: {len(activity_log)}")
        print(f"Total trades: {results.total_trades}")
        print(f"Total P&L: ${results.total_pnl:.2f}")
        
        # Check for data fetcher initialization
        data_fetcher_initialized = any("Alpaca data fetcher" in entry.message for entry in activity_log)
        real_data_entries = [e for e in activity_log if "Real data:" in e.message]
        
        print(f"\nData source verification:")
        print(f"  Alpaca fetcher initialized: {data_fetcher_initialized}")
        print(f"  Real data entries: {len(real_data_entries)}")
        
        # Show some real data entries
        if real_data_entries:
            print(f"\nSample real data entries:")
            for entry in real_data_entries[:5]:
                print(f"  - {entry.message}")
        
        # Save detailed log
        with open("data/test_outputs/real_data_backtest_log.txt", "w") as f:
            f.write("=== REAL DATA BACKTEST LOG ===\n\n")
            f.write(f"Date range: {config.start_date.date()} to {config.end_date.date()}\n")
            f.write(f"Symbols: {config.symbols}\n\n")
            
            for entry in activity_log:
                f.write(f"[{entry.timestamp}] {entry.type.upper()}: {entry.message}\n")
            
            f.write(f"\n\nTotal entries: {len(activity_log)}")
            f.write(f"\nUsing real data: {data_fetcher_initialized}")
        
        print(f"\nLog saved to: data/test_outputs/real_data_backtest_log.txt")
        
    except Exception as e:
        print(f"\nError during backtest: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Ensure output directory exists
    os.makedirs("data/test_outputs", exist_ok=True)
    
    result = asyncio.run(test_real_data())
    print(f"\nTest {'PASSED' if result else 'FAILED'}")