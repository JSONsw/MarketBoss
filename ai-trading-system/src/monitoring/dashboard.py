"""Simple dashboard/metrics hooks.

File-backed metrics sink with optional Pushgateway push.
"""

import json
import os
from typing import Any, Dict

try:
    import yaml
except Exception:
    yaml = None

from src.monitoring import pushgateway


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def metrics_path(path: str = None) -> str:
    if path is None:
        path = os.path.join("logs", "metrics.json")
    return path


def _maybe_push(metrics: Dict[str, float]) -> None:
    # read config for pushgateway if present
    try:
        cfg = {}
        if yaml is not None:
            with open("config/alerts.yaml", "r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
        pg = cfg.get("pushgateway", {})
        url = pg.get("url")
        job = pg.get("job")
        if url and job:
            pushgateway.push_metrics(url, job, metrics)
    except Exception:
        pass


def increment(metric: str, value: int = 1, path: str = None) -> str:
    p = metrics_path(path)
    _ensure_dir(os.path.dirname(p) or ".")
    data = {}
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
    except Exception:
        data = {}
    data[metric] = data.get(metric, 0) + value
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
        fh.flush()
    # push single metric
    try:
        _maybe_push({metric: float(data[metric])})
    except Exception:
        pass
    return p


def set_gauge(metric: str, value: Any, path: str = None) -> str:
    p = metrics_path(path)
    _ensure_dir(os.path.dirname(p) or ".")
    data = {}
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
    except Exception:
        data = {}
    data[metric] = value
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
        fh.flush()
    # push gauge
    try:
        _maybe_push({metric: float(value)})
    except Exception:
        pass
    return p


__all__ = ["increment", "set_gauge"]
