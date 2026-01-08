from src.backtesting.backtester import run_backtest_ticks
from src.backtesting.metrics import cumulative_pnl, max_drawdown, trade_stats


def test_e2e_backtest_flow():
    """End-to-end integration test: tick simulation -> metrics."""

    # Market ticks (prices across 12 ticks)
    prices = [
        100.0, 100.2, 100.5, 100.3, 100.8, 101.0,
        100.7, 100.9, 101.2, 101.0, 100.6, 100.4,
    ]

    # Signals attach to ticks; include an order that exceeds available_volume
    signals = [
        (0, {"price": 100.0, "qty": 1.0, "side": "buy"}),
        (
            2,
            {
                "price": 100.5,
                "qty": 2.0,
                "side": "buy",
                "available_volume": 2.0,
            },
        ),
        (
            5,
            {
                "price": 101.0,
                "qty": 5.0,
                "side": "sell",
                "available_volume": 2.0,
            },
        ),
        (9, {"price": 101.0, "qty": 1.0, "side": "sell"}),
    ]

    res = run_backtest_ticks(
        signals,
        prices,
        slippage_bp=5.0,
        commission_pct=0.0002,
        fixed_fee=0.5,
    )

    # Basic checks: executed trades count matches signals
    assert len(res) == len(signals)

    # Compute per-trade pnl series and aggregate metrics
    pnls = [r["pnl"] for r in res]
    cum = cumulative_pnl(pnls)
    dd = max_drawdown(cum)
    stats = trade_stats(res)

    # Sanity assertions
    assert isinstance(cum, list) and len(cum) == len(pnls)
    assert dd >= 0.0
    assert stats["n_trades"] == float(len(res))

    # Ensure we see at least one non-zero pnl (trades impacted PnL)
    assert any(p != 0.0 for p in pnls)
