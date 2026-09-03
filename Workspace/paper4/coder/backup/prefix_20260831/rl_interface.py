# src/rl_interface.py
# ============================================================================
# RL Agent Interface for AoI-aware V2I Uplink Scheduling Pipeline
#
# Implements:
# 1. StateVectorizer: 17-dimensional normalized observation vector in [-1.0, 1.0]
#    from the RSU perspective without future / ground-truth estimation error leakage.
# 2. ActionDecoder: Decodes hybrid action space (logits & indices) into valid
#    grant 3-tuple (Delta in [DELTA_MIN, DELTA_MAX]s, ch in {0..3}, p in [P_MIN, P_MAX]dBm).
# 3. RetrospectiveReplayBuffer: SMDP retrospective transition buffer with
#    variable-interval discount gamma^Delta support.
#
# This module is the SINGLE SOURCE OF TRUTH for the observation dimension
# (STATE_DIM) and for the hybrid action bounds (DELTA_MIN/MAX, P_MIN/MAX).
# Downstream code (hot_swap_trainer, hpo, evaluate, baselines) must read those
# from here instead of duplicating literals.
# ============================================================================

from __future__ import annotations
import math
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import xml.etree.ElementTree as ET
import numpy as np
import torch

# ----------------------------------------------------------------------------
# Canonical design constants (Conversation.md sections 1-2, user-approved).
# ----------------------------------------------------------------------------
#: Observation dimension emitted by StateVectorizer.
#: 18 -> 17 (2026-08-29, design_spec_v2 D4): the hand-synthesised
#: `stop/start_imminent` feature was removed. It was an arithmetic mean of two
#: quantities the vector already carries independently (time_to_switch and
#: dist_to_stopline), i.e. a derived feature that pre-computes for the network
#: what the network should learn for itself.
STATE_DIM: int = 17

#: Transmit power bounds, dBm.
#: 23 dBm is the 3GPP TS 36.101 / 38.101 power-class-3 UE maximum transmit power;
#: 10 dBm is the design-approved lower bound for a usable V2I uplink.
P_MIN: float = 10.0
P_MAX: float = 23.0

#: Delta (update interval) minimum, seconds (ETSI EN 302 637-2 CAM T_GenCamMin).
DELTA_MIN: float = 0.1


def get_sumo_max_red_phase_duration(
    net_file: Optional[str] = None,
    default_duration: float = 45.0,
) -> float:
    """
    Dynamically extract the maximum Red traffic light phase duration (seconds)
    from SUMO's generated network XML file (generated.net.xml) or TraCI.

    Parses all <tlLogic> program definitions in the net file, computes for each
    signal link across cyclic phases the maximum consecutive duration of 'r'/'R'
    phases (handling cycle wrap-around), and returns the overall maximum.

    If the network file is not yet generated or cannot be parsed, falls back
    safely to `default_duration` (45.0 s).
    """
    if net_file is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        net_file = os.path.join(base_dir, "sumo", "generated.net.xml")

    if not os.path.exists(net_file):
        return default_duration

    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
        max_red = 0.0

        for tl in root.findall("tlLogic"):
            phases = tl.findall("phase")
            if not phases:
                continue
            durations = [float(p.get("duration", 0.0)) for p in phases]
            states = [p.get("state", "") for p in phases]
            if not states or not durations:
                continue
            num_links = max(len(s) for s in states)
            n_phases = len(phases)

            for link_idx in range(num_links):
                curr_red = 0.0
                max_link_red = 0.0
                # Double the cycle to handle cyclic wrap-around
                for step in range(2 * n_phases):
                    p_idx = step % n_phases
                    char = states[p_idx][link_idx] if link_idx < len(states[p_idx]) else "g"
                    if char in ("r", "R"):
                        curr_red += durations[p_idx]
                        if curr_red > max_link_red:
                            max_link_red = curr_red
                    else:
                        curr_red = 0.0
                total_cycle = sum(durations)
                max_link_red = min(max_link_red, total_cycle)
                if max_link_red > max_red:
                    max_red = max_link_red

        return float(max_red) if max_red > 0.0 else default_duration
    except Exception:
        return default_duration


#: Delta (update interval) maximum, dynamically extracted from SUMO net XML.
DELTA_MAX: float = get_sumo_max_red_phase_duration()


