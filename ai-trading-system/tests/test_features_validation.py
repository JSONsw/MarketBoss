from src.features import feature_engineering, validation


def make_sample_records():
    return [
        {"timestamp": "2025-01-01T00:00:00Z", "symbol": "A", "close": 10.0},
        {"timestamp": "2025-01-01T00:01:00Z", "symbol": "A", "close": 10.5},
        {"timestamp": "2025-01-01T00:02:00Z", "symbol": "A", "close": 11.0},
        {"timestamp": "2025-01-01T00:00:00Z", "symbol": "B", "close": 20.0},
        {"timestamp": "2025-01-01T00:01:00Z", "symbol": "B", "close": 19.5},
    ]


def test_build_features_and_required_present():
    recs = make_sample_records()
    feats = feature_engineering.build_features(recs)
    ok, missing = validation.required_features_present(feats, ["return", "ma_3"])
    assert ok is True
    assert missing == []


def test_missing_value_counts_and_drift():
    recs = make_sample_records()
    feats = feature_engineering.build_features(recs)
    mv = validation.missing_value_counts(feats)
    # first row per symbol has None return
    assert mv.get("return", 0) >= 2

    # check drift: compare first two returns to later returns
    returns = [f.get("return") for f in feats if f.get("return") is not None]
    old = returns[:1]
    new = returns[1:]
    drift = validation.population_drift(old, new, mean_threshold=0.01)
    assert isinstance(drift, bool)
