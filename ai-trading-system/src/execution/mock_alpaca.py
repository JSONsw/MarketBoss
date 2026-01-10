"""Mock Alpaca API client for local paper trading simulation.

Simulates order execution, fills, and account equity tracking without
requiring real Alpaca API credentials or paid service.

Usage:
    from src.execution.mock_alpaca import MockAlpacaClient
    
    client = MockAlpacaClient(initial_cash=100000)
    order = client.submit_order(symbol="AAPL", qty=10, side="buy", type="market", time_in_force="day")
    filled_order = client.get_order(order.id)
"""

import json
import random
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4


class OrderStatus(Enum):
    """Order status enum."""
    PENDING = "pending_new"
    ACCEPTED = "accepted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass
class MockOrder:
    """Simulated order object."""
    id: str
    symbol: str
    qty: int
    filled_qty: int
    side: str
    type: str
    time_in_force: str
    status: str
    filled_avg_price: Optional[float] = None
    created_at: str = None
    filled_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class MockPosition:
    """Simulated position object."""
    symbol: str
    qty: float
    avg_fill_price: float
    side: str


@dataclass
class MockAccount:
    """Simulated account object."""
    id: str
    cash: float
    portfolio_value: float
    buying_power: float
    multiplier: float = 1.0
    account_number: str = None
    
    def __post_init__(self):
        if self.account_number is None:
            self.account_number = self.id


