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

# 2. Generate Dummy Data
np.random.seed(42)

# Graph 1: Reward Convergence
episodes = np.arange(1, 1001, 10)
reward_data = {'Episode': episodes}
for m in models:
    if m['name'] == 'REMO-DQN':
        r = -50 + 150 * (1 - np.exp(-episodes/200)) + np.random.normal(0, 5, len(episodes))
    else:
        r = -100 + 120 * (1 - np.exp(-episodes/np.random.uniform(300, 800))) + np.random.normal(0, 10, len(episodes))
    reward_data[m['name']] = r
pd.DataFrame(reward_data).to_csv(os.path.join(DATA_DIR, 'reward_convergence.csv'), index=False)

# Graph 2: Ablation Study (Convergence Curve)
ablation_episodes = np.arange(1, 1001, 10)
ablation_data = {'Episode': ablation_episodes}
ablation_data['Vanilla DQN'] = -100 + 100 * (1 - np.exp(-ablation_episodes/600)) + np.random.normal(0, 15, len(ablation_episodes))
ablation_data['DQN+MoE'] = -80 + 120 * (1 - np.exp(-ablation_episodes/400)) + np.random.normal(0, 10, len(ablation_episodes))
ablation_data['REMO-DQN'] = -50 + 150 * (1 - np.exp(-ablation_episodes/200)) + np.random.normal(0, 3, len(ablation_episodes))
pd.DataFrame(ablation_data).to_csv(os.path.join(DATA_DIR, 'ablation_study.csv'), index=False)

# Densities used for 3, 8, 9 (interpolated to 50 points)
densities = np.linspace(10, 100, 50)

# Graph 3: MoE Routing Distribution
moe_data = {'Density': densities, 
            'Expert1 (Low Density)': np.clip(100 - densities, 0, 100),
            'Expert2 (Medium Density)': np.clip(50 - np.abs(densities - 50)*1.5, 0, 100),
            'Expert3 (High Density)': np.clip(densities * 1.2 - 20, 0, 100)}
pd.DataFrame(moe_data).to_csv(os.path.join(DATA_DIR, 'moe_routing.csv'), index=False)

# Graph 4: t-SNE Scatter Plot (N x 5 = 1500)
tsne_data = pd.DataFrame({
    'x': np.random.normal(0, 1, 1500),
    'y': np.random.normal(0, 1, 1500),
    'Cluster': np.random.choice(['Low Traffic', 'Medium Traffic', 'High Traffic'], 1500)
})
tsne_data.to_csv(os.path.join(DATA_DIR, 'tsne_clustering.csv'), index=False)

# Graph 5: Hardware Feasibility (Table for REMO-DQN only)
hw_data = pd.DataFrame({
    'Metric': ['Parameters', 'MACs/FLOPs', 'Inference Time', 'RAM Usage'],
    'REMO-DQN': ['3.5M', '12.4G', '8 ms', '150 MB']
})
hw_data.to_csv(os.path.join(DATA_DIR, 'hardware_feasibility.csv'), index=False)

# Graph 7: CBR Trace (Target Limit ~ 0.6)
time_s = np.arange(0, 101, 1)
cbr_data = {'Time': time_s}
for m in models:
    if m['name'] == 'REMO-DQN':
        cbr_data[m['name']] = 0.61 + np.random.normal(0, 0.005, len(time_s))
    elif m['name'] == 'AdaptDCC':
        cbr_data[m['name']] = 0.55 + 0.25 * np.sin(time_s/5) + np.random.normal(0, 0.02, len(time_s))
    else:
        cbr_data[m['name']] = np.random.uniform(0.3, 0.9) + np.random.normal(0, 0.05, len(time_s))
pd.DataFrame(cbr_data).to_csv(os.path.join(DATA_DIR, 'cbr_trace.csv'), index=False)

# Graph 8: PDR vs Density (REMO-DQN top, others drop sharply to 0~20%)
pdr_data = {'Density': densities}
for m in models:
    if m['name'] == 'REMO-DQN':
        pdr_data[m['name']] = 76.0 + np.random.normal(0, 0.5, len(densities)) - (densities - 10) * 0.02
    else:
        # others drop sharply
        drop_rate = np.random.uniform(0.8, 1.5)
        pdr = 90 - drop_rate * (densities - 10) + np.random.normal(0, 2, len(densities))
        pdr_data[m['name']] = np.clip(pdr, 0, 30) if m['name'] in ['SAC', 'PPO', 'DDPG', 'MAPPO'] else np.clip(pdr, 0, 100)
pd.DataFrame(pdr_data).to_csv(os.path.join(DATA_DIR, 'pdr_vs_density.csv'), index=False)

# Graph 9: AoI vs Density
aoi_data = {'Density': densities}
for m in models:
    if m['name'] == 'REMO-DQN':
        base = 150
        rise = 5
    else:
        base = np.random.uniform(100, 3000)
        rise = np.random.uniform(10, 60)
    aoi = base + rise * (densities - 10) + np.random.normal(0, 20, len(densities))
    aoi_data[m['name']] = np.clip(aoi, 0, 10000)
pd.DataFrame(aoi_data).to_csv(os.path.join(DATA_DIR, 'aoi_vs_density.csv'), index=False)

# Graph 10: PDR vs Distance
distances = np.arange(50, 501, 50)
pdr_dist_data = {'Distance': distances}
for m in models:
    if m['name'] == 'REMO-DQN':
        base = 95
        drop = 0.05
    else:
        base = np.random.uniform(70, 95)
        drop = np.random.uniform(0.08, 0.2)
    pdr_dist = base - drop * distances + np.random.normal(0, 2, len(distances))
    pdr_dist_data[m['name']] = np.clip(pdr_dist, 0, 100)
pd.DataFrame(pdr_dist_data).to_csv(os.path.join(DATA_DIR, 'pdr_vs_distance.csv'), index=False)


# 3. Plotting
plt.rcParams.update({'font.size': 12})

# 1. Reward Convergence
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

# 2. Ablation Study (Convergence Curve)
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

# 3. MoE Routing Distribution
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

# 4. t-SNE Scatter Plot
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

# 5. Hardware Feasibility (Table only)
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

# 7. CBR Trace
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

# 8. PDR vs Density
df = pd.read_csv(os.path.join(DATA_DIR, 'pdr_vs_density.csv'))
plt.figure(figsize=(10,6))
for m in models:
    name = m['name']
    if name in df.columns:
        c, ls, mk, lw, z = get_style(name)
        plt.plot(df['Density'], df[name], color=c, linestyle=ls, marker=mk if mk and mk != 'None' else None, linewidth=lw, zorder=z, label=name)
plt.title('PDR vs Vehicle Density')
plt.xlabel('Density (vehicles/km)')
plt.ylabel('PDR (%)')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(VIS_DIR, '8_pdr_vs_density.png'))
plt.close()

# 9. AoI vs Density
df = pd.read_csv(os.path.join(DATA_DIR, 'aoi_vs_density.csv'))
plt.figure(figsize=(10,6))
for m in models:
    name = m['name']
    if name in df.columns:
        c, ls, mk, lw, z = get_style(name)
        plt.plot(df['Density'], df[name], color=c, linestyle=ls, marker=mk if mk and mk != 'None' else None, linewidth=lw, zorder=z, label=name)
plt.title('AoI vs Vehicle Density')
plt.xlabel('Density (vehicles/km)')
plt.ylabel('AoI (ms)')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(VIS_DIR, '9_aoi_vs_density.png'))
plt.close()

# 10. PDR vs Distance
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

print("완료")
