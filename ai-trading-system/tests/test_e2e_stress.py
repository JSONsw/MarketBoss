from src.backtesting import synthetic_market
from src.backtesting.backtester import run_backtest_ticks


def test_e2e_stress_zero_volume_and_spikes():
    """Test market simulation with zero-volume pockets and price spikes."""

    # Generate deterministic market data
    prices = synthetic_market.generate_price_series(
        seed=2026, length=100, spike_prob=0.05, spike_scale=0.3
    )
    volumes = synthetic_market.generate_volume_series(
        seed=2027, length=100, avg=200.0, std=300.0
    )

    # Introduce zero-volume pockets intentionally
    for i in range(10, 20):
        volumes[i] = 0.0

    # Create signals across ticks (some orders larger than available volume)
    signals = []
    for t in range(0, 100, 10):
        signals.append(
            (
                t,
                {
                    "price": prices[t],
                    "qty": 50.0,
                    "side": "buy",
                    "available_volume": volumes[t],
                },
            )
        )

    # Ensure the simulator runs without throwing and returns results
    res = run_backtest_ticks(
        signals,
        prices,
        slippage_bp=10.0,
        commission_pct=0.0002,
        fixed_fee=0.25,
    )

    assert isinstance(res, list)
    assert len(res) == len(signals)
