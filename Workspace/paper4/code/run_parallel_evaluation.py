#!/usr/bin/env python3
"""
run_parallel_evaluation.py
==========================
Parallel training and evaluation pipeline for 16 models (13 RL Baselines + 3 non-RL Baselines)
on the Urban Grid DCC scenario for Paper4 (REMO-DQN).

Requirements:
- 13 RL Baselines: VanillaDQN, DoubleDQN, DuelingDQN, MoEDQN, PPO, SAC, DDPG, TD3,
                   ActorCritic, MAPPO, DecisionTransformer, QLearning, SARSA
- 3 non-RL Baselines: Fixed10Hz, ReactDCC, AdaptDCC
- 100 episodes x 2000 steps (total 200,000 steps per model)
- epsilon_decay=0.95 (DQN/tabular models), min_epsilon=0.01
- Dynamic random density: random.choice([30, 50, 100]) per episode
- Log format: 9-column CSV: [Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean, Loss, Epsilon, Density]
- Output weights: data/models/<model_name>.pth (or .pkl)
- Output CSV: data/models/<model_name>_convergence.csv
"""

import os
import csv
import random
import traceback
import sys
import gc
import shutil
import multiprocessing as mp
import time
import argparse
import numpy as np
import torch

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook, CBR_TARGET, T_STALE
from etsi_cam_layer import ACTION_DIM

# Agent imports
from qlearning_agent import QLearningAgent
from sarsa_agent import SARSAAgent
from actor_critic_agent import ActorCriticAgent
from dqn_agent import DQNAgent
from ddqn_agent import DDQNAgent
from dueling_dqn_agent import DuelingDQNAgent
from ddpg_agent import DDPGAgent
from ppo_agent import PPOAgent
from sac_agent import SACAgent
from td3_agent import TD3Agent
from dt_agent import DTAgent
from mappo_agent import MAPPOAgent
from moe_agent import MoEAgent 
from resnet_moe_agent import ResNetMoEAgent

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
OPTUNA_DIR = os.environ.get("OPTUNA_DIR", os.path.join(DATA_DIR, "optuna"))
MODELS_DIR = os.environ.get("MODELS_DIR", os.path.join(DATA_DIR, "models"))
EVAL_DIR = os.environ.get("EVAL_DIR", os.path.join(DATA_DIR, "evaluation"))
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(EVAL_DIR, exist_ok=True)

CSV_HEADER = ['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean', 'Loss', 'Epsilon', 'Density']

RL_METHODS = [
    ("VanillaDQN", "VanillaDQN"),
    ("DoubleDQN", "DoubleDQN"),
    ("DuelingDQN", "DuelingDQN"),
    ("MoEDQN", "MoEDQN"),
    ("PPO", "PPO"),
    ("SAC", "SAC"),
    ("DDPG", "DDPG"),
    ("TD3", "TD3"),
    ("ActorCritic", "ActorCritic"),
    ("MAPPO", "MAPPO"),
    ("DecisionTransformer", "DecisionTransformer"),
    ("QLearning", "QLearning"),
    ("SARSA", "SARSA"),
]

NON_RL_METHODS = [
    ("Fixed10Hz", "Fixed10Hz"),
    ("ReactDCC", "ReactDCC"),
    ("AdaptDCC", "AdaptDCC"),
]

ALL_16_METHODS = RL_METHODS + [(name, name) for name, _ in NON_RL_METHODS]


def load_optuna_params(method_name):
    csv_path = os.path.join(OPTUNA_DIR, f"best_params_{method_name}.csv")
    if method_name == "REMO-DQN" and not os.path.exists(csv_path):
        csv_path = os.path.join(OPTUNA_DIR, "best_params_ResNetMoEDQN.csv")
    
    params = {}
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader) 
            for row in reader:
                if len(row) == 2:
                    k, v = row
                    try:
                        f_v = float(v)
                        if f_v.is_integer() and k in ['batch_size', 'hidden_dim', 'buffer_size', 'num_experts', 'max_depth']:
                            params[k] = int(f_v)
                        else:
                            params[k] = f_v
                    except Exception:
                        params[k] = v
    return params


