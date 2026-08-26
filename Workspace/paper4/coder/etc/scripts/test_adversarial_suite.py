#!/usr/bin/env python3
"""
test_adversarial_suite.py
=============================================================================
Adversarial Stress Testing & Fault Injection Suite for challenger_final_1.

Covers all 5 verification points:
1. verify_environment.py execution & genuine SUMO verification.
2. Fault injection into AoiV2IEnv anti-mocking assertions (1-4).
3. 9 Baseline RL models stepping & inferring on real SUMO environment.
4. DualModelHotSwapManager & TransitionStreamer atomic swap & gradient update.
5. System halt state verification (no running 200k heavy background training).
=============================================================================
"""

import math
import os
import queue
import subprocess
import sys
import threading
import time
import numpy as np
import torch
import torch.nn as nn

# Ensure venv in PATH
if "/home/imnyj/venv/bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = "/home/imnyj/venv/bin:" + os.environ.get("PATH", "")

PROJECT_ROOT = "/home/imnyj/Workspace/paper4/coder"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import src.Communications as comm
import src.NetSim as net
import src.sumo.make_sumo_set as ss
from src.aoi_env import AoiV2IEnv
from src.baselines import (
    HybridPPO,
    HybridSAC,
    HybridTD3,
    MAPPO,
    HyARPPO,
    MPDQN,
    PureAoI,
    DuelingQAoI,
    SACAoI,
)
from src.hot_swap_trainer import DualModelHotSwapManager, TransitionStreamer, HotSwapTrainer
from src.rl_interface import RetrospectiveReplayBuffer


def section(title: str):
    print("\n" + "=" * 80)
    print(f"=== [CHALLENGER TEST] {title}")
    print("=" * 80)


def test_1_verify_environment_script():
    section("1. Run verify_environment.py directly and assert zero exit code")
    cmd = ["/home/imnyj/venv/bin/python", os.path.join(PROJECT_ROOT, "verify_environment.py")]
    t0 = time.time()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    dt = time.time() - t0
    print(f"verify_environment.py output (took {dt:.2f}s):\n{res.stdout}")
    if res.stderr:
        print(f"STDERR:\n{res.stderr}")
    assert res.returncode == 0, f"verify_environment.py failed with returncode {res.returncode}"
    assert "ALL ENVIRONMENT VERIFICATION TESTS PASSED (100% GENUINE)" in res.stdout
    print(">>> TEST 1 PASSED: verify_environment.py successfully verified genuine SUMO connection & delta_x > 0.")


def test_2_fault_injection_on_env():
    section("2. Fault Injection on AoiV2IEnv Anti-Mocking Assertions")

    # 2.1 Test Assertion 1: Simulation Time Regression / Freeze
    print("\n--- Subtest 2.1: Assertion 1 Fault Injection (Time Freeze/Regression) ---")
    env = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
    obs, info = env.reset(seed=42)
    
    # Intentionally corrupt _prev_sim_time to future time (simulating time regression in step)
    env._prev_sim_time = 999999.0
    caught_1 = False
    try:
        env.step()
    except AssertionError as e:
        caught_1 = True
        print(f"  [SUCCESSFULLY CAUGHT] Assertion 1 triggered on time regression: {e}")
    finally:
        env.close()
    assert caught_1, "FAILED: AoiV2IEnv did not trigger AssertionError when simulation time regressed!"

    # 2.2 Test Assertion 2: Coordinate Freeze / Zero Displacement
    print("\n--- Subtest 2.2: Assertion 2 Fault Injection (Vehicle Coordinate Freeze) ---")
    import src.aoi_env as aoi_mod
    class FrozenPosDict(dict):
        def __getitem__(self, vid):
            return aoi_mod.sumo.vehicle.getPosition(vid)
        def __contains__(self, vid):
            return True

    env = aoi_mod.AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
    obs, info = env.reset(seed=42)
    env.step()

    # Inject frozen coordinate behavior
    env._prev_vehicle_positions = FrozenPosDict()

    caught_2 = False
    try:
        env.step()
    except AssertionError as e:
        caught_2 = True
        print(f"  [SUCCESSFULLY CAUGHT] Assertion 2 triggered on coordinate freeze: {e}")
    finally:
        env.close()
    assert caught_2, "FAILED: AoiV2IEnv did not trigger AssertionError when vehicle coordinate froze at high speed!"

    # 2.3 Test Assertion 3: Bypass Communications / Invalid Probability
    print("\n--- Subtest 2.3: Assertion 3 Fault Injection (Invalid Wireless Channel Output) ---")
    env = aoi_mod.AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
    obs, info = env.reset(seed=42)
    
    real_judge = comm.judge_uplink
    caught_3 = False
    try:
        def fake_judge(records, num_subchannels=4):
            return {item[0]: 1.5 for item in records}
        
        comm.judge_uplink = fake_judge
        # Force immediate transmission
        for rec in env.target_rsu.track.values():
            rec["next_update_t"] = 0.0

        try:
            env.step()
        except AssertionError as e:
            caught_3 = True
            print(f"  [SUCCESSFULLY CAUGHT] Assertion 3 triggered on corrupted channel probability: {e}")
    finally:
        comm.judge_uplink = real_judge
        env.close()
    assert caught_3, "FAILED: AoiV2IEnv did not trigger AssertionError when judge_uplink returned corrupted probability!"

    # 2.4 Test Assertion 4: Reward Tampering / Positivity
    print("\n--- Subtest 2.4: Assertion 4 Fault Injection (Reward Formula Violation) ---")
    env = aoi_mod.AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 20})
    obs, info = env.reset(seed=42)
    
    caught_4 = False
    try:
        # Intentionally inject negative weight to create positive reward
        env.w_error = -10.0
        env.step()
    except AssertionError as e:
        caught_4 = True
        print(f"  [SUCCESSFULLY CAUGHT] Assertion 4 triggered on positive/tampered reward: {e}")
    finally:
        env.close()
    assert caught_4, "FAILED: AoiV2IEnv did not trigger AssertionError on tampered reward values!"

    print(">>> TEST 2 PASSED: All 4 Anti-Mocking Assertions trigger reliably on fault injection.")


