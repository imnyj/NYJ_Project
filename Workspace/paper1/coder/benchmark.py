import torch
import torch.nn as nn
import torch.optim as optim
import time
from models import H_ST_MBAN

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("Using device:", DEVICE)

model = H_ST_MBAN().to(DEVICE)
optimizer = optim.AdamW(model.parameters(), lr=0.001)
criterion = nn.L1Loss()

# Dummy data of batch size 2048
x_k = torch.randn(2048, 7).to(DEVICE)
x_t = torch.randn(2048, 4).to(DEVICE)
x_s = torch.randn(2048, 17).to(DEVICE)
xp = torch.randn(2048, 2).to(DEVICE)
y = torch.randn(2048, 2).to(DEVICE)

# Warmup
for _ in range(5):
    preds = model(x_k, x_t, x_s, xp)
    loss = criterion(preds, y)
    loss.backward()
    optimizer.step()
    optimizer.zero_grad()

torch.cuda.synchronize()

t0 = time.time()
for _ in range(100):
    optimizer.zero_grad()
    preds = model(x_k, x_t, x_s, xp)
    loss = criterion(preds, y)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()

torch.cuda.synchronize()
t1 = time.time()
print(f"Time for 100 training steps: {t1 - t0:.4f} seconds")
print(f"Time per step: {(t1 - t0)/100:.6f} seconds")
