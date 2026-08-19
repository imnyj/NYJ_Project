#!/usr/bin/env python3
"""
Paper4 Publication Visualization Pipeline
=========================================
Generates all 11 target figures and tables (13 total files) for Paper 4,
strictly adhering to evaluation_plan.md and PROJECT.md specifications:

1. ablation_study.png (Structure & Reward Ablation Study Curves)
2. optuna_sensitivity_table.csv & optuna_sensitivity_table.tex (Optuna Hyperparameter Sensitivity Table)
3. reward_convergence.png (17 Baseline Models Reward Convergence Curves)
4. tsne_clustering.png (MoE Latent Feature Space t-SNE Clustering, 300+ DPI)
5. moe_routing.png (Vehicle Density vs MoE 3 Experts Activation Weight Distribution)
6. cbr_trace.png (Time-Series Channel Busy Ratio Trace + 0.60 Target Line, 17 Baselines)
7. pdr_vs_density.png (Vehicle Density vs PDR Curves, 17 Baselines)
8. aoi_vs_density.png (Vehicle Density vs AoI Curves, 17 Baselines)
9. pdr_vs_distance.png (Transmission Distance vs PDR Curves, 17 Baselines)
10. aoi_vs_distance.png (Transmission Distance vs AoI Curves, 17 Baselines)
11. hardware_feasibility_table.csv & hardware_feasibility_table.tex (Hardware Complexity Profiling Table)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import seaborn as sns

# Directory setup
VIS_DIR = "/home/imnyj/Workspace/paper4/visualizer"
DATA_DIR = "/home/imnyj/Workspace/paper4/data"
CODER_DATA = "/home/imnyj/Workspace/paper4/coder/data"

os.makedirs(VIS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CODER_DATA, exist_ok=True)

# Set IEEE Journal typography & layout standards
mpl.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['DejaVu Serif', 'Times New Roman', 'Liberation Serif'],
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.titlesize': 14,
    'lines.linewidth': 1.6,
    'lines.markersize': 5,
    'grid.alpha': 0.35,
    'grid.linestyle': '--',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'savefig.dpi': 350,
    'savefig.bbox': 'tight'
})

# -------------------------------------------------------------
# 17 Baselines Configuration (evaluation_plan.md §2 Strict Spec)
# -------------------------------------------------------------
BASELINES_SPEC = [
    {
        "name": "REMO-DQN (Proposed)",
        "keys": ["REMO-DQN (Proposed)", "REMO-DQN", "Proposed", "ResNetMoEDQN"],
        "color": "#FF0000",
        "linestyle": "-",
        "marker": "o",
        "linewidth": 2.5,
        "alpha": 1.0,
        "zorder": 99
    },
    {
        "name": "Fixed 10Hz",
        "keys": ["Fixed 10Hz", "Fixed10Hz"],
        "color": "#0000FF",
        "linestyle": "--",
        "marker": "s",
        "linewidth": 1.6,
        "alpha": 0.6,
        "zorder": 5
    },
    {
        "name": "ReactDCC (ETSI Standard)",
        "keys": ["ReactDCC (ETSI Standard)", "ReactDCC"],
        "color": "#4D96FF",
        "linestyle": "-.",
        "marker": "^",
        "linewidth": 1.6,
        "alpha": 0.6,
        "zorder": 6
    },
    {
        "name": "AdaptDCC (ETSI Standard)",
        "keys": ["AdaptDCC (ETSI Standard)", "AdaptDCC"],
        "color": "#2A4B7C",
        "linestyle": ":",
        "marker": "v",
        "linewidth": 1.6,
        "alpha": 0.6,
        "zorder": 7
    },
    {
        "name": "MoEDQN",
        "keys": ["MoEDQN", "DQN+MoE", "MoE-DQN"],
        "color": "#9B5DE5",
        "linestyle": "-",
        "marker": "D",
        "linewidth": 1.6,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "MAPPO",
        "keys": ["MAPPO"],
        "color": "#D783FF",
        "linestyle": "-",
        "marker": "P",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "PPO",
        "keys": ["PPO"],
        "color": "#7A49A5",
        "linestyle": "-",
        "marker": "p",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "SAC",
        "keys": ["SAC"],
        "color": "#00FF00",
        "linestyle": "-",
        "marker": "h",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "DDPG",
        "keys": ["DDPG"],
        "color": "#6BCB77",
        "linestyle": "-",
        "marker": "X",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "TD3",
        "keys": ["TD3"],
        "color": "#2E8B57",
        "linestyle": "-",
        "marker": "d",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "DuelingDQN",
        "keys": ["DuelingDQN", "Dueling DQN", "Dueling"],
        "color": "#FF9F1C",
        "linestyle": "-",
        "marker": "<",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "DoubleDQN",
        "keys": ["DoubleDQN", "Double DQN", "DDQN"],
        "color": "#FFD166",
        "linestyle": "-",
        "marker": ">",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "VanillaDQN",
        "keys": ["VanillaDQN", "Vanilla DQN", "DQN"],
        "color": "#D67229",
        "linestyle": "-",
        "marker": "x",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "QLearning",
        "keys": ["QLearning", "Q-Learning"],
        "color": "#1A1A1A",
        "linestyle": "-",
        "marker": "1",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "SARSA",
        "keys": ["SARSA"],
        "color": "#555555",
        "linestyle": "-",
        "marker": "2",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "ActorCritic",
        "keys": ["ActorCritic", "Actor-Critic", "A2C"],
        "color": "#888888",
        "linestyle": "-",
        "marker": "3",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    },
    {
        "name": "DecisionTransformer",
        "keys": ["DecisionTransformer", "Decision Transformer", "DT"],
        "color": "#B5B5B5",
        "linestyle": "-",
        "marker": "4",
        "linewidth": 1.5,
        "alpha": 0.6,
        "zorder": 8
    }
]

def get_style(col_name):
    """Retrieve color, linestyle, marker, linewidth, alpha for a baseline."""
    clean = str(col_name).strip()
    for spec in BASELINES_SPEC:
        if clean in spec["keys"]:
            return spec
    return {
        "name": clean,
        "color": "#333333",
        "linestyle": "-",
        "marker": "",
        "linewidth": 1.2,
        "alpha": 0.5,
        "zorder": 2
    }

def apply_ordered_legend(ax, handles_labels=None, ncol=2, loc="upper left", bbox_to_anchor=(1.02, 1.0)):
    """Strictly order the legend according to evaluation_plan.md §2."""
    if handles_labels is None:
        handles, labels = ax.get_legend_handles_labels()
    else:
        handles, labels = handles_labels

    def get_order_idx(label):
        for i, spec in enumerate(BASELINES_SPEC):
            if label == spec["name"] or label in spec["keys"]:
                return i
        return 999

    pairs = list(zip(handles, labels))
    seen = set()
    unique_pairs = []
    for h, l in pairs:
        if l not in seen:
            seen.add(l)
            unique_pairs.append((h, l))

    sorted_pairs = sorted(unique_pairs, key=lambda x: get_order_idx(x[1]))
    s_handles = [p[0] for p in sorted_pairs]
    s_labels = [p[1] for p in sorted_pairs]

    leg = ax.legend(s_handles, s_labels, loc=loc, bbox_to_anchor=bbox_to_anchor,
                    ncol=ncol, frameon=True, fancybox=True, edgecolor="#CCCCCC", fontsize=8.5)
    leg.get_frame().set_alpha(0.95)
    return leg

def load_dataset(filename):
    """Load CSV from data/ or coder/data/."""
    p1 = os.path.join(DATA_DIR, filename)
    p2 = os.path.join(CODER_DATA, filename)
    if os.path.exists(p1):
        return pd.read_csv(p1)
    elif os.path.exists(p2):
        return pd.read_csv(p2)
    else:
        raise FileNotFoundError(f"Could not locate {filename} in {DATA_DIR} or {CODER_DATA}")

def save_dual_figure(fig, basename, dpi=350):
    """Save figure in both high-res PNG (350 DPI) and publication-grade vector PDF."""
    pdf_path = os.path.join(VIS_DIR, f"{basename}.pdf")
    png_path = os.path.join(VIS_DIR, f"{basename}.png")
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=dpi, bbox_inches="tight")
    
    # Save unprefixed alias if basename starts with number prefix
    if basename[0].isdigit() and "_" in basename:
        unprefixed = basename.split("_", 1)[1]
        fig.savefig(os.path.join(VIS_DIR, f"{unprefixed}.pdf"), format="pdf", bbox_inches="tight")
        fig.savefig(os.path.join(VIS_DIR, f"{unprefixed}.png"), format="png", dpi=dpi, bbox_inches="tight")
        
    plt.close(fig)
    print(f"  -> Successfully generated {png_path} & {pdf_path} (DPI={dpi})")

# =========================================================================
# 1. Target 1: ablation_study.png
# =========================================================================
def plot_target1_ablation_study():
    print("[1/11] Generating Target 1: 1_ablation_study.png ...")
    df = load_dataset("ablation_study.csv")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2), sharey=True)
    
    if "Global_Step" in df.columns:
        steps = df["Global_Step"].values
    elif "Episode" in df.columns:
        steps = df["Episode"].values * 2000
    else:
        steps = np.linspace(2000, 200000, len(df))
        
    mark_freq = max(1, len(steps) // 12)
    
    # (a) Structure Ablation
    struct_curves = [
        ("REMO-DQN (Proposed)", "REMO-DQN", "#FF0000", "-", "o", 2.5, 1.0, 20),
        ("w/o ResNet Block", "w/o ResNet", "#2A4B7C", "--", "s", 1.8, 0.85, 5),
        ("w/o MoE Routing", "w/o MoE", "#9B5DE5", "-.", "^", 1.8, 0.85, 5),
        ("w/o Dueling Stream", "w/o Dueling", "#FF9F1C", ":", "D", 1.8, 0.85, 5),
    ]
    
    for label, col, color, ls, mk, lw, alpha, zo in struct_curves:
        if col in df.columns:
            vals = df[col].values
            ax1.plot(steps, vals, label=label, color=color, linestyle=ls,
                     marker=mk, markevery=mark_freq, linewidth=lw, alpha=alpha, zorder=zo)
            
    # Phase I & II Background Shading & Labels
    ax1.axvspan(0, 120000, color="#4A90E2", alpha=0.08, zorder=1)
    ax1.axvspan(120000, 200000, color="#2ECC71", alpha=0.08, zorder=1)
    ax1.axvline(x=120000, color="#718096", linestyle=":", linewidth=1.4, alpha=0.75, zorder=2)
    ax1.text(60000, -137000, "Phase I: Convergence\n(0 ~ 120k Steps)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1A365D", bbox=dict(boxstyle="round,pad=0.25", fc="#EBF8FF", ec="#90CDF4", alpha=0.9), zorder=25)
    ax1.text(160000, -137000, "Phase II: Stability\n(120k ~ 200k Steps)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1C4532", bbox=dict(boxstyle="round,pad=0.25", fc="#F0FFF4", ec="#9AE6B4", alpha=0.9), zorder=25)

    ax1.set_xlim(0, 200000)
    ax1.set_xticks([0, 40000, 80000, 120000, 160000, 200000])
    ax1.set_xticklabels(['0', '40k', '80k', '120k', '160k', '200k'])
    ax1.set_title("(a) Structural Component Ablation", fontsize=12, fontweight='bold', pad=10)
    ax1.set_xlabel("Training Steps (Iterations)", fontsize=11)
    ax1.set_ylabel("Cumulative Episode Reward", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(loc="lower right", frameon=True, fancybox=True, edgecolor="#CCCCCC", fontsize=9.5)
    
    # (b) Reward Formulation Ablation
    reward_curves = [
        ("Full Reward ($R_{full}$)", "REMO-DQN", "#FF0000", "-", "o", 2.5, 1.0, 20),
        (r"w/o $R_{\mathrm{CBR}}$ (CBR Penalty, $R_1$)", "w/o R1", "#E63946", "--", "v", 1.8, 0.85, 5),
        (r"w/o $R_{\mathrm{AoI}}$ (AoI Penalty, $R_2$)", "w/o R2", "#457B9D", "-.", "<", 1.8, 0.85, 5),
        (r"w/o $R_{\mathrm{Stab}}$ (Energy/Stability, $R_3$)", "w/o R3", "#1D3557", ":", ">", 1.8, 0.85, 5),
    ]
    
    for label, col, color, ls, mk, lw, alpha, zo in reward_curves:
        if col in df.columns:
            vals = df[col].values
            ax2.plot(steps, vals, label=label, color=color, linestyle=ls,
                     marker=mk, markevery=mark_freq, linewidth=lw, alpha=alpha, zorder=zo)
            
    # Phase I & II Background Shading & Labels
    ax2.axvspan(0, 120000, color="#4A90E2", alpha=0.08, zorder=1)
    ax2.axvspan(120000, 200000, color="#2ECC71", alpha=0.08, zorder=1)
    ax2.axvline(x=120000, color="#718096", linestyle=":", linewidth=1.4, alpha=0.75, zorder=2)
    ax2.text(60000, -137000, "Phase I: Convergence\n(0 ~ 120k Steps)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1A365D", bbox=dict(boxstyle="round,pad=0.25", fc="#EBF8FF", ec="#90CDF4", alpha=0.9), zorder=25)
    ax2.text(160000, -137000, "Phase II: Stability\n(120k ~ 200k Steps)", ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1C4532", bbox=dict(boxstyle="round,pad=0.25", fc="#F0FFF4", ec="#9AE6B4", alpha=0.9), zorder=25)

    ax2.set_xlim(0, 200000)
    ax2.set_xticks([0, 40000, 80000, 120000, 160000, 200000])
    ax2.set_xticklabels(['0', '40k', '80k', '120k', '160k', '200k'])
    ax2.set_title("(b) Multi-Objective Reward Ablation", fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel("Training Steps (Iterations)", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(loc="lower right", frameon=True, fancybox=True, edgecolor="#CCCCCC", fontsize=9.5)
    
    plt.tight_layout()
    save_dual_figure(fig, "1_ablation_study", dpi=350)

# =========================================================================
# 2. Target 2: optuna_sensitivity_table.csv & optuna_sensitivity_table.tex
# =========================================================================
def plot_target2_optuna_sensitivity_table():
    print("[2/11] Generating Target 2: 2_optuna_sensitivity_table.csv & .tex ...")
    df = load_dataset("optuna_sensitivity_table.csv")
    
    csv_path = os.path.join(VIS_DIR, "optuna_sensitivity_table.csv")
    csv_path_num = os.path.join(VIS_DIR, "2_optuna_sensitivity_table.csv")
    df.to_csv(csv_path, index=False)
    df.to_csv(csv_path_num, index=False)
    
    tex_content = []
    tex_content.append("% Optuna Hyperparameter Sensitivity & Performance Comparison Table\n")
    tex_content.append("\\begin{table*}[t]\n")
    tex_content.append("\\centering\n")
    tex_content.append("\\caption{Optuna Hyperparameter Optimization Results and Empirical Performance Across 17 Baselines}\n")
    tex_content.append("\\label{tab:optuna-sensitivity}\n")
    tex_content.append("\\resizebox{\\textwidth}{!}{\n")
    tex_content.append("\\begin{tabular}{l l p{6.8cm} r r r r}\n")
    tex_content.append("\\toprule\n")
    tex_content.append("\\textbf{Method} & \\textbf{Model Type} & \\textbf{Optimal Hyperparameters} & \\textbf{Reward} & \\textbf{PDR (\\%)} & \\textbf{AoI (ms)} & \\textbf{CBR} \\\\\n")
    tex_content.append("\\midrule\n")
    for _, r in df.iterrows():
        is_bold = "REMO-DQN" in str(r["Method"])
        prefix = "\\textbf{" if is_bold else ""
        suffix = "}" if is_bold else ""
        hparams_tex = str(r['Tuned Hyperparameters']).replace('_', r'\_')
        method_tex = str(r['Method']).replace('_', r'\_')
        arch_tex = str(r['Architecture']).replace('_', r'\_')
        tex_content.append(f"{prefix}{method_tex}{suffix} & {arch_tex} & \\small{{{hparams_tex}}} & {float(r['Reward Convergence']):.1f} & {float(r['Mean PDR (%)']):.2f} & {float(r['Mean AoI (ms)']):.2f} & {float(r['Mean CBR']):.3f} \\\\\n")
    tex_content.append("\\bottomrule\n")
    tex_content.append("\\end{tabular}\n")
    tex_content.append("}\n")
    tex_content.append("\\end{table*}\n")
    
    full_tex = "".join(tex_content)
    tex_path = os.path.join(VIS_DIR, "optuna_sensitivity_table.tex")
    tex_path_num = os.path.join(VIS_DIR, "2_optuna_sensitivity_table.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(full_tex)
    with open(tex_path_num, "w", encoding="utf-8") as f:
        f.write(full_tex)
    print(f"  -> Successfully generated {csv_path_num} & {tex_path_num}")

# =========================================================================
# 3. Target 3: reward_convergence.png
# =========================================================================
def plot_target3_reward_convergence():
    print("[3/11] Generating Target 3: 3_reward_convergence.png ...")
    df = load_dataset("reward_convergence.csv")
    
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    
    if "Global_Step" in df.columns:
        steps = df["Global_Step"].values
    elif "Episode" in df.columns:
        steps = df["Episode"].values * 2000
    else:
        steps = np.linspace(2000, 200000, len(df))
        
    # Phase I & II Background Shading & Boundary Line
    ax.axvspan(0, 120000, color="#4A90E2", alpha=0.08, zorder=1)
    ax.axvspan(120000, 200000, color="#2ECC71", alpha=0.08, zorder=1)
    ax.axvline(x=120000, color="#718096", linestyle=":", linewidth=1.4, alpha=0.75, zorder=2)
    
    # Phase text annotations
    ax.text(60000, -825000, "Phase I: Convergence & Exploration\n(0 ~ 120k Steps)", ha="center", va="top", fontsize=9.5, fontweight="bold", color="#1A365D", bbox=dict(boxstyle="round,pad=0.3", fc="#EBF8FF", ec="#90CDF4", alpha=0.9), zorder=30)
    ax.text(160000, -825000, "Phase II: Post-Convergence Steady-State Stability\n(120k ~ 200k Steps)", ha="center", va="top", fontsize=9.5, fontweight="bold", color="#1C4532", bbox=dict(boxstyle="round,pad=0.3", fc="#F0FFF4", ec="#9AE6B4", alpha=0.9), zorder=30)

    for spec in BASELINES_SPEC:
        name = spec["name"]
        col_found = None
        for k in spec["keys"]:
            if k in df.columns:
                col_found = k
                break
        if col_found:
            y = df[col_found].values
            # Moving average smoothing for clean publication aesthetics
            window = 3
            y_smooth = pd.Series(y).rolling(window, min_periods=1).mean().values
            
            ax.plot(steps, y_smooth, label=name, color=spec["color"],
                    linestyle=spec["linestyle"], linewidth=spec["linewidth"],
                    alpha=spec["alpha"], zorder=spec["zorder"])
            
            # Subtle confidence interval band for proposed method
            if name.startswith("REMO-DQN"):
                std = pd.Series(y).rolling(window, min_periods=1).std().fillna(1500).values
                ax.fill_between(steps, y_smooth - std, y_smooth + std, color=spec["color"], alpha=0.15, zorder=spec["zorder"]-1)
                
    ax.set_xlim(0, 200000)
    ax.set_xticks([0, 40000, 80000, 120000, 160000, 200000])
    ax.set_xticklabels(['0', '40k', '80k', '120k', '160k', '200k'])
    ax.set_title("Training Reward Convergence Across 17 Baselines (200,000 Steps)", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Training Steps (Iterations)", fontsize=11)
    ax.set_ylabel("Cumulative Episode Reward", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    
    apply_ordered_legend(ax, ncol=2, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    
    plt.tight_layout()
    save_dual_figure(fig, "3_reward_convergence", dpi=350)

# =========================================================================
# 4. Target 4: tsne_clustering.png (350 DPI)
# =========================================================================
def plot_target4_tsne_clustering():
    print("[4/11] Generating Target 4: 4_tsne_clustering.png ...")
    df = load_dataset("tsne_clustering.csv")
    
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    
    clusters = [
        ("Low Traffic", "#2A4B7C", "o", "Expert 1: Sparse Traffic Regime"),
        ("Medium Traffic", "#FF9F1C", "s", "Expert 2: Moderate Congestion Regime"),
        ("High Traffic", "#FF0000", "^", "Expert 3: Severe Saturation Regime")
    ]
    
    for c_name, color, marker, desc in clusters:
        sub = df[df["Cluster"] == c_name]
        if len(sub) > 0:
            ax.scatter(sub["x"], sub["y"], label=desc, color=color,
                       marker=marker, s=55, alpha=0.85, edgecolors='k', linewidth=0.6, zorder=5)
            
            # Confidence ellipse around cluster center
            mean_x, mean_y = sub["x"].mean(), sub["y"].mean()
            std_x, std_y = sub["x"].std(), sub["y"].std()
            ellipse = Ellipse((mean_x, mean_y), width=std_x*3.2, height=std_y*3.2,
                              color=color, alpha=0.12, zorder=2)
            ax.add_patch(ellipse)
            
    ax.set_title("t-SNE Latent Feature Space & MoE Expert Routing Clusters", fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel("t-SNE Dimension 1", fontsize=11)
    ax.set_ylabel("t-SNE Dimension 2", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="upper right", frameon=True, fancybox=True, edgecolor="#CCCCCC", fontsize=9)
    
    plt.tight_layout()
    save_dual_figure(fig, "4_tsne_clustering", dpi=350)

# =========================================================================
# 5. Target 5: moe_routing.png
# =========================================================================
def plot_target5_moe_routing():
    print("[5/11] Generating Target 5: 5_moe_routing.png ...")
    df = load_dataset("moe_routing.csv")
    
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    
    densities = df["Density"].values
    e1 = df["Expert1 (Low Density)"].values
    e2 = df["Expert2 (Medium Density)"].values
    e3 = df["Expert3 (High Density)"].values
    
    # Smooth stacked area plot
    ax.stackplot(densities, e1, e2, e3,
                 labels=[
                     "Expert 1: Low-Density Policy (High Frequency / Low Power)",
                     "Expert 2: Moderate-Density Policy (Adaptive Rate Balancing)",
                     "Expert 3: High-Density Policy (Congestion Avoidance / Backoff)"
                 ],
                 colors=["#4D96FF", "#FFD166", "#FF6B6B"],
                 alpha=[0.85, 0.85, 0.85])
    
    # Overlay boundary lines
    ax.plot(densities, e1, color="#2A4B7C", linewidth=1.5, linestyle="--")
    ax.plot(densities, e1 + e2, color="#D67229", linewidth=1.5, linestyle="--")
    
    ax.set_title("MoE Dynamic Expert Activation Weight vs. Vehicle Density", fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel("Vehicle Density (veh/km)", fontsize=11)
    ax.set_ylabel("Expert Gating Activation Weight (%)", fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_xlim(densities.min(), densities.max())
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=1, frameon=True, fancybox=True, edgecolor="#CCCCCC", fontsize=9)
    
    plt.tight_layout()
    save_dual_figure(fig, "5_moe_routing", dpi=350)

# =========================================================================
# 6. Target 6: cbr_trace.png (+ 0.60 Target Line, 17 Baselines)
# =========================================================================
def plot_target6_cbr_trace():
    print("[6/11] Generating Target 6: 6_cbr_trace.png ...")
    df = load_dataset("cbr_trace.csv")
    
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    time_steps = df["Time"].values
    
    # Target CBR reference line at 0.60
    ax.axhline(y=0.60, color="#CC0000", linestyle="--", linewidth=2.0, alpha=0.9,
               label=r"ETSI DCC Target CBR ($CBR_{\mathrm{target}} = 0.60$)", zorder=25)
    
    for spec in BASELINES_SPEC:
        name = spec["name"]
        col_found = None
        for k in spec["keys"]:
            if k in df.columns:
                col_found = k
                break
        if col_found:
            y = df[col_found].values
            ax.plot(time_steps, y, label=name, color=spec["color"],
                    linestyle=spec["linestyle"], linewidth=spec["linewidth"],
                    alpha=spec["alpha"], zorder=spec["zorder"])
            
    ax.set_title("Time-Series Channel Busy Ratio (CBR) Trace and Stability Comparison", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Simulation Time (s)", fontsize=11)
    ax.set_ylabel("Channel Busy Ratio (CBR)", fontsize=11)
    ax.set_ylim(0.25, 0.95)
    ax.grid(True, linestyle="--", alpha=0.4)
    
    apply_ordered_legend(ax, ncol=2, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    
    plt.tight_layout()
    save_dual_figure(fig, "6_cbr_trace", dpi=350)

# =========================================================================
# 7. Target 7: pdr_vs_density.png (17 Baselines)
# =========================================================================
def plot_target7_pdr_vs_density():
    print("[7/11] Generating Target 7: 7_pdr_vs_density.png ...")
    df = load_dataset("pdr_vs_density.csv")
    
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    densities = df["Density"].values
    
    for spec in BASELINES_SPEC:
        name = spec["name"]
        col_found = None
        for k in spec["keys"]:
            if k in df.columns:
                col_found = k
                break
        if col_found:
            y = df[col_found].values
            ax.plot(densities, y, label=name, color=spec["color"],
                    linestyle=spec["linestyle"], marker=spec["marker"],
                    markevery=5, linewidth=spec["linewidth"],
                    alpha=spec["alpha"], zorder=spec["zorder"])
            
    ax.set_title("Packet Delivery Ratio (PDR) vs. Vehicle Density Across 17 Baselines", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Vehicle Density (veh/km)", fontsize=11)
    ax.set_ylabel("Packet Delivery Ratio (PDR, %)", fontsize=11)
    ax.set_ylim(30, 102)
    ax.grid(True, linestyle="--", alpha=0.4)
    
    apply_ordered_legend(ax, ncol=2, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    
    plt.tight_layout()
    save_dual_figure(fig, "7_pdr_vs_density", dpi=350)

# =========================================================================
# 8. Target 8: aoi_vs_density.png (17 Baselines)
# =========================================================================
def plot_target8_aoi_vs_density():
    print("[8/11] Generating Target 8: 8_aoi_vs_density.png ...")
    df = load_dataset("aoi_vs_density.csv")
    
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    densities = df["Density"].values
    
    for spec in BASELINES_SPEC:
        name = spec["name"]
        col_found = None
        for k in spec["keys"]:
            if k in df.columns:
                col_found = k
                break
        if col_found:
            y = df[col_found].values
            ax.plot(densities, y, label=name, color=spec["color"],
                    linestyle=spec["linestyle"], marker=spec["marker"],
                    markevery=5, linewidth=spec["linewidth"],
                    alpha=spec["alpha"], zorder=spec["zorder"])
            
    ax.set_title("Age of Information (AoI) vs. Vehicle Density Across 17 Baselines", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Vehicle Density (veh/km)", fontsize=11)
    ax.set_ylabel("Age of Information (AoI, ms)", fontsize=11)
    ax.set_ylim(80, 1900)
    ax.grid(True, linestyle="--", alpha=0.4)
    
    apply_ordered_legend(ax, ncol=2, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    
    plt.tight_layout()
    save_dual_figure(fig, "8_aoi_vs_density", dpi=350)

# =========================================================================
# 9. Target 9: pdr_vs_distance.png (17 Baselines)
# =========================================================================
def plot_target9_pdr_vs_distance():
    print("[9/11] Generating Target 9: 9_pdr_vs_distance.png ...")
    df = load_dataset("pdr_vs_distance.csv")
    
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    dist = df["Distance"].values
    
    for spec in BASELINES_SPEC:
        name = spec["name"]
        col_found = None
        for k in spec["keys"]:
            if k in df.columns:
                col_found = k
                break
        if col_found:
            y = df[col_found].values
            ax.plot(dist, y, label=name, color=spec["color"],
                    linestyle=spec["linestyle"], marker=spec["marker"],
                    linewidth=spec["linewidth"], alpha=spec["alpha"],
                    zorder=spec["zorder"])
            
    ax.set_title("Packet Delivery Ratio (PDR) vs. Transmission Distance Across 17 Baselines", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Communication Distance (m)", fontsize=11)
    ax.set_ylabel("Packet Delivery Ratio (PDR, %)", fontsize=11)
    ax.set_ylim(35, 102)
    ax.grid(True, linestyle="--", alpha=0.4)
    
    apply_ordered_legend(ax, ncol=2, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    
    plt.tight_layout()
    save_dual_figure(fig, "9_pdr_vs_distance", dpi=350)

# =========================================================================
# 10. Target 10: aoi_vs_distance.png (17 Baselines)
# =========================================================================
def plot_target10_aoi_vs_distance():
    print("[10/11] Generating Target 10: 10_aoi_vs_distance.png ...")
    df = load_dataset("aoi_vs_distance.csv")
    
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    dist = df["Distance"].values
    
    for spec in BASELINES_SPEC:
        name = spec["name"]
        col_found = None
        for k in spec["keys"]:
            if k in df.columns:
                col_found = k
                break
        if col_found:
            y = df[col_found].values
            ax.plot(dist, y, label=name, color=spec["color"],
                    linestyle=spec["linestyle"], marker=spec["marker"],
                    linewidth=spec["linewidth"], alpha=spec["alpha"],
                    zorder=spec["zorder"])
            
    ax.set_title("Age of Information (AoI) vs. Transmission Distance Across 17 Baselines", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Communication Distance (m)", fontsize=11)
    ax.set_ylabel("Age of Information (AoI, ms)", fontsize=11)
    ax.set_ylim(100, 950)
    ax.grid(True, linestyle="--", alpha=0.4)
    
    apply_ordered_legend(ax, ncol=2, bbox_to_anchor=(1.02, 1.0))
    
    plt.tight_layout()
    save_dual_figure(fig, "10_aoi_vs_distance", dpi=350)

# =========================================================================
# 11. Target 11: hardware_feasibility_table.csv & .tex
# =========================================================================
def plot_target11_hardware_feasibility_table():
    print("[11/11] Generating Target 11: 11_hardware_feasibility_table.csv & .tex ...")
    df = load_dataset("hardware_feasibility_table.csv")
    
    csv_path = os.path.join(VIS_DIR, "hardware_feasibility_table.csv")
    csv_path_num = os.path.join(VIS_DIR, "11_hardware_feasibility_table.csv")
    df.to_csv(csv_path, index=False)
    df.to_csv(csv_path_num, index=False)
    
    tex_content = []
    tex_content.append("% Hardware Feasibility & Complexity Profiling Table\n")
    tex_content.append("\\begin{table*}[t]\n")
    tex_content.append("\\centering\n")
    tex_content.append("\\caption{Hardware Profiling, Computational Complexity, and On-Device Feasibility Analysis on Embedded OBU/MCU Target Platform}\n")
    tex_content.append("\\label{tab:hardware-feasibility}\n")
    tex_content.append("\\resizebox{\\textwidth}{!}{\n")
    tex_content.append("\\begin{tabular}{l l r r r r l}\n")
    tex_content.append("\\toprule\n")
    tex_content.append("\\textbf{Model} & \\textbf{Architecture} & \\textbf{MACs/FLOPs} & \\textbf{Parameters} & \\textbf{Latency (ms)} & \\textbf{RAM/Flash (KB)} & \\textbf{Feasibility Status} \\\\\n")
    tex_content.append("\\midrule\n")
    for _, r in df.iterrows():
        is_bold = "REMO-DQN" in str(r["Model"])
        prefix = "\\textbf{" if is_bold else ""
        suffix = "}" if is_bold else ""
        macs_val = str(r['MACs_FLOPs'])
        if '<' in macs_val:
            macs_tex = "$< 0.01$~M"
        else:
            macs_tex = macs_val
        model_tex = str(r['Model']).replace('_', r'\_')
        arch_tex = str(r['Architecture']).replace('_', r'\_')
        tex_content.append(f"{prefix}{model_tex}{suffix} & {arch_tex} & {macs_tex} & {r['Parameters']} & {float(r['Inference_Latency_ms']):.3f} & {float(r['Memory_Footprint_KB']):.1f} & {r['MCU_Feasibility']} \\\\\n")
    tex_content.append("\\bottomrule\n")
    tex_content.append("\\end{tabular}\n")
    tex_content.append("}\n")
    tex_content.append("\\end{table*}\n")
    
    full_tex = "".join(tex_content)
    tex_path = os.path.join(VIS_DIR, "hardware_feasibility_table.tex")
    tex_path_num = os.path.join(VIS_DIR, "11_hardware_feasibility_table.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(full_tex)
    with open(tex_path_num, "w", encoding="utf-8") as f:
        f.write(full_tex)
    print(f"  -> Successfully generated {csv_path_num} & {tex_path_num}")

# =========================================================================
# Main Execution Entry Point
# =========================================================================
def main():
    print("================================================================")
    print("  Paper 4 Visualization & Evaluation Execution Pipeline (350 DPI)")
    print("================================================================")
    
    # 1. Ablation Study Curves
    plot_target1_ablation_study()
    
    # 2. Optuna Sensitivity Table (CSV & Tex)
    plot_target2_optuna_sensitivity_table()
    
    # 3. Reward Convergence (17 Baselines)
    plot_target3_reward_convergence()
    
    # 4. t-SNE Clustering (350 DPI PNG)
    plot_target4_tsne_clustering()
    
    # 5. MoE Routing Distribution
    plot_target5_moe_routing()
    
    # 6. CBR Trace (+ 0.60 Target Line, 17 Baselines)
    plot_target6_cbr_trace()
    
    # 7. PDR vs Density (17 Baselines)
    plot_target7_pdr_vs_density()
    
    # 8. AoI vs Density (17 Baselines)
    plot_target8_aoi_vs_density()
    
    # 9. PDR vs Distance (17 Baselines)
    plot_target9_pdr_vs_distance()
    
    # 10. AoI vs Distance (17 Baselines)
    plot_target10_aoi_vs_distance()
    
    # 11. Hardware Feasibility Table (CSV & Tex)
    plot_target11_hardware_feasibility_table()
    
    print("================================================================")
    print("  All 11 Target Visualizations and Tables Generated Successfully!")
    print("================================================================")

if __name__ == "__main__":
    main()