def test_3_all_9_baselines_real_sumo():
    section("3. Verify All 9 Baseline RL Models Step and Infer on Real SUMO Transitions")
    
    model_classes = [
        ("HybridPPO", HybridPPO),
        ("HybridSAC", HybridSAC),
        ("HybridTD3", HybridTD3),
        ("MAPPO", MAPPO),
        ("HyARPPO", HyARPPO),
        ("MPDQN", MPDQN),
        ("PureAoI", PureAoI),
        ("DuelingQAoI", DuelingQAoI),
        ("SACAoI", SACAoI),
    ]

    env = AoiV2IEnv(config={"warmup_steps": 60, "max_steps": 30})
    obs, info = env.reset(seed=42)
    print(f"  AoiV2IEnv initialized with {info['n_active']} active vehicles at t={info['sim_time']:.1f}s")
    assert len(obs) > 0, "No active vehicles in reset!"

    state_dim = 16
    for name, cls in model_classes:
        t_start = time.time()
        agent = cls(state_dim=state_dim)
        
        # 1. Test inference on current observation dict
        actions = {}
        for vid, s_vec in obs.items():
            decoded_grant, raw_act, aux_info = agent.select_action(s_vec, deterministic=False)
            actions[vid] = decoded_grant
            delta, ch, p = decoded_grant
            assert 0.5 <= delta <= 10.0, f"Delta {delta} out of bounds [0.5, 10.0] for {name}"
            assert ch in (0, 1, 2, 3), f"Channel {ch} out of bounds {{0,1,2,3}} for {name}"
            assert 20.0 <= p <= 30.0, f"Power {p} out of bounds [20.0, 30.0] for {name}"

        # 2. Step environment with agent's actions
        next_obs, rewards, term, trunc, step_info = env.step(actions)
        
        # Verify step properties
        assert len(next_obs) > 0, f"Empty observations after step for {name}"
        assert step_info["step_reward"] <= 0.0, f"Positive reward for {name}"
        
        obs = next_obs
        dt = time.time() - t_start
        print(f"  [{name:12s}] PASSED: active={len(next_obs):2d} | Mean Reward={step_info['step_reward']:+.4f} | sim_time={step_info['sim_time']:.1f}s ({dt:.3f}s)")

    env.close()
    print("\n>>> TEST 3 PASSED: All 9 baseline models successfully inferred and stepped on genuine SUMO.")


