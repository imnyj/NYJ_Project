# aoi_env.py
# ============================================================================
# S1+S2 -- Environment layer for AoI-aware V2I uplink update scheduling.
#
# S1 (event-driven env + retrospective estimation error):
#   E1 entry  : vehicle enters the target RSU cell and registers its state.
#   E2 update : at scheduled instants the vehicle re-sends its state; on success
#               the RSU refreshes (x_hat, tau) and finalizes the error integral
#               accumulated over the elapsed interval (retrospective).
#   E3 exit   : vehicle leaves the cell / despawns; its interval is closed.
#   The RSU extrapolates each last-known state at constant velocity and, every
#   step, integrates the gap to the true position (SUMO ground truth). Stationary
#   or constant-velocity vehicles yield ~0 error regardless of age.
#
# S2 (probabilistic SINR uplink):
#   A grant is (Delta, subchannel, power). E2 transmissions on the SAME
#   subchannel within a step interfere; success is judged by Communications.
#   judge_uplink (Rayleigh SINR). Only successful transmissions refresh the RSU;
#   failures leave the estimate stale (error keeps accumulating). Because RSUs
#   are stepped before vehicles, a step's attempts are resolved on the next step
#   (a one-step processing delay).
#
# The placeholder decide_grant (fixed Delta, round-robin subchannel, mid power)
# is replaced by the RL agent in S3/S4.
# ============================================================================
from __future__ import annotations
import math
import random
from typing import Dict, Optional, Tuple, List
import src.NetSim as net
import src.sumo.make_sumo_set as ss
import src.Communications as comm

# ----------------------------------------------------------------------------
# Config (placeholder scheduler for S1/S2; the agent overrides decide_grant)
# ----------------------------------------------------------------------------
FIXED_DELTA = 1.0          # s -- placeholder inter-update interval
WARMUP_S    = 25.0         # pick the busiest cell after this, then start scheduling


# ----------------------------------------------------------------------------
# Pure estimation-error math (SUMO-independent -> unit-testable)
# ----------------------------------------------------------------------------
def extrapolate(pos: Tuple[float, float], vel: Tuple[float, float], dt: float) -> Tuple[float, float]:
    return (pos[0] + vel[0] * dt, pos[1] + vel[1] * dt)


def estimation_error(true_pos: Tuple[float, float],
                     last_pos: Tuple[float, float],
                     last_vel: Tuple[float, float],
                     age: float) -> float:
    ex, ey = extrapolate(last_pos, last_vel, age)
    return math.hypot(true_pos[0] - ex, true_pos[1] - ey)


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
class Metrics:
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
        # S2 uplink stats
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
            self.err_sum_lowspeed += e; self.n_lowspeed += 1
        else:
            self.err_sum_highspeed += e; self.n_highspeed += 1

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

# The single active RSU cell (design: one RSU cell). Chosen as the busiest RSU
# after a warmup window (a central-by-geometry RSU may carry little traffic).
TARGET_RSU = None
_warmup_hits: Dict[str, int] = {}
_grant_rr = {"n": 0}


def reset_env() -> None:
    """Reset per-episode env state (call before each run)."""
    global TARGET_RSU, _warmup_hits
    TARGET_RSU = None
    _warmup_hits = {}
    _grant_rr["n"] = 0
    METRICS.reset()
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


def decide_grant(state: dict) -> Tuple[float, int, float]:
    """Placeholder scheduler (S1/S2): fixed interval, round-robin subchannel,
    mid power. S3/S4 replace this with the RL agent's grant."""
    ch = _grant_rr["n"] % comm.NUM_SUBCHANNELS
    _grant_rr["n"] += 1
    levels = comm.TX_POWER_LEVELS_DBM
    p = levels[len(levels) // 2]
    return (FIXED_DELTA, ch, p)


def _target_covering(node):
    rsu = TARGET_RSU
    if rsu is None:
        return None
    return rsu if node.distance_to(rsu) <= rsu.comm_range else None


# ----------------------------------------------------------------------------
# Nodes
# ----------------------------------------------------------------------------
class VehicleNode(net.Node):
    def __init__(self, node_id: str, pos: Tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(node_id, pos=pos, comm_range=0.0)
        self._prev_pos: Tuple[float, float] = pos
        self._prev_t: Optional[float] = None
        self.vel: Tuple[float, float] = (0.0, 0.0)
        self.registered_rsu: Optional[str] = None
        self.next_update_t: Optional[float] = None
        self.cur_ch: int = 0
        self.cur_p: float = comm.TX_POWER_LEVELS_DBM[len(comm.TX_POWER_LEVELS_DBM) // 2]

    def _estimate_velocity(self, t: float) -> None:
        if self._prev_t is not None and t > self._prev_t:
            dt = t - self._prev_t
            self.vel = ((self.pos[0] - self._prev_pos[0]) / dt,
                        (self.pos[1] - self._prev_pos[1]) / dt)
        self._prev_pos, self._prev_t = self.pos, t

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
            # E1: entry registration (direct; entry beacon assumed to succeed)
            rsu.on_update(self.id, self.pos, self.vel, current_time, is_entry=True)
            self.registered_rsu = rsu.id
            self._apply_grant(current_time)
            return

        # E2: scheduled uplink attempt -> queued for SINR resolution
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
        return {"vid": self.id, "pos": self.pos, "vel": self.vel, "speed": self.speed()}


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

        # resolve the previous step's uplink attempts (one-step processing delay)
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
                gone.append(vid); continue
            age = current_time - rec["t_update"]
            e = estimation_error(veh.pos, rec["pos"], rec["vel"], age)
            rec["err_integral"] += e * dt
            METRICS.record_sample(e, veh.speed() if hasattr(veh, "speed") else 0.0)
        for vid in gone:
            rec = self.track.pop(vid, None)
            if rec is not None:
                METRICS.record_interval(rec["err_integral"], current_time - rec["t_update"])
                METRICS.n_exits += 1


def start_message(sim, vehicles, rsu_list, t_init) -> None:
    return
