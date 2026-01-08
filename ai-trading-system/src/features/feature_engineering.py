"""Feature engineering pipeline.

Provides a minimal `build_features` function that accepts a list of
price records (dicts with `timestamp`, `symbol`, `close`) and returns
a list of feature dicts. This is intentionally small and testable; it
demonstrates how upstream code should call into feature builders.
"""

from typing import List, Dict


def build_features(records: List[Dict]) -> List[Dict]:
    """Build a tiny feature set: compute log-returns and a rolling mean.

    records: list of dicts with keys `timestamp`, `symbol`, `close`.
    Returns list of dicts with added keys `return` and `ma_3`.
    """
    out = []
    # group by symbol
    groups = {}
    for r in records:
        sym = r.get("symbol")
        groups.setdefault(sym, []).append(r)

    for sym, recs in groups.items():
        # sort by timestamp string (ISO assumed)
        recs = sorted(recs, key=lambda x: x.get("timestamp"))
        closes = [
            float(r.get("close")) if r.get("close") is not None else None for r in recs
        ]
        ma_window = 3
        for i, r in enumerate(recs):
            features = dict(r)
            prev = closes[i - 1] if i > 0 else None
            if prev is None or closes[i] is None:
                features["return"] = None
            else:
                try:
                    features["return"] = (closes[i] - prev) / prev
                except Exception:
                    features["return"] = None
            # moving average
            start = max(0, i - ma_window + 1)
            window = [c for c in closes[start : i + 1] if c is not None]
            features["ma_3"] = sum(window) / len(window) if window else None
            out.append(features)
    return out


__all__ = ["build_features"]
