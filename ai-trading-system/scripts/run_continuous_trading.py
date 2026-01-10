#!/usr/bin/env python
"""Run live trading continuously with periodic retraining and market data refresh.

This script runs the live trading system in a continuous loop:
1. Fetches fresh market data
2. Generates/refreshes trade signals via ML model
3. Executes live trading for the market session
4. Logs results and performance metrics
5. Repeats on a configurable schedule

Usage:
    # Run continuously with default settings (updates every 8 hours)
    python scripts/run_continuous_trading.py
    
    # Run with custom intervals and optimization parameters
    python scripts/run_continuous_trading.py --interval 3600 --min-profit-bp 4 --min-confidence 0.65
    
    # Run with aggressive profit optimization (tighter filters)
    python scripts/run_continuous_trading.py --interval 3600 --aggressive
"""

import argparse
import sys
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
import json
import yfinance as yf
import pandas as pd
import pytz

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.monitoring.structured_logger import get_logger
from src.execution.trading_engine import run_live_trading

logger = get_logger("continuous_trading")

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info("Shutdown signal received, finishing current iteration...")
    shutdown_requested = True


def is_market_open() -> bool:
    """Check if US stock market is currently open.
    
    Returns:
        True if market is open, False otherwise
    """
    import pytz
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    
    # Check if weekend
    if now_est.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check market hours (9:30 AM - 4:00 PM EST)
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now_est <= market_close


