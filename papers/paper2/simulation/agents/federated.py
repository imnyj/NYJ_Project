"""
federated.py
============
Federated learning module for MAFAC.

Protocol:
  1. Each vehicle trains locally for E episodes
  2. Vehicles send critic parameters to nearest RSU
  3. RSU aggregates with inverse-AoI weighting
  4. RSUs exchange aggregated models
  5. Global model broadcast back to vehicles

Only critics are federated (actors remain local for policy diversity).
"""

import math
import copy
import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class FederatedAggregator:
    """
    Federated critic aggregation with inverse-AoI weighting.
    Implements Algorithm 2 from the paper.
    """

    def __init__(
        self,
        num_rsus: int = 4,
        rsu_ids: List[str] = None,
        aoi_tracker=None,
        seed: int = 42,
    ):
        self.num_rsus    = num_rsus
        self.rsu_ids     = rsu_ids or [f"RSU_{i}" for i in range(num_rsus)]
        self.aoi_tracker = aoi_tracker

        # Round tracking
        self.round_count      = 0
        self.total_bytes_sent = 0  # for communication overhead

        # RSU-level aggregated models
        self._rsu_models: Dict[str, Optional[dict]] = {rid: None for rid in self.rsu_ids}

        # Communication overhead log
        self.overhead_log: List[dict] = []

    # ── Weight Computation ────────────────────────────────────────────────────
    def compute_aoi_weight(self, agent_id: str, current_time: float) -> float:
        """
        Compute inverse-AoI weight for an agent.
        w_i = 1 / (Delta_i + epsilon)  (higher weight = lower AoI = better data quality)
        """
        if self.aoi_tracker is None:
            return 1.0
        aoi = self.aoi_tracker.average_aoi(node_id=agent_id, current_time=current_time)
        return 1.0 / (aoi + 1e-6)

    # ── RSU-level Aggregation ─────────────────────────────────────────────────
    def aggregate_at_rsu(
        self,
        rsu_id: str,
        agent_params: Dict[str, dict],  # agent_id → critic state_dict
        current_time: float,
        min_participants: int = 1,
    ) -> Optional[dict]:
        """
        Aggregate critic parameters at a single RSU using inverse-AoI weighting.

        Returns aggregated state dict, or None if too few participants.
        """
        if len(agent_params) < min_participants:
            return None

        # Compute weights
        weights = {}
        for aid, params in agent_params.items():
            weights[aid] = self.compute_aoi_weight(aid, current_time)

        total_w = sum(weights.values())
        if total_w <= 0:
            total_w = 1.0

        # Weighted average of parameters
        agg_params = None
        for aid, params in agent_params.items():
            w = weights[aid] / total_w
            if agg_params is None:
                # Initialize with zeros
                agg_params = {k: v.clone() * w for k, v in params.items()}                     if hasattr(next(iter(params.values())), "clone")                     else {k: v * w for k, v in params.items()}
            else:
                for k in agg_params:
                    if k in params:
                        agg_params[k] = agg_params[k] + params[k] * w

        # Track communication overhead
        # Approximate: each model param transfer = 4 bytes per float
        for aid, params in agent_params.items():
            model_bytes = sum(
                (v.numel() if hasattr(v, "numel") else len(v.flatten())) * 4
                for v in params.values()
            )
            self.total_bytes_sent += model_bytes

        self._rsu_models[rsu_id] = agg_params
        return agg_params

    # ── Inter-RSU Aggregation ─────────────────────────────────────────────────
    def aggregate_rsu_models(self, current_time: float) -> Optional[dict]:
        """
        Aggregate RSU-level models into a global model.
        Uses uniform averaging (all RSUs equally weighted).
        Returns global aggregated model.
        """
        valid_models = {rid: m for rid, m in self._rsu_models.items()
                        if m is not None}
        if not valid_models:
            return None

        N = len(valid_models)
        global_model = None

        for rid, params in valid_models.items():
            if global_model is None:
                global_model = {k: v.clone() / N if hasattr(v, "clone") else v / N
                                for k, v in params.items()}
            else:
                for k in global_model:
                    if k in params:
                        global_model[k] = global_model[k] + params[k] / N

        # Track RSU-RSU communication
        if global_model:
            for rid, params in valid_models.items():
                model_bytes = sum(
                    (v.numel() if hasattr(v, "numel") else len(v.flatten())) * 4
                    for v in params.values()
                ) * self.num_rsus  # broadcast to all RSUs
                self.total_bytes_sent += model_bytes

        return global_model

    # ── Full Federation Round ─────────────────────────────────────────────────
    def run_federation_round(
        self,
        agents: Dict[str, Any],          # agent_id → agent object
        vehicle_to_rsu: Dict[str, str],  # vehicle_id → nearest RSU id
        current_time: float,
        apply_to_agents: bool = True,
    ) -> Optional[dict]:
        """
        Execute one complete federated round:
        1. Collect critic params from all agents
        2. Aggregate per RSU
        3. Aggregate across RSUs
        4. Broadcast global model back to agents

        Returns global model dict.
        """
        self.round_count += 1

        # Step 1: Collect params per RSU
        rsu_buckets: Dict[str, Dict[str, dict]] = {rid: {} for rid in self.rsu_ids}

        for agent_id, agent in agents.items():
            params = agent.get_critic_params()
            if not params:
                continue
            rsu_id = vehicle_to_rsu.get(agent_id, self.rsu_ids[0])
            if rsu_id in rsu_buckets:
                rsu_buckets[rsu_id][agent_id] = params

        # Step 2: Per-RSU aggregation
        for rsu_id, bucket in rsu_buckets.items():
            if bucket:
                self.aggregate_at_rsu(rsu_id, bucket, current_time)

        # Step 3: Inter-RSU aggregation
        global_model = self.aggregate_rsu_models(current_time)

        # Step 4: Broadcast
        if apply_to_agents and global_model is not None:
            for agent in agents.values():
                agent.set_critic_params(global_model)

        # Log overhead
        self.overhead_log.append({
            "round":       self.round_count,
            "time":        current_time,
            "total_bytes": self.total_bytes_sent,
            "num_agents":  len(agents),
            "num_rsus":    len([m for m in self._rsu_models.values() if m]),
        })

        return global_model

    # ── Vehicle-to-RSU Assignment ─────────────────────────────────────────────
    @staticmethod
    def assign_vehicles_to_rsus(
        vehicle_positions: Dict[str, Tuple[float, float]],
        rsu_positions: Dict[str, Tuple[float, float]],
    ) -> Dict[str, str]:
        """Assign each vehicle to the nearest RSU."""
        assignment = {}
        rsu_list = list(rsu_positions.items())
        for vid, (vx, vy) in vehicle_positions.items():
            best_rsu, best_d = None, float("inf")
            for rid, (rx, ry) in rsu_list:
                d = math.sqrt((vx-rx)**2 + (vy-ry)**2)
                if d < best_d:
                    best_rsu, best_d = rid, d
            assignment[vid] = best_rsu or rsu_list[0][0]
        return assignment

    # ── Statistics ────────────────────────────────────────────────────────────
    def get_overhead_mb(self) -> float:
        """Total communication overhead in megabytes."""
        return self.total_bytes_sent / (1024 * 1024)

    def get_overhead_stats(self) -> dict:
        return {
            "rounds":          self.round_count,
            "total_bytes":     self.total_bytes_sent,
            "total_mb":        self.get_overhead_mb(),
            "bytes_per_round": self.total_bytes_sent / max(1, self.round_count),
        }

    def __repr__(self):
        return (f"FederatedAggregator(rounds={self.round_count}, "
                f"overhead={self.get_overhead_mb():.2f}MB)")
