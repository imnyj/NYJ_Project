#!/usr/bin/env python3
"""
aoi_tracker.py
==============
Per-vehicle Age-of-Information (AoI) tracker (M1 metric).

AoI_ij(t) = t_rx - t_gen  (time since the LAST successfully received CAM from i at j)

For missed receptions, AoI continues accumulating (staleness grows) until
the next successful reception.

Metric output:
  - M1_mean_AoI: average AoI across all (i,j) pairs [ms]
  - per-step time series for CSV output

Author: Experimenter agent (Stage 2: implement)
"""

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class AoITracker:
    """
    Tracks Age-of-Information for all (sender, receiver) vehicle pairs.

    Usage:
      tracker = AoITracker(comm_range_m=300.0)
      # On CAM transmission:
      tracker.on_cam_sent(sender_id, t_gen, x_sender, y_sender)
      # On CAM reception:
      tracker.on_cam_received(sender_id, receiver_id, t_rx, t_gen)
      # At each step (to accumulate AoI for non-received pairs):
      mean_aoi = tracker.step(sim_time, active_vehicles_positions)
    """

    def __init__(self, comm_range_m: float = 300.0, eval_start_time: float = 30.0):
        """
        comm_range_m: communication range threshold for M3 PDR measurement.
        eval_start_time: warmup period to exclude from metrics (seconds).
        """
        self.comm_range_m = comm_range_m
        self.eval_start_time = eval_start_time

        # Dict: sender_id -> latest (t_gen, x, y) from last CAM sent
        self.last_cam_sent: Dict[str, Tuple[float, float, float]] = {}

        # Dict: (sender_id, receiver_id) -> t_gen of last RECEIVED CAM
        self.last_received_gen_time: Dict[Tuple[str, str], float] = {}

        # Running AoI measurements (for step-level averaging)
        self.aoi_history: List[float] = []        # mean AoI per step [ms]
        self.step_times: List[float] = []         # sim time per step

        # PDR tracking
        self.cam_tx_count: Dict[str, int] = defaultdict(int)   # per sender
        self.cam_rx_count: Dict[Tuple[str, str], int] = defaultdict(int)  # per pair
        self.cam_rx_within_range: int = 0
        self.cam_tx_total: int = 0

        # For per-pair AoI accumulation: stores latest AoI value
        self.current_aoi: Dict[Tuple[str, str], float] = {}  # ms

        # Warmup exclusion flag
        self._in_warmup = True

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------
    def on_cam_sent(self, sender_id: str, t_gen: float, x: float, y: float):
        """Record a CAM transmission event."""
        self.last_cam_sent[sender_id] = (t_gen, x, y)
        if not self._in_warmup:
            self.cam_tx_count[sender_id] += 1
            self.cam_tx_total += 1

    def on_cam_received(self, sender_id: str, receiver_id: str,
                        t_rx: float, t_gen: float,
                        dist_m: float = 0.0):
        """
        Record a successful CAM reception event.

        t_rx: time of reception (s)
        t_gen: generation timestamp from CAM payload (s)
        dist_m: distance between sender and receiver at t_rx
        """
        if self._in_warmup:
            return
        pair = (sender_id, receiver_id)
        self.last_received_gen_time[pair] = t_gen

        # Update instantaneous AoI for this pair [ms]
        aoi_ms = (t_rx - t_gen) * 1000.0
        if aoi_ms < 0:
            aoi_ms = 0.0
        self.current_aoi[pair] = aoi_ms

        # PDR: count reception within communication range
        if dist_m <= self.comm_range_m:
            self.cam_rx_within_range += 1
        self.cam_rx_count[pair] += 1

    # -------------------------------------------------------------------------
    # Step update: compute mean AoI across all active pairs
    # -------------------------------------------------------------------------
    def step(self, sim_time: float,
             vehicle_positions: Dict[str, Tuple[float, float]]) -> float:
        """
        Called once per simulation step (100 ms).
        vehicle_positions: {vid: (x, y)}

        Updates _in_warmup flag.
        Returns mean AoI [ms] across all (i,j) pairs in range.
        If no pairs exist, returns 0.0.
        """
        if sim_time >= self.eval_start_time:
            self._in_warmup = False

        if self._in_warmup:
            return 0.0

        vehicle_ids = list(vehicle_positions.keys())
        n = len(vehicle_ids)
        if n < 2:
            return 0.0

        aoi_values = []
        for i, sid in enumerate(vehicle_ids):
            for j, rid in enumerate(vehicle_ids):
                if sid == rid:
                    continue
                pair = (sid, rid)
                sx, sy = vehicle_positions[sid]
                rx, ry = vehicle_positions[rid]
                dist = math.sqrt((sx - rx)**2 + (sy - ry)**2)

                if dist > self.comm_range_m:
                    # Out of range: skip this pair
                    continue

                # Accumulate AoI: time since last CAM was received (or since start)
                if pair in self.last_received_gen_time:
                    # AoI = current_time - t_gen_of_last_received_cam
                    t_gen_last = self.last_received_gen_time[pair]
                    aoi_ms = (sim_time - t_gen_last) * 1000.0
                else:
                    # Never received a CAM from this sender: AoI = time since sim start
                    aoi_ms = (sim_time - self.eval_start_time) * 1000.0

                if aoi_ms < 0:
                    aoi_ms = 0.0
                self.current_aoi[pair] = aoi_ms
                aoi_values.append(aoi_ms)

        if not aoi_values:
            return 0.0

        mean_aoi = sum(aoi_values) / len(aoi_values)
        self.aoi_history.append(mean_aoi)
        self.step_times.append(sim_time)
        return mean_aoi

    # -------------------------------------------------------------------------
    # Aggregate metrics
    # -------------------------------------------------------------------------
    def get_mean_aoi(self) -> float:
        """Return time-averaged mean AoI [ms] over evaluation period."""
        if not self.aoi_history:
            return 0.0
        return sum(self.aoi_history) / len(self.aoi_history)

    def get_pdr(self, vehicle_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> float:
        """
        Packet Delivery Ratio: received CAMs within range / transmitted CAMs * 100.
        Returns PDR [%].
        """
        if self.cam_tx_total == 0:
            return 100.0
        # Expected receptions = tx_count * (n-1) vehicles within range (simplified)
        total_rx = sum(self.cam_rx_count.values())
        total_tx = self.cam_tx_total
        if total_tx == 0:
            return 100.0
        # Use within-range receptions
        pdr = 100.0 * self.cam_rx_within_range / max(total_tx, 1)
        return min(pdr, 100.0)

    def reset(self):
        """Reset all state for a new simulation run."""
        self.last_cam_sent.clear()
        self.last_received_gen_time.clear()
        self.aoi_history.clear()
        self.step_times.clear()
        self.cam_tx_count.clear()
        self.cam_rx_count.clear()
        self.cam_rx_within_range = 0
        self.cam_tx_total = 0
        self.current_aoi.clear()
        self._in_warmup = True
