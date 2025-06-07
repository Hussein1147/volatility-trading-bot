#!/usr/bin/env python3
"""
Quick test to verify Claude analyses are saved and loaded in dashboard
"""

import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.data.backtest_db import backtest_db

def check_latest_runs():
    """Check the latest runs and their analyses"""
    print("🔍 Checking Latest Backtest Runs")
    print("=" * 50)
    
    runs = backtest_db.get_backtest_runs(limit=5)
    
    if not runs:
        print("No backtest runs found in database")
        return
    
    print(f"Found {len(runs)} recent runs\n")
    
    for i, run in enumerate(runs):
        print(f"Run #{i+1} (ID: {run['run_id']})")
        print(f"  Date: {run['run_timestamp']}")
        print(f"  Trades: {run['total_trades']}")
        print(f"  P&L: ${run['total_pnl']:.2f}")
        
        # Get analyses for this run
        analyses = backtest_db.get_run_analyses(run['run_id'])
        print(f"  Analyses: {len(analyses)}")
        
        if analyses:
            # Show summary
            trade_signals = sum(1 for a in analyses if a['should_trade'])
            print(f"    - Trade signals: {trade_signals}")
            print(f"    - No-trade signals: {len(analyses) - trade_signals}")
            
            # Show first analysis
            first = analyses[0]
            print(f"    - First analysis: {first['symbol']} @ ${first['current_price']:.2f}")
            print(f"      Confidence: {first['confidence']}%")
            if first['reasoning']:
                print(f"      Reasoning: {first['reasoning'][:80]}...")
        print()

if __name__ == "__main__":
    check_latest_runs()