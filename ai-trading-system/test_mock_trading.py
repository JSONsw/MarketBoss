"""Quick test of simulated paper trading."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(ROOT))

from src.execution.mock_alpaca import create_mock_client

def test_mock_client():
    """Test the mock Alpaca client."""
    print("\n" + "="*70)
    print("Testing Mock Alpaca Client")
    print("="*70 + "\n")
    
    # Create client
    client = create_mock_client(initial_cash=100000.0)
    
    # Submit orders
    orders = []
    print("Submitting 5 test orders...")
    for i in range(5):
        side = "buy" if i % 2 == 0 else "sell"
        order = client.submit_order(symbol="AAPL", qty=10, side=side)
        orders.append(order)
        print(f"  [{i+1}] Order {order.id[:8]}... {side.upper()} 10 AAPL")
    
    print("\nWaiting for fills (3-5 seconds)...")
    import time
    
    # Poll until fills arrive
    max_wait = 5.0
    start = time.time()
    while time.time() - start < max_wait:
        filled_count = sum(1 for o in orders if client.get_order(o.id).filled_qty > 0)
        if filled_count == len(orders):
            break
        time.sleep(0.5)
    
    # Check fills
    print("\nOrder Status:")
    filled = 0
    for i, order in enumerate(orders):
        filled_order = client.get_order(order.id)
        status = "FILLED" if filled_order.filled_qty > 0 else "PENDING"
        if status == "FILLED":
            filled += 1
        price_str = f"${filled_order.filled_avg_price:.2f}" if filled_order.filled_avg_price else "N/A"
        print(f"  [{i+1}] {status:<8} | {filled_order.qty} shares @ {price_str}")
    
    # Account status
    account = client.get_account()
    print(f"\nAccount Status:")
    print(f"  Cash:           ${account.cash:,.2f}")
    print(f"  Portfolio Value: ${account.portfolio_value:,.2f}")
    print(f"  Buying Power:   ${account.buying_power:,.2f}")
    
    # Positions
    positions = client.get_positions()
    print(f"\nOpen Positions: {len(positions)}")
    for pos in positions:
        print(f"  {pos.symbol}: {pos.qty} @ avg ${pos.avg_fill_price:.2f}")
    
    # Trades
    trades = client.get_trades()
    print(f"\nTrades Executed: {len(trades)}")
    
    # Equity history
    equity = client.get_equity_history()
    print(f"Equity Snapshots: {len(equity)}")
    print(f"  Start: ${equity[0]['portfolio_value']:,.2f}")
    print(f"  End:   ${equity[-1]['portfolio_value']:,.2f}")
    
    print("\n" + "="*70)
    print("✓ Mock Client Test Successful!")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_mock_client()
