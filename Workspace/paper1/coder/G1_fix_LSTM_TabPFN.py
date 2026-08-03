import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
import os
from dataset import get_dataloaders
from G1_learning import DATA_DIRS, get_dl_model, get_ml_model
import warnings
warnings.filterwarnings("ignore")

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
    
    mae_0 = np.mean(np.abs(np.zeros_like(Y_val) - Y_val))
    results = []
    
    # Skip TabPFN as it's already done
    
    # 2. LSTM
    print("\n--- Training LSTM ---")
    model_name = "LSTM"
    in_dim = X_train.shape[1]
    model = get_dl_model(model_name, {}, in_dim=in_dim).cuda()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.L1Loss()
    
    def evaluate_model(m, loader):
        m.eval()
        val_mae = 0.0
        count = 0
        with torch.no_grad():
            for x_k, x_t, x_s, y in loader:
                x_k, x_t, x_s, y = x_k.cuda(), x_t.cuda(), x_s.cuda(), y.cuda()
                preds = m(x_k, x_t, x_s)
                val_mae += torch.sum(torch.abs(preds - y)).item()
                count += y.numel()
        return val_mae / count

    mae_dl_0 = evaluate_model(model, val_loader)
    results.append({"Model": model_name, "Step": 0, "MAE": mae_dl_0})
    print(f"[LSTM] Epoch 0 (Untrained) MAE: {mae_dl_0:.4f}")
    
    for ep in range(1, 201):
        model.train()
        for x_k, x_t, x_s, y in train_loader:
            x_k, x_t, x_s, y = x_k.cuda(), x_t.cuda(), x_s.cuda(), y.cuda()
            optimizer.zero_grad()
            preds = model(x_k, x_t, x_s)
            loss = criterion(preds, y)
            loss.backward()
            optimizer.step()
            
        mae_val = evaluate_model(model, val_loader)
        results.append({"Model": model_name, "Step": ep, "MAE": mae_val})
        if ep % 10 == 0:
            print(f"[LSTM] Epoch {ep}/200 MAE: {mae_val:.4f}")
            
    df_lstm = pd.DataFrame([r for r in results if r["Model"] == "LSTM"])
    df_lstm.to_csv("/home/imnyj/papers/paper1/data/G1/LSTM_learning_curves.csv", index=False)
    print("\nSaved LSTM and TabPFN learning curves to data/G1/")

if __name__ == "__main__":
    main()
