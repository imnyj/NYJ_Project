import os
import csv
import torch
import numpy as np
import traceback
import sys
import gc
import shutil

# Append path to make sure imports work
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
from resnet_moe_agent import ResNetMoEAgent

OPTUNA_DIR = "/home/imnyj/Workspace/paper4/data/optuna"
MODELS_DIR = "/home/imnyj/Workspace/paper4/data/models"
EVAL_DIR = "/home/imnyj/Workspace/paper4/data/evaluation"
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(EVAL_DIR, exist_ok=True)

rl_methods = [
    ("QLearning", "QLearning"),
    ("SARSA", "SARSA"),
    ("ActorCritic", "ActorCritic"),
    ("VanillaDQN", "VanillaDQN"),
    ("DoubleDQN", "DoubleDQN"),
    ("DuelingDQN", "DuelingDQN"),
    ("DDPG", "DDPG"),
    ("PPO", "PPO"),
    ("SAC", "SAC"),
    ("TD3", "TD3"),
    ("DecisionTransformer", "DecisionTransformer"),
    ("MAPPO", "MAPPO"),
    ("MoEDQN", "MoEDQN"),
    ("REMO-DQN", "ResNetMoEDQN"),  # proposed method
]

heuristic_methods = ["Proposed", "StdMLP", "DecTree", "ReactDCC", "AdaptDCC", "Heuristic", "Fixed10Hz"]

def load_optuna_params(method_name):
    # Some files use real method name, some use alias like "REMO-DQN". We will try both.
    csv_path = os.path.join(OPTUNA_DIR, f"best_params_{method_name}.csv")
    if method_name == "REMO-DQN" and not os.path.exists(csv_path):
        csv_path = os.path.join(OPTUNA_DIR, f"best_params_ResNetMoEDQN.csv")
    
    params = {}
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader) 
            for row in reader:
                if len(row) == 2:
                    k, v = row
                    try:
                        f_v = float(v)
                        if f_v.is_integer() and k in ['batch_size', 'hidden_dim', 'buffer_size', 'num_experts', 'max_depth']:
                            params[k] = int(f_v)
                        else:
                            params[k] = f_v
                    except:
                        params[k] = v
    return params

