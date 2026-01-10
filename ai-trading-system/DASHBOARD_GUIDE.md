# MarketBoss Dashboard & Paper Trading Guide

## Dashboard Enhancement Summary

The Streamlit dashboard has been fully enhanced with **paper trading equity tracking** and **backtest vs live comparison metrics**.

### Dashboard Features

#### 1. **Market Data Overview**
- Price and volume charts from `data/market_data.jsonl`
- Returns statistics (mean, volatility)

#### 2. **Signals Inspection**
- Table of all generated signals
- Timestamp, action, symbol, quantity visibility

#### 3. **Model Metrics**
- Latest model metadata from `models/`
- Feature importance visualization (bar chart)
- Training metrics (MSE, fold statistics)

#### 4. **Quick Backtest View**
- Real-time backtest using current signals
- P&L, Return %, Sharpe ratio, Max Drawdown
- Equity curve visualization

#### 5. **Paper Trading (NEW!)**
- **Live equity curve** from `data/paper_trading_equity.jsonl`
- Current portfolio value, P&L, return %
- Trade execution count and last update timestamp

#### 6. **Backtest vs Paper Trading Comparison (NEW!)**
Displays side-by-side comparison when paper trading logs exist:
- **Backtest Metrics**: Return %, Sharpe, Max Drawdown
- **Paper Trading Metrics**: Return %, P&L $, Status (✅ Positive / ⚠️ Below Initial)
- **Comparison Metrics**: Return difference, slippage impact, total trades

### How to Run the Dashboard

```bash
# Basic usage (loads default paths)
streamlit run dashboard/app.py

# Or with Python -m
python -m streamlit run dashboard/app.py
```

**Sidebar Configuration:**
- **Market data JSONL**: Path to OHLCV bars (default: `data/market_data.jsonl`)
- **Signals JSONL**: Path to trade signals (default: `data/signals.jsonl`)
- **Models dir**: Directory with trained models (default: `models`)
- **Paper trading equity log**: Path to live equity snapshots (default: `data/paper_trading_equity.jsonl`)
- **Initial cash**: Starting capital for backtest comparison (default: $100,000)

---

## Paper Trading Executor

### Script Location
`scripts/run_paper_trading.py`

### Features
- ✅ Alpaca API integration (paper account)
- ✅ Market order execution with fill verification
- ✅ Real-time equity snapshots
- ✅ Trade logging to JSONL
- ✅ Structured logging (JSON format)
- ✅ Rate limiting (1 sec between orders)
- ✅ Order timeout handling (5 min window for fills)

### Usage

```bash
# Execute first 50 signals on paper account
python scripts/run_paper_trading.py \
  --signals data/signals.jsonl \
  --max-trades 50

# Full options
python scripts/run_paper_trading.py \
  --signals data/signals.jsonl \
  --max-trades 100 \
  --trades-output data/paper_trading_trades.jsonl \
  --equity-output data/paper_trading_equity.jsonl
```

### Environment Setup (Required!)

Before running paper trading, configure Alpaca API credentials:

```bash
# Linux/macOS
export APCA_API_BASE_URL="https://paper-api.alpaca.markets"
export APCA_API_KEY_ID="your_api_key"
export APCA_API_SECRET_KEY="your_secret_key"

# Windows PowerShell
$env:APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
$env:APCA_API_KEY_ID = "your_api_key"
$env:APCA_API_SECRET_KEY = "your_secret_key"
```

Or create `.env` file in project root:
```
APCA_API_BASE_URL=https://paper-api.alpaca.markets
APCA_API_KEY_ID=your_api_key
APCA_API_SECRET_KEY=your_secret_key
```

### Output Files

**Trades Log** (`data/paper_trading_trades.jsonl`):
```json
{
  "timestamp": "2026-01-09T18:42:00.000Z",
  "signal_timestamp": "2025-01-01T12:00:00.000Z",
  "order_id": "abc123",
  "symbol": "AAPL",
  "side": "BUY",
  "qty": 10,
  "filled_price": 150.25,
  "status": "filled"
}
```

**Equity Log** (`data/paper_trading_equity.jsonl`):
```json
{
  "timestamp": "2026-01-09T18:42:00.000Z",
  "cash": 95000.00,
  "portfolio_value": 105250.30,
  "buying_power": 105250.30,
  "equity_multiplier": 1.0
}
```

### Workflow

1. **Generate Signals**
   ```bash
   python scripts/generate_sample_signals.py --data data/market_data.jsonl
   ```

2. **Start Paper Trading**
   ```bash
   python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 50
   ```

3. **View Dashboard**
   ```bash
   streamlit run dashboard/app.py
   ```
   - Equity curve updates with each new snapshot
   - Comparison metrics show backtest vs live performance
   - Trade count increments as orders fill

---

## Performance Expectations

### Backtest (Synthetic, MTM Tracking)
- **Return**: Variable (typically -0.5% to +2%)
- **Sharpe**: Variable (depends on signal quality)
- **Max Drawdown**: <2%
- **Win Rate**: 15-25% (MA crossover strategy)

### Paper Trading (Live Market)
- Expect **slippage** of 1-5bp per trade (vs 0 in backtest)
- **Real commissions** from Alpaca (typically 0.1%)
- **Market impact** from orders (especially low-liquidity symbols)
- Returns **will differ** from backtest (this is expected!)

### Key Metrics to Monitor
- **Return Difference**: Paper vs Backtest (typically -1% to -3% due to slippage)
- **Sharpe Ratio**: Paper trading Sharpe should remain positive if strategy is sound
- **Max Drawdown**: Should be contained (<5%)
- **Win Rate**: Paper should match backtest within 5-10%

---

## Troubleshooting

### Dashboard Won't Load
- Check paths in sidebar match actual files
- Ensure `data/market_data.jsonl` and `data/signals.jsonl` exist
- Verify Streamlit installed: `pip install streamlit`

### Paper Trading Fails (Alpaca API)
- Verify env vars: `echo $APCA_API_KEY_ID` (or use `.env` file)
- Ensure paper account active on Alpaca
- Check API key permissions (trade, read account)
- Verify symbol format (e.g., "AAPL", not "aapl")

### No Paper Trading Data in Dashboard
- Run executor first: `python scripts/run_paper_trading.py ...`
- Check output files exist:
  - `data/paper_trading_equity.jsonl`
  - `data/paper_trading_trades.jsonl`
- Hard-refresh dashboard (Ctrl+Shift+R) to clear cache

### Trades Not Filling
- Orders expire after 5 minutes in executor
- Check market hours (9:30-16:00 ET, Mon-Fri)
- Verify buying power (check Alpaca account dashboard)
- Use liquid symbols (SPY, AAPL, QQQ, etc.)

---

## Next Steps

1. **Test Paper Trading** (today)
   - Execute 10-20 signals, observe fills and slippage
   - Compare dashboard backtest vs live P&L

2. **Monitor Performance** (ongoing)
   - Daily dashboard checks
   - Track return divergence from backtest
   - Adjust slippage assumptions if needed

3. **Multi-Strategy Framework** (next week)
   - Implement 2-3 additional strategies
   - Compare side-by-side on dashboard
   - Select best performer for expanded paper trading

4. **Automated Retraining** (next 2 weeks)
   - Schedule daily model refresh
   - Detect feature drift
   - Auto-retrain if performance degrades

5. **Live Trading** (after validation)
   - Migrate to live account after 2+ weeks of paper trading
   - Implement position limits and stop-losses
   - Add Slack/email alerts for key events
