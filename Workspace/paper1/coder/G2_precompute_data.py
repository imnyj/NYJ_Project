import torch
import numpy as np
import pandas as pd
import pickle
import os
import sys
from torch.utils.data import TensorDataset, DataLoader

# Add Command/core to path for lock manager and audit logger
sys.path.append("/home/imnyj/Command/core")
from lock_manager import LockManager
from audit_logger import AuditLogger

from dataset import get_dataloaders

DATA_DIRS = [
    "/home/imnyj/SumoNetSim1.1.6/data",
    "/home/imnyj/papers/paper1/paper/data(Desk01)",
    "/home/imnyj/papers/paper1/paper/data(Desk02)"
]
BATCH_SIZE = 2048

def safe_write_pkl(data, path, agent_id="worker_g2"):
    lm = LockManager()
    logger = AuditLogger()
    if lm.acquire(path, agent_id):
        try:
            with open(path, "wb") as f:
                pickle.dump(data, f)
            logger.log_action(agent_id, "CREATE", path, f"Saved precomputed ablation dataset to {path}")
        finally:
            lm.release(path, agent_id)

def main():
    print("Loading datasets...")
    train_loader, val_loader, scaler = get_dataloaders(DATA_DIRS, batch_size=BATCH_SIZE)
    
    print("Loading XGBoost prior models...")
    with open("/home/imnyj/papers/paper1/code/saved_models/XGB_Hybrid_Base_y1_best.pkl", "rb") as f:
        xgb_y1 = pickle.load(f)
    with open("/home/imnyj/papers/paper1/code/saved_models/XGB_Hybrid_Base_y2_best.pkl", "rb") as f:
        xgb_y2 = pickle.load(f)

    # Precompute XGBoost predictions for Train Set
    print("Precomputing XGBoost predictions for Train Set...")
    X_train_flat = []
    all_xk, all_xt, all_xs, all_y = [], [], [], []
    for x_k, x_t, x_s, y in train_loader:
        all_xk.append(x_k)
        all_xt.append(x_t)
        all_xs.append(x_s)
        all_y.append(y)
        X_train_flat.append(torch.cat([x_k, x_t, x_s], dim=1).numpy())
    
    X_train_flat = np.vstack(X_train_flat)
    p1 = xgb_y1.predict(X_train_flat)
    p2 = xgb_y2.predict(X_train_flat)
    xp_train = torch.tensor(np.column_stack((p1, p2)), dtype=torch.float32)
    
    all_xk = torch.cat(all_xk)
    all_xt = torch.cat(all_xt)
    all_xs = torch.cat(all_xs)
    all_y = torch.cat(all_y)
    
    # Precompute XGBoost predictions for Validation Set
    print("Precomputing XGBoost predictions for Validation Set...")
    X_val_flat = []
    val_xk, val_xt, val_xs, val_y = [], [], [], []
    for x_k, x_t, x_s, y in val_loader:
        val_xk.append(x_k)
        val_xt.append(x_t)
        val_xs.append(x_s)
        val_y.append(y)
        X_val_flat.append(torch.cat([x_k, x_t, x_s], dim=1).numpy())
        
    X_val_flat = np.vstack(X_val_flat)
    p1_val = xgb_y1.predict(X_val_flat)
    p2_val = xgb_y2.predict(X_val_flat)
    xp_val = torch.tensor(np.column_stack((p1_val, p2_val)), dtype=torch.float32)
    
    val_xk = torch.cat(val_xk)
    val_xt = torch.cat(val_xt)
    val_xs = torch.cat(val_xs)
    val_y = torch.cat(val_y)
    
    # Pack data
    precomputed_data = {
        "all_xk": all_xk,
        "all_xt": all_xt,
        "all_xs": all_xs,
        "xp_train": xp_train,
        "all_y": all_y,
        "val_xk": val_xk,
        "val_xt": val_xt,
        "val_xs": val_xs,
        "xp_val": xp_val,
        "val_y": val_y
    }
    
    out_path = "/home/imnyj/papers/paper1/data/ablation_precomputed_data.pkl"
    safe_write_pkl(precomputed_data, out_path)
    print("Precomputation finished and saved successfully.")

if __name__ == "__main__":
    main()