def get_sumo_max_edge_speed(
    net_file: Optional[str] = None,
    default_speed: float = 13.32,
) -> float:
    """
    Maximum lane speed limit (m/s) declared anywhere in the generated network.

    Read from the net file for the same reason `DELTA_MAX` is: a normalisation
    constant that is silently inconsistent with the scenario it normalises is a
    defect waiting to happen. `make_sumo_set.py` randomises each edge's speed
    around `AV_SPEED` with +/- `DEL_SPEED`, so the effective limit is a property
    of the generated network, not a literal anyone can restate correctly.

    Falls back to `default_speed` (the 40 km/h + 20 % case) when the network has
    not been generated yet.
    """
    if net_file is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        net_file = os.path.join(base_dir, "sumo", "generated.net.xml")

    if not os.path.exists(net_file):
        return default_speed

    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
        speeds = []
        for edge in root.findall("edge"):
            # Internal junction edges inherit their speed from the corner limit
            # and would drag the maximum down; they are not where vehicles cruise.
            if edge.get("function") == "internal":
                continue
            for lane in edge.findall("lane"):
                v = lane.get("speed")
                if v is not None:
                    speeds.append(float(v))
        return float(max(speeds)) if speeds else default_speed
    except Exception:
        return default_speed


#: Scenario speed limit (m/s), derived from the generated network.
V_LIMIT: float = get_sumo_max_edge_speed()

#: RSU communication range (m). `src/sumo/make_sumo_set.py` owns this value --
#: it is what actually builds the network geometry (EDGE_LENGTH is derived from
#: it) -- so every consumer must read it from there instead of restating 300.0.
#: A literal here would go stale the moment anyone sweeps the range, and the
#: mismatch would be silent: observations would normalise distances against one
#: radius while the environment admitted vehicles using another.
try:
    from src.sumo.make_sumo_set import RSU_RANGE as _SS_RSU_RANGE
    RSU_RANGE: float = float(_SS_RSU_RANGE)
except Exception:  # pragma: no cover - only when the sumo package is unavailable
    RSU_RANGE = 300.0

def refresh_scenario_constants() -> Dict[str, float]:
    """Re-read the scenario-derived constants from the generated network.

    DELTA_MAX, V_LIMIT and E_REF describe the network on disk, not this module.
    They are computed once at import, which is wrong the moment `make_sumo_files()`
    writes a different network afterwards -- a changed signal plan moves DELTA_MAX,
    a changed AV_SPEED moves V_LIMIT and E_REF, and nothing would notice. The
    environment calls this right after generating its network, so the constants
    describe the scenario actually being simulated.

    Consumers must read these through a live lookup rather than capturing them in
    a default argument, which binds at definition time. `ActionDecoder` and
    `StateVectorizer` take 0.0 to mean "resolve now"; `norm_sq_error` reads the
    module global on every call.
    """
    global DELTA_MAX, V_LIMIT, E_REF
    DELTA_MAX = get_sumo_max_red_phase_duration()
    V_LIMIT = get_sumo_max_edge_speed()
    E_REF = V_LIMIT * 1.0
    return {"DELTA_MAX": DELTA_MAX, "V_LIMIT": V_LIMIT, "E_REF": E_REF}


#: Estimation-error reference scale (metres), design_spec_v2 D5.
#:
#: One second of travel at the scenario speed limit. The point of dividing a
#: position error by a speed is that it converts metres into an *equivalent age*:
#: `e = E_REF` means the RSU's belief about this vehicle is as wrong as if it had
#: simply not heard from it for one second. That is the natural unit for an AoI
#: paper, and unlike a bare literal it follows the scenario automatically -- raise
#: `AV_SPEED` in make_sumo_set.py and this tracks it.
#:
#: NOT the RSU communication range: `e` is a positioning error, the range is a
#: link-budget quantity, and normalising one by the other pushes the error term
#: roughly two orders of magnitude below the power term. Since `hpo.py` normalises
#: w1..w4 to sum to 1, no weight Optuna can sample recovers from that.
E_REF: float = V_LIMIT * 1.0


