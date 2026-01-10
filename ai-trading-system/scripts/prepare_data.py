"""Fetch, clean, and prepare market data for training.

This script:
1. Fetches historical market data from Alpaca
2. Cleans and validates the data
3. Saves to JSONL format for training

Usage:
    python scripts/prepare_data.py --symbols SPY AAPL --days 365 --output data/market_data.jsonl
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_pipeline.market_fetcher import MarketFetcher
from src.data_pipeline.clean_data import clean_data
from src.data_pipeline.store_data import save_to_jsonl
from src.monitoring.structured_logger import StructuredLogger


def main():
    parser = argparse.ArgumentParser(description='Prepare market data for training')
    parser.add_argument('--symbols', nargs='+', default=['SPY'], help='Stock symbols to fetch')
    parser.add_argument('--days', type=int, default=365, help='Number of days of historical data')
    parser.add_argument('--timeframe', default='5Min', choices=['1Min', '5Min', '15Min', '1Hour', '1Day'], 
                        help='Timeframe for bars')
    parser.add_argument('--output', default='data/market_data.jsonl', help='Output file path')
    
    args = parser.parse_args()
    
    logger = StructuredLogger('prepare_data')
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    logger.info(f"Fetching {args.days} days of {args.timeframe} data for {args.symbols}", 
                extra={'start_date': start_date.isoformat(), 'end_date': end_date.isoformat()})
    
    # Initialize fetcher
    fetcher = MarketFetcher()
    
    # Fetch data for each symbol
    all_data = []
    
    for symbol in args.symbols:
        logger.info(f"Fetching data for {symbol}")
        
        try:
            df = fetcher.fetch_intraday(
                symbol=symbol,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                timeframe=args.timeframe
            )
            
            if df is None or len(df) == 0:
                logger.warning(f"No data returned for {symbol}")
                continue
            
            logger.info(f"Fetched {len(df)} bars for {symbol}")
            
            # Clean the data
            df_clean = clean_data(df)
            logger.info(f"Cleaned data: {len(df_clean)} bars remaining")
            
            # Convert to list of dicts
            for _, row in df_clean.iterrows():
                record = {
                    'symbol': symbol,
                    'timestamp': row.name.isoformat() if hasattr(row.name, 'isoformat') else str(row.name),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume'])
                }
                all_data.append(record)
                
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            continue
    
    if not all_data:
        logger.error("No data was fetched")
        sys.exit(1)
    
    # Save to JSONL
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    save_to_jsonl(all_data, str(output_path))
    
    logger.info(f"Saved {len(all_data)} records to {args.output}")
    print(f"\n✓ Successfully prepared {len(all_data)} market data records")
    print(f"  Output: {args.output}")
    print(f"  Symbols: {', '.join(args.symbols)}")
    print(f"  Date range: {start_date.date()} to {end_date.date()}")


if __name__ == '__main__':
    main()
