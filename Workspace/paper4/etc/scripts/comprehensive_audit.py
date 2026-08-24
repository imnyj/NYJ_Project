import os
import pandas as pd
import numpy as np
from PIL import Image

base_dir = "/home/imnyj/Workspace/paper4"
data_dir = os.path.join(base_dir, "data")
vis_dir = os.path.join(base_dir, "visualizer")

print("=================================================================")
print("=== COMPREHENSIVE AUDIT OF 11 TARGET DATASETS & VISUALIZERS ===")
print("=================================================================")

target_datasets = [
    ("1. Ablation Study", "ablation_study.csv", (100, 9)),
    ("1a. Ablation Structure", "ablation_structure.csv", (100, 6)),
    ("1b. Ablation Reward", "ablation_reward.csv", (100, 6)),
    ("2. Optuna Sensitivity Table", "optuna_sensitivity_table.csv", (17, 7)),
    ("3. Reward Convergence", "reward_convergence.csv", (100, 19)),
    ("4. t-SNE Clustering", "tsne_clustering.csv", (300, 3)),
    ("5. MoE Routing", "moe_routing.csv", (11, 4)),
    ("6. CBR Trace", "cbr_trace.csv", (100, 18)),
    ("7. PDR vs Density", "pdr_vs_density.csv", (5, 18)),
    ("8. AoI vs Density", "aoi_vs_density.csv", (5, 18)),
    ("9. PDR vs Distance", "pdr_vs_distance.csv", (7, 18)),
    ("10. AoI vs Distance", "aoi_vs_distance.csv", (7, 18)),
    ("11. Hardware Feasibility Table", "hardware_feasibility_table.csv", (11, 7)),
]

print("\n--- [PART 1] Target CSV Validation ---")
csv_results = []
for label, fname, expected_shape in target_datasets:
    fpath = os.path.join(data_dir, fname)
    if not os.path.exists(fpath):
        print(f"[FAIL] {label}: File not found: {fpath}")
        csv_results.append((label, fname, "MISSING", None, 0, 0))
        continue
    df = pd.read_csv(fpath)
    shape = df.shape
    null_count = int(df.isnull().sum().sum())
    inf_count = int(np.isinf(df.select_dtypes(include=[np.number])).sum().sum()) if not df.empty else 0
    shape_match = (shape == expected_shape) or (shape[0] == expected_shape[0] and shape[1] >= expected_shape[1])
    status = "PASS" if shape_match and null_count == 0 and inf_count == 0 else "WARNING"
    print(f"[{status}] {label:30s} | Shape: {str(shape):10s} (Exp: {str(expected_shape):10s}) | Nulls: {null_count} | Infs: {inf_count}")
    csv_results.append((label, fname, status, shape, null_count, inf_count))

print("\n--- [PART 2] Numerical Range & Trend Verification ---")

# 1. Ablation Study
df_abl = pd.read_csv(os.path.join(data_dir, "ablation_study.csv"))
print(f"Ablation Study Step Range: {df_abl['Global_Step'].min()} ~ {df_abl['Global_Step'].max()}")
print(f"Ablation REMO-DQN Reward: Start={df_abl['REMO-DQN'].iloc[0]:.2f}, End={df_abl['REMO-DQN'].iloc[-1]:.2f}, Max={df_abl['REMO-DQN'].max():.2f}")

# 2. PDR vs Density
df_pdr = pd.read_csv(os.path.join(data_dir, "pdr_vs_density.csv"))
pdr_cols = [c for c in df_pdr.columns if c != "Density"]
pdr_min = df_pdr[pdr_cols].min().min()
pdr_max = df_pdr[pdr_cols].max().max()
print(f"PDR vs Density Range: {pdr_min:.2f}% ~ {pdr_max:.2f}% (Valid: 0 <= PDR <= 100)")

# 3. CBR Trace
df_cbr = pd.read_csv(os.path.join(data_dir, "cbr_trace.csv"))
cbr_cols = [c for c in df_cbr.columns if c != "Time"]
cbr_min = df_cbr[cbr_cols].min().min()
cbr_max = df_cbr[cbr_cols].max().max()
print(f"CBR Trace Range: {cbr_min:.4f} ~ {cbr_max:.4f} (Valid: 0 <= CBR <= 1.0)")

# 4. AoI vs Density
df_aoi = pd.read_csv(os.path.join(data_dir, "aoi_vs_density.csv"))
aoi_cols = [c for c in df_aoi.columns if c != "Density"]
aoi_min = df_aoi[aoi_cols].min().min()
aoi_max = df_aoi[aoi_cols].max().max()
print(f"AoI vs Density Range: {aoi_min:.2f}ms ~ {aoi_max:.2f}ms (Valid: AoI > 0)")

# 5. MoE Routing
df_moe = pd.read_csv(os.path.join(data_dir, "moe_routing.csv"))
print("MoE Routing Values:")
print(df_moe)

print("\n--- [PART 3] Visualizer Artifacts & DPI Verification ---")
target_visuals = [
    ("1_ablation_study.png", "1_ablation_study.pdf"),
    ("2_optuna_sensitivity_table.csv", "2_optuna_sensitivity_table.tex"),
    ("3_reward_convergence.png", "3_reward_convergence.pdf"),
    ("4_tsne_clustering.png", "4_tsne_clustering.pdf"),
    ("5_moe_routing.png", "5_moe_routing.pdf"),
    ("6_cbr_trace.png", "6_cbr_trace.pdf"),
    ("7_pdr_vs_density.png", "7_pdr_vs_density.pdf"),
    ("8_aoi_vs_density.png", "8_aoi_vs_density.pdf"),
    ("9_pdr_vs_distance.png", "9_pdr_vs_distance.pdf"),
    ("10_aoi_vs_distance.png", "10_aoi_vs_distance.pdf"),
    ("11_hardware_feasibility_table.csv", "11_hardware_feasibility_table.tex")
]

for item in target_visuals:
    p1 = os.path.join(vis_dir, item[0])
    p2 = os.path.join(vis_dir, item[1])
    exists_1 = os.path.exists(p1)
    exists_2 = os.path.exists(p2)
    
    dpi_info = ""
    size_info = ""
    if exists_1 and item[0].endswith(".png"):
        try:
            with Image.open(p1) as img:
                dpi = img.info.get('dpi', (None, None))
                w, h = img.size
                dpi_info = f"DPI: {dpi[0]}x{dpi[1]}" if dpi[0] is not None else "DPI: None"
                size_info = f"Size: {w}x{h} px"
        except Exception as e:
            dpi_info = f"Error reading img: {e}"
            
    print(f"Visual: {item[0]:35s} (Exists: {str(exists_1):5s}) | {item[1]:35s} (Exists: {str(exists_2):5s}) | {dpi_info} | {size_info}")

