"""Minimal Pushgateway client helper.

This module implements a tiny helper to push simple metrics to a
Prometheus Pushgateway. If `requests` is available it will be used;
otherwise the function is a no-op and returns False.
"""

from typing import Dict

try:
    import requests  # type: ignore
except Exception:
    requests = None


def push_metrics(
    pushgateway_url: str,
    job: str,
    metrics: Dict[str, float],
    grouping: Dict[str, str] = None,
    timeout: int = 5,
) -> bool:
    """Push `metrics` (dict of name->value) to `pushgateway_url` under `job`.

    Returns True on success.
    """
    if not pushgateway_url or requests is None:
        return False
    grouping = grouping or {}
    # Build text exposition format
    lines = []
    for k, v in metrics.items():
        lines.append(f"{k} {float(v)}")
    data = "\n".join(lines) + "\n"
    # Construct URL
    if grouping:
        grp = ";".join([f"{k}={v}" for k, v in grouping.items()])
    else:
        grp = ""
    url = f"{pushgateway_url.rstrip('/')}/metrics/job/{job}"
    if grp:
        url = f"{url}/{grp}"
    try:
        resp = requests.post(url, data=data.encode("utf-8"), timeout=timeout)
        return resp.status_code < 400
    except Exception:
        return False


__all__ = ["push_metrics"]
