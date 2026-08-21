#!/usr/bin/env python3
"""
plot_complexity.py - Edge Computational Complexity Comparison for Paper4 (REMO-DQN).

Plots Parameters and FLOPs/MACs comparison across the 7 benchmark models (ACTION_DIM=24).
"""

import os
import sys
import matplotlib.pyplot as plt
import numpy as np

# Ensure code directory is in sys.path
_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

try:
    from calc_flops import get_all_7_models_stats
    stats_list = get_all_7_models_stats(state_dim=5, action_dim=24)
except Exception:
    stats_list = [
        {"Model": "DecTree", "Parameters": 350, "FLOPs": 20, "MACs": 10},
        {"Model": "StdMLP", "Parameters": 10264, "FLOPs": 20096, "MACs": 10048},
        {"Model": "VanillaDQN", "Parameters": 20376, "FLOPs": 40192, "MACs": 20096},
        {"Model": "DoubleDQN", "Parameters": 20376, "FLOPs": 40192, "MACs": 20096},
        {"Model": "DuelingDQN", "Parameters": 35417, "FLOPs": 70016, "MACs": 35008},
        {"Model": "MoEDQN", "Parameters": 53211, "FLOPs": 104960, "MACs": 52480},
        {"Model": "REMO-DQN (Proposed)", "Parameters": 129678, "FLOPs": 257024, "MACs": 128512},
    ]

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
OUT_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(OUT_DIR, exist_ok=True)

# Order models in ascending complexity
model_labels = []
params = []
flops = []

# Map stats to sorted display order
display_order = [
    "DecTree",
    "StdMLP",
    "VanillaDQN",
    "DoubleDQN",
    "DuelingDQN",
    "MoEDQN",
    "REMO-DQN (Proposed)"
]

stats_map = {s["Model"]: s for s in stats_list}

for name in display_order:
    if name in stats_map:
        s = stats_map[name]
        label = "REMO-DQN\n(Proposed)" if "Proposed" in name else name
        model_labels.append(label)
        params.append(s["Parameters"])
        flops.append(s["FLOPs"])

x = np.arange(len(model_labels))
width = 0.35

fig, ax1 = plt.subplots(figsize=(11, 6))

color1 = '#1f77b4' # Steel Blue
ax1.set_xlabel('AI Benchmark Models (Action Space = 24)', fontsize=11, fontweight='bold')
ax1.set_ylabel('Number of Parameters', color=color1, fontsize=11, fontweight='bold')
bars1 = ax1.bar(x - width/2, params, width, label='Parameters', color=color1, alpha=0.9, edgecolor='black', linewidth=0.8)
ax1.tick_params(axis='y', labelcolor=color1, labelsize=10)

ax2 = ax1.twinx()
color2 = '#ff7f0e' # Bright Orange
ax2.set_ylabel('Inference FLOPs', color=color2, fontsize=11, fontweight='bold')
bars2 = ax2.bar(x + width/2, flops, width, label='FLOPs', color=color2, alpha=0.9, edgecolor='black', linewidth=0.8)
ax2.tick_params(axis='y', labelcolor=color2, labelsize=10)

ax1.set_xticks(x)
ax1.set_xticklabels(model_labels, fontsize=9.5)
ax1.set_title('Edge AI Computational Complexity Comparison (Paper4 REMO-DQN)', fontsize=13, fontweight='bold', pad=12)

# Use log scale for clear visibility across wide range (350 ~ 257k)
ax1.set_yscale('log')
ax2.set_yscale('log')

def autolabel(rects, ax, is_flops=False):
    for rect in rects:
        height = rect.get_height()
        if height >= 1000:
            text = f"{height/1000:.1f}k"
        else:
            text = f"{int(height)}"
        ax.annotate(text,
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='semibold')

autolabel(bars1, ax1)
autolabel(bars2, ax2, is_flops=True)

# Adjust y-limits for log-scale annotation headroom
ax1.set_ylim(bottom=10, top=max(params) * 8)
ax2.set_ylim(bottom=5, top=max(flops) * 8)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', framealpha=0.9)

ax1.grid(True, which='both', linestyle='--', linewidth=0.5, alpha=0.5)

fig.tight_layout()

out_path = os.path.join(OUT_DIR, "fig_complexity.png")
plt.savefig(out_path, dpi=300)
print(f"Complexity plot saved to {out_path}")

# Also save to paper/figures if directory exists
paper_fig_dir = os.path.join(_project_root, "paper", "figures")
if os.path.exists(paper_fig_dir):
    paper_out_path = os.path.join(paper_fig_dir, "fig_complexity.png")
    plt.savefig(paper_out_path, dpi=300)
    print(f"Complexity plot also saved to {paper_out_path}")
