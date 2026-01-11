# Custom Trade Feed - Quick Start Guide

## What Is This?

A **real-time trade feed viewer** that displays all trading activity **inside the dashboard** instead of requiring a console window.

## Why Use It?

### Problems with Console Window
- ❌ Separate window gets lost/minimized
- ❌ Can't scroll back through history easily
- ❌ No search or filtering
- ❌ Lost when console is closed
- ❌ No statistics or metrics

### Benefits of Trade Feed
- ✅ **Integrated** - Shows right in the dashboard
- ✅ **Persistent** - Survives dashboard restarts
- ✅ **Searchable** - Full data tables
- ✅ **Statistics** - Real-time P&L, trade counts
- ✅ **Filterable** - View all updates or trades only
- ✅ **Sidebar Widget** - Quick glance at activity

## Quick Start

### 1. View in Dashboard (Recommended)

```bash
# Start the dashboard
streamlit run dashboard/app.py
```

**Then:**
1. Look at the **sidebar** - you'll see a compact feed with recent activity
2. Scroll to the **bottom** of the dashboard
3. Expand "📊 View Detailed Trade Feed"
4. Choose your view:
   - **Statistics** - P&L, trade count, metrics
   - **All Updates** - Every event (INIT/TICK/TRADE)
   - **Trades Only** - Just executed orders

### 2. Standalone Viewer (Full Screen)

```bash
# Run dedicated trade feed app
streamlit run dashboard/trade_feed.py
```

Features:
- Full-screen trade activity
- Auto-refresh toggle (updates every 5 seconds)
- Manual refresh button
- No other dashboard clutter

## What You'll See

### Sidebar Feed (Compact)
```
📡 Live Trade Feed

Portfolio Value: $100,234.56
Cash: $95,234.56
Positions: 1
Trades: 42

Recent Activity:
🔔 14:32:15 - TRADE | Portfolio: $100,234.56 | Positions: 1 | Trades: 42
📊 14:32:10 - TICK | Portfolio: $100,123.45 | Positions: 1 | Trades: 41
🔔 14:32:05 - TRADE | Portfolio: $100,050.00 | Positions: 0 | Trades: 41
```

### Statistics Tab
```
Total P&L: $234.56 (+0.23%)
Total Trades: 42
Updates Logged: 1,234
Avg Trade Value: $2,386.54

Recent Trade Summary:
Recent Buys: 6
Recent Sells: 4
```

### All Updates Tab
```
Time       | Type  | Portfolio ($) | Cash ($)   | Positions | Total Trades
14:32:15   | TRADE | $100,234.56   | $95,234.56 | 1         | 42
14:32:10   | TICK  | $100,123.45   | $95,123.45 | 1         | 41
14:32:05   | TRADE | $100,050.00   | $100,050.00| 0         | 41
```

### Trades Only Tab
```
Time     | Symbol | Side | Qty | Price ($) | Portfolio ($)
14:32:15 | SPY    | BUY  | 10  | $450.50   | $100,234.56
14:32:05 | SPY    | SELL | 10  | $449.25   | $100,050.00
14:31:50 | SPY    | BUY  | 10  | $448.75   | $99,875.00
```

## How It Works

### Data Source
The feed reads from two JSONL files created by the trading engine:

1. **data/live_trading_updates.jsonl** - All events
   - INIT: Engine starts
   - TICK: Price updates (mark-to-market)
   - TRADE: Order executions

2. **data/live_trading_trades.jsonl** - Executed orders only
   - Symbol, side, quantity, price
   - Portfolio value after trade

### Real-Time Updates
- Dashboard auto-refreshes every 2 seconds when trading is active
- Standalone viewer can auto-refresh every 5 seconds
- Manual refresh button available

### Color Coding
- 🔔 **TRADE** (Green) - Order executed
- 📊 **TICK** (Blue) - Price update
- ℹ️ **INIT** (Gray) - System initialization

## Usage Examples

### Check Recent Activity
1. Open dashboard
2. Look at sidebar - see last 10 updates
3. Instant view of trading status

### Review All Trades
1. Scroll to bottom of dashboard
2. Expand "📊 View Detailed Trade Feed"
3. Click "Trades Only" tab
4. Adjust slider to show more/fewer trades

### Monitor Performance
1. Expand trade feed
2. Click "Statistics" tab
3. View P&L, trade count, buy/sell ratio

### Export Trade History
1. Expand trade feed
2. View "Trades Only" tab
3. Use Streamlit's built-in data export (top-right of table)
4. Download as CSV

## Tips & Tricks

### Increase Visible Updates
In "All Updates" or "Trades Only" tab:
- Use the slider to adjust display count (10-200)
- Default is 50 items

### Auto-Refresh
**Main Dashboard:**
- Auto-refreshes every 2 seconds when trading is active
- No toggle needed - automatic

**Standalone Viewer:**
- Check "Auto-refresh (every 5 seconds)" box
- Or click "🔄 Refresh Now" button

### Find Specific Trades
Use browser's search (Ctrl+F / Cmd+F):
- Search for symbol (e.g., "SPY")
- Search for side ("BUY", "SELL")
- Search for time ("14:32")

### Performance Optimization
If feed is slow:
- Reduce display limit slider to 20-30
- Clear old JSONL files if >100K lines
- Increase auto-refresh interval

## Comparison: Console vs Trade Feed

| Feature | Console Window | Trade Feed |
|---------|----------------|------------|
| **Location** | Separate window | In dashboard |
| **History** | Scroll back limited | Full JSONL history |
| **Search** | None | Full text search |
| **Statistics** | None | Real-time metrics |
| **Export** | Copy/paste | CSV download |
| **Persistence** | Lost on close | Permanent |
| **Filtering** | None | By type, symbol |
| **Accessibility** | Easy to lose | Always available |

## Troubleshooting

### "No trading activity yet"
✅ **Solution:** Click "🚀 Start Trading" button to start the trading engine

### Feed not updating
✅ **Solution:** 
- Check auto-refresh is enabled
- Click "🔄 Refresh Now" manually
- Verify trading engine is running

### No data in files
✅ **Solution:**
- Check `data/live_trading_updates.jsonl` exists
- Verify trading engine has started
- Look for errors in trading console

### Slow performance
✅ **Solution:**
- Reduce display limit to 20-30
- Clear JSONL files if very large
- Restart dashboard

## Files

| File | Purpose |
|------|---------|
| `dashboard/trade_feed.py` | Trade feed component |
| `dashboard/app.py` | Main dashboard (includes feed) |
| `data/live_trading_updates.jsonl` | All trading events |
| `data/live_trading_trades.jsonl` | Executed trades |

## Next Steps

1. **Try It:** Click "🚀 Start Trading" and watch the feed populate
2. **Explore:** Expand the detailed feed and browse all tabs
3. **Customize:** Adjust sliders to show more/fewer items
4. **Monitor:** Keep sidebar feed visible for at-a-glance status

---

**Ready to use!** No configuration needed - just open the dashboard and start trading.
