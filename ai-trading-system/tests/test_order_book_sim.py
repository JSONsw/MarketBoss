from src.backtesting.order_book_sim import (
    simulate_limit_order_fill,
    generate_synthetic_book,
)


def test_full_fill_buy():
    book = generate_synthetic_book(mid_price=100.0, depth=3, tick=0.5, size=50.0)
    asks = book["asks"]
    # place a buy that is fully covered within the asks
    res = simulate_limit_order_fill(
        order_qty=80.0, side="buy", limit_price=101.5, book_levels=asks
    )
    assert res["executed_qty"] == 80.0
    assert res["remaining_qty"] == 0.0
    assert res["avg_price"] is not None


def test_partial_fill_buy():
    book = generate_synthetic_book(mid_price=50.0, depth=2, tick=1.0, size=10.0)
    asks = book["asks"]
    # try to buy more than available within limit
    res = simulate_limit_order_fill(
        order_qty=50.0, side="buy", limit_price=52.0, book_levels=asks
    )
    assert res["executed_qty"] < 50.0
    assert res["remaining_qty"] > 0.0


def test_sell_fill_and_avg():
    book = generate_synthetic_book(mid_price=200.0, depth=4, tick=0.25, size=20.0)
    bids = book["bids"]
    res = simulate_limit_order_fill(
        order_qty=30.0, side="sell", limit_price=199.0, book_levels=bids
    )
    # should execute at levels >= 199.0 on bids
    assert res["executed_qty"] > 0
    assert res["avg_price"] is not None


def test_market_order_consumes_book():
    book = generate_synthetic_book(mid_price=10.0, depth=3, tick=0.1, size=5.0)
    asks = book["asks"]
    # market buy should consume asks irrespective of limit
    res = simulate_limit_order_fill(
        order_qty=12.0, side="buy", limit_price=None, book_levels=asks
    )
    assert res["executed_qty"] <= 15.0
    assert res["avg_price"] is not None
