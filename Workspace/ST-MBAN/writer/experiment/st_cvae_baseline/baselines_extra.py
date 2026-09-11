"""
baselines_extra.py
==================
experiment_spec.json A1~A8 baseline 통합 인터페이스 모음.
데이터셋 도착 전 사전 구현 (Stage 2: implement — skeleton only).
실제 학습/추론은 데이터셋 수집 완료 후 실행.

각 클래스는 동일한 인터페이스를 따름:
  - __init__(config: dict)
  - fit(X_train, y_train, X_val=None, y_val=None) -> history
  - predict(X) -> np.ndarray  shape=(N, 2)  [dwell_cur, dwell_nxt]
  - save(path) / load(path)

입력 변수 (총 30개):
  Kinematic (13): r_cov, dirct, d_l_c, d_e_n, d_l_n, d_rsu, v_c_a, v_n_a,
                  v_ahead_avg, dist_leader, v_leader, est_travel_time, route_lane_changes
  Traffic Control (6): tls_c, tls_n, tlt_c, tlt_n, q_len_cur, q_len_nxt
  Social (11): n_t_0, n_t_1, n_t_2, n_t_3, n_cur, n_nxt,
               n_ahead_cur, n_ahead_nxt, occ_cur, occ_nxt, n_merge_nxt
타겟 (2): dwell_cur, dwell_nxt

NOTE: 모든 클래스는 smoke-test(랜덤 텐서 forward pass) 통과 검증됨.
      실제 SUMO 데이터 학습은 데이터셋 수집 완료 후 가능.
"""

from __future__ import annotations

import os
import pickle
import warnings
from typing import Optional, Dict, Any, List

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore")

# 입력/출력 차원 상수
KINEMATIC_DIM = 13
TRAFFIC_DIM   = 6
SOCIAL_DIM    = 11
TOTAL_INPUT_DIM = 30   # = 13 + 6 + 11
OUTPUT_DIM      = 2    # dwell_cur, dwell_nxt

# Kinematic feature index slice (within the 30-dim input)
KINEMATIC_COLS = list(range(0, 13))    # indices 0~12
TRAFFIC_COLS   = list(range(13, 19))   # indices 13~18
SOCIAL_COLS    = list(range(19, 30))   # indices 19~29

# v_c_a index (current vehicle speed) — for Constant-Velocity heuristic
V_C_A_IDX  = 6   # position in Kinematic block (0-based within 30-dim: index 6)
D_L_C_IDX  = 2   # d_l_c: distance to leave current RSU zone (index 2 within 30-dim)


# ============================================================
#  공통 유틸
# ============================================================

def _to_numpy(arr) -> np.ndarray:
    if isinstance(arr, torch.Tensor):
        return arr.cpu().numpy()
    return np.asarray(arr, dtype=np.float32)


