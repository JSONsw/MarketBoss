from src.backtesting.slippage import apply_volume_aware_slippage


def test_volume_aware_partial_fill():
    price = 100.0
    qty = 10.0
    available = 4.0

    filled_qty, exec_price, eff_slip = apply_volume_aware_slippage(
        price,
        qty,
        "buy",
        slippage_bp=10.0,
        available_volume=available,
        impact_coeff=0.5,
    )

    assert filled_qty == available
    assert exec_price > price
    assert eff_slip >= 10.0


def test_volume_aware_full_fill():
    price = 50.0
    qty = 2.0
    available = 5.0

    filled_qty, exec_price, eff_slip = apply_volume_aware_slippage(
        price,
        qty,
        "sell",
        slippage_bp=5.0,
        available_volume=available,
        impact_coeff=0.5,
    )

    assert filled_qty == qty
    assert exec_price < price
    assert eff_slip >= 5.0
