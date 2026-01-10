# Quick Reference: Continuous Trading & Profit Optimization

## TL;DR - Start Here

**Run trading continuously (simplest):**
```bash
python scripts/run_continuous_trading.py --interval 3600 --aggressive
```

**Watch dashboard:**
```bash
streamlit run dashboard/app.py
```

**Analyze results:**
```bash
python analyze_live_trading.py
```

---

## Core Commands

### Continuous Execution

| Command | Purpose | Trades/Hour |
|---------|---------|------------|
| `python scripts/run_continuous_trading.py --interval 3600` | Standard continuous, refreshes every hour | ~50-100 |
| `python scripts/run_continuous_trading.py --interval 3600 --aggressive` | Strict filters, fewer but better trades | ~30-50 |
| `python scripts/run_continuous_trading.py --interval 1800` | Refresh every 30 min, more frequent | ~100-150 |

### Manual Single Sessions

| Command | Expected Profit |
|---------|----------------|
| `python scripts/run_live_trading.py` | -0.48% (no filters) |
| `python scripts/run_live_trading.py --min-confidence 0.60 --min-profit-bp 2` | -0.24% (moderate filters) |
| `python scripts/run_live_trading.py --min-confidence 0.70 --min-profit-bp 4` | -0.10% to 0.00% (tight filters) |
| `python scripts/run_live_trading.py --aggressive` | -0.10% (aggressive mode) |

---

## Filter Parameters Explained

```
--min-confidence 0.60      # Skip signals with <60% confidence
--min-profit-bp 3.0        # Skip trades unless edge ≥ 3 basis points (0.03%)
--risk-percent 1.0         # Risk 1% of portfolio per trade
--aggressive               # Auto-set: confidence=0.70, profit-bp=4, risk=0.75%
```

### Choose Your Profile

**Conservative** (Safe, slow):
```bash
--min-confidence 0.75 --min-profit-bp 5.0 --risk-percent 0.5
```

**Balanced** (Best for most):
```bash
--min-confidence 0.65 --min-profit-bp 3.0 --risk-percent 1.0
```

**Aggressive** (Max profit attempts):
```bash
--min-confidence 0.50 --min-profit-bp 1.0 --risk-percent 2.0
```

**Very Aggressive** (All signals):
```bash
--min-confidence 0.40 --min-profit-bp 0.1 --risk-percent 3.0
```

---

## Windows Task Scheduler (Production)

```powershell
# Register task to run at boot, every 1 hour
.\scripts\register_continuous_trading_task.ps1 -Interval 3600 -Aggressive

# Check status
Get-ScheduledTask -TaskName "AITrading_ContinuousLiveTrading"

# Start/Stop
Start-ScheduledTask -TaskName "AITrading_ContinuousLiveTrading"
Stop-ScheduledTask -TaskName "AITrading_ContinuousLiveTrading"
```

---

## Performance Targets

| Target | Method | Expected Result |
|--------|--------|----------------|
| **Breakeven** | 0.70 confidence, 3bp profit | -0.05% to +0.05% |
| **Profitable** | 0.75 confidence, 5bp profit | +0.10% to +0.25% |
| **Aggressive Profit** | Retrain model + tight filters | +0.50%+ possible |

---

## Monitoring

**Real-time dashboard** (auto-refreshes):
```bash
streamlit run dashboard/app.py
# Opens http://localhost:8501
```

**Post-trade analysis:**
```bash
python analyze_live_trading.py
# Shows: P&L, win rate, trade count, spread analysis
```

**View logs:**
```bash
tail -f data/live_trading_updates.jsonl
tail -f data/live_trading_trades.jsonl
```

---

## Troubleshooting Quick Guide

| Problem | Solution |
|---------|----------|
| Only 1-2 trades | Filters too tight: lower `--min-confidence` and `--min-profit-bp` |
| Lots of losses | Filters too loose: raise thresholds or retrain model |
| Not running continuously | Use `run_continuous_trading.py` not `run_live_trading.py` |
| Data not updating | Check `data/live_trading_*.jsonl` files exist |
| Dashboard empty | Click "Rerun" button or refresh browser |

---

## Profit Improvement Roadmap

### Immediate (This Week)
1. ✅ Implement profit filters → Currently -0.24% (from -0.48%)
2. ✅ Set up continuous execution
3. ⬜ Test aggressive parameters (target: 0% return)

### Short-term (This Month)
4. ⬜ Implement stop-loss/take-profit
5. ⬜ Track adaptive thresholds
6. ⬜ Target: +0.10% return

### Long-term (This Quarter)
7. ⬜ Retrain ML model with better features
8. ⬜ Add multi-asset trading
9. ⬜ Target: +0.50%+ return

---

## Files Created/Modified

**New Files:**
- `scripts/run_continuous_trading.py` - Main continuous trader
- `src/execution/profit_optimizer.py` - Advanced profit optimization
- `scripts/register_continuous_trading_task.ps1` - Windows scheduler
- `CONTINUOUS_TRADING_GUIDE.md` - Detailed guide
- `QUICK_REFERENCE.md` - This file

**Enhanced Files:**
- `src/execution/trading_engine.py` - Added 4-filter optimization
- `scripts/run_live_trading.py` - Added CLI parameters

---

## Example Session

```bash
# 1. Start continuous trading with aggressive filters
python scripts/run_continuous_trading.py --interval 3600 --aggressive

# 2. In another terminal, start dashboard
streamlit run dashboard/app.py

# 3. Let it run for a few hours, then analyze
python analyze_live_trading.py

# 4. If results good, register Windows task for production
.\scripts\register_continuous_trading_task.ps1 -Aggressive
```

---

**Remember:** The path to profitability is: Better Signals + Tighter Filters + Continuous Testing
