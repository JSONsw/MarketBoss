#!/usr/bin/env python3
"""Analyze live trading losses."""
import json
import pandas as pd

# Load trades
with open('data/live_trading_trades.jsonl', 'r') as f:
    trades = [json.loads(line) for line in f]

# Load equity snapshots
with open('data/live_trading_equity.jsonl', 'r') as f:
    equity_updates = [json.loads(line) for line in f]

# Get final equity
trades_df = pd.DataFrame(trades)
equity_df = pd.DataFrame(equity_updates)

if not equity_df.empty:
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'], errors='coerce')
    
    # Get first and last records
    first = equity_df.iloc[0]
    last = equity_df.iloc[-1]
    
    # Calculate P&L
    initial_pv = first.get('portfolio_value', first.get('mtm', 100000))
    final_pv = last.get('portfolio_value', last.get('mtm', initial_pv))
    pnl = final_pv - initial_pv
    
    print(f"Initial Portfolio Value: ${initial_pv:,.2f}")
    print(f"Final Portfolio Value:   ${final_pv:,.2f}")
    print(f"P&L:                     ${pnl:,.2f}")
    print(f"Return:                  {(pnl/initial_pv)*100:+.2f}%")
    print()
    print(f"Total Trades Executed:   {len(trades)}")
    
    if not trades_df.empty:
        trades_df['filled_price'] = trades_df['filled_price'].astype(float)
        buy_trades = trades_df[trades_df['side'] == 'BUY']
        sell_trades = trades_df[trades_df['side'] == 'SELL']
        
        print(f"BUY trades:              {len(buy_trades)}")
        print(f"SELL trades:             {len(sell_trades)}")
        print()
        
        if len(buy_trades) > 0:
            avg_buy_price = buy_trades['filled_price'].mean()
            print(f"Average BUY price:       ${avg_buy_price:,.2f}")
        
        if len(sell_trades) > 0:
            avg_sell_price = sell_trades['filled_price'].mean()
            print(f"Average SELL price:      ${avg_sell_price:,.2f}")
            
            if len(buy_trades) > 0:
                spread = avg_sell_price - avg_buy_price
                print(f"Average Spread:          ${spread:+.2f}")
                print(f"Spread %:                {(spread/avg_buy_price)*100:+.2f}%")

print("\n" + "="*60)
print("ROOT CAUSE ANALYSIS")
print("="*60)

# Analyze by showing first few trades
print("\nFirst 5 trades:")
print(trades_df[['timestamp', 'side', 'qty', 'filled_price']].head())

print("\nLast 5 trades:")
print(trades_df[['timestamp', 'side', 'qty', 'filled_price']].tail())
