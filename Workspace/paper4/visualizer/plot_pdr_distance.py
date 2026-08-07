import json
import numpy as np
import matplotlib.pyplot as plt
import os
from plot_utils import get_style, apply_legend, DATA_TO_CONFIG

DATA_FILE = "/home/imnyj/papers/paper4/paper/data/SA1_arrays.json"
OUT_DIR = "/home/imnyj/papers/paper4/paper/data/plots"

if not os.path.exists(DATA_FILE):
    print("No data yet.")
    exit(0)

with open(DATA_FILE, 'r') as f:
    data = json.load(f)

# Group by method for n_vehicles == 100
# If n_vehicles=100 doesn't have data, just take the max density
methods = {}
for row in data:
    if int(row["param_value"]) == 100:
        meth = row.get("method")
        pdr_arr = row.get("distance_pdr", [])
        if pdr_arr and len(pdr_arr) == 6:
            if meth not in methods:
                methods[meth] = []
            methods[meth].append(pdr_arr)

if not methods:
    print("No valid distance_pdr data found in SA1_arrays.json")
    exit(0)

fig, ax = plt.subplots(figsize=(8, 6))
buckets = [25, 75, 125, 175, 225, 275]  # Midpoints

for meth, arrs in methods.items():
    mean_pdr = np.mean(arrs, axis=0)
    c, ls, m, lw, z = get_style(meth)
    lbl = DATA_TO_CONFIG.get(meth, meth)
    ax.plot(buckets, mean_pdr, color=c, linestyle=ls, marker=m, linewidth=lw, zorder=z, label=lbl)

ax.set_xlabel("Distance (m)")
ax.set_ylabel("Packet Delivery Ratio (PDR) %")
ax.set_title("PDR vs Distance (100 Vehicles)")
ax.grid(True)
apply_legend(ax)

fig.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "pdr_distance.png"), bbox_inches='tight', dpi=300)
print("Saved pdr_distance.png")
