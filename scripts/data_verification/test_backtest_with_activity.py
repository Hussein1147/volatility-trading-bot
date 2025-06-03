#!/usr/bin/env python3
"""
Test backtest with guaranteed activity
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from datetime import datetime, timedelta
from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry
import numpy as np

# Override the _get_historical_data method to generate more events
class TestBacktestEngine(BacktestEngineWithLogging):
    async def _get_historical_data(self, symbol: str, date: datetime):
        """Override to generate more frequent events"""
        # 50% chance of volatility event instead of 5%
        random_event = np.random.random()
        if random_event < 0.5:  # 50% chance
            percent_change = np.random.choice([-3, -2.5, -2, 2, 2.5, 3])
            iv_rank = np.random.uniform(70, 95)
            
            self.log_activity("info", f"Market data for {symbol}: {percent_change:.2f}% move, IV Rank: {iv_rank:.1f}")
            
            return {
                'symbol': symbol,
                'date': date,
                'current_price': 100 * (1 + percent_change/100),
                'percent_change': percent_change,
                'volume': np.random.randint(1000000, 5000000),
                'iv_rank': iv_rank,
                'iv_percentile': iv_rank + 5
            }
        else:
            self.log_activity("info", f"No significant move in {symbol} on {date.strftime('%Y-%m-%d')}")
        
        return None

async def test_with_activity():
    print("=== TESTING BACKTEST WITH INCREASED ACTIVITY ===\n")
    
    # Activity tracking
    activity_log = []
    
    def activity_callback(entry: ActivityLogEntry):
        activity_log.append(entry)
        print(f"[ACTIVITY] {entry.timestamp.strftime('%H:%M:%S.%f')[:-3]} - {entry.type}: {entry.message}")
    
    def progress_callback(current: int, total: int, message: str):
        print(f"[PROGRESS] {current}/{total} - {message}")
    
    # Configure backtest
    config = BacktestConfig(
        start_date=datetime.now() - timedelta(days=5),
        end_date=datetime.now(),
        symbols=['SPY', 'QQQ'],  # Multiple symbols for more activity
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=60,  # Lower threshold
        min_price_move=1.0,  # Lower threshold
        confidence_threshold=50,  # Lower threshold
        commission_per_contract=0.65,
        use_real_data=True
    )
    
    print(f"Config: {config.start_date.date()} to {config.end_date.date()}")
    print(f"Symbols: {config.symbols}")
    print("Using modified engine with 50% volatility event chance\n")
    
    # Create engine
    engine = TestBacktestEngine(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    # Run backtest
    results = await engine.run_backtest()
    
    print(f"\n=== RESULTS ===")
    print(f"Total activity log entries: {len(activity_log)}")
    print(f"Total trades: {results.total_trades}")
    
    # Show activity breakdown
    activity_types = {}
    for entry in activity_log:
        activity_types[entry.type] = activity_types.get(entry.type, 0) + 1
    
    print(f"\nActivity breakdown:")
    for activity_type, count in activity_types.items():
        print(f"  {activity_type}: {count}")
    
    # Save detailed log
    with open("data/test_outputs/detailed_activity_log.txt", "w") as f:
        f.write("=== DETAILED ACTIVITY LOG ===\n\n")
        for i, entry in enumerate(activity_log):
            f.write(f"{i+1}. [{entry.timestamp}] {entry.type.upper()}: {entry.message}\n")
            if entry.details:
                f.write(f"   Details: {entry.details}\n")
        f.write(f"\nTotal entries: {len(activity_log)}")
    
    print(f"\nDetailed log saved to: data/test_outputs/detailed_activity_log.txt")
    
    return len(activity_log) > 20  # Expect at least 20 log entries

if __name__ == "__main__":
    result = asyncio.run(test_with_activity())
    print(f"\nTest result: {'PASSED' if result else 'FAILED'}")