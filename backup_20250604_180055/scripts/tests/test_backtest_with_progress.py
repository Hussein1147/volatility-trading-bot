#!/usr/bin/env python3
"""
Test the backtesting system with progress monitoring
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_backtest_with_progress():
    """Test backtest with progress updates"""
    
    print("\n=== Testing Backtest Engine with Rate Limiting ===\n")
    
    # Quick test config - 30 days, 1 symbol
    config = BacktestConfig(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
        symbols=['SPY'],
        initial_capital=100000,
        max_risk_per_trade=0.02,
        min_iv_rank=80,  # Higher threshold for fewer trades
        min_price_move=2.5,  # Higher threshold for fewer trades
        confidence_threshold=70
    )
    
    print(f"Backtest Configuration:")
    print(f"- Date Range: {config.start_date.strftime('%Y-%m-%d')} to {config.end_date.strftime('%Y-%m-%d')}")
    print(f"- Symbols: {', '.join(config.symbols)}")
    print(f"- Initial Capital: ${config.initial_capital:,.2f}")
    print(f"- Min Price Move: {config.min_price_move}%")
    print(f"- Min IV Rank: {config.min_iv_rank}")
    print(f"\nNote: Rate limiting is set to 4 requests/minute to avoid API errors")
    print("Processing may take 1-2 minutes for a 30-day backtest...\n")
    
    # Create engine and run backtest
    engine = BacktestEngine(config)
    
    # Track progress
    start_time = time.time()
    last_update = start_time
    
    # Create a progress monitoring task
    async def monitor_progress():
        while True:
            await asyncio.sleep(5)  # Update every 5 seconds
            elapsed = time.time() - start_time
            trades = len(engine.results.trades)
            open_positions = len(engine.open_positions)
            
            print(f"\rProgress: {elapsed:.0f}s elapsed | {trades} trades completed | {open_positions} positions open", end='', flush=True)
            
            # Check if we're rate limited
            if engine.last_api_calls:
                api_calls_last_minute = len([t for t in engine.last_api_calls if time.time() - t < 60])
                if api_calls_last_minute >= engine.max_api_calls_per_minute:
                    print(f" | Rate limit active", end='', flush=True)
    
    # Start monitoring
    monitor_task = asyncio.create_task(monitor_progress())
    
    try:
        # Run backtest
        results = await engine.run_backtest()
        
        # Cancel monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
            
        # Clear the progress line
        print("\r" + " " * 80 + "\r", end='')
        
        # Print results
        elapsed_time = time.time() - start_time
        print(f"\n=== Backtest Complete in {elapsed_time:.1f} seconds ===\n")
        
        print(f"Performance Summary:")
        print(f"- Total Trades: {results.total_trades}")
        print(f"- Winning Trades: {results.winning_trades}")
        print(f"- Losing Trades: {results.losing_trades}")
        print(f"- Win Rate: {results.win_rate:.1f}%")
        print(f"- Total P&L: ${results.total_pnl:,.2f}")
        print(f"- Profit Factor: {results.profit_factor:.2f}")
        print(f"- Max Drawdown: ${results.max_drawdown:,.2f} ({results.max_drawdown_pct:.1f}%)")
        print(f"- Sharpe Ratio: {results.sharpe_ratio:.2f}")
        print(f"- Avg Days in Trade: {results.avg_days_in_trade:.1f}")
        
        if results.trades:
            print(f"\nSample Trades (First 5):")
            for i, trade in enumerate(results.trades[:5]):
                print(f"{i+1}. {trade.symbol} {trade.spread_type}: "
                      f"${trade.realized_pnl:,.2f} ({trade.days_in_trade} days) - {trade.exit_reason}")
        
        # Test rate limiting
        print(f"\nRate Limiting Stats:")
        print(f"- Max API calls/minute: {engine.max_api_calls_per_minute}")
        print(f"- Total API calls made: {len(engine.last_api_calls)}")
        
        return True
        
    except Exception as e:
        monitor_task.cancel()
        print(f"\n\nERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_rate_limiting():
    """Specifically test the rate limiting functionality"""
    print("\n=== Testing Rate Limiting ===\n")
    
    config = BacktestConfig(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        symbols=['SPY', 'QQQ'],  # Multiple symbols to trigger more API calls
        initial_capital=100000,
        min_iv_rank=70,  # Lower threshold to get more signals
        min_price_move=1.5  # Lower threshold to get more signals
    )
    
    engine = BacktestEngine(config)
    
    # Track API calls
    api_call_times = []
    original_claude_analysis = engine._claude_analysis
    
    async def wrapped_claude_analysis(*args, **kwargs):
        api_call_times.append(time.time())
        return await original_claude_analysis(*args, **kwargs)
    
    engine._claude_analysis = wrapped_claude_analysis
    
    try:
        # Run short backtest
        results = await engine.run_backtest()
        
        print(f"API Call Analysis:")
        print(f"- Total API calls: {len(api_call_times)}")
        
        # Check rate limiting
        for i in range(1, len(api_call_times)):
            time_diff = api_call_times[i] - api_call_times[i-1]
            print(f"- Call {i}: {time_diff:.1f}s after previous")
            
        # Verify no more than 4 calls per minute
        for i in range(len(api_call_times)):
            calls_in_window = sum(1 for t in api_call_times if api_call_times[i] - t < 60 and t <= api_call_times[i])
            assert calls_in_window <= 4, f"Too many API calls in 60s window: {calls_in_window}"
            
        print("\n✓ Rate limiting working correctly!")
        return True
        
    except Exception as e:
        print(f"\n✗ Rate limiting test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("Starting Backtest System Tests")
    print("=" * 50)
    
    # Test 1: Basic backtest with progress
    test1_passed = await test_backtest_with_progress()
    
    # Test 2: Rate limiting
    test2_passed = await test_rate_limiting()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"- Backtest with Progress: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"- Rate Limiting: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    
    all_passed = test1_passed and test2_passed
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)