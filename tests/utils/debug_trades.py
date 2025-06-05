#!/usr/bin/env python3
"""
Debug trades in backtest results
"""

import streamlit as st
import pandas as pd

def debug_trades():
    """Debug the trades in session state"""
    
    print("=== TRADE DEBUG ===\n")
    
    if 'backtest_results' not in st.session_state:
        print("No backtest results in session state")
        return
        
    results = st.session_state.backtest_results
    
    if not results:
        print("Results are None")
        return
        
    print(f"Total trades in results: {len(results.trades) if hasattr(results, 'trades') else 0}")
    print(f"Total trades metric: {results.total_trades if hasattr(results, 'total_trades') else 0}")
    
    # Count activity log entries
    if 'activity_log' in st.session_state:
        activity_log = st.session_state.activity_log
        opened_count = sum(1 for entry in activity_log if 'OPENED:' in entry.message)
        closed_count = sum(1 for entry in activity_log if 'CLOSED:' in entry.message)
        
        print(f"\nActivity Log:")
        print(f"- OPENED trades: {opened_count}")
        print(f"- CLOSED trades: {closed_count}")
        print(f"- Difference (still open): {opened_count - closed_count}")
        
        # Show sample trades
        print("\nSample OPENED trades:")
        for i, entry in enumerate(activity_log):
            if 'OPENED:' in entry.message:
                print(f"  {entry.message}")
                if i >= 5:  # Show first 5
                    break
                    
        print("\nSample CLOSED trades:")
        for i, entry in enumerate(activity_log):
            if 'CLOSED:' in entry.message:
                print(f"  {entry.message}")
                if i >= 5:  # Show first 5
                    break
    
    # Check trade attributes
    if hasattr(results, 'trades') and results.trades:
        print(f"\nFirst trade details:")
        trade = results.trades[0]
        for attr in ['entry_time', 'exit_time', 'symbol', 'spread_type', 
                     'realized_pnl', 'exit_reason', 'days_in_trade']:
            print(f"  {attr}: {getattr(trade, attr, 'MISSING')}")
        
        # Check how many have exit times
        trades_with_exit = sum(1 for t in results.trades if t.exit_time is not None)
        print(f"\nTrades with exit_time: {trades_with_exit}/{len(results.trades)}")
        
        # Check P&L
        total_pnl = sum(t.realized_pnl for t in results.trades if hasattr(t, 'realized_pnl'))
        print(f"Total P&L from trades: ${total_pnl:.2f}")
        print(f"Results total_pnl: ${results.total_pnl:.2f}")

if __name__ == "__main__":
    # This needs to run inside Streamlit context
    debug_trades()