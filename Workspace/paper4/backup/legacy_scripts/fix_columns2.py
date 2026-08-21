import glob

files = [
    "/home/imnyj/papers/paper4/sim/plot_results.py",
    "/home/imnyj/papers/paper4/sim/plot_bubble.py",
    "/home/imnyj/papers/paper4/sim/plot_radar.py"
]

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Rename param_value to method
    old_read = "df = pd.read_csv(CSV_PATH)"
    new_read = "df = pd.read_csv(CSV_PATH).rename(columns={'param_value': 'method'})"
    content = content.replace(old_read, new_read)
    
    with open(filepath, "w") as f:
        f.write(content)
