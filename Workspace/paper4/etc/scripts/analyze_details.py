import os
import pandas as pd
import json

print("=== 1. eval_density_results.csv ===")
df_eval = pd.read_csv("/home/imnyj/Workspace/paper4/data/evaluation/eval_density_results.csv")
print("Methods in eval_density_results:", df_eval['method'].unique())
print("Densities:", sorted(df_eval['density'].unique()))
print(df_eval.head(5))

print("\n=== 2. coder/data/pdr_vs_density.csv ===")
df_pdr = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/pdr_vs_density.csv")
print("Columns in coder/data/pdr_vs_density.csv:", list(df_pdr.columns))
print(df_pdr.head(3))

print("\n=== 3. coder/data/aoi_vs_density.csv ===")
df_aoi = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/aoi_vs_density.csv")
print("Columns in coder/data/aoi_vs_density.csv:", list(df_aoi.columns))
print(df_aoi.head(3))

print("\n=== 4. coder/data/cbr_trace.csv ===")
df_cbr = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/cbr_trace.csv")
print("Columns in coder/data/cbr_trace.csv:", list(df_cbr.columns))
print(df_cbr.head(3))

print("\n=== 5. coder/data/pdr_vs_distance.csv ===")
df_dist = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/pdr_vs_distance.csv")
print("Columns in coder/data/pdr_vs_distance.csv:", list(df_dist.columns))
print(df_dist)

print("\n=== 6. coder/data/ablation_study.csv ===")
df_abl = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/ablation_study.csv")
print("Columns in coder/data/ablation_study.csv:", list(df_abl.columns))
print(df_abl)

print("\n=== 7. coder/data/hardware_feasibility.csv ===")
df_hw = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/hardware_feasibility.csv")
print("Columns in coder/data/hardware_feasibility.csv:", list(df_hw.columns))
print(df_hw)

print("\n=== 8. coder/data/moe_routing.csv ===")
df_moe = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/moe_routing.csv")
print("Columns in coder/data/moe_routing.csv:", list(df_moe.columns))
print(df_moe)

print("\n=== 9. optuna ===")
with open("/home/imnyj/Workspace/paper4/data/optuna/all_best_params.json") as f:
    print("all_best_params keys:", list(json.load(f).keys()))

