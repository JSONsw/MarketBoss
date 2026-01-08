from src.backtesting.walk_forward import walk_forward


def test_walk_forward_runs_windows():
    # Prepare two tiny windows
    win1_signals = [{"price": 10.0, "qty": 1.0, "side": "buy"}]
    win1_prices = [10.5]

    win2_signals = [{"price": 20.0, "qty": 2.0, "side": "sell"}]
    win2_prices = [19.5]

    windows = [
        (win1_signals, win1_prices),
        (win2_signals, win2_prices),
    ]

    all_results = walk_forward(
        windows,
        slippage_bp=1.0,
        commission_pct=0.0001,
        fixed_fee=0.0,
    )

    assert len(all_results) == 2
    assert len(all_results[0]) == 1
    assert len(all_results[1]) == 1