def create_agent(method_name, state_dim=5, action_dim=ACTION_DIM, epsilon_decay=0.95):
    params = load_optuna_params(method_name)
    def get_p(key, default):
        return params.get(key, default)

    if method_name == "QLearning":
        return QLearningAgent(state_bins=[10,10,10,10,10], action_dim=action_dim,
                              alpha=get_p('alpha', 0.1), gamma=get_p('gamma', 0.99),
                              epsilon_decay=epsilon_decay)
    elif method_name == "SARSA":
        return SARSAAgent(state_bins=[10,10,10,10,10], action_dim=action_dim,
                          alpha=get_p('alpha', 0.1), gamma=get_p('gamma', 0.99),
                          epsilon_decay=epsilon_decay)
    elif method_name == "ActorCritic":
        return ActorCriticAgent(state_dim=state_dim, action_dim=action_dim,
                                lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "VanillaDQN":
        return DQNAgent(state_dim=state_dim, action_dim=action_dim,
                        lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99),
                        epsilon_decay=epsilon_decay)
    elif method_name == "DoubleDQN":
        return DDQNAgent(state_dim=state_dim, action_dim=action_dim,
                         lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99),
                         epsilon_decay=epsilon_decay)
    elif method_name == "DuelingDQN":
        return DuelingDQNAgent(state_dim=state_dim, action_dim=action_dim,
                              lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99),
                              epsilon_decay=epsilon_decay)
    elif method_name == "DDPG":
        return DDPGAgent(state_dim=state_dim, action_dim=action_dim,
                         lr_actor=get_p('lr_actor', 1e-4), lr_critic=get_p('lr_critic', 1e-3),
                         gamma=get_p('gamma', 0.99))
    elif method_name == "PPO":
        return PPOAgent(state_dim=state_dim, action_dim=action_dim,
                        lr=get_p('lr', 3e-4), gamma=get_p('gamma', 0.99))
    elif method_name == "SAC":
        return SACAgent(state_dim=state_dim, action_dim=action_dim,
                        lr=get_p('lr', 3e-4), gamma=get_p('gamma', 0.99))
    elif method_name == "TD3":
        return TD3Agent(state_dim=state_dim, action_dim=action_dim,
                        lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99),
                        noise_decay=epsilon_decay)
    elif method_name == "DecisionTransformer":
        return DTAgent(state_dim=state_dim, action_dim=action_dim,
                       lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "MAPPO":
        return MAPPOAgent(local_state_dim=state_dim, global_state_dim=state_dim,
                          action_dim=action_dim, lr=get_p('lr', 3e-4), gamma=get_p('gamma', 0.99))
    elif method_name == "MoEDQN":
        return MoEAgent(state_dim=state_dim, action_dim=action_dim,
                        num_experts=get_p('num_experts', 2), lr=get_p('lr', 1e-3),
                        gamma=get_p('gamma', 0.99), epsilon_decay=epsilon_decay)
    elif method_name in ["REMO-DQN", "ResNetMoEDQN"]:
        return ResNetMoEAgent(state_dim=state_dim, action_dim=action_dim,
                              num_experts=get_p('num_experts', 3), hidden_dim=get_p('hidden_dim', 128),
                              batch_size=get_p('batch_size', 64), epsilon_decay=epsilon_decay)
    else:
        raise ValueError(f"Unknown RL method {method_name}")


def train_rl_worker(args):
    name, hook_name, gpu_id, total_episodes, steps_per_ep, epsilon_decay = args
    if gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        if torch.cuda.is_available():
            torch.cuda.set_device(0)

    ext = ".pkl" if name in ["QLearning", "SARSA"] else ".pth"
    model_path = os.path.join(MODELS_DIR, f"{name}{ext}")
    log_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")

    # Check existing progress to compute start_ep
    start_ep = 0
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if len(lines) > 1:
                # Check header format
                header_cols = [c.strip() for c in lines[0].split(',')]
                if len(header_cols) == len(CSV_HEADER):
                    try:
                        last_ep = int(lines[-1].split(',')[0])
                        start_ep = last_ep
                    except (ValueError, IndexError):
                        start_ep = len(lines) - 1
                else:
                    # Legacy header, restart with proper 9-column format
                    start_ep = 0

    if start_ep >= total_episodes:
        print(f"[{name}] Already completed ({start_ep}/{total_episodes} episodes).")
        return name

    try:
        print(f"--- Training {name} starting from Ep {start_ep+1}/{total_episodes} on GPU {gpu_id} ---", flush=True)
        agent = create_agent(name, epsilon_decay=epsilon_decay)

        if start_ep > 0 and os.path.exists(model_path):
            try:
                agent.load(model_path)
                print(f"[{name}] Loaded checkpoint from {model_path}", flush=True)
            except Exception as e:
                print(f"[{name}] Warning loading checkpoint: {e}", flush=True)

        if start_ep > 0 and hasattr(agent, 'epsilon') and hasattr(agent, 'epsilon_decay'):
            decay_factor = agent.epsilon_decay ** start_ep
            min_eps = getattr(agent, 'epsilon_min', getattr(agent, 'epsilon_end', 0.01))
            initial_eps = getattr(agent, 'epsilon_start', 1.0)
            agent.epsilon = max(min_eps, initial_eps * decay_factor)
            print(f"[{name}] Adjusted epsilon to {agent.epsilon:.4f} for start_ep={start_ep}", flush=True)

        hook = get_hook(hook_name)
        hook.set_agent(agent)
        hook.is_training = True

        if start_ep == 0 or not os.path.exists(log_path):
            with open(log_path, 'w', newline='') as f:
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

            # Policy update
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
            with open(log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)

            # Save checkpoint
            agent.save(model_path)
            print(f"[{name}] Ep {ep+1}/{total_episodes} (Dens:{density}) | R:{ep_reward:.1f} | AoI:{aoi:.1f} | CBR:{cbr:.3f} | PDR:{pdr:.1f}% | Loss:{avg_loss:.4f} | Eps:{eps_val:.3f}", flush=True)

        print(f"[{name}] Completed {total_episodes} episodes. Saved to {model_path}")
        del agent
        gc.collect()
        return name
    except Exception as e:
        print(f"Error training {name}: {e}", flush=True)
        traceback.print_exc()
        return None


def eval_non_rl_worker(args):
    name, hook_name, gpu_id, total_episodes, steps_per_ep = args
    log_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")

    start_ep = 0
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if len(lines) > 1:
                header_cols = [c.strip() for c in lines[0].split(',')]
                if len(header_cols) == len(CSV_HEADER):
                    try:
                        last_ep = int(lines[-1].split(',')[0])
                        start_ep = last_ep
                    except (ValueError, IndexError):
                        start_ep = len(lines) - 1
                else:
                    start_ep = 0

    if start_ep >= total_episodes:
        print(f"[{name}] Already completed ({start_ep}/{total_episodes} episodes).")
        return name

    try:
        print(f"--- Evaluating non-RL {name} starting from Ep {start_ep+1}/{total_episodes} ---", flush=True)
        if start_ep == 0 or not os.path.exists(log_path):
            with open(log_path, 'w', newline='') as f:
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

            # Standard C-3 reward evaluation for non-RL baseline
            # over-target + staleness + transmission cost
            t_gen_def = 0.1 if name == "Fixed10Hz" else 0.3
            cost = 0.1 / max(t_gen_def, 1e-3)
            over = max(0.0, cbr - CBR_TARGET)
            stale = max(0.0, (aoi / 1000.0) - T_STALE)
            ep_reward = (-1.0 * over - 0.3 * stale - 0.05 * cost) * (steps_per_ep * density / 10.0)

            row_data = [ep + 1, global_step, ep_reward, aoi, cbr, pdr, 0.0, 0.0, density]
            with open(log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)

            print(f"[{name}] Ep {ep+1}/{total_episodes} (Dens:{density}) | R:{ep_reward:.1f} | AoI:{aoi:.1f} | CBR:{cbr:.3f} | PDR:{pdr:.1f}%", flush=True)

        print(f"[{name}] Non-RL evaluation completed {total_episodes} episodes.")
        return name
    except Exception as e:
        print(f"Error evaluating non-RL {name}: {e}", flush=True)
        traceback.print_exc()
        return None


def dispatch_worker(task_info):
    t_type, task_args = task_info
    if t_type == "RL":
        return train_rl_worker(task_args)
    else:
        return eval_non_rl_worker(task_args)


def run_all_training(total_episodes=100, steps_per_ep=2000, epsilon_decay=0.95,
                     num_workers=8, gpus=[0, 1, 2, 3], target_models=None):
    print("=" * 80)
    print(f"LAUNCHING PARALLEL CONVERGENCE TRAINING & EVALUATION (16 MODELS)")
    print(f"Episodes: {total_episodes}, Steps/Ep: {steps_per_ep}, Epsilon Decay: {epsilon_decay}")
    print(f"GPUs: {gpus}, Workers: {num_workers}")
    print("=" * 80)

    rl_tasks = []
    non_rl_tasks = []

    for i, (name, hook_name) in enumerate(RL_METHODS):
        if target_models and name not in target_models:
            continue
        gpu_id = gpus[i % len(gpus)] if gpus else 0
        rl_tasks.append((name, hook_name, gpu_id, total_episodes, steps_per_ep, epsilon_decay))

    for i, (name, hook_name) in enumerate(NON_RL_METHODS):
        if target_models and name not in target_models:
            continue
        gpu_id = gpus[i % len(gpus)] if gpus else 0
        non_rl_tasks.append((name, hook_name, gpu_id, total_episodes, steps_per_ep))

    all_tasks = [("RL", t) for t in rl_tasks] + [("NON_RL", t) for t in non_rl_tasks]

    with mp.Pool(processes=min(num_workers, len(all_tasks))) as pool:
        results = pool.map(dispatch_worker, all_tasks)

    print("\n" + "=" * 80)
    print(f"All {len(results)} model training/eval tasks completed: {results}")
    print("=" * 80)


def main():
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

    parser = argparse.ArgumentParser(description="Parallel Training & Evaluation for 16 Baselines")
    parser.add_argument("--episodes", type=int, default=100, help="Episodes per model (default: 100)")
    parser.add_argument("--duration_steps", type=int, default=2000, help="Steps per episode (default: 2000)")
    parser.add_argument("--epsilon_decay", type=float, default=0.95, help="Epsilon decay rate (default: 0.95)")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel worker processes (default: 8)")
    parser.add_argument("--gpus", type=int, nargs="+", default=[1, 2, 0, 3], help="GPU device IDs to distribute across")
    parser.add_argument("--models", type=str, nargs="+", default=None, help="Specific models to run (default: all 16)")
    args = parser.parse_args()

    run_all_training(
        total_episodes=args.episodes,
        steps_per_ep=args.duration_steps,
        epsilon_decay=args.epsilon_decay,
        num_workers=args.workers,
        gpus=args.gpus,
        target_models=args.models
    )


if __name__ == "__main__":
    main()
