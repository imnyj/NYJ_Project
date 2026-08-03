import os
os.environ["CUDA_VISIBLE_DEVICES"] = "1"
import json
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import pickle
from torch.utils.data import TensorDataset, DataLoader, Subset

# --- ML & Baseline Imports ---
from sklearn.linear_model import SGDRegressor
from xgboost import XGBRegressor
from catboost import CatBoostRegressor
from ngboost import NGBRegressor
from sklearn.ensemble import RandomForestRegressor
try:
    from tabpfn import TabPFNRegressor
    HAS_TABPFN = True
except ImportError:
    HAS_TABPFN = False

# --- Custom Architecture Imports ---
from dataset import get_dataloaders
from models import (
    Baseline_MLP, Baseline_LSTM, Baseline_GRU, 
    Baseline_FTT, Baseline_TabR, Baseline_ResNet, H_ST_MBAN
)

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
DATA_DIRS = [
    "/home/imnyj/SumoNetSim1.1.6/data",
    "/home/imnyj/papers/paper1/paper/data(Desk01)",
    "/home/imnyj/papers/paper1/paper/data(Desk02)"
]
OUT_CSV = "/home/imnyj/papers/paper1/data/G1_learning_curves.csv"
MODEL_SAVE_DIR = "/home/imnyj/papers/paper1/code/saved_models"
EPOCHS = 200

os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

# ---------------------------------------------------------
# Part 1: Helper Functions
# ---------------------------------------------------------
def load_optuna_params():
    params = {}
    base_dir = "/home/imnyj/papers/paper1/code"
    try:
        with open(os.path.join(base_dir, "best_hyperparameters_baselines.json"), "r") as f:
            params.update(json.load(f))
        with open(os.path.join(base_dir, "best_hyperparameters_ml.json"), "r") as f:
            params.update(json.load(f))
    except Exception as e:
        print(f"Warning: Could not load some param files: {e}")
    return params

def save_ml_model(model, name):
    path = os.path.join(MODEL_SAVE_DIR, f"{name}_best.pkl")
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"Saved {name} to {path}")

def save_dl_model(model, name):
    path = os.path.join(MODEL_SAVE_DIR, f"{name}_best.pth")
    torch.save(model.state_dict(), path)
    print(f"Saved {name} to {path}")

# ---------------------------------------------------------
# Part 2: Model Constructors
# ---------------------------------------------------------
def get_ml_model(name, params):
    if name == "LR":
        return SGDRegressor(max_iter=1, warm_start=True, learning_rate='optimal', alpha=1e-4)
    elif name == "XGBoost":
        p = params.get("XGB", {"n_estimators": 200, "learning_rate": 0.05, "max_depth": 6})
        if 'max_depth' in p: p['max_depth'] = int(p['max_depth'])
        return XGBRegressor(**p, eval_metric="mae")
    elif name == "CatBoost":
        p = params.get("CatBoost", {"iterations": 200, "learning_rate": 0.05, "depth": 6})
        if 'depth' in p: p['depth'] = int(p['depth'])
        if 'iterations' in p: p['iterations'] = int(p['iterations'])
        return CatBoostRegressor(**p, eval_metric="MAE", verbose=False)
    elif name == "RF":
        p = params.get("RF", {"n_estimators": 200, "max_depth": 10})
        if 'n_estimators' in p: p['n_estimators'] = int(p['n_estimators'])
        if 'max_depth' in p: p['max_depth'] = int(p['max_depth'])
        if 'min_samples_split' in p: p['min_samples_split'] = int(p['min_samples_split'])
        if 'min_samples_leaf' in p: p['min_samples_leaf'] = int(p['min_samples_leaf'])
        return RandomForestRegressor(**p, n_jobs=-1, warm_start=True)
    elif name == "NGBoost":
        return NGBRegressor(n_estimators=200, learning_rate=0.05, verbose=False)
    elif name == "TabPFN":
        return TabPFNRegressor(device='cuda' if torch.cuda.is_available() else 'cpu')
    return None

