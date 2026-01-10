"""Execute signals live on Alpaca paper trading account or simulated environment.

Paper trading executor with order execution, equity tracking, and trade logging.

Can run in two modes:
1. SIMULATED (default, no credentials needed): Local mock Alpaca broker
2. REAL: Live Alpaca paper trading account (requires API credentials)

Usage:
    # Simulated mode (no API credentials needed)
    python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 50
    
    # Real Alpaca paper trading (requires APCA_API_KEY_ID and APCA_API_SECRET_KEY)
    python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 50 --real

Requirements (Real Mode):
    - APCA_API_BASE_URL env var set (default: https://paper-api.alpaca.markets)
    - APCA_API_KEY_ID and APCA_API_SECRET_KEY env vars set
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd

# Try alpaca_trade_api import (for real trading)
try:
    from alpaca_trade_api import REST
    HAS_ALPACA = True
except ImportError:
    HAS_ALPACA = False

# Project imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.monitoring.structured_logger import get_logger
from src.execution.mock_alpaca import MockAlpacaClient, create_mock_client

logger = get_logger("paper_trading")


class PaperTradingExecutor:
    """Execute signals on paper trading account (real or simulated)."""
    
    def __init__(self, use_real: bool = False):
        """Initialize trading client (real or mock).
        
        Args:
            use_real: If True, use real Alpaca API. If False, use mock.
        """
        self.use_real = use_real
        self.client = None
        self.account = None
        self.trades_executed = []
        self.equity_snapshots = []
        
        if use_real:
            if not HAS_ALPACA:
                raise RuntimeError(
                    "alpaca-trade-api not installed. Run: pip install alpaca-trade-api"
                )
            # Real Alpaca API
            self.client = REST()
            self.account = self.client.get_account()
            logger.info("Alpaca Paper Trading (REAL) initialized", extra={
                "account_id": getattr(self.account, "account_number", "unknown"),
                "buying_power": float(self.account.buying_power)
            })
        else:
            # Mock Alpaca client (no credentials needed)
            self.client = create_mock_client(initial_cash=100000.0)
            self.account = self.client.get_account()
            logger.info("Alpaca Paper Trading (SIMULATED) initialized", extra={
                "account_id": self.account.account_number,
                "buying_power": self.account.buying_power,
                "mode": "SIMULATED"
            })
        
        self._record_equity_snapshot()
    
    def _record_equity_snapshot(self) -> Dict[str, Any]:
        """Record current account equity snapshot."""
        if self.use_real:
            self.account = self.client.get_account()
            snapshot = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cash": float(self.account.cash),
                "portfolio_value": float(self.account.portfolio_value),
                "buying_power": float(self.account.buying_power),
                "equity_multiplier": float(self.account.multiplier if hasattr(self.account, "multiplier") else 1.0),
            }
        else:
            # Mock client
            self.account = self.client.get_account()
            snapshot = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cash": round(self.account.cash, 2),
                "portfolio_value": round(self.account.portfolio_value, 2),
                "buying_power": round(self.account.buying_power, 2),
                "equity_multiplier": self.account.multiplier,
            }
        self.equity_snapshots.append(snapshot)
        return snapshot
    
    def execute_signal(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a single signal (place order).
        
        Args:
            signal: Dict with keys like action, symbol, qty, price
        
        Returns:
            Executed trade record or None if failed
        """
        try:
            action = signal.get("action", "").upper()
            symbol = signal.get("symbol", "AAPL")
            qty = signal.get("qty", 1)
            
            if qty <= 0:
                logger.warning("Invalid qty in signal", extra={"signal": signal})
                return None
            
            if self.use_real:
                # Real Alpaca API
                side = "buy" if action == "BUY" else "sell"
                order = self.client.submit_order(
                    symbol=symbol,
                    qty=int(qty),
                    side=side,
                    type="market",
                    time_in_force="day"
                )
                order_id = order.id
                
                # Wait for fill with timeout
                filled_price = None
                for attempt in range(30):  # ~5 min with 10s waits
                    try:
                        order = self.client.get_order(order_id)
                        if order.filled_qty and order.filled_avg_price:
                            filled_price = float(order.filled_avg_price)
                            break
                    except:
                        pass
                    time.sleep(10)
            else:
                # Mock client (instant simulation)
                side = "buy" if action == "BUY" else "sell"
                order = self.client.submit_order(
                    symbol=symbol,
                    qty=int(qty),
                    side=side,
                    type="market",
                    time_in_force="day"
                )
                order_id = order.id
                
                # Get fill (simulated with ~2 sec delay built into mock)
                filled_price = None
                for attempt in range(5):  # Quick poll for mock
                    order = self.client.get_order(order_id)
                    if order.filled_qty and order.filled_avg_price:
                        filled_price = order.filled_avg_price
                        break
                    time.sleep(0.5)
            
            logger.info("Order submitted", extra={
                "order_id": order_id,
                "symbol": symbol,
                "side": action,
                "qty": qty,
                "status": order.status if hasattr(order, "status") else "pending"
            })
            
            if not filled_price:
                logger.warning("Order not filled within timeout", extra={
                    "order_id": order_id,
                    "symbol": symbol
                })
                return None
            
            trade = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "signal_timestamp": signal.get("timestamp", ""),
                "order_id": order_id,
                "symbol": symbol,
                "side": action,
                "qty": int(qty),
                "filled_price": filled_price,
                "status": getattr(order, "status", "unknown"),
            }
            self.trades_executed.append(trade)
            logger.info("Trade executed", extra=trade)
            
            # Snap equity after trade
            self._record_equity_snapshot()
            
            return trade
        
        except Exception as e:
            logger.error("Failed to execute signal", extra={
                "error": str(e),
                "signal": signal
            })
            return None
    
    def get_equity_curve(self) -> pd.DataFrame:
        """Return equity curve as DataFrame."""
        return pd.DataFrame(self.equity_snapshots)
    
    def save_trades(self, output_path: Path):
        """Save executed trades to JSONL."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for trade in self.trades_executed:
                f.write(json.dumps(trade) + "\n")
        logger.info("Trades saved", extra={"path": str(output_path), "count": len(self.trades_executed)})
    
    def save_equity(self, output_path: Path):
        """Save equity snapshots to JSONL."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for snap in self.equity_snapshots:
                f.write(json.dumps(snap) + "\n")
        logger.info("Equity snapshots saved", extra={"path": str(output_path), "count": len(self.equity_snapshots)})


