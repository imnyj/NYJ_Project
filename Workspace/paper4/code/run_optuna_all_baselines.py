#!/usr/bin/env python3
"""
run_optuna_all_baselines.py
===========================
Optuna Hyperparameter Optimization Suite for 14 RL Models in Paper4.
Ensures standard ACTION_DIM=24 and supports single-model or multi-model tuning.
"""

import os
import csv
import json
import optuna
import numpy as np
import traceback
import sys
import argparse
import torch

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM

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

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
OUTPUT_DIR = os.environ.get("OPTUNA_DIR", os.path.join(DATA_DIR, "optuna"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_CONFIGS = {
    "REMO-DQN": {
        "hook_name": "REMO-DQN",
        "arch": "ResNet + MoE + Dueling DQN",
        "factory": lambda t: ResNetMoEAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            num_experts=t.suggest_int("num_experts", 2, 4),
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5])
        )
    },
    "MoEDQN": {
        "hook_name": "MoEDQN",
        "arch": "MoE + Standard DQN",
        "factory": lambda t: MoEAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            num_experts=t.suggest_int("num_experts", 2, 4),
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5])
        )
    },
    "DuelingDQN": {
        "hook_name": "DuelingDQN",
        "arch": "Dueling Deep Q-Network",
        "factory": lambda t: DuelingDQNAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5])
        )
    },
    "DoubleDQN": {
        "hook_name": "DoubleDQN",
        "arch": "Double Deep Q-Network",
        "factory": lambda t: DDQNAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5])
        )
    },
    "VanillaDQN": {
        "hook_name": "VanillaDQN",
        "arch": "Standard DQN (Mnih et al.)",
        "factory": lambda t: DQNAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5])
        )
    },
    "PPO": {
        "hook_name": "PPO",
        "arch": "Proximal Policy Optimization",
        "factory": lambda t: PPOAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            eps_clip=t.suggest_float("eps_clip", 0.1, 0.3),
            k_epochs=t.suggest_int("k_epochs", 3, 10),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000])
        )
    },
    "MAPPO": {
        "hook_name": "MAPPO",
        "arch": "Multi-Agent PPO",
        "factory": lambda t: MAPPOAgent(
            local_state_dim=5,
            global_state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            eps_clip=t.suggest_float("eps_clip", 0.1, 0.3),
            k_epochs=t.suggest_int("k_epochs", 3, 10),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000])
        )
    },
    "SAC": {
        "hook_name": "SAC",
        "arch": "Soft Actor-Critic",
        "factory": lambda t: SACAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            tau=t.suggest_float("tau", 0.001, 0.01),
            alpha=t.suggest_float("alpha", 0.05, 0.5),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000])
        )
    },
    "DDPG": {
        "hook_name": "DDPG",
        "arch": "Deep Deterministic Policy Gradient",
        "factory": lambda t: DDPGAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr_actor=t.suggest_float("lr_actor", 1e-5, 1e-2, log=True),
            lr_critic=t.suggest_float("lr_critic", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            tau=t.suggest_float("tau", 0.001, 0.01),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000])
        )
    },
    "TD3": {
        "hook_name": "TD3",
        "arch": "Twin Delayed DDPG",
        "factory": lambda t: TD3Agent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            tau=t.suggest_float("tau", 0.001, 0.01),
            policy_delay=t.suggest_int("policy_delay", 1, 3),
            target_noise=t.suggest_float("target_noise", 0.1, 0.3),
            noise_clip=t.suggest_float("noise_clip", 0.3, 0.7),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000])
        )
    },
    "ActorCritic": {
        "hook_name": "ActorCritic",
        "arch": "Advantage Actor-Critic (A2C)",
        "factory": lambda t: ActorCriticAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000])
        )
    },
    "DecisionTransformer": {
        "hook_name": "DecisionTransformer",
        "arch": "Transformer-based Sequence RL",
        "factory": lambda t: DTAgent(
            state_dim=5,
            action_dim=ACTION_DIM,
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000])
        )
    },
    "QLearning": {
        "hook_name": "QLearning",
        "arch": "Tabular Q-Learning",
        "factory": lambda t: QLearningAgent(
            state_bins=[10, 10, 10, 10, 10],
            action_dim=ACTION_DIM,
            alpha=t.suggest_float("alpha", 0.01, 0.5),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            epsilon_decay=t.suggest_float("epsilon_decay", 0.90, 0.999)
        )
    },
    "SARSA": {
        "hook_name": "SARSA",
        "arch": "State-Action-Reward-State-Action",
        "factory": lambda t: SARSAAgent(
            state_bins=[10, 10, 10, 10, 10],
            action_dim=ACTION_DIM,
            alpha=t.suggest_float("alpha", 0.01, 0.5),
            gamma=t.suggest_float("gamma", 0.90, 0.999),
            epsilon_decay=t.suggest_float("epsilon_decay", 0.90, 0.999)
        )
    }
}


