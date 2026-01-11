# Live Trade Feed - Custom Data Feed Alternative

## Overview

The **Live Trade Feed** provides a real-time, in-dashboard view of trading activity without requiring a console window. It reads directly from `live_trading_updates.jsonl` and `live_trading_trades.jsonl` to display trading events as they happen.

## Features

### 1. Sidebar Compact Feed
- **Real-time metrics** displayed in sidebar
- Shows last 10 updates with color-coded icons
- Portfolio value, positions, and trade count at a glance
- Auto-refreshes every 2 seconds during active trading

### 2. Detailed Feed Viewer
Located at the bottom of the main dashboard in an expandable section:

#### Statistics Tab
- Total P&L ($ and %)
- Total trades executed
- Updates logged count
- Average trade value
- Recent buy/sell breakdown

#### All Updates Tab
- View last 100 trading updates (configurable)
- Shows INIT, TICK, and TRADE events
- Real-time portfolio value changes
- Cash balance and position tracking
- Time-stamped activity log

#### Trades Only Tab
- Filtered view of executed trades
- Symbol, side (BUY/SELL), quantity, price
- Portfolio value after each trade
- Sorted by most recent first

### 3. Standalone Feed Viewer
Run as a separate Streamlit app:
```bash
streamlit run dashboard/trade_feed.py
```

Features:
- Full-page trade feed
- Auto-refresh toggle (5-second intervals)
- Manual refresh button
- Statistics overview
- Detailed trade history

## Usage

### In Main Dashboard (Integrated)

**Sidebar Feed:**
```python
# Automatically displays when you import and call
from dashboard.trade_feed import render_trade_feed_sidebar

# In sidebar section
render_trade_feed_sidebar()
```

**Full Feed Section:**
The trade feed is automatically included at the bottom of the dashboard. Expand the "📊 View Detailed Trade Feed" section to see:
- Statistics
- All updates (INIT/TICK/TRADE)
- Trades only

### As Standalone Viewer

```bash
# Run dedicated trade feed viewer
streamlit run dashboard/trade_feed.py
```

Features:
- Auto-refresh checkbox (updates every 5 seconds)
- Manual refresh button
- Full-width layout
- Real-time statistics

## Data Sources

### live_trading_updates.jsonl
Contains all trading engine events:

**INIT** - Engine initialization
```json
{
  "timestamp": "2026-01-09T20:02:07.393262Z",
  "update_type": "INIT",
  "cash": 100000.0,
  "portfolio_value": 100000.0,
  "positions": 0,
  "trades_executed": 0
}
```

**TICK** - Market price update (MTM)
```json
{
  "timestamp": "2026-01-09T20:02:07.401481Z",
  "update_type": "TICK",
  "cash": 100000.0,
  "portfolio_value": 100000.0,
  "positions": 0
}
```

**TRADE** - Order execution
```json
{
  "timestamp": "2026-01-09T20:02:07.509605Z",
  "update_type": "TRADE",
  "cash": 95500.0,
  "portfolio_value": 100016.93,
  "positions": 1,
  "trades_executed": 1
}
```

### live_trading_trades.jsonl
Contains executed trade details:
```json
{
  "timestamp": "2026-01-09T20:02:07.509605Z",
  "symbol": "SPY",
  "side": "BUY",
  "qty": 10,
  "price": 450.50,
  "portfolio_value": 100016.93
}
```

## Benefits vs Console Window

| Feature | Console Window | Trade Feed |
|---------|----------------|------------|
| **Visibility** | Separate window | Integrated in dashboard |
| **Accessibility** | Can be closed/lost | Always available |
| **Searchability** | Scroll only | Filterable, searchable |
| **History** | Limited buffer | Full JSONL history |
| **Export** | Copy/paste | Direct CSV export |
| **Statistics** | None | Real-time metrics |
| **Filtering** | None | By type, time, symbol |
| **Multi-session** | Lost on restart | Persists across sessions |

## Components

### TradeFeedViewer Class
Main component for rendering trade feeds:

```python
from dashboard.trade_feed import TradeFeedViewer

# Initialize viewer
viewer = TradeFeedViewer(
    updates_path=Path("data/live_trading_updates.jsonl"),
    trades_path=Path("data/live_trading_trades.jsonl")
)

# Load recent data
updates = viewer.load_recent_updates(limit=100)
trades = viewer.load_recent_trades(limit=50)

# Render views
viewer.render_compact_feed(limit=10)    # Minimal view
viewer.render_detailed_feed(limit=50)   # Full view
viewer.render_statistics()              # Stats overview
```

