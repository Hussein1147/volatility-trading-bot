#!/usr/bin/env python3
"""
Simulated P&L tracker for dev mode
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict
import sqlite3

class SimulatedPnLTracker:
    """Track simulated P&L for dev mode trades"""
    
    def __init__(self):
        self.trades = []
        self.closed_trades = []
        self._load_from_database()
        
    def add_trade(self, trade_data: Dict):
        """Add a simulated trade"""
        trade = {
            'id': trade_data.get('trade_id', f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            'symbol': trade_data['symbol'],
            'spread_type': trade_data['spread_type'],
            'entry_credit': trade_data['entry_credit'],
            'max_loss': trade_data['max_loss'],
            'entry_time': trade_data.get('entry_time', datetime.now()),
            'status': 'open',
            'current_value': trade_data['entry_credit'],
            'unrealized_pnl': 0,
            'is_winner': random.random() < 0.7  # Determine fate when trade is created
        }
        self.trades.append(trade)
        
    def update_positions(self):
        """Simulate P&L changes for open positions"""
        for trade in self.trades:
            if trade['status'] == 'open':
                # Calculate time decay
                days_held = (datetime.now() - trade['entry_time']).days
                
                # Simulate realistic P&L based on time and randomness
                # Most credit spreads should be profitable
                base_profit_rate = 0.7  # 70% win rate
                
                if trade.get('is_winner', True):
                    # Winning trade - time decay works in our favor
                    # Add some randomness to make it more realistic
                    decay_factor = min(days_held * 0.08 + random.uniform(-0.02, 0.02), 0.5)  # Up to 50% profit
                    trade['current_value'] = trade['entry_credit'] * (1 - decay_factor)
                    trade['unrealized_pnl'] = trade['entry_credit'] - trade['current_value']
                else:
                    # Losing trade - move against us
                    loss_factor = random.uniform(0.1, 0.5)
                    # Current value increases (costs more to close)
                    # max_loss is already the NET loss amount
                    trade['current_value'] = trade['entry_credit'] + trade['max_loss'] * loss_factor
                    # P&L = Credit received - Cost to close (negative since cost > credit)
                    trade['unrealized_pnl'] = trade['entry_credit'] - trade['current_value']
                
                # Check for exit conditions
                profit_pct = trade['unrealized_pnl'] / trade['entry_credit']
                
                # Take profit at 35%
                if profit_pct >= 0.35:
                    trade['status'] = 'closed'
                    trade['exit_time'] = datetime.now()
                    trade['realized_pnl'] = trade['unrealized_pnl']
                    trade['exit_reason'] = 'Profit Target'
                    self.closed_trades.append(trade)
                
                # Stop loss at 75% of credit (meaning we lose 75% of what we collected)
                elif trade['unrealized_pnl'] <= -trade['entry_credit'] * 0.75:
                    trade['status'] = 'closed'
                    trade['exit_time'] = datetime.now()
                    trade['realized_pnl'] = trade['unrealized_pnl']
                    trade['exit_reason'] = 'Stop Loss'
                    self.closed_trades.append(trade)
        
        # Remove closed trades from active list
        self.trades = [t for t in self.trades if t['status'] == 'open']
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio P&L summary"""
        self.update_positions()
        
        total_unrealized = sum(t['unrealized_pnl'] for t in self.trades)
        total_realized = sum(t.get('realized_pnl', 0) for t in self.closed_trades)
        
        open_trades = len(self.trades)
        closed_trades = len(self.closed_trades)
        
        # Calculate win rate
        winning_trades = len([t for t in self.closed_trades if t.get('realized_pnl', 0) > 0])
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        # Calculate average P&L
        avg_win = 0
        avg_loss = 0
        if self.closed_trades:
            wins = [t['realized_pnl'] for t in self.closed_trades if t.get('realized_pnl', 0) > 0]
            losses = [t['realized_pnl'] for t in self.closed_trades if t.get('realized_pnl', 0) < 0]
            
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
        
        return {
            'open_trades': open_trades,
            'closed_trades': closed_trades,
            'total_trades': open_trades + closed_trades,
            'unrealized_pnl': total_unrealized,
            'realized_pnl': total_realized,
            'total_pnl': total_unrealized + total_realized,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }
    
    def get_open_positions(self) -> List[Dict]:
        """Get list of open positions"""
        self.update_positions()
        return self.trades
    
    def get_trade_history(self) -> List[Dict]:
        """Get closed trades history"""
        return self.closed_trades
    
    def _load_from_database(self):
        """Load simulated trades from database"""
        try:
            conn = sqlite3.connect('trade_history.db')
            cursor = conn.cursor()
            
            # Load recent simulated trades from the last 24 hours
            cursor.execute("""
                SELECT symbol, spread_type, credit, contracts, timestamp
                FROM trades 
                WHERE status = 'SIMULATED' 
                AND timestamp > datetime('now', '-1 day')
                ORDER BY timestamp DESC
            """)
            
            for row in cursor.fetchall():
                symbol, spread_type, credit, contracts, timestamp = row
                entry_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                
                # Calculate total credit (credit is per contract)
                total_credit = credit * contracts * 100
                # Max loss per contract = spread width - credit per contract
                max_loss_per_contract = 5.00 - credit  # $5 spread width
                max_loss = max_loss_per_contract * contracts * 100  # Total max loss
                
                trade = {
                    'id': f"SIM-{symbol}-{entry_time.strftime('%Y%m%d%H%M%S')}",
                    'symbol': symbol,
                    'spread_type': spread_type,
                    'entry_credit': total_credit,
                    'max_loss': max_loss,
                    'entry_time': entry_time,
                    'status': 'open',
                    'current_value': total_credit,
                    'unrealized_pnl': 0,
                    'is_winner': random.random() < 0.7  # 70% win rate
                }
                self.trades.append(trade)
            
            conn.close()
            
            # Update positions to calculate current P&L
            if self.trades:
                self.update_positions()
                
        except Exception as e:
            print(f"Error loading from database: {e}")

# Global instance for easy access
simulated_tracker = SimulatedPnLTracker()