#!/usr/bin/env python3
"""
Comprehensive test suite for the volatility trading bot with new folder structure
"""

import sys
import os
import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.trade_manager import EnhancedTradeManager, TradeManagementRules, OptionContract
from src.data.trade_db import TradeDatabase
from src.data.simulated_pnl import SimulatedPnLTracker
from src.core.position_tracker import PositionTracker

class TestTradeManager(unittest.TestCase):
    """Test the EnhancedTradeManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.trade_manager = EnhancedTradeManager(paper_trading=True)
        
    def test_initialization(self):
        """Test trade manager initialization"""
        self.assertIsNotNone(self.trade_manager.trading_client)
        self.assertEqual(len(self.trade_manager.active_trades), 0)
        self.assertFalse(self.trade_manager.is_monitoring)
        
    def test_trade_rules(self):
        """Test trade management rules"""
        rules = self.trade_manager.rules
        self.assertEqual(rules.profit_target_percent, 0.35)
        self.assertEqual(rules.stop_loss_percent, 0.75)
        self.assertEqual(rules.time_stop_dte, 3)
        self.assertEqual(rules.max_position_size_pct, 0.02)
        
    @patch('src.core.trade_manager.TradingClient')
    def test_get_account_balance(self, mock_client):
        """Test account balance retrieval"""
        # Mock account data
        mock_account = MagicMock()
        mock_account.buying_power = '50000.00'
        mock_account.cash = '100000.00'
        
        self.trade_manager.trading_client.get_account = MagicMock(return_value=mock_account)
        
        balance = self.trade_manager.get_account_balance()
        self.assertEqual(balance, 100000.00)
        
    async def test_calculate_position_size(self):
        """Test position size calculation"""
        # Mock account balance
        self.trade_manager.get_account_balance = MagicMock(return_value=100000.00)
        
        # Test position sizing (2% of $100k = $2000 max risk)
        size = await self.trade_manager.calculate_position_size(
            account_balance=100000.00,
            spread_width=5.00,
            credit_received=1.25
        )
        
        # Max risk = $2000, risk per contract = $3.75
        # Expected contracts = floor(2000 / 375) = 5
        self.assertEqual(size, 5)
        
    def test_option_contract_creation(self):
        """Test OptionContract data class"""
        contract = OptionContract(
            symbol="SPY230630C00400000",
            strike_price=400.00,
            expiration_date="2023-06-30",
            option_type="call",
            ask_price=1.50,
            bid_price=1.45,
            implied_volatility=0.25,
            delta=-0.30,
            gamma=0.05,
            theta=-0.10,
            vega=0.15
        )
        
        self.assertEqual(contract.symbol, "SPY230630C00400000")
        self.assertEqual(contract.strike_price, 400.00)
        self.assertEqual(contract.option_type, "call")
        self.assertEqual(contract.implied_volatility, 0.25)

class TestDatabase(unittest.TestCase):
    """Test the database functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.db = TradeDatabase(db_path=":memory:")  # Use in-memory database for tests
        
    def test_add_claude_analysis(self):
        """Test adding Claude analysis to database"""
        analysis_data = {
            'symbol': 'SPY',
            'market_data': {
                'current_price': 450.00,
                'percent_change': -2.5,
                'iv_rank': 85,
                'volume': 1000000
            },
            'claude_analysis': {
                'should_trade': True,
                'spread_type': 'call_credit',
                'confidence': 85
            },
            'decision': 'EXECUTE TRADE',
            'mode': 'TEST'
        }
        
        analysis_id = self.db.add_claude_analysis(analysis_data)
        self.assertIsNotNone(analysis_id)
        self.assertGreater(analysis_id, 0)
        
    def test_add_trade(self):
        """Test adding trade to database"""
        trade_data = {
            'symbol': 'SPY',
            'spread_type': 'call_credit',
            'short_strike': 455,
            'long_strike': 460,
            'contracts': 2,
            'credit': 1.25,
            'status': 'OPEN',
            'mode': 'TEST'
        }
        
        trade_id = self.db.add_trade(trade_data)
        self.assertIsNotNone(trade_id)
        self.assertGreater(trade_id, 0)
        
    def test_get_statistics(self):
        """Test getting database statistics"""
        # Add some test data
        self.db.add_claude_analysis({
            'symbol': 'SPY',
            'market_data': {'current_price': 450, 'percent_change': -2, 'iv_rank': 80, 'volume': 1000000},
            'claude_analysis': {'should_trade': True, 'confidence': 85},
            'decision': 'EXECUTE',
            'mode': 'TEST'
        })
        
        stats = self.db.get_statistics()
        self.assertIn('total_analyses', stats)
        self.assertIn('total_trades', stats)
        self.assertEqual(stats['total_analyses'], 1)

