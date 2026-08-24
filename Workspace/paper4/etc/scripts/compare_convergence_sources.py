#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np

data_dir = "/home/imnyj/Workspace/paper4/data"

df_remo_log = pd.read_csv(os.path.join(data_dir, "models", "REMO-DQN_convergence.csv"))
df_reward_conv = pd.read_csv(os.path.join(data_dir, "reward_convergence.csv"))
df_resnet_train = pd.read_csv("/home/imnyj/Workspace/paper4/code/resnet_train_log.csv")

print("=== REMO-DQN_convergence.csv vs reward_convergence.csv ===")
print("REMO-DQN_convergence.csv (First 15 episodes):")
print(df_remo_log[['Episode', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean', 'Epsilon', 'Density']].head(15))

print("\nREMO-DQN_convergence.csv (Last 15 episodes):")
print(df_remo_log[['Episode', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean', 'Epsilon', 'Density']].tail(15))

print("\nreward_convergence.csv['REMO-DQN'] (First 15 vs Last 15):")
print("First 15:", df_reward_conv['REMO-DQN'].head(15).values)
print("Last 15 :", df_reward_conv['REMO-DQN'].tail(15).values)

print("\nAre columns in reward_convergence.csv different from data/models/*_convergence.csv?")
print("Checking correlation or transformation between REMO-DQN_convergence.csv and reward_convergence.csv...")
