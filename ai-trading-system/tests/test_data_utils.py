from src.data_pipeline import data_utils


def test_validate_schema_ok():
    records = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    ok, missing = data_utils.validate_schema(records, ["a", "b"])
    assert ok is True
    assert missing == []


def test_validate_schema_missing():
    records = [{"a": 1}, {"a": 3, "b": None}]
    ok, missing = data_utils.validate_schema(records, ["a", "b"])
    assert ok is False
    assert "b" in missing


def test_missing_value_report_and_dedupe_and_range_check():
    records = [
        {"id": 1, "price": 10.0, "vol": None},
        {"id": 2, "price": 9999.0, "vol": 100},
        {"id": 1, "price": 10.0, "vol": None},
    ]
    mv = data_utils.missing_value_report(records)
    assert mv["vol"] == 2

    deduped = data_utils.deduplicate(records, ["id"])
    assert len(deduped) == 2

    violations = data_utils.basic_range_check(records, {"price": (0.0, 1000.0)})
    assert violations["price"] == 1
