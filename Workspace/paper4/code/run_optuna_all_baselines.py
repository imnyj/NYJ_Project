import os
import csv
import optuna
import numpy as np
import traceback
import sys
import argparse

sys.path.append("/home/imnyj/Workspace/paper4/code")

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook

from qlearning_agent import QLearningAgent
from sarsa_agent import SARSAAgent
from actor_critic_agent import ActorCriticAgent
from dqn_agent import DQNAgent
from ddqn_agent import DDQNAgent
from dueling_dqn_agent import DuelingDQNAgent
from ddpg_agent import DDPGAgent
from ppo_agent import PPOAgent
from sac_agent import SACAgent
from td3_agent import TD3Agent
from dt_agent import DTAgent
from mappo_agent import MAPPOAgent
from moe_agent import MoEAgent 

OUTPUT_DIR = "/home/imnyj/Workspace/paper4/data/optuna"
os.makedirs(OUTPUT_DIR, exist_ok=True)

N_TRIALS = 2
TRAIN_EPISODES = 2
EVAL_EPISODES = 1

def run_optimization(method_name, hook_name, factory):
    def objective(trial):
        try:
            agent = factory(trial)
            hook = get_hook(hook_name)
            hook.set_agent(agent)
            
            # --- TRAINING PHASE ---
            hook.is_training = True
            for ep in range(TRAIN_EPISODES):
                hook.reset_episode()
                runner = SimulationRunner(
                    scenario="urban_grid", 
                    n_vehicles=10, 
                    seed=42+ep, 
                    method=hook_name, 
                    method_params={}, 
                    duration_steps=200
                )
                runner.run()
                
                # Perform post-episode updates
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
            for ep in range(EVAL_EPISODES):
                hook.reset_episode()
                runner = SimulationRunner(
                    scenario="urban_grid", 
                    n_vehicles=15, 
                    seed=100+ep, 
                    method=hook_name, 
                    method_params={}, 
                    duration_steps=200
                )
                runner.run()
                eval_rewards.append(hook.episode_reward)
                
            return np.mean(eval_rewards)
            
        except Exception as e:
            print(f"Error in trial for {method_name}: {e}")
            traceback.print_exc()
            raise optuna.exceptions.TrialPruned()

    study = optuna.create_study(direction="maximize", study_name=method_name)
    study.optimize(objective, n_trials=N_TRIALS)
    
    print(f"Best params for {method_name}:", study.best_params)
    
    csv_path = os.path.join(OUTPUT_DIR, f"best_params_{method_name}.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Value"])
        for k, v in study.best_params.items():
            writer.writerow([k, v])
    print(f"Saved to {csv_path}")


def main():
    methods = [
        ("QLearning", "QLearning", lambda t: QLearningAgent(state_bins=[10,10,10,10,10], action_dim=16, 
            alpha=t.suggest_float("alpha", 0.01, 0.5), 
            gamma=t.suggest_float("gamma", 0.9, 0.999), 
            epsilon_decay=t.suggest_float("epsilon_decay", 0.9, 0.999))),
            
        ("SARSA", "SARSA", lambda t: SARSAAgent(state_bins=[10,10,10,10,10], action_dim=16, 
            alpha=t.suggest_float("alpha", 0.01, 0.5), 
            gamma=t.suggest_float("gamma", 0.9, 0.999), 
            epsilon_decay=t.suggest_float("epsilon_decay", 0.9, 0.999))),
            
        ("ActorCritic", "ActorCritic", lambda t: ActorCriticAgent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]))),
            
        ("VanillaDQN", "VanillaDQN", lambda t: DQNAgent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5]))),
            
        ("DoubleDQN", "DoubleDQN", lambda t: DDQNAgent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5]))),
            
        ("DuelingDQN", "DuelingDQN", lambda t: DuelingDQNAgent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5]))),
            
        ("DDPG", "DDPG", lambda t: DDPGAgent(state_dim=5, action_dim=16, 
            lr_actor=t.suggest_float("lr_actor", 1e-5, 1e-2, log=True), 
            lr_critic=t.suggest_float("lr_critic", 1e-5, 1e-2, log=True),
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            tau=t.suggest_float("tau", 0.001, 0.01),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]))),
            
        ("PPO", "PPO", lambda t: PPOAgent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            eps_clip=t.suggest_float("eps_clip", 0.1, 0.3),
            k_epochs=t.suggest_int("k_epochs", 3, 10),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]))),
            
        ("SAC", "SAC", lambda t: SACAgent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            tau=t.suggest_float("tau", 0.001, 0.01),
            alpha=t.suggest_float("alpha", 0.05, 0.5),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]))),
            
        ("TD3", "TD3", lambda t: TD3Agent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            tau=t.suggest_float("tau", 0.001, 0.01),
            policy_delay=t.suggest_int("policy_delay", 1, 3),
            target_noise=t.suggest_float("target_noise", 0.1, 0.3),
            noise_clip=t.suggest_float("noise_clip", 0.3, 0.7),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]))),
            
        ("DecisionTransformer", "DecisionTransformer", lambda t: DTAgent(state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]))),
            
        ("MAPPO", "MAPPO", lambda t: MAPPOAgent(local_state_dim=5, global_state_dim=5, action_dim=16, 
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            eps_clip=t.suggest_float("eps_clip", 0.1, 0.3),
            k_epochs=t.suggest_int("k_epochs", 3, 10),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]))),
            
        ("MoEDQN", "MoEDQN", lambda t: MoEAgent(state_dim=5, action_dim=16, 
            num_experts=t.suggest_int("num_experts", 2, 5),
            lr=t.suggest_float("lr", 1e-5, 1e-2, log=True), 
            gamma=t.suggest_float("gamma", 0.9, 0.999),
            batch_size=t.suggest_categorical("batch_size", [32, 64, 128]),
            buffer_size=t.suggest_categorical("buffer_size", [10000, 50000, 100000]),
            target_update_freq=t.suggest_categorical("target_update_freq", [1, 2, 5])))
    ]

    for name, hook_name, factory in methods:
        print(f"\n--- Optimizing {name} ---")
        run_optimization(name, hook_name, factory)

if __name__ == "__main__":
    main()
