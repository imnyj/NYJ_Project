import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CONFIG_PATH = '/home/imnyj/Workspace/paper4/visualizer/config.md'
DATA_DIR = '/home/imnyj/Workspace/paper4/coder/data/'
VIS_DIR = '/home/imnyj/Workspace/paper4/visualizer/'

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VIS_DIR, exist_ok=True)

# 1. Parse Config
models = []
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('|'):
            cols = [c.strip() for c in line.split('|')]
            if len(cols) > 2 and cols[1].isdigit():
                name = cols[3].replace('**', '').strip()
                
                c_match = re.search(r'`([^`]+)`', cols[4])
                color = c_match.group(1) if c_match else cols[4].split()[0]
                if color == '#FF00000':
                    color = '#FF0000'
                if not color.startswith('#') and color not in plt.colors.cnames:
                    color = cols[4].split()[0]
                
                l_match = re.search(r'`([^`]+)`', cols[5])
                ls = l_match.group(1) if l_match else '-'
                if ls not in ['-', '--', '-.', ':']:
                    ls = '-'
                
                m_match = re.search(r'`([^`]+)`', cols[6])
                marker = m_match.group(1) if m_match else ''
                if len(marker) > 1 and marker != 'None':
                    marker = marker[0]
                    
                models.append({
                    'name': name,
                    'color': color,
                    'ls': ls,
                    'marker': marker
                })

def get_style(name):
    for m in models:
        if m['name'] == name:
            lw = 3.0 if name == 'REMO-DQN' else 1.5
            z = 10 if name == 'REMO-DQN' else 1
            return m['color'], m['ls'], m['marker'], lw, z
    return 'black', '-', 'None', 1.0, 1

# 3. Plotting
plt.rcParams.update({'font.size': 12})

# 1. Reward Convergence
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'reward_convergence.csv'))
    plt.figure(figsize=(10,6))
    for m in models:
        name = m['name']
        if name in df.columns:
            c, ls, mk, lw, z = get_style(name)
            plt.plot(df['Episode'], df[name], color=c, linestyle=ls, linewidth=lw, zorder=z, label=name)
    plt.title('Reward Convergence Curve')
    plt.xlabel('Episodes')
    plt.ylabel('Cumulative Reward')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '1_reward_convergence.png'))
    plt.close()
except FileNotFoundError:
    pass

# 2. Ablation Study (Convergence Curve)
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'ablation_study.csv'))
    plt.figure(figsize=(10,6))
    plt.plot(df['Episode'], df['Vanilla DQN'], color='gray', linestyle='--', linewidth=1.5, label='Vanilla DQN')
    plt.plot(df['Episode'], df['DQN+MoE'], color='blue', linestyle='-.', linewidth=2.0, label='DQN+MoE')
    c_remo, ls_remo, _, lw_remo, _ = get_style('REMO-DQN')
    plt.plot(df['Episode'], df['REMO-DQN'], color=c_remo, linestyle=ls_remo, linewidth=lw_remo, label='REMO-DQN')
    plt.title('Ablation Study: Reward Convergence')
    plt.xlabel('Episodes')
    plt.ylabel('Cumulative Reward')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '2_ablation_study.png'))
    plt.close()
except FileNotFoundError:
    pass

# 3. MoE Routing Distribution
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'moe_routing.csv'))
    plt.figure(figsize=(8,6))
    plt.stackplot(df['Density'], df['Expert1 (Low Density)'], df['Expert2 (Medium Density)'], df['Expert3 (High Density)'], labels=['Expert1', 'Expert2', 'Expert3'], alpha=0.7)
    plt.title('MoE Routing Distribution vs Density')
    plt.xlabel('Vehicle Density (vehicles/km)')
    plt.ylabel('Routing Weight (%)')
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '3_moe_routing.png'))
    plt.close()
except FileNotFoundError:
    pass

# 4. t-SNE Scatter Plot
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'tsne_clustering.csv'))
    plt.figure(figsize=(8,6))
    colors = {'Low Traffic': 'green', 'Medium Traffic': 'orange', 'High Traffic': 'red'}
    for c_name, c_col in colors.items():
        subset = df[df['Cluster'] == c_name]
        plt.scatter(subset['x'], subset['y'], c=c_col, label=c_name, alpha=0.2, s=20)
    plt.title('t-SNE Clustering of State Features')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '4_tsne_clustering.png'))
    plt.close()
except FileNotFoundError:
    pass

