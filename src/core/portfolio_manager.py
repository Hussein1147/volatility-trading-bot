"""
Portfolio-level management for Greeks, events, and validation
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PortfolioGreeks:
    """Portfolio-level Greeks"""
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    net_contracts: int = 0
    
    def is_within_limits(self) -> Tuple[bool, str]:
        """Check if portfolio Greeks are within risk limits"""
        if abs(self.total_delta) > 0.30:
            return False, f"Portfolio delta {self.total_delta:.3f} exceeds ±0.30 limit"
        return True, "Within limits"

class PortfolioManager:
    """
    Manages portfolio-level constraints and validations
    """
    
    def __init__(self):
        self.max_portfolio_delta = 0.30
        self.max_day_risk_pct = 0.10  # 10% max day risk
        
        # Economic events that trigger blackouts
        self.blackout_events = ['FOMC', 'CPI', 'NFP', 'GDP', 'PCE']
        
    def calculate_portfolio_greeks(self, positions: List[Dict]) -> PortfolioGreeks:
        """
        Calculate total portfolio Greeks from all positions
        
        Args:
            positions: List of open positions with Greeks
            
        Returns:
            PortfolioGreeks object
        """
        portfolio = PortfolioGreeks()
        
        for pos in positions:
            # Extract Greeks if available
            if 'greeks' in pos and pos['greeks']:
                greeks = pos['greeks']
                contracts = pos.get('contracts', 1)
                
                # Aggregate Greeks (multiply by contracts and 100)
                multiplier = contracts * 100
                portfolio.total_delta += greeks.get('delta', 0) * multiplier
                portfolio.total_gamma += greeks.get('gamma', 0) * multiplier
                portfolio.total_theta += greeks.get('theta', 0) * multiplier
                portfolio.total_vega += greeks.get('vega', 0) * multiplier
                portfolio.net_contracts += contracts
                
        return portfolio
    
    def check_spread_quality(self, bid: float, ask: float, spread_width: float) -> Tuple[bool, float]:
        """
        Check if bid-ask spread is acceptable (≤ 1% of width)
        
        Args:
            bid: Bid price of the spread
            ask: Ask price of the spread  
            spread_width: Width of the spread in dollars
            
        Returns:
            (is_acceptable, spread_percentage)
        """
        if spread_width <= 0:
            return False, 0.0
            
        bid_ask_spread = ask - bid
        spread_pct = (bid_ask_spread / spread_width) * 100
        
        return spread_pct <= 1.0, spread_pct
    
    def check_credit_target(self, credit: float, spread_width: float, target_pct: float = 0.20) -> Tuple[bool, float]:
        """
        Check if credit meets target percentage of width
        
        Args:
            credit: Credit received
            spread_width: Width of the spread
            target_pct: Target credit as % of width (default 20%)
            
        Returns:
            (meets_target, actual_percentage)
        """
        if spread_width <= 0:
            return False, 0.0
            
        credit_pct = credit / (spread_width * 100)
        return credit_pct >= target_pct, credit_pct
    
    def is_in_blackout_window(self, current_date: datetime, events_calendar: List[Dict]) -> Tuple[bool, str]:
        """
        Check if we're in a blackout window (24h before/after major events)
        
        Args:
            current_date: Current datetime
            events_calendar: List of upcoming events with dates
            
        Returns:
            (in_blackout, event_name)
        """
        for event in events_calendar:
            event_date = event.get('date')
            event_name = event.get('name', '')
            
            if not event_date:
                continue
                
            # Check if event is a blackout trigger
            is_blackout_event = any(trigger in event_name.upper() for trigger in self.blackout_events)
            
            if is_blackout_event:
                # Convert to datetime if needed
                if isinstance(event_date, str):
                    event_date = datetime.strptime(event_date, '%Y-%m-%d')
                    
                # Check if within 24h window
                time_to_event = abs((event_date - current_date).total_seconds() / 3600)
                
                if time_to_event <= 24:
                    return True, event_name
                    
        return False, ""
    
    def calculate_day_risk(self, new_positions: List[Dict], existing_positions: List[Dict], 
                          account_balance: float) -> Tuple[float, bool]:
        """
        Calculate total day-at-risk including new positions
        
        Args:
            new_positions: Positions to be opened today
            existing_positions: Already open positions from today
            account_balance: Current account balance
            
        Returns:
            (total_risk_pct, is_within_limit)
        """
        total_day_risk = 0.0
        
        # Sum risk from existing positions opened today
        today = datetime.now().date()
        for pos in existing_positions:
            if pos.get('entry_date', datetime.min).date() == today:
                total_day_risk += pos.get('max_loss', 0)
                
        # Add risk from new positions
        for pos in new_positions:
            total_day_risk += pos.get('max_loss', 0)
            
        risk_pct = total_day_risk / account_balance if account_balance > 0 else 0
        
        return risk_pct, risk_pct <= self.max_day_risk_pct
    
    def should_hedge_vix(self, portfolio_greeks: PortfolioGreeks, avg_iv_rank: float) -> bool:
        """
        Determine if VIX hedge is needed
        
        Conditions:
        - Portfolio vega is negative (short volatility)
        - Average IV rank > 60
        
        Args:
            portfolio_greeks: Current portfolio Greeks
            avg_iv_rank: Average IV rank across universe
            
        Returns:
            True if VIX hedge should be added
        """
        return portfolio_greeks.total_vega < 0 and avg_iv_rank > 60
    
    def size_vix_hedge(self, account_balance: float, target_pct: float = 0.015) -> int:
        """
        Calculate VIX call contracts for hedge (1-2% notional)
        
        Args:
            account_balance: Current account balance
            target_pct: Target hedge size as % of account (default 1.5%)
            
        Returns:
            Number of VIX call contracts
        """
        # Assume VIX around 20 and each contract = $1000 notional
        vix_price = 20  # Approximate
        contract_notional = vix_price * 100
        
        target_notional = account_balance * target_pct
        contracts = int(target_notional / contract_notional)
        
        return max(1, contracts)  # At least 1 contract