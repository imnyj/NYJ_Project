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
    time_to_switch: float = float("inf"),
    leader_dist: Optional[float] = None,
    leader_speed: Optional[float] = None,
) -> float:
    """
    Computes the imminent-stop indicator I_stop in [0.0, 1.0].
    
    A vehicle is considered about to stop if:
    1. Active strong deceleration / braking: vehicle speed > 0.5 m/s and
       braking time to stop is within 3.0 seconds (or speed + accel * 2.0 <= 0.5).
    2. Approaching red ('r') or yellow ('y') traffic signal within braking
       distance and signal will remain red/yellow upon arrival (time_to_switch > 1.5s).
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
            # If the light is turning green very soon (<= 1.0s), vehicle might not need to stop
            if time_to_switch > 1.0:
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
    time_to_switch: float = float("inf"),
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

        # Case B: Signal is currently red but will turn green imminently (<= 2.0s)
        if sig == "r" and time_to_switch <= 2.0 and dist_to_stopline <= 35.0:
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
def extract_tls_features(
    sumo_conn: Any,
    vid: str,
    current_time: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Extracts traffic signal and kinematics features for a vehicle via TraCI / libsumo.
    
    Returns a dictionary conforming to the interface contract:
    {
        'tls_id': str,
        'dist_to_stopline': float,
        'state': str,             # 'r', 'y', 'g', 'G', or 'none'
        'time_to_switch': float,
        'stop_imminent': float,   # I_stop in [0.0, 1.0]
        'start_imminent': float,  # I_start in [0.0, 1.0]
        'speed': float,
        'accel': float,
        'leader_vid': Optional[str],
        'leader_gap': Optional[float],
        'leader_speed': Optional[float],
        'waiting_time': float,
    }
    """
    driver = sumo_conn if sumo_conn is not None else sumo
    default_res: Dict[str, Any] = {
        "tls_id": "",
        "tls_index": -1,
        "dist_to_stopline": float("inf"),
        "state": "none",
        "time_to_switch": float("inf"),
        "stop_imminent": 0.0,
        "start_imminent": 0.0,
        "speed": 0.0,
        "accel": 0.0,
        "leader_vid": None,
        "leader_gap": None,
        "leader_speed": None,
        "waiting_time": 0.0,
    }

    if driver is None:
        return default_res

    try:
        if current_time is None:
            try:
                current_time = float(driver.simulation.getTime())
            except Exception:
                current_time = 0.0

        # 1. Vehicle kinematics
        try:
            speed = float(driver.vehicle.getSpeed(vid))
        except Exception:
            speed = 0.0

        try:
            accel = float(driver.vehicle.getAcceleration(vid))
        except Exception:
            accel = 0.0

        try:
            waiting_time = float(driver.vehicle.getWaitingTime(vid))
        except Exception:
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
                except Exception:
                    leader_speed = None
        except Exception:
            pass

        # 3. Next TLS info
        tls_id = ""
        tls_index = -1
        dist_to_stopline = float("inf")
        state_char = "none"
        time_to_switch = float("inf")

        try:
            tls_list = driver.vehicle.getNextTLS(vid)
            if tls_list:
                first_tls = tls_list[0]
                tls_id = str(first_tls[0])
                tls_index = int(first_tls[1])
                dist_to_stopline = float(first_tls[2])
                state_char = str(first_tls[3])
        except Exception:
            pass

        # 4. Traffic light switch time
        if tls_id:
            try:
                next_switch_t = float(driver.trafficlight.getNextSwitch(tls_id))
                time_to_switch = max(0.0, next_switch_t - current_time)
            except Exception:
                time_to_switch = float("inf")

        # 5. Calculate transition indicators
        i_stop = predict_stop_imminent(
            speed=speed,
            accel=accel,
            dist_to_stopline=dist_to_stopline,
            signal_state=state_char,
            time_to_switch=time_to_switch,
            leader_dist=leader_gap,
            leader_speed=leader_speed,
        )

        i_start = predict_start_imminent(
            speed=speed,
            accel=accel,
            dist_to_stopline=dist_to_stopline,
            signal_state=state_char,
            time_to_switch=time_to_switch,
            leader_dist=leader_gap,
            leader_speed=leader_speed,
            waiting_time=waiting_time,
        )

        return {
            "tls_id": tls_id,
            "tls_index": tls_index,
            "dist_to_stopline": dist_to_stopline,
            "state": state_char,
            "time_to_switch": time_to_switch,
            "stop_imminent": i_stop,
            "start_imminent": i_start,
            "speed": speed,
            "accel": accel,
            "leader_vid": leader_vid,
            "leader_gap": leader_gap,
            "leader_speed": leader_speed,
            "waiting_time": waiting_time,
        }

    except Exception:
        return default_res


class DynamicsPredictor:
    """
    High-level helper class for trajectory and dynamics transition prediction.
    """
    def __init__(self, sumo_conn: Any = None) -> None:
        self.sumo_conn = sumo_conn

    def get_features(self, vid: str, current_time: Optional[float] = None) -> Dict[str, Any]:
        return extract_tls_features(self.sumo_conn, vid, current_time=current_time)

    def is_transition_imminent(self, vid: str, current_time: Optional[float] = None) -> Tuple[bool, float, float]:
        feats = self.get_features(vid, current_time=current_time)
        i_stop = feats["stop_imminent"]
        i_start = feats["start_imminent"]
        return (i_stop >= 0.5 or i_start >= 0.5), i_stop, i_start
