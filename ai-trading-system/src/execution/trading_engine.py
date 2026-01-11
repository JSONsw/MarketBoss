"""Live Trading Engine - runs inline with market data and executes trades algorithmically.

Processes a stream of market data + signals and:
1. Evaluates signals against current market conditions
2. Executes trades automatically
3. Updates equity in real-time (mark-to-market)
4. Streams updates to JSONL for dashboard consumption
5. All updates happen tick-by-tick as data arrives

Usage:
    engine = LiveTradingEngine(initial_cash=100000)
    
    # Feed market data and signals
    for market_tick in market_data_stream:
        for signal in signals_at_time:
            engine.process_signal(signal, market_tick)
        engine.update_market_prices(market_tick)  # MTM update

Or use the runner:
    python scripts/run_live_trading.py --market-data data/market_data.jsonl --signals data/signals.jsonl
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict

from src.execution.mock_alpaca import MockAlpacaClient
from src.execution.account_persistence import AccountStateManager
from src.monitoring.structured_logger import get_logger

try:
    from src.execution.strategy_config import StrategyConfig
except ImportError:
    # Strategy config is optional for backward compatibility
    StrategyConfig = None

logger = get_logger("trading_engine")


@dataclass
class MarketTick:
    """Single market data point."""
    timestamp: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class LiveTradingEngine:
    """Live trading engine - processes market data + signals in real-time.
    
    Features:
    - Signal confidence filtering (min_confidence threshold)
    - Slippage buffer - only trades with minimum expected edge (min_profit_bp)
    - Dynamic position sizing - risk-based shares (risk_percent)
    - Trade frequency limits - prevent over-trading
    
    Key differences from batch paper trading:
    1. Processes data tick-by-tick as it arrives
    2. Updates equity on EVERY price change (MTM), not just on trades
    3. Executes trades algorithmically based on signals
    4. Streams live updates to dashboard
    5. Single continuous process
    """
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        output_dir: Path = Path("data"),
        update_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        min_confidence: float = 0.6,
        min_profit_bp: float = 3.0,
        risk_percent: float = 1.0,
        strategy: Optional[Any] = None  # StrategyConfig or None (using Any for type compatibility)
    ):
        """Initialize trading engine with profit optimization.
        
        Args:
            initial_cash: Starting capital
            output_dir: Directory to write JSONL updates
            update_callback: Optional callback for each update (for streaming)
            min_confidence: Minimum signal confidence threshold (0-1). Default 0.6 = 60%
            min_profit_bp: Minimum expected profit in basis points. Default 3bp
            risk_percent: Risk per trade as % of portfolio. Default 1.0%
            strategy: Optional StrategyConfig object. If provided, overrides individual params.
        """
        self.initial_cash = initial_cash
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.update_callback = update_callback
        
        # Strategy configuration (can override individual parameters)
        self.strategy = strategy
        
        # Profit optimization parameters (use strategy values if provided, otherwise use args)
        if strategy:
            self.min_confidence = getattr(strategy, 'min_confidence', min_confidence)
            self.min_profit_bp = getattr(strategy, 'min_profit_bp', min_profit_bp)
            self.risk_percent = getattr(strategy, 'risk_percent', risk_percent)
            self.min_cooldown_seconds = getattr(strategy, 'min_cooldown_seconds', 300.0)
        else:
            self.min_confidence = min_confidence
            self.min_profit_bp = min_profit_bp
            self.risk_percent = risk_percent
            self.min_cooldown_seconds = 300.0  # Default 5 minutes
        
        # Profit optimization parameters (use strategy values if provided, otherwise use args)
        if strategy:
            self.min_confidence = strategy.min_confidence
            self.min_profit_bp = strategy.min_profit_bp
            self.risk_percent = strategy.risk_percent
            self.min_cooldown_seconds = strategy.min_cooldown_seconds
        else:
            self.min_confidence = min_confidence
            self.min_profit_bp = min_profit_bp
            self.risk_percent = risk_percent
            self.min_cooldown_seconds = 300.0  # Default 5 minutes
        
        # Account persistence - load saved state first
        self.account_state_manager = AccountStateManager(output_dir / "account_state.json")
        saved_state = self.account_state_manager.load_state()
        
        # Use saved state if available, otherwise use initial_cash
        if saved_state:
            actual_cash = saved_state.get('portfolio_value', initial_cash)
            logger.info(
                "Loaded persisted account state",
                extra={
                    "cash": actual_cash,
                    "session_count": saved_state.get('session_count', 0),
                    "lifetime_trades": saved_state.get('trades_count', 0)
                }
            )
        else:
            actual_cash = initial_cash
            logger.info("No saved state found - starting fresh", extra={"initial_cash": initial_cash})
        
        self.session_start_trades = self.account_state_manager.get_lifetime_trades()
        
        # Trading state - use persisted cash
        self.client = MockAlpacaClient(initial_cash=actual_cash, fill_delay_sec=0.1)
        self.account = self.client.get_account()
        
        # Output files
        self.equity_log = self.output_dir / "live_trading_equity.jsonl"
        self.trades_log = self.output_dir / "live_trading_trades.jsonl"
        self.updates_log = self.output_dir / "live_trading_updates.jsonl"
        
        # State
        self.current_prices: Dict[str, float] = {}
        self.last_update_time = 0.0
        self.update_count = 0
        self.trades_count = 0
        self.last_trade_time = {}  # Track last trade time per symbol
        self.position_state: Dict[str, str] = {}  # Track position state per symbol: "FLAT", "LONG", "SHORT"
        
        # Record initial state
        self._record_equity_update("INIT")
        
        logger.info("Live Trading Engine initialized", extra={
            "initial_cash": initial_cash,
            "output_dir": str(self.output_dir)
        })
    
    def process_signal(self, signal: Dict[str, Any], current_price: float) -> bool:
        """Process a single trade signal with profit optimization filters.
        
        Filters applied:
        1. Signal confidence threshold (min_confidence)
        2. Minimum profit edge threshold (min_profit_bp)
        3. Trade frequency limits (prevent over-trading)
        4. Dynamic position sizing based on portfolio risk
        
        Args:
            signal: Signal dict with action/side, symbol, qty, confidence, etc.
            current_price: Current market price for the symbol
        
        Returns:
            True if trade executed, False otherwise
        """
        try:
            # Normalize action (could be "action" or "side" field)
            action = signal.get("action", signal.get("side", "")).upper()
            symbol = signal.get("symbol", "SPY")
            base_qty = signal.get("qty", 10)
            
            if base_qty <= 0 or action not in ["BUY", "SELL"]:
                return False
            
            # CRITICAL: Position-aware filtering - prevent churning
            # Get current position state from broker
            positions = self.client.get_positions()
            current_position = next((p for p in positions if p.symbol == symbol), None)
            
            # Determine current state: FLAT, LONG, or SHORT
            if current_position and current_position.qty > 0:
                current_state = "LONG"
            elif current_position and current_position.qty < 0:
                current_state = "SHORT"
            else:
                current_state = "FLAT"
            
            # Cache the state
            self.position_state[symbol] = current_state
            
            # FILTER 0: Position State Machine - only trade on position transitions
            # LONG state: ignore BUY signals (already long), only accept SELL to exit
            # SHORT state: ignore SELL signals (already short), only accept BUY to exit
            # FLAT state: accept both BUY (enter long) and SELL (enter short)
            
            if current_state == "LONG" and action == "BUY":
                logger.debug("Signal filtered - already LONG, ignoring BUY signal", extra={
                    "symbol": symbol,
                    "current_state": current_state,
                    "signal_action": action
                })
                return False
            
            if current_state == "SHORT" and action == "SELL":
                logger.debug("Signal filtered - already SHORT, ignoring SELL signal", extra={
                    "symbol": symbol,
                    "current_state": current_state,
                    "signal_action": action
                })
                return False
            
            # FILTER 1: Signal Confidence Check (optional field, defaults to 0.5)
            confidence = signal.get("confidence", 0.50)
            # Only skip if confidence is explicitly provided AND below threshold
            if "confidence" in signal and confidence < self.min_confidence:
                logger.debug("Signal filtered - low confidence", extra={
                    "symbol": symbol,
                    "confidence": confidence,
                    "min_required": self.min_confidence
                })
                return False
            
            # FILTER 2: Minimum Profit Edge Check (optional field, defaults to 0 = accept all)
            expected_profit_pct = signal.get("expected_profit", 0.0) or 0.0
            expected_profit_bp = expected_profit_pct * 10000
            # Only skip if explicitly provided AND below threshold
            if "expected_profit" in signal and expected_profit_bp < self.min_profit_bp:
                logger.debug("Signal filtered - insufficient profit edge", extra={
                    "symbol": symbol,
                    "expected_profit_bp": expected_profit_bp,
                    "min_required_bp": self.min_profit_bp
                })
                return False
            
            # FILTER 3: Trade Frequency Limit (prevent over-trading same symbol)
            current_time = time.time()
            min_time_between_trades = self.min_cooldown_seconds  # Use strategy cooldown or default
            if symbol in self.last_trade_time:
                time_since_last = current_time - self.last_trade_time[symbol]
                if time_since_last < min_time_between_trades:
                    logger.debug("Signal filtered - too frequent", extra={
                        "symbol": symbol,
                        "time_since_last_minutes": time_since_last / 60.0,
                        "min_required_minutes": min_time_between_trades / 60.0
                    })
                    return False
            
            # FILTER 4: Dynamic Position Sizing (Risk-based)
            portfolio_value = self.client.get_account().portfolio_value
            risk_amount = portfolio_value * (self.risk_percent / 100.0)
            max_loss_per_share = current_price * (self.min_profit_bp / 10000.0)
            
            # Safety: Ensure max_loss_per_share is above minimum threshold
            min_loss_threshold = current_price * 0.0001  # Minimum 1 basis point
            if max_loss_per_share < min_loss_threshold:
                max_loss_per_share = min_loss_threshold
            
            max_qty = int(risk_amount / max_loss_per_share)
            qty = min(int(base_qty), max(1, max_qty))
            
            # Additional safety: Cap maximum position size
            max_position_value = portfolio_value * 0.1  # Max 10% of portfolio per position
            max_shares = int(max_position_value / current_price)
            qty = min(qty, max_shares)
            
            if qty <= 0:
                logger.debug("Signal filtered - insufficient capital for risk", extra={
                    "symbol": symbol,
                    "portfolio_value": portfolio_value,
                    "risk_percent": self.risk_percent
                })
                return False
            
            # For BUY: check buying power
            if action == "BUY":
                cost = qty * current_price
                if cost > self.account.buying_power:
                    logger.warning("Insufficient buying power", extra={
                        "required": cost,
                        "available": self.account.buying_power,
                        "symbol": symbol
                    })
                    return False
            
            # For SELL: check if we have the position
            elif action == "SELL":
                positions = self.client.get_positions()
                pos = next((p for p in positions if p.symbol == symbol), None)
                if not pos or pos.qty < qty:
                    logger.warning("Insufficient position to sell", extra={
                        "symbol": symbol,
                        "requested": qty,
                        "available": pos.qty if pos else 0
                    })
                    return False
            
            # Submit order with accurate market price
            # Pass current market price to client for accurate fill simulation
            self.client.set_market_prices({symbol: current_price})
            
            order = self.client.submit_order(
                symbol=symbol,
                qty=int(qty),
                side=action.lower(),
                type="market",
                time_in_force="day"
            )
            
            # Wait for fill (with retries for fill delay simulation)
            max_attempts = 50  # 50 * 50ms = 2.5 seconds
            attempt = 0
            while attempt < max_attempts:
                filled_order = self.client.get_order(order.id)
                if filled_order.filled_qty > 0 or filled_order.status == "filled":
                    self.trades_count += 1
                    self.last_trade_time[symbol] = current_time
                    self._record_trade(filled_order, signal)
                    self._record_equity_update("TRADE")
                    
                    # Update position state after trade
                    if action == "BUY":
                        # BUY from FLAT = LONG, BUY from SHORT = FLAT (cover)
                        new_state = "LONG" if current_state in ["FLAT", "SHORT"] else "LONG"
                    else:  # SELL
                        # SELL from FLAT = SHORT, SELL from LONG = FLAT (exit)
                        new_state = "SHORT" if current_state == "FLAT" else "FLAT"
                    
                    self.position_state[symbol] = new_state
                    
                    logger.info("Trade executed", extra={
                        "symbol": symbol,
                        "action": action,
                        "qty": filled_order.filled_qty,
                        "price": filled_order.filled_avg_price,
                        "confidence": confidence,
                        "expected_profit_bp": expected_profit_bp,
                        "position_transition": f"{current_state} -> {new_state}"
                    })
                    
                    return True
                
                # Brief sleep before retry
                time.sleep(0.05)
                attempt += 1
            
            # Order not filled after timeout
            logger.warning("Order did not fill within timeout", extra={
                "symbol": symbol,
                "action": action,
                "order_id": order.id
            })
            return False
        
        except Exception as e:
            logger.error("Failed to process signal", extra={
                "error": str(e),
                "signal": signal
            })
        
        return False
    
    def update_market_prices(self, market_tick: MarketTick) -> None:
        """Update market prices and recalculate MTM equity.
        
        Called on every price tick to update portfolio value.
        This is the key to real-time equity updates.
        
        Args:
            market_tick: Current market data point
        """
        # Update price
        self.current_prices[market_tick.symbol] = market_tick.close
        
        # Update account with current prices (MTM)
        self.client._update_portfolio_value()
        self.account = self.client.get_account()
        
        # Record update (with throttling to avoid too many writes)
        now = time.time()
        if now - self.last_update_time > 1.0:  # Max 1 update per second
            self._record_equity_update("TICK")
            self.last_update_time = now
    
    def _record_trade(self, filled_order, signal) -> None:
        """Record a filled trade."""
        trade = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "signal_timestamp": signal.get("timestamp", ""),
            "order_id": filled_order.id,
            "symbol": filled_order.symbol,
            "side": filled_order.side.upper(),
            "qty": filled_order.filled_qty,
            "filled_price": filled_order.filled_avg_price,
            "status": "filled"
        }
        
        # Append to trades log
        with self.trades_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trade) + "\n")
    
    def _record_equity_update(self, update_type: str) -> None:
        """Record equity snapshot (called on every significant event)."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "update_type": update_type,
            "cash": round(self.account.cash, 2),
            "portfolio_value": round(self.account.portfolio_value, 2),
            "buying_power": round(self.account.buying_power, 2),
            "positions": len(self.client.get_positions()),
            "trades_executed": self.trades_count,
        }
        
        # Append to equity log
        with self.equity_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot) + "\n")
        
        # Append to updates log (for streaming)
        with self.updates_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot) + "\n")
        
        # Callback for streaming
        if self.update_callback:
            self.update_callback(snapshot)
        
        self.update_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        positions = self.client.get_positions()
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "cash": round(self.account.cash, 2),
            "portfolio_value": round(self.account.portfolio_value, 2),
            "buying_power": round(self.account.buying_power, 2),
            "positions_count": len(positions),
            "trades_executed": self.trades_count,
            "updates_recorded": self.update_count,
            "current_prices": self.current_prices,
        }
    
    def get_equity_curve(self):
        """Get equity history as list of snapshots."""
        return self.client.get_equity_history()
    
    def get_trades(self):
        """Get all executed trades."""
        return self.client.get_trades()
    
    def get_positions(self):
        """Get current open positions."""
        return self.client.get_positions()
    
    def save_account_state(self) -> None:
        """Save current account state for persistence across sessions."""
        positions = self.client.get_positions()
        positions_dict = {
            p.symbol: {"qty": p.qty, "avg_price": p.avg_fill_price}
            for p in positions
        }
        
        session_count = self.account_state_manager.get_session_count() + 1
        lifetime_trades = self.session_start_trades + self.trades_count
        
        self.account_state_manager.save_state(
            cash=self.account.cash,
            portfolio_value=self.account.portfolio_value,
            positions=positions_dict,
            trades_count=lifetime_trades,
            session_count=session_count
        )
        
        logger.info("Account state saved", extra={
            "portfolio_value": self.account.portfolio_value,
            "session": session_count,
            "lifetime_trades": lifetime_trades
        })


