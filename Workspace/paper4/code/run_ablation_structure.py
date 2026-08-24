#!/usr/bin/env python3
"""
run_ablation_structure.py
=========================
Executes Structure Ablation Study (4 variants):
  1. REMO-DQN   (Variant 1: ResNet + MoE + Dueling)
  2. wo_ResNet   (Variant 2: MLP + MoE + Dueling)
  3. wo_MoE      (Variant 3: ResNet + Dueling, no MoE)
  4. wo_Dueling  (Variant 4: ResNet + MoE + Standard DQN)

Training specs:
  - 100 episodes x 2000 steps (Total 200,000 steps per variant)
  - ACTION_DIM = 24 (4 transmission intervals x 6 transmit powers)
  - Dynamic random density: random.choice([30, 50, 100]) per episode
  - Epsilon decay: 0.95 (1.0 -> 0.01)
  - Target GPU: GPU 3 (cuda:3)
"""

import os
import sys
import csv
import time
import random
import argparse
import numpy as np
import torch

# Ensure code directory is in sys.path
_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

from sim_engine import SimulationRunner
from ablation_agents import AblationAgent
from ai_dcc_hook import ResNetMoEDQNHook, _hooks
from etsi_cam_layer import ACTION_DIM

VARIANTS = [
    (1, "REMO-DQN"),
    (2, "wo_ResNet"),
    (3, "wo_MoE"),
    (4, "wo_Dueling")
]

