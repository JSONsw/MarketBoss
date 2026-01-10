"""Exposure limit checks.

Provides validation of portfolio exposure against hard risk limits
including position sizing, leverage, and per-instrument caps.
"""

from typing import Dict, List, Tuple
from src.monitoring.structured_logger import get_logger

logger = get_logger()


class ExposureLimitError(Exception):
    """Raised when exposure exceeds configured limits."""
    pass


def check_exposure(
    portfolio: Dict,
    max_position_size: float = 100000.0,
    max_leverage: float = 2.0,
    per_instrument_limit: float = 50000.0,
) -> Tuple[bool, List[str]]:
    """
    Validate portfolio exposure against risk limits.

    :param portfolio: Dict with 'cash', 'positions' (symbol -> qty*price dict)
    :param max_position_size: Maximum notional per trade
    :param max_leverage: Maximum portfolio leverage (total_exposure / cash)
    :param per_instrument_limit: Max exposure per instrument
    :return: (all_ok, list_of_violations)
    """
    violations = []
    
    if not portfolio:
        return True, []
    
    cash = portfolio.get("cash", 0.0)
    positions = portfolio.get("positions", {})
    
    # Calculate total exposure
    total_exposure = 0.0
    for symbol, exposure in positions.items():
        exposure_val = float(exposure) if exposure is not None else 0.0
        
        # Check per-instrument limit
        if abs(exposure_val) > per_instrument_limit:
            violations.append(f"{symbol}: exposure ${abs(exposure_val):.2f} exceeds limit ${per_instrument_limit:.2f}")
            logger.warning("exposure_limit_violation", symbol=symbol, exposure=exposure_val, limit=per_instrument_limit)
        
        # Check max position size
        if abs(exposure_val) > max_position_size:
            violations.append(f"{symbol}: position size ${abs(exposure_val):.2f} exceeds max ${max_position_size:.2f}")
            logger.warning("position_size_violation", symbol=symbol, size=exposure_val, limit=max_position_size)
        
        total_exposure += abs(exposure_val)
    
    # Check leverage
    if cash > 0:
        leverage = total_exposure / cash
        if leverage > max_leverage:
            violations.append(f"Leverage {leverage:.2f}x exceeds limit {max_leverage:.2f}x")
            logger.warning("leverage_violation", leverage=leverage, limit=max_leverage)
    
    if violations:
        logger.error("exposure_check_failed", violations=violations)
        return False, violations
    
    logger.info("exposure_check_passed", total_exposure=total_exposure, cash=cash)
    return True, []


__all__ = ["check_exposure", "ExposureLimitError"]
