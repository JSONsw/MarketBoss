"""Training entrypoint for models.

This module now computes feature importance after training (using
`model_utils.compute_feature_importance`) and persists the importances
to `models/feature_importance.json`. It also updates a dashboard metric
`last_feature_importance_run`.
"""

import json
import os
from typing import List

from src.models import model_utils
from src.monitoring import dashboard


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def train(X: List[List[float]], y: List[float], feature_names: List[str], params=None):
    """Train model and compute feature importance when possible.

    Returns a stub model object; primary side-effect is writing importances.
    """
    # Placeholder training (user should replace with actual model training)
    model = {"model": "trained_stub"}

    try:
        imps = model_utils.compute_feature_importance(X, y, feature_names)
        out_dir = os.path.join("models")
        _ensure_dir(out_dir)
        out_path = os.path.join(out_dir, "feature_importance.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump({"importances": imps}, fh)
        # update dashboard metric timestamp
        dashboard.set_gauge("last_feature_importance_run", __import__("time").time())
    except Exception:
        # best-effort: don't fail training if importance computation fails
        pass

    return model


__all__ = ["train"]
