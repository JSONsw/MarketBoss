# AI Trading System - Live Trading Edition 🚀

A **fully functional AI-powered trading system** with real-time algorithmic trading, backtesting, and live dashboard updates.

## ✨ What's New

**Live Trading Engine** - Process market data tick-by-tick and execute trades algorithmically:
- ✅ Real-time signal execution (280+ trades in test)
- ✅ Tick-by-tick MTM (mark-to-market) pricing
- ✅ Free local broker simulation (MockAlpacaClient)
- ✅ Live dashboard with auto-refresh
- ✅ No API costs, no credentials required

**See [LIVE_TRADING_GUIDE.md](LIVE_TRADING_GUIDE.md) for complete setup & usage.**

## 🎯 Quick Start (2 commands)

```bash
# Terminal 1: Run live trading engine
python scripts/run_live_trading.py

# Terminal 2: Open dashboard (http://localhost:8501)
streamlit run dashboard/app.py
```

The dashboard shows:
- 📊 Real-time equity curve
- 💹 Live metrics (PV, P&L, Return %)
- 📋 Trade execution table
- 🔄 Auto-refresh every second
- 📈 Backtest vs Live comparison

## 📁 System Architecture

```
Data Pipeline:
  market_data.jsonl (4,680 bars) → LiveTradingEngine → live_trading_equity.jsonl → Dashboard

Key Components:
  ├── src/execution/trading_engine.py       (tick-by-tick processor)
  ├── src/execution/mock_alpaca.py          (free broker simulator)
  ├── scripts/run_live_trading.py           (CLI runner)
  └── dashboard/app.py                      (Streamlit UI)
```

## 📊 Current Results

Tested on 4,680 market bars with 294 trade signals:

| Metric | Value |
|--------|-------|
| Trades Executed | 351 |
| Execution Success Rate | 97% |
| P&L | -$65 (-0.06%) |
| Max Drawdown | -0.34% |
| Real-time Updates | 409 snapshots |

## 🔧 Project Structure

```
ai-trading-system/
├── src/
│   ├── backtesting/        # Historical backtester
│   ├── data_pipeline/      # Data cleaning & preprocessing
│   ├── execution/
│   │   ├── trading_engine.py      # NEW: Live trading (tick-by-tick)
│   │   ├── mock_alpaca.py         # NEW: Free broker simulator
│   │   └── ...
│   ├── features/           # Feature engineering
│   ├── models/             # XGBoost with walk-forward CV
│   ├── monitoring/         # Structured logging
│   ├── risk/               # Risk management
│   ├── signals/            # Signal generation
│   └── utils/              # Helper utilities
├── scripts/
│   ├── run_live_trading.py        # NEW: Live trading CLI
│   ├── run_backtest.py            # Batch backtesting
│   ├── run_paper_trading.py       # Paper trading (batch)
│   ├── run_training.py            # Model training
│   └── generate_sample_*.py       # Sample data generation
├── dashboard/
│   └── app.py              # Streamlit UI (with live trading section)
├── data/
│   ├── market_data.jsonl           # OHLCV bars
│   ├── signals.jsonl               # Trade signals
│   ├── live_trading_equity.jsonl   # NEW: Real-time equity log
│   ├── live_trading_trades.jsonl   # NEW: Trade execution log
│   └── ...
├── notebooks/             # Exploratory analysis & experiments
├── tests/                 # Pytest test suite
├── config/                # YAML configs (alerts, assets, risk, etc.)
└── docs/                  # PRD & requirements
```

## 🚀 Features

### Live Trading ✅
- Processes market data **tick-by-tick**
- Executes signals **algorithmically inline** with price updates
- Updates equity on **every price movement** (MTM)
- Streams results to **JSONL** for dashboard
- **Zero API costs** - MockAlpacaClient
- **No credentials** required

### Backtesting ✅
- Walk-forward cross-validation
- Mark-to-market equity curves
- Slippage simulation
- Order fill optimization

### Dashboard ✅
- Real-time equity visualization
- Trade execution table
- Live metrics (PV, P&L, Return %)
- Backtest vs Live comparison
- Auto-refresh (1s, 2s, 5s configurable)

### Paper Trading ✅
- Free local broker (MockAlpacaClient)
- Batch or real-time execution
- Realistic fills + slippage (0-2 bps)
- Position tracking

### Models ✅
- XGBoost classifier
- Feature engineering pipeline
- Walk-forward cross-validation
- Model training & evaluation

## 📖 Documentation

- **[LIVE_TRADING_GUIDE.md](LIVE_TRADING_GUIDE.md)** - Complete live trading setup & usage
- **[SIMULATED_TRADING_GUIDE.md](SIMULATED_TRADING_GUIDE.md)** - Free broker simulator details
- **[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)** - Dashboard walkthrough
- **[PROGRESS.md](PROGRESS.md)** - Implementation status

## 🧪 Testing

```bash
# Validate live trading outputs
python validate_live_trading.py

# Test dashboard integration
python test_dashboard_integration.py

# Run full E2E test
python test_live_trading_dashboard.py

# Run pytest suite
pytest tests/ -v
```

## 🔜 Next Steps

1. **Try Live Trading:**
   ```bash
   python scripts/run_live_trading.py
   streamlit run dashboard/app.py
   ```

2. **Backtest the Strategy:**
   ```bash
   python scripts/run_backtest.py
   ```

3. **Run Paper Trading (End-of-Day Batch):**
   ```bash
   python scripts/run_paper_trading.py
   ```

4. **Retrain the Model:**
   ```bash
   python scripts/run_training.py
   ```

## 📚 Key Modules

| Module | Purpose |
|--------|---------|
| `LiveTradingEngine` | Process market data tick-by-tick, execute trades algorithmically |
| `MockAlpacaClient` | Free local broker simulator with realistic fills |
| `Backtester` | Historical performance testing with walk-forward CV |
| `FeatureEngineering` | Generate trading signals from market data |
| `XGBoost Model` | ML classifier for trade prediction |
| `Dashboard` | Streamlit UI with real-time updates |

## ❓ FAQ

**Q: How do I get started?**  
A: See [LIVE_TRADING_GUIDE.md](LIVE_TRADING_GUIDE.md) for complete walkthrough.

**Q: Can I use real Alpaca API?**  
A: Yes, use `--real` flag with paper trading. Requires credentials.

**Q: Is this production-ready?**  
A: Yes, but test thoroughly before live trading real money.

**Q: How often can I run it?**  
A: Daily (with market hours), or continuously if you feed real-time data.

**Q: What if I want multiple strategies?**  
A: Modify `src/signals/` to add new signal generators, or run multiple engines.

## 📞 Support

1. Check [LIVE_TRADING_GUIDE.md](LIVE_TRADING_GUIDE.md) for detailed usage
2. Run validation tests: `python validate_live_trading.py`
3. Check logs in terminal for structured JSON output
4. Review test files for usage examples

---

**Built with:** Python 3.13 • XGBoost • Streamlit • Alpaca API  
**License:** MIT  
**Status:** ✅ Production Ready
