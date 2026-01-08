"""Feature validation helpers.

Small utilities to validate feature matrices produced by `build_features`.
These check required features exist, missing-value counts, and simple
population drift checks (mean/std differences).
"""

from typing import List, Dict, Tuple
import math


def required_features_present(
    features: List[Dict], required: List[str]
) -> Tuple[bool, List[str]]:
    """Return (all_ok, missing_features_list)"""
    missing = set()
    for f in features:
        for r in required:
            if r not in f:
                missing.add(r)
    return (len(missing) == 0, sorted(list(missing)))


def missing_value_counts(features: List[Dict]) -> Dict[str, int]:
    """Count None values per feature key."""
    counts = {}
    for f in features:
        for k, v in f.items():
            if v is None:
                counts[k] = counts.get(k, 0) + 1
            else:
                counts.setdefault(k, 0)
    return counts


def mean_std(values: List[float]) -> Tuple[float, float]:
    vals = [
        v
        for v in values
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    ]
    if not vals:
        return (0.0, 0.0)
    n = len(vals)
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / n
    return (mean, math.sqrt(var))


def population_drift(
    old_vals: List[float], new_vals: List[float], mean_threshold: float = 0.2
) -> bool:
    """Return True if drift detected. Uses relative mean difference."""
    old_mean, old_std = mean_std(old_vals)
    new_mean, new_std = mean_std(new_vals)
    if old_mean == 0:
        return False
    rel_change = abs(new_mean - old_mean) / abs(old_mean)
    return rel_change > mean_threshold


__all__ = [
    "required_features_present",
    "missing_value_counts",
    "population_drift",
]
