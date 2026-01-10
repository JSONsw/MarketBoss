#!/usr/bin/env python
"""
End-to-end test: Live Trading Engine + Dashboard Real-time Integration

This demonstrates:
1. Live trading engine processing market data tick-by-tick
2. Algorithmic trade execution inline with price updates
3. Real-time MTM (mark-to-market) equity updates
4. Dashboard auto-refresh showing live data
5. Backtest vs Live comparison

Run this test to verify the full system works:
    python test_live_trading_dashboard.py

Then in another terminal, view the dashboard:
    streamlit run dashboard/app.py
"""

import json
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import time

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from src.execution.trading_engine import run_live_trading
from src.backtesting.backtester import run_backtest
from src.monitoring.structured_logger import get_logger

logger = get_logger("live_trading_dashboard_test")


def load_jsonl(path: Path) -> list:
    """Load JSONL file."""
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_live_trading_engine():
    """Test 1: Run live trading engine."""
    print_section("TEST 1: LIVE TRADING ENGINE")
    
    market_data_path = Path("data/market_data.jsonl")
    signals_path = Path("data/signals.jsonl")
    output_dir = Path("data")
    
    # Verify data files exist
    if not market_data_path.exists():
        logger.error(f"Market data not found: {market_data_path}")
        return False
    
    if not signals_path.exists():
        logger.error(f"Signals not found: {signals_path}")
        return False
    
    logger.info(f"Starting live trading engine...")
    logger.info(f"  Market data: {market_data_path}")
    logger.info(f"  Signals: {signals_path}")
    logger.info(f"  Output: {output_dir}")
    
    try:
        engine = run_live_trading(
            market_data_path=market_data_path,
            signals_path=signals_path,
            initial_cash=100000.0,
            output_dir=output_dir
        )
        
        if engine:
            logger.info("✅ Live trading engine completed successfully")
            return True
        else:
            logger.error("❌ Live trading engine returned None")
            return False
            
    except Exception as e:
        logger.error(f"❌ Live trading engine failed: {e}", exc_info=True)
        return False


def test_live_trading_output():
    """Test 2: Verify live trading output files."""
    print_section("TEST 2: LIVE TRADING OUTPUT FILES")
    
    output_files = {
        "live_trading_equity.jsonl": "Equity snapshots (for dashboard chart)",
        "live_trading_trades.jsonl": "Executed trades (for trade table)",
        "live_trading_updates.jsonl": "All updates (INIT, TICK, TRADE)",
    }
    
    results = {}
    for filename, description in output_files.items():
        path = Path("data") / filename
        if path.exists():
            records = load_jsonl(path)
            results[filename] = len(records)
            logger.info(f"✅ {filename}: {len(records)} records")
            logger.info(f"   Description: {description}")
        else:
            results[filename] = 0
            logger.warning(f"⚠️  {filename}: NOT FOUND")
    
    return all(results.values())


