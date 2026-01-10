"""Backtest metrics utilities: cumulative PnL, drawdown, turnover, trade stats.

This module contains lightweight, dependency-free helpers used by unit
tests and simple CI checks.
"""

import numpy as np
from typing import Iterable, List, Dict


def cumulative_pnl(pnls: Iterable[float]) -> List[float]:
    cum = []
    total = 0.0
    for p in pnls:
        total += float(p)
        cum.append(total)
    return cum


def max_drawdown(cum_pnls: Iterable[float]) -> float:
    cur_peak = -float("inf")
    max_dd = 0.0
    for x in cum_pnls:
        if x > cur_peak:
            cur_peak = x
        dd = cur_peak - x
        if dd > max_dd:
            max_dd = dd
    return float(max_dd)


def trade_stats(results: Iterable[Dict[str, float]]) -> Dict[str, float]:
    """Compute simple trade-level statistics.

    Expects each item in results to contain `pnl` and optionally `slippage`.
    Returns dict with `n_trades`, `total_pnl`, `avg_pnl`, `win_rate`, and
    `avg_slippage`.
    """
    pnls = []
    slippages = []
    for r in results:
        pnls.append(float(r.get("pnl", 0.0)))
        if "slippage" in r:
            slippages.append(float(r["slippage"]))

    n = len(pnls)
    total = sum(pnls)
    avg = total / n if n else 0.0
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / n if n else 0.0
    avg_slip = sum(slippages) / len(slippages) if slippages else 0.0

    return {
        "n_trades": float(n),
        "total_pnl": float(total),
        "avg_pnl": float(avg),
        "win_rate": float(win_rate),
        "avg_slippage": float(avg_slip),
    }


def calculate_sharpe(returns: Iterable[float], risk_free_rate: float = 0.0) -> float:
    """Calculate annualized Sharpe ratio.
    
    Args:
        returns: List/array of periodic returns
        risk_free_rate: Annualized risk-free rate (default 0.0)
        
    Returns:
        Annualized Sharpe ratio
    """
    returns_array = np.array(list(returns))
    
    if len(returns_array) == 0:
        return 0.0
    
    # Calculate excess returns
    excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
    
    # Calculate Sharpe
    if np.std(excess_returns) == 0:
        return 0.0
    
    sharpe = np.mean(excess_returns) / np.std(excess_returns)
    
    # Annualize (assuming daily returns)
    sharpe_annual = sharpe * np.sqrt(252)
    
    return float(sharpe_annual)


def calculate_max_drawdown(equity_curve: Iterable[float]) -> float:
    """Calculate maximum drawdown from equity curve.
    
    Args:
        equity_curve: List/array of cumulative equity values
        
    Returns:
        Maximum drawdown as a positive percentage (e.g., 0.15 for 15% drawdown)
    """
    equity_array = np.array(list(equity_curve))
    
    if len(equity_array) == 0:
        return 0.0
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(equity_array)
    
    # Calculate drawdown at each point
    drawdown = (running_max - equity_array) / running_max
    
    # Return maximum drawdown
    max_dd = float(np.max(drawdown))
    
    return max_dd
