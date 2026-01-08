import os
import pandas as pd
from src.data_pipeline import store_data


def test_validate_and_store_success(tmp_path):
    records = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "symbol": "ABC",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 100,
        },
        {
            "timestamp": "2025-01-01T00:01:00Z",
            "symbol": "ABC",
            "open": 10.5,
            "high": 11.2,
            "low": 10.3,
            "close": 11.0,
            "volume": 150,
        },
    ]
    out_path = tmp_path / "out.jsonl"
    ok = store_data.validate_and_store(
        records,
        schema_path=os.path.join("config", "data_schema.yaml"),
        out_path=str(out_path),
    )
    assert ok is True
    assert out_path.exists()
    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_validate_and_store_failure_triggers_alert(tmp_path):
    # missing 'close' field triggers validation failure
    records = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "symbol": "ABC",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "volume": 100,
        },
    ]
    ok = store_data.validate_and_store(
        records,
        schema_path=os.path.join("config", "data_schema.yaml"),
        out_path=str(tmp_path / "out.jsonl"),
    )
    assert ok is False
    # alerts log should be created
    alerts_path = os.path.join("logs", "alerts.log")
    assert os.path.exists(alerts_path)
    content = open(alerts_path, "r", encoding="utf-8").read()
    assert "Validation failed" in content or "validation failed" in content.lower()


def test_validate_and_store_empty_records(tmp_path):
    # No records should pass
    records = []
    out_path = tmp_path / "out.jsonl"
    ok = store_data.validate_and_store(records, schema_path=os.path.join("config", "data_schema.yaml"), out_path=str(out_path))
    assert not ok  # Should return False due to no data


def test_validate_and_store_missing_required_fields(tmp_path):
    # Required fields like timestamp, symbol, etc., are missing
    records = [
        {"open": 10.5, "high": 11.0, "low": 10.0, "close": 10.8, "volume": 100},
    ]
    out_path = tmp_path / "out.jsonl"
    ok = store_data.validate_and_store(records, schema_path=os.path.join("config", "data_schema.yaml"), out_path=str(out_path))
    assert not ok  # Should return False due to missing required fields


def test_validate_and_store_invalid_types(tmp_path):
    # Invalid types for fields (open is a string not coercible to float)
    records = [
        {"timestamp": "2025-01-01T00:00:00Z", "symbol": "ABC", "open": "INVALID", "high": 11.0, "low": 10.0, "close": 10.8, "volume": 100},
    ]
    out_path = tmp_path / "out.jsonl"
    ok = store_data.validate_and_store(records, schema_path=os.path.join("config", "data_schema.yaml"), out_path=str(out_path))
    assert not ok  # Should fail because 'open' cannot be coerced to a float


def test_validate_time_series_single_record():
    data = pd.DataFrame([{"timestamp": "2025-01-01T00:00:00Z"}])
    data["timestamp"] = pd.to_datetime(data["timestamp"])  # Ensure proper datetime format
    is_valid = store_data.validate_time_series(data, timestamp_col="timestamp")
    assert is_valid  # Validation should pass as there's only one record


def test_validate_time_series_non_sequential():
    data = pd.DataFrame([
        {"timestamp": "2025-01-01T00:05:00Z"},
        {"timestamp": "2025-01-01T00:00:00Z"},
        {"timestamp": "2025-01-01T00:03:00Z"},
    ])
    data["timestamp"] = pd.to_datetime(data["timestamp"])  # Ensure proper datetime format
    is_valid = store_data.validate_time_series(data, timestamp_col="timestamp")
    assert not is_valid  # Validation should fail due to non-sequential timestamps


def test_validate_outliers_with_outliers():
    data = pd.DataFrame({
        "open": [10, 12, 200, 10.5],  # 'open' has an outlier (200)
        "volume": [100, 102, 101, 99],  # No outliers in 'volume'
    })
    outlier_columns = store_data.validate_outliers(data, threshold=1.5)  # Threshold is less sensitive with IQR
    assert "open" in outlier_columns  # Outlier detected in 'open'
    assert "volume" not in outlier_columns  # No outliers in 'volume'

def test_validate_outliers_large_dataset():
    data = pd.DataFrame({
        "open": [10, 12, 11, 10.5] * 250,  # Repeated values, no outliers
        "volume": [99, 100, 101, 100.5] * 250,
    })
    outlier_columns = store_data.validate_outliers(data, threshold=1.5)
    assert outlier_columns == []  # No outliers should be detected

def test_validate_outliers_identical_values():
    data = pd.DataFrame({
        "open": [10, 10, 10, 10],  # All values are identical
        "volume": [100, 100, 100, 100],
    })
    outlier_columns = store_data.validate_outliers(data, threshold=1.5)
    assert outlier_columns == []  # No outliers should be detected

def test_validate_and_store_missing_schema(tmp_path):
    # Schema path is invalid or the file is missing
    records = [
        {"timestamp": "2025-01-01T00:00:00Z", "symbol": "ABC", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 100},
    ]
    out_path = tmp_path / "out.jsonl"
    ok = store_data.validate_and_store(records, schema_path="invalid_schema.yaml", out_path=str(out_path))
    assert not ok  # Should return False due to missing schema