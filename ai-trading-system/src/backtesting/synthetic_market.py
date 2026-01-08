"""Deterministic synthetic market data generator for tests.

Provides reproducible price and volume series using a given seed.
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np


def create_rng(seed: int) -> np.random.Generator:
    """Create a deterministic numpy random generator."""
    return np.random.default_rng(seed)


def generate_price_series(
    seed: int,
    length: int = 100,
    base_price: float = 100.0,
    volatility: float = 0.01,
    trend: float = 0.0,
    spike_prob: float = 0.0,
    spike_scale: float = 0.05,
) -> List[float]:
    """Generate a deterministic price series.

    Args:
        seed: random seed
        length: number of price points
        base_price: starting price
        volatility: std-dev of log returns
        trend: additive expected return per step
        spike_prob: probability of a multiplicative spike per step
        spike_scale: scale of spikes

    Returns:
        List of float prices
    """
    rng = create_rng(seed)
    # Gaussian log-returns
    rets = rng.normal(loc=trend, scale=volatility, size=length)

    # Introduce spikes
    if spike_prob > 0:
        spikes = rng.random(size=length) < spike_prob
        directions = rng.choice([-1.0, 1.0], size=length)
        spike_vals = rng.uniform(0.0, spike_scale, size=length)
        rets = rets + spikes * directions * spike_vals

    prices = [float(base_price)]
    for r in rets:
        prices.append(float(prices[-1] * np.exp(r)))

    # drop the initial seed price to return `length` points
    return prices[1:]


def generate_volume_series(
    seed: int,
    length: int = 100,
    avg: float = 1000.0,
    std: float = 200.0,
) -> List[float]:
    """Generate deterministic volume series (floats)."""
    rng = create_rng(seed)
    vols = rng.normal(loc=avg, scale=std, size=length)
    # ensure non-negative
    vols = np.clip(vols, a_min=0.0, a_max=None)
    return [float(v) for v in vols]


def generate_spiky_market(
    seed: int, length: int = 100
) -> Tuple[List[float], List[float]]:
    """Return (prices, volumes) with occasional spikes."""
    prices = generate_price_series(
        seed,
        length,
        volatility=0.005,
        spike_prob=0.02,
        spike_scale=0.5,
    )
    volumes = generate_volume_series(
        seed + 1,
        length,
        avg=500.0,
        std=400.0,
    )
    return prices, volumes
