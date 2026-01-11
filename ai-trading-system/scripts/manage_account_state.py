"""Account state management utility.

Allows viewing, resetting, or modifying persistent account state.

Usage:
    # View current account state
    python scripts/manage_account_state.py --view
    
    # Reset account to initial capital
    python scripts/manage_account_state.py --reset
    
    # Reset with custom amount
    python scripts/manage_account_state.py --reset --initial-cash 50000
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.execution.account_persistence import AccountStateManager


def view_state(state_file: Path):
    """Display current account state."""
    mgr = AccountStateManager(state_file)
    state = mgr.load_state()
    
    if state is None:
        print("❌ No saved account state found")
        print(f"   File: {state_file}")
        print("\n💡 State will be created automatically when trading starts")
        return
    
    print("\n" + "="*70)
    print("ACCOUNT STATE")
    print("="*70)
    print(f"Last Updated:     {state.get('last_updated', 'unknown')}")
    print(f"Session Count:    {state.get('session_count', 0)}")
    print(f"Lifetime Trades:  {state.get('trades_count', 0)}")
    print(f"\nPortfolio Value:  ${state.get('portfolio_value', 0):,.2f}")
    print(f"Cash Balance:     ${state.get('cash', 0):,.2f}")
    
    positions = state.get('positions', {})
    if positions:
        print(f"\nOpen Positions:")
        for symbol, pos_data in positions.items():
            qty = pos_data.get('qty', 0)
            avg_price = pos_data.get('avg_price', 0)
            print(f"  {symbol}: {qty} shares @ ${avg_price:.2f}")
    else:
        print(f"\nOpen Positions:   None (FLAT)")
    
    print("="*70 + "\n")


def reset_state(state_file: Path, initial_cash: float):
    """Reset account state to initial capital."""
    mgr = AccountStateManager(state_file)
    
    # Check if state exists
    existing_state = mgr.load_state()
    if existing_state:
        print("\n⚠️  WARNING: This will reset your account state!")
        print(f"   Current portfolio value: ${existing_state.get('portfolio_value', 0):,.2f}")
        print(f"   Session count: {existing_state.get('session_count', 0)}")
        print(f"   Lifetime trades: {existing_state.get('trades_count', 0)}")
        
        confirm = input(f"\n   Reset to ${initial_cash:,.2f}? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Reset cancelled")
            return
    
    mgr.reset_state(initial_cash)
    print(f"\n✅ Account reset to ${initial_cash:,.2f}")
    print(f"   File: {state_file}\n")


def main():
    parser = argparse.ArgumentParser(description="Manage persistent account state")
    parser.add_argument(
        "--view",
        action="store_true",
        help="View current account state"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset account state to initial capital"
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=100000.0,
        help="Initial cash for reset (default: 100000)"
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("data/account_state.json"),
        help="Path to account state file"
    )
    
    args = parser.parse_args()
    
    if args.view:
        view_state(args.state_file)
    elif args.reset:
        reset_state(args.state_file, args.initial_cash)
    else:
        parser.print_help()
        print("\n💡 Use --view to see current state or --reset to reset account")


if __name__ == "__main__":
    main()
