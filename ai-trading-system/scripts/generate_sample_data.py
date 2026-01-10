"""Generate sample market data for testing the training pipeline.

Creates synthetic OHLCV data with realistic patterns for testing purposes.
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Parameters
n_days = 60
bars_per_day = 78  # 6.5 hours * 12 (5-min bars)
n_samples = n_days * bars_per_day

# Generate timestamps (5-minute bars during market hours: 9:30 AM - 4:00 PM ET)
start_date = datetime(2025, 10, 1, 9, 30)
timestamps = []

current_date = start_date
for day in range(n_days):
    for bar in range(bars_per_day):
        timestamps.append(current_date)
        current_date += timedelta(minutes=5)
    # Skip to next day's market open
    current_date = current_date.replace(hour=9, minute=30) + timedelta(days=1)

# Generate price data with realistic patterns
base_price = 100.0
prices = [base_price]
volatility = 0.02

for i in range(1, n_samples):
    # Random walk with slight upward drift
    drift = 0.0001
    shock = np.random.normal(0, volatility)
    new_price = prices[-1] * (1 + drift + shock)
    prices.append(new_price)

# Generate OHLCV data
data = []
for i, (ts, close) in enumerate(zip(timestamps, prices)):
    # Generate realistic open/high/low around close
    volatility_range = close * 0.005
    open_price = close + np.random.normal(0, volatility_range)
    high = max(open_price, close) + abs(np.random.normal(0, volatility_range))
    low = min(open_price, close) - abs(np.random.normal(0, volatility_range))
    
    # Generate volume (higher at market open/close)
    hour = ts.hour
    if hour == 9 or hour == 15:
        base_volume = 1000000
    else:
        base_volume = 500000
    volume = int(base_volume * np.random.lognormal(0, 0.5))
    
    record = {
        'symbol': 'SPY',
        'timestamp': ts.isoformat(),
        'open': round(open_price, 2),
        'high': round(high, 2),
        'low': round(low, 2),
        'close': round(close, 2),
        'volume': volume
    }
    data.append(record)

# Save to JSONL
output_dir = Path('data')
output_dir.mkdir(exist_ok=True)
output_file = output_dir / 'market_data.jsonl'

with open(output_file, 'w') as f:
    for record in data:
        f.write(json.dumps(record) + '\n')

print(f"✓ Generated {len(data)} sample market data records")
print(f"  Output: {output_file}")
print(f"  Symbol: SPY")
print(f"  Date range: {timestamps[0].date()} to {timestamps[-1].date()}")
print(f"  Price range: ${min(prices):.2f} to ${max(prices):.2f}")
print(f"\nYou can now run:")
print(f"  python scripts/run_training.py --data {output_file}")
