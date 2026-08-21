import pandas as pd
import matplotlib.pyplot as plt
import os

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
CSV_PATH = os.path.join(DATA_DIR, "SA1_results.csv")
OUT_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)
# aggregate by method and n_vehicles
df_agg = df.groupby(['method', 'param_value']).agg({
    'AoI_mean': 'mean',
    'CBR_mean': 'mean'
}).reset_index()

df_agg.rename(columns={'param_value': 'n_vehicles'}, inplace=True)
df_agg['n_vehicles'] = df_agg['n_vehicles'].astype(int)

colors_map = {
    'Fixed10Hz': '#cccccc',
    'Heuristic': '#aaaaaa',
    'AdaptDCC': '#777777',
    'ReactDCC': '#444444',
    'DecTree': '#1f77b4',
    'StdMLP': '#ff7f0e',
    'Proposed': '#cc0000',
    'TinyMLP': '#cc0000'
}

plt.figure(figsize=(8, 5))
for method in df_agg['method'].unique():
    subset = df_agg[df_agg['method'] == method].sort_values('n_vehicles')
    c = colors_map.get(method, 'black')
    lw = 3 if 'Proposed' in method or 'TinyMLP' in method else 1.5
    plt.plot(subset['n_vehicles'], subset['AoI_mean'], marker='o', linewidth=lw, color=c, label=method)

plt.xlabel('Vehicle Density (Vehicles/km)')
plt.ylabel('Mean Age of Information (ms)')
plt.title('Scalability: AoI vs Vehicle Density')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_aoi_density.png"), dpi=300)

plt.figure(figsize=(8, 5))
for method in df_agg['method'].unique():
    subset = df_agg[df_agg['method'] == method].sort_values('n_vehicles')
    c = colors_map.get(method, 'black')
    lw = 3 if 'Proposed' in method or 'TinyMLP' in method else 1.5
    plt.plot(subset['n_vehicles'], subset['CBR_mean']*100, marker='s', linewidth=lw, color=c, label=method)

plt.axhline(y=60, color='r', linestyle=':', label='Target CBR (60%)')
plt.xlabel('Vehicle Density (Vehicles/km)')
plt.ylabel('Mean CBR (%)')
plt.title('Scalability: CBR vs Vehicle Density')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_cbr_density.png"), dpi=300)
print("Density line plots saved.")