class ContinuousTrader:
    """Runs live trading in a continuous loop with periodic updates."""
    
    def __init__(
        self,
        symbol: str = "SPY",
        interval_seconds: int = 28800,  # 8 hours default
        market_data_path: Path = Path("data/market_data.jsonl"),
        signals_path: Path = Path("data/signals.jsonl"),
        min_confidence: float = 0.60,
        min_profit_bp: float = 3.0,
        risk_percent: float = 1.0,
        aggressive: bool = False,
        test_mode: bool = False,
    ):
        self.symbol = symbol
        self.interval = interval_seconds
        self.market_data_path = market_data_path
        self.signals_path = signals_path
        self.min_confidence = min_confidence
        self.min_profit_bp = min_profit_bp
        self.risk_percent = risk_percent
        self.aggressive = aggressive
        self.test_mode = test_mode
        self.run_count = 0
        
        # Aggressive mode: tighter filters for better profitability
        if aggressive:
            self.min_confidence = 0.70
            self.min_profit_bp = 4.0
            self.risk_percent = 0.75
            logger.info("Aggressive mode enabled - using stricter profit filters")
        
        # Test mode: bypass market hours check
        if test_mode:
            logger.info("TEST MODE ENABLED - Will trade outside market hours for testing")
        
        logger.info(
            "Continuous Trading initialized",
            extra={
                "symbol": self.symbol,
                "interval_seconds": interval_seconds,
                "min_confidence": self.min_confidence,
                "min_profit_bp": self.min_profit_bp,
                "risk_percent": self.risk_percent,
                "test_mode": self.test_mode,
            }
        )
    
    def get_current_market_price(self, symbol: str) -> Optional[float]:
        """Get the current real-time market price from Yahoo Finance with retry.
        
        Fetches the latest available price to ensure trades execute at
        current market levels, not stale historical data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Current market price or None if fetch fails after retries
        """
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol)
                # Get latest available data (1 minute interval)
                df = ticker.history(period="1d", interval="1m")
                if df.empty:
                    logger.warning(f"Could not fetch current price for {symbol} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                
                # Get the most recent close price
                current_price = float(df.iloc[-1]['Close'])
                logger.info(f"Current market price for {symbol}: ${current_price:.2f}")
                return current_price
                
            except Exception as e:
                logger.warning(f"Error fetching current price (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return None
        
        return None
    
    def refresh_data(self) -> bool:
        """Fetch fresh market data from Yahoo Finance and save to JSONL.
        
        Fetches 5-minute intraday data for the selected symbol with proper timezone handling.
        Filters to regular market hours (9:30 AM - 4:00 PM EST).
        Uses accurate real-time data from Yahoo Finance.
        """
        try:
            logger.info("Fetching fresh market data from Yahoo Finance")
            
            # Timezone handling
            est = pytz.timezone('US/Eastern')
            utc = pytz.UTC
            
            # Fetch last 7 days of 5-minute data (Yahoo Finance limit for 5m interval)
            # Add 1 day buffer to end_date to ensure we capture today's intraday data
            end_date = (datetime.now(tz=est) + timedelta(days=1)).date()
            start_date = end_date - timedelta(days=8)  # 7 days + 1 day buffer
            
            logger.info(f"Requesting data for {self.symbol} from {start_date} to {end_date} (EST)")
            
            ticker = yf.Ticker(self.symbol)
            # Fetch with prepost=False to exclude pre/post-market, auto_adjust=False for accurate prices
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval="5m",
                prepost=False,  # Exclude pre/post-market hours
                auto_adjust=False  # Use actual prices, not adjusted
            )
            
            if df.empty:
                logger.error("No data returned from Yahoo Finance")
                return False
            
            # Convert timezone from UTC to EST if needed
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert(est)
            
            # Filter to regular market hours only (9:30 AM - 4:00 PM EST)
            df['hour'] = df.index.hour
            df['minute'] = df.index.minute
            # Keep bars from 9:30 AM (09:30) to 3:55 PM (15:55) to ensure close time is included
            df = df[((df['hour'] == 9) & (df['minute'] >= 30)) | 
                     ((df['hour'] > 9) & (df['hour'] < 16))]
            df = df.drop(['hour', 'minute'], axis=1)
            
            if df.empty:
                logger.error("No data in regular market hours")
                return False
            
            logger.info(f"Filtered to {len(df)} bars in regular market hours (9:30 AM - 4:00 PM EST)")
            
            # Convert to JSONL format with accurate timestamps
            records = []
            for timestamp, row in df.iterrows():
                # Ensure timestamp is in EST and format as ISO string
                ts_est = timestamp.tz_convert(est) if timestamp.tz is not None else timestamp
                record = {
                    'symbol': self.symbol,
                    'timestamp': ts_est.isoformat(),  # ISO format with timezone info
                    'open': round(float(row['Open']), 2),
                    'high': round(float(row['High']), 2),
                    'low': round(float(row['Low']), 2),
                    'close': round(float(row['Close']), 2),
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0
                }
                records.append(record)
            
            # Save to JSONL file
            self.market_data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.market_data_path, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
            
            logger.info("Market data refreshed", extra={
                "records": len(records),
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d'),
                "timezone": "US/Eastern",
                "market_hours": "9:30 AM - 4:00 PM EST",
                "source": "Yahoo Finance (non-adjusted prices)",
                "symbol": self.symbol,
                "first_timestamp": records[0]['timestamp'] if records else 'N/A',
                "last_timestamp": records[-1]['timestamp'] if records else 'N/A'
            })
            
            # Validate signals file exists (signals are generated separately)
            if not self.signals_path.exists():
                logger.warning("Signals file not found - you may need to regenerate signals")
                # Continue anyway - run_live_trading will handle missing signals
            
            return True
            
        except Exception as e:
            logger.error("Market data refresh failed", extra={"error": str(e)})
            return False
    
    def run_trading_session(self) -> Dict[str, Any]:
        """Execute one live trading session with current market price."""
        try:
            # Check if market is open (skip check in test mode)
            if not self.test_mode and not is_market_open():
                logger.info("Market is closed, skipping trading session")
                return {"success": False, "reason": "market_closed"}
            
            if self.test_mode:
                logger.info("TEST MODE: Trading outside market hours for testing")
            
            logger.info(
                f"Starting trading session {self.run_count + 1}",
                extra={
                    "timestamp": datetime.now().isoformat(),
                    "min_confidence": self.min_confidence,
                    "min_profit_bp": self.min_profit_bp,
                }
            )
            
            # Fetch current market price for accurate trade execution
            current_price = self.get_current_market_price(self.symbol)
            if current_price is None:
                logger.error("Failed to fetch current market price after retries, aborting session")
                return {"success": False, "error": "price_fetch_failed"}
            
            # Run live trading with Path objects and current market price
            run_live_trading(
                market_data_path=self.market_data_path,
                signals_path=self.signals_path,
                min_confidence=self.min_confidence,
                min_profit_bp=self.min_profit_bp,
                risk_percent=self.risk_percent,
                current_price=current_price,
            )
            
            self.run_count += 1
            logger.info(f"Trading session {self.run_count} completed")
            
            return {"success": True, "session": self.run_count}
            
        except Exception as e:
            logger.error("Trading session failed", extra={"error": str(e)})
            return {"success": False, "error": str(e)}
    
    def run(self, max_iterations: int = None):
        """Run continuous trading loop with real-time market data updates.
        
        Refreshes market data frequently (every 5 minutes) to ensure trades use
        current market prices instead of stale cached data.
        
        Args:
            max_iterations: Max number of trading sessions (None = infinite)
        """
        global shutdown_requested
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Starting continuous trading loop", extra={"interval_seconds": self.interval})
        
        iteration = 0
        data_refresh_interval = 300  # Refresh market data every 5 minutes for real-time accuracy
        
        try:
            while not shutdown_requested:
                iteration += 1
                
                # Check iteration limit
                if max_iterations and iteration > max_iterations:
                    logger.info(f"Reached max iterations ({max_iterations}), stopping")
                    break
                
                # Always refresh market data before trading session for real-time accuracy
                # This ensures trades execute at current market prices, not stale cached data
                logger.info("Refreshing market data for real-time accuracy")
                if not self.refresh_data():
                    logger.warning("Data refresh failed, using existing data")
                
                # Run trading session
                self.run_trading_session()
                
                # Wait for next interval (check shutdown flag every second)
                next_run = datetime.now() + timedelta(seconds=self.interval)
                logger.info(
                    "Trading session complete, next run scheduled",
                    extra={
                        "next_run": next_run.isoformat(),
                        "wait_seconds": self.interval,
                    }
                )
                
                # Sleep in chunks to allow responsive shutdown
                for _ in range(self.interval):
                    if shutdown_requested:
                        break
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Continuous trading stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(
                "Unexpected error in trading loop",
                extra={"error": str(e)}
            )
        finally:
            logger.info("Continuous trading shutdown complete")
            # Cleanup: close any open resources
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Run live trading continuously with automatic data refresh"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="SPY",
        help="Stock ticker symbol to trade (default: SPY)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=28800,
        help="Time between trading sessions in seconds (default: 28800 = 8 hours)",
    )
    parser.add_argument(
        "--market-data",
        type=Path,
        default=Path("data/market_data.jsonl"),
        help="Path to market data file",
    )
    parser.add_argument(
        "--signals",
        type=Path,
        default=Path("data/signals.jsonl"),
        help="Path to signals file",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.60,
        help="Minimum signal confidence (0-1)",
    )
    parser.add_argument(
        "--min-profit-bp",
        type=float,
        default=3.0,
        help="Minimum expected profit in basis points",
    )
    parser.add_argument(
        "--risk-percent",
        type=float,
        default=1.0,
        help="Risk per trade as percentage of portfolio",
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Enable aggressive mode (stricter filters for better profits)",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Enable test mode (bypass market hours check for testing)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum trading sessions to run (None = infinite)",
    )
    
    args = parser.parse_args()
    
    trader = ContinuousTrader(
        symbol=args.symbol,
        interval_seconds=args.interval,
        market_data_path=args.market_data,
        signals_path=args.signals,
        min_confidence=args.min_confidence,
        min_profit_bp=args.min_profit_bp,
        risk_percent=args.risk_percent,
        aggressive=args.aggressive,
        test_mode=args.test_mode,
    )
    
    trader.run(max_iterations=args.max_iterations)


if __name__ == "__main__":
    main()
