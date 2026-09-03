# Phase 6 ML & Models 아키텍처 정밀 조사 및 설계 명세서 (survey_models.md)

- **문서 식별자**: `Auto_Stock/Phase6/Survey_Models/R1`
- **작성자**: Phase 6 ML & Models Explorer (`teamwork_preview_explorer_p6_1`)
- **작성 일시**: 2026-09-03
- **대상 모듈**: `modules/models/` (`feature_extractor.py`, `hybrid_policy.py`), `modules/engine/`, `modules/hpo/`

---

## 1. 개요 및 요구사항 정의 (Phase 6 R1)

Auto_Stock 프로젝트의 Phase 6 요구사항 R1은 기존 구축된 하이브리드 RL 환경 위에서 다중 시계열 데이터를 처리할 수 있는 3가지 이상의 상이한 지도학습(SL) 아키텍처를 특징 추출기(Feature Extractor)로 설계 및 구현하는 것을 명시하고 있습니다.

### 1.1 핵심 요구사항
1. **아키텍처 다양성**:
   - 1D-CNN 기반 ResNet (Residual Time-Series Network)
   - 시계열 Attention 기반 Transformer (Temporal Self-Attention Network)
   - 잠재 공간 이상치 탐지 기반 CVAE (Conditional Variational Autoencoder)
2. **다중 타임프레임(Multi-Timeframe) 입력 일관성**:
   - 일봉(Daily) 시계열과 분봉(Intraday/Minute) 시계열, 그리고 펀더멘털/계좌(Tabular) 상태 벡터를 동시에 수용할 수 있는 동일한 텐서 인터페이스 구축.
3. **출력 규격 표준화**:
   - 하류 강화학습(RL) 정책망 결합을 위한 특징 표현 벡터 (`features`, 기본 64차원)
   - 멀티태스크 지도학습(SL) 사전학습을 위한 예측 타겟 (기대 수익률 `pred_return`, 추세 분류 로짓 `pred_direction`)
   - 잠재 공간 기반 상태 모니터링을 위한 이상치 신호 (CVAE 잠재 벡터 `mu`, 재건 오차 `anomaly_score`)
4. **기존 시스템과의 100% 하위 호환성**:
   - `SLPretrainer`, `HybridActorCritic`, `HybridPPO`, `SB3CustomFeaturesExtractor`, `HybridTradingEnv`와의 무결절 연동.

---

## 2. 기존 모델 아키텍처 및 텐서 구조 분석

### 2.1 기존 소스 코드 구조 (`modules/models/`)

#### 1) `TabularMLPFeatureExtractor` (`feature_extractor.py:48-182`)
- **입력 Shape**: `(Batch, input_dim)` 또는 unbatched `(input_dim,)`
  - 현재 단일 관측 벡터(시장 10차원 + 계좌 4차원 = 14차원) 처리용으로 사용됨.
- **내부 구조**:
  - `hidden_dims`: 기본 `[128, 64]`
  - `Linear -> LayerNorm -> Activation(GELU/ReLU) -> Dropout` 레이어 스택
  - 가중치 직교 초기화 (`nn.init.orthogonal_`, gain=sqrt(2))
  - `torch.nan_to_num(x, nan=0.0, posinf=1.0, neginf=-1.0)` 안전 방어 내장.
  - 선택적 잔차 연결(`use_residual=True` 시 `res_proj`를 통한 입력-출력 가산).
- **출력 Shape**: `(Batch, output_dim)` (기본 64차원)

#### 2) `Temporal1DCNNFeatureExtractor` (`feature_extractor.py:185-335`)
- **입력 Shape**:
  - Batched 3D: `(Batch, seq_len, in_channels)` 또는 `(Batch, in_channels, seq_len)` (내부 자동 전치)
  - 2D: `(Batch, in_channels)` (단일 시점) 또는 unbatched `(seq_len, in_channels)`
  - 기준 파라미터: `in_channels=10`, `seq_len=20`
- **내부 구조**:
  - 순차적 1D 합성곱 블록: `[Conv1d -> GroupNorm/BatchNorm1d -> ReLU -> Dropout] * L`
  - 풀링 계층: `AdaptiveAvgPool1d(1)` 또는 `AdaptiveMaxPool1d(1)` 또는 `flatten`
  - 선형 투영: `Linear(prev_c, output_dim) -> LayerNorm -> ReLU`
