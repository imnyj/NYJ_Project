#!/usr/bin/env python3
"""
run_scenario.py
===============
Run evaluation for a single scenario + algorithm combination.

Usage:
  python run_scenario.py --scenario S1 --algorithm MAFAC
  python run_scenario.py --scenario S2 --algorithm IQL --num-eval 5
  python run_scenario.py --scenario S3 --algorithm No-Cache
"""

import sys
import argparse
import random
import numpy as np
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from env.sumo_env import SUMOEnv
from training.trainer import make_agent, Trainer
from training.evaluator import Evaluator

# ─────────────────────────────────────────────────────────────────────────────
# Scenario definitions (from experiment_spec.json)
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS = {
    "S1": {
        "name": "vehicle_density_variation",
        "prefix": "density",
        "param_name": "num_vehicles",
        "param_values": [20, 50, 100],
        "fixed_params": {
            "cache_size": 50, "rician_K_db": 7.0,
            "num_contents": 200, "zipf_alpha": 1.0,
            "content_update_rate": 0.5,
        },
        "metrics": ["average_aoi", "peak_aoi", "cache_hit_ratio",
                    "tx_success_rate", "throughput_mbps", "constraint_violation"],
    },
    "S2": {
        "name": "cache_size_sensitivity",
        "prefix": "cache",
        "param_name": "cache_size",
        "param_values": [10, 20, 30, 50, 70, 100],
        "fixed_params": {
            "num_vehicles": 50, "rician_K_db": 7.0,
            "num_contents": 200, "zipf_alpha": 1.0,
            "content_update_rate": 0.5,
        },
        "metrics": ["average_aoi", "peak_aoi", "cache_hit_ratio", "tx_success_rate"],
    },
    "S3": {
        "name": "channel_quality_variation",
        "prefix": "channel",
        "param_name": "rician_K_db",
        "param_values": [3.0, 5.0, 7.0, 10.0],
        "fixed_params": {
            "num_vehicles": 50, "cache_size": 50,
            "num_contents": 200, "zipf_alpha": 1.0,
            "content_update_rate": 0.5,
        },
        "metrics": ["average_aoi", "peak_aoi", "tx_success_rate", "throughput_mbps"],
    },
    "S4": {
        "name": "zipf_exponent_sensitivity",
        "prefix": "zipf",
        "param_name": "zipf_alpha",
        "param_values": [0.8, 1.0, 1.2],
        "fixed_params": {
            "num_vehicles": 50, "cache_size": 50,
            "rician_K_db": 7.0, "num_contents": 200,
            "content_update_rate": 0.5,
        },
        "metrics": ["average_aoi", "cache_hit_ratio"],
    },
}

ALGORITHMS = ["MAFAC", "Centralized-AoI", "SAC-Single", "IQL", "NDN-LRU", "No-Cache"]


def run_scenario(scenario_id: str, algorithm: str,
                 training_episodes: int = 100,
                 num_eval_episodes: int = 3,
                 output_dir: str = "home/nyj/0_paper/paper/data",
                 seed: int = 42,
                 verbose: bool = True):
    """Run one scenario for one algorithm."""

    scen = SCENARIOS[scenario_id]
    param_name   = scen["param_name"]
    param_values = scen["param_values"]
    fixed_params = scen["fixed_params"]

    print(f"[run_scenario] Scenario {scenario_id} ({scen['name']}) | Algorithm: {algorithm}")
    print(f"  Sweeping {param_name} over {param_values}")

    results = {}

    for pval in param_values:
        print(f"\n  {param_name} = {pval}")

        # Build env config for this parameter value
        env_cfg = dict(fixed_params)
        env_cfg[param_name] = pval
        env_cfg["episode_duration_s"] = 300.0
        env_cfg["headless"] = True

        # Train agent
        if algorithm.lower() not in ("ndn-lru", "ndnlru", "no-cache", "nocache"):
            trainer = Trainer(
                algorithm=algorithm,
                env_config=env_cfg,
                total_episodes=training_episodes,
                output_dir=output_dir,
                seed=seed,
                verbose=False,
            )
            metrics_hist = trainer.train()
            trained_agents = trainer.agents
        else:
            # Heuristic: no training needed
            trained_agents = {}

        # Evaluate
        evaluator = Evaluator(env_config=env_cfg, output_dir=output_dir, seed=seed)

        # If no trained agents, create fresh heuristic agents
        if not trained_agents:
            env = SUMOEnv(seed=seed, **env_cfg)
            obs = env.reset()
            for vid in env.vehicle_ids:
                trained_agents[vid] = make_agent(
                    algorithm, vid, env.obs_dim, env.action_dims, seed=seed)
            env.close()

        ep_metrics = evaluator.evaluate_agents(
            trained_agents, algorithm, num_eval_episodes, env_cfg)
        results[pval] = ep_metrics

        # Log to CSV
        for metric_name in scen["metrics"]:
            # Map to CSV filename
            prefix = scen["prefix"]
            metric_map = {
                "average_aoi":       f"{scenario_id}_{prefix}_average_aoi",
                "peak_aoi":          f"{scenario_id}_{prefix}_peak_aoi",
                "cache_hit_ratio":   f"{scenario_id}_{prefix}_cache_hit_ratio",
                "tx_success_rate":   f"{scenario_id}_{prefix}_tx_success_rate",
                "throughput_mbps":   f"{scenario_id}_{prefix}_throughput",
                "constraint_violation": f"{scenario_id}_{prefix}_constraint_violation",
            }
            fn = metric_map.get(metric_name, f"{scenario_id}_{metric_name}")
            evaluator.logger.log_scenario(
                fn, param_name, pval, algorithm,
                {metric_name: ep_metrics.get(metric_name, 0.0)})

        evaluator.close()

        if verbose:
            print(f"    AoI={ep_metrics.get('average_aoi', 0):.3f}s "
                  f"CHR={ep_metrics.get('cache_hit_ratio', 0):.3f} "
                  f"TSR={ep_metrics.get('tx_success_rate', 0):.3f}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run individual scenario")
    parser.add_argument("--scenario",   type=str, default="S1",
                        choices=list(SCENARIOS.keys()))
    parser.add_argument("--algorithm",  type=str, default="MAFAC",
                        choices=ALGORITHMS)
    parser.add_argument("--train-episodes", type=int, default=100)
    parser.add_argument("--num-eval",   type=int, default=3)
    parser.add_argument("--output-dir", type=str,
                        default="home/nyj/0_paper/paper/data")
    parser.add_argument("--seed",       type=int, default=42)
    parser.add_argument("--verbose",    action="store_true", default=True)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    results = run_scenario(
        args.scenario, args.algorithm,
        training_episodes=args.train_episodes,
        num_eval_episodes=args.num_eval,
        output_dir=args.output_dir,
        seed=args.seed,
        verbose=args.verbose,
    )

    print(f"\nScenario {args.scenario} | {args.algorithm} complete.")
    for pval, m in results.items():
        print(f"  {args.scenario} param={pval}: "
              f"AoI={m.get('average_aoi', 0):.3f}s, "
              f"CHR={m.get('cache_hit_ratio', 0):.3f}")


if __name__ == "__main__":
    main()