def load_signals(path: Path) -> List[Dict[str, Any]]:
    """Load signals from JSONL file."""
    signals = []
    if not path.exists():
        logger.error("Signals file not found", extra={"path": str(path)})
        return signals
    
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                signals.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    logger.info("Signals loaded", extra={"path": str(path), "count": len(signals)})
    return signals


def main():
    parser = argparse.ArgumentParser(description="Execute signals on paper trading account")
    parser.add_argument("--signals", type=Path, default=Path("data/signals.jsonl"),
                        help="Path to signals JSONL file")
    parser.add_argument("--max-trades", type=int, default=50,
                        help="Max trades to execute")
    parser.add_argument("--trades-output", type=Path, default=Path("data/paper_trading_trades.jsonl"),
                        help="Output file for executed trades")
    parser.add_argument("--equity-output", type=Path, default=Path("data/paper_trading_equity.jsonl"),
                        help="Output file for equity snapshots")
    parser.add_argument("--real", action="store_true",
                        help="Use real Alpaca API (default: simulated local environment)")
    parser.add_argument("--initial-cash", type=float, default=100000.0,
                        help="Initial cash for simulated environment")
    args = parser.parse_args()
    
    try:
        mode = "REAL Alpaca" if args.real else "SIMULATED"
        print(f"\n{'='*70}")
        print(f"Paper Trading Mode: {mode}")
        print(f"{'='*70}")
        
        executor = PaperTradingExecutor(use_real=args.real)
        
        signals = load_signals(args.signals)
        if not signals:
            logger.error("No signals to execute")
            return 1
        
        print(f"\nSignals loaded: {len(signals)}")
        print(f"Max trades to execute: {args.max_trades}\n")
        
        # Execute signals (up to max_trades)
        executed = 0
        for i, signal in enumerate(signals[:args.max_trades], 1):
            print(f"[{i}/{args.max_trades}] Executing signal: {signal.get('symbol', 'UNKNOWN')} {signal.get('action', 'UNKNOWN')}")
            if executor.execute_signal(signal):
                executed += 1
            time.sleep(0.5)  # Rate limit
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"Paper Trading Complete!")
        print(f"{'='*70}")
        print(f"Mode: {mode}")
        print(f"Signals processed: {min(len(signals), args.max_trades)}")
        print(f"Trades executed: {executed}")
        
        final_account = executor.account
        print(f"Final portfolio value: ${final_account.portfolio_value:,.2f}")
        print(f"Final cash: ${final_account.cash:,.2f}")
        print(f"Buying power: ${final_account.buying_power:,.2f}")
        print(f"{'='*70}\n")
        
        logger.info("Paper trading complete", extra={
            "mode": mode,
            "signals_processed": min(len(signals), args.max_trades),
            "trades_executed": executed
        })
        
        # Save outputs
        executor.save_trades(args.trades_output)
        executor.save_equity(args.equity_output)
        
        print(f"✓ Trades saved to: {args.trades_output}")
        print(f"✓ Equity log saved to: {args.equity_output}")
        
        return 0
    
    except Exception as e:
        logger.error("Paper trading failed", extra={"error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
