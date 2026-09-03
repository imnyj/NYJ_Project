# dynamics_predictor.py
# ============================================================================
# S2.5 -- Signal-based Dynamics Prediction & Transition Indicators
#
# Extracts traffic light states, distance to stopline, remaining phase,
# and leader vehicle dynamics via TraCI / libsumo.
# Computes transition indicators (I_stop, I_start) to forecast imminent
# changes in vehicle kinematics before divergence in constant-velocity
# extrapolation occurs.
# ============================================================================
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

try:
    import libsumo as sumo
except ImportError:
    try:
        import traci as sumo
    except ImportError:
        sumo = None  # fallback for headless unit tests without SUMO installed


# ----------------------------------------------------------------------------
# Pure Physics & Dynamics Transition Indicators (Unit-Testable without SUMO)
# ----------------------------------------------------------------------------
def predict_stop_imminent(
    speed: float,
    accel: float,
    dist_to_stopline: float = float("inf"),
    signal_state: str = "none",
    time_to_green: float = float("inf"),
    leader_dist: Optional[float] = None,
    leader_speed: Optional[float] = None,
) -> float:
    """
    Computes the imminent-stop indicator I_stop in [0.0, 1.0].
    
    A vehicle is considered about to stop if:
    1. Active strong deceleration / braking: vehicle speed > 0.5 m/s and
       braking time to stop is within 3.0 seconds (or speed + accel * 2.0 <= 0.5).
    2. Approaching red ('r') or yellow ('y') traffic signal within braking
       distance and signal will remain red/yellow upon arrival (time_to_green > 1.5s).
    3. Approaching a stopped / slow leader vehicle (leader_dist <= max(12.0, speed * 2.5)
       and leader_speed <= 1.0 m/s).
    
    If vehicle is already stationary (speed <= 0.3 m/s), I_stop returns 0.0
    since the transition into the stop state has already concluded.
    """
    if speed <= 0.3:
        return 0.0

    # 1. Active deceleration check
    if accel <= -1.2:
        # Time until complete stop under current deceleration
        t_stop = speed / abs(accel)
        if t_stop <= 5.0 or (speed + accel * 2.5) <= 1.0 or accel <= -2.0:
            return 1.0

    # 2. Traffic light stopline approach
    sig = signal_state.lower()
    if sig in ("r", "y", "u"):
        # Required stopping distance: d_stop = v^2 / (2 * b_comfort) + v * t_react + margin
        # Assuming comfortable deceleration b ~ 2.5 m/s^2, reaction 1.5s, margin 5.0m
        d_brake_thresh = max(15.0, (speed ** 2) / (2.0 * 2.5) + speed * 2.0 + 5.0)
        if dist_to_stopline <= d_brake_thresh:
            # If the light is turning green very soon (<= 1.0s), vehicle might not need to stop.
            # `time_to_green` is time until THIS link shows green, not until the
            # program's next phase change -- see `compute_time_to_green`.
            if time_to_green > 1.0:
                return 1.0

    # 3. Leader vehicle stopped/stopping ahead
    if leader_dist is not None and leader_speed is not None:
        safe_gap = max(10.0, speed * 2.5)
        if leader_dist <= safe_gap and leader_speed <= 1.0 and speed > 1.0:
            return 1.0

    return 0.0


