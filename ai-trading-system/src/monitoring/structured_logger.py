"""Structured JSON logger used across backtester and tests.

This is a tiny wrapper around the standard `logging` module that emits
JSON-like dicts via `logger.info()` for easy capture in tests and CI.
"""
import json
import logging
from typing import Any, Dict


class StructuredLogger:
    def __init__(self, name: str = "ai_trader"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def info(self, msg: str, **fields: Any) -> None:
        payload: Dict[str, Any] = {"message": msg}
        payload.update(fields)
        # Emit compact JSON on a single line
        self.logger.info(json.dumps(payload, default=str))


_default_logger = StructuredLogger()


def get_logger(name: str = "ai_trader") -> StructuredLogger:
    return _default_logger
