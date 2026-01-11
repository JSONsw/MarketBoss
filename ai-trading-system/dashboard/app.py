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
from dashboard.trade_feed import TradeFeedViewer, render_trade_feed_sidebar

# Try to import strategy configuration
try:
    from src.execution.strategy_config import StrategyManager
    STRATEGY_SUPPORT = True
except ImportError:
    STRATEGY_SUPPORT = False
    logger.warning("Strategy configuration not available")

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
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON at line {line_num} in {path}")
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


def load_market_df(path: Path, use_yahoo: bool = False, symbol: str = "SPY", days: int = 60) -> pd.DataFrame:
    """Load market data from JSONL file or fetch from Yahoo Finance.
    
    If use_yahoo is False and path doesn't exist, automatically fetches from Yahoo Finance
    and caches the data to the path.
    """
    if use_yahoo:
        return fetch_yahoo_finance_data(symbol, days=days)
    
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
st.set_page_config(page_title="MarketBoss Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("📊 MarketBoss Dashboard")

# Initialize session state for trading controls
if 'trading_symbol' not in st.session_state:
    st.session_state.trading_symbol = "SPY"
if 'is_trading' not in st.session_state:
    st.session_state.is_trading = False
if 'trading_process' not in st.session_state:
    st.session_state.trading_process = None
if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = "intraday"
if 'data_interval' not in st.session_state:
    st.session_state.data_interval = "5m"
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Auto-refresh using Streamlit's native rerun (preserves UI state)
if time.time() - st.session_state.last_refresh > 60:
    st.session_state.last_refresh = time.time()
    st.rerun()

with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Strategy Selection
    if STRATEGY_SUPPORT:
        st.subheader("📈 Trading Strategy")
        try:
            strategy_mgr = StrategyManager()
            available_strategies = list(strategy_mgr.list_strategies().keys())
            
            # Initialize selected_strategy in session state if needed
            if 'selected_strategy' not in st.session_state or st.session_state.selected_strategy not in available_strategies:
                st.session_state.selected_strategy = available_strategies[0]
            
            # Callback function to update data interval when strategy changes
            def on_strategy_change():
                strategy = strategy_mgr.get_strategy(st.session_state.selected_strategy)
                st.session_state.data_interval = strategy.data_interval
            
            # Use selectbox with key parameter to bind directly to session state
            st.selectbox(
                "Select Strategy",
                options=available_strategies,
                key='selected_strategy',  # Binds directly to st.session_state.selected_strategy
                on_change=on_strategy_change,
                help="Choose trading timeframe: intraday (5m), swing (1h), weekly (1d), monthly (1d)"
            )
            
            # Display strategy info (always load current strategy from session state)
            strategy = strategy_mgr.get_strategy(st.session_state.selected_strategy)
            with st.expander("ℹ️ Strategy Details", expanded=False):
                st.write(f"**{strategy.name}**")
                st.write(f"📊 Interval: {strategy.data_interval}")
                st.write(f"📉 MA Periods: {strategy.ma_fast_period}/{strategy.ma_slow_period}")
                st.write(f"⏱️ Cooldown: {strategy.min_cooldown_minutes}min")
                st.write(f"🎯 Min Confidence: {strategy.min_confidence}%")
                st.write(f"💰 Risk per Trade: {strategy.risk_percent}%")
        except Exception as e:
            st.error(f"Strategy loading error: {e}")
            st.session_state.selected_strategy = "intraday"
    else:
        st.warning("Strategy config not available")
        st.session_state.selected_strategy = "intraday"
    
    st.divider()
    
    # Market Data Source Selection
    st.subheader("📊 Market Data")
    data_source = st.radio(
        "Data Source",
        ["Yahoo Finance (Real-time)", "JSONL File (Historical)"],
        index=0,
        help="Real-time fetches live data, JSONL uses cached historical data"
    )
    
    if data_source == "Yahoo Finance (Real-time)":
        use_yahoo = True
        symbol = st.text_input("Symbol", st.session_state.trading_symbol, key="symbol_input")
        if symbol != st.session_state.trading_symbol:
            st.session_state.trading_symbol = symbol
        
        # Strategy-aware lookback period
        if STRATEGY_SUPPORT and 'strategy' in locals():
            default_days = strategy.lookback_days
            st.caption(f"Strategy default: {default_days} days")
        else:
            default_days = 60
        
        days = st.number_input("Days of history", min_value=1, max_value=730, value=default_days)
        market_path = None
    else:
        use_yahoo = False
        symbol = st.session_state.trading_symbol
        market_path = Path(st.text_input("Market data JSONL", "data/market_data.jsonl"))
    
    st.divider()
    
    # Trading Control Section
    st.subheader("🎮 Trading Controls")
    st.write(f"**Symbol:** {st.session_state.trading_symbol}")
    if STRATEGY_SUPPORT:
        st.write(f"**Strategy:** {st.session_state.selected_strategy.title()}")
    
    col_trader1, col_trader2 = st.columns(2)
    
    with col_trader1:
        if st.button("🚀 Start Trading", key="start_trading", use_container_width=True):
            import subprocess
            import os
            import sys
            import json
            from datetime import datetime, timezone, timedelta
            
            # Always do fresh check for running processes (don't trust session state)
            running_processes = []
            try:
                result = subprocess.run(
                    ['powershell', '-Command', 
                     'Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like "*run_continuous_trading.py*"} | Select-Object ProcessId,CommandLine | ConvertTo-Json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != '[]':
                    try:
                        processes = json.loads(result.stdout)
                        if isinstance(processes, dict):
                            running_processes = [processes]
                        elif isinstance(processes, list):
                            running_processes = processes
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                logger.warning(f"Could not check for existing processes: {e}")
            
            # If processes found, check if they're actually active by checking file timestamp
            if running_processes:
                # Check if live_trading_updates.jsonl has recent updates (within last 5 minutes)
                updates_file = ROOT / "data" / "live_trading_updates.jsonl"
                is_actively_trading = False
                
                if updates_file.exists():
                    try:
                        # Get last line of file
                        with open(updates_file, 'r') as f:
                            lines = f.readlines()
                            if lines:
                                last_line = json.loads(lines[-1])
                                last_timestamp = datetime.fromisoformat(last_line['timestamp'].replace('Z', '+00:00'))
                                time_since_update = datetime.now(timezone.utc) - last_timestamp
                                
                                # If updates within last 5 minutes, consider it active
                                if time_since_update < timedelta(minutes=5):
                                    is_actively_trading = True
                    except Exception as e:
                        logger.warning(f"Could not check trading activity: {e}")
                        # If we can't check, assume process is active to be safe
                        is_actively_trading = True
                
                if is_actively_trading:
                    st.sidebar.warning(f"⚠️ Trading already running! Found {len(running_processes)} active process(es).")
                    st.sidebar.info("Click 'Stop Trading' first, then wait 2 seconds before starting again.")
                    for proc in running_processes[:3]:  # Show first 3
                        st.sidebar.text(f"PID: {proc.get('ProcessId')}")
                    # Update session state to match reality
                    st.session_state.is_trading = True
                    st.stop()
                else:
                    # Process exists but no recent updates - likely zombie/stale process
                    st.sidebar.warning(f"⚠️ Found stale trading process (no updates in 5+ minutes)")
                    st.sidebar.info("Killing stale process...")
                    for proc in running_processes:
                        pid = proc.get('ProcessId')
                        try:
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                                         capture_output=True, timeout=5)
                            st.sidebar.success(f"Killed stale process {pid}")
                        except Exception as e:
                            logger.warning(f"Could not kill process {pid}: {e}")
                    # Wait a moment then allow start
                    import time
                    time.sleep(1)
            
            # No processes running - safe to start
            # Clear any stale session state
            st.session_state.is_trading = False
            st.session_state.trading_process = None
            
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
                    # Add strategy if available
                    if STRATEGY_SUPPORT and st.session_state.selected_strategy:
                        cmd.extend(["--strategy", st.session_state.selected_strategy])
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
                    # Add strategy if available
                    if STRATEGY_SUPPORT and st.session_state.selected_strategy:
                        cmd.extend(["--strategy", st.session_state.selected_strategy])
                    process = subprocess.Popen(cmd, cwd=str(ROOT))
                
                st.session_state.trading_process = process.pid
                
                # Save PID to file for persistence across dashboard restarts
                pid_file = ROOT / "data" / ".trading_process.pid"
                pid_file.parent.mkdir(parents=True, exist_ok=True)
                with open(pid_file, 'w') as f:
                    f.write(str(process.pid))
                
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
            import subprocess
            import os
            
            try:
                killed_count = 0
                
                # Method 1: Try to kill process from PID file
                pid_file = ROOT / "data" / ".trading_process.pid"
                if pid_file.exists():
                    try:
                        with open(pid_file, 'r') as f:
                            saved_pid = int(f.read().strip())
                        
                        # Use /T to kill entire process tree (including children)
                        result = subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(saved_pid)],
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode == 0 or "SUCCESS" in result.stdout:
                            st.sidebar.success(f"✅ Stopped trading process tree {saved_pid}")
                            killed_count += 1
                        elif "not found" not in result.stderr.lower():
                            st.sidebar.warning(f"Process {saved_pid} may already be stopped")
                        
                        # Clean up PID file
                        pid_file.unlink()
                    except Exception as e:
                        logger.warning(f"Could not kill process from PID file: {e}")
                
                # Method 2: Try to kill process from session state
                if st.session_state.trading_process:
                    try:
                        # Use /T to kill entire process tree
                        result = subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(st.session_state.trading_process)],
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode == 0 or "SUCCESS" in result.stdout:
                            st.sidebar.success(f"✅ Stopped trading process tree {st.session_state.trading_process}")
                            killed_count += 1
                        elif "not found" not in result.stderr.lower():
                            st.sidebar.warning(f"Process {st.session_state.trading_process} may already be stopped")
                    except Exception as e:
                        logger.warning(f"Could not kill process from session: {e}")
                
                # Method 3: Find and kill all run_continuous_trading.py processes
                try:
                    # Use tasklist to find processes running our script
                    result = subprocess.run(
                        ['powershell', '-Command', 
                         'Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like "*run_continuous_trading.py*"} | Select-Object ProcessId,CommandLine | ConvertTo-Json'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != '[]':
                        import json
                        processes = json.loads(result.stdout)
                        
                        # Handle single process (not in array)
                        if isinstance(processes, dict):
                            processes = [processes]
                        
                        for proc in processes:
                            pid = proc['ProcessId']
                            # Use /T to kill entire process tree
                            kill_result = subprocess.run(
                                ["taskkill", "/F", "/T", "/PID", str(pid)], 
                                capture_output=True,
                                text=True
                            )
                            if kill_result.returncode == 0 or "SUCCESS" in kill_result.stdout:
                                st.sidebar.success(f"✅ Killed trading process tree {pid}")
                                killed_count += 1
                except Exception as e:
                    logger.warning(f"Could not search for trading processes: {e}")
                
                # Update state
                st.session_state.is_trading = False
                st.session_state.trading_process = None
                
                if killed_count == 0:
                    st.sidebar.warning("⚠️ No active trading processes found")
                else:
                    st.sidebar.success(f"✅ Stopped {killed_count} trading process(es)")
                    # Give processes time to fully terminate
                    import time
                    time.sleep(1.5)
                
                st.rerun()
                
            except Exception as e:
                st.sidebar.error(f"❌ Error stopping trading: {str(e)}")
                logger.error(f"Error stopping trading: {str(e)}", exc_info=True)
                st.session_state.is_trading = False
                st.session_state.trading_process = None
    
    # Status indicator
    if st.session_state.is_trading:
        st.sidebar.success(f"🟢 Trading active for {st.session_state.trading_symbol}")
    else:
        st.sidebar.info("⚫ Trading not active")
    
    # Add live trade feed to sidebar
    render_trade_feed_sidebar()
    
    st.divider()
    signals_path = Path(st.text_input("Signals JSONL", "data/signals.jsonl"))
    models_dir = Path(st.text_input("Models dir", "models"))
    paper_trading_path = Path(st.text_input("Paper trading equity log", "data/paper_trading_equity.jsonl"))
    initial_cash = st.number_input("Initial cash", value=100000.0, step=1000.0)

# Load data
if use_yahoo:
    with st.spinner(f"Fetching real-time data from Yahoo Finance for {symbol}..."):
        market_df = load_market_df(None, use_yahoo=True, symbol=symbol, days=days)
        if not market_df.empty:
            st.sidebar.success(f"✅ Loaded {len(market_df)} bars from Yahoo Finance (last {days} days)")
        else:
            st.sidebar.error("❌ Failed to fetch Yahoo Finance data")
else:
    market_df = load_market_df(market_path)
signals_df = load_signals_df(signals_path)
model_meta = load_latest_model_metadata(models_dir)

# Overview Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 Market Bars", f"{len(market_df):,}")
with col2:
    st.metric("🎯 Signals", f"{len(signals_df):,}")
with col3:
    if STRATEGY_SUPPORT:
        st.metric("⚡ Strategy", st.session_state.selected_strategy.title())
    else:
        st.metric("⚡ Interval", st.session_state.data_interval)
with col4:
    if model_meta:
        metrics = model_meta.get("metrics", {})
        st.metric("🎓 Model MSE", f"{metrics.get('avg_val_mse', 0):.6f}")
    else:
        st.metric("🎓 Model MSE", "-")

# Create tabbed interface for better organization
tab1, tab2, tab3, tab4 = st.tabs(["📈 Market Analysis", "🎯 Signals & Model", "💹 Live Trading", "📊 Performance"])

# TAB 1: Market Analysis
with tab1:
    data_source_label = f"Yahoo Finance ({symbol}) - Real-time" if use_yahoo else "Historical JSONL"
    st.subheader(f"Market Data - {data_source_label}")
    
    if market_df.empty:
        st.info("No market data found at the provided path.")
    else:
        # Show data freshness
        if not market_df.empty and hasattr(market_df.index, 'max'):
            latest_timestamp = market_df.index.max()
            st.caption(f"Latest data: {latest_timestamp} | Total bars: {len(market_df):,}")
        
        # Close price chart with real-time data
        col_title_price, col_help_price = st.columns([0.93, 0.07])
        with col_title_price:
            st.markdown("**📈 Closing Price Over Time (Real-Time)**")
        with col_help_price:
            with st.popover("ℹ️", use_container_width=True):
                st.write("Real-time closing prices from Yahoo Finance. Auto-refreshes every 60 seconds.")
        
        # Always fetch fresh data for the price chart (last 5 days for detailed view)
        realtime_price_df = fetch_yahoo_finance_data(symbol=symbol, days=min(5, days))  # Use up to 5 days or user selection
        
        if not realtime_price_df.empty:
            # Calculate ATL and ATH for closing prices
            close_min = realtime_price_df["close"].min()
            close_max = realtime_price_df["close"].max()
            close_range = close_max - close_min
            y_min = close_min - (close_range * 0.02)
            y_max = close_max + (close_range * 0.02)
            
            # Get current price and calculate change
            current_price = realtime_price_df["close"].iloc[-1]
            prev_price = realtime_price_df["close"].iloc[-2] if len(realtime_price_df) > 1 else current_price
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price * 100) if prev_price > 0 else 0
            
            # Display current price with change
            col_curr_price, col_change = st.columns(2)
            with col_curr_price:
                st.metric("💰 Current Price", f"${current_price:.2f}")
            with col_change:
                st.metric("📊 Change", f"${price_change:.2f}", f"{price_change_pct:+.2f}%")
            
            fig_close = go.Figure()
            fig_close.add_trace(go.Scatter(
                x=realtime_price_df.index, 
                y=realtime_price_df["close"], 
                mode='lines', 
                name='Close Price', 
                line=dict(color='#1f77b4', width=2)
            ))
            fig_close.update_layout(
                height=400, 
                yaxis_range=[y_min, y_max], 
                xaxis_title="Time", 
                yaxis_title="Price ($)", 
                showlegend=False, 
                template="plotly_white",
                uirevision='price_chart'  # Persist zoom/pan state across refreshes
            )
            st.plotly_chart(fig_close, use_container_width=True, key='price_chart')
            
            # Show last update time
            last_update = realtime_price_df.index[-1]
            st.caption(f"🕐 Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh in 60s")
        else:
            st.error("Failed to fetch real-time price data")
        
        # Volume chart - use the same data source (market_df is already loaded with user's days selection)
        col_title_vol, col_help_vol = st.columns([0.93, 0.07])
        with col_title_vol:
            st.markdown("**📊 Trading Volume**")
        with col_help_vol:
            with st.popover("ℹ️", use_container_width=True):
                st.write("Trading volume indicates liquidity and market interest. Higher volume = stronger moves.")
        
        # Use all available data from market_df (respects user's days selection)
        if not market_df.empty and "volume" in market_df.columns:
            volume_data = market_df["volume"].tail(200)
            vol_max = volume_data.max()
            
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(x=volume_data.index, y=volume_data, name='Volume', marker_color='#ff7f0e'))
            fig_vol.update_layout(
                height=300, 
                yaxis_range=[0, vol_max * 1.05], 
                xaxis_title="Time", 
                yaxis_title="Volume", 
                showlegend=False, 
                template="plotly_white",
                uirevision='volume_chart'  # Persist zoom/pan state across refreshes
            )
            st.plotly_chart(fig_vol, use_container_width=True, key='volume_chart')
        else:
            st.info("Volume data not available")
        
        # Returns statistics - use market_df which respects user's days selection
        if not market_df.empty and "close" in market_df.columns:
            returns = market_df["close"].pct_change().dropna()
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("📈 Mean Return", f"{returns.mean():.6f}")
            with col_stats2:
                st.metric("📊 Volatility", f"{returns.std():.6f}")
            with col_stats3:
                sharpe_est = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
                st.metric("⚡ Sharpe (Est)", f"{sharpe_est:.2f}")

