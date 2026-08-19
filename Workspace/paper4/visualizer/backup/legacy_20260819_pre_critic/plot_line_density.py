import pandas as pd
import matplotlib.pyplot as plt
import os
from plot_utils import get_style, apply_legend, DATA_TO_CONFIG

DATA_FILE = "/home/imnyj/papers/paper4/paper/data/SA1_results.csv"
OUT_DIR = "/home/imnyj/papers/paper4/paper/data/plots"

df = pd.read_csv(DATA_FILE, header=None, skiprows=1)
df.columns = ["sweep_id","param_name","param_value","seed","AoI_mean","CBR_mean","PDR_mean","energy_efficiency","ETSI_compliance","runtime_sec","n_cam_events","status","error","method"]

agg = df.groupby(["method", "param_value"]).agg({
    "AoI_mean": "mean",
    "CBR_mean": "mean"
}).reset_index()

methods = agg['method'].dropna().unique()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

for method in methods:
    m_df = agg[agg['method'] == method].sort_values("param_value")
    x = m_df["param_value"]
    c, ls, m, lw, z = get_style(method)
    lbl = DATA_TO_CONFIG.get(method, method)
    
    ax1.plot(x, m_df["AoI_mean"], color=c, linestyle=ls, marker=m, linewidth=lw, zorder=z, label=lbl)
    ax2.plot(x, m_df["CBR_mean"], color=c, linestyle=ls, marker=m, linewidth=lw, zorder=z, label=lbl)

ax1.set_xlabel("Number of Vehicles")
ax1.set_ylabel("Mean AoI (ms)")
ax1.set_title("AoI vs Vehicle Density")
ax1.grid(True)

ax2.set_xlabel("Number of Vehicles")
ax2.set_ylabel("Mean CBR")
ax2.set_title("CBR vs Vehicle Density")
ax2.grid(True)

apply_legend(ax2)

fig.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "line_density.png"), bbox_inches='tight', dpi=300)
print("Saved line_density.png")
