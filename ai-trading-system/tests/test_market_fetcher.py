import pytest
from src.data_pipeline.market_fetcher import MarketFetcher

# Setup constants for testing
DUMMY_API_KEY = "your_dummy_api_key"  # Replace with actual API key for integration tests
SYMBOL = "AAPL"
FAKE_DATA = {
    "Time Series (1min)": {
        "2025-01-01 00:00:00": {
            "1. open": "100.0",
            "2. high": "110.0",
            "3. low": "99.0",
            "4. close": "105.0",
            "5. volume": "10000",
        }
    }
}

@pytest.fixture
def mock_valid_response(mocker):
    """
    Mock a valid API response from Alpha Vantage to simulate real market data.
    """
    return mocker.patch(
        "requests.get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: FAKE_DATA
        ),
    )

@pytest.fixture
def fetcher():
    """
    Return an instance of the MarketFetcher class for testing.
    """
    return MarketFetcher(api_key=DUMMY_API_KEY)

def test_fetch_intraday_success(fetcher, mock_valid_response):
    """
    Test if `fetch_intraday` works and normalizes valid data correctly.
    """
    data = fetcher.fetch_intraday(SYMBOL, interval="1min")
    assert len(data) == 1
    record = data[0]
    assert record["timestamp"] == "2025-01-01 00:00:00"
    assert record["symbol"] == SYMBOL
    assert record["open"] == 100.0
    assert record["high"] == 110.0
    assert record["low"] == 99.0
    assert record["close"] == 105.0
    assert record["volume"] == 10000

def test_fetch_intraday_invalid_symbol(fetcher, mocker):
    """
    Test how `fetch_intraday` handles an invalid symbol or bad API response.
    """
    mocker.patch(
        "requests.get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {"Note": "Invalid symbol"}
        ),
    )
    data = fetcher.fetch_intraday("INVALID_SYMBOL", interval="1min")
    assert data is None

def test_fetch_intraday_api_error(fetcher, mocker):
    """
    Test how `fetch_intraday` handles API connectivity or server errors.
    """
    mocker.patch(
        "requests.get",
        side_effect=Exception("API request failed")
    )
    data = fetcher.fetch_intraday(SYMBOL, interval="1min")
    assert data is None

def test_live_market_fetcher():
    fetcher = MarketFetcher()  # Picks API_KEY from .env
    data = fetcher.fetch_intraday("AAPL", interval="1min")
    assert data is not None, "Failed to fetch live data"
    print(data)