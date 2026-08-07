#!/usr/bin/env python3
import os
import csv
import optuna
import numpy as np
import json

from sim_engine import SimulationRunner
from dt_agent import DTAgent
from ai_dcc_hook import get_hook

def objective(trial):
    # Suggest hyperparameters
    lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)
    gamma = trial.suggest_float("gamma", 0.9, 0.999)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    
    state_dim = 5
    action_dim = 16
    
    agent = DTAgent(state_dim=state_dim, action_dim=action_dim, lr=lr, gamma=gamma, batch_size=batch_size)
    hook = get_hook("DecisionTransformer")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 2
    mean_reward = 0
    
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="DecisionTransformer", method_params={}, duration_steps=500)
        _ = runner.run()
        
        # Train a bit after episode
        num_updates = len(agent.memory) // agent.batch_size
        if num_updates < 1:
            num_updates = 1
        for _ in range(num_updates):
            agent.train_step()
            
        mean_reward += hook.episode_reward
        
    return mean_reward / num_episodes

def train_best_model(best_params):
    print("Training final model with best params:", best_params)
    
    state_dim = 5
    action_dim = 16
    
    agent = DTAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        lr=best_params["lr"],
        gamma=best_params["gamma"],
        batch_size=best_params["batch_size"]
    )
    
    hook = get_hook("DecisionTransformer")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 5
    
    with open('dt_train_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Loss', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    for ep in range(num_episodes):
        hook.reset_episode()
        print(f"Starting Episode {ep+1}/{num_episodes}...")
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="DecisionTransformer", method_params={}, duration_steps=1000)
        metrics = runner.run()
        
        t_loss = 0
        num_updates = len(agent.memory) // agent.batch_size
        if num_updates < 1:
            num_updates = 1
        for _ in range(num_updates):
            l = agent.train_step()
            t_loss += l
        t_loss /= num_updates
            
        ep_reward = hook.episode_reward
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1} | Reward: {ep_reward:.2f}")
        print(f"Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open('dt_train_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, t_loss, aoi, cbr, pdr])
            
    # Evaluation run
    print("Running final evaluation...")
    hook.is_training = False
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=99, method="DecisionTransformer", method_params={}, duration_steps=3000)
    final_metrics = runner.run()
    
    agent.save("dt_model.pth")
    print("Training finished, model saved to dt_model.pth")
    
    print("Final Evaluation Metrics:")
    print(f"AoI: {final_metrics.get('AoI_mean', 0.0):.4f}")
    print(f"CBR: {final_metrics.get('CBR_mean', 0.0):.4f}")
    print(f"PDR: {final_metrics.get('PDR_mean', 0.0):.4f}")
    
    return final_metrics

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=5)
    print("Best Params found:", study.best_params)
    
    metrics = train_best_model(study.best_params)
    with open('dt_eval_metrics.json', 'w') as f:
        json.dump(metrics, f)
