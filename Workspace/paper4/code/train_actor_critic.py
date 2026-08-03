#!/usr/bin/env python3
import os
import csv
import optuna
import numpy as np
import torch

from sim_engine import SimulationRunner
from actor_critic_agent import ActorCriticAgent
from ai_dcc_hook import get_hook

def objective(trial):
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    gamma = trial.suggest_float("gamma", 0.8, 0.99)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    
    agent = ActorCriticAgent(state_dim=5, action_dim=16, lr=lr, gamma=gamma, buffer_size=50000, batch_size=batch_size)
    hook = get_hook("ActorCritic")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 2
    mean_reward = 0
    
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="ActorCritic", method_params={}, duration_steps=500)
        _ = runner.run()
        
        # Train agent
        num_updates = len(agent.memory) // agent.batch_size
        if num_updates > 20:
            num_updates = 20
        for _ in range(num_updates):
            agent.train_step()
            
        mean_reward += hook.episode_reward
        
    return mean_reward / num_episodes

def train_best_model(best_params):
    print("Training final model with best params:", best_params)
    
    agent = ActorCriticAgent(
        state_dim=5,
        action_dim=16,
        lr=best_params["lr"],
        gamma=best_params["gamma"],
        buffer_size=50000,
        batch_size=best_params["batch_size"]
    )
    
    hook = get_hook("ActorCritic")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 5
    
    with open('actor_critic_train_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'ActorLoss', 'CriticLoss', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    for ep in range(num_episodes):
        hook.reset_episode()
        print(f"Starting Episode {ep+1}/{num_episodes}...")
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="ActorCritic", method_params={}, duration_steps=1000)
        metrics = runner.run()
        
        # Train agent
        actor_losses = []
        critic_losses = []
        num_updates = len(agent.memory) // agent.batch_size
        if num_updates > 100:
            num_updates = 100
            
        for _ in range(num_updates):
            aloss, closs = agent.train_step()
            if aloss != 0.0 or closs != 0.0:
                actor_losses.append(aloss)
                critic_losses.append(closs)
                
        ep_reward = hook.episode_reward
        
        avg_aloss = sum(actor_losses)/len(actor_losses) if actor_losses else 0.0
        avg_closs = sum(critic_losses)/len(critic_losses) if critic_losses else 0.0
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1} | Reward: {ep_reward:.2f} | ALoss: {avg_aloss:.4f} | CLoss: {avg_closs:.4f}")
        print(f"Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open('actor_critic_train_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, avg_aloss, avg_closs, aoi, cbr, pdr])
            
    # Evaluation run
    print("Running final evaluation...")
    hook.is_training = False
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=99, method="ActorCritic", method_params={}, duration_steps=3000)
    final_metrics = runner.run()
    
    agent.save("actor_critic.pth")
    print("Training finished, model saved to actor_critic.pth")
    
    print("Final Evaluation Metrics:")
    print(f"AoI: {final_metrics.get('AoI_mean', 0.0):.4f}")
    print(f"CBR: {final_metrics.get('CBR_mean', 0.0):.4f}")
    print(f"PDR: {final_metrics.get('PDR_mean', 0.0):.4f}")
    
    return final_metrics

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=3)
    print("Best Params found:", study.best_params)
    
    train_best_model(study.best_params)
