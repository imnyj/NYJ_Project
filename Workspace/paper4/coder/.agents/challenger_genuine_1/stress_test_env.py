#!/usr/bin/env python3
"""
stress_test_env.py
=============================================================================
Adversarial Stress Test Harness for Genuine SUMO V2I AoI Environment.

Executes 5 comprehensive adversarial test suites:
1. Boundary & Extreme Hybrid Action Space Stress Test (Sigmoid/Logit/Bounds).
2. Communications Layer Rayleigh Fading, Massive Contention & Near-Far Effect.
3. Live Fault Injection & Anti-Mocking Assertion Bypass Verification.
4. Multi-Cycle Environment Reset & TraCI/SUMO Zombie Process Audit.
5. High-Contention 50-Step Full Rollout with Observation & Reward Invariants.

Author: challenger_genuine_1 (Empirical Challenger)
=============================================================================
"""

import math
import os
import subprocess
import sys
import time
import traceback
from typing import Any, Dict, List, Tuple
import numpy as np
import torch

# Ensure PATH has virtualenv
if "/home/imnyj/venv/bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = "/home/imnyj/venv/bin:" + os.environ.get("PATH", "")

# Add project root to sys.path
PROJECT_ROOT = "/home/imnyj/Workspace/paper4/coder"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import src.Communications as comm
from src.aoi_env import AoiV2IEnv
from src.rl_interface import ActionDecoder, StateVectorizer

# Attempt libsumo first, fallback to traci
try:
    import libsumo as sumo
except ImportError:
    try:
        import traci as sumo
    except ImportError:
        sumo = None


