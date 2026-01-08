"""Backtest metrics utilities: cumulative PnL, drawdown, turnover, trade stats.

This module contains lightweight, dependency-free helpers used by unit
tests and simple CI checks.
"""

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
