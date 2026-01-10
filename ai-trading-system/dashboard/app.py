"""Streamlit dashboard for MarketBoss.

Features:
- Price/volume overview from market data JSONL
- Signals inspection
- Model metrics & feature importance (latest model)
- Quick backtest view using existing signals via run_backtest_mtm
- LIVE TRADING VIEW with real-time equity updates
- Backtest vs Live Trading comparison
- Auto-refresh to show live updates

Run:
    # Start live trading in one terminal:
    python scripts/run_live_trading.py
    
    # Then open dashboard in another:
    streamlit run dashboard/app.py
"""

import json
import glob
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Add project root to path for src imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import pytz

from src.backtesting.backtester import run_backtest_mtm
from src.monitoring.structured_logger import get_logger

logger = get_logger("dashboard")
# Project root (repo root two levels up from this file)
ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load records from a JSONL file, skipping blank/invalid lines."""
    if path is None:
        return []

    records: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON line in {path}")
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
    except Exception as e:
        logger.error(f"Error reading {path}: {e}", exc_info=True)
    return records


def fetch_yahoo_finance_data(symbol: str = "SPY", days: int = 60) -> pd.DataFrame:
    """Fetch accurate real-time market data from Yahoo Finance.
    Filters to regular market hours and renames columns.
    """
    try:
        import warnings
        warnings.filterwarnings('ignore')

        end_date = datetime.now().date() + timedelta(days=1)
        start_date = end_date - timedelta(days=days + 1)

        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="5m")
        if df.empty:
            df = ticker.history(start=start_date, end=end_date)

        if df.empty:
            st.error(f"No data returned for {symbol}")
            logger.error(f"No data returned for {symbol}")
            return pd.DataFrame()

        # Ensure index is datetime
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        df.index = df.index.tz_convert('US/Eastern')

        # Rename columns
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Add symbol column
        df['symbol'] = symbol

        logger.info(f"Fetched {len(df)} bars for {symbol}")
        return df[['symbol', 'open', 'high', 'low', 'close', 'volume']]

    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        logger.error(f"Yahoo Finance fetch failed: {str(e)}", exc_info=True)
        return pd.DataFrame()


def load_market_df(path: Path, use_yahoo: bool = False, symbol: str = "SPY") -> pd.DataFrame:
    """Load market data from JSONL file or fetch from Yahoo Finance.
    
    If use_yahoo is False and path doesn't exist, automatically fetches from Yahoo Finance
    and caches the data to the path.
    """
    if use_yahoo:
        return fetch_yahoo_finance_data(symbol)
    
    # If JSONL path doesn't exist, auto-fetch from Yahoo Finance
    if not path.exists():
        st.info(f"Market data file not found at {path}")
        st.info("Auto-fetching from Yahoo Finance...")
        df = fetch_yahoo_finance_data(symbol="SPY", days=60)
        
        # Cache the fetched data to the JSONL file
        if not df.empty:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                records = []
                for timestamp, row in df.iterrows():
                    record = {
                        'symbol': row.get('symbol', 'SPY'),
                        'timestamp': str(timestamp),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    }
                    records.append(record)
                
                with open(path, 'w') as f:
                    for record in records:
                        f.write(json.dumps(record) + '\n')
                st.success(f"✓ Cached {len(records)} bars to {path}")
                logger.info(f"Cached {len(records)} bars to {path}")
            except Exception as e:
                st.error(f"Failed to cache data: {e}")
                logger.error(f"Failed to cache data: {e}")
        return df
    
    # Load from existing JSONL file
    st.write(f"Loading data from {path}...")
    records = load_jsonl(path)
    if not records:
        st.warning(f"No records found in {path}")
        return pd.DataFrame()
    
    st.write(f"Loaded {len(records)} records")
    df = pd.DataFrame(records)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")
        df = df.set_index("timestamp")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    st.success(f"✓ Loaded {len(df)} bars from {path}")
    return df


@st.cache_data(show_spinner=False)
def load_signals_df(path: Path) -> pd.DataFrame:
    records = load_jsonl(path)
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")
    return df


@st.cache_data(show_spinner=False)
def load_latest_model_metadata(models_dir: Path) -> Dict[str, Any]:
    meta_files = sorted(models_dir.glob("*_metadata.json"))
    if not meta_files:
        return {}
    latest = meta_files[-1]
    try:
        with latest.open("r", encoding="utf-8") as f:
            data = json.load(f)
            data["_path"] = str(latest)
            return data
    except Exception:
        return {}


# ---------- Backtest helper ----------
def run_quick_backtest(signals_df: pd.DataFrame, prices: List[float], initial_cash: float) -> Dict[str, Any]:
    if signals_df.empty or not prices:
        return {}
    signals = signals_df.to_dict("records")
    results = run_backtest_mtm(
        signals=signals,
        market_prices=prices,
        slippage_bp=5.0,
        commission_pct=0.001,
        fixed_fee=0.0,
        initial_cash=initial_cash,
    )
    equity = [initial_cash]
    for r in results:
        equity.append(r.get("mtm", equity[-1]))
    returns = [equity[i] - equity[i - 1] for i in range(1, len(equity))]
    sharpe = 0.0
    if np.std(returns) > 0:
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
    dd = 0.0
    if equity:
        eq = np.array(equity)
        running_max = np.maximum.accumulate(eq)
        dd = float(np.max((running_max - eq) / running_max))
    return {
        "results": results,
        "equity": equity,
        "total_pnl": equity[-1] - equity[0],
        "total_return_pct": (equity[-1] - equity[0]) / equity[0] * 100,
        "sharpe": sharpe,
        "max_drawdown": dd * 100,
    }


# ---------- UI ----------
st.set_page_config(page_title="MarketBoss Dashboard", layout="wide")
st.title("MarketBoss Dashboard")

# Initialize session state for trading controls
if 'trading_symbol' not in st.session_state:
    st.session_state.trading_symbol = "SPY"
if 'is_trading' not in st.session_state:
    st.session_state.is_trading = False
if 'trading_process' not in st.session_state:
    st.session_state.trading_process = None

with st.sidebar:
    st.header("Data Sources & Trading")
    
    # Market Data Source Selection
    st.subheader("Market Data")
    data_source = st.radio(
        "Data Source",
        ["Yahoo Finance (Real-time)", "JSONL File (Historical)"],
        index=0
    )
    
    if data_source == "Yahoo Finance (Real-time)":
        use_yahoo = True
        symbol = st.text_input("Symbol", st.session_state.trading_symbol, key="symbol_input")
        # Update session state when symbol changes
        if symbol != st.session_state.trading_symbol:
            st.session_state.trading_symbol = symbol
        days = st.number_input("Days of history", min_value=1, max_value=365, value=60)
        market_path = None
    else:
        use_yahoo = False
        symbol = st.session_state.trading_symbol
        market_path = Path(st.text_input("Market data JSONL", "data/market_data.jsonl"))
    
    st.divider()
    
    # Trading Control Section
    st.subheader("📈 Trading Controls")
    st.write(f"**Currently selected:** {st.session_state.trading_symbol}")
    
    col_trader1, col_trader2 = st.columns(2)
    
    with col_trader1:
        if st.button("🚀 Start Trading", key="start_trading", use_container_width=True):
            import subprocess
            import os
            import sys
            
            # Normalize and store the current symbol from input (default SPY)
            current_symbol = (st.session_state.get("symbol_input", st.session_state.trading_symbol) or "SPY").upper()
            st.session_state.trading_symbol = current_symbol
            st.session_state.is_trading = True
            
            try:
                # Get the Python executable path
                python_exe = sys.executable
                
                # Build the command
                if os.name == 'nt':  # Windows
                    script_path = os.path.join(str(ROOT), "scripts", "run_continuous_trading.py")
                    cmd = [
                        "cmd", "/K",
                        python_exe,
                        script_path,
                        "--symbol", current_symbol,
                        "--interval", "300",
                        "--aggressive",
                        "--test-mode"
                    ]
                    process = subprocess.Popen(
                        cmd,
                        cwd=str(ROOT),
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:  # Unix/Linux
                    cmd = [
                        python_exe,
                        "scripts/run_continuous_trading.py",
                        "--symbol", current_symbol,
                        "--interval", "300",
                        "--aggressive",
                        "--test-mode"
                    ]
                    process = subprocess.Popen(cmd, cwd=str(ROOT))
                
                st.session_state.trading_process = process.pid
                st.sidebar.success(f"✅ Started trading {current_symbol}")
                st.sidebar.info(f"Process ID: {process.pid}")
                st.sidebar.info(f"Console window opened - check for trading output")
                st.sidebar.info(f"Command: {' '.join(cmd)}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Failed to start trading: {str(e)}")
                logger.error(f"Failed to start trading: {str(e)}")
                st.session_state.is_trading = False
    
    with col_trader2:
        if st.button("⏹️ Stop Trading", key="stop_trading", use_container_width=True):
            try:
                import subprocess
                # Kill only the specific trading process, not all Python processes
                if st.session_state.trading_process:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(st.session_state.trading_process)],
                        capture_output=True,
                        shell=True
                    )
                    st.sidebar.success(f"✅ Stopped trading process {st.session_state.trading_process}")
                else:
                    st.sidebar.warning("No active trading process to stop")
                
                st.session_state.is_trading = False
                st.session_state.trading_process = None
                st.rerun()
            except Exception as e:
                st.sidebar.warning(f"Could not stop trading: {str(e)}")
                st.session_state.is_trading = False
                st.session_state.trading_process = None
    
    # Status indicator
    if st.session_state.is_trading:
        st.sidebar.success(f"🟢 Trading active for {st.session_state.trading_symbol}")
    else:
        st.sidebar.info("⚫ Trading not active")
    
    st.divider()
    signals_path = Path(st.text_input("Signals JSONL", "data/signals.jsonl"))
    models_dir = Path(st.text_input("Models dir", "models"))
    paper_trading_path = Path(st.text_input("Paper trading equity log", "data/paper_trading_equity.jsonl"))
    initial_cash = st.number_input("Initial cash", value=100000.0, step=1000.0)

# Load data
if use_yahoo:
    with st.spinner(f"Fetching real-time data from Yahoo Finance for {symbol}..."):
        market_df = load_market_df(None, use_yahoo=True, symbol=symbol)
        if not market_df.empty:
            st.sidebar.success(f"✅ Loaded {len(market_df)} bars from Yahoo Finance")
        else:
            st.sidebar.error("❌ Failed to fetch Yahoo Finance data")
else:
    market_df = load_market_df(market_path)
signals_df = load_signals_df(signals_path)
model_meta = load_latest_model_metadata(models_dir)

# Overview
col1, col2, col3 = st.columns(3)
col1.metric("Market bars", f"{len(market_df):,}")
col2.metric("Signals", f"{len(signals_df):,}")
if model_meta:
    metrics = model_meta.get("metrics", {})
    col3.metric("Avg Val MSE", f"{metrics.get('avg_val_mse', 0):.6f}")
else:
    col3.metric("Avg Val MSE", "-")

# Price and volume
data_source_label = f"Yahoo Finance ({symbol}) - Real-time" if use_yahoo else "Historical JSONL"
st.subheader(f"Market Data - {data_source_label}")
if market_df.empty:
    st.info("No market data found at the provided path.")
else:
    # Show data freshness
    if not market_df.empty and hasattr(market_df.index, 'max'):
        latest_timestamp = market_df.index.max()
        st.caption(f"Latest data: {latest_timestamp} | Total bars: {len(market_df):,}")
    
    # Close price chart
    col_title_price, col_help_price = st.columns([0.93, 0.07])
    with col_title_price:
        st.markdown("**📈 Closing Price Over Time**")
    with col_help_price:
        with st.popover("ℹ️", use_container_width=True):
            st.write("Historical daily closing prices. Use for trend analysis and price movement identification.")
    
    # Calculate ATL and ATH for closing prices
    close_min = market_df["close"].min()
    close_max = market_df["close"].max()
    close_range = close_max - close_min
    # Add 2% padding for better visualization
    y_min = close_min - (close_range * 0.02)
    y_max = close_max + (close_range * 0.02)
    
    fig_close = go.Figure()
    fig_close.add_trace(go.Scatter(x=market_df.index, y=market_df["close"], mode='lines', name='Close Price'))
    fig_close.update_layout(height=500, yaxis_range=[y_min, y_max], xaxis_title="Time", yaxis_title="Price ($)", showlegend=False)
    st.plotly_chart(fig_close, use_container_width=True)
    
    # Volume chart
    col_title_vol, col_help_vol = st.columns([0.93, 0.07])
    with col_title_vol:
        st.markdown("**📊 Trading Volume (Last 200 Bars)**")
    with col_help_vol:
        with st.popover("ℹ️", use_container_width=True):
            st.write("Daily trading volume indicates liquidity and market interest. Higher volume = stronger moves.")
    
    # Volume chart should start at 0 and go to max
    volume_data = market_df["volume"].tail(200)
    vol_max = volume_data.max()
    
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(x=volume_data.index, y=volume_data, name='Volume'))
    fig_vol.update_layout(height=500, yaxis_range=[0, vol_max * 1.05], xaxis_title="Time", yaxis_title="Volume", showlegend=False)
    st.plotly_chart(fig_vol, use_container_width=True)
    
    # Returns statistics
    if "close" in market_df.columns:
        returns = market_df["close"].pct_change().dropna()
        col_stats1, col_stats2 = st.columns(2)
        with col_stats1:
            st.metric("Mean Daily Return", f"{returns.mean():.6f}")
        with col_stats2:
            st.metric("Daily Volatility", f"{returns.std():.6f}")

# Signals
st.subheader("Signals")
if signals_df.empty:
    st.info("No signals loaded. Use the generator or provide a signals JSONL.")
else:
    col_sig_title, col_sig_help = st.columns([0.93, 0.07])
    with col_sig_title:
        st.markdown(f"**🎯 Trade Signals (Last 50 of {len(signals_df)})**")
    with col_sig_help:
        with st.popover("ℹ️", use_container_width=True):
            st.write("Buy/Sell signals generated by the ML model. Columns: timestamp, symbol, side, quantity, price")
    st.write(signals_df.tail(50))

# Model metrics
st.subheader("Model Metrics (Latest)")
if not model_meta:
    st.info("No model metadata found in models directory.")
else:
    col_metrics_title, col_metrics_help = st.columns([0.93, 0.07])
    with col_metrics_title:
        st.markdown("**📊 Validation Metrics**")
    with col_metrics_help:
        with st.popover("ℹ️", use_container_width=True):
            st.write("Performance metrics from model validation. Includes MSE, MAE, R2, and other accuracy measures.")
    metrics = model_meta.get("metrics", {})
    st.json(metrics)
    
    fi = model_meta.get("feature_importance", [])
    if fi:
        col_fi_title, col_fi_help = st.columns([0.93, 0.07])
        with col_fi_title:
            st.markdown("**🎯 Feature Importance**")
        with col_fi_help:
            with st.popover("ℹ️", use_container_width=True):
                st.write("Relative importance of features for price prediction. Sorted by importance (highest first).")
        fi_df = pd.DataFrame(fi)
        fi_df = fi_df.sort_values("importance", ascending=False)
        # Calculate y-axis range for feature importance
        fi_min = fi_df["importance"].min()
        fi_max = fi_df["importance"].max()
        fi_range = fi_max - fi_min
        fi_y_min = max(0, fi_min - (fi_range * 0.02))  # Don't go below 0
        fi_y_max = fi_max + (fi_range * 0.02)
        
        fig_fi = go.Figure()
        fig_fi.add_trace(go.Bar(x=fi_df["feature"], y=fi_df["importance"], name='Importance'))
        fig_fi.update_layout(height=400, yaxis_range=[fi_y_min, fi_y_max], xaxis_title="Feature", yaxis_title="Importance", showlegend=False)
        st.plotly_chart(fig_fi, use_container_width=True)
    st.caption(f"Metadata file: {model_meta.get('_path', 'N/A')}")

# Backtest quick view
st.subheader("Quick Backtest (using current signals)")
if signals_df.empty:
    st.info("Load signals to run quick backtest.")
else:
    # Use signal prices if available; otherwise, align to market close series
    if "price" in signals_df.columns:
        prices = signals_df["price"].astype(float).tolist()
    elif not market_df.empty and "close" in market_df.columns:
        prices = market_df["close"].iloc[: len(signals_df)].tolist()
    else:
        prices = []

    bt = run_quick_backtest(signals_df, prices, initial_cash)
    if not bt:
        st.info("Unable to run backtest (missing prices).")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total P&L", f"${bt['total_pnl']:.2f}", help="Net profit/loss from the backtest")
        c2.metric("Return", f"{bt['total_return_pct']:.2f}%", help="Total percentage return on initial capital")
        c3.metric("Sharpe", f"{bt['sharpe']:.3f}", help="Risk-adjusted return ratio (higher is better)")
        
        col_dd1, col_dd2 = st.columns(2)
        with col_dd1:
            st.metric("Max Drawdown", f"{bt['max_drawdown']:.2f}%", help="Largest peak-to-trough decline during backtest")
        with col_dd2:
            st.metric("Total Trades", f"{len(signals_df)}", help="Number of buy/sell signals executed")
        
        col_eq_title, col_eq_help = st.columns([0.93, 0.07])
        with col_eq_title:
            st.markdown("**💰 Equity Curve (Backtest)**")
        with col_eq_help:
            with st.popover("ℹ️", use_container_width=True):
                st.write("Portfolio value over time. Shows cumulative performance from initial capital.")
        equity_series = pd.Series(bt["equity"], name="Equity")
        # Calculate range for equity curve
        eq_min = equity_series.min()
        eq_max = equity_series.max()
        eq_range = eq_max - eq_min
        eq_y_min = eq_min - (eq_range * 0.02)
        eq_y_max = eq_max + (eq_range * 0.02)
        
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=list(range(len(equity_series))), y=equity_series, mode='lines', name='Equity'))
        fig_bt.update_layout(height=400, yaxis_range=[eq_y_min, eq_y_max], xaxis_title="Trade #", yaxis_title="Equity ($)", showlegend=False)
        st.plotly_chart(fig_bt, use_container_width=True)

# Live Trading view (Real-time with MTM updates)
st.subheader("📈 Live Trading (Real-time with Tick-by-tick Updates)")

# Add input for live trading equity log path
col_live1, col_live2 = st.columns([3, 1])
with col_live1:
    live_trading_equity_log = st.text_input(
        "Live Trading Equity Log",
        value="data/live_trading_equity.jsonl",
        help="Path to live trading equity updates (auto-refreshed every second)"
    )
with col_live2:
    refresh_interval = st.selectbox("Refresh", options=["1s", "2s", "5s"], index=0)

live_trading_equity_path = Path(live_trading_equity_log)

# Load live trading data without caching for real-time updates
def load_live_trading_data():
    """Load live trading equity log with real-time updates."""
    if live_trading_equity_path.exists():
        return load_jsonl(live_trading_equity_path)
    return []

def load_live_trading_trades():
    """Load executed trades with real-time updates."""
    trades_path = Path("data/live_trading_trades.jsonl")
    if trades_path.exists():
        return load_jsonl(trades_path)
    return []

live_equity_records = load_live_trading_data()
live_trades = load_live_trading_trades()

if live_equity_records:
    lt_df = pd.DataFrame(live_equity_records)
    lt_df["timestamp"] = pd.to_datetime(lt_df["timestamp"], errors="coerce")
    lt_df = lt_df.set_index("timestamp")
    
    # Calculate metrics
    initial_pv = lt_df["portfolio_value"].iloc[0]
    current_pv = lt_df["portfolio_value"].iloc[-1]
    live_pnl = current_pv - initial_pv
    live_return_pct = (live_pnl / initial_pv) * 100
    
    # Current status
    latest_update = lt_df.iloc[-1]
    last_update_time = lt_df.index[-1]
    
    # Metrics row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🎯 Current PV", f"${current_pv:,.2f}", delta=f"${live_pnl:,.2f}")
    m2.metric("📊 Return %", f"{live_return_pct:+.2f}%")
    m3.metric("💹 Trades", f"{len(live_trades)}", help=f"Algorithmic executions")
    
    # Status indicator
    status_icon = "🟢" if live_return_pct > 0 else "🔴"
    status_text = "Profitable" if live_return_pct > 0 else "Loss"
    m4.metric(f"{status_icon} Status", status_text)
    
    # Last update
    m5.metric("⏱️ Last Update", last_update_time.strftime("%H:%M:%S"))
    
    # Real-time equity curve with MTM on every tick
    col_title, col_pop = st.columns([0.93, 0.07])
    with col_title:
        st.markdown("**📈 Equity Curve (Real-time MTM)**")
    with col_pop:
        with st.popover("ℹ️", use_container_width=True):
            st.write("Portfolio value updated tick-by-tick with mark-to-market pricing. Green = profit, Red = loss.")
    chart_data = lt_df[["portfolio_value"]].copy()
    chart_data.columns = ["Portfolio Value"]
    
    # Calculate ATL and ATH for portfolio value
    pv_min = chart_data["Portfolio Value"].min()
    pv_max = chart_data["Portfolio Value"].max()
    pv_range = pv_max - pv_min
    pv_y_min = pv_min - (pv_range * 0.02)
    pv_y_max = pv_max + (pv_range * 0.02)
    
    fig_live = go.Figure()
    fig_live.add_trace(go.Scatter(x=chart_data.index, y=chart_data["Portfolio Value"], mode='lines', name='Portfolio Value'))
    fig_live.update_layout(height=500, yaxis_range=[pv_y_min, pv_y_max], xaxis_title="Time", yaxis_title="Portfolio Value ($)", showlegend=False)
    st.plotly_chart(fig_live, use_container_width=True)
    
    # Recent trades table
    if live_trades:
        col_trades_title, col_trades_pop = st.columns([0.93, 0.07])
        with col_trades_title:
            st.markdown("**📋 Recent Algorithmic Trades**")
        with col_trades_pop:
            with st.popover("ℹ️", use_container_width=True):
                st.write("Last 10 executed trades with timestamps, symbols, sides (BUY/SELL), quantities, fill prices, and status.")
        trades_df = pd.DataFrame(live_trades[-10:])  # Last 10 trades
        if "timestamp" in trades_df.columns:
            trades_df["timestamp"] = pd.to_datetime(trades_df["timestamp"], errors="coerce")
            # Handle column name variations (qty/quantity, filled_price/price)
            cols_to_select = []
            for col in ["timestamp", "symbol", "side"]:
                if col in trades_df.columns:
                    cols_to_select.append(col)
            if "qty" in trades_df.columns:
                cols_to_select.append("qty")
            elif "quantity" in trades_df.columns:
                cols_to_select.append("quantity")
            if "filled_price" in trades_df.columns:
                cols_to_select.append("filled_price")
            elif "price" in trades_df.columns:
                cols_to_select.append("price")
            if "status" in trades_df.columns:
                cols_to_select.append("status")
            
            trades_df = trades_df[cols_to_select]
            # Rename columns for display
            rename_map = {"timestamp": "Time", "symbol": "Symbol", "side": "Side", 
                         "qty": "Qty", "quantity": "Qty", "filled_price": "Fill Price", 
                         "price": "Price", "status": "Status"}
            trades_df.columns = [rename_map.get(col, col) for col in trades_df.columns]
            st.dataframe(trades_df, use_container_width=True, height=250)
        st.caption(f"Total trades executed: {len(live_trades)}")
    
    # Update frequency indicator
    st.info(f"🔄 Auto-refreshing every second | {len(live_equity_records)} equity snapshots recorded | Last: {latest_update.get('update_type', 'TICK')}")
    
else:
    st.warning("⚠️ Live trading not started or no data yet.")
    st.markdown("**To start live trading:**")
    st.code(
        "# Terminal 1: Start live trading engine\n"
        "python scripts/run_live_trading.py --market-data data/market_data.jsonl --signals data/signals.jsonl\n\n"
        "# Terminal 2: Start dashboard (it will auto-refresh)\n"
        "streamlit run dashboard/app.py",
        language="bash"
    )
    st.markdown("The live trading engine will:")
    st.markdown("- Process market data **tick-by-tick**")
    st.markdown("- Execute signals **algorithmically inline** with price updates")
    st.markdown("- Update equity on **every price movement** (MTM)")
    st.markdown("- Stream results to `live_trading_equity.jsonl` (auto-refreshed here)")

# Backtest vs Live Trading Comparison
st.markdown("---")
col_cmp_title, col_cmp_pop = st.columns([0.93, 0.07])
with col_cmp_title:
    st.subheader("📋 Backtest vs Live Trading Comparison")
with col_cmp_pop:
    with st.popover("ℹ️", use_container_width=True):
        st.write("Compare historical backtesting performance (ideal market conditions) vs real-time live trading (with slippage, fill delays, and realistic fills).")

if "bt" in locals() and bt and live_equity_records:
    st.divider()
    st.subheader("📊 Backtest vs Live Trading Comparison")
    
    cmp_col1, cmp_col2, cmp_col3 = st.columns(3)
    
    with cmp_col1:
        st.markdown("### 📈 Backtest (Ideal Conditions)")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Return %", f"{bt['total_return_pct']:.2f}%", help="Total % return on backtest period")
        with col_m2:
            st.metric("Sharpe", f"{bt['sharpe']:.3f}", help="Risk-adjusted return ratio")
        st.metric("Max DD %", f"{bt['max_drawdown']:.2f}%", help="Largest peak-to-trough drawdown")
    
    with cmp_col2:
        st.markdown("### 🟢 Live Trading (Real Conditions)")
        col_m3, col_m4 = st.columns(2)
        with col_m3:
            st.metric("Return %", f"{live_return_pct:.2f}%", help="Live return with slippage/fills")
        with col_m4:
            st.metric("P&L $", f"${live_pnl:,.2f}", help="Absolute profit or loss")
        status = "✅ Profitable" if current_pv > initial_pv else "⚠️ Below initial"
        st.metric("Status", status, help="Current profitability status")
    
    with cmp_col3:
        st.markdown("### 📊 Impact Analysis")
        col_m5, col_m6 = st.columns(2)
        with col_m5:
            diff = live_return_pct - bt['total_return_pct']
            st.metric("Return Diff %", f"{diff:+.2f}%", help="Performance gap (usually negative due to costs)")
        with col_m6:
            st.metric("Trades", len(live_trades), help="Executed via algorithmic engine")
        diff_reason = "Slippage/fills" if diff < 0 else "Better execution"
        st.metric("Reason", diff_reason, help="Why live trades differ from backtest")
        
elif live_equity_records:
    st.divider()
    st.info("💡 **Run backtest first** to see comparison. Live trading data is available.")
elif "bt" in locals() and bt:
    st.divider()
    st.info("💡 **Live trading not started yet.** Once running, comparison will appear here.")

st.caption("Run via: `streamlit run dashboard/app.py`")

# Auto-refresh the dashboard every 2 seconds when live trading is active
if live_equity_records:
    import time
    time.sleep(2)
    st.rerun()
