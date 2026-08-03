import torch
import torch.nn as nn
import torch.optim as optim
import time
from torch.utils.data import TensorDataset, DataLoader
from models import H_ST_MBAN

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("Using device:", DEVICE)

model = H_ST_MBAN().to(DEVICE)
optimizer = optim.AdamW(model.parameters(), lr=0.001)
criterion = nn.L1Loss()

# Create dummy datasets directly on GPU
train_ds = TensorDataset(
    torch.randn(312968, 7).to(DEVICE),
    torch.randn(312968, 4).to(DEVICE),
    torch.randn(312968, 17).to(DEVICE),
    torch.randn(312968, 2).to(DEVICE),
    torch.randn(312968, 2).to(DEVICE)
)
val_ds = TensorDataset(
    torch.randn(78242, 7).to(DEVICE),
    torch.randn(78242, 4).to(DEVICE),
    torch.randn(78242, 17).to(DEVICE),
    torch.randn(78242, 2).to(DEVICE),
    torch.randn(78242, 2).to(DEVICE)
)

train_loader = DataLoader(train_ds, batch_size=2048, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=2048, shuffle=False)

print("Starting GPU dataset loop benchmark...")
for ep in range(1, 6):
    t0 = time.time()
    
    # Train
    model.train()
    for batch in train_loader:
        x_k, x_t, x_s, xp, y = batch
        optimizer.zero_grad()
        preds = model(x_k, x_t, x_s)
        loss = criterion(preds, y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
    # Val
    model.eval()
    val_mae = 0.0
    count = 0
    with torch.no_grad():
        for batch in val_loader:
            x_k, x_t, x_s, xp, y = batch
            preds = model(x_k, x_t, x_s)
            val_mae += torch.sum(torch.abs(preds - y)).item()
            count += y.numel()
            
    t1 = time.time()
    print(f"Epoch {ep} took {t1 - t0:.4f} seconds (Val MAE: {val_mae/count:.4f})")
