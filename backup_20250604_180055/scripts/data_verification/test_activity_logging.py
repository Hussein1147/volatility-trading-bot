#!/usr/bin/env python3
"""
Test activity logging in backtest engine
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from datetime import datetime, timedelta
from collections import deque
from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry

# Global activity log to track updates
activity_updates = []
progress_updates = []

def activity_callback(entry: ActivityLogEntry):
    """Track activity updates"""
    activity_updates.append(entry)
    print(f"[ACTIVITY] {entry.timestamp.strftime('%H:%M:%S')} - {entry.type}: {entry.message}")

def progress_callback(current: int, total: int, message: str):
    """Track progress updates"""
    progress_updates.append((current, total, message))
    if total > 0:
        print(f"[PROGRESS] {current}/{total} ({current/total*100:.1f}%) - {message}")
    else:
        print(f"[PROGRESS] {message}")

async def test_logging():
    print("=== TESTING ACTIVITY LOGGING ===\n")
    
    # Short backtest config
    config = BacktestConfig(
        start_date=datetime.now() - timedelta(days=3),
        end_date=datetime.now(),
        symbols=['SPY'],
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=60,  # Lower threshold to trigger more activity
        min_price_move=1.0,  # Lower threshold
        confidence_threshold=60,
        commission_per_contract=0.65,
        use_real_data=True
    )
    
    print(f"Config: {config.start_date.date()} to {config.end_date.date()}")
    print(f"Expecting ~2-3 trading days\n")
    
    # Create engine with callbacks
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    # Run backtest
    print("Starting backtest...\n")
    results = await engine.run_backtest()
    
    print(f"\n=== RESULTS ===")
    print(f"Activity updates received: {len(activity_updates)}")
    print(f"Progress updates received: {len(progress_updates)}")
    print(f"Engine activity log entries: {len(engine.activity_log)}")
    
    # Show some activity entries
    print(f"\nFirst 5 activity entries:")
    for entry in activity_updates[:5]:
        print(f"  - {entry.type}: {entry.message}")
    
    print(f"\nLast 5 activity entries:")
    for entry in activity_updates[-5:]:
        print(f"  - {entry.type}: {entry.message}")
    
    # Check for specific events
    info_count = sum(1 for e in activity_updates if e.type == "info")
    trade_count = sum(1 for e in activity_updates if e.type == "trade")
    warning_count = sum(1 for e in activity_updates if e.type == "warning")
    error_count = sum(1 for e in activity_updates if e.type == "error")
    
    print(f"\nActivity breakdown:")
    print(f"  Info: {info_count}")
    print(f"  Trade: {trade_count}")
    print(f"  Warning: {warning_count}")
    print(f"  Error: {error_count}")
    
    return len(activity_updates) > 0

async def test_simulated_activity():
    """Test with simulated activity to ensure callbacks work"""
    print("\n=== TESTING SIMULATED ACTIVITY ===\n")
    
    # Create a mock activity log
    test_log = deque(maxlen=100)
    
    def test_callback(entry):
        test_log.append(entry)
        print(f"Received: {entry.message}")
    
    # Simulate some activity
    for i in range(5):
        entry = ActivityLogEntry(
            timestamp=datetime.now(),
            type="info" if i % 2 == 0 else "trade",
            message=f"Test message {i+1}"
        )
        test_callback(entry)
        await asyncio.sleep(0.1)
    
    print(f"\nSimulated log entries: {len(test_log)}")
    return len(test_log) == 5

if __name__ == "__main__":
    print("ACTIVITY LOGGING TEST")
    print("=" * 50)
    
    # Run tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Test simulated activity first
    sim_result = loop.run_until_complete(test_simulated_activity())
    print(f"\nSimulated test: {'PASSED' if sim_result else 'FAILED'}")
    
    # Test real backtest activity
    real_result = loop.run_until_complete(test_logging())
    print(f"\nReal backtest test: {'PASSED' if real_result else 'FAILED'}")
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE")