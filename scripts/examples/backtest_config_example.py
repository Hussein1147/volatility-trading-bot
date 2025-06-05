#!/usr/bin/env python3
"""Example backtest configuration and quick test"""

from datetime import datetime, timedelta

print("BACKTEST CONFIGURATION GUIDE")
print("="*60)
print("\nRecommended settings for initial testing:")
print("\n1. DATE RANGE:")
print("   - Start: Last 30-60 days for quick test")
print("   - End: Today")
print("   - Note: Options data only available from Feb 2024")

print("\n2. SYMBOLS:")
print("   - Start with 1-2 symbols (e.g., SPY, QQQ)")
print("   - Add more symbols after initial test")

print("\n3. PARAMETERS:")
print("   - Initial Capital: $100,000")
print("   - Max Risk per Trade: 2%")
print("   - Min IV Rank: 70 (high volatility filter)")
print("   - Min Price Move: 2.0% (reduces false signals)")
print("   - Min Confidence: 70% (Claude's confidence threshold)")

print("\n4. EXPECTED BEHAVIOR:")
print("   - Backtest will scan for volatility spikes")
print("   - Claude AI analyzes each opportunity")
print("   - Trades are simulated with realistic P&L")
print("   - Results show equity curve and metrics")

print("\n5. TROUBLESHOOTING:")
print("   - If no trades: Lower min_price_move or min_iv_rank")
print("   - If too many trades: Increase thresholds")
print("   - Check logs in terminal for errors")

print("\n✅ Dashboard is ready at: http://localhost:8502")
print("\nHappy backtesting!")