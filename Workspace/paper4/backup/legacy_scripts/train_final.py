#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import pickle
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

FEATURE_COLS = ["cbr_global", "n_neighbors", "v_norm", "dt_since_last_cam", "cbr_smoothed"]
LABEL_COL = "action_idx"
DATASET_PATH = "/home/imnyj/Workspace/paper4/coder/data/oracle_dataset.csv"

# Load data
df = pd.read_csv(DATASET_PATH)
X = df[FEATURE_COLS].values.astype(np.float32)
y = df[LABEL_COL].values.astype(np.int64)

n_classes = int(y.max()) + 1
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

X_train_t = torch.tensor(X_train)
y_train_t = torch.tensor(y_train)
X_test_t = torch.tensor(X_test)
y_test_t = torch.tensor(y_test)

class TinyMLP(nn.Module):
    def __init__(self, in_dim=5, hidden_dim=32, n_classes=16):
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

model = TinyMLP(5, 32, n_classes)
optimizer = optim.Adam(model.parameters(), lr=0.000207)
criterion = nn.CrossEntropyLoss()
dataset = TensorDataset(X_train_t, y_train_t)
loader = DataLoader(dataset, batch_size=256, shuffle=True)

log_data = []

print("Training TinyMLP...")
for epoch in range(150):
    model.train()
    total_loss = 0
    correct = 0
    for bx, by in loader:
        optimizer.zero_grad()
        out = model(bx)
        loss = criterion(out, by)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * bx.size(0)
        correct += (out.argmax(dim=1) == by).sum().item()
        
    train_loss = total_loss / len(X_train_t)
    train_acc = correct / len(X_train_t)
    
    model.eval()
    with torch.no_grad():
        out = model(X_test_t)
        val_loss = criterion(out, y_test_t).item()
        val_acc = (out.argmax(dim=1) == y_test_t).float().mean().item()
        
    log_data.append({"epoch": epoch+1, "train_loss": train_loss, "train_acc": train_acc, "val_loss": val_loss, "val_acc": val_acc})
    if epoch % 10 == 0:
        print(f"Epoch {epoch}: Train Loss {train_loss:.4f}, Val Acc {val_acc:.4f}")

df_log = pd.DataFrame(log_data)
df_log.to_csv("train_log.csv", index=False)
print("Saved train_log.csv")

weights = {}
idx = 1
for layer in model.net:
    if isinstance(layer, nn.Linear):
        weights[f"W{idx}"] = layer.weight.detach().numpy()
        weights[f"b{idx}"] = layer.bias.detach().numpy()
        idx += 1

from etsi_cam_layer import PTX_GRID_DBM, T_GRID_S
t_grid = list(T_GRID_S)
p_tx_grid = list(PTX_GRID_DBM)
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
print("Saved tinymlp_model.pkl")
