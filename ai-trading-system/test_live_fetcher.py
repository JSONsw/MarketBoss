#!/usr/bin/env python
"""Test live market data fetching."""

from src.data_pipeline.market_fetcher import MarketFetcher

print("=" * 60)
print("Testing Live Market Fetcher Functionality")
print("=" * 60)

try:
    fetcher = MarketFetcher()
    print("\n[OK] MarketFetcher initialized")
    
    # Test fetching intraday data
    print("\nAttempting to fetch intraday data for AAPL (1-minute bars)...")
    data = fetcher.fetch_intraday(
        symbol="AAPL",
        start="2025-01-08T15:00:00Z",
        end="2025-01-08T16:00:00Z",
        interval="1Min"
    )
    
    if data:
        print(f"\n[OK] Successfully fetched {len(data)} records")
        print("\nSample record:")
        if len(data) > 0:
            record = data[0]
            print(f"  Timestamp: {record.get('timestamp')}")
            print(f"  Symbol:    {record.get('symbol')}")
            print(f"  Open:      ${record.get('open'):.2f}")
            print(f"  High:      ${record.get('high'):.2f}")
            print(f"  Low:       ${record.get('low'):.2f}")
            print(f"  Close:     ${record.get('close'):.2f}")
            print(f"  Volume:    {record.get('volume')}")
        print("\n[SUCCESS] LIVE MARKET FETCHER WORKS - DATA RETRIEVED")
    else:
        print("\n[WARN] No data returned (possible API rate limit or invalid parameters)")
        print("Note: Paper trading API may have limited data availability")
        
except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nPossible causes:")
    print("  - Invalid API credentials")
    print("  - Network connectivity issue")
    print("  - Alpaca API service down")
    print("  - Rate limit exceeded")

print("=" * 60)
