import os
from src.data_pipeline import store_data


def test_validate_and_store_success(tmp_path):
    records = [
        {"timestamp": "2025-01-01T00:00:00Z", "symbol": "ABC", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 100},
        {"timestamp": "2025-01-01T00:01:00Z", "symbol": "ABC", "open": 10.5, "high": 11.2, "low": 10.3, "close": 11.0, "volume": 150},
    ]
    out_path = tmp_path / "out.jsonl"
    ok = store_data.validate_and_store(records, schema_path=os.path.join("config", "data_schema.yaml"), out_path=str(out_path))
    assert ok is True
    assert out_path.exists()
    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_validate_and_store_failure_triggers_alert(tmp_path):
    # missing 'close' field triggers validation failure
    records = [
        {"timestamp": "2025-01-01T00:00:00Z", "symbol": "ABC", "open": 10.0, "high": 11.0, "low": 9.5, "volume": 100},
    ]
    ok = store_data.validate_and_store(records, schema_path=os.path.join("config", "data_schema.yaml"), out_path=str(tmp_path / "out.jsonl"))
    assert ok is False
    # alerts log should be created
    alerts_path = os.path.join("logs", "alerts.log")
    assert os.path.exists(alerts_path)
    content = open(alerts_path, "r", encoding="utf-8").read()
    assert "Validation failed" in content or "validation failed" in content.lower()
