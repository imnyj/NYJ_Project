# ST-CVAE Baseline

ST-MBAN 성능 비교를 위한 ST-CVAE 베이스라인 (PyTorch 구현)

## 구조 요약

```
[Training]
  Posterior: [X, Y] → Linear → ResBlock×2 → LayerNorm → mu_psi, log_sigma_psi → Z*
  Decoder:   [X, Z*] → Linear → ResBlock×3 → Linear → Y_hat
  Loss: Huber(Y_hat, Y) + beta * KL(posterior || prior)

[Inference]
  Prior:   [X] → Linear → ResBlock×2 → LayerNorm → mu_phi
  Decoder: [X, mu_phi] → Y_hat  (deterministic)
```

## 입력/출력

- **입력 변수 (17개):** r_cov, dirct, d_n_c, n_t_0~3, d_t_c, d_t_n, v_c_a, v_n_a, tls_c, tls_n, tlt_c, tlt_n, n_cur, n_nxt
- **출력 변수 (2개):** dwell_cur, dwell_nxt

## 학습 실행

```bash
cd /home/nyj/ST-MBAN/시뮬/st_cvae_baseline

python train.py \
  --data_dir /home/nyj/ST-MBAN/시뮬/데이터셋 \
  --hidden 128 \
  --latent 32 \
  --epochs 100 \
  --lr 1e-3 \
  --batch 256 \
  --warmup 50 \
  --device cpu
```

## 하이퍼파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `--hidden` | 128 | Hidden layer 차원 |
| `--latent` | 32 | Latent space 차원 |
| `--epochs` | 100 | 학습 에포크 수 |
| `--lr` | 1e-3 | 초기 학습률 (ReduceLROnPlateau 스케줄러) |
| `--batch` | 256 | 배치 크기 |
| `--warmup` | 50 | KL annealing warmup 에포크 수 |
| `--device` | cpu | cuda / cpu |

## KL Annealing

`beta = min(epoch / warmup, 1.0)`

초반 학습에서 KL Collapse를 방지하기 위해 beta를 0에서 1로 선형 증가.

## 산출물

```
results/
├── st_cvae_best.pt     # 최적 모델 체크포인트 (val_recon 기준)
├── training_log.csv    # epoch별 train/val loss 로그
└── scalers/
    ├── feat_scaler.pkl # Feature StandardScaler
    └── tgt_scaler.pkl  # Target StandardScaler
```

## 의존성

```
torch >= 1.12
scikit-learn
pandas
numpy
```

## 비고

- 데이터셋이 없으면 먼저 `dataset_scenario.py` 시뮬레이션 실행 필요
- `float('inf')` 값은 자동으로 5000.0으로 클리핑
- Train/Val/Test = 70/15/15 split (seed=42 고정)
