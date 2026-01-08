"""Model utility functions for saving/loading and evaluation."""

import json


def save_model(model_obj, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"model": "stub"}, f)


def compute_feature_importance(X, y, feature_names):
    """
    Compute simple feature importance using sklearn RandomForest if
    available, otherwise return zeros. Returns list of
    (feature, importance).
    """
    try:
        from sklearn.ensemble import RandomForestRegressor
        import numpy as _np

        arrX = _np.array(X)
        arrY = _np.array(y)
        model = RandomForestRegressor(n_estimators=10, random_state=1)
        model.fit(arrX, arrY)
        importances = model.feature_importances_
        return list(zip(feature_names, [float(v) for v in importances]))
    except Exception:
        return list(zip(feature_names, [0.0 for _ in feature_names]))
