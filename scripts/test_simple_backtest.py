#!/usr/bin/env python3
"""
Simple backtest to verify system still works after reorganization
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.historical_iv_database import get_historical_iv_rank

async def run_simple_backtest():
    """Run a simple backtest to verify functionality"""
    print("=" * 60)
    print("RUNNING SIMPLE BACKTEST TO VERIFY SYSTEM")
    print("=" * 60)
    
    # Test IV data is available
    print("\n1. Testing IV data availability...")
    test_date = datetime(2024, 8, 5)  # Known high IV date
    spy_iv = get_historical_iv_rank('SPY', test_date)
    print(f"   SPY IV Rank on {test_date.date()}: {spy_iv}")
    
    if spy_iv is None:
        print("   ❌ IV data not available!")
        return False
    else:
        print("   ✅ IV data working correctly")
    
    # Run a very short backtest
    print("\n2. Running 3-day backtest...")
    
    config = BacktestConfig(
        start_date=datetime(2024, 8, 5),
        end_date=datetime(2024, 8, 7),
        symbols=['SPY'],
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=70,
        min_price_move=1.5,
        confidence_threshold=70,
        use_real_data=True
    )
    
    try:
        # Use the basic engine to avoid complexity
        engine = BacktestEngine(config)
        results = await engine.run_backtest()
        
        print(f"\n3. Backtest Results:")
        print(f"   Trades executed: {results.total_trades}")
        print(f"   Total P&L: ${results.total_pnl:,.2f}")
        print(f"   Win rate: {results.win_rate:.1f}%")
        print(f"   Final capital: ${config.initial_capital + results.total_pnl:,.2f}")
        
        print("\n✅ BACKTEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"\n❌ BACKTEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_simple_backtest())
    sys.exit(0 if success else 1)