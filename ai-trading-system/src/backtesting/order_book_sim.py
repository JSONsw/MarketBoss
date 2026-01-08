from typing import List, Dict, Optional, Tuple


def simulate_limit_order_fill(
    order_qty: float,
    side: str,
    limit_price: Optional[float],
    book_levels: List[Dict[str, float]],
) -> Dict[str, object]:
    """Simulate filling a limit (or market if `limit_price` is None)
    order against an order book.

    Args:
        order_qty: desired quantity to execute (positive float).
        side: 'buy' or 'sell'.
        limit_price: limit price; if None treated as market order.
        book_levels: list of levels, each a dict with keys 'price'
            and 'size'. For buys, `book_levels` should be the ask
            side (ascending prices). For sells, `book_levels` should
            be the bid side (descending prices).

    Returns:
        A dict with keys: 'executed_qty', 'avg_price', 'fills', and
        'remaining_qty'.
    """
    if order_qty <= 0:
        return {
            "executed_qty": 0.0,
            "avg_price": None,
            "fills": [],
            "remaining_qty": 0.0,
        }

    remaining = float(order_qty)
    executed_qty = 0.0
    executed_cost = 0.0
    fills: List[Tuple[float, float]] = []

    is_buy = side.lower() == "buy"

    for lvl in book_levels:
        lvl_price = float(lvl["price"])
        lvl_size = float(lvl["size"])

        # Limit order: for buys we need lvl_price <= limit_price
        if limit_price is not None:
            if is_buy and lvl_price > float(limit_price):
                break
            if (not is_buy) and lvl_price < float(limit_price):
                break

        if lvl_size <= 0:
            continue

        take = min(lvl_size, remaining)
        if take <= 0:
            break

        fills.append((lvl_price, take))
        executed_qty += take
        executed_cost += take * lvl_price
        remaining -= take

        if remaining <= 1e-12:
            remaining = 0.0
            break

    avg_price: Optional[float]
    if executed_qty > 0:
        avg_price = executed_cost / executed_qty
    else:
        avg_price = None

    return {
        "executed_qty": executed_qty,
        "avg_price": avg_price,
        "fills": fills,
        "remaining_qty": remaining,
    }


def generate_synthetic_book(
    mid_price: float,
    depth: int = 5,
    tick: float = 0.01,
    size: float = 100.0,
) -> Dict[str, List[Dict[str, float]]]:
    """Create a simple symmetric book with `depth` levels on each
    side.

    Returns a dict with keys 'bids' (desc) and 'asks' (asc).
    """
    bids: List[Dict[str, float]] = []
    asks: List[Dict[str, float]] = []
    for i in range(1, depth + 1):
        bids.append({"price": round(mid_price - i * tick, 8), "size": size})
        asks.append({"price": round(mid_price + i * tick, 8), "size": size})

    # bids sorted desc, asks sorted asc
    bids = sorted(bids, key=lambda x: x["price"], reverse=True)
    asks = sorted(asks, key=lambda x: x["price"])
    return {"bids": bids, "asks": asks}
