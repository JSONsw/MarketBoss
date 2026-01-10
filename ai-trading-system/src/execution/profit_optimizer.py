"""Advanced profit optimization strategies for live trading.

Implements sophisticated filters to push trading systems toward profitability:
1. Adaptive confidence thresholds based on recent win rate
2. Stop-loss and take-profit targets per position
3. Dynamic position sizing based on volatility
4. Trade exit strategies (trailing stops, profit targets)
5. Win-rate tracking for signal quality feedback
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics

from src.monitoring.structured_logger import get_logger

logger = get_logger("profit_optimizer")


@dataclass
class Position:
    """Track an open position for exit management."""
    symbol: str
    side: str  # BUY or SELL
    qty: int
    entry_price: float
    entry_time: float
    entry_timestamp: str
    
    # Exit targets
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop: Optional[float] = None
    
    # Performance tracking
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        if self.side == "BUY":
            return (current_price - self.entry_price) * self.qty
        else:  # SELL
            return (self.entry_price - current_price) * self.qty
    
    def should_exit(self, current_price: float) -> Tuple[bool, Optional[str]]:
        """Check if position should be closed based on exit rules.
        
        Returns:
            (should_exit, reason)
        """
        pnl = self.calculate_pnl(current_price)
        
        # Check stop-loss
        if self.stop_loss_price is not None:
            if self.side == "BUY" and current_price <= self.stop_loss_price:
                return True, "stop_loss"
            elif self.side == "SELL" and current_price >= self.stop_loss_price:
                return True, "stop_loss"
        
        # Check take-profit
        if self.take_profit_price is not None:
            if self.side == "BUY" and current_price >= self.take_profit_price:
                return True, "take_profit"
            elif self.side == "SELL" and current_price <= self.take_profit_price:
                return True, "take_profit"
        
        # Check trailing stop
        if self.trailing_stop is not None and pnl > 0:
            trailing_loss = pnl * (self.trailing_stop / 100.0)
            if pnl - (pnl - trailing_loss) >= trailing_loss:
                return True, "trailing_stop"
        
        return False, None


class ProfitOptimizer:
    """Advanced profit optimization with adaptive filters."""
    
    def __init__(self, lookback_trades: int = 100):
        self.lookback_trades = lookback_trades
        self.recent_trades: List[Dict[str, Any]] = []
        self.open_positions: Dict[str, Position] = {}
        
        logger.info(
            "Profit Optimizer initialized",
            extra={"lookback_trades": lookback_trades}
        )
    
    def record_trade(self, symbol: str, side: str, qty: int, price: float,
                     confidence: float = 0.5, expected_profit_bp: float = 0.0,
                     pnl: Optional[float] = None):
        """Record a completed trade for win-rate calculation."""
        trade = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "confidence": confidence,
            "expected_profit_bp": expected_profit_bp,
            "pnl": pnl if pnl is not None else 0.0,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.recent_trades.append(trade)
        
        # Keep only lookback window
        if len(self.recent_trades) > self.lookback_trades:
            self.recent_trades.pop(0)
    
    def get_win_rate(self) -> float:
        """Calculate win rate from recent trades."""
        if not self.recent_trades:
            return 0.5
        
        winning = sum(1 for t in self.recent_trades if t["pnl"] > 0)
        return winning / len(self.recent_trades)
    
    def get_average_pnl_per_trade(self) -> float:
        """Calculate average P&L per trade."""
        if not self.recent_trades:
            return 0.0
        
        total_pnl = sum(t["pnl"] for t in self.recent_trades)
        return total_pnl / len(self.recent_trades)
    
    def calculate_adaptive_thresholds(self) -> Dict[str, float]:
        """Calculate adaptive confidence/profit thresholds based on recent performance.
        
        Returns:
            Dict with adjusted thresholds
        """
        win_rate = self.get_win_rate()
        avg_pnl = self.get_average_pnl_per_trade()
        
        # Increase thresholds if recent trades are unprofitable
        base_confidence = 0.60
        base_profit_bp = 3.0
        
        if win_rate < 0.45:  # Poor performance
            confidence_threshold = base_confidence + 0.15
            profit_bp_threshold = base_profit_bp + 3.0
        elif win_rate < 0.50:  # Below breakeven
            confidence_threshold = base_confidence + 0.10
            profit_bp_threshold = base_profit_bp + 2.0
        elif win_rate < 0.55:  # Slightly below breakeven
            confidence_threshold = base_confidence + 0.05
            profit_bp_threshold = base_profit_bp + 1.0
        else:  # Good or breakeven performance
            confidence_threshold = base_confidence
            profit_bp_threshold = base_profit_bp
        
        return {
            "confidence_threshold": min(confidence_threshold, 0.90),
            "profit_bp_threshold": profit_bp_threshold,
            "win_rate": win_rate,
            "avg_pnl_per_trade": avg_pnl,
        }
    
    def calculate_position_stops(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        qty: int,
        risk_percent: float = 2.0,  # 2% max loss per trade
        profit_target_bp: float = 5.0,  # Target 5bp profit
    ) -> Tuple[float, float]:
        """Calculate stop-loss and take-profit prices for a position.
        
        Args:
            symbol: Trading symbol
            side: BUY or SELL
            entry_price: Entry price
            qty: Quantity
            risk_percent: Max risk as % of portfolio (2% = 0.02)
            profit_target_bp: Target profit in basis points
        
        Returns:
            (stop_loss_price, take_profit_price)
        """
        # Convert basis points to absolute dollar amount
        profit_target_dollars = (profit_target_bp / 10000.0) * entry_price
        risk_dollars = (risk_percent / 100.0) * entry_price
        
        if side == "BUY":
            stop_loss = entry_price - risk_dollars
            take_profit = entry_price + profit_target_dollars
        else:  # SELL
            stop_loss = entry_price + risk_dollars
            take_profit = entry_price - profit_target_dollars
        
        return stop_loss, take_profit
    
    def should_take_trade(
        self,
        symbol: str,
        confidence: float,
        expected_profit_bp: float,
    ) -> Tuple[bool, Optional[str]]:
        """Determine if a trade should be taken based on adaptive thresholds.
        
        Returns:
            (should_trade, reason_if_not)
        """
        thresholds = self.calculate_adaptive_thresholds()
        
        if confidence < thresholds["confidence_threshold"]:
            return False, f"low_confidence (need {thresholds['confidence_threshold']:.2f}, got {confidence:.2f})"
        
        if expected_profit_bp < thresholds["profit_bp_threshold"]:
            return False, f"insufficient_profit_bp (need {thresholds['profit_bp_threshold']:.1f}, got {expected_profit_bp:.1f})"
        
        return True, None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary statistics of recent trading."""
        if not self.recent_trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_pnl": 0.0,
                "total_pnl": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
            }
        
        pnls = [t["pnl"] for t in self.recent_trades]
        winning = sum(1 for p in pnls if p > 0)
        
        return {
            "total_trades": len(self.recent_trades),
            "win_rate": winning / len(self.recent_trades),
            "avg_pnl": statistics.mean(pnls),
            "total_pnl": sum(pnls),
            "best_trade": max(pnls),
            "worst_trade": min(pnls),
            "std_dev_pnl": statistics.stdev(pnls) if len(pnls) > 1 else 0.0,
        }
    
    def save_performance_log(self, output_path: Path):
        """Save performance metrics to disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        summary = self.get_performance_summary()
        summary["trades"] = self.recent_trades
        
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(
            "Performance log saved",
            extra={"path": str(output_path), "trades": len(self.recent_trades)}
        )