class TestSimulatedPnL(unittest.TestCase):
    """Test the simulated P&L tracker"""
    
    def setUp(self):
        """Set up test P&L tracker"""
        self.tracker = SimulatedPnLTracker()
        # Clear any existing trades
        self.tracker.trades = []
        self.tracker.closed_trades = []
        
    def test_add_trade(self):
        """Test adding a simulated trade"""
        trade_data = {
            'trade_id': 'TEST-001',
            'symbol': 'SPY',
            'spread_type': 'call_credit',
            'entry_credit': 250.00,
            'max_loss': 250.00,
            'entry_time': datetime.now()
        }
        
        self.tracker.add_trade(trade_data)
        self.assertEqual(len(self.tracker.trades), 1)
        self.assertEqual(self.tracker.trades[0]['symbol'], 'SPY')
        
    def test_pnl_calculation(self):
        """Test P&L calculation logic"""
        # Add a winning trade
        trade_data = {
            'symbol': 'SPY',
            'spread_type': 'call_credit',
            'entry_credit': 250.00,
            'max_loss': 250.00,
            'entry_time': datetime.now() - timedelta(days=1)
        }
        
        self.tracker.add_trade(trade_data)
        self.tracker.trades[0]['is_winner'] = True
        
        # Update positions
        self.tracker.update_positions()
        
        # Check that P&L is positive for winning trade
        if self.tracker.trades:  # Trade might have closed
            self.assertGreaterEqual(self.tracker.trades[0]['unrealized_pnl'], 0)
        
    def test_max_loss_constraint(self):
        """Test that losses don't exceed max loss"""
        # Add a losing trade
        trade_data = {
            'symbol': 'SPY',
            'spread_type': 'call_credit',
            'entry_credit': 250.00,
            'max_loss': 250.00,
            'entry_time': datetime.now()
        }
        
        self.tracker.add_trade(trade_data)
        self.tracker.trades[0]['is_winner'] = False
        
        # Update positions multiple times
        for _ in range(10):
            self.tracker.update_positions()
            
            # Check all trades (open and closed)
            all_trades = self.tracker.trades + self.tracker.closed_trades
            for trade in all_trades:
                loss = abs(min(0, trade.get('unrealized_pnl', 0)))
                self.assertLessEqual(loss, trade['max_loss'], 
                                   f"Loss ${loss} exceeds max loss ${trade['max_loss']}")

class TestPositionTracker(unittest.TestCase):
    """Test the position tracker"""
    
    @patch('src.core.position_tracker.TradingClient')
    def setUp(self, mock_client):
        """Set up test position tracker"""
        self.tracker = PositionTracker(paper_trading=True)
        
    def test_initialization(self):
        """Test position tracker initialization"""
        self.assertIsNotNone(self.tracker.trading_client)
        self.assertTrue(self.tracker.paper_trading)

class TestIntegration(unittest.TestCase):
    """Integration tests for the full system"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.trade_manager = EnhancedTradeManager(paper_trading=True)
        self.db = TradeDatabase(db_path=":memory:")
        self.pnl_tracker = SimulatedPnLTracker()
        
    def test_full_trade_flow(self):
        """Test complete trade flow from analysis to execution"""
        # 1. Add Claude analysis
        analysis_data = {
            'symbol': 'SPY',
            'market_data': {
                'current_price': 450.00,
                'percent_change': -2.5,
                'iv_rank': 85,
                'volume': 1000000
            },
            'claude_analysis': {
                'should_trade': True,
                'spread_type': 'call_credit',
                'short_strike': 455,
                'long_strike': 460,
                'contracts': 2,
                'expected_credit': 1.25,
                'confidence': 85
            },
            'decision': 'EXECUTE TRADE',
            'mode': 'TEST'
        }
        
        analysis_id = self.db.add_claude_analysis(analysis_data)
        self.assertIsNotNone(analysis_id)
        
        # 2. Add trade to database
        trade_data = {
            'symbol': 'SPY',
            'spread_type': 'call_credit',
            'short_strike': 455,
            'long_strike': 460,
            'contracts': 2,
            'credit': 1.25,
            'status': 'SIMULATED',
            'mode': 'TEST'
        }
        
        trade_id = self.db.add_trade(trade_data, analysis_id)
        self.assertIsNotNone(trade_id)
        
        # 3. Add to P&L tracker
        pnl_data = {
            'trade_id': f'TEST-{trade_id}',
            'symbol': 'SPY',
            'spread_type': 'call_credit',
            'entry_credit': 250.00,  # 1.25 * 2 * 100
            'max_loss': 250.00,      # (5 - 1.25) * 2 * 100
            'entry_time': datetime.now()
        }
        
        self.pnl_tracker.add_trade(pnl_data)
        
        # 4. Verify everything is connected
        stats = self.db.get_statistics()
        self.assertEqual(stats['total_analyses'], 1)
        self.assertEqual(stats['total_trades'], 1)
        
        summary = self.pnl_tracker.get_portfolio_summary()
        self.assertGreaterEqual(summary['total_trades'], 1)

def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTradeManager))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestSimulatedPnL))
    suite.addTests(loader.loadTestsFromTestCase(TestPositionTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result

if __name__ == "__main__":
    print("Running comprehensive test suite for volatility trading bot...")
    print("=" * 70)
    
    result = run_tests()
    
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ Some tests failed. Check output above for details.")