- **한계점**:
  - 단순 순차 1D-CNN 구조로, 잔차 연결(Skip Connection)이 없어 층을 깊게 쌓을 경우 기울기 소실 발생.
  - 단일 시계열(예: 일봉 20스텝)만 입력받을 수 있어 다중 타임프레임(일봉 + 분봉 동시 수용)을 지원하지 못함.
  - 고정된 합성곱 수용 영역(Receptive Field)으로 인해 장기 의존성 포착 한계.

#### 3) `DualStreamSLFeatureExtractor` (`feature_extractor.py:337-542`)
- **입력 인터페이스**:
  - `temporal_x`: `(Batch, seq_len, in_channels)`
  - `tabular_x`: `(Batch, tabular_dim)`
  - 통합 `x`: Dict `{"temporal": ..., "tabular": ...}`, Tuple `(temporal_x, tabular_x)`, 또는 Flat Tensor `(Batch, in_channels + tabular_dim)`
- **내부 구조**:
  - Temporal Stream (`Temporal1DCNNFeatureExtractor`, 출력 64차원)
  - Tabular Stream (`TabularMLPFeatureExtractor`, 출력 32차원)
  - Fusion MLP: `Concat([feat_temp, feat_tab])` (96차원) -> `Linear(96, fusion_dim=128) -> LayerNorm -> ReLU -> Linear(128, output_dim=64) -> LayerNorm -> ReLU`
- **출력 Shape**: `(Batch, output_dim)` (64차원)

#### 4) `SLPretrainer` (`feature_extractor.py:544-877`)
- **기능**: 지도학습 사전학습 및 다중 목적 최적화
- **헤드 구조**:
  - `return_head`: `Linear(feature_dim, 32) -> ReLU -> Linear(32, 1)` (수익률 회귀)
  - `direction_head`: `Linear(feature_dim, 32) -> ReLU -> Linear(32, num_classes=3)` (방향성 분류 로짓)
- **손실 함수**:
  - 회귀 손실: `SmoothL1Loss` 또는 `MSELoss`
  - 분류 손실: `CrossEntropyLoss`
  - 종합 손실: $\mathcal{L} = \lambda_{reg} \mathcal{L}_{reg} + \lambda_{cls} \mathcal{L}_{cls}$
- **인터페이스**: `train_step()`, `fit()`, `evaluate()`, `save_pretrained()`, `load_pretrained()`, `get_backbone()`

#### 5) `HybridActorCritic` (`hybrid_policy.py:45-330`)
- **백본 연동**: `self.feature_extractor`에 `DualStreamSLFeatureExtractor` 또는 커스텀 모듈 주입 가능.
- **출력 구성**:
  - `disc_logits`: `(Batch, 3)` (0: HOLD, 1: BUY, 2: SELL)
  - `p1, p2`: Beta 분포 파라미터 $(\alpha, \beta)$ 또는 Gaussian $(\mu, \sigma)$
  - `value`: `(Batch, 1)` 상태 가치 $V(s)$
- **전이 학습 인터페이스**: `load_from_sl_pretrainer(pretrainer, freeze=True/False)`를 통해 SL 백본을 RL 정책망으로 즉각 전이 지원.

---

## 3. 다중 타임프레임 (Multi-Timeframe) 텐서 입력/출력 인터페이스 표준화

### 3.1 텐서 정의 및 차원 규격

주식 가격 형성 메커니즘은 장기 거시 추세(일봉)와 단기 미시 모멘텀(분봉)의 복합적 상호작용으로 이루어집니다. 따라서 Phase 6의 모든 신규 아키텍처는 아래의 표준화된 입력을 처리할 수 있어야 합니다.

| 텐서 명칭 | 파라미터명 | 표준 Shape | 설명 및 대표 피처 구성 |
|---|---|---|---|
| **일봉 시계열** | `daily_x` | `(Batch, T_day, C_day)` | `T_day=20` (20거래일), `C_day=10`<br>[시가변화율, 고가변화율, 저가변화율, 종가변화율, 거래량정규화, 변동성(20d), MA5이격도, MA20이격도, MA60이격도, 로그수익률] |
| **분봉 시계열** | `minute_x` | `(Batch, T_min, C_min)` | `T_min=60` (최근 60분/틱 집계), `C_min=10`<br>[분봉수익률, 고저변동폭, 거래량급증률, 체결강도, 호가스프레드, 단기MA이격도 등] |
| **정적/계좌 피처**| `tabular_x` | `(Batch, D_tab)` | `D_tab=4` (계좌 상태) 또는 `7` (펀더멘털 포함)<br>[cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress] + [dynamic_per, dynamic_pbr, dynamic_market_cap] |

