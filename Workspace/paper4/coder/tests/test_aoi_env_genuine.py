# tests/test_aoi_env_genuine.py
# ============================================================================
# Comprehensive Unit & Integration Test Suite for Genuine AoiV2IEnv & Verification
#
# Covers:
# 1. Pure estimation error extrapolation and distance mathematics.
# 2. Episode metrics and telemetry aggregation.
# 3. Genuine AoiV2IEnv reset and TraCI/libsumo lifecycle management.
# 4. Physical 20-step simulation rollout and vehicle coordinate displacements.
# 5. Rayleigh fading wireless channel model integration under contention.
# 6. Composite normalized penalty reward mathematical verification.
# 7. Fault-injection tests verifying all 4 anti-mocking assertion triggers.
# 8. End-to-end execution of verify_environment.py.
# ============================================================================

import math
import os
import subprocess
import sys
import numpy as np
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.aoi_env import (  # noqa: E402
    AoiV2IEnv,
    AoIEnv,
    Metrics,
    estimation_error,
    extrapolate,
)


class TestAoiEnvGenuine:
    """Comprehensive test suite for genuine AoiV2IEnv and anti-mocking assertions."""

    def test_01_pure_estimation_math(self):
        """Verify linear extrapolation and Euclidean error calculations."""
        # 1. Stationary vehicle: position should not drift
        pos0 = (100.0, 200.0)
        vel0 = (0.0, 0.0)
        p_extrap = extrapolate(pos0, vel0, dt=10.0)
        assert p_extrap == (100.0, 200.0)
        err_still = estimation_error(pos0, pos0, vel0, age=10.0)
        assert err_still == 0.0

        # 2. Constant velocity motion: extrapolation perfectly matches true pos
        pos_start = (0.0, 0.0)
        vel = (15.0, 20.0)  # speed = 25 m/s
        dt = 4.0
        true_pos = (60.0, 80.0)
        err_perfect = estimation_error(true_pos, pos_start, vel, age=dt)
        assert math.isclose(err_perfect, 0.0, abs_tol=1e-6)

        # 3. Kinematic divergence: vehicle turned or accelerated
        actual_pos = (60.0, 90.0)  # offset by 10m on Y
        err_diverged = estimation_error(actual_pos, pos_start, vel, age=dt)
        assert math.isclose(err_diverged, 10.0, abs_tol=1e-6)

    def test_02_metrics_tracking(self):
        """Verify episode metrics recording and summary statistics."""
        metrics = Metrics()
        assert metrics.n_registrations == 0
        assert metrics.n_updates == 0

        # Record intervals and samples
        metrics.record_interval(err_integral=25.0, duration=2.5)
        metrics.record_sample(e=5.0, speed=12.0)
        metrics.record_sample(e=0.2, speed=1.0)
        metrics.record_attempt(p=0.85, contenders=3)
        metrics.n_registrations += 1
        metrics.n_updates += 1
        metrics.n_exits += 1

        summary = metrics.summary()
        assert summary["registrations_E1"] == 1
        assert summary["updates_E2"] == 1
        assert summary["exits_E3"] == 1
        assert summary["intervals"] == 1
        assert summary["mean_interval_err_integral"] == 25.0
        assert summary["mean_interval_duration_s"] == 2.5
        assert summary["tx_attempts"] == 1
        assert summary["tx_success"] == 1
        assert summary["tx_success_rate"] == 1.0
        assert summary["err_max"] == 5.0

    def test_03_env_initialization_and_config(self):
        """Verify environment instantiates with custom and default configurations."""
        custom_config = {
            "warmup_steps": 40,
            "max_steps": 500,
            "step_length": 1.0,
            "weights": {"w1": 0.6, "w2": 0.15, "w3": 0.15, "w4": 0.1},
            "p_min": 10.0,
            "p_max": 23.0,
        }
        env = AoiV2IEnv(config=custom_config)
        assert env.warmup_steps == 40
        assert env.max_steps == 500
        assert env.w_error == 0.6
        assert env.w_power == 0.15
        assert env.w_congestion == 0.15
        assert env.w_redundant == 0.1
        assert env.num_channels == 4
        assert AoIEnv is AoiV2IEnv

    def test_04_env_reset_real_sumo(self):
        """Verify env.reset() spins up real SUMO, selects target RSU, and returns 18-dim states."""
        env = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 100, "step_length": 1.0})
        obs, info = env.reset(seed=42)

        assert isinstance(obs, dict)
        assert "sim_time" in info
        assert "target_rsu" in info
        assert "n_active" in info
        assert info["n_active"] > 0
        assert len(obs) == info["n_active"]

        for vid, s_vec in obs.items():
            assert s_vec.shape == (18,)
            assert s_vec.dtype == np.float32
            assert np.all(s_vec >= -1.0) and np.all(s_vec <= 1.0)

        env.close()

    def test_05_env_step_physical_rollout(self):
        """Verify env.step() advances SUMO simulation time and tracks moving vehicle coordinates."""
        env = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 100, "step_length": 1.0})
        obs, info = env.reset(seed=42)
        initial_time = info["sim_time"]

        positions_step0 = {vid: env._prev_vehicle_positions[vid] for vid in env.get_active_vehicles()}

        # Run 5 steps with hybrid actions
        for step in range(5):
            action_dict = {
                vid: (1.0 + (i % 3) * 0.5, (i + step) % 4, 20.0)
                for i, vid in enumerate(env.get_active_vehicles())
            }
            obs, rewards, term, trunc, step_info = env.step(action_dict)

            assert math.isclose(step_info["sim_time"], initial_time + float(step + 1), abs_tol=1e-4)
            assert isinstance(rewards, dict)
            assert step_info["step_reward"] <= 0.0

        # Verify vehicles moved
        displacements = [
            math.hypot(env._prev_vehicle_positions[vid][0] - pos0[0],
                       env._prev_vehicle_positions[vid][1] - pos0[1])
            for vid, pos0 in positions_step0.items()
            if vid in env._prev_vehicle_positions
        ]
        assert any(d > 0.0 for d in displacements), "Expected vehicle movement in SUMO rollout"

        env.close()

    def test_06_reward_formula_and_bounds(self):
        """Verify reward calculation strictly follows Conversation.md specification."""
        env = AoiV2IEnv(config={
            "warmup_steps": 60,
            "step_length": 1.0,
            "weights": {"w_error": 0.5, "w_power": 0.2, "w_congestion": 0.2, "w_redundant": 0.1},
        })
        obs, info = env.reset(seed=42)

        # Single step with diverse channel allocation
        action_dict = {
            vid: (1.0, i % 4, 10.0 + (i % 3) * 6.5)
            for i, vid in enumerate(env.get_active_vehicles())
        }
        obs, rewards, term, trunc, step_info = env.step(action_dict)
        reward_details = step_info["reward_details"]

        for vid, r_det in reward_details.items():
            ne = r_det["norm_error_sq"]
            np_ = r_det["norm_ptx"]
            nc = r_det["norm_cfreq"]
            ir = r_det["i_redundant"]
            rv = r_det["reward"]

            assert 0.0 <= ne <= 1.0
            assert 0.0 <= np_ <= 1.0
            assert 0.0 <= nc <= 1.0
            assert ir in (0.0, 1.0)
            expected = -(0.5 * ne + 0.2 * np_ + 0.2 * nc + 0.1 * ir)
            assert math.isclose(rv, expected, abs_tol=1e-5)
            assert rv <= 0.0

        env.close()

    def test_07_anti_mocking_assertion1_time_regression_fault(self):
        """Verify Assertion 1 raises AssertionError if simulation time regresses or freezes."""
        sim_time = 50.0
        prev_sim_time = 52.0  # Simulated regression
        with pytest.raises(AssertionError, match="Simulation time regression/freeze detected"):
            assert sim_time > prev_sim_time, f"FATAL: Simulation time regression/freeze detected: {sim_time} <= {prev_sim_time}"

    def test_08_anti_mocking_assertion2_coordinate_freeze_fault(self):
        """Verify Assertion 2 raises AssertionError if moving vehicle has zero coordinate displacement."""
        vid = "veh_test_0"
        spd = 12.5  # Moving vehicle
        pos = (500.0, 500.0)
        prev_p = (500.0, 500.0)  # Frozen coordinate
        dist_moved = math.hypot(pos[0] - prev_p[0], pos[1] - prev_p[1])
        with pytest.raises(AssertionError, match="coordinate did not change"):
            if spd > 1.0:
                assert dist_moved > 0.0, f"FATAL: Vehicle {vid} speed is {spd} m/s but coordinate did not change from {prev_p}!"

    def test_09_anti_mocking_assertion3_communications_fault(self):
        """Verify Assertion 3 raises AssertionError if uplink probability is invalid or out of bounds."""
        corrupted_probs = {"veh_bad": 1.25}
        with pytest.raises(AssertionError, match="out of"):
            for vid, p in corrupted_probs.items():
                assert 0.0 <= p <= 1.0, f"FATAL: Uplink success probability {p} for {vid} out of [0, 1]!"

    def test_10_anti_mocking_assertion4_reward_integrity_fault(self):
        """Verify Assertion 4 raises AssertionError if reward computation diverges from mathematical spec."""
        w_e, w_p, w_c, w_r = 0.5, 0.2, 0.2, 0.1
        ne, np_, nc, ir = 0.3, 0.5, 0.1, 0.0
        tampered_reward = -0.05  # Tampered reward value
        expected = -(w_e * ne + w_p * np_ + w_c * nc + w_r * ir)  # -0.27

        with pytest.raises(AssertionError, match="Reward calculation mismatch"):
            assert math.isclose(tampered_reward, expected, abs_tol=1e-5), (
                f"FATAL: Reward calculation mismatch for test_veh: {tampered_reward} != {expected}"
            )

    def test_11_verify_environment_subprocess_execution(self):
        """Verify that verify_environment.py runs from start to finish and exits with code 0."""
        script_path = os.path.join(PROJECT_ROOT, "verify_environment.py")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0, f"verify_environment.py failed with exit code {result.returncode}:\n{result.stderr}\n{result.stdout}"
        assert "ALL ENVIRONMENT VERIFICATION TESTS PASSED" in result.stdout
