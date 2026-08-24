#!/usr/bin/env python3
import os
import sys

_code_dir = os.path.dirname(os.path.abspath(__file__))

template = """#!/usr/bin/env python3
import optuna
import csv
import os
import sys
import torch
import numpy as np

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from sim_engine import SimulationRunner
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM
from {agent_module} import {agent_class}

def objective(trial):
{params_code}
    
    agent = {agent_class}(
{init_args}
    )
    
    hook = get_hook("{hook_name}")
    hook.set_agent(agent)
    
    # --- TRAINING PHASE ---
    hook.is_training = True
    num_episodes = 2
    for ep in range(num_episodes):
        hook.reset_episode()
        runner = SimulationRunner(
            scenario="urban_grid", 
            n_vehicles=10, 
            seed=42 + ep + trial.number * 10, 
            method="{hook_name}", 
            method_params={{}}, 
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
            seed=100 + ep + trial.number * 10, 
            method="{hook_name}", 
            method_params={{}}, 
            duration_steps=200
        )
        runner.run()
        eval_rewards.append(hook.episode_reward)
        
    return float(np.mean(eval_rewards))

def main():
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(direction="maximize", study_name="{hook_name}", sampler=sampler)
    study.optimize(objective, n_trials=15)
    
    print(f"[{hook_name}] Best params:", study.best_params)
    
    output_dir = os.environ.get("OPTUNA_DIR", os.path.join(_project_root, "data", "optuna"))
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "best_params_{hook_name}.csv")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Value"])
        for key, value in study.best_params.items():
            writer.writerow([key, value])
            
    print(f"[{hook_name}] Best parameters saved to {{output_file}}")

if __name__ == "__main__":
    main()
"""