def get_dl_model(name, params, in_dim=28):
    p = params.get(name, {})
    if name == "H-ST-MBAN":
        return H_ST_MBAN(
            d_model=p.get('d_model', 128),
            num_layers=p.get('num_layers', 4)
        ).to(DEVICE)
    elif name == "MLP":
        return Baseline_MLP(in_dim, hidden_dim=p.get('hidden_dim', 128), num_layers=p.get('num_layers', 3), dropout=p.get('dropout', 0.1)).to(DEVICE)
    elif name == "LSTM":
        return Baseline_LSTM(in_dim, hidden_dim=p.get('hidden_dim', 64), num_layers=p.get('num_layers', 2), dropout=p.get('dropout', 0.1)).to(DEVICE)
    elif name == "GRU":
        return Baseline_GRU(in_dim, hidden_dim=p.get('hidden_dim', 64), num_layers=p.get('num_layers', 2), dropout=p.get('dropout', 0.1)).to(DEVICE)
    elif name == "FTT":
        return Baseline_FTT(in_dim, d_model=p.get('d_model', 64), num_layers=p.get('num_layers', 2)).to(DEVICE)
    elif name == "TabR":
        return Baseline_TabR(in_dim, hidden_dim=p.get('hidden_dim', 128), num_layers=p.get('num_layers', 2)).to(DEVICE)
    elif name == "ResNet":
        return Baseline_ResNet(in_dim, hidden_dim=p.get('hidden_dim', 128), num_layers=p.get('num_layers', 3), dropout=p.get('dropout', 0.1)).to(DEVICE)
    return None

