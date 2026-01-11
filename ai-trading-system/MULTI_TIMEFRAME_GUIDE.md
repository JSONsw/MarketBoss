# Multi-Timeframe Trading Strategies

## Overview

The system now supports multiple trading timeframes beyond the default intraday strategy. You can configure the system to trade on:

- **Intraday** (default): 5-minute bars, same-day trading
- **Swing**: 1-hour bars, multi-day positions
- **Weekly**: Daily bars, weekly rebalancing
- **Monthly**: Daily bars, monthly rebalancing

Each strategy has optimized parameters for its timeframe, including MA periods, cooldown times, and risk settings.

## Quick Start

### 1. Choose Your Strategy

```bash
# Intraday trading (5-minute bars, fast moves)
python scripts/fetch_strategy_data.py --strategy intraday --symbol SPY

# Swing trading (1-hour bars, hold days)
python scripts/fetch_strategy_data.py --strategy swing --symbol SPY

# Weekly trading (daily bars, hold weeks)
python scripts/fetch_strategy_data.py --strategy weekly --symbol SPY

# Monthly trading (daily bars, hold months)
python scripts/fetch_strategy_data.py --strategy monthly --symbol SPY
```

### 2. Generate Signals for That Strategy

```bash
# Using strategy config (automatic MA periods)
python scripts/generate_sample_signals.py \
    --strategy swing \
    --data data/market_data.jsonl \
    --output data/signals.jsonl

# Or manual MA periods
python scripts/generate_sample_signals.py \
    --fast 10 \
    --slow 50 \
    --data data/market_data.jsonl \
    --output data/signals.jsonl
```

### 3. Start Trading

The dashboard will automatically use the strategy parameters when trading.

## Strategy Comparison

| Strategy | Data Interval | Lookback | MA Periods | Trade Frequency | Cooldown | Risk/Trade |
|----------|--------------|----------|------------|-----------------|----------|------------|
| **Intraday** | 5-minute | 7 days | 5/20 | 10-50/week | 5 min | 1.0% |
| **Swing** | 1-hour | 60 days | 10/50 | 2-10/week | 6 hours | 2.0% |
| **Weekly** | Daily | 180 days | 5/20 | 0-2/week | 1 week | 3.0% |
| **Monthly** | Daily | 365 days | 20/60 | 0-1/week | 1 month | 5.0% |

## Strategy Details

### Intraday Strategy

**Best for:** Day traders, active management, quick profits  
**Time commitment:** Monitor during market hours  
**Typical trade duration:** 5 minutes to 6 hours  
**Position exit:** All positions closed before market close

```yaml
Configuration:
  Data interval: 5m
  MA periods: 5 (fast) / 20 (slow)
  Cooldown: 5 minutes
  Min confidence: 60%
  Min profit target: 3 basis points
  Risk per trade: 1%
```

**Pros:**
- Quick feedback on strategy performance
- No overnight risk
- High trade frequency for testing

**Cons:**
- Requires active monitoring
- Higher transaction costs (more trades)
- More sensitive to noise

### Swing Trading Strategy

**Best for:** Part-time traders, medium-term trends  
**Time commitment:** Check once or twice daily  
**Typical trade duration:** 1 to 5 days  
**Position exit:** Can hold overnight

```yaml
Configuration:
  Data interval: 1h
  MA periods: 10 (fast) / 50 (slow)
  Cooldown: 6 hours
  Min confidence: 65%
  Min profit target: 10 basis points
  Risk per trade: 2%
```

**Pros:**
- Reduced noise vs. intraday
- Captures multi-day trends
- Less time intensive

**Cons:**
- Overnight gap risk
- Slower feedback
- Requires higher profit targets

### Weekly Strategy

**Best for:** Passive management, trend following  
**Time commitment:** Weekly review  
**Typical trade duration:** 1 week to 1 month  
**Position exit:** Long-term holds

```yaml
Configuration:
  Data interval: 1d (daily bars)
  MA periods: 5 (fast) / 20 (slow)
  Cooldown: 1 week
  Min confidence: 70%
  Min profit target: 25 basis points
  Risk per trade: 3%
```

**Pros:**
- Very low time commitment
- Captures weekly/monthly trends
- Low transaction costs

**Cons:**
- Very slow feedback
- Can miss short-term opportunities
- Higher drawdowns

### Monthly Strategy

**Best for:** Long-term investors, retirement accounts  
**Time commitment:** Monthly rebalancing  
**Typical trade duration:** 1 to 3 months  
**Position exit:** Very long-term

```yaml
Configuration:
  Data interval: 1d (daily bars)
  MA periods: 20 (fast) / 60 (slow)
  Cooldown: 1 month
  Min confidence: 75%
  Min profit target: 50 basis points
  Risk per trade: 5%
```

**Pros:**
- Minimal time commitment
- Captures long-term trends
- Lowest transaction costs
- Good for retirement/passive portfolios

