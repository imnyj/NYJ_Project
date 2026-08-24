#!/usr/bin/env python3
"""
train_all.py
============
Master Multi-GPU Parallel Retraining Pipeline for all 17 models in Paper4.

Models (17 total):
  14 RL Models:
    - REMO-DQN (Proposed ResNet + MoE + Dueling DQN)
    - MoEDQN
    - DuelingDQN
    - DoubleDQN
    - VanillaDQN
    - PPO
    - MAPPO
    - SAC
    - DDPG
    - TD3
    - ActorCritic
    - DecisionTransformer
    - QLearning
    - SARSA
  3 Non-RL Models:
    - Fixed 10Hz
    - ReactDCC
    - AdaptDCC

Features:
  - Genuine simulation & training (100 episodes x 2000 steps = 200,000 steps per model).
  - Pure negative penalty reward formulation R = r_CBR + r_AoI + r_cost (no manual offsets).
  - Best hyperparameters loaded directly from data/optuna_best_params.json.
  - Multi-GPU parallel distributed execution across 4x NVIDIA RTX 3090 GPUs.
  - Saves all 17 model checkpoints to data/models/<name>.pth or .pkl.
  - Saves 9-column convergence logs data/models/<name>_convergence.csv for each model.
  - Synthesizes 19-column unified data/reward_convergence.csv.
  - Performs comprehensive post-training validation on all 17 checkpoints and convergence files.
"""

import os
import sys
import csv
import json
import time
import random
import pickle
import traceback
import argparse
import numpy as np
import torch
import multiprocessing as mp

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook, CBR_TARGET, T_STALE
from etsi_cam_layer import ACTION_DIM

# Agent imports
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
MODELS_DIR = os.path.join(DATA_DIR, "models")
OPTUNA_FILE = os.path.join(DATA_DIR, "optuna_best_params.json")
REWARD_CONV_FILE = os.path.join(DATA_DIR, "reward_convergence.csv")

os.makedirs(MODELS_DIR, exist_ok=True)

CSV_HEADER = ['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean', 'Loss', 'Epsilon', 'Density']

# 14 RL Models (Display Name, Hook Name)
RL_MODELS = [
    ("REMO-DQN", "REMO-DQN"),
    ("MoEDQN", "MoEDQN"),
    ("DuelingDQN", "DuelingDQN"),
    ("DoubleDQN", "DoubleDQN"),
    ("VanillaDQN", "VanillaDQN"),
    ("PPO", "PPO"),
    ("MAPPO", "MAPPO"),
    ("SAC", "SAC"),
    ("DDPG", "DDPG"),
    ("TD3", "TD3"),
    ("ActorCritic", "ActorCritic"),
    ("DecisionTransformer", "DecisionTransformer"),
    ("QLearning", "QLearning"),
    ("SARSA", "SARSA")
]

# 3 Non-RL Models (Display Name, Hook Name)
NON_RL_MODELS = [
    ("Fixed 10Hz", "Fixed10Hz"),
    ("ReactDCC", "ReactDCC"),
    ("AdaptDCC", "AdaptDCC")
]

ALL_17_MODELS = RL_MODELS + NON_RL_MODELS

# Column order for data/reward_convergence.csv
CONVERGENCE_ORDER = [
    "REMO-DQN", "Fixed 10Hz", "ReactDCC", "AdaptDCC", "MoEDQN", "MAPPO", "PPO",
    "SAC", "DDPG", "TD3", "DuelingDQN", "DoubleDQN", "VanillaDQN", "QLearning",
    "SARSA", "ActorCritic", "DecisionTransformer"
]


def load_all_optuna_params():
    """Load best hyperparameters from data/optuna_best_params.json."""
    if os.path.exists(OPTUNA_FILE):
        with open(OPTUNA_FILE, 'r') as f:
            return json.load(f)
    optuna_alt = os.path.join(DATA_DIR, "optuna", "all_best_params.json")
    if os.path.exists(optuna_alt):
        with open(optuna_alt, 'r') as f:
            return json.load(f)
    print(f"[WARNING] Optuna best params file not found at {OPTUNA_FILE} or {optuna_alt}, using defaults.")
    return {}


