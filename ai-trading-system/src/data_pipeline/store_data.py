"""
Store data to disk or a database, with validation hooks.

Provides `validate_and_store` which validates incoming record batches
against a YAML schema and writes JSONL on success. On validation
failures it emits alerts via `src.monitoring.alerts.send_alert`.
"""

import json
import os
import requests
from typing import Iterable, Dict, Optional, List
from datetime import datetime

from tenacity import retry, stop_after_attempt, wait_exponential
from src.data_pipeline import data_utils
from src.monitoring import alerts
import pandas as pd


def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def _coerce_value(value, pytypes):
    """Coerce string values into schema-declared Python types."""
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    s = value.strip()
    if s == "":
        return None

    try:
        if pytypes == (int,):
            return int(float(s))
        if pytypes == (float, int):
            return float(s)
        if pytypes == (bool,):
            if s.lower() in ("true", "1", "yes"):
                return True
            if s.lower() in ("false", "0", "no"):
                return False
    except Exception:
        print(f"Failed to coerce value: {value}")
        return value

    return value


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_data_from_vendors(vendor_urls: List[str]) -> List[Dict]:
    """
    Attempt to fetch financial data from multiple data vendors.
    Retries on failure, with exponential backoff.
    """
    for url in vendor_urls:
        try:
            print(f"Trying vendor: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as ex:
            print(f"Vendor {url} failed: {ex}")
    raise Exception("All data vendors failed! Check network or vendor API health.")


def update_schema(schema_path: str, metadata: dict):
    """
    Dynamically extend the YAML schema with new fields based on metadata.
    """
    import yaml

    with open(schema_path, "r+", encoding="utf-8") as schema_file:
        schema = yaml.safe_load(schema_file) or {}
        fields = schema.get("fields", {})

        # Add new fields to schema dynamically
        for field, definition in metadata.items():
            if field not in fields:
                fields[field] = definition

        schema["fields"] = fields
        schema_file.seek(0)
        yaml.safe_dump(schema, schema_file)


def validate_outliers(data: pd.DataFrame, threshold: float = 3.0) -> List[str]:
    """
    Detect outliers using the Interquartile Range (IQR) method.
    Returns a list of column names with outliers detected.
    """
    numeric_data = data.select_dtypes(include=['number'])
    print(f"Numeric columns for outlier detection: {numeric_data.columns.tolist()}")  # Debug print

    outlier_columns = []
    for col in numeric_data.columns:
        q1 = numeric_data[col].quantile(0.25)  # 25th percentile
        q3 = numeric_data[col].quantile(0.75)  # 75th percentile
        iqr = q3 - q1  # Interquartile range
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        if (numeric_data[col] < lower_bound).any() or (numeric_data[col] > upper_bound).any():
            outlier_columns.append(col)

    return outlier_columns


def validate_time_series(data: pd.DataFrame, timestamp_col: str = "timestamp") -> bool:
    """
    Validate time-series data continuity based on timestamps.
    Returns True if data passes, else False.
    """
    # Ensure timestamps are converted to pandas datetime
    data[timestamp_col] = pd.to_datetime(data[timestamp_col], errors="coerce")
    print(f"Converted timestamps: {data[timestamp_col].to_list()}")  # Debug timestamps

    # Check for invalid timestamps
    if data[timestamp_col].isna().any():  # NaT indicates invalid timestamps
        alerts.send_alert(
            "Time-series validation failed: invalid timestamps detected",
            level="critical",
        )
        print("Time-series validation failed: invalid timestamps detected.")
        return False

    # Check for time deltas
    if len(data[timestamp_col]) < 2:  # No deltas possible with fewer than 2 records
        print("Time-series validation passed: not enough data for deltas.")
        return True

    time_deltas = data[timestamp_col].diff().dropna()
    print(f"Time deltas: {time_deltas.to_list()}")  # Debug time deltas

    # Apply loosened consistency checks for smaller datasets
    if len(time_deltas) == 1:  # Single delta; cannot calculate standard deviation
        return True

    # Check delta consistency for larger datasets
    if time_deltas.std() == 0 or time_deltas.mean() >= 2 * time_deltas.std():
        print("Time-series validation passed.")
        return True
    else:
        print("Time-series validation failed: inconsistent time deltas.")
        return False


def validate_and_store(
    records: Iterable[Dict],
    schema_path: Optional[str] = None,
    out_path: Optional[str] = None,
) -> bool:
    """Validate `records` using `schema_path` (YAML) and store JSONL to
    `out_path`.

    Returns True on success, False on validation failure.
    """
    if schema_path is None:
        schema_path = os.path.join("config", "data_schema.yaml")

    # Load schema
    schema = {}
    try:
        import yaml

        with open(schema_path, "r", encoding="utf-8") as fh:
            schema = yaml.safe_load(fh) or {}
    except Exception:
        alerts.send_alert("Failed to load schema", level="critical")
        return False

    required = schema.get("required_fields", [])
    unique_key = schema.get("unique_key", [])
    ranges_cfg = schema.get("ranges", {})
    fields_def = schema.get("fields", {})

    records_list = list(records)

    # ---- COERCION ----
    print("Initial records:", records_list)
    # Coercion logic for fields
    if fields_def:
        type_map = {}
        for fname, meta in fields_def.items():
            t = str(meta.get("type", "str")).lower()
            nullable = bool(meta.get("nullable", False))

            if t in ("str", "string"):
                pytypes = (str,)
            elif t in ("float", "number"):
                pytypes = (float, int)
            elif t in ("int", "integer"):
                pytypes = (int,)
            elif t in ("bool", "boolean"):
                pytypes = (bool,)
            else:
                pytypes = (str,)

            type_map[fname] = (pytypes, nullable)

        bad = []
        for r in records_list:
            for fname, (pytypes, nullable) in type_map.items():
                if fname not in r:
                    continue

                v = r.get(fname)
                coerced = _coerce_value(v, pytypes)
                r[fname] = coerced

                if coerced is None and not nullable:
                    bad.append((fname, "null"))
                elif coerced is not None and not isinstance(coerced, pytypes):
                    bad.append((fname, type(coerced).__name__))

        if bad:
            msg = f"Type validation failed for fields: {bad}"
            alerts.send_alert(msg, level="error")
            return False
        print("After coercion:", records_list)

    # ---- REQUIRED FIELD CHECK ----
    ok, missing = data_utils.validate_schema(records_list, required)
    if not ok:
        msg = f"Validation failed: missing fields {missing}"
        alerts.send_alert(msg, level="error")
        return False
    print("All required fields present.")

    # ---- MISSING VALUE DENSITY ----
    mv = data_utils.missing_value_report(records_list)
    print("Missing value density:", mv)

    problematic = [
        k for k, v in mv.items() if k in required and v >= len(records_list) * 0.5
    ]
    if problematic:
        msg = f"Validation failed: too many missing values {problematic}"
        alerts.send_alert(msg, level="error")
        return False
    print("Passed missing value check.")

    # ---- RANGE CHECKS ----
    ranges = {}
    if "price" in ranges_cfg:
        lo = float(ranges_cfg["price"]["min"])
        hi = float(ranges_cfg["price"]["max"])
        for f in ("open", "high", "low", "close"):
            ranges[f] = (lo, hi)

    if "volume" in ranges_cfg:
        lo = float(ranges_cfg["volume"]["min"])
        hi = float(ranges_cfg["volume"]["max"])
        ranges["volume"] = (lo, hi)

    range_violations = data_utils.basic_range_check(records_list, ranges)
    out_of_range = [k for k, v in range_violations.items() if v > 0]
    if out_of_range:
        msg = f"Validation failed: out-of-range values in {out_of_range}"
        alerts.send_alert(msg, level="warning")
        return False
    print("Passed range checks.")

    # ---- TIME-SERIES AND OUTLIER CHECKS ----
    dataframe = pd.DataFrame(records_list)  # Convert records to DataFrame
    if not validate_time_series(dataframe, "timestamp"):
        alerts.send_alert("Time-series validation failed", level="critical")
        return False
    print("Passed time-series validation.")

    outliers = validate_outliers(dataframe, threshold=3.0)
    print("Outliers detected", outliers)

    if outliers:
        alerts.send_alert(f"Outliers detected in columns: {outliers}", level="warning")
        print("Detected outliers, but allowing operation to continue.")

    # ---- DEDUPLICATION ----
    if unique_key:
        records_list = data_utils.deduplicate(records_list, unique_key)

    # ---- WRITE JSONL ----
    if out_path is None:
        out_path = os.path.join("data", "processed", "output.jsonl")

    _ensure_dir(os.path.dirname(out_path) or ".")

    with open(out_path, "w", encoding="utf-8") as fh:
        for r in records_list:
            fh.write(json.dumps(r) + "\n")

    return True


__all__ = ["validate_and_store", "fetch_data_from_vendors", "update_schema"]
