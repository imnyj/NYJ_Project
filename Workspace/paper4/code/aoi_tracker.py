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

import numpy as np
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
        self.first_tx_time: Dict[str, float] = {}

        # Dict: (sender_id, receiver_id) -> t_gen of last RECEIVED CAM
        self.last_received_gen_time: Dict[Tuple[str, str], float] = {}

        # Running AoI measurements (for step-level averaging)
        self.aoi_history: List[float] = []        # mean AoI per step [ms]
        self.step_times: List[float] = []         # sim time per step

        # Distance-binned AoI measurements: 6 bins [0~50, 50~100, 100~150, 150~200, 200~250, 250~300m]
        # (center distances: 25, 75, 125, 175, 225, 275 m)
        self.dist_aoi_sum: List[float] = [0.0] * 6
        self.dist_aoi_count: List[int] = [0] * 6
        self.dist_aoi_samples: List[List[float]] = [[] for _ in range(6)]

        # PDR tracking
        self.cam_tx_count: Dict[str, int] = defaultdict(int)   # per sender
        self.cam_rx_count: Dict[Tuple[str, str], int] = defaultdict(int)  # per pair
        self.cam_rx_within_range: int = 0
        self.cam_tx_total: int = 0
        self.cam_tx_in_range_total: int = 0

        # For per-pair AoI accumulation: stores latest AoI value
        self.current_aoi: Dict[Tuple[str, str], float] = {}  # ms

        # Warmup exclusion flag
        self._in_warmup = True

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------
    def on_cam_sent(self, sender_id: str, t_gen: float, x: float, y: float, in_range_count: int = 0):
        """Record a CAM transmission event."""
        self.last_cam_sent[sender_id] = (t_gen, x, y)
        if sender_id not in self.first_tx_time:
            self.first_tx_time[sender_id] = t_gen
            
        if not self._in_warmup:
            self.cam_tx_count[sender_id] += 1
            self.cam_tx_total += 1
            self.cam_tx_in_range_total += in_range_count

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

        vid_to_idx = {vid: i for i, vid in enumerate(vehicle_ids)}
        coords = np.array([vehicle_positions[vid] for vid in vehicle_ids], dtype=np.float32)
        diff = coords[:, None, :] - coords[None, :, :]
        dist_sq = np.sum(diff**2, axis=-1)
        in_range_mask = (dist_sq <= self.comm_range_m**2)
        np.fill_diagonal(in_range_mask, False)

        if not np.any(in_range_mask):
            return 0.0

        T_matrix = np.full((n, n), -1.0, dtype=np.float32)
        for sid, ft in self.first_tx_time.items():
            if sid in vid_to_idx:
                T_matrix[vid_to_idx[sid], :] = ft

        for (sid, rid), t_gen in self.last_received_gen_time.items():
            if sid in vid_to_idx and rid in vid_to_idx:
                T_matrix[vid_to_idx[sid], vid_to_idx[rid]] = t_gen

        valid_mask = in_range_mask & (T_matrix >= 0)
        if not np.any(valid_mask):
            return 0.0

        aoi_matrix = np.clip((sim_time - T_matrix) * 1000.0, 0.0, 2000.0)
        valid_aoi = aoi_matrix[valid_mask]
        mean_aoi = float(np.mean(valid_aoi))
        self.aoi_history.append(mean_aoi)
        self.step_times.append(sim_time)

        # Distance binning for AoI (6 bins of 50m up to 300m)
        dists = np.sqrt(dist_sq[valid_mask])
        bin_indices = np.clip((dists / 50.0).astype(int), 0, 5)
        for b in range(6):
            b_mask = (bin_indices == b)
            if np.any(b_mask):
                b_aois = valid_aoi[b_mask]
                self.dist_aoi_sum[b] += float(np.sum(b_aois))
                self.dist_aoi_count[b] += int(np.sum(b_mask))
                self.dist_aoi_samples[b].extend(b_aois.tolist())

        return mean_aoi

    # -------------------------------------------------------------------------
    # Aggregate metrics
    # -------------------------------------------------------------------------
    def get_mean_aoi(self) -> float:
        """Return time-averaged mean AoI [ms] over evaluation period."""
        if not self.aoi_history:
            return 0.0
        return sum(self.aoi_history) / len(self.aoi_history)

    def get_distance_aoi(self, as_dict: bool = False):
        """
        Return mean AoI [ms] across 6 distance bins:
        [0~50m, 50~100m, 100~150m, 150~200m, 200~250m, 250~300m]
        (center distances: 25, 75, 125, 175, 225, 275 m).

        Parameters:
            as_dict (bool): If True, returns a dict with 'distances', 'aoi_mean', 'aoi_std'.
                           If False, returns a list of 6 float values.

        Returns:
            List[float] or Dict[str, List[float]]
        """
        means = []
        stds = []
        for b in range(6):
            if self.dist_aoi_count[b] > 0:
                mean_val = self.dist_aoi_sum[b] / self.dist_aoi_count[b]
                means.append(round(float(mean_val), 3))
            else:
                means.append(0.0)

            if len(self.dist_aoi_samples[b]) > 1:
                stds.append(round(float(np.std(self.dist_aoi_samples[b])), 3))
            else:
                stds.append(0.0)

        if as_dict:
            return {
                "distances": [25, 75, 125, 175, 225, 275],
                "aoi_mean": means,
                "aoi_std": stds
            }
        return means

    def get_distance_aoi_dict(self) -> Dict[str, List[float]]:
        """Convenience method returning distance AoI dictionary with mean and std."""
        return self.get_distance_aoi(as_dict=True)

    def get_pdr(self, vehicle_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> float:
        """
        Packet Delivery Ratio: received CAMs within range / transmitted CAMs * 100.
        Returns PDR [%].
        """
        if self.cam_tx_total == 0 or self.cam_tx_in_range_total == 0:
            return 100.0
        # Use proper denominator: number of transmission events that had a receiver in range
        pdr = 100.0 * self.cam_rx_within_range / max(self.cam_tx_in_range_total, 1)
        return min(pdr, 100.0)

    def reset(self):
        """Reset all state for a new simulation run."""
        self.last_cam_sent.clear()
        self.first_tx_time.clear()
        self.last_received_gen_time.clear()
        self.aoi_history.clear()
        self.step_times.clear()
        self.dist_aoi_sum = [0.0] * 6
        self.dist_aoi_count = [0] * 6
        self.dist_aoi_samples = [[] for _ in range(6)]
        self.cam_tx_count.clear()
        self.cam_rx_count.clear()
        self.cam_rx_within_range = 0
        self.cam_tx_total = 0
        self.cam_tx_in_range_total = 0
        self.current_aoi.clear()
        self._in_warmup = True

    def remove_vehicle(self, vid: str):
        """Clean up state for departed vehicles to prevent memory leaks."""
        self.last_cam_sent.pop(vid, None)
        self.first_tx_time.pop(vid, None)
        self.cam_tx_count.pop(vid, None)
        
        # Clean up pair-based dictionaries where vid is either sender or receiver
        keys_to_remove_rx = [pair for pair in self.last_received_gen_time if pair[0] == vid or pair[1] == vid]
        for k in keys_to_remove_rx:
            del self.last_received_gen_time[k]

        keys_to_remove_aoi = [pair for pair in self.current_aoi if pair[0] == vid or pair[1] == vid]
        for k in keys_to_remove_aoi:
            del self.current_aoi[k]

        keys_to_remove_cam_rx = [pair for pair in self.cam_rx_count if pair[0] == vid or pair[1] == vid]
        for k in keys_to_remove_cam_rx:
            del self.cam_rx_count[k]
