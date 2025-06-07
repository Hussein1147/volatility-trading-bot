"""
Dynamic position sizing based on confidence levels
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    contracts: int
    risk_amount: float
    risk_percentage: float
    confidence_tier: str
    book_type: str
    max_loss_per_contract: float
    total_max_loss: float
    
class DynamicPositionSizer:
    """
    Dynamic position sizing based on confidence and strategy rules
    
    Professional strategy tiers:
    - 70-79% confidence → Risk 3% of account
    - 80-89% confidence → Risk 5% of account  
    - 90%+ confidence → Risk 8% of account
    """
    
    def __init__(self, account_balance: float):
        self.account_balance = account_balance
        
        # Risk tiers based on confidence
        self.risk_tiers = {
            (70, 79): 0.03,   # 3%
            (80, 89): 0.05,   # 5%
            (90, 100): 0.08   # 8%
        }
        
        # Risk limits
        self.max_day_risk = 0.10  # 10% max day-at-risk
        self.income_pop_max_risk = 0.01  # 1% for income-pop trades
        
        # Current exposure tracking
        self.current_day_risk = 0.0
        self.open_positions = []
        
    def calculate_position_size(self, 
                              confidence: int,
                              max_loss_per_contract: float,
                              book_type: str = 'PRIMARY',
                              current_positions: Optional[list] = None) -> PositionSizeResult:
        """
        Calculate position size based on confidence and risk parameters
        
        Args:
            confidence: Confidence score (0-100)
            max_loss_per_contract: Maximum loss per contract
            book_type: 'PRIMARY' or 'INCOME_POP'
            current_positions: List of current open positions for risk check
            
        Returns:
            PositionSizeResult with sizing details
        """
        
        # Validate confidence
        if confidence < 70:
            logger.warning(f"Confidence {confidence}% below minimum threshold of 70%")
            return PositionSizeResult(
                contracts=0,
                risk_amount=0,
                risk_percentage=0,
                confidence_tier="Below threshold",
                book_type=book_type,
                max_loss_per_contract=max_loss_per_contract,
                total_max_loss=0
            )
        
        # Get risk percentage based on confidence tier
        risk_pct = self.get_risk_percentage(confidence, book_type)
        confidence_tier = self.get_confidence_tier(confidence)
        
        # Calculate current day-at-risk if positions provided
        if current_positions:
            self.current_day_risk = self.calculate_current_day_risk(current_positions)
        
        # Check if adding this position would exceed day risk limit
        if self.current_day_risk + risk_pct > self.max_day_risk:
            available_risk = max(0, self.max_day_risk - self.current_day_risk)
            if available_risk < 0.01:  # Less than 1% available
                logger.warning(f"Day risk limit reached. Current: {self.current_day_risk:.1%}, Max: {self.max_day_risk:.1%}")
                return PositionSizeResult(
                    contracts=0,
                    risk_amount=0,
                    risk_percentage=0,
                    confidence_tier=f"{confidence_tier} (Risk limit reached)",
                    book_type=book_type,
                    max_loss_per_contract=max_loss_per_contract,
                    total_max_loss=0
                )
            else:
                # Use available risk instead
                risk_pct = available_risk
                logger.info(f"Adjusted risk to {risk_pct:.1%} due to day limit")
        
        # Calculate position size
        risk_amount = self.account_balance * risk_pct
        contracts = int(risk_amount / max_loss_per_contract)
        
        # Ensure minimum 1 contract if risk allows
        if contracts == 0 and risk_amount >= max_loss_per_contract * 0.8:
            contracts = 1
            
        # Calculate actual risk with selected contracts
        total_max_loss = contracts * max_loss_per_contract
        actual_risk_pct = total_max_loss / self.account_balance
        
        logger.info(f"Position sizing: Confidence {confidence}% ({confidence_tier}) → "
                   f"{contracts} contracts, Risk ${risk_amount:.0f} ({risk_pct:.1%})")
        
        return PositionSizeResult(
            contracts=contracts,
            risk_amount=risk_amount,
            risk_percentage=actual_risk_pct,
            confidence_tier=confidence_tier,
            book_type=book_type,
            max_loss_per_contract=max_loss_per_contract,
            total_max_loss=total_max_loss
        )
    
    def get_risk_percentage(self, confidence: int, book_type: str) -> float:
        """Get risk percentage based on confidence and book type"""
        
        # Income-pop book has fixed 1% risk
        if book_type == 'INCOME_POP':
            return self.income_pop_max_risk
            
        # Primary book uses tiered risk
        for (low, high), risk_pct in self.risk_tiers.items():
            if low <= confidence <= high:
                return risk_pct
                
        # Default to highest tier if confidence > 100 (shouldn't happen)
        return 0.08
    
    def get_confidence_tier(self, confidence: int) -> str:
        """Get confidence tier description"""
        if confidence < 70:
            return "Below threshold"
        elif 70 <= confidence <= 79:
            return "Standard (3%)"
        elif 80 <= confidence <= 89:
            return "High (5%)"
        elif confidence >= 90:
            return "Very High (8%)"
        else:
            return "Unknown"
    
    def calculate_current_day_risk(self, positions: list) -> float:
        """Calculate current total day-at-risk from open positions"""
        total_risk = 0.0
        
        for position in positions:
            # Get max loss for position
            if hasattr(position, 'max_loss'):
                max_loss = position.max_loss
            elif hasattr(position, 'total_max_loss'):
                max_loss = position.total_max_loss
            else:
                # Estimate from spread width and contracts
                spread_width = abs(getattr(position, 'long_strike', 0) - getattr(position, 'short_strike', 0))
                contracts = getattr(position, 'contracts', 0)
                credit = getattr(position, 'entry_credit', 0)
                max_loss = (spread_width * 100 * contracts) - credit
                
            total_risk += max_loss
            
        return total_risk / self.account_balance
    
    def validate_position_limits(self, symbol: str, book_type: str, 
                               existing_positions: Dict[str, list]) -> Tuple[bool, str]:
        """
        Validate position limits per symbol and book
        
        Returns:
            (is_valid, reason)
        """
        
        # Check symbol concentration (max 20% in one symbol)
        symbol_exposure = 0.0
        if symbol in existing_positions:
            for pos in existing_positions[symbol]:
                symbol_exposure += pos.get('risk_percentage', 0)
                
        if symbol_exposure >= 0.20:
            return False, f"Symbol concentration limit reached for {symbol}"
            
        # Check book limits
        if book_type == 'INCOME_POP':
            # Max 5 income-pop positions
            income_pop_count = sum(1 for positions in existing_positions.values() 
                                 for pos in positions 
                                 if pos.get('book_type') == 'INCOME_POP')
            if income_pop_count >= 5:
                return False, "Income-Pop book limit reached (max 5)"
                
        return True, "OK"
    
    def update_account_balance(self, new_balance: float):
        """Update account balance for calculations"""
        self.account_balance = new_balance
        logger.info(f"Account balance updated to ${new_balance:,.2f}")