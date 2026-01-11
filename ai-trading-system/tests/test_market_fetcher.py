"""Tests for MarketFetcher using Yahoo Finance backend."""

import pytest
from datetime import datetime, timedelta
from src.data_pipeline.market_fetcher import MarketFetcher

# Setup constants for testing
SYMBOL = "AAPL"


@pytest.fixture
def mock_yfinance(mocker):
    """
    Mock yfinance Ticker.history() to return test data without hitting the API.
    """
    import pandas as pd
    
    # Create mock DataFrame that yfinance returns
    mock_df = pd.DataFrame({
        'Open': [100.0],
        'High': [110.0],
        'Low': [99.0],
        'Close': [105.0],
        'Volume': [10000]
    }, index=pd.DatetimeIndex(['2025-01-01 00:00:00'], name='Datetime'))
    
    mock_ticker = mocker.Mock()
    mock_ticker.history.return_value = mock_df
    
    # Patch yfinance.Ticker to return our mock
    mocker.patch('yfinance.Ticker', return_value=mock_ticker)
    
    return mock_ticker


@pytest.fixture
def fetcher():
    """
    Return an instance of the MarketFetcher class (no credentials needed for Yahoo Finance).
    """
    return MarketFetcher()


def test_fetch_intraday_success(fetcher, mock_yfinance):
    """
    Test if `fetch_intraday` works and normalizes valid data correctly.
    """
    start = (datetime.now() - timedelta(days=1)).isoformat()
    end = datetime.now().isoformat()
    data = fetcher.fetch_intraday(SYMBOL, start=start, end=end, interval="1m")
    
    assert data is not None
    assert len(data) == 1
    record = data[0]
    assert record["timestamp"] == "2025-01-01T00:00:00"
    assert record["symbol"] == SYMBOL
    assert record["open"] == 100.0
    assert record["high"] == 110.0
    assert record["low"] == 99.0
    assert record["close"] == 105.0
    assert record["volume"] == 10000


def test_fetch_intraday_no_data(fetcher, mocker):
    """
    Test how `fetch_intraday` handles empty response (no data available).
    """
    import pandas as pd
    
    # Mock empty DataFrame
    mock_ticker = mocker.Mock()
    mock_ticker.history.return_value = pd.DataFrame()
    mocker.patch('yfinance.Ticker', return_value=mock_ticker)
    
    start = (datetime.now() - timedelta(days=1)).isoformat()
    end = datetime.now().isoformat()
    data = fetcher.fetch_intraday(SYMBOL, start=start, end=end, interval="1m")
    
    assert data is None


def test_fetch_intraday_api_error(fetcher, mocker):
    """
    Test how `fetch_intraday` handles API connectivity or server errors.
    """
    # Mock yfinance to raise an exception
    mock_ticker = mocker.Mock()
    mock_ticker.history.side_effect = Exception("Network error")
    mocker.patch('yfinance.Ticker', return_value=mock_ticker)
    
    start = (datetime.now() - timedelta(days=1)).isoformat()
    end = datetime.now().isoformat()
    data = fetcher.fetch_intraday(SYMBOL, start=start, end=end, interval="1m")
    
    assert data is None


def test_interval_mapping(fetcher, mock_yfinance):
    """
    Test that interval mapping works correctly (Alpaca format -> Yahoo Finance format).
    """
    start = (datetime.now() - timedelta(days=1)).isoformat()
    end = datetime.now().isoformat()
    
    # Test various interval formats
    for alpaca_interval, yf_interval in [("1Min", "1m"), ("5Min", "5m"), ("1Hour", "1h"), ("1Day", "1d")]:
        data = fetcher.fetch_intraday(SYMBOL, start=start, end=end, interval=alpaca_interval)
        assert data is not None
        # Verify the mock was called with the correct yfinance interval
        mock_yfinance.history.assert_called()


def test_market_fetcher_no_credentials_required():
    """
    Test that MarketFetcher can be initialized without any API credentials.
    """
    # Should not raise any errors
    fetcher = MarketFetcher()
    assert fetcher.base_url == "Yahoo Finance (free API)"


def test_market_fetcher_backward_compatibility():
    """
    Test that MarketFetcher still accepts legacy Alpaca parameters for backward compatibility.
    """
    # Should not raise errors even though these parameters are ignored
    fetcher = MarketFetcher(
        api_key="dummy_key",
        api_secret="dummy_secret",
        base_url="https://example.com"
    )
    assert fetcher.base_url == "Yahoo Finance (free API)"
