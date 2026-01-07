"""
Store data to disk or a database, with validation hooks.

Provides `validate_and_store` which validates incoming record batches
against a YAML schema and writes JSONL on success. On validation
failures it emits alerts via `src.monitoring.alerts.send_alert`.
"""

import json
import os
from typing import Iterable, Dict, Optional

from src.data_pipeline import data_utils
from src.monitoring import alerts


def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def _coerce_value(value, pytypes):
    """Coerce string values into schema-declared Python types."""
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    s = value.strip()
    if s == "":
        return None

    try:
        if pytypes == (int,):
            return int(float(s))
        if pytypes == (float, int):
            return float(s)
        if pytypes == (bool,):
            if s.lower() in ("true", "1", "yes"):
                return True
            if s.lower() in ("false", "0", "no"):
                return False
    except Exception:
        return value

    return value


def validate_and_store(
    records: Iterable[Dict],
    schema_path: Optional[str] = None,
    out_path: Optional[str] = None,
) -> bool:
    """Validate `records` using `schema_path` (YAML) and store JSONL to
    `out_path`.

    Returns True on success, False on validation failure.
    """
    if schema_path is None:
        schema_path = os.path.join("config", "data_schema.yaml")

    # Load schema
    schema = {}
    try:
        import yaml

        with open(schema_path, "r", encoding="utf-8") as fh:
            schema = yaml.safe_load(fh) or {}
    except Exception:
        alerts.send_alert("Failed to load schema", level="critical")
        return False

    required = schema.get("required_fields", [])
    unique_key = schema.get("unique_key", [])
    ranges_cfg = schema.get("ranges", {})
    fields_def = schema.get("fields", {})

    records_list = list(records)

    # ---- COERCION ----
    if fields_def:
        type_map = {}
        for fname, meta in fields_def.items():
            t = str(meta.get("type", "str")).lower()
            nullable = bool(meta.get("nullable", False))

            if t in ("str", "string"):
                pytypes = (str,)
            elif t in ("float", "number"):
                pytypes = (float, int)
            elif t in ("int", "integer"):
                pytypes = (int,)
            elif t in ("bool", "boolean"):
                pytypes = (bool,)
            else:
                pytypes = (str,)

            type_map[fname] = (pytypes, nullable)

        bad = []
        for r in records_list:
            for fname, (pytypes, nullable) in type_map.items():
                if fname not in r:
                    continue

                v = r.get(fname)
                coerced = _coerce_value(v, pytypes)
                r[fname] = coerced

                if coerced is None and not nullable:
                    bad.append((fname, "null"))
                elif coerced is not None and not isinstance(coerced, pytypes):
                    bad.append((fname, type(coerced).__name__))

        if bad:
            msg = f"Type validation failed for fields: {bad}"
            alerts.send_alert(msg, level="error")
            return False

    # ---- REQUIRED FIELD CHECK ----
    ok, missing = data_utils.validate_schema(records_list, required)
    if not ok:
        msg = f"Validation failed: missing fields {missing}"
        alerts.send_alert(msg, level="error")
        return False

    # ---- MISSING VALUE DENSITY ----
    mv = data_utils.missing_value_report(records_list)
    problematic = [
        k
        for k, v in mv.items()
        if k in required and v >= len(records_list) * 0.5
    ]
    if problematic:
        msg = f"Validation failed: too many missing values {problematic}"
        alerts.send_alert(msg, level="error")
        return False

    # ---- RANGE CHECKS ----
    ranges = {}
    if "price" in ranges_cfg:
        lo = float(ranges_cfg["price"]["min"])
        hi = float(ranges_cfg["price"]["max"])
        for f in ("open", "high", "low", "close"):
            ranges[f] = (lo, hi)

    if "volume" in ranges_cfg:
        lo = float(ranges_cfg["volume"]["min"])
        hi = float(ranges_cfg["volume"]["max"])
        ranges["volume"] = (lo, hi)

    range_violations = data_utils.basic_range_check(records_list, ranges)
    out_of_range = [k for k, v in range_violations.items() if v > 0]
    if out_of_range:
        msg = f"Validation failed: out-of-range values in {out_of_range}"
        alerts.send_alert(msg, level="warning")
        return False

    # ---- DEDUPLICATION ----
    if unique_key:
        records_list = data_utils.deduplicate(records_list, unique_key)

    # ---- WRITE JSONL ----
    if out_path is None:
        out_path = os.path.join("data", "processed", "output.jsonl")

    _ensure_dir(os.path.dirname(out_path) or ".")

    with open(out_path, "w", encoding="utf-8") as fh:
        for r in records_list:
            fh.write(json.dumps(r) + "\n")

    return True


__all__ = ["validate_and_store"]
