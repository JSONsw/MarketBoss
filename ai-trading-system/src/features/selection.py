"""Feature selection and importance helpers.

Provides mutual information-based selection if scikit-learn is available,
otherwise falls back to correlation-based ranking.
"""

from typing import List, Dict, Tuple
import math

try:
    from sklearn.feature_selection import mutual_info_regression
except Exception:
    mutual_info_regression = None


def _corr_importance(
    X: List[Dict], feature_names: List[str], target_name: str
) -> List[Tuple[str, float]]:
    # compute Pearson correlation between each feature and target
    xs = {f: [] for f in feature_names}
    y = []
    for row in X:
        for f in feature_names:
            xs[f].append(row.get(f))
        y.append(row.get(target_name))
    res = []
    for f in feature_names:
        xf = xs[f]
        # simple correlation
        try:
            n = len(xf)
            mean_x = sum(x for x in xf if x is not None) / n
            mean_y = sum(yy for yy in y if yy is not None) / n
            num = sum((a - mean_x) * (b - mean_y) for a, b in zip(xf, y))
            den = math.sqrt(
                sum((a - mean_x) ** 2 for a in xf)
                * sum((b - mean_y) ** 2 for b in y)
            )
            corr = num / den if den != 0 else 0.0
        except Exception:
            corr = 0.0
        res.append((f, abs(corr)))
    res.sort(key=lambda x: x[1], reverse=True)
    return res


def feature_importance(
    X: List[Dict], feature_names: List[str], target_name: str
) -> List[Tuple[str, float]]:
    """Return ranked list of (feature, importance)."""
    # try mutual information
    if mutual_info_regression is not None:
        try:
            # build arrays
            import numpy as _np

            arrX = _np.array(
                [
                    [
                        row.get(f) if row.get(f) is not None else 0.0
                        for f in feature_names
                    ]
                    for row in X
                ]
            )
            arrY = _np.array(
                [
                    (
                        row.get(target_name)
                        if row.get(target_name) is not None
                        else 0.0
                    )
                    for row in X
                ]
            )
            mi = mutual_info_regression(arrX, arrY)
            res = list(zip(feature_names, [float(v) for v in mi]))
            res.sort(key=lambda x: x[1], reverse=True)
            return res
        except Exception:
            pass
    return _corr_importance(X, feature_names, target_name)


def select_top_features(
    importances: List[Tuple[str, float]], k: int
) -> List[str]:
    return [f for f, _ in importances[:k]]


__all__ = ["feature_importance", "select_top_features"]
