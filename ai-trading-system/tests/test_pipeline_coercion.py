import os
from src.data_pipeline import store_data


def test_validate_and_store_coercion(tmp_path):
    # numeric fields provided as strings should be coerced
    records = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "symbol": "ABC",
            "open": "10.0",
            "high": "11.0",
            "low": "9.5",
            "close": "10.5",
            "volume": "100",
        },
    ]
    out_path = tmp_path / "out.jsonl"
    ok = store_data.validate_and_store(
        records,
        schema_path=os.path.join("config", "data_schema.yaml"),
        out_path=str(out_path),
    )
    assert ok is True
    # read back and ensure numbers are coerced
    text = out_path.read_text(encoding="utf-8").strip()
    assert '"open": 10.0' in text or '"open": 10' in text
