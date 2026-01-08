"""Common technical indicators implemented without pandas dependency.

Functions accept lists of numeric closes and return lists aligned with input
length (None for indices where the indicator is undefined).
"""

from typing import List, Optional


def sma(values: List[float], window: int) -> List[Optional[float]]:
    out = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
    window_vals = [v for v in values[i - window + 1 : i + 1] if v is not None]
    out.append(sum(window_vals) / len(window_vals) if window_vals else None)
    return out


def ema(values: List[float], window: int) -> List[Optional[float]]:
    alpha = 2 / (window + 1)
    out = []
    prev = None
    for v in values:
        if v is None:
            out.append(None)
            continue
        if prev is None:
            prev = v
        else:
            prev = alpha * v + (1 - alpha) * prev
        out.append(prev)
    return out


def rsi(values: List[float], window: int = 14) -> List[Optional[float]]:
    gains = [0]
    losses = [0]
    for i in range(1, len(values)):
        if values[i] is None or values[i - 1] is None:
            gains.append(0)
            losses.append(0)
            continue
        diff = values[i] - values[i - 1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    out = [None] * len(values)
    avg_gain = None
    avg_loss = None
    for i in range(len(values)):
        if i < window:
            out[i] = None
            continue
        if i == window:
            avg_gain = sum(gains[1 : window + 1]) / window
            avg_loss = sum(losses[1 : window + 1]) / window
        else:
            avg_gain = (avg_gain * (window - 1) + gains[i]) / window
            avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss if avg_loss else None
            out[i] = 100 - (100 / (1 + rs)) if rs is not None else None
    return out


__all__ = ["sma", "ema", "rsi"]