### 3.2 다중 입력 형태 수용성 (Polymorphic Input Handling)

신규 모델들은 다음 4가지 호출 형태를 모두 자동으로 감지하고 안전하게 변환하여야 합니다:

1. **명시적 다중 키워드 호출**:
   ```python
   out = model(daily_x=daily_tensor, minute_x=minute_tensor, tabular_x=tabular_tensor)
   ```
2. **딕셔너리 컨테이너 호출**:
   ```python
   out = model(x={"daily": daily_tensor, "minute": minute_tensor, "tabular": tabular_tensor})
   ```
3. **튜플 컨테이너 호출**:
   ```python
   out = model(x=(daily_tensor, minute_tensor, tabular_tensor))
   ```
4. **하위 호환 2-스트림 / 단일 텐서 호출**:
   ```python
   out = model(temporal_x=temp_tensor, tabular_x=tab_tensor)  # minute_x 자동 zero-padding 또는 fallback
   out = model(x=flat_obs_tensor)  # 1D Gymnasium Box 관측값 자동 슬라이싱 및 reshape
   ```

### 3.3 모델 공통 출력 규격

모든 신규 모델은 Feature Extractor 및 Multi-task 예측기 역할을 수행하며, 다음 출력을 반환합니다:

1. `extract_features(...) -> Tensor(Batch, output_dim)`:
   - RL 에이전트(`HybridActorCritic`) 및 SB3 추출기(`SB3CustomFeaturesExtractor`)에 전달되는 최종 잠재 표현 벡터 (`output_dim=64`).
2. `forward(...) -> Tuple[Tensor, Tensor, Tensor]`:
   - `(features, pred_return, pred_direction)`
   - `features`: `(Batch, output_dim)`
   - `pred_return`: `(Batch, 1)` (익일 기대 수익률 예측값)
   - `pred_direction`: `(Batch, num_classes=3)` (추세 방향 로짓: 하락, 보합, 상승)
3. CVAE 전용 보조 딕셔너리 (`aux_dict`):
   - `latent_mu`: `(Batch, latent_dim)`
   - `latent_logvar`: `(Batch, latent_dim)`
   - `latent_z`: `(Batch, latent_dim)`
   - `reconstructed_daily`: `(Batch, T_day, C_day)`
   - `reconstructed_minute`: `(Batch, T_min, C_min)`
   - `anomaly_score`: `(Batch, 1)`

---

## 4. 아키텍처 1: 1D-CNN 기반 ResNet (`TemporalResNetFeatureExtractor`)

### 4.1 설계 배경 및 수식 모델
기존 1D-CNN은 단일 합성곱 계층이 누적될수록 신호 감쇠 및 표현력 한계가 존재합니다. Residual Block을 도입하여 잔차 함수 $\mathcal{F}(x) = \mathcal{H}(x) - x$를 학습함으로써 깊은 신경망에서도 역전파 경로를 원활히 유지합니다.

$$y = \sigma\left(\mathcal{F}(x, \{W_i\}) + \mathcal{W}_s x\right)$$

- $\mathcal{F}$: $1\text{D-Conv} \rightarrow \text{GroupNorm} \rightarrow \text{GELU} \rightarrow \text{Dropout} \rightarrow 1\text{D-Conv} \rightarrow \text{GroupNorm}$
- $\mathcal{W}_s$: 입력 채널과 출력 채널이 다르거나 스트라이드가 적용될 경우 $1\times 1$ 합성곱 사상, 동일할 경우 $\mathcal{I}$ (Identity).

### 4.2 세부 아키텍처 명세

