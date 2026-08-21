#!/usr/bin/env python3
import os
import sys
import csv
import argparse
import torch
import numpy as np

from sim_engine import SimulationRunner
from ddqn_agent import DDQNAgent
from ai_dcc_hook import get_hook
from etsi_cam_layer import ACTION_DIM

def train(num_episodes=500, seed=42, duration_steps=1000,
          output_model="ddqn.pth", output_log="ddqn_train_log.csv",
          epsilon_decay=0.995, min_epsilon=0.01):
    """
    Train DoubleDQN agent on Urban Grid DCC scenario.
    Default: 500 episodes, epsilon_decay=0.995 (1.0 -> 0.082 across 500 episodes).
    """
    agent = DDQNAgent(
        state_dim=5,
        action_dim=ACTION_DIM,
        epsilon_start=1.0,
        epsilon_end=min_epsilon,
        epsilon_decay=epsilon_decay,
        buffer_size=100000,
        batch_size=64
    )
    hook = get_hook("DoubleDQN")
    hook.set_agent(agent)
    hook.is_training = True

    log_dir = os.path.dirname(output_log)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    with open(output_log, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Loss', 'Epsilon', 'Steps', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    print(f"Starting DoubleDQN training: episodes={num_episodes}, epsilon_decay={epsilon_decay}, min_eps={min_epsilon}")

    for ep in range(num_episodes):
        hook.reset_episode()
        
        print(f"Starting Episode {ep+1}/{num_episodes} (Epsilon: {agent.epsilon:.4f})...")
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=50,
            seed=seed+ep,
            method="DoubleDQN",
            method_params={},
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
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1}/{num_episodes} | Reward: {ep_reward:.2f} | Loss: {avg_loss:.4f} | Epsilon: {agent.epsilon:.4f} | Steps: {steps_val}")
        print(f"  Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open(output_log, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, avg_loss, agent.epsilon, steps_val, aoi, cbr, pdr])
            
    # Save trained weights
    model_dir = os.path.dirname(output_model)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
    agent.save(output_model)
    print(f"Training finished. Model saved to {output_model}, Log saved to {output_log}")
    return agent

def parse_args():
    parser = argparse.ArgumentParser(description="Train DoubleDQN on Urban Grid DCC")
    parser.add_argument("--episodes", type=int, default=500, help="Number of training episodes (default: 500)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed base (default: 42)")
    parser.add_argument("--duration_steps", type=int, default=1000, help="Steps per episode (default: 1000)")
    parser.add_argument("--epsilon_decay", type=float, default=0.995, help="Epsilon decay rate per episode (default: 0.995)")
    parser.add_argument("--min_epsilon", type=float, default=0.01, help="Minimum exploration epsilon (default: 0.01)")
    parser.add_argument("--output_model", type=str, default="ddqn.pth", help="Output model checkpoint path")
    parser.add_argument("--output_log", type=str, default="ddqn_train_log.csv", help="Output CSV log file path")
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
