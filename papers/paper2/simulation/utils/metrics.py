"""
metrics.py
==========
Metric calculation utilities for MAFAC simulation.
"""

import math
import numpy as np
from typing import Dict, List, Optional


def compute_average_aoi(aoi_values: List[float]) -> float:
    """Compute mean AoI from a list of instantaneous AoI values."""
    if not aoi_values:
        return 0.0
    return float(np.mean(aoi_values))


def compute_peak_aoi(aoi_values: List[float]) -> float:
    """Compute peak AoI."""
    if not aoi_values:
        return 0.0
    return float(np.max(aoi_values))


def compute_cache_hit_ratio(hits: int, total: int) -> float:
    if total == 0:
        return 0.0
    return hits / total


def compute_tx_success_rate(successes: int, total: int) -> float:
    if total == 0:
        return 0.0
    return successes / total


def compute_throughput_mbps(total_bits: float, duration_s: float) -> float:
    if duration_s <= 0:
        return 0.0
    return total_bits / duration_s / 1e6


def compute_constraint_violation_rate(violations: int, total_steps: int) -> float:
    if total_steps == 0:
        return 0.0
    return violations / total_steps


def convergence_speed(reward_history: List[float],
                      window: int = 10,
                      threshold: float = 0.95) -> Optional[int]:
    """
    Find episode number when average reward first reaches threshold
    of the final value (within 5%).
    """
    if len(reward_history) < window:
        return None
    final_val = np.mean(reward_history[-window:])
    target    = threshold * abs(final_val)

    for i in range(window, len(reward_history)):
        running = np.mean(reward_history[i-window:i])
        if abs(running) >= target:
            return i
    return len(reward_history)


def compute_ndn_aoi_reduction(baseline_aoi: float, ndn_aoi: float) -> float:
    """
    Theorem 1: AoI reduction factor due to NDN caching.
    Returns relative reduction (0 to 1).
    """
    if baseline_aoi <= 0:
        return 0.0
    return max(0.0, (baseline_aoi - ndn_aoi) / baseline_aoi)


def compute_optimal_ttl(lambda_k: float, w_k: float,
                        c_miss: float, mu_k: float) -> float:
    """
    Theorem 2: Optimal TTL for content k.
    TTL*_k = (1/lambda_k) * ln(1 + w_k*lambda_k/(c_miss*mu_k))
    """
    if lambda_k <= 0 or mu_k <= 0 or c_miss <= 0:
        return 30.0
    val = 1.0 + (w_k * lambda_k) / (c_miss * mu_k)
    return (1.0 / lambda_k) * math.log(max(val, 1.0 + 1e-9))


def compute_theorem1_bound(
    p_hit: float,
    p_tx_success: float,
    lambda_content: float,
    delta_direct: float,
) -> float:
    """
    Theorem 1: NDN AoI bound.
    Delta^NDN <= (1 - p_hit * p_tx) * Delta^direct + p_hit * (1/lambda_content)
    """
    return ((1.0 - p_hit * p_tx_success) * delta_direct
            + p_hit * (1.0 / max(lambda_content, 1e-6)))


class EpisodeMetrics:
    """Collects and aggregates metrics over one episode."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.aoi_samples       = []
        self.tx_successes      = 0
        self.tx_total          = 0
        self.cache_hits        = 0
        self.cache_total       = 0
        self.total_bits        = 0.0
        self.constraint_viols  = 0
        self.total_steps       = 0
        self.rewards           = []

    def update(self, info: dict, rewards: dict = None):
        """Update metrics from info dict returned by env.step()."""
        # AoI tracking
        if "average_aoi" in info:
            self.aoi_samples.append(info["average_aoi"])

        # Transmission stats
        if "tx_successes" in info and "tx_total" in info:
            self.tx_successes += info["tx_successes"]
            self.tx_total += info["tx_total"]
        elif "tx_success_rate" in info:
            n = info.get("num_vehicles", 1)
            self.tx_total += n
            self.tx_successes += int(round(info["tx_success_rate"] * n))

        # Cache stats
        if "cache_hits" in info and "cache_total" in info:
            self.cache_hits += info["cache_hits"]
            self.cache_total += info["cache_total"]
        elif "cache_hit_ratio" in info:
            n = info.get("num_vehicles", 1)
            self.cache_total += n
            self.cache_hits += int(round(info["cache_hit_ratio"] * n))

        # Throughput
        if "bits_delivered" in info:
            self.total_bits += info["bits_delivered"]

        # CBR constraint
        if "cbr" in info:
            if info["cbr"] > 0.65:
                self.constraint_viols += 1

        self.total_steps += 1

        if rewards:
            self.rewards.append(float(np.mean(list(rewards.values()))))

    def update_tx(self, success: bool):
        self.tx_total += 1
        if success:
            self.tx_successes += 1

    def update_cache(self, hit: bool):
        self.cache_total += 1
        if hit:
            self.cache_hits += 1

    def update_bits(self, bits: float):
        self.total_bits += bits

    def update_constraint(self, violated: bool):
        if violated:
            self.constraint_viols += 1

    def finalize(self, episode_duration_s: float = 300.0) -> dict:
        """Return final metric dict for this episode."""
        return {
            "average_aoi":          compute_average_aoi(self.aoi_samples),
            "peak_aoi":             compute_peak_aoi(self.aoi_samples),
            "tx_success_rate":      compute_tx_success_rate(self.tx_successes, self.tx_total),
            "cache_hit_ratio":      compute_cache_hit_ratio(self.cache_hits, self.cache_total),
            "throughput_mbps":      compute_throughput_mbps(self.total_bits, episode_duration_s),
            "constraint_violation": compute_constraint_violation_rate(
                                        self.constraint_viols, max(1, self.total_steps)),
            "mean_episode_reward":  float(np.mean(self.rewards)) if self.rewards else 0.0,
        }