class MockAlpacaClient:
    """Mock Alpaca API client for local paper trading.
    
    Simulates:
    - Order submission and execution
    - Fill simulation with random delays
    - Account equity tracking
    - Position management
    - Trade logging
    """
    
    def __init__(self, initial_cash: float = 100000.0, fill_delay_sec: float = 2.0):
        """Initialize mock Alpaca client.
        
        Args:
            initial_cash: Starting cash balance
            fill_delay_sec: Simulated delay before order fills (seconds)
        """
        self.account_id = "mock_" + str(uuid4())[:8]
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.portfolio_value = initial_cash
        self.buying_power = initial_cash
        self.fill_delay_sec = fill_delay_sec
        self.orders = {}
        self.positions = {}
        self._order_fill_times = {}
        self.market_prices = {}  # Dict of {symbol: price} for accurate fills
        self.trades = []  # Log of all trades executed
        self.equity_snapshots = []  # Time-series of equity values
        self.multiplier = 1.0
        self.fill_delay_sec = fill_delay_sec
        
        self.orders: Dict[str, MockOrder] = {}
        self.positions: Dict[str, MockPosition] = {}
        self.trades: List[Dict[str, Any]] = []
        self.equity_history: List[Dict[str, Any]] = []
        
        # Mock market prices (symbol -> last_price)
        self.market_prices: Dict[str, float] = {
            "AAPL": 150.00,
            "MSFT": 380.00,
            "GOOGL": 140.00,
            "TSLA": 250.00,
            "SPY": 450.00,
            "QQQ": 380.00,
            "IWM": 200.00,
        }
        
        self._order_fill_times: Dict[str, float] = {}
        self._record_equity_snapshot()
    
    def set_market_prices(self, prices_dict: dict) -> None:
        """Set current market prices for accurate order fills.
        
        Args:
            prices_dict: Dict of {symbol: price} from market data
        """
        self.market_prices = prices_dict.copy()
    
    def _get_market_price(self, symbol: str) -> float:
        """Get current market price for symbol (with realistic noise).
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Current simulated market price
        """
        base_price = self.market_prices.get(symbol, 100.0)
        # Add small random walk (±0.5% volatility)
        noise = base_price * random.uniform(-0.005, 0.005)
        return max(1.0, base_price + noise)
    
    def _simulate_fill(self, order: MockOrder) -> None:
        """Simulate order fill after delay.
        
        Args:
            order: Order to fill
        """
        if order.id not in self._order_fill_times:
            self._order_fill_times[order.id] = time.time()
        
        # Check if fill delay has elapsed
        elapsed = time.time() - self._order_fill_times[order.id]
        if elapsed < self.fill_delay_sec:
            return  # Not ready to fill yet
        
        # Simulate fill with 95% success rate
        if random.random() > 0.95:
            order.status = OrderStatus.REJECTED.value
            order.filled_qty = 0
            order.filled_avg_price = None
            return
        
        # Fill the order at actual market price from market data (not regenerated random price)
        # This uses the price passed via set_market_prices() which comes from live market data
        market_price = self.market_prices.get(order.symbol, 100.0)
        
        # Add minimal realistic slippage (0-2 basis points) - not 50bps
        slippage_bps = random.uniform(0.00, 0.0002)  # Realistic market maker spread
        slippage = market_price * slippage_bps
        if order.side.lower() == "buy":
            fill_price = market_price + slippage  # Adverse: higher on buy
        else:  # sell
            fill_price = market_price - slippage  # Adverse: lower on sell
        
        order.filled_qty = order.qty
        order.filled_avg_price = round(fill_price, 2)
        order.status = OrderStatus.FILLED.value
        order.filled_at = datetime.now(timezone.utc).isoformat()
        
        # Update positions and cash
        self._update_position(order)
        self._record_trade(order)
        self._record_equity_snapshot()
    
    def _update_position(self, order: MockOrder) -> None:
        """Update position after order fill.
        
        Args:
            order: Filled order
        """
        symbol = order.symbol
        qty = order.filled_qty
        price = order.filled_avg_price
        side = order.side.lower()
        
        # Update cash
        cost = qty * price
        if side == "buy":
            self.cash -= cost
        else:  # sell
            self.cash += cost
        
        # Update position
        if symbol not in self.positions:
            if side == "buy":
                self.positions[symbol] = MockPosition(
                    symbol=symbol,
                    qty=qty,
                    avg_fill_price=price,
                    side="long"
                )
        else:
            pos = self.positions[symbol]
            if side == "buy":
                # Add to position
                total_cost = pos.qty * pos.avg_fill_price + qty * price
                pos.qty += qty
                pos.avg_fill_price = total_cost / pos.qty if pos.qty > 0 else price
            else:  # sell
                # Reduce position
                pos.qty -= qty
                if pos.qty <= 0:
                    del self.positions[symbol]
                else:
                    pos.avg_fill_price = pos.avg_fill_price  # Keep average
        
        # Update portfolio value
        self._update_portfolio_value()
    
    def _update_portfolio_value(self) -> None:
        """Update total portfolio value (cash + positions)."""
        position_value = sum(
            pos.qty * self._get_market_price(pos.symbol)
            for pos in self.positions.values()
        )
        self.portfolio_value = self.cash + position_value
        self.buying_power = self.portfolio_value
    
    def _record_trade(self, order: MockOrder) -> None:
        """Record executed trade.
        
        Args:
            order: Filled order
        """
        trade = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "order_id": order.id,
            "symbol": order.symbol,
            "side": order.side.upper(),
            "qty": order.filled_qty,
            "filled_price": order.filled_avg_price,
            "cost": order.filled_qty * order.filled_avg_price,
        }
        self.trades.append(trade)
    
    def _record_equity_snapshot(self) -> None:
        """Record current account equity snapshot."""
        self._update_portfolio_value()
        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cash": round(self.cash, 2),
            "portfolio_value": round(self.portfolio_value, 2),
            "buying_power": round(self.buying_power, 2),
            "equity_multiplier": self.multiplier,
        }
        self.equity_history.append(snapshot)
    
    def get_account(self) -> MockAccount:
        """Get current account status.
        
        Returns:
            MockAccount with current equity, cash, etc.
        """
        self._update_portfolio_value()
        return MockAccount(
            id=self.account_id,
            cash=self.cash,
            portfolio_value=self.portfolio_value,
            buying_power=self.buying_power,
            multiplier=self.multiplier,
            account_number=self.account_id
        )
    
    def submit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        type: str = "market",
        time_in_force: str = "day"
    ) -> MockOrder:
        """Submit an order.
        
        Args:
            symbol: Stock ticker
            qty: Order quantity
            side: "buy" or "sell"
            type: Order type (default: "market")
            time_in_force: Order time in force (default: "day")
        
        Returns:
            MockOrder with unique ID
        """
        order_id = str(uuid4())
        order = MockOrder(
            id=order_id,
            symbol=symbol.upper(),
            qty=qty,
            filled_qty=0,
            side=side.lower(),
            type=type.lower(),
            time_in_force=time_in_force.lower(),
            status=OrderStatus.PENDING.value
        )
        self.orders[order_id] = order
        return order
    
    def get_order(self, order_id: str) -> Optional[MockOrder]:
        """Get order by ID (simulates fill if delay elapsed).
        
        Args:
            order_id: Order ID to retrieve
        
        Returns:
            MockOrder (may be filled or still pending)
        """
        if order_id not in self.orders:
            return None
        
        order = self.orders[order_id]
        
        # Simulate fill if not yet filled
        if order.status == OrderStatus.PENDING.value:
            self._simulate_fill(order)
        
        return order
    
    def get_positions(self) -> List[MockPosition]:
        """Get all open positions.
        
        Returns:
            List of MockPosition objects
        """
        return list(self.positions.values())
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """Get all executed trades.
        
        Returns:
            List of trade records
        """
        return self.trades
    
    def get_equity_history(self) -> List[Dict[str, Any]]:
        """Get account equity history.
        
        Returns:
            List of equity snapshots with timestamps
        """
        return self.equity_history
    
    def close_position(self, symbol: str) -> Optional[MockOrder]:
        """Close a position by selling all shares.
        
        Args:
            symbol: Position symbol to close
        
        Returns:
            MockOrder for the closing sale, or None if no position
        """
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        order = self.submit_order(
            symbol=symbol,
            qty=int(pos.qty),
            side="sell"
        )
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if cancelled, False if not found or already filled
        """
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status == OrderStatus.FILLED.value:
            return False
        
        order.status = OrderStatus.CANCELED.value
        return True


def create_mock_client(initial_cash: float = 100000.0) -> MockAlpacaClient:
    """Factory function to create mock Alpaca client.
    
    Args:
        initial_cash: Starting capital
    
    Returns:
        MockAlpacaClient ready for use
    """
    return MockAlpacaClient(initial_cash=initial_cash)
