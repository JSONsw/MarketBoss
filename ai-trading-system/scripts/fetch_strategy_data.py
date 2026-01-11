"""Fetch market data for different trading strategies.

This script fetches market data with the appropriate interval and lookback
period for each strategy (intraday, swing, weekly, monthly).

Usage:
    # Fetch data for intraday strategy (5-minute bars)
    python scripts/fetch_strategy_data.py --strategy intraday --symbol SPY

    # Fetch data for swing strategy (1-hour bars)
    python scripts/fetch_strategy_data.py --strategy swing --symbol SPY

    # Fetch for multiple symbols
    python scripts/fetch_strategy_data.py --strategy weekly --symbol SPY,QQQ,IWM
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.data_pipeline.market_fetcher import MarketFetcher
from src.execution.strategy_config import StrategyManager
from src.monitoring.structured_logger import get_logger

logger = get_logger("fetch_strategy_data")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch market data for different trading strategies"
    )
    parser.add_argument(
        "--strategy",
        choices=["intraday", "swing", "weekly", "monthly"],
        required=True,
        help="Trading strategy to fetch data for"
    )
    parser.add_argument(
        "--symbol",
        default="SPY",
        help="Symbol(s) to fetch (comma-separated for multiple)"
    )
    parser.add_argument(
        "--output",
        default="data/market_data.jsonl",
        help="Output file path"
    )
    args = parser.parse_args()

    # Load strategy configuration
    manager = StrategyManager()
    strategy = manager.get_strategy(args.strategy)

    print(f"📊 Fetching data for '{strategy.name}' strategy")
    print(f"   Timeframe: {strategy.data_interval} bars")
    print(f"   Lookback: {strategy.lookback_days} days")
    print(f"   MA periods: {strategy.ma_fast_period}/{strategy.ma_slow_period}")

    # Parse symbols
    symbols = [s.strip() for s in args.symbol.split(",")]
    print(f"   Symbols: {', '.join(symbols)}")

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=strategy.lookback_days)

    # Fetch data for each symbol
    fetcher = MarketFetcher()
    all_records = []

    for symbol in symbols:
        print(f"\n   Fetching {symbol}...")
        records = fetcher.fetch_intraday(
            symbol=symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=strategy.data_interval
        )

        if records:
            print(f"   ✓ Fetched {len(records)} bars for {symbol}")
            all_records.extend(records)
        else:
            print(f"   ⚠️  No data returned for {symbol}")

    if not all_records:
        print("\n❌ No data fetched. Exiting.")
        return 1

    # Sort by timestamp
    all_records.sort(key=lambda x: x["timestamp"])

    # Write to JSONL
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record) + "\n")

    print(f"\n✅ Saved {len(all_records)} records to {args.output}")
    print(f"\n📌 Next steps:")
    print(f"   1. Generate signals:")
    print(f"      python scripts/generate_sample_signals.py \\")
    print(f"        --strategy {args.strategy} \\")
    print(f"        --data {args.output} \\")
    print(f"        --output data/signals.jsonl")
    print(f"\n   2. Start trading:")
    print(f"      streamlit run dashboard/app.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
