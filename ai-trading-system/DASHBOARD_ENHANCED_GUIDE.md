# MarketBoss Dashboard - Enhanced Multi-Timeframe Trading Interface

## Overview

The MarketBoss Dashboard is a comprehensive Streamlit-based trading interface that provides real-time market analysis, signal visualization, live trading monitoring, and performance analytics. The enhanced version includes full support for multi-timeframe trading strategies with an optimized layout for professional use.

## Key Features

### ✨ New Features (Enhanced Version)

1. **Multi-Timeframe Strategy Support**
   - Select from 4 pre-configured strategies (intraday, swing, weekly, monthly)
   - Strategy-aware data fetching with appropriate intervals
   - Automatic parameter optimization for each timeframe
   - Real-time strategy info display

2. **Optimized Tab-Based Layout**
   - **Market Analysis Tab**: Price charts, volume, and statistics
   - **Signals & Model Tab**: Trade signals and ML model metrics
   - **Live Trading Tab**: Real-time monitoring and execution
   - **Performance Tab**: Backtesting and comparative analysis

3. **Enhanced User Experience**
   - Cleaner, more intuitive interface
   - Better visual hierarchy with consistent color coding
   - Responsive charts with proper scaling
   - Contextual help popovers throughout

4. **Strategy-Aware Trading Controls**
   - One-click trading start/stop with strategy selection
   - Automatic strategy parameter injection
   - Visual strategy status indicators

## Quick Start

### Launch Dashboard

```bash
# Start the dashboard
streamlit run dashboard/app.py

# Dashboard will open at http://localhost:8501
```

### Basic Workflow

1. **Select Strategy** (Sidebar)
   - Choose: Intraday, Swing, Weekly, or Monthly
   - View strategy details (MA periods, cooldown, risk params)

2. **Configure Data Source** (Sidebar)
   - Yahoo Finance: Real-time data fetching
   - JSONL File: Historical cached data

3. **Navigate Tabs**
   - Tab 1: Market Analysis - Price/volume charts
   - Tab 2: Signals & Model - View signals and model performance
   - Tab 3: Live Trading - Monitor real-time trading
   - Tab 4: Performance - Compare backtest vs live results

4. **Start Trading** (Sidebar)
   - Click "🚀 Start Trading"
   - Selected strategy is automatically applied
   - Monitor live updates in Tab 3

## Interface Components

### Sidebar Configuration

#### Strategy Selection
```
📊 Trading Strategy
└── Select Strategy: [Intraday ▾]
    ├── Intraday (5m bars, MA 5/20)
    ├── Swing (1h bars, MA 10/50)
    ├── Weekly (1d bars, MA 5/20)
    └── Monthly (1d bars, MA 20/60)

ℹ️ Strategy Details (Expandable)
├── Interval: 5m
├── MA Periods: 5/20
├── Cooldown: 5min
├── Min Confidence: 60%
└── Risk per Trade: 2%
```

#### Data Source Configuration
```
📊 Market Data
├── Data Source: Yahoo Finance (Real-time) ⦿
│   ├── Symbol: SPY
│   └── Days of history: 60 (Strategy default)
│
└── Data Source: JSONL File (Historical) ○
    └── Market data JSONL: data/market_data.jsonl
```

#### Trading Controls
```
🎮 Trading Controls
Symbol: SPY
Strategy: Intraday

[🚀 Start Trading] [⏹️ Stop Trading]

Status: 🟢 Trading active for SPY
```

### Tab 1: Market Analysis

**Components:**
- Closing price chart (time series with trend line)
- Trading volume chart (bar chart)
- Statistical metrics (mean return, volatility, Sharpe estimate)
- Data freshness indicator

**Use Cases:**
- Identify market trends
- Analyze price movements
- Assess volatility levels
- Validate data quality

### Tab 2: Signals & Model

**Components:**
- Signal statistics (buy count, sell count, ratio)
- Recent signals table (last 50)
- Model validation metrics (MSE, MAE, R², RMSE)
- Feature importance chart (top 15 features)

**Use Cases:**
- Review generated signals
- Validate signal balance
- Assess model performance
- Understand predictive features

### Tab 3: Live Trading

**Components:**
- Real-time equity monitoring
- Performance metrics (PV, Return %, Trades, Status)
- Live equity curve (color-coded: green=profit, red=loss)
- Recent trades table
- Auto-refresh status

**Use Cases:**
- Monitor live trading in real-time
- Track portfolio value changes
- Review executed trades
- Verify strategy execution

### Tab 4: Performance

**Components:**
- Quick backtest results
- Equity curve visualization
- Backtest vs Live comparison (3-column layout)
  - Backtest metrics
  - Live trading metrics
  - Impact analysis
