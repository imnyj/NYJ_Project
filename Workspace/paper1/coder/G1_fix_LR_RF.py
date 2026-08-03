import torch
import numpy as np
import pandas as pd
from dataset import get_dataloaders
from sklearn.linear_model import SGDRegressor
from sklearn.ensemble import RandomForestRegressor
import os

def main():
    print("Loading data...")
    from G1_learning import DATA_DIRS
    train_loader, val_loader, test_loader = get_dataloaders(DATA_DIRS, batch_size=2048)
    
    # Flatten datasets for ML models
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
    
    results = []
    
    # --- 1. LR using SGDRegressor ---
    print("\n--- Training LR (SGDRegressor) ---")
    # Using invscaling to avoid divergence, and warm_start=True
    lr_y1 = SGDRegressor(max_iter=1, warm_start=True, tol=None, learning_rate='invscaling', eta0=0.01)
    lr_y2 = SGDRegressor(max_iter=1, warm_start=True, tol=None, learning_rate='invscaling', eta0=0.01)
    
    mae_0 = np.mean(np.abs(np.zeros_like(Y_val) - Y_val))
    results.append({"Model": "LR", "Step": 0, "MAE": mae_0})
    
    for ep in range(1, 201):
        lr_y1.fit(X_train, Y_train[:, 0])
        lr_y2.fit(X_train, Y_train[:, 1])
        
        p1 = lr_y1.predict(X_val)
        p2 = lr_y2.predict(X_val)
        mae = (np.mean(np.abs(p1 - Y_val[:, 0])) + np.mean(np.abs(p2 - Y_val[:, 1]))) / 2.0
        results.append({"Model": "LR", "Step": ep, "MAE": mae})
        if ep % 20 == 0:
            print(f"[LR] Epoch {ep}/200 MAE: {mae:.4f}")
            
    # --- 2. RF using warm_start ---
    print("\n--- Training RF (warm_start) ---")
    rf_y1 = RandomForestRegressor(n_estimators=1, warm_start=True, n_jobs=-1, random_state=42)
    rf_y2 = RandomForestRegressor(n_estimators=1, warm_start=True, n_jobs=-1, random_state=42)
    
    results.append({"Model": "RF", "Step": 0, "MAE": mae_0})
    
    n_trees_target = 100
    for i in range(1, n_trees_target + 1):
        rf_y1.n_estimators = i
        rf_y2.n_estimators = i
        
        rf_y1.fit(X_train, Y_train[:, 0])
        rf_y2.fit(X_train, Y_train[:, 1])
        
        # In RF, typically we step by 1 tree, but to map to 200 epochs we could just save each tree as 2 epochs?
        # Let's map it: 100 trees over 200 epochs = 1 tree every 2 epochs, or just record it as step i*2
        p1 = rf_y1.predict(X_val)
        p2 = rf_y2.predict(X_val)
        mae = (np.mean(np.abs(p1 - Y_val[:, 0])) + np.mean(np.abs(p2 - Y_val[:, 1]))) / 2.0
        
        # Step matching up to 200
        step_mapped = int((i / n_trees_target) * 200)
        results.append({"Model": "RF", "Step": step_mapped, "MAE": mae})
        if i % 10 == 0:
            print(f"[RF] Trees {i}/{n_trees_target} (Mapped Epoch {step_mapped}) MAE: {mae:.4f}")
            
    os.makedirs("/home/imnyj/papers/paper1/data/G1", exist_ok=True)
    df = pd.DataFrame(results)
    save_path = "/home/imnyj/papers/paper1/data/G1/LR_RF_learning_curves.csv"
    df.to_csv(save_path, index=False)
    print(f"\nSaved CSV to {save_path}")

if __name__ == "__main__":
    main()
