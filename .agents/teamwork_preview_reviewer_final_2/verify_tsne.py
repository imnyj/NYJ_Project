import re
import os
import pandas as pd
import numpy as np

# Verify Table XIV (Table 5.12) values
tsne_csv = "/home/imnyj/Workspace/paper4/coder/data/tsne_clustering.csv"
if os.path.exists(tsne_csv):
    df_tsne = pd.read_csv(tsne_csv)
    print("Found tsne_clustering.csv with shape:", df_tsne.shape)
    for c in df_tsne['Cluster'].unique():
        sub = df_tsne[df_tsne['Cluster'] == c]
        print(f"  Cluster {c}: samples={len(sub)}, mean_x={sub['x'].mean():.3f}, std_x={sub['x'].std():.3f}, mean_y={sub['y'].mean():.3f}, std_y={sub['y'].std():.3f}")
