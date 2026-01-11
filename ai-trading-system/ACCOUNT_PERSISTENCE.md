# Account Persistence Feature

## Overview

The account persistence system ensures your trading account balance, positions, and performance metrics carry forward across trading sessions. Instead of resetting to $100,000 every time you restart the dashboard or trading process, the system now maintains continuous state.

## Problem Solved

**Before:** Every time the trading dashboard or continuous trading process restarted, the account reset to $100,000, making it impossible to track algorithmic performance over time.

**After:** Account state (portfolio value, cash, positions, trades) persists to disk and automatically loads on restart.

## How It Works

### 1. Account State File

State is saved to: `data/account_state.json`

```json
{
  "last_updated": "2026-01-10T20:30:57.550237+00:00",
  "cash": 110000.0,
  "portfolio_value": 110000.0,
  "positions": {},
  "trades_count": 8,
  "session_count": 2
}
```

### 2. Automatic Persistence

**On Session Start:**
- System checks if `data/account_state.json` exists
- If exists: Loads saved `portfolio_value` as starting capital
- If not: Uses default $100,000

**On Session End:**
- Automatically saves current cash, portfolio value, positions, trade count
- Increments session count

**Example Flow:**
```
Session 1: Start $100k → Trade → End $105k → SAVE
Session 2: Load $105k → Trade → End $108k → SAVE
Session 3: Load $108k → Trade → End $112k → SAVE
```

## Usage

### Starting Trading (Automatic)

When you start trading via the dashboard or `run_continuous_trading.py`, persistence is **enabled by default**:

```python
from src.execution.trading_engine import run_live_trading

# Persistence enabled automatically
run_live_trading(
    symbols=["SPY"],
    use_persistence=True  # ← Default
)
```

**Output on First Run:**
```
📊 Starting new account - Initial capital: $100,000.00
```

**Output on Subsequent Runs:**
```
📊 Resuming existing account:
   Session #3
   Last updated: 2026-01-10T14:23:15+00:00
   Portfolio value: $108,532.45
   Cash balance: $106,234.12
   Total trades (lifetime): 127
```

### Viewing Account State

Check current account status without starting trading:

```bash
python scripts/manage_account_state.py --view
```

**Output:**
```
======================================================================
ACCOUNT STATE
======================================================================
Last Updated:     2026-01-10T20:30:57.550237+00:00
Session Count:    3
Lifetime Trades:  127

Portfolio Value:  $108,532.45
Cash Balance:     $106,234.12

Open Positions:   SPY: 8 shares @ $295.39 avg
======================================================================
```

### Resetting Account

To start fresh with a new $100,000 account:

```bash
python scripts/manage_account_state.py --reset
```

**Interactive Confirmation:**
```
⚠️  WARNING: This will reset your account to initial capital!

Current State:
  Portfolio Value: $108,532.45
  Cash Balance:    $106,234.12
  Lifetime Trades: 127
  Sessions:        3

Type 'yes' to confirm reset: yes

✅ Account state reset to $100,000.00
```

### Custom Initial Capital

Reset with a specific amount:

```bash
python scripts/manage_account_state.py --reset --initial-cash 50000
```

## Implementation Details

### Core Components

**1. AccountStateManager (`src/execution/account_persistence.py`)**
- `save_state()`: Persist account to JSON
- `load_state()`: Restore account from JSON
- `get_initial_cash()`: Get starting capital (saved or default)
- `reset_state()`: Wipe account back to initial capital

**2. LiveTradingEngine Integration (`src/execution/trading_engine.py`)**
- Constructor: Creates `AccountStateManager` instance
- `save_account_state()`: Called at end of session to persist state
- `run_live_trading()`: Loads saved state if `use_persistence=True`

**3. CLI Tool (`scripts/manage_account_state.py`)**
- `--view`: Display current account state
- `--reset`: Reset account to initial capital
- `--initial-cash N`: Set custom initial capital

### Session Lifecycle

```
┌─────────────────────────────────────────────────┐
│ Session Start                                   │
├─────────────────────────────────────────────────┤
│ 1. Check for data/account_state.json           │
│ 2. If exists:                                   │
│    - Load portfolio_value as starting_capital   │
│    - Display resume message                     │
│ 3. If not exists:                               │
│    - Use default $100,000                       │
│    - Display new account message                │
│ 4. Create LiveTradingEngine(starting_capital)   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Trading Active                                  │
├─────────────────────────────────────────────────┤
│ - Process signals                               │
│ - Execute trades                                │
│ - Update positions                              │
│ - Track cash/portfolio value                    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Session End (Stop Button / Process Exit)       │
├─────────────────────────────────────────────────┤
│ 1. Call engine.save_account_state()             │
│ 2. Write to data/account_state.json:            │
│    - cash                                       │
│    - portfolio_value                            │
│    - positions                                  │
│    - trades_count (incremental)                 │
│    - session_count (incremented)                │
│ 3. Display "Account state saved" message        │
└─────────────────────────────────────────────────┘
```