# TAB 2: Signals & Model
with tab2:
    st.subheader("🎯 Signals")
    if signals_df.empty:
        st.info("No signals loaded. Generate signals using the signal generator.")
        st.code(f"python scripts/generate_sample_signals.py --strategy {st.session_state.selected_strategy}", language="bash")
    else:
        col_sig_title, col_sig_help = st.columns([0.93, 0.07])
        with col_sig_title:
            st.markdown(f"**Trade Signals Overview (Total: {len(signals_df)})**")
        with col_sig_help:
            with st.popover("ℹ️", use_container_width=True):
                st.write("Buy/Sell signals generated by the strategy. Columns: timestamp, symbol, side, quantity, price")
        
        # Show signal statistics
        if 'side' in signals_df.columns:
            buy_count = (signals_df['side'] == 'BUY').sum()
            sell_count = (signals_df['side'] == 'SELL').sum()
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("🟢 Buy Signals", buy_count)
            with col_s2:
                st.metric("🔴 Sell Signals", sell_count)
            with col_s3:
                ratio = buy_count / sell_count if sell_count > 0 else 0
                st.metric("📊 Buy/Sell Ratio", f"{ratio:.2f}")
        
        # Display recent signals
        st.markdown("**Recent Signals (Last 50)**")
        display_df = signals_df.tail(50).copy()
        if 'timestamp' in display_df.columns:
            display_df = display_df.sort_values('timestamp', ascending=False)
        st.dataframe(display_df, use_container_width=True, height=400)
    
    st.divider()
    
    # Model metrics
    st.subheader("🎓 Model Metrics (Latest)")
    if not model_meta:
        st.info("No model metadata found in models directory.")
    else:
        col_metrics_title, col_metrics_help = st.columns([0.93, 0.07])
        with col_metrics_title:
            st.markdown("**Validation Metrics**")
        with col_metrics_help:
            with st.popover("ℹ️", use_container_width=True):
                st.write("Performance metrics from model validation.")
        
        metrics = model_meta.get("metrics", {})
        if metrics:
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("MSE", f"{metrics.get('avg_val_mse', 0):.6f}")
            with col_m2:
                st.metric("MAE", f"{metrics.get('avg_val_mae', 0):.6f}")
            with col_m3:
                st.metric("R²", f"{metrics.get('avg_val_r2', 0):.4f}")
            with col_m4:
                st.metric("RMSE", f"{np.sqrt(metrics.get('avg_val_mse', 0)):.6f}")
        
        fi = model_meta.get("feature_importance", [])
        if fi:
            st.markdown("**🎯 Feature Importance**")
            fi_df = pd.DataFrame(fi)
            fi_df = fi_df.sort_values("importance", ascending=False).head(15)
            
            fig_fi = go.Figure()
            fig_fi.add_trace(go.Bar(x=fi_df["feature"], y=fi_df["importance"], name='Importance', marker_color='#2ca02c'))
            fig_fi.update_layout(height=350, xaxis_title="Feature", yaxis_title="Importance", showlegend=False, template="plotly_white")
            st.plotly_chart(fig_fi, use_container_width=True)
        
        st.caption(f"Metadata file: {model_meta.get('_path', 'N/A')}")

