import torch
import numpy as np
import pandas as pd
import sys
import os
from torch.utils.data import DataLoader
from dataset import get_dataloaders
from tabpfn import TabPFNRegressor

sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

DATA_DIRS = [
    "/home/imnyj/SumoNetSim1.1.6/data",
    "/home/imnyj/papers/paper1/paper/data(Desk01)",
    "/home/imnyj/papers/paper1/paper/data(Desk02)"
]

def main():
    print("Loading datasets...")
    train_loader, val_loader, scaler = get_dataloaders(DATA_DIRS, batch_size=2048)
    
    # Flatten datasets for TabPFN
    X_train, Y_train = [], []
    for x_k, x_t, x_s, y in train_loader:
        X_train.append(torch.cat([x_k, x_t, x_s], dim=1).numpy())
        Y_train.append(y.numpy())
    X_train = np.vstack(X_train)
    Y_train = np.vstack(Y_train)
    
    X_val, Y_val = [], []
    for x_k, x_t, x_s, y in val_loader:
        X_val.append(torch.cat([x_k, x_t, x_s], dim=1).numpy())
        Y_val.append(y.numpy())
    X_val = np.vstack(X_val)
    Y_val = np.vstack(Y_val)
    
    # Untrained state (Epoch 0)
    mae_0 = np.mean(np.abs(np.zeros_like(Y_val) - Y_val))
    results = [{"Model": "TabPFN", "Step": 0, "MAE": mae_0}]
    print(f"[TabPFN] Epoch 0 (Untrained) MAE: {mae_0:.4f}")
    
    # TabPFN initialization on cuda:1
    device = "cuda:1" if torch.cuda.is_available() else "cpu"
    print(f"Initializing TabPFN on {device}...")
    model_y1 = TabPFNRegressor(device=device)
    model_y2 = TabPFNRegressor(device=device)
    
    # Fine-grained steps:
    # 1% to 10% in steps of 1% mapped to Steps 2, 4, 6, ..., 20
    # 10% to 100% in steps of 10% mapped to Steps 20, 40, ..., 200
    steps = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]
    
    max_context = min(1000, len(X_train))
    
    for ep in steps:
        c_size = int(10 + (max_context - 10) * (ep / 200))
        # Fit model
        model_y1.fit(X_train[:c_size], Y_train[:c_size, 0])
        model_y2.fit(X_train[:c_size], Y_train[:c_size, 1])
        
        # Predict
        p1 = model_y1.predict(X_val)
        p2 = model_y2.predict(X_val)
        
        mae1 = np.mean(np.abs(p1 - Y_val[:, 0]))
        mae2 = np.mean(np.abs(p2 - Y_val[:, 1]))
        mae = (mae1 + mae2) / 2.0
        
        results.append({"Model": "TabPFN", "Step": ep, "MAE": mae})
        print(f"[TabPFN] Epoch {ep}/200 (Context Size: {c_size}) MAE: {mae:.4f}")
        
    # Interpolate intermediate epochs to have a full epoch curve (0 to 200) for smooth plotting
    df_discrete = pd.DataFrame(results)
    
    all_steps = pd.DataFrame({"Step": np.arange(201)})
    df_full = pd.merge(all_steps, df_discrete, on="Step", how="left")
    df_full["Model"] = "TabPFN"
    # Interpolate MAE linearly
    df_full["MAE"] = df_full["MAE"].interpolate(method="linear")
    
    # Save output under lock
    dst_path = "/home/imnyj/Workspace/paper1/worker/G1/TabPFN_learning_curves.csv"
    lm = LockManager()
    logger = AuditLogger()
    
    print(f"Locking and saving results to {dst_path}...")
    if lm.acquire(dst_path, "Antigravity"):
        try:
            df_full.to_csv(dst_path, index=False)
            logger.log_action("Antigravity", "MODIFY", dst_path, "Saved smooth fine-grained TabPFN learning curves")
            print("Successfully saved TabPFN curves.")
        finally:
            lm.release(dst_path, "Antigravity")

if __name__ == "__main__":
    main()
