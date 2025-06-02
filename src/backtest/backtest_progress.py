"""
Progress tracking for backtesting
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class BacktestProgress:
    """Track backtest progress"""
    current_day: int = 0
    total_days: int = 0
    current_date: Optional[datetime] = None
    trades_completed: int = 0
    is_rate_limited: bool = False
    message: str = ""
    
    @property
    def progress_percent(self) -> float:
        """Get progress as percentage"""
        if self.total_days == 0:
            return 0.0
        return min(self.current_day / self.total_days, 1.0)
    
    def get_status_message(self) -> str:
        """Get formatted status message"""
        if self.current_date:
            msg = f"Processing {self.current_date.strftime('%Y-%m-%d')} | Day {self.current_day}/{self.total_days} | {self.trades_completed} trades"
            if self.is_rate_limited:
                msg += " | ⏱️ Rate limited"
            return msg
        return "Initializing backtest..."