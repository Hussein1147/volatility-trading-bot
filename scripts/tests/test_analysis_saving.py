#!/usr/bin/env python3
"""
Test that Claude's analyses are being saved and loaded correctly
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.backtest.backtest_engine import BacktestConfig, BacktestEngine
from src.data.backtest_db import backtest_db

async def test_analysis_saving():
    """Test analysis saving functionality"""
    print("🧪 Testing Analysis Saving Feature")
    print("=" * 50)
    
    # Create a short backtest config
    config = BacktestConfig(
        start_date=datetime(2024, 8, 1),
        end_date=datetime(2024, 8, 7),  # Just one week
        symbols=['SPY'],
        initial_capital=10000,
        max_risk_per_trade=0.02,
        min_iv_rank=40,
        min_price_move=1.5,
        confidence_threshold=70,
        use_real_data=True
    )
    
    # Create engine
    engine = BacktestEngine(
        config,
        synthetic_pricing=True,
        delta_target=0.16
    )
    
    print(f"📊 Running backtest from {config.start_date.date()} to {config.end_date.date()}")
    print(f"   Symbols: {', '.join(config.symbols)}")
    
    # Run backtest
    results = await engine.run_backtest()
    
    print(f"\n✅ Backtest completed")
    print(f"   Total trades: {results.total_trades}")
    print(f"   Analyses captured: {len(engine.all_analyses) if hasattr(engine, 'all_analyses') else 0}")
    
    if hasattr(engine, 'all_analyses') and engine.all_analyses:
        print("\n📋 Sample Analyses:")
        for i, analysis in enumerate(engine.all_analyses[:5]):
            print(f"\n   Analysis #{i+1}:")
            print(f"   - Symbol: {analysis['symbol']}")
            print(f"   - Price: ${analysis['current_price']:.2f}")
            print(f"   - Change: {analysis['percent_change']:.2f}%")
            print(f"   - IV Rank: {analysis['iv_rank']:.1f}")
            print(f"   - Should Trade: {analysis['should_trade']}")
            print(f"   - Confidence: {analysis['confidence']}%")
            if analysis.get('short_strike'):
                print(f"   - Strikes: ${analysis['short_strike']}/{analysis['long_strike']}")
            print(f"   - Reasoning: {analysis['reasoning'][:100]}...")
    
    # Save to database
    if results.total_trades > 0:
        print("\n💾 Saving to database...")
        run_id = backtest_db.save_backtest_run(config, results, notes="Analysis saving test")
        
        # Save analyses
        saved_count = 0
        if hasattr(engine, 'all_analyses'):
            for analysis in engine.all_analyses:
                backtest_db.save_analysis(
                    run_id=run_id,
                    timestamp=analysis['timestamp'],
                    symbol=analysis['symbol'],
                    market_data={
                        'current_price': analysis['current_price'],
                        'percent_change': analysis['percent_change'],
                        'volume': analysis['volume'],
                        'iv_rank': analysis['iv_rank']
                    },
                    analysis={
                        'should_trade': analysis['should_trade'],
                        'spread_type': analysis.get('spread_type'),
                        'short_strike': analysis.get('short_strike'),
                        'long_strike': analysis.get('long_strike'),
                        'contracts': analysis.get('contracts'),
                        'expected_credit': analysis.get('expected_credit'),
                        'confidence': analysis['confidence'],
                        'reasoning': analysis['reasoning']
                    }
                )
                saved_count += 1
        
        print(f"   Run ID: {run_id}")
        print(f"   Analyses saved: {saved_count}")
        
        # Now load them back
        print("\n🔍 Loading analyses from database...")
        loaded_analyses = backtest_db.get_run_analyses(run_id)
        print(f"   Analyses loaded: {len(loaded_analyses)}")
        
        if loaded_analyses:
            print("\n📊 Loaded Analysis Summary:")
            trade_signals = [a for a in loaded_analyses if a['should_trade']]
            no_trade_signals = [a for a in loaded_analyses if not a['should_trade']]
            
            print(f"   - Trade signals: {len(trade_signals)}")
            print(f"   - No-trade signals: {len(no_trade_signals)}")
            
            # Show confidence distribution
            confidences = [a['confidence'] for a in loaded_analyses if a['confidence']]
            if confidences:
                print(f"   - Avg confidence: {sum(confidences)/len(confidences):.1f}%")
                print(f"   - Min confidence: {min(confidences)}%")
                print(f"   - Max confidence: {max(confidences)}%")
    else:
        print("\n⚠️  No trades executed in this period")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_analysis_saving())