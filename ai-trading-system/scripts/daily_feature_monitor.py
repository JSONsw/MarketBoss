"""Scheduled job to persist baseline feature distributions and run drift checks.

Intended to be run daily (cron / scheduler). It will:
- load recent features from a provided path (or test fixture)
- persist baseline snapshot if none exists
- compare current to baseline via `src.monitoring.feature_drift.check_feature_drift`
"""

import json
import os
from datetime import datetime
from typing import List

from src.monitoring import feature_drift, dashboard


BASELINE_PATH = os.path.join("data", "baseline_features.json")
RECENT_PATH = os.path.join("data", "recent_features.json")


def load_features(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_baseline(features: List[dict], path: str = BASELINE_PATH) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(features, fh)


def run(thresholds_path: str = os.path.join("config", "feature_monitor.yaml")) -> None:
    recent = load_features(RECENT_PATH)
    baseline = load_features(BASELINE_PATH)

    if not baseline and recent:
        save_baseline(recent)
        baseline = recent

    # load thresholds
    try:
        import yaml

        with open(thresholds_path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except Exception:
        cfg = {}

    features = list(cfg.get("features", {}).keys()) or ["return", "ma_3"]
    thresholds = cfg.get("features", {})

    if baseline and recent:
        results = feature_drift.check_feature_drift(baseline, recent, features, thresholds={**{"default": cfg.get("default_threshold", 0.2)}, **thresholds})
        # record a run timestamp
        dashboard.set_gauge("last_feature_monitor_run", datetime.utcnow().isoformat() + "Z")
        # store last run results
        with open(os.path.join("logs", "last_feature_monitor.json"), "w", encoding="utf-8") as fh:
            json.dump({"results": results, "timestamp": datetime.utcnow().isoformat() + "Z"}, fh)


if __name__ == "__main__":
    run()
