"""Data cleaning utilities.

Handles missing values, outliers, duplicates, and data quality issues
in market data pipelines.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from src.monitoring.structured_logger import get_logger

logger = get_logger()


def clean_data(
    df: pd.DataFrame,
    fill_method: str = "ffill",
    drop_duplicates: bool = True,
    handle_outliers: bool = True,
    outlier_std_threshold: float = 5.0,
) -> pd.DataFrame:
    """
    Perform comprehensive cleaning on a DataFrame.
    
    :param df: Input DataFrame
    :param fill_method: Method for filling missing values ('ffill', 'bfill', 'interpolate', 'drop')
    :param drop_duplicates: Whether to remove duplicate rows
    :param handle_outliers: Whether to cap outliers
    :param outlier_std_threshold: Number of std devs for outlier detection
    :return: Cleaned DataFrame
    """
    logger.info("clean_data_started", rows=len(df), cols=len(df.columns))
    
    df_clean = df.copy()
    
    # 1. Remove duplicates
    if drop_duplicates:
        initial_rows = len(df_clean)
        df_clean = df_clean.drop_duplicates()
        removed = initial_rows - len(df_clean)
        if removed > 0:
            logger.info("duplicates_removed", count=removed)
    
    # 2. Handle missing values
    missing_before = df_clean.isnull().sum().sum()
    if missing_before > 0:
        df_clean = handle_missing_values(df_clean, method=fill_method)
        missing_after = df_clean.isnull().sum().sum()
        logger.info("missing_values_handled", before=missing_before, after=missing_after, method=fill_method)
    
    # 3. Handle outliers
    if handle_outliers:
        df_clean = cap_outliers(df_clean, std_threshold=outlier_std_threshold)
    
    # 4. Ensure proper data types for OHLCV data
    df_clean = standardize_types(df_clean)
    
    logger.info("clean_data_completed", rows=len(df_clean), cols=len(df_clean.columns))
    return df_clean


def handle_missing_values(
    df: pd.DataFrame,
    method: str = "ffill",
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Handle missing values in DataFrame.
    
    :param df: Input DataFrame
    :param method: 'ffill' (forward fill), 'bfill' (backward fill), 
                   'interpolate' (linear), 'mean', 'median', 'drop'
    :param limit: Maximum number of consecutive NaNs to fill
    :return: DataFrame with handled missing values
    """
    df_filled = df.copy()
    
    if method == "ffill":
        df_filled = df_filled.ffill(limit=limit)
    elif method == "bfill":
        df_filled = df_filled.bfill(limit=limit)
    elif method == "interpolate":
        # Only interpolate numeric columns
        numeric_cols = df_filled.select_dtypes(include=[np.number]).columns
        df_filled[numeric_cols] = df_filled[numeric_cols].interpolate(method='linear', limit=limit)
    elif method == "mean":
        numeric_cols = df_filled.select_dtypes(include=[np.number]).columns
        df_filled[numeric_cols] = df_filled[numeric_cols].fillna(df_filled[numeric_cols].mean())
    elif method == "median":
        numeric_cols = df_filled.select_dtypes(include=[np.number]).columns
        df_filled[numeric_cols] = df_filled[numeric_cols].fillna(df_filled[numeric_cols].median())
    elif method == "drop":
        df_filled = df_filled.dropna()
    else:
        logger.warning("unknown_fill_method", method=method)
    
    return df_filled


