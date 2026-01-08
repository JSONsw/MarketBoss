from src.backtesting.synthetic_market import (
    generate_price_series,
    generate_volume_series,
    generate_spiky_market,
)


def test_deterministic_price_and_volume():
    p1 = generate_price_series(42, length=50)
    p2 = generate_price_series(42, length=50)
    assert p1 == p2

    v1 = generate_volume_series(7, length=50)
    v2 = generate_volume_series(7, length=50)
    assert v1 == v2


def test_spiky_market_returns_both():
    prices, volumes = generate_spiky_market(123, length=30)
    assert len(prices) == 30
    assert len(volumes) == 30