# TAB 3: Live Trading
with tab3:
    st.subheader("📈 Live Trading Monitor")
    
    # Add input for live trading equity log path
    col_live1, col_live2 = st.columns([3, 1])
    with col_live1:
        live_trading_equity_log = st.text_input(
            "Live Trading Equity Log",
            value="data/live_trading_equity.jsonl",
            help="Path to live trading equity updates (auto-refreshed)"
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
                st.write("Portfolio value updated tick-by-tick with mark-to-market pricing.")
        
        chart_data = lt_df[["portfolio_value"]].copy()
        chart_data.columns = ["Portfolio Value"]
        
        # Calculate ATL and ATH for portfolio value
        pv_min = chart_data["Portfolio Value"].min()
        pv_max = chart_data["Portfolio Value"].max()
        pv_range = pv_max - pv_min
        pv_y_min = pv_min - (pv_range * 0.02)
        pv_y_max = pv_max + (pv_range * 0.02)
        
        # Color based on performance
        line_color = '#2ca02c' if live_return_pct > 0 else '#d62728'
        
        fig_live = go.Figure()
        fig_live.add_trace(go.Scatter(x=chart_data.index, y=chart_data["Portfolio Value"], mode='lines', name='Portfolio Value', line=dict(color=line_color, width=2)))
        fig_live.update_layout(height=400, yaxis_range=[pv_y_min, pv_y_max], xaxis_title="Time", yaxis_title="Portfolio Value ($)", showlegend=False, template="plotly_white")
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
        st.info(f"🔄 Auto-refreshing | {len(live_equity_records)} snapshots | Last: {latest_update.get('update_type', 'TICK')}")
    
    else:
        st.warning("⚠️ Live trading not started or no data yet.")
        st.markdown("**To start live trading:**")
        st.code(
            f"# Start trading with {st.session_state.selected_strategy} strategy\n"
            f"python scripts/run_continuous_trading.py --symbol {symbol} --strategy {st.session_state.selected_strategy}",
            language="bash"
        )
        st.markdown("The live trading engine will:")
        st.markdown("- Process market data **tick-by-tick**")
        st.markdown("- Execute signals **algorithmically**")
        st.markdown("- Update equity with **real-time MTM**")

# TAB 4: Performance Analysis
with tab4:
    st.subheader("📊 Performance Analysis")
    
    # Backtest section
    st.markdown("### Quick Backtest")
    
    if signals_df.empty:
        st.info("Load signals to run quick backtest.")
        st.code(f"python scripts/generate_sample_signals.py --strategy {selected_strategy}", language="bash")
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
            c1.metric("💰 Total P&L", f"${bt['total_pnl']:.2f}")
            c2.metric("📈 Return", f"{bt['total_return_pct']:.2f}%")
            c3.metric("⚡ Sharpe", f"{bt['sharpe']:.3f}")
            
            col_dd1, col_dd2 = st.columns(2)
            with col_dd1:
                st.metric("📉 Max Drawdown", f"{bt['max_drawdown']:.2f}%")
            with col_dd2:
                st.metric("🎯 Total Trades", f"{len(signals_df)}")
            
            st.markdown("**💰 Equity Curve (Backtest)**")
            equity_series = pd.Series(bt["equity"], name="Equity")
            eq_min = equity_series.min()
            eq_max = equity_series.max()
            eq_range = eq_max - eq_min
            eq_y_min = eq_min - (eq_range * 0.02)
            eq_y_max = eq_max + (eq_range * 0.02)
            
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=list(range(len(equity_series))), y=equity_series, mode='lines', name='Equity', line=dict(color='#1f77b4', width=2)))
            fig_bt.update_layout(height=350, yaxis_range=[eq_y_min, eq_y_max], xaxis_title="Trade #", yaxis_title="Equity ($)", showlegend=False, template="plotly_white")
            st.plotly_chart(fig_bt, use_container_width=True)
    
    st.divider()
    
    # Comparison section
    st.markdown("### 📋 Backtest vs Live Trading Comparison")
    
    # Load live trading data for comparison
    live_trading_equity_path = Path("data/live_trading_equity.jsonl")
    live_equity_records = load_jsonl(live_trading_equity_path) if live_trading_equity_path.exists() else []
    live_trades_path = Path("data/live_trading_trades.jsonl")
    live_trades = load_jsonl(live_trades_path) if live_trades_path.exists() else []
    
    if "bt" in locals() and bt and live_equity_records:
        lt_df = pd.DataFrame(live_equity_records)
        lt_df["timestamp"] = pd.to_datetime(lt_df["timestamp"], errors="coerce")
        initial_pv = lt_df["portfolio_value"].iloc[0]
        current_pv = lt_df["portfolio_value"].iloc[-1]
        live_pnl = current_pv - initial_pv
        live_return_pct = (live_pnl / initial_pv) * 100
        
        cmp_col1, cmp_col2, cmp_col3 = st.columns(3)
        
        with cmp_col1:
            st.markdown("#### 📈 Backtest")
            st.metric("Return %", f"{bt['total_return_pct']:.2f}%")
            st.metric("Sharpe", f"{bt['sharpe']:.3f}")
            st.metric("Max DD %", f"{bt['max_drawdown']:.2f}%")
        
        with cmp_col2:
            st.markdown("#### 🟢 Live Trading")
            st.metric("Return %", f"{live_return_pct:.2f}%")
            st.metric("P&L $", f"${live_pnl:,.2f}")
            status = "✅ Profitable" if current_pv > initial_pv else "⚠️ Below initial"
            st.metric("Status", status)
        
        with cmp_col3:
            st.markdown("#### 📊 Impact")
            diff = live_return_pct - bt['total_return_pct']
            st.metric("Return Diff", f"{diff:+.2f}%")
            st.metric("Live Trades", len(live_trades))
            diff_reason = "Slippage/fills" if diff < 0 else "Better execution"
            st.metric("Reason", diff_reason)
    elif live_equity_records:
        st.info("💡 Run backtest first to see comparison. Live trading data is available.")
    elif "bt" in locals() and bt:
        st.info("💡 Live trading not started yet. Once running, comparison will appear here.")
    else:
        st.info("💡 Run backtest and start live trading to see performance comparison.")

