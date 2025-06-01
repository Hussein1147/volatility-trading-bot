#!/usr/bin/env python3

import os
import asyncio
import json
from datetime import datetime, timedelta, date
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple, Any
import logging
from decimal import Decimal

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, OrderType, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockQuotesRequest, OptionChainRequest
from alpaca.data.timeframe import TimeFrame

from anthropic import AsyncAnthropic
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TradeManagementRules:
    profit_target_percent: float = 0.35  # 35% of max profit
    stop_loss_percent: float = 0.75  # 75% of max loss (stop at 75% loss)
    max_dte: int = 45  # Maximum days to expiration
    min_dte: int = 7   # Minimum days to expiration  
    time_stop_dte: int = 5  # Close all trades at 5 DTE
    monitoring_interval: int = 60  # Check every 60 seconds
    max_daily_loss: float = 500  # Max daily loss limit
    max_position_size: float = 0.02  # 2% of account per trade

@dataclass 
class OptionContract:
    symbol: str
    strike_price: float
    expiration_date: str
    option_type: str  # 'call' or 'put'
    bid_price: float
    ask_price: float
    volume: int
    open_interest: int
    delta: float
    gamma: float
    theta: float
    vega: float
    implied_volatility: float

@dataclass
class Trade:
    trade_id: str
    symbol: str
    strategy_type: str
    spread_type: str
    short_leg: OptionContract
    long_leg: OptionContract
    contracts: int
    entry_time: datetime
    entry_credit: float
    max_loss: float
    current_value: float
    unrealized_pnl: float
    status: str
    profit_target: float
    stop_loss_target: float
    days_to_expiration: int
    probability_profit: float
    confidence_score: int
    claude_reasoning: str
    # Exit tracking fields
    exit_time: Optional[datetime] = None
    realized_pnl: float = 0.0
    exit_reason: Optional[str] = None

