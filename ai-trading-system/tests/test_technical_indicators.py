from src.features import technical_indicators


def test_sma_ema_rsi():
    vals = [1, 2, 3, 4, 5, 6]
    s = technical_indicators.sma(vals, 3)
    assert s[-1] == 5.0
    e = technical_indicators.ema(vals, 3)
    assert e[-1] is not None
    r = technical_indicators.rsi(vals, window=3)
    assert isinstance(r, list)
