#!/usr/bin/env python3
import os
import sys
import csv
import random
import argparse
import shutil
import torch
import numpy as np

# Ensure code directory is in sys.path
_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

from sim_engine import SimulationRunner
from resnet_moe_agent import ResNetMoEAgent
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM

def train(num_episodes=100, seed=42, duration_steps=2000,
          output_model="data/models/resnet_moe_dqn.pth",
          output_log="data/models/REMO-DQN_convergence.csv",
          epsilon_decay=0.95, min_epsilon=0.01):
    """
    Train ResNetMoEDQN (Proposed REMO-DQN) agent on Urban Grid DCC scenario.
    Default: 100 episodes, duration_steps=2000, epsilon_decay=0.95 (1.0 -> 0.01 across 100 episodes).
    Dynamic density: random.choice([30, 50, 100]) per episode.
    """
    # Seed everything
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    project_root = os.path.abspath(os.path.join(_cur_dir, ".."))

    agent = ResNetMoEAgent(
        state_dim=5,
        action_dim=ACTION_DIM,
        num_experts=3,
        hidden_dim=128,
        epsilon_start=1.0,
        epsilon_end=min_epsilon,
        epsilon_decay=epsilon_decay,
        buffer_size=100000,
        batch_size=64
    )
    hook = get_hook("ResNetMoEDQN")
    hook.set_agent(agent)
    hook.is_training = True

    # Helper function to resolve relative paths
    def resolve_path(p):
        if os.path.isabs(p):
            return p
        # Check if relative to current working directory or project root
        return os.path.abspath(os.path.join(project_root, p))

    primary_log_path = resolve_path(output_log)
    
    # Configure all required log target paths
    log_targets = [primary_log_path]
    std_conv_log = os.path.join(project_root, "data", "models", "REMO-DQN_convergence.csv")
    code_local_log = os.path.join(_cur_dir, "resnet_train_log.csv")
    
    for l_path in [std_conv_log, code_local_log]:
        abs_l = os.path.abspath(l_path)
        if abs_l not in [os.path.abspath(f) for f in log_targets]:
            log_targets.append(abs_l)

    csv_header = ['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean', 'Loss', 'Epsilon', 'Density']

    for log_path in log_targets:
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        with open(log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_header)

    # Configure all required model checkpoint target paths
    primary_model_path = resolve_path(output_model)
    model_targets = [primary_model_path]
    std_model_1 = os.path.join(project_root, "data", "models", "resnet_moe_dqn.pth")
    std_model_2 = os.path.join(project_root, "data", "models", "REMO-DQN.pth")
    code_local_model = os.path.join(_cur_dir, "resnet_moe_dqn.pth")
    
    for m_path in [std_model_1, std_model_2, code_local_model]:
        abs_m = os.path.abspath(m_path)
        if abs_m not in [os.path.abspath(p) for p in model_targets]:
            model_targets.append(abs_m)

    print(f"Starting ResNetMoEDQN training: episodes={num_episodes}, duration_steps={duration_steps}, epsilon_decay={epsilon_decay}, min_eps={min_epsilon}")
    print(f"Primary log: {primary_log_path}")
    print(f"Primary model: {primary_model_path}")

    global_step = 0

    for ep in range(num_episodes):
        hook.reset_episode()
        density = random.choice([30, 50, 100])
        
        print(f"\nStarting Episode {ep+1}/{num_episodes} (Density: {density}, Epsilon: {agent.epsilon:.4f})...")
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=density,
            seed=seed+ep,
            method="ResNetMoEDQN",
            method_params={'n_vehicles_sweep': density},
            duration_steps=duration_steps
        )
        metrics = runner.run()
        
        # Policy update
        losses = []
        num_updates = max(1, len(agent.memory) // agent.batch_size)
        for _ in range(num_updates):
            loss = agent.train_step()
            if loss > 0.0:
                losses.append(loss)
                
        agent.update_target_network()
        
        # Decay epsilon once per episode
        if hasattr(agent, 'update_epsilon'):
            agent.update_epsilon()
        
        avg_loss = float(np.mean(losses)) if losses else 0.0
        ep_reward = hook.episode_reward
        steps_val = metrics.get('steps', duration_steps)
        global_step += steps_val
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1}/{num_episodes} | Step: {global_step} | Reward: {ep_reward:.2f} | Loss: {avg_loss:.4f} | Epsilon: {agent.epsilon:.4f} | Density: {density}")
        print(f"  Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        row_data = [ep+1, global_step, ep_reward, aoi, cbr, pdr, avg_loss, agent.epsilon, density]
        for log_path in log_targets:
            with open(log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
                f.flush()
                
        # Periodic checkpoint save (every 10 episodes and final)
        if (ep + 1) % 10 == 0 or (ep + 1) == num_episodes:
            for m_path in model_targets:
                m_dir = os.path.dirname(m_path)
                if m_dir and not os.path.exists(m_dir):
                    os.makedirs(m_dir, exist_ok=True)
                agent.save(m_path)
            print(f"Checkpoint saved at episode {ep+1} to {primary_model_path}")
            
    print(f"\nTraining finished successfully across {num_episodes} episodes ({global_step} steps).")
    return agent

def parse_args():
    parser = argparse.ArgumentParser(description="Train ResNetMoEDQN (REMO-DQN) on Urban Grid DCC")
    parser.add_argument("--episodes", type=int, default=100, help="Number of training episodes (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed base (default: 42)")
    parser.add_argument("--duration_steps", type=int, default=2000, help="Steps per episode (default: 2000)")
    parser.add_argument("--epsilon_decay", type=float, default=0.95, help="Epsilon decay rate per episode (default: 0.95)")
    parser.add_argument("--min_epsilon", type=float, default=0.01, help="Minimum exploration epsilon (default: 0.01)")
    parser.add_argument("--output_model", type=str, default="data/models/resnet_moe_dqn.pth", help="Output model checkpoint path")
    parser.add_argument("--output_log", type=str, default="data/models/REMO-DQN_convergence.csv", help="Output CSV log file path")
    return parser.parse_args()

def main():
    args = parse_args()
    train(
        num_episodes=args.episodes,
        seed=args.seed,
        duration_steps=args.duration_steps,
        output_model=args.output_model,
        output_log=args.output_log,
        epsilon_decay=args.epsilon_decay,
        min_epsilon=args.min_epsilon
    )

if __name__ == "__main__":
    main()
