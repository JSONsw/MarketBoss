import pytest
from unittest.mock import patch, Mock
from src.data_pipeline.market_fetcher import MarketFetcher
from src.data_pipeline.store_data import validate_and_store

# Dummy constants for testing
DUMMY_API_KEY = "your_dummy_api_key"
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
def fetcher():
    """
    Return a MarketFetcher instance for testing.
    """
    return MarketFetcher(api_key=DUMMY_API_KEY)


@pytest.fixture
def valid_response():
    """
    Create a mocked valid API response.
    """
    response = Mock()
    response.status_code = 200
    response.json.return_value = FAKE_DATA
    return response


def test_integration_valid_data(fetcher, mocker, valid_response):
    """
    Verify MarketFetcher and validation pipeline with valid data.
    """
    mocker.patch("requests.get", return_value=valid_response)

    # Fetch data
    data = fetcher.fetch_intraday(SYMBOL, interval="1min")
    assert data is not None
    assert isinstance(data, list)

    # Validate and store data
    result = validate_and_store(
        records=data,
        schema_path="config/data_schema.yaml",
        out_path="data/validated_integration_test.jsonl"
    )
    assert result, "Integration pipeline failed to validate and store data"


def test_integration_empty_data(fetcher, mocker):
    """
    Verify how the pipeline handles empty API responses.
    """
    empty_response = Mock()
    empty_response.status_code = 200
    empty_response.json.return_value = {"Time Series (1min)": {}}
    mocker.patch("requests.get", return_value=empty_response)

    data = fetcher.fetch_intraday(SYMBOL, interval="1min")
    assert data == [], "The system should return an empty list for no data."


def test_integration_invalid_data(fetcher, mocker):
    """
    Verify how the pipeline handles invalid API responses.
    """
    invalid_response = Mock()
    invalid_response.status_code = 200
    invalid_response.json.return_value = {"foo": "bar"}
    mocker.patch("requests.get", return_value=invalid_response)

    data = fetcher.fetch_intraday(SYMBOL, interval="1min")
    assert data is None, "The system should return None for invalid data."


# def test_stress_multiple_symbols(fetcher, mocker, valid_response):
#     """
#     Simulate high load with multiple symbols fetched in quick succession.
#     """
#     symbols = ["AAPL", "GOOG", "MSFT", "TSLA", "AMZN", "NFLX", "META"]
#     mocker.patch("requests.get", return_value=valid_response)

#     for symbol in symbols:
#         data = fetcher.fetch_intraday(symbol, interval="1min")
#         assert data is not None, f"Failed to fetch data for {symbol}"
#         assert len(data) > 0, f"Expected data for symbol {symbol} but got none"