def create_rl_agent(name: str, best_params: dict, epsilon_decay: float = 0.95):
    """Instantiate RL agent with optimal hyperparameters."""
    p = best_params.get(name, {})
    if name == "REMO-DQN":
        return ResNetMoEAgent(
            state_dim=5, action_dim=ACTION_DIM,
            num_experts=int(p.get("num_experts", 3)),
            hidden_dim=int(p.get("hidden_dim", 128)),
            lr=float(p.get("lr", 2.267e-3)),
            gamma=float(p.get("gamma", 0.9197)),
            batch_size=int(p.get("batch_size", 64)),
            buffer_size=int(p.get("buffer_size", 10000)),
            target_update_freq=int(p.get("target_update_freq", 2)),
            epsilon_decay=epsilon_decay
        )
    elif name == "MoEDQN":
        return MoEAgent(
            state_dim=5, action_dim=ACTION_DIM,
            num_experts=int(p.get("num_experts", 2)),
            lr=float(p.get("lr", 9.287e-4)),
            gamma=float(p.get("gamma", 0.9575)),
            batch_size=int(p.get("batch_size", 64)),
            buffer_size=int(p.get("buffer_size", 100000)),
            target_update_freq=int(p.get("target_update_freq", 1)),
            epsilon_decay=epsilon_decay
        )
    elif name == "DuelingDQN":
        return DuelingDQNAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 9.099e-4)),
            gamma=float(p.get("gamma", 0.9177)),
            batch_size=int(p.get("batch_size", 64)),
            buffer_size=int(p.get("buffer_size", 50000)),
            target_update_freq=int(p.get("target_update_freq", 1)),
            epsilon_decay=epsilon_decay
        )
    elif name in ["DoubleDQN", "DDQN"]:
        return DDQNAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 2.258e-4)),
            gamma=float(p.get("gamma", 0.9238)),
            batch_size=int(p.get("batch_size", 32)),
            buffer_size=int(p.get("buffer_size", 100000)),
            target_update_freq=int(p.get("target_update_freq", 2)),
            epsilon_decay=epsilon_decay
        )
    elif name in ["VanillaDQN", "DQN"]:
        return DQNAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 5.829e-3)),
            gamma=float(p.get("gamma", 0.9088)),
            batch_size=int(p.get("batch_size", 128)),
            buffer_size=int(p.get("buffer_size", 100000)),
            target_update_freq=int(p.get("target_update_freq", 5)),
            epsilon_decay=epsilon_decay
        )
    elif name == "PPO":
        return PPOAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 8.153e-3)),
            gamma=float(p.get("gamma", 0.9006)),
            eps_clip=float(p.get("eps_clip", 0.2135)),
            k_epochs=int(p.get("k_epochs", 8)),
            batch_size=int(p.get("batch_size", 64)),
            buffer_size=int(p.get("buffer_size", 100000))
        )
    elif name == "MAPPO":
        return MAPPOAgent(
            local_state_dim=5, global_state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 6.647e-4)),
            gamma=float(p.get("gamma", 0.9169)),
            eps_clip=float(p.get("eps_clip", 0.1130)),
            k_epochs=int(p.get("k_epochs", 10)),
            batch_size=int(p.get("batch_size", 32)),
            buffer_size=int(p.get("buffer_size", 50000))
        )
    elif name == "SAC":
        return SACAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 3.986e-3)),
            gamma=float(p.get("gamma", 0.9451)),
            tau=float(p.get("tau", 0.00994)),
            alpha=float(p.get("alpha", 0.2712)),
            batch_size=int(p.get("batch_size", 64)),
            buffer_size=int(p.get("buffer_size", 100000))
        )
    elif name == "DDPG":
        return DDPGAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr_actor=float(p.get("lr_actor", 6.647e-4)),
            lr_critic=float(p.get("lr_critic", 3.248e-5)),
            gamma=float(p.get("gamma", 0.9064)),
            tau=float(p.get("tau", 0.00954)),
            batch_size=int(p.get("batch_size", 32)),
            buffer_size=int(p.get("buffer_size", 50000))
        )
    elif name == "TD3":
        return TD3Agent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 2.227e-5)),
            gamma=float(p.get("gamma", 0.9327)),
            tau=float(p.get("tau", 0.00547)),
            policy_delay=int(p.get("policy_delay", 1)),
            target_noise=float(p.get("target_noise", 0.2004)),
            noise_clip=float(p.get("noise_clip", 0.4214)),
            batch_size=int(p.get("batch_size", 32)),
            buffer_size=int(p.get("buffer_size", 10000))
        )
    elif name == "ActorCritic":
        return ActorCriticAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 1.999e-3)),
            gamma=float(p.get("gamma", 0.9636)),
            batch_size=int(p.get("batch_size", 64)),
            buffer_size=int(p.get("buffer_size", 10000))
        )
    elif name == "DecisionTransformer":
        return DTAgent(
            state_dim=5, action_dim=ACTION_DIM,
            lr=float(p.get("lr", 1.568e-3)),
            gamma=float(p.get("gamma", 0.9298)),
            batch_size=int(p.get("batch_size", 32)),
            buffer_size=int(p.get("buffer_size", 100000))
        )
    elif name == "QLearning":
        return QLearningAgent(
            state_bins=[10, 10, 10, 10, 10], action_dim=ACTION_DIM,
            alpha=float(p.get("alpha", 0.01729)),
            gamma=float(p.get("gamma", 0.9803)),
            epsilon_decay=float(p.get("epsilon_decay", 0.9472))
        )
    elif name == "SARSA":
        return SARSAAgent(
            state_bins=[10, 10, 10, 10, 10], action_dim=ACTION_DIM,
            alpha=float(p.get("alpha", 0.03846)),
            gamma=float(p.get("gamma", 0.9858)),
            epsilon_decay=float(p.get("epsilon_decay", 0.9595))
        )
    else:
        raise ValueError(f"Unknown RL agent: {name}")


