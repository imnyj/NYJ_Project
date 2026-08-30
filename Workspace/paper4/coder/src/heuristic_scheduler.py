# heuristic_scheduler.py
# ============================================================================
# S2.5 -- Signal-aware Heuristic Scheduler Baseline
#
# Implements domain-knowledge-driven scheduling rules:
# 1. Imminent stop/start transition (I_stop or I_start >= 0.5):
#    Force immediate update (Delta = delta_min, high power, low-contention channel).
# 2. Stopped vehicles at long red phase:
#    Backoff (Delta = min(Delta_max, t_left - 1.0s), low power) to eliminate
#    wasteful updates while zero-velocity extrapolation is accurate.
# 3. Cruising vehicles:
#    Dynamic interval selection based on speed and acceleration stability.
# ============================================================================
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List
import src.Communications as comm
from src.dynamics_predictor import extract_tls_features, predict_stop_imminent, predict_start_imminent

try:
    import libsumo as sumo
except ImportError:
    try:
        import traci as sumo
    except ImportError:
        sumo = None


class HeuristicScheduler:
    """
    S2.5 Domain-Knowledge Rule-Based Scheduler for AoI-aware V2I Uplink.
    """
    def __init__(
        self,
        delta_min: float = 0.1,
        delta_max: float = 45.0,
        delta_cruise_steady: float = 3.5,
        delta_cruise_accel: float = 1.5,
        p_high: float = 23.0,
        p_mid: float = 20.0,
        p_low: float = 10.0,
        num_subchannels: int = comm.NUM_SUBCHANNELS,
        sumo_conn: Any = None,
    ) -> None:
        self.delta_min = float(delta_min)
        self.delta_max = float(delta_max)
        self.delta_cruise_steady = float(delta_cruise_steady)
        self.delta_cruise_accel = float(delta_cruise_accel)
        self.p_high = float(p_high)
        self.p_mid = float(p_mid)
        self.p_low = float(p_low)
        self.num_subchannels = int(num_subchannels)
        self.sumo_conn = sumo_conn

        # Channel load tracker: counts grants allocated per subchannel for load-balancing
        self.channel_alloc_counts: List[int] = [0] * self.num_subchannels
        self._rr_idx: int = 0

    def reset(self) -> None:
        """Reset internal allocation counters."""
        self.channel_alloc_counts = [0] * self.num_subchannels
        self._rr_idx = 0

    def _pick_least_loaded_channel(self) -> int:
        """Finds the subchannel with the lowest allocation count and increments it."""
        min_load = min(self.channel_alloc_counts)
        # Select among channels with min load using round-robin preference
        candidates = [i for i, c in enumerate(self.channel_alloc_counts) if c == min_load]
        ch = candidates[self._rr_idx % len(candidates)]
        self._rr_idx = (self._rr_idx + 1) % max(1, self.num_subchannels)
        self.channel_alloc_counts[ch] += 1
        return ch

    def decide_grant(
        self,
        vehicle_id_or_state: Any,
        state_dict: Optional[Dict[str, Any]] = None,
        metrics: Optional[Any] = None,
    ) -> Tuple[float, int, float]:
        """
        Decide grant tuple (interval_s, subchannel_idx, tx_power_dbm).
        
        Supports both signatures:
          decide_grant(vehicle_id: str, state_dict: dict, metrics=None)
          decide_grant(state_dict: dict)
        """
        if isinstance(vehicle_id_or_state, dict) and state_dict is None:
            state = vehicle_id_or_state
            vid = str(state.get("vid", ""))
        else:
            vid = str(vehicle_id_or_state)
            state = state_dict if state_dict is not None else {}

        # 1. Retrieve or extract kinematics
        speed = float(state.get("speed", 0.0))
        accel = float(state.get("accel", 0.0))
        dist_to_rsu = float(state.get("dist_to_rsu", 300.0))
        current_time = state.get("current_time", None)

        # 2. Retrieve or extract TLS & transition indicators
        tls_info = state.get("tls_features")
        if tls_info is None and vid:
            # Attempt to extract via TraCI if available
            driver = self.sumo_conn if self.sumo_conn is not None else sumo
            if driver is not None:
                tls_info = extract_tls_features(driver, vid, current_time=current_time)

        if tls_info is None:
            tls_info = {}

        sig_state = str(tls_info.get("state", state.get("signal_state", "none"))).lower()
        t_left = float(tls_info.get("time_to_switch", state.get("time_to_switch", float("inf"))))
        dist_stopline = float(tls_info.get("dist_to_stopline", state.get("dist_to_stopline", float("inf"))))

        # Check indicators from tls_info or compute from state
        i_stop = float(tls_info.get("stop_imminent", 0.0))
        i_start = float(tls_info.get("start_imminent", 0.0))

        if i_stop == 0.0 and i_start == 0.0:
            i_stop = predict_stop_imminent(
                speed=speed,
                accel=accel,
                dist_to_stopline=dist_stopline,
                signal_state=sig_state,
                time_to_switch=t_left,
                leader_dist=tls_info.get("leader_gap"),
                leader_speed=tls_info.get("leader_speed"),
            )
            i_start = predict_start_imminent(
                speed=speed,
                accel=accel,
                dist_to_stopline=dist_stopline,
                signal_state=sig_state,
                time_to_switch=t_left,
                leader_dist=tls_info.get("leader_gap"),
                leader_speed=tls_info.get("leader_speed"),
                waiting_time=float(tls_info.get("waiting_time", 0.0)),
            )

        # =====================================================================
        # Rule 1: Imminent Dynamics Transition (I_stop >= 0.5 or I_start >= 0.5)
        # =====================================================================
        if i_stop >= 0.5 or i_start >= 0.5:
            # Non-linear velocity transition incoming: force immediate state refresh!
            interval = self.delta_min
            power = self.p_high        # upper bound, for high-reliability delivery
            channel = self._pick_least_loaded_channel()
            return (interval, channel, power)

        # =====================================================================
        # Rule 2: Stopped vehicle at long red phase
        # =====================================================================
        # Vehicle is stationary at red light with substantial time remaining:
        # Zero-velocity extrapolation is completely accurate (error ~ 0).
        if speed <= 1.0 and sig_state in ("r", "y") and t_left > 2.0:
            # Backoff: wake up just before the signal turns green (t_left - 1.0s)
            backoff_t = max(1.0, t_left - 1.0)
            interval = min(self.delta_max, backoff_t)
            power = self.p_low          # lower bound, saves energy and avoids interference
            channel = self._pick_least_loaded_channel()
            return (interval, channel, power)

        # =====================================================================
        # Rule 3: Cruising / In-Motion Vehicles
        # =====================================================================
        if speed <= 1.0:
            # Stopped vehicle with unknown/green signal or no TLS: moderate short interval
            interval = 2.0
            power = self.p_low
        elif abs(accel) <= 0.3 and speed > 3.0:
            # Steady velocity: constant-velocity extrapolation works very well
            interval = self.delta_cruise_steady  # e.g. 3.5s
            # Distance-adaptive power: farther vehicles need slightly more power
            power = self.p_mid if dist_to_rsu <= 400.0 else self.p_high
        elif abs(accel) <= 1.0:
            # Gentle acceleration / deceleration
            interval = self.delta_cruise_accel   # e.g. 1.5s
            power = self.p_mid
        else:
            # Rapid maneuvering / heavy acceleration
            interval = 1.0
            power = self.p_high

        channel = self._pick_least_loaded_channel()
        return (interval, channel, power)