def run_optimization(method_name, n_trials=15, train_episodes=2, eval_episodes=1, duration_steps=200, output_dir=OUTPUT_DIR):
    config = MODEL_CONFIGS[method_name]
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
                metrics = runner.run()
                eval_rewards.append(hook.episode_reward)
                
            return float(np.mean(eval_rewards))
            
        except Exception as e:
            print(f"[{method_name}] Error in trial {trial.number}: {e}")
            traceback.print_exc()
            raise optuna.exceptions.TrialPruned()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=42)
    pruner = optuna.pruners.MedianPruner(n_startup_trials=3, n_warmup_steps=1)
    
    study = optuna.create_study(
        direction="maximize",
        study_name=f"optuna_{method_name}",
        sampler=sampler,
        pruner=pruner
    )
    
    print(f"[{method_name}] Starting optimization ({n_trials} trials)...")
    study.optimize(objective, n_trials=n_trials)
    
    print(f"[{method_name}] Optimization complete! Best Reward: {study.best_value:.2f}")
    print(f"[{method_name}] Best params:", study.best_params)
    
    # Save CSV
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"best_params_{method_name}.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Value"])
        for k, v in study.best_params.items():
            writer.writerow([k, v])
            
    return study.best_params, study.best_value


def main():
    parser = argparse.ArgumentParser(description="Run Optuna optimization for RL models.")
    parser.add_argument("--model", type=str, default="all", help="Model name or 'all'")
    parser.add_argument("--n_trials", type=int, default=15, help="Number of Optuna trials")
    parser.add_argument("--train_episodes", type=int, default=2, help="Train episodes per trial")
    parser.add_argument("--eval_episodes", type=int, default=1, help="Eval episodes per trial")
    parser.add_argument("--duration_steps", type=int, default=200, help="Duration steps per episode")
    parser.add_argument("--gpu_id", type=int, default=None, help="CUDA device index")
    parser.add_argument("--output_dir", type=str, default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    if args.gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_id)

    if args.model == "all":
        target_models = list(MODEL_CONFIGS.keys())
    elif args.model in MODEL_CONFIGS:
        target_models = [args.model]
    else:
        raise ValueError(f"Unknown model: {args.model}. Available: {list(MODEL_CONFIGS.keys())}")

    all_best_params = {}
    for name in target_models:
        print(f"\n==========================================")
        print(f" Optimizing {name}")
        print(f"==========================================")
        best_p, best_val = run_optimization(
            name,
            n_trials=args.n_trials,
            train_episodes=args.train_episodes,
            eval_episodes=args.eval_episodes,
            duration_steps=args.duration_steps,
            output_dir=args.output_dir
        )
        all_best_params[name] = best_p

    # Save summary JSON
    json_path = os.path.join(args.output_dir, "all_best_params.json")
    with open(json_path, 'w') as f:
        json.dump(all_best_params, f, indent=4)
    print(f"\nAll best parameters saved to {json_path}")


if __name__ == "__main__":
    main()
