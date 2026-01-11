"""Generate sample trading signals JSONL for backtesting.

Uses a simple moving-average crossover on the synthetic market data to
produce buy/sell signals compatible with scripts/run_backtest.py.

Usage:
    python scripts/generate_sample_signals.py \
        --data data/market_data.jsonl \
        --output signals.jsonl \
        --fast 5 \
        --slow 20 \
        --qty 10
"""

import argparse
import json
from pathlib import Path
import pandas as pd


def load_market_data(path: str) -> pd.DataFrame:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    if not records:
        raise ValueError("No records found in market data file")
    df = pd.DataFrame(records)
    # Expect columns: timestamp, open, high, low, close, volume
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def generate_signals(df: pd.DataFrame, fast: int, slow: int, qty: float):
    if len(df) < slow:
        raise ValueError(f"Not enough data to compute slow MA={slow}")

    df = df.copy()
    df["fast_ma"] = df["close"].rolling(window=fast, min_periods=1).mean()
    df["slow_ma"] = df["close"].rolling(window=slow, min_periods=1).mean()

    signals = []
    current_position = 0  # Track to avoid double entries

    for i in range(1, len(df)):
        prev_fast = df.loc[i - 1, "fast_ma"]
        prev_slow = df.loc[i - 1, "slow_ma"]
        fast_ma = df.loc[i, "fast_ma"]
        slow_ma = df.loc[i, "slow_ma"]

        # Detect crossover
        crossed_up = prev_fast <= prev_slow and fast_ma > slow_ma
        crossed_down = prev_fast >= prev_slow and fast_ma < slow_ma

        if crossed_up and current_position <= 0:
            side = "buy"
            signals.append(
                {
                    "timestamp": df.loc[i, "timestamp"].isoformat(),
                    "symbol": df.loc[i, "symbol"],
                    "price": float(df.loc[i, "close"]),
                    "qty": float(qty),
                    "side": side,
                    "signal": "ma_crossover_up",
                }
            )
            current_position += qty
        elif crossed_down and current_position >= 0:
            side = "sell"
            signals.append(
                {
                    "timestamp": df.loc[i, "timestamp"].isoformat(),
                    "symbol": df.loc[i, "symbol"],
                    "price": float(df.loc[i, "close"]),
                    "qty": float(qty),
                    "side": side,
                    "signal": "ma_crossover_down",
                }
            )
            current_position -= qty

    return signals


def main():
    parser = argparse.ArgumentParser(description="Generate sample signals for backtesting")
    parser.add_argument("--data", default="data/market_data.jsonl", help="Path to market data JSONL")
    parser.add_argument("--output", default="signals.jsonl", help="Output signals file (JSONL)")
    parser.add_argument("--strategy", choices=["intraday", "swing", "weekly", "monthly"], 
                       help="Use predefined strategy config (overrides --fast/--slow)")
    parser.add_argument("--fast", type=int, help="Fast MA window (default: 5 for manual, or from strategy)")
    parser.add_argument("--slow", type=int, help="Slow MA window (default: 20 for manual, or from strategy)")
    parser.add_argument("--qty", type=float, default=10.0, help="Order quantity per signal")
    args = parser.parse_args()

    # Load strategy config if specified
    if args.strategy:
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        from src.execution.strategy_config import load_strategy
        
        strategy = load_strategy(args.strategy)
        fast = strategy.ma_fast_period
        slow = strategy.ma_slow_period
        print(f"📊 Using '{strategy.name}' strategy")
        print(f"   Timeframe: {strategy.data_interval} bars")
        print(f"   MA periods: {fast} (fast) / {slow} (slow)")
    else:
        fast = args.fast if args.fast is not None else 5
        slow = args.slow if args.slow is not None else 20
        print(f"📊 Using manual MA periods: {fast} (fast) / {slow} (slow)")

    df = load_market_data(args.data)
    signals = generate_signals(df, fast, slow, args.qty)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for sig in signals:
            f.write(json.dumps(sig) + "\n")

    print(f"✓ Generated {len(signals)} signals")
    print(f"  Input data: {args.data}")
    print(f"  Output: {args.output}")
    print(f"  Strategy: MA crossover (fast={fast}, slow={slow}, qty={args.qty})")


if __name__ == "__main__":
    main()
