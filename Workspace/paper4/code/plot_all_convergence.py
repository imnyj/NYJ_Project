import pandas as pd
import matplotlib.pyplot as plt
import os

model_configs = {
    "Q-Learning": {"file": "qlearning_train_log.csv", "color": "#D3D3D3", "style": "-", "marker": ".", "lw": 1.5, "zorder": 2},
    "SARSA": {"file": "sarsa_train_log.csv", "color": "#A9A9A9", "style": "-", "marker": ",", "lw": 1.5, "zorder": 2},
    "Actor-Critic": {"file": "actor_critic_train_log.csv", "color": "#808080", "style": "-", "marker": "1", "lw": 1.5, "zorder": 2},
    "Vanilla DQN": {"file": "dqn_train_log.csv", "color": "#87CEEB", "style": "-", "marker": "s", "lw": 1.5, "zorder": 3},
    "PPO": {"file": "ppo_train_log.csv", "color": "#0000FF", "style": "-", "marker": "p", "lw": 1.5, "zorder": 3},
    "DDPG": {"file": "ddpg_train_log.csv", "color": "#000080", "style": "-", "marker": "h", "lw": 1.5, "zorder": 3},
    "Double DQN": {"file": "ddqn_train_log.csv", "color": "#00FFFF", "style": "-", "marker": "+", "lw": 1.5, "zorder": 4},
    "TD3": {"file": "td3_train_log.csv", "color": "#008080", "style": "-", "marker": "d", "lw": 1.5, "zorder": 4},
    "Decision Transformer": {"file": "dt_train_log.csv", "color": "#90EE90", "style": "-", "marker": "*", "lw": 1.5, "zorder": 5},
    "SAC": {"file": "sac_train_log.csv", "color": "#FFA500", "style": "-", "marker": "D", "lw": 1.5, "zorder": 5},
    "MAPPO": {"file": "mappo_train_log.csv", "color": "#808000", "style": "-", "marker": "o", "lw": 1.5, "zorder": 5},
    "REMO-DQN": {"file": "resnet_train_log.csv", "color": "#FF0000", "style": "-", "marker": "*", "lw": 3.5, "zorder": 10},
}

plt.figure(figsize=(10, 6))

for name, config in model_configs.items():
    if os.path.exists(config["file"]):
        try:
            df = pd.read_csv(config["file"])
            if 'Episode' in df.columns and 'Reward' in df.columns:
                plt.plot(df['Episode'], df['Reward'], label=name, color=config["color"], 
                         linestyle=config["style"], marker=config["marker"], 
                         linewidth=config["lw"], zorder=config["zorder"])
        except Exception as e:
            print(f"Failed to plot {name}: {e}")

plt.title('RL Models Convergence Curve (Cumulative Reward)')
plt.xlabel('Episode')
plt.ylabel('Cumulative Reward')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=1)
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
os.makedirs("../paper/data/plots", exist_ok=True)
plt.savefig("../paper/data/plots/fig_all_convergence.png", dpi=300)
print("Convergence plots saved to ../paper/data/plots/fig_all_convergence.png")
