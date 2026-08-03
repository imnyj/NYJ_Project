"""
ST-MBAN Training Script
Usage:
    python train_stmban.py --data_dir /home/nyj/ST-MBAN/시뮬/데이터셋 \
                           --hidden 64 --n_heads 4 --epochs 100 \
                           --lr 1e-3 --batch 256 --device cpu

    # Optuna HPO 실행
    python train_stmban.py --data_dir /home/nyj/ST-MBAN/시뮬/데이터셋 \
                           --epochs 100 --device cpu \
                           --optuna --n_trials 50 --timeout 3600
"""
import argparse
import csv
import os

import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader

from model_stmban import STMBAN
from dataset import SumoDataset

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _OPTUNA_AVAILABLE = True
except ImportError:
    _OPTUNA_AVAILABLE = False

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_stmban")


# ── 평가 함수 ────────────────────────────────────────────────────────────────

def evaluate_loss(model: nn.Module, loader: DataLoader,
                  device: torch.device, delta: float) -> float:
    """Huber loss (평균)."""
    model.eval()
    total_loss, n_total = 0.0, 0
    with torch.no_grad():
        for X, Y in loader:
            X, Y = X.to(device), Y.to(device)
            y_hat = model(X)
            loss = nn.functional.huber_loss(y_hat, Y, delta=delta, reduction='sum')
            total_loss += loss.item()
            n_total    += X.size(0)
    return total_loss / n_total


def evaluate_metrics(model: nn.Module, loader: DataLoader,
                     device: torch.device):
    """MAE, RMSE 계산 (스케일된 공간 기준)."""
    model.eval()
    preds, targets = [], []
    with torch.no_grad():
        for X, Y in loader:
            X = X.to(device)
            y_hat = model(X).cpu()
            preds.append(y_hat)
            targets.append(Y)
    preds   = torch.cat(preds,   dim=0).numpy()
    targets = torch.cat(targets, dim=0).numpy()
    mae  = np.mean(np.abs(preds - targets))
    rmse = np.sqrt(np.mean((preds - targets) ** 2))
    return mae, rmse


# ── 학습 루프 ────────────────────────────────────────────────────────────────

def train_one_epoch(model: nn.Module, loader: DataLoader,
                    optimizer: torch.optim.Optimizer,
                    device: torch.device, delta: float) -> float:
    model.train()
    total_loss, n_total = 0.0, 0
    for X, Y in loader:
        X, Y = X.to(device), Y.to(device)
        optimizer.zero_grad()
        y_hat = model(X)
        loss = nn.functional.huber_loss(y_hat, Y, delta=delta)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        total_loss += loss.item() * X.size(0)
        n_total    += X.size(0)
    return total_loss / n_total


def run_training(model: nn.Module, train_loader: DataLoader,
                 val_loader: DataLoader, optimizer, scheduler,
                 epochs: int, device: torch.device, delta: float,
                 patience: int = 15,
                 log_path: str = None, best_model_path: str = None,
                 verbose: bool = True):
    """
    공통 학습 루프.
    Returns: best_val_loss, best_epoch, best_state_dict
    """
    best_val_loss = float('inf')
    best_epoch    = 0
    best_state    = None
    no_improve    = 0

    if log_path:
        with open(log_path, 'w', newline='') as f:
            csv.writer(f).writerow(['epoch', 'train_loss', 'val_loss', 'lr'])

    for epoch in range(1, epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, device, delta)
        val_loss   = evaluate_loss(model, val_loader, device, delta)
        current_lr = scheduler.get_last_lr()[0]
        scheduler.step()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch    = epoch
            best_state    = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            no_improve    = 0
            if best_model_path:
                torch.save({
                    'epoch':       epoch,
                    'model_state': model.state_dict(),
                    'val_loss':    val_loss,
                }, best_model_path)
        else:
            no_improve += 1
            if no_improve >= patience:
                break

        if log_path:
            with open(log_path, 'a', newline='') as f:
                csv.writer(f).writerow([
                    epoch,
                    f"{train_loss:.6f}",
                    f"{val_loss:.6f}",
                    f"{current_lr:.2e}",
                ])

        if verbose and (epoch % 10 == 0 or epoch == 1):
            print(f"Epoch {epoch:4d}/{epochs} | "
                  f"train_loss={train_loss:.4f} | "
                  f"val_loss={val_loss:.4f} | "
                  f"lr={current_lr:.2e}")

    if best_state is not None:
        model.load_state_dict(best_state)

    return best_val_loss, best_epoch, best_state


# ── Optuna objective ──────────────────────────────────────────────────────────

