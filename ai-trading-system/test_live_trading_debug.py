#!/usr/bin/env python
"""Test live trading with debug output."""
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from src.execution.trading_engine import LiveTradingEngine, MarketTick, load_market_data, load_signals
from src.monitoring.structured_logger import get_logger

logger = get_logger("live_trading_test")

# Load data
market_data = load_market_data(Path("data/market_data.jsonl"))
signals = load_signals(Path("data/signals.jsonl"))

print(f"Market data: {len(market_data)} points")
print(f"Signals: {len(signals)} signals")

# Sort
market_data = sorted(market_data, key=lambda x: x.get("timestamp", ""))
signals = sorted(signals, key=lambda x: x.get("timestamp", ""))

# Create engine
engine = LiveTradingEngine(initial_cash=100000.0)

# Process tick by tick
trades = 0
signal_idx = 0

print(f"\nFirst signal: {signals[0]}")
print(f"First market data: {market_data[0]}")
print(f"\nProcessing...\n")

for i, tick_data in enumerate(market_data):
    ts = tick_data.get("timestamp", "")
    symbol = tick_data.get("symbol", "SPY")
    close = tick_data.get("close", 0.0)
    
    # Process signals at or before this time
    while signal_idx < len(signals):
        signal = signals[signal_idx]
        signal_ts = signal.get("timestamp", "")
        
        if signal_ts <= ts:
            print(f"[{ts}] Processing signal #{signal_idx}: {signal['side'].upper()} {signal['qty']} {signal['symbol']} @ {close}")
            
            result = engine.process_signal(signal, close)
            if result:
                print(f"  [OK] Trade executed!")
                trades += 1
            else:
                print(f"  [FAIL] Trade failed (check buying power)")
                account = engine.account
                print(f"     Buying power: ${account.buying_power:.2f}, Cost: ${signal['qty'] * close:.2f}")
            
            signal_idx += 1
        else:
            break
    
    # Update prices
    tick = MarketTick(
        timestamp=ts,
        symbol=symbol,
        open=tick_data.get("open", 0.0),
        high=tick_data.get("high", 0.0),
        low=tick_data.get("low", 0.0),
        close=close,
        volume=tick_data.get("volume", 0)
    )
    engine.update_market_prices(tick)

print(f"\n{'='*70}")
print(f"Total trades executed: {trades}")
print(f"Final status: {engine.get_status()}")
