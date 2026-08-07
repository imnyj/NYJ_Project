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

# Group CBR history by method for n_vehicles == 100
methods = {}
for row in data:
    if int(row["param_value"]) == 100:
        meth = row.get("method")
        cbr_arr = row.get("cbr_history", [])
        if cbr_arr:
            if meth not in methods:
                methods[meth] = []
            methods[meth].extend(cbr_arr)

if not methods:
    print("No valid cbr_history data found in SA1_arrays.json")
    exit(0)

fig, ax = plt.subplots(figsize=(8, 6))

for meth, cbr_list in methods.items():
    c, ls, m, lw, z = get_style(meth)
    lbl = DATA_TO_CONFIG.get(meth, meth)
    
    # Compute CDF
    sorted_data = np.sort(cbr_list)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    
    # For CDF, we usually don't use markers if there are thousands of points, 
    # but we can use markevery to show markers without cluttering
    ax.plot(sorted_data, yvals, color=c, linestyle=ls, marker=m, linewidth=lw, 
            markevery=len(sorted_data)//10 + 1, zorder=z, label=lbl)

ax.set_xlabel("Channel Busy Ratio (CBR)")
ax.set_ylabel("CDF")
ax.set_title("CBR Cumulative Distribution (100 Vehicles)")
ax.grid(True)
apply_legend(ax)

fig.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "cbr_cdf.png"), bbox_inches='tight', dpi=300)
print("Saved cbr_cdf.png")
