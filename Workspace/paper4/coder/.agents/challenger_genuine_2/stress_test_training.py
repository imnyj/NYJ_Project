# /home/imnyj/Workspace/paper4/coder/.agents/challenger_genuine_2/stress_test_training.py
"""
Adversarial Stress Test Harness for:
1. 9 Baseline RL Models (forward pass, action selection, backward loss updates, extreme/corrupted tensors)
2. DualModelHotSwapManager (atomic hot-swap, NaN/Inf weight rejection, multi-threaded reader/writer race condition)
3. AoiV2IEnv + HotSwapTrainer Rollout (50 real SUMO steps, TensorBoard scalar logging, checkpoint creation)
4. Optuna HPO Composite Objective & Search Space Boundary Stress
"""

import copy
import math
import os
import sys
import threading
import time
import traceback
from typing import Any, Dict, List, Tuple

import numpy as np
import optuna
import torch
import torch.nn as nn

# Add project root to sys.path
sys.path.insert(0, "/home/imnyj/Workspace/paper4/coder")

from src.baselines import (
    BASELINE_REGISTRY,
    BaseRLModel,
    DuelingQAoI,
    HyARPPO,
    HybridPPO,
    HybridSAC,
    HybridTD3,
    MAPPO,
    MPDQN,
    PureAoI,
    SACAoI,
)
from src.hot_swap_trainer import (
    AoiV2IEnv,
    BackgroundTrainer,
    DualModelHotSwapManager,
    HotSwapRLScheduler,
    HotSwapTrainer,
    TransitionStreamer,
    run_hot_swap_training,
)
from src.hpo import (
    CANONICAL_MODEL_NAMES,
    compute_composite_objective,
    normalize_model_name,
    sample_hparams,
)


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


