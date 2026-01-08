from src.backtesting.slippage import (
    apply_slippage,
    compute_transaction_cost,
    apply_trade,
)


def test_apply_slippage_buy():
    p = 100.0
    adj = apply_slippage(p, "buy", 10)  # 10 bp = 0.1%
    assert abs(adj - 100.1) < 1e-6


def test_apply_slippage_sell():
    p = 100.0
    adj = apply_slippage(p, "sell", 20)  # 20 bp = 0.2%
    assert abs(adj - 99.8) < 1e-6


def test_compute_transaction_cost():
    notional = 10000
    cost = compute_transaction_cost(
        notional,
        commission_pct=0.0005,
        fixed_fee=1.0,
    )
    expected = notional * 0.0005 + 1.0
    assert abs(cost - expected) < 1e-8


def test_apply_trade():
    notional, cost = apply_trade(
        50.0,
        10,
        "buy",
        slippage_bp=5,
        commission_pct=0.0001,
        fixed_fee=0.5,
    )

    # Executed price should be slightly higher than 50.0
    assert notional > 50.0 * 10 - 1e-9
    assert cost > 0
