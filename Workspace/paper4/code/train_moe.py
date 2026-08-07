import csv
import torch
import numpy as np

from sim_engine import SimulationRunner
from moe_agent import MoEAgent
from ai_dcc_hook import get_hook

def main():
    agent = MoEAgent(state_dim=5, action_dim=16, num_experts=2, buffer_size=50000, batch_size=64)
    hook = get_hook("MoEDQN")
    hook.set_agent(agent)
    hook.is_training = True

    num_episodes = 5
    
    with open('moe_train_log.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Reward', 'Loss', 'Epsilon', 'AoI_mean', 'CBR_mean', 'PDR_mean'])

    for ep in range(num_episodes):
        hook.reset_episode()
        
        print(f"Starting Episode {ep+1}/{num_episodes}...")
        runner = SimulationRunner(scenario="urban_grid", n_vehicles=50, seed=42+ep, method="MoEDQN", method_params={}, duration_steps=1000)
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
        
        with open('moe_train_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([ep+1, ep_reward, avg_loss, agent.epsilon, aoi, cbr, pdr])
            
    agent.save("moe_dqn.pth")
    print("Training finished, model saved to moe_dqn.pth")

if __name__ == "__main__":
    main()