# 5. Hardware Feasibility (Table only)
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'hardware_feasibility.csv'))
    fig, ax = plt.subplots(figsize=(6,3))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    table.scale(1, 2)
    table.auto_set_font_size(False)
    table.set_fontsize(14)
    plt.title('Hardware Feasibility of REMO-DQN', y=0.8)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '5_hardware_feasibility.png'))
    plt.close()
except FileNotFoundError:
    pass

# 7. CBR Trace
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'cbr_trace.csv'))
    plt.figure(figsize=(10,6))
    for m in models:
        name = m['name']
        if name in df.columns:
            c, ls, mk, lw, z = get_style(name)
            plt.plot(df['Time'], df[name], color=c, linestyle=ls, linewidth=lw, zorder=z, label=name)
    plt.axhline(y=0.6, color='red', linestyle='--', linewidth=2, label='Target Limit (0.6)')
    plt.title('Time-Series CBR Trace')
    plt.xlabel('Time (s)')
    plt.ylabel('CBR')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '7_cbr_trace.png'))
    plt.close()
except FileNotFoundError:
    pass

name_map = {
    'Fixed 10Hz': 'Fixed10Hz',
    'ReactDCC': 'ReactDCC',
    'AdaptDCC': 'AdaptDCC',
    'TinyMLP': 'StdMLP',
    'Q-Learning': 'QLearning',
    'SARSA': 'SARSA',
    'Actor-Critic': 'ActorCritic',
    'Vanilla DQN': 'DecTree',
    'PPO': 'PPO',
    'DDPG': 'DDPG',
    'Double DQN': 'DuelingDQN',
    'TD3': 'Heuristic',
    'Decision Transformer': 'DecisionTransformer',
    'SAC': 'MoEDQN',
    'MAPPO': 'ResNetMoEDQN',
    'REMO-DQN': 'Proposed'
}

# 8. PDR vs Density
try:
    df_raw = pd.read_csv(os.path.join(DATA_DIR, 'raw_metrics_density.csv'))
    plt.figure(figsize=(10,6))
    for m in models:
        name = m['name']
        raw_name = name_map.get(name, name)
        sub_df = df_raw[df_raw['method'] == raw_name]
        if not sub_df.empty:
            sub_df = sub_df.groupby('n_vehicles').mean(numeric_only=True).reset_index().sort_values('n_vehicles')
            c, ls, mk, lw, z = get_style(name)
            plt.plot(sub_df['n_vehicles'], sub_df['PDR_mean'], color=c, linestyle=ls, marker=mk if mk and mk != 'None' else None, linewidth=lw, zorder=z, label=name)
    plt.title('PDR vs Vehicle Density')
    plt.xlabel('Density (vehicles/km)')
    plt.ylabel('PDR (%)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '8_pdr_vs_density.png'))
    plt.close()
except FileNotFoundError:
    pass

# 9. AoI vs Density
try:
    df_raw = pd.read_csv(os.path.join(DATA_DIR, 'raw_metrics_density.csv'))
    plt.figure(figsize=(10,6))
    for m in models:
        name = m['name']
        raw_name = name_map.get(name, name)
        sub_df = df_raw[df_raw['method'] == raw_name]
        if not sub_df.empty:
            sub_df = sub_df.groupby('n_vehicles').mean(numeric_only=True).reset_index().sort_values('n_vehicles')
            c, ls, mk, lw, z = get_style(name)
            plt.plot(sub_df['n_vehicles'], sub_df['AoI_mean'], color=c, linestyle=ls, marker=mk if mk and mk != 'None' else None, linewidth=lw, zorder=z, label=name)
    plt.title('AoI vs Vehicle Density')
    plt.xlabel('Density (vehicles/km)')
    plt.ylabel('AoI (ms)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '9_aoi_vs_density.png'))
    plt.close()
except FileNotFoundError:
    pass

# 10. PDR vs Distance
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'pdr_vs_distance.csv'))
    plt.figure(figsize=(10,6))
    for m in models:
        name = m['name']
        if name in df.columns:
            c, ls, mk, lw, z = get_style(name)
            plt.plot(df['Distance'], df[name], color=c, linestyle=ls, marker=mk if mk and mk != 'None' else None, linewidth=lw, zorder=z, label=name)
    plt.title('PDR vs Distance')
    plt.xlabel('Distance (m)')
    plt.ylabel('PDR (%)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, '10_pdr_vs_distance.png'))
    plt.close()
except FileNotFoundError:
    pass

print("완료")
