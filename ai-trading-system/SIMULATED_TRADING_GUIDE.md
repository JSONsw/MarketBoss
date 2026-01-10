# 🎮 Simulated Paper Trading Environment

## Overview

You now have a **fully functional local paper trading simulator** that requires **no API credentials** and **no paid services**. It simulates realistic order execution, fills, slippage, and equity tracking.

---

## How It Works

### Mock Alpaca Client
**File**: `src/execution/mock_alpaca.py`

The simulator includes a `MockAlpacaClient` class that:
- ✅ Simulates market prices with realistic volatility (±0.5%)
- ✅ Fills orders with realistic slippage (0-2 basis points)
- ✅ Tracks account equity in real-time
- ✅ Maintains position records
- ✅ Logs all trades to JSONL
- ✅ Provides equity snapshots after each trade
- ✅ Has 95% order fill rate (5% simulated rejections)

### Features
1. **Realistic Order Simulation**
   - Fill delays (~2 sec per order)
   - Random slippage based on order side
   - Position management
   - Trade logging

2. **Account Tracking**
   - Cash balance
   - Portfolio value (cash + positions)
   - Buying power
   - Position history

3. **Market Price Simulation**
   - Random walk for each symbol
   - Predefined base prices for common stocks (AAPL, MSFT, SPY, etc.)
   - Realistic volatility

---

## Usage

### Run Simulated Paper Trading (No Credentials Needed!)

```bash
cd ai-trading-system
python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 20
```

**Output**:
```
======================================================================
Paper Trading Mode: SIMULATED
======================================================================

Signals loaded: 294
Max trades to execute: 20

[1/20] Executing signal: AAPL BUY
[2/20] Executing signal: MSFT SELL
...
[20/20] Executing signal: SPY BUY

======================================================================
Paper Trading Complete!
======================================================================
Mode: SIMULATED
Signals processed: 20
Trades executed: 20
Final portfolio value: $101,234.56
Final cash: $45,123.45
Buying power: $101,234.56
======================================================================

✓ Trades saved to: data/paper_trading_trades.jsonl
✓ Equity log saved to: data/paper_trading_equity.jsonl
```

### Switch to Real Alpaca (When Ready)

When you want to use real Alpaca paper trading:

```bash
# Set your API credentials
export APCA_API_KEY_ID="your_key"
export APCA_API_SECRET_KEY="your_secret"

# Run with --real flag
python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 50 --real
```

---

## Output Files

### Paper Trading Trades (`data/paper_trading_trades.jsonl`)

Each line is a JSON record:
```json
{
  "timestamp": "2026-01-09T18:42:00.000Z",
  "signal_timestamp": "2025-01-01T12:00:00.000Z",
  "order_id": "abc-123-def",
  "symbol": "AAPL",
  "side": "BUY",
  "qty": 10,
  "filled_price": 150.25,
  "status": "filled"
}
```

### Paper Trading Equity (`data/paper_trading_equity.jsonl`)

Equity snapshot after each trade:
```json
{
  "timestamp": "2026-01-09T18:42:00.000Z",
  "cash": 95000.00,
  "portfolio_value": 105250.30,
  "buying_power": 105250.30,
  "equity_multiplier": 1.0
}
```

---

## Simulation Features

### Realistic Slippage
- Buy orders: +0 to +2 bps
- Sell orders: -0 to -2 bps
- Randomized to simulate real market conditions

### Position Management
- Tracks average fill prices
- Updates on buys and sells
- Closes positions when qty → 0
- Calculates MTM value in portfolio

### Market Prices
Predefined base prices that evolve with random walk:
- **AAPL**: $150.00
- **MSFT**: $380.00
- **GOOGL**: $140.00
- **TSLA**: $250.00
- **SPY**: $450.00
- **QQQ**: $380.00
- **IWM**: $200.00

You can extend with more symbols by editing `mock_alpaca.py`.

### Performance Tracking
- Starting cash: $100,000 (configurable)
- Real-time equity updates
- Cash tracking
- Buying power calculation
- Return calculations

---

## Comparison: Simulated vs Real

| Feature | Simulated | Real Alpaca |
|---------|-----------|------------|
| **Cost** | Free ✅ | Free (paper) ✅ |
| **Speed** | Instant ✅ | Realistic delays |
| **Market Hours** | Always open ✅ | 9:30-16:00 ET |
| **API Credentials** | None needed ✅ | Required |
| **Slippage** | Simulated | Real |
| **Realism** | High | Very High |
| **Testing** | Perfect ✅ | Live validation |

---

## Workflow

### Step 1: Test Strategy Locally (Simulated)
```bash
# No credentials, no waiting for market hours
python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 50
```

### Step 2: View Results in Dashboard
```bash
streamlit run dashboard/app.py
```

Dashboard shows:
- Simulated equity curve
- Backtest vs simulated comparison
- All trades executed
- Real-time metrics

### Step 3: Go Live (When Ready)
```bash
# Switch to real Alpaca when confident
python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 50 --real
```

---

## Extending the Simulator

### Add New Symbols

Edit `src/execution/mock_alpaca.py`:

```python
self.market_prices: Dict[str, float] = {
    "AAPL": 150.00,
    "MSFT": 380.00,
    "YOUR_SYMBOL": 100.00,  # Add here
}
```

### Change Starting Capital

```bash
python scripts/run_paper_trading.py --initial-cash 50000 --signals data/signals.jsonl --max-trades 20
```

### Adjust Fill Delay

Edit `src/execution/mock_alpaca.py`:

```python
executor = PaperTradingExecutor(use_real=False)
# Or in init: fill_delay_sec=5.0  # 5 second delays instead of 2
```

---

## Example Run

```bash
# Run 20 simulated trades
python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 20

# Check results
cat data/paper_trading_trades.jsonl | head -3
cat data/paper_trading_equity.jsonl | tail -5

# View in dashboard
streamlit run dashboard/app.py
```

---

## Benefits

✅ **No API Costs** - Free to test unlimited times  
✅ **No Market Hours** - Run 24/7, any time  
✅ **No Credentials** - Zero security risk during testing  
✅ **Instant Testing** - Quick iteration on strategies  
✅ **Reproducible** - Same signals = predictable results  
✅ **Education** - Learn how orders work  
✅ **Safe** - No real money at risk  

---

## Next Steps

1. **Try it now**: 
   ```bash
   python scripts/run_paper_trading.py --signals data/signals.jsonl --max-trades 20
   ```

2. **View results**: 
   ```bash
   streamlit run dashboard/app.py
   ```

3. **Iterate**: Modify strategies and re-test instantly

4. **Go live**: When confident, set real credentials and use `--real` flag

---

## Summary

You have a complete, **free, local paper trading simulator** with:
- ✅ Realistic order fills
- ✅ Slippage simulation
- ✅ Equity tracking
- ✅ Trade logging
- ✅ Dashboard integration
- ✅ Easy transition to real trading

No API credentials, no paid service, no waiting for market hours. Perfect for testing and learning!