def extrapolate(last_pos: Tuple[float, float],
                last_vel: Tuple[float, float],
                age: float) -> Tuple[float, float]:
    """The RSU's dead-reckoned belief: last reported position carried forward.

        p_hat(t) = p_last + v_last * age

    Constant-velocity extrapolation is deliberate, not a simplification to
    apologise for: it is what makes a stopped vehicle's stale record stay exact
    (v = 0 so the belief never drifts) while a manoeuvring one decays. That
    asymmetry is the whole premise of scheduling updates by need.
    """
    return (float(last_pos[0]) + float(last_vel[0]) * float(age),
            float(last_pos[1]) + float(last_vel[1]) * float(age))


def estimation_error(true_pos: Tuple[float, float],
                     last_pos: Tuple[float, float],
                     last_vel: Tuple[float, float],
                     age: float) -> float:
    """Euclidean distance between ground truth and the RSU's extrapolation.

    This is `e` in the reward: the quantity `norm_sq_error` squashes and the
    quantity `I_redundant` thresholds. One definition, one function, so the
    paper's symbol and the code cannot drift apart.
    """
    ex, ey = extrapolate(last_pos, last_vel, age)
    return math.hypot(float(true_pos[0]) - ex, float(true_pos[1]) - ey)


def norm_sq_error(err_m: float, e_ref: float = 0.0) -> float:
    """Normalise a squared position error into [0, 1) -- design_spec_v2 D5.

        Norm(e^2) = e^2 / (e^2 + e_ref^2)

    Chosen over `min(1, e^2 / e_max^2)` because the clipped form has zero
    gradient everywhere past `e_max`. With Delta reaching 45 s a moving vehicle
    leaves that region within about a second, so the clipped form would stop
    distinguishing "slightly stale" from "hopelessly stale" exactly where the
    scheduling decision matters. This form is strictly monotone in `e`, equals
    0.5 at `e = e_ref`, and never saturates.
    """
    ref = float(e_ref) if e_ref and e_ref > 0.0 else E_REF
    e2 = float(err_m) ** 2
    return float(e2 / (e2 + ref * ref)) if (e2 + ref * ref) > 0.0 else 0.0


