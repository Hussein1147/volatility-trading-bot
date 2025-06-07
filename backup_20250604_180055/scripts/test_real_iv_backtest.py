"""
Test backtest with real historical IV rank data
"""

import asyncio
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest.backtest_engine_with_logging import BacktestEngineWithLogging
from src.backtest.backtest_engine import BacktestConfig
from src.backtest.historical_iv_database import get_historical_iv_rank

def print_activity(entry):
    """Print activity log entries"""
    time_str = entry.timestamp.strftime("%H:%M:%S")
    icon = {
        "info": "ℹ️",
        "trade": "💰",
        "warning": "⚠️",
        "error": "❌"
    }.get(entry.type, "📝")
    
    print(f"{time_str} {icon} {entry.message}")

def print_progress(current, total, message):
    """Print progress updates"""
    if total > 0:
        pct = (current / total) * 100
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r[{bar}] {pct:.1f}% - {message}", end="", flush=True)

async def test_real_iv_backtest():
    """Test backtesting with real IV data"""
    print("=" * 80)
    print("TESTING BACKTEST WITH REAL HISTORICAL IV RANK DATA")
    print("=" * 80)
    
    # First, let's verify we have IV data for our test period
    print("\n1. Verifying IV data availability:")
    
    test_dates = [
        datetime(2024, 8, 5),   # Market selloff - high IV
        datetime(2024, 7, 15),  # Summer doldrums - low IV
        datetime(2024, 10, 31), # Tech earnings - elevated IV
        datetime(2023, 3, 10),  # SVB collapse - very high IV
    ]
    
    for date in test_dates:
        spy_iv = get_historical_iv_rank('SPY', date)
        qqq_iv = get_historical_iv_rank('QQQ', date)
        print(f"  {date.strftime('%Y-%m-%d')}: SPY={spy_iv:.0f}, QQQ={qqq_iv:.0f}")
    
    # Configure backtest for a period with known volatility events
    print("\n2. Running backtest for August 2024 (includes market selloff):")
    
    config = BacktestConfig(
        start_date=datetime(2024, 8, 1),
        end_date=datetime(2024, 8, 10),  # Short period for testing
        symbols=['SPY', 'QQQ'],
        initial_capital=10000,
        max_risk_per_trade=0.02,  # 2% risk
        min_iv_rank=70,  # Only trade when IV rank > 70
        min_price_move=1.5,  # 1.5% minimum move
        confidence_threshold=70,
        use_real_data=True
    )
    
    # Create engine with callbacks
    engine = BacktestEngineWithLogging(
        config,
        activity_callback=print_activity,
        progress_callback=print_progress
    )
    
    # Run backtest
    print("\n3. Starting backtest...")
    results = await engine.run_backtest()
    
    print("\n\n4. Backtest Results:")
    print(f"  Total P&L: ${results.total_pnl:,.2f}")
    print(f"  Total Trades: {results.total_trades}")
    print(f"  Win Rate: {results.win_rate:.1f}%")
    print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {results.max_drawdown:.2f}%")
    
    # Show trades with IV ranks
    if results.trades:
        print("\n5. Trades with Real IV Ranks:")
        for trade in results.trades:
            # Get IV rank for the trade date
            iv_rank = get_historical_iv_rank(trade.symbol, trade.entry_time)
            print(f"  {trade.entry_time.strftime('%Y-%m-%d')} {trade.symbol}:")
            print(f"    IV Rank: {iv_rank:.0f}")
            print(f"    Spread: {trade.spread_type} {trade.short_strike}/{trade.long_strike}")
            print(f"    P&L: ${trade.realized_pnl:.2f}")
    
    # Test a longer period with more variety
    print("\n\n6. Running extended backtest (Q3 2024):")
    
    config_extended = BacktestConfig(
        start_date=datetime(2024, 7, 1),
        end_date=datetime(2024, 9, 30),
        symbols=['SPY', 'QQQ', 'IWM'],
        initial_capital=25000,
        max_risk_per_trade=0.02,
        min_iv_rank=65,  # Lower threshold
        min_price_move=1.5,
        confidence_threshold=70,
        use_real_data=True
    )
    
    engine_extended = BacktestEngineWithLogging(config_extended)
    results_extended = await engine_extended.run_backtest()
    
    print(f"\nExtended Results (Q3 2024):")
    print(f"  Total P&L: ${results_extended.total_pnl:,.2f}")
    print(f"  Total Trades: {results_extended.total_trades}")
    print(f"  Win Rate: {results_extended.win_rate:.1f}%")
    
    # Show IV rank distribution of trades
    if results_extended.trades:
        iv_ranks = []
        for trade in results_extended.trades:
            iv_rank = get_historical_iv_rank(trade.symbol, trade.entry_time)
            if iv_rank:
                iv_ranks.append(iv_rank)
        
        if iv_ranks:
            print(f"\n  IV Rank Statistics:")
            print(f"    Average: {sum(iv_ranks)/len(iv_ranks):.1f}")
            print(f"    Min: {min(iv_ranks):.0f}")
            print(f"    Max: {max(iv_ranks):.0f}")
            print(f"    Trades by IV Rank:")
            print(f"      65-70: {sum(1 for iv in iv_ranks if 65 <= iv < 70)}")
            print(f"      70-80: {sum(1 for iv in iv_ranks if 70 <= iv < 80)}")
            print(f"      80+: {sum(1 for iv in iv_ranks if iv >= 80)}")

if __name__ == "__main__":
    asyncio.run(test_real_iv_backtest())