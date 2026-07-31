import optuna
import csv
import torch
import numpy as np

from sim_engine import SimulationRunner
from mappo_agent import MAPPOAgent
from ai_dcc_hook import get_hook

def objective(trial):
    lr = trial.suggest_float("lr", 1e-4, 5e-3, log=True)
    gamma = trial.suggest_float("gamma", 0.90, 0.99)
    eps_clip = trial.suggest_float("eps_clip", 0.1, 0.3)
    k_epochs = trial.suggest_int("k_epochs", 2, 10)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    
    agent = MAPPOAgent(local_state_dim=5, global_state_dim=5, action_dim=16, lr=lr, gamma=gamma, eps_clip=eps_clip, k_epochs=k_epochs, batch_size=batch_size, buffer_size=10000)
    hook = get_hook("MAPPO")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 2
    avg_rewards = []
    
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=30, seed=42+ep, method="MAPPO", method_params={}, duration_steps=500)
        runner.run()
        
        if len(agent.memory) > 0:
            agent.train_step()
        
        avg_rewards.append(hook.episode_reward)
        
    return np.mean(avg_rewards)

def main():
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=5)
    
    print("Best params:", study.best_params)
    
    best_lr = study.best_params["lr"]
    best_gamma = study.best_params["gamma"]
    best_eps_clip = study.best_params["eps_clip"]
    best_k_epochs = study.best_params["k_epochs"]
    best_batch_size = study.best_params["batch_size"]
    
    agent = MAPPOAgent(local_state_dim=5, global_state_dim=5, action_dim=16, lr=best_lr, gamma=best_gamma, eps_clip=best_eps_clip, k_epochs=best_k_epochs, batch_size=best_batch_size, buffer_size=50000)
    hook = get_hook("MAPPO")
    hook.set_agent(agent)
    hook.is_training = True
    
    with open('mappo_train_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Loss', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    num_episodes = 5
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=100+ep, method="MAPPO", method_params={}, duration_steps=1000)
        metrics = runner.run()
        
        loss_actor, loss_critic = 0, 0
        if len(agent.memory) > 0:
            loss_actor, loss_critic = agent.train_step()
            
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        ep_reward = hook.episode_reward
        
        print(f"Episode {ep+1} | Reward: {ep_reward:.2f} | Loss (A/C): {loss_actor:.4f}/{loss_critic:.4f}")
        print(f"Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open('mappo_train_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, loss_actor + loss_critic, aoi, cbr, pdr])
        
    agent.save("mappo.pth")
    print("Model saved.")
    
    # Evaluation
    hook.is_training = False
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=999, method="MAPPO", method_params={}, duration_steps=2000)
    metrics = runner.run()
    
    aoi = metrics.get('AoI_mean', 0.0)
    cbr = metrics.get('CBR_mean', 0.0)
    pdr = metrics.get('PDR_mean', 0.0)
    
    print(f"EVAL -> PDR: {pdr:.3f}, CBR: {cbr:.3f}, AoI: {aoi:.3f}")

if __name__ == "__main__":
    main()
