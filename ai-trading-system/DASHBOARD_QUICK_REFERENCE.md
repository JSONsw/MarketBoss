# Dashboard Quick Reference Card

## 🚀 Launch Dashboard
```bash
streamlit run dashboard/app.py
```
Opens at: http://localhost:8501

## 📊 Dashboard Layout

### Sidebar (Left)
```
⚙️ Configuration
├── 📊 Trading Strategy
│   └── [Select Strategy ▾]
│       ├── Intraday (5m bars)
│       ├── Swing (1h bars)
│       ├── Weekly (1d bars)
│       └── Monthly (1d bars)
│   ℹ️ Strategy Details
│
├── 📊 Market Data
│   ├── Data Source: Yahoo Finance / JSONL
│   ├── Symbol: SPY
│   └── Days: 60
│
├── 🎮 Trading Controls
│   ├── [🚀 Start Trading]
│   └── [⏹️ Stop Trading]
│   Status: 🟢/⚫
│
└── 📡 Trade Feed
    (Collapsible)
```

### Main Content (Tabs)

#### Tab 1: 📈 Market Analysis
- Closing price chart (time series)
- Trading volume chart (bars)
- Statistics: Mean Return, Volatility, Sharpe

#### Tab 2: 🎯 Signals & Model
- Signal statistics (Buy/Sell counts, ratio)
- Recent signals table (last 50)
- Model metrics (MSE, MAE, R², RMSE)
- Feature importance (top 15)

#### Tab 3: 💹 Live Trading
- 5-Metric Dashboard:
  - 🎯 Current PV
  - 📊 Return %
  - 💹 Trades
  - 🟢/🔴 Status
  - ⏱️ Last Update
- Live equity curve (color-coded)
- Recent trades table

#### Tab 4: 📊 Performance
- Backtest results & equity curve
- 3-Column Comparison:
  - 📈 Backtest metrics
  - 🟢 Live trading metrics
  - 📊 Impact analysis

## ⚡ Quick Workflows

### Workflow 1: Start Intraday Trading
```bash
# 1. Launch dashboard
streamlit run dashboard/app.py

# 2. In sidebar:
- Strategy: Intraday
- Data Source: Yahoo Finance
- Symbol: SPY

# 3. Click: 🚀 Start Trading

# 4. Monitor in Tab 3
```

### Workflow 2: Start Swing Trading
```bash
# 1. Launch dashboard
streamlit run dashboard/app.py

# 2. In sidebar:
- Strategy: Swing
- Symbol: AAPL

# 3. Generate signals:
python scripts/generate_sample_signals.py --strategy swing

# 4. Click: 🚀 Start Trading

# 5. Check performance in Tab 4
```

### Workflow 3: Backtest Analysis
```bash
# 1. Launch dashboard
streamlit run dashboard/app.py

# 2. Navigate to Tab 2 (Signals & Model)
- Verify signals loaded

# 3. Navigate to Tab 4 (Performance)
- View backtest equity curve
- Check metrics

# 4. If live trading running:
- Compare Backtest vs Live in 3-column view
```

## 🎨 Color Coding

