"""
evaluator.py
============
Evaluation loop for MAFAC simulation.
Runs learned policies in the environment and collects metrics.

CHANGES from original:
  - evaluate_agents(): handle empty obs dict when no vehicles are present
  - evaluate_agents(): handle empty rewards dict gracefully
  - evaluate_agents(): skip action selection for vehicles not in agents dict,
    fall back to random action, guarded against empty obs
  - Added defensive check: if all_metrics is empty, return zero-filled dict
"""

import sys
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE))

from env.sumo_env import SUMOEnv
from utils.metrics import EpisodeMetrics
from utils.logger import ExperimentLogger


class Evaluator:
    """
    Evaluates trained agents over multiple episodes.
    Collects all metrics required for CSV output.
    """

    def __init__(
        self,
        env_config: dict = None,
        output_dir: str = "home/nyj/0_paper/paper/data",
        seed: int = 42,
        verbose: bool = True,
    ):
        self.env_config = env_config or {}
        self.output_dir = Path(output_dir)
        self.seed       = seed
        self.verbose    = verbose
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = ExperimentLogger(str(self.output_dir))

    def evaluate_agents(
        self,
        agents: Dict[str, Any],
        algorithm: str,
        num_eval_episodes: int = 5,
        env_config: dict = None,
    ) -> dict:
        """
        Evaluate a set of agents over num_eval_episodes.
        Returns averaged metric dict.

        CHANGED:
          - Handles empty obs dict gracefully (no vehicles after warmup)
          - Handles empty rewards dict when computing mean reward
          - Skips agent action selection when obs is empty
          - Defensive fallback if all_metrics ends up empty
        """
        cfg = env_config or self.env_config
        env = SUMOEnv(seed=self.seed, **cfg)

        all_metrics = []
        for ep_i in range(num_eval_episodes):
            obs = env.reset()
            ep_metrics = EpisodeMetrics()
            step_count = 0
            ep_dur = cfg.get("episode_duration_s", 300.0)
            max_steps = int(ep_dur / 0.1)

            # If no vehicles present after reset, skip episode
            if not obs:
                if self.verbose:
                    print(f"[Evaluator] Episode {ep_i+1}: No vehicles after reset, skipping.")
                final = ep_metrics.finalize(ep_dur)
                all_metrics.append(final)
                continue

            while step_count < max_steps:
                # Build action dict - only for vehicles with observations
                actions = {}
                if obs:  # guard against empty obs
                    for vid, obs_vec in obs.items():
                        if vid in agents:
                            actions[vid] = agents[vid].select_action(
                                obs_vec, deterministic=True)
                        else:
                            # Random action for new/unknown vehicles
                            import random as _random
                            actions[vid] = np.array(
                                [_random.randint(0, d-1) for d in env.action_dims],
                                dtype=np.int32)

                try:
                    next_obs, rewards, dones, truncated, info = env.step(actions)
                except Exception as e:
                    if self.verbose:
                        print(f"[Evaluator] env.step error at step {step_count}: {e}")
                    break

                ep_metrics.update(info, rewards)
                obs = next_obs
                step_count += 1
                if truncated:
                    break

            final = ep_metrics.finalize(ep_dur)
            all_metrics.append(final)

        env.close()

        # Guard against all episodes being empty
        if not all_metrics:
            if self.verbose:
                print("[Evaluator] WARNING: No valid episodes collected.")
            return {}

        # Average over episodes
        averaged = {}
        for key in all_metrics[0]:
            try:
                vals = [m[key] for m in all_metrics if key in m]
                if vals:
                    averaged[key] = float(np.mean(vals))
                    averaged[f"{key}_std"] = float(np.std(vals))
                else:
                    averaged[key] = 0.0
                    averaged[f"{key}_std"] = 0.0
            except (TypeError, ValueError):
                averaged[key] = 0.0
                averaged[f"{key}_std"] = 0.0

        return averaged

    def run_scenario_evaluation(
        self,
        scenario_id: str,
        param_name: str,
        param_values: List,
        algorithms_agents: Dict[str, Dict],
        fixed_params: dict = None,
        num_eval_episodes: int = 3,
    ) -> dict:
        """
        Run evaluation across parameter sweep for a scenario.
        Returns nested dict: {param_val: {algorithm: metrics}}.
        """
        results = {}
        fixed = fixed_params or {}

        for pval in param_values:
            results[pval] = {}
            print(f"[Evaluator] Scenario {scenario_id}: {param_name}={pval}")

            env_cfg = dict(self.env_config)
            env_cfg.update(fixed)
            env_cfg[param_name] = pval

            for alg_name, agents in algorithms_agents.items():
                print(f"  [Evaluator] Algorithm: {alg_name}")
                metrics = self.evaluate_agents(
                    agents, alg_name, num_eval_episodes, env_cfg)
                results[pval][alg_name] = metrics

                filename = f"{scenario_id}_{param_name.replace('_', '')}"
                for metric_key in ["average_aoi", "peak_aoi", "cache_hit_ratio",
                                   "tx_success_rate", "throughput_mbps",
                                   "constraint_violation"]:
                    fn = f"{scenario_id}_{metric_key}"
                    self.logger.log_scenario(
                        fn, param_name, pval, alg_name,
                        {k: metrics.get(k, 0.0) for k in [metric_key]})

        return results

    def save_scenario_csv(
        self,
        scenario_id: str,
        results: dict,
        param_name: str,
        metric_name: str,
    ):
        """
        Save results to proper CSV format matching experiment_spec output files.
        Format: rows=param_values, columns=algorithms.
        """
        algorithms = ["MAFAC", "Centralized-AoI", "SAC-Single",
                      "IQL", "NDN-LRU", "No-Cache"]
        param_vals = sorted(results.keys())
        filename = f"{scenario_id}_{metric_name}"
        fields = [param_name] + algorithms
        lg = self.logger.get_logger(filename, fields)

        for pval in param_vals:
            row = {param_name: pval}
            for alg in algorithms:
                m = results.get(pval, {}).get(alg, {})
                row[alg] = m.get(metric_name, 0.0) if m else 0.0
            lg.log(row)

    def close(self):
        self.logger.close_all()
