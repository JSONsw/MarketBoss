import os
import requests
import time

from alpaca_trade_api.rest import REST, TimeFrame
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
from src.monitoring.structured_logger import get_logger

load_dotenv()

logger = get_logger()


class MarketFetcher:
    def __init__(self, api_key=None, api_secret=None, base_url="https://paper-api.alpaca.markets", rate_limit=5):
        """
        Initialize the market fetcher.

        :param api_key: Optional API key (overrides APCA_API_KEY_ID env var for testing)
        :param api_secret: Optional API secret (overrides APCA_API_SECRET_KEY env var for testing)
        :param base_url: Base URL of the market data provider API (default: paper trading).
        :param rate_limit: Number of allowed API calls per minute (default=5).
        """
        self.api_key = api_key or os.getenv("APCA_API_KEY_ID")
        self.api_secret = api_secret or os.getenv("APCA_API_SECRET_KEY")
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required. Please check your .env file or pass as parameters.")
        self.base_url = base_url
        self.client = REST(self.api_key, self.api_secret, base_url)
        self.rate_limit = rate_limit
        logger.info("MarketFetcher initialized", base_url=base_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_bars(self, symbol, timeframe, start, end):
        """Fetch bars from Alpaca API with retry logic."""
        return self.client.get_bars(symbol, timeframe, start=start, end=end).df

    def fetch_intraday(self, symbol, start, end, interval="1Min"):
        """
        Fetch intraday market data for a given symbol.

        :param symbol: Ticker symbol (e.g., 'AAPL').
        :param start: Start time in ISO8601 format (e.g., '2023-01-01T09:30:00Z').
        :param end: End time in ISO8601 format.
        :param interval: Granularity of data (e.g., '1Min', '5Min', '15Min', '1Hour', '1Day').
        :return: List of processed records or None on failure.
        """
        try:
            # Map interval to Alpaca TimeFrame
            # Note: Alpaca only supports these base timeframes; 5Min/15Min are derived
            interval_mapping = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame.Minute,  # Will fetch 1Min, can aggregate to 5Min later
                "15Min": TimeFrame.Minute,  # Will fetch 1Min, can aggregate to 15Min later
                "1Hour": TimeFrame.Hour,
                "1Day": TimeFrame.Day,
            }
            timeframe = interval_mapping.get(interval, TimeFrame.Minute)

            # Fetch historical bar data with retry
            bars = self._fetch_bars(symbol, timeframe, start, end)

            # Normalize data to match expected output format
            normalized_data = self._normalize_data(bars, symbol)
            logger.info("intraday_fetch_success", symbol=symbol, record_count=len(normalized_data))
            return normalized_data

        except ValueError as e:
            logger.error("intraday_fetch_validation_error", symbol=symbol, error=str(e))
            return None
        except Exception as e:
            logger.error("intraday_fetch_error", symbol=symbol, error=str(e))
            return None

    def _normalize_data(self, bars_df, symbol):
        """
        Normalize Alpaca's data to a pipeline-compatible format.

        :param bars_df: DataFrame of bar data.
        :param symbol: Ticker symbol.
        :return: List of normalized records.
        """
        normalized_records = []
        error_count = 0
        for timestamp, row in bars_df.iterrows():
            try:
                record = {
                    "timestamp": timestamp.isoformat(),
                    "symbol": symbol,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
                normalized_records.append(record)
            except (KeyError, ValueError, TypeError) as e:
                error_count += 1
                logger.warning(
                    "normalization_error",
                    symbol=symbol,
                    timestamp=str(timestamp),
                    error=str(e)
                )
        
        if error_count > 0:
            logger.info("normalize_completed_with_errors", symbol=symbol, error_count=error_count, total=len(bars_df))
        
        return normalized_records