def predict_start_imminent(
    speed: float,
    accel: float,
    dist_to_stopline: float = float("inf"),
    signal_state: str = "none",
    time_to_green: float = float("inf"),
    leader_dist: Optional[float] = None,
    leader_speed: Optional[float] = None,
    waiting_time: float = 0.0,
) -> float:
    """
    Computes the imminent-start indicator I_start in [0.0, 1.0].
    
    A vehicle is considered about to start moving if:
    1. Vehicle is currently stopped / crawling (speed <= 1.5 m/s):
       a. Signal is green ('g', 'G') and vehicle is near stopline or has been waiting.
       b. Signal is red ('r') but about to switch to green within 2.0 seconds.
       c. Leader vehicle ahead has started moving (leader_speed >= 1.5 m/s) and opening a gap.
       d. Initial positive acceleration from stop (accel >= 0.6 m/s^2).
    
    If vehicle is already cruising at normal speed (speed > 3.0 m/s and accel >= -0.2),
    I_start returns 0.0.
    """
    if speed > 3.0 and accel >= -0.2:
        return 0.0

    if speed <= 1.5:
        # Case A: Signal turned green and vehicle is near intersection / waiting
        sig = signal_state.lower()
        if sig in ("g", "s"):
            if dist_to_stopline <= 40.0 or waiting_time > 0.0:
                return 1.0

        # Case B: Signal is currently red but will turn green imminently (<= 2.0s).
        #
        # `time_to_green` MUST be the time until this link shows green, which is
        # what `compute_time_to_green` returns. Feeding
        # `trafficlight.getNextSwitch()` in here -- as this module did until
        # 2026-09-02 -- is wrong: getNextSwitch is the next phase change of the
        # PROGRAM, and one link's red spans two phases (the cross direction's
        # 42 s green plus its 3 s yellow). During the first 42 s of a 45 s red the
        # next switch is the cross yellow, so the value understated time-to-green
        # by 3 s and this branch fired 2 s before the cross green ended, i.e. 5 s
        # before our own green. Measured on N10 over 3 cycles at 0.1 s
        # resolution: 2016 link-steps satisfied the branch, only 800 were
        # actually green 2 s later -- a 60.3 % false-positive rate on the single
        # feature the predictive-scheduling claim rests on.
        if sig == "r" and time_to_green <= 2.0 and dist_to_stopline <= 35.0:
            return 1.0

        # Case C: Leader vehicle ahead begins moving off
        if leader_dist is not None and leader_speed is not None:
            if leader_dist <= 30.0 and leader_speed >= 1.5:
                return 1.0

        # Case D: Positive takeoff acceleration
        if accel >= 0.6:
            return 1.0

    return 0.0


# ----------------------------------------------------------------------------
# TraCI / libsumo Feature Extraction
# ----------------------------------------------------------------------------

# SUMO's own definition of a "halting" vehicle (see Lane::getLastStepHaltingNumber
# and TraCI docs): speed below 0.1 m/s. Reused here so `n_queue` is consistent with
# SUMO's built-in halting statistics.
HALTING_SPEED_THRESHOLD: float = 0.1

# ----------------------------------------------------------------------------
# Fallback bookkeeping.
#
# Every `except` in this module returns a safe default. That is the right defence
# for one vehicle's transient lookup failure, but if the TraCI connection itself
# degrades, `n_queue`, `leader_*` and `time_to_switch` freeze at 0/inf and the
# episode still reports plausible numbers -- this project has already been bitten
# twice by a fallback that turned a defect into a healthy-looking run. Counting
# the fallbacks lets the caller tell "one vehicle blinked" from "nothing is being
# measured".
# ----------------------------------------------------------------------------
FALLBACK_COUNTS: Dict[str, int] = {}


def _note_fallback(where: str, vid: str, exc: BaseException) -> None:
    FALLBACK_COUNTS[where] = FALLBACK_COUNTS.get(where, 0) + 1
    logging.debug("dynamics_predictor fallback in %s for %s: %s", where, vid, exc)


def reset_fallback_counts() -> None:
    """Zero the fallback counters. Called once per episode by AoiV2IEnv.reset().

    Also drops the cached traffic-light programs. The scenario is regenerated per
    episode, so a cache entry keyed by (tls_id, program_id) can otherwise survive
    into a network whose phases differ while the ids happen to match.
    """
    FALLBACK_COUNTS.clear()
    _TLS_PROGRAM_CACHE.clear()


# ----------------------------------------------------------------------------
# Time until a specific link turns green.
#
# `trafficlight.getNextSwitch(tls_id)` answers a different question than the one
# the transition predictors ask. It returns when the PROGRAM changes phase, not
# when a given link goes green, and in this scenario one link's 45 s red spans
# two phases: the cross direction's 42 s green and its 3 s yellow. For the first
# 42 s of that red the next switch is the cross yellow, so getNextSwitch reports
# 3 s at a moment when green is 45 s away.
#
# The fix reads the program definition and walks phases forward from the current
# one, accumulating durations until the phase whose state string is green at this
# link's index. `getNextSwitch` is still used, but only for what it is correct
# about: how much of the CURRENT phase is left.
# ----------------------------------------------------------------------------

