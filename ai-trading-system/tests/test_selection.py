from src.features import selection


def test_feature_importance_and_selection():
    X = [
        {"f1": 1, "f2": 10, "target": 2},
        {"f1": 2, "f2": 20, "target": 4},
        {"f1": 3, "f2": 30, "target": 6},
    ]
    imps = selection.feature_importance(X, ["f1", "f2"], "target")
    assert len(imps) == 2
    top = selection.select_top_features(imps, 1)
    assert isinstance(top, list) and len(top) == 1
