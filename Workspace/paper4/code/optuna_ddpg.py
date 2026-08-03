#!/usr/bin/env python3
import os
import csv
import optuna
import numpy as np

from sim_engine import SimulationRunner
from ddpg_agent import DDPGAgent
from ai_dcc_hook import get_hook

def objective(trial):
    # Suggest hyperparameters
    lr_actor = trial.suggest_float("lr_actor", 1e-5, 1e-3, log=True)
    lr_critic = trial.suggest_float("lr_critic", 1e-4, 1e-2, log=True)
    gamma = trial.suggest_float("gamma", 0.9, 0.999)
    tau = trial.suggest_float("tau", 0.001, 0.05)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    
    state_dim = 5
    action_dim = 16
    
    agent = DDPGAgent(state_dim=state_dim, action_dim=action_dim, lr_actor=lr_actor, lr_critic=lr_critic, gamma=gamma, tau=tau, batch_size=batch_size)
    hook = get_hook("DDPG")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 2
    mean_reward = 0
    
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="DDPG", method_params={}, duration_steps=500)
        _ = runner.run()
        
        # Train a bit after episode
        for _ in range(50):
            agent.train_step()
            
        mean_reward += hook.episode_reward
        
    return mean_reward / num_episodes

def train_best_model(best_params):
    print("Training final model with best params:", best_params)
    
    state_dim = 5
    action_dim = 16
    
    agent = DDPGAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        lr_actor=best_params["lr_actor"],
        lr_critic=best_params["lr_critic"],
        gamma=best_params["gamma"],
        tau=best_params["tau"],
        batch_size=best_params["batch_size"]
    )
    
    hook = get_hook("DDPG")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 5
    
    with open('ddpg_train_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'ActorLoss', 'CriticLoss', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    for ep in range(num_episodes):
        hook.reset_episode()
        print(f"Starting Episode {ep+1}/{num_episodes}...")
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="DDPG", method_params={}, duration_steps=1000)
        metrics = runner.run()
        
        a_loss, c_loss = 0, 0
        for _ in range(100):
            al, cl = agent.train_step()
            a_loss += al
            c_loss += cl
            
        ep_reward = hook.episode_reward
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1} | Reward: {ep_reward:.2f}")
        print(f"Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open('ddpg_train_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, a_loss/100, c_loss/100, aoi, cbr, pdr])
            
    # Evaluation run
    print("Running final evaluation...")
    hook.is_training = False
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=99, method="DDPG", method_params={}, duration_steps=3000)
    final_metrics = runner.run()
    
    agent.save("ddpg_model.pth")
    print("Training finished, model saved to ddpg_model.pth")
    
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
    # write to a file so we can parse it easily
    import json
    with open('ddpg_eval_metrics.json', 'w') as f:
        json.dump(metrics, f)