def make_optuna_objective(args, train_ds, val_ds, input_dim, target_dim, device):
    """Optuna objective 함수를 클로저로 반환."""

    def objective(trial):
        d_branch = trial.suggest_categorical('d_branch', [32, 64, 128, 256])
        n_heads  = trial.suggest_categorical('n_heads',  [2, 4, 8])
        # d_branch % n_heads == 0 보장: pruning
        if d_branch % n_heads != 0:
            raise optuna.exceptions.TrialPruned()
        lr       = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
        dropout  = trial.suggest_float('dropout', 0.0, 0.4)
        batch    = trial.suggest_categorical('batch', [128, 256, 512])
        T_sig    = trial.suggest_categorical('T_sig',   [60.0, 90.0, 120.0])
        T_phase  = trial.suggest_categorical('T_phase', [20.0, 30.0, 45.0])
        delta    = trial.suggest_categorical('delta',   [0.5, 1.0, 2.0])

        hpo_epochs = min(args.epochs, 50)

        loader_tr  = DataLoader(train_ds, batch_size=batch, shuffle=True,  num_workers=0)
        loader_val = DataLoader(val_ds,   batch_size=batch, shuffle=False, num_workers=0)

        model = STMBAN(
            input_dim=input_dim,
            d_branch=d_branch,
            n_heads=n_heads,
            dropout=dropout,
            T_sig=T_sig,
            T_phase=T_phase,
        ).to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=hpo_epochs, eta_min=lr * 1e-2
        )

        best_val, _, _ = run_training(
            model, loader_tr, loader_val, optimizer, scheduler,
            epochs=hpo_epochs, device=device, delta=delta,
            patience=8, verbose=False,
        )
        return best_val

    return objective


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train ST-MBAN")
    parser.add_argument("--data_dir", type=str,
                        default="/home/nyj/ST-MBAN/시뮬/데이터셋")
    parser.add_argument("--hidden",   type=int,   default=64,
                        help="d_branch: 각 branch 인코더 출력 차원")
    parser.add_argument("--n_heads",  type=int,   default=4,
                        help="MHA head 수 (d_branch % n_heads == 0 이어야 함)")
    parser.add_argument("--epochs",   type=int,   default=100)
    parser.add_argument("--lr",       type=float, default=1e-3)
    parser.add_argument("--batch",    type=int,   default=256)
    parser.add_argument("--dropout",  type=float, default=0.1)
    parser.add_argument("--device",   type=str,   default="cpu")
    parser.add_argument("--delta",    type=float, default=1.0,
                        help="Huber loss delta")
    parser.add_argument("--T_sig",    type=float, default=90.0,
                        help="CTE 신호 위상 주기 (초)")
    parser.add_argument("--T_phase",  type=float, default=30.0,
                        help="CTE 위상 잔여 시간 주기 (초)")
    parser.add_argument("--seed",     type=int,   default=42)
    # Optuna HPO
    parser.add_argument("--optuna",   action="store_true", help="Optuna HPO 실행")
    parser.add_argument("--n_trials", type=int,   default=50, help="Optuna trial 수")
    parser.add_argument("--timeout",  type=int,   default=None, help="Optuna 최대 시간(초)")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # 디바이스 설정
    if args.device != "cpu" and torch.cuda.is_available():
        device = torch.device(args.device)
    else:
        device = torch.device("cpu")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    scaler_dir = os.path.join(RESULTS_DIR, "scalers")

    # ── Dataset ──────────────────────────────────────────────────────────────
    print(f"[Data] Loading from: {args.data_dir}")
    train_ds = SumoDataset(args.data_dir, split='train', seed=args.seed,
                           scaler_dir=scaler_dir)
    val_ds   = SumoDataset(args.data_dir, split='val',   seed=args.seed,
                           scaler_dir=scaler_dir)
    test_ds  = SumoDataset(args.data_dir, split='test',  seed=args.seed,
                           scaler_dir=scaler_dir)

    input_dim  = train_ds.input_dim
    target_dim = train_ds.target_dim
    print(f"[Data] Train={len(train_ds)} | Val={len(val_ds)} | Test={len(test_ds)}")
    print(f"[Data] input_dim={input_dim}, target_dim={target_dim}")

    log_path        = os.path.join(RESULTS_DIR, "training_log_stmban.csv")
    best_model_path = os.path.join(RESULTS_DIR, "st_mban_best.pt")

    # ── Optuna HPO 분기 ───────────────────────────────────────────────────────
    if args.optuna:
        if not _OPTUNA_AVAILABLE:
            print("[Warning] optuna not installed. Falling back to default training.")
            args.optuna = False
        else:
            print(f"\n[HPO] Starting Optuna HPO | n_trials={args.n_trials} | "
                  f"timeout={args.timeout}s")
            print("-" * 65)

            objective = make_optuna_objective(
                args, train_ds, val_ds, input_dim, target_dim, device
            )
            study = optuna.create_study(
                direction='minimize',
                sampler=optuna.samplers.TPESampler(seed=args.seed),
            )
            study.optimize(
                objective,
                n_trials=args.n_trials,
                timeout=args.timeout,
                show_progress_bar=False,
            )

            best_params = study.best_params
            print(f"\n[HPO] Done | best_val={study.best_value:.4f}")
            print(f"[HPO] best_params={best_params}")

            # best_params 적용
            d_branch = best_params['d_branch']
            n_heads  = best_params['n_heads']
            lr       = best_params['lr']
            dropout  = best_params['dropout']
            batch    = best_params['batch']
            T_sig    = best_params['T_sig']
            T_phase  = best_params['T_phase']
            delta    = best_params['delta']

            train_loader = DataLoader(train_ds, batch_size=batch, shuffle=True,  num_workers=0)
            val_loader   = DataLoader(val_ds,   batch_size=batch, shuffle=False, num_workers=0)
            test_loader  = DataLoader(test_ds,  batch_size=batch, shuffle=False, num_workers=0)

            model = STMBAN(
                input_dim=input_dim,
                d_branch=d_branch,
                n_heads=n_heads,
                dropout=dropout,
                T_sig=T_sig,
                T_phase=T_phase,
            ).to(device)

            n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            print(f"\n[Model] STMBAN (HPO) | d_branch={d_branch} | n_heads={n_heads} "
                  f"| params={n_params:,}")

            optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=args.epochs, eta_min=lr * 1e-2
            )

            print(f"\n[Train] Full training | epochs={args.epochs} | "
                  f"Huber delta={delta}")
            print("-" * 65)

            best_val_loss, best_epoch, best_state = run_training(
                model, train_loader, val_loader, optimizer, scheduler,
                epochs=args.epochs, device=device, delta=delta,
                patience=15, log_path=log_path,
                best_model_path=best_model_path, verbose=True,
            )

            # best_model_path에 full 메타 저장
            torch.save({
                'epoch':       best_epoch,
                'model_state': best_state,
                'input_dim':   input_dim,
                'target_dim':  target_dim,
                'd_branch':    d_branch,
                'n_heads':     n_heads,
                'dropout':     dropout,
                'T_sig':       T_sig,
                'T_phase':     T_phase,
                'val_loss':    best_val_loss,
                'best_params': best_params,
            }, best_model_path)

            print("-" * 65)

            # ── Test Evaluation ───────────────────────────────────────────────
            ckpt = torch.load(best_model_path, map_location=device)
            model.load_state_dict(ckpt['model_state'])

            test_loss            = evaluate_loss(model, test_loader, device, delta)
            test_mae, test_rmse  = evaluate_metrics(model, test_loader, device)

            print(f"\n[Test] Best epoch={ckpt['epoch']} | "
                  f"val_loss(best)={ckpt['val_loss']:.4f}")
            print(f"[Test] test_huber={test_loss:.4f} | "
                  f"test_MAE={test_mae:.4f} | test_RMSE={test_rmse:.4f}")
            print(f"\n[Done] Model saved : {best_model_path}")
            print(f"[Done] Log saved   : {log_path}")
            return

    # ── 기존 학습 루프 ────────────────────────────────────────────────────────
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch, shuffle=False, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=args.batch, shuffle=False, num_workers=0)

    model = STMBAN(
        input_dim=input_dim,
        d_branch=args.hidden,
        n_heads=args.n_heads,
        dropout=args.dropout,
        T_sig=args.T_sig,
        T_phase=args.T_phase,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[Model] STMBAN | d_branch={args.hidden} | n_heads={args.n_heads} "
          f"| params={n_params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=args.lr * 1e-2
    )

    print(f"\n[Train] Starting {args.epochs} epochs on {device} | "
          f"Huber delta={args.delta}")
    print("-" * 65)

    best_val_loss, best_epoch, best_state = run_training(
        model, train_loader, val_loader, optimizer, scheduler,
        epochs=args.epochs, device=device, delta=args.delta,
        patience=15, log_path=log_path,
        best_model_path=best_model_path, verbose=True,
    )

    # best_model_path에 full 메타 저장
    torch.save({
        'epoch':       best_epoch,
        'model_state': best_state,
        'input_dim':   input_dim,
        'target_dim':  target_dim,
        'd_branch':    args.hidden,
        'n_heads':     args.n_heads,
        'dropout':     args.dropout,
        'T_sig':       args.T_sig,
        'T_phase':     args.T_phase,
        'val_loss':    best_val_loss,
    }, best_model_path)

    print("-" * 65)

    # ── Test Evaluation ───────────────────────────────────────────────────────
    ckpt = torch.load(best_model_path, map_location=device)
    model.load_state_dict(ckpt['model_state'])

    test_loss            = evaluate_loss(model, test_loader, device, args.delta)
    test_mae, test_rmse  = evaluate_metrics(model, test_loader, device)

    print(f"\n[Test] Best epoch={ckpt['epoch']} | "
          f"val_loss(best)={ckpt['val_loss']:.4f}")
    print(f"[Test] test_huber={test_loss:.4f} | "
          f"test_MAE={test_mae:.4f} | test_RMSE={test_rmse:.4f}")
    print(f"\n[Done] Model saved : {best_model_path}")
    print(f"[Done] Log saved   : {log_path}")


if __name__ == "__main__":
    main()
