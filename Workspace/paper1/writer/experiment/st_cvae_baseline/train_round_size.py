import os
import torch
import pandas as pd
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader, Subset
from dataset import SumoDataset
from model_stmban import STMBAN
from train_stmban import evaluate_metrics

DATA_DIR = "/home/imnyj/SumoNetSim1.1.5/data"

def train_on_subset(train_dataset, val_dataset, subset_size, device):
    # subset train_dataset
    indices = torch.randperm(len(train_dataset))[:subset_size]
    subset = Subset(train_dataset, indices)
    train_loader = DataLoader(subset, batch_size=128, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)
    
    model = STMBAN(input_dim=30, d_branch=64, n_heads=4).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=2e-3)
    criterion = torch.nn.HuberLoss(delta=1.0, reduction='mean')
    
    best_mae = float('inf')
    epochs = 40
    for epoch in range(epochs):
        model.train()
        for X, Y in train_loader:
            X, Y = X.to(device), Y.to(device)
            optimizer.zero_grad()
            y_hat = model(X)
            loss = criterion(y_hat, Y)
            loss.backward()
            optimizer.step()
        
        # evaluate
        metrics = evaluate_metrics(model, val_loader, device)
        mae = metrics[0]
        if mae < best_mae:
            best_mae = mae
    return best_mae

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    scaler_dir = "scalers_round"
    train_dataset = SumoDataset(DATA_DIR, split='train', seed=42, scaler_dir=scaler_dir)
    val_dataset = SumoDataset(DATA_DIR, split='val', seed=42, scaler_dir=scaler_dir)
    
    sizes = [1000, 2000, 3000, 4000, 5000]
    maes = []
    
    for size in sizes:
        print(f"Training on round size: {size}")
        mae = train_on_subset(train_dataset, val_dataset, size, device)
        maes.append(mae)
        print(f"Size: {size}, Validation MAE: {mae:.4f}")
        
    df = pd.DataFrame({"Round_Size": sizes, "MAE": maes})
    
    csv_path = "/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/round_size_results.csv"
    df.to_csv(csv_path, index=False)
    
    plt.figure(figsize=(8,6))
    plt.plot(sizes, maes, marker='o', linewidth=2, markersize=8, color='#00a65a')
    plt.title("Effect of Data Size per Round on ST-MBAN MAE", fontsize=14, pad=15)
    plt.xlabel("Number of Samples per Round", fontsize=12)
    plt.ylabel("Validation MAE (s)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    for i, txt in enumerate(maes):
        plt.annotate(f"{txt:.2f}", (sizes[i], maes[i]), textcoords="offset points", xytext=(0,10), ha='center')

    plot_path = "/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/plot_round_size_mae.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Results saved to {csv_path} and {plot_path}")

if __name__ == "__main__":
    main()
