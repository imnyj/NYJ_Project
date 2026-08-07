import matplotlib.pyplot as plt
import numpy as np
import os

OUT_DIR = "/home/imnyj/papers/paper4/paper/data/plots"
os.makedirs(OUT_DIR, exist_ok=True)

models = ['DecTree', 'TinyMLP', 'StdMLP', 'Vanilla DQN', 'REMO-DQN\n(Proposed)']
params = [450, 89, 9289, 19205, 127253]       # Approx parameters/nodes
flops = [450, 178, 18578, 18944, 126152]       # Approx FLOPs

x = np.arange(len(models))
width = 0.35

fig, ax1 = plt.subplots(figsize=(10, 6))

color1 = 'tab:blue'
ax1.set_xlabel('AI Models')
ax1.set_ylabel('Number of Parameters', color=color1)
bars1 = ax1.bar(x - width/2, params, width, label='Parameters', color=color1)
ax1.tick_params(axis='y', labelcolor=color1)

ax2 = ax1.twinx()
color2 = 'tab:orange'
ax2.set_ylabel('MACs/FLOPs', color=color2)
bars2 = ax2.bar(x + width/2, flops, width, label='MACs/FLOPs', color=color2)
ax2.tick_params(axis='y', labelcolor=color2)

ax1.set_xticks(x)
ax1.set_xticklabels(models)
ax1.set_title('Edge Computational Complexity Comparison')

# Use log scale because REMO-DQN is 100x larger than TinyMLP, 
# otherwise the smaller bars won't be visible.
ax1.set_yscale('log')
ax2.set_yscale('log')

def autolabel(rects, ax):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

autolabel(bars1, ax1)
autolabel(bars2, ax2)

# Adjust y-limits slightly to make room for annotations
ax1.set_ylim(top=max(params) * 5)
ax2.set_ylim(top=max(flops) * 5)

fig.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_complexity.png"), dpi=300)
print("Complexity plot saved.")