def train_and_eval_variant(variant_num: int, name: str, num_episodes: int = 100,
                           duration_steps: int = 2000, seed: int = 42,
                           epsilon_decay: float = 0.95, min_epsilon: float = 0.01,
                           device_str: str = "cuda:3"):
    print("\n" + "="*70 + f"\n[Structure Ablation] Starting {name} (Variant {variant_num}) on {device_str}\n" + "="*70)
    
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    project_root = os.path.abspath(os.path.join(_cur_dir, ".."))
    out_dir = os.path.join(project_root, "data", "ablation_structure")
    os.makedirs(out_dir, exist_ok=True)

    state_dim = 5
    action_dim = ACTION_DIM  # 24
    num_experts = 3
    hidden_dim = 128
    buffer_size = 100000
    batch_size = 64

    # Resolve device
    if torch.cuda.is_available() and device_str.startswith("cuda"):
        try:
            device = torch.device(device_str)
            _ = torch.zeros(1, device=device)
        except Exception:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device("cpu")

    agent = AblationAgent(
        variant_type=variant_num,
        state_dim=state_dim,
        action_dim=action_dim,
        num_experts=num_experts,
        hidden_dim=hidden_dim,
        epsilon_start=1.0,
        epsilon_end=min_epsilon,
        epsilon_decay=epsilon_decay,
        buffer_size=buffer_size,
        batch_size=batch_size,
        device=device
    )

    hook = ResNetMoEDQNHook(agent=agent, is_training=True, reward_variant="Base")
    _hooks[name] = hook

    log_file = os.path.join(out_dir, f"{name}_train_log.csv")
    csv_header = ["Episode", "Global_Step", "Reward", "AoI_mean", "CBR_mean", "PDR_mean", "Loss", "Epsilon", "Density"]
    with open(log_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    global_step = 0
    t_start = time.time()

    for ep in range(num_episodes):
        hook.reset_episode()
        density = random.choice([30, 50, 100])
        
        ep_seed = seed + ep
        runner = SimulationRunner(
            scenario="urban_grid",
            n_vehicles=density,
            seed=ep_seed,
            method=name,
            method_params={"n_vehicles_sweep": density},
            duration_steps=duration_steps
        )
        metrics = runner.run()

        # Training updates
        losses = []
        num_updates = max(1, len(agent.memory) // agent.batch_size)
        for _ in range(num_updates):
            loss = agent.train_step()
            if loss > 0.0:
                losses.append(loss)

        agent.update_target_network()

        # Decay epsilon once per episode
        if hasattr(agent, "update_epsilon"):
            agent.update_epsilon()

        avg_loss = float(np.mean(losses)) if losses else 0.0
        ep_reward = hook.episode_reward
        steps_val = metrics.get("steps", duration_steps)
        global_step += steps_val

        aoi = metrics.get("AoI_mean", 0.0)
        cbr = metrics.get("CBR_mean", 0.0)
        pdr = metrics.get("PDR_mean", 0.0)

        if (ep + 1) % 5 == 0 or ep == 0 or (ep + 1) == num_episodes:
            elapsed = time.time() - t_start
            print(f"[{name}] Ep {ep+1:3d}/{num_episodes} | Step: {global_step:6d} | Reward: {ep_reward:9.2f} | "
                  f"Loss: {avg_loss:6.4f} | Eps: {agent.epsilon:.4f} | AoI: {aoi:6.3f} | CBR: {cbr:.3f} | PDR: {pdr:5.1f}% | Elapsed: {elapsed:5.1f}s")

        with open(log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, global_step, ep_reward, aoi, cbr, pdr, avg_loss, agent.epsilon, density])

    # Save trained model
    model_path = os.path.join(out_dir, f"{name}_model.pth")
    agent.save(model_path)
    print(f"[{name}] Training finished. Model saved to {model_path}")

    # Evaluation run
    print(f"[{name}] Running post-training evaluation (2000 steps, seed=100)...")
    hook.is_training = False
    eval_runner = SimulationRunner(
        scenario="urban_grid",
        n_vehicles=50,
        seed=100,
        method=name,
        method_params={},
        duration_steps=duration_steps
    )
    eval_metrics = eval_runner.run()

    eval_file = os.path.join(out_dir, f"{name}_eval_metrics.csv")
    with open(eval_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["AoI_mean", "CBR_mean", "PDR_mean", "CBR_var", "PDR_var", "Total_Bytes_Tx"])
        writer.writerow([
            eval_metrics.get("AoI_mean", 0.0),
            eval_metrics.get("CBR_mean", 0.0),
            eval_metrics.get("PDR_mean", 0.0),
            eval_metrics.get("CBR_var", 0.0),
            eval_metrics.get("PDR_var", 0.0),
            eval_metrics.get("Total_Bytes_Tx", 0.0)
        ])
    print(f"[{name}] Evaluation metrics saved to {eval_file}")

    return eval_metrics


def merge_structure_ablation_csv():
    project_root = os.path.abspath(os.path.join(_cur_dir, ".."))
    out_dir = os.path.join(project_root, "data", "ablation_structure")
    merged_file = os.path.join(project_root, "data", "ablation_structure.csv")

    var_names = ["REMO-DQN", "wo_ResNet", "wo_MoE", "wo_Dueling"]
    logs = {}
    for name in var_names:
        log_p = os.path.join(out_dir, f"{name}_train_log.csv")
        if not os.path.exists(log_p):
            print(f"[Warning] {log_p} does not exist yet. Cannot merge structure ablation CSV.")
            return
        with open(log_p, "r") as f:
            reader = csv.DictReader(f)
            logs[name] = list(reader)

    num_rows = len(logs["REMO-DQN"])
    with open(merged_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Episode", "Global_Step", "REMO-DQN", "wo_ResNet", "wo_MoE", "wo_Dueling"])
        for i in range(num_rows):
            ep = logs["REMO-DQN"][i]["Episode"]
            step = logs["REMO-DQN"][i]["Global_Step"]
            r_remo = logs["REMO-DQN"][i]["Reward"]
            r_nores = logs["wo_ResNet"][i]["Reward"] if i < len(logs["wo_ResNet"]) else ""
            r_nomoe = logs["wo_MoE"][i]["Reward"] if i < len(logs["wo_MoE"]) else ""
            r_noduel = logs["wo_Dueling"][i]["Reward"] if i < len(logs["wo_Dueling"]) else ""
            writer.writerow([ep, step, r_remo, r_nores, r_nomoe, r_noduel])

    print(f"Merged structure ablation CSV saved to: {merged_file} ({num_rows} episodes)")


def main():
    parser = argparse.ArgumentParser(description="Run Structure Ablation Experiments")
    parser.add_argument("--variant", type=str, default="all", choices=["all", "REMO-DQN", "wo_ResNet", "wo_MoE", "wo_Dueling"], help="Specific variant to train or all")
    parser.add_argument("--episodes", type=int, default=100, help="Number of episodes (default: 100)")
    parser.add_argument("--duration_steps", type=int, default=2000, help="Steps per episode (default: 2000)")
    parser.add_argument("--device", type=str, default="cuda:3", help="Target device (default: cuda:3)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    if args.variant == "all":
        for var_num, name in VARIANTS:
            train_and_eval_variant(var_num, name, num_episodes=args.episodes,
                                   duration_steps=args.duration_steps, seed=args.seed,
                                   device_str=args.device)
        merge_structure_ablation_csv()
    else:
        var_dict = {v[1]: v[0] for v in VARIANTS}
        train_and_eval_variant(var_dict[args.variant], args.variant,
                               num_episodes=args.episodes, duration_steps=args.duration_steps,
                               seed=args.seed, device_str=args.device)
        merge_structure_ablation_csv()

if __name__ == "__main__":
    main()
