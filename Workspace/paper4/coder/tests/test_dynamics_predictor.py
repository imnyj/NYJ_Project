# tests/test_dynamics_predictor.py
# ============================================================================
# Unit & Integration Test Suite for Milestone 1:
# Signal-based Dynamics Prediction & Heuristic Baseline Scheduler (S2.5)
# ============================================================================
from __future__ import annotations

import os
import pytest

from src.dynamics_predictor import (
    predict_stop_imminent,
    predict_start_imminent,
    extract_tls_features,
    DynamicsPredictor,
)
from src.heuristic_scheduler import HeuristicScheduler
import src.aoi_env as env
import src.Communications as comm


# ----------------------------------------------------------------------------
# 1. Estimation Error & Extrapolation Math Tests
# ----------------------------------------------------------------------------
def test_extrapolate_and_estimation_error_stationary():
    pos = (100.0, 200.0)
    vel = (0.0, 0.0)
    # Stopped vehicle: true pos stays constant
    err = env.estimation_error(pos, pos, vel, age=10.0)
    assert pytest.approx(err, abs=1e-6) == 0.0


def test_extrapolate_and_estimation_error_constant_velocity():
    pos = (100.0, 200.0)
    vel = (15.0, -5.0)
    age = 3.0
    true_pos = (pos[0] + vel[0] * age, pos[1] + vel[1] * age)
    err = env.estimation_error(true_pos, pos, vel, age=age)
    assert pytest.approx(err, abs=1e-6) == 0.0


def test_extrapolate_and_estimation_error_accelerating():
    pos = (0.0, 0.0)
    vel = (10.0, 0.0)
    a = 2.0  # m/s^2
    age = 4.0
    # s = v0*t + 0.5*a*t^2 -> error should be exactly 0.5*a*t^2 = 0.5*2*16 = 16.0
    true_pos = (vel[0] * age + 0.5 * a * (age ** 2), 0.0)
    err = env.estimation_error(true_pos, pos, vel, age=age)
    expected_err = 0.5 * a * (age ** 2)
    assert pytest.approx(err, abs=1e-4) == expected_err


# ----------------------------------------------------------------------------
# 2. Imminent Stop Indicator (I_stop) Unit Tests
# ----------------------------------------------------------------------------
def test_stop_imminent_approaching_red_light():
    # Moving at 12 m/s, 25m from stopline, signal is red, 10s left
    i_stop = predict_stop_imminent(
        speed=12.0,
        accel=0.0,
        dist_to_stopline=25.0,
        signal_state="r",
        time_to_switch=10.0,
    )
    assert i_stop == 1.0


def test_stop_imminent_approaching_yellow_light():
    # Moving at 10 m/s, 20m from stopline, signal is yellow
    i_stop = predict_stop_imminent(
        speed=10.0,
        accel=0.0,
        dist_to_stopline=20.0,
        signal_state="y",
        time_to_switch=3.0,
    )
    assert i_stop == 1.0


def test_stop_imminent_hard_braking():
    # Moving at 10 m/s with strong deceleration a = -2.5 m/s^2
    i_stop = predict_stop_imminent(
        speed=10.0,
        accel=-2.5,
        dist_to_stopline=200.0,
        signal_state="g",
        time_to_switch=20.0,
    )
    assert i_stop == 1.0


def test_stop_imminent_stopped_leader_ahead():
    # Moving at 10 m/s, leader stopped (0.0 m/s) at 15m ahead
    i_stop = predict_stop_imminent(
        speed=10.0,
        accel=0.0,
        dist_to_stopline=500.0,
        signal_state="g",
        time_to_switch=50.0,
        leader_dist=15.0,
        leader_speed=0.0,
    )
    assert i_stop == 1.0


def test_not_stop_imminent_green_cruising():
    # Cruising at 12 m/s through green light
    i_stop = predict_stop_imminent(
        speed=12.0,
        accel=0.0,
        dist_to_stopline=30.0,
        signal_state="g",
        time_to_switch=15.0,
    )
    assert i_stop == 0.0


def test_not_stop_imminent_already_stationary():
    # Stationary vehicle (0.0 m/s) - stop transition has already concluded
    i_stop = predict_stop_imminent(
        speed=0.0,
        accel=0.0,
        dist_to_stopline=5.0,
        signal_state="r",
        time_to_switch=15.0,
    )
    assert i_stop == 0.0


# ----------------------------------------------------------------------------
# 3. Imminent Start Indicator (I_start) Unit Tests
# ----------------------------------------------------------------------------
def test_start_imminent_green_light_turned():
    # Stopped at stopline (5m) and signal is green ('G')
    i_start = predict_start_imminent(
        speed=0.0,
        accel=0.0,
        dist_to_stopline=5.0,
        signal_state="G",
        time_to_switch=20.0,
        waiting_time=10.0,
    )
    assert i_start == 1.0


