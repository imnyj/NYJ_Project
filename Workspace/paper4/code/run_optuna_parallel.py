#!/usr/bin/env python3
"""
run_optuna_parallel.py
======================
Distributed 4-GPU Optuna Optimization Engine for 14 RL Models + Non-RL Benchmark Evaluation.
Leverages 4x NVIDIA RTX 3090 GPUs to run genuine hyperparameter optimization in parallel.
Outputs:
  - data/optuna_best_params.json
  - data/optuna_sensitivity_table.csv
  - data/optuna_sensitivity.csv
  - data/optuna/all_best_params.json
  - data/optuna/best_params_<ModelName>.csv
"""

import os
import sys
import csv
import json
import time
import optuna
import numpy as np
import traceback
import multiprocessing as mp

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM
from run_optuna_all_baselines import MODEL_CONFIGS

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
OPTUNA_DIR = os.path.join(DATA_DIR, "optuna")
os.makedirs(OPTUNA_DIR, exist_ok=True)

# Non-RL Baselines
NON_RL_MODELS = {
    "ReactDCC": {
        "arch": "ETSI TS 102 687 Reactive DCC",
        "params_str": "Fixed Look-up Table (Interval 100ms-1000ms based on CBR thresholds)"
    },
    "AdaptDCC": {
        "arch": "ETSI TS 102 687 Adaptive DCC",
        "params_str": "Linear rate adaptation (Target CBR=0.60, delta_T=50ms)"
    },
    "Fixed 10Hz": {
        "arch": "Standard Constant Rate",
        "params_str": "Generation Interval = 100ms (Fixed 10 Hz CAM beaconing)"
    }
}


def optimize_single_model(model_name, gpu_id, n_trials, train_episodes, eval_episodes, duration_steps, result_queue):
    """Worker function to optimize a single model on a designated GPU."""
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        config = MODEL_CONFIGS[model_name]
        hook_name = config["hook_name"]
        factory = config["factory"]

        def objective(trial):
            try:
                agent = factory(trial)
                hook = get_hook(hook_name)
                hook.set_agent(agent)

                # --- TRAINING PHASE ---
                hook.is_training = True
                for ep in range(train_episodes):
                    hook.reset_episode()
                    runner = SimulationRunner(
                        scenario="urban_grid",
                        n_vehicles=10,
                        seed=42 + ep + trial.number * 10,
                        method=hook_name,
                        method_params={},
                        duration_steps=duration_steps
                    )
                    runner.run()

                    # Perform updates
                    if hasattr(agent, 'memory'):
                        batch_size = getattr(agent, 'batch_size', 64)
                        num_updates = max(1, len(agent.memory) // batch_size)
                        for _ in range(num_updates):
                            if hasattr(agent, 'train_step'):
                                agent.train_step()
                            if hasattr(agent, 'update_epsilon'):
                                agent.update_epsilon()

                        if hasattr(agent, 'update_target_network'):
                            freq = getattr(agent, 'target_update_freq', 1)
                            if (ep + 1) % freq == 0:
                                agent.update_target_network()

                # --- EVALUATION PHASE ---
                hook.is_training = False
                eval_rewards = []
                for ep in range(eval_episodes):
                    hook.reset_episode()
                    runner = SimulationRunner(
                        scenario="urban_grid",
                        n_vehicles=15,
                        seed=100 + ep + trial.number * 10,
                        method=hook_name,
                        method_params={},
                        duration_steps=duration_steps
                    )
                    runner.run()
                    eval_rewards.append(hook.episode_reward)

                return float(np.mean(eval_rewards))

            except Exception as e:
                print(f"[{model_name} | GPU {gpu_id}] Trial {trial.number} failed: {e}")
                traceback.print_exc()
                raise optuna.exceptions.TrialPruned()

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        sampler = optuna.samplers.TPESampler(seed=42)
        pruner = optuna.pruners.MedianPruner(n_startup_trials=3, n_warmup_steps=1)

        study = optuna.create_study(
            direction="maximize",
            study_name=f"optuna_{model_name}",
            sampler=sampler,
            pruner=pruner
        )

        print(f"==> [{model_name}] Started optimization on GPU {gpu_id} ({n_trials} trials)...")
        study.optimize(objective, n_trials=n_trials)
        print(f"<== [{model_name}] Finished! Best Reward: {study.best_value:.2f}")

        # Save individual CSV
        csv_path = os.path.join(OPTUNA_DIR, f"best_params_{model_name}.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Parameter", "Value"])
            for k, v in study.best_params.items():
                writer.writerow([k, v])

        # Evaluate final best agent to collect genuine metrics (PDR, AoI, CBR, Reward)
        best_trial = study.best_trial
        best_agent = factory(best_trial)
        hook = get_hook(hook_name)
        hook.set_agent(best_agent)
        hook.is_training = False
        hook.reset_episode()

        eval_runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=15,
            seed=2026,
            method=hook_name,
            method_params={},
            duration_steps=300
        )
        metrics = eval_runner.run()
        eval_reward = hook.episode_reward

        result = {
            "model_name": model_name,
            "arch": config["arch"],
            "best_params": study.best_params,
            "best_value": study.best_value,
            "eval_reward": eval_reward,
            "pdr_mean": metrics.get("PDR_mean", 0.0),
            "aoi_mean": metrics.get("AoI_mean", 0.0),
            "cbr_mean": metrics.get("CBR_mean", 0.0),
            "energy_efficiency": metrics.get("energy_efficiency", 0.0)
        }
        result_queue.put((model_name, True, result))

    except Exception as e:
        print(f"Worker for {model_name} failed: {e}")
        traceback.print_exc()
        result_queue.put((model_name, False, str(e)))


