"""
aoi_tracker.py
==============
Age of Information (AoI) tracking module.

Tracks per-node, per-content AoI with support for:
  - Average AoI calculation
  - Peak AoI calculation
  - Cache-aware NDN AoI (direct path vs. cache path)
  - AoI weighted by content popularity
"""

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class AoITracker:
    """
    Tracks AoI for all nodes and contents in the network.

    AoI for node d, content k at time t:
        Delta_{d,k}(t) = t - u_{d,k}(t)
    where u_{d,k}(t) is the generation time of the most recent
    successfully received update for content k at node d.

    NDN-aware AoI (Theorem 1):
        Delta^NDN_{d,k}(t) = min(Delta^direct_{d,k}(t), Delta^cache_{d,k}(t))
    """

    def __init__(self, num_contents: int = 200, aoi_cap: float = 300.0):
        """
        num_contents : total number of distinct content types
        aoi_cap      : maximum AoI value (seconds) before capping
        """
        self.num_contents = num_contents
        self.aoi_cap      = aoi_cap

        # last_update[node_id][content_id] = generation_time of last update
        self._last_update: Dict[str, Dict[int, float]] = defaultdict(
            lambda: defaultdict(lambda: -1e9)
        )

        # AoI history for averaging
        # aoi_history[node_id][content_id] = list of (time, aoi) samples
        self._aoi_samples: Dict[str, Dict[int, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Peak AoI per (node, content)
        self._peak_aoi: Dict[str, Dict[int, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # Current time
        self._current_time: float = 0.0

        # Integral for time-averaged AoI
        # _aoi_integral[node_id][content_id] = accumulated integral value
        self._aoi_integral: Dict[str, Dict[int, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._last_record_time: Dict[str, Dict[int, float]] = defaultdict(
            lambda: defaultdict(float)
        )

    # ── Update ────────────────────────────────────────────────────────────────
    def record_update(self, node_id: str, content_id: int,
                      generation_time: float, current_time: float):
        """
        Record that node `node_id` received fresh content `content_id`
        with generation time `generation_time`.
        """
        # Only accept if fresher than current
        if generation_time > self._last_update[node_id][content_id]:
            self._last_update[node_id][content_id] = generation_time

    def tick(self, current_time: float, node_ids: List[str],
             dt: float = 0.1):
        """
        Advance time and update AoI integrals for all (node, content) pairs.
        Call once per simulation step.
        """
        self._current_time = current_time

        for node_id in node_ids:
            for cid in range(self.num_contents):
                aoi = self.get_aoi(node_id, cid, current_time)

                # Accumulate integral
                last_t = self._last_record_time[node_id][cid]
                if last_t > 0:
                    self._aoi_integral[node_id][cid] += aoi * dt
                self._last_record_time[node_id][cid] = current_time

                # Track peak
                if aoi > self._peak_aoi[node_id][cid]:
                    self._peak_aoi[node_id][cid] = aoi

                # Store sample (decimated to save memory: every 10 steps)
                self._aoi_samples[node_id][cid].append(aoi)

    # ── AoI Query ─────────────────────────────────────────────────────────────
    def get_aoi(self, node_id: str, content_id: int,
                current_time: float) -> float:
        """
        Current AoI for (node, content) pair.
        AoI = current_time - generation_time_of_last_received_update
        """
        gen_t = self._last_update[node_id][content_id]
        if gen_t < 0:
            # Never received → age since simulation start
            return min(current_time, self.aoi_cap)
        aoi = current_time - gen_t
        return min(aoi, self.aoi_cap)

    def get_ndn_aoi(self, node_id: str, content_id: int,
                    current_time: float,
                    cache_gen_time: Optional[float] = None) -> float:
        """
        NDN-aware AoI: minimum of direct path AoI and cache AoI.
        cache_gen_time: generation time of cache hit (if any).
        """
        direct_aoi = self.get_aoi(node_id, content_id, current_time)
        if cache_gen_time is not None and cache_gen_time >= 0:
            cache_aoi = current_time - cache_gen_time
            cache_aoi = min(cache_aoi, self.aoi_cap)
            return min(direct_aoi, cache_aoi)
        return direct_aoi

    # ── Averages ──────────────────────────────────────────────────────────────
    def average_aoi(self, node_id: str = None,
                    content_weights: Dict[int, float] = None,
                    current_time: float = None) -> float:
        """
        Compute average AoI.
        If node_id is None: average over all nodes.
        content_weights: optional per-content weights (e.g., Zipf probabilities).
        current_time: if provided, use current instantaneous AoI.
        """
        if current_time is None:
            current_time = self._current_time

        if node_id is not None:
            return self._avg_aoi_node(node_id, content_weights, current_time)

        # Average over all nodes
        node_aois = []
        for nid in self._last_update:
            a = self._avg_aoi_node(nid, content_weights, current_time)
            node_aois.append(a)

        if not node_aois:
            return 0.0
        return sum(node_aois) / len(node_aois)

    def _avg_aoi_node(self, node_id: str,
                      content_weights: Dict[int, float] = None,
                      current_time: float = None) -> float:
        if current_time is None:
            current_time = self._current_time

        total_weight = 0.0
        weighted_sum = 0.0

        for cid in range(self.num_contents):
            aoi = self.get_aoi(node_id, cid, current_time)
            w   = (content_weights[cid]
                   if content_weights and cid in content_weights
                   else 1.0)
            weighted_sum += w * aoi
            total_weight += w

        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight

    def time_averaged_aoi(self, node_id: str = None,
                          total_time: float = None) -> float:
        """
        Time-averaged AoI using accumulated integrals.
        Delta_bar = (1/T) * integral_0^T Delta(t) dt
        """
        if total_time is None:
            total_time = max(self._current_time, 1.0)

        if node_id is not None:
            aoi_sum = sum(self._aoi_integral[node_id].values())
            n_contents = max(1, len(self._aoi_integral[node_id]))
            return aoi_sum / (total_time * n_contents)

        all_vals = []
        for nid, contents in self._aoi_integral.items():
            for cid, integral in contents.items():
                all_vals.append(integral / total_time)
        if not all_vals:
            return 0.0
        return sum(all_vals) / len(all_vals)

    def peak_aoi(self, node_id: str = None,
                 content_id: int = None) -> float:
        """
        Return peak AoI.
        If node_id and content_id are given: specific (node, content) pair.
        If only node_id: max over all contents.
        If neither: global max.
        """
        if node_id is not None and content_id is not None:
            return self._peak_aoi[node_id][content_id]

        if node_id is not None:
            peaks = list(self._peak_aoi[node_id].values())
            return max(peaks) if peaks else 0.0

        # Global peak
        all_peaks = []
        for nid, cid_dict in self._peak_aoi.items():
            all_peaks.extend(cid_dict.values())
        return max(all_peaks) if all_peaks else 0.0

    def network_average_aoi(self, current_time: float,
                             content_weights: Dict[int, float] = None) -> float:
        """
        Network-wide time-averaged weighted AoI (M1 metric from paper).
        Delta_bar = (1/T) * sum_t (1/|D|) * sum_d sum_k w_k * Delta^NDN_{d,k}(t)
        """
        node_ids = list(self._last_update.keys())
        if not node_ids:
            return 0.0

        total = 0.0
        for nid in node_ids:
            total += self._avg_aoi_node(nid, content_weights, current_time)
        return total / len(node_ids)

    # ── Reset ─────────────────────────────────────────────────────────────────
    def reset(self):
        """Reset all AoI tracking state."""
        self._last_update.clear()
        self._aoi_samples.clear()
        self._peak_aoi.clear()
        self._aoi_integral.clear()
        self._last_record_time.clear()
        self._current_time = 0.0

    def reset_node(self, node_id: str):
        """Reset AoI tracking for a specific node (e.g., when vehicle departs)."""
        self._last_update.pop(node_id, None)
        self._aoi_samples.pop(node_id, None)
        self._peak_aoi.pop(node_id, None)
        self._aoi_integral.pop(node_id, None)
        self._last_record_time.pop(node_id, None)

    # ── Statistics ────────────────────────────────────────────────────────────
    def get_stats(self, current_time: float = None) -> dict:
        """Return a summary dictionary of AoI statistics."""
        if current_time is None:
            current_time = self._current_time
        return {
            "average_aoi":        self.network_average_aoi(current_time),
            "peak_aoi":           self.peak_aoi(),
            "time_averaged_aoi":  self.time_averaged_aoi(),
            "num_nodes_tracked":  len(self._last_update),
        }

    def __repr__(self):
        return (f"AoITracker(nodes={len(self._last_update)}, "
                f"t={self._current_time:.1f}s)")
