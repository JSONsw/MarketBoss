from src.backtesting.backtester import run_backtest_mtm


def test_run_backtest_mtm_basic():
    signals = [
        {"price": 100.0, "qty": 1.0, "side": "buy"},
        {"price": 105.0, "qty": 1.0, "side": "sell"},
    ]

    # Market prices for MTM (one per signal)
    market_prices = [101.0, 104.0]

    results = run_backtest_mtm(
        signals,
        market_prices,
        slippage_bp=5.0,
        commission_pct=0.0001,
        fixed_fee=0.5,
    )

    assert len(results) == 2

    first = results[0]
    second = results[1]

    # After first buy we should have a positive position
    assert first["position"] == 1.0
    # MTM should be a float
    assert isinstance(first["mtm"], float)

    # After sell, position should be back to zero
    assert second["position"] == 0.0
