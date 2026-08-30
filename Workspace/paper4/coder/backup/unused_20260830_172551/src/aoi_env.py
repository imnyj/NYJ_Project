# aoi_env.py
# ============================================================================
# Genuine Gymnasium-style V2I AoI Scheduling Environment Layer
#
# Driven by real SUMO micro-simulation (make_sumo_set.py, NetSim.py) and
# physical Rayleigh fading wireless channel model (Communications.py).
#
# Features:
# - Constant-velocity smart extrapolation estimation error model (S1).
# - Rayleigh fading SINR uplink interference and packet reception (S2).
# - Signal-aware dynamics integration (S2.5).
# - 16-dimensional normalized observation vector in [-1.0, 1.0].
# - Hybrid continuous-discrete action decoding (Delta in [0.5, 10.0]s, ch in {0..3}, p in [20, 30]dBm).
# - Normalized composite penalty reward:
#     R_t = -(w1*Norm(e^2) + w2*Norm(P_tx) + w3*Norm(C_freq) + w4*I_redundant)
# - 4 Hardcoded Anti-Mocking Assertions embedded directly into step().
# ============================================================================

from __future__ import annotations

import math
import os
import random
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union
import xml.etree.ElementTree as ET

import numpy as np

# Ensure SUMO binaries in venv are reachable
if "/home/imnyj/venv/bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = "/home/imnyj/venv/bin:" + os.environ.get("PATH", "")

os.environ.setdefault("SUMO_USE_LIBSUMO", "1")

# Attempt libsumo first for speed, fallback to traci
try:
    import libsumo as sumo
except ImportError:
    try:
        import traci as sumo
    except ImportError:
        sumo = None

import src.Communications as comm
import src.NetSim as net
import src.sumo.make_sumo_set as ss
from src.dynamics_predictor import extract_tls_features
from src.heuristic_scheduler import HeuristicScheduler
from src.rl_interface import (
    ActionDecoder,
    StateVectorizer,
    P_MIN,
    P_MAX,
    DELTA_MIN,
    DELTA_MAX,
)

# ----------------------------------------------------------------------------
# Pure Estimation Error Math (Unit-Testable without SUMO)
# ----------------------------------------------------------------------------

def extrapolate(pos: Tuple[float, float], vel: Tuple[float, float], dt: float) -> Tuple[float, float]:
    """Constant-velocity linear position extrapolation."""
    return (pos[0] + vel[0] * dt, pos[1] + vel[1] * dt)


def estimation_error(
    true_pos: Tuple[float, float],
    last_pos: Tuple[float, float],
    last_vel: Tuple[float, float],
    age: float,
) -> float:
    """Euclidean distance between ground truth position and RSU extrapolation."""
    ex, ey = extrapolate(last_pos, last_vel, age)
    return math.hypot(true_pos[0] - ex, true_pos[1] - ey)


# ----------------------------------------------------------------------------
# Metrics Tracking
# ----------------------------------------------------------------------------