# ---------------------------------------------------------
# Part 3: Main Training Pipeline
# ---------------------------------------------------------
def main():
    params = load_optuna_params()
    print("Loading datasets...")
    train_loader, val_loader, scaler = get_dataloaders(DATA_DIRS, batch_size=2048)
    
    train_dataset = train_loader.dataset
    
    # ---------------------------------------------------------
    # Create Full Sequential Tensors for OOF
    # ---------------------------------------------------------
    train_loader_seq = DataLoader(train_dataset, batch_size=2048, shuffle=False)
    all_xk, all_xt, all_xs, all_y = [], [], [], []
    for x_k, x_t, x_s, y in train_loader_seq:
        all_xk.append(x_k); all_xt.append(x_t); all_xs.append(x_s); all_y.append(y)
    all_xk = torch.cat(all_xk)
    all_xt = torch.cat(all_xt)
    all_xs = torch.cat(all_xs)
    all_y = torch.cat(all_y)
    
    X_train_full = torch.cat([all_xk, all_xt, all_xs], dim=1).numpy()
    Y_train_full = all_y.numpy()
    
    # ---------------------------------------------------------
    # 1) XGBoost Progressive OOF Precomputing (Plan A)
    # ---------------------------------------------------------
    print("\n[0] Pre-computing Progressive Out-Of-Fold XGBoost Priors for H-ST-MBAN...")
    from sklearn.model_selection import KFold
    from xgboost import XGBRegressor
    
    X_val, Y_val = [], []
    for x_k, x_t, x_s, y in val_loader:
        X_val.append(torch.cat([x_k, x_t, x_s], dim=1).numpy())
        Y_val.append(y.numpy())
    X_val = np.vstack(X_val)
    Y_val = np.vstack(Y_val)
    
    xgb_oof_by_epoch = np.zeros((EPOCHS + 1, len(Y_train_full), 2))
    xgb_val_by_epoch = np.zeros((EPOCHS + 1, len(Y_val), 2))
    
    xgb_oof_by_epoch[0] = 0.0
    xgb_val_by_epoch[0] = 0.0
    
    xgb_params = params.get("XGB", {"n_estimators": 200, "learning_rate": 0.05, "max_depth": 6})
    if 'max_depth' in xgb_params: xgb_params['max_depth'] = int(xgb_params['max_depth'])
    xgb_params["n_estimators"] = EPOCHS
    
    kf = KFold(n_splits=2, shuffle=True, random_state=42)
    
    print("Training fold XGBoost models once...")
    fold_models = []
    for train_idx, val_idx in kf.split(X_train_full):
        fold_y1 = XGBRegressor(**xgb_params, eval_metric="mae", n_jobs=-1)
        fold_y2 = XGBRegressor(**xgb_params, eval_metric="mae", n_jobs=-1)
        fold_y1.fit(X_train_full[train_idx], Y_train_full[train_idx, 0])
        fold_y2.fit(X_train_full[train_idx], Y_train_full[train_idx, 1])
        fold_models.append((train_idx, val_idx, fold_y1, fold_y2))
        
    print("Training base XGBoost models once...")
    base_y1 = XGBRegressor(**xgb_params, eval_metric="mae", n_jobs=-1)
    base_y2 = XGBRegressor(**xgb_params, eval_metric="mae", n_jobs=-1)
    base_y1.fit(X_train_full, Y_train_full[:, 0])
    base_y2.fit(X_train_full, Y_train_full[:, 1])
    
    print("Generating progressive predictions across epochs using iteration_range...")
    for ep in range(1, EPOCHS + 1):
        for train_idx, val_idx, fold_y1, fold_y2 in fold_models:
            p1 = fold_y1.predict(X_train_full[val_idx], iteration_range=(0, ep))
            p2 = fold_y2.predict(X_train_full[val_idx], iteration_range=(0, ep))
            xgb_oof_by_epoch[ep, val_idx] = np.column_stack([p1, p2])
            
        p1_val = base_y1.predict(X_val, iteration_range=(0, ep))
        p2_val = base_y2.predict(X_val, iteration_range=(0, ep))
        xgb_val_by_epoch[ep] = np.column_stack([p1_val, p2_val])
        
        if ep % 20 == 0 or ep == 1:
            print(f"Precomputed XGBoost predictions for Epoch {ep}/{EPOCHS}")
            
    xgb_base_y1 = XGBRegressor(**xgb_params, eval_metric="mae", n_jobs=-1)
    xgb_base_y2 = XGBRegressor(**xgb_params, eval_metric="mae", n_jobs=-1)
    xgb_base_y1.fit(X_train_full, Y_train_full[:, 0])
    xgb_base_y2.fit(X_train_full, Y_train_full[:, 1])
    save_ml_model(xgb_base_y1, "XGB_Hybrid_Base_y1")
    save_ml_model(xgb_base_y2, "XGB_Hybrid_Base_y2")
    
    dl_train_loader = DataLoader(TensorDataset(all_xk, all_xt, all_xs, all_y), batch_size=2048, shuffle=True)
    
    all_val_xk, all_val_xt, all_val_xs, all_val_y = [], [], [], []
    for x_k, x_t, x_s, y in val_loader:
        all_val_xk.append(x_k); all_val_xt.append(x_t); all_val_xs.append(x_s); all_val_y.append(y)
    
    X_train, Y_train = X_train_full, Y_train_full
    
    params = load_optuna_params()
    results = []
    
    model_order = [
        "LR", "RF", "XGBoost", "CatBoost", "NGBoost", "TabPFN",
        "MLP", "ResNet", "LSTM", "GRU", "FTT", "TabR", "H-ST-MBAN"
    ]
    
    if os.path.exists("G1_learning_curves.csv"):
        print("Found existing G1_learning_curves.csv! Resuming...")
        try:
            existing_df = pd.read_csv("G1_learning_curves.csv")
            results = existing_df.to_dict('records')
            # If a model has entries with Step > 0, consider it trained.
            trained_models = set(existing_df[existing_df['Step'] > 0]['Model'].unique())
            model_order = [m for m in model_order if m not in trained_models]
            print(f"Skipping already trained models: {trained_models}")
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            
    for model_name in model_order:
        print(f"\n--- Training {model_name} ---")
        
        # === A. Machine Learning Models ===
        if model_name in ["LR", "RF", "XGBoost", "CatBoost", "NGBoost", "TabPFN"]:
            model = get_ml_model(model_name, params)
            if model is None:
                continue
                
            history = []
            
            # Untrained (Step 0) - Dynamically calculated
            mae_0 = np.mean(np.abs(np.zeros_like(Y_val) - Y_val))
            results.append({"Model": model_name, "Step": 0, "MAE": mae_0})
            
            if model_name == "LR":
                model_y2 = get_ml_model(model_name, params)
                for ep in range(1, 201):
                    # Data is already scaled by CCVNDataset, no double-scaling
                    model.fit(X_train, Y_train[:, 0])
                    model_y2.fit(X_train, Y_train[:, 1])
                    mae1 = np.mean(np.abs(model.predict(X_val) - Y_val[:, 0]))
                    mae2 = np.mean(np.abs(model_y2.predict(X_val) - Y_val[:, 1]))
                    history.append((mae1 + mae2) / 2.0)
                save_ml_model(model, "LR_y1")
                save_ml_model(model_y2, "LR_y2")
                
            elif model_name == "RF":
                model_y2 = get_ml_model(model_name, params)
                n_trees = model.n_estimators
                for i in range(1, n_trees + 1, max(1, n_trees // 20)):
                    model.n_estimators = i
                    model_y2.n_estimators = i
                    model.fit(X_train, Y_train[:, 0])
                    model_y2.fit(X_train, Y_train[:, 1])
                    mae1 = np.mean(np.abs(model.predict(X_val) - Y_val[:, 0]))
                    mae2 = np.mean(np.abs(model_y2.predict(X_val) - Y_val[:, 1]))
                    results.append({"Model": model_name, "Step": i, "MAE": (mae1 + mae2) / 2.0})
                save_ml_model(model, "RF_y1")
                save_ml_model(model_y2, "RF_y2")
                continue
                
            elif model_name == "CatBoost":
                model_y2 = get_ml_model(model_name, params)
                model.fit(X_train, Y_train[:, 0], eval_set=(X_val, Y_val[:, 0]), verbose=False)
                model_y2.fit(X_train, Y_train[:, 1], eval_set=(X_val, Y_val[:, 1]), verbose=False)
                evals1 = model.evals_result_
                evals2 = model_y2.evals_result_
                
                history1, history2 = [], []
                if 'validation' in evals1 and 'MAE' in evals1['validation']:
                    history1 = evals1['validation']['MAE']
                if 'validation' in evals2 and 'MAE' in evals2['validation']:
                    history2 = evals2['validation']['MAE']
                
                history = [(h1 + h2) / 2.0 for h1, h2 in zip(history1, history2)]
                
                save_ml_model(model, "CatBoost_y1")
                save_ml_model(model_y2, "CatBoost_y2")
                
            elif model_name == "XGBoost":
                model_y2 = get_ml_model(model_name, params)
                model.fit(X_train, Y_train[:, 0])
                model_y2.fit(X_train, Y_train[:, 1])
                n_trees = model.n_estimators
                for i in range(1, n_trees + 1, max(1, n_trees // 20)):
                    p1 = model.predict(X_val, iteration_range=(0, i))
                    p2 = model_y2.predict(X_val, iteration_range=(0, i))
                    mae1 = np.mean(np.abs(p1 - Y_val[:, 0]))
                    mae2 = np.mean(np.abs(p2 - Y_val[:, 1]))
                    results.append({"Model": model_name, "Step": i, "MAE": (mae1 + mae2) / 2.0})
                save_ml_model(model, f"{model_name}_y1")
                save_ml_model(model_y2, f"{model_name}_y2")
                continue
                
            elif model_name == "NGBoost":
                model_y2 = get_ml_model(model_name, params)
                model.fit(X_train, Y_train[:, 0])
                model_y2.fit(X_train, Y_train[:, 1])
                hist1 = [np.mean(np.abs(p - Y_val[:, 0])) for p in model.staged_predict(X_val)]
                hist2 = [np.mean(np.abs(p - Y_val[:, 1])) for p in model_y2.staged_predict(X_val)]
                history = [(h1 + h2) / 2.0 for h1, h2 in zip(hist1, hist2)]
                save_ml_model(model, f"{model_name}_y1")
                save_ml_model(model_y2, f"{model_name}_y2")
                
            elif model_name == "TabPFN":
                max_context = min(1000, len(X_train))
                steps = [10, 50, 100, 150, 200]
                model_y2 = get_ml_model(model_name, params)
                for ep in steps:
                    c_size = int(10 + (max_context - 10) * (ep / 200))
                    model.fit(X_train[:c_size], Y_train[:c_size, 0])
                    model_y2.fit(X_train[:c_size], Y_train[:c_size, 1])
                    mae1 = np.mean(np.abs(model.predict(X_val) - Y_val[:, 0]))
                    mae2 = np.mean(np.abs(model_y2.predict(X_val) - Y_val[:, 1]))
                    results.append({"Model": model_name, "Step": ep, "MAE": (mae1 + mae2) / 2.0})
                save_ml_model(model, "TabPFN_y1")
                save_ml_model(model_y2, "TabPFN_y2")
                continue
            
            for step_idx, mae in enumerate(history, 1):
                results.append({"Model": model_name, "Step": step_idx, "MAE": mae})

        # === B. Deep Learning Models ===
        else:
            in_dim = X_train.shape[1]
            model = get_dl_model(model_name, params, in_dim=in_dim)
            if model is None: continue
            
            lr = params.get(model_name, {}).get("lr", 1e-3)
            weight_decay = params.get(model_name, {}).get("weight_decay", 1e-4)
            optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
            criterion = nn.L1Loss()
            
            best_mae = float('inf')
            
            # --- Epoch 0 (Untrained state) ---
            model.eval()
            val_mae_0 = 0.0
            count_0 = 0
            with torch.no_grad():
                if model_name == "H-ST-MBAN":
                    xp_val_0 = torch.tensor(xgb_val_by_epoch[0], dtype=torch.float32)
                    temp_loader = DataLoader(TensorDataset(torch.cat(all_val_xk), torch.cat(all_val_xt), torch.cat(all_val_xs), xp_val_0, torch.cat(all_val_y)), batch_size=2048, shuffle=False)
                    for batch in temp_loader:
                        x_k, x_t, x_s, xp, y = [b.to(DEVICE) for b in batch]
                        preds = model(x_k, x_t, x_s, xp)
                        val_mae_0 += torch.sum(torch.abs(preds - y)).item()
                        count_0 += y.numel()
                else:
                    for batch in val_loader:
                        x_k, x_t, x_s, y = [b.to(DEVICE) for b in batch]
                        preds = model(x_k, x_t, x_s)
                        val_mae_0 += torch.sum(torch.abs(preds - y)).item()
                        count_0 += y.numel()
            mae_0 = val_mae_0 / count_0
            results.append({"Model": model_name, "Step": 0, "MAE": mae_0})
            print(f"[{model_name}] Epoch 0/{EPOCHS} (Untrained) MAE: {mae_0:.4f}")

            for ep in range(1, EPOCHS + 1):
                model.train()
                
                if model_name == "H-ST-MBAN":
                    xp_train_ep = torch.tensor(xgb_oof_by_epoch[ep], dtype=torch.float32)
                    current_train_loader = DataLoader(TensorDataset(all_xk, all_xt, all_xs, xp_train_ep, all_y), batch_size=2048, shuffle=True)
                else:
                    current_train_loader = dl_train_loader
                
                for batch in current_train_loader:
                    optimizer.zero_grad()
                    
                    if model_name == "H-ST-MBAN":
                        x_k, x_t, x_s, xp, y = [b.to(DEVICE) for b in batch]
                        preds = model(x_k, x_t, x_s, xp)
                    else:
                        x_k, x_t, x_s, y = [b.to(DEVICE) for b in batch]
                        preds = model(x_k, x_t, x_s)
                        
                    loss = criterion(preds, y)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                
                # Validation
                model.eval()
                val_mae = 0.0
                count = 0
                
                if model_name == "H-ST-MBAN":
                    xp_val_ep = torch.tensor(xgb_val_by_epoch[ep], dtype=torch.float32)
                    current_val_loader = DataLoader(TensorDataset(torch.cat(all_val_xk), torch.cat(all_val_xt), torch.cat(all_val_xs), xp_val_ep, torch.cat(all_val_y)), batch_size=2048, shuffle=False)
                else:
                    current_val_loader = val_loader
                    
                with torch.no_grad():
                    for batch in current_val_loader:
                        if model_name == "H-ST-MBAN":
                            x_k, x_t, x_s, xp, y = [b.to(DEVICE) for b in batch]
                            preds = model(x_k, x_t, x_s, xp)
                        else:
                            x_k, x_t, x_s, y = [b.to(DEVICE) for b in batch]
                            preds = model(x_k, x_t, x_s)
                        
                        val_mae += torch.sum(torch.abs(preds - y)).item()
                        count += y.numel()
                
                mae = val_mae / count
                results.append({"Model": model_name, "Step": ep, "MAE": mae})
                if ep % 20 == 0:
                    print(f"[{model_name}] Epoch {ep}/{EPOCHS} MAE: {mae:.4f}")
                    
                if mae < best_mae:
                    best_mae = mae
                    save_dl_model(model, model_name)

        # Save results continuously so we don't lose data on crash
        pd.DataFrame(results).to_csv("G1_learning_curves.csv", index=False)
        
    print("\n--- Training Complete ---")

    # ---------------------------------------------------------
    # Part 4: Save to CSV
    # ---------------------------------------------------------
    df = pd.DataFrame(results)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nAll models evaluated. Results saved to {OUT_CSV}")

if __name__ == "__main__":
    main()
