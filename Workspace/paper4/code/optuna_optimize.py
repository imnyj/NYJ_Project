#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import pickle
import optuna
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

FEATURE_COLS = ["cbr_global", "n_neighbors", "v_norm", "dt_since_last_cam", "cbr_smoothed"]
LABEL_COL = "action_idx"
DATASET_PATH = "/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv"

# Load data
df = pd.read_csv(DATASET_PATH)
X = df[FEATURE_COLS].values.astype(np.float32)
y = df[LABEL_COL].values.astype(np.int64)

n_classes = int(y.max()) + 1
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
X_train_t = torch.tensor(X_train)
y_train_t = torch.tensor(y_train)
X_test_t = torch.tensor(X_test)
y_test_t = torch.tensor(y_test)

class TinyMLP(nn.Module):
    def __init__(self, in_dim=5, hidden_dim=8, n_classes=16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_classes),
        )
    def forward(self, x):
        return self.net(x)

def objective_tinymlp(trial):
    hidden_dim = trial.suggest_categorical("hidden_dim", [8, 16, 32])
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])
    
    model = TinyMLP(5, hidden_dim, n_classes)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    
    dataset = TensorDataset(X_train_t, y_train_t)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Train
    model.train()
    for epoch in range(50):  # Reduced max_epoch for speed in optuna
        for bx, by in loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
            
    # Eval
    model.eval()
    with torch.no_grad():
        out = model(X_test_t)
        preds = out.argmax(dim=1)
        acc = (preds == y_test_t).float().mean().item()
    return acc

def objective_stdmlp(trial):
    hidden_size = trial.suggest_categorical("hidden_size", [32, 64, 128])
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    
    mlp = MLPClassifier(hidden_layer_sizes=(hidden_size, hidden_size, hidden_size), 
                        learning_rate_init=lr, max_iter=200, random_state=42)
    mlp.fit(X_train, y_train)
    return mlp.score(X_test, y_test)

def objective_dectree(trial):
    max_depth = trial.suggest_int("max_depth", 5, 20)
    min_samples_split = trial.suggest_int("min_samples_split", 2, 20)
    
    dt = DecisionTreeClassifier(max_depth=max_depth, min_samples_split=min_samples_split, random_state=42)
    dt.fit(X_train, y_train)
    return dt.score(X_test, y_test)

if __name__ == "__main__":
    print("Optimizing TinyMLP...")
    study_tiny = optuna.create_study(direction="maximize")
    study_tiny.optimize(objective_tinymlp, n_trials=10)
    print("Best TinyMLP params:", study_tiny.best_params)
    
    print("Optimizing StdMLP...")
    study_std = optuna.create_study(direction="maximize")
    study_std.optimize(objective_stdmlp, n_trials=10)
    print("Best StdMLP params:", study_std.best_params)
    
    print("Optimizing DecTree...")
    study_dt = optuna.create_study(direction="maximize")
    study_dt.optimize(objective_dectree, n_trials=10)
    print("Best DecTree params:", study_dt.best_params)
    
    # Retrain with best and save
    # 1. TinyMLP
    p = study_tiny.best_params
    best_tiny = TinyMLP(5, p["hidden_dim"], n_classes)
    optimizer = optim.Adam(best_tiny.parameters(), lr=p["lr"])
    criterion = nn.CrossEntropyLoss()
    dataset = TensorDataset(X_train_t, y_train_t)
    loader = DataLoader(dataset, batch_size=p["batch_size"], shuffle=True)
    
    # Increase epoch for final train
    for epoch in range(150):
        for bx, by in loader:
            optimizer.zero_grad()
            out = best_tiny(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
            
    # Extract weights for the hook
    weights = {}
    idx = 1
    for layer in best_tiny.net:
        if isinstance(layer, nn.Linear):
            weights[f"W{idx}"] = layer.weight.detach().numpy()
            weights[f"b{idx}"] = layer.bias.detach().numpy()
            idx += 1
            
    # Hardcode action grids as defined
    t_grid = [0.1, 0.2, 0.5, 1.0]
    p_tx_grid = [0.0, 10.0, 20.0, 30.0]
    if n_classes == 9:
        t_grid = [0.1, 0.5, 1.0]
        p_tx_grid = [-10.0, 0.0, 20.0]
        
    model_dict = {
        "weights": weights,
        "t_grid": t_grid,
        "p_tx_grid": p_tx_grid
    }
    with open("tinymlp_model.pkl", "wb") as f:
        pickle.dump(model_dict, f)
        
    # 2. StdMLP
    p = study_std.best_params
    mlp = MLPClassifier(hidden_layer_sizes=(p["hidden_size"], p["hidden_size"], p["hidden_size"]), 
                        learning_rate_init=p["lr"], max_iter=300, random_state=42)
    mlp.fit(X_train, y_train)
    with open("stdmlp_model.pkl", "wb") as f:
        pickle.dump(mlp, f)
        
    # 3. DecTree
    p = study_dt.best_params
    dt = DecisionTreeClassifier(max_depth=p["max_depth"], min_samples_split=p["min_samples_split"], random_state=42)
    dt.fit(X_train, y_train)
    with open("dectree_model.pkl", "wb") as f:
        pickle.dump(dt, f)
        
    print("All best models trained and saved.")
