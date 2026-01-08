"""Feature drift monitoring and alerting.

Compares baseline and current feature distributions and sends alerts
when relative mean change exceeds configured thresholds.
"""

from typing import List, Dict
from src.monitoring import alerts, dashboard, pushgateway
import os
import yaml


def check_feature_drift(
    baseline: List[Dict],
    current: List[Dict],
    features: List[str],
    thresholds: Dict[str, float] = None,
) -> Dict[str, bool]:
    """Return a dict feature -> drift_detected(bool)."""
    thresholds = thresholds or {}
    results = {}
    for f in features:
        base_vals = [r.get(f) for r in baseline if r.get(f) is not None]
        cur_vals = [r.get(f) for r in current if r.get(f) is not None]
        if not base_vals or not cur_vals:
            results[f] = False
            continue
        base_mean = sum(base_vals) / len(base_vals)
        cur_mean = sum(cur_vals) / len(cur_vals)
        if base_mean == 0:
            results[f] = False
            continue
        rel = abs(cur_mean - base_mean) / abs(base_mean)
        thr = thresholds.get(f, thresholds.get("default", 0.2))
        drift = rel > thr
        results[f] = drift
        if drift:
            msg = (
                f"Feature drift detected for {f}: "
                f"baseline_mean={base_mean:.6f} "
                f"current_mean={cur_mean:.6f} "
                f"rel_change={rel:.3f}"
            )
            alerts.send_alert(msg, level="warning")
            dashboard.increment("feature_drift_alerts", 1)
            # push to pushgateway if configured
            try:
                cfg = {}
                if os.path.exists("config/alerts.yaml"):
                    with open(
                        "config/alerts.yaml", "r", encoding="utf-8"
                    ) as fh:
                        cfg = yaml.safe_load(fh) or {}
                pg = cfg.get("pushgateway", {})
                url = pg.get("url")
                job = pg.get("job")
                if url and job:
                    pushgateway.push_metrics(
                        url, job, {f"feature_drift_{f}": 1}
                    )
            except Exception:
                pass
    return results


__all__ = ["check_feature_drift"]
