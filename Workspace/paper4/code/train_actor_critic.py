#!/usr/bin/env python3
import os
import sys
import csv
import argparse
import torch
import numpy as np

from sim_engine import SimulationRunner
from actor_critic_agent import ActorCriticAgent
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM

def train(num_episodes=500, seed=42, duration_steps=1000,
          output_model="actor_critic.pth", output_log="actor_critic_train_log.csv",
          lr=1e-3, gamma=0.99, batch_size=64):
    """
    Train ActorCritic (A2C) agent on Urban Grid DCC scenario.
    Default: 500 episodes.
    """
    agent = ActorCriticAgent(
        state_dim=5,
        action_dim=ACTION_DIM,
        lr=lr,
        gamma=gamma,
        buffer_size=50000,
        batch_size=batch_size
    )
    hook = get_hook("ActorCritic")
    hook.set_agent(agent)
    hook.is_training = True

    log_dir = os.path.dirname(output_log)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    with open(output_log, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'ActorLoss', 'CriticLoss', 'Loss', 'Epsilon', 'Steps', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    print(f"Starting ActorCritic training: episodes={num_episodes}, lr={lr}, gamma={gamma}")

    for ep in range(num_episodes):
        hook.reset_episode()
        
        print(f"Starting Episode {ep+1}/{num_episodes}...")
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=50,
            seed=seed+ep,
            method="ActorCritic",
            method_params={},
            duration_steps=duration_steps
        )
        metrics = runner.run()
        
        # Policy update
        avg_aloss, avg_closs = agent.train_step()
        total_loss = (avg_aloss + avg_closs) / 2.0
        
        if hasattr(agent, 'update_epsilon'):
            agent.update_epsilon()
            
        ep_reward = hook.episode_reward
        eps_val = getattr(agent, 'epsilon', 0.0)
        steps_val = metrics.get('steps', duration_steps)
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1}/{num_episodes} | Reward: {ep_reward:.2f} | ALoss: {avg_aloss:.4f} | CLoss: {avg_closs:.4f} | Steps: {steps_val}")
        print(f"  Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open(output_log, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, avg_aloss, avg_closs, total_loss, eps_val, steps_val, aoi, cbr, pdr])
            
    # Save trained model
    model_dir = os.path.dirname(output_model)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
    agent.save(output_model)
    print(f"Training finished. Model saved to {output_model}, Log saved to {output_log}")
    return agent

def run_optuna_study(n_trials=3):
    import optuna
    
    def objective(trial):
        lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
        gamma = trial.suggest_float("gamma", 0.8, 0.99)
        batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
        
        agent = ActorCriticAgent(state_dim=5, action_dim=ACTION_DIM, lr=lr, gamma=gamma, buffer_size=50000, batch_size=batch_size)
        hook = get_hook("ActorCritic")
        hook.set_agent(agent)
        hook.is_training = True
        
        total_r = 0.0
        for ep in range(2):
            hook.reset_episode()
            runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="ActorCritic", method_params={}, duration_steps=500)
            runner.run()
            agent.train_step()
            total_r += hook.episode_reward
        return total_r / 2.0

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    print("Optuna Best Params:", study.best_params)
    return study.best_params

def parse_args():
    parser = argparse.ArgumentParser(description="Train ActorCritic on Urban Grid DCC")
    parser.add_argument("--episodes", type=int, default=500, help="Number of training episodes (default: 500)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed base (default: 42)")
    parser.add_argument("--duration_steps", type=int, default=1000, help="Steps per episode (default: 1000)")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate (default: 1e-3)")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor gamma (default: 0.99)")
    parser.add_argument("--batch_size", type=int, default=64, help="Batch size (default: 64)")
    parser.add_argument("--output_model", type=str, default="actor_critic.pth", help="Output model checkpoint path")
    parser.add_argument("--output_log", type=str, default="actor_critic_train_log.csv", help="Output CSV log file path")
    parser.add_argument("--optuna", action="store_true", help="Run Optuna hyperparameter optimization first")
    return parser.parse_args()

def main():
    args = parse_args()
    lr = args.lr
    gamma = args.gamma
    bs = args.batch_size
    
    if args.optuna:
        best_p = run_optuna_study(n_trials=3)
        lr = best_p.get("lr", lr)
        gamma = best_p.get("gamma", gamma)
        bs = best_p.get("batch_size", bs)
        
    train(
        num_episodes=args.episodes,
        seed=args.seed,
        duration_steps=args.duration_steps,
        output_model=args.output_model,
        output_log=args.output_log,
        lr=lr,
        gamma=gamma,
        batch_size=bs
    )

if __name__ == "__main__":
    main()