**Cons:**
- Extremely slow feedback
- Can experience large drawdowns
- Miss medium-term opportunities

## Workflow Examples

### Example 1: Switch to Swing Trading

```bash
# Step 1: Fetch 60 days of hourly data
python scripts/fetch_strategy_data.py \
    --strategy swing \
    --symbol SPY \
    --output data/market_data_swing.jsonl

# Step 2: Generate swing signals (10/50 MA)
python scripts/generate_sample_signals.py \
    --strategy swing \
    --data data/market_data_swing.jsonl \
    --output data/signals_swing.jsonl

# Step 3: Backtest (optional)
python scripts/run_backtest.py \
    --signals data/signals_swing.jsonl \
    --market-data data/market_data_swing.jsonl

# Step 4: Start trading via dashboard
streamlit run dashboard/app.py
# In dashboard: use signals_swing.jsonl
```

### Example 2: Weekly Portfolio Rebalancing

```bash
# Fetch 6 months of daily data for portfolio
python scripts/fetch_strategy_data.py \
    --strategy weekly \
    --symbol SPY,QQQ,IWM,TLT,GLD \
    --output data/market_data_weekly.jsonl

# Generate signals
python scripts/generate_sample_signals.py \
    --strategy weekly \
    --data data/market_data_weekly.jsonl \
    --output data/signals_weekly.jsonl

# Review signals (should be ~1 signal per week per symbol)
tail -n 50 data/signals_weekly.jsonl
```

### Example 3: Test Multiple Strategies

```bash
# Fetch data for all strategies
for strategy in intraday swing weekly monthly; do
    python scripts/fetch_strategy_data.py \
        --strategy $strategy \
        --symbol SPY \
        --output data/market_data_$strategy.jsonl
    
    python scripts/generate_sample_signals.py \
        --strategy $strategy \
        --data data/market_data_$strategy.jsonl \
        --output data/signals_$strategy.jsonl
done

# Compare signal counts
wc -l data/signals_*.jsonl
```

## Configuration Files

### Strategy Config: `config/trading_strategies.yaml`

This file defines all strategy parameters. You can:

1. **Modify existing strategies:**
   ```yaml
   intraday:
     timeframe:
       ma_fast_period: 3  # Change from 5 to 3
       ma_slow_period: 15  # Change from 20 to 15
   ```

2. **Add custom strategies:**
   ```yaml
   strategies:
     custom_4h:
       name: "4-Hour Swing"
       timeframe:
         data_interval: "4h"
         lookback_days: 90
         ma_fast_period: 6
         ma_slow_period: 24
       execution:
         min_cooldown_minutes: 240  # 4 hours
   ```

3. **Change default:**
   ```yaml
   default_strategy: swing  # Change from 'intraday' to 'swing'
   ```

## Programmatic Usage

### In Python Scripts

```python
from src.execution.strategy_config import load_strategy

# Load a strategy
strategy = load_strategy("swing")

# Access parameters
print(f"Data interval: {strategy.data_interval}")  # "1h"
print(f"MA periods: {strategy.ma_fast_period}/{strategy.ma_slow_period}")  # 10/50
print(f"Cooldown: {strategy.min_cooldown_minutes} minutes")  # 360

# Use with trading engine
from src.execution.trading_engine import LiveTradingEngine

engine = LiveTradingEngine(
    initial_cash=100000,
    strategy=strategy  # Engine uses strategy's risk/confidence settings
)
```

### With Market Fetcher

```python
from src.data_pipeline.market_fetcher import MarketFetcher
from src.execution.strategy_config import load_strategy
from datetime import datetime, timedelta

# Load strategy
strategy = load_strategy("weekly")

# Calculate date range
end = datetime.now()
start = end - timedelta(days=strategy.lookback_days)

# Fetch data
fetcher = MarketFetcher()
data = fetcher.fetch_intraday(
    symbol="SPY",
    start=start.isoformat(),
    end=end.isoformat(),
    interval=strategy.data_interval  # Uses "1d" from strategy
)
```

## Data Requirements & Limits

Yahoo Finance has data availability limits:

| Interval | Max History | Best For Strategy |
|----------|-------------|-------------------|
| 1m | 7 days | Not recommended (too granular) |
| 5m | 60 days | **Intraday** (7 days sufficient) |
| 1h | 730 days | **Swing** (60 days sufficient) |
| 1d | Unlimited | **Weekly, Monthly** |
| 1wk | Unlimited | Alternative for Monthly |

**Important:** The system automatically handles Yahoo Finance's interval format:
- `"5m"` → 5-minute bars
- `"1h"` → 1-hour bars
- `"1d"` → Daily bars
- `"1wk"` → Weekly bars

## Performance Expectations

Based on MA crossover strategy:

