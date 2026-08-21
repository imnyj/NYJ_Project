import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Set style for IEEE paper
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'serif',
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'legend.fontsize': 12,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'figure.figsize': (8, 5),
    'figure.autolayout': True
})

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
CSV_PATH = os.path.join(DATA_DIR, "SA2_results.csv")

# Ensure output dir exists
OUT_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)
if 'method' in df.columns and 'param_value' in df.columns:
    df = df.drop(columns=['method'])
df = df.rename(columns={'param_value': 'method'})

# Aggregate data by method
df_agg = df.groupby('method').agg({
    'energy_efficiency': ['mean', 'std'],
    'AoI_mean': ['mean', 'std'],
    'CBR_mean': ['mean', 'std']
}).reset_index()
df_agg.columns = ['method', 'EE_mean', 'EE_std', 'AoI_mean', 'AoI_std', 'CBR_mean', 'CBR_std']

# Sorting order for plots
order = ['Fixed10Hz', 'Heuristic', 'AdaptDCC', 'ReactDCC', 'DecTree', 'Proposed']
df_agg['method'] = pd.Categorical(df_agg['method'], categories=order, ordered=True)
df_agg = df_agg.sort_values('method').dropna(subset=['method'])

name_map = {
    'ReactDCC': 'ReactDCC',
    'AdaptDCC': 'AdaptDCC',
    'Heuristic': 'Heuristic',
    'Fixed10Hz': 'Fixed10Hz',
    'DecTree': 'DecTree',
    'StdMLP': 'StdMLP',
    'Proposed': 'TinyMLP'
}
df_agg['method_name'] = df_agg['method'].map(name_map)

colors = ['#cccccc', '#aaaaaa', '#777777', '#444444', '#1f77b4', '#ff7f0e', '#cc0000']

# 1. Bar Chart: Energy Efficiency
plt.figure(figsize=(8, 5))
bars = plt.bar(df_agg['method_name'], df_agg['EE_mean'], yerr=df_agg['EE_std'], capsize=5, color=colors, edgecolor='black')
plt.ylabel('Energy Consumption (mJ/km)')
plt.title('Energy Efficiency Comparison')
plt.grid(axis='y', linestyle='--', alpha=0.7)
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.2, f'{yval:.2f}', ha='center', va='bottom', fontweight='bold')
plt.savefig(os.path.join(OUT_DIR, "fig_energy_efficiency.png"), dpi=300)
plt.close()

# 2. Bar Chart: Average AoI
plt.figure(figsize=(8, 5))
bars = plt.bar(df_agg['method_name'], df_agg['AoI_mean'], yerr=df_agg['AoI_std'], capsize=5, color=colors, edgecolor='black')
plt.ylabel('Average Age of Information (ms)')
plt.title('Information Freshness (AoI) Comparison')
plt.grid(axis='y', linestyle='--', alpha=0.7)
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 10, f'{yval:.1f}', ha='center', va='bottom')
plt.ylim(0, 600)
plt.savefig(os.path.join(OUT_DIR, "fig_aoi.png"), dpi=300)
plt.close()

# 3. Bar Chart: CBR
plt.figure(figsize=(8, 5))
bars = plt.bar(df_agg['method_name'], df_agg['CBR_mean'], yerr=df_agg['CBR_std'], capsize=5, color=colors, edgecolor='black')
plt.ylabel('Average Channel Busy Ratio (CBR)')
plt.title('Channel Congestion Comparison')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.axhline(y=0.6, color='r', linestyle='--', label='ETSI Active Threshold (0.60)')
plt.legend()
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.02, f'{yval:.3f}', ha='center', va='bottom')
plt.ylim(0, 0.8)
plt.savefig(os.path.join(OUT_DIR, "fig_cbr.png"), dpi=300)
plt.close()

# 4. Scatter / Line Plot (Trade-off: AoI vs Energy)
plt.figure(figsize=(8, 6))
for i, row in df_agg.iterrows():
    m = row['method_name']
    plt.scatter(row['EE_mean'], row['AoI_mean'], s=200, label=m, color=colors[i], edgecolors='black', zorder=5)
    plt.errorbar(row['EE_mean'], row['AoI_mean'], xerr=row['EE_std'], yerr=row['AoI_std'], color='black', alpha=0.5, zorder=4)

# Draw lines connecting the baselines to show Pareto frontier shift
baseline_x = df_agg[df_agg['method'].isin(['ReactDCC', 'AdaptDCC', 'Heuristic', 'Fixed10Hz', 'DecTree', 'StdMLP'])]['EE_mean'].values
baseline_y = df_agg[df_agg['method'].isin(['ReactDCC', 'AdaptDCC', 'Heuristic', 'Fixed10Hz', 'DecTree', 'StdMLP'])]['AoI_mean'].values
plt.plot(baseline_x, baseline_y, linestyle='--', color='gray', alpha=0.6, label='Baseline Trade-off')
plt.plot([df_agg[df_agg['method_name'] == 'ReactDCC']['EE_mean'].values[0], df_agg[df_agg['method_name'] == 'TinyMLP']['EE_mean'].values[0]],
         [df_agg[df_agg['method_name'] == 'ReactDCC']['AoI_mean'].values[0], df_agg[df_agg['method_name'] == 'TinyMLP']['AoI_mean'].values[0]],
         linestyle='-', color='red', alpha=0.8, label='Proposed Improvement')

plt.xlabel('Energy Consumption (mJ/km) -> Lower is better')
plt.ylabel('Average AoI (ms) -> Lower is better')
plt.title('Performance Trade-off: Energy vs. AoI')
plt.grid(True, linestyle=':', alpha=0.7)
plt.legend(title="Methods", loc="upper right")
plt.savefig(os.path.join(OUT_DIR, "fig_tradeoff_aoi_energy.png"), dpi=300)
plt.close()

print("Plots generated successfully in 'plots' directory.")
