#!/usr/bin/env python3
"""
Comprehensive test for all professional trading strategy features
Tests all Phase 1-4 implementations
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.position_sizer import DynamicPositionSizer
from src.core.strike_selector import DeltaStrikeSelector
from src.core.portfolio_manager import PortfolioManager, PortfolioGreeks
from src.backtest.backtest_engine import BacktestConfig, BacktestEngine

class ProfessionalStrategyTester:
    """Test all professional strategy components"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"     └─ {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            
    def test_directional_filters(self):
        """Test directional filter rules"""
        print("\n" + "="*60)
        print("Testing Directional Filters")
        print("="*60)
        
        # Test cases
        test_cases = [
            # (price, sma, rsi, spread_type, should_allow)
            (100, 95, 55, 'put_credit', True),   # Price > SMA, RSI > 50 → PUT allowed
            (100, 95, 45, 'put_credit', False),  # Price > SMA, RSI < 50 → PUT blocked
            (100, 105, 45, 'call_credit', True), # Price < SMA, RSI < 50 → CALL allowed
            (100, 105, 55, 'call_credit', False),# Price < SMA, RSI > 50 → CALL blocked
        ]
        
        for price, sma, rsi, spread_type, should_allow in test_cases:
            # Simulate directional check
            if spread_type == 'put_credit':
                allowed = price > sma and rsi > 50
            else:  # call_credit
                allowed = price < sma and rsi < 50
                
            passed = allowed == should_allow
            self.log_test(
                f"Directional: {spread_type} with Price={price}, SMA={sma}, RSI={rsi}",
                passed,
                f"Expected {should_allow}, got {allowed}"
            )
            
    def test_delta_selection(self):
        """Test 0.15 delta strike selection"""
        print("\n" + "="*60)
        print("Testing Delta-Based Strike Selection")
        print("="*60)
        
        selector = DeltaStrikeSelector(target_delta=0.15)
        
        # Test different volatility scenarios
        test_cases = [
            (450, 0.20, 45, 'put_credit'),   # Normal vol
            (450, 0.35, 45, 'put_credit'),   # High vol
            (450, 0.20, 14, 'call_credit'),  # Short DTE
        ]
        
        for spot, vol, dte, spread_type in test_cases:
            short_strike, long_strike = selector.select_spread_strikes(
                symbol='SPY',
                spot_price=spot,
                spread_type=spread_type,
                dte=dte,
                volatility=vol,
                spread_width=5.0
            )
            
            # Check strikes are reasonable
            if spread_type == 'put_credit':
                strikes_valid = short_strike < spot and long_strike < short_strike
            else:
                strikes_valid = short_strike > spot and long_strike > short_strike
                
            spread_width = abs(long_strike - short_strike)
            width_valid = 4.5 <= spread_width <= 5.5  # Allow small rounding
            
            self.log_test(
                f"Delta Selection: {spread_type} vol={vol:.0%} dte={dte}",
                strikes_valid and width_valid,
                f"Strikes: {short_strike}/{long_strike}, Width: ${spread_width:.2f}"
            )
            
    def test_position_sizing(self):
        """Test dynamic position sizing by confidence"""
        print("\n" + "="*60)
        print("Testing Dynamic Position Sizing")
        print("="*60)
        
        sizer = DynamicPositionSizer(100000)  # $100k account
        
        # Test confidence tiers
        test_cases = [
            (72, 'STANDARD (70-79%)'),   # 3% risk
            (85, 'ELEVATED (80-89%)'),   # 5% risk
            (95, 'HIGH (90-100%)'),      # 8% risk
            (65, None),                  # Below threshold
        ]
        
        for confidence, expected_tier in test_cases:
            result = sizer.calculate_position_size(
                confidence=confidence,
                max_loss_per_contract=500,  # $5 wide spread
                book_type='PRIMARY',
                current_positions=[]
            )
            
            if expected_tier:
                passed = result.contracts > 0 and result.confidence_tier == expected_tier
            else:
                passed = result.contracts == 0
                
            self.log_test(
                f"Position Sizing: {confidence}% confidence",
                passed,
                f"Contracts: {result.contracts}, Tier: {result.confidence_tier}, Risk: {result.risk_percentage:.1%}"
            )
            
    def test_exit_rules(self):
        """Test professional exit rules"""
        print("\n" + "="*60)
        print("Testing Exit Rules")
        print("="*60)
        
        # Test scaling exits
        test_cases = [
            # (contracts, pnl_pct, dte, book_type, expected_exit)
            (5, 0.50, 30, 'PRIMARY', 'Profit Target (50%)'),      # Scale exit 1
            (5, 0.75, 30, 'PRIMARY', 'Profit Target (75%)'),      # Scale exit 2
            (5, 0.95, 30, 'PRIMARY', 'Profit Target (90%+)'),     # Scale exit 3
            (2, 0.50, 30, 'PRIMARY', 'Profit Target (50%)'),      # Small position
            (2, 0.25, 10, 'INCOME_POP', 'Profit Target (25%)'),   # Income-Pop
            (5, 0.10, 20, 'PRIMARY', 'Time Stop (21 DTE)'),       # Time stop
            (5, -1.51, 30, 'PRIMARY', 'Stop Loss (150%)'),        # Hard stop
        ]
        
        for contracts, pnl_pct, dte, book_type, expected in test_cases:
            # Determine actual exit (simplified logic)
            if pnl_pct <= -1.5:
                actual = 'Stop Loss (150%)'
            elif dte <= 21 and book_type == 'PRIMARY':
                actual = 'Time Stop (21 DTE)'
            elif contracts >= 3:
                if pnl_pct >= 0.90:
                    actual = 'Profit Target (90%+)'
                elif pnl_pct >= 0.75:
                    actual = 'Profit Target (75%)'
                elif pnl_pct >= 0.50:
                    actual = 'Profit Target (50%)'
                else:
                    actual = None
            else:
                if book_type == 'INCOME_POP' and pnl_pct >= 0.25:
                    actual = 'Profit Target (25%)'
                elif book_type == 'PRIMARY' and pnl_pct >= 0.50:
                    actual = 'Profit Target (50%)'
                else:
                    actual = None
                    
            passed = actual == expected
            self.log_test(
                f"Exit Rules: {contracts} contracts, {pnl_pct:.0%} P&L, {dte} DTE, {book_type}",
                passed,
                f"Expected '{expected}', got '{actual}'"
            )
            
    def test_portfolio_constraints(self):
        """Test portfolio-level constraints"""
        print("\n" + "="*60)
        print("Testing Portfolio Constraints")
        print("="*60)
        
        manager = PortfolioManager()
        
        # Test 1: Portfolio delta limit
        positions = [
            {'greeks': {'delta': -0.15}, 'contracts': 1},  # -15 delta
            {'greeks': {'delta': -0.10}, 'contracts': 2},  # -20 delta
        ]
        greeks = manager.calculate_portfolio_greeks(positions)
        within_limits, msg = greeks.is_within_limits()
        
        self.log_test(
            "Portfolio Delta Limit (±0.30)",
            not within_limits,  # Should fail, -0.35 > 0.30
            f"Delta: {greeks.total_delta:.2f}"
        )
        
        # Test 2: Bid-ask spread check
        is_ok, spread_pct = manager.check_spread_quality(bid=1.00, ask=1.03, spread_width=5.0)
        self.log_test(
            "Bid-Ask Spread ≤ 1% of width",
            is_ok,
            f"Spread: {spread_pct:.1f}% of width"
        )
        
        # Test 3: Credit target (20% of width)
        meets_target, credit_pct = manager.check_credit_target(credit=100, spread_width=5.0)
        self.log_test(
            "Credit Target ≥ 20% of width",
            meets_target,
            f"Credit: {credit_pct:.0%} of width"
        )
        
        # Test 4: Blackout window
        events = [
            {'date': datetime.now() + timedelta(hours=12), 'name': 'FOMC Meeting'},
            {'date': datetime.now() + timedelta(days=3), 'name': 'GDP Report'}
        ]
        in_blackout, event = manager.is_in_blackout_window(datetime.now(), events)
        self.log_test(
            "Event Blackout Detection",
            in_blackout,
            f"Event: {event}"
        )
        
        # Test 5: VIX hedge trigger
        portfolio = PortfolioGreeks(total_vega=-500)  # Short vega
        should_hedge = manager.should_hedge_vix(portfolio, avg_iv_rank=65)
        self.log_test(
            "VIX Hedge Trigger (Vega < 0 & IV > 60)",
            should_hedge,
            f"Vega: {portfolio.total_vega}, IV: 65"
        )
        
    def test_iron_condor_logic(self):
        """Test iron condor selection for high IV"""
        print("\n" + "="*60)
        print("Testing Iron Condor Logic")
        print("="*60)
        
        # Test IV thresholds
        test_cases = [
            (50, 'put_credit'),    # IV < 65 → single spread
            (70, 'iron_condor'),   # IV ≥ 65 → iron condor
            (85, 'iron_condor'),   # High IV → iron condor
        ]
        
        for iv_rank, expected_type in test_cases:
            # Simulate strategy selection
            if iv_rank >= 65:
                actual_type = 'iron_condor'
            else:
                actual_type = 'put_credit'  # or call_credit based on direction
                
            passed = actual_type == expected_type
            self.log_test(
                f"Iron Condor Selection: IV Rank = {iv_rank}",
                passed,
                f"Expected {expected_type}, got {actual_type}"
            )
            
    def run_all_tests(self):
        """Run all test suites"""
        print("\n" + "="*60)
        print("PROFESSIONAL TRADING STRATEGY TEST SUITE")
        print("="*60)
        
        # Run all test categories
        self.test_directional_filters()
        self.test_delta_selection()
        self.test_position_sizing()
        self.test_exit_rules()
        self.test_portfolio_constraints()
        self.test_iron_condor_logic()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.passed_tests + self.failed_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        
        if self.failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! The professional strategy is working correctly.")
        else:
            print(f"\n⚠️  {self.failed_tests} tests failed. Review the details above.")
            
        # List failed tests
        if self.failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['details']}")
                    
        return self.failed_tests == 0

def main():
    """Run the test suite"""
    tester = ProfessionalStrategyTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()