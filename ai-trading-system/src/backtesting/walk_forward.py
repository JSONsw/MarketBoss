from typing import Iterable, List, Tuple

from .backtester import run_backtest_mtm


def walk_forward(
    data_windows: Iterable[Tuple[Iterable[dict], Iterable[float]]],
    slippage_bp: float = 0.0,
    commission_pct: float = 0.0,
    fixed_fee: float = 0.0,
) -> List[List[dict]]:
    """Run walk-forward evaluation over a sequence of (signals, prices)
    windows.

    Each item in `data_windows` is a tuple (signals, market_prices).
    Returns a list of per-window results (output of `run_backtest_mtm`).
    """
    all_results: List[List[dict]] = []

    for signals, market_prices in data_windows:
        res = run_backtest_mtm(
            signals,
            market_prices,
            slippage_bp=slippage_bp,
            commission_pct=commission_pct,
            fixed_fee=fixed_fee,
        )
        all_results.append(res)

    return all_results
