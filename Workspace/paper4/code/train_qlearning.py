#!/usr/bin/env python3
import os
import csv
import optuna
import numpy as np

from sim_engine import SimulationRunner
from qlearning_agent import QLearningAgent
from ai_dcc_hook import get_hook

def objective(trial):
    # Suggest hyperparameters
    alpha = trial.suggest_float("alpha", 0.01, 0.5, log=True)
    gamma = trial.suggest_float("gamma", 0.8, 0.99)
    epsilon_decay = trial.suggest_float("epsilon_decay", 0.9, 0.999)
    
    # Bins for the 5 state variables
    bins = [
        trial.suggest_int("bin_cbr_global", 3, 10),
        trial.suggest_int("bin_n_neighbors", 3, 10),
        trial.suggest_int("bin_v_norm", 3, 10),
        trial.suggest_int("bin_dt", 3, 10),
        trial.suggest_int("bin_cbr_smoothed", 3, 10)
    ]
    
    agent = QLearningAgent(state_bins=bins, action_dim=16, alpha=alpha, gamma=gamma, epsilon=1.0, epsilon_decay=epsilon_decay)
    hook = get_hook("QLearning")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 2  # Keep it small for optuna to finish
    mean_reward = 0
    
    for ep in range(num_episodes):
        hook.reset_episode()
        # duration_steps 500 for fast eval
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="QLearning", method_params={}, duration_steps=500)
        _ = runner.run()
        
        agent.update_epsilon()
        mean_reward += hook.episode_reward
        
    return mean_reward / num_episodes

def train_best_model(best_params):
    print("Training final model with best params:", best_params)
    
    bins = [
        best_params["bin_cbr_global"],
        best_params["bin_n_neighbors"],
        best_params["bin_v_norm"],
        best_params["bin_dt"],
        best_params["bin_cbr_smoothed"]
    ]
    
    agent = QLearningAgent(
        state_bins=bins,
        action_dim=16,
        alpha=best_params["alpha"],
        gamma=best_params["gamma"],
        epsilon=1.0,
        epsilon_decay=best_params["epsilon_decay"]
    )
    
    hook = get_hook("QLearning")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 5
    
    with open('qlearning_train_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Epsilon', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    for ep in range(num_episodes):
        hook.reset_episode()
        print(f"Starting Episode {ep+1}/{num_episodes}...")
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="QLearning", method_params={}, duration_steps=1000)
        metrics = runner.run()
        
        agent.update_epsilon()
        ep_reward = hook.episode_reward
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1} | Reward: {ep_reward:.2f} | Epsilon: {agent.epsilon:.3f}")
        print(f"Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open('qlearning_train_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, agent.epsilon, aoi, cbr, pdr])
            
    # Evaluation run
    print("Running final evaluation...")
    hook.is_training = False
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=99, method="QLearning", method_params={}, duration_steps=3000)
    final_metrics = runner.run()
    
    agent.save("qlearning_model.pkl")
    print("Training finished, model saved to qlearning_model.pkl")
    
    print("Final Evaluation Metrics:")
    print(f"AoI: {final_metrics.get('AoI_mean', 0.0):.4f}")
    print(f"CBR: {final_metrics.get('CBR_mean', 0.0):.4f}")
    print(f"PDR: {final_metrics.get('PDR_mean', 0.0):.4f}")

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    # Quick optimization
    study.optimize(objective, n_trials=3)
    print("Best Params found:", study.best_params)
    
    train_best_model(study.best_params)