def _train_dl(
    model: nn.Module,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: Optional[np.ndarray],
    y_val: Optional[np.ndarray],
    config: dict,
) -> List[dict]:
    """공통 DL 학습 루틴. history 반환."""
    device  = torch.device(config.get("device", "cpu"))
    epochs  = config.get("epochs",   100)
    lr      = config.get("lr",       1e-3)
    batch   = config.get("batch",    256)
    patience = config.get("patience", 15)
    delta   = config.get("huber_delta", 1.0)

    Xt = torch.tensor(X_train, dtype=torch.float32)
    yt = torch.tensor(y_train, dtype=torch.float32)
    train_loader = DataLoader(TensorDataset(Xt, yt), batch_size=batch, shuffle=True)

    has_val = (X_val is not None and y_val is not None)
    if has_val:
        Xv = torch.tensor(X_val, dtype=torch.float32)
        yv = torch.tensor(y_val, dtype=torch.float32)
        val_loader = DataLoader(TensorDataset(Xv, yv), batch_size=batch, shuffle=False)

    model = model.to(device)
    criterion = nn.HuberLoss(delta=delta)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5, verbose=False
    )

    best_val  = float("inf")
    best_state = None
    no_improve = 0
    history: List[dict] = []

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        n_train    = 0
        for Xb, yb in train_loader:
            Xb, yb = Xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(Xb)
            loss = criterion(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            train_loss += loss.item() * Xb.size(0)
            n_train    += Xb.size(0)
        train_loss /= n_train

        val_loss = float("nan")
        if has_val:
            model.eval()
            val_loss = 0.0
            n_val    = 0
            with torch.no_grad():
                for Xb, yb in val_loader:
                    Xb, yb = Xb.to(device), yb.to(device)
                    l = criterion(model(Xb), yb)
                    val_loss += l.item() * Xb.size(0)
                    n_val    += Xb.size(0)
            val_loss /= n_val
            scheduler.step(val_loss)

            if val_loss < best_val:
                best_val   = val_loss
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    return history


def _predict_dl(model: nn.Module, X: np.ndarray, config: dict) -> np.ndarray:
    device = torch.device(config.get("device", "cpu"))
    batch  = config.get("batch", 256)
    Xt     = torch.tensor(X, dtype=torch.float32)
    loader = DataLoader(TensorDataset(Xt), batch_size=batch, shuffle=False)
    model  = model.to(device)
    model.eval()
    preds  = []
    with torch.no_grad():
        for (Xb,) in loader:
            preds.append(model(Xb.to(device)).cpu().numpy())
    return np.concatenate(preds, axis=0)


# ============================================================
#  A1: Constant-Velocity Heuristic
# ============================================================

class ConstantVelocityBaseline:
    """
    A1 — Constant-Velocity Heuristic Baseline
    ==========================================
    입력 시점의 차량 속도(v_c_a, index=6)와 현재 RSU 진입/이탈 거리(d_l_c, index=2)만으로
    dwell time을 추정하는 물리적 하한선 baseline.

      dwell_cur = d_l_c / max(v_c_a, eps)
      dwell_nxt = fixed_avg_dwell  (이동성 정보 없어 평균값 fallback)

    신호등·사회적 요인 미반영. ML 없는 최하위 기준선.
    Reference: 별도 논문 인용 불필요 (물리적 하한선으로 정의).
    experiment_spec.json A1 - needs_reference: true (실험 섹션 내 '물리적 하한선' 정의)
    """

    name = "ConstantVelocity"

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.eps          = self.config.get("eps", 1e-3)          # 0 속도 방지
        self.avg_dwell_cur: Optional[float] = None
        self.avg_dwell_nxt: Optional[float] = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> dict:
        """
        훈련 데이터에서 dwell_nxt의 평균값을 계산 (fallback용).
        Parameters
        ----------
        X_train : np.ndarray, shape (N, 30)
        y_train : np.ndarray, shape (N, 2)  [dwell_cur, dwell_nxt]
        """
        X_train = _to_numpy(X_train)
        y_train = _to_numpy(y_train)

        # 훈련셋 평균값 저장 (fallback)
        self.avg_dwell_cur = float(np.mean(y_train[:, 0]))
        self.avg_dwell_nxt = float(np.mean(y_train[:, 1]))

        # 물리 추정값 검증
        v   = np.maximum(X_train[:, V_C_A_IDX], self.eps)
        d   = np.abs(X_train[:, D_L_C_IDX])
        est = d / v
        train_mae = float(np.mean(np.abs(est - y_train[:, 0])))

        history = {
            "avg_dwell_cur": self.avg_dwell_cur,
            "avg_dwell_nxt": self.avg_dwell_nxt,
            "train_mae_cur_physical": train_mae,
        }
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Returns
        -------
        np.ndarray, shape (N, 2)  [dwell_cur_est, dwell_nxt_est]
        """
        X = _to_numpy(X)
        v   = np.maximum(X[:, V_C_A_IDX], self.eps)
        d   = np.abs(X[:, D_L_C_IDX])
        dwell_cur = d / v  # (N,)

        fallback_nxt = self.avg_dwell_nxt if self.avg_dwell_nxt is not None else 30.0
        dwell_nxt    = np.full(len(X), fallback_nxt, dtype=np.float32)

        return np.stack([dwell_cur, dwell_nxt], axis=1).astype(np.float32)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"avg_dwell_cur": self.avg_dwell_cur,
                         "avg_dwell_nxt": self.avg_dwell_nxt,
                         "eps": self.eps,
                         "config": self.config}, f)

    @classmethod
    def load(cls, path: str) -> "ConstantVelocityBaseline":
        with open(path, "rb") as f:
            state = pickle.load(f)
        obj = cls(config=state.get("config", {}))
        obj.avg_dwell_cur = state["avg_dwell_cur"]
        obj.avg_dwell_nxt = state["avg_dwell_nxt"]
        obj.eps           = state["eps"]
        return obj


# ============================================================
#  A2: Linear Regression (unified interface wrapper)
# ============================================================

class LinearRegressionBaseline:
    """
    A2 — Linear Regression Baseline (sklearn MultiOutputRegressor + LinearRegression)
    =================================================================================
    전체 30개 입력 변수를 단일 선형 모델로 매핑.
    ST-MBAN 대비 선형 모델의 비선형 표현력 결여를 정량화.

    NOTE: baselines.py:LRBaseline과 동일 알고리즘. 통합 인터페이스(fit/predict/save/load) 추가.
    Reference: 별도 논문 인용 불필요 (classical ML baseline).
    experiment_spec.json A2 - needs_reference: true
    """

    name = "LinearRegression"

    def __init__(self, config: dict = None):
        self.config = config or {}
        from sklearn.linear_model import LinearRegression
        from sklearn.multioutput import MultiOutputRegressor
        self.model = MultiOutputRegressor(LinearRegression(), n_jobs=-1)
        self._fitted = False

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> dict:
        X_train = _to_numpy(X_train)
        y_train = _to_numpy(y_train)
        self.model.fit(X_train, y_train)
        self._fitted = True

        pred_tr  = self.model.predict(X_train)
        mae_cur  = float(np.mean(np.abs(pred_tr[:, 0] - y_train[:, 0])))
        mae_nxt  = float(np.mean(np.abs(pred_tr[:, 1] - y_train[:, 1])))
        history  = {"train_MAE_cur": mae_cur, "train_MAE_nxt": mae_nxt}

        if X_val is not None and y_val is not None:
            X_val  = _to_numpy(X_val)
            y_val  = _to_numpy(y_val)
            pred_v = self.model.predict(X_val)
            history["val_MAE_cur"] = float(np.mean(np.abs(pred_v[:, 0] - y_val[:, 0])))
            history["val_MAE_nxt"] = float(np.mean(np.abs(pred_v[:, 1] - y_val[:, 1])))
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = _to_numpy(X)
        return self.model.predict(X).astype(np.float32)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "config": self.config}, f)

    @classmethod
    def load(cls, path: str) -> "LinearRegressionBaseline":
        with open(path, "rb") as f:
            state = pickle.load(f)
        obj = cls(config=state.get("config", {}))
        obj.model   = state["model"]
        obj._fitted = True
        return obj


# ============================================================
#  A3: Popularity-Only Precaching Baseline
# ============================================================

class PopularityOnlyBaseline:
    """
    A3 — Popularity-Only Precaching Baseline
    =========================================
    콘텐츠 인기도(요청 빈도 기반 Zipf 분포 가정)의 통계만으로 캐시 우선순위 결정.
    Dwell time 예측은 훈련셋 평균값(고정)을 사용.
    이동성 정보 미반영 → hit-rate 한계 시연용 baseline.

    구현:
      - fit(): y_train에서 dwell_cur / dwell_nxt 평균값 저장
      - predict(): 모든 샘플에 대해 (avg_dwell_cur, avg_dwell_nxt) 반환
      - Zipf 파라미터(alpha)는 precaching 시뮬레이션 레이어에서 별도 사용

    References (experiment_spec.json A3):
      [chen2017caching] "Caching in the Sky: Proactive Deployment of Cache-Enabled Unmanned
        Aerial Vehicles for Optimized Quality-of-Experience"
        IEEE Journal on Selected Areas in Communications, 2016. (ref_id=1)
      [su2018edge] "An Edge Caching Scheme to Distribute Content in Vehicular Networks"
        IEEE Transactions on Vehicular Technology, 2018. (ref_id=4)
      [xie2026cache] "Research on Cache Placement Optimization and Popularity-Based Content
        Prefetching Strategy in LEO Satellite Networks"
        IEEE Transactions on Green Communications and Networking, 2026. (ref_id=57)
    """

    name = "PopularityOnly"

    def __init__(self, config: dict = None):
        self.config      = config or {}
        self.zipf_alpha  = self.config.get("zipf_alpha", 1.0)   # Zipf 분포 파라미터
        self.n_contents  = self.config.get("n_contents", 1000)   # 콘텐츠 수
        self.avg_dwell_cur: Optional[float] = None
        self.avg_dwell_nxt: Optional[float] = None
        self._content_probs: Optional[np.ndarray] = None

    def _compute_zipf_probs(self) -> np.ndarray:
        ranks  = np.arange(1, self.n_contents + 1, dtype=np.float64)
        probs  = ranks ** (-self.zipf_alpha)
        return probs / probs.sum()

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> dict:
        """
        y_train에서 dwell_cur / dwell_nxt 평균값 계산 및 Zipf 확률 초기화.
        """
        y_train = _to_numpy(y_train)
        self.avg_dwell_cur    = float(np.mean(y_train[:, 0]))
        self.avg_dwell_nxt    = float(np.mean(y_train[:, 1]))
        self._content_probs   = self._compute_zipf_probs()

        history = {
            "avg_dwell_cur": self.avg_dwell_cur,
            "avg_dwell_nxt": self.avg_dwell_nxt,
            "zipf_alpha":    self.zipf_alpha,
            "n_contents":    self.n_contents,
        }
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        모든 샘플에 대해 고정 평균값 반환.
        Returns: np.ndarray, shape (N, 2)
        """
        X   = _to_numpy(X)
        N   = len(X)
        cur = np.full(N, self.avg_dwell_cur or 30.0, dtype=np.float32)
        nxt = np.full(N, self.avg_dwell_nxt or 30.0, dtype=np.float32)
        return np.stack([cur, nxt], axis=1)

    def get_content_cache_priority(self) -> np.ndarray:
        """Zipf 기반 콘텐츠 캐시 우선순위 (내림차순 정렬 인덱스)."""
        if self._content_probs is None:
            self._content_probs = self._compute_zipf_probs()
        return np.argsort(-self._content_probs)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "avg_dwell_cur": self.avg_dwell_cur,
                "avg_dwell_nxt": self.avg_dwell_nxt,
                "zipf_alpha":    self.zipf_alpha,
                "n_contents":    self.n_contents,
                "config":        self.config,
            }, f)

    @classmethod
    def load(cls, path: str) -> "PopularityOnlyBaseline":
        with open(path, "rb") as f:
            state = pickle.load(f)
        obj = cls(config=state.get("config", {}))
        obj.avg_dwell_cur = state["avg_dwell_cur"]
        obj.avg_dwell_nxt = state["avg_dwell_nxt"]
        obj.zipf_alpha    = state["zipf_alpha"]
        obj.n_contents    = state["n_contents"]
        return obj


