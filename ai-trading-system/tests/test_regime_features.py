from src.features import regime_features


def test_volatility_regime():
    records = [
        {"timestamp": "t1", "close": 1},
        {"timestamp": "t2", "close": 2},
        {"timestamp": "t3", "close": 1},
        {"timestamp": "t4", "close": 2},
    ]
    out = regime_features.volatility_regime(records, window=2)
    assert all("vol_regime" in r for r in out)