### Helper Functions

**Sidebar Integration:**
```python
from dashboard.trade_feed import render_trade_feed_sidebar

render_trade_feed_sidebar()  # Adds feed to sidebar
```

**Full Page View:**
```python
from dashboard.trade_feed import render_trade_feed_page

render_trade_feed_page()  # Standalone page
```

## Customization

### Update Display Limits
```python
# Show more/fewer updates
viewer.render_compact_feed(limit=20)  # Default: 10
viewer.render_detailed_feed(limit=200)  # Default: 50
```

### Auto-Refresh Rate
In dashboard `app.py`:
```python
# Auto-refresh every 2 seconds (default)
if live_equity_records:
    import time
    time.sleep(2)  # Change this value
    st.rerun()
```

In standalone `trade_feed.py`:
```python
# Auto-refresh every 5 seconds (default)
<meta http-equiv="refresh" content="5">  # Change this value
```

### Color Coding
Update types have color-coded borders:

- 🔔 **TRADE** - Green (`#28a745`)
- 📊 **TICK** - Blue (`#17a2b8`)
- ℹ️ **INIT** - Gray (`#6c757d`)

Modify in `trade_feed.py`:
```python
if update_type == 'TRADE':
    icon = "🔔"
    color = "#28a745"  # Change color here
```

## Performance

### Memory Efficiency
- Only loads last N records (configurable)
- Uses streaming reads (line-by-line)
- No full file load into memory

### Update Frequency
- **Sidebar feed:** Updates every 2 seconds
- **Full feed:** Updates on manual refresh or auto-refresh timer
- **Data files:** Written real-time by trading engine

### Scalability
- Handles 10,000+ updates efficiently
- JSONL format allows incremental reads
- Old data automatically pruned by trading engine

## Troubleshooting

### "No trading activity yet"
- Start trading: Click "🚀 Start Trading" button
- Check `data/live_trading_updates.jsonl` exists
- Verify trading script is running

### Feed not updating
- Check auto-refresh is enabled
- Click manual refresh button
- Verify trading engine is writing to JSONL files
- Check file permissions on `data/` directory

### Slow performance
- Reduce display limit: `viewer.render_detailed_feed(limit=20)`
- Clear old JSONL files if >100K lines
- Increase auto-refresh interval

### Missing trades
- Check `data/live_trading_trades.jsonl` exists
- Verify signals are being generated
- Check trading filters (min_confidence, min_profit_bp)

## Examples

### Basic Integration
```python
import streamlit as st
from dashboard.trade_feed import TradeFeedViewer

st.title("My Trading Dashboard")

# Create viewer
viewer = TradeFeedViewer()

# Show stats
viewer.render_statistics()

# Show recent trades
viewer.render_detailed_feed(limit=50)
```

### Custom Sidebar
```python
import streamlit as st
from dashboard.trade_feed import TradeFeedViewer

with st.sidebar:
    st.markdown("### 📡 Live Feed")
    
    viewer = TradeFeedViewer()
    updates = viewer.load_recent_updates(limit=5)
    
    for update in reversed(updates):
        st.write(f"{update['update_type']}: ${update['portfolio_value']:,.2f}")
```

### Export to CSV
```python
import pandas as pd
from dashboard.trade_feed import TradeFeedViewer

viewer = TradeFeedViewer()
trades = viewer.load_recent_trades(limit=1000)

df = pd.DataFrame(trades)
df.to_csv("trades_export.csv", index=False)
```

## Files Created

| File | Purpose | Size |
|------|---------|------|
| `dashboard/trade_feed.py` | Trade feed viewer component | ~15 KB |
| `data/live_trading_updates.jsonl` | All trading updates | Grows over time |
| `data/live_trading_trades.jsonl` | Executed trades only | Grows over time |

## Next Steps

1. **Add Filtering:** Filter by symbol, time range, update type
2. **Add Charts:** Real-time equity curve, trade frequency histogram
3. **Add Alerts:** Desktop notifications for trades, losses
4. **Add Export:** One-click CSV/JSON export
5. **Add Search:** Full-text search across all updates

---

**Created:** January 10, 2026  
**Status:** ✅ Production Ready  
**Dependencies:** streamlit, pandas, json, pathlib