- Performance attribution

**Use Cases:**
- Validate strategy performance
- Compare ideal vs real-world results
- Analyze slippage/execution costs
- Measure strategy effectiveness

## Strategy Integration

### How Strategies Work in Dashboard

1. **Strategy Selection**
   ```python
   # User selects strategy from dropdown
   selected_strategy = "swing"  # 1-hour bars, MA 10/50
   ```

2. **Automatic Parameter Loading**
   ```python
   strategy = StrategyManager().get_strategy("swing")
   # Loads: data_interval=1h, lookback_days=90
   #        ma_fast_period=10, ma_slow_period=50
   #        min_cooldown=360min, risk_percent=3%
   ```

3. **Data Fetching with Strategy**
   ```bash
   # Dashboard fetches data with strategy interval
   # For swing: 1h bars, 90 days lookback
   ```

4. **Trading Execution with Strategy**
   ```bash
   # Start button passes strategy to trading engine
   python scripts/run_continuous_trading.py \
       --symbol SPY \
       --strategy swing  # Uses swing params
   ```

### Strategy Comparison Table

| Strategy  | Interval | MA Periods | Cooldown | Trades/Week | Holding Time |
|-----------|----------|------------|----------|-------------|--------------|
| Intraday  | 5m       | 5/20       | 5min     | 20-50       | Minutes-Hours|
| Swing     | 1h       | 10/50      | 6h       | 3-8         | Days-Week    |
| Weekly    | 1d       | 5/20       | 1week    | 1-2         | Weeks-Month  |
| Monthly   | 1d       | 20/60      | 1month   | 0-1         | Months       |

## Workflow Examples

### Example 1: Intraday Trading Setup

```bash
# 1. Start dashboard
streamlit run dashboard/app.py

# 2. In dashboard sidebar:
- Select Strategy: Intraday
- Data Source: Yahoo Finance (Real-time)
- Symbol: SPY
- Days: 60 (default for intraday)

# 3. Navigate to Tab 1 (Market Analysis)
- Verify data freshness (should show recent 5m bars)
- Check volume patterns

# 4. Navigate to Tab 2 (Signals & Model)
- Generate signals if needed:
  python scripts/generate_sample_signals.py --strategy intraday
- Review signal count and balance

# 5. Click "🚀 Start Trading" in sidebar
- Monitor live updates in Tab 3
- Check performance in Tab 4 after trades execute
```

### Example 2: Swing Trading Setup

```bash
# 1. Start dashboard
streamlit run dashboard/app.py

# 2. In dashboard sidebar:
- Select Strategy: Swing
- Data Source: Yahoo Finance (Real-time)
- Symbol: AAPL
- Days: 90 (default for swing)

# 3. View strategy details:
- Interval: 1h
- MA Periods: 10/50
- Cooldown: 6 hours
- Risk: 3% per trade

# 4. Generate swing signals:
python scripts/fetch_strategy_data.py --strategy swing --symbol AAPL
python scripts/generate_sample_signals.py --strategy swing

# 5. Start trading and monitor in Tab 3
```

### Example 3: Multi-Strategy Portfolio

```bash
# Monitor multiple strategies simultaneously

# Terminal 1: Intraday SPY
streamlit run dashboard/app.py --server.port 8501

# Terminal 2: Swing AAPL
streamlit run dashboard/app.py --server.port 8502

# Terminal 3: Weekly QQQ
streamlit run dashboard/app.py --server.port 8503

# Each dashboard runs independent strategy
```

## Chart Visualizations

