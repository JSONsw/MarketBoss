"""Run a backtest using the backtesting engine."""

import argparse
import os
import sys
import json
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backtesting.backtester import run_backtest_mtm
from src.backtesting.metrics import calculate_sharpe, calculate_max_drawdown
from src.monitoring.structured_logger import get_logger

logger = get_logger()


def load_signals(signals_path: str):
    """Load trading signals from JSONL file."""
    signals = []
    with open(signals_path, 'r', encoding='utf-8') as f:
        for line in f:
            signals.append(json.loads(line))
    return signals


def main():
    parser = argparse.ArgumentParser(description='Run backtest on trading signals')
    parser.add_argument('--signals', type=str, required=True, help='Path to signals file (JSONL)')
    parser.add_argument('--slippage-bp', type=float, default=5.0, help='Slippage in basis points')
    parser.add_argument('--commission-pct', type=float, default=0.001, help='Commission as percentage')
    parser.add_argument('--fixed-fee', type=float, default=0.0, help='Fixed fee per trade')
    parser.add_argument('--initial-cash', type=float, default=100000.0, help='Initial cash')
    parser.add_argument('--output', type=str, help='Output path for results (JSON)')
    
    args = parser.parse_args()
    
    logger.info("backtest_started", signals_path=args.signals)
    
    # Load signals
    print(f"Loading signals from {args.signals}...")
    signals = load_signals(args.signals)
    
    if not signals:
        print("Error: No signals found")
        sys.exit(1)
    
    print(f"Loaded {len(signals)} signals")
    
    # Extract market prices (use signal price as market price for simplicity)
    market_prices = [float(s.get('price', 0)) for s in signals]
    
    # Run backtest
    print(f"Running backtest with:")
    print(f"  Slippage: {args.slippage_bp} bps")
    print(f"  Commission: {args.commission_pct * 100:.3f}%")
    print(f"  Fixed Fee: ${args.fixed_fee}")
    print(f"  Initial Cash: ${args.initial_cash:,.2f}")
    
    results = run_backtest_mtm(
        signals=signals,
        market_prices=market_prices,
        slippage_bp=args.slippage_bp,
        commission_pct=args.commission_pct,
        fixed_fee=args.fixed_fee,
        initial_cash=args.initial_cash,
    )
    
    # Calculate metrics
    equity_curve = [args.initial_cash]
    for r in results:
        equity_curve.append(r.get('mtm', equity_curve[-1]))

    # Periodic PnL as differences in MTM
    returns = []
    for i in range(1, len(equity_curve)):
        returns.append(equity_curve[i] - equity_curve[i-1])
    total_pnl = equity_curve[-1] - equity_curve[0]
    
    # Get final position and cash from last result
    final_result = results[-1] if results else {}
    final_cash = final_result.get('cash', args.initial_cash)
    final_position = final_result.get('position', 0)
    final_equity = final_result.get('mtm', final_cash)
    
    total_return_pct = ((final_equity - args.initial_cash) / args.initial_cash) * 100
    
    # Calculate Sharpe ratio
    try:
        sharpe = calculate_sharpe(returns)
    except:
        sharpe = 0.0
    
    # Calculate max drawdown
    try:
        max_dd = calculate_max_drawdown(equity_curve)
    except:
        max_dd = 0.0
    
    # Count trades
    n_trades = len([r for r in results if r.get('executed_notional', 0) != 0])
    winning_trades = len([r for r in returns if r > 0])
    losing_trades = len([r for r in returns if r < 0])
    win_rate = (winning_trades / n_trades * 100) if n_trades > 0 else 0
    
    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"\nPerformance:")
    print(f"  Initial Capital:  ${args.initial_cash:,.2f}")
    print(f"  Final Equity:     ${final_equity:,.2f}")
    print(f"  Total P&L:        ${total_pnl:,.2f}")
    print(f"  Total Return:     {total_return_pct:.2f}%")
    print(f"  Sharpe Ratio:     {sharpe:.3f}")
    print(f"  Max Drawdown:     {max_dd:.2f}%")
    
    print(f"\nTrade Statistics:")
    print(f"  Total Trades:     {n_trades}")
    print(f"  Winning Trades:   {winning_trades}")
    print(f"  Losing Trades:    {losing_trades}")
    print(f"  Win Rate:         {win_rate:.1f}%")
    
    print(f"\nFinal Position:")
    print(f"  Cash:             ${final_cash:,.2f}")
    print(f"  Position:         {final_position:.0f} shares")
    print("=" * 60)
    
    # Save results if output path provided
    if args.output:
        output_data = {
            "backtest_params": {
                "signals_file": args.signals,
                "slippage_bp": args.slippage_bp,
                "commission_pct": args.commission_pct,
                "fixed_fee": args.fixed_fee,
                "initial_cash": args.initial_cash,
            },
            "metrics": {
                "total_pnl": total_pnl,
                "total_return_pct": total_return_pct,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "n_trades": n_trades,
                "win_rate": win_rate,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
            },
            "final_state": {
                "cash": final_cash,
                "position": final_position,
                "equity": final_equity,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to {args.output}")
    
    logger.info("backtest_completed", n_trades=n_trades, total_return=total_return_pct, sharpe=sharpe)


if __name__ == '__main__':
    main()