| Strategy | Expected Trades/Week | Win Rate | Avg Return/Trade | Annual Return (Est.) |
|----------|---------------------|----------|------------------|---------------------|
| Intraday | 10-50 | 45-55% | -0.05% to +0.15% | Variable (high volatility) |
| Swing | 2-10 | 50-60% | +0.10% to +0.30% | 5-15% |
| Weekly | 0-2 | 55-65% | +0.25% to +0.75% | 10-25% |
| Monthly | 0-1 | 60-70% | +0.50% to +1.50% | 6-18% |

**Note:** These are rough estimates. Actual performance depends on market conditions, symbol selection, and parameter tuning.

## Best Practices

### 1. Match Data Interval to Strategy

```bash
# ✅ Correct: Swing strategy with hourly data
python scripts/fetch_strategy_data.py --strategy swing  # Fetches 1h bars

# ❌ Incorrect: Swing strategy with 5-minute data
python scripts/fetch_strategy_data.py --strategy intraday  # Wrong timeframe
python scripts/generate_sample_signals.py --strategy swing  # Mismatch!
```

### 2. Sufficient Data for MA Calculation

Ensure you fetch enough bars for the slow MA:

- Intraday (MA 20): Need 20+ bars = 100+ minutes = ~2 hours minimum
- Swing (MA 50): Need 50+ bars = ~3 trading days minimum
- Weekly (MA 20): Need 20+ days = ~1 month minimum
- Monthly (MA 60): Need 60+ days = ~3 months minimum

### 3. Account for Market Hours

- **Intraday/Swing**: Only execute during market hours (9:30 AM - 4:00 PM ET)
- **Weekly/Monthly**: Can generate signals once daily after market close

### 4. Monitor Signal Frequency

```bash
# Check signal generation
wc -l data/signals.jsonl

# Expected counts (1 month of data):
# Intraday: 100-500 signals
# Swing: 10-50 signals
# Weekly: 2-10 signals
# Monthly: 0-2 signals
```

If you see too many or too few signals, adjust MA periods or check data quality.

### 5. Backtest Before Live Trading

Always backtest a strategy before going live:

```bash
python scripts/run_backtest.py \
    --signals data/signals_weekly.jsonl \
    --market-data data/market_data_weekly.jsonl
```

Review metrics:
- Sharpe ratio > 1.0
- Max drawdown < 20%
- Win rate > 50%

## Troubleshooting

### Problem: No signals generated

**Solution:** Check if you have enough data for slow MA
```bash
# Count bars
wc -l data/market_data.jsonl

# For weekly strategy (MA 20), need 20+ daily bars
# Fetch more data:
python scripts/fetch_strategy_data.py --strategy weekly --symbol SPY
```

### Problem: Too many signals (over-trading)

**Solution:** Increase MA slow period or cooldown
```yaml
# In config/trading_strategies.yaml
swing:
  timeframe:
    ma_slow_period: 100  # Increase from 50
  execution:
    min_cooldown_minutes: 720  # Increase to 12 hours
```

### Problem: Data fetch fails for old dates

**Solution:** Yahoo Finance limits vary by interval
```bash
# ❌ Won't work (5m limited to 60 days)
python scripts/fetch_strategy_data.py --strategy intraday --symbol SPY
# (If lookback_days > 60)

# ✅ Works (daily data has unlimited history)
python scripts/fetch_strategy_data.py --strategy monthly --symbol SPY
```

### Problem: Strategy performance is poor

**Suggestions:**
1. Adjust MA periods (try different combinations)
2. Increase min_confidence threshold
3. Add more filters (volume, volatility)
4. Try different symbols
5. Test in different market regimes

## Advanced: Creating Custom Strategies

Edit `config/trading_strategies.yaml`:

```yaml
strategies:
  aggressive_scalp:
    name: "Aggressive Scalping"
    description: "Ultra-short term scalping on 1-minute bars"
    timeframe:
      data_interval: "1m"
      lookback_days: 2  # Yahoo limit for 1m
      ma_fast_period: 3
      ma_slow_period: 10
    execution:
      min_cooldown_minutes: 1  # 1 minute between trades
      max_holding_hours: 1
      position_exit_before_close: 60
    risk:
      min_confidence: 0.75  # High confidence for scalping
      min_profit_bp: 1.0
      risk_percent: 0.5  # Low risk per trade
```

Use it:
```bash
python scripts/fetch_strategy_data.py --strategy aggressive_scalp --symbol SPY
python scripts/generate_sample_signals.py --strategy aggressive_scalp
```

## Summary

✅ **4 Built-in Strategies**: Intraday, Swing, Weekly, Monthly  
✅ **Automated Parameter Configuration**: MA periods, cooldowns, risk settings  
✅ **Simple Workflow**: Fetch data → Generate signals → Trade  
✅ **Flexible**: Add custom strategies via YAML  
✅ **Backward Compatible**: Default intraday strategy unchanged  

**Next Steps:**
1. Choose a strategy that matches your time commitment
2. Fetch appropriate data for that strategy
3. Generate signals with strategy-specific parameters
4. Backtest before going live
5. Start trading via dashboard

**Questions?** See `config/trading_strategies.yaml` for all parameters.