class StateVectorizer:
    """
    Normalized State Vectorizer; the width is STATE_DIM, never a literal.

    Transforms raw vehicle kinematics, RSU spatial metrics, TraCI TLS signal states,
    and channel congestion indicators into a normalized feature vector in [-1.0, 1.0].

    Features:
    [0]  Last prediction error, normalized: norm_sq_error(e_last) in [0.0, 1.0).
         How wrong the RSU's dead reckoning was at this vehicle's most recent
         update. Replaces the former normalized-age slot, which is identically
         zero at every SMDP decision epoch and therefore carried no signal.
    [1]  Normalized Vx: clip(vx / v_max, -1.0, 1.0)
    [2]  Normalized Vy: clip(vy / v_max, -1.0, 1.0)
    [3]  Normalized Speed: clip(speed / v_max, 0.0, 1.0)
    [4]  Normalized Acceleration: clip(accel / a_max, -1.0, 1.0)
    [5]  Relative X: clip(dx / rsu_range, -1.0, 1.0)
    [6]  Relative Y: clip(dy / rsu_range, -1.0, 1.0)
    [7]  Normalized Distance: clip(dist / rsu_range, 0.0, 1.0)
    [8]  TLS Red one-hot: 1.0 if red else 0.0
    [9]  TLS Yellow one-hot: 1.0 if yellow else 0.0
    [10] TLS Green one-hot: 1.0 if green else 0.0
    [11] Phase remaining time: clip(time_to_switch / 60.0, 0.0, 1.0)
    [12] Distance to stopline: clip(dist_to_stopline / rsu_range, 0.0, 1.0)
    [13] Active vehicles in cell: clip(n_active / 100.0, 0.0, 1.0)
    [14] Channel Busy Ratio (CBR): clip(cbr, 0.0, 1.0)
    [15] n_queue (Conversation.md S1): normalized number of vehicles queued ahead in the
         same lane -- clip(n_queue / queue_max, 0.0, 1.0)
    [16] heading (Conversation.md S1): signed approach/recede indicator w.r.t. the RSU --
         cos(angle between velocity vector and the vehicle->RSU vector) in [-1.0, 1.0].
         +1.0 = driving straight at the RSU, -1.0 = driving straight away, 0.0 = stopped
         or moving tangentially.
    """

    #: Canonical observation dimension (module-level single source of truth).
    STATE_DIM: int = STATE_DIM

    def __init__(
        self,
        rsu_range: float = 0.0,
        v_max: float = 0.0,
        a_max: float = 5.0,
        queue_max: float = 20.0,
    ) -> None:
        # 0 means "derive from the scenario", same convention as v_max below.
        self.rsu_range = float(rsu_range) if rsu_range and rsu_range > 0.0 else RSU_RANGE
        # 0 means "derive from the scenario". The former literal 30.0 m/s was
        # 2.3x the fastest lane in the generated network, so the speed features
        # only ever used the bottom 44 % of their range.
        self.v_max = float(v_max) if v_max and v_max > 0.0 else V_LIMIT
        self.a_max = float(a_max)
        self.queue_max = max(1.0, float(queue_max))

    @property
    def state_dim(self) -> int:
        """Dimension of the emitted observation vector. Read this instead of hardcoding."""
        return STATE_DIM

    # ------------------------------------------------------------------
    # Feature helpers for the two design-mandated features (n_queue, heading)
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_queue_count(*sources: Optional[Dict[str, Any]]) -> float:
        """
        Recover the number of vehicles queued ahead in the same lane from whatever
        telemetry the dynamics/TLS feature dicts expose.

        Preferred keys are a real halting count published by the SUMO layer
        (TraCI lane.getLastStepHaltingNumber). If none is present, fall back to the
        leader-vehicle signal already produced by dynamics_predictor.extract_tls_features:
        a stopped/crawling leader within a plausible queue gap implies at least one
        vehicle queued ahead.
        """
        for src in sources:
            if not src:
                continue
            for key in ("n_queue", "queue_length", "lane_halting_number", "halting_number"):
                val = src.get(key)
                if val is not None:
                    try:
                        return max(0.0, float(val))
                    except (TypeError, ValueError):
                        continue
        for src in sources:
            if not src:
                continue
            gap = src.get("leader_gap")
            lspd = src.get("leader_speed")
            if gap is None or lspd is None:
                continue
            try:
                gap_f, lspd_f = float(gap), float(lspd)
            except (TypeError, ValueError):
                continue
            if math.isfinite(gap_f) and gap_f <= 30.0 and lspd_f <= 1.0:
                return 1.0
            return 0.0
        return 0.0

    @staticmethod
    def _compute_heading(vx: float, vy: float, dx: float, dy: float) -> float:
        """
        Signed approach/recede indicator in [-1.0, 1.0].

        dx, dy are the RSU-relative coordinates of the vehicle (vehicle - RSU), so the
        vehicle->RSU direction is (-dx, -dy). Returns the normalized dot product of the
        velocity vector with that direction: +1 approaching head-on, -1 receding,
        0 when stopped or exactly at the RSU.
        """
        speed = math.hypot(vx, vy)
        dist = math.hypot(dx, dy)
        if speed < 1e-6 or dist < 1e-6:
            return 0.0
        cos_theta = (vx * (-dx) + vy * (-dy)) / (speed * dist)
        return float(np.clip(cos_theta, -1.0, 1.0))

    def vectorize(
        self,
        vehicle_node: Any,
        rsu_node: Any,
        current_time: float,
        tls_info: Optional[Dict[str, Any]] = None,
        cbr: float = 0.0,
        n_active: int = 1,
        n_queue: Optional[float] = None,
    ) -> np.ndarray:
        """
        Vectorize node objects into a 17-dim normalized observation vector.

        n_queue: explicit count of vehicles queued ahead in the same lane. When None
        it is recovered from the TLS/dynamics feature dict (see _extract_queue_count).
        """
        vec = np.zeros(STATE_DIM, dtype=np.float32)
        if vehicle_node is None or rsu_node is None:
            return vec

        # [0] Quality of the RSU's last prediction (see vectorize_from_dict).
        vec[0] = norm_sq_error(float(getattr(vehicle_node, "last_pred_err", 0.0)))

        # [1-3] Velocities and speed
        vel = getattr(vehicle_node, "vel", (0.0, 0.0))
        if hasattr(vehicle_node, "speed"):
            spd_val = vehicle_node.speed() if callable(vehicle_node.speed) else vehicle_node.speed
        else:
            spd_val = math.hypot(vel[0], vel[1])
        
        vec[1] = np.clip(vel[0] / self.v_max, -1.0, 1.0)
        vec[2] = np.clip(vel[1] / self.v_max, -1.0, 1.0)
        vec[3] = np.clip(float(spd_val) / self.v_max, 0.0, 1.0)

        # [4] Acceleration
        accel = getattr(vehicle_node, "accel", 0.0)
        vec[4] = np.clip(float(accel) / self.a_max, -1.0, 1.0)

        # [5-7] Relative coordinates and Distance to RSU
        pos = getattr(vehicle_node, "pos", (0.0, 0.0))
        rsu_pos = getattr(rsu_node, "pos", (0.0, 0.0))
        dx = float(pos[0] - rsu_pos[0])
        dy = float(pos[1] - rsu_pos[1])
        dist = math.hypot(dx, dy)
        vec[5] = np.clip(dx / self.rsu_range, -1.0, 1.0)
        vec[6] = np.clip(dy / self.rsu_range, -1.0, 1.0)
        vec[7] = np.clip(dist / self.rsu_range, 0.0, 1.0)

        # [8-12] TLS features (TraCI)
        tls = tls_info or {}
        if not tls and hasattr(vehicle_node, "_state_dict"):
            st = vehicle_node._state_dict()
            tls = st.get("tls_features", {})

        state = str(tls.get("state", "g")).lower()
        vec[8] = 1.0 if state in ["r", "red"] else 0.0
        vec[9] = 1.0 if state in ["y", "yellow"] else 0.0
        vec[10] = 1.0 if state in ["g", "green"] else 0.0

        t_switch = float(tls.get("time_to_switch", 30.0))
        vec[11] = np.clip(t_switch / 60.0, 0.0, 1.0)

        d_stop = float(tls.get("dist_to_stopline", self.rsu_range))
        vec[12] = np.clip(d_stop / self.rsu_range, 0.0, 1.0)

        # [13-14] Network contention and measured channel occupancy
        vec[13] = np.clip(float(n_active) / 100.0, 0.0, 1.0)
        vec[14] = np.clip(float(cbr), 0.0, 1.0)

        # [15] n_queue: vehicles queued ahead in the same lane (design S1)
        if n_queue is None:
            q_cnt = self._extract_queue_count(tls, getattr(vehicle_node, "__dict__", None))
        else:
            q_cnt = max(0.0, float(n_queue))
        vec[15] = np.clip(q_cnt / self.queue_max, 0.0, 1.0)

        # [16] heading: signed approach (+) / recede (-) indicator w.r.t. the RSU (design S1)
        vec[16] = self._compute_heading(float(vel[0]), float(vel[1]), dx, dy)

        return vec

    def vectorize_from_dict(self, state_dict: Dict[str, Any], rsu_pos: Tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
        """
        Convenience method to vectorize directly from a state dictionary.
        """
        vec = np.zeros(STATE_DIM, dtype=np.float32)
        pos = state_dict.get("pos", (0.0, 0.0))
        vel = state_dict.get("vel", (0.0, 0.0))
        speed = state_dict.get("speed", math.hypot(vel[0], vel[1]))
        accel = state_dict.get("accel", 0.0)
        # [0] Quality of the RSU's last prediction for this vehicle.
        #
        # This slot used to hold normalized age. Under the SMDP formulation age
        # is structurally zero at every decision epoch -- the RSU decides right
        # after an update lands -- so the feature reached the policy as a
        # constant and carried nothing. Measured: 1 unique value over a full run.
        #
        # What the RSU does know at that instant, for free, is how wrong its
        # dead-reckoned belief turned out to be just before the report arrived.
        # That is a direct read on how far this particular vehicle can be trusted
        # to stay predictable, which is exactly what choosing Delta needs.
        vec[0] = norm_sq_error(float(state_dict.get("last_pred_err", 0.0)))
        vec[1] = np.clip(vel[0] / self.v_max, -1.0, 1.0)
        vec[2] = np.clip(vel[1] / self.v_max, -1.0, 1.0)
        vec[3] = np.clip(float(speed) / self.v_max, 0.0, 1.0)
        vec[4] = np.clip(float(accel) / self.a_max, -1.0, 1.0)

        dx = float(pos[0] - rsu_pos[0])
        dy = float(pos[1] - rsu_pos[1])
        dist = state_dict.get("dist_to_rsu", math.hypot(dx, dy))
        vec[5] = np.clip(dx / self.rsu_range, -1.0, 1.0)
        vec[6] = np.clip(dy / self.rsu_range, -1.0, 1.0)
        vec[7] = np.clip(float(dist) / self.rsu_range, 0.0, 1.0)

        tls = state_dict.get("tls_features", state_dict)
        state = str(tls.get("state", "g")).lower()
        vec[8] = 1.0 if state in ["r", "red"] else 0.0
        vec[9] = 1.0 if state in ["y", "yellow"] else 0.0
        vec[10] = 1.0 if state in ["g", "green"] else 0.0
        vec[11] = np.clip(float(tls.get("time_to_switch", 30.0)) / 60.0, 0.0, 1.0)
        vec[12] = np.clip(float(tls.get("dist_to_stopline", self.rsu_range)) / self.rsu_range, 0.0, 1.0)

        vec[13] = np.clip(float(state_dict.get("n_active", 1)) / 100.0, 0.0, 1.0)
        vec[14] = np.clip(float(state_dict.get("cbr", 0.0)), 0.0, 1.0)

        # [15] n_queue: vehicles queued ahead in the same lane (design S1).
        # Prefer an explicit count on the state dict, then the TLS/dynamics feature
        # dict, then the leader-vehicle fallback.
        q_cnt = self._extract_queue_count(state_dict, tls)
        vec[15] = np.clip(q_cnt / self.queue_max, 0.0, 1.0)

        # [16] heading: signed approach (+) / recede (-) indicator w.r.t. the RSU (design S1)
        vec[16] = self._compute_heading(float(vel[0]), float(vel[1]), dx, dy)

        return vec


class ActionDecoder:
    """
    Hybrid Action Space Decoder.
    
    Decodes raw model logits or tensor outputs into a concrete uplink grant 3-tuple:
    (Delta in [0.1, 45.0]s, ch in {0, 1, 2, 3}, power in [10.0, 23.0]dBm).

    These bounds are the user-approved design (Conversation.md S2) and are the SINGLE
    SOURCE OF TRUTH for the action space. Rationale for the record:
      * p_max = 23 dBm -- 3GPP TS 36.101/38.101 power-class-3 UE maximum transmit power.
      * delta_min = 0.1 s -- ETSI EN 302 637-2 CAM minimum generation interval
        (T_GenCamMin); generating faster than this is not standards-compliant.
      * delta_max = 45.0 s -- worst-case standstill duration in the actual SUMO
        scenario (generated.net.xml tlLogic: green 42 s + yellow 3 s => 45 s red per
        approach), i.e. the longest interval over which a stopped vehicle's mobility
        state provably need not be refreshed.

    Delta mapping is GEOMETRIC, not linear. The Delta range spans a factor of 450, so a
    linear interpolation of sigmoid(logit) would need u ~= 0.0089 just to emit 0.5 s and
    would destroy all resolution in the short-interval regime. Instead:

        u     = sigmoid(raw_delta)                              in [0, 1]
        delta = delta_min * (delta_max / delta_min) ** u        (inverse: u = log(d/d_min)/log(d_max/d_min))

    which gives uniform *relative* resolution across u. Power stays linear: dBm is
    already a logarithmic unit.

    Downstream code must read delta_min/delta_max/p_min/p_max off the decoder
    instance rather than duplicating the literals.
    """

    def __init__(
        self,
        num_channels: int = 4,
        delta_min: float = DELTA_MIN,
        delta_max: float = 0.0,
        p_min: float = P_MIN,
        p_max: float = P_MAX,
    ) -> None:
        self.num_channels = int(num_channels)
        self.delta_min = float(delta_min)
        # 0.0 means "resolve from the scenario now". A `= DELTA_MAX` default
        # would bind the value at import time and ignore any later network.
        self.delta_max = float(delta_max) if delta_max and delta_max > 0.0 else DELTA_MAX
        self.p_min = float(p_min)
        self.p_max = float(p_max)
        # log(delta_max / delta_min): the geometric span used by the Delta mapping.
        # Guarded so a degenerate delta_min == delta_max decoder still works.
        if self.delta_min > 0.0 and self.delta_max > self.delta_min:
            self._log_delta_ratio = math.log(self.delta_max / self.delta_min)
        else:
            self._log_delta_ratio = 0.0

    def delta_from_unit(self, u: float) -> float:
        """Geometric map u in [0, 1] -> Delta in [delta_min, delta_max]."""
        u = min(max(float(u), 0.0), 1.0)
        if self._log_delta_ratio <= 0.0:
            # Degenerate range: fall back to linear interpolation.
            return self.delta_min + u * (self.delta_max - self.delta_min)
        if u <= 0.0:
            return self.delta_min
        if u >= 1.0:
            return self.delta_max
        return self.delta_min * math.exp(u * self._log_delta_ratio)

    def unit_from_delta(self, delta: float) -> float:
        """Inverse geometric map Delta -> u in [0, 1]."""
        d = min(max(float(delta), self.delta_min), self.delta_max)
        if self._log_delta_ratio <= 0.0:
            return (d - self.delta_min) / max(1e-6, self.delta_max - self.delta_min)
        return math.log(d / self.delta_min) / self._log_delta_ratio

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x < -50.0:
            return 0.0
        if x > 50.0:
            return 1.0
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _logit(p: float) -> float:
        p_clamped = min(max(p, 1e-6), 1.0 - 1e-6)
        return math.log(p_clamped / (1.0 - p_clamped))

    def decode_action(self, raw_action: Any) -> Tuple[float, int, float]:
        """
        Decodes raw action into (delta_s, channel_idx, power_dbm).
        """
        if isinstance(raw_action, dict):
            raw_delta = raw_action.get("delta", raw_action.get("delta_raw", 0.0))
            raw_ch = raw_action.get("ch", raw_action.get("channel_idx", 0))
            raw_p = raw_action.get("power", raw_action.get("tx_power_dbm", 0.0))
        elif isinstance(raw_action, (list, tuple, np.ndarray, torch.Tensor)):
            if isinstance(raw_action, torch.Tensor):
                raw_action = raw_action.detach().cpu().numpy().flatten()
            raw_list = list(raw_action)
            if len(raw_list) >= 3:
                raw_delta, raw_ch, raw_p = raw_list[0], raw_list[1], raw_list[2]
            elif len(raw_list) == 2:
                raw_delta, raw_ch, raw_p = raw_list[0], 0, raw_list[1]
            elif len(raw_list) == 1:
                raw_delta, raw_ch, raw_p = raw_list[0], 0, 0.0
            else:
                raw_delta, raw_ch, raw_p = 0.0, 0, 0.0
        else:
            raw_delta, raw_ch, raw_p = 0.0, 0, 0.0

        # Continuous delta mapping, GEOMETRIC over [delta_min, delta_max].
        # This used to be a linear interpolation of the sigmoid, which contradicted
        # this class's own docstring and `delta_from_unit`. The two disagree by an
        # order of magnitude in the region the scheduler lives in: at logit 0 the
        # linear form emits 22.55 s where the geometric one emits 2.12 s. Every
        # baseline calls `delta_from_unit` directly, so the linear form never
        # reached a run -- but it was one fallback away from silently halving the
        # resolution of the short-interval regime the paper is about.
        sig_d = self._sigmoid(float(raw_delta))
        delta = self.delta_from_unit(sig_d)

        # Discrete channel mapping {0..num_channels-1}
        ch = int(round(float(raw_ch))) % self.num_channels

        # Continuous power mapping [p_min, p_max]
        sig_p = self._sigmoid(float(raw_p))
        power = self.p_min + sig_p * (self.p_max - self.p_min)

        return (float(delta), int(ch), float(power))

    def encode_action(self, delta: float, ch: int, power: float) -> np.ndarray:
        """Inverse of `decode_action`: (delta, ch, power) back to raw logits.

        Delta inverts through `unit_from_delta` so the pair stays geometric on
        both sides. Power stays linear because dBm is already a log unit.
        """
        norm_d = self.unit_from_delta(delta)
        norm_p = (power - self.p_min) / max(1e-6, self.p_max - self.p_min)
        raw_d = self._logit(norm_d)
        raw_p = self._logit(norm_p)
        return np.array([raw_d, float(ch), raw_p], dtype=np.float32)


class RetrospectiveReplayBuffer:
    """
    SMDP Retrospective Replay Buffer with variable-interval discount gamma^Delta support.
    """

    def __init__(self, capacity: int = 10000, gamma: float = 0.99) -> None:
        self.capacity = int(capacity)
        self.gamma = float(gamma)
        self.buffer: List[Dict[str, Any]] = []
        self.position = 0

    def push(
        self,
        state: Union[np.ndarray, torch.Tensor, List[float]],
        action: Union[np.ndarray, torch.Tensor, List[float], Tuple[float, ...]],
        reward: float,
        next_state: Union[np.ndarray, torch.Tensor, List[float]],
        done: bool,
        delta_t: float,
        action_idx: Optional[int] = None,
    ) -> None:
        """
        Push a transition tuple (s, a, r, s', done, delta_t) into buffer.

        action_idx (optional): the combined *discrete* action index that a
        discrete-action agent (e.g. DuelingQAoI, whose grid is
        interval_idx * num_channels + channel_idx) actually selected. It is
        stored verbatim so that credit assignment in update() targets the true
        action instead of a lossy reconstruction from the decoded continuous
        action. Agents with purely continuous / factorized action heads simply
        leave it as None; sample() then omits the "action_idx" key entirely,
        so batch contents are unchanged for every other baseline.
        """
        s_arr = np.array(state, dtype=np.float32) if not isinstance(state, np.ndarray) else state.astype(np.float32)
        if isinstance(action, torch.Tensor):
            a_arr = action.detach().cpu().numpy().astype(np.float32)
        elif isinstance(action, (list, tuple)):
            a_arr = np.array(action, dtype=np.float32)
        else:
            a_arr = np.array(action, dtype=np.float32)

        ns_arr = np.array(next_state, dtype=np.float32) if not isinstance(next_state, np.ndarray) else next_state.astype(np.float32)

        item = {
            "state": s_arr,
            "action": a_arr,
            "reward": float(reward),
            "next_state": ns_arr,
            "done": float(done),
            "delta_t": float(delta_t),
            "action_idx": None if action_idx is None else int(action_idx),
        }

        if len(self.buffer) < self.capacity:
            self.buffer.append(item)
        else:
            self.buffer[self.position] = item
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> Dict[str, torch.Tensor]:
        """
        Sample a random batch of transitions as PyTorch Tensors.
        Raises ValueError if buffer is empty.
        """
        if len(self.buffer) == 0:
            raise ValueError("Cannot sample from an empty buffer.")

        batch_size = min(batch_size, len(self.buffer))
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]

        states = np.array([b["state"] for b in batch], dtype=np.float32)
        actions = np.array([b["action"] for b in batch], dtype=np.float32)
        rewards = np.array([[b["reward"]] for b in batch], dtype=np.float32)
        next_states = np.array([b["next_state"] for b in batch], dtype=np.float32)
        dones = np.array([[b["done"]] for b in batch], dtype=np.float32)
        delta_ts = np.array([[b["delta_t"]] for b in batch], dtype=np.float32)
        discounts = np.power(self.gamma, delta_ts).astype(np.float32)

        out = {
            "state": torch.from_numpy(states),
            "action": torch.from_numpy(actions),
            "reward": torch.from_numpy(rewards),
            "next_state": torch.from_numpy(next_states),
            "done": torch.from_numpy(dones),
            "delta_t": torch.from_numpy(delta_ts),
            "discount": torch.from_numpy(discounts),
        }

        # Optional discrete action indices. Emitted only when EVERY sampled
        # transition carries one, so batches for continuous-action baselines
        # keep exactly the legacy key set / tensor shapes.
        idx_list = [b.get("action_idx") for b in batch]
        if len(idx_list) > 0 and all(i is not None for i in idx_list):
            out["action_idx"] = torch.from_numpy(np.array(idx_list, dtype=np.int64))

        return out

    def is_ready(self, batch_size: int) -> bool:
        return len(self.buffer) >= batch_size

    def clear(self) -> None:
        self.buffer.clear()
        self.position = 0

    def __len__(self) -> int:
        return len(self.buffer)
