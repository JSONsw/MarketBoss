#!/usr/bin/env python
"""Run the live trading engine with real-time market data and profit optimization.

This runs the trading engine in real-time, processing market data tick-by-tick
and executing trades algorithmically as signals arrive. Includes profit optimization:
- Signal confidence filtering (skip low-confidence signals)
- Slippage buffer (only trade with minimum expected edge)
- Dynamic position sizing (risk-based share quantities)
- Trade frequency limits (prevent over-trading)

Usage:
    # Run with default paths (optimized for profit)
    python scripts/run_live_trading.py
    
    # Custom paths with optimization parameters
    python scripts/run_live_trading.py --market-data data/market_data.jsonl --signals data/signals.jsonl --min-confidence 0.65 --min-profit-bp 3
    
    # Conservative mode (higher thresholds)
    python scripts/run_live_trading.py --min-confidence 0.75 --min-profit-bp 5 --risk-percent 0.5
    
    # Watch the dashboard in another terminal:
    # streamlit run dashboard/app.py
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.execution.trading_engine import run_live_trading
from src.monitoring.structured_logger import get_logger

logger = get_logger("live_trading_runner")


def main():
    parser = argparse.ArgumentParser(description="Run live trading engine with profit optimization")
    parser.add_argument(
        "--market-data",
        type=Path,
        default=Path("data/market_data.jsonl"),
        help="Path to market OHLCV data"
    )
    parser.add_argument(
        "--signals",
        type=Path,
        default=Path("data/signals.jsonl"),
        help="Path to trade signals"
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=100000.0,
        help="Starting capital"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for trading logs"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.60,
        help="Minimum signal confidence threshold (0-1). Default: 0.60 (60%)"
    )
    parser.add_argument(
        "--min-profit-bp",
        type=float,
        default=3.0,
        help="Minimum expected profit in basis points to take trade. Default: 3bp"
    )
    parser.add_argument(
        "--risk-percent",
        type=float,
        default=1.0,
        help="Risk per trade as percentage of portfolio. Default: 1.0%"
    )
    
    args = parser.parse_args()
    
    try:
        engine = run_live_trading(
            market_data_path=args.market_data,
            signals_path=args.signals,
            initial_cash=args.initial_cash,
            output_dir=args.output_dir,
            min_confidence=args.min_confidence,
            min_profit_bp=args.min_profit_bp,
            risk_percent=args.risk_percent
        )
        
        if engine:
            return 0
        return 1
    
    except Exception as e:
        logger.error("Live trading failed", extra={"error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
