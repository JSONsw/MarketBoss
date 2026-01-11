"""Strategy configuration loader and manager.

This module loads trading strategy configurations from YAML and provides
a unified interface for accessing strategy parameters across different
timeframes (intraday, swing, weekly, monthly).
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class StrategyConfig:
    """Trading strategy configuration."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize strategy config from dictionary.
        
        Args:
            config_dict: Strategy configuration dictionary
        """
        self.name = config_dict.get("name", "Unknown Strategy")
        self.description = config_dict.get("description", "")
        
        # Timeframe settings
        timeframe = config_dict.get("timeframe", {})
        self.data_interval = timeframe.get("data_interval", "5m")
        self.lookback_days = timeframe.get("lookback_days", 7)
        self.ma_fast_period = timeframe.get("ma_fast_period", 5)
        self.ma_slow_period = timeframe.get("ma_slow_period", 20)
        
        # Execution settings
        execution = config_dict.get("execution", {})
        self.min_cooldown_minutes = execution.get("min_cooldown_minutes", 5)
        self.max_holding_hours = execution.get("max_holding_hours", 6)
        self.position_exit_before_close = execution.get("position_exit_before_close", 30)
        
        # Risk settings
        risk = config_dict.get("risk", {})
        self.min_confidence = risk.get("min_confidence", 0.60)
        self.min_profit_bp = risk.get("min_profit_bp", 3.0)
        self.risk_percent = risk.get("risk_percent", 1.0)
        self.max_positions = risk.get("max_positions", 3)
        
        self.description_detail = config_dict.get("description_detail", "")
    
    @property
    def min_cooldown_seconds(self) -> float:
        """Get minimum cooldown in seconds."""
        return self.min_cooldown_minutes * 60.0
    
    @property
    def max_holding_seconds(self) -> float:
        """Get maximum holding time in seconds."""
        return self.max_holding_hours * 3600.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy config to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "timeframe": {
                "data_interval": self.data_interval,
                "lookback_days": self.lookback_days,
                "ma_fast_period": self.ma_fast_period,
                "ma_slow_period": self.ma_slow_period,
            },
            "execution": {
                "min_cooldown_minutes": self.min_cooldown_minutes,
                "max_holding_hours": self.max_holding_hours,
                "position_exit_before_close": self.position_exit_before_close,
            },
            "risk": {
                "min_confidence": self.min_confidence,
                "min_profit_bp": self.min_profit_bp,
                "risk_percent": self.risk_percent,
                "max_positions": self.max_positions,
            }
        }
    
    def __repr__(self) -> str:
        return f"<StrategyConfig: {self.name} ({self.data_interval})>"


class StrategyManager:
    """Manager for loading and accessing trading strategies."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize strategy manager.
        
        Args:
            config_path: Path to trading_strategies.yaml file.
                        If None, uses default config/trading_strategies.yaml
        """
        if config_path is None:
            # Default to config/trading_strategies.yaml relative to project root
            project_root = Path(__file__).resolve().parent.parent.parent
            config_path = project_root / "config" / "trading_strategies.yaml"
        
        self.config_path = Path(config_path)
        self.strategies: Dict[str, StrategyConfig] = {}
        self.default_strategy: str = "intraday"
        
        self._load_strategies()
    
    def _load_strategies(self):
        """Load strategies from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Strategy config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Load each strategy
        strategies_config = config.get("strategies", {})
        for strategy_name, strategy_dict in strategies_config.items():
            self.strategies[strategy_name] = StrategyConfig(strategy_dict)
        
        # Load default strategy
        self.default_strategy = config.get("default_strategy", "intraday")
        
        if not self.strategies:
            raise ValueError("No strategies found in config file")
        
        if self.default_strategy not in self.strategies:
            # Fallback to first strategy if default not found
            self.default_strategy = list(self.strategies.keys())[0]
    
    def get_strategy(self, name: Optional[str] = None) -> StrategyConfig:
        """Get strategy configuration by name.
        
        Args:
            name: Strategy name (intraday, swing, weekly, monthly).
                 If None, returns default strategy.
        
        Returns:
            StrategyConfig object
        
        Raises:
            KeyError: If strategy name not found
        """
        if name is None:
            name = self.default_strategy
        
        if name not in self.strategies:
            available = list(self.strategies.keys())
            raise KeyError(
                f"Strategy '{name}' not found. "
                f"Available strategies: {available}"
            )
        
        return self.strategies[name]
    
    def list_strategies(self) -> Dict[str, str]:
        """List all available strategies with descriptions.
        
        Returns:
            Dict mapping strategy name to description
        """
        return {
            name: strategy.description
            for name, strategy in self.strategies.items()
        }
    
    def get_default_strategy(self) -> StrategyConfig:
        """Get the default strategy."""
        return self.get_strategy(self.default_strategy)


def load_strategy(strategy_name: Optional[str] = None,
                 config_path: Optional[str] = None) -> StrategyConfig:
    """Convenience function to load a strategy.
    
    Args:
        strategy_name: Strategy name (intraday, swing, weekly, monthly).
                      If None, uses default.
        config_path: Path to config file. If None, uses default.
    
    Returns:
        StrategyConfig object
    
    Example:
        >>> strategy = load_strategy("swing")
        >>> print(strategy.data_interval)  # "1h"
        >>> print(strategy.ma_fast_period)  # 10
    """
    manager = StrategyManager(config_path)
    return manager.get_strategy(strategy_name)


# Convenience functions for common use cases
def get_intraday_strategy(config_path: Optional[str] = None) -> StrategyConfig:
    """Get intraday trading strategy (5-minute bars)."""
    return load_strategy("intraday", config_path)


def get_swing_strategy(config_path: Optional[str] = None) -> StrategyConfig:
    """Get swing trading strategy (1-hour bars)."""
    return load_strategy("swing", config_path)


def get_weekly_strategy(config_path: Optional[str] = None) -> StrategyConfig:
    """Get weekly trading strategy (daily bars)."""
    return load_strategy("weekly", config_path)


def get_monthly_strategy(config_path: Optional[str] = None) -> StrategyConfig:
    """Get monthly trading strategy (daily bars)."""
    return load_strategy("monthly", config_path)
