#!/usr/bin/env python3
import os
import sys
import csv
import argparse
import numpy as np

from sim_engine import SimulationRunner
from sarsa_agent import SARSAAgent
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM

def train(num_episodes=500, seed=42, duration_steps=1000,
          output_model="sarsa_model.pkl", output_log="sarsa_train_log.csv",
          epsilon_decay=0.995, min_epsilon=0.01,
          alpha=0.1, gamma=0.99, state_bins=None):
    """
    Train SARSA agent on Urban Grid DCC scenario.
    Default: 500 episodes, epsilon_decay=0.995 (1.0 -> 0.082 across 500 episodes).
    """
    if state_bins is None:
        state_bins = [5, 5, 5, 5, 5]
        
    agent = SARSAAgent(
        state_bins=state_bins,
        action_dim=ACTION_DIM,
        alpha=alpha,
        gamma=gamma,
        epsilon=1.0,
        epsilon_decay=epsilon_decay,
        epsilon_min=min_epsilon
    )
    hook = get_hook("SARSA")
    hook.set_agent(agent)
    hook.is_training = True

    log_dir = os.path.dirname(output_log)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    with open(output_log, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Loss', 'Epsilon', 'Steps', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    print(f"Starting SARSA training: episodes={num_episodes}, epsilon_decay={epsilon_decay}, min_eps={min_epsilon}")

    for ep in range(num_episodes):
        hook.reset_episode()
        
        print(f"Starting Episode {ep+1}/{num_episodes} (Epsilon: {agent.epsilon:.4f})...")
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=50,
            seed=seed+ep,
            method="SARSA",
            method_params={},
            duration_steps=duration_steps
        )
        metrics = runner.run()
        
        # SARSA is updated online in the hook, no-op train_step
        loss = agent.train_step()
        
        # Decay epsilon once per episode
        agent.update_epsilon()
        
        ep_reward = hook.episode_reward
        steps_val = metrics.get('steps', duration_steps)
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1}/{num_episodes} | Reward: {ep_reward:.2f} | Loss: {loss:.4f} | Epsilon: {agent.epsilon:.4f} | Steps: {steps_val}")
        print(f"  Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open(output_log, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, loss, agent.epsilon, steps_val, aoi, cbr, pdr])
            
    # Save trained model
    model_dir = os.path.dirname(output_model)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
    agent.save(output_model)
    print(f"Training finished. Model saved to {output_model}, Log saved to {output_log}")
    return agent

def run_optuna_study(n_trials=5):
    import optuna
    
    def objective(trial):
        alpha = trial.suggest_float("alpha", 0.01, 0.5, log=True)
        gamma = trial.suggest_float("gamma", 0.8, 0.99)
        epsilon_decay = trial.suggest_float("epsilon_decay", 0.99, 0.999)
        bins = [
            trial.suggest_int("bin_cbr_global", 3, 8),
            trial.suggest_int("bin_n_neighbors", 3, 8),
            trial.suggest_int("bin_v_norm", 3, 8),
            trial.suggest_int("bin_dt", 3, 8),
            trial.suggest_int("bin_cbr_smoothed", 3, 8)
        ]
        agent = SARSAAgent(state_bins=bins, action_dim=ACTION_DIM, alpha=alpha, gamma=gamma, epsilon=1.0, epsilon_decay=epsilon_decay)
        hook = get_hook("SARSA")
        hook.set_agent(agent)
        hook.is_training = True
        
        total_r = 0.0
        for ep in range(2):
            hook.reset_episode()
            runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="SARSA", method_params={}, duration_steps=500)
            runner.run()
            agent.update_epsilon()
            total_r += hook.episode_reward
        return total_r / 2.0

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    print("Optuna Best Params:", study.best_params)
    return study.best_params

def parse_args():
    parser = argparse.ArgumentParser(description="Train SARSA on Urban Grid DCC")
    parser.add_argument("--episodes", type=int, default=500, help="Number of training episodes (default: 500)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed base (default: 42)")
    parser.add_argument("--duration_steps", type=int, default=1000, help="Steps per episode (default: 1000)")
    parser.add_argument("--epsilon_decay", type=float, default=0.995, help="Epsilon decay rate per episode (default: 0.995)")
    parser.add_argument("--min_epsilon", type=float, default=0.01, help="Minimum exploration epsilon (default: 0.01)")
    parser.add_argument("--alpha", type=float, default=0.1, help="Learning rate alpha (default: 0.1)")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor gamma (default: 0.99)")
    parser.add_argument("--output_model", type=str, default="sarsa_model.pkl", help="Output model checkpoint path")
    parser.add_argument("--output_log", type=str, default="sarsa_train_log.csv", help="Output CSV log file path")
    parser.add_argument("--optuna", action="store_true", help="Run Optuna hyperparameter optimization first")
    return parser.parse_args()

def main():
    args = parse_args()
    alpha = args.alpha
    gamma = args.gamma
    decay = args.epsilon_decay
    bins = [5, 5, 5, 5, 5]
    
    if args.optuna:
        best_p = run_optuna_study(n_trials=5)
        alpha = best_p.get("alpha", alpha)
        gamma = best_p.get("gamma", gamma)
        decay = best_p.get("epsilon_decay", decay)
        bins = [
            best_p["bin_cbr_global"],
            best_p["bin_n_neighbors"],
            best_p["bin_v_norm"],
            best_p["bin_dt"],
            best_p["bin_cbr_smoothed"]
        ]
        
    train(
        num_episodes=args.episodes,
        seed=args.seed,
        duration_steps=args.duration_steps,
        output_model=args.output_model,
        output_log=args.output_log,
        epsilon_decay=decay,
        min_epsilon=args.min_epsilon,
        alpha=alpha,
        gamma=gamma,
        state_bins=bins
    )

if __name__ == "__main__":
    main()
