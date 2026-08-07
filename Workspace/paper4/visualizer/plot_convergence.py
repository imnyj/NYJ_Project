import pandas as pd
import matplotlib.pyplot as plt
import os

DATA_FILE = "/home/imnyj/Workspace/paper4/code/train_log.csv"
OUT_DIR = "/home/imnyj/papers/paper4/paper/data/plots"

df = pd.read_csv(DATA_FILE)

fig, ax1 = plt.subplots(figsize=(8, 6))

color = 'tab:red'
ax1.set_xlabel('Epoch')
ax1.set_ylabel('Loss', color=color)
ax1.plot(df['epoch'], df['train_loss'], color='tab:red', linestyle='-', label='Train Loss')
ax1.plot(df['epoch'], df['val_loss'], color='tab:orange', linestyle='--', label='Val Loss')
ax1.tick_params(axis='y', labelcolor=color)
ax1.grid(True, linestyle=':', alpha=0.6)

ax2 = ax1.twinx()  
color = 'tab:blue'
ax2.set_ylabel('Accuracy', color=color)
ax2.plot(df['epoch'], df['train_acc'], color='tab:blue', linestyle='-', label='Train Acc')
ax2.plot(df['epoch'], df['val_acc'], color='tab:cyan', linestyle='--', label='Val Acc')
ax2.tick_params(axis='y', labelcolor=color)

fig.tight_layout()
fig.legend(loc='upper center', bbox_to_anchor=(0.5, 1.1), ncol=4)
plt.savefig(os.path.join(OUT_DIR, "convergence.png"), bbox_inches='tight', dpi=300)
print("Saved convergence.png")