class AdversarialTestRunner:
    def __init__(self) -> None:
        self.results: Dict[str, Dict[str, Any]] = {}

    def log_header(self, title: str) -> None:
        print("\n" + "=" * 78)
        print(f"  >>> {title}")
        print("=" * 78)

    def record_result(self, suite_name: str, passed: bool, details: str) -> None:
        self.results[suite_name] = {"passed": passed, "details": details}
        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_str} {suite_name}: {details}")

    # =========================================================================
    # SUITE 1: Boundary & Extreme Action Space Stress Testing
    # =========================================================================
    def run_suite_1_action_space(self) -> bool:
        self.log_header("SUITE 1: Boundary & Extreme Action Space Stress Testing")
        passed = True
        suite_details = []

        decoder = ActionDecoder(num_channels=4, delta_min=0.5, delta_max=10.0, p_min=20.0, p_max=30.0)

        # 1.1 Test raw extreme actions
        extreme_inputs = [
            ("Negative Infinity", [-1e9, 0, -1e9]),
            ("Positive Infinity", [1e9, 3, 1e9]),
            ("Negative Out-of-Bounds Channel", [0.0, -10, 0.0]),
            ("Large Out-of-Bounds Channel", [0.0, 999, 0.0]),
            ("All Zeros", [0.0, 0.0, 0.0]),
            ("Float Channel Rounding", [0.0, 2.6, 0.0]),
            ("Extreme Floats", [-50.0, 1.4, 50.0]),
        ]

        for name, raw_act in extreme_inputs:
            delta, ch, p = decoder.decode_action(raw_act)
            in_range = (0.5 <= delta <= 10.0) and (ch in [0, 1, 2, 3]) and (20.0 <= p <= 30.0)
            if not in_range:
                passed = False
                suite_details.append(f"Failed on {name}: got ({delta}, {ch}, {p})")
            else:
                suite_details.append(f"{name} -> delta={delta:.2f}s, ch={ch}, p={p:.2f}dBm (OK)")

        # 1.2 Test exact boundary round-trip encoding/decoding
        boundary_cases = [
            (0.5, 0, 20.0),
            (10.0, 3, 30.0),
            (0.5, 3, 30.0),
            (10.0, 0, 20.0),
            (5.25, 2, 25.0),
        ]
        for b_delta, b_ch, b_p in boundary_cases:
            enc = decoder.encode_action(b_delta, b_ch, b_p)
            dec_delta, dec_ch, dec_p = decoder.decode_action(enc)
            d_err = abs(dec_delta - b_delta)
            p_err = abs(dec_p - b_p)
            ch_match = (dec_ch == b_ch)
            if d_err > 1e-4 or p_err > 1e-4 or not ch_match:
                passed = False
                suite_details.append(f"Roundtrip failed for ({b_delta}, {b_ch}, {b_p}): got ({dec_delta}, {dec_ch}, {dec_p})")
            else:
                suite_details.append(f"Roundtrip ({b_delta}, {b_ch}, {b_p}) -> encoded {enc} -> decoded ({dec_delta:.4f}, {dec_ch}, {dec_p:.4f}) (OK)")

        # 1.3 Test input format polymorphism (Tensor, Dict, List, Tuple, np.ndarray)
        formats = [
            ("Dict raw", {"delta_raw": 0.0, "ch": 1, "tx_power_dbm": 0.0}),
            ("Dict decoded", {"delta": 5.0, "channel_idx": 2, "power": 25.0}),
            ("PyTorch Tensor", torch.tensor([0.5, 2.0, -0.5])),
            ("NumPy Array", np.array([-1.0, 1.0, 1.0], dtype=np.float32)),
            ("Tuple", (1.0, 3, 2.0)),
        ]
        for fname, act in formats:
            try:
                d, c, p = decoder.decode_action(act)
                assert 0.5 <= d <= 10.0 and c in [0, 1, 2, 3] and 20.0 <= p <= 30.0
                suite_details.append(f"Format {fname} handled correctly -> ({d:.2f}, {c}, {p:.2f})")
            except Exception as e:
                passed = False
                suite_details.append(f"Format {fname} raised exception: {e}")

        # 1.4 Test environment stepping with extreme action dictionary
        env = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
        obs, info = env.reset(seed=101)
        vids = env.get_active_vehicles()

        # Step with boundary min action
        act_min = {vid: (-100.0, 0, -100.0) for vid in vids}
        obs, rew, term, trunc, sinfo = env.step(act_min)
        assert len(obs) > 0, "No observations after min step!"

        # Step with boundary max action
        act_max = {vid: (100.0, 3, 100.0) for vid in vids}
        obs, rew, term, trunc, sinfo = env.step(act_max)
        assert len(obs) > 0, "No observations after max step!"
        env.close()

        for d in suite_details[:6]:
            print(f"    - {d}")
        print(f"    - ... ({len(suite_details)} sub-verifications completed)")

        self.record_result("Suite 1 (Action Space & Boundaries)", passed, f"{len(suite_details)} tests verified")
        return passed

    # =========================================================================
    # SUITE 2: Rayleigh Fading Channel & Massive Contention Stress Testing
    # =========================================================================
    def run_suite_2_communications(self) -> bool:
        self.log_header("SUITE 2: Rayleigh Fading Channel & Massive Contention Stress Testing")
        passed = True
        details = []

        # 2.1 Solo transmission across distances and powers
        distances = [1.0, 10.0, 50.0, 100.0, 200.0, 500.0, 800.0, 1500.0, 5000.0]
        powers = [20.0, 25.0, 30.0]

        for p in powers:
            prev_prob = 1.01
            for d in distances:
                prob = comm.judge_uplink([("solo", p, d)], num_subchannels=4)["solo"]
                assert 0.0 <= prob <= 1.0, f"Solo prob out of bounds: {prob}"
                assert not math.isnan(prob) and not math.isinf(prob), f"Prob NaN/Inf: {prob}"
                if prob > prev_prob:
                    passed = False
                    details.append(f"Non-monotonic distance attenuation at d={d}, p={p}: {prob} > {prev_prob}")
                prev_prob = prob
            details.append(f"Power {p}dBm distance sweep monotonically attenuated: 1m -> {comm.judge_uplink([('s', p, 1.0)])['s']:.4f} down to 5000m -> {comm.judge_uplink([('s', p, 5000.0)])['s']:.6e}")

        # 2.2 Massive multi-vehicle contention on the SAME subchannel
        contender_counts = [1, 2, 4, 8, 16, 32, 64, 128, 256]
        prev_mean_p = 1.01
        for n_cont in contender_counts:
            group = [(f"veh_{i}", 25.0, 200.0 + (i % 10) * 10.0) for i in range(n_cont)]
            res = comm.judge_uplink(group, num_subchannels=4)
            mean_p = sum(res.values()) / len(res)
            for vid, prob in res.items():
                assert 0.0 <= prob <= 1.0, f"Probability out of range [0, 1]: {prob}"
                assert not math.isnan(prob) and not math.isinf(prob), f"Probability NaN: {prob}"

            if mean_p > prev_mean_p:
                passed = False
                details.append(f"Contention failure: N={n_cont} mean prob {mean_p:.6f} > N_prev mean prob {prev_mean_p:.6f}")
            prev_mean_p = mean_p
            details.append(f"Contention N={n_cont:3d}: Mean Success Probability = {mean_p:.6f}")

        # 2.3 Near-Far Capture Effect Verification
        # 1 strong close vehicle (30 dBm, 20m) vs 10 far weak vehicles (20 dBm, 600m)
        mixed_group = [("strong_close", 30.0, 20.0)] + [(f"weak_far_{i}", 20.0, 600.0) for i in range(10)]
        mixed_res = comm.judge_uplink(mixed_group, num_subchannels=4)
        p_strong = mixed_res["strong_close"]
        p_weak_avg = sum(mixed_res[f"weak_far_{i}"] for i in range(10)) / 10.0
        details.append(f"Near-Far Capture Effect: Strong/Close P_succ={p_strong:.4f} vs Weak/Far P_succ={p_weak_avg:.8f}")
        if p_strong <= p_weak_avg:
            passed = False
            details.append("Near-Far Capture effect failed: strong transmitter did not dominate")

        # 2.4 Extreme boundary inputs (0m distance, 100,000m distance, 0 subchannels handling)
        zero_d_res = comm.judge_uplink([("zero_d", 25.0, 0.0)])
        assert 0.0 <= zero_d_res["zero_d"] <= 1.0, "Zero distance failed"
        huge_d_res = comm.judge_uplink([("huge_d", 25.0, 100000.0)])
        assert 0.0 <= huge_d_res["huge_d"] <= 1.0, "Huge distance failed"
        details.append(f"Edge distances: 0m -> {zero_d_res['zero_d']:.4f}, 100,000m -> {huge_d_res['huge_d']:.8e}")

        # 2.5 Empty group handling
        empty_res = comm.judge_uplink([])
        assert empty_res == {}, "Empty group did not return empty dict"
        details.append("Empty transmitter group handled cleanly -> {}")

        for d in details:
            print(f"    - {d}")

        self.record_result("Suite 2 (Communications & Rayleigh SINR)", passed, f"{len(contender_counts)} contention levels & physical laws verified")
        return passed

    # =========================================================================
    # SUITE 3: Live Fault Injection & Anti-Mocking Assertion Bypass Tests
    # =========================================================================
    def run_suite_3_anti_mocking_bypass(self) -> bool:
        self.log_header("SUITE 3: Live Fault Injection & Anti-Mocking Assertion Bypass Tests")
        passed = True
        details = []

        # Attack 3.1: Inject time freeze during env.step()
        print("  [Attack 3.1] Testing Time Regression / Freeze Assertion in live step()...")
        env1 = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
        env1.reset(seed=42)
        # Advance 1 step
        env1.step()
        # Tamper _prev_sim_time to future time (simulating time regression)
        env1._prev_sim_time = 99999.0
        caught_1 = False
        try:
            env1.step()
        except AssertionError as e:
            if "FATAL: Simulation time regression/freeze detected" in str(e):
                caught_1 = True
                details.append(f"Attack 3.1 caught as expected: {e}")
        finally:
            env1.close()

        if not caught_1:
            passed = False
            details.append("Attack 3.1 FAILED: Time regression was not caught by live step() assertion!")

        # Attack 3.2: Inject coordinate freeze on a moving vehicle
        print("  [Attack 3.2] Testing Vehicle Coordinate Freeze Assertion in live step()...")
        env2 = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
        env2.reset(seed=42)
        env2.step()
        active_vids = env2.get_active_vehicles()
        caught_2 = False
        if active_vids:
            target_v = active_vids[0]
            # Save original getPosition
            orig_get_pos = sumo.vehicle.getPosition
            orig_get_spd = sumo.vehicle.getSpeed
            try:
                # Monkeypatch getPosition to return identical previous position while getSpeed returns 20 m/s
                fake_pos = env2._prev_vehicle_positions.get(target_v, (100.0, 100.0))
                sumo.vehicle.getPosition = lambda vid: fake_pos if vid == target_v else orig_get_pos(vid)
                sumo.vehicle.getSpeed = lambda vid: 20.0 if vid == target_v else orig_get_spd(vid)
                env2.step()
            except AssertionError as e:
                if "speed is 20.0 m/s but coordinate did not change" in str(e):
                    caught_2 = True
                    details.append(f"Attack 3.2 caught as expected: {e}")
            finally:
                sumo.vehicle.getPosition = orig_get_pos
                sumo.vehicle.getSpeed = orig_get_spd
                env2.close()

        if not caught_2:
            passed = False
            details.append("Attack 3.2 FAILED: Coordinate freeze was not caught by live step() assertion!")

        # Attack 3.3: Inject Out-of-Bounds vehicle coordinate (Mocked teleportation)
        print("  [Attack 3.3] Testing Out-of-Bounds Coordinate Assertion in live step()...")
        env3 = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
        env3.reset(seed=42)
        env3.step()
        active_vids = env3.get_active_vehicles()
        caught_3 = False
        if active_vids:
            target_v = active_vids[0]
            orig_get_pos = sumo.vehicle.getPosition
            try:
                sumo.vehicle.getPosition = lambda vid: (9999999.0, 9999999.0) if vid == target_v else orig_get_pos(vid)
                env3.step()
            except AssertionError as e:
                if "is out of SUMO grid bounds" in str(e):
                    caught_3 = True
                    details.append(f"Attack 3.3 caught as expected: {e}")
            finally:
                sumo.vehicle.getPosition = orig_get_pos
                env3.close()

        if not caught_3:
            passed = False
            details.append("Attack 3.3 FAILED: Out-of-bounds coordinate was not caught!")

        # Attack 3.4: Corrupt Communications probability return (> 1.0)
        print("  [Attack 3.4] Testing Corrupted Uplink Probability Assertion in live step()...")
        env4 = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
        env4.reset(seed=42)
        # Force all vehicles to transmit immediately
        cur_t = float(sumo.simulation.getTime())
        for rec in env4.target_rsu.track.values():
            rec["next_update_t"] = cur_t - 1.0

        orig_judge = comm.judge_uplink
        caught_4 = False
        try:
            comm.judge_uplink = lambda grp, num_subchannels=4: {item[0]: 1.88 for item in grp}
            env4.step()
        except AssertionError as e:
            if "out of [0, 1]" in str(e):
                caught_4 = True
                details.append(f"Attack 3.4 caught as expected: {e}")
        finally:
            comm.judge_uplink = orig_judge
            env4.close()

        if not caught_4:
            passed = False
            details.append("Attack 3.4 FAILED: Corrupted probability was not caught!")

        # Attack 3.5: Corrupt Carrier Frequency Constant
        print("  [Attack 3.5] Testing Carrier Frequency Constant Assertion...")
        env5 = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
        env5.reset(seed=42)
        orig_freq = comm.FREQ_HZ
        caught_5 = False
        try:
            comm.FREQ_HZ = 2.4e9  # Corrupt 5.9GHz ITS to 2.4GHz
            env5.step()
        except AssertionError as e:
            if "Communications.FREQ_HZ is corrupted" in str(e):
                caught_5 = True
                details.append(f"Attack 3.5 caught as expected: {e}")
        finally:
            comm.FREQ_HZ = orig_freq
            env5.close()

        if not caught_5:
            passed = False
            details.append("Attack 3.5 FAILED: Corrupted FREQ_HZ was not caught!")

        for d in details:
            print(f"    - {d}")

        self.record_result("Suite 3 (Anti-Mocking Assertion Triggers)", passed, f"{len(details)} live attack vectors verified and blocked")
        return passed

    # =========================================================================
    # SUITE 4: Multi-Cycle Reset & TraCI Zombie Process Audit
    # =========================================================================
    def run_suite_4_lifecycle_zombies(self) -> bool:
        self.log_header("SUITE 4: Multi-Cycle Reset & TraCI Zombie Process Audit")
        passed = True
        details = []

        def get_sumo_pids() -> List[int]:
            try:
                res = subprocess.run(
                    ["pgrep", "-f", "sumo"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                pids = [int(p.strip()) for p in res.stdout.strip().split() if p.strip()]
                return pids
            except Exception:
                return []

        initial_pids = get_sumo_pids()
        details.append(f"Initial SUMO processes before test: {initial_pids}")

        # 4.1 Rapid sequential reset and close test (5 cycles)
        env = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
        for cycle in range(5):
            seed = 1000 + cycle
            obs, info = env.reset(seed=seed)
            assert len(obs) > 0, f"Cycle {cycle} reset returned 0 active vehicles!"
            # Step 3 times
            for _ in range(3):
                obs, rew, term, trunc, sinfo = env.step()
            details.append(f"Cycle {cycle+1}/5 (seed={seed}) completed: t={info['sim_time']}s, active={info['n_active']}")

        env.close()
        time.sleep(0.5)

        # 4.2 Multiple independent environment instances in sequence
        for inst_idx in range(3):
            env_temp = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 10})
            obs, info = env_temp.reset(seed=2000 + inst_idx)
            assert len(obs) > 0, f"Instance {inst_idx} reset returned 0 active vehicles!"
            for _ in range(5):
                env_temp.step()
            env_temp.close()
            details.append(f"Independent instance {inst_idx+1}/3 cleanly executed and closed")

        time.sleep(1.0)
        final_pids = get_sumo_pids()
        details.append(f"Final SUMO processes after test: {final_pids}")

        # Check for zombies / leaks
        new_leaked_pids = [p for p in final_pids if p not in initial_pids]
        if new_leaked_pids:
            passed = False
            details.append(f"Zombie / orphaned SUMO processes detected: {new_leaked_pids}")
        else:
            details.append("ZERO zombie / orphaned TraCI processes detected (Clean Lifecycle)")

        for d in details:
            print(f"    - {d}")

        self.record_result("Suite 4 (Reset Lifecycle & Zombie Process Audit)", passed, "Clean termination across 8 reset cycles without zombie processes")
        return passed

    # =========================================================================
    # SUITE 5: High-Contention 50-Step Full Rollout & Invariant Audit
    # =========================================================================
    def run_suite_5_stress_rollout(self) -> bool:
        self.log_header("SUITE 5: High-Contention 50-Step Full Rollout & Invariant Audit")
        passed = True
        details = []

        env = AoiV2IEnv(config={
            "warmup_steps": 60,
            "max_steps": 50,
            "step_length": 1.0,
            "weights": {"w_error": 0.5, "w_power": 0.2, "w_congestion": 0.2, "w_redundant": 0.1},
        })

        obs, info = env.reset(seed=999)
        details.append(f"Rollout started: Target RSU={info['target_rsu']} at {info['target_rsu_pos']}, Initial Active={info['n_active']}")

        step_rewards = []

        for step in range(50):
            active_vids = env.get_active_vehicles()
            # Stress action: All vehicles transmit EVERY step on channel 0 with maximum power 30 dBm
            # This triggers maximum possible contention, interference, and packet collisions
            stress_actions = {}
            for vid in active_vids:
                # delta = 0.5s (minimum interval), ch = 0 (same subchannel), power = 30.0 dBm (max power)
                stress_actions[vid] = env.decoder.encode_action(delta=0.5, ch=0, power=30.0)

            obs, rewards, term, trunc, sinfo = env.step(stress_actions)

            # Invariant 1: All observation vectors must be strictly in [-1.0, 1.0]
            for vid, o_vec in obs.items():
                if not (np.all(o_vec >= -1.0 - 1e-5) and np.all(o_vec <= 1.0 + 1e-5)):
                    passed = False
                    details.append(f"Observation bounds violated at step {step} for {vid}: min={o_vec.min()}, max={o_vec.max()}")

            # Invariant 2: All rewards must be negative penalty values <= 0.0
            for vid, r in rewards.items():
                if r > 0.0:
                    passed = False
                    details.append(f"Reward > 0 at step {step} for {vid}: {r}")

            step_rewards.append(sinfo["step_reward"])

            # Telemetry snapshot
            if step % 10 == 0 or step == 49:
                m = env.get_metrics_summary()
                details.append(
                    f"Step {step:02d} (t={sinfo['sim_time']:.1f}s): Active={sinfo['n_active']} | "
                    f"Reward={sinfo['step_reward']:.4f} | TxAttempts={m['tx_attempts']} | "
                    f"TxSuccess={m['tx_success']} | TxFail={m['tx_fail']} | "
                    f"SuccessRate={m['tx_success_rate']*100:.1f}% | Contenders/Ch={m['mean_contenders_per_ch']:.1f}"
                )

        metrics = env.get_metrics_summary()
        env.close()

        details.append(f"Final 50-step metrics: {metrics}")
        # High contention should have caused high collision/drop rate
        assert metrics["tx_attempts"] > 100, f"Expected >100 tx attempts, got {metrics['tx_attempts']}"
        assert metrics["tx_fail"] > 0, "High contention failed to produce packet collisions/drops!"

        for d in details:
            print(f"    - {d}")

        self.record_result("Suite 5 (High-Contention 50-Step Rollout)", passed, f"50 steps completed under maximum contention; All invariants verified")
        return passed

    def run_all(self) -> int:
        print("=" * 78)
        print("STARTING EMPIRICAL ADVERSARIAL STRESS TESTING SUITE")
        print("Target: AoiV2IEnv & Communications.py & SUMO Simulation")
        print("=" * 78)

        s1 = self.run_suite_1_action_space()
        s2 = self.run_suite_2_communications()
        s3 = self.run_suite_3_anti_mocking_bypass()
        s4 = self.run_suite_4_lifecycle_zombies()
        s5 = self.run_suite_5_stress_rollout()

        all_passed = s1 and s2 and s3 and s4 and s5

        print("\n" + "=" * 78)
        print("FINAL ADVERSARIAL STRESS TEST SUMMARY")
        print("=" * 78)
        for suite, res in self.results.items():
            status = "[PASS]" if res["passed"] else "[FAIL]"
            print(f"  {status:7s} | {suite}: {res['details']}")
        print("=" * 78)

        if all_passed:
            print("\n>>> OVERALL VERDICT: ALL ADVERSARIAL CHALLENGES PASSED (100% GENUINE & ROBUST)\n")
            return 0
        else:
            print("\n>>> OVERALL VERDICT: ONE OR MORE CHALLENGES FAILED\n")
            return 1


if __name__ == "__main__":
    runner = AdversarialTestRunner()
    sys.exit(runner.run_all())
