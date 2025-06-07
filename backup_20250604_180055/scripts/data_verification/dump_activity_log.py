#!/usr/bin/env python3
"""
Run backtest and dump complete activity log to file
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from datetime import datetime, timedelta
from src.backtest.backtest_engine import BacktestConfig
from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging, ActivityLogEntry

async def run_and_dump_log():
    print("=== RUNNING BACKTEST AND DUMPING ACTIVITY LOG ===\n")
    
    # Collect all activities
    all_activities = []
    all_progress = []
    
    def activity_callback(entry: ActivityLogEntry):
        all_activities.append(entry)
        print(f"[ACTIVITY] {entry.timestamp.strftime('%H:%M:%S')} - {entry.type}: {entry.message}")
    
    def progress_callback(current: int, total: int, message: str):
        all_progress.append((current, total, message, datetime.now()))
        print(f"[PROGRESS] {current}/{total} - {message}")
    
    # Configure backtest with low thresholds to see activity
    config = BacktestConfig(
        start_date=datetime(2024, 11, 1),  # Real data period
        end_date=datetime(2024, 11, 8),    # One week
        symbols=['SPY', 'QQQ'],
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=30,      # Lower threshold
        min_price_move=0.3,  # Lower threshold  
        confidence_threshold=40,  # Lower threshold
        commission_per_contract=0.65,
        use_real_data=True
    )
    
    print(f"Config: {config.start_date.date()} to {config.end_date.date()}")
    print(f"Symbols: {config.symbols}")
    print(f"Thresholds: {config.min_price_move}% move, {config.min_iv_rank} IV, {config.confidence_threshold}% confidence\n")
    
    # Create and run engine
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=activity_callback,
        progress_callback=progress_callback
    )
    
    print("Starting backtest...\n")
    results = await engine.run_backtest()
    
    print(f"\n=== BACKTEST COMPLETE ===")
    print(f"Activities captured: {len(all_activities)}")
    print(f"Progress updates: {len(all_progress)}")
    print(f"Total trades: {results.total_trades}")
    print(f"Total P&L: ${results.total_pnl:.2f}")
    
    # Dump to file
    output_file = "data/test_outputs/complete_activity_dump.txt"
    with open(output_file, "w") as f:
        f.write("=== COMPLETE BACKTEST ACTIVITY LOG ===\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Date Range: {config.start_date.date()} to {config.end_date.date()}\n")
        f.write(f"Symbols: {config.symbols}\n")
        f.write(f"Settings: {config.min_price_move}% move, {config.min_iv_rank} IV, {config.confidence_threshold}% confidence\n\n")
        
        f.write("=== PROGRESS UPDATES ===\n")
        for current, total, message, timestamp in all_progress:
            f.write(f"[{timestamp.strftime('%H:%M:%S')}] {current}/{total} - {message}\n")
        
        f.write(f"\n=== ACTIVITY LOG ({len(all_activities)} entries) ===\n")
        for i, entry in enumerate(all_activities, 1):
            f.write(f"{i:3d}. [{entry.timestamp.strftime('%H:%M:%S')}] {entry.type.upper()}: {entry.message}\n")
            if entry.details:
                f.write(f"     Details: {entry.details}\n")
        
        f.write(f"\n=== RESULTS ===\n")
        f.write(f"Total trades: {results.total_trades}\n")
        f.write(f"Winning trades: {results.winning_trades}\n")
        f.write(f"Losing trades: {results.losing_trades}\n")
        f.write(f"Total P&L: ${results.total_pnl:.2f}\n")
        f.write(f"Max drawdown: {results.max_drawdown:.2f}%\n")
        
        # Check for key activities
        claude_mentions = [a for a in all_activities if 'claude' in a.message.lower()]
        trade_activities = [a for a in all_activities if a.type == 'trade']
        real_data_activities = [a for a in all_activities if 'real data' in a.message.lower()]
        
        f.write(f"\n=== ANALYSIS ===\n")
        f.write(f"Claude AI mentions: {len(claude_mentions)}\n")
        f.write(f"Trade activities: {len(trade_activities)}\n")
        f.write(f"Real data activities: {len(real_data_activities)}\n")
        
        if claude_mentions:
            f.write(f"\nClaude activities:\n")
            for activity in claude_mentions:
                f.write(f"  - {activity.message}\n")
                
        if trade_activities:
            f.write(f"\nTrade activities:\n")
            for activity in trade_activities:
                f.write(f"  - {activity.message}\n")
    
    print(f"\nComplete log saved to: {output_file}")
    
    # Show summary
    print(f"\n=== ACTIVITY SUMMARY ===")
    activity_types = {}
    for activity in all_activities:
        activity_types[activity.type] = activity_types.get(activity.type, 0) + 1
    
    for activity_type, count in activity_types.items():
        print(f"  {activity_type}: {count}")
    
    return len(all_activities) > 0

if __name__ == "__main__":
    # Ensure output directory exists
    os.makedirs("data/test_outputs", exist_ok=True)
    
    result = asyncio.run(run_and_dump_log())
    print(f"\nLog dump {'successful' if result else 'failed'}")