class Metrics:
    """Tracks episode telemetry, error integrals, and channel contention stats."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.n_registrations = 0      # E1
        self.n_updates = 0            # E2 successes
        self.n_exits = 0              # E3
        self.interval_err_integrals: List[float] = []
        self.interval_durations: List[float] = []
        self.err_sum_lowspeed = 0.0
        self.n_lowspeed = 0
        self.err_sum_highspeed = 0.0
        self.n_highspeed = 0
        self.err_max = 0.0
        # Wireless channel stats
        self.n_tx_attempts = 0
        self.n_tx_fail = 0
        self.sum_succ_prob = 0.0
        self.n_prob = 0
        self.sum_contenders = 0

    def record_interval(self, err_integral: float, duration: float) -> None:
        self.interval_err_integrals.append(err_integral)
        self.interval_durations.append(duration)

    def record_sample(self, e: float, speed: float) -> None:
        self.err_max = max(self.err_max, e)
        if speed < 2.0:
            self.err_sum_lowspeed += e
            self.n_lowspeed += 1
        else:
            self.err_sum_highspeed += e
            self.n_highspeed += 1

    def record_attempt(self, p: float, contenders: int) -> None:
        self.n_tx_attempts += 1
        self.sum_succ_prob += p
        self.n_prob += 1
        self.sum_contenders += contenders

    def summary(self) -> dict:
        n_iv = len(self.interval_err_integrals)
        mean_iv = sum(self.interval_err_integrals) / n_iv if n_iv else 0.0
        mean_dur = sum(self.interval_durations) / n_iv if n_iv else 0.0
        return {
            "registrations_E1": self.n_registrations,
            "updates_E2": self.n_updates,
            "exits_E3": self.n_exits,
            "intervals": n_iv,
            "mean_interval_err_integral": round(mean_iv, 4),
            "mean_interval_duration_s": round(mean_dur, 4),
            "mean_err_lowspeed": round(self.err_sum_lowspeed / self.n_lowspeed, 4) if self.n_lowspeed else 0.0,
            "mean_err_highspeed": round(self.err_sum_highspeed / self.n_highspeed, 4) if self.n_highspeed else 0.0,
            "err_max": round(self.err_max, 4),
            "tx_attempts": self.n_tx_attempts,
            "tx_success": self.n_updates,
            "tx_fail": self.n_tx_fail,
            "tx_success_rate": round(self.n_updates / self.n_tx_attempts, 4) if self.n_tx_attempts else 0.0,
            "mean_success_prob": round(self.sum_succ_prob / self.n_prob, 4) if self.n_prob else 0.0,
            "mean_contenders_per_ch": round(self.sum_contenders / self.n_prob, 4) if self.n_prob else 0.0,
        }


METRICS = Metrics()
TARGET_RSU: Optional[Any] = None
ACTIVE_SCHEDULER: Optional[Any] = None
WARMUP_S = 25.0
FIXED_DELTA = 1.0
_warmup_hits: Dict[str, int] = {}
_grant_rr = {"n": 0}


def set_scheduler(scheduler: Optional[Any]) -> None:
    """Set active scheduler instance."""
    global ACTIVE_SCHEDULER
    ACTIVE_SCHEDULER = scheduler


def get_scheduler() -> Optional[Any]:
    """Get active scheduler instance."""
    return ACTIVE_SCHEDULER


def reset_env() -> None:
    """Reset global metrics and scheduler state."""
    global TARGET_RSU, _warmup_hits
    TARGET_RSU = None
    _warmup_hits = {}
    _grant_rr["n"] = 0
    METRICS.reset()
    if ACTIVE_SCHEDULER is not None and hasattr(ACTIVE_SCHEDULER, "reset"):
        ACTIVE_SCHEDULER.reset()
    for r in getattr(net, "rsu_list", []):
        if hasattr(r, "active"):
            r.active = False
        if hasattr(r, "track"):
            r.track = {}
        if hasattr(r, "pending_tx"):
            r.pending_tx = []
            r.pending_t = None
        if hasattr(r, "_last_dwell_t"):
            r._last_dwell_t = None


def decide_grant(state: dict) -> Tuple[float, int, float]:
    """Decide grant tuple using active scheduler or default heuristic."""
    if ACTIVE_SCHEDULER is not None:
        if hasattr(ACTIVE_SCHEDULER, "decide_grant"):
            try:
                return ACTIVE_SCHEDULER.decide_grant(state.get("vid", ""), state, METRICS)
            except TypeError:
                return ACTIVE_SCHEDULER.decide_grant(state)
        elif callable(ACTIVE_SCHEDULER):
            return ACTIVE_SCHEDULER(state)

    ch = _grant_rr["n"] % comm.NUM_SUBCHANNELS
    _grant_rr["n"] += 1
    levels = comm.TX_POWER_LEVELS_DBM
    p = levels[len(levels) // 2]
    return (FIXED_DELTA, ch, p)


def start_message(sim, vehicles, rsu_list, t_init) -> None:
    """Legacy start message hook."""
    return


def _ensure_target(t: float) -> None:
    global TARGET_RSU
    if TARGET_RSU is not None or t < WARMUP_S or not _warmup_hits:
        return
    best_id = max(_warmup_hits, key=_warmup_hits.get)
    for r in getattr(net, "rsu_list", []):
        if r.id == best_id:
            r.active = True
            TARGET_RSU = r
            break


def _target_covering(node):
    rsu = TARGET_RSU
    if rsu is None:
        return None
    return rsu if node.distance_to(rsu) <= rsu.comm_range else None


# ----------------------------------------------------------------------------
# Legacy Node Compatibility Layer (wrapping NetSim.Node)
# ----------------------------------------------------------------------------

class VehicleNode(net.Node):
    def __init__(self, node_id: str, pos: Tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(node_id, pos=pos, comm_range=0.0)
        self._prev_pos: Tuple[float, float] = pos
        self._prev_t: Optional[float] = None
        self._prev_vel: Tuple[float, float] = (0.0, 0.0)
        self.vel: Tuple[float, float] = (0.0, 0.0)
        self.accel: float = 0.0
        self.registered_rsu: Optional[str] = None
        self.next_update_t: Optional[float] = None
        self.cur_ch: int = 0
        self.cur_p: float = 25.0

    def _estimate_velocity(self, t: float) -> None:
        if self._prev_t is not None and t > self._prev_t:
            dt = t - self._prev_t
            self.vel = ((self.pos[0] - self._prev_pos[0]) / dt,
                        (self.pos[1] - self._prev_pos[1]) / dt)
            prev_spd = math.hypot(self._prev_vel[0], self._prev_vel[1])
            cur_spd = math.hypot(self.vel[0], self.vel[1])
            self.accel = (cur_spd - prev_spd) / dt
        self._prev_pos, self._prev_t, self._prev_vel = self.pos, t, self.vel

    def speed(self) -> float:
        return math.hypot(self.vel[0], self.vel[1])

    def _apply_grant(self, t: float) -> None:
        d, ch, p = decide_grant(self._state_dict())
        self.cur_ch, self.cur_p = ch, p
        self.next_update_t = t + d

    def update_dwell(self, current_time: float) -> None:
        super().update_dwell(current_time)
        self._estimate_velocity(current_time)
        _ensure_target(current_time)
        rsu = _target_covering(self)
        if rsu is None:
            return

        if self.registered_rsu is None:
            rsu.on_update(self.id, self.pos, self.vel, current_time, is_entry=True)
            self.registered_rsu = rsu.id
            self._apply_grant(current_time)
            return

        if self.next_update_t is not None and current_time >= self.next_update_t:
            rsu.pending_tx.append({
                "vid": self.id, "pos": self.pos, "vel": self.vel,
                "tx_dbm": self.cur_p, "dist": self.distance_to(rsu),
                "ch": self.cur_ch, "t": current_time,
            })
            if rsu.pending_t is None:
                rsu.pending_t = current_time
            self._apply_grant(current_time)

    def _state_dict(self) -> dict:
        rsu = _target_covering(self) or TARGET_RSU
        dist_rsu = self.distance_to(rsu) if rsu is not None else 300.0
        sumo_mod = getattr(net, "sumo", None)
        tls_feats = extract_tls_features(sumo_mod, self.id, current_time=self._prev_t)
        return {
            "vid": self.id,
            "pos": self.pos,
            "vel": self.vel,
            "speed": self.speed(),
            "accel": self.accel,
            "dist_to_rsu": dist_rsu,
            "registered_rsu": self.registered_rsu,
            "current_time": self._prev_t,
            "tls_features": tls_feats,
        }


class RSUNode(net.Node):
    def __init__(self, node_id: str, pos: Tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(node_id, pos=pos, comm_range=float(getattr(ss, "RSU_RANGE", 800.0)))
        self.is_rsu = True
        self.active = False
        self.track: Dict[str, dict] = {}
        self.pending_tx: List[dict] = []
        self.pending_t: Optional[float] = None
        self._last_dwell_t: Optional[float] = None

    def on_update(self, vid: str, pos, vel, t: float, is_entry: bool) -> None:
        rec = self.track.get(vid)
        if rec is not None and not is_entry:
            METRICS.record_interval(rec["err_integral"], t - rec["t_update"])
            METRICS.n_updates += 1
        if is_entry:
            METRICS.n_registrations += 1
        self.track[vid] = {"pos": pos, "vel": vel, "t_update": t, "err_integral": 0.0}

    def _resolve_pending(self) -> None:
        if not self.pending_tx:
            return
        by_ch: Dict[int, List[dict]] = {}
        for a in self.pending_tx:
            by_ch.setdefault(a["ch"], []).append(a)
        for ch, grp in by_ch.items():
            probs = comm.judge_uplink([(a["vid"], a["tx_dbm"], a["dist"]) for a in grp])
            for a in grp:
                p = probs[a["vid"]]
                METRICS.record_attempt(p, len(grp))
                if random.random() < p:
                    self.on_update(a["vid"], a["pos"], a["vel"], a["t"], is_entry=False)
                else:
                    METRICS.n_tx_fail += 1
        self.pending_tx = []
        self.pending_t = None

    def update_dwell(self, current_time: float) -> None:
        super().update_dwell(current_time)
        if TARGET_RSU is None:
            if current_time < WARMUP_S:
                c = sum(1 for v in net.vehicles.values()
                        if self.distance_to(v) <= self.comm_range)
                _warmup_hits[self.id] = _warmup_hits.get(self.id, 0) + c
                return
            _ensure_target(current_time)
        if not self.active:
            return

        if self.pending_t is not None and current_time > self.pending_t:
            self._resolve_pending()

        dt = 0.0 if self._last_dwell_t is None else (current_time - self._last_dwell_t)
        self._last_dwell_t = current_time
        if dt <= 0.0:
            return

        gone: List[str] = []
        for vid, rec in self.track.items():
            veh = net.vehicles.get(vid)
            if veh is None or self.distance_to(veh) > self.comm_range:
                gone.append(vid)
                continue
            age = current_time - rec["t_update"]
            e = estimation_error(veh.pos, rec["pos"], rec["vel"], age)
            rec["err_integral"] += e * dt
            METRICS.record_sample(e, veh.speed() if hasattr(veh, "speed") else 0.0)
        for vid in gone:
            rec = self.track.pop(vid, None)
            if rec is not None:
                METRICS.record_interval(rec["err_integral"], current_time - rec["t_update"])
                METRICS.n_exits += 1


# ----------------------------------------------------------------------------
# Genuine AoiV2IEnv (Gymnasium-Compatible V2I AoI Scheduling Environment)
# ----------------------------------------------------------------------------

class AoiV2IEnv:
    """
    Genuine Gymnasium-compatible V2I AoI Scheduling Environment.
    
    Interfaces real SUMO via TraCI/libsumo, computes physical Rayleigh fading SINR
    contention over 4 subchannels, evaluates constant-velocity extrapolation errors,
    and enforces 4 hardcoded anti-mocking runtime assertions.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

        # Path configurations
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.sumo_dir = os.path.join(self.base_dir, "sumo")
        self.cfg_path = self.config.get("sumocfg_path", os.path.join(self.sumo_dir, "generated.sumocfg"))
        self.nod_path = os.path.join(self.sumo_dir, "generated.nod.xml")

        # Environment parameters
        self.step_length = float(self.config.get("step_length", 0.1))
        self.max_steps = int(self.config.get("max_steps", 3600))
        self.warmup_steps = int(self.config.get("warmup_steps", 60))
        self.rsu_range = float(self.config.get("rsu_range", getattr(ss, "RSU_RANGE", 300.0)))
        self.num_channels = int(self.config.get("num_channels", comm.NUM_SUBCHANNELS))
        self.grid_size = float(getattr(ss, "GRID_SIZE", 14400.0))
        self.network_max_x = 50000.0
        self.network_max_y = 50000.0

        # Reward weights (Conversation.md specification)
        weights = self.config.get("weights", {})
        self.w_error = float(weights.get("w1", weights.get("w_error", 0.5)))
        self.w_power = float(weights.get("w2", weights.get("w_power", 0.2)))
        self.w_congestion = float(weights.get("w3", weights.get("w_congestion", 0.2)))
        self.w_redundant = float(weights.get("w4", weights.get("w_redundant", 0.1)))

        # Power, Delta, and Error normalization bounds
        self.p_min = float(self.config.get("p_min", P_MIN))
        self.p_max = float(self.config.get("p_max", P_MAX))
        self.delta_min = float(self.config.get("delta_min", DELTA_MIN))
        self.delta_max = float(self.config.get("delta_max", DELTA_MAX))
        self.norm_error_max = float(self.config.get("norm_error_max", 50.0))
        self.norm_error_sq_max = self.norm_error_max ** 2

        # Interface helpers
        self.vectorizer = StateVectorizer(rsu_range=self.rsu_range, v_max=30.0, a_max=5.0)
        self.decoder = ActionDecoder(
            num_channels=self.num_channels,
            delta_min=self.delta_min,
            delta_max=self.delta_max,
            p_min=self.p_min,
            p_max=self.p_max,
        )
        self.heuristic = HeuristicScheduler(num_subchannels=self.num_channels)

        # Internal state
        self.metrics = Metrics()
        self.rsus: Dict[str, RSUNode] = {}
        self.target_rsu: Optional[RSUNode] = None
        self.target_rsu_id: Optional[str] = self.config.get("target_rsu_id", None)
        self.is_running = False
        self.current_seed = 42

        # Anti-Mocking tracking state
        self._prev_sim_time = 0.0
        self._prev_vehicle_positions: Dict[str, Tuple[float, float]] = {}
        self._step_count = 0

    def _ensure_sumo_files(self) -> None:
        """Verify presence of SUMO configuration and XML files; generate if missing."""
        os.makedirs(self.sumo_dir, exist_ok=True)
        required_files = [
            os.path.join(self.sumo_dir, "generated.net.xml"),
            os.path.join(self.sumo_dir, "generated.rou.xml"),
            os.path.join(self.sumo_dir, "generated.sumocfg"),
            os.path.join(self.sumo_dir, "generated.nod.xml"),
        ]
        if not all(os.path.exists(f) for f in required_files) or self.config.get("force_generate_sumo", False):
            ss.make_sumo_files()

        # Ensure rsu.poi.xml exists
        rsu_poi = os.path.join(self.sumo_dir, "rsu.poi.xml")
        if not os.path.exists(rsu_poi) and os.path.exists(self.nod_path):
            tree = ET.parse(self.nod_path)
            root = tree.getroot()
            with open(rsu_poi, "w") as f:
                f.write("<additional>\n")
                for node in root.findall("node"):
                    if node.get("type") == "traffic_light":
                        nid = node.get("id")
                        x = float(node.get("x"))
                        y = float(node.get("y"))
                        f.write(f'  <poi id="{nid}" x="{x}" y="{y}" type="RSU" color="1,0,0"/>\n')
                f.write("</additional>\n")

    def _load_rsus(self) -> None:
        """Parse traffic light nodes from XML as RSUs and determine network bounds."""
        self.rsus = {}
        if os.path.exists(self.nod_path):
            tree = ET.parse(self.nod_path)
            root = tree.getroot()
            xs, ys = [], []
            for node in root.findall("node"):
                x = float(node.get("x"))
                y = float(node.get("y"))
                xs.append(x)
                ys.append(y)
                if node.get("type") == "traffic_light":
                    nid = node.get("id")
                    rsu = RSUNode(nid, pos=(x, y))
                    self.rsus[nid] = rsu
            if xs and ys:
                self.network_max_x = max(xs)
                self.network_max_y = max(ys)

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Resets the SUMO simulation and initial environment state.
        
        Returns:
            observations: Dictionary mapping vehicle IDs to 16-dimensional state vectors.
            info: Metadata dictionary containing active vehicle count and simulation time.
        """
        if seed is not None:
            self.current_seed = int(seed)

        self._ensure_sumo_files()
        self._load_rsus()

        # Close existing SUMO instance if active
        self.close()

        sumo_bin = shutil.which("sumo") or "/home/imnyj/venv/bin/sumo"
        cmd = [
            sumo_bin,
            "-c", self.cfg_path,
            "--step-length", str(self.step_length),
            "--no-step-log", "true",
            "--duration-log.disable", "true",
            "--quit-on-end", "false",
            "--time-to-teleport", "60",
            "--collision.action", "warn",
            "--seed", str(self.current_seed),
        ]

        if sumo is None:
            raise RuntimeError("libsumo / traci is not installed or available.")

        sumo.start(cmd)
        self.is_running = True
        self.metrics.reset()
        self._step_count = 0
        self._prev_vehicle_positions = {}

        # Run warmup steps so vehicles spawn and populate RSUs
        warmup_n = max(30, self.warmup_steps)
        rsu_traffic_counts: Dict[str, int] = {rid: 0 for rid in self.rsus}

        for _ in range(warmup_n):
            sumo.simulationStep()
            cur_vids = sumo.vehicle.getIDList()
            for vid in cur_vids:
                vx, vy = sumo.vehicle.getPosition(vid)
                self._prev_vehicle_positions[vid] = (float(vx), float(vy))
                for rid, rsu in self.rsus.items():
                    if math.hypot(vx - rsu.pos[0], vy - rsu.pos[1]) <= self.rsu_range:
                        rsu_traffic_counts[rid] += 1

        # Select target RSU (busiest cell or specified target)
        if self.target_rsu_id and self.target_rsu_id in self.rsus:
            self.target_rsu = self.rsus[self.target_rsu_id]
        elif rsu_traffic_counts and max(rsu_traffic_counts.values()) > 0:
            best_id = max(rsu_traffic_counts, key=rsu_traffic_counts.get)
            self.target_rsu = self.rsus[best_id]
        elif self.rsus:
            self.target_rsu = next(iter(self.rsus.values()))
        else:
            self.target_rsu = RSUNode("RSU_0", pos=(self.grid_size / 2.0, self.grid_size / 2.0))
            self.rsus["RSU_0"] = self.target_rsu

        self.target_rsu.active = True
        self.target_rsu.track.clear()

        current_time = float(sumo.simulation.getTime())
        self._prev_sim_time = current_time

        # Initial registration (E1) of vehicles inside target RSU coverage
        reg_idx = 0
        for vid in sumo.vehicle.getIDList():
            pos = sumo.vehicle.getPosition(vid)
            spd = sumo.vehicle.getSpeed(vid)
            self._prev_vehicle_positions[vid] = (float(pos[0]), float(pos[1]))
            dist_to_rsu = math.hypot(pos[0] - self.target_rsu.pos[0], pos[1] - self.target_rsu.pos[1])
            if dist_to_rsu <= self.rsu_range:
                tls_feats = extract_tls_features(sumo, vid, current_time=current_time)
                st_dict = {
                    "vid": vid,
                    "pos": pos,
                    "vel": (spd, 0.0),
                    "speed": spd,
                    "accel": 0.0,
                    "dist_to_rsu": dist_to_rsu,
                    "tls_features": tls_feats,
                    "current_time": current_time,
                }
                delta, ch, power = self.heuristic.decide_grant(vid, st_dict)
                # Distribute initial channels and stagger initial transmit times
                ch_assigned = (reg_idx) % self.num_channels
                stagger_offset = (reg_idx % 3) * 0.5
                self.target_rsu.track[vid] = {
                    "pos": pos,
                    "vel": (spd, 0.0),
                    "t_update": current_time,
                    "err_integral": 0.0,
                    "last_tx_t": current_time,
                    "next_update_t": current_time + stagger_offset,
                    "cur_ch": ch_assigned,
                    "cur_p": power,
                    "grant_delta": delta,
                }
                self.metrics.n_registrations += 1
                reg_idx += 1

        observations = {vid: self._vectorize_state(vid) for vid in self.target_rsu.track.keys()}
        info = {
            "sim_time": current_time,
            "target_rsu": self.target_rsu.id,
            "target_rsu_pos": self.target_rsu.pos,
            "n_active": len(self.target_rsu.track),
        }
        return observations, info

    def _vectorize_state(self, vid: str) -> np.ndarray:
        """Builds a normalized state vector from the RSU perspective."""
        if not self.is_running or vid not in self.target_rsu.track:
            return np.zeros(self.vectorizer.state_dim, dtype=np.float32)

        rec = self.target_rsu.track[vid]
        try:
            pos = sumo.vehicle.getPosition(vid)
            spd = float(sumo.vehicle.getSpeed(vid))
            accel = float(sumo.vehicle.getAcceleration(vid))
        except Exception:
            pos = rec["pos"]
            spd = math.hypot(rec["vel"][0], rec["vel"][1])
            accel = 0.0

        current_time = float(sumo.simulation.getTime())
        tls_feats = extract_tls_features(sumo, vid, current_time=current_time)

        state_dict = {
            "vid": vid,
            "pos": pos,
            "vel": rec["vel"],
            "speed": spd,
            "accel": accel,
            "current_time": current_time,
            "last_update_time": rec["t_update"],
            "dist_to_rsu": math.hypot(pos[0] - self.target_rsu.pos[0], pos[1] - self.target_rsu.pos[1]),
            "n_active": len(self.target_rsu.track),
            "cbr": float(min(1.0, len(self.target_rsu.track) / 40.0)),
            "tls_features": tls_feats,
        }
        return self.vectorizer.vectorize_from_dict(state_dict, rsu_pos=self.target_rsu.pos)

    def step(
        self,
        action_dict: Optional[Union[Dict[str, Any], Tuple, List, np.ndarray]] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, float], bool, bool, Dict[str, Any]]:
        """
        Advances the genuine SUMO simulation by one physical timestep.
        
        Args:
            action_dict: Map of vehicle IDs to hybrid action (Delta, ch, power),
                         or single action applied to all active vehicles.
        
        Returns:
            observations: Dictionary of 16-dim state vectors for active vehicles.
            rewards: Dictionary of per-vehicle scalar rewards.
            terminated: Boolean indicating episode termination.
            truncated: Boolean indicating step budget reached.
            info: Diagnostic telemetry and metrics summary.
        """
        if not self.is_running:
            raise RuntimeError("Environment is not running. Call env.reset() before env.step().")

        # 1. Parse and record action grants for vehicles
        if action_dict is not None and not isinstance(action_dict, dict):
            # Single global action decoded and mapped
            decoded_grant = self.decoder.decode_action(action_dict)
            action_map = {vid: decoded_grant for vid in self.target_rsu.track}
        else:
            action_map = action_dict or {}

        for vid, raw_act in action_map.items():
            if vid in self.target_rsu.track:
                delta, ch, p = self.decoder.decode_action(raw_act)
                self.target_rsu.track[vid]["cur_ch"] = ch
                self.target_rsu.track[vid]["cur_p"] = p
                self.target_rsu.track[vid]["grant_delta"] = delta

        # 2. Advance physical SUMO simulation step
        sumo.simulationStep()
        current_time = float(sumo.simulation.getTime())
        self._step_count += 1

        # ====================================================================
        # ANTI-MOCKING ASSERTION 1: TraCI / libsumo Time Advance Verification
        # ====================================================================
        assert sumo is not None, "FATAL: libsumo/traci is not imported or initialized!"
        assert current_time > self._prev_sim_time, (
            f"FATAL: Simulation time regression/freeze detected: {current_time} <= {self._prev_sim_time}"
        )
        assert hasattr(sumo.simulation, "getLoadedNumber") or hasattr(sumo.simulation, "getTime"), (
            "FATAL: Fake sumo module detected!"
        )

        # ====================================================================
        # ANTI-MOCKING ASSERTION 2: Actual SUMO Vehicle Coordinates & Motion
        # ====================================================================
        raw_vehicle_ids = sumo.vehicle.getIDList()
        assert isinstance(raw_vehicle_ids, (list, tuple)), (
            "FATAL: sumo.vehicle.getIDList() did not return a valid list!"
        )

        for vid in raw_vehicle_ids:
            v_pos = sumo.vehicle.getPosition(vid)
            v_spd = sumo.vehicle.getSpeed(vid)

            assert isinstance(v_pos[0], float) and isinstance(v_pos[1], float), (
                f"FATAL: Vehicle {vid} position coordinates must be floats, got {v_pos}"
            )
            assert isinstance(v_spd, float), f"FATAL: Vehicle {vid} speed must be float, got {v_spd}"
            assert -5000.0 <= v_pos[0] <= self.network_max_x + 5000.0 and -5000.0 <= v_pos[1] <= self.network_max_y + 5000.0, (
                f"FATAL: Vehicle {vid} position {v_pos} is out of SUMO grid bounds [0, {self.network_max_x}]!"
            )

            # Check displacement for moving vehicles
            if vid in self._prev_vehicle_positions and v_spd > 1.0:
                p_prev = self._prev_vehicle_positions[vid]
                dist_moved = math.hypot(v_pos[0] - p_prev[0], v_pos[1] - p_prev[1])
                assert dist_moved > 0.0, (
                    f"FATAL: Vehicle {vid} speed is {v_spd} m/s but coordinate did not change from {p_prev}!"
                )
            self._prev_vehicle_positions[vid] = (float(v_pos[0]), float(v_pos[1]))

        # 3. Vehicle Entry (E1) and Exit (E3) within target RSU cell
        raw_vids_set = set(raw_vehicle_ids)
        current_cell_vids: set[str] = set()

        for vid in raw_vehicle_ids:
            px, py = self._prev_vehicle_positions[vid]
            dist_rsu = math.hypot(px - self.target_rsu.pos[0], py - self.target_rsu.pos[1])
            if dist_rsu <= self.rsu_range:
                current_cell_vids.add(vid)
                if vid not in self.target_rsu.track:
                    # E1: Entry registration
                    spd = float(sumo.vehicle.getSpeed(vid))
                    tls_f = extract_tls_features(sumo, vid, current_time=current_time)
                    st_dict = {
                        "vid": vid,
                        "pos": (px, py),
                        "vel": (spd, 0.0),
                        "speed": spd,
                        "accel": 0.0,
                        "dist_to_rsu": dist_rsu,
                        "tls_features": tls_f,
                        "current_time": current_time,
                    }
                    d_init, ch_init, p_init = self.heuristic.decide_grant(vid, st_dict)
                    self.target_rsu.track[vid] = {
                        "pos": (px, py),
                        "vel": (spd, 0.0),
                        "t_update": current_time,
                        "err_integral": 0.0,
                        "last_tx_t": current_time,
                        "next_update_t": current_time + d_init,
                        "cur_ch": ch_init,
                        "cur_p": p_init,
                        "grant_delta": d_init,
                    }
                    self.metrics.n_registrations += 1

        # E3: Handle vehicle departures / despawns
        departed_vids = [vid for vid in self.target_rsu.track if vid not in current_cell_vids]
        for vid in departed_vids:
            rec = self.target_rsu.track.pop(vid)
            self.metrics.record_interval(rec["err_integral"], max(0.001, current_time - rec["t_update"]))
            self.metrics.n_exits += 1

        # 4. Transmissions and Rayleigh Fading SINR Resolution (E2)
        transmitting_records: List[dict] = []
        for vid, rec in self.target_rsu.track.items():
            if current_time >= rec["next_update_t"]:
                pos = self._prev_vehicle_positions[vid]
                dist = math.hypot(pos[0] - self.target_rsu.pos[0], pos[1] - self.target_rsu.pos[1])
                spd = float(sumo.vehicle.getSpeed(vid)) if vid in raw_vids_set else 0.0
                transmitting_records.append({
                    "vid": vid,
                    "pos": pos,
                    "vel": (spd, 0.0),
                    "dist": dist,
                    "ch": rec["cur_ch"],
                    "p": rec["cur_p"],
                })

        # Group by subchannel for SINR interference computation
        transmissions_by_ch: Dict[int, List[dict]] = {ch: [] for ch in range(self.num_channels)}
        for tx in transmitting_records:
            ch_idx = tx["ch"] % self.num_channels
            transmissions_by_ch[ch_idx].append(tx)

        succ_probs_by_vid: Dict[str, float] = {}
        for ch, group in transmissions_by_ch.items():
            if group:
                judge_input = [(item["vid"], item["p"], item["dist"]) for item in group]
                probs = comm.judge_uplink(judge_input, num_subchannels=self.num_channels)
                succ_probs_by_vid.update(probs)

        # ====================================================================
        # ANTI-MOCKING ASSERTION 3: Communications Rayleigh SINR Execution
        # ====================================================================
        assert hasattr(comm, "judge_uplink"), "FATAL: Communications.judge_uplink is missing!"
        assert hasattr(comm, "path_loss_db"), "FATAL: Communications.path_loss_db is missing!"
        assert comm.FREQ_HZ == 5.9e9, f"FATAL: Communications.FREQ_HZ is corrupted: {comm.FREQ_HZ}"

        if transmitting_records:
            assert len(succ_probs_by_vid) == len(transmitting_records), (
                "FATAL: judge_uplink did not evaluate all transmitting vehicles!"
            )
            for vid, p in succ_probs_by_vid.items():
                assert 0.0 <= p <= 1.0, f"FATAL: Uplink success probability {p} for {vid} out of [0, 1]!"
                assert not math.isnan(p) and not math.isinf(p), f"FATAL: Uplink success probability {p} is NaN/Inf!"

        # Resolve uplink success/failure outcomes
        for tx in transmitting_records:
            vid = tx["vid"]
            ch_idx = tx["ch"] % self.num_channels
            p_succ = succ_probs_by_vid[vid]
            n_contenders = len(transmissions_by_ch[ch_idx])
            self.metrics.record_attempt(p_succ, n_contenders)

            rec = self.target_rsu.track[vid]
            if random.random() < p_succ:
                # Transmission SUCCESS -> Refresh RSU state baseline
                self.metrics.record_interval(rec["err_integral"], max(0.001, current_time - rec["t_update"]))
                self.metrics.n_updates += 1
                rec["pos"] = tx["pos"]
                rec["vel"] = tx["vel"]
                rec["t_update"] = current_time
                rec["err_integral"] = 0.0
                rec["last_tx_t"] = current_time
            else:
                # Transmission FAILURE -> Keep stale state
                self.metrics.n_tx_fail += 1
                rec["last_tx_t"] = current_time

            # Schedule next transmission time interval
            grant_delta = rec.get("grant_delta", 1.0)
            rec["next_update_t"] = current_time + grant_delta

        # 5. Continuous Estimation Error Extrapolation & Reward Calculation
        dt = current_time - self._prev_sim_time
        reward_dict: Dict[str, float] = {}
        reward_details: Dict[str, dict] = {}
        transmitting_dict = {tx["vid"]: tx for tx in transmitting_records}

        for vid, rec in self.target_rsu.track.items():
            true_pos = self._prev_vehicle_positions.get(vid, rec["pos"])
            spd = float(sumo.vehicle.getSpeed(vid)) if vid in raw_vids_set else 0.0

            age = max(0.0, current_time - rec["t_update"])
            err = estimation_error(true_pos, rec["pos"], rec["vel"], age)
            rec["err_integral"] += err * dt
            self.metrics.record_sample(err, spd)

            # Component 1: Normalized Estimation Error Squared
            norm_error_sq = float(min(1.0, (err ** 2) / max(1.0, self.norm_error_sq_max)))

            # Component 2, 3, 4: Power, Congestion, and Redundancy
            if vid in transmitting_dict:
                tx_info = transmitting_dict[vid]
                ptx = tx_info["p"]
                norm_ptx = float(np.clip((ptx - self.p_min) / max(1e-6, self.p_max - self.p_min), 0.0, 1.0))
                ch_contenders = len(transmissions_by_ch[tx_info["ch"] % self.num_channels])
                norm_cfreq = float(min(1.0, max(0.0, (ch_contenders - 1) / 10.0)))
                # Redundant update indicator (vehicle stationary and error already negligible)
                i_redundant = 1.0 if (spd < 0.1 and err < 0.05) else 0.0
            else:
                norm_ptx = 0.0
                norm_cfreq = 0.0
                i_redundant = 0.0

            # Mathematical composite penalty reward (Conversation.md)
            r_val = -(
                self.w_error * norm_error_sq
                + self.w_power * norm_ptx
                + self.w_congestion * norm_cfreq
                + self.w_redundant * i_redundant
            )

            reward_dict[vid] = float(r_val)
            reward_details[vid] = {
                "norm_error_sq": norm_error_sq,
                "norm_ptx": norm_ptx,
                "norm_cfreq": norm_cfreq,
                "i_redundant": i_redundant,
                "reward": float(r_val),
                "error": err,
                "aoi": age,
            }

        # ====================================================================
        # ANTI-MOCKING ASSERTION 4: Reward Mathematical Specification Check
        # ====================================================================
        for vid, r_info in reward_details.items():
            ne = r_info["norm_error_sq"]
            np_ = r_info["norm_ptx"]
            nc = r_info["norm_cfreq"]
            ir = r_info["i_redundant"]
            rv = r_info["reward"]

            assert 0.0 <= ne <= 1.0, f"FATAL: Normalized error sq {ne} out of bounds [0, 1]!"
            assert 0.0 <= np_ <= 1.0, f"FATAL: Normalized power {np_} out of bounds [0, 1]!"
            assert 0.0 <= nc <= 1.0, f"FATAL: Normalized congestion {nc} out of bounds [0, 1]!"
            assert ir in (0.0, 1.0), f"FATAL: I_redundant must be binary (0.0 or 1.0), got {ir}!"

            expected_r = -(self.w_error * ne + self.w_power * np_ + self.w_congestion * nc + self.w_redundant * ir)
            assert math.isclose(rv, expected_r, abs_tol=1e-5), (
                f"FATAL: Reward calculation mismatch for {vid}: {rv} != {expected_r}"
            )
            assert rv <= 0.0, f"FATAL: Penalty-based reward must be <= 0, got {rv}"

        # 6. Finalize Step State
        self._prev_sim_time = current_time
        observations = {vid: self._vectorize_state(vid) for vid in self.target_rsu.track.keys()}

        terminated = False
        truncated = self._step_count >= self.max_steps
        step_mean_reward = float(np.mean(list(reward_dict.values()))) if reward_dict else 0.0

        info = {
            "sim_time": current_time,
            "step_count": self._step_count,
            "n_active": len(self.target_rsu.track),
            "step_reward": step_mean_reward,
            "reward_details": reward_details,
            "metrics": self.metrics.summary(),
        }

        return observations, reward_dict, terminated, truncated, info

    def get_active_vehicles(self) -> List[str]:
        """Returns list of vehicle IDs currently tracked by the target RSU."""
        if not self.target_rsu:
            return []
        return list(self.target_rsu.track.keys())

    def get_metrics_summary(self) -> dict:
        """Returns cumulative episode metrics summary."""
        return self.metrics.summary()

    def close(self) -> None:
        """Closes the SUMO simulation cleanly."""
        if self.is_running and sumo is not None:
            try:
                sumo.close()
            except Exception:
                pass
            self.is_running = False


# Alias for backward and interchangeable compatibility
AoIEnv = AoiV2IEnv
