"""Trade logging utilities.

Provides a minimal immutable JSONL trade logger used by backtests and live
simulations. Each `log_trade` call appends a single JSON line to a run
specific file. Files are created under `logs/` and named with the
`run_id` (timestamp) to keep logs immutable per run.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def log_trade(
    trade: Dict, run_id: Optional[str] = None, path: Optional[str] = None
) -> str:
    """Append `trade` (a dict) as a JSON line to a run-specific file.

    Returns the path written to.
    """
    if run_id is None:
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    if path is None:
        path = os.path.join("logs", f"trades-{run_id}.jsonl")
    _ensure_dir(os.path.dirname(path) or ".")
    line = json.dumps(trade, default=str, separators=(",", ":"))
    # Open in append mode and flush+fsync for durability in backtests/live
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except Exception:
            # Windows may raise for text-mode files; best-effort durability
            pass
    return path


def read_trades(path: str):
    """Yield parsed JSON trades from `path` (JSONL)."""
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


__all__ = ["log_trade", "read_trades"]
