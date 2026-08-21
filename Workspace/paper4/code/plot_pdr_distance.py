import json
import matplotlib.pyplot as plt
import os
import numpy as np

_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_project_root, "data"))
ARRAYS_PATH = os.path.join(DATA_DIR, "SA2_arrays.json")
OUT_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(OUT_DIR, exist_ok=True)

with open(ARRAYS_PATH, "r") as f:
    results = json.load(f)

# Aggregate distance PDR across seeds for each method
method_pdr = {}
for run in results:
    if run["status"] != "ok": continue
    method = run["method"]
    dist_pdr = run.get("distance_pdr", [])
    if not dist_pdr: continue
    
    if method not in method_pdr:
        method_pdr[method] = []
    method_pdr[method].append(dist_pdr)

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

dist_labels = ["0-50m", "50-100m", "100-150m", "150-200m", "200-250m", "250-300m"]

plt.figure(figsize=(8, 5))
for method, pdrs in method_pdr.items():
    # pdrs is a list of lists. average over seeds.
    avg_pdr = np.mean(pdrs, axis=0)
    c = colors_map.get(method, 'black')
    lw = 3 if 'Proposed' in method or 'TinyMLP' in method else 1.5
    plt.plot(dist_labels[:len(avg_pdr)], avg_pdr, marker='^', linewidth=lw, color=c, label=method)

plt.xlabel('Distance Range')
plt.ylabel('Packet Delivery Ratio (%)')
plt.title('Spatial Reliability: PDR vs Distance')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_pdr_distance.png"), dpi=300)
print("Distance PDR plot saved.")