# ============================================================================
# Test Suite 1: 9 Baseline Models Adversarial Stress
# ============================================================================
def test_baseline_models_stress() -> Dict[str, Any]:
    print_section("SUITE 1: 9 Baseline Models Adversarial Stress & Numerical Stability")
    results = {}
    
    canonical_models = [
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

    for name, model_cls in canonical_models:
        print(f"\n--- Testing Baseline: {name} ---")
        model_results = {"passed": True, "details": []}
        
        try:
            model = model_cls(state_dim=16, num_channels=4)
            model.eval()

            # 1. Nominal forward pass and action selection
            state_1d = np.random.randn(16).astype(np.float32)
            state_2d = torch.randn(1, 16)
            
            # Deterministic and stochastic
            grant_det, raw_det, info_det = model.select_action(state_1d, deterministic=True)
            grant_stoch, raw_stoch, info_stoch = model.select_action(state_2d, deterministic=False)
            
            # Verify grant ranges
            for grant, mode in [(grant_det, "det"), (grant_stoch, "stoch")]:
                delta, ch, p = grant
                assert 0.5 <= delta <= 10.0, f"[{name}] {mode} Delta out of range: {delta}"
                assert 0 <= ch < 4, f"[{name}] {mode} Channel out of range: {ch}"
                assert 20.0 <= p <= 30.0, f"[{name}] {mode} Power out of range: {p}"
                assert not math.isnan(delta) and not math.isnan(p), f"[{name}] {mode} NaN in grant"

            model_results["details"].append("Nominal action selection: PASS")

            # 2. Extreme state values (Boundary Testing)
            extreme_states = [
                ("Zero state", np.zeros(16, dtype=np.float32)),
                ("Huge positive (+1e5)", np.ones(16, dtype=np.float32) * 1e5),
                ("Huge negative (-1e5)", np.ones(16, dtype=np.float32) * -1e5),
                ("Small non-zero (1e-8)", np.ones(16, dtype=np.float32) * 1e-8),
            ]

            for label, ext_s in extreme_states:
                grant_ext, raw_ext, info_ext = model.select_action(ext_s, deterministic=True)
                delta, ch, p = grant_ext
                assert not math.isnan(delta) and not math.isnan(p), f"[{name}] Extreme state {label} produced NaN"
                assert not math.isinf(delta) and not math.isinf(p), f"[{name}] Extreme state {label} produced Inf"
                assert 0 <= ch < 4, f"[{name}] Extreme state {label} produced invalid channel: {ch}"

            model_results["details"].append("Extreme state value stability: PASS")

            # 3. Model Training & Backward Loss Update
            model.train()
            batch_size = 16
            nominal_batch = {
                "state": torch.randn(batch_size, 16),
                "action": torch.cat([
                    torch.rand(batch_size, 1) * 9.5 + 0.5,
                    torch.randint(0, 4, (batch_size, 1)).float(),
                    torch.rand(batch_size, 1) * 10.0 + 20.0,
                ], dim=-1),
                "reward": torch.randn(batch_size, 1) * 2.0 - 1.0,
                "next_state": torch.randn(batch_size, 16),
                "done": (torch.rand(batch_size, 1) > 0.8).float(),
                "delta_t": torch.rand(batch_size, 1) * 4.0 + 0.5,
            }

            loss_dict = model.update(nominal_batch)
            assert "loss" in loss_dict, f"[{name}] 'loss' key missing from update loss_dict"
            assert not math.isnan(loss_dict["loss"]) and not math.isinf(loss_dict["loss"]), f"[{name}] Nominal loss is NaN/Inf: {loss_dict}"
            model_results["details"].append(f"Nominal update (loss={loss_dict['loss']:.4f}): PASS")

            # 4. Corrupted / Extreme Batch Loss Updates
            # Test extreme rewards, out-of-bound channels, extreme delta_ts
            stress_batch = {
                "state": torch.randn(batch_size, 16) * 100.0,
                "action": torch.cat([
                    torch.randn(batch_size, 1) * 50.0,
                    torch.tensor([[-99.0], [999.0]] * (batch_size // 2)),  # Out-of-bounds channels
                    torch.randn(batch_size, 1) * 50.0,
                ], dim=-1),
                "reward": torch.tensor([[-1e5], [1e5]] * (batch_size // 2)),  # Extreme rewards
                "next_state": torch.randn(batch_size, 16) * 100.0,
                "done": torch.ones(batch_size, 1),
                "delta_t": torch.tensor([[0.0], [100.0]] * (batch_size // 2)),  # Extreme delta_t
            }

            stress_loss = model.update(stress_batch)
            assert "loss" in stress_loss, f"[{name}] 'loss' missing in stress update"
            assert not math.isnan(stress_loss["loss"]) and not math.isinf(stress_loss["loss"]), f"[{name}] Stress loss is NaN/Inf: {stress_loss}"
            model_results["details"].append(f"Adversarial batch update (loss={stress_loss['loss']:.4f}): PASS")

            print(f"[{name}] ALL TESTS PASSED: {model_results['details']}")

        except Exception as e:
            model_results["passed"] = False
            model_results["error"] = f"{type(e).__name__}: {str(e)}"
            model_results["traceback"] = traceback.format_exc()
            print(f"[{name}] FAILED with error: {e}")
            traceback.print_exc()

        results[name] = model_results

    return results


# ============================================================================
# Test Suite 2: DualModelHotSwapManager Atomic Concurrency & NaN/Inf Guard
# ============================================================================
def test_hot_swap_manager_stress() -> Dict[str, Any]:
    print_section("SUITE 2: DualModelHotSwapManager Atomic Synchronization & NaN/Inf Safety Guard")
    results = {"passed": True, "details": []}

    try:
        act_model = HybridPPO(state_dim=16, num_channels=4)
        rest_model = HybridPPO(state_dim=16, num_channels=4)
        swap_lock = threading.Lock()

        manager = DualModelHotSwapManager(
            act_model=act_model,
            rest_model=rest_model,
            swap_lock=swap_lock,
        )

        # 1. Verify clean weights initial validation & swap
        assert manager.validate_weights() is True, "validate_weights failed on clean weights"
        succ = manager.hot_swap()
        assert succ is True, "hot_swap failed on clean weights"
        assert manager.swap_count == 1, f"Expected swap_count 1, got {manager.swap_count}"
        results["details"].append("Clean weight hot-swap: PASS")

        # 2. NaN weight corruption guard test
        with torch.no_grad():
            first_param = next(rest_model.parameters())
            orig_val = first_param.clone()
            first_param[0] = float("nan")

        assert manager.validate_weights() is False, "validate_weights failed to detect NaN"
        swap_res = manager.hot_swap()
        assert swap_res is False, "hot_swap succeeded despite NaN in Rest model parameters!"
        assert manager.failed_swaps == 1, f"Expected failed_swaps 1, got {manager.failed_swaps}"
        results["details"].append("NaN weight rejection guard: PASS")

        # 3. Inf weight corruption guard test
        with torch.no_grad():
            first_param[0] = float("inf")

        assert manager.validate_weights() is False, "validate_weights failed to detect +Inf"
        swap_res_inf = manager.hot_swap()
        assert swap_res_inf is False, "hot_swap succeeded despite Inf in Rest model parameters!"
        assert manager.failed_swaps == 2, f"Expected failed_swaps 2, got {manager.failed_swaps}"
        results["details"].append("Inf weight rejection guard: PASS")

        # 4. Restore clean weights and verify recovery
        with torch.no_grad():
            first_param.copy_(orig_val)

        assert manager.validate_weights() is True, "validate_weights failed after restoring clean weights"
        recovery_swap = manager.hot_swap()
        assert recovery_swap is True, "hot_swap failed to recover after clean weights restored"
        assert manager.swap_count == 2, f"Expected swap_count 2, got {manager.swap_count}"
        results["details"].append("Recovery after corruption: PASS")

        # 5. Multi-threaded Concurrent Reader/Writer Race Condition Stress Test
        print("\nStarting multi-threaded concurrent race condition stress test (8 readers, 1 writer)...")
        stop_flag = threading.Event()
        read_errors = []
        read_counts = [0] * 8
        total_swaps = [0]

        def reader_worker(worker_id: int):
            state = np.random.randn(16).astype(np.float32)
            while not stop_flag.is_set():
                try:
                    with swap_lock:
                        grant, raw_a, info = act_model.select_action(state, deterministic=False)
                    delta, ch, p = grant
                    if math.isnan(delta) or math.isnan(p) or not (0 <= ch < 4):
                        read_errors.append(f"Worker {worker_id} read invalid grant: {grant}")
                    read_counts[worker_id] += 1
                    time.sleep(0.0002)  # Realistic telemetry arrival interval (avoids artificial thread starving)
                except Exception as e:
                    read_errors.append(f"Worker {worker_id} exception: {e}")
                    traceback.print_exc()

        def writer_worker():
            batch_size = 16
            while not stop_flag.is_set():
                try:
                    # Modify rest model parameters via gradient update
                    batch = {
                        "state": torch.randn(batch_size, 16),
                        "action": torch.cat([
                            torch.rand(batch_size, 1) * 9.5 + 0.5,
                            torch.randint(0, 4, (batch_size, 1)).float(),
                            torch.rand(batch_size, 1) * 10.0 + 20.0,
                        ], dim=-1),
                        "reward": torch.randn(batch_size, 1),
                        "next_state": torch.randn(batch_size, 16),
                        "done": torch.zeros(batch_size, 1),
                        "delta_t": torch.ones(batch_size, 1),
                    }
                    rest_model.train()
                    rest_model.update(batch)
                    
                    # Execute hot-swap
                    succ = manager.hot_swap()
                    if succ:
                        total_swaps[0] += 1
                    time.sleep(0.001)
                except Exception as e:
                    read_errors.append(f"Writer exception: {e}")
                    traceback.print_exc()

        reader_threads = [threading.Thread(target=reader_worker, args=(i,), daemon=True) for i in range(8)]
        writer_thread = threading.Thread(target=writer_worker, daemon=True)

        for t in reader_threads:
            t.start()
        writer_thread.start()

        # Run concurrent stress for 3.0 seconds
        time.sleep(3.0)
        stop_flag.set()

        for t in reader_threads:
            t.join(timeout=1.0)
        writer_thread.join(timeout=1.0)

        total_reads = sum(read_counts)
        stats = manager.get_stats()
        print(f"Concurrent stress finished: {total_reads} reads, {total_swaps[0]} swaps, {len(read_errors)} errors.")
        print(f"Manager stats: {stats}")

        assert len(read_errors) == 0, f"Concurrent reads produced errors: {read_errors[:5]}"
        assert total_reads > 500, f"Too few concurrent reads: {total_reads}"
        assert total_swaps[0] >= 10, f"Too few concurrent swaps: {total_swaps[0]}"

        results["details"].append(
            f"Concurrent race condition stress ({total_reads} reads, {total_swaps[0]} swaps, 0 errors, mean latency={stats['mean_swap_latency_ms']}ms): PASS"
        )

    except Exception as e:
        results["passed"] = False
        results["error"] = f"{type(e).__name__}: {str(e)}"
        results["traceback"] = traceback.format_exc()
        print(f"[HotSwapManager] FAILED: {e}")
        traceback.print_exc()

    return results


# ============================================================================
# Test Suite 3: AoiV2IEnv Rollout & HotSwapTrainer Full Pipeline (50 Real Steps)
# ============================================================================
def test_sumo_rollout_and_trainer_stress() -> Dict[str, Any]:
    print_section("SUITE 3: AoiV2IEnv 50 Real SUMO Steps Rollout, HotSwapTrainer & TensorBoard Logging")
    results = {"passed": True, "details": []}

    try:
        checkpoint_dir = "/home/imnyj/Workspace/paper4/coder/checkpoints/test_challenger"
        tensorboard_dir = "/home/imnyj/Workspace/paper4/coder/logs/tensorboard/test_challenger"
        csv_log_path = "/home/imnyj/Workspace/paper4/coder/logs/training/test_challenger_progress.csv"

        os.makedirs(checkpoint_dir, exist_ok=True)
        os.makedirs(tensorboard_dir, exist_ok=True)

        print("Executing run_hot_swap_training with HybridPPO for 50 steps...")
        train_res = run_hot_swap_training(
            model_name="HybridPPO",
            total_steps=50,
            episodes=1,
            density=25.0,
            batch_size=16,
            swap_interval=10,
            checkpoint_dir=checkpoint_dir,
            tensorboard_dir=tensorboard_dir,
            log_csv_path=csv_log_path,
            warmup_steps=35,
            seed=42,
        )

        print(f"Training run completed! Returned dict: {train_res}")

        # Assertions
        assert train_res["total_steps"] == 50, f"Expected 50 total steps, got {train_res['total_steps']}"
        assert train_res["elapsed_seconds"] > 0.0, "Elapsed seconds must be > 0"
        assert train_res["throughput_steps_per_sec"] > 0.0, "Throughput must be > 0"
        assert os.path.exists(csv_log_path), f"Log CSV not created: {csv_log_path}"
        results["details"].append(f"50 real SUMO steps executed ({train_res['throughput_steps_per_sec']} steps/s): PASS")

        # Verify Checkpoints Created
        best_ckpt = os.path.join(checkpoint_dir, "HybridPPO_best.pt")
        ep_ckpt = os.path.join(checkpoint_dir, "HybridPPO_ep001.pt")
        assert os.path.exists(best_ckpt) or os.path.exists(ep_ckpt), "No checkpoint file saved!"
        
        target_ckpt = best_ckpt if os.path.exists(best_ckpt) else ep_ckpt
        ckpt_data = torch.load(target_ckpt, map_location="cpu")
        assert "act_state_dict" in ckpt_data, "act_state_dict missing from checkpoint"
        assert "rest_state_dict" in ckpt_data, "rest_state_dict missing from checkpoint"
        assert "training_steps" in ckpt_data, "training_steps missing from checkpoint"
        results["details"].append(f"Checkpoint integrity verified ({os.path.basename(target_ckpt)}): PASS")

        # Verify TensorBoard Event File Created
        tb_subdirs = [os.path.join(tensorboard_dir, d) for d in os.listdir(tensorboard_dir) if os.path.isdir(os.path.join(tensorboard_dir, d))]
        assert len(tb_subdirs) > 0, "No TensorBoard log directory created!"
        tb_files = os.listdir(tb_subdirs[0])
        event_files = [f for f in tb_files if "events.out.tfevents" in f]
        assert len(event_files) > 0, f"No event files in TensorBoard dir: {tb_subdirs[0]}"
        results["details"].append(f"TensorBoard event file verified ({event_files[0]}): PASS")

        # Verify CSV progress file content
        import pandas as pd
        df = pd.read_csv(csv_log_path)
        assert len(df) >= 1, "Progress CSV is empty"
        assert "mean_aoi" in df.columns, "mean_aoi column missing from CSV"
        assert "mean_error" in df.columns, "mean_error column missing from CSV"
        results["details"].append(f"Progress CSV verified ({len(df)} rows, {len(df.columns)} columns): PASS")

    except Exception as e:
        results["passed"] = False
        results["error"] = f"{type(e).__name__}: {str(e)}"
        results["traceback"] = traceback.format_exc()
        print(f"[SUMO Rollout & Trainer] FAILED: {e}")
        traceback.print_exc()

    return results


# ============================================================================
# Test Suite 4: Optuna HPO Composite Objective & Search Space Boundary Stress
# ============================================================================
def test_optuna_hpo_stress() -> Dict[str, Any]:
    print_section("SUITE 4: Optuna HPO Composite Objective & Search Space Boundary Stress")
    results = {"passed": True, "details": []}

    try:
        # 1. Composite Objective Function Boundary Calculations
        test_cases = [
            (
                "Ideal zero metrics",
                {"mean_error": 0.0, "mean_aoi": 0.0, "outage_rate": 0.0, "avg_power_norm": 0.0},
                0.0,
            ),
            (
                "Standard nominal metrics",
                {"mean_error": 5.0, "mean_aoi": 2.0, "outage_rate": 0.1, "avg_power_norm": 0.5},
                1.0 * 5.0 + 0.5 * 2.0 + 2.0 * 0.1 + 0.2 * 0.5,  # 5.0 + 1.0 + 0.2 + 0.1 = 6.3
            ),
            (
                "Worst-case boundary metrics",
                {"mean_error": 100.0, "mean_aoi": 50.0, "outage_rate": 1.0, "avg_power_norm": 1.0},
                1.0 * 100.0 + 0.5 * 50.0 + 2.0 * 1.0 + 0.2 * 1.0,  # 100 + 25 + 2 + 0.2 = 127.2
            ),
            (
                "Fallback aliases (packet_loss_rate instead of outage_rate)",
                {"mean_error": 2.0, "mean_aoi": 1.0, "packet_loss_rate": 0.05, "avg_power_norm": 0.2},
                1.0 * 2.0 + 0.5 * 1.0 + 2.0 * 0.05 + 0.2 * 0.2,  # 2.0 + 0.5 + 0.1 + 0.04 = 2.64
            ),
            (
                "Empty metrics dictionary",
                {},
                0.2 * 0.5,  # Default power_norm = 0.5 -> 0.1
            ),
        ]

        for desc, m_dict, expected_val in test_cases:
            val = compute_composite_objective(m_dict)
            assert math.isclose(val, expected_val, rel_tol=1e-5, abs_tol=1e-5), f"Mismatch for '{desc}': got {val}, expected {expected_val}"

        results["details"].append("Composite objective boundary calculations: PASS")

        # 2. Search Space Sampling for all 9 canonical baselines
        study = optuna.create_study(direction="minimize")
        
        for model_name in CANONICAL_MODEL_NAMES:
            trial = study.ask()
            params = sample_hparams(trial, model_name)
            assert isinstance(params, dict) and len(params) > 0, f"[{model_name}] sample_hparams returned invalid/empty dict: {params}"
            
            # Verify instantiated model with sampled params
            model_cls = BASELINE_REGISTRY[model_name]
            instance = model_cls(state_dim=16, num_channels=4, **params)
            assert instance is not None, f"Failed to instantiate {model_name} with params {params}"

        results["details"].append(f"Optuna search space sampling and instantiation for all {len(CANONICAL_MODEL_NAMES)} baselines: PASS")

    except Exception as e:
        results["passed"] = False
        results["error"] = f"{type(e).__name__}: {str(e)}"
        results["traceback"] = traceback.format_exc()
        print(f"[Optuna HPO Stress] FAILED: {e}")
        traceback.print_exc()

    return results


# ============================================================================
# Master Runner & Execution Summary
# ============================================================================
def main():
    start_time = time.perf_counter()
    print("\n" + "#" * 80)
    print("  ADVERSARIAL STRESS TESTING HARNESS — challenger_genuine_2")
    print("#" * 80)

    r1 = test_baseline_models_stress()
    r2 = test_hot_swap_manager_stress()
    r3 = test_sumo_rollout_and_trainer_stress()
    r4 = test_optuna_hpo_stress()

    elapsed = time.perf_counter() - start_time
    print_section(f"TEST EXECUTION SUMMARY (Total Elapsed: {elapsed:.2f}s)")

    all_passed = True
    
    # Check Baselines
    baseline_passed = all(v["passed"] for v in r1.values())
    if baseline_passed:
        print("✓ Suite 1 (9 Baseline Models Stress): ALL 9 PASSED")
    else:
        all_passed = False
        print("✗ Suite 1 (9 Baseline Models Stress): SOME FAILED")
        for k, v in r1.items():
            if not v["passed"]:
                print(f"   - {k}: FAILED ({v.get('error')})")

    # Check Hot-Swap Manager
    if r2["passed"]:
        print("✓ Suite 2 (DualModelHotSwapManager Concurrency & NaN/Inf Guard): PASSED")
    else:
        all_passed = False
        print(f"✗ Suite 2 (DualModelHotSwapManager): FAILED ({r2.get('error')})")

    # Check SUMO Rollout & Trainer
    if r3["passed"]:
        print("✓ Suite 3 (AoiV2IEnv 50 SUMO Steps Rollout, Trainer & TensorBoard): PASSED")
    else:
        all_passed = False
        print(f"✗ Suite 3 (AoiV2IEnv Rollout & Trainer): FAILED ({r3.get('error')})")

    # Check Optuna HPO
    if r4["passed"]:
        print("✓ Suite 4 (Optuna HPO Composite Objective & Search Space): PASSED")
    else:
        all_passed = False
        print(f"✗ Suite 4 (Optuna HPO): FAILED ({r4.get('error')})")

    print("\n" + "=" * 80)
    if all_passed:
        print(">>> OVERALL VERDICT: ALL ADVERSARIAL STRESS TESTS PASSED (APPROVE) <<<")
    else:
        print(">>> OVERALL VERDICT: ONE OR MORE STRESS TESTS FAILED (REJECT) <<<")
    print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
