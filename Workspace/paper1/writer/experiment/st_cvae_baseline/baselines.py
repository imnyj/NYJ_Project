"""
ST-MBAN Baseline Models
=======================
10개 비교 기준선 모델 구현 (ML 5개 + DL 5개)

Usage:
    python baselines.py --data_dir /home/nyj/ST-MBAN/시뮬/데이터셋 \
                        --epochs 100 --lr 1e-3 --batch 256 --device cpu \
                        --n_trials 50
"""
import argparse
import os
import time
import warnings
import pickle

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset import SumoDataset, FEATURE_COLS, TARGET_COLS

warnings.filterwarnings("ignore")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _OPTUNA_AVAILABLE = True
except ImportError:
    _OPTUNA_AVAILABLE = False

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results_baselines")

# ============================================================
#  공통 유틸
# ============================================================

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    y_true, y_pred: shape (N, 2) — [dwell_cur, dwell_nxt]
    반환: MAE_cur, MAE_nxt, RMSE_cur, RMSE_nxt
    """
    err = y_true - y_pred
    mae  = np.mean(np.abs(err), axis=0)   # (2,)
    rmse = np.sqrt(np.mean(err ** 2, axis=0))  # (2,)
    return {
        "MAE_cur":  float(mae[0]),
        "MAE_nxt":  float(mae[1]),
        "RMSE_cur": float(rmse[0]),
        "RMSE_nxt": float(rmse[1]),
    }


def numpy_from_dataset(ds: SumoDataset):
    """SumoDataset → (X_np, Y_np) numpy arrays"""
    return ds.X.numpy(), ds.Y.numpy()


# ============================================================
#  ML Baselines (scikit-learn)
# ============================================================

class LRBaseline:
    """Linear Regression (sklearn MultiOutputRegressor)"""
    name = "LR"

    def __init__(self):
        from sklearn.linear_model import LinearRegression
        from sklearn.multioutput import MultiOutputRegressor
        self.model = MultiOutputRegressor(LinearRegression(), n_jobs=-1)

    def fit(self, X, Y):
        self.model.fit(X, Y)

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)


class RFBaseline:
    """Random Forest Regressor"""
    name = "RF"

    def __init__(self):
        from sklearn.ensemble import RandomForestRegressor
        # RandomForestRegressor는 multi-output을 직접 지원
        self.model = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42)

    def fit(self, X, Y):
        self.model.fit(X, Y)

    def predict(self, X) -> np.ndarray:
        return self.model.predict(X)


class XGBBaseline:
    """XGBoost Regressor"""
    name = "XGBoost"

    def __init__(self):
        try:
            from xgboost import XGBRegressor
            from sklearn.multioutput import MultiOutputRegressor
            self.model = MultiOutputRegressor(
                XGBRegressor(
                    n_estimators=500,
                    learning_rate=0.05,
                    max_depth=6,
                    random_state=42,
                    n_jobs=-1,
                    verbosity=0,
                ),
                n_jobs=1,
            )
            self._available = True
        except ImportError:
            print("[Warning] xgboost not installed. Skipping XGBoost.")
            self._available = False

    def fit(self, X, Y):
        if not self._available:
            return
        self.model.fit(X, Y)

    def predict(self, X) -> np.ndarray:
        if not self._available:
            return None
        return self.model.predict(X)


class CatBoostBaseline:
    """CatBoost Regressor"""
    name = "CatBoost"

    def __init__(self):
        try:
            from catboost import CatBoostRegressor
            from sklearn.multioutput import MultiOutputRegressor
            self.model = MultiOutputRegressor(
                CatBoostRegressor(
                    iterations=500,
                    learning_rate=0.05,
                    depth=6,
                    verbose=0,
                    random_seed=42,
                ),
                n_jobs=1,
            )
            self._available = True
        except ImportError:
            print("[Warning] catboost not installed. Skipping CatBoost.")
            self._available = False

    def fit(self, X, Y):
        if not self._available:
            return
        self.model.fit(X, Y)

    def predict(self, X) -> np.ndarray:
        if not self._available:
            return None
        return self.model.predict(X)


class NGBoostBaseline:
    """NGBoost — 확률 예측 모델, 점 추정값(mean)을 baseline으로 사용"""
    name = "NGBoost"

    def __init__(self):
        try:
            from ngboost import NGBRegressor
            from sklearn.multioutput import MultiOutputRegressor
            self.model = MultiOutputRegressor(
                NGBRegressor(
                    n_estimators=500,
                    learning_rate=0.05,
                    verbose=False,
                    random_state=42,
                ),
                n_jobs=1,
            )
            self._available = True
        except ImportError:
            print("[Warning] ngboost not installed. Skipping NGBoost.")
            self._available = False

    def fit(self, X, Y):
        if not self._available:
            return
        self.model.fit(X, Y)

    def predict(self, X) -> np.ndarray:
        if not self._available:
            return None
        return self.model.predict(X)


# ============================================================
#  DL Baselines (PyTorch)
# ============================================================

class MLPBaseline(nn.Module):
    """
    Multi-Layer Perceptron
    hidden_dims: [256, 128, 64] (기본값)
    """
    name = "MLP"

    def __init__(self, input_dim: int, output_dim: int, hidden_dims=None, dropout: float = 0.1):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [256, 128, 64]
        layers = []
        prev = input_dim
        for h in hidden_dims:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class TabResNet(nn.Module):
    """
    ResNet for Tabular Data (Gorishniy et al., NeurIPS 2021)
    구조: Linear projection + (LayerNorm → Linear → ReGLU → Dropout → Linear → Dropout) × n_blocks + skip
    """
    name = "ResNet"

    class _ReGLU(nn.Module):
        """Rectified Gated Linear Unit: splits last dim in half, applies ReLU gating."""
        def forward(self, x):
            a, b = x.chunk(2, dim=-1)
            return a * torch.relu(b)

    class _ResBlock(nn.Module):
        def __init__(self, d_main: int, d_hidden: int, dropout: float):
            super().__init__()
            self.norm = nn.LayerNorm(d_main)
            self.linear1 = nn.Linear(d_main, d_hidden * 2)  # *2 for ReGLU
            self.act = TabResNet._ReGLU()
            self.drop1 = nn.Dropout(dropout)
            self.linear2 = nn.Linear(d_hidden, d_main)
            self.drop2 = nn.Dropout(dropout)

        def forward(self, x):
            residual = x
            x = self.norm(x)
            x = self.linear1(x)
            x = self.act(x)
            x = self.drop1(x)
            x = self.linear2(x)
            x = self.drop2(x)
            return x + residual

    def __init__(self, input_dim: int, output_dim: int,
                 d_main: int = 128, d_hidden: int = 256,
                 n_blocks: int = 4, dropout: float = 0.1):
        super().__init__()
        self.proj = nn.Linear(input_dim, d_main)
        self.blocks = nn.Sequential(
            *[TabResNet._ResBlock(d_main, d_hidden, dropout) for _ in range(n_blocks)]
        )
        self.head = nn.Sequential(nn.LayerNorm(d_main), nn.ReLU(), nn.Linear(d_main, output_dim))

    def forward(self, x):
        x = self.proj(x)
        x = self.blocks(x)
        return self.head(x)


class FTTransformer(nn.Module):
    """
    Feature Tokenizer + Transformer (Gorishniy et al., NeurIPS 2021)
    각 피처를 d_token 차원으로 임베딩 → [CLS] token 추가 → Transformer Encoder → CLS 출력 → Linear
    """
    name = "FTT"

    def __init__(self, input_dim: int, output_dim: int,
                 d_token: int = 64, n_heads: int = 8,
                 n_layers: int = 3, dropout: float = 0.1):
        super().__init__()
        self.input_dim = input_dim
        self.d_token = d_token

        # 각 피처: scalar → d_token (weight + bias)
        self.feature_weight = nn.Parameter(torch.empty(input_dim, d_token))
        self.feature_bias   = nn.Parameter(torch.empty(input_dim, d_token))
        nn.init.kaiming_uniform_(self.feature_weight, a=np.sqrt(5))
        nn.init.zeros_(self.feature_bias)

        # [CLS] token
        self.cls_token = nn.Parameter(torch.empty(1, 1, d_token))
        nn.init.normal_(self.cls_token, std=0.02)

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_token,
            nhead=n_heads,
            dim_feedforward=d_token * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,  # pre-norm (Gorishniy 권장)
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.head = nn.Sequential(nn.LayerNorm(d_token), nn.ReLU(), nn.Linear(d_token, output_dim))

    def forward(self, x):
        # x: (B, F)
        # Feature Tokenization: (B, F) → (B, F, d_token)
        tokens = x.unsqueeze(-1) * self.feature_weight.unsqueeze(0) + self.feature_bias.unsqueeze(0)
        # CLS token: (1, 1, d_token) → (B, 1, d_token)
        cls = self.cls_token.expand(x.size(0), -1, -1)
        # Concatenate: (B, F+1, d_token)
        tokens = torch.cat([cls, tokens], dim=1)
        # Transformer
        out = self.transformer(tokens)
        # CLS 출력만 사용
        cls_out = out[:, 0, :]
        return self.head(cls_out)


class TabR(nn.Module):
    """
    TabR — 간소화 버전 (Gorishniy et al., ICLR 2023)
    원본의 복잡한 retrieval 메커니즘을 다음으로 간소화:
      - 훈련 데이터 서브셋을 key-value store로 사용
      - 각 샘플에 대해 top-K nearest neighbor 검색 (L2 거리)
      - neighbor label 평균 + MLP 출력 가중 결합 (학습 가능한 alpha)
    """
    name = "TabR"

    def __init__(self, input_dim: int, output_dim: int,
                 hidden_dims=None, dropout: float = 0.1,
                 k: int = 5):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [256, 128, 64]
        self.k = k

        # MLP backbone
        layers = []
        prev = input_dim
        for h in hidden_dims:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, output_dim))
        self.mlp = nn.Sequential(*layers)

        # 결합 가중치 (학습 가능, sigmoid → [0,1])
        self.alpha = nn.Parameter(torch.tensor(0.5))

        # key-value store (훈련 중 등록)
        self.register_buffer("store_X", torch.empty(0))
        self.register_buffer("store_Y", torch.empty(0))
        self._store_ready = False

    def register_store(self, X: torch.Tensor, Y: torch.Tensor):
        """훈련 데이터 서브셋을 key-value store로 등록"""
        self.store_X = X.detach()
        self.store_Y = Y.detach()
        self._store_ready = True

    def _knn_predict(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, F) → (B, output_dim) neighbor 평균"""
        # 거리 행렬: (B, N_store)
        diff = x.unsqueeze(1) - self.store_X.unsqueeze(0)  # (B, N, F)
        dist = (diff ** 2).sum(-1)  # (B, N)
        # top-K
        k = min(self.k, dist.size(1))
        _, idx = dist.topk(k, dim=1, largest=False)  # (B, k)
        neighbor_y = self.store_Y[idx]  # (B, k, output_dim)
        return neighbor_y.mean(dim=1)   # (B, output_dim)

    def forward(self, x):
        mlp_out = self.mlp(x)
        if self._store_ready and self.store_X.size(0) > 0:
            knn_out = self._knn_predict(x)
            alpha = torch.sigmoid(self.alpha)
            return alpha * mlp_out + (1 - alpha) * knn_out
        return mlp_out


