"""Real-time Trade Feed Viewer for MarketBoss Dashboard.

Displays live trading activity without requiring a console window.
Reads from live_trading_updates.jsonl and streams updates in real-time.

Usage:
    Add to dashboard sidebar or as a separate tab
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import streamlit as st
import pandas as pd


class TradeFeedViewer:
    """Real-time trade feed viewer component."""
    
    def __init__(self, updates_path: Path = None, trades_path: Path = None):
        """Initialize trade feed viewer.
        
        Args:
            updates_path: Path to live_trading_updates.jsonl
            trades_path: Path to live_trading_trades.jsonl
        """
        self.updates_path = updates_path or Path("data/live_trading_updates.jsonl")
        self.trades_path = trades_path or Path("data/live_trading_trades.jsonl")
    
    def load_recent_updates(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Load most recent trading updates.
        
        Args:
            limit: Number of recent updates to load
            
        Returns:
            List of update dictionaries
        """
        if not self.updates_path.exists():
            return []
        
        updates = []
        try:
            with open(self.updates_path, 'r') as f:
                # Read all lines
                lines = f.readlines()
                # Take last N lines
                for line in lines[-limit:]:
                    line = line.strip()
                    if line:
                        try:
                            updates.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            st.error(f"Error loading updates: {e}")
        
        return updates
    
    def load_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Load most recent executed trades.
        
        Args:
            limit: Number of recent trades to load
            
        Returns:
            List of trade dictionaries
        """
        if not self.trades_path.exists():
            return []
        
        trades = []
        try:
            with open(self.trades_path, 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    line = line.strip()
                    if line:
                        try:
                            trades.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            st.error(f"Error loading trades: {e}")
        
        return trades
    
    def format_timestamp(self, ts_str: str) -> str:
        """Format timestamp to readable string.
        
        Args:
            ts_str: ISO format timestamp string
            
        Returns:
            Formatted time string
        """
        try:
            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            return dt.strftime('%H:%M:%S')
        except:
            return ts_str
    
    def render_compact_feed(self, limit: int = 20):
        """Render compact live feed view (minimal).
        
        Args:
            limit: Number of recent updates to show
        """
        st.markdown("### 📡 Live Trade Feed")
        
        updates = self.load_recent_updates(limit=limit)
        
        if not updates:
            st.info("No trading activity yet. Start trading to see live updates.")
            return
        
        # Get latest status
        latest = updates[-1] if updates else None
        
        if latest:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Portfolio Value", f"${latest.get('portfolio_value', 0):,.2f}")
            
            with col2:
                st.metric("Cash", f"${latest.get('cash', 0):,.2f}")
            
            with col3:
                st.metric("Positions", latest.get('positions', 0))
            
            with col4:
                st.metric("Trades", latest.get('trades_executed', 0))
        
        # Show recent activity
        st.markdown("#### Recent Activity")
        
        # Create feed display
        feed_container = st.container()
        
        with feed_container:
            # Reverse to show newest first
            for update in reversed(updates[-10:]):
                update_type = update.get('update_type', 'UNKNOWN')
                timestamp = self.format_timestamp(update.get('timestamp', ''))
                portfolio_value = update.get('portfolio_value', 0)
                
                # Color code by update type
                if update_type == 'TRADE':
                    icon = "🔔"
                    color = "#28a745"  # Green
                elif update_type == 'TICK':
                    icon = "📊"
                    color = "#17a2b8"  # Blue
                else:
                    icon = "ℹ️"
                    color = "#6c757d"  # Gray
                
                st.markdown(
                    f"""
                    <div style="padding: 8px; margin: 4px 0; border-left: 3px solid {color}; background-color: rgba(0,0,0,0.05); border-radius: 4px;">
                        <span style="font-size: 14px;">
                            <b>{icon} {timestamp}</b> - {update_type} | 
                            Portfolio: ${portfolio_value:,.2f} | 
                            Positions: {update.get('positions', 0)} | 
                            Trades: {update.get('trades_executed', 0)}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
    def render_detailed_feed(self, limit: int = 50):
        """Render detailed feed view with full information.
        
        Args:
            limit: Number of recent updates to show
        """
        st.markdown("### 📊 Detailed Trade Feed")
        
        tab1, tab2 = st.tabs(["All Updates", "Trades Only"])
        
        with tab1:
            updates = self.load_recent_updates(limit=limit)
            
            if not updates:
                st.info("No trading updates available.")
            else:
                # Convert to DataFrame for better display
                df = pd.DataFrame(updates)
                
                # Format timestamp
                if 'timestamp' in df.columns:
                    df['time'] = df['timestamp'].apply(self.format_timestamp)
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
        
        with tab2:
            trades = self.load_recent_trades(limit=limit)
            
            if not trades:
                st.info("No trades executed yet.")
            else:
                # Convert to DataFrame
                df = pd.DataFrame(trades)
                
                # Format columns if they exist
                display_cols = []
                if 'timestamp' in df.columns:
                    df['time'] = df['timestamp'].apply(self.format_timestamp)
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
    
    def render_statistics(self):
        """Render trading statistics summary."""
        st.markdown("### 📈 Trading Statistics")
        
        updates = self.load_recent_updates(limit=1000)
        trades = self.load_recent_trades(limit=1000)
        
        if not updates:
            st.info("No trading statistics available.")
            return
        
        # Calculate statistics
        latest = updates[-1] if updates else {}
        initial = updates[0] if updates else {}
        
        initial_value = initial.get('portfolio_value', 100000)
        current_value = latest.get('portfolio_value', initial_value)
        pnl = current_value - initial_value
        pnl_pct = (pnl / initial_value) * 100 if initial_value > 0 else 0
        
        total_trades = latest.get('trades_executed', 0)
        
        # Count update types
        trade_updates = len([u for u in updates if u.get('update_type') == 'TRADE'])
        tick_updates = len([u for u in updates if u.get('update_type') == 'TICK'])
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total P&L",
                f"${pnl:,.2f}",
                f"{pnl_pct:+.2f}%",
                delta_color="normal"
            )
        
        with col2:
            st.metric("Total Trades", total_trades)
        
        with col3:
            st.metric("Updates Logged", len(updates))
        
        with col4:
            avg_trade_value = current_value / total_trades if total_trades > 0 else 0
            st.metric("Avg Trade Value", f"${avg_trade_value:,.2f}")
        
        # Recent trades summary
        if trades:
            st.markdown("#### Recent Trade Summary")
            
            # Get last 10 trades
            recent_trades = trades[-10:]
            
            buy_count = len([t for t in recent_trades if t.get('side', '').upper() == 'BUY'])
            sell_count = len([t for t in recent_trades if t.get('side', '').upper() == 'SELL'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Recent Buys", buy_count)
            
            with col2:
                st.metric("Recent Sells", sell_count)


def render_trade_feed_sidebar():
    """Render compact trade feed in sidebar."""
    viewer = TradeFeedViewer()
    
    with st.sidebar:
        st.markdown("---")
        viewer.render_compact_feed(limit=10)


def render_trade_feed_page():
    """Render full-page trade feed view."""
    st.title("📡 Live Trade Feed")
    
    viewer = TradeFeedViewer()
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh (every 5 seconds)", value=False)
    
    if auto_refresh:
        st.markdown(
            """
            <meta http-equiv="refresh" content="5">
            """,
            unsafe_allow_html=True
        )
    
    # Refresh button
    if st.button("🔄 Refresh Now"):
        st.rerun()
    
    # Render statistics
    viewer.render_statistics()
    
    st.markdown("---")
    
    # Render detailed feed
    viewer.render_detailed_feed(limit=100)


if __name__ == "__main__":
    # Standalone app mode
    st.set_page_config(
        page_title="MarketBoss Trade Feed",
        page_icon="📡",
        layout="wide"
    )
    
    render_trade_feed_page()