## Performance Tracking

With persistence enabled, you can now:

1. **Track Multi-Day Performance**
   ```
   Day 1: $100k → $102k (+2%)
   Day 2: $102k → $105k (+2.9%)
   Day 3: $105k → $103k (-1.9%)
   Overall: $100k → $103k (+3%)
   ```

2. **Monitor Lifetime Trade Count**
   - Trades accumulate across sessions
   - View total trades in account state

3. **Session Statistics**
   - Track how many sessions run
   - Compare session-by-session performance

4. **Position Continuity**
   - Open positions carry forward
   - System remembers overnight positions

## Safety Features

1. **Automatic Backup**: Consider backing up `account_state.json` periodically
2. **Confirmation Required**: Reset command requires explicit "yes" confirmation
3. **State Validation**: System validates JSON structure on load
4. **Default Fallback**: If state file corrupted, falls back to default $100k

## Disabling Persistence (Not Recommended)

To disable persistence (always start with $100k):

```python
run_live_trading(
    symbols=["SPY"],
    use_persistence=False  # ← Disable persistence
)
```

**Use cases for disabling:**
- Testing new strategies in isolation
- Running parallel backtests
- Debugging without affecting main account

## Testing

Test persistence with the included test script:

```bash
python test_account_persistence.py
```

**Expected Output:**
```
✅ All persistence tests passed!

📌 Key Points:
   - Session 1: $100k → $105k (+$5k)
   - Session 2: $105k → $110k (+$5k)
   - Session 3 would start: $110k
   - Total gain over 2 sessions: +$10k (+10%)

💡 Account state persists across restarts!
```

## Troubleshooting

### Account Not Persisting

**Check 1:** Verify state file exists
```bash
ls -la data/account_state.json
```

**Check 2:** Check file permissions
```bash
# Windows
icacls data\account_state.json

# Linux/Mac
ls -l data/account_state.json
```

**Check 3:** Verify persistence enabled
```python
# In trading_engine.py, check run_live_trading() call
run_live_trading(..., use_persistence=True)  # Should be True
```

### State File Corrupted

**Symptom:** Error loading account state

**Solution 1:** Reset account
```bash
python scripts/manage_account_state.py --reset
```

**Solution 2:** Manual fix
```bash
# Backup corrupted file
mv data/account_state.json data/account_state.json.bak

# System will create fresh state on next run
```

### Starting Capital Wrong

**Symptom:** System starts with unexpected amount

**Cause:** State file contains different portfolio value

**Solution:** View current state, then reset if needed
```bash
python scripts/manage_account_state.py --view
python scripts/manage_account_state.py --reset
```

## Migration from Old System

If you have existing trading data from before persistence was implemented:

1. **Start Fresh (Recommended):**
   ```bash
   # Backup old data
   cp -r data/ data_backup_$(date +%Y%m%d)/
   
   # Clear trading files
   rm data/live_trading_*.jsonl
   
   # Start new account
   python scripts/manage_account_state.py --reset
   ```

2. **Preserve History:**
   - Old trades in `data/backup_*` folders remain intact
   - New persistence system starts from next session
   - Historical analysis still possible from backup files

## Best Practices

1. **Monitor Account State:**
   ```bash
   # Check state before/after trading
   python scripts/manage_account_state.py --view
   ```

2. **Periodic Resets:**
   - Reset account monthly/quarterly to avoid drift
   - Allows comparing strategy performance in isolation

3. **Backup State File:**
   ```bash
   # Daily backup
   cp data/account_state.json backups/account_state_$(date +%Y%m%d).json
   ```

4. **Track Session Performance:**
   - Note starting/ending portfolio value each session
   - Calculate session returns: `(end - start) / start * 100`

## Summary

✅ **Enabled by Default**: Persistence works automatically  
✅ **Cross-Session Tracking**: Performance accumulates over time  
✅ **Simple Management**: CLI tool for viewing/resetting state  
✅ **Robust**: Falls back to defaults if state file missing  
✅ **Tested**: Comprehensive test suite validates functionality  

**Next Steps:**
1. Start trading via dashboard: Account persists automatically
2. View state anytime: `python scripts/manage_account_state.py --view`
3. Reset when needed: `python scripts/manage_account_state.py --reset`
