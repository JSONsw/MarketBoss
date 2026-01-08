"""Regime detection features such as volatility regime and momentum regime."""

from typing import List, Dict
import math


def rolling_std(values: List[float], window: int) -> List[float]:
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_vals = [v for v in values[start : i + 1] if v is not None]
        if not window_vals:
            out.append(None)
        else:
            mean = sum(window_vals) / len(window_vals)
            var = sum((x - mean) ** 2 for x in window_vals) / len(window_vals)
            out.append(math.sqrt(var))
    return out


def volatility_regime(
    records: List[Dict], window: int = 20, threshold: float = None
) -> List[Dict]:
    """Label records with volatility regime: 'low' or 'high'.

    If `threshold` is None, uses median rolling std as threshold.
    """
    closes = [
        float(r.get("close")) if r.get("close") is not None else None for r in records
    ]
    stds = rolling_std(closes, window)
    vals = [s for s in stds if s is not None]
    if not vals:
        thr = threshold or 0.0
    else:
        thr = threshold if threshold is not None else sorted(vals)[len(vals) // 2]
    out = []
    for r, s in zip(records, stds):
        rec = dict(r)
        rec["volatility"] = s
        rec["vol_regime"] = "high" if s is not None and s >= thr else "low"
        out.append(rec)
    return out


__all__ = ["volatility_regime"]
"""Market regime detection features."""


def detect_regime(df):
    return df
