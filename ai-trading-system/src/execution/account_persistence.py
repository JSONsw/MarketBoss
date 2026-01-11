"""Account state persistence module.

Saves and restores trading account state between sessions to track
performance over time instead of resetting to initial capital.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class AccountStateManager:
    """Manages persistent account state across trading sessions."""
    
    def __init__(self, state_file: Path = Path("data/account_state.json")):
        """Initialize account state manager.
        
        Args:
            state_file: Path to persistent state file
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def save_state(
        self,
        cash: float,
        portfolio_value: float,
        positions: Dict[str, Any],
        trades_count: int,
        session_count: int = 1
    ) -> None:
        """Save current account state to disk.
        
        Args:
            cash: Current cash balance
            portfolio_value: Total portfolio value (cash + positions)
            positions: Dict of open positions {symbol: {qty, avg_price}}
            trades_count: Total trades executed across all sessions
            session_count: Number of trading sessions completed
        """
        state = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "cash": cash,
            "portfolio_value": portfolio_value,
            "positions": positions,
            "trades_count": trades_count,
            "session_count": session_count,
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load account state from disk.
        
        Returns:
            Dict with account state, or None if no saved state exists
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Failed to load account state: {e}")
            return None
    
    def get_initial_cash(self, default: float = 100000.0) -> float:
        """Get initial cash for new session.
        
        If saved state exists, returns the last portfolio value.
        Otherwise returns the default initial capital.
        
        Args:
            default: Default initial cash if no saved state
        
        Returns:
            Cash amount to initialize trading engine with
        """
        state = self.load_state()
        
        if state is None:
            print(f"📊 Starting new account - Initial capital: ${default:,.2f}")
            return default
        
        portfolio_value = state.get('portfolio_value', default)
        cash = state.get('cash', default)
        session_count = state.get('session_count', 0)
        trades_count = state.get('trades_count', 0)
        last_updated = state.get('last_updated', 'unknown')
        
        print(f"📊 Resuming existing account:")
        print(f"   Session #{session_count + 1}")
        print(f"   Last updated: {last_updated}")
        print(f"   Portfolio value: ${portfolio_value:,.2f}")
        print(f"   Cash balance: ${cash:,.2f}")
        print(f"   Total trades (lifetime): {trades_count}")
        
        # Use portfolio value as starting point for new session
        # This includes both cash and open positions
        return portfolio_value
    
    def reset_state(self, initial_cash: float = 100000.0) -> None:
        """Reset account to fresh state with initial capital.
        
        Args:
            initial_cash: Starting capital amount
        """
        self.save_state(
            cash=initial_cash,
            portfolio_value=initial_cash,
            positions={},
            trades_count=0,
            session_count=0
        )
        print(f"✅ Account reset to ${initial_cash:,.2f}")
    
    def get_session_count(self) -> int:
        """Get number of completed trading sessions.
        
        Returns:
            Session count, or 0 if no saved state
        """
        state = self.load_state()
        return state.get('session_count', 0) if state else 0
    
    def get_lifetime_trades(self) -> int:
        """Get total number of trades across all sessions.
        
        Returns:
            Total trades count, or 0 if no saved state
        """
        state = self.load_state()
        return state.get('trades_count', 0) if state else 0