def test_4_dual_model_hotswap_and_streamer():
    section("4. Stress Test DualModelHotSwapManager & TransitionStreamer")

    from src.baselines.hybrid_sac import HybridSAC

    state_dim = 16
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Testing on device: {device}")

    act_model = HybridSAC(state_dim=state_dim, device=device)
    rest_model = HybridSAC(state_dim=state_dim, device=device)

    # 4.1 Test DualModelHotSwapManager Atomic Swap
    print("\n--- Subtest 4.1: Atomic Swap and Parameter Synchronization ---")
    manager = DualModelHotSwapManager(act_model=act_model, rest_model=rest_model)

    # Perturb rest model weights
    with torch.no_grad():
        for p in rest_model.parameters():
            p.add_(torch.randn_like(p) * 0.1)

    # Perform atomic hot swap
    swap_res = manager.hot_swap()
    assert swap_res is True, "Hot swap returned False!"

    # Verify act model weights match rest model weights exactly
    for p_act, p_rest in zip(act_model.parameters(), rest_model.parameters()):
        assert torch.allclose(p_act, p_rest), "Act model weights mismatch after hot swap!"
    print("  [OK] Parameter synchronization verified under mutex lock.")

    # 4.2 Test NaN/Inf Gradient Protection Guard
    print("\n--- Subtest 4.2: NaN/Inf Fault Injection in Rest Model ---")
    with torch.no_grad():
        first_param = next(rest_model.parameters())
        first_param.view(-1)[0] = float("nan")

    nan_swap_res = manager.hot_swap()
    assert nan_swap_res is False, "Hot swap failed to reject NaN corrupted weights!"
    print("  [OK] NaN weight corruption safely blocked from contaminating Act model.")

    # 4.3 Test Cross-Device Transfer (CPU to Device or Vice Versa)
    print("\n--- Subtest 4.3: Cross-Device Parameter Hot-Swap ---")
    cpu_model = HybridSAC(state_dim=state_dim, device="cpu")
    cross_mgr = DualModelHotSwapManager(act_model=act_model, rest_model=cpu_model)
    cross_swap = cross_mgr.hot_swap()
    assert cross_swap is True, "Cross-device hot swap failed!"
    print("  [OK] Cross-device hot swap (CPU -> target device) verified.")

    # 4.4 Test TransitionStreamer Multi-Threaded Throughput & Buffer Push
    print("\n--- Subtest 4.4: Multi-threaded TransitionStreamer Throughput ---")
    streamer = TransitionStreamer(maxsize=1000)
    replay_buf = RetrospectiveReplayBuffer(capacity=2000, gamma=0.99)
    
    n_items = 300
    pushed_items = []
    
    def producer():
        for i in range(n_items):
            s = np.random.randn(16).astype(np.float32)
            a = (1.5, 2, 25.0)
            r = -0.35
            s_next = np.random.randn(16).astype(np.float32)
            d = False
            dt = 1.0
            pushed = streamer.push(s, a, r, s_next, d, dt)
            if pushed:
                pushed_items.append(i)
            time.sleep(0.0002)

    t = threading.Thread(target=producer)
    t.start()

    inserted_total = 0
    t_end = time.time() + 3.0
    while time.time() < t_end and (t.is_alive() or not streamer.is_empty()):
        n_ins = streamer.push_to_buffer(replay_buf, max_items=50)
        inserted_total += n_ins
        time.sleep(0.001)

    t.join(timeout=2.0)
    # Drain any remaining
    inserted_total += streamer.push_to_buffer(replay_buf)

    print(f"  [OK] TransitionStreamer pushed {len(pushed_items)} items, inserted {inserted_total} items into RetrospectiveReplayBuffer.")
    assert inserted_total == len(pushed_items), f"Buffer count mismatch: {inserted_total} != {len(pushed_items)}"
    assert len(replay_buf) == inserted_total, f"Replay buffer size mismatch: {len(replay_buf)} != {inserted_total}"

    # Sample batch from replay buffer
    batch = replay_buf.sample(batch_size=32)
    assert batch["state"].shape == (32, 16)
    assert batch["reward"].shape == (32, 1)
    print("  [OK] Sampled SMDP batch verified from RetrospectiveReplayBuffer.")

    print(">>> TEST 4 PASSED: DualModelHotSwapManager & TransitionStreamer verified with 100% integrity.")


def test_5_verify_system_halt_state():
    section("5. Verify No Infinite 200,000-Step Training Loop Is Running (Safe Halt Check)")
    res = subprocess.run(["ps", "aux"], stdout=subprocess.PIPE, text=True)
    lines = res.stdout.splitlines()
    
    suspicious_keywords = ["200000", "hpo.py", "run_experiment.py", "hot_swap_trainer.py"]
    active_suspicious = []
    for line in lines:
        if "test_adversarial_suite.py" in line or "grep" in line:
            continue
        for kw in suspicious_keywords:
            if kw in line and "pytest" not in line and "python -c" not in line:
                active_suspicious.append(line)

    print(f"  Checking process table for runaway heavy training scripts...")
    if active_suspicious:
        print(f"  WARNING: Found suspicious processes: {active_suspicious}")
    else:
        print("  [OK] Confirmed: No background heavy training loops (200k steps) are running.")
    
    assert len(active_suspicious) == 0, f"Runaway processes detected: {active_suspicious}"
    print(">>> TEST 5 PASSED: Execution is cleanly halted awaiting user review.")


def main():
    print("################################################################################")
    print("### EMPIRICAL CHALLENGER ADVERSARIAL STRESS TEST SUITE (challenger_final_1)  ###")
    print("################################################################################")
    
    test_1_verify_environment_script()
    test_2_fault_injection_on_env()
    test_3_all_9_baselines_real_sumo()
    test_4_dual_model_hotswap_and_streamer()
    test_5_verify_system_halt_state()

    print("\n" + "#" * 80)
    print("### ALL 5 ADVERSARIAL CHALLENGES COMPLETED & PASSED WITH 100% SUCCESS!       ###")
    print("################################################################################\n")


if __name__ == "__main__":
    main()
