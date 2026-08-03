import optuna
import csv
import torch
import numpy as np

from sim_engine import SimulationRunner
from td3_agent import TD3Agent
from ai_dcc_hook import get_hook

def objective(trial):
    lr = trial.suggest_float("lr", 1e-4, 5e-3, log=True)
    gamma = trial.suggest_float("gamma", 0.90, 0.99)
    tau = trial.suggest_float("tau", 0.001, 0.05)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    policy_delay = trial.suggest_int("policy_delay", 1, 4)
    target_noise = trial.suggest_float("target_noise", 0.1, 0.5)
    
    agent = TD3Agent(state_dim=5, action_dim=16, lr=lr, gamma=gamma, tau=tau, batch_size=batch_size, policy_delay=policy_delay, target_noise=target_noise, buffer_size=10000)
    hook = get_hook("TD3")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 2
    avg_rewards = []
    
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=30, seed=42+ep, method="TD3", method_params={}, duration_steps=500)
        runner.run()
        
        for _ in range(int(len(agent.memory) / batch_size)):
            agent.train_step()
        
        avg_rewards.append(hook.episode_reward)
        
    return np.mean(avg_rewards)

def main():
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=5)
    
    print("Best params:", study.best_params)
    
    best_lr = study.best_params["lr"]
    best_gamma = study.best_params["gamma"]
    best_tau = study.best_params["tau"]
    best_batch_size = study.best_params["batch_size"]
    best_policy_delay = study.best_params["policy_delay"]
    best_target_noise = study.best_params["target_noise"]
    
    agent = TD3Agent(state_dim=5, action_dim=16, lr=best_lr, gamma=best_gamma, tau=best_tau, batch_size=best_batch_size, policy_delay=best_policy_delay, target_noise=best_target_noise, buffer_size=50000)
    hook = get_hook("TD3")
    hook.set_agent(agent)
    hook.is_training = True
    
    with open('td3_train_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Loss_Critic', 'Loss_Actor', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    num_episodes = 5
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=100+ep, method="TD3", method_params={}, duration_steps=1000)
        metrics = runner.run()
        
        loss_critic, loss_actor = 0, 0
        train_steps = int(len(agent.memory) / best_batch_size)
        if train_steps > 0:
            for _ in range(train_steps):
                c_loss, a_loss = agent.train_step()
                loss_critic += c_loss
                loss_actor += a_loss
            loss_critic /= train_steps
            loss_actor /= train_steps
            
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        ep_reward = hook.episode_reward
        
        print(f"Episode {ep+1} | Reward: {ep_reward:.2f} | C_Loss: {loss_critic:.4f} | A_Loss: {loss_actor:.4f}")
        print(f"Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open('td3_train_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, loss_critic, loss_actor, aoi, cbr, pdr])
        
    agent.save("td3.pth")
    print("Model saved.")
    
    # Evaluation
    hook.is_training = False
    runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=999, method="TD3", method_params={}, duration_steps=2000)
    metrics = runner.run()
    
    aoi = metrics.get('AoI_mean', 0.0)
    cbr = metrics.get('CBR_mean', 0.0)
    pdr = metrics.get('PDR_mean', 0.0)
    
    print(f"EVAL -> PDR: {pdr:.3f}, CBR: {cbr:.3f}, AoI: {aoi:.3f}")

if __name__ == "__main__":
    main()
