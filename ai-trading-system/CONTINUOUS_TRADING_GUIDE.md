# Continuous Trading & Profit Optimization Guide

## Overview
This guide explains how to run your live trading system continuously and push toward profitability.

## Part 1: Running Continuously

### Option A: Simple Loop (Recommended for Development)

Run trading in a continuous loop that refreshes data every N seconds:

```bash
# Run with 1-hour refresh intervals (3600 seconds)
python scripts/run_continuous_trading.py --interval 3600

# Run with 30-minute intervals
python scripts/run_continuous_trading.py --interval 1800

# Run with aggressive profit optimization
python scripts/run_continuous_trading.py --interval 3600 --aggressive

# Run for testing (max 5 sessions then stop)
python scripts/run_continuous_trading.py --interval 600 --max-iterations 5
```

**What happens in each session:**
1. Fetches fresh market data (OHLCV bars)
2. Generates/updates trade signals via ML model
3. Executes live trading with market data
4. Logs all trades and performance metrics
5. Waits for next interval, then repeats

### Option B: Windows Scheduled Task (Production)

For true continuous operation on Windows, register as a scheduled task:

```powershell
# Run PowerShell as Administrator, then:
cd "C:\Users\Jason\Trade\MarketBoss\ai-trading-system"
.\scripts\register_continuous_trading_task.ps1 -Interval 3600 -Aggressive
```

This will:
- Start automatically when Windows boots
- Run trading session every hour
- Continue indefinitely
- Log all output to Windows Event Log

**Manage the task:**
```powershell
# Check status
Get-ScheduledTask -TaskName "AITrading_ContinuousLiveTrading"

# Manually start
Start-ScheduledTask -TaskName "AITrading_ContinuousLiveTrading"

# Stop
Stop-ScheduledTask -TaskName "AITrading_ContinuousLiveTrading"

# View task log
Get-ScheduledTaskInfo -TaskName "AITrading_ContinuousLiveTrading"
```

### Option C: Python Scheduler (Cross-platform)

For a more sophisticated Python-based scheduler:

```python
import schedule
import time
from scripts.run_continuous_trading import ContinuousTrader

trader = ContinuousTrader(
    interval_seconds=3600,
    aggressive=True
)

# This would run the trader loop continuously
trader.run()
```

---

## Part 2: Pushing Toward Profitability

### Current Performance
| Metric | Before Optimization | After Optimization |
|--------|---------------------|-------------------|
| Return | -0.48% | -0.24% |
| Loss | -$484.21 | -$237.53 |
| Trades | 629 | 282 |

### Strategy 1: Tighter Profit Filters

The most direct way to improve profits is to reject trades that don't meet minimum profit thresholds:

```bash
# Conservative: only take trades with 4bp+ profit potential
python scripts/run_live_trading.py --min-profit-bp 4.0 --min-confidence 0.65

# Very aggressive: 5bp minimum profit
python scripts/run_live_trading.py --min-profit-bp 5.0 --min-confidence 0.70

# Use the --aggressive flag (auto-applies: 0.70 confidence, 4bp profit, 0.75% risk)
python scripts/run_live_trading.py --aggressive
```

**Parameter meanings:**
- `--min-confidence 0.65`: Skip signals with <65% confidence
- `--min-profit-bp 4.0`: Skip signals with <4bp expected profit (0.04% edge)
- `--risk-percent 0.75`: Risk only 0.75% of portfolio per trade

### Strategy 2: Adaptive Profit Thresholds

The system now includes `ProfitOptimizer` that automatically adjusts thresholds based on recent trading performance:

```python
from src.execution.profit_optimizer import ProfitOptimizer

optimizer = ProfitOptimizer(lookback_trades=100)

# After trading, log results
for trade in completed_trades:
    optimizer.record_trade(
        symbol=trade['symbol'],
        side=trade['side'],
        qty=trade['qty'],
        price=trade['price'],
        pnl=trade['pnl']
    )

# Get adaptive thresholds based on recent performance
thresholds = optimizer.calculate_adaptive_thresholds()
print(f"Current confidence threshold: {thresholds['confidence_threshold']}")
print(f"Current profit BP threshold: {thresholds['profit_bp_threshold']}")
print(f"Recent win rate: {thresholds['win_rate']:.1%}")
```