```
[daily_x: (B, T_d, C_d)]       [minute_x: (B, T_m, C_m)]       [tabular_x: (B, D_tab)]
         │                               │                               │
  Transpose(1, 2)                 Transpose(1, 2)                        │
         │                               │                               │
Input Conv1d (C_d -> 32)        Input Conv1d (C_m -> 32)                 │
         │                               │                               │
ResNet1DBlock 1 (32 -> 64)      ResNet1DBlock 1 (32 -> 64)               │
         │                               │                               │
ResNet1DBlock 2 (64 -> 64)      ResNet1DBlock 2 (64 -> 64)               │
         │                               │                               │
AdaptiveAvgPool1d(1)            AdaptiveAvgPool1d(1)                     │
         │                               │                               │
Flatten -> Linear(64, 48)       Flatten -> Linear(64, 48)         TabularMLP (D_tab -> 32)
         │                               │                               │
         └───────────────┬───────────────┘                               │
                         │ Concat                                        │
                 (B, 48 + 48 = 96)                                       │
                         │                                               │
                         └───────────────────────┬───────────────────────┘
                                                 │ Concat (B, 96 + 32 = 128)
                                                 ▼
                                        Fusion MLP (128 -> 64)
                                                 │
                                                 ▼
                                     features: (B, output_dim=64)
                                                 │
                                 ┌───────────────┴───────────────┐
                                 ▼                               ▼
                      return_head: (B, 1)            direction_head: (B, 3)
```

### 4.3 모듈 구성 명세
1. `ResNet1DBlock`:
   - 파라미터: `in_channels`, `out_channels`, `kernel_size=3`, `stride=1`, `dilation=1`, `dropout=0.1`
   - 정규화: `GroupNorm` (배치 크기 1에서도 안전 작동, $G=\min(4, \text{channels})$)
   - 활성화 함수: `GELU`
2. `TemporalResNetFeatureExtractor`:
   - Daily Branch: Conv1d 사상 후 2개의 Residual Block, 적응형 평균 풀링.
   - Minute Branch: Conv1d 사상 후 2개의 Residual Block, 적응형 평균 풀링.
   - Tabular Branch: 2계층 MLP.
   - Fusion Layer: 선형 투영 + LayerNorm + GELU.
   - Multi-Task Heads: 익일 수익률 선형 헤드 및 3클래스 추세 분류 헤드.

---

## 5. 아키텍처 2: 시계열 Attention 기반 Transformer (`TemporalTransformerFeatureExtractor`)

### 5.1 설계 배경 및 수식 모델
금융 시계열은 주기성 및 비정형적 시간 지연 상관관계가 존재합니다. 고정 크기 합성곱 필터 대신 Self-Attention 메커니즘을 적용하여 시퀀스 전체 타임스텝 간의 동적 가중치 관계를 모델링합니다.

$$\text{Attention}(Q, K, V) = \text{Softmax}\left(\frac{Q K^T}{\sqrt{d_k}} + M_{causal}\right) V$$

학습 안정성을 위해 Pre-LN (LayerNorm prior to Attention/FFN) 방식을 적용합니다:
$$x^{(1)} = x + \text{MHA}(\text{LN}(x))$$
$$x^{(2)} = x^{(1)} + \text{FFN}(\text{LN}(x^{(1)}))$$

### 5.2 세부 아키텍처 명세

```
[daily_x: (B, T_d, C_d)]              [minute_x: (B, T_m, C_m)]
         │                                     │
Linear Proj (C_d -> d_model=64)        Linear Proj (C_m -> d_model=64)
         │                                     │
+ Positional Encoding (Sinusoidal)     + Positional Encoding (Sinusoidal)
         │                                     │
TransformerEncoder (Pre-LN, 2 layers)  TransformerEncoder (Pre-LN, 2 layers)
         │                                     │
Cross-Timeframe CrossAttention (Query: Daily, Key/Value: Minute)
         │
Temporal Attention Pooling (Learnable Query q_pool -> Weighted Sum)
         │
daily_feat: (B, d_model)              minute_feat: (B, d_model)
         │                                     │
         └──────────────────────┬──────────────┘
                                │ Concat + Tabular MLP (B, 64 + 64 + 32 = 160)
                                ▼
                       Fusion MLP (160 -> 64)
                                │
                                ▼
                    features: (B, output_dim=64)
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
     return_head: (B, 1)            direction_head: (B, 3)
```

### 5.3 모듈 구성 명세
1. `TemporalPositionalEncoding`:
   - Sinusoidal 위치 임베딩 계산: $PE_{(pos, 2i)} = \sin(pos / 10000^{2i/d})$, $PE_{(pos, 2i+1)} = \cos(pos / 10000^{2i/d})$.
2. `CrossTimeframeAttention`:
   - Query: 거시 일봉 시퀀스 표현
   - Key, Value: 미시 분봉 시퀀스 표현
   - 일봉 추세 관점에서 가장 영향력 높은 분봉 타임스텝의 상호작용 포착.