def train_single_rl_worker(args):
    """Worker task to train a single RL agent for total_episodes."""
    name, hook_name, gpu_id, total_episodes, steps_per_ep, epsilon_decay, best_params = args
    
    if gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        if torch.cuda.is_available():
            torch.cuda.set_device(0)

    ext = ".pkl" if name in ["QLearning", "SARSA"] else ".pth"
    primary_model_path = os.path.join(MODELS_DIR, f"{name}{ext}")
    primary_log_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")

    # Define alias paths
    alias_models = [primary_model_path]
    alias_logs = [primary_log_path]
    
    if name == "REMO-DQN":
        alias_models.append(os.path.join(MODELS_DIR, "resnet_moe_dqn.pth"))
        alias_logs.append(os.path.join(_code_dir, "resnet_train_log.csv"))
    elif name == "MoEDQN":
        alias_logs.append(os.path.join(_code_dir, "moe_train_log.csv"))
    elif name == "DuelingDQN":
        alias_logs.append(os.path.join(_code_dir, "dueling_dqn_train_log.csv"))
    elif name == "DoubleDQN":
        alias_models.append(os.path.join(MODELS_DIR, "DDQN.pth"))
        alias_logs.append(os.path.join(MODELS_DIR, "DDQN_convergence.csv"))
        alias_logs.append(os.path.join(_code_dir, "ddqn_train_log.csv"))
    elif name == "VanillaDQN":
        alias_models.append(os.path.join(MODELS_DIR, "DQN.pth"))
        alias_logs.append(os.path.join(_code_dir, "dqn_train_log.csv"))
    elif name == "PPO":
        alias_logs.append(os.path.join(_code_dir, "ppo_train_log.csv"))
    elif name == "MAPPO":
        alias_logs.append(os.path.join(_code_dir, "mappo_train_log.csv"))
    elif name == "SAC":
        alias_logs.append(os.path.join(_code_dir, "sac_train_log.csv"))
    elif name == "DDPG":
        alias_logs.append(os.path.join(_code_dir, "ddpg_train_log.csv"))
    elif name == "TD3":
        alias_logs.append(os.path.join(_code_dir, "td3_train_log.csv"))
    elif name == "ActorCritic":
        alias_logs.append(os.path.join(_code_dir, "actor_critic_train_log.csv"))
    elif name == "DecisionTransformer":
        alias_logs.append(os.path.join(_code_dir, "dt_train_log.csv"))
    elif name == "QLearning":
        alias_logs.append(os.path.join(_code_dir, "qlearning_train_log.csv"))
    elif name == "SARSA":
        alias_logs.append(os.path.join(_code_dir, "sarsa_train_log.csv"))

    # Check resumption
    start_ep = 0
    if os.path.exists(primary_log_path):
        with open(primary_log_path, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            if len(lines) > 1 and len(lines[0].split(',')) == len(CSV_HEADER):
                try:
                    start_ep = int(lines[-1].split(',')[0])
                except (ValueError, IndexError):
                    start_ep = len(lines) - 1

    if start_ep >= total_episodes:
        print(f"[{name}] Already finished ({start_ep}/{total_episodes} ep).", flush=True)
        return name

    try:
        print(f"[{name}] Starting training from Ep {start_ep+1}/{total_episodes} on GPU {gpu_id}...", flush=True)
        agent = create_rl_agent(name, best_params, epsilon_decay=epsilon_decay)

        if start_ep > 0 and os.path.exists(primary_model_path):
            try:
                agent.load(primary_model_path)
                print(f"[{name}] Loaded checkpoint from {primary_model_path}", flush=True)
            except Exception as e:
                print(f"[{name}] Warning loading checkpoint: {e}", flush=True)

        if start_ep > 0 and hasattr(agent, 'epsilon') and hasattr(agent, 'epsilon_decay'):
            decay_factor = agent.epsilon_decay ** start_ep
            min_eps = getattr(agent, 'epsilon_min', getattr(agent, 'epsilon_end', 0.01))
            initial_eps = getattr(agent, 'epsilon_start', 1.0)
            agent.epsilon = max(min_eps, initial_eps * decay_factor)

        hook = get_hook(hook_name)
        hook.set_agent(agent)
        hook.is_training = True

        if start_ep == 0 or not os.path.exists(primary_log_path):
            for l_path in alias_logs:
                os.makedirs(os.path.dirname(l_path), exist_ok=True)
                with open(l_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_HEADER)

        global_step = start_ep * steps_per_ep

        for ep in range(start_ep, total_episodes):
            hook.reset_episode()
            density_rng = random.Random(42 + ep)
            density = density_rng.choice([30, 50, 100])

            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=density,
                seed=42 + ep,
                method=hook_name,
                method_params={'n_vehicles_sweep': density},
                duration_steps=steps_per_ep
            )
            metrics = runner.run()
            global_step += steps_per_ep

            # Policy updates
            losses = []
            if hasattr(agent, 'memory'):
                batch_size = getattr(agent, 'batch_size', 64)
                num_updates = max(1, len(agent.memory) // batch_size)
                for _ in range(num_updates):
                    if hasattr(agent, 'train_step'):
                        loss_val = agent.train_step()
                        if loss_val is not None:
                            if isinstance(loss_val, (tuple, list)):
                                losses.append(float(np.mean([float(x) for x in loss_val if x is not None])))
                            elif isinstance(loss_val, (float, int, np.floating)):
                                if float(loss_val) > 0.0:
                                    losses.append(float(loss_val))
            elif hasattr(agent, 'train_step'):
                loss_val = agent.train_step()
                if loss_val is not None:
                    if isinstance(loss_val, (tuple, list)):
                        losses.append(float(np.mean([float(x) for x in loss_val if x is not None])))
                    elif isinstance(loss_val, (float, int, np.floating)):
                        losses.append(float(loss_val))

            if hasattr(agent, 'update_target_network'):
                freq = getattr(agent, 'target_update_freq', 1)
                if (ep + 1) % freq == 0:
                    agent.update_target_network()

            if hasattr(agent, 'update_epsilon'):
                agent.update_epsilon()
            elif hasattr(agent, 'epsilon') and hasattr(agent, 'epsilon_decay'):
                min_eps = getattr(agent, 'epsilon_min', getattr(agent, 'epsilon_end', 0.01))
                agent.epsilon = max(min_eps, agent.epsilon * agent.epsilon_decay)

            avg_loss = float(np.mean(losses)) if losses else 0.0
            eps_val = getattr(agent, 'epsilon', 0.0)
            ep_reward = hook.episode_reward
            aoi = metrics.get('AoI_mean', 0.0)
            cbr = metrics.get('CBR_mean', 0.0)
            pdr = metrics.get('PDR_mean', 0.0)

            row_data = [ep + 1, global_step, ep_reward, aoi, cbr, pdr, avg_loss, eps_val, density]
            for l_path in alias_logs:
                with open(l_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(row_data)
                    f.flush()

            # Save checkpoint periodically and at completion
            if (ep + 1) % 5 == 0 or (ep + 1) == total_episodes:
                for m_path in alias_models:
                    os.makedirs(os.path.dirname(m_path), exist_ok=True)
                    agent.save(m_path)

            if (ep + 1) % 10 == 0 or (ep + 1) == total_episodes:
                print(f"[{name}] Ep {ep+1}/{total_episodes} | R: {ep_reward:.2f} | AoI: {aoi:.2f} | CBR: {cbr:.3f} | PDR: {pdr:.1f}% | Loss: {avg_loss:.4f} | Eps: {eps_val:.3f}", flush=True)

        print(f"[{name}] Retraining COMPLETED ({total_episodes} episodes). Saved to {primary_model_path}", flush=True)
        return name
    except Exception as e:
        print(f"[ERROR] Exception during training {name}: {e}", flush=True)
        traceback.print_exc()
        return None


def eval_single_non_rl_worker(args):
    """Worker task to evaluate a non-RL model for total_episodes."""
    name, hook_name, gpu_id, total_episodes, steps_per_ep = args

    primary_model_path = os.path.join(MODELS_DIR, f"{name}.pkl")
    primary_log_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")

    alias_models = [primary_model_path]
    alias_logs = [primary_log_path]

    if name == "Fixed 10Hz":
        alias_models.append(os.path.join(MODELS_DIR, "Fixed10Hz.pkl"))
        alias_logs.append(os.path.join(MODELS_DIR, "Fixed10Hz_convergence.csv"))

    # Check resumption
    start_ep = 0
    if os.path.exists(primary_log_path):
        with open(primary_log_path, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            if len(lines) > 1 and len(lines[0].split(',')) == len(CSV_HEADER):
                try:
                    start_ep = int(lines[-1].split(',')[0])
                except (ValueError, IndexError):
                    start_ep = len(lines) - 1

    if start_ep >= total_episodes:
        print(f"[{name}] Already finished ({start_ep}/{total_episodes} ep).", flush=True)
        return name

    try:
        print(f"[{name}] Evaluating non-RL baseline from Ep {start_ep+1}/{total_episodes}...", flush=True)
        if start_ep == 0 or not os.path.exists(primary_log_path):
            for l_path in alias_logs:
                os.makedirs(os.path.dirname(l_path), exist_ok=True)
                with open(l_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_HEADER)

        global_step = start_ep * steps_per_ep

        for ep in range(start_ep, total_episodes):
            density_rng = random.Random(42 + ep)
            density = density_rng.choice([30, 50, 100])

            runner = SimulationRunner(
                scenario="urban_grid",
                n_vehicles=density,
                seed=42 + ep,
                method=hook_name,
                method_params={'n_vehicles_sweep': density},
                duration_steps=steps_per_ep
            )
            metrics = runner.run()
            global_step += steps_per_ep

            aoi = metrics.get('AoI_mean', 0.0)
            cbr = metrics.get('CBR_mean', 0.0)
            pdr = metrics.get('PDR_mean', 0.0)

            # Pure negative penalty C-3 reward formulation for non-RL
            t_gen_def = 0.1 if "Fixed" in name else (0.2 if "Adapt" in name else 0.3)
            cost = 0.1 / max(t_gen_def, 1e-3)
            over = max(0.0, cbr - CBR_TARGET)
            stale = max(0.0, (aoi / 1000.0) - T_STALE)
            ep_reward = (-1.0 * over - 0.3 * stale - 0.05 * cost) * (steps_per_ep * density / 10.0)

            row_data = [ep + 1, global_step, ep_reward, aoi, cbr, pdr, 0.0, 0.0, density]
            for l_path in alias_logs:
                with open(l_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(row_data)
                    f.flush()

            if (ep + 1) % 20 == 0 or (ep + 1) == total_episodes:
                print(f"[{name}] Ep {ep+1}/{total_episodes} | R: {ep_reward:.2f} | AoI: {aoi:.2f} | CBR: {cbr:.3f} | PDR: {pdr:.1f}%", flush=True)

        # Save non-RL checkpoint metadata dictionary
        non_rl_metadata = {
            "name": name,
            "method": hook_name,
            "type": "non_rl_baseline",
            "episodes": total_episodes,
            "steps": global_step,
            "t_gen_def": t_gen_def,
            "trained": False,
            "status": "converged_steady_state"
        }
        for m_path in alias_models:
            os.makedirs(os.path.dirname(m_path), exist_ok=True)
            with open(m_path, "wb") as f:
                pickle.dump(non_rl_metadata, f)

        print(f"[{name}] Non-RL evaluation COMPLETED ({total_episodes} episodes).", flush=True)
        return name
    except Exception as e:
        print(f"[ERROR] Exception evaluating non-RL {name}: {e}", flush=True)
        traceback.print_exc()
        return None


def dispatch_train_worker(task_info):
    t_type, task_args = task_info
    if t_type == "RL":
        return train_single_rl_worker(task_args)
    else:
        return eval_single_non_rl_worker(task_args)


def generate_reward_convergence_csv():
    """Merge all 17 individual convergence logs into unified data/reward_convergence.csv."""
    print("\n--- Synthesizing Unified Reward Convergence Dataset (data/reward_convergence.csv) ---")
    model_rewards = {}

    for model_name in CONVERGENCE_ORDER:
        log_path = os.path.join(MODELS_DIR, f"{model_name}_convergence.csv")
        if not os.path.exists(log_path) and model_name == "Fixed 10Hz":
            log_path = os.path.join(MODELS_DIR, "Fixed10Hz_convergence.csv")
        if not os.path.exists(log_path):
            print(f"[WARNING] Missing convergence log for {model_name} at {log_path}, skipping convergence dataset synthesis.")
            return

        episodes = []
        steps = []
        rewards = []
        with open(log_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 3:
                    episodes.append(int(row[0]))
                    steps.append(int(row[1]))
                    rewards.append(float(row[2]))

        if len(rewards) != 100:
            print(f"[WARNING] {model_name} has {len(rewards)} rows (expected 100)")
        model_rewards[model_name] = (episodes, steps, rewards)

    # Write unified CSV (100 rows x 19 columns)
    header_cols = ["Episode", "Global_Step"] + CONVERGENCE_ORDER
    with open(REWARD_CONV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header_cols)
        for i in range(100):
            ep = i + 1
            step = (i + 1) * 2000
            row = [ep, step]
            for m in CONVERGENCE_ORDER:
                _, _, r_list = model_rewards[m]
                val = r_list[i] if i < len(r_list) else -999999.0
                row.append(val)
            writer.writerow(row)

    print(f"Successfully generated {REWARD_CONV_FILE} (100 rows x 19 columns).")


def verify_all_artifacts():
    """Verify integrity of all 17 checkpoints and convergence files."""
    print("\n" + "=" * 80)
    print("VERIFYING ARTIFACTS INTEGRITY ACROSS ALL 17 MODELS")
    print("=" * 80)
    
    best_params = load_all_optuna_params()
    sample_state = np.array([0.2, 0.5, 0.3, 0.1, 0.25], dtype=np.float32)
    sample_tensor = torch.FloatTensor(sample_state).unsqueeze(0)

    # 1. Verify 14 RL Models
    rl_verified = 0
    for name, hook_name in RL_MODELS:
        ext = ".pkl" if name in ["QLearning", "SARSA"] else ".pth"
        model_path = os.path.join(MODELS_DIR, f"{name}{ext}")
        log_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")

        # Check file existence and size
        if not os.path.exists(model_path) or os.path.getsize(model_path) == 0:
            print(f"[{name}] [FAIL] Checkpoint missing or empty: {model_path}")
            continue
        if not os.path.exists(log_path):
            print(f"[{name}] [FAIL] Convergence log missing: {log_path}")
            continue

        # Verify log row count
        with open(log_path, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if len(lines) != 101:
            print(f"[{name}] [FAIL] Log line count is {len(lines)} (expected 101)")
            continue

        # Verify load & forward pass
        try:
            agent = create_rl_agent(name, best_params)
            agent.load(model_path)
            if name == "MAPPO":
                act = agent.act(sample_state, sample_state, evaluate=True)
            else:
                act = agent.act(sample_state, evaluate=True)
            assert 0 <= int(act) < ACTION_DIM, f"Invalid action {act}"
            print(f"[{name}] [PASS] Checkpoint size: {os.path.getsize(model_path):,} B | Action: {act} | Log: {len(lines)} lines")
            rl_verified += 1
        except Exception as e:
            print(f"[{name}] [FAIL] Error verifying agent: {e}")
            traceback.print_exc()

    # 2. Verify 3 Non-RL Models
    non_rl_verified = 0
    for name, hook_name in NON_RL_MODELS:
        model_path = os.path.join(MODELS_DIR, f"{name}.pkl")
        log_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")
        if not os.path.exists(model_path) or os.path.getsize(model_path) == 0:
            print(f"[{name}] [FAIL] Checkpoint missing or empty: {model_path}")
            continue
        if not os.path.exists(log_path):
            print(f"[{name}] [FAIL] Convergence log missing: {log_path}")
            continue
        with open(log_path, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if len(lines) != 101:
            print(f"[{name}] [FAIL] Log line count is {len(lines)} (expected 101)")
            continue

        try:
            with open(model_path, 'rb') as f:
                meta = pickle.load(f)
            assert meta.get("type") == "non_rl_baseline"
            print(f"[{name}] [PASS] Checkpoint size: {os.path.getsize(model_path):,} B | Meta: {meta.get('status')} | Log: {len(lines)} lines")
            non_rl_verified += 1
        except Exception as e:
            print(f"[{name}] [FAIL] Error verifying non-RL metadata: {e}")

    # 3. Verify reward_convergence.csv
    conv_verified = False
    if os.path.exists(REWARD_CONV_FILE):
        with open(REWARD_CONV_FILE, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if len(lines) == 101:
            header_cols = lines[0].split(',')
            if len(header_cols) == 19:
                print(f"[reward_convergence.csv] [PASS] 100 rows x 19 columns strictly verified.")
                conv_verified = True
            else:
                print(f"[reward_convergence.csv] [FAIL] Column count is {len(header_cols)} (expected 19)")
        else:
            print(f"[reward_convergence.csv] [FAIL] Line count is {len(lines)} (expected 101)")
    else:
        print(f"[reward_convergence.csv] [FAIL] File does not exist: {REWARD_CONV_FILE}")

    print("=" * 80)
    print(f"VERIFICATION SUMMARY: {rl_verified}/14 RL Models PASS | {non_rl_verified}/3 Non-RL Models PASS | Convergence Dataset: {'PASS' if conv_verified else 'FAIL'}")
    print("=" * 80)
    return (rl_verified == 14 and non_rl_verified == 3 and conv_verified)


def run_parallel_training(total_episodes=100, steps_per_ep=2000, epsilon_decay=0.95,
                          num_workers=16, gpus=[0, 1, 2, 3], target_models=None):
    print("=" * 80)
    print("STARTING 17-MODEL FULL RETRAINING ENGINE (MILESTONE 3)")
    print(f"Episodes: {total_episodes} | Steps/Ep: {steps_per_ep} | Total Steps: {total_episodes * steps_per_ep:,}")
    print(f"GPUs: {gpus} | Workers: {num_workers}")
    print("=" * 80)

    best_params = load_all_optuna_params()

    rl_tasks = []
    non_rl_tasks = []

    for i, (name, hook_name) in enumerate(RL_MODELS):
        if target_models and name not in target_models:
            continue
        gpu_id = gpus[i % len(gpus)] if gpus else 0
        rl_tasks.append((name, hook_name, gpu_id, total_episodes, steps_per_ep, epsilon_decay, best_params))

    for i, (name, hook_name) in enumerate(NON_RL_MODELS):
        if target_models and name not in target_models:
            continue
        gpu_id = gpus[i % len(gpus)] if gpus else 0
        non_rl_tasks.append((name, hook_name, gpu_id, total_episodes, steps_per_ep))

    all_tasks = [("RL", t) for t in rl_tasks] + [("NON_RL", t) for t in non_rl_tasks]

    t0 = time.time()
    with mp.Pool(processes=min(num_workers, len(all_tasks))) as pool:
        results = pool.map(dispatch_train_worker, all_tasks)

    elapsed = time.time() - t0
    print(f"\nAll {len(results)} tasks completed in {elapsed/60:.2f} minutes.")
    print(f"Task completion results: {results}")

    # Generate unified convergence CSV
    generate_reward_convergence_csv()

    # Verify all artifacts
    verify_all_artifacts()


def main():
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

    parser = argparse.ArgumentParser(description="Master Retraining Pipeline for 17 Models")
    parser.add_argument("--episodes", type=int, default=100, help="Episodes per model (default: 100)")
    parser.add_argument("--duration_steps", type=int, default=2000, help="Steps per episode (default: 2000)")
    parser.add_argument("--epsilon_decay", type=float, default=0.95, help="Epsilon decay rate (default: 0.95)")
    parser.add_argument("--workers", type=int, default=16, help="Parallel worker count (default: 16)")
    parser.add_argument("--gpus", type=int, nargs="+", default=[0, 1, 2, 3], help="GPU device IDs (default: 0 1 2 3)")
    parser.add_argument("--models", type=str, nargs="+", default=None, help="Target model names (default: all 17)")
    parser.add_argument("--verify-only", action="store_true", help="Run verification checks only")
    args = parser.parse_args()

    if args.verify_only:
        verify_all_artifacts()
    else:
        run_parallel_training(
            total_episodes=args.episodes,
            steps_per_ep=args.duration_steps,
            epsilon_decay=args.epsilon_decay,
            num_workers=args.workers,
            gpus=args.gpus,
            target_models=args.models
        )


if __name__ == "__main__":
    main()
