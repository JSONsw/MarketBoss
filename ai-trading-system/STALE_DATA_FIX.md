# Stale Market Data Fix

## Problem Identified

The algorithmic trading system was executing trades **when the market was closed**, using **stale data from the previous trading day**.

### Root Cause

The continuous trading loop had a **critical logic flaw** in [run_continuous_trading.py](scripts/run_continuous_trading.py):

**OLD (BROKEN) LOGIC:**
```python
def run():
    # 1. Fetch fresh market data (even when market is closed!)
    refresh_data()
    
    # 2. Then check if market is open
    if not is_market_open():
        skip trading
    
    # 3. Execute trades
    run_trading_session()
```

**Problem:** Yahoo Finance always returns the most recent data available. When queried at 8 PM, it returns 4 PM close data. This data is "fresh" from the API perspective but **stale for trading purposes**.

**Result:** System would fetch yesterday's closing prices and execute trades hours after market closed.

## Solution Implemented

### 1. Check Market Hours BEFORE Fetching Data

**Lines 164-177** - Added pre-fetch market hours validation:
```python
def refresh_data(self) -> bool:
    """Returns False if market is closed to prevent trading on stale data."""
    try:
        # Check if market is open BEFORE fetching data to avoid stale data
        if not self.test_mode and not is_market_open():
            logger.warning("Market is closed - skipping data refresh to avoid stale data")
            return False  # 🔴 Stop here - don't fetch or trade
        
        logger.info("Fetching fresh market data from Yahoo Finance")
        # ... proceed with data fetch only if market is open
```

### 2. Validate Data Freshness

**Lines 224-241** - Added 15-minute freshness check:
```python
# Validate data freshness - most recent bar should be within last 15 minutes
if not self.test_mode:
    latest_timestamp = df.index[-1]
    now_est = datetime.now(pytz.timezone('US/Eastern'))
    
    # Ensure latest_timestamp has timezone
    if latest_timestamp.tzinfo is None:
        latest_timestamp = est.localize(latest_timestamp)
    else:
        latest_timestamp = latest_timestamp.tz_convert(est)
    
    data_age_minutes = (now_est - latest_timestamp).total_seconds() / 60
    
    if data_age_minutes > 15:
        logger.error(
            f"Market data is stale (age: {data_age_minutes:.1f} minutes) - aborting refresh",
            extra={"latest_timestamp": str(latest_timestamp), "current_time": str(now_est)}
        )
        return False  # 🔴 Reject stale data
    
    logger.info(f"Data freshness validated: {data_age_minutes:.1f} minutes old")
```

### 3. Skip Trading Session If Data Refresh Fails

**Lines 365-370** - Improved error handling:
```python
if not self.refresh_data():
    logger.warning("Data refresh failed (market closed or stale data) - skipping trading session")
    # Wait and retry in next iteration
    time.sleep(min(self.interval, 300))  # Wait up to 5 minutes
    continue  # 🔴 Skip trading, loop back to check market status
```

### 4. Removed Redundant Market Hours Check

**Lines 292-297** - Simplified run_trading_session():
```python
def run_trading_session(self) -> Dict[str, Any]:
    """Execute one live trading session with current market price.
    
    Note: Market hours check is done in refresh_data() to prevent fetching stale data.
    """
    # No redundant market hours check here - already validated in refresh_data()
```

## How It Works Now

**NEW (FIXED) LOGIC:**
```
┌─────────────────────────────────────┐
│ Continuous Trading Loop             │
└─────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │ Is market    │  NO  ──▶ Wait 5 minutes, retry
    │ open?        │
    └──────────────┘
           │ YES
           ▼
    ┌──────────────┐
    │ Fetch market │
    │ data from    │
    │ Yahoo Finance│
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ Is data      │  NO  ──▶ Abort, wait, retry
    │ < 15 min old?│
    └──────────────┘
           │ YES
           ▼
    ┌──────────────┐
    │ Execute      │
    │ trades with  │
    │ fresh data   │
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ Wait until   │
    │ next interval│
    └──────────────┘
           │
           └──────▶ Loop back
```

## Behavior Changes

### Before Fix ❌
```bash
# At 8:00 PM (market closed)
[INFO] Fetching fresh market data
[INFO] Fetched 78 bars (last bar: 4:00 PM)  # ❌ 4 hours old!
[INFO] Market is closed, skipping trading session
# Still saved stale data to disk
```

### After Fix ✅
```bash
# At 8:00 PM (market closed)
[WARNING] Market is closed - skipping data refresh to avoid stale data
[WARNING] Data refresh failed (market closed or stale data) - skipping trading session
# ✅ No stale data fetched or saved
# ✅ No trades executed
```

### During Market Hours ✅
```bash
# At 2:30 PM (market open)
[INFO] Fetching fresh market data
[INFO] Fetched 78 bars (last bar: 2:25 PM)
[INFO] Data freshness validated: 5.0 minutes old  # ✅ Fresh!
[INFO] Starting trading session 1
[INFO] Current market price for SPY: $450.25
[INFO] Executed 2 trades
```

## Testing

### Test Mode Override
For testing outside market hours, use `--test-mode`:
```bash
python scripts/run_continuous_trading.py --test-mode
```

This bypasses market hours and freshness checks (useful for development).

### Manual Verification
Check logs for these key messages:

**Market Closed (Expected):**
```
[WARNING] Market is closed - skipping data refresh to avoid stale data
[WARNING] Data refresh failed (market closed or stale data) - skipping trading session
```

**Market Open (Expected):**
```
[INFO] Fetching fresh market data from Yahoo Finance
[INFO] Data freshness validated: X.X minutes old
[INFO] Starting trading session N
```

**Stale Data Detected (Edge Case):**
```
[ERROR] Market data is stale (age: 23.5 minutes) - aborting refresh
```

## Market Hours Reference

**US Stock Market (NYSE/NASDAQ):**
- **Trading Hours:** 9:30 AM - 4:00 PM ET
- **Weekdays Only:** Monday-Friday
- **Closed:** Weekends and market holidays

**Data Freshness Threshold:**
- Maximum age: **15 minutes**
- Ensures trades execute on near real-time data
- Prevents execution on delayed or cached prices

## Files Changed

| File | Lines | Changes |
|------|-------|---------|
| [run_continuous_trading.py](scripts/run_continuous_trading.py) | 164-177 | Added market hours pre-check in `refresh_data()` |
| [run_continuous_trading.py](scripts/run_continuous_trading.py) | 224-241 | Added 15-minute freshness validation |
| [run_continuous_trading.py](scripts/run_continuous_trading.py) | 292-297 | Removed redundant market hours check |
| [run_continuous_trading.py](scripts/run_continuous_trading.py) | 365-370 | Improved error handling with sleep/retry |

## Impact

### Before
- ❌ Traded on stale data outside market hours
- ❌ Executed trades with 4+ hour old prices
- ❌ Risk of significant slippage and losses
- ❌ Incorrect equity calculations

### After
- ✅ Only trades during market hours (9:30 AM - 4:00 PM ET)
- ✅ Data must be < 15 minutes old
- ✅ Automatically waits and retries when market closed
- ✅ Real-time price accuracy for trade execution
- ✅ Test mode available for development

## Deployment

No configuration changes needed - the fix is automatic. Restart the continuous trading script:

```bash
# Normal production mode (respects market hours)
python scripts/run_continuous_trading.py

# Development mode (bypasses market hours check)
python scripts/run_continuous_trading.py --test-mode
```

---

**Issue:** Stale market data trading  
**Status:** ✅ Fixed  
**Date:** January 10, 2026  
**Impact:** High (prevents trading losses from stale data)
