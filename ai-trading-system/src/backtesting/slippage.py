"""Slippage and transaction-cost helpers for backtesting.

These functions are small, deterministic, and easy to unit-test. They
are intended to be used by the backtester to adjust executed prices and
compute P&L after fees.
"""

from typing import Tuple


def apply_slippage(price: float, side: str, slippage_bp: float) -> float:
    """Apply slippage in basis points to a price.

    side: 'buy' or 'sell'. `slippage_bp` is basis points (1 bp = 0.0001).
    For buys, price increases; for sells, price decreases.
    """
    if price is None:
        return price
    adj = (
        1.0 + (slippage_bp / 10000.0)
        if side.lower() == "buy"
        else 1.0 - (slippage_bp / 10000.0)
    )
    return price * adj


def compute_transaction_cost(
    notional: float, commission_pct: float = 0.0, fixed_fee: float = 0.0
) -> float:
    """Return total transaction cost given a notional trade amount.

    `commission_pct` is a fraction (e.g., 0.0005 for 5 bps). `fixed_fee`
    is an absolute cost per trade.
    """
    pct_cost = abs(notional) * float(commission_pct)
    return pct_cost + float(fixed_fee)


def apply_trade(
    price: float,
    qty: float,
    side: str,
    slippage_bp: float,
    commission_pct: float = 0.0,
    fixed_fee: float = 0.0,
) -> Tuple[float, float]:
    """Apply slippage and transaction costs to a trade.

    Returns executed_notional, total_cost
    """
    executed_price = apply_slippage(price, side, slippage_bp)
    notional = executed_price * qty
    cost = compute_transaction_cost(
        notional, commission_pct=commission_pct, fixed_fee=fixed_fee
    )
    return notional, cost


def apply_volume_aware_slippage(
    price: float,
    qty: float,
    side: str,
    slippage_bp: float,
    available_volume: float,
    impact_coeff: float = 0.25,
) -> Tuple[float, float, float]:
    """Apply volume-aware slippage and simulate partial fills.

    - `available_volume` is the market volume available to fill the order.
    - `impact_coeff` controls additional slippage when demand exceeds
      available volume.

    Returns (filled_qty, avg_executed_price, slippage_applied_bp).
    """
    if available_volume is None or available_volume <= 0:
        # No liquidity information; fallback to single-price execution
        executed_price = apply_slippage(price, side, slippage_bp)
        return qty, executed_price, slippage_bp

    # fraction of order filled by available liquidity
    fill_fraction = min(1.0, float(available_volume) / float(qty))

    # additional slippage increases as fill fraction decreases
    extra_slippage_bp = impact_coeff * (1.0 - fill_fraction) * slippage_bp
    effective_slippage_bp = float(slippage_bp) + float(extra_slippage_bp)

    executed_price = apply_slippage(price, side, effective_slippage_bp)
    filled_qty = qty * fill_fraction

    return filled_qty, executed_price, effective_slippage_bp


__all__ = [
    "apply_slippage",
    "compute_transaction_cost",
    "apply_trade",
    "apply_volume_aware_slippage",
]
