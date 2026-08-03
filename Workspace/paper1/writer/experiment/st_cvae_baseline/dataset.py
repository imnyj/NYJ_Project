"""
Dataset loader for ST-CVAE baseline.
Loads RSU CSV files, handles preprocessing and train/val/test split.
"""
import os
import glob
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from sklearn.preprocessing import StandardScaler
import pickle

FEATURE_COLS = [
    # --- Kinematic Branch (K) --- K_DIM = 13
    'r_cov',               # RSU 통신범위
    'dirct',               # 차량 방향 (-1: next RSU 방향, +1: 반대)
    'd_l_c',               # 현재 RSU 통신 경계까지 잔여 거리
    'd_e_n',               # 다음 RSU 통신범위 진입까지 거리
    'd_l_n',               # 다음 RSU 통신범위 이탈 경계까지 거리
    'd_rsu',               # 현재-다음 RSU 간 물리적 거리
    'v_c_a', 'v_n_a',      # 현재/다음 RSU 통신범위 평균 속도
    'v_ahead_avg',         # 동일 차선 전방 차량 평균 속도
    'dist_leader',         # 선행 차량까지 거리
    'v_leader',            # 선행 차량 속도
    'est_travel_time',     # SUMO 기반 현재 edge 예상 통과 시간
    'route_lane_changes',  # next RSU 도달까지 필요 차선 변경 횟수
    # --- Traffic Control Branch (T) --- T_DIM_RAW = 6
    'tls_c', 'tls_n',      # 현재/다음 RSU 신호등 상태
    'tlt_c', 'tlt_n',      # 현재/다음 RSU 신호 변경까지 대기 시간
    'q_len_cur', 'q_len_nxt',  # 현재/다음 교차로 정지 차량 수
    # --- Social Branch (S) --- S_DIM = 11
    'n_t_0', 'n_t_1', 'n_t_2', 'n_t_3',  # 4방향에서 next RSU로 향하는 차량 수
    'n_cur', 'n_nxt',      # 현재/다음 RSU 통신범위 내 총 차량 수
    'n_ahead_cur',         # 동일 차선 전방 차량 수 (현재 RSU)
    'n_ahead_nxt',         # 동일 차선 전방에서 next RSU로 향하는 차량 수
    'occ_cur', 'occ_nxt',  # 현재/다음 RSU 차선 점유율 [0,1]
    'n_merge_nxt',         # next RSU로 합류 예정 인접 RSU 차량 수
]
TARGET_COLS = ['dwell_cur', 'dwell_nxt']

INF_CLIP = 5000.0  # float('inf') 대체값


def load_and_merge_csvs(data_dir: str) -> pd.DataFrame:
    """data_dir 내 모든 rsu_*.csv 파일을 합산하여 반환."""
    pattern = os.path.join(data_dir, "rsu_*.csv")
    files = glob.glob(pattern)
    if not files:
        # fallback: 모든 csv
        files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    dfs = []
    for f in sorted(files):
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"[Warning] Skipping {f}: {e}")
    return pd.concat(dfs, ignore_index=True)


def preprocess(df: pd.DataFrame, feature_cols=None, target_cols=None):
    """
    - inf/NaN 처리
    - 존재하는 컬럼만 사용
    """
    if feature_cols is None:
        feature_cols = FEATURE_COLS
    if target_cols is None:
        target_cols = TARGET_COLS

    # 존재하는 컬럼만 필터링
    feat_avail = [c for c in feature_cols if c in df.columns]
    tgt_avail  = [c for c in target_cols  if c in df.columns]
    missing_feat = set(feature_cols) - set(feat_avail)
    missing_tgt  = set(target_cols)  - set(tgt_avail)
    if missing_feat:
        print(f"[Warning] Missing feature columns: {missing_feat}")
    if missing_tgt:
        print(f"[Warning] Missing target columns: {missing_tgt}")

    df = df[feat_avail + tgt_avail].copy()

    # inf → clip
    df.replace([np.inf, -np.inf], INF_CLIP, inplace=True)

    # NaN → drop
    df.dropna(inplace=True)

    # 음수 target 제거 (물리적으로 불가)
    for col in tgt_avail:
        df = df[df[col] >= 0]

    return df, feat_avail, tgt_avail


class SumoDataset(Dataset):
    """
    ST-CVAE 학습용 Dataset.
    split: 'train' | 'val' | 'test'
    scaler_dir: scaler를 저장/로드할 경로 (None이면 저장 안 함)
    """
    def __init__(
        self,
        data_dir: str,
        split: str = 'train',
        feature_cols=None,
        target_cols=None,
        seed: int = 42,
        scaler_dir: str = None,
    ):
        self.feature_cols = feature_cols or FEATURE_COLS
        self.target_cols  = target_cols  or TARGET_COLS

        df_raw = load_and_merge_csvs(data_dir)
        df, feat_avail, tgt_avail = preprocess(df_raw, self.feature_cols, self.target_cols)
        self.feature_cols = feat_avail
        self.target_cols  = tgt_avail

        # Split 70/15/15 — 시간순 유지 (시뮬 데이터의 시간적 자기상관 방지)
        # RSU CSV는 시뮬레이션 진행 순서대로 기록되므로 shuffle 없이 분할
        n = len(df)
        i_train = int(n * 0.70)
        i_val   = int(n * 0.85)

        splits = {'train': df.iloc[:i_train],
                  'val':   df.iloc[i_train:i_val],
                  'test':  df.iloc[i_val:]}
        subset = splits[split]

        X_raw = subset[feat_avail].values.astype(np.float32)
        Y_raw = subset[tgt_avail].values.astype(np.float32)

        # Scaler: train에서 fit, 나머지는 load
        if scaler_dir:
            os.makedirs(scaler_dir, exist_ok=True)
            feat_path = os.path.join(scaler_dir, 'feat_scaler.pkl')
            tgt_path  = os.path.join(scaler_dir, 'tgt_scaler.pkl')

        if split == 'train':
            self.feat_scaler = StandardScaler()
            self.tgt_scaler  = StandardScaler()
            X_raw = self.feat_scaler.fit_transform(X_raw)
            Y_raw = self.tgt_scaler.fit_transform(Y_raw)
            if scaler_dir:
                with open(feat_path, 'wb') as f: pickle.dump(self.feat_scaler, f)
                with open(tgt_path,  'wb') as f: pickle.dump(self.tgt_scaler,  f)
        else:
            if scaler_dir and os.path.exists(feat_path):
                with open(feat_path, 'rb') as f: self.feat_scaler = pickle.load(f)
                with open(tgt_path,  'rb') as f: self.tgt_scaler  = pickle.load(f)
                X_raw = self.feat_scaler.transform(X_raw)
                Y_raw = self.tgt_scaler.transform(Y_raw)
            else:
                # scaler 없으면 그냥 사용
                self.feat_scaler = None
                self.tgt_scaler  = None

        self.X = torch.from_numpy(X_raw)
        self.Y = torch.from_numpy(Y_raw)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.Y[idx]

    @property
    def input_dim(self):
        return self.X.shape[1]

    @property
    def target_dim(self):
        return self.Y.shape[1]
