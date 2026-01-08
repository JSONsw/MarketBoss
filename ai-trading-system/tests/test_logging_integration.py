import json

from src.monitoring.structured_logger import StructuredLogger


def test_structured_logger_emits_json(capsys):
    logger = StructuredLogger("test_logger")

    # Emit a structured message
    logger.info("hello", foo="bar", x=1)

    captured = capsys.readouterr()
    # StreamHandler prints to stderr by default; check both
    output = captured.err.strip() or captured.out.strip()
    obj = json.loads(output)
    assert obj["message"] == "hello"
    assert obj["foo"] == "bar"
    assert obj["x"] == 1
