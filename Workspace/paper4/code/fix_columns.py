import glob
import os

files = glob.glob("/home/imnyj/papers/paper4/sim/plot_*.py")

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Rename param_value to method if it reads from SAx_results
    if "pd.read_csv(CSV_PATH)" in content:
        content = content.replace("pd.read_csv(CSV_PATH)", "pd.read_csv(CSV_PATH).rename(columns={'param_value': 'method', 'n_vehicles': 'n_vehicles_dummy'})")
        # In plot_sweep.py, n_vehicles is a column? Wait, SA1 sets param_name = 'n_vehicles', param_value is the density.
        # Let's handle SA1 separately if needed. For SA2, rename param_value to method.
    
    with open(filepath, "w") as f:
        f.write(content)
