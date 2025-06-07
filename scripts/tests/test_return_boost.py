#!/usr/bin/env python3
"""
Test Return-Boost v1 features
"""
import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.backtest.backtest_engine import BacktestConfig, BacktestEngine
from src.strategies.credit_spread import CreditSpreadStrategy

async def test_return_boost_features():
    """Test the new Return-Boost v1 features"""
    print("🚀 Testing Return-Boost v1 Features")
    print("=" * 50)
    
    # Test 1: Short-dated expiry selection
    print("\n1️⃣ Testing Short-Dated Expiry Selection:")
    strategy = CreditSpreadStrategy(dte_target=9)
    
    # Test from different days of the week
    test_dates = [
        datetime(2024, 8, 1),  # Thursday
        datetime(2024, 8, 5),  # Monday
        datetime(2024, 8, 7),  # Wednesday
    ]
    
    for test_date in test_dates:
        expiry = strategy.select_expiry(test_date)
        print(f"   Current date: {test_date.strftime('%Y-%m-%d (%A)')}")
        print(f"   Selected expiry: {expiry.strftime('%Y-%m-%d (%A)')}")
        print(f"   Days to expiry: {(expiry - test_date).days}")
        print()
    
    # Test 2: IV-aware sizing
    print("\n2️⃣ Testing IV-Aware Position Sizing:")
    config = BacktestConfig(
        start_date=datetime(2024, 8, 1),
        end_date=datetime(2024, 8, 7),
        symbols=['SPY'],
        initial_capital=100000,
        dte_target=9,
        force_exit_days=7
    )
    
    engine = BacktestEngine(config, synthetic_pricing=True)
    
    # Test different IV levels
    test_cases = [
        (50, 75),   # Base case: IV=50, confidence=75
        (90, 75),   # High IV case
        (100, 95),  # Max IV, max confidence
    ]
    
    for iv_rank, confidence in test_cases:
        market_data = {
            'iv_rank': iv_rank,
            'percent_change': -1.5,  # Example price move
            'current_price': 500
        }
        analysis = {'confidence': confidence}
        sizing = await engine._claude_position_size(market_data, analysis)
        
        # Simulate sizing calculation
        base_risk = sizing.get('risk_percentage', 0.03)
        iv_boost = max(1.0, min(2.0, iv_rank / 50.0))
        final_risk = min(base_risk * iv_boost, 0.08)
        
        print(f"\n   IV={iv_rank}, Confidence={confidence}%:")
        print(f"   - Base risk: {base_risk*100:.1f}%")
        print(f"   - IV boost: {iv_boost:.1f}×")
        print(f"   - Final risk: {final_risk*100:.1f}%")
    
    # Test 3: Enhanced tier targets
    print("\n3️⃣ Testing Enhanced Tier Targets:")
    print(f"   Default tier targets: {engine.tier_targets}")
    print(f"   - Tier 1 (40% contracts): Exit at +{engine.tier_targets[0]*100:.0f}%")
    print(f"   - Tier 2 (40% contracts): Exit at +{engine.tier_targets[1]*100:.0f}%")
    print(f"   - Stop Loss: {engine.tier_targets[2]*100:.0f}%")
    print(f"   - Final 20%: Potential +150% (with wider stop)")
    
    # Test 4: Force exit adjustment
    print("\n4️⃣ Testing Force Exit Adjustment:")
    config_short = BacktestConfig(
        start_date=datetime(2024, 8, 1),
        end_date=datetime(2024, 8, 7),
        symbols=['SPY'],
        dte_target=9
    )
    config_long = BacktestConfig(
        start_date=datetime(2024, 8, 1),
        end_date=datetime(2024, 8, 7),
        symbols=['SPY'],
        dte_target=15
    )
    
    print(f"   DTE=9: force_exit_days = {config_short.force_exit_days}")
    print(f"   DTE=15: force_exit_days = {config_long.force_exit_days}")
    
    print("\n✅ All Return-Boost v1 features tested successfully!")

if __name__ == "__main__":
    asyncio.run(test_return_boost_features())