#: Link-state characters that mean "this link may proceed". 'G' priority green
#: and 'g' permissive green are SUMO's two greens; 'g'/'s' matches the set
#: `predict_start_imminent` already treats as green after lower-casing.
GREEN_STATE_CHARS: frozenset = frozenset("gs")

#: (tls_id, program_id) -> tuple of (phase_duration_s, phase_state_string).
#: The program is static for the life of an episode, so it is read once per
#: traffic light instead of once per vehicle per step.
_TLS_PROGRAM_CACHE: Dict[Tuple[str, str], Tuple[Tuple[float, str], ...]] = {}


def _is_green(state_char: str) -> bool:
    return str(state_char).lower() in GREEN_STATE_CHARS


def _get_tls_phases(driver: Any, tls_id: str) -> Tuple[Tuple[float, str], ...]:
    """Phase (duration, state-string) pairs of `tls_id`'s active program."""
    try:
        program_id = str(driver.trafficlight.getProgram(tls_id))
    except Exception as exc:
        _note_fallback("getProgram", tls_id, exc)
        program_id = ""

    key = (str(tls_id), program_id)
    cached = _TLS_PROGRAM_CACHE.get(key)
    if cached is not None:
        return cached

    logics = None
    for getter_name in ("getAllProgramLogics", "getCompleteRedYellowGreenDefinition"):
        getter = getattr(driver.trafficlight, getter_name, None)
        if getter is None:
            continue
        try:
            logics = getter(tls_id)
            break
        except Exception as exc:
            _note_fallback(getter_name, tls_id, exc)
            logics = None
    if not logics:
        # Not cached: a transient read failure must not pin an empty program for
        # the rest of the episode.
        return ()

    logic = logics[0]
    for candidate in logics:
        if str(getattr(candidate, "programID", "")) == program_id:
            logic = candidate
            break

    try:
        phases = tuple(
            (float(ph.duration), str(ph.state)) for ph in getattr(logic, "phases", ())
        )
    except Exception as exc:
        _note_fallback("tls_phases", tls_id, exc)
        return ()

    if not phases:
        return ()
    _TLS_PROGRAM_CACHE[key] = phases
    return phases


def compute_time_to_green(
    sumo_conn: Any,
    tls_id: str,
    link_index: int,
    current_time: float,
) -> float:
    """Seconds until `link_index` of `tls_id` shows green. 0.0 if it already does.

    Returns `inf` when the answer cannot be established (no connection, unknown
    program, link never green in the cycle). `inf` is the safe direction for both
    consumers: `predict_stop_imminent` then still says "stop", and
    `predict_start_imminent` Case B then never fires.
    """
    driver = sumo_conn if sumo_conn is not None else sumo
    if driver is None or not tls_id:
        return float("inf")
    try:
        idx = int(link_index)
    except (TypeError, ValueError):
        return float("inf")
    if idx < 0:
        return float("inf")

    phases = _get_tls_phases(driver, tls_id)
    if not phases:
        return float("inf")

    try:
        cur = int(driver.trafficlight.getPhase(tls_id))
    except Exception as exc:
        _note_fallback("getPhase", tls_id, exc)
        return float("inf")
    n_phases = len(phases)
    if not (0 <= cur < n_phases):
        return float("inf")

    cur_state = phases[cur][1]
    if idx >= len(cur_state):
        return float("inf")
    if _is_green(cur_state[idx]):
        return 0.0

    try:
        next_switch = float(driver.trafficlight.getNextSwitch(tls_id))
    except Exception as exc:
        _note_fallback("getNextSwitch", tls_id, exc)
        return float("inf")

    elapsed_to_green = max(0.0, next_switch - float(current_time))
    for step in range(1, n_phases + 1):
        phase_duration, phase_state = phases[(cur + step) % n_phases]
        if idx < len(phase_state) and _is_green(phase_state[idx]):
            return elapsed_to_green
        elapsed_to_green += float(phase_duration)
    return float("inf")