def create_agent(method_name, state_dim=5, action_dim=16):
    params = load_optuna_params(method_name)
    
    def get_p(key, default):
        return params.get(key, default)

    if method_name == "QLearning":
        return QLearningAgent(state_bins=[10,10,10,10,10], action_dim=action_dim, alpha=get_p('alpha', 0.1), gamma=get_p('gamma', 0.99), epsilon_decay=get_p('epsilon_decay', 0.995))
    elif method_name == "SARSA":
        return SARSAAgent(state_bins=[10,10,10,10,10], action_dim=action_dim, alpha=get_p('alpha', 0.1), gamma=get_p('gamma', 0.99), epsilon_decay=get_p('epsilon_decay', 0.995))
    elif method_name == "ActorCritic":
        return ActorCriticAgent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "VanillaDQN":
        return DQNAgent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "DoubleDQN":
        return DDQNAgent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "DuelingDQN":
        return DuelingDQNAgent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "DDPG":
        return DDPGAgent(state_dim=state_dim, action_dim=action_dim, lr_actor=get_p('lr_actor', 1e-4), lr_critic=get_p('lr_critic', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "PPO":
        return PPOAgent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 3e-4), gamma=get_p('gamma', 0.99))
    elif method_name == "SAC":
        return SACAgent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 3e-4), gamma=get_p('gamma', 0.99))
    elif method_name == "TD3":
        return TD3Agent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "DecisionTransformer":
        return DTAgent(state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "MAPPO":
        return MAPPOAgent(local_state_dim=state_dim, global_state_dim=state_dim, action_dim=action_dim, lr=get_p('lr', 3e-4), gamma=get_p('gamma', 0.99))
    elif method_name == "MoEDQN":
        return MoEAgent(state_dim=state_dim, action_dim=action_dim, num_experts=get_p('num_experts', 2), lr=get_p('lr', 1e-3), gamma=get_p('gamma', 0.99))
    elif method_name == "REMO-DQN":
        return ResNetMoEAgent(state_dim=state_dim, action_dim=action_dim, num_experts=get_p('num_experts', 3), hidden_dim=get_p('hidden_dim', 128), batch_size=get_p('batch_size', 64))
    else:
        raise ValueError(f"Unknown RL method {method_name}")

def train_all():
    print("=== PART 1: Training Convergence ===")
    
    TOTAL_EPISODES = 100
    STEPS_PER_EP = 2000
    
    for name, hook_name in rl_methods:
        # Check if already trained to save time, if desired, but we'll re-train if requested or not exists
        ext = ".pkl" if name in ["QLearning", "SARSA"] else ".pth"
        model_path = os.path.join(MODELS_DIR, f"{name}{ext}")
        log_path = os.path.join(MODELS_DIR, f"{name}_convergence.csv")
        
        if os.path.exists(model_path) and os.path.exists(log_path):
            print(f"[{name}] Already trained. Skipping...")
            continue
            
        try:
            print(f"--- Training {name} ---")
            agent = create_agent(name)
            hook = get_hook(hook_name)
            hook.set_agent(agent)
            hook.is_training = True
            
            with open(log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean'])
                
            global_step = 0
            for ep in range(TOTAL_EPISODES):
                hook.reset_episode()
                runner = SimulationRunner(
                    scenario="urban_grid",
                    n_vehicles=50,
                    seed=42 + ep,
                    method=hook_name,
                    method_params={},
                    duration_steps=STEPS_PER_EP
                )
                metrics = runner.run()
                global_step += STEPS_PER_EP
                
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
                    agent.update_target_network()
                    
                ep_reward = hook.episode_reward
                aoi = metrics.get('AoI_mean', 0.0)
                cbr = metrics.get('CBR_mean', 0.0)
                pdr = metrics.get('PDR_mean', 0.0)
                
                with open(log_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([ep+1, global_step, ep_reward, aoi, cbr, pdr])
                
                if (ep + 1) % 10 == 0:
                    print(f"[{name}] Ep {ep+1}/{TOTAL_EPISODES} - Reward: {ep_reward:.2f}")
                
            agent.save(model_path)
            print(f"Saved {name} to {model_path}")
            
            del agent
            gc.collect()
            
        except Exception as e:
            print(f"Error training {name}: {e}")
            traceback.print_exc()

def run_evaluation(sweep_name, sweep_var_name, sweep_values, eval_methods_info, duration_steps=1000):
    out_file = os.path.join(EVAL_DIR, f"eval_{sweep_name}_results.csv")
    file_exists = os.path.isfile(out_file)
    with open(out_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "method", sweep_var_name, "seed", "runtime_sec", 
                "n_cam_events", "Reward", "CBR_mean", "AoI_mean", "PDR_mean", 
                "energy_efficiency", "ETSI_compliance"
            ])
            
        print(f"\nStarting {sweep_name} Sweep Simulations...")
        for val in sweep_values:
            print(f"========== RUNNING {sweep_name.upper()}: {val} ==========")
            for method_display, hook_name, method_type in eval_methods_info:
                # Load models explicitly
                agent = None
                if method_type == "RL":
                    agent = create_agent(method_display)
                    ext = ".pkl" if method_display in ["QLearning", "SARSA"] else ".pth"
                    model_path = os.path.join(MODELS_DIR, f"{method_display}{ext}")
                    if os.path.exists(model_path):
                        agent.load(model_path)
                    else:
                        print(f"WARNING: Model {model_path} not found. Using untrained agent for {method_display}.")
                
                # We need to test on multiple seeds
                for seed in [111, 222, 333]:
                    print(f"  -> Method: {method_display}, Seed: {seed}")
                    
                    method_params = {}
                    n_vehicles = 50
                    if sweep_var_name == "density":
                        n_vehicles = val
                        method_params['n_vehicles_sweep'] = val
                    elif sweep_var_name == "speed":
                        method_params['speed'] = val
                        
                    if method_display == "AdaptDCC":
                        method_params['cbr_target'] = 0.60
                        
                    try:
                        # Set up the hook
                        if method_type == "RL" or hook_name in ["Proposed", "StdMLP", "DecTree"]:
                            hook = get_hook(hook_name)
                            if agent is not None:
                                hook.set_agent(agent)
                            hook.is_training = False
                            if hasattr(hook, 'reset_episode'):
                                hook.reset_episode() # FLUSH PREV STATES! (Rule 3)
                        
                        runner = SimulationRunner(
                            scenario='urban_grid',
                            n_vehicles=n_vehicles,
                            seed=seed,
                            method=hook_name,
                            method_params=method_params,
                            duration_steps=duration_steps,
                            warmup_s=30.0
                        )
                        metrics = runner.run()
                        
                        reward = 0.0
                        if method_type == "RL" or hook_name in ["Proposed", "StdMLP", "DecTree"]:
                            hook = get_hook(hook_name)
                            reward = getattr(hook, 'episode_reward', 0.0)
                        
                        writer.writerow([
                            method_display,
                            val,
                            seed,
                            metrics.get("runtime_sec", 0),
                            metrics.get("n_cam_events", 0),
                            reward,
                            metrics.get("CBR_mean", 0),
                            metrics.get("AoI_mean", 0),
                            metrics.get("PDR_mean", 0),
                            metrics.get("energy_efficiency", 0),
                            metrics.get("ETSI_compliance", 0)
                        ])
                        f.flush()
                        
                    except Exception as e:
                        print(f"Error evaluating {method_display} with {sweep_var_name}={val}: {e}")
                        traceback.print_exc()
                        
                # Free memory
                if agent is not None:
                    del agent
                    gc.collect()

def evaluate_all():
    print("=== PART 2: Evaluation Experiments ===")
    
    # Prepare methods info list: (Display_Name, Hook_Name, Type)
    eval_methods_info = []
    for name, hook_name in rl_methods:
        eval_methods_info.append((name, hook_name, "RL"))
    for h in heuristic_methods:
        eval_methods_info.append((h, h, "Heuristic"))
        
    densities = [20, 40, 60, 80, 100, 120]
    run_evaluation("density", "density", densities, eval_methods_info, duration_steps=1000)
    
    speeds = [20, 40, 60, 80, 100]
    run_evaluation("speed", "speed", speeds, eval_methods_info, duration_steps=1000)
    
    print("\n[SUCCESS] Massive data generation completed successfully!")

if __name__ == "__main__":
    train_all()
    evaluate_all()
