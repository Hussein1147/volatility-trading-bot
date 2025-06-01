#!/usr/bin/env python3
"""
Position tracker for monitoring active options positions in Alpaca
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderStatus, QueryOrderStatus
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class PositionTracker:
    """Track and monitor active options positions"""
    
    def __init__(self, paper_trading: bool = True):
        # Determine which API keys to use
        if paper_trading:
            api_key = os.getenv('ALPACA_API_KEY_PAPER_TRADING')
            secret_key = os.getenv('ALPACA_SECRET_KEY_PAPER_TRADING')
        else:
            api_key = os.getenv('ALPACA_API_KEY')
            secret_key = os.getenv('ALPACA_SECRET_KEY')
            
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper_trading
        )
        self.paper_trading = paper_trading
        
    def get_all_positions(self) -> List[Dict]:
        """Get all current positions from Alpaca"""
        try:
            positions = self.trading_client.get_all_positions()
            
            position_list = []
            for position in positions:
                position_dict = {
                    'symbol': position.symbol,
                    'qty': int(position.qty),
                    'side': position.side,
                    'market_value': float(position.market_value or 0),
                    'cost_basis': float(position.cost_basis or 0),
                    'unrealized_pl': float(position.unrealized_pl or 0),
                    'unrealized_plpc': float(position.unrealized_plpc or 0) * 100,  # Convert to percentage
                    'current_price': float(position.current_price or 0),
                    'avg_entry_price': float(position.avg_entry_price or 0),
                    'asset_class': position.asset_class,
                    'exchange': position.exchange
                }
                
                # Check if it's an options position
                if position.asset_class == 'us_option':
                    # Parse option details from symbol
                    position_dict['is_option'] = True
                    position_dict['underlying'] = position.symbol[:3]  # First 3 chars are usually the underlying
                    # Add more option-specific parsing as needed
                else:
                    position_dict['is_option'] = False
                    
                position_list.append(position_dict)
                
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_option_positions(self) -> List[Dict]:
        """Get only options positions"""
        all_positions = self.get_all_positions()
        return [p for p in all_positions if p.get('is_option', False)]
    
    def get_recent_orders(self, limit: int = 50) -> List[Dict]:
        """Get recent orders to track executions"""
        try:
            request = GetOrdersRequest(
                status=QueryOrderStatus.ALL,
                limit=limit,
                nested=True  # Include nested orders
            )
            
            orders = self.trading_client.get_orders(filter=request)
            
            order_list = []
            for order in orders:
                order_dict = {
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': int(order.qty),
                    'side': order.side.value,
                    'type': order.order_type.value,
                    'status': order.status.value,
                    'filled_qty': int(order.filled_qty or 0),
                    'filled_avg_price': float(order.filled_avg_price or 0),
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'asset_class': order.asset_class.value,
                    'order_class': order.order_class.value if order.order_class else None
                }
                
                # Check if it's an options order
                if order.asset_class.value == 'us_option':
                    order_dict['is_option'] = True
                else:
                    order_dict['is_option'] = False
                    
                order_list.append(order_dict)
                
            return order_list
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def get_filled_orders_today(self) -> List[Dict]:
        """Get orders filled today"""
        orders = self.get_recent_orders()
        today = datetime.now().date()
        
        filled_today = []
        for order in orders:
            if (order['status'] == 'filled' and 
                order.get('filled_at') and 
                order['filled_at'].date() == today):
                filled_today.append(order)
                
        return filled_today
    
    def calculate_spread_positions(self, positions: List[Dict]) -> List[Dict]:
        """Group options positions into spreads"""
        # Group by underlying and expiration
        spreads = {}
        
        for pos in positions:
            if not pos.get('is_option'):
                continue
                
            # Extract underlying from option symbol
            # Alpaca option symbols follow format: SPY230630C00400000
            symbol = pos['symbol']
            underlying = symbol[:3]  # First 3 chars
            
            # Group by underlying
            if underlying not in spreads:
                spreads[underlying] = []
            spreads[underlying].append(pos)
        
        # Identify credit spreads (one long, one short position)
        spread_list = []
        for underlying, positions in spreads.items():
            # Sort by strike price
            positions.sort(key=lambda x: x['symbol'])
            
            # Look for pairs (simplified - you may need more sophisticated matching)
            if len(positions) >= 2:
                for i in range(0, len(positions), 2):
                    if i + 1 < len(positions):
                        spread = {
                            'underlying': underlying,
                            'type': 'credit_spread',
                            'short_leg': positions[i] if positions[i]['qty'] < 0 else positions[i+1],
                            'long_leg': positions[i+1] if positions[i]['qty'] < 0 else positions[i],
                            'net_credit': abs(positions[i]['cost_basis']) - abs(positions[i+1]['cost_basis']),
                            'unrealized_pl': positions[i]['unrealized_pl'] + positions[i+1]['unrealized_pl']
                        }
                        spread_list.append(spread)
                        
        return spread_list
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            account = self.trading_client.get_account()
            
            return {
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'transfers_blocked': account.transfers_blocked,
                'account_blocked': account.account_blocked,
                'daytrade_count': account.daytrade_count,
                'daytrading_buying_power': float(account.daytrading_buying_power or 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}

# Standalone functions for easy access
def get_current_positions(paper_trading: bool = True) -> List[Dict]:
    """Get all current positions"""
    tracker = PositionTracker(paper_trading)
    return tracker.get_all_positions()

def get_option_spreads(paper_trading: bool = True) -> List[Dict]:
    """Get current option spread positions"""
    tracker = PositionTracker(paper_trading)
    positions = tracker.get_option_positions()
    return tracker.calculate_spread_positions(positions)

def get_todays_trades(paper_trading: bool = True) -> List[Dict]:
    """Get trades executed today"""
    tracker = PositionTracker(paper_trading)
    return tracker.get_filled_orders_today()