"""
Configuration defaults for the trading system
"""
from typing import Dict, Any, List


DEFAULTS: Dict[str, Any] = {
    # Trading parameters
    "synthetic_pricing": True,
    "delta_target": 0.16,
    "dte_target": 9,  # Target days to expiration
    
    # Exit parameters
    "tier_targets": [0.50, 0.75, -2.50],  # +50%, +75%, -250% loss
    "contracts_by_tier": [0.4, 0.4, 0.2],
    "force_exit_days": 7,  # Default for short-dated options
    
    # Risk parameters
    "base_risk_pct": 0.03,  # 3% base risk
    "max_risk_pct": 0.08,   # 8% max risk (with IV boost)
    "confidence_threshold": 70,
    
    # Market parameters
    "min_iv_rank": 40,
    "min_price_move": 1.5,
    
    # Commission
    "commission_per_contract": 0.65,
}


def get_config(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get configuration with optional overrides
    
    Args:
        overrides: Dictionary of values to override defaults
        
    Returns:
        Complete configuration dictionary
    """
    config = DEFAULTS.copy()
    if overrides:
        config.update(overrides)
    
    # Adjust force_exit_days based on dte_target
    if config["dte_target"] <= 10:
        config["force_exit_days"] = min(config["force_exit_days"], 7)
    
    return config