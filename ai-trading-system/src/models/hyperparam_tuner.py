"""Hyperparameter tuning harness.

Provides a lightweight grid-search tuner that uses scikit-learn when
available. Results are written to a JSON file for later inspection.
"""

import json
import os
from typing import Dict, Any, List, Optional
from src.models.artifact_logger import save_artifact


def _iter_param_grid(grid: Dict[str, List[Any]]):
    # simple cartesian product without external deps
    keys = list(grid.keys())
    if not keys:
        yield {}
        return

    lists = [grid[k] for k in keys]

    def rec(idx, cur):
        if idx == len(keys):
            yield dict(cur)
            return
        for v in lists[idx]:
            cur[keys[idx]] = v
            yield from rec(idx + 1, cur)

    yield from rec(0, {})


def run_grid_search(
    X,
    y,
    param_grid: Dict[str, List[Any]],
    cv: int = 3,
    scoring: str = "neg_mean_squared_error",
    out_path: Optional[str] = None,
):
    """Run a simple grid search using sklearn when available.

    X and y should be array-like (lists of lists / lists).
    Returns a dict with all evaluated results and the best params.
    """
    results = []
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import KFold
        from sklearn.metrics import mean_squared_error
        import numpy as _np

        arrX = _np.array(X)
        arrY = _np.array(y)

        for params in _iter_param_grid(param_grid):
            # build model with params
            model = RandomForestRegressor(**params, random_state=1)
            # cross-val
            kf = KFold(n_splits=max(2, int(cv)), shuffle=True, random_state=1)
            scores = []
            for tr_idx, te_idx in kf.split(arrX):
                model.fit(arrX[tr_idx], arrY[tr_idx])
                pred = model.predict(arrX[te_idx])
                mse = float(mean_squared_error(arrY[te_idx], pred))
                scores.append(mse)
            avg_score = float(sum(scores) / len(scores))
            results.append({"params": params, "mse": avg_score})

        # pick best (lowest mse)
        best = min(results, key=lambda r: r["mse"]) if results else None
    except Exception:
        # sklearn not available or other error: return empty result
        results = []
        best = None

    out = {"results": results, "best": best}
    if out_path:
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2)
        except Exception:
            pass
    # save artifact manifest for reproducibility
    try:
        meta = {"param_grid": param_grid, "cv": cv, "scoring": scoring}
        save_artifact(
            out,
            name="tuning_results",
            metadata=meta,
            out_dir=os.path.join("models", "artifacts"),
        )
    except Exception:
        pass

    return out


__all__ = ["run_grid_search"]
