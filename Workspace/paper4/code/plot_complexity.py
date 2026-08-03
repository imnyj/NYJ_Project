import matplotlib.pyplot as plt
import numpy as np
import os

OUT_DIR = "/home/imnyj/papers/paper4/paper/data/plots"
os.makedirs(OUT_DIR, exist_ok=True)

models = ['TinyMLP (Proposed)', 'DecTree', 'StdMLP']
params = [89, 450, 9289]       # Approx parameters/nodes
flops = [178, 450, 18578]       # Approx FLOPs

x = np.arange(len(models))
width = 0.35

fig, ax1 = plt.subplots(figsize=(8, 5))

color1 = 'tab:blue'
ax1.set_xlabel('AI Models')
ax1.set_ylabel('Number of Parameters', color=color1)
bars1 = ax1.bar(x - width/2, params, width, label='Parameters', color=color1)
ax1.tick_params(axis='y', labelcolor=color1)

ax2 = ax1.twinx()
color2 = 'tab:orange'
ax2.set_ylabel('FLOPs', color=color2)
bars2 = ax2.bar(x + width/2, flops, width, label='FLOPs', color=color2)
ax2.tick_params(axis='y', labelcolor=color2)

ax1.set_xticks(x)
ax1.set_xticklabels(models)
ax1.set_title('Edge Computational Complexity Comparison')

def autolabel(rects, ax):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  
                    textcoords="offset points",
                    ha='center', va='bottom')

autolabel(bars1, ax1)
autolabel(bars2, ax2)

fig.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_complexity.png"), dpi=300)
print("Complexity plot saved.")
