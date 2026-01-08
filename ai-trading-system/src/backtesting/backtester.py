"""
Backtesting engine (simplified): applies slippage and transaction costs
to a sequence of trades and returns per-trade results.

This is intentionally simple for integration tests; a full backtester
will expand on position management, market data, and execution timing.
"""

from typing import Any, Dict, Iterable, List

from .slippage import (
    apply_trade,
    apply_volume_aware_slippage,
    compute_transaction_cost,
)
from src.monitoring.structured_logger import get_logger
from .order_book_sim import simulate_limit_order_fill, generate_synthetic_book


def run_backtest(
    signals: Iterable[Dict[str, Any]],
    slippage_bp: float = 0.0,
    commission_pct: float = 0.0,
    fixed_fee: float = 0.0,
) -> List[Dict[str, Any]]:
    """Run a simple backtest over provided `signals`."""
    logger = get_logger("backtester")
    results: List[Dict[str, Any]] = []

    for sig in signals:
        price = float(sig["price"])
        qty = float(sig["qty"])
        side = str(sig.get("side", "buy"))

        notional, cost = apply_trade(
            price,
            qty,
            side,
            slippage_bp,
            commission_pct=commission_pct,
            fixed_fee=fixed_fee,
        )

        executed_price = notional / qty if qty != 0 else price
        if qty != 0:
            slippage = executed_price - price
        else:
            slippage = 0.0

        if side.lower() == "sell":
            pnl = notional - cost
        else:
            pnl = -notional - cost

        results.append(
            {
                "executed_price": executed_price,
                "notional": notional,
                "cost": cost,
                "pnl": pnl,
                "slippage": slippage,
            }
        )

        logger.info(
            "trade_executed",
            tick=sig.get("tick") if isinstance(sig, dict) else None,
            side=side,
            qty=qty,
            executed_price=executed_price,
            notional=notional,
            cost=cost,
            pnl=pnl,
        )

    return results


def run_backtest_mtm(
    signals: Iterable[Dict[str, Any]],
    market_prices: Iterable[float],
    slippage_bp: float = 0.0,
    commission_pct: float = 0.0,
    fixed_fee: float = 0.0,
) -> List[Dict[str, Any]]:
    """Run a basic backtest with position tracking and mark-to-market."""
    logger = get_logger("backtester_mtm")
    results: List[Dict[str, Any]] = []
    position = 0.0
    cash = 0.0

    for sig, mkt_price in zip(signals, market_prices):
        price = float(sig["price"])
        qty = float(sig["qty"])
        side = str(sig.get("side", "buy"))

        notional, cost = apply_trade(
            price,
            qty,
            side,
            slippage_bp,
            commission_pct=commission_pct,
            fixed_fee=fixed_fee,
        )

        if side.lower() == "buy":
            position += qty
            cash -= notional + cost
        else:
            position -= qty
            cash += notional - cost

        mtm = cash + position * float(mkt_price)

        results.append(
            {
                "position": position,
                "cash": cash,
                "mtm": mtm,
                "executed_notional": notional,
                "cost": cost,
            }
        )

        logger.info(
            "mtm_update",
            position=position,
            cash=cash,
            mtm=mtm,
            executed_notional=notional,
            cost=cost,
        )

    return results


def run_backtest_ticks(
    signals_by_tick,
    market_prices: Iterable[float],
    slippage_bp: float = 0.0,
    commission_pct: float = 0.0,
    fixed_fee: float = 0.0,
) -> List[Dict[str, Any]]:
    """Simulate execution on an intraday (per-tick) price series."""
    tick_map = {}
    for item in signals_by_tick:
        if isinstance(item, (tuple, list)):
            tick, sig = item
        elif isinstance(item, dict) and "tick" in item and "signal" in item:
            tick = int(item["tick"])
            sig = item["signal"]
        else:
            raise ValueError(
                "signals_by_tick items must be either a (tick, signal) tuple "
                "or a dict with keys 'tick' and 'signal'"
            )
        tick_map.setdefault(int(tick), []).append(sig)

    logger = get_logger("backtester_ticks")
    executed: List[Dict[str, Any]] = []
    position = 0.0
    cash = 0.0
    prices_list = list(market_prices)

    for t in range(len(prices_list)):
        mprice = float(prices_list[t])
        for sig in tick_map.get(t, []):
            qty = float(sig.get("qty", 0.0))
            side = str(sig.get("side", "buy"))
            # Prefer order-book-driven fills if a book or flag provided
            book = sig.get("book")
            use_ob = sig.get("use_order_book") or (book is not None)

            if use_ob:
                # If no book provided, generate a simple synthetic book
                if book is None:
                    book = generate_synthetic_book(mid_price=mprice)

                # For buys, match against asks; for sells, match against bids
                if side.lower() == "buy":
                    book_levels = book.get("asks")
                else:
                    book_levels = book.get("bids")
                limit_price = sig.get("limit_price")

                ob_res = simulate_limit_order_fill(
                    order_qty=qty,
                    side=side,
                    limit_price=limit_price,
                    book_levels=book_levels,
                )

                qty_executed = float(ob_res.get("executed_qty", 0.0))
                avg_px = ob_res.get("avg_price")
                if avg_px is not None:
                    notional = float(avg_px) * qty_executed
                else:
                    notional = 0.0

                cost = compute_transaction_cost(
                    notional,
                    commission_pct=commission_pct,
                    fixed_fee=fixed_fee,
                )
            else:
                avail = sig.get("available_volume")
                if avail is not None:
                    filled_qty, executed_px, _ = apply_volume_aware_slippage(
                        mprice,
                        qty,
                        side,
                        slippage_bp,
                        available_volume=avail,
                    )
                    qty_executed = filled_qty
                    notional = executed_px * filled_qty
                    cost = compute_transaction_cost(
                        notional,
                        commission_pct=commission_pct,
                        fixed_fee=fixed_fee,
                    )
                else:
                    notional, cost = apply_trade(
                        mprice,
                        qty,
                        side,
                        slippage_bp,
                        commission_pct=commission_pct,
                        fixed_fee=fixed_fee,
                    )
                    qty_executed = qty

            if side.lower() == "buy":
                position += qty_executed
                cash -= notional + cost
            else:
                position -= qty_executed
                cash += notional - cost

            if qty_executed != 0:
                executed_price = notional / qty_executed
                slippage = executed_price - mprice
            else:
                slippage = 0.0

            if side.lower() == "sell":
                pnl = notional - cost
            else:
                pnl = -notional - cost

            executed.append(
                {
                    "tick": t,
                    "executed_price": executed_price,
                    "notional": notional,
                    "cost": cost,
                    "pnl": pnl,
                    "slippage": slippage,
                    "position": position,
                    "cash": cash,
                }
            )

            logger.info(
                "tick_trade",
                tick=t,
                side=side,
                qty=qty,
                executed_price=executed_price,
                notional=notional,
                cost=cost,
                position=position,
                cash=cash,
            )

    return executed