| Color | Meaning | Used For |
|-------|---------|----------|
| 🔵 Blue (#1f77b4) | Neutral/Info | Price charts, backtest |
| 🟠 Orange (#ff7f0e) | Volume | Volume bars |
| 🟢 Green (#2ca02c) | Profitable | Equity when profit, features |
| 🔴 Red (#d62728) | Loss | Equity when loss |

## 📊 Key Metrics

### Overview (Top Bar)
- 📊 Market Bars: Total data points
- 🎯 Signals: Generated signals count
- ⚡ Strategy: Current strategy name
- 🎓 Model MSE: Model accuracy

### Live Trading (Tab 3)
- 🎯 Current PV: Portfolio value now
- 📊 Return %: Percentage gain/loss
- 💹 Trades: Executed trades count
- 🟢/🔴 Status: Profitable or Loss
- ⏱️ Last Update: Latest data time

### Performance (Tab 4)
- 💰 Total P&L: Net profit/loss
- 📈 Return: Total return %
- ⚡ Sharpe: Risk-adjusted return
- 📉 Max Drawdown: Largest loss
- 🎯 Total Trades: Signal count

## 🔧 Common Commands

### Generate Signals
```bash
# Intraday
python scripts/generate_sample_signals.py --strategy intraday

# Swing
python scripts/generate_sample_signals.py --strategy swing

# Weekly
python scripts/generate_sample_signals.py --strategy weekly

# Monthly
python scripts/generate_sample_signals.py --strategy monthly
```

### Fetch Market Data
```bash
# With strategy (recommended)
python scripts/fetch_strategy_data.py --strategy swing --symbol AAPL

# Multiple symbols
python scripts/fetch_strategy_data.py --strategy intraday --symbol SPY,QQQ,IWM
```

### Stop Trading
- Click "⏹️ Stop Trading" in sidebar
- Kills all trading processes automatically

## 💡 Tips & Tricks

### Tip 1: Multi-Monitor Setup
- Monitor 1: Dashboard Tab 3 (Live Trading)
- Monitor 2: Trading console output
- Monitor 3: Dashboard Tab 1 (Market Analysis)

### Tip 2: Refresh Control
In Tab 3, adjust refresh interval:
- **1s**: Active monitoring (high CPU)
- **2s**: Balanced (default)
- **5s**: Background monitoring (low CPU)

### Tip 3: Strategy Switching
Change strategy anytime:
1. Select new strategy from dropdown
2. Click "Stop Trading" if running
3. Generate new signals
4. Click "Start Trading"

### Tip 4: Data Source
- **Yahoo Finance**: Always fresh, requires internet
- **JSONL**: Fast loading, works offline

### Tip 5: Performance Analysis
Best comparison when:
- Backtest complete (signals generated)
- Live trading has executed trades
- Both use same strategy and symbol

## 🐛 Quick Troubleshooting

### Issue: Strategy dropdown empty
```bash
# Check strategy config exists
ls config/trading_strategies.yaml

# Test import
python -c "from src.execution.strategy_config import StrategyManager; print('OK')"
```

### Issue: Charts not showing
```bash
# Verify data exists
python -c "import pandas as pd; df = pd.read_json('data/market_data.jsonl', lines=True); print(len(df))"
```

### Issue: Live trading not updating
```bash
# Check file exists and is recent
ls -la data/live_trading_equity.jsonl
Get-Content data/live_trading_equity.jsonl -Tail 3
```

### Issue: Trading won't start
```bash
# Check if already running
Get-Process | Where-Object {$_.CommandLine -like "*run_continuous_trading*"}

# Stop all trading processes
Click "⏹️ Stop Trading" in dashboard
```

## 📚 Documentation Links

- **Comprehensive Guide**: `DASHBOARD_ENHANCED_GUIDE.md`
- **Strategy Details**: `MULTI_TIMEFRAME_GUIDE.md`
- **Trading Setup**: `LIVE_TRADING_GUIDE.md`
- **System Overview**: `README.md`

## 🎯 Strategy Quick Reference

| Strategy | Interval | MA | Cooldown | Trades/Week | Best For |
|----------|----------|----|-----------|--------------| ---------|
| Intraday | 5m | 5/20 | 5min | 20-50 | Active trading |
| Swing | 1h | 10/50 | 6h | 3-8 | Medium-term |
| Weekly | 1d | 5/20 | 1week | 1-2 | Long-term trends |
| Monthly | 1d | 20/60 | 1month | 0-1 | Position trading |

## ⌨️ Keyboard Shortcuts

Dashboard runs in browser:
- **F5**: Refresh page
- **Ctrl+F**: Search in page
- **Ctrl+Shift+R**: Hard refresh (clear cache)
- **F11**: Fullscreen mode

## 📱 Mobile/Tablet Access

Access dashboard from other devices on same network:

1. Find your computer's IP:
```powershell
ipconfig | findstr IPv4
```

2. Start dashboard with external access:
```bash
streamlit run dashboard/app.py --server.address 0.0.0.0
```

3. On mobile/tablet, browse to:
```
http://YOUR_IP_ADDRESS:8501
```

## 🔒 Security Notes

- Dashboard is for **local use only** by default
- External access (0.0.0.0) exposes to network
- No authentication built-in
- Use firewall for external access
- Consider VPN for remote access

## 📞 Support

For issues:
1. Check `DASHBOARD_ENHANCED_GUIDE.md` FAQ section
2. Review logs in console output
3. Verify file paths in sidebar inputs
4. Check strategy config with test import
5. Restart dashboard with `Ctrl+C` then relaunch

---

**Quick Start:**
```bash
streamlit run dashboard/app.py
# Select Strategy → Click Start Trading → Monitor in Tab 3
```

**Status Check:**
- 🟢 = Trading active
- ⚫ = Trading inactive
- Green equity = Profitable
- Red equity = Loss

**Remember:**
- Tab 1: Market data
- Tab 2: Signals & Model
- Tab 3: Live trading
- Tab 4: Performance
