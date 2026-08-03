"""
ST-CVAE Baseline Training Script
Usage:
    python train.py --data_dir /home/nyj/ST-MBAN/시뮬/데이터셋 \
                    --hidden 128 --latent 32 --epochs 100 \
                    --lr 1e-3 --batch 256 --device cpu
"""
import argparse
import csv
import os

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from model import STCVAE
from dataset import SumoDataset

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def get_beta(epoch: int, warmup_epochs: int = 50) -> float:
    """KL annealing: 0 → 1 over first warmup_epochs epochs."""
    return min(epoch / warmup_epochs, 1.0)


def evaluate(model, loader, device, beta):
    model.eval()
    total, recon_sum, kl_sum = 0, 0.0, 0.0
    with torch.no_grad():
        for X, Y in loader:
            X, Y = X.to(device), Y.to(device)
            loss, recon, kl = model.compute_loss(X, Y, beta=beta)
            n = X.size(0)
            total += n
            recon_sum += recon.item() * n
            kl_sum    += kl.item()    * n
    return recon_sum / total, kl_sum / total


def main():
    parser = argparse.ArgumentParser(description="Train ST-CVAE baseline")
    parser.add_argument("--data_dir",  type=str, default="/home/nyj/ST-MBAN/시뮬/데이터셋")
    parser.add_argument("--hidden",    type=int, default=128)
    parser.add_argument("--latent",    type=int, default=32)
    parser.add_argument("--epochs",    type=int, default=100)
    parser.add_argument("--lr",        type=float, default=1e-3)
    parser.add_argument("--batch",     type=int, default=256)
    parser.add_argument("--warmup",    type=int, default=50,
                        help="KL annealing warmup epochs")
    parser.add_argument("--device",    type=str, default="cpu")
    parser.add_argument("--seed",      type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device(args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    scaler_dir = os.path.join(RESULTS_DIR, "scalers")

    # ── Dataset ──────────────────────────────────────────────────
    print(f"[Data] Loading from {args.data_dir}")
    train_ds = SumoDataset(args.data_dir, split='train', seed=args.seed, scaler_dir=scaler_dir)
    val_ds   = SumoDataset(args.data_dir, split='val',   seed=args.seed, scaler_dir=scaler_dir)
    test_ds  = SumoDataset(args.data_dir, split='test',  seed=args.seed, scaler_dir=scaler_dir)

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch, shuffle=False, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=args.batch, shuffle=False, num_workers=0)

    input_dim  = train_ds.input_dim
    target_dim = train_ds.target_dim
    print(f"[Data] Train={len(train_ds)} | Val={len(val_ds)} | Test={len(test_ds)}")
    print(f"[Data] input_dim={input_dim}, target_dim={target_dim}")

    # ── Model ─────────────────────────────────────────────────────
    model = STCVAE(
        input_dim=input_dim,
        target_dim=target_dim,
        hidden_dim=args.hidden,
        latent_dim=args.latent,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=10, verbose=True
    )

    # ── Training Loop ─────────────────────────────────────────────
    log_path = os.path.join(RESULTS_DIR, "training_log.csv")
    best_val_recon = float('inf')
    best_model_path = os.path.join(RESULTS_DIR, "st_cvae_best.pt")

    with open(log_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['epoch', 'beta', 'train_recon', 'train_kl', 'val_recon', 'val_kl'])

    print(f"\n[Train] Starting {args.epochs} epochs on {device}")
    for epoch in range(1, args.epochs + 1):
        model.train()
        beta = get_beta(epoch, args.warmup)

        ep_recon, ep_kl, ep_n = 0.0, 0.0, 0
        for X, Y in train_loader:
            X, Y = X.to(device), Y.to(device)
            optimizer.zero_grad()
            loss, recon, kl = model.compute_loss(X, Y, beta=beta)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            n = X.size(0)
            ep_recon += recon.item() * n
            ep_kl    += kl.item()    * n
            ep_n     += n

        train_recon = ep_recon / ep_n
        train_kl    = ep_kl    / ep_n

        val_recon, val_kl = evaluate(model, val_loader, device, beta)
        scheduler.step(val_recon)

        # Best model save
        if val_recon < best_val_recon:
            best_val_recon = val_recon
            torch.save({
                'epoch': epoch,
                'model_state': model.state_dict(),
                'input_dim': input_dim,
                'target_dim': target_dim,
                'hidden_dim': args.hidden,
                'latent_dim': args.latent,
                'val_recon': val_recon,
            }, best_model_path)

        # Log
        with open(log_path, 'a', newline='') as f:
            csv.writer(f).writerow([epoch, f"{beta:.3f}", f"{train_recon:.4f}",
                                     f"{train_kl:.4f}", f"{val_recon:.4f}", f"{val_kl:.4f}"])

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:4d}/{args.epochs} | beta={beta:.2f} | "
                  f"train_recon={train_recon:.4f} kl={train_kl:.4f} | "
                  f"val_recon={val_recon:.4f} kl={val_kl:.4f}")

    # ── Test Evaluation ───────────────────────────────────────────
    ckpt = torch.load(best_model_path, map_location=device)
    model.load_state_dict(ckpt['model_state'])
    test_recon, test_kl = evaluate(model, test_loader, device, beta=1.0)
    print(f"\n[Test] Best epoch={ckpt['epoch']} | test_recon={test_recon:.4f} | test_kl={test_kl:.4f}")
    print(f"[Done] Model saved: {best_model_path}")
    print(f"[Done] Log saved:   {log_path}")


if __name__ == "__main__":
    main()