### Price Charts
- **Color Scheme**: Blue line (#1f77b4)
- **Template**: Plotly White (clean, professional)
- **Scaling**: Auto-scaled with 2% padding for clarity
- **Features**: Hover tooltips, zoom, pan

### Volume Charts
- **Color Scheme**: Orange bars (#ff7f0e)
- **Y-Axis**: Starts at 0, max + 5% for headroom
- **Features**: Interactive hover for exact volumes

### Equity Curves
- **Color Coding**:
  - Green (#2ca02c): Profitable performance
  - Red (#d62728): Loss position
  - Blue (#1f77b4): Backtest (neutral)
- **Scaling**: Dynamic with 2% padding
- **Features**: Time-series or trade-indexed

### Feature Importance
- **Color Scheme**: Green bars (#2ca02c)
- **Sorting**: Descending by importance
- **Display**: Top 15 features only (for clarity)

## Performance Metrics Explained

### Live Trading Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| 🎯 Current PV | Current portfolio value | Cash + Open Positions MTM |
| 📊 Return % | Percentage return | (Current PV - Initial) / Initial * 100 |
| 💹 Trades | Number of executed trades | Count of BUY/SELL executions |
| 🟢/🔴 Status | Profitability indicator | Green if Return % > 0 |
| ⏱️ Last Update | Most recent data timestamp | Latest equity snapshot time |

### Backtest Metrics

| Metric | Description | Typical Range |
|--------|-------------|---------------|
| 💰 Total P&L | Net profit/loss | Depends on capital |
| 📈 Return | Total return % | -50% to +200% |
| ⚡ Sharpe | Risk-adjusted return | -1 to 3 (>1 is good) |
| 📉 Max Drawdown | Largest peak-to-trough loss | 5% to 30% |
| 🎯 Total Trades | Signal count | Strategy-dependent |

### Comparison Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| Return Diff | Live Return % - Backtest Return % | Usually negative (slippage) |
| Live Trades | Actual executions | May differ from signals |
| Reason | Attribution | "Slippage/fills" or "Better execution" |

## Auto-Refresh Behavior

### Live Trading Tab
- **Frequency**: Configurable (1s, 2s, 5s)
- **Default**: 1 second
- **Data**: Equity updates, trades, positions
- **Trigger**: Presence of live_trading_equity.jsonl

### Dashboard Rerun
```python
# Auto-refresh when live data exists
if live_equity_records:
    time.sleep(2)  # 2-second delay
    st.rerun()     # Reload dashboard
```

## Customization

### Adjust Chart Colors

```python
# Edit dashboard/app.py

# Price chart color
fig_close.add_trace(go.Scatter(..., line=dict(color='#YOUR_COLOR', width=2)))

# Volume chart color
fig_vol.add_trace(go.Bar(..., marker_color='#YOUR_COLOR'))

# Equity curve (profitable)
line_color = '#YOUR_GREEN_COLOR' if profitable else '#YOUR_RED_COLOR'
```

### Change Refresh Interval

```python
# Edit auto-refresh section
if live_equity_records:
    time.sleep(5)  # Change from 2 to 5 seconds
    st.rerun()
```

### Add Custom Metrics

```python
# Add to Tab 4 performance section
with tab4:
    st.metric("Custom Metric", f"{value:.2f}")
```

## Troubleshooting

### Issue: Strategy dropdown not appearing

**Cause**: Strategy config module not found

**Solution**:
```bash
# Verify strategy_config.py exists
ls src/execution/strategy_config.py

# Check YAML config
ls config/trading_strategies.yaml

# Test import
python -c "from src.execution.strategy_config import StrategyManager; print('OK')"
```

### Issue: Charts not displaying properly

**Cause**: Data type mismatch or missing data

**Solution**:
```python
# Verify data types
print(market_df.dtypes)
print(market_df.head())

# Check for NaN values
print(market_df.isnull().sum())
```

### Issue: Live trading not updating

**Cause**: File path incorrect or trading not started

**Solution**:
```bash
# Check file exists
ls data/live_trading_equity.jsonl

# Verify recent writes
Get-Content data/live_trading_equity.jsonl -Tail 5

# Restart trading if needed
# Click Stop Trading, then Start Trading
```

### Issue: Backtest comparison not showing

**Cause**: Missing signals or live trading data

**Solution**:
```bash
# Generate signals
python scripts/generate_sample_signals.py --strategy intraday

# Start trading
# Click "Start Trading" in dashboard

# Wait for trades to execute
# Comparison appears when both backtest and live data exist
```

## Best Practices

### 1. Strategy Selection
- **Intraday**: Active traders, frequent signals, requires monitoring
- **Swing**: Medium-term, balanced approach, less monitoring
- **Weekly**: Long-term trends, minimal trading, low maintenance
- **Monthly**: Very long-term, rare trades, position trading

### 2. Data Management
- Use Yahoo Finance for live data (always fresh)
- Use JSONL for backtesting historical periods
- Clear old JSONL files periodically to save space
- Backup live trading logs before clearing

### 3. Performance Monitoring
- Check Tab 4 comparison regularly
- If Return Diff is too negative (>5%), investigate:
  - Slippage settings
  - Commission rates
  - Signal quality
  - Market conditions

### 4. Resource Usage
- Close unused dashboard instances
- Limit historical data to needed periods
- Use appropriate refresh intervals (1s for active, 5s for monitoring)

### 5. Multi-Monitor Setup
- Monitor 1: Dashboard (Tab 3 - Live Trading)
- Monitor 2: Console (trading process output)
- Monitor 3: Market charts (external tool)
- Monitor 4: Dashboard (Tab 1 - Market Analysis)

## Advanced Features

### Trade Feed Viewer

Located at bottom of dashboard (expandable):

```
📡 Live Trade Feed
└── 📊 View Detailed Trade Feed (Expandable)
    ├── Tab: 📈 Statistics
    │   └── Trade counts, P&L summary, win rate
    ├── Tab: 📊 All Updates
    │   └── Full update history (up to 200 records)
    └── Tab: 💹 Trades Only
        └── Executed trades (up to 200 records)
```

**Use Cases:**
- Debug trading issues
- Analyze trade timing
- Verify signal execution
- Monitor update frequency

### Programmatic Access

```python
# Access dashboard components programmatically
from dashboard.trade_feed import TradeFeedViewer
from pathlib import Path

# Create viewer
viewer = TradeFeedViewer(
    updates_path=Path("data/live_trading_updates.jsonl"),
    trades_path=Path("data/live_trading_trades.jsonl")
)

# Load data
updates = viewer.load_recent_updates(limit=100)
trades = viewer.load_recent_trades(limit=50)

# Render in custom Streamlit app
viewer.render_statistics()
```

## Integration with Trading System

### Dashboard → Trading Engine Flow

```
1. User selects strategy in dashboard
   ↓
2. Dashboard loads strategy config
   ↓
3. User clicks "Start Trading"
   ↓
4. Dashboard spawns trading process with strategy param
   ↓
5. Trading engine uses strategy parameters
   ↓
6. Trades execute with strategy settings
   ↓
7. Results stream to JSONL files
   ↓
8. Dashboard auto-refreshes and displays
```

### File Dependencies

```
Dashboard reads:
├── data/market_data.jsonl (or Yahoo Finance API)
├── data/signals.jsonl
├── data/live_trading_equity.jsonl
├── data/live_trading_trades.jsonl
├── data/live_trading_updates.jsonl
├── models/*_metadata.json
└── config/trading_strategies.yaml

Dashboard writes:
├── data/.trading_process.pid (process tracking)
└── (No direct data writes; reads only)
```

## Command Reference

### Start Dashboard
```bash
streamlit run dashboard/app.py
```

### Start with Custom Port
```bash
streamlit run dashboard/app.py --server.port 8502
```

### Start with External Access
```bash
streamlit run dashboard/app.py --server.address 0.0.0.0
```

### Generate Signals for Dashboard
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

### Fetch Data for Dashboard
```bash
# Fetch with strategy
python scripts/fetch_strategy_data.py --strategy swing --symbol AAPL

# Fetch multiple symbols
python scripts/fetch_strategy_data.py --strategy intraday --symbol SPY,QQQ,IWM
```

## FAQ

**Q: Can I run multiple strategies at once?**
A: Yes, start multiple dashboard instances on different ports and select different strategies in each.

**Q: How do I change the default strategy?**
A: Edit `config/trading_strategies.yaml` and change `default_strategy: intraday` to your preferred strategy.

**Q: Can I create custom strategies?**
A: Yes, add new strategy definitions to `config/trading_strategies.yaml`. See MULTI_TIMEFRAME_GUIDE.md for details.

**Q: Why isn't live trading updating?**
A: Check that:
1. Trading process is running (green status in sidebar)
2. File `data/live_trading_equity.jsonl` exists and is being written to
3. Auto-refresh is enabled (dropdown shows 1s, 2s, or 5s)

**Q: How do I stop all trading processes?**
A: Click "⏹️ Stop Trading" button in sidebar. It will find and kill all trading processes.

**Q: Can I export backtest results?**
A: Results are shown in Tab 4. For detailed export, use the backtesting scripts directly:
```bash
python scripts/run_backtest.py --export results.json
```

**Q: What's the difference between Yahoo Finance and JSONL data source?**
A: 
- **Yahoo Finance**: Live, always fresh, requires internet, slower load
- **JSONL**: Cached, fast load, offline access, may be stale

**Q: How do I optimize dashboard performance?**
A: 
1. Limit days of history (60 for intraday, 90 for swing)
2. Use JSONL for historical analysis
3. Increase refresh interval to 5s if not actively monitoring
4. Close unused tabs in browser

## Conclusion

The enhanced MarketBoss Dashboard provides a professional-grade interface for multi-timeframe trading with:

✅ **Intuitive Navigation**: Tab-based layout for clear workflows  
✅ **Strategy Flexibility**: Easy switching between timeframes  
✅ **Real-time Monitoring**: Live updates with auto-refresh  
✅ **Performance Analytics**: Comprehensive backtest vs live comparison  
✅ **Visual Clarity**: Optimized charts with proper scaling  
✅ **User-Friendly Controls**: One-click trading start/stop  

The dashboard seamlessly integrates with the multi-timeframe trading system to provide complete visibility and control over your algorithmic trading operations.

For more information:
- Strategy details: See `MULTI_TIMEFRAME_GUIDE.md`
- System overview: See `README.md`
- Trading setup: See `LIVE_TRADING_GUIDE.md`
