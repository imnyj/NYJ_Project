import optuna
import csv
import torch
import numpy as np

from sim_engine import SimulationRunner
from dqn_agent import DQNAgent
from ai_dcc_hook import get_hook

def objective(trial):
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    gamma = trial.suggest_float("gamma", 0.90, 0.99)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    
    agent = DQNAgent(state_dim=5, action_dim=16, lr=lr, gamma=gamma, buffer_size=10000, batch_size=batch_size)
    hook = get_hook("DuelingDQN")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 2
    avg_rewards = []
    
    for ep in range(num_episodes):
        hook.reset_episode()
        # Shorter duration for optuna
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=30, seed=42+ep, method="DuelingDQN", method_params={}, duration_steps=500)
        runner.run()
        
        # Train agent
        num_updates = len(agent.memory) // agent.batch_size
        if num_updates > 50:
            num_updates = 50
            
        for _ in range(num_updates):
            agent.train_step()
                
        agent.update_epsilon()
        agent.update_target_network()
        
        avg_rewards.append(hook.episode_reward)
        
    return np.mean(avg_rewards)

def main():
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=5)
    
    print("Best params:", study.best_params)
    
    # Train final agent
    best_lr = study.best_params["lr"]
    best_gamma = study.best_params["gamma"]
    best_batch_size = study.best_params["batch_size"]
    
    agent = DQNAgent(state_dim=5, action_dim=16, lr=best_lr, gamma=best_gamma, buffer_size=50000, batch_size=best_batch_size)
    hook = get_hook("DuelingDQN")
    hook.set_agent(agent)
    hook.is_training = True
    
    # Run a full training
    num_episodes = 3
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=100+ep, method="DuelingDQN", method_params={}, duration_steps=1000)
        runner.run()
        
        num_updates = len(agent.memory) // agent.batch_size
        if num_updates > 100:
            num_updates = 100
        for _ in range(num_updates):
            agent.train_step()
        agent.update_epsilon()
        agent.update_target_network()
        
    agent.save("vanilla_dqn.pth")
    print("Model saved.")
    
    # Evaluation
    hook.is_training = False
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=999, method="DuelingDQN", method_params={}, duration_steps=2000)
    metrics = runner.run()
    
    aoi = metrics.get('AoI_mean', 0.0)
    cbr = metrics.get('CBR_mean', 0.0)
    pdr = metrics.get('PDR_mean', 0.0)
    
    print(f"EVAL -> PDR: {pdr:.3f}, CBR: {cbr:.3f}, AoI: {aoi:.3f}")

if __name__ == "__main__":
    main()
