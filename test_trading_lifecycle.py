#!/usr/bin/env python3
"""
Comprehensive Trading Lifecycle Test Suite for Volatility Trading Bot

This suite simulates the full lifecycle of options trades using Alpaca's data structure,
including data simulation, order entry, execution, and position management.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
import logging

# Import our trading components
from enhanced_trade_manager import (
    EnhancedTradeManager, 
    TradeManagementRules, 
    OptionContract, 
    Trade
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AlpacaOptionContract:
    """Alpaca-style option contract data structure"""
    symbol: str  # e.g., "AAPL240119C00100000"
    name: str
    type: str  # "call" or "put"
    strike_price: float
    expiration_date: str  # "2024-01-19"
    underlying_symbol: str  # "AAPL"
    bid_price: float
    ask_price: float
    last_price: float
    volume: int
    open_interest: int
    delta: float
    gamma: float
    theta: float
    vega: float
    implied_volatility: float
    
    @property
    def option_type(self):
        """Compatibility with our OptionContract"""
        return self.type

class AlpacaDataSimulator:
    """Simulates Alpaca market data and option chains"""
    
    def __init__(self):
        self.base_prices = {
            'SPY': 450.00,
            'QQQ': 380.00,
            'IWM': 190.00,
            'AAPL': 180.00
        }
        self.volatility_map = {
            'SPY': 0.18,
            'QQQ': 0.22,
            'IWM': 0.25,
            'AAPL': 0.28
        }
        
    def generate_option_symbol(self, underlying: str, expiration: str, 
                             option_type: str, strike: float) -> str:
        """Generate Alpaca-format option symbol"""
        # Format: AAPL240119C00100000
        exp_date = expiration.replace('-', '')[2:]  # 240119
        type_char = 'C' if option_type == 'call' else 'P'
        strike_int = int(strike * 1000)  # 100.00 -> 100000
        # Pad underlying to ensure consistent length
        padded_underlying = underlying.ljust(4)[:4]
        return f"{padded_underlying}{exp_date}{type_char}{strike_int:08d}"
    
    def calculate_black_scholes(self, S: float, K: float, T: float, 
                               r: float, sigma: float, option_type: str) -> Dict[str, float]:
        """Calculate option price and Greeks using Black-Scholes"""
        from scipy.stats import norm
        
        # Handle edge cases
        if T <= 0:
            T = 0.001  # Minimum time to avoid division by zero
        if sigma <= 0:
            sigma = 0.01  # Minimum volatility
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            delta = norm.cdf(d1)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = -norm.cdf(-d1)
        
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Divide by 100 for percentage
        
        return {
            'price': max(0.01, round(price, 2)),
            'delta': round(delta, 4),
            'gamma': round(gamma, 4),
            'theta': round(theta / 365, 4),  # Convert to daily
            'vega': round(vega, 4)
        }
    
    async def get_stock_quote(self, symbol: str) -> Dict[str, float]:
        """Simulate current stock quote"""
        base_price = self.base_prices.get(symbol, 100.0)
        # Add some random movement
        movement = random.uniform(-0.02, 0.02)  # ±2% movement
        current_price = base_price * (1 + movement)
        
        return {
            'symbol': symbol,
            'bid_price': round(current_price - 0.01, 2),
            'ask_price': round(current_price + 0.01, 2),
            'last_price': round(current_price, 2),
            'volume': random.randint(1000000, 10000000),
            'day_change': round(current_price - base_price, 2),
            'day_change_percent': round(movement * 100, 2)
        }
    
    async def get_option_chain(self, symbol: str, expiration_date: str) -> List[AlpacaOptionContract]:
        """Simulate option chain for a given symbol and expiration"""
        quote = await self.get_stock_quote(symbol)
        current_price = quote['last_price']
        
        # Calculate days to expiration
        exp_date = datetime.strptime(expiration_date, '%Y-%m-%d')
        dte = (exp_date - datetime.now()).days
        T = dte / 365.0
        
        # Generate strikes around current price
        strikes = []
        strike_interval = 1.0 if current_price < 50 else 5.0
        for i in range(-10, 11):
            strike = round(current_price + (i * strike_interval))
            if strike > 0:
                strikes.append(strike)
        
        contracts = []
        r = 0.05  # Risk-free rate
        
        for strike in strikes:
            for option_type in ['call', 'put']:
                # Use implied volatility based on moneyness
                moneyness = strike / current_price
                iv_adjustment = abs(1 - moneyness) * 0.1  # IV smile
                iv = self.volatility_map.get(symbol, 0.25) + iv_adjustment
                
                # Calculate option price and Greeks
                greeks = self.calculate_black_scholes(
                    current_price, strike, T, r, iv, option_type
                )
                
                # Add bid-ask spread
                spread = max(0.01, greeks['price'] * 0.02)  # 2% spread
                bid = max(0.01, greeks['price'] - spread / 2)
                ask = greeks['price'] + spread / 2
                
                # Generate volume and open interest
                itm = (option_type == 'call' and strike < current_price) or \
                      (option_type == 'put' and strike > current_price)
                volume_base = 1000 if itm else 500
                volume = random.randint(volume_base // 2, volume_base * 2)
                
                contract = AlpacaOptionContract(
                    symbol=self.generate_option_symbol(symbol, expiration_date, option_type, strike),
                    name=f"{symbol} {expiration_date} {strike} {option_type.upper()}",
                    type=option_type,
                    strike_price=strike,
                    expiration_date=expiration_date,
                    underlying_symbol=symbol,
                    bid_price=round(bid, 2),
                    ask_price=round(ask, 2),
                    last_price=greeks['price'],
                    volume=volume,
                    open_interest=volume * random.randint(5, 20),
                    delta=greeks['delta'],
                    gamma=greeks['gamma'],
                    theta=greeks['theta'],
                    vega=greeks['vega'],
                    implied_volatility=round(iv, 4)
                )
                contracts.append(contract)
        
        return contracts
    
    def simulate_price_movement(self, contract: AlpacaOptionContract, 
                               underlying_move: float, iv_change: float = 0) -> AlpacaOptionContract:
        """Simulate option price movement based on underlying and IV changes"""
        # Get current underlying price
        quote_price = self.base_prices.get(contract.underlying_symbol, 100)
        new_underlying = quote_price * (1 + underlying_move)
        
        # Recalculate option price with new underlying and IV
        exp_date = datetime.strptime(contract.expiration_date, '%Y-%m-%d')
        dte = max(1, (exp_date - datetime.now()).days)
        T = dte / 365.0
        
        new_iv = contract.implied_volatility + iv_change
        greeks = self.calculate_black_scholes(
            new_underlying, contract.strike_price, T, 0.05, new_iv, contract.type
        )
        
        # Update contract with new prices
        spread = max(0.01, greeks['price'] * 0.02)
        contract.bid_price = max(0.01, greeks['price'] - spread / 2)
        contract.ask_price = greeks['price'] + spread / 2
        contract.last_price = greeks['price']
        contract.delta = greeks['delta']
        contract.gamma = greeks['gamma']
        contract.theta = greeks['theta']
        contract.vega = greeks['vega']
        contract.implied_volatility = new_iv
        
        return contract

class OrderSimulator:
    """Simulates order entry and execution"""
    
    def __init__(self, data_simulator: AlpacaDataSimulator):
        self.data_simulator = data_simulator
        self.orders = {}
        self.order_id_counter = 1000
        self.positions = {}
        
    async def submit_order(self, symbol: str, qty: int, side: str, 
                          order_type: str = 'market', limit_price: Optional[float] = None) -> Dict:
        """Simulate order submission"""
        order_id = f"order_{self.order_id_counter}"
        self.order_id_counter += 1
        
        order = {
            'id': order_id,
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': order_type,
            'status': 'pending_new',
            'created_at': datetime.now().isoformat(),
            'filled_qty': 0,
            'filled_avg_price': None,
            'limit_price': limit_price
        }
        
        self.orders[order_id] = order
        
        # Simulate immediate execution for market orders
        if order_type == 'market':
            await self.execute_order(order_id)
        
        return order
    
    async def execute_order(self, order_id: str) -> Dict:
        """Simulate order execution"""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Parse option symbol to get contract details
        symbol_parts = self._parse_option_symbol(order['symbol'])
        
        # Get current option price
        contracts = await self.data_simulator.get_option_chain(
            symbol_parts['underlying'],
            symbol_parts['expiration']
        )
        
        matching_contract = None
        for contract in contracts:
            if contract.symbol == order['symbol']:
                matching_contract = contract
                break
        
        if not matching_contract:
            raise ValueError(f"Contract {order['symbol']} not found")
        
        # Determine fill price based on side
        if order['side'] == 'buy':
            fill_price = matching_contract.ask_price
        else:
            fill_price = matching_contract.bid_price
        
        # Update order
        order['status'] = 'filled'
        order['filled_qty'] = order['qty']
        order['filled_avg_price'] = fill_price
        order['filled_at'] = datetime.now().isoformat()
        
        # Update positions
        self._update_positions(order, fill_price)
        
        return order
    
    def _parse_option_symbol(self, symbol: str) -> Dict[str, Any]:
        """Parse Alpaca option symbol format"""
        # Example: SPY 250630C00450000
        # First 4 chars are underlying (padded)
        underlying = symbol[:4].strip()
        date_str = symbol[4:10]  # 6 chars for date
        option_type = 'call' if symbol[10] == 'C' else 'put'
        strike_str = symbol[11:]  # Rest is strike
        
        expiration = f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
        strike = float(strike_str) / 1000
        
        return {
            'underlying': underlying,
            'expiration': expiration,
            'type': option_type,
            'strike': strike
        }
    
    def _update_positions(self, order: Dict, fill_price: float):
        """Update positions based on filled order"""
        symbol = order['symbol']
        qty = order['filled_qty'] if order['side'] == 'buy' else -order['filled_qty']
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                'symbol': symbol,
                'qty': 0,
                'avg_price': 0,
                'unrealized_pnl': 0
            }
        
        pos = self.positions[symbol]
        
        # Update quantity and average price
        if pos['qty'] == 0:
            pos['avg_price'] = fill_price
        elif (pos['qty'] > 0 and qty > 0) or (pos['qty'] < 0 and qty < 0):
            # Adding to position
            total_value = pos['qty'] * pos['avg_price'] + qty * fill_price
            pos['avg_price'] = total_value / (pos['qty'] + qty)
        
        pos['qty'] += qty
        
        # Remove position if closed
        if pos['qty'] == 0:
            del self.positions[symbol]

class TradingLifecycleTest:
    """Comprehensive test suite for full trading lifecycle"""
    
    def __init__(self):
        self.data_simulator = AlpacaDataSimulator()
        self.order_simulator = OrderSimulator(self.data_simulator)
        self.trade_manager = EnhancedTradeManager()
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test results"""
        result = {
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now()
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name} - {details}")
        
    async def test_market_data_simulation(self):
        """Test market data simulation"""
        print("\n🔍 Testing Market Data Simulation...")
        
        try:
            # Test stock quote
            quote = await self.data_simulator.get_stock_quote('SPY')
            assert 'bid_price' in quote and 'ask_price' in quote
            self.log_test("Stock quote simulation", True, f"SPY: ${quote['last_price']}")
            
            # Test option chain
            expiration = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            chain = await self.data_simulator.get_option_chain('SPY', expiration)
            assert len(chain) > 0
            assert all(hasattr(c, 'delta') for c in chain)
            self.log_test("Option chain simulation", True, f"Generated {len(chain)} contracts")
            
            # Test Greeks calculation
            sample_contract = chain[len(chain)//2]  # ATM contract
            assert -1 <= sample_contract.delta <= 1
            assert sample_contract.gamma >= 0
            assert sample_contract.implied_volatility > 0
            self.log_test("Greeks calculation", True, 
                         f"Delta: {sample_contract.delta}, IV: {sample_contract.implied_volatility}")
            
            return True
            
        except Exception as e:
            self.log_test("Market data simulation", False, str(e))
            return False
    
    async def test_order_entry_execution(self):
        """Test order entry and execution flow"""
        print("\n🔍 Testing Order Entry & Execution...")
        
        try:
            # Get option contracts
            expiration = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            chain = await self.data_simulator.get_option_chain('SPY', expiration)
            
            # Find ATM call and put
            current_price = self.data_simulator.base_prices['SPY']
            atm_call = min(chain, key=lambda c: abs(c.strike_price - current_price) if c.type == 'call' else float('inf'))
            otm_call = next(c for c in chain if c.type == 'call' and c.strike_price > atm_call.strike_price)
            
            # Test credit spread order (sell ATM, buy OTM)
            # Sell leg
            sell_order = await self.order_simulator.submit_order(
                symbol=atm_call.symbol,
                qty=1,
                side='sell',
                order_type='market'
            )
            assert sell_order['status'] == 'filled'
            self.log_test("Sell order execution", True, 
                         f"Sold {atm_call.symbol} @ ${sell_order['filled_avg_price']}")
            
            # Buy leg
            buy_order = await self.order_simulator.submit_order(
                symbol=otm_call.symbol,
                qty=1,
                side='buy',
                order_type='market'
            )
            assert buy_order['status'] == 'filled'
            self.log_test("Buy order execution", True,
                         f"Bought {otm_call.symbol} @ ${buy_order['filled_avg_price']}")
            
            # Check positions
            assert len(self.order_simulator.positions) == 2
            self.log_test("Position tracking", True, 
                         f"Tracking {len(self.order_simulator.positions)} positions")
            
            return True
            
        except Exception as e:
            self.log_test("Order entry/execution", False, str(e))
            return False
    
    async def test_trade_lifecycle(self):
        """Test complete trade lifecycle from entry to exit"""
        print("\n🔍 Testing Complete Trade Lifecycle...")
        
        try:
            # Setup mock for trade manager
            with patch.object(self.trade_manager, 'get_real_time_options_data') as mock_options:
                # Create initial option chain
                expiration = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                chain = await self.data_simulator.get_option_chain('SPY', expiration)
                
                # Setup mock to return our simulated data
                mock_options.return_value = [
                    OptionContract(
                        symbol=c.symbol,
                        strike_price=c.strike_price,
                        expiration_date=c.expiration_date,
                        option_type=c.type,
                        bid_price=c.bid_price,
                        ask_price=c.ask_price,
                        volume=c.volume,
                        open_interest=c.open_interest,
                        delta=c.delta,
                        gamma=c.gamma,
                        theta=c.theta,
                        vega=c.vega,
                        implied_volatility=c.implied_volatility
                    ) for c in chain
                ]
                
                # Find suitable contracts for credit spread
                current_price = self.data_simulator.base_prices['SPY']
                put_contracts = [c for c in chain if c.type == 'put']
                short_put = min(put_contracts, key=lambda c: abs(c.strike_price - current_price * 0.95))
                long_put = next(c for c in put_contracts if c.strike_price < short_put.strike_price)
                
                # Create trade
                trade_data = {
                    'symbol': 'SPY',
                    'strategy_type': 'put_credit_spread',
                    'spread_type': 'put_credit',
                    'short_leg': OptionContract(
                        symbol=short_put.symbol,
                        strike_price=short_put.strike_price,
                        expiration_date=short_put.expiration_date,
                        option_type='put',
                        bid_price=short_put.bid_price,
                        ask_price=short_put.ask_price,
                        volume=short_put.volume,
                        open_interest=short_put.open_interest,
                        delta=short_put.delta,
                        gamma=short_put.gamma,
                        theta=short_put.theta,
                        vega=short_put.vega,
                        implied_volatility=short_put.implied_volatility
                    ),
                    'long_leg': OptionContract(
                        symbol=long_put.symbol,
                        strike_price=long_put.strike_price,
                        expiration_date=long_put.expiration_date,
                        option_type='put',
                        bid_price=long_put.bid_price,
                        ask_price=long_put.ask_price,
                        volume=long_put.volume,
                        open_interest=long_put.open_interest,
                        delta=long_put.delta,
                        gamma=long_put.gamma,
                        theta=long_put.theta,
                        vega=long_put.vega,
                        implied_volatility=long_put.implied_volatility
                    ),
                    'contracts': 1,
                    'entry_credit': (short_put.bid_price - long_put.ask_price) * 100,
                    'max_loss': (short_put.strike_price - long_put.strike_price) * 100,
                    'probability_profit': 65
                }
                
                trade = await self.trade_manager.add_trade(trade_data)
                self.log_test("Trade creation", True, 
                             f"Created {trade.spread_type} for ${trade.entry_credit:.2f} credit")
                
                # Simulate price movement (underlying drops 2%)
                for contract in chain:
                    self.data_simulator.simulate_price_movement(contract, -0.02, 0.05)
                
                # Update mock with new prices
                mock_options.return_value = [
                    OptionContract(
                        symbol=c.symbol,
                        strike_price=c.strike_price,
                        expiration_date=c.expiration_date,
                        option_type=c.type,
                        bid_price=c.bid_price,
                        ask_price=c.ask_price,
                        volume=c.volume,
                        open_interest=c.open_interest,
                        delta=c.delta,
                        gamma=c.gamma,
                        theta=c.theta,
                        vega=c.vega,
                        implied_volatility=c.implied_volatility
                    ) for c in chain
                ]
                
                # Calculate new P&L
                current_value, unrealized_pnl = await self.trade_manager.calculate_current_trade_value(trade)
                self.log_test("P&L calculation", True,
                             f"Unrealized P&L: ${unrealized_pnl:.2f} after 2% drop")
                
                # Test profit target exit
                trade.unrealized_pnl = trade.entry_credit * 0.4  # 40% profit
                should_close, reason = await self.trade_manager.check_exit_conditions(trade)
                assert should_close == True
                assert "profit target" in reason.lower()
                self.log_test("Profit target detection", True, reason)
                
                # Test stop loss
                trade.unrealized_pnl = -trade.max_loss * 0.8  # 80% loss
                should_close, reason = await self.trade_manager.check_exit_conditions(trade)
                assert should_close == True
                assert "stop loss" in reason.lower()
                self.log_test("Stop loss detection", True, reason)
                
                # Test time decay exit
                trade.unrealized_pnl = 10  # Small profit
                trade.short_leg.expiration_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
                should_close, reason = await self.trade_manager.check_exit_conditions(trade)
                assert should_close == True
                assert "dte" in reason.lower()
                self.log_test("Time stop detection", True, reason)
                
                return True
                
        except Exception as e:
            self.log_test("Trade lifecycle", False, str(e))
            return False
    
    async def test_analytics_tracking(self):
        """Test analytics and performance tracking"""
        print("\n🔍 Testing Analytics & Performance Tracking...")
        
        try:
            # Create multiple trades with different outcomes
            trades_to_simulate = [
                {'result': 'win', 'pnl_percent': 0.35, 'days_held': 15},
                {'result': 'win', 'pnl_percent': 0.25, 'days_held': 10},
                {'result': 'loss', 'pnl_percent': -0.50, 'days_held': 20},
                {'result': 'win', 'pnl_percent': 0.40, 'days_held': 12},
                {'result': 'scratch', 'pnl_percent': 0.05, 'days_held': 25}
            ]
            
            for i, sim in enumerate(trades_to_simulate):
                mock_contract = Mock()
                mock_contract.strike_price = 450
                mock_contract.expiration_date = '2024-02-15'
                mock_contract.delta = -0.3
                
                trade = Trade(
                    trade_id=f"test_{i}",
                    symbol='SPY',
                    strategy_type='put_credit_spread',
                    spread_type='put_credit',
                    entry_time=datetime.now() - timedelta(days=sim['days_held']),
                    short_leg=mock_contract,
                    long_leg=Mock(strike_price=445, expiration_date='2024-02-15', delta=-0.1),
                    contracts=1,
                    entry_credit=200,
                    max_loss=500,
                    current_value=200 * (1 - sim['pnl_percent']),
                    unrealized_pnl=200 * sim['pnl_percent'],
                    status='closed' if sim['result'] != 'active' else 'active',
                    profit_target=70,  # 35% of 200
                    stop_loss_target=-375,  # 75% of 500
                    days_to_expiration=30 - sim['days_held'],
                    probability_profit=65,
                    confidence_score=75,
                    claude_reasoning="Test trade"
                )
                
                if sim['result'] != 'active':
                    trade.exit_time = datetime.now()
                    trade.realized_pnl = trade.entry_credit * sim['pnl_percent']
                    trade.exit_reason = 'profit_target' if sim['result'] == 'win' else 'stop_loss'
                
                self.trade_manager.active_trades.append(trade)
            
            # Get analytics
            summary = self.trade_manager.get_trade_summary()
            
            # Verify summary calculations
            assert 'total_trades' in summary
            assert 'win_rate' in summary
            assert 'average_win' in summary
            assert 'average_loss' in summary
            
            self.log_test("Trade summary calculation", True,
                         f"Win rate: {summary.get('win_rate', 0):.1f}%")
            
            # Test daily P&L tracking
            daily_pnl = sum(t.realized_pnl for t in self.trade_manager.active_trades 
                           if hasattr(t, 'exit_time') and t.exit_time and 
                           t.exit_time.date() == datetime.now().date())
            
            self.log_test("Daily P&L tracking", True, f"Today's P&L: ${daily_pnl:.2f}")
            
            # Test position Greeks aggregation
            total_delta = sum(getattr(t.short_leg, 'delta', 0) - getattr(t.long_leg, 'delta', 0) 
                            for t in self.trade_manager.active_trades if t.status == 'active')
            
            self.log_test("Greeks aggregation", True, f"Portfolio Delta: {total_delta:.4f}")
            
            return True
            
        except Exception as e:
            self.log_test("Analytics tracking", False, str(e))
            return False
    
    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n🔍 Testing Edge Cases...")
        
        try:
            # Test expired contract handling
            expired_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            try:
                # Should handle expired dates gracefully
                chain = await self.data_simulator.get_option_chain('SPY', expired_date)
                # It will still generate contracts but with very low time value
                assert len(chain) > 0
                self.log_test("Expired contract handling", True, "Gracefully handled expired date")
            except Exception as e:
                self.log_test("Expired contract handling", False, str(e))
            
            # Test invalid symbol
            quote = await self.data_simulator.get_stock_quote('INVALID')
            assert quote['last_price'] == 100.0  # Default price
            self.log_test("Invalid symbol handling", True)
            
            # Test extreme market conditions
            contract = AlpacaOptionContract(
                symbol='SPY240215C00450000',
                name='SPY Call',
                type='call',
                strike_price=450,
                expiration_date='2024-02-15',
                underlying_symbol='SPY',
                bid_price=10.0,
                ask_price=10.5,
                last_price=10.25,
                volume=100,
                open_interest=1000,
                delta=0.5,
                gamma=0.01,
                theta=-0.05,
                vega=0.15,
                implied_volatility=0.25
            )
            
            # Simulate 10% crash
            updated = self.data_simulator.simulate_price_movement(contract, -0.10, 0.20)
            assert updated.bid_price < contract.bid_price
            assert updated.implied_volatility > contract.implied_volatility
            self.log_test("Extreme market movement", True, 
                         f"Price dropped from ${contract.bid_price} to ${updated.bid_price}")
            
            return True
            
        except Exception as e:
            self.log_test("Edge case handling", False, str(e))
            return False
    
    def assertRaises(self, exception_type):
        """Helper for exception testing"""
        class ExceptionContext:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    raise AssertionError(f"Expected {exception_type} but no exception was raised")
                return issubclass(exc_type, exception_type)
        return ExceptionContext()
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 60)
        print("TRADING LIFECYCLE TEST SUITE")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        tests = [
            self.test_market_data_simulation,
            self.test_order_entry_execution,
            self.test_trade_lifecycle,
            self.test_analytics_tracking,
            self.test_edge_cases
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if await test():
                passed += 1
            print()
        
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("✅ ALL TESTS PASSED - Trading lifecycle fully validated!")
        else:
            print("❌ SOME TESTS FAILED - Review issues above")
        
        # Generate detailed report
        self.generate_test_report()
        
        return passed == total
    
    def generate_test_report(self):
        """Generate detailed test report"""
        report_path = "trading_lifecycle_test_report.json"
        
        report = {
            'test_run': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(self.test_results),
                'passed': sum(1 for r in self.test_results if r['passed']),
                'failed': sum(1 for r in self.test_results if not r['passed'])
            },
            'results': [
                {
                    'test': r['test'],
                    'passed': r['passed'],
                    'details': r['details'],
                    'timestamp': r['timestamp'].isoformat()
                }
                for r in self.test_results
            ]
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_path}")

async def main():
    """Main test runner"""
    tester = TradingLifecycleTest()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))