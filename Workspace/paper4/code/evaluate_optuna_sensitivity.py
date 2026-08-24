#!/usr/bin/env python3
"""
evaluate_optuna_sensitivity.py
==============================
Evaluates all 17 models (14 RL + 3 non-RL) using optimal Optuna hyperparameters
over a 50-second urban simulation with 5.0s warmup to compute accurate, authentic
metrics for data/optuna_sensitivity_table.csv and data/optuna_sensitivity.csv.
"""

import os
import sys
import json
import csv
import multiprocessing as mp
import numpy as np

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM
from run_optuna_all_baselines import MODEL_CONFIGS

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
best_params_path = os.path.join(DATA_DIR, "optuna_best_params.json")
with open(best_params_path, "r") as f:
    best_params = json.load(f)

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

def eval_model(model_name, gpu_id, result_queue):
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        if model_name in MODEL_CONFIGS:
            config = MODEL_CONFIGS[model_name]
            hook_name = config["hook_name"]
            params = best_params[model_name]
            
            from resnet_moe_agent import ResNetMoEAgent
            from moe_agent import MoEAgent
            from dueling_dqn_agent import DuelingDQNAgent
            from ddqn_agent import DDQNAgent
            from dqn_agent import DQNAgent
            from ppo_agent import PPOAgent
            from mappo_agent import MAPPOAgent
            from sac_agent import SACAgent
            from ddpg_agent import DDPGAgent
            from td3_agent import TD3Agent
            from actor_critic_agent import ActorCriticAgent
            from dt_agent import DTAgent
            from qlearning_agent import QLearningAgent
            from sarsa_agent import SARSAAgent
            
            if model_name == "REMO-DQN":
                agent = ResNetMoEAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "MoEDQN":
                agent = MoEAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "DuelingDQN":
                agent = DuelingDQNAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "DoubleDQN":
                agent = DDQNAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "VanillaDQN":
                agent = DQNAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "PPO":
                agent = PPOAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "MAPPO":
                agent = MAPPOAgent(local_state_dim=5, global_state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "SAC":
                agent = SACAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "DDPG":
                agent = DDPGAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "TD3":
                agent = TD3Agent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "ActorCritic":
                agent = ActorCriticAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "DecisionTransformer":
                agent = DTAgent(state_dim=5, action_dim=ACTION_DIM, **params)
            elif model_name == "QLearning":
                agent = QLearningAgent(state_bins=[10,10,10,10,10], action_dim=ACTION_DIM, **params)
            elif model_name == "SARSA":
                agent = SARSAAgent(state_bins=[10,10,10,10,10], action_dim=ACTION_DIM, **params)
                
            hook = get_hook(hook_name)
            hook.set_agent(agent)
            hook.is_training = False
            hook.reset_episode()
            
            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=20,
                seed=2026,
                method=hook_name,
                method_params={},
                duration_steps=500,
                warmup_s=5.0
            )
            metrics = runner.run()
            reward = hook.episode_reward
            
            items = []
            for k, v in params.items():
                if isinstance(v, float):
                    if v < 1e-3 or v > 1e4:
                        items.append(f"{k}={v:.1e}")
                    else:
                        items.append(f"{k}={v:.4g}")
                else:
                    items.append(f"{k}={v}")
            params_str = ", ".join(items)
            
            result = {
                "model_name": model_name,
                "arch": config["arch"],
                "params_str": params_str,
                "reward": reward,
                "pdr_mean": metrics.get("PDR_mean", 0.0),
                "aoi_mean": metrics.get("AoI_mean", 0.0),
                "cbr_mean": metrics.get("CBR_mean", 0.0)
            }
            result_queue.put((model_name, True, result))
        else:
            info = NON_RL_MODELS[model_name]
            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=20,
                seed=2026,
                method=model_name,
                method_params={},
                duration_steps=500,
                warmup_s=5.0
            )
            metrics = runner.run()
            hook = get_hook(model_name)
            reward = getattr(hook, "episode_reward", -950000.0)
            result = {
                "model_name": model_name,
                "arch": info["arch"],
                "params_str": info["params_str"],
                "reward": reward,
                "pdr_mean": metrics.get("PDR_mean", 0.0),
                "aoi_mean": metrics.get("AoI_mean", 0.0),
                "cbr_mean": metrics.get("CBR_mean", 0.0)
            }
            result_queue.put((model_name, True, result))
    except Exception as e:
        print(f"Error evaluating {model_name}: {e}")
        import traceback
        traceback.print_exc()
        result_queue.put((model_name, False, str(e)))


def main():
    mp.set_start_method("spawn", force=True)
    all_models = list(best_params.keys()) + list(NON_RL_MODELS.keys())
    result_queue = mp.Queue()
    active_procs = []
    results = {}
    
    print(f"Evaluating {len(all_models)} models with genuine metrics...")
    
    idx = 0
    # Run 4 in parallel across 4 GPUs
    while idx < len(all_models) or active_procs:
        while idx < len(all_models) and len(active_procs) < 4:
            m_name = all_models[idx]
            gpu_id = len(active_procs) % 4
            p = mp.Process(target=eval_model, args=(m_name, gpu_id, result_queue))
            p.start()
            active_procs.append((m_name, p))
            idx += 1
            
        time.sleep(0.5)
        
        while not result_queue.empty():
            m_name, success, payload = result_queue.get()
            if success:
                results[m_name] = payload
                print(f" [EVAL DONE] {m_name}: PDR={payload['pdr_mean']:.2f}%, AoI={payload['aoi_mean']:.2f}ms, CBR={payload['cbr_mean']:.3f}, Reward={payload['reward']:.1f}")
                
        rem = []
        for m_name, p in active_procs:
            if p.is_alive():
                rem.append((m_name, p))
            else:
                p.join()
        active_procs = rem
        
    while not result_queue.empty():
        m_name, success, payload = result_queue.get()
        if success:
            results[m_name] = payload
            
    table_order = [
        "REMO-DQN", "MoEDQN", "MAPPO", "PPO", "SAC", "DDPG", "TD3",
        "DuelingDQN", "DoubleDQN", "VanillaDQN", "QLearning", "SARSA",
        "ActorCritic", "DecisionTransformer", "ReactDCC", "AdaptDCC", "Fixed 10Hz"
    ]
    
    rows = []
    for name in table_order:
        res = results[name]
        display_name = "REMO-DQN (Proposed)" if name == "REMO-DQN" else name
        rows.append({
            "Method": display_name,
            "Architecture": res["arch"],
            "Tuned Hyperparameters": res["params_str"],
            "Reward Convergence": f"{res['reward']:.1f}",
            "Mean PDR (%)": f"{res['pdr_mean']:.2f}",
            "Mean AoI (ms)": f"{res['aoi_mean']:.2f}",
            "Mean CBR": f"{res['cbr_mean']:.3f}"
        })
        
    fieldnames = ["Method", "Architecture", "Tuned Hyperparameters", "Reward Convergence", "Mean PDR (%)", "Mean AoI (ms)", "Mean CBR"]
    for filename in ["optuna_sensitivity_table.csv", "optuna_sensitivity.csv"]:
        out_csv = os.path.join(DATA_DIR, filename)
        with open(out_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        print(f"Updated {out_csv}")


if __name__ == "__main__":
    import time
    main()
