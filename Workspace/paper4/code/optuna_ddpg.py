#!/usr/bin/env python3
import optuna
import csv
import os
import sys
import torch
import numpy as np

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM
from ddpg_agent import DDPGAgent

def objective(trial):
    lr_actor = trial.suggest_float("lr_actor", 1e-5, 1e-2, log=True)
    lr_critic = trial.suggest_float("lr_critic", 1e-5, 1e-2, log=True)
    gamma = trial.suggest_float("gamma", 0.90, 0.999)
    tau = trial.suggest_float("tau", 0.001, 0.01)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])
    
    agent = DDPGAgent(
        state_dim=5,
        action_dim=ACTION_DIM,
        lr_actor=lr_actor,
        lr_critic=lr_critic,
        gamma=gamma,
        tau=tau,
        batch_size=batch_size,
        buffer_size=buffer_size
    )
    
    hook = get_hook("DDPG")
    hook.set_agent(agent)
    
    # --- TRAINING PHASE ---
    hook.is_training = True
    num_episodes = 2
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(
            scenario="urban_grid", 
            n_vehicles=10, 
            seed=42 + ep + trial.number * 10, 
            method="DDPG", 
            method_params={}, 
            duration_steps=200
        )
        runner.run()
        
        # Post-episode updates
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
    for ep in range(1):
        hook.reset_episode()
        runner = SimulationRunner(
            scenario="urban_grid", 
            n_vehicles=15, 
            seed=100 + ep + trial.number * 10, 
            method="DDPG", 
            method_params={}, 
            duration_steps=200
        )
        runner.run()
        eval_rewards.append(hook.episode_reward)
        
    return float(np.mean(eval_rewards))

def main():
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(direction="maximize", study_name="DDPG", sampler=sampler)
    study.optimize(objective, n_trials=15)
    
    print(f"[DDPG] Best params:", study.best_params)
    
    output_dir = os.environ.get("OPTUNA_DIR", os.path.join(_project_root, "data", "optuna"))
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "best_params_DDPG.csv")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Value"])
        for key, value in study.best_params.items():
            writer.writerow([key, value])
            
    print(f"[DDPG] Best parameters saved to {output_file}")

if __name__ == "__main__":
    main()