def load_market_data(path: Path) -> List[Dict[str, Any]]:
    """Load market data from JSONL."""
    data = []
    if not path.exists():
        return data
    
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    return data


def load_signals(path: Path) -> List[Dict[str, Any]]:
    """Load signals from JSONL."""
    signals = []
    if not path.exists():
        return signals
    
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                signals.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    return signals


def run_live_trading(
    market_data_path: Path = Path("data/market_data.jsonl"),
    signals_path: Path = Path("data/signals.jsonl"),
    initial_cash: float = 100000.0,
    output_dir: Path = Path("data"),
    min_confidence: float = 0.60,
    min_profit_bp: float = 3.0,
    risk_percent: float = 1.0,
    current_price: Optional[float] = None,
    use_persistence: bool = True,
) -> LiveTradingEngine:
    """Run live trading simulation with profit optimization and account persistence.
    
    Args:
        market_data_path: Path to market OHLCV data
        signals_path: Path to trade signals
        initial_cash: Starting capital (only used if no saved state exists)
        output_dir: Output directory for logs
        min_confidence: Minimum signal confidence threshold (0-1)
        min_profit_bp: Minimum expected profit in basis points
        risk_percent: Risk per trade as % of portfolio
        current_price: Current market price to use (overrides historical data)
        use_persistence: If True, load/save account state between sessions
    
    Returns:
        Completed trading engine with results
    """
    print(f"\n{'='*70}")
    print("Live Trading Engine - Real-time Simulation with Profit Optimization")
    print(f"{'='*70}\n")
    
    # Load or initialize account state
    if use_persistence:
        account_mgr = AccountStateManager(output_dir / "account_state.json")
        starting_capital = account_mgr.get_initial_cash(default=initial_cash)
    else:
        starting_capital = initial_cash
        print(f"📊 Starting new account - Initial capital: ${initial_cash:,.2f}")
    
    # Load data
    market_data = load_market_data(market_data_path)
    signals = load_signals(signals_path)
    
    if not market_data:
        print("ERROR: No market data found")
        return None
    if not signals:
        print("ERROR: No signals found")
        return None
    
    print(f"Market data points: {len(market_data)}")
    print(f"Signals: {len(signals)}")
    print(f"Starting capital: ${starting_capital:,.2f}\n")
    print("Profit Optimization Settings:")
    print(f"  Min Confidence: {min_confidence*100:.1f}%")
    print(f"  Min Profit Edge: {min_profit_bp:.1f}bp")
    print(f"  Risk per Trade: {risk_percent:.1f}%\n")
    
    # Create engine with optimization parameters
    engine = LiveTradingEngine(
        initial_cash=starting_capital,
        output_dir=output_dir,
        min_confidence=min_confidence,
        min_profit_bp=min_profit_bp,
        risk_percent=risk_percent
    )
    
    # Sort both data streams by timestamp for time-based matching
    market_data = sorted(market_data, key=lambda x: x.get("timestamp", ""))
    signals = sorted(signals, key=lambda x: x.get("timestamp", ""))
    
    # Get the primary symbol from market data (use first record's symbol)
    primary_symbol = market_data[0].get("symbol", "SPY") if market_data else "SPY"
    
    # Filter signals to only those matching the primary symbol
    signals = [s for s in signals if s.get("symbol", "") == primary_symbol]
    
    print(f"Filtered to {len(signals)} signals for {primary_symbol}")
    
    # Process market data tick by tick with signal execution
    trades_executed = 0
    signal_idx = 0
    
    for i, tick_data in enumerate(market_data):
        ts = tick_data.get("timestamp", "")
        symbol = tick_data.get("symbol", "SPY")
        close = tick_data.get("close", 0.0)
        
        # Use current_price if provided (real-time), otherwise use historical bar close
        execution_price = current_price if current_price is not None else close
        
        # Process all signals that occur at or before this timestamp
        while signal_idx < len(signals):
            signal = signals[signal_idx]
            signal_ts = signal.get("timestamp", "")
            
            # Only process signals at or before current time
            if signal_ts <= ts:
                if engine.process_signal(signal, execution_price):
                    trades_executed += 1
                signal_idx += 1
            else:
                break
        
        # Update market prices (MTM)
        tick = MarketTick(
            timestamp=ts,
            symbol=symbol,
            open=tick_data.get("open", 0.0),
            high=tick_data.get("high", 0.0),
            low=tick_data.get("low", 0.0),
            close=close,
            volume=tick_data.get("volume", 0)
        )
        engine.update_market_prices(tick)
    
    # Final summary
    status = engine.get_status()
    
    print(f"\n{'='*70}")
    print("Live Trading Complete!")
    print(f"{'='*70}")
    print(f"Trades executed: {trades_executed}")
    print(f"Equity updates: {status['updates_recorded']}")
    print(f"\nFinal Portfolio:")
    print(f"  Cash:           ${status['cash']:,.2f}")
    print(f"  Portfolio Value: ${status['portfolio_value']:,.2f}")
    print(f"  Buying Power:   ${status['buying_power']:,.2f}")
    print(f"  Open Positions: {status['positions_count']}")
    
    initial_pv = starting_capital
    final_pv = status['portfolio_value']
    pnl = final_pv - initial_pv
    return_pct = (pnl / initial_pv) * 100
    print(f"\nSession Performance:")
    print(f"  P&L:    ${pnl:,.2f}")
    print(f"  Return: {return_pct:+.2f}%")
    
    # Save account state for next session
    if use_persistence:
        engine.save_account_state()
        print(f"\n✅ Account state saved for next session")
    
    print(f"{'='*70}\n")
    
    return engine
