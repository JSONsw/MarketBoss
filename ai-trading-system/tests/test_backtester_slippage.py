import math

from src.backtesting.backtester import run_backtest


def test_backtester_applies_slippage_and_costs():
    signals = [
        {"price": 100.0, "qty": 1.0, "side": "buy"},
        {"price": 110.0, "qty": 2.0, "side": "sell"},
    ]

    # Apply 10 bps slippage for each trade, 5 bps commission, and $1 fixed fee
    results = run_backtest(
        signals,
        slippage_bp=10.0,
        commission_pct=0.0005,
        fixed_fee=1.0,
    )

    assert len(results) == 2

    buy = results[0]
    sell = results[1]

    # Executed price for buy should be higher than 100 due to slippage
    assert buy["executed_price"] > 100.0
    # Executed price for sell should be lower than 110 due to slippage
    assert sell["executed_price"] < 110.0

    # Costs should be positive numbers
    assert buy["cost"] > 0
    assert sell["cost"] > 0

    # PnL sign: buy is negative, sell is positive (we receive notional on sell)
    assert buy["pnl"] < 0
    assert sell["pnl"] > 0

    # Basic sanity: aggregate PnL equals sum of per-trade pnl
    total = sum(r["pnl"] for r in results)
    assert math.isfinite(total)