**How it works:**
- If win rate < 45%: Tighten filters significantly (↑ 0.15 confidence, ↑ 3bp profit)
- If win rate < 50%: Moderate tightening (↑ 0.10 confidence, ↑ 2bp profit)  
- If win rate < 55%: Light tightening (↑ 0.05 confidence, ↑ 1bp profit)
- If win rate ≥ 55%: Use base thresholds (0.60 confidence, 3bp profit)

### Strategy 3: Stop-Loss & Take-Profit Targets

Every position gets automated exit rules:

```python
from src.execution.profit_optimizer import ProfitOptimizer

optimizer = ProfitOptimizer()

# For each opened position, calculate exit prices
stop_loss, take_profit = optimizer.calculate_position_stops(
    symbol='SPY',
    side='BUY',
    entry_price=450.00,
    qty=10,
    risk_percent=2.0,        # Max 2% loss per trade
    profit_target_bp=5.0     # Target 5bp profit
)

print(f"Entry: $450.00")
print(f"Stop Loss: ${stop_loss:.2f}")
print(f"Take Profit: ${take_profit:.2f}")
```

This ensures:
- Losses are capped at 2% per trade
- Profits are locked in at target levels
- No position runs away into large losses

### Strategy 4: Improve Signal Quality

The root cause of losses is signal quality (negative spread = buying high, selling low). Long-term improvement requires better ML model:

```bash
# Retrain model with more data/features
python scripts/run_training.py --epochs 50 --cv-folds 5

# Generate signals with improved model
python -c "
from src.models.model import XGBoostModel
model = XGBoostModel()
model.generate_signals('data/market_data.jsonl', 'data/signals.jsonl')
"

# Test improved signals
python scripts/run_live_trading.py --min-confidence 0.50 --min-profit-bp 1.0
```

---

## Part 3: Monitoring & Dashboard

While trading continuously, monitor performance in real-time:

```bash
# In a separate terminal, run the dashboard
streamlit run dashboard/app.py
```

This shows:
- Live P&L and equity curve
- Active positions and trades
- Win rate and performance metrics
- Signal confidence distribution
- Recent trade details

---

## Part 4: Testing Strategy Changes

To test a new strategy without risking capital:

```bash
# Test with limited trades first
python scripts/run_live_trading.py \
    --min-confidence 0.70 \
    --min-profit-bp 5.0 \
    --risk-percent 0.5

# Then analyze the results
python analyze_live_trading.py

# Compare to baseline
# Baseline: -0.48% loss on 629 trades
# New: ? on X trades
```

---

## Part 5: Configuration Recommendations

### Conservative (Lower risk, fewer trades)
```bash
python scripts/run_continuous_trading.py \
    --interval 1800 \
    --min-confidence 0.75 \
    --min-profit-bp 5.0 \
    --risk-percent 0.5
```
- ~100 trades per session
- Expected: -0.10% to 0.00% return

### Balanced (Moderate risk, many trades)
```bash
python scripts/run_continuous_trading.py \
    --interval 1800 \
    --min-confidence 0.65 \
    --min-profit-bp 3.0 \
    --risk-percent 1.0
```
- ~200 trades per session
- Expected: -0.20% to +0.10% return

### Aggressive (Higher risk, all signals)
```bash
python scripts/run_continuous_trading.py \
    --interval 1800 \
    --min-confidence 0.50 \
    --min-profit-bp 1.0 \
    --risk-percent 2.0 \
    --aggressive
```
- ~250+ trades per session
- Expected: -0.30% to +0.20% return

---

## Part 6: Troubleshooting

**"Only a few trades executed"**
- Filters are too tight
- Try: `--min-confidence 0.50 --min-profit-bp 1.0`

**"Too many losses"**
- Signals are poor quality or market is choppy
- Try: `--min-confidence 0.70 --min-profit-bp 5.0`
- Or retrain model with more data

**"System not running continuously"**
- Use `run_continuous_trading.py` instead of `run_live_trading.py`
- For Windows scheduled task, check Event Viewer logs

**"Dashboard not showing data"**
- Make sure trading is running (check `data/live_trading_*.jsonl` files)
- Refresh browser with Ctrl+Shift+R

---

## Next Steps

1. **Start simple**: `python scripts/run_continuous_trading.py --interval 3600 --aggressive`
2. **Monitor dashboard**: `streamlit run dashboard/app.py`
3. **Analyze results**: `python analyze_live_trading.py`
4. **Tune parameters**: Adjust confidence, profit-bp, risk-percent based on results
5. **Improve signals**: Retrain model if win rate stays < 50%
6. **Production**: Use Windows scheduled task for true continuous operation

Good luck! 📈
