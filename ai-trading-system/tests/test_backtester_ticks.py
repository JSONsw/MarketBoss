from src.backtesting.backtester import run_backtest_ticks


def test_tick_simulation_basic():
    # Signals: list of (tick_index, signal_dict)
    signals = [
        (0, {"price": 100.0, "qty": 1.0, "side": "buy"}),
        (2, {"price": 101.0, "qty": 1.0, "side": "sell"}),
    ]

    # Market price series for ticks 0..3
    prices = [100.0, 100.5, 101.0, 100.8]

    res = run_backtest_ticks(
        signals,
        prices,
        slippage_bp=5.0,
        commission_pct=0.0001,
        fixed_fee=0.0,
    )

    # Expect two executed trades
    assert len(res) == 2
    # Check ordering and tick fields
    assert res[0]["tick"] == 0
    assert res[1]["tick"] == 2