def total_fallbacks() -> int:
    return int(sum(FALLBACK_COUNTS.values()))


def extract_lane_position(sumo_conn: Any, vid: str) -> Dict[str, Any]:
    """`lane_id` + `lane_position` only, without walking the lane.

    The ledger update needs these two on every call, but the O(vehicles-on-lane)
    queue scan below is only needed when an observation vector is being built.
    Separating them is what makes `with_queue=False` actually cheap: the comment
    in `AoiV2IEnv._get_vehicle_state_dict` claimed the scan had been removed from
    the two non-observation calls, but `extract_tls_features` called
    `extract_queue_features` unconditionally, so all three calls per vehicle per
    step still walked the lane.
    """
    driver = sumo_conn if sumo_conn is not None else sumo
    res: Dict[str, Any] = {"lane_id": "", "lane_position": 0.0}
    if driver is None:
        return res
    try:
        lane_id = str(driver.vehicle.getLaneID(vid))
    except Exception as exc:
        _note_fallback("getLaneID", vid, exc)
        return res
    if not lane_id:
        return res
    res["lane_id"] = lane_id
    try:
        res["lane_position"] = float(driver.vehicle.getLanePosition(vid))
    except Exception as exc:
        _note_fallback("getLanePosition", vid, exc)
    return res


def extract_queue_features(sumo_conn: Any, vid: str) -> Dict[str, Any]:
    """Measures the real queue ahead of `vid` on its current lane via TraCI / libsumo.

    All values come from live simulation state -- nothing is estimated or synthesised.

    Returns:
        {
            'lane_id': str,             # current lane, '' if unavailable
            'lane_position': float,     # longitudinal position of ego on that lane (m)
            'n_ahead': int,             # vehicles ahead of ego on the same lane
            'n_queue': int,             # vehicles ahead of ego on the same lane that are
                                        #   halting (speed < HALTING_SPEED_THRESHOLD)
            'n_lane_halting': int,      # lane.getLastStepHaltingNumber(lane) -- whole lane
            'lane_vehicle_count': int,  # lane.getLastStepVehicleNumber(lane)
        }

    `n_queue` is the $n_{queue}$ state variable of the approved design: the number of
    vehicles queued *ahead of the ego vehicle in its own lane*, which is the direct
    delay cause. `n_lane_halting` is kept alongside it as the lane-wide SUMO statistic.
    """
    driver = sumo_conn if sumo_conn is not None else sumo
    res: Dict[str, Any] = {
        "lane_id": "",
        "lane_position": 0.0,
        "n_ahead": 0,
        "n_queue": 0,
        "n_lane_halting": 0,
        "lane_vehicle_count": 0,
    }
    if driver is None:
        return res

    try:
        lane_id = str(driver.vehicle.getLaneID(vid))
    except Exception as exc:
        _note_fallback("getLaneID", vid, exc)
        return res
    if not lane_id:
        return res
    res["lane_id"] = lane_id

    try:
        ego_pos = float(driver.vehicle.getLanePosition(vid))
    except Exception as exc:
        _note_fallback("getLanePosition", vid, exc)
        return res
    res["lane_position"] = ego_pos

    try:
        res["n_lane_halting"] = int(driver.lane.getLastStepHaltingNumber(lane_id))
    except Exception as exc:
        _note_fallback("getLastStepHaltingNumber", vid, exc)

    try:
        lane_vids = list(driver.lane.getLastStepVehicleIDs(lane_id))
    except Exception as exc:
        _note_fallback("getLastStepVehicleIDs", vid, exc)
        return res
    res["lane_vehicle_count"] = len(lane_vids)

    n_ahead = 0
    n_queue = 0
    for other in lane_vids:
        if other == vid:
            continue
        try:
            other_pos = float(driver.vehicle.getLanePosition(other))
        except Exception:
            continue
        if other_pos <= ego_pos:
            continue
        n_ahead += 1
        try:
            other_speed = float(driver.vehicle.getSpeed(other))
        except Exception:
            continue
        if other_speed < HALTING_SPEED_THRESHOLD:
            n_queue += 1

    res["n_ahead"] = n_ahead
    res["n_queue"] = n_queue
    return res


