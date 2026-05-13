#!/usr/bin/env python3
"""
run_full_simulation.py
======================
MAFAC 논문용 전체 시뮬레이션 수행 스크립트.

=== 워크스테이션 실행 가이드 ===

  # 처음 실행 (GPU 사용, Phase 2 전체 500 에피소드)
  python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500

  # 백그라운드 실행 (nohup, 로그는 simulation_log.txt에 저장됨)
  nohup python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 > simulation_log.txt 2>&1 &

  # 중단 후 재개 (--resume 플래그)
  python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 --resume

== 전체 파이프라인 실행 ==
  # 모든 Phase (0~5)
  python3 run_full_simulation.py --device cuda

  # 특정 Phase만
  python3 run_full_simulation.py --phases 1,2 --device cuda
  python3 run_full_simulation.py --phases 3,4,5 --device cuda

== 에피소드 수 조절 (빠른 테스트) ==
  python3 run_full_simulation.py --phases 2 --p2-episodes 50 --device cuda

== GPU 메모리 부족 시 조절 가능한 파라미터 ==
  - --batch-size 128   (기본값: 256)  ← MAFACAgent의 batch_size
  - --p2-episodes 200  (에피소드 수 줄이기)
  - num_vehicles 줄이기 (env_config 내 직접 수정, 기본 50)
  - buffer_size 줄이기 (MAFACAgent 기본값 100000 → 50000)

== 결과 ==
  모든 결과는 OUTPUT_DIR (paper/data/) 에 CSV로 저장됩니다.
"""

import sys
import os
import argparse
import random
import math
import time
import traceback
import numpy as np
from pathlib import Path

# ── Path Setup ────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# ── Constants ─────────────────────────────────────────────────────────────────
OUTPUT_DIR     = str(_HERE.parent / "paper" / "data")
CHECKPOINT_DIR = str(_HERE / "checkpoints")
LOG_FILE       = str(_HERE / "simulation_log.txt")

ALGORITHMS = ["MAFAC", "Centralized-AoI", "SAC-Single", "IQL", "NDN-LRU", "No-Cache"]

# ── Logging Helper ────────────────────────────────────────────────────────────
class Logger:
    """Dual output: console + log file."""
    def __init__(self, log_path):
        self.log_path = log_path
        self.start_time = time.time()
        with open(log_path, "a") as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"Simulation started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*70}\n")

    def log(self, msg):
        elapsed = time.time() - self.start_time
        ts = f"[{elapsed/60:7.1f}m]"
        line = f"{ts} {msg}"
        print(line)
        with open(self.log_path, "a") as f:
            f.write(line + "\n")

    def error(self, msg):
        self.log(f"ERROR: {msg}")

    def section(self, title):
        sep = "=" * 60
        self.log(sep)
        self.log(title)
        self.log(sep)


