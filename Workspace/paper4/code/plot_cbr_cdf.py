import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

ARRAYS_PATH = "/home/imnyj/papers/paper4/paper/data/SA2_arrays.json"
OUT_DIR = "/home/imnyj/papers/paper4/paper/data/plots"

with open(ARRAYS_PATH, "r") as f:
    results = json.load(f)

cbr_data = []

for run in results:
    if run["status"] != "ok": continue
    method = run["method"]
    hist = run.get("cbr_history", [])
    if not hist: continue
    
    # Take a sample of the history or the whole thing to compute CDF
    # For boxplot/CDF, we just accumulate all CBR measurements for each method
    for val in hist:
        cbr_data.append({"method": method, "cbr": val * 100}) # convert to percentage

df_cbr = pd.DataFrame(cbr_data)

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

order = ['Fixed10Hz', 'Heuristic', 'AdaptDCC', 'ReactDCC', 'DecTree', 'StdMLP', 'Proposed']
# Ensure Proposed/TinyMLP naming consistency
df_cbr['method'] = df_cbr['method'].replace('Proposed', 'TinyMLP')
order = ['Fixed10Hz', 'Heuristic', 'AdaptDCC', 'ReactDCC', 'DecTree', 'StdMLP', 'TinyMLP']

plt.figure(figsize=(10, 6))
sns.boxplot(x='method', y='cbr', data=df_cbr, order=order, palette=colors_map, showfliers=False)
plt.axhline(y=60, color='r', linestyle='--', label='Target CBR (60%)')
plt.title('Channel Occupancy Stability (CBR Distribution)')
plt.ylabel('CBR (%)')
plt.xlabel('Method')
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_cbr_boxplot.png"), dpi=300)

print("CBR Boxplot saved.")

# Option to also plot CDF of CBR for a few methods
plt.figure(figsize=(8, 5))
methods_to_plot = ['ReactDCC', 'AdaptDCC', 'TinyMLP']
for m in methods_to_plot:
    subset = df_cbr[df_cbr['method'] == m]['cbr']
    sns.ecdfplot(data=subset, label=m, color=colors_map.get(m, 'black'), linewidth=3 if m == 'TinyMLP' else 2)

plt.axvline(x=60, color='r', linestyle='--', label='Target CBR (60%)')
plt.title('CBR Cumulative Distribution Function')
plt.xlabel('CBR (%)')
plt.ylabel('Cumulative Probability')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_cbr_cdf.png"), dpi=300)
print("CBR CDF saved.")