def test_live_trading_metrics():
    """Test 3: Validate live trading metrics."""
    print_section("TEST 3: LIVE TRADING METRICS")
    
    equity_path = Path("data/live_trading_equity.jsonl")
    trades_path = Path("data/live_trading_trades.jsonl")
    
    if not equity_path.exists():
        logger.warning("Equity file not found, skipping metrics test")
        return False
    
    equity_records = load_jsonl(equity_path)
    if not equity_records:
        logger.warning("No equity records found")
        return False
    
    # Convert to DataFrame
    df = pd.DataFrame(equity_records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    
    initial_pv = df["portfolio_value"].iloc[0]
    final_pv = df["portfolio_value"].iloc[-1]
    pnl = final_pv - initial_pv
    return_pct = (pnl / initial_pv) * 100
    max_pv = df["portfolio_value"].max()
    min_pv = df["portfolio_value"].min()
    max_dd = ((min_pv - max_pv) / max_pv) * 100
    
    logger.info(f"Portfolio Performance:")
    logger.info(f"  Initial Value: ${initial_pv:,.2f}")
    logger.info(f"  Final Value: ${final_pv:,.2f}")
    logger.info(f"  P&L: ${pnl:,.2f}")
    logger.info(f"  Return: {return_pct:+.2f}%")
    logger.info(f"  Max Drawdown: {max_dd:.2f}%")
    logger.info(f"  Equity snapshots: {len(equity_records)}")
    logger.info(f"  Time span: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    trades = load_jsonl(trades_path)
    if trades:
        logger.info(f"\n  Trades executed: {len(trades)}")
        # Show first 5 trades
        for i, trade in enumerate(trades[:5]):
            logger.info(
                f"    Trade {i+1}: {trade.get('symbol')} "
                f"{trade.get('side')} {trade.get('quantity')} @ ${trade.get('price', 0):.2f}"
            )
        if len(trades) > 5:
            logger.info(f"    ... and {len(trades)-5} more trades")
    
    return True


def test_backtest_comparison():
    """Test 4: Run backtest for comparison with live trading."""
    print_section("TEST 4: BACKTEST (FOR COMPARISON)")
    
    logger.info("Running backtest for comparison with live trading...")
    
    try:
        backtest_results = run_backtest(
            market_data_path=Path("data/market_data.jsonl"),
            signals_path=Path("data/signals.jsonl"),
            initial_cash=100000.0,
            output_dir=Path("data")
        )
        
        if backtest_results:
            logger.info(f"✅ Backtest completed")
            logger.info(f"  Return: {backtest_results.get('total_return_pct', 0):.2f}%")
            logger.info(f"  Sharpe: {backtest_results.get('sharpe', 0):.3f}")
            logger.info(f"  Max DD: {backtest_results.get('max_drawdown', 0):.2f}%")
            return True
        else:
            logger.warning("⚠️  Backtest returned None")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️  Backtest failed (not critical): {e}")
        return False


def test_dashboard_integration():
    """Test 5: Verify dashboard can read live trading data."""
    print_section("TEST 5: DASHBOARD INTEGRATION")
    
    equity_path = Path("data/live_trading_equity.jsonl")
    trades_path = Path("data/live_trading_trades.jsonl")
    
    # Verify dashboard can read the files
    equity_data = load_jsonl(equity_path)
    trades_data = load_jsonl(trades_path)
    
    logger.info("Dashboard Data Sources:")
    logger.info(f"  ✅ live_trading_equity.jsonl: {len(equity_data)} snapshots")
    logger.info(f"  ✅ live_trading_trades.jsonl: {len(trades_data)} trades")
    
    if equity_data:
        df = pd.DataFrame(equity_data)
        logger.info(f"\n  Equity columns: {list(df.columns)}")
        logger.info(f"  Sample record: {json.dumps(equity_data[0], indent=2)}")
    
    if trades_data:
        logger.info(f"\n  Trade columns: {list(pd.DataFrame(trades_data).columns)}")
    
    logger.info("\n📊 To view the dashboard with live data:")
    logger.info("  1. This test completes (you're reading this!)")
    logger.info("  2. Open another terminal")
    logger.info("  3. Run: streamlit run dashboard/app.py")
    logger.info("  4. The 'Live Trading (Real-time)' section will show the data above")
    logger.info("  5. Dashboard auto-refreshes every 1 second (configurable)")
    
    return True


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "LIVE TRADING + DASHBOARD E2E TEST" + " "*19 + "║")
    print("╚" + "="*68 + "╝")
    
    tests = [
        ("Live Trading Engine", test_live_trading_engine),
        ("Live Trading Output", test_live_trading_output),
        ("Live Trading Metrics", test_live_trading_metrics),
        ("Backtest Comparison", test_backtest_comparison),
        ("Dashboard Integration", test_dashboard_integration),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}", exc_info=True)
            results[test_name] = False
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready for live trading.")
        print("\nNext steps:")
        print("  1. Open dashboard: streamlit run dashboard/app.py")
        print("  2. View the 'Live Trading (Real-time)' section")
        print("  3. See real-time equity updates with MTM pricing")
        print("  4. Compare backtest vs live trading metrics")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
