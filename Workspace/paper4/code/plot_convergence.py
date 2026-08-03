import pandas as pd
import matplotlib.pyplot as plt
import os

df = pd.read_csv("train_log.csv")

plt.figure(figsize=(8, 5))
plt.plot(df['epoch'], df['train_loss'], label='Train Loss', color='blue', linewidth=2)
plt.plot(df['epoch'], df['val_loss'], label='Val Loss', color='red', linestyle='--', linewidth=2)
plt.title('TinyMLP Convergence (Loss)')
plt.xlabel('Epoch')
plt.ylabel('Cross-Entropy Loss')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig("../paper/data/plots/fig_convergence_loss.png", dpi=300)

plt.figure(figsize=(8, 5))
plt.plot(df['epoch'], df['train_acc']*100, label='Train Accuracy', color='blue', linewidth=2)
plt.plot(df['epoch'], df['val_acc']*100, label='Val Accuracy', color='red', linestyle='--', linewidth=2)
plt.title('TinyMLP Convergence (Accuracy)')
plt.xlabel('Epoch')
plt.ylabel('Accuracy (%)')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig("../paper/data/plots/fig_convergence_acc.png", dpi=300)
print("Convergence plots saved.")