# ============================================================
#  DL 학습 공통 루틴
# ============================================================

def train_dl_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int,
    lr: float,
    device: torch.device,
    patience: int = 15,
) -> nn.Module:
    """
    공통 DL 학습 루틴
    - Loss: HuberLoss(delta=1.0)
    - Optimizer: AdamW
    - Scheduler: CosineAnnealingLR
    - Early stopping: val_loss patience
    """
    model = model.to(device)
    criterion = nn.HuberLoss(delta=1.0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val = float("inf")
    best_state = None
    no_improve = 0

    for epoch in range(1, epochs + 1):
        # --- train ---
        model.train()
        for X_b, Y_b in train_loader:
            X_b, Y_b = X_b.to(device), Y_b.to(device)
            optimizer.zero_grad()
            pred = model(X_b)
            loss = criterion(pred, Y_b)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
        scheduler.step()

        # --- val ---
        model.eval()
        val_loss = 0.0
        val_n = 0
        with torch.no_grad():
            for X_b, Y_b in val_loader:
                X_b, Y_b = X_b.to(device), Y_b.to(device)
                pred = model(X_b)
                val_loss += criterion(pred, Y_b).item() * X_b.size(0)
                val_n += X_b.size(0)
        val_loss /= val_n

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


def predict_dl(model: nn.Module, loader: DataLoader, device: torch.device) -> np.ndarray:
    """DataLoader → numpy predictions"""
    model.eval()
    preds = []
    with torch.no_grad():
        for X_b, _ in loader:
            X_b = X_b.to(device)
            preds.append(model(X_b).cpu().numpy())
    return np.concatenate(preds, axis=0)


# ============================================================
#  Unified Runner
# ============================================================

class BaselineRunner:
    """모든 baseline을 동일 조건으로 학습/평가"""

    def __init__(self, data_dir: str, epochs: int = 100, lr: float = 1e-3,
                 batch: int = 256, device: str = "cpu", hidden: int = 128,
                 n_trials: int = 0, timeout: int = None):
        self.data_dir = data_dir
        self.epochs = epochs
        self.lr = lr
        self.batch = batch
        self.device = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
        self.hidden = hidden
        self.n_trials = n_trials
        self.timeout = timeout
        self._load_data()

    def _load_data(self):
        print(f"[Data] Loading from {self.data_dir}")
        scaler_dir = os.path.join(RESULTS_DIR, "scalers")
        self.train_ds = SumoDataset(self.data_dir, split="train", scaler_dir=scaler_dir)
        self.val_ds   = SumoDataset(self.data_dir, split="val",   scaler_dir=scaler_dir)
        self.test_ds  = SumoDataset(self.data_dir, split="test",  scaler_dir=scaler_dir)

        self.train_loader = DataLoader(self.train_ds, batch_size=self.batch, shuffle=True,  num_workers=0)
        self.val_loader   = DataLoader(self.val_ds,   batch_size=self.batch, shuffle=False, num_workers=0)
        self.test_loader  = DataLoader(self.test_ds,  batch_size=self.batch, shuffle=False, num_workers=0)

        self.X_train, self.Y_train = numpy_from_dataset(self.train_ds)
        self.X_val,   self.Y_val   = numpy_from_dataset(self.val_ds)
        self.X_test,  self.Y_test  = numpy_from_dataset(self.test_ds)

        self.input_dim  = self.train_ds.input_dim
        self.output_dim = self.train_ds.target_dim
        print(f"[Data] Train={len(self.train_ds)} | Val={len(self.val_ds)} | Test={len(self.test_ds)}")
        print(f"[Data] input_dim={self.input_dim}, output_dim={self.output_dim}")

    # ============================================================
    #  Optuna objective 함수들 (ML)
    # ============================================================

    def _optuna_objective_rf(self, trial):
        from sklearn.ensemble import RandomForestRegressor
        params = {
            'n_estimators':      trial.suggest_int('n_estimators', 100, 600, step=100),
            'max_depth':         trial.suggest_int('max_depth', 3, 15),
            'min_samples_split': trial.suggest_int('min_samples_split', 2, 10),
        }
        model = RandomForestRegressor(**params, random_state=42, n_jobs=-1)
        model.fit(self.X_train, self.Y_train)
        pred = model.predict(self.X_val)
        mae = np.mean(np.abs(self.Y_val - pred))
        return mae

    def _optuna_objective_xgb(self, trial):
        from xgboost import XGBRegressor
        from sklearn.multioutput import MultiOutputRegressor
        params = {
            'n_estimators':     trial.suggest_int('n_estimators', 100, 700, step=100),
            'learning_rate':    trial.suggest_float('learning_rate', 1e-3, 0.3, log=True),
            'max_depth':        trial.suggest_int('max_depth', 3, 9),
            'subsample':        trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        }
        model = MultiOutputRegressor(
            XGBRegressor(**params, random_state=42, n_jobs=-1, verbosity=0),
            n_jobs=1,
        )
        model.fit(self.X_train, self.Y_train)
        pred = model.predict(self.X_val)
        mae = np.mean(np.abs(self.Y_val - pred))
        return mae

    def _optuna_objective_catboost(self, trial):
        from catboost import CatBoostRegressor
        from sklearn.multioutput import MultiOutputRegressor
        params = {
            'iterations':    trial.suggest_int('iterations', 100, 700, step=100),
            'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.3, log=True),
            'depth':         trial.suggest_int('depth', 3, 10),
            'l2_leaf_reg':   trial.suggest_float('l2_leaf_reg', 1.0, 10.0),
        }
        model = MultiOutputRegressor(
            CatBoostRegressor(**params, verbose=0, random_seed=42),
            n_jobs=1,
        )
        model.fit(self.X_train, self.Y_train)
        pred = model.predict(self.X_val)
        mae = np.mean(np.abs(self.Y_val - pred))
        return mae

    def _optuna_objective_ngboost(self, trial):
        from ngboost import NGBRegressor
        from sklearn.multioutput import MultiOutputRegressor
        params = {
            'n_estimators':   trial.suggest_int('n_estimators', 100, 600, step=100),
            'learning_rate':  trial.suggest_float('learning_rate', 1e-3, 0.2, log=True),
            'minibatch_frac': trial.suggest_float('minibatch_frac', 0.5, 1.0),
        }
        model = MultiOutputRegressor(
            NGBRegressor(**params, verbose=False, random_state=42),
            n_jobs=1,
        )
        model.fit(self.X_train, self.Y_train)
        pred = model.predict(self.X_val)
        mae = np.mean(np.abs(self.Y_val - pred))
        return mae

    # ============================================================
    #  Optuna objective 함수들 (DL)
    # ============================================================

    def _optuna_objective_mlp(self, trial):
        n_layers = trial.suggest_int('n_layers', 2, 4)
        width    = trial.suggest_categorical('width', [64, 128, 256, 512])
        lr       = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
        dropout  = trial.suggest_float('dropout', 0.0, 0.4)
        batch    = trial.suggest_categorical('batch', [128, 256, 512])

        loader_tr  = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
        loader_val = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)

        model = MLPBaseline(self.input_dim, self.output_dim,
                            hidden_dims=[width] * n_layers, dropout=dropout)
        model = train_dl_model(model, loader_tr, loader_val,
                               epochs=min(self.epochs, 50),
                               lr=lr, device=self.device, patience=10)

        criterion = nn.HuberLoss(delta=1.0)
        model.eval()
        val_loss = 0.0
        n = 0
        with torch.no_grad():
            for Xb, Yb in loader_val:
                Xb, Yb = Xb.to(self.device), Yb.to(self.device)
                val_loss += criterion(model(Xb), Yb).item() * Xb.size(0)
                n += Xb.size(0)
        return val_loss / n

    def _optuna_objective_resnet(self, trial):
        d_main   = trial.suggest_categorical('d_main',   [64, 128, 256])
        d_hidden = trial.suggest_categorical('d_hidden', [128, 256, 512])
        n_blocks = trial.suggest_int('n_blocks', 2, 6)
        lr       = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
        dropout  = trial.suggest_float('dropout', 0.0, 0.4)
        batch    = trial.suggest_categorical('batch', [128, 256, 512])

        loader_tr  = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
        loader_val = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)

        model = TabResNet(self.input_dim, self.output_dim,
                          d_main=d_main, d_hidden=d_hidden,
                          n_blocks=n_blocks, dropout=dropout)
        model = train_dl_model(model, loader_tr, loader_val,
                               epochs=min(self.epochs, 50),
                               lr=lr, device=self.device, patience=10)

        criterion = nn.HuberLoss(delta=1.0)
        model.eval()
        val_loss = 0.0
        n = 0
        with torch.no_grad():
            for Xb, Yb in loader_val:
                Xb, Yb = Xb.to(self.device), Yb.to(self.device)
                val_loss += criterion(model(Xb), Yb).item() * Xb.size(0)
                n += Xb.size(0)
        return val_loss / n

    def _optuna_objective_ftt(self, trial):
        d_token  = trial.suggest_categorical('d_token',  [32, 64, 128])
        # d_token을 나눌 수 있는 n_heads 중에서 선택
        valid_heads = [h for h in [2, 4, 8] if d_token % h == 0]
        n_heads  = trial.suggest_categorical('n_heads', valid_heads)
        n_layers = trial.suggest_int('n_layers', 1, 4)
        lr       = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
        dropout  = trial.suggest_float('dropout', 0.0, 0.3)
        batch    = trial.suggest_categorical('batch', [128, 256, 512])

        loader_tr  = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
        loader_val = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)

        model = FTTransformer(self.input_dim, self.output_dim,
                              d_token=d_token, n_heads=n_heads,
                              n_layers=n_layers, dropout=dropout)
        model = train_dl_model(model, loader_tr, loader_val,
                               epochs=min(self.epochs, 50),
                               lr=lr, device=self.device, patience=10)

        criterion = nn.HuberLoss(delta=1.0)
        model.eval()
        val_loss = 0.0
        n = 0
        with torch.no_grad():
            for Xb, Yb in loader_val:
                Xb, Yb = Xb.to(self.device), Yb.to(self.device)
                val_loss += criterion(model(Xb), Yb).item() * Xb.size(0)
                n += Xb.size(0)
        return val_loss / n

    def _optuna_objective_tabr(self, trial):
        width    = trial.suggest_categorical('width',   [64, 128, 256])
        n_layers = trial.suggest_int('n_layers', 2, 4)
        k        = trial.suggest_int('k', 3, 15)
        lr       = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
        dropout  = trial.suggest_float('dropout', 0.0, 0.4)
        batch    = trial.suggest_categorical('batch', [128, 256, 512])

        loader_tr  = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
        loader_val = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)

        model = TabR(self.input_dim, self.output_dim,
                     hidden_dims=[width] * n_layers, dropout=dropout, k=k)

        # store 등록 (훈련 전 서브셋)
        MAX_STORE = 2000
        X_np = self.X_train
        Y_np = self.Y_train
        if len(X_np) > MAX_STORE:
            idx = np.random.RandomState(42).choice(len(X_np), MAX_STORE, replace=False)
            X_np = X_np[idx]
            Y_np = Y_np[idx]

        model = train_dl_model(model, loader_tr, loader_val,
                               epochs=min(self.epochs, 50),
                               lr=lr, device=self.device, patience=10)
        model = model.to(self.device)
        store_X = torch.from_numpy(X_np).to(self.device)
        store_Y = torch.from_numpy(Y_np).to(self.device)
        model.register_store(store_X, store_Y)

        criterion = nn.HuberLoss(delta=1.0)
        model.eval()
        val_loss = 0.0
        n = 0
        with torch.no_grad():
            for Xb, Yb in loader_val:
                Xb, Yb = Xb.to(self.device), Yb.to(self.device)
                val_loss += criterion(model(Xb), Yb).item() * Xb.size(0)
                n += Xb.size(0)
        return val_loss / n

    # ============================================================
    #  HPO 실행 헬퍼
    # ============================================================

    def _run_hpo(self, model_name: str, objective_fn) -> dict:
        """Optuna study를 생성하고 최적 파라미터를 반환."""
        if not _OPTUNA_AVAILABLE:
            print(f"  [{model_name}] optuna not installed. Skipping HPO.")
            return {}
        study = optuna.create_study(
            direction='minimize',
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        study.optimize(
            objective_fn,
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=False,
        )
        print(f"  [{model_name}] HPO done | best_val={study.best_value:.4f} | "
              f"best_params={study.best_params}")
        return study.best_params

    # ---- ML 실행 ----

    def _run_ml(self, baseline_obj) -> dict | None:
        if hasattr(baseline_obj, "_available") and not baseline_obj._available:
            return None
        t0 = time.time()
        baseline_obj.fit(self.X_train, self.Y_train)
        pred = baseline_obj.predict(self.X_test)
        if pred is None:
            return None
        elapsed = time.time() - t0
        metrics = compute_metrics(self.Y_test, pred)
        metrics["time_s"] = round(elapsed, 1)
        return metrics

    # ---- DL 실행 ----

    def _run_dl(self, model: nn.Module) -> dict:
        t0 = time.time()
        model = train_dl_model(
            model, self.train_loader, self.val_loader,
            self.epochs, self.lr, self.device
        )
        pred = predict_dl(model, self.test_loader, self.device)
        elapsed = time.time() - t0
        metrics = compute_metrics(self.Y_test, pred)
        metrics["time_s"] = round(elapsed, 1)
        return metrics

    # ---- TabPFN ----

    def _run_tabpfn(self) -> dict | None:
        try:
            from tabpfn import TabPFNRegressor
        except ImportError:
            print("[Warning] tabpfn not installed. Skipping TabPFN.")
            return None

        MAX_TRAIN = 3000
        X_tr = self.X_train
        Y_tr = self.Y_train
        if len(X_tr) > MAX_TRAIN:
            idx = np.random.RandomState(42).choice(len(X_tr), MAX_TRAIN, replace=False)
            X_tr = X_tr[idx]
            Y_tr = Y_tr[idx]
            print(f"[TabPFN] Subsampled train to {MAX_TRAIN} samples.")

        t0 = time.time()
        preds_list = []
        for col_idx, col_name in enumerate(["dwell_cur", "dwell_nxt"]):
            reg = TabPFNRegressor(device=str(self.device))
            reg.fit(X_tr, Y_tr[:, col_idx])
            preds_list.append(reg.predict(self.X_test))
        pred = np.stack(preds_list, axis=1)  # (N, 2)
        elapsed = time.time() - t0
        metrics = compute_metrics(self.Y_test, pred)
        metrics["time_s"] = round(elapsed, 1)
        return metrics

    # ---- TabR 특수 처리 (store 등록 필요) ----

    def _run_tabr(self, best_params: dict = None) -> dict:
        if best_params:
            width    = best_params.get('width',    self.hidden * 2)
            n_layers = best_params.get('n_layers', 3)
            k        = best_params.get('k',        5)
            lr       = best_params.get('lr',       self.lr)
            dropout  = best_params.get('dropout',  0.1)
            batch    = best_params.get('batch',    self.batch)
            hidden_dims = [width] * n_layers
        else:
            hidden_dims = [self.hidden * 2, self.hidden, self.hidden // 2]
            lr      = self.lr
            dropout = 0.1
            batch   = self.batch
            k       = 5

        train_loader = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
        val_loader   = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)
        test_loader  = DataLoader(self.test_ds,  batch_size=batch, shuffle=False, num_workers=0)

        model = TabR(
            input_dim=self.input_dim,
            output_dim=self.output_dim,
            hidden_dims=hidden_dims,
            dropout=dropout,
            k=k,
        )
        # store 등록: 훈련 전에 (학습 데이터 서브셋 최대 2000개)
        MAX_STORE = 2000
        X_np = self.X_train
        Y_np = self.Y_train
        if len(X_np) > MAX_STORE:
            idx = np.random.RandomState(42).choice(len(X_np), MAX_STORE, replace=False)
            X_np = X_np[idx]
            Y_np = Y_np[idx]
        store_X = torch.from_numpy(X_np).to(self.device)
        store_Y = torch.from_numpy(Y_np).to(self.device)

        t0 = time.time()
        model = train_dl_model(
            model, train_loader, val_loader,
            self.epochs, lr, self.device
        )
        # 학습 완료 후 store 등록 (device 이동 후)
        model = model.to(self.device)
        model.register_store(store_X, store_Y)

        pred = predict_dl(model, test_loader, self.device)
        elapsed = time.time() - t0
        metrics = compute_metrics(self.Y_test, pred)
        metrics["time_s"] = round(elapsed, 1)
        return metrics

    # ---- 전체 실행 ----

    def run_all(self) -> pd.DataFrame:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        results = []

        def _log(name, metrics, best_params=None):
            if metrics is None:
                print(f"  [{name}] SKIPPED")
                return
            print(f"  [{name}] MAE_cur={metrics['MAE_cur']:.4f} MAE_nxt={metrics['MAE_nxt']:.4f} "
                  f"RMSE_cur={metrics['RMSE_cur']:.4f} RMSE_nxt={metrics['RMSE_nxt']:.4f} "
                  f"time={metrics['time_s']}s")
            row = {"model": name, **metrics, "best_params": str(best_params) if best_params else ""}
            results.append(row)

        use_hpo = (self.n_trials > 0) and _OPTUNA_AVAILABLE
        if self.n_trials > 0 and not _OPTUNA_AVAILABLE:
            print("[Warning] optuna not installed. Running without HPO.")

        print("\n===== ML Baselines =====")

        # LR: 튜닝 파라미터 없음, 그대로 실행
        print("  Running LR ...")
        obj = LRBaseline()
        m = self._run_ml(obj)
        _log("LR", m)

        # RF
        print("  Running RF ...")
        if use_hpo:
            best_params_rf = self._run_hpo("RF", self._optuna_objective_rf)
            from sklearn.ensemble import RandomForestRegressor
            final_model = RandomForestRegressor(
                n_estimators=best_params_rf.get('n_estimators', 300),
                max_depth=best_params_rf.get('max_depth', None),
                min_samples_split=best_params_rf.get('min_samples_split', 2),
                random_state=42, n_jobs=-1,
            )
            t0 = time.time()
            final_model.fit(self.X_train, self.Y_train)
            pred = final_model.predict(self.X_test)
            elapsed = time.time() - t0
            m = compute_metrics(self.Y_test, pred)
            m["time_s"] = round(elapsed, 1)
            _log("RF", m, best_params_rf)
        else:
            obj = RFBaseline()
            m = self._run_ml(obj)
            _log("RF", m)

        # XGBoost
        print("  Running XGBoost ...")
        try:
            from xgboost import XGBRegressor
            from sklearn.multioutput import MultiOutputRegressor as MOR
            _xgb_available = True
        except ImportError:
            _xgb_available = False
            print("[Warning] xgboost not installed. Skipping XGBoost.")

        if _xgb_available:
            if use_hpo:
                best_params_xgb = self._run_hpo("XGBoost", self._optuna_objective_xgb)
                final_model = MOR(
                    XGBRegressor(
                        n_estimators=best_params_xgb.get('n_estimators', 500),
                        learning_rate=best_params_xgb.get('learning_rate', 0.05),
                        max_depth=best_params_xgb.get('max_depth', 6),
                        subsample=best_params_xgb.get('subsample', 1.0),
                        colsample_bytree=best_params_xgb.get('colsample_bytree', 1.0),
                        random_state=42, n_jobs=-1, verbosity=0,
                    ),
                    n_jobs=1,
                )
                t0 = time.time()
                final_model.fit(self.X_train, self.Y_train)
                pred = final_model.predict(self.X_test)
                elapsed = time.time() - t0
                m = compute_metrics(self.Y_test, pred)
                m["time_s"] = round(elapsed, 1)
                _log("XGBoost", m, best_params_xgb)
            else:
                obj = XGBBaseline()
                m = self._run_ml(obj)
                _log("XGBoost", m)

        # CatBoost
        print("  Running CatBoost ...")
        try:
            from catboost import CatBoostRegressor
            from sklearn.multioutput import MultiOutputRegressor as MOR2
            _cat_available = True
        except ImportError:
            _cat_available = False
            print("[Warning] catboost not installed. Skipping CatBoost.")

        if _cat_available:
            if use_hpo:
                best_params_cat = self._run_hpo("CatBoost", self._optuna_objective_catboost)
                final_model = MOR2(
                    CatBoostRegressor(
                        iterations=best_params_cat.get('iterations', 500),
                        learning_rate=best_params_cat.get('learning_rate', 0.05),
                        depth=best_params_cat.get('depth', 6),
                        l2_leaf_reg=best_params_cat.get('l2_leaf_reg', 3.0),
                        verbose=0, random_seed=42,
                    ),
                    n_jobs=1,
                )
                t0 = time.time()
                final_model.fit(self.X_train, self.Y_train)
                pred = final_model.predict(self.X_test)
                elapsed = time.time() - t0
                m = compute_metrics(self.Y_test, pred)
                m["time_s"] = round(elapsed, 1)
                _log("CatBoost", m, best_params_cat)
            else:
                obj = CatBoostBaseline()
                m = self._run_ml(obj)
                _log("CatBoost", m)

        # NGBoost
        print("  Running NGBoost ...")
        try:
            from ngboost import NGBRegressor
            from sklearn.multioutput import MultiOutputRegressor as MOR3
            _ngb_available = True
        except ImportError:
            _ngb_available = False
            print("[Warning] ngboost not installed. Skipping NGBoost.")

        if _ngb_available:
            if use_hpo:
                best_params_ngb = self._run_hpo("NGBoost", self._optuna_objective_ngboost)
                final_model = MOR3(
                    NGBRegressor(
                        n_estimators=best_params_ngb.get('n_estimators', 500),
                        learning_rate=best_params_ngb.get('learning_rate', 0.05),
                        minibatch_frac=best_params_ngb.get('minibatch_frac', 1.0),
                        verbose=False, random_state=42,
                    ),
                    n_jobs=1,
                )
                t0 = time.time()
                final_model.fit(self.X_train, self.Y_train)
                pred = final_model.predict(self.X_test)
                elapsed = time.time() - t0
                m = compute_metrics(self.Y_test, pred)
                m["time_s"] = round(elapsed, 1)
                _log("NGBoost", m, best_params_ngb)
            else:
                obj = NGBoostBaseline()
                m = self._run_ml(obj)
                _log("NGBoost", m)

        print("\n===== DL Baselines =====")
        d = self.input_dim
        o = self.output_dim
        h = self.hidden

        # MLP
        print("  Running MLP ...")
        if use_hpo:
            best_params_mlp = self._run_hpo("MLP", self._optuna_objective_mlp)
            width    = best_params_mlp.get('width',   h)
            n_layers = best_params_mlp.get('n_layers', 3)
            lr_mlp   = best_params_mlp.get('lr',      self.lr)
            dropout  = best_params_mlp.get('dropout', 0.1)
            batch    = best_params_mlp.get('batch',   self.batch)
            loader_tr = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
            loader_te = DataLoader(self.test_ds,  batch_size=batch, shuffle=False, num_workers=0)
            loader_vl = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)
            model_mlp = MLPBaseline(d, o, hidden_dims=[width] * n_layers, dropout=dropout)
            t0 = time.time()
            model_mlp = train_dl_model(model_mlp, loader_tr, loader_vl,
                                       self.epochs, lr_mlp, self.device)
            pred = predict_dl(model_mlp, loader_te, self.device)
            elapsed = time.time() - t0
            m = compute_metrics(self.Y_test, pred)
            m["time_s"] = round(elapsed, 1)
            _log("MLP", m, best_params_mlp)
        else:
            model_mlp = MLPBaseline(d, o, hidden_dims=[h * 2, h, h // 2])
            m = self._run_dl(model_mlp)
            _log("MLP", m)

        # ResNet
        print("  Running ResNet ...")
        if use_hpo:
            best_params_res = self._run_hpo("ResNet", self._optuna_objective_resnet)
            d_main   = best_params_res.get('d_main',   h)
            d_hidden = best_params_res.get('d_hidden', h * 2)
            n_blocks = best_params_res.get('n_blocks', 4)
            lr_res   = best_params_res.get('lr',       self.lr)
            dropout  = best_params_res.get('dropout',  0.1)
            batch    = best_params_res.get('batch',    self.batch)
            loader_tr = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
            loader_te = DataLoader(self.test_ds,  batch_size=batch, shuffle=False, num_workers=0)
            loader_vl = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)
            model_res = TabResNet(d, o, d_main=d_main, d_hidden=d_hidden,
                                  n_blocks=n_blocks, dropout=dropout)
            t0 = time.time()
            model_res = train_dl_model(model_res, loader_tr, loader_vl,
                                       self.epochs, lr_res, self.device)
            pred = predict_dl(model_res, loader_te, self.device)
            elapsed = time.time() - t0
            m = compute_metrics(self.Y_test, pred)
            m["time_s"] = round(elapsed, 1)
            _log("ResNet", m, best_params_res)
        else:
            model_res = TabResNet(d, o, d_main=h, d_hidden=h * 2, n_blocks=4)
            m = self._run_dl(model_res)
            _log("ResNet", m)

        # FTT
        print("  Running FTT ...")
        if use_hpo:
            best_params_ftt = self._run_hpo("FTT", self._optuna_objective_ftt)
            d_token  = best_params_ftt.get('d_token',  max(h // 2, 32))
            n_heads  = best_params_ftt.get('n_heads',  4)
            n_layers = best_params_ftt.get('n_layers', 3)
            lr_ftt   = best_params_ftt.get('lr',       self.lr)
            dropout  = best_params_ftt.get('dropout',  0.1)
            batch    = best_params_ftt.get('batch',    self.batch)
            loader_tr = DataLoader(self.train_ds, batch_size=batch, shuffle=True,  num_workers=0)
            loader_te = DataLoader(self.test_ds,  batch_size=batch, shuffle=False, num_workers=0)
            loader_vl = DataLoader(self.val_ds,   batch_size=batch, shuffle=False, num_workers=0)
            model_ftt = FTTransformer(d, o, d_token=d_token, n_heads=n_heads,
                                      n_layers=n_layers, dropout=dropout)
            t0 = time.time()
            model_ftt = train_dl_model(model_ftt, loader_tr, loader_vl,
                                       self.epochs, lr_ftt, self.device)
            pred = predict_dl(model_ftt, loader_te, self.device)
            elapsed = time.time() - t0
            m = compute_metrics(self.Y_test, pred)
            m["time_s"] = round(elapsed, 1)
            _log("FTT", m, best_params_ftt)
        else:
            model_ftt = FTTransformer(d, o, d_token=max(h // 2, 32), n_heads=4, n_layers=3)
            m = self._run_dl(model_ftt)
            _log("FTT", m)

        # TabR
        print("  Running TabR ...")
        if use_hpo:
            best_params_tabr = self._run_hpo("TabR", self._optuna_objective_tabr)
            m = self._run_tabr(best_params=best_params_tabr)
            _log("TabR", m, best_params_tabr)
        else:
            m = self._run_tabr()
            _log("TabR", m)

        # TabPFN: 파라미터 없음, 그대로 실행
        print("  Running TabPFN ...")
        m = self._run_tabpfn()
        _log("TabPFN", m)

        df = pd.DataFrame(results)
        return df

    def save_results(self, df: pd.DataFrame):
        path = os.path.join(RESULTS_DIR, "baseline_results.csv")
        df.to_csv(path, index=False)
        print(f"\n[Done] Results saved → {path}")
        print(df.to_string(index=False))


# ============================================================
#  Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="ST-MBAN Baseline Models")
    parser.add_argument("--data_dir", type=str,
                        default="/home/nyj/ST-MBAN/시뮬/데이터셋",
                        help="RSU CSV 파일이 있는 디렉토리")
    parser.add_argument("--epochs",   type=int,   default=100,   help="DL 모델 학습 epoch 수")
    parser.add_argument("--lr",       type=float, default=1e-3,  help="DL 모델 학습률")
    parser.add_argument("--batch",    type=int,   default=256,   help="DL 모델 배치 크기")
    parser.add_argument("--device",   type=str,   default="cpu", help="cuda / cpu")
    parser.add_argument("--hidden",   type=int,   default=128,   help="DL 모델 hidden 기본 차원")
    parser.add_argument("--seed",     type=int,   default=42,    help="랜덤 시드")
    parser.add_argument("--n_trials", type=int,   default=50,    help="Optuna trial 수 (0이면 HPO 건너뜀)")
    parser.add_argument("--timeout",  type=int,   default=None,  help="모델당 Optuna 최대 시간(초)")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    runner = BaselineRunner(
        data_dir=args.data_dir,
        epochs=args.epochs,
        lr=args.lr,
        batch=args.batch,
        device=args.device,
        hidden=args.hidden,
        n_trials=args.n_trials,
        timeout=args.timeout,
    )
    df = runner.run_all()
    runner.save_results(df)


if __name__ == "__main__":
    main()
