import os
import csv
import torch
import numpy as np

from sim_engine import SimulationRunner
from ablation_agents import AblationAgent
from ai_dcc_hook import DuelingDQNHook, _hooks

def train_and_eval_variant(state_variant_name):
    print(f"\n{'='*50}\nStarting State Ablation: {state_variant_name}\n{'='*50}")
    
    # Hyperparameters
    state_dim = 5
    action_dim = 16
    num_experts = 3
    hidden_dim = 128
    buffer_size = 50000
    batch_size = 64
    num_episodes = 2
    
    agent = AblationAgent(
        variant_type=1, # Always use REMO-DQN base structure
        state_dim=state_dim, 
        action_dim=action_dim, 
        num_experts=num_experts, 
        hidden_dim=hidden_dim, 
        buffer_size=buffer_size, 
        batch_size=batch_size
    )
    
    class CustomHook(DuelingDQNHook):
        def __init__(self, agent=None, is_training=False, state_variant="Base"):
            super().__init__(agent, is_training, reward_variant="Base", state_variant=state_variant)
            
    # Use a unique method name in _hooks dictionary
    hook_key = f"StateAblation_{state_variant_name}"
    _hooks[hook_key] = CustomHook(state_variant=state_variant_name)
    hook = _hooks[hook_key]
    hook.set_agent(agent)
    hook.is_training = True
    
    log_file = f'/home/imnyj/Workspace/paper4/data/ablation_state/{state_variant_name}_train_log.csv'
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Loss', 'Epsilon', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    for ep in range(num_episodes):
        hook.reset_episode()
        
        print(f"Starting Episode {ep+1}/{num_episodes} for {state_variant_name}...")
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method=hook_key, method_params={}, duration_steps=500)
        
        # Monkeypatch sim_engine's check for method to allow our custom hook_key if needed.
        # It seems etsi_cam_layer checks for specific strings, but run_ablation_reward uses `reward_variant_name` directly (e.g. `wo_R1`).
        # Let's see if we need to modify etsi_cam_layer first. Actually `run_ablation_reward.py` works because `wo_R1` is added to the valid methods list in etsi_cam_layer!
        metrics = runner.run()
        
        losses = []
        num_updates = len(agent.memory) // agent.batch_size
        if num_updates < 1:
            num_updates = 1
            
        for _ in range(num_updates):
            loss = agent.train_step()
            if loss > 0.0:
                losses.append(loss)
            if hasattr(agent, 'update_epsilon'):
                agent.update_epsilon()
        agent.update_target_network()
        
        avg_loss = sum(losses)/len(losses) if losses else 0.0
        ep_reward = hook.episode_reward
        
        aoi = metrics.get('AoI_mean', 0.0)
        cbr = metrics.get('CBR_mean', 0.0)
        pdr = metrics.get('PDR_mean', 0.0)
        
        print(f"Episode {ep+1} | Reward: {ep_reward:.2f} | Loss: {avg_loss:.4f} | Epsilon: {agent.epsilon:.3f}")
        print(f"Metrics -> AoI: {aoi:.3f}, CBR: {cbr:.3f}, PDR: {pdr:.3f}")
        
        with open(log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, avg_loss, agent.epsilon, aoi, cbr, pdr])
            
    # Save model
    model_path = f"/home/imnyj/Workspace/paper4/data/ablation_state/{state_variant_name}_model.pth"
    agent.save(model_path)
    print(f"Training finished, model saved to {model_path}")
    
    # Evaluation run
    print(f"Evaluating {state_variant_name}...")
    hook.is_training = False
    eval_runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=100, method=hook_key, method_params={}, duration_steps=500)
    eval_metrics = eval_runner.run()
    
    eval_file = f'/home/imnyj/Workspace/paper4/data/ablation_state/{state_variant_name}_eval_metrics.csv'
    with open(eval_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['AoI_mean', 'CBR_mean', 'PDR_mean', 'CBR_var', 'PDR_var', 'Total_Bytes_Tx'])
        writer.writerow([
            eval_metrics.get('AoI_mean', 0.0),
            eval_metrics.get('CBR_mean', 0.0),
            eval_metrics.get('PDR_mean', 0.0),
            eval_metrics.get('CBR_var', 0.0),
            eval_metrics.get('PDR_var', 0.0),
            eval_metrics.get('Total_Bytes_Tx', 0.0)
        ])
    print(f"Evaluation metrics saved to {eval_file}")
    
    return eval_metrics

def main():
    os.makedirs('/home/imnyj/Workspace/paper4/data/ablation_state', exist_ok=True)
    
    variants = [
        "Base",
        "wo_Density",
        "wo_CBR",
        "wo_Kinematics"
    ]
    
    all_metrics = {}
    for name in variants:
        metrics = train_and_eval_variant(name)
        all_metrics[name] = metrics
        
    print("\n" + "="*50)
    print("State Ablation Study Summary:")
    print(f"{'Variant':<15} | {'AoI':<8} | {'CBR':<8} | {'PDR':<8}")
    print("-" * 50)
    for name in all_metrics:
        m = all_metrics[name]
        print(f"{name:<15} | {m.get('AoI_mean',0.0):.4f} | {m.get('CBR_mean',0.0):.4f} | {m.get('PDR_mean',0.0):.4f}")

if __name__ == "__main__":
    main()