class EnhancedTradeManager:
    def __init__(self, paper_trading=True):
        # Determine which API keys to use based on mode
        if paper_trading:
            api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING')
            secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING')
        else:
            api_key = os.getenv('ALPACA_API_KEY')
            secret_key = os.getenv('ALPACA_SECRET_KEY')
            
        logger.info(f"Initializing TradeManager in {'PAPER' if paper_trading else 'LIVE'} mode")
        
        # Initialize Alpaca clients
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper_trading
        )
        
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )
        
        # Options data client (for real-time options data)
        self.options_client = OptionHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )
        
        # Initialize Claude
        self.anthropic = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Trade management
        self.rules = TradeManagementRules()
        self.active_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.daily_pnl = 0
        self.account_balance = 100000
        
        # Monitoring state
        self.is_monitoring = False
        self.last_check_time = None
        
    async def get_real_time_options_data(self, symbol: str, expiration: str) -> List[OptionContract]:
        """Get real-time options chain data from Alpaca"""
        try:
            # Get options chain
            request = OptionChainRequest(
                underlying_symbol=symbol,
                expiration_date=expiration
            )
            
            options_data = self.options_client.get_option_chain(request)
            
            contracts = []
            
            # Handle dict response from Alpaca API
            if isinstance(options_data, dict):
                logger.info(f"Retrieved {len(options_data)} option contracts for {symbol}")
                
                for option_symbol, option in options_data.items():
                    try:
                        # Extract fields from the option object
                        # Check for nested structures like latest_quote
                        if hasattr(option, 'latest_quote') and option.latest_quote:
                            bid_price = float(getattr(option.latest_quote, 'bid_price', 0) or 0)
                            ask_price = float(getattr(option.latest_quote, 'ask_price', 0) or 0)
                        else:
                            bid_price = float(getattr(option, 'bid_price', 0) or 0)
                            ask_price = float(getattr(option, 'ask_price', 0) or 0)
                        
                        # Extract greeks if available
                        if hasattr(option, 'greeks') and option.greeks:
                            delta = float(getattr(option.greeks, 'delta', 0) or 0)
                            gamma = float(getattr(option.greeks, 'gamma', 0) or 0)
                            theta = float(getattr(option.greeks, 'theta', 0) or 0)
                            vega = float(getattr(option.greeks, 'vega', 0) or 0)
                        else:
                            delta = float(getattr(option, 'delta', 0) or 0)
                            gamma = float(getattr(option, 'gamma', 0) or 0)
                            theta = float(getattr(option, 'theta', 0) or 0)
                            vega = float(getattr(option, 'vega', 0) or 0)
                        
                        # Extract IV
                        if hasattr(option, 'implied_volatility'):
                            iv = float(option.implied_volatility or 0)
                        elif hasattr(option, 'greeks') and hasattr(option.greeks, 'implied_volatility'):
                            iv = float(option.greeks.implied_volatility or 0)
                        else:
                            iv = 0
                        
                        # Parse option symbol to extract details
                        # Alpaca format: "AAPL211015C00145000"
                        strike_price = float(getattr(option, 'strike_price', 0))
                        option_type = 'call' if 'C' in option_symbol else 'put'
                        
                        contract = OptionContract(
                            symbol=option_symbol,
                            strike_price=strike_price,
                            expiration_date=expiration,
                            option_type=option_type,
                            bid_price=bid_price,
                            ask_price=ask_price,
                            volume=int(getattr(option, 'volume', 0) or 0),
                            open_interest=int(getattr(option, 'open_interest', 0) or 0),
                            delta=delta,
                            gamma=gamma,
                            theta=theta,
                            vega=vega,
                            implied_volatility=iv
                        )
                        contracts.append(contract)
                        
                    except Exception as contract_error:
                        logger.warning(f"Error processing option {option_symbol}: {contract_error}")
                        continue
            else:
                logger.warning(f"Unexpected options data type: {type(options_data)}")
            
            logger.info(f"Successfully processed {len(contracts)} option contracts")
            return contracts
            
        except Exception as e:
            logger.error(f"Error getting options data: {e}")
            # Fallback to simulated data for demo purposes
            return self._generate_simulated_options_data(symbol, expiration)
    
    def _generate_simulated_options_data(self, symbol: str, expiration: str) -> List[OptionContract]:
        """Generate simulated options data as fallback"""
        logger.info(f"Generating simulated options data for {symbol}")
        contracts = []
        
        # Simulate reasonable strike prices around current price
        base_price = 450 if symbol == "SPY" else 350  # Rough approximation
        
        for i in range(20):  # Generate 20 strikes
            strike = base_price + (i - 10) * 5  # Strikes around base price
            
            # Call contract
            call_contract = OptionContract(
                symbol=f"{symbol}_{expiration.replace('-', '')}C{int(strike):08d}",
                strike_price=strike,
                expiration_date=expiration,
                option_type="call",
                bid_price=max(0.1, 10 - i * 0.5),
                ask_price=max(0.2, 10.1 - i * 0.5),
                volume=max(10, 200 - i * 10),
                open_interest=max(50, 1000 - i * 40),
                delta=max(0.05, 0.8 - i * 0.07),
                gamma=0.1,
                theta=-0.05,
                vega=0.2,
                implied_volatility=0.25 + i * 0.01
            )
            contracts.append(call_contract)
            
            # Put contract
            put_contract = OptionContract(
                symbol=f"{symbol}_{expiration.replace('-', '')}P{int(strike):08d}",
                strike_price=strike,
                expiration_date=expiration,
                option_type="put",
                bid_price=max(0.1, 5 + i * 0.3),
                ask_price=max(0.2, 5.1 + i * 0.3),
                volume=max(10, 150 - i * 7),
                open_interest=max(50, 800 - i * 30),
                delta=max(-0.95, -0.2 - i * 0.05),
                gamma=0.1,
                theta=-0.05,
                vega=0.2,
                implied_volatility=0.25 + i * 0.01
            )
            contracts.append(put_contract)
        
        return contracts
    
    def _parse_options_snapshot(self, symbol: str, snapshot, expiration: str) -> Optional[OptionContract]:
        """Parse Alpaca OptionsSnapshot into our OptionContract format"""
        try:
            # Extract nested data safely
            bid_price = 0.0
            ask_price = 0.0
            
            if hasattr(snapshot, 'latest_quote') and snapshot.latest_quote:
                bid_price = float(getattr(snapshot.latest_quote, 'bid_price', 0) or 0)
                ask_price = float(getattr(snapshot.latest_quote, 'ask_price', 0) or 0)
            
            # Extract Greeks from nested structure
            delta = gamma = theta = vega = 0.0
            if hasattr(snapshot, 'greeks') and snapshot.greeks:
                delta = float(getattr(snapshot.greeks, 'delta', 0) or 0)
                gamma = float(getattr(snapshot.greeks, 'gamma', 0) or 0)
                theta = float(getattr(snapshot.greeks, 'theta', 0) or 0)
                vega = float(getattr(snapshot.greeks, 'vega', 0) or 0)
            
            # Extract strike and type from symbol
            strike_price = self._extract_strike_from_symbol(symbol)
            option_type = self._extract_type_from_symbol(symbol)
            
            # Extract other fields
            volume = int(getattr(snapshot, 'volume', 0) or 0)
            open_interest = int(getattr(snapshot, 'open_interest', 0) or 0)
            implied_volatility = float(getattr(snapshot, 'implied_volatility', 0) or 0)
            
            return OptionContract(
                symbol=symbol,
                strike_price=strike_price,
                expiration_date=expiration,
                option_type=option_type,
                bid_price=bid_price,
                ask_price=ask_price,
                volume=volume,
                open_interest=open_interest,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                implied_volatility=implied_volatility
            )
        except Exception as e:
            logger.error(f"Failed to parse snapshot for {symbol}: {e}")
            return None
    
    def _extract_strike_from_symbol(self, symbol: str) -> float:
        """Extract strike price from option symbol"""
        try:
            # Alpaca format: SPY250131C00450000
            # The last 8 digits are the strike price (in cents)
            strike_str = symbol[-8:]
            strike_cents = int(strike_str)
            return strike_cents / 100.0
        except:
            logger.error(f"Failed to extract strike from {symbol}")
            return 0.0
    
    def _extract_type_from_symbol(self, symbol: str) -> str:
        """Extract option type from symbol"""
        try:
            # Check for C or P in the symbol
            if 'C' in symbol[6:]:  # After the underlying and date
                return "call"
            elif 'P' in symbol[6:]:
                return "put"
            else:
                return "unknown"
        except:
            logger.error(f"Failed to extract type from {symbol}")
            return "unknown"
    
    async def calculate_current_trade_value(self, trade: Trade) -> Tuple[float, float]:
        """Calculate current value and P&L of a trade using real options data"""
        try:
            # Get current options prices
            short_contracts = await self.get_real_time_options_data(
                trade.symbol, 
                trade.short_leg.expiration_date
            )
            
            long_contracts = await self.get_real_time_options_data(
                trade.symbol,
                trade.long_leg.expiration_date
            )
            
            # Find matching contracts
            short_current = None
            long_current = None
            
            for contract in short_contracts:
                if (contract.strike_price == trade.short_leg.strike_price and 
                    contract.option_type == trade.short_leg.option_type):
                    short_current = contract
                    break
            
            for contract in long_contracts:
                if (contract.strike_price == trade.long_leg.strike_price and
                    contract.option_type == trade.long_leg.option_type):
                    long_current = contract
                    break
            
            if short_current and long_current:
                # Calculate spread value
                # For credit spreads: we sold the spread, so lower value is better
                current_spread_value = (short_current.ask_price - long_current.bid_price) * 100 * trade.contracts
                
                # P&L = Entry Credit - Current Spread Value  
                unrealized_pnl = trade.entry_credit - current_spread_value
                
                return current_spread_value, unrealized_pnl
            else:
                # Fallback to estimated values
                return trade.current_value, trade.unrealized_pnl
                
        except Exception as e:
            logger.error(f"Error calculating trade value: {e}")
            return trade.current_value, trade.unrealized_pnl
    
    async def execute_trade_closure(self, trade: Trade, reason: str) -> bool:
        """Actually close a trade by submitting closing orders"""
        try:
            logger.info(f"Closing trade {trade.trade_id}: {reason}")
            
            # Set exit reason
            trade.exit_reason = reason
            
            # For credit spreads, we need to BUY BACK the spread to close
            # This means: BUY the short leg, SELL the long leg
            
            orders_submitted = []
            
            # Close short leg (BUY back what we sold)
            short_order = MarketOrderRequest(
                symbol=trade.short_leg.symbol,
                qty=trade.contracts,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            short_response = self.trading_client.submit_order(short_order)
            orders_submitted.append(short_response)
            logger.info(f"Submitted BUY order for short leg: {short_response.id}")
            
            # Close long leg (SELL what we bought)  
            long_order = MarketOrderRequest(
                symbol=trade.long_leg.symbol,
                qty=trade.contracts,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            
            long_response = self.trading_client.submit_order(long_order)
            orders_submitted.append(long_response)
            logger.info(f"Submitted SELL order for long leg: {long_response.id}")
            
            # Update trade status
            trade.status = "CLOSING"
            
            # Wait for orders to fill
            await self.wait_for_order_fills(orders_submitted, trade)
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing trade {trade.trade_id}: {e}")
            return False
    
    async def wait_for_order_fills(self, orders: List, trade: Trade, timeout: int = 300):
        """Wait for orders to fill and update trade status"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            all_filled = True
            
            for order in orders:
                # Check order status
                order_status = self.trading_client.get_order_by_id(order.id)
                
                if order_status.status not in ["filled", "partially_filled"]:
                    all_filled = False
                    break
            
            if all_filled:
                # All orders filled - trade is closed
                trade.status = "closed"
                trade.exit_time = datetime.now()
                
                # Calculate final P&L
                current_value, final_pnl = await self.calculate_current_trade_value(trade)
                trade.realized_pnl = final_pnl
                trade.unrealized_pnl = 0  # No longer unrealized
                
                logger.info(f"Trade {trade.trade_id} successfully closed. Final P&L: ${final_pnl:.2f}")
                
                # Update daily P&L
                self.daily_pnl += final_pnl
                
                # Move to closed trades
                self.closed_trades.append(trade)
                
                # Remove from active trades
                self.active_trades = [t for t in self.active_trades if t.trade_id != trade.trade_id]
                
                return True
            
            await asyncio.sleep(10)  # Check every 10 seconds
        
        logger.warning(f"Trade {trade.trade_id} closure timed out")
        return False
    
    async def check_exit_conditions(self, trade: Trade) -> Tuple[bool, str]:
        """Check if trade should be closed based on strategy rules
        
        Returns:
            Tuple[bool, str]: (should_close, reason)
        """
        
        # Update current trade value
        current_value, unrealized_pnl = await self.calculate_current_trade_value(trade)
        trade.current_value = current_value
        trade.unrealized_pnl = unrealized_pnl
        
        # Calculate days to expiration
        exp_date = datetime.strptime(trade.short_leg.expiration_date, '%Y-%m-%d')
        trade.days_to_expiration = (exp_date.date() - datetime.now().date()).days
        
        # Check profit target (35% of max profit)
        if unrealized_pnl >= trade.profit_target:
            return True, f"PROFIT_TARGET: ${unrealized_pnl:.2f} >= ${trade.profit_target:.2f}"
        
        # Check stop loss (75% of max loss)
        max_loss_threshold = trade.max_loss * self.rules.stop_loss_percent
        if unrealized_pnl <= -max_loss_threshold:
            return True, f"STOP_LOSS: ${unrealized_pnl:.2f} <= ${-max_loss_threshold:.2f}"
        
        # Check time stop (close at 5 DTE)
        if trade.days_to_expiration <= self.rules.time_stop_dte:
            return True, f"TIME_STOP: {trade.days_to_expiration} DTE <= {self.rules.time_stop_dte}"
        
        # Check daily loss limit
        if self.daily_pnl <= -self.rules.max_daily_loss:
            return True, f"DAILY_LOSS_LIMIT: ${self.daily_pnl:.2f} <= ${-self.rules.max_daily_loss:.2f}"
        
        return False, "No exit conditions met"
    
    async def monitor_all_trades(self):
        """Monitor all active trades and execute closures"""
        if not self.active_trades:
            return
        
        logger.info(f"Monitoring {len(self.active_trades)} active trades...")
        
        for trade in self.active_trades.copy():  # Use copy to avoid modification during iteration
            try:
                should_close, exit_reason = await self.check_exit_conditions(trade)
                
                if should_close:
                    logger.info(f"Exit condition met for trade {trade.trade_id}: {exit_reason}")
                    
                    # Execute trade closure
                    success = await self.execute_trade_closure(trade, exit_reason)
                    
                    if success:
                        logger.info(f"✅ Successfully closed trade {trade.trade_id}")
                    else:
                        logger.error(f"❌ Failed to close trade {trade.trade_id}")
                else:
                    # Log current status
                    logger.info(f"Trade {trade.trade_id}: ${trade.unrealized_pnl:.2f} P&L, {trade.days_to_expiration} DTE")
                    
            except Exception as e:
                logger.error(f"Error monitoring trade {trade.trade_id}: {e}")
        
        self.last_check_time = datetime.now()
    
    async def start_monitoring(self):
        """Start the trade monitoring loop"""
        self.is_monitoring = True
        logger.info("🔍 Starting trade monitoring...")
        
        while self.is_monitoring:
            try:
                # Only monitor during market hours
                now = datetime.now()
                market_open = now.replace(hour=9, minute=30, second=0)
                market_close = now.replace(hour=16, minute=0, second=0)
                
                if market_open <= now <= market_close and now.weekday() < 5:
                    await self.monitor_all_trades()
                else:
                    logger.info("Market closed - monitoring paused")
                
                # Wait for next check
                await asyncio.sleep(self.rules.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    def stop_monitoring(self):
        """Stop the trade monitoring loop"""
        self.is_monitoring = False
        logger.info("🛑 Stopping trade monitoring...")
    
    async def add_trade(self, trade_data: Dict[str, Any]) -> Trade:
        """Add a new trade to monitoring"""
        
        # Create Trade object
        trade = Trade(
            trade_id=f"TRADE_{len(self.active_trades) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            symbol=trade_data['symbol'],
            strategy_type=trade_data['strategy_type'],
            spread_type=trade_data['spread_type'],
            short_leg=trade_data['short_leg'],
            long_leg=trade_data['long_leg'],
            contracts=trade_data['contracts'],
            entry_time=datetime.now(),
            entry_credit=trade_data['entry_credit'],
            max_loss=trade_data['max_loss'],
            current_value=trade_data['entry_credit'],
            unrealized_pnl=0,
            status="active",
            profit_target=trade_data['entry_credit'] * self.rules.profit_target_percent,
            stop_loss_target=trade_data['max_loss'] * self.rules.stop_loss_percent,
            days_to_expiration=trade_data.get('days_to_expiration', 14),
            probability_profit=trade_data.get('probability_profit', 75),
            confidence_score=trade_data.get('confidence_score', 80),
            claude_reasoning=trade_data.get('claude_reasoning', '')
        )
        
        self.active_trades.append(trade)
        
        logger.info(f"✅ Added trade {trade.trade_id} to monitoring")
        logger.info(f"   Profit Target: ${trade.profit_target:.2f}")
        logger.info(f"   Stop Loss: ${-trade.stop_loss_target:.2f}")
        logger.info(f"   Time Stop: {self.rules.time_stop_dte} DTE")
        
        return trade
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get summary of all trades and performance"""
        # Separate active and closed trades
        active_trades = [t for t in self.active_trades if t.status != "closed"]
        closed_trades = getattr(self, 'closed_trades', [])
        
        # If no trades at all
        if not active_trades and not closed_trades:
            return {
                "total_trades": 0,
                "open_trades": 0,
                "closed_trades": 0,
                "total_credit": 0,
                "total_risk": 0,
                "unrealized_pnl": 0,
                "realized_pnl": 0,
                "total_pnl": 0,
                "daily_pnl": self.daily_pnl,
                "win_rate": 0,
                "average_win": 0,
                "average_loss": 0,
                "profit_factor": 0,
                "monitoring_active": self.is_monitoring,
                "last_check": self.last_check_time
            }
        
        # Calculate metrics for active trades
        total_credit = sum(t.entry_credit for t in active_trades) if active_trades else 0
        total_risk = sum(t.max_loss for t in active_trades) if active_trades else 0
        unrealized_pnl = sum(t.unrealized_pnl for t in active_trades) if active_trades else 0
        
        # Calculate metrics for closed trades
        realized_pnl = sum(t.realized_pnl for t in closed_trades) if closed_trades else 0
        wins = [t for t in closed_trades if t.realized_pnl > 0]
        losses = [t for t in closed_trades if t.realized_pnl < 0]
        
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0
        average_win = (sum(t.realized_pnl for t in wins) / len(wins)) if wins else 0
        average_loss = (sum(t.realized_pnl for t in losses) / len(losses)) if losses else 0
        
        # Calculate profit factor
        total_wins = sum(t.realized_pnl for t in wins) if wins else 0
        total_losses = abs(sum(t.realized_pnl for t in losses)) if losses else 0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        return {
            "total_trades": len(active_trades) + len(closed_trades),
            "open_trades": len(active_trades),
            "closed_trades": len(closed_trades),
            "total_credit": total_credit,
            "total_risk": total_risk,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "total_pnl": unrealized_pnl + realized_pnl,
            "daily_pnl": self.daily_pnl,
            "win_rate": round(win_rate, 1),
            "average_win": round(average_win, 2),
            "average_loss": round(average_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "monitoring_active": self.is_monitoring,
            "last_check": self.last_check_time
        }
    
    async def execute_options_trade(self, symbol: str, analysis: Dict[str, Any], market_data: Dict[str, Any]) -> Trade:
        """Execute an options trade based on Claude's analysis"""
        try:
            logger.info(f"Executing {analysis['spread_type']} for {symbol}")
            
            # Get the expiration date
            expiration_days = analysis.get('expiration_days', 14)
            expiration_date = (datetime.now() + timedelta(days=expiration_days)).strftime('%Y-%m-%d')
            
            # Get options chain
            options_data = await self.get_real_time_options_data(symbol, expiration_date)
            
            # Find the specific contracts
            short_contract = None
            long_contract = None
            
            for contract in options_data:
                if contract.strike_price == analysis['short_strike'] and contract.option_type == analysis['spread_type'].split('_')[0]:
                    short_contract = contract
                elif contract.strike_price == analysis['long_strike'] and contract.option_type == analysis['spread_type'].split('_')[0]:
                    long_contract = contract
            
            if not short_contract or not long_contract:
                logger.error(f"Could not find matching contracts for strikes {analysis['short_strike']}/{analysis['long_strike']}")
                return None
            
            # Calculate actual credit and validate
            actual_credit = (short_contract.bid_price - long_contract.ask_price) * 100 * analysis['contracts']
            
            if actual_credit <= 0:
                logger.warning(f"No credit available for spread: ${actual_credit:.2f}")
                return None
            
            # Execute the trades
            orders = []
            
            # Sell short leg
            short_order = MarketOrderRequest(
                symbol=short_contract.symbol,
                qty=analysis['contracts'],
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            
            short_response = self.trading_client.submit_order(short_order)
            orders.append(short_response)
            logger.info(f"Submitted SELL order for short leg: {short_response.id}")
            
            # Buy long leg
            long_order = MarketOrderRequest(
                symbol=long_contract.symbol,
                qty=analysis['contracts'],
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            long_response = self.trading_client.submit_order(long_order)
            orders.append(long_response)
            logger.info(f"Submitted BUY order for long leg: {long_response.id}")
            
            # Create trade object
            max_loss = abs(analysis['short_strike'] - analysis['long_strike']) * 100 * analysis['contracts']
            
            trade_data = {
                'symbol': symbol,
                'strategy_type': analysis['spread_type'],
                'spread_type': analysis['spread_type'],
                'short_leg': short_contract,
                'long_leg': long_contract,
                'contracts': analysis['contracts'],
                'entry_credit': actual_credit,
                'max_loss': max_loss,
                'days_to_expiration': expiration_days,
                'probability_profit': analysis.get('probability_profit', 65),
                'confidence_score': analysis['confidence'],
                'claude_reasoning': analysis['reasoning']
            }
            
            trade = await self.add_trade(trade_data)
            
            # Log execution
            logger.info(f"Trade executed successfully: {trade.trade_id}")
            logger.info(f"   Type: {analysis['spread_type']}")
            logger.info(f"   Strikes: ${analysis['short_strike']}/{analysis['long_strike']}")
            logger.info(f"   Credit: ${actual_credit:.2f}")
            logger.info(f"   Max Loss: ${max_loss:.2f}")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return None