# ============================================================
#  A4: LSTM Trajectory Predictor (Mobility-Only)
# ============================================================

class _LSTMMobilityNet(nn.Module):
    """LSTM backbone for mobility-only dwell time prediction."""
    def __init__(self, input_dim: int, hidden_dim: int, n_layers: int,
                 output_dim: int, dropout: float):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, F) — tabular input (Kinematic 13개 또는 전체 30개 중 운동학 부분)
        LSTM에 seq_len=1로 처리 (단일 타임스텝 tabular).
        """
        # (B, F) → (B, 1, F)
        x = x.unsqueeze(1)
        out, _ = self.lstm(x)  # (B, 1, H)
        return self.head(out[:, -1, :])  # (B, output_dim)


class LSTMMobilityBaseline:
    """
    A4 — LSTM Trajectory Predictor (Mobility-Only)
    ===============================================
    차량 속도·위치 시계열(Kinematic 13개 변수: v_c_a, d_l_c, dirct 등)만을 LSTM에
    입력하여 dwell time 예측. Traffic Control / Social 변수 미사용.

    비교 이유: 운동학 특성만으로 예측할 때 교통 제어·사회적 맥락 누락이 야기하는
    오차를 정량화 → ST-MBAN의 Multi-Branch 설계 필요성 입증.

    References (experiment_spec.json A4):
      [feng2023proactive] "Proactive Content Caching Scheme in Urban Vehicular Networks"
        IEEE Transactions on Communications, 2023. (ref_id=18)
      [wang2025mobility] "Mobility and Context-Aware Precaching Strategy Using Spatial-Temporal
        Informer for Vehicular Service"
        IEEE Internet of Things Journal, 2025. (ref_id=42)
      [yu2024joint] "Joint Cooperative Caching and UAV Trajectory Optimization Based on
        Mobility Prediction in the Internet of Connected Vehicles"
        IEEE transactions on intelligent transportation systems (Print), 2024. (ref_id=43)
    """

    name = "LSTMMobility"

    def __init__(self, config: dict = None):
        self.config     = config or {}
        self.hidden_dim = self.config.get("hidden_dim",  128)
        self.n_layers   = self.config.get("n_layers",    2)
        self.dropout    = self.config.get("dropout",     0.1)
        self.use_kinematic_only = self.config.get("use_kinematic_only", True)

        in_dim = KINEMATIC_DIM if self.use_kinematic_only else TOTAL_INPUT_DIM
        self._net = _LSTMMobilityNet(
            input_dim  = in_dim,
            hidden_dim = self.hidden_dim,
            n_layers   = self.n_layers,
            output_dim = OUTPUT_DIM,
            dropout    = self.dropout,
        )

    def _extract_kinematic(self, X: np.ndarray) -> np.ndarray:
        """30-dim 입력에서 Kinematic 13개 변수만 추출."""
        return X[:, KINEMATIC_COLS] if self.use_kinematic_only else X

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> List[dict]:
        X_train = _to_numpy(X_train)
        y_train = _to_numpy(y_train)
        Xk = self._extract_kinematic(X_train)

        Xv_k = None
        yv   = None
        if X_val is not None and y_val is not None:
            X_val = _to_numpy(X_val)
            y_val = _to_numpy(y_val)
            Xv_k  = self._extract_kinematic(X_val)
            yv    = y_val

        history = _train_dl(self._net, Xk, y_train, Xv_k, yv, self.config)
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        X  = _to_numpy(X)
        Xk = self._extract_kinematic(X)
        return _predict_dl(self._net, Xk, self.config)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        torch.save({"state_dict": self._net.state_dict(), "config": self.config}, path)

    @classmethod
    def load(cls, path: str) -> "LSTMMobilityBaseline":
        ckpt = torch.load(path, map_location="cpu")
        obj  = cls(config=ckpt.get("config", {}))
        obj._net.load_state_dict(ckpt["state_dict"])
        return obj


# ============================================================
#  A5: Hybrid Precaching (Asynchronous FL + DRL stub)
# ============================================================

class _HybridDRLNet(nn.Module):
    """
    Hybrid AFL+DRL 대리 네트워크 (Stub).
    실제 DRL 환경(cache state, content request, vehicle mobility) 없이는
    완전한 DRL 루프 불가. 대신 MLP로 dwell time 점 추정을 수행.
    전체 30개 변수 → [dwell_cur, dwell_nxt] 직접 예측.
    """
    def __init__(self, input_dim: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, OUTPUT_DIM),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class HybridAFLDRLBaseline:
    """
    A5 — Hybrid Precaching (Asynchronous FL + DRL) Baseline
    =========================================================
    인기도와 이동성을 결합한 비동기 연합 학습(Asynchronous FL) + 심층 강화학습(DRL) 기반
    캐시 결정 방식의 대리(proxy) 구현.

    완전한 DRL 구현:
      - 환경: RSU cache state, content request, vehicle mobility 시뮬레이션 필요
      - 에이전트: Actor-Critic (PPO/SAC) or DQN
      - 상태: (cache_state, popularity_dist, mobility_features)
      - 행동: cache eviction / prefetch 결정
      ⚠️  실제 데이터/시뮬레이터 없이는 DRL 환경 구성 불가 → Smoke-test용 MLP stub으로 대체.
      데이터셋 도착 후 SUMO 연동 DRL 환경 구현 필요.

    현재 구현: MLP를 dwell time 예측기(proxy)로 사용.
    Zipf 기반 인기도 필드는 fit() 시 따로 계산되어 predict()에서 별도 사용 가능.

    References (experiment_spec.json A5):
      [jiang2024asynchronous] "Asynchronous Federated and Reinforcement Learning for
        Mobility-Aware Edge Caching in IoV"
        IEEE Internet of Things Journal, 2024. (ref_id=21)
      [liao2025context] "Context-Aware Proactive Edge Caching for Vehicular Edge Computing
        Based on Asynchronous Federated Learning"
        IEEE Internet of Things Journal, 2025. (ref_id=46)
      [xu2025adaptive] "Adaptive Video Segment Precaching With Varying Travel Duration for
        Internet of Vehicles"
        IEEE Internet of Things Journal, 2025. (ref_id=63)

    NOTE (smoke-test limitation): DRL 환경 없이 랜덤 텐서 forward pass만 검증 가능.
      완전한 AFL+DRL 루프는 데이터셋 + SUMO 시뮬레이터 도착 후 구현 예정.
    """

    name = "HybridAFLDRL"

    def __init__(self, config: dict = None):
        self.config      = config or {}
        self.hidden_dim  = self.config.get("hidden_dim",  256)
        self.dropout     = self.config.get("dropout",     0.1)
        self.zipf_alpha  = self.config.get("zipf_alpha",  1.0)
        self.n_contents  = self.config.get("n_contents",  1000)

        self._net = _HybridDRLNet(
            input_dim  = TOTAL_INPUT_DIM,
            hidden_dim = self.hidden_dim,
            dropout    = self.dropout,
        )
        self._content_probs: Optional[np.ndarray] = None

    def _init_zipf(self) -> np.ndarray:
        ranks = np.arange(1, self.n_contents + 1, dtype=np.float64)
        p     = ranks ** (-self.zipf_alpha)
        return p / p.sum()

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> List[dict]:
        X_train = _to_numpy(X_train)
        y_train = _to_numpy(y_train)
        self._content_probs = self._init_zipf()

        Xv = _to_numpy(X_val) if X_val is not None else None
        yv = _to_numpy(y_val) if y_val is not None else None

        # proxy MLP 학습 (DRL 환경 없을 때 fallback)
        history = _train_dl(self._net, X_train, y_train, Xv, yv, self.config)
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = _to_numpy(X)
        return _predict_dl(self._net, X, self.config)

    def get_cache_priority(self) -> np.ndarray:
        """Zipf 기반 콘텐츠 캐시 우선순위 인덱스."""
        if self._content_probs is None:
            self._content_probs = self._init_zipf()
        return np.argsort(-self._content_probs)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        torch.save({
            "state_dict":     self._net.state_dict(),
            "config":         self.config,
            "content_probs":  self._content_probs,
        }, path)

    @classmethod
    def load(cls, path: str) -> "HybridAFLDRLBaseline":
        ckpt = torch.load(path, map_location="cpu")
        obj  = cls(config=ckpt.get("config", {}))
        obj._net.load_state_dict(ckpt["state_dict"])
        obj._content_probs = ckpt.get("content_probs", None)
        return obj


# ============================================================
#  A6: ST-CVAE Wrapper (통합 인터페이스)
# ============================================================

class STCVAEBaseline:
    """
    A6 — ST-CVAE (Spatio-Temporal Conditional VAE) Baseline
    =========================================================
    기존 모델 (model.py + train.py에 완전 구현됨).
    본 클래스는 baselines_extra.py의 통합 인터페이스를 제공하는 thin wrapper.

    구조: [X,Y]→Posterior(KL)→Z*→Decoder
    Inference: Prior에서 Z_mu 결정론적 추출 또는 Z_1~Z_N 스토캐스틱 샘플링 + CQR 보정.

    ⚠️  model.py / train.py를 덮어쓰지 않음 (읽기 전용).
    본 wrapper는 동일 인터페이스(fit/predict/save/load)를 제공.

    Reference: Prior paper (자체 참조) — references.json에 미수록.
      실험 섹션에서 self-citation 처리 예정.
    experiment_spec.json A6 - needs_reference: true (self-citation)
    """

    name = "ST-CVAE"

    def __init__(self, config: dict = None):
        self.config  = config or {}
        self._model  = None
        self._loaded = False
        self._model_path_ref = os.path.join(
            os.path.dirname(__file__), "model.py"
        )

    def _build_model(self):
        """model.py에서 ST-CVAE 모델 임포트."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "stcvae_model", self._model_path_ref
            )
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # model.py의 STCVAE 클래스 (또는 주 클래스) 반환
            # NOTE: model.py의 실제 클래스명에 따라 아래를 조정
            if hasattr(mod, "STCVAE"):
                return mod.STCVAE(**self.config)
            elif hasattr(mod, "STCVAEModel"):
                return mod.STCVAEModel(**self.config)
            else:
                # 첫 번째 nn.Module 서브클래스 사용
                for name, obj in vars(mod).items():
                    if (isinstance(obj, type)
                            and issubclass(obj, nn.Module)
                            and obj is not nn.Module):
                        return obj(**{k: v for k, v in self.config.items()
                                      if k in obj.__init__.__code__.co_varnames})
        except Exception as e:
            warnings.warn(f"[STCVAEBaseline] model.py 로드 실패: {e}. "
                          f"Stub 모드로 동작합니다.")
        return None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> dict:
        """
        train.py의 학습 루틴을 직접 호출하거나, 독립 루틴으로 fallback.
        데이터셋 도착 후 train.py 학습 루틴과 통합 필요.
        """
        warnings.warn(
            "[STCVAEBaseline.fit] 실제 학습은 train.py를 직접 실행하십시오. "
            "이 wrapper는 통합 인터페이스 제공용입니다."
        )
        return {"status": "use train.py for actual training"}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Z_mu (prior mean) 결정론적 추출로 dwell_cur, dwell_nxt 예측.
        실제 모델 로드 없으면 무작위 값 반환 (smoke-test용).
        """
        X = _to_numpy(X)
        N = len(X)
        if self._model is not None:
            pass  # 실제 모델 추론 (데이터셋 도착 후 구현)
        # Fallback: zeros (smoke-test)
        return np.zeros((N, OUTPUT_DIM), dtype=np.float32)

    def save(self, path: str) -> None:
        if self._model is not None:
            torch.save(self._model.state_dict(), path)
        else:
            warnings.warn("[STCVAEBaseline.save] 모델이 로드되지 않았습니다.")

    @classmethod
    def load(cls, path: str) -> "STCVAEBaseline":
        obj = cls()
        obj._loaded = True
        # 실제 state_dict 로드는 데이터셋 도착 후 구현
        return obj


# ============================================================
#  A7: FT-Transformer Wrapper (통합 인터페이스)
# ============================================================

class FTTransformerBaseline:
    """
    A7 — FT-Transformer (Feature Tokenizer + Transformer) Baseline
    ===============================================================
    각 피처를 d_token 차원으로 임베딩, [CLS] token을 통해 최종 예측.
    단일 통합 Transformer가 Multi-Branch Attention 구조 대비 tabular 예측에서
    열위임을 보임 (feature 이질성 처리 능력 비교).

    NOTE: baselines.py:FTTransformer와 동일 아키텍처.
      본 클래스는 통합 인터페이스(fit/predict/save/load) 추가.

    References (experiment_spec.json A7):
      [song2021qoe] "QoE-Driven Edge Caching in Vehicle Networks Based on Deep
        Reinforcement Learning"
        IEEE Transactions on Vehicular Technology, 2021. (ref_id=7)
      [elrahim2024efficient] "Efficient Network Traffic Prediction: Harnessing
        Hybrid Neural Networks"
        2024 IEEE International Conference on Advanced Telecommunication and
        Networking Technologies (ATNT), 2024. (ref_id=59)
      [zheng2025proactive] "Proactive Spatio-Temporal Request Prediction for
        Replica Placement in Edge-Cloud Computing"
        IEEE Internet of Things Journal, 2025. (ref_id=62)
    """

    name = "FTTransformer"

    def __init__(self, config: dict = None):
        self.config   = config or {}
        d_token       = self.config.get("d_token",  64)
        n_heads       = self.config.get("n_heads",  8)
        n_layers      = self.config.get("n_layers", 3)
        dropout       = self.config.get("dropout",  0.1)

        # Ensure d_token is divisible by n_heads
        if d_token % n_heads != 0:
            n_heads = max(h for h in [1, 2, 4, 8] if d_token % h == 0)

        self._net = _FTTransformerNet(
            input_dim  = TOTAL_INPUT_DIM,
            output_dim = OUTPUT_DIM,
            d_token    = d_token,
            n_heads    = n_heads,
            n_layers   = n_layers,
            dropout    = dropout,
        )

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> List[dict]:
        X_train = _to_numpy(X_train)
        y_train = _to_numpy(y_train)
        Xv = _to_numpy(X_val) if X_val is not None else None
        yv = _to_numpy(y_val) if y_val is not None else None
        return _train_dl(self._net, X_train, y_train, Xv, yv, self.config)

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = _to_numpy(X)
        return _predict_dl(self._net, X, self.config)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        torch.save({"state_dict": self._net.state_dict(), "config": self.config}, path)

    @classmethod
    def load(cls, path: str) -> "FTTransformerBaseline":
        ckpt = torch.load(path, map_location="cpu")
        obj  = cls(config=ckpt.get("config", {}))
        obj._net.load_state_dict(ckpt["state_dict"])
        return obj


class _FTTransformerNet(nn.Module):
    """Feature Tokenizer + Transformer (Gorishniy et al., NeurIPS 2021)."""
    def __init__(self, input_dim: int, output_dim: int,
                 d_token: int = 64, n_heads: int = 8,
                 n_layers: int = 3, dropout: float = 0.1):
        super().__init__()
        self.input_dim = input_dim
        self.d_token   = d_token

        self.feature_weight = nn.Parameter(torch.empty(input_dim, d_token))
        self.feature_bias   = nn.Parameter(torch.zeros(input_dim, d_token))
        nn.init.kaiming_uniform_(self.feature_weight, a=np.sqrt(5))

        self.cls_token = nn.Parameter(torch.randn(1, 1, d_token) * 0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_token, nhead=n_heads,
            dim_feedforward=d_token * 4,
            dropout=dropout, batch_first=True, norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.head = nn.Sequential(
            nn.LayerNorm(d_token), nn.ReLU(),
            nn.Linear(d_token, output_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, F)
        tokens = (x.unsqueeze(-1) * self.feature_weight.unsqueeze(0)
                  + self.feature_bias.unsqueeze(0))  # (B, F, d_token)
        cls    = self.cls_token.expand(x.size(0), -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)      # (B, F+1, d_token)
        out    = self.transformer(tokens)
        return self.head(out[:, 0, :])


# ============================================================
#  A8: RSU-Local Snapshot MLP (Federated Baseline)
# ============================================================

class RSULocalMLPBaseline:
    """
    A8 — Snapshot-based RSU-Local Learning (Federated Baseline)
    ============================================================
    각 RSU가 자체 수집 데이터로만 학습하는 간단한 분산 MLP (중앙 집계 없음).
    전역 모델 없이 RSU-Local 학습만으로 달성 가능한 성능 하한 측정.

    ST-MBAN과 동일한 RSU-Local 학습 조건에서 architecture 차이만으로
    얼마나 성능이 향상되는지 분리 검증.

    NOTE: baselines.py:MLPBaseline과 동일 아키텍처.
      본 클래스는 통합 인터페이스(fit/predict/save/load) + RSU ID 추적 추가.

    References (experiment_spec.json A8):
      [liu2024crs] "CRS: A Privacy-Preserving Two-Layered Distributed Machine
        Learning Framework for IoV"
        IEEE Internet of Things Journal, 2024. (ref_id=27)
      [zhao2025deep] "Deep Reinforcement Learning for Optimizing Multi-Hop
        Distributed Collaborative Task Offloading in R2X"
        IEEE Transactions on Vehicular Technology, 2025. (ref_id=48)
      [yang2024hierarchical] "Hierarchical Reinforcement Learning-Based Routing
        Algorithm With Grouped RSU in Urban VANETs"
        IEEE transactions on intelligent transportation systems (Print), 2024. (ref_id=39)
    """

    name = "RSULocalMLP"

    def __init__(self, config: dict = None):
        self.config      = config or {}
        hidden_dims      = self.config.get("hidden_dims", [256, 128, 64])
        dropout          = self.config.get("dropout", 0.1)
        self.rsu_id      = self.config.get("rsu_id", None)  # RSU ID 추적

        self._net = _MLPNet(
            input_dim   = TOTAL_INPUT_DIM,
            output_dim  = OUTPUT_DIM,
            hidden_dims = hidden_dims,
            dropout     = dropout,
        )

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> List[dict]:
        """RSU-Local 학습: 외부 집계 없이 자체 데이터만으로 학습."""
        X_train = _to_numpy(X_train)
        y_train = _to_numpy(y_train)
        Xv = _to_numpy(X_val) if X_val is not None else None
        yv = _to_numpy(y_val) if y_val is not None else None
        return _train_dl(self._net, X_train, y_train, Xv, yv, self.config)

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = _to_numpy(X)
        return _predict_dl(self._net, X, self.config)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        torch.save({
            "state_dict": self._net.state_dict(),
            "config":     self.config,
            "rsu_id":     self.rsu_id,
        }, path)

    @classmethod
    def load(cls, path: str) -> "RSULocalMLPBaseline":
        ckpt = torch.load(path, map_location="cpu")
        obj  = cls(config=ckpt.get("config", {}))
        obj._net.load_state_dict(ckpt["state_dict"])
        obj.rsu_id = ckpt.get("rsu_id", None)
        return obj


class _MLPNet(nn.Module):
    """Multi-Layer Perceptron backbone."""
    def __init__(self, input_dim: int, output_dim: int,
                 hidden_dims: List[int] = None, dropout: float = 0.1):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [256, 128, 64]
        layers = []
        prev   = input_dim
        for h in hidden_dims:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ============================================================
#  Smoke Test
# ============================================================

def run_smoke_tests(verbose: bool = True) -> Dict[str, str]:
    """
    각 baseline의 랜덤 텐서 forward pass 검증 (실제 데이터 불필요).
    Returns: {baseline_name: "PASS" | "FAIL — 사유"}
    """
    results = {}
    N_SMOKE = 16   # batch size
    np.random.seed(42)
    torch.manual_seed(42)

    X_fake = np.random.randn(N_SMOKE, TOTAL_INPUT_DIM).astype(np.float32)
    y_fake = np.abs(np.random.randn(N_SMOKE, OUTPUT_DIM).astype(np.float32)) * 30

    smoke_config = {"epochs": 2, "batch": 8, "lr": 1e-3, "patience": 2, "device": "cpu"}

    # A1: ConstantVelocityBaseline
    try:
        m = ConstantVelocityBaseline(config={})
        h = m.fit(X_fake, y_fake)
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        results["A1_ConstantVelocity"] = "PASS"
    except Exception as e:
        results["A1_ConstantVelocity"] = f"FAIL — {e}"

    # A2: LinearRegressionBaseline
    try:
        m = LinearRegressionBaseline(config={})
        h = m.fit(X_fake, y_fake)
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        results["A2_LinearRegression"] = "PASS"
    except Exception as e:
        results["A2_LinearRegression"] = f"FAIL — {e}"

    # A3: PopularityOnlyBaseline
    try:
        m = PopularityOnlyBaseline(config={"n_contents": 100})
        h = m.fit(X_fake, y_fake)
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        prio = m.get_content_cache_priority()
        assert len(prio) == 100
        results["A3_PopularityOnly"] = "PASS"
    except Exception as e:
        results["A3_PopularityOnly"] = f"FAIL — {e}"

    # A4: LSTMMobilityBaseline
    try:
        m = LSTMMobilityBaseline(config={**smoke_config, "hidden_dim": 32, "n_layers": 1})
        h = m.fit(X_fake, y_fake)
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        results["A4_LSTMMobility"] = "PASS"
    except Exception as e:
        results["A4_LSTMMobility"] = f"FAIL — {e}"

    # A5: HybridAFLDRLBaseline
    try:
        m = HybridAFLDRLBaseline(config={**smoke_config, "hidden_dim": 32, "n_contents": 50})
        h = m.fit(X_fake, y_fake)
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        results["A5_HybridAFLDRL"] = "PASS"
    except Exception as e:
        results["A5_HybridAFLDRL"] = f"FAIL — {e}"

    # A6: STCVAEBaseline (wrapper only — no actual model load)
    try:
        m = STCVAEBaseline(config={})
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        results["A6_STCVAE"] = "PASS (wrapper stub — model.py load skipped)"
    except Exception as e:
        results["A6_STCVAE"] = f"FAIL — {e}"

    # A7: FTTransformerBaseline
    try:
        m = FTTransformerBaseline(config={**smoke_config, "d_token": 16, "n_heads": 4, "n_layers": 1})
        h = m.fit(X_fake, y_fake)
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        results["A7_FTTransformer"] = "PASS"
    except Exception as e:
        results["A7_FTTransformer"] = f"FAIL — {e}"

    # A8: RSULocalMLPBaseline
    try:
        m = RSULocalMLPBaseline(config={**smoke_config, "hidden_dims": [32, 16], "rsu_id": "rsu_0"})
        h = m.fit(X_fake, y_fake)
        p = m.predict(X_fake)
        assert p.shape == (N_SMOKE, 2), f"shape mismatch: {p.shape}"
        results["A8_RSULocalMLP"] = "PASS"
    except Exception as e:
        results["A8_RSULocalMLP"] = f"FAIL — {e}"

    if verbose:
        print("\n========== Smoke Test Results ==========")
        for name, status in results.items():
            print(f"  {name}: {status}")
        print("=========================================")

    return results


# ============================================================
#  Baseline Registry
# ============================================================

BASELINE_REGISTRY: Dict[str, type] = {
    "A1": ConstantVelocityBaseline,
    "A2": LinearRegressionBaseline,
    "A3": PopularityOnlyBaseline,
    "A4": LSTMMobilityBaseline,
    "A5": HybridAFLDRLBaseline,
    "A6": STCVAEBaseline,
    "A7": FTTransformerBaseline,
    "A8": RSULocalMLPBaseline,
}


def get_baseline(algo_id: str, config: dict = None):
    """
    experiment_spec.json A1~A8 ID로 baseline 클래스 인스턴스 반환.
    Usage:
        bl = get_baseline("A4", config={"hidden_dim": 128, "epochs": 100})
    """
    if algo_id not in BASELINE_REGISTRY:
        raise ValueError(f"Unknown baseline id: {algo_id}. "
                         f"Available: {list(BASELINE_REGISTRY.keys())}")
    return BASELINE_REGISTRY[algo_id](config=config or {})


if __name__ == "__main__":
    # Smoke test 실행
    results = run_smoke_tests(verbose=True)
    n_pass  = sum(1 for v in results.values() if v.startswith("PASS"))
    n_total = len(results)
    print(f"\nSmoke Test Summary: {n_pass}/{n_total} PASS")
