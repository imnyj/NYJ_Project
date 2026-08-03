import pandas as pd
import matplotlib.pyplot as plt
import os

# Set style for IEEE paper
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'serif',
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'legend.fontsize': 11,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'figure.figsize': (8, 5),
    'figure.autolayout': True
})

DATA_DIR = "/home/imnyj/papers/paper4/paper/data"
CSV_PATH = os.path.join(DATA_DIR, "sweep_density_results_v2.csv")
OUT_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)

# Aggregate (mean and std) over seeds for each method and density
df_agg = df.groupby(['method', 'n_vehicles']).agg({
    'energy_efficiency': ['mean', 'std'],
    'AoI_mean': ['mean', 'std'],
    'CBR_mean': ['mean', 'std']
}).reset_index()

df_agg.columns = ['method', 'n_vehicles', 'EE_mean', 'EE_std', 'AoI_mean', 'AoI_std', 'CBR_mean', 'CBR_std']

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

# Define styles
methods = ['Fixed-10Hz', 'Stat-DCC', 'Adaptive-DCC', 'ETSI-Reactive', 'Proposed (TinyMLP)']
colors = {
    'Fixed10Hz': '#cccccc',
    'Heuristic': '#aaaaaa',
    'AdaptDCC': '#777777',
    'ReactDCC': '#444444',
    'DecTree': '#1f77b4',
    'StdMLP': '#ff7f0e',
    'TinyMLP': '#cc0000'
}
markers = {
    'Fixed-10Hz': 'x',
    'Stat-DCC': 's',
    'Adaptive-DCC': '^',
    'ETSI-Reactive': 'o',
    'Proposed (TinyMLP)': '*'
}
linestyles = {
    'Fixed-10Hz': '-',
    'Stat-DCC': '-',
    'Adaptive-DCC': '-',
    'ETSI-Reactive': '-',
    'Proposed (TinyMLP)': '--'
}

# 1. Line Plot: Energy Efficiency vs Density
plt.figure()
for m in methods:
    m_df = df_agg[df_agg['method_name'] == m]
    # Add slight jitter to x for Proposed to make it visible
    x_val = m_df['n_vehicles'] + (1.5 if m == 'Proposed (TinyMLP)' else 0)
    plt.errorbar(x_val, m_df['EE_mean'], yerr=m_df['EE_std'],
                 color=colors[m], marker=markers[m], linestyle=linestyles[m], label=m, capsize=3, linewidth=2.5 if m=='Proposed (TinyMLP)' else 2, markersize=10 if m=='Proposed (TinyMLP)' else 8)
plt.xlabel('Vehicle Density (n_vehicles)')
plt.ylabel('Energy Consumption (mJ/km)')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.savefig(os.path.join(OUT_DIR, "fig_density_energy.png"), dpi=300)
plt.close()

# 2. Line Plot: Average AoI vs Density
plt.figure()
for m in methods:
    m_df = df_agg[df_agg['method_name'] == m]
    x_val = m_df['n_vehicles'] + (1.5 if m == 'Proposed (TinyMLP)' else 0)
    plt.errorbar(x_val, m_df['AoI_mean'], yerr=m_df['AoI_std'],
                 color=colors[m], marker=markers[m], linestyle=linestyles[m], label=m, capsize=3, linewidth=2.5 if m=='Proposed (TinyMLP)' else 2, markersize=10 if m=='Proposed (TinyMLP)' else 8)
plt.xlabel('Vehicle Density (n_vehicles)')
plt.ylabel('Average Age of Information (ms)')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.savefig(os.path.join(OUT_DIR, "fig_density_aoi.png"), dpi=300)
plt.close()

# 3. Line Plot: CBR vs Density
plt.figure()
for m in methods:
    m_df = df_agg[df_agg['method_name'] == m]
    x_val = m_df['n_vehicles'] + (1.5 if m == 'Proposed (TinyMLP)' else 0)
    plt.errorbar(x_val, m_df['CBR_mean'], yerr=m_df['CBR_std'],
                 color=colors[m], marker=markers[m], linestyle=linestyles[m], label=m, capsize=3, linewidth=2.5 if m=='Proposed (TinyMLP)' else 2, markersize=10 if m=='Proposed (TinyMLP)' else 8)
plt.axhline(y=0.6, color='r', linestyle='--', label='ETSI Target (0.60)')
plt.xlabel('Vehicle Density (n_vehicles)')
plt.ylabel('Average Channel Busy Ratio (CBR)')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.savefig(os.path.join(OUT_DIR, "fig_density_cbr.png"), dpi=300)
plt.close()

print("Line plots generated successfully.")