3. `AttentionPooling1D`:
   - 단순 평균 풀링 대신 학습 가능한 쿼리 벡터 $u$를 도입: $\alpha_t = \frac{\exp(u^T h_t)}{\sum_k \exp(u^T h_k)}$, $c = \sum \alpha_t h_t$.
   - 타임스텝 중요도 가중치 산출 및 XAI(설명 가능한 인공지능) 시각화 지원 (`get_attention_weights()`).

---

## 6. 아키텍처 3: 잠재 공간 이상치 탐지 기반 CVAE (`TemporalCVAEFeatureExtractor`)

### 6.1 설계 배경 및 수식 모델
금융 시장에서는 플래시 크래시, 서킷브레이커, 급변 체제(Regime Change) 등 정상적인 통계적 분포를 벗어나는 극단적 이상치가 발생합니다. CVAE는 정상 조건 $C$(정적 지표, 계좌 상태, 매크로) 하에서 다중 타임프레임 시계열 $X$의 생성 모델을 학습하고, 이상치 점수(Anomaly Score)를 산출하여 정책망에 리스크 신호를 주입합니다.

1. **Evidence Lower Bound (ELBO)**:
   $$\log p(X | C) \ge \mathbb{E}_{q_\phi(z|X, C)}\left[\log p_\theta(X | z, C)\right] - \beta \cdot D_{KL}\left(q_\phi(z | X, C) \parallel p(z | C)\right)$$
2. **Reparameterization Trick**:
   $$z = \mu(X, C) + \sigma(X, C) \odot \epsilon, \quad \epsilon \sim \mathcal{N}(0, I)$$
3. **이상치 점수 산출 (Anomaly Metric)**:
   $$\text{AnomalyScore} = \frac{1}{N} \|X - \hat{X}\|_2^2 + \gamma \cdot D_{KL}(q(z|X, C) \parallel \mathcal{N}(0, I))$$
   - 정상 장세에서는 $\text{AnomalyScore}$가 낮게 유지됨.
   - 급격한 왜곡이나 분포 외(OOD) 충격 발생 시 재건 오차가 폭증하여 에이전트에게 경보 제공.

### 6.2 세부 아키텍처 명세

```
[X_daily, X_minute]                  [Condition C: tabular_x]
         │                                       │
Temporal Conv1D Encoder               Condition Encoder (MLP -> c_emb: 32)
         │                                       │
  h_x: (B, 64)                                   │
         │                                       │
         └───────────────────────┬───────────────┘
                                 │ Concat (B, 64 + 32 = 96)
                                 ▼
                     Latent Projection Layers
                      ┌──────────┴──────────┐
                      ▼                     ▼
               mu: (B, latent_dim=16)  logvar: (B, latent_dim=16)
                      └──────────┬──────────┘
                                 ▼ Reparameterization
                        z: (B, latent_dim=16)
                                 │
         ┌───────────────────────┴───────────────┐
         │ Concat with c_emb                     │
         ▼                                       ▼
  Decoder Network (Transposed Conv)      Downstream Feature Fusion
         │                                       │
Reconstructed [X_hat_d, X_hat_m]                 Concat [mu, AnomalyScore, c_emb]
         │                                       │
Reconstruction Loss & Anomaly Score              Linear -> LayerNorm -> GELU
                                                 │
                                                 ▼
                                     features: (B, output_dim=64)
                                                 │
                                 ┌───────────────┴───────────────┐
                                 ▼                               ▼
                      return_head: (B, 1)            direction_head: (B, 3)
```

### 6.3 모듈 구성 명세
1. `ConditionEncoder`:
   - `tabular_x`를 $c_{emb}$ (32차원)로 변환.
2. `CVAEEncoder`:
   - 다중 타임프레임 시계열을 1D-CNN으로 처리 후 $c_{emb}$와 결합하여 $\mu, \log \sigma^2$ (기본 16차원) 산출.
3. `CVAEDecoder`:
   - 잠재 벡터 $z$와 $c_{emb}$를 결합하여 원본 일봉 및 분봉 텐서 크기로 복원.
4. `compute_cvae_loss`:
   - 재건 손실(Smooth L1) + $\beta \cdot \text{KL Loss}$ + 멀티태스크 예측 손실.

---

## 7. 비교 및 아키텍처 종합 매트릭스