def test_start_imminent_red_expiring_soon():
    # Stopped at red light (dist=10m) with 1.5s remaining on red phase
    i_start = predict_start_imminent(
        speed=0.0,
        accel=0.0,
        dist_to_stopline=10.0,
        signal_state="r",
        time_to_switch=1.5,
        waiting_time=15.0,
    )
    assert i_start == 1.0


def test_start_imminent_leader_moving_off():
    # Stopped vehicle, leader vehicle ahead starts moving off (speed=3.0 m/s, gap=10m)
    i_start = predict_start_imminent(
        speed=0.0,
        accel=0.0,
        dist_to_stopline=300.0,
        signal_state="none",
        time_to_switch=float("inf"),
        leader_dist=10.0,
        leader_speed=3.0,
    )
    assert i_start == 1.0


def test_start_imminent_takeoff_acceleration():
    # Initial takeoff acceleration from standstill (accel = 1.2 m/s^2, speed = 0.5 m/s)
    i_start = predict_start_imminent(
        speed=0.5,
        accel=1.2,
        dist_to_stopline=100.0,
        signal_state="none",
        time_to_switch=float("inf"),
    )
    assert i_start == 1.0


def test_not_start_imminent_long_red():
    # Stopped at red light with 25s remaining
    i_start = predict_start_imminent(
        speed=0.0,
        accel=0.0,
        dist_to_stopline=10.0,
        signal_state="r",
        time_to_switch=25.0,
        waiting_time=5.0,
    )
    assert i_start == 0.0


def test_not_start_imminent_already_cruising():
    # Cruising at 15 m/s
    i_start = predict_start_imminent(
        speed=15.0,
        accel=0.2,
        dist_to_stopline=100.0,
        signal_state="g",
        time_to_switch=10.0,
    )
    assert i_start == 0.0


# ----------------------------------------------------------------------------
# 4. Feature Extraction & DynamicsPredictor Helper Tests
# ----------------------------------------------------------------------------
def test_extract_tls_features_fallback_none_driver():
    feats = extract_tls_features(None, "v_nonexistent")
    assert isinstance(feats, dict)
    assert "tls_id" in feats
    assert "dist_to_stopline" in feats
    assert "state" in feats
    assert "time_to_switch" in feats
    assert "stop_imminent" in feats
    assert "start_imminent" in feats
    assert feats["stop_imminent"] == 0.0
    assert feats["start_imminent"] == 0.0


def test_dynamics_predictor_class():
    predictor = DynamicsPredictor(sumo_conn=None)
    feats = predictor.get_features("v1")
    assert feats["state"] == "none"
    is_imminent, i_stop, i_start = predictor.is_transition_imminent("v1")
    assert not is_imminent
    assert i_stop == 0.0 and i_start == 0.0


# ----------------------------------------------------------------------------
# 5. HeuristicScheduler Rule Tests
# ----------------------------------------------------------------------------
def test_heuristic_scheduler_imminent_stop_grant():
    scheduler = HeuristicScheduler()
    state = {
        "vid": "veh_01",
        "speed": 12.0,
        "accel": 0.0,
        "dist_to_rsu": 250.0,
        "tls_features": {
            "state": "r",
            "dist_to_stopline": 20.0,
            "time_to_switch": 10.0,
            "stop_imminent": 1.0,
            "start_imminent": 0.0,
        },
    }
    interval, ch, power = scheduler.decide_grant("veh_01", state)
    assert interval == scheduler.delta_min  # Forced immediate update
    assert power >= 23.0    # High power for reliability
    assert 0 <= ch < comm.NUM_SUBCHANNELS


def test_heuristic_scheduler_imminent_start_grant():
    scheduler = HeuristicScheduler()
    state = {
        "vid": "veh_02",
        "speed": 0.0,
        "accel": 0.0,
        "dist_to_rsu": 300.0,
        "tls_features": {
            "state": "G",
            "dist_to_stopline": 5.0,
            "time_to_switch": 20.0,
            "stop_imminent": 0.0,
            "start_imminent": 1.0,
        },
    }
    interval, ch, power = scheduler.decide_grant("veh_02", state)
    assert interval == scheduler.delta_min
    assert power >= 23.0
    assert 0 <= ch < comm.NUM_SUBCHANNELS


def test_heuristic_scheduler_long_red_backoff():
    scheduler = HeuristicScheduler(delta_max=10.0)
    # Stopped at red with 8.0s remaining -> backoff = min(10.0, max(1.0, 8.0 - 1.0)) = 7.0s
    state = {
        "vid": "veh_03",
        "speed": 0.0,
        "accel": 0.0,
        "dist_to_rsu": 200.0,
        "tls_features": {
            "state": "r",
            "dist_to_stopline": 15.0,
            "time_to_switch": 8.0,
            "stop_imminent": 0.0,
            "start_imminent": 0.0,
        },
    }
    interval, ch, power = scheduler.decide_grant("veh_03", state)
    assert pytest.approx(interval, abs=1e-4) == 7.0
    assert power == scheduler.p_low  # Low power to minimize interference


