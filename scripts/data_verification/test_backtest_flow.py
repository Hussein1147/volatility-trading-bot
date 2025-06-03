#!/usr/bin/env python3
"""
Test the complete backtest flow with simulated data
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from datetime import datetime, timedelta
from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry

def activity_callback(entry: ActivityLogEntry):
    """Print activity log entries"""
    print(f"[{entry.timestamp.strftime('%H:%M:%S')}] {entry.type.upper()}: {entry.message}")
    if entry.details:
        print(f"  Details: {entry.details}")

def progress_callback(current: int, total: int, message: str):
    """Print progress updates"""
    if total > 0:
        percent = (current / total) * 100
        print(f"Progress: {percent:.1f}% ({current}/{total}) - {message}")
    else:
        print(f"Progress: {message}")

async def test_backtest():
    """Run a simple backtest with callbacks"""
    
    print("=== TESTING BACKTEST WITH ACTIVITY LOG AND PROGRESS ===\n")
    
    # Configure a short backtest
    config = BacktestConfig(
        start_date=datetime.now() - timedelta(days=7),  # Last 7 days
        end_date=datetime.now(),
        symbols=['SPY'],
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=70,
        min_price_move=1.5,
        confidence_threshold=70,
        commission_per_contract=0.65,
        use_real_data=True  # Will use simulated data due to auth
    )
    
    print(f"Configuration:")
    print(f"  Date Range: {config.start_date.date()} to {config.end_date.date()}")
    print(f"  Symbols: {config.symbols}")
    print(f"  Initial Capital: ${config.initial_capital:,.2f}")
    print(f"  Min IV Rank: {config.min_iv_rank}")
    print(f"  Min Price Move: {config.min_price_move}%")
    print()
    
    # Create engine with callbacks
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    print("Starting backtest...\n")
    
    # Run backtest
    results = await engine.run_backtest()
    
    print(f"\n=== BACKTEST RESULTS ===")
    print(f"Total P&L: ${results.total_pnl:.2f}")
    print(f"Total Trades: {results.total_trades}")
    print(f"Winning Trades: {results.winning_trades}")
    print(f"Losing Trades: {results.losing_trades}")
    if results.total_trades > 0:
        print(f"Win Rate: {results.win_rate:.1f}%")
        print(f"Avg Win: ${results.avg_win:.2f}")
        print(f"Avg Loss: ${results.avg_loss:.2f}")
    print(f"Max Drawdown: {results.max_drawdown:.2f}%")
    print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
    
    print(f"\nActivity Log Entries: {len(engine.activity_log)}")
    
    # Save results
    with open("backtest_test_results.txt", "w") as f:
        f.write("=== BACKTEST TEST RESULTS ===\n\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write(f"Config: {config}\n\n")
        f.write(f"Results:\n{results}\n\n")
        f.write(f"Activity Log ({len(engine.activity_log)} entries):\n")
        for entry in engine.activity_log:
            f.write(f"  [{entry.timestamp}] {entry.type}: {entry.message}\n")
            if entry.details:
                f.write(f"    Details: {entry.details}\n")
    
    print(f"\nResults saved to backtest_test_results.txt")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_backtest())