| 아키텍처 | 주요 모델 클래스 | 핵심 기제 | 장점 | 단점 / 극복 방안 | 적합 장세 / 목적 |
|---|---|---|---|---|---|
| **ResNet 1D-CNN** | `TemporalResNetFeatureExtractor` | Residual Skip Connection, GroupNorm, 1D Convolutions | 빠른 연산 속도, 메모리 효율성, 안정적 수렴 | 고정된 Receptive Field -> Multi-Scale 커널 및 Dilation 블록 적용 | 단기 모멘텀 포착, 고빈도 추세 추종 |
| **TimeSeries Transformer** | `TemporalTransformerFeatureExtractor` | Multi-Head Attention, Pre-LN, Cross-Timeframe Attention | 장기 시계열 의존성 학습, 어텐션 가중치 기반 설명가능성(XAI) | 연산량 증가 -> 사전 프로젝션 및 경량화(Pre-LN, Attention Pooling) | 중장기 추세 판단, 일봉/분봉 간 교차 상관 분석 |
| **Latent CVAE** | `TemporalCVAEFeatureExtractor` | 조건부 잠재 공간 인코딩, Reparameterization, 이상치 점수화 | 시장 체제 전환 및 블랙 스완 조기 감지, 강건한 잠재 표현 | KL 소실(KL Vanishing) 위험 -> $\beta$-VAE 어닐링 및 Free Bits 적용 | 급변장/위험 관리, 시장 이상치 감지 및 방어적 비중 조절 |

---

## 8. 하이브리드 RL (HybridActorCritic / PPO) 연계 방안 (Phase 6 R2 대응)

### 8.1 정책망 결합 방식 (End-to-End Feature Integration)
- `HybridActorCritic` 초기화 시 `feature_extractor` 파라미터로 신규 3개 모델 인스턴스를 주입:
  ```python
  # ResNet 정책망
  policy_resnet = HybridActorCritic(
      obs_dim=obs_dim,
      feature_extractor=TemporalResNetFeatureExtractor(output_dim=64),
      feature_dim=64,
      distribution_type="beta"
  )
  # Transformer 정책망
  policy_transformer = HybridActorCritic(
      obs_dim=obs_dim,
      feature_extractor=TemporalTransformerFeatureExtractor(output_dim=64),
      feature_dim=64,
      distribution_type="beta"
  )
  # CVAE 정책망
  policy_cvae = HybridActorCritic(
      obs_dim=obs_dim,
      feature_extractor=TemporalCVAEFeatureExtractor(output_dim=64),
      feature_dim=64,
      distribution_type="beta"
  )
  ```
- 정책망의 `extract_features(obs)`는 입력이 Dict, Tuple, 1D Box Tensor인지 여부를 판별하여 백본 모델로 라우팅.

### 8.2 상태 공간 증강 방식 (State Augmentation Integration)
- 환경(`HybridTradingEnv`) 또는 전처리 래퍼에서 SL 모델의 예측값(`pred_return`, `pred_direction_prob`, `anomaly_score`)을 기존 관측 벡터 $o_t$ 뒤에 결합:
  $$s_t = \left[o_t, \hat{r}_{t+1}, P(\text{DOWN}), P(\text{HOLD}), P(\text{UP}), \text{Score}_{anomaly}\right]$$
- 이를 통해 Actor-Critic은 단순 과거 데이터뿐만 아니라 SL 모델의 종합적인 미래 전망 및 위험 평가를 고려하여 최적의 매매 행동 및 비중을 산출.

### 8.3 사전학습 전이(Transfer) 및 부분 동결(Freeze)
- `SLPretrainer`로 대량의 과거 데이터에 대해 사전학습을 수행한 후, `policy.load_from_sl_pretrainer(pretrainer, freeze=True)`를 실행.
- 특징 추출기 가중치를 고정(Freeze)한 채 PPO 에이전트를 학습시키면 RL 탐색 초기의 정책 붕괴(Policy Collapse)를 완벽히 차단 가능.

---

## 9. 대규모 Optuna HPO 파이프라인 연계 방안 (Phase 6 R3 대응)

### 9.1 아키텍처별 탐색 공간 (Hyperparameter Search Space)