def evaluate_non_rl_models():
    """Evaluate non-RL models to obtain genuine comparison metrics."""
    results = {}
    for name, info in NON_RL_MODELS.items():
        print(f"Evaluating non-RL baseline: {name}...")
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=15,
            seed=2026,
            method=name,
            method_params={},
            duration_steps=300
        )
        metrics = runner.run()
        hook = get_hook(name)
        reward = getattr(hook, "episode_reward", -900000.0)
        results[name] = {
            "model_name": name,
            "arch": info["arch"],
            "params_str": info["params_str"],
            "eval_reward": reward,
            "pdr_mean": metrics.get("PDR_mean", 0.0),
            "aoi_mean": metrics.get("AoI_mean", 0.0),
            "cbr_mean": metrics.get("CBR_mean", 0.0),
            "energy_efficiency": metrics.get("energy_efficiency", 0.0)
        }
    return results


def format_params_str(params_dict):
    """Format dictionary of parameters into concise string."""
    items = []
    for k, v in params_dict.items():
        if isinstance(v, float):
            if v < 1e-3 or v > 1e4:
                items.append(f"{k}={v:.1e}")
            else:
                items.append(f"{k}={v:.4g}")
        else:
            items.append(f"{k}={v}")
    return ", ".join(items)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Parallel Optuna Hyperparameter Optimization across 4 GPUs.")
    parser.add_argument("--n_trials", type=int, default=15, help="Number of trials per model")
    parser.add_argument("--train_episodes", type=int, default=2, help="Train episodes per trial")
    parser.add_argument("--eval_episodes", type=int, default=1, help="Eval episodes per trial")
    parser.add_argument("--duration_steps", type=int, default=200, help="Steps per episode")
    parser.add_argument("--num_gpus", type=int, default=4, help="Number of GPUs to utilize")
    args = parser.parse_args()

    mp.set_start_method("spawn", force=True)

    all_models = list(MODEL_CONFIGS.keys())
    print(f"Starting Parallel Optuna Tuning for {len(all_models)} RL Models on {args.num_gpus} GPUs...")
    print(f"Models: {all_models}")

    result_queue = mp.Queue()
    active_processes = []
    model_idx = 0
    results_map = {}

    start_time = time.time()

    # Launch initial batch up to num_gpus
    while model_idx < len(all_models) and len(active_processes) < args.num_gpus:
        m_name = all_models[model_idx]
        gpu_id = len(active_processes) % args.num_gpus
        p = mp.Process(
            target=optimize_single_model,
            args=(m_name, gpu_id, args.n_trials, args.train_episodes, args.eval_episodes, args.duration_steps, result_queue)
        )
        p.start()
        active_processes.append((m_name, gpu_id, p))
        model_idx += 1

    # Monitor and spawn remaining models
    while active_processes:
        time.sleep(0.5)
        # Check queue
        while not result_queue.empty():
            m_name, success, payload = result_queue.get()
            if success:
                results_map[m_name] = payload
                print(f" [SUCCESS] Result collected for {m_name}")
            else:
                print(f" [ERROR] Optimization failed for {m_name}: {payload}")

        # Check for finished processes
        remaining_procs = []
        for m_name, gpu_id, p in active_processes:
            if p.is_alive():
                remaining_procs.append((m_name, gpu_id, p))
            else:
                p.join()
                print(f"Process for {m_name} on GPU {gpu_id} terminated.")
                # If there are still models left, launch next one on this freed GPU
                if model_idx < len(all_models):
                    next_model = all_models[model_idx]
                    next_p = mp.Process(
                        target=optimize_single_model,
                        args=(next_model, gpu_id, args.n_trials, args.train_episodes, args.eval_episodes, args.duration_steps, result_queue)
                    )
                    next_p.start()
                    remaining_procs.append((next_model, gpu_id, next_p))
                    model_idx += 1

        active_processes = remaining_procs

    # Drain queue
    while not result_queue.empty():
        m_name, success, payload = result_queue.get()
        if success:
            results_map[m_name] = payload

    total_time = time.time() - start_time
    print(f"\nAll {len(results_map)} RL models optimized in {total_time:.1f} seconds!")

    # Evaluate non-RL baselines
    print("\n--- Evaluating Non-RL Baselines ---")
    non_rl_results = evaluate_non_rl_models()

    # Construct unified best_params JSON
    best_params_json = {}
    for m_name, res in results_map.items():
        best_params_json[m_name] = res["best_params"]

    # Save to data/optuna_best_params.json and data/optuna/all_best_params.json
    out_json_path1 = os.path.join(DATA_DIR, "optuna_best_params.json")
    out_json_path2 = os.path.join(OPTUNA_DIR, "all_best_params.json")
    for pth in [out_json_path1, out_json_path2]:
        with open(pth, 'w') as f:
            json.dump(best_params_json, f, indent=4)
        print(f"Saved: {pth}")

    # Build Sensitivity Table
    # Order: REMO-DQN first, then other DRLs, then Tabular, then Non-RL
    table_order = [
        "REMO-DQN", "MoEDQN", "MAPPO", "PPO", "SAC", "DDPG", "TD3",
        "DuelingDQN", "DoubleDQN", "VanillaDQN", "QLearning", "SARSA",
        "ActorCritic", "DecisionTransformer", "ReactDCC", "AdaptDCC", "Fixed 10Hz"
    ]

    sensitivity_rows = []
    for name in table_order:
        if name == "REMO-DQN":
            display_name = "REMO-DQN (Proposed)"
            res = results_map.get("REMO-DQN")
            arch = res["arch"] if res else "ResNet + MoE + Dueling DQN"
            params_str = format_params_str(res["best_params"]) if res else ""
            reward = res["eval_reward"] if res else 0.0
            pdr = res["pdr_mean"] if res else 0.0
            aoi = res["aoi_mean"] if res else 0.0
            cbr = res["cbr_mean"] if res else 0.0
        elif name in results_map:
            display_name = name
            res = results_map[name]
            arch = res["arch"]
            params_str = format_params_str(res["best_params"])
            reward = res["eval_reward"]
            pdr = res["pdr_mean"] if res else 0.0
            aoi = res["aoi_mean"] if res else 0.0
            cbr = res["cbr_mean"] if res else 0.0
        elif name in non_rl_results:
            display_name = name
            res = non_rl_results[name]
            arch = res["arch"]
            params_str = res["params_str"]
            reward = res["eval_reward"]
            pdr = res["pdr_mean"]
            aoi = res["aoi_mean"]
            cbr = res["cbr_mean"]
        else:
            continue

        sensitivity_rows.append({
            "Method": display_name,
            "Architecture": arch,
            "Tuned Hyperparameters": params_str,
            "Reward Convergence": f"{reward:.1f}",
            "Mean PDR (%)": f"{pdr:.2f}",
            "Mean AoI (ms)": f"{aoi:.2f}",
            "Mean CBR": f"{cbr:.3f}"
        })

    # Save to data/optuna_sensitivity_table.csv and data/optuna_sensitivity.csv
    table_csv_path1 = os.path.join(DATA_DIR, "optuna_sensitivity_table.csv")
    table_csv_path2 = os.path.join(DATA_DIR, "optuna_sensitivity.csv")
    fieldnames = ["Method", "Architecture", "Tuned Hyperparameters", "Reward Convergence", "Mean PDR (%)", "Mean AoI (ms)", "Mean CBR"]

    for pth in [table_csv_path1, table_csv_path2]:
        with open(pth, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in sensitivity_rows:
                writer.writerow(r)
        print(f"Saved: {pth}")

    print("\nOptuna Hyperparameter Re-Optimization Pipeline Completed Successfully!")


if __name__ == "__main__":
    main()
