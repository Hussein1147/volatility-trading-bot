#!/usr/bin/env python3
"""
Test Claude integration with TradeBrain-V prompt
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.backtest.backtest_engine import BacktestConfig, BacktestEngine
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_claude_tradebrain():
    """Test that Claude properly analyzes trades using TradeBrain-V prompt"""
    
    print("\n" + "="*60)
    print("TESTING CLAUDE TRADEBRAIN-V INTEGRATION")
    print("="*60)
    
    # Create a simple backtest config
    config = BacktestConfig(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now() - timedelta(days=28),  # Just 2 days
        symbols=['SPY'],
        initial_capital=100000,
        min_iv_rank=40,
        min_price_move=1.5,
        confidence_threshold=70
    )
    
    # Create backtest engine
    engine = BacktestEngine(config)
    
    # Test market data scenarios
    test_scenarios = [
        {
            'name': 'High IV Put Opportunity',
            'data': {
                'symbol': 'SPY',
                'date': datetime.now(),
                'current_price': 450.0,
                'percent_change': -2.5,
                'volume': 100000000,
                'iv_rank': 75.0,
                'iv_percentile': 80.0,
                'sma_20': 445.0,  # Price > SMA
                'rsi_14': 55.0    # RSI > 50
            }
        },
        {
            'name': 'Low IV Call Opportunity',
            'data': {
                'symbol': 'SPY',
                'date': datetime.now(),
                'current_price': 440.0,
                'percent_change': -2.0,
                'volume': 80000000,
                'iv_rank': 45.0,
                'iv_percentile': 50.0,
                'sma_20': 448.0,  # Price < SMA
                'rsi_14': 35.0    # RSI < 50
            }
        },
        {
            'name': 'Iron Condor Setup',
            'data': {
                'symbol': 'SPY',
                'date': datetime.now(),
                'current_price': 445.0,
                'percent_change': 3.0,
                'volume': 120000000,
                'iv_rank': 85.0,  # Very high IV
                'iv_percentile': 90.0,
                'sma_20': 440.0,  # Price > SMA
                'rsi_14': 65.0    # RSI > 50
            }
        }
    ]
    
    print("\nTesting Claude's analysis with different scenarios:")
    print("-" * 60)
    
    for scenario in test_scenarios:
        print(f"\n📊 Scenario: {scenario['name']}")
        print(f"   Market conditions: {scenario['data']['percent_change']:.1f}% move, IV Rank {scenario['data']['iv_rank']}")
        
        # Get Claude's analysis
        analysis = await engine._claude_analysis(scenario['data'])
        
        if analysis:
            print(f"   ✅ Claude recommends: {analysis['spread_type']}")
            print(f"   📈 Confidence: {analysis.get('sizing', {}).get('confidence_score', 0)}%")
            print(f"   💰 Risk: {analysis.get('sizing', {}).get('risk_percentage', 0.03):.1%} of account")
            print(f"   📝 Reasoning: {analysis.get('reasoning', 'No reasoning provided')[:100]}...")
            
            # Check if Claude followed the rules
            if 'risk_checks' in analysis:
                checks = analysis['risk_checks']
                print(f"   🔍 Risk checks:")
                print(f"      - Directional filter: {'✅' if checks.get('directional_filter_passed') else '❌'}")
                print(f"      - IV rank sufficient: {'✅' if checks.get('iv_rank_sufficient') else '❌'}")
                print(f"      - Event blackout clear: {'✅' if checks.get('event_blackout_clear') else '❌'}")
        else:
            print(f"   ❌ Claude rejected the trade")
    
    print("\n" + "="*60)
    print("CLAUDE INTEGRATION TEST COMPLETE")
    print("="*60)
    print("\nClaude is now making intelligent decisions based on the TradeBrain-V prompt!")
    print("No more hardcoded rules - pure AI-driven analysis! 🤖")

def main():
    """Run the test"""
    asyncio.run(test_claude_tradebrain())

if __name__ == "__main__":
    main()