def cap_outliers(
    df: pd.DataFrame,
    std_threshold: float = 5.0,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Cap outliers using standard deviation method.
    
    :param df: Input DataFrame
    :param std_threshold: Number of standard deviations for outlier threshold
    :param columns: Specific columns to process (None = all numeric columns)
    :return: DataFrame with capped outliers
    """
    df_capped = df.copy()
    
    if columns is None:
        columns = df_capped.select_dtypes(include=[np.number]).columns.tolist()
    
    outliers_capped = 0
    
    for col in columns:
        if col not in df_capped.columns:
            continue
            
        mean = df_capped[col].mean()
        std = df_capped[col].std()
        
        if std == 0:
            continue
        
        lower_bound = mean - std_threshold * std
        upper_bound = mean + std_threshold * std
        
        # Count outliers before capping
        outliers = ((df_capped[col] < lower_bound) | (df_capped[col] > upper_bound)).sum()
        outliers_capped += outliers
        
        # Cap values
        df_capped[col] = df_capped[col].clip(lower=lower_bound, upper=upper_bound)
    
    if outliers_capped > 0:
        logger.info("outliers_capped", count=outliers_capped, threshold=std_threshold)
    
    return df_capped


def standardize_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure proper data types for common OHLCV columns.
    
    :param df: Input DataFrame
    :return: DataFrame with standardized types
    """
    df_typed = df.copy()
    
    # Float columns
    float_cols = ['open', 'high', 'low', 'close', 'vwap', 'price']
    for col in float_cols:
        if col in df_typed.columns:
            df_typed[col] = pd.to_numeric(df_typed[col], errors='coerce')
    
    # Integer columns
    int_cols = ['volume', 'trade_count', 'qty', 'quantity']
    for col in int_cols:
        if col in df_typed.columns:
            df_typed[col] = pd.to_numeric(df_typed[col], errors='coerce').fillna(0).astype('int64')
    
    # Timestamp column
    if 'timestamp' in df_typed.columns:
        try:
            df_typed['timestamp'] = pd.to_datetime(df_typed['timestamp'])
        except Exception as e:
            logger.warning("timestamp_conversion_failed", error=str(e))
    
    return df_typed


def remove_low_volume_periods(
    df: pd.DataFrame,
    volume_threshold: float = 0,
    volume_col: str = 'volume',
) -> pd.DataFrame:
    """
    Remove rows with volume below threshold (e.g., pre-market, after-hours).
    
    :param df: Input DataFrame
    :param volume_threshold: Minimum volume to keep
    :param volume_col: Name of volume column
    :return: Filtered DataFrame
    """
    if volume_col not in df.columns:
        logger.warning("volume_column_not_found", column=volume_col)
        return df
    
    initial_rows = len(df)
    df_filtered = df[df[volume_col] > volume_threshold].copy()
    removed = initial_rows - len(df_filtered)
    
    if removed > 0:
        logger.info("low_volume_removed", count=removed, threshold=volume_threshold)
    
    return df_filtered


def adjust_for_splits(
    df: pd.DataFrame,
    split_info: List[Dict[str, Any]],
) -> pd.DataFrame:
    """
    Adjust OHLCV data for stock splits.
    
    :param df: Input DataFrame with 'timestamp' column
    :param split_info: List of dicts with 'date' and 'ratio' keys
                       Example: [{'date': '2024-01-15', 'ratio': 2.0}]
    :return: Split-adjusted DataFrame
    """
    if not split_info or 'timestamp' not in df.columns:
        return df
    
    df_adjusted = df.copy()
    
    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_adjusted['timestamp']):
        df_adjusted['timestamp'] = pd.to_datetime(df_adjusted['timestamp'])
    
    price_cols = ['open', 'high', 'low', 'close']
    volume_col = 'volume'
    
    for split in split_info:
        split_date = pd.to_datetime(split['date'])
        ratio = float(split['ratio'])
        
        # Adjust prices before split date
        mask = df_adjusted['timestamp'] < split_date
        
        for col in price_cols:
            if col in df_adjusted.columns:
                df_adjusted.loc[mask, col] = df_adjusted.loc[mask, col] / ratio
        
        # Adjust volume
        if volume_col in df_adjusted.columns:
            df_adjusted.loc[mask, volume_col] = df_adjusted.loc[mask, volume_col] * ratio
        
        logger.info("split_adjustment_applied", date=split['date'], ratio=ratio)
    
    return df_adjusted


__all__ = [
    "clean_data",
    "handle_missing_values",
    "cap_outliers",
    "standardize_types",
    "remove_low_volume_periods",
    "adjust_for_splits",
]
