"""
Helper utilities for the data pipeline.

Lightweight, dependency-free helpers for validating simple record sets
(list of dicts) used by the pipeline. These are intentionally minimal
so unit tests do not require pandas; they can be extended later to
accept `pandas.DataFrame` inputs.
"""

from typing import Iterable, Dict, List, Tuple


def validate_schema(
    records: Iterable[dict],
    required_fields: Iterable[str],
) -> tuple[bool, list[str]]:
    """Check that each record contains the required fields.

    Returns (all_ok, missing_field_list).
    """
    required = set(required_fields)
    missing = set()
    count = 0
    for r in records:
        count += 1
        record_keys = set(r.keys())
        missing |= required - record_keys
    all_ok = count > 0 and len(missing) == 0
    return all_ok, sorted(list(missing))


def missing_value_report(records: Iterable[Dict]) -> Dict[str, int]:
    """Return count of missing (None) values per field across records."""
    counts = {}
    for r in records:
        for k, v in r.items():
            if v is None:
                counts[k] = counts.get(k, 0) + 1
            else:
                counts.setdefault(k, 0)
    return counts


def deduplicate(
    records: Iterable[Dict],
    key_fields: Iterable[str],
) -> List[Dict]:
    """Return records deduplicated by `key_fields` preserving first seen
    order.
    """
    seen = set()
    out = []
    keys = list(key_fields)
    for r in records:
        key = tuple(r.get(k) for k in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def basic_range_check(
    records: Iterable[Dict],
    ranges: Dict[str, Tuple[float, float]],
) -> Dict[str, int]:
    """Return number of out-of-range values per field according to `ranges`.

    `ranges` is a dict field -> (min, max).
    """
    violations = {k: 0 for k in ranges.keys()}
    for r in records:
        for k, (lo, hi) in ranges.items():
            v = r.get(k)
            if v is None:
                continue
            try:
                if not (lo <= v <= hi):
                    violations[k] += 1
            except TypeError:
                violations[k] += 1
    return violations


__all__ = [
    "validate_schema",
    "missing_value_report",
    "deduplicate",
    "basic_range_check",
]
