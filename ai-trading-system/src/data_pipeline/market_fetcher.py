"""Market data fetcher using Yahoo Finance.

This module provides market data fetching capabilities using yfinance,
replacing the previous Alpaca API integration. Yahoo Finance is free,
requires no API credentials, and provides reliable historical and 
real-time market data.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

from dotenv import load_dotenv
from src.monitoring.structured_logger import get_logger

load_dotenv()

logger = get_logger()


class MarketFetcher:
    """Fetch market data using Yahoo Finance API (free, no credentials required)."""
    
    def __init__(self, api_key=None, api_secret=None, base_url=None, rate_limit=5):
        """
        Initialize the market fetcher with Yahoo Finance backend.

        :param api_key: Deprecated - Yahoo Finance doesn't require API keys
        :param api_secret: Deprecated - Yahoo Finance doesn't require API secrets
        :param base_url: Deprecated - Yahoo Finance uses its own endpoints
        :param rate_limit: Number of allowed API calls per minute (default=5).
        
        Note: api_key, api_secret, and base_url parameters are kept for backward
        compatibility but are ignored. Yahoo Finance is free and requires no credentials.
        """
        if yf is None:
            raise ImportError("yfinance is required. Install with: pip install yfinance")
        
        self.rate_limit = rate_limit
        self.base_url = "Yahoo Finance (free API)"
        logger.info("MarketFetcher initialized", backend="Yahoo Finance", credentials_required=False)

    def fetch_intraday(self, symbol: str, start: str, end: str, interval: str = "1Min") -> Optional[List[Dict]]:
        """
        Fetch intraday market data for a given symbol using Yahoo Finance.

        :param symbol: Ticker symbol (e.g., 'AAPL', 'SPY').
        :param start: Start time in ISO8601 format (e.g., '2023-01-01T09:30:00').
        :param end: End time in ISO8601 format.
        :param interval: Granularity of data ('1m', '2m', '5m', '15m', '30m', '60m', '1h', '1d').
        :return: List of normalized records or None on failure.
        
        Supported intervals:
        - Intraday: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h
        - Daily and above: 1d, 5d, 1wk, 1mo, 3mo
        
        Note: Yahoo Finance has data limits:
        - 1m data: max 7 days
        - 5m data: max 60 days
        - 1h data: max 730 days
        """
        try:
            # Normalize interval format (convert from Alpaca format if needed)
            interval_mapping = {
                "1Min": "1m",
                "5Min": "5m",
                "15Min": "15m",
                "1Hour": "1h",
                "1Day": "1d",
                "1min": "1m",
                "5min": "5m",
                "15min": "15m",
                "1hour": "1h",
                "1day": "1d",
            }
            yf_interval = interval_mapping.get(interval, interval)
            
            # Parse start/end dates
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
            
            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_dt, end=end_dt, interval=yf_interval)
            
            if df.empty:
                logger.warning("no_data_returned", symbol=symbol, start=start, end=end, interval=yf_interval)
                return None

            # Normalize data to match expected output format
            normalized_data = self._normalize_data(df, symbol)
            logger.info("intraday_fetch_success", symbol=symbol, record_count=len(normalized_data), interval=yf_interval)
            return normalized_data

        except ValueError as e:
            logger.error("intraday_fetch_validation_error", symbol=symbol, error=str(e))
            return None
        except Exception as e:
            logger.error("intraday_fetch_error", symbol=symbol, error=str(e), exc_info=True)
            return None

    def _normalize_data(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """
        Normalize Yahoo Finance data to pipeline-compatible format.

        :param df: DataFrame from yfinance with OHLCV data
        :param symbol: Ticker symbol
        :return: List of normalized records
        """
        # Rename columns to lowercase if needed
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        normalized_records = []
        error_count = 0
        
        for timestamp, row in df.iterrows():
            try:
                record = {
                    "timestamp": timestamp.isoformat(),
                    "symbol": symbol,
                    "open": float(row["open"]) if pd.notna(row["open"]) else 0.0,
                    "high": float(row["high"]) if pd.notna(row["high"]) else 0.0,
                    "low": float(row["low"]) if pd.notna(row["low"]) else 0.0,
                    "close": float(row["close"]) if pd.notna(row["close"]) else 0.0,
                    "volume": int(row["volume"]) if pd.notna(row["volume"]) else 0,
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
            logger.info("normalize_completed_with_errors", symbol=symbol, error_count=error_count, total=len(df))
        
        return normalized_records