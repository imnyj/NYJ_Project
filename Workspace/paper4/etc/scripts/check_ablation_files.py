import pandas as pd
import glob

print("=== Structure train logs ===")
for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/data/ablation_structure/*_train_log.csv")):
    df = pd.read_csv(p)
    print(p)
    print(df)

print("\n=== Reward train logs ===")
for p in sorted(glob.glob("/home/imnyj/Workspace/paper4/data/ablation_reward/*.csv")):
    df = pd.read_csv(p)
    print(p)
    print(df)