# Footer
st.markdown("---")
st.caption("🚀 MarketBoss Dashboard | Multi-Timeframe Trading System")

# Live Trade Feed Section (collapsible at bottom)
st.markdown("---")
st.markdown("## 📡 Live Trade Feed")

# Create trade feed viewer
trade_feed_viewer = TradeFeedViewer(
    updates_path=Path("data/live_trading_updates.jsonl"),
    trades_path=Path("data/live_trading_trades.jsonl")
)

# Add expander for detailed view
with st.expander("📊 View Detailed Trade Feed", expanded=False):
    st.markdown("### Real-time Trading Activity Monitor")
    st.markdown("View all trading updates without opening the console window.")
    
    # Add tabs for different views
    feed_tab1, feed_tab2, feed_tab3 = st.tabs(["📈 Statistics", "📊 All Updates", "💹 Trades Only"])
    
    with feed_tab1:
        trade_feed_viewer.render_statistics()
    
    with feed_tab2:
        updates = trade_feed_viewer.load_recent_updates(limit=100)
        
        if not updates:
            st.info("No trading updates available. Start trading to see live activity.")
        else:
            # Show update count selector
            update_limit = st.slider("Number of updates to display", 10, 200, 50, step=10)
            
            # Load and display
            updates = trade_feed_viewer.load_recent_updates(limit=update_limit)
            df = pd.DataFrame(updates)
            
            # Format timestamp
            if 'timestamp' in df.columns:
                df['time'] = df['timestamp'].apply(trade_feed_viewer.format_timestamp)
                df = df[['time', 'update_type', 'portfolio_value', 'cash', 'positions', 'trades_executed']]
            
            # Rename columns
            df = df.rename(columns={
                'time': 'Time',
                'update_type': 'Type',
                'portfolio_value': 'Portfolio ($)',
                'cash': 'Cash ($)',
                'positions': 'Positions',
                'trades_executed': 'Total Trades'
            })
            
            # Format currency columns
            if 'Portfolio ($)' in df.columns:
                df['Portfolio ($)'] = df['Portfolio ($)'].apply(lambda x: f"${x:,.2f}")
            if 'Cash ($)' in df.columns:
                df['Cash ($)'] = df['Cash ($)'].apply(lambda x: f"${x:,.2f}")
            
            # Reverse to show newest first
            df = df.iloc[::-1].reset_index(drop=True)
            
            st.dataframe(df, use_container_width=True, height=400)
    
    with feed_tab3:
        trades = trade_feed_viewer.load_recent_trades(limit=100)
        
        if not trades:
            st.info("No trades executed yet. Start trading to see executed orders.")
        else:
            # Show trade count selector
            trade_limit = st.slider("Number of trades to display", 10, 200, 50, step=10)
            
            # Load and display
            trades = trade_feed_viewer.load_recent_trades(limit=trade_limit)
            df = pd.DataFrame(trades)
            
            # Format columns if they exist
            display_cols = []
            if 'timestamp' in df.columns:
                df['time'] = df['timestamp'].apply(trade_feed_viewer.format_timestamp)
                display_cols.append('time')
            
            for col in ['symbol', 'side', 'qty', 'price', 'portfolio_value']:
                if col in df.columns:
                    display_cols.append(col)
            
            if display_cols:
                df = df[display_cols]
                
                # Rename columns
                rename_map = {
                    'time': 'Time',
                    'symbol': 'Symbol',
                    'side': 'Side',
                    'qty': 'Qty',
                    'price': 'Price ($)',
                    'portfolio_value': 'Portfolio ($)'
                }
                df = df.rename(columns=rename_map)
                
                # Format currency
                if 'Price ($)' in df.columns:
                    df['Price ($)'] = df['Price ($)'].apply(lambda x: f"${x:,.2f}")
                if 'Portfolio ($)' in df.columns:
                    df['Portfolio ($)'] = df['Portfolio ($)'].apply(lambda x: f"${x:,.2f}")
                
                # Reverse to show newest first
                df = df.iloc[::-1].reset_index(drop=True)
                
                st.dataframe(df, use_container_width=True, height=400)

# Auto-refresh the dashboard every 2 seconds when live trading is active
if live_equity_records:
    import time
    time.sleep(2)
    st.rerun()