# ── Phase 0: Network Check ───────────────────────────────────────────────────
def phase0_check_network(logger):
    """Verify SUMO network files exist."""
    logger.section("Phase 0: SUMO Network Verification")

    config_dir = _HERE / "config"
    required = ["grid5x5.net.xml", "vehicles.rou.xml", "sumo_config.sumocfg"]
    all_ok = True
    for f in required:
        fp = config_dir / f
        if fp.exists():
            sz = fp.stat().st_size
            logger.log(f"  [OK] {f} ({sz:,} bytes)")
        else:
            logger.error(f"  [MISSING] {f}")
            all_ok = False

    if not all_ok:
        logger.log("  Network files missing. Running setup_network.py...")
        import subprocess
        result = subprocess.run(
            [sys.executable, str(_HERE / "setup_network.py"),
             "--num-vehicles=50", "--seed=42"],
            capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logger.log("  Network generated successfully.")
        else:
            logger.error(f"  Network generation failed: {result.stderr[:300]}")
            logger.log("  Simulation will use Mock SUMO mode.")

    # Check libsumo & torch
    try:
        import libsumo
        logger.log("  [OK] libsumo available")
    except ImportError:
        logger.log("  [WARN] libsumo not found → Mock SUMO mode")

    try:
        import torch
        device_detected = "cuda" if torch.cuda.is_available() else "cpu"
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem  = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.log(f"  [OK] PyTorch {torch.__version__} "
                       f"(GPU: {gpu_name}, VRAM: {gpu_mem:.1f}GB)")
        else:
            logger.log(f"  [OK] PyTorch {torch.__version__} (CPU only)")
    except ImportError:
        logger.log("  [WARN] PyTorch not found → numpy fallback mode")

    return all_ok


# ── Phase 1: Model Verification ──────────────────────────────────────────────
def phase1_model_verification(logger, seed=42):
    """Verify Theorem 1 (AoI Bound) and Theorem 2 (Optimal TTL)."""
    logger.section("Phase 1: Model Verification (Theorem 1 & 2)")

    from utils.logger import ExperimentLogger
    from utils.metrics import compute_theorem1_bound, compute_optimal_ttl
    from env.channel_model import ChannelModel
    from env.ndn_layer import ZipfContentModel

    exp_logger = ExperimentLogger(OUTPUT_DIR)

    # ── Theorem 1: NDN AoI Reduction Bound ────────────────────────────────
    logger.log("Verifying Theorem 1: NDN AoI Reduction Bound")
    channel = ChannelModel(K_db=7.0, seed=seed)
    rng = np.random.default_rng(seed)

    p_hit_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    lambda_content = 0.5

    for p_hit in p_hit_values:
        p_tx = channel.tx_success_prob_analytical(23.0, 150.0, "v2v", True, 100)
        delta_direct = 1.0 / lambda_content + 5.0

        delta_ndn_bound = compute_theorem1_bound(p_hit, p_tx, lambda_content, delta_direct)

        sim_aoi_samples = []
        for _ in range(500):
            if rng.random() < p_hit * p_tx:
                aoi = rng.exponential(1.0 / lambda_content)
            else:
                aoi = delta_direct + rng.exponential(0.5)
            sim_aoi_samples.append(aoi)
        sim_aoi = float(np.mean(sim_aoi_samples))
        rel_err = abs(sim_aoi - delta_ndn_bound) / max(delta_ndn_bound, 1e-6)

        exp_logger.log_theorem1({
            "cache_hit_ratio": p_hit, "p_tx_success": p_tx,
            "lambda_content": lambda_content,
            "simulated_aoi": round(sim_aoi, 4),
            "theoretical_bound": round(delta_ndn_bound, 4),
            "relative_error": round(rel_err, 4),
        })
        logger.log(f"  p_hit={p_hit:.1f}: sim={sim_aoi:.3f}s, bound={delta_ndn_bound:.3f}s, err={rel_err:.3f}")

    # ── Theorem 2: Optimal TTL ────────────────────────────────────────────
    logger.log("Verifying Theorem 2: Optimal TTL")
    zipf = ZipfContentModel(200, 1.0, seed)
    lambda_k = 0.5
    c_miss = 0.1
    w_k = 1.0

    for cid in range(20):
        mu_k = zipf.popularity(cid) * 10.0
        ttl_opt = compute_optimal_ttl(lambda_k, w_k, c_miss, max(mu_k, 1e-6))

        best_ttl, best_aoi = ttl_opt, 1e9
        for ttl_test in [ttl_opt * 0.5, ttl_opt, ttl_opt * 1.5, ttl_opt * 2.0]:
            aoi_test = 1.0 / (2 * lambda_k) + ttl_test / 2.0
            if aoi_test < best_aoi:
                best_aoi = aoi_test
                best_ttl = ttl_test
        aoi_at_opt = 1.0 / (2 * lambda_k) + ttl_opt / 2.0

        exp_logger.log_theorem2({
            "content_id": cid, "lambda_k": round(lambda_k, 4),
            "mu_k": round(mu_k, 6),
            "optimal_ttl_theory": round(ttl_opt, 4),
            "best_ttl_sim": round(best_ttl, 4),
            "aoi_at_optimal": round(aoi_at_opt, 4),
            "aoi_at_best": round(best_aoi, 4),
        })

    exp_logger.close_all()
    logger.log("Phase 1 complete.")


# ── Phase 2: Training + Convergence ──────────────────────────────────────────
def phase2_training(logger, episodes=500, seed=42, device=None, resume=False, update_every=10):
    """Train MAFAC and log convergence curves.

    Args:
        device: PyTorch device string ("cuda" / "cpu" / None=auto).
        resume: If True, pass resume_from to Trainer to continue interrupted training.
        update_every: Gradient update frequency (every N steps).
    """
    logger.section(f"Phase 2: Training MAFAC ({episodes} episodes, device={device})")

    from training.trainer import Trainer

    env_config = {
        "num_vehicles": 50, "cache_size": 50,
        "num_contents": 200, "zipf_alpha": 1.0,
        "rician_K_db": 7.0, "content_update_rate": 0.5,
        "episode_duration_s": 300.0, "headless": True,
    }

    # Resume: point to the MAFAC checkpoint sub-directory
    resume_from = None
    if resume:
        resume_from = str(Path(CHECKPOINT_DIR) / "MAFAC")
        logger.log(f"  Resume mode: loading checkpoint from {resume_from}")

    trainer = Trainer(
        algorithm="MAFAC", env_config=env_config,
        total_episodes=episodes,
        federated_round_interval=10,
        checkpoint_dir=CHECKPOINT_DIR,
        output_dir=OUTPUT_DIR,
        seed=seed,
        verbose=True,
        device=device,
        resume_from=resume_from,
        update_every=update_every,
    )

    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0
    logger.log(f"Phase 2 complete. Training time: {elapsed/60:.1f} min")


# ── Phase 3: Performance Evaluation ──────────────────────────────────────────
def phase3_performance(logger, train_episodes=100, eval_episodes=5, seed=42,
                       device=None):
    """Run all 4 scenarios × 6 algorithms."""
    logger.section("Phase 3: Performance Evaluation (4 scenarios × 6 algorithms)")

    from run_scenario import run_scenario, SCENARIOS

    total_combos = 4 * len(ALGORITHMS)
    completed = 0

    for scenario_id in ["S1", "S2", "S3", "S4"]:
        logger.log(f"\n=== Scenario {scenario_id} ({SCENARIOS[scenario_id]['name']}) ===")
        for algorithm in ALGORITHMS:
            completed += 1
            logger.log(f"  [{completed}/{total_combos}] {scenario_id}/{algorithm}")
            t0 = time.time()
            try:
                run_scenario(
                    scenario_id, algorithm,
                    training_episodes=train_episodes,
                    num_eval_episodes=eval_episodes,
                    output_dir=OUTPUT_DIR, seed=seed, verbose=False,
                    device=device,
                )
                elapsed = time.time() - t0
                logger.log(f"    Done ({elapsed/60:.1f} min)")
            except Exception as e:
                logger.error(f"    {scenario_id}/{algorithm}: {e}")
                traceback.print_exc()

    logger.log("Phase 3 complete.")


# ── Phase 4: Ablation Study ──────────────────────────────────────────────────
def phase4_ablation(logger, train_episodes=100, eval_episodes=3, seed=42,
                    device=None):
    """Ablation study."""
    logger.section("Phase 4: Ablation Study")

    from training.trainer import Trainer
    from training.evaluator import Evaluator
    from utils.logger import ExperimentLogger

    exp_logger = ExperimentLogger(OUTPUT_DIR)

    ablation_variants = {
        "MAFAC-Full":        "MAFAC",
        "MAFAC-NoCaching":   "No-Cache",
        "MAFAC-NoFederated": "IQL",
        "MAFAC-Centralized": "Centralized-AoI",
        "NDN-LRU":           "NDN-LRU",
        "No-Cache":          "No-Cache",
    }

    env_config = {
        "num_vehicles": 50, "cache_size": 50,
        "num_contents": 200, "zipf_alpha": 1.0,
        "rician_K_db": 7.0, "content_update_rate": 0.5,
        "episode_duration_s": 300.0, "headless": True,
    }

    for variant_name, algorithm in ablation_variants.items():
        logger.log(f"  Variant: {variant_name} ({algorithm})")
        t0 = time.time()
        try:
            trainer = Trainer(
                algorithm=algorithm, env_config=env_config,
                total_episodes=train_episodes, output_dir=OUTPUT_DIR,
                checkpoint_dir=CHECKPOINT_DIR, seed=seed, verbose=False,
                device=device)
            trainer.train()

            evaluator = Evaluator(env_config=env_config, output_dir=OUTPUT_DIR, seed=seed)
            metrics = evaluator.evaluate_agents(
                trainer.agents, algorithm, eval_episodes, env_config)
            evaluator.close()

            exp_logger.log_ablation({
                "scenario": "S1_default", "variant": variant_name,
                "average_aoi": round(metrics.get("average_aoi", 0), 4),
                "peak_aoi": round(metrics.get("peak_aoi", 0), 4),
                "cache_hit_ratio": round(metrics.get("cache_hit_ratio", 0), 4),
                "tx_success_rate": round(metrics.get("tx_success_rate", 0), 4),
                "throughput_mbps": round(metrics.get("throughput_mbps", 0), 4),
                "constraint_violation": round(metrics.get("constraint_violation", 0), 4),
            })
            elapsed = time.time() - t0
            logger.log(f"    AoI={metrics.get('average_aoi',0):.3f}s, "
                       f"CHR={metrics.get('cache_hit_ratio',0):.3f} ({elapsed/60:.1f} min)")
        except Exception as e:
            logger.error(f"    {variant_name}: {e}")
            traceback.print_exc()

    exp_logger.close_all()
    logger.log("Phase 4 complete.")


# ── Phase 5: Communication Overhead ──────────────────────────────────────────
def phase5_overhead(logger, train_episodes=100, seed=42, device=None):
    """Communication overhead analysis."""
    logger.section("Phase 5: Communication Overhead Analysis")

    from training.trainer import Trainer
    from utils.logger import ExperimentLogger

    exp_logger = ExperimentLogger(OUTPUT_DIR)

    for algorithm in ["MAFAC", "IQL", "No-Cache"]:
        logger.log(f"  Algorithm: {algorithm}")
        env_config = {
            "num_vehicles": 50, "cache_size": 50,
            "num_contents": 200, "zipf_alpha": 1.0,
            "rician_K_db": 7.0, "content_update_rate": 0.5,
            "episode_duration_s": 300.0, "headless": True,
        }
        try:
            trainer = Trainer(
                algorithm=algorithm, env_config=env_config,
                total_episodes=train_episodes, output_dir=OUTPUT_DIR,
                checkpoint_dir=CHECKPOINT_DIR, seed=seed, verbose=False,
                device=device)
            trainer.train()

            if trainer.federated:
                ov = trainer.federated.get_overhead_stats()
                rounds = trainer.federated.round_count
            else:
                ov = {"total_mb": 0.0, "bytes_per_round": 0.0}
                rounds = 0

            for r in range(max(1, rounds)):
                exp_logger.log_overhead(r + 1, algorithm, {
                    "num_agents": len(trainer.agents), "num_rsus": 4,
                    "bytes_per_round": ov.get("bytes_per_round", 0.0),
                    "cumulative_mb": ov.get("total_mb", 0.0) * (r + 1) / max(1, rounds),
                    "time_s": trainer.env.sim_time if hasattr(trainer.env, "sim_time") else 0,
                })
        except Exception as e:
            logger.error(f"    {algorithm}: {e}")
            traceback.print_exc()

    exp_logger.close_all()
    logger.log("Phase 5 complete.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="MAFAC Full Simulation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 처음 실행 (GPU 사용)
  python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500

  # 백그라운드 실행
  nohup python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 > simulation_log.txt 2>&1 &

  # 중단 후 재개
  python3 run_full_simulation.py --phases 2 --device cuda --p2-episodes 500 --resume

  # 전체 파이프라인 (Phase 0~5)
  python3 run_full_simulation.py --device cuda

  # 특정 Phase만
  python3 run_full_simulation.py --phases 1,2 --device cuda

  # Quick test run
  python3 run_full_simulation.py --phases 1 --p2-episodes 20 --p3-episodes 10
        """)
    parser.add_argument("--phases", type=str, default="0,1,2,3,4,5",
                        help="Phases to run (comma-separated, default: 0,1,2,3,4,5)")
    parser.add_argument("--p2-episodes", type=int, default=500,
                        help="Phase 2 training episodes (default: 500)")
    parser.add_argument("--p3-episodes", type=int, default=100,
                        help="Phase 3-5 per-config training episodes (default: 100)")
    parser.add_argument("--eval-episodes", type=int, default=5,
                        help="Evaluation episodes per config (default: 5)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--device", type=str, default="auto",
                        help="Device: auto/cpu/cuda (default: auto). "
                             "Passed to Trainer and MAFACAgent.")
    # NEW: --resume flag
    parser.add_argument("--resume", action="store_true", default=False,
                        help="Resume Phase 2 training from the latest checkpoint. "
                             "Reads checkpoints/MAFAC/trainer_state.json and "
                             "checkpoints/MAFAC/latest/*.pt to restore state.")
    parser.add_argument("--update-every", type=int, default=10,
                        help="Gradient update frequency (every N steps). Default 10.")
    args = parser.parse_args()

    # Parse phases
    phases = [int(p.strip()) for p in args.phases.split(",") if p.strip()]

    # Resolve device
    device = args.device
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    # Seeds
    random.seed(args.seed)
    np.random.seed(args.seed)
    try:
        import torch
        torch.manual_seed(args.seed)
        if device == "cuda":
            torch.cuda.manual_seed_all(args.seed)
    except ImportError:
        pass

    # Setup directories
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)

    # Logger
    logger = Logger(LOG_FILE)

    logger.section("MAFAC Full Simulation Pipeline")
    logger.log(f"Phases:            {phases}")
    logger.log(f"Phase 2 episodes:  {args.p2_episodes}")
    logger.log(f"Phase 3-5 episodes:{args.p3_episodes}")
    logger.log(f"Eval episodes:     {args.eval_episodes}")
    logger.log(f"Seed:              {args.seed}")
    logger.log(f"Device:            {device}")
    logger.log(f"Resume:            {args.resume}")
    logger.log(f"Output dir:        {OUTPUT_DIR}")
    logger.log(f"Checkpoint dir:    {CHECKPOINT_DIR}")
    logger.log(f"Log file:          {LOG_FILE}")

    t_total = time.time()

    # Phase 0
    if 0 in phases:
        phase0_check_network(logger)

    # Phase 1
    if 1 in phases:
        try:
            phase1_model_verification(logger, seed=args.seed)
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            traceback.print_exc()

    # Phase 2
    if 2 in phases:
        try:
            phase2_training(logger, episodes=args.p2_episodes, seed=args.seed,
                           device=device, resume=args.resume,
                           update_every=args.update_every)
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            traceback.print_exc()

    # Phase 3
    if 3 in phases:
        try:
            phase3_performance(logger,
                             train_episodes=args.p3_episodes,
                             eval_episodes=args.eval_episodes,
                             seed=args.seed, device=device)
        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            traceback.print_exc()

    # Phase 4
    if 4 in phases:
        try:
            phase4_ablation(logger,
                          train_episodes=args.p3_episodes,
                          eval_episodes=args.eval_episodes,
                          seed=args.seed, device=device)
        except Exception as e:
            logger.error(f"Phase 4 failed: {e}")
            traceback.print_exc()

    # Phase 5
    if 5 in phases:
        try:
            phase5_overhead(logger,
                          train_episodes=args.p3_episodes,
                          seed=args.seed, device=device)
        except Exception as e:
            logger.error(f"Phase 5 failed: {e}")
            traceback.print_exc()

    # Summary
    total_elapsed = time.time() - t_total
    logger.section("SIMULATION COMPLETE")
    logger.log(f"Total elapsed time: {total_elapsed/3600:.2f} hours ({total_elapsed/60:.1f} min)")
    logger.log(f"Results saved to:   {OUTPUT_DIR}")
    logger.log(f"Checkpoints at:     {CHECKPOINT_DIR}")
    logger.log(f"Log file:           {LOG_FILE}")

    # List output files
    data_dir = Path(OUTPUT_DIR)
    if data_dir.exists():
        files = sorted(data_dir.glob("*.csv"))
        logger.log(f"\nGenerated {len(files)} CSV files:")
        for f in files:
            logger.log(f"  {f.name} ({f.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
