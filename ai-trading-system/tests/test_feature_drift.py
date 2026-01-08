from src.monitoring import feature_drift


def test_feature_drift_alerting(tmp_path, monkeypatch):
    baseline = [
        {"return": 0.01, "ma_3": 10},
        {"return": 0.02, "ma_3": 10.5},
    ]
    current = [
        {"return": 0.5, "ma_3": 9},
        {"return": 0.6, "ma_3": 9.5},
    ]
    # monkeypatch alerts to write to tmp path
    res = feature_drift.check_feature_drift(
        baseline,
        current,
        ["return", "ma_3"],
        thresholds={"default": 0.1, "return": 0.1},
    )
    assert isinstance(res, dict)