definitions = {
    "optuna_remo_dqn.py": {
        "agent_module": "resnet_moe_agent",
        "agent_class": "ResNetMoEAgent",
        "hook_name": "REMO-DQN",
        "params": [
            'num_experts = trial.suggest_int("num_experts", 2, 4)',
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])',
            'target_update_freq = trial.suggest_categorical("target_update_freq", [1, 2, 5])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM", "num_experts=num_experts",
            "lr=lr", "gamma=gamma",
            "batch_size=batch_size", "buffer_size=buffer_size",
            "target_update_freq=target_update_freq"
        ]
    },
    "optuna_moe_dqn.py": {
        "agent_module": "moe_agent",
        "agent_class": "MoEAgent",
        "hook_name": "MoEDQN",
        "params": [
            'num_experts = trial.suggest_int("num_experts", 2, 4)',
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])',
            'target_update_freq = trial.suggest_categorical("target_update_freq", [1, 2, 5])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM", "num_experts=num_experts",
            "lr=lr", "gamma=gamma",
            "batch_size=batch_size", "buffer_size=buffer_size",
            "target_update_freq=target_update_freq"
        ]
    },
    "optuna_dueling_dqn.py": {
        "agent_module": "dueling_dqn_agent",
        "agent_class": "DuelingDQNAgent",
        "hook_name": "DuelingDQN",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])',
            'target_update_freq = trial.suggest_categorical("target_update_freq", [1, 2, 5])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma",
            "batch_size=batch_size", "buffer_size=buffer_size",
            "target_update_freq=target_update_freq"
        ]
    },
    "optuna_ddqn.py": {
        "agent_module": "ddqn_agent",
        "agent_class": "DDQNAgent",
        "hook_name": "DoubleDQN",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])',
            'target_update_freq = trial.suggest_categorical("target_update_freq", [1, 2, 5])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma",
            "batch_size=batch_size", "buffer_size=buffer_size",
            "target_update_freq=target_update_freq"
        ]
    },
    "optuna_vanilla_dqn.py": {
        "agent_module": "dqn_agent",
        "agent_class": "DQNAgent",
        "hook_name": "VanillaDQN",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])',
            'target_update_freq = trial.suggest_categorical("target_update_freq", [1, 2, 5])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma",
            "batch_size=batch_size", "buffer_size=buffer_size",
            "target_update_freq=target_update_freq"
        ]
    },
    "optuna_ppo.py": {
        "agent_module": "ppo_agent",
        "agent_class": "PPOAgent",
        "hook_name": "PPO",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'eps_clip = trial.suggest_float("eps_clip", 0.1, 0.3)',
            'k_epochs = trial.suggest_int("k_epochs", 3, 10)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma", "eps_clip=eps_clip", "k_epochs=k_epochs",
            "batch_size=batch_size", "buffer_size=buffer_size"
        ]
    },
    "optuna_mappo.py": {
        "agent_module": "mappo_agent",
        "agent_class": "MAPPOAgent",
        "hook_name": "MAPPO",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'eps_clip = trial.suggest_float("eps_clip", 0.1, 0.3)',
            'k_epochs = trial.suggest_int("k_epochs", 3, 10)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])'
        ],
        "args": [
            "local_state_dim=5", "global_state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma", "eps_clip=eps_clip", "k_epochs=k_epochs",
            "batch_size=batch_size", "buffer_size=buffer_size"
        ]
    },
    "optuna_sac.py": {
        "agent_module": "sac_agent",
        "agent_class": "SACAgent",
        "hook_name": "SAC",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'tau = trial.suggest_float("tau", 0.001, 0.01)',
            'alpha = trial.suggest_float("alpha", 0.05, 0.5)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma", "tau=tau", "alpha=alpha",
            "batch_size=batch_size", "buffer_size=buffer_size"
        ]
    },
    "optuna_ddpg.py": {
        "agent_module": "ddpg_agent",
        "agent_class": "DDPGAgent",
        "hook_name": "DDPG",
        "params": [
            'lr_actor = trial.suggest_float("lr_actor", 1e-5, 1e-2, log=True)',
            'lr_critic = trial.suggest_float("lr_critic", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'tau = trial.suggest_float("tau", 0.001, 0.01)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr_actor=lr_actor", "lr_critic=lr_critic", "gamma=gamma", "tau=tau",
            "batch_size=batch_size", "buffer_size=buffer_size"
        ]
    },
    "optuna_td3.py": {
        "agent_module": "td3_agent",
        "agent_class": "TD3Agent",
        "hook_name": "TD3",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'tau = trial.suggest_float("tau", 0.001, 0.01)',
            'policy_delay = trial.suggest_int("policy_delay", 1, 3)',
            'target_noise = trial.suggest_float("target_noise", 0.1, 0.3)',
            'noise_clip = trial.suggest_float("noise_clip", 0.3, 0.7)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma", "tau=tau", "policy_delay=policy_delay",
            "target_noise=target_noise", "noise_clip=noise_clip",
            "batch_size=batch_size", "buffer_size=buffer_size"
        ]
    },
    "optuna_actor_critic.py": {
        "agent_module": "actor_critic_agent",
        "agent_class": "ActorCriticAgent",
        "hook_name": "ActorCritic",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma",
            "batch_size=batch_size", "buffer_size=buffer_size"
        ]
    },
    "optuna_dt.py": {
        "agent_module": "dt_agent",
        "agent_class": "DTAgent",
        "hook_name": "DecisionTransformer",
        "params": [
            'lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'batch_size = trial.suggest_categorical("batch_size", [32, 64, 128])',
            'buffer_size = trial.suggest_categorical("buffer_size", [10000, 50000, 100000])'
        ],
        "args": [
            "state_dim=5", "action_dim=ACTION_DIM",
            "lr=lr", "gamma=gamma",
            "batch_size=batch_size", "buffer_size=buffer_size"
        ]
    },
    "optuna_qlearning.py": {
        "agent_module": "qlearning_agent",
        "agent_class": "QLearningAgent",
        "hook_name": "QLearning",
        "params": [
            'alpha = trial.suggest_float("alpha", 0.01, 0.5)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'epsilon_decay = trial.suggest_float("epsilon_decay", 0.90, 0.999)'
        ],
        "args": [
            "state_bins=[10,10,10,10,10]", "action_dim=ACTION_DIM",
            "alpha=alpha", "gamma=gamma", "epsilon_decay=epsilon_decay"
        ]
    },
    "optuna_sarsa.py": {
        "agent_module": "sarsa_agent",
        "agent_class": "SARSAAgent",
        "hook_name": "SARSA",
        "params": [
            'alpha = trial.suggest_float("alpha", 0.01, 0.5)',
            'gamma = trial.suggest_float("gamma", 0.90, 0.999)',
            'epsilon_decay = trial.suggest_float("epsilon_decay", 0.90, 0.999)'
        ],
        "args": [
            "state_bins=[10,10,10,10,10]", "action_dim=ACTION_DIM",
            "alpha=alpha", "gamma=gamma", "epsilon_decay=epsilon_decay"
        ]
    }
}

for filename, config in definitions.items():
    params_str = "\n".join([f"    {p}" for p in config["params"]])
    args_str = ",\n".join([f"        {a}" for a in config["args"]])
    
    code = template.format(
        agent_module=config["agent_module"],
        agent_class=config["agent_class"],
        hook_name=config["hook_name"],
        params_code=params_str,
        init_args=args_str
    )
    target_path = os.path.join(_code_dir, filename)
    with open(target_path, 'w') as f:
        f.write(code)
    print(f"Generated: {target_path}")

print("All individual Optuna scripts regenerated with ACTION_DIM=24.")
