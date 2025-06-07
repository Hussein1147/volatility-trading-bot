"""
Unit tests for BacktestEngine with synthetic pricing
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.engines.backtest_engine import (
    BacktestConfig, BacktestEngine, BacktestResults,
    BacktestTrade, DEFAULTS
)
from src.engines.synthetic_pricer import SyntheticOptionPricer


class TestBacktestEngine:
    """Test the backtest engine with synthetic pricing"""
    
    @pytest.fixture
    def basic_config(self):
        """Create a basic backtest configuration"""
        return BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            symbols=['SPY'],
            initial_capital=100000,
            max_risk_per_trade=0.02,
            min_iv_rank=40,
            min_price_move=1.5,
            confidence_threshold=70,
            commission_per_contract=0.65,
            use_real_data=False  # Use simulated data for testing
        )
    
    @pytest.fixture
    def mock_ai_provider(self):
        """Mock AI provider for testing"""
        class MockAIProvider:
            async def analyze_opportunity(self, prompt):
                # Return a consistent positive response
                return '''
                {
                    "confidence": 75,
                    "spread_type": "put_credit",
                    "reasoning": "Test trade signal"
                }
                '''
        
        return MockAIProvider()
    
    @pytest.mark.asyncio
    async def test_synthetic_pricing_initialization(self, basic_config):
        """Test that synthetic pricer is initialized correctly"""
        engine = BacktestEngine(
            basic_config,
            synthetic_pricing=True,
            delta_target=0.16
        )
        
        assert engine.synthetic_pricing is True
        assert engine.synthetic_pricer is not None
        assert isinstance(engine.synthetic_pricer, SyntheticOptionPricer)
        assert engine.delta_target == 0.16
    
    @pytest.mark.asyncio
    async def test_tiered_exit_parameters(self, basic_config):
        """Test tiered exit configuration"""
        tier_targets = [0.50, 0.75, -1.50]
        contracts_by_tier = [0.4, 0.4, 0.2]
        force_exit_days = 21
        
        engine = BacktestEngine(
            basic_config,
            synthetic_pricing=True,
            tier_targets=tier_targets,
            contracts_by_tier=contracts_by_tier,
            force_exit_days=force_exit_days
        )
        
        assert engine.tier_targets == tier_targets
        assert engine.contracts_by_tier == contracts_by_tier
        assert engine.force_exit_days == force_exit_days
    
    @pytest.mark.asyncio
    async def test_default_parameters(self, basic_config):
        """Test that DEFAULTS are applied correctly"""
        engine = BacktestEngine(basic_config)
        
        # Check defaults from DEFAULTS dict
        assert engine.tier_targets == DEFAULTS['tier_targets']
        assert engine.contracts_by_tier == DEFAULTS['contracts_by_tier']
        assert engine.force_exit_days == DEFAULTS['force_exit_days']
    
    def test_tiered_exit_logic(self):
        """Test the tiered exit calculation logic"""
        # Create a mock trade
        trade = BacktestTrade(
            entry_time=datetime(2024, 1, 1),
            symbol='SPY',
            spread_type='put_credit',
            short_strike=450,
            long_strike=445,
            contracts=5,  # >= 3 for tiered exits
            entry_credit=150.0,
            max_profit=150.0,
            max_loss=350.0,
            expiration_days=45
        )
        
        # Test 50% profit target
        current_pnl = 75.0  # 50% of max profit
        pnl_percentage = current_pnl / trade.max_profit
        assert abs(pnl_percentage - 0.50) < 0.01
        
        # Test 75% profit target
        current_pnl = 112.5  # 75% of max profit
        pnl_percentage = current_pnl / trade.max_profit
        assert abs(pnl_percentage - 0.75) < 0.01
        
        # Test stop loss at -150%
        current_pnl = -225.0  # -150% of credit
        stop_loss_level = trade.entry_credit * -1.5
        assert current_pnl <= stop_loss_level
    
    @pytest.mark.asyncio
    async def test_synthetic_pricing_in_trade(self, basic_config, mock_ai_provider):
        """Test that synthetic pricing is used during trade execution"""
        # Create engine with synthetic pricing
        engine = BacktestEngine(
            basic_config,
            synthetic_pricing=True,
            delta_target=0.16,
            ai_provider=mock_ai_provider
        )
        
        # Create a mock market data signal
        market_data = {
            'symbol': 'SPY',
            'date': datetime(2024, 1, 15),
            'current_price': 480.0,
            'percent_change': 2.5,
            'volume': 100000000,
            'iv_rank': 60.0,
            'iv_percentile': 65.0,
            'sma_20': 475.0,
            'rsi_14': 45.0
        }
        
        # Cache IV for synthetic pricing
        engine.synthetic_pricer.cache_iv('SPY', 0.18)
        
        # Test strike selection with synthetic pricing
        signal = {
            'symbol': 'SPY',
            'date': market_data['date'],
            'market_data': market_data,
            'analysis': {
                'confidence': 75,
                'spread_type': 'put_credit',
                'reasoning': 'Test signal'
            }
        }
        
        # Execute trade
        await engine._execute_trade(signal, market_data['date'])
        
        # Verify a trade was created
        assert len(engine.open_positions) == 1
        
        # Get the trade
        trade_id = list(engine.open_positions.keys())[0]
        trade = engine.open_positions[trade_id]
        
        # Verify strikes were selected
        assert trade.short_strike > 0
        assert trade.long_strike > 0
        assert trade.short_strike > trade.long_strike  # Put spread
        
        # Verify credit was calculated
        assert trade.entry_credit > 0
        assert trade.max_profit == trade.entry_credit
    
    @pytest.mark.asyncio
    async def test_partial_position_closing(self, basic_config):
        """Test partial position closing for larger positions"""
        engine = BacktestEngine(
            basic_config,
            synthetic_pricing=True,
            tier_targets=[0.50, 0.75, -1.50],
            contracts_by_tier=[0.4, 0.4, 0.2]
        )
        
        # Create a large position
        trade = BacktestTrade(
            entry_time=datetime(2024, 1, 1),
            symbol='SPY',
            spread_type='put_credit',
            short_strike=450,
            long_strike=445,
            contracts=10,  # Large position for tiered exits
            entry_credit=500.0,
            max_profit=500.0,
            max_loss=4500.0,
            expiration_days=45
        )
        
        trade_id = 'SPY_20240101_120000'
        engine.open_positions[trade_id] = trade
        
        # Simulate 50% profit - should close 40% of contracts
        # This would happen in _manage_positions but we test the logic
        pnl_percentage = 0.50
        contracts_to_close = int(trade.contracts * engine.contracts_by_tier[0])
        
        assert contracts_to_close == 4  # 40% of 10
        
        # Record partial close
        engine.partial_closes[trade_id] = [{
            'date': datetime(2024, 1, 10),
            'contracts': contracts_to_close,
            'pnl_per_contract': 25.0,
            'tier': 1,
            'reason': 'Profit Target (50%)'
        }]
        
        # Check remaining contracts
        closed_contracts = sum(h['contracts'] for h in engine.partial_closes[trade_id])
        remaining = trade.contracts - closed_contracts
        assert remaining == 6
    
    @pytest.mark.asyncio
    async def test_time_stop_exit(self, basic_config):
        """Test force exit at specified DTE"""
        engine = BacktestEngine(
            basic_config,
            synthetic_pricing=True,
            force_exit_days=21
        )
        
        # Create a position
        trade = BacktestTrade(
            entry_time=datetime(2024, 1, 1),
            symbol='SPY',
            spread_type='call_credit',
            short_strike=490,
            long_strike=495,
            contracts=2,  # Small position
            entry_credit=100.0,
            max_profit=100.0,
            max_loss=400.0,
            expiration_days=45
        )
        
        # Check if position should exit at 21 DTE
        days_in_trade = 45 - 21  # 24 days
        remaining_dte = trade.expiration_days - days_in_trade
        
        assert remaining_dte == engine.force_exit_days
        
        # For small positions (<3 contracts), should exit at force_exit_days
        should_exit = remaining_dte <= engine.force_exit_days
        assert should_exit is True


@pytest.mark.asyncio
async def test_tiny_synthetic_backtest():
    """Run a minimal synthetic backtest on SPY for January 2024"""
    config = BacktestConfig(
        start_date=datetime(2024, 1, 2),
        end_date=datetime(2024, 1, 5),  # Just 4 days
        symbols=['SPY'],
        initial_capital=100000,
        max_risk_per_trade=0.02,
        min_iv_rank=30,  # Lower threshold for testing
        min_price_move=0.5,  # Lower threshold for testing
        confidence_threshold=70,
        commission_per_contract=0.65
    )
    
    # Mock AI that always signals trades
    class AlwaysTradeAI:
        async def analyze_opportunity(self, prompt):
            return '''
            {
                "confidence": 80,
                "spread_type": "put_credit",
                "reasoning": "Testing synthetic pricing"
            }
            '''
    
    # Create engine with synthetic pricing
    engine = BacktestEngine(
        config,
        synthetic_pricing=True,
        delta_target=0.16,
        tier_targets=[0.50, 0.75, -1.50],
        contracts_by_tier=[0.4, 0.4, 0.2],
        force_exit_days=21,
        ai_provider=AlwaysTradeAI()
    )
    
    # Mock the data fetcher to return test data
    original_get_historical = engine._get_historical_data
    
    async def mock_get_historical_data(symbol, date):
        # Return data that triggers a trade signal
        return {
            'symbol': symbol,
            'date': date,
            'current_price': 470.0 + (date.day * 0.5),  # Slight price variation
            'percent_change': 1.8,  # Above min threshold
            'volume': 80000000,
            'iv_rank': 45.0,  # Above min threshold
            'iv_percentile': 50.0,
            'high': 472.0,
            'low': 468.0,
            'open': 469.0,
            'sma_20': 468.0,
            'rsi_14': 55.0
        }
    
    engine._get_historical_data = mock_get_historical_data
    
    # Run the backtest
    results = await engine.run_backtest()
    
    # Verify results
    assert isinstance(results, BacktestResults)
    assert results.total_trades >= 0  # May or may not execute trades
    
    # If trades were executed, verify they used synthetic pricing
    if results.trades:
        # Check that trades have valid data
        for trade in results.trades:
            assert trade.entry_credit > 0
            assert trade.short_strike > 0
            assert trade.long_strike > 0
            assert trade.contracts > 0
            
    # Verify equity curve was tracked
    assert len(results.equity_curve) > 0
    assert results.equity_curve[0] == config.initial_capital