| 아키텍처 | 파라미터명 | 타입 | 탐색 범위 | 기본값 |
|---|---|---|---|---|
| **공통 SL/RL** | `sl_lr` | float (log) | `1e-5` ~ `1e-2` | `1e-3` |
| | `rl_lr` | float (log) | `1e-5` ~ `1e-3` | `3e-4` |
| | `rl_gamma` | float | `0.90` ~ `0.999` | `0.99` |
| | `rl_clip_range` | float | `0.1` ~ `0.3` | `0.2` |
| | `rl_ent_coef` | float (log) | `1e-4` ~ `1e-1` | `0.01` |
| **ResNet** | `num_blocks` | categorical | `[1, 2, 3]` | `2` |
| | `base_filters` | categorical | `[32, 64, 128]` | `64` |
| | `kernel_size` | categorical | `[3, 5]` | `3` |
| | `dropout` | float | `0.0` ~ `0.3` | `0.1` |
| **Transformer** | `d_model` | categorical | `[32, 64, 128]` | `64` |
| | `nhead` | categorical | `[2, 4, 8]` | `4` |
| | `num_layers` | categorical | `[1, 2, 3]` | `2` |
| | `dim_feedforward` | categorical | `[64, 128, 256]` | `128` |
| | `dropout` | float | `0.0` ~ `0.3` | `0.1` |
| **CVAE** | `latent_dim` | categorical | `[8, 16, 32]` | `16` |
| | `hidden_dim` | categorical | `[32, 64, 128]` | `64` |
| | `kl_weight` ($\beta$) | float (log) | `1e-4` ~ `1e-1` | `1e-3` |

### 9.2 CSV 내보내기 규격 (`etc/hpo_results/main_models_hpo.csv`)
- Phase 6 R3 요구사항에 명시된 저장 경로 준수: `etc/hpo_results/main_models_hpo.csv`
- 프로세스 간 `fcntl` 파일 락을 통해 멀티프로세스 동시 기록 안전성 보장.
- 컬럼 구성:
  `architecture, trial_id, state, objective_value, total_equity, total_return_pct, sharpe_ratio, max_drawdown_pct, total_trades, win_rate, param_sl_lr, param_rl_lr, param_arch_specific_json, duration_seconds, datetime_start, datetime_complete`

---

## 10. 소스 코드 배치 및 모듈화 권고안

### 10.1 권장 파일 분할 구조
기존 `feature_extractor.py`는 이미 877라인에 달하므로, 단일 파일 비대화를 방지하고 클린 코드 원칙을 준수하기 위해 서브모듈 분리를 권장합니다:

```
modules/models/
├── __init__.py                      # 모든 기존 및 신규 클래스 일괄 re-export (하위 호환성 100%)
├── feature_extractor.py             # 기존 Tabular, Temporal1D, DualStream, SLPretrainer 유지
├── resnet.py                        # 신규: ResNet1DBlock, TemporalResNetFeatureExtractor
├── transformer.py                   # 신규: PositionalEncoding, AttentionPooling, TemporalTransformerFeatureExtractor
├── cvae.py                          # 신규: TemporalCVAEFeatureExtractor
└── hybrid_policy.py                 # HybridActorCritic, HybridPPO, SB3 어댑터
```

`modules/models/__init__.py`에 아래와 같이 등록하여 기존 코드 및 신규 테스트에서 일관되게 임포트 가능하도록 구성:
```python
from modules.models.resnet import TemporalResNetFeatureExtractor, ResNet1DBlock
from modules.models.transformer import TemporalTransformerFeatureExtractor
from modules.models.cvae import TemporalCVAEFeatureExtractor
```

### 10.2 검증 스위트 구성 가이드 (`tests/`)
1. `tests/test_phase6_models.py`:
   - 3가지 모델(`TemporalResNetFeatureExtractor`, `TemporalTransformerFeatureExtractor`, `TemporalCVAEFeatureExtractor`)의 텐서 입출력 형상 검증.
   - 명시적 키워드 인자, Dict, Tuple, 단일 텐서 입력에 대한 순전파 및 역전파(Gradient Flow) 확인.
   - 출력 Shape: `features.shape == (B, output_dim)`, `pred_return.shape == (B, 1)`, `pred_direction.shape == (B, 3)`.
   - CVAE의 잠재 벡터 및 재건 텐서 Shape, 이상치 점수 산출 검증.
   - `HybridActorCritic` 및 `SLPretrainer`와의 상호운용성 검증.
2. `tests/test_phase6_hpo.py`:
   - 3대 아키텍처별로 Optuna HPO가 최소 2회(`n_trials=2`) 이상 크래시 없이 완주되는지 검증.
   - 결과 파일 `etc/hpo_results/main_models_hpo.csv`가 정상 생성되고 데이터가 기록되었는지 검증.
