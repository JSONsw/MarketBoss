#!/usr/bin/env python
"""Debug signal-to-market-data matching."""
import json
from pathlib import Path
from collections import defaultdict

def load_jsonl(path):
    records = []
    if path.exists():
        with open(path) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records

# Load data
market_data = load_jsonl(Path("data/market_data.jsonl"))
signals = load_jsonl(Path("data/signals.jsonl"))

print(f"Market data points: {len(market_data)}")
print(f"Signals: {len(signals)}")

# Show sample data
print("\n=== First 5 Market Data Records ===")
for i, m in enumerate(market_data[:5]):
    print(f"{i}: {m['timestamp']} - {m['symbol']} @ {m['close']}")

print("\n=== First 5 Signal Records ===")
for i, s in enumerate(signals[:5]):
    print(f"{i}: {s['timestamp']} - {s['symbol']} {s['side']} {s['qty']}")

# Check for timestamp matches
market_timestamps = set(m['timestamp'] for m in market_data)
signal_timestamps = set(s['timestamp'] for s in signals)

print(f"\n=== Timestamp Matching ===")
print(f"Unique market timestamps: {len(market_timestamps)}")
print(f"Unique signal timestamps: {len(signal_timestamps)}")

# Find exact matches
exact_matches = market_timestamps & signal_timestamps
print(f"Exact timestamp matches: {len(exact_matches)}")

if exact_matches:
    print(f"Sample matches: {list(exact_matches)[:5]}")
else:
    print("NO EXACT MATCHES!")
    
    # Show gap analysis
    market_ts_sorted = sorted(market_timestamps)
    signal_ts_sorted = sorted(signal_timestamps)
    
    print(f"\nFirst market timestamp: {market_ts_sorted[0]}")
    print(f"Last market timestamp: {market_ts_sorted[-1]}")
    print(f"\nFirst signal timestamp: {signal_ts_sorted[0]}")
    print(f"Last signal timestamp: {signal_ts_sorted[-1]}")
    
    # Find nearest matches
    print("\n=== Nearest Timestamp Matches ===")
    for sig_ts in signal_ts_sorted[:3]:
        # Find closest market timestamp
        closest = min(market_ts_sorted, key=lambda x: abs((x > sig_ts) - (x <= sig_ts)))
        print(f"Signal {sig_ts} closest to market {closest}")
