"""Lightweight reproducible artifact logger for models.

Provides utilities to save model artifacts and metadata (hyperparams,
metrics, git info, timestamp). Artifacts are saved under `models/artifacts/`.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _git_info() -> Dict[str, Any]:
    try:
        # lightweight git info capture
        import subprocess

        sha = (
            subprocess.check_output(["git", "rev-parse", "HEAD"]) .decode()
        ).strip()
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            )
            .decode()
            .strip()
        )
        return {"sha": sha, "branch": branch}
    except Exception:
        return {}


def save_artifact(
    artifact_obj: Any,
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    out_dir: str = "models/artifacts",
) -> Dict[str, Any]:
    """Save `artifact_obj` (JSON-serializable) and metadata. Returns manifest.

    `name` should be a short identifier (used as filename prefix).
    """
    _ensure_dir(out_dir)
    ts = datetime.now(timezone.utc).isoformat()
    manifest = {
        "name": name,
        "timestamp": ts,
        "metadata": metadata or {},
        "git": _git_info(),
    }
    # artifact filename
    base = f"{name}_{ts.replace(':', '-')}.json"
    art_path = os.path.join(out_dir, base)
    try:
        payload = {"artifact": artifact_obj, "manifest": manifest}
        with open(art_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    except Exception:
        # best-effort: still return manifest
        pass

    # also write a manifest file for quick lookup
    try:
        man_path = os.path.join(out_dir, f"{name}_manifest.json")
        with open(man_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
    except Exception:
        pass

    manifest["path"] = art_path
    return manifest


__all__ = ["save_artifact"]
