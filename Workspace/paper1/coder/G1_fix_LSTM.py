import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from dataset import get_dataloaders
from models import Baseline_LSTM
from G1_learning import DATA_DIRS, DEVICE

def train_lstm():
    print("Loading datasets for LSTM smoothing...")
    train_loader, val_loader, scaler = get_dataloaders(DATA_DIRS, batch_size=2048)
    
    model = Baseline_LSTM(in_dim=28, hidden_dim=64, num_layers=2, out_dim=2).to(DEVICE)
    
    optimizer = optim.Adam(model.parameters(), lr=0.002)
    # Cosine Annealing Scheduler to smoothly lower learning rate and avoid plateaus
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=200, eta_min=1e-5)
    criterion = nn.L1Loss()
    
    results = []
    
    # Evaluate untrained (Epoch 0)
    model.eval()
    val_loss = 0.0
    with torch.no_grad():
        for x_k, x_t, x_s, y in val_loader:
            x_k, x_t, x_s, y = x_k.to(DEVICE), x_t.to(DEVICE), x_s.to(DEVICE), y.to(DEVICE)
            preds = model(x_k, x_t, x_s)
            val_loss += criterion(preds, y).item() * y.size(0)
    val_mae = val_loss / len(val_loader.dataset)
    results.append({"Model": "LSTM", "Step": 0, "MAE": val_mae})
    print(f"[LSTM] Epoch 0/200 Val MAE: {val_mae:.4f}")
    
    # Train
    for ep in range(1, 201):
        model.train()
        for x_k, x_t, x_s, y in train_loader:
            x_k, x_t, x_s, y = x_k.to(DEVICE), x_t.to(DEVICE), x_s.to(DEVICE), y.to(DEVICE)
            optimizer.zero_grad()
            preds = model(x_k, x_t, x_s)
            loss = criterion(preds, y)
            loss.backward()
            
            # Gradient Clipping to prevent unstable jumps
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            
        scheduler.step()
        
        # Eval
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_k, x_t, x_s, y in val_loader:
                x_k, x_t, x_s, y = x_k.to(DEVICE), x_t.to(DEVICE), x_s.to(DEVICE), y.to(DEVICE)
                preds = model(x_k, x_t, x_s)
                val_loss += criterion(preds, y).item() * y.size(0)
        val_mae = val_loss / len(val_loader.dataset)
        results.append({"Model": "LSTM", "Step": ep, "MAE": val_mae})
        
        if ep % 20 == 0:
            print(f"[LSTM] Epoch {ep}/200 Val MAE: {val_mae:.4f} (LR: {scheduler.get_last_lr()[0]:.6f})")

    df = pd.DataFrame(results)
    df.to_csv("/home/imnyj/papers/paper1/data/G1/LSTM_learning_curves.csv", index=False)
    print("Saved smooth LSTM learning curves.")

if __name__ == "__main__":
    train_lstm()