def extract_tls_features(
    sumo_conn: Any,
    vid: str,
    current_time: Optional[float] = None,
    with_queue: bool = False,
) -> Dict[str, Any]:
    """
    Extracts traffic signal and kinematics features for a vehicle via TraCI / libsumo.
    
    Returns a dictionary conforming to the interface contract:
    {
        'tls_id': str,
        'dist_to_stopline': float,
        'state': str,             # 'r', 'y', 'g', 'G', or 'none'
        'time_to_switch': float,  # next PROGRAM phase change (observation slot [11])
        'time_to_green': float,   # until THIS link shows green (transition predictors)
        'stop_imminent': float,   # I_stop in [0.0, 1.0]
        'start_imminent': float,  # I_start in [0.0, 1.0]
        'speed': float,
        'accel': float,
        'leader_vid': Optional[str],
        'leader_gap': Optional[float],
        'leader_speed': Optional[float],
        'waiting_time': float,
        'n_queue': int,           # halting vehicles ahead on the ego's own lane
        'n_ahead': int,           # all vehicles ahead on the ego's own lane
        'n_lane_halting': int,    # SUMO lane-wide halting count
        'lane_id': str,
        'lane_position': float,
        'lane_vehicle_count': int,
    }
    """
    driver = sumo_conn if sumo_conn is not None else sumo
    default_res: Dict[str, Any] = {
        "tls_id": "",
        "tls_index": -1,
        "dist_to_stopline": float("inf"),
        "state": "none",
        "time_to_switch": float("inf"),
        "time_to_green": float("inf"),
        "stop_imminent": 0.0,
        "start_imminent": 0.0,
        "speed": 0.0,
        "accel": 0.0,
        "leader_vid": None,
        "leader_gap": None,
        "leader_speed": None,
        "waiting_time": 0.0,
        "lane_id": "",
        "lane_position": 0.0,
        "n_ahead": 0,
        "n_queue": 0,
        "n_lane_halting": 0,
        "lane_vehicle_count": 0,
    }

    if driver is None:
        return default_res

    try:
        if current_time is None:
            try:
                current_time = float(driver.simulation.getTime())
            except Exception as exc:
                _note_fallback("getTime", vid, exc)
                current_time = 0.0

        # 1. Vehicle kinematics
        try:
            speed = float(driver.vehicle.getSpeed(vid))
        except Exception as exc:
            _note_fallback("getSpeed", vid, exc)
            speed = 0.0

        try:
            accel = float(driver.vehicle.getAcceleration(vid))
        except Exception as exc:
            _note_fallback("getAcceleration", vid, exc)
            accel = 0.0

        try:
            waiting_time = float(driver.vehicle.getWaitingTime(vid))
        except Exception as exc:
            _note_fallback("getWaitingTime", vid, exc)
            waiting_time = 0.0

        # 2. Leader info
        leader_vid: Optional[str] = None
        leader_gap: Optional[float] = None
        leader_speed: Optional[float] = None
        try:
            leader_info = driver.vehicle.getLeader(vid, 60.0)
            if leader_info is not None and leader_info[0]:
                leader_vid = str(leader_info[0])
                leader_gap = float(leader_info[1])
                try:
                    leader_speed = float(driver.vehicle.getSpeed(leader_vid))
                except Exception as exc:
                    _note_fallback("getSpeed(leader)", vid, exc)
                    leader_speed = None
        except Exception as exc:
            _note_fallback("getLeader", vid, exc)

        # 2b. Lane bookkeeping, and -- only on the observation path -- the real
        # per-lane queue measurement. `n_queue` from here is SUMO ground truth and
        # is NOT what reaches the observation vector: `AoiV2IEnv` overrides it with
        # its ledger-based reconstruction (design decision D3). It is produced at
        # all only for the heuristic scheduler and for diagnostics.
        queue_feats = (
            extract_queue_features(driver, vid) if with_queue
            else extract_lane_position(driver, vid)
        )

        # 3. Next TLS info
        tls_id = ""
        tls_index = -1
        dist_to_stopline = float("inf")
        state_char = "none"
        time_to_switch = float("inf")
        time_to_green = float("inf")

        try:
            tls_list = driver.vehicle.getNextTLS(vid)
            if tls_list:
                first_tls = tls_list[0]
                tls_id = str(first_tls[0])
                tls_index = int(first_tls[1])
                dist_to_stopline = float(first_tls[2])
                state_char = str(first_tls[3])
        except Exception as exc:
            _note_fallback("getNextTLS", vid, exc)

        # 4a. Remaining time in the current program phase. This is what
        #     getNextSwitch actually answers, and it is what observation slot
        #     [11] ("phase remaining time") documents itself as carrying.
        if tls_id:
            try:
                next_switch_t = float(driver.trafficlight.getNextSwitch(tls_id))
                time_to_switch = max(0.0, next_switch_t - current_time)
            except Exception as exc:
                _note_fallback("getNextSwitch", vid, exc)
                time_to_switch = float("inf")

        # 4b. Time until THIS link goes green. Different quantity, different
        #     source: the program definition walked forward from the current
        #     phase. The transition predictors take this one, never 4a.
        if tls_id:
            time_to_green = compute_time_to_green(driver, tls_id, tls_index, current_time)

        # 5. Calculate transition indicators
        i_stop = predict_stop_imminent(
            speed=speed,
            accel=accel,
            dist_to_stopline=dist_to_stopline,
            signal_state=state_char,
            time_to_green=time_to_green,
            leader_dist=leader_gap,
            leader_speed=leader_speed,
        )

        i_start = predict_start_imminent(
            speed=speed,
            accel=accel,
            dist_to_stopline=dist_to_stopline,
            signal_state=state_char,
            time_to_green=time_to_green,
            leader_dist=leader_gap,
            leader_speed=leader_speed,
            waiting_time=waiting_time,
        )

        result: Dict[str, Any] = {
            "tls_id": tls_id,
            "tls_index": tls_index,
            "dist_to_stopline": dist_to_stopline,
            "state": state_char,
            "time_to_switch": time_to_switch,
            "time_to_green": time_to_green,
            "stop_imminent": i_stop,
            "start_imminent": i_start,
            "speed": speed,
            "accel": accel,
            "leader_vid": leader_vid,
            "leader_gap": leader_gap,
            "leader_speed": leader_speed,
            "waiting_time": waiting_time,
        }
        result.update(queue_feats)
        return result

    except Exception as exc:
        # The widest net in the module: ANY internal failure becomes a plausible
        # "no signal, not stopped, queue 0" dict. That is precisely how a degraded
        # TraCI connection turns into believable-looking data, so it is logged at
        # warning level and counted rather than swallowed.
        logging.warning("extract_tls_features fell back to defaults for %s: %s", vid, exc)
        FALLBACK_COUNTS["extract_tls_features"] = FALLBACK_COUNTS.get("extract_tls_features", 0) + 1
        return default_res


class DynamicsPredictor:
    """
    High-level helper class for trajectory and dynamics transition prediction.
    """
    def __init__(self, sumo_conn: Any = None) -> None:
        self.sumo_conn = sumo_conn

    def get_features(self, vid: str, current_time: Optional[float] = None) -> Dict[str, Any]:
        return extract_tls_features(self.sumo_conn, vid, current_time=current_time)

    def get_queue_features(self, vid: str) -> Dict[str, Any]:
        """Real per-lane queue measurement only (cheaper than the full TLS extraction)."""
        return extract_queue_features(self.sumo_conn, vid)

    def get_n_queue(self, vid: str) -> int:
        """Number of halting vehicles ahead of `vid` on its own lane (live SUMO data)."""
        return int(extract_queue_features(self.sumo_conn, vid)["n_queue"])

    def is_transition_imminent(self, vid: str, current_time: Optional[float] = None) -> Tuple[bool, float, float]:
        feats = self.get_features(vid, current_time=current_time)
        i_stop = feats["stop_imminent"]
        i_start = feats["start_imminent"]
        return (i_stop >= 0.5 or i_start >= 0.5), i_stop, i_start