def test_heuristic_scheduler_long_red_backoff_max_clamp():
    scheduler = HeuristicScheduler(delta_max=10.0)
    # Stopped at red with 30.0s remaining -> clamped to delta_max = 10.0s
    state = {
        "vid": "veh_04",
        "speed": 0.0,
        "accel": 0.0,
        "dist_to_rsu": 200.0,
        "tls_features": {
            "state": "r",
            "dist_to_stopline": 15.0,
            "time_to_switch": 30.0,
            "stop_imminent": 0.0,
            "start_imminent": 0.0,
        },
    }
    interval, ch, power = scheduler.decide_grant("veh_04", state)
    assert interval == 10.0
    assert power == scheduler.p_low


def test_heuristic_scheduler_cruising_dynamic_interval():
    scheduler = HeuristicScheduler(delta_cruise_steady=3.5, delta_cruise_accel=1.5)
    # Steady cruise
    state_steady = {
        "vid": "veh_05",
        "speed": 12.0,
        "accel": 0.1,
        "dist_to_rsu": 200.0,
        "tls_features": {"state": "g", "time_to_switch": 20.0, "stop_imminent": 0.0, "start_imminent": 0.0},
    }
    interval, ch, power = scheduler.decide_grant("veh_05", state_steady)
    assert interval == 3.5

    # Accelerating
    state_accel = {
        "vid": "veh_06",
        "speed": 10.0,
        "accel": 0.8,
        "dist_to_rsu": 200.0,
        "tls_features": {"state": "g", "time_to_switch": 20.0, "stop_imminent": 0.0, "start_imminent": 0.0},
    }
    interval_acc, ch_acc, power_acc = scheduler.decide_grant("veh_06", state_accel)
    assert interval_acc == 1.5


def test_heuristic_scheduler_channel_load_balancing():
    scheduler = HeuristicScheduler(num_subchannels=4)
    state = {
        "vid": "veh_01",
        "speed": 12.0,
        "accel": 0.0,
        "dist_to_rsu": 200.0,
        "tls_features": {"state": "g", "time_to_switch": 20.0, "stop_imminent": 0.0, "start_imminent": 0.0},
    }
    channels_allocated = [scheduler.decide_grant(f"v_{i}", state)[1] for i in range(12)]
    # Each of the 4 subchannels should have been allocated exactly 3 times
    for ch in range(4):
        assert channels_allocated.count(ch) == 3


# ----------------------------------------------------------------------------
# 6. Live SUMO Integration Test
# ----------------------------------------------------------------------------
def test_sumo_simulation_with_heuristic_scheduler():
    """Drive a short live SUMO run through the heuristic scheduler.

    This test overrides module-level geometry/demand globals in make_sumo_set and
    NetSim, which are shared process-wide and also drive the cached SUMO XML in
    src/sumo/. Without restoring them, the overrides leak into every later test in
    the session and leave generated.net.xml built for a different RSU range than the
    project's, so the next training run has to regenerate. Everything mutated here is
    therefore saved up front and restored in a finally block.
    """
    os.environ["PATH"] = f"/home/imnyj/venv/bin:{os.environ.get('PATH', '')}"
    os.environ.setdefault("SUMO_HOME", "/home/imnyj/venv/lib/python3.12/site-packages/sumo")

    import src.NetSim as net
    import src.sumo.make_sumo_set as ss

    ss_names = ("RSU_RANGE", "AV_SPEED", "DENSITY", "MAX_STEPS", "SPEED", "P_GEN")
    net_names = ("MAX_EPISODE", "b_step_log", "b_reroute")
    saved_ss = {n: getattr(ss, n) for n in ss_names}
    saved_net = {n: getattr(net, n) for n in net_names}
    saved_warmup = getattr(env, "WARMUP_S", None)

    try:
        ss.RSU_RANGE = 800.0
        ss.AV_SPEED = 40.0
        ss.DENSITY = 25.0
        ss.MAX_STEPS = 60.0
        ss.SPEED = ss.AV_SPEED / 3.6
        ss.P_GEN = (ss.DENSITY * ss.SPEED) / 3600.0
        net.MAX_EPISODE = 1
        net.b_step_log = False
        net.b_reroute = False

        scheduler = HeuristicScheduler()
        env.WARMUP_S = 15.0
        env.set_scheduler(scheduler)
        env.reset_env()

        sim = net.SumoNetSim(
            VehicleClass=env.VehicleNode,
            RSUClass=env.RSUNode,
            start_message_fn=env.start_message,
        )
        sim.run()

        summary = env.METRICS.summary()
        assert summary["registrations_E1"] > 0
        assert summary["tx_attempts"] > 0
        assert summary["tx_attempts"] == summary["tx_success"] + summary["tx_fail"]
        assert summary["tx_success_rate"] >= 0.0
        assert summary["mean_interval_err_integral"] >= 0.0
    finally:
        for name, value in saved_ss.items():
            setattr(ss, name, value)
        for name, value in saved_net.items():
            setattr(net, name, value)
        if saved_warmup is not None:
            env.WARMUP_S = saved_warmup
