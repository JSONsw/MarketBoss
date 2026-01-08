from src.backtesting.synthetic_market import (
    generate_price_series,
    generate_volume_series,
)
from src.backtesting.backtester import run_backtest_ticks


def _assert_basic_results(signals, prices, **kwargs):
    res = run_backtest_ticks(signals, prices, **kwargs)
    assert isinstance(res, list)
    assert len(res) == len(signals)
    # ensure pnl entries are finite
    assert all(isinstance(r.get("pnl"), float) for r in res)


def test_gap_opening_scenario():
    # Simulate a gap open at tick 0
    prices = generate_price_series(seed=1, length=50)
    # Make a sharp opening gap
    prices[0] = prices[0] * 1.20

    volumes = generate_volume_series(seed=2, length=50, avg=100.0, std=20.0)

    signals = [
        (
            0,
            {
                "price": prices[0],
                "qty": 1.0,
                "side": "buy",
                "available_volume": volumes[0],
            },
        ),
        (
            10,
            {
                "price": prices[10],
                "qty": 1.0,
                "side": "sell",
                "available_volume": volumes[10],
            },
        ),
    ]

    _assert_basic_results(
        signals, prices, slippage_bp=10.0, commission_pct=0.0002
    )


def test_liquidity_drought():
    # Long zero-volume stretch in middle of series
    prices = generate_price_series(seed=3, length=60)
    volumes = generate_volume_series(seed=4, length=60, avg=300.0, std=50.0)

    for i in range(20, 35):
        volumes[i] = 0.0

    signals = []
    for t in [18, 22, 30, 40]:
        signals.append(
            (
                t,
                {
                    "price": prices[t],
                    "qty": 20.0,
                    "side": "buy",
                    "available_volume": volumes[t],
                },
            )
        )

    _assert_basic_results(
        signals, prices, slippage_bp=15.0, commission_pct=0.0003
    )


def test_large_spike_series():
    # High spike probability and magnitude
    prices = generate_price_series(
        seed=5, length=80, spike_prob=0.08, spike_scale=0.8, volatility=0.02
    )
    volumes = generate_volume_series(seed=6, length=80, avg=200.0, std=150.0)

    signals = [
        (
            5,
            {
                "price": prices[5],
                "qty": 5.0,
                "side": "buy",
                "available_volume": volumes[5],
            },
        ),
        (
            25,
            {
                "price": prices[25],
                "qty": 5.0,
                "side": "sell",
                "available_volume": volumes[25],
            },
        ),
        (
            55,
            {
                "price": prices[55],
                "qty": 10.0,
                "side": "buy",
                "available_volume": volumes[55],
            },
        ),
    ]

    _assert_basic_results(
        signals, prices, slippage_bp=25.0, commission_pct=0.0005
    )


def test_mean_reversion_stress():
    # Downtrend followed by rebound
    down = generate_price_series(
        seed=7,
        length=40,
        trend=-0.001,
        volatility=0.005,
    )
    up = generate_price_series(
        seed=8,
        length=40,
        trend=0.001,
        volatility=0.005,
    )
    prices = down + up
    volumes = generate_volume_series(
        seed=9,
        length=80,
        avg=400.0,
        std=100.0,
        )

    signals = [
        (
            10,
            {
                "price": prices[10],
                "qty": 2.0,
                "side": "buy",
                "available_volume": volumes[10],
            },
        ),
        (
            50,
            {
                "price": prices[50],
                "qty": 2.0,
                "side": "sell",
                "available_volume": volumes[50],
            },
        ),
    ]

    _assert_basic_results(
        signals, prices, slippage_bp=8.0, commission_pct=0.0002
    )
