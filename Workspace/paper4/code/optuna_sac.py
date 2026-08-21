import optuna
import csv
import os
import torch
import numpy as np

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook
from sac_agent import SACAgent

def objective(trial):
    lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)
    gamma = trial.suggest_float("gamma", 0.9, 0.999)
    tau = trial.suggest_float("tau", 0.001, 0.01)
    alpha = trial.suggest_float("alpha", 0.05, 0.5)
    batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])
    buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])
    
    agent = SACAgent(
        state_dim=5,
        action_dim=16,
        lr=lr,
        gamma=gamma,
        tau=tau,
        alpha=alpha,
        batch_size=batch_size,
        buffer_size=buffer_size
    )
    
    hook = get_hook("SAC")
    hook.set_agent(agent)
    
    # --- TRAINING PHASE ---
    hook.is_training = True
    num_episodes = 2
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(
            scenario="urban_grid", 
            n_vehicles=10, 
            seed=42+ep, 
            method="SAC", 
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
            seed=100+ep, 
            method="SAC", 
            method_params={}, 
            duration_steps=200
        )
        runner.run()
        eval_rewards.append(hook.episode_reward)
        
    return np.mean(eval_rewards)

def main():
    study = optuna.create_study(direction="maximize", study_name="SAC")
    study.optimize(objective, n_trials=2)
    
    print("Best params:", study.best_params)
    
    code_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(code_dir)
    output_dir = os.environ.get("OPTUNA_DIR", os.path.join(project_root, "data", "optuna"))
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "best_params_SAC.csv")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Value"])
        for key, value in study.best_params.items():
            writer.writerow([key, value])
            
    print(f"Best parameters saved to {output_file}")

if __name__ == "__main__":
    main()
