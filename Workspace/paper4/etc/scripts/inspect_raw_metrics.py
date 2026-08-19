import pandas as pd

df_raw = pd.read_csv("/home/imnyj/Workspace/paper4/coder/data/raw_metrics_density.csv")
print("raw_metrics_density methods:", df_raw['method'].unique())
print("n_vehicles:", df_raw['n_vehicles'].unique())
print(df_raw.head())

df_eval = pd.read_csv("/home/imnyj/Workspace/paper4/data/evaluation/eval_density_results.csv")
print("\neval_density_results methods:", df_eval['method'].unique())
print("density:", df_eval['density'].unique())
print(df_eval.groupby(['method', 'density'])[['PDR_mean', 'AoI_mean', 'CBR_mean']].mean())

