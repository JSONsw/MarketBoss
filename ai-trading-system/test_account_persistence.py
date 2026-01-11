"""Test account persistence across sessions"""
import json
import os
from src.execution.account_persistence import AccountStateManager

def test_account_persistence():
    """Test that account state saves and loads correctly"""
    
    # Clean state
    state_file = "data/account_state.json"
    if os.path.exists(state_file):
        os.remove(state_file)
        print("✓ Cleaned existing state")
    
    # Create manager
    mgr = AccountStateManager(state_file)
    
    # Check initial state (no file)
    initial = mgr.get_initial_cash(default=100000.0)
    print(f"✓ Initial cash (no saved state): ${initial:,.2f}")
    assert initial == 100000.0, "Should return default when no state exists"
    
    # Simulate session 1: Start with $100k, end with $105k
    print("\n📊 Session 1: Trading...")
    mgr.save_state(
        cash=102000.0,
        portfolio_value=105000.0,
        positions={"SPY": {"qty": 10, "avg_price": 300.0}},
        trades_count=5
    )
    print("✓ Session 1 saved: $105,000 portfolio value")
    
    # Verify file created
    assert os.path.exists(state_file), "State file should exist"
    with open(state_file) as f:
        data = json.load(f)
        print(f"   - Cash: ${data['cash']:,.2f}")
        print(f"   - Portfolio Value: ${data['portfolio_value']:,.2f}")
        print(f"   - Positions: {data['positions']}")
        print(f"   - Session: {data['session_count']}")
        print(f"   - Trades: {data['trades_count']}")
    
    # Session 2: Load previous state
    print("\n📊 Session 2: Resuming...")
    mgr2 = AccountStateManager(state_file)
    starting_capital = mgr2.get_initial_cash(default=100000.0)
    print(f"✓ Starting capital (loaded): ${starting_capital:,.2f}")
    assert starting_capital == 105000.0, "Should load saved portfolio value"
    
    session_count = mgr2.get_session_count()
    lifetime_trades = mgr2.get_lifetime_trades()
    print(f"   - Session count: {session_count}")
    print(f"   - Lifetime trades: {lifetime_trades}")
    
    # End session 2 with $110k
    mgr2.save_state(
        cash=110000.0,
        portfolio_value=110000.0,
        positions={},
        trades_count=8
    )
    print("✓ Session 2 saved: $110,000 portfolio value")
    
    # Session 3: Verify accumulation
    print("\n📊 Session 3: Resuming...")
    mgr3 = AccountStateManager(state_file)
    starting_capital = mgr3.get_initial_cash(default=100000.0)
    print(f"✓ Starting capital (loaded): ${starting_capital:,.2f}")
    assert starting_capital == 110000.0, "Should accumulate gains"
    
    session_count = mgr3.get_session_count()
    lifetime_trades = mgr3.get_lifetime_trades()
    print(f"   - Session count: {session_count}")
    print(f"   - Lifetime trades: {lifetime_trades}")
    
    print("\n✅ All persistence tests passed!")
    print("\n📌 Key Points:")
    print("   - Session 1: $100k → $105k (+$5k)")
    print("   - Session 2: $105k → $110k (+$5k)")
    print("   - Session 3 would start: $110k")
    print("   - Total gain over 2 sessions: +$10k (+10%)")
    print("\n💡 Account state persists across restarts!")

if __name__ == "__main__":
    test_account_persistence()
