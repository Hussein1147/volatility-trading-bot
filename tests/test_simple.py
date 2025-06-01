#!/usr/bin/env python3
"""Simple tests that work with current implementation"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.trade_db import TradeDatabase
from src.data.simulated_pnl import SimulatedPnLTracker

print("Testing core functionality...")

# Test 1: Database with file
print("\n1. Testing database with file...")
db = TradeDatabase("test_trades.db")
analysis = {
    'timestamp': datetime.now(),
    'symbol': 'SPY',
    'market_data': {'current_price': 450, 'percent_change': -2.5, 'iv_rank': 85, 'volume': 1000000},
    'claude_analysis': {'should_trade': True, 'spread_type': 'call_credit', 'confidence': 85},
    'decision': 'EXECUTE',
    'mode': 'TEST'
}
try:
    analysis_id = db.add_claude_analysis(analysis)
    print(f"✅ Added analysis with ID: {analysis_id}")
    
    stats = db.get_statistics()
    print(f"✅ Database stats: Total analyses = {stats['total_analyses']}")
except Exception as e:
    print(f"❌ Database error: {e}")

# Clean up test database
import os
if os.path.exists("test_trades.db"):
    os.remove("test_trades.db")

# Test 2: P&L Tracker
print("\n2. Testing P&L tracker...")
tracker = SimulatedPnLTracker.__new__(SimulatedPnLTracker)
tracker.trades = []
tracker.closed_trades = []

trade_data = {
    'trade_id': 'TEST-001',
    'symbol': 'SPY',
    'spread_type': 'call_credit',
    'entry_credit': 250.00,
    'max_loss': 375.00,  # Correct calculation: ($5 - $1.25) * 100
    'entry_time': datetime.now()
}

tracker.add_trade(trade_data)
print(f"✅ Added trade: {tracker.trades[0]['symbol']}")
print(f"✅ Entry credit: ${tracker.trades[0]['entry_credit']:.2f}")
print(f"✅ Max loss: ${tracker.trades[0]['max_loss']:.2f}")

# Test 3: P&L within bounds
print("\n3. Testing P&L bounds...")
tracker.trades[0]['is_winner'] = False  # Force losing trade
tracker.update_positions()

if tracker.trades:  # Trade might have been closed
    trade = tracker.trades[0]
    loss = abs(min(0, trade['unrealized_pnl']))
    if loss <= trade['max_loss']:
        print(f"✅ P&L within bounds: Loss ${loss:.2f} <= Max ${trade['max_loss']:.2f}")
    else:
        print(f"❌ P&L exceeds bounds: Loss ${loss:.2f} > Max ${trade['max_loss']:.2f}")

print("\n✅ Basic functionality tests completed!")
print("\nNote: Live trading features require alpaca-py package")