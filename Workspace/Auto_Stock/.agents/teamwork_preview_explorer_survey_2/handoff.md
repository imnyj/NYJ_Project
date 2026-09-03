# Handoff Report: Auto_Stock Models & Hybrid Action Space Survey

## 1. Observation (직접 관찰 결과)

### 1.1 프로젝트 환경 및 라이브러리 상태
로컬 가상환경(`/home/imnyj/venv/bin/python`) 실행을 통해 주요 라이브러리 버전 및 GPU 가속 상태를 직접 검증하였습니다:
- **PyTorch**: `2.11.0+cu130` (CUDA 가속 활성화: `True`, NVIDIA GPU 사용 가능)
- **Gymnasium**: `1.2.0` (최신 Gymnasium 표준 API 준수)
- **Stable-Baselines3**: `2.7.0`
- **Optuna**: `4.8.0`
- **Pandas**: `2.3.3`, **NumPy**: `2.4.4`, **PyArrow**: `19.0.1`

### 1.2 기존 데이터 파이프라인 및 시계열 데이터 피처 구조
- 파일 경로: `/home/imnyj/Workspace/Auto_Stock/data/raw/005930_consolidated.parquet` (100 rows × 40 columns, 결측치 0건)
- **시세 및 거래량 피처**: `open`, `high`, `low`, `close`, `volume`, `value`
- **기술적 지표 피처**: `returns_1d`, `return_1d`, `volatility_20d`, `log_return`, `ma_5`, `ma_20`, `ma_60`
- **Point-in-Time(PIT) 동적 밸류에이션 피처**: `dynamic_per`, `dynamic_pbr`, `dynamic_market_cap`, `roe`, `eps`, `bps`, `div_yield`
- **검증 메타데이터**: `is_cross_verified`, `validation_status`

### 1.3 가상 체결 엔진 및 시뮬레이터 인터페이스
- 파일 경로: `/home/imnyj/Workspace/Auto_Stock/modules/engine/mock_environment.py`
  - `VirtualAccount` (라인 224~509): 1원 단위 엄격한 `Decimal` 회계 연산, 이동평균 평단가 갱신, 마이너스 잔고 원천 차단.
  - `MockExecutionEngine` (라인 514~886): 수수료(0.015%), 증권거래세(0.18%), 슬리피지(0.1%) 적용, `verify_accounting_invariant` 회계 불변식(오차 0원) 검증.
  - `MockEnvironment` (라인 1125~1346): `reset()`, `step()`, `get_state()` 표준 인터페이스 제공.
- 파일 경로: `/home/imnyj/Workspace/Auto_Stock/modules/engine/live_learning_simulator.py`
  - `LiveLearningSimulator` (라인 27~157): Kiwoom REST API 실시간 시세 연동 및 Paper Trading 지원.

### 1.4 Stable-Baselines3와 Gymnasium Hybrid Action Space 간 호환성 검증 결과
직접 테스트 스크립트 실행 시 SB3의 내장 정책(`MlpPolicy` 등)에 `spaces.Tuple` 또는 `spaces.Dict` 액션 공간을 전달할 경우 다음과 같은 예외가 발생함을 직접 확인하였습니다:
```text
SB3 Tuple Action Space error: AssertionError: The algorithm only supports (<class 'gymnasium.spaces.box.Box'>, <class 'gymnasium.spaces.discrete.Discrete'>, <class 'gymnasium.spaces.multi_discrete.MultiDiscrete'>, <class 'gymnasium.spaces.multi_binary.MultiBinary'>) as action spaces but Tuple(Discrete(3), Box(0.0, 1.0, (1,), float32)) was provided

SB3 Dict Action Space error: AssertionError: The algorithm only supports (<class 'gymnasium.spaces.box.Box'>, <class 'gymnasium.spaces.discrete.Discrete'>, <class 'gymnasium.spaces.multi_discrete.MultiDiscrete'>, <class 'gymnasium.spaces.multi_binary.MultiBinary'>) as action spaces but Dict('action_type': Discrete(3), 'position_size': Box(0.0, 1.0, (1,), float32)) was provided
```
반면, PyTorch 기반 커스텀 `HybridActorCritic` 네트워크 및 2D Continuous `Box(low=[-1.0, 0.0], high=[1.0, 1.0])` 변환 Wrapper를 통한 SB3 연동은 에러 없이 정상 동작함을 확인하였습니다.

---

## 2. Logic Chain (논리 추론 체계)

```
[Observation 1.2: 40개 컬럼의 PIT 데이터셋]
       │
       ▼ (Step 1: SL 특징 추출기 아키텍처 설계)
  - Tabular MLP: 고속 학습, 정적 펀더멘털+계좌 상태 처리에 최적
  - Temporal 1D-CNN: 슬라이딩 윈도우 시계열 국소 패턴 및 모멘텀 포착
  - SL 사전학습 태스크: 익일 수익률 예측(MSE) + 방향성 분류(CrossEntropy)
       │
       ▼ (Step 2: SL Backbone → RL 정책망 전이)
  - 사전학습된 SL Backbone 가중치를 Actor-Critic Feature Extractor로 전이
  - 미세조정(Fine-tuning) 및 Feature Representation 재사용 극대화
       │
       ▼ (Step 3: Gymnasium Hybrid Action Space 설계 & 호환성 분기)
[Observation 1.4: SB3는 Tuple/Dict Action을 미지원]
       ├── [Option A: 표준 Gymnasium Tuple/Dict] → 의미론적 명확성 & 로깅/감사 최적
       ├── [Option B: Continuous Box Wrapper] → SB3 PPO 베이스라인 완벽 호환
       └── [Option C: Native PyTorch Hybrid PPO] → Categorical(3) + Normal/Beta(1) 결합 최적화
       │
       ▼ (Step 4: 액션 디코딩 및 가상 체결 엔진 연동)
[Observation 1.3: MockEnvironment의 정밀 회계 모델]
  - Buy 액션: 가용 현금 × 포지션 비율 → 수수료/슬리피지 반영 최대 매수 수량 산출
  - Sell 액션: 보유 주식 × 포지션 비율 → 정수 매도 수량 산출
  - Hold 액션: 0주 주문 전송
       │
       ▼ (Step 5: Optuna HPO 파이프라인 연계)
[Observation 1.1: Optuna 4.8.0 설치 완료]
  - 학습률, 배치 크기, 네트워크 차원, 클리핑 범위, 엔트로피 계수 탐색
  - 목적함수: 에피소드 종료 총 평가금(Total Equity) 및 샤프 지수(Sharpe Ratio)
  - 결과 저장: `etc/hpo_results/baseline_hpo.csv`
```

### 상세 분석 내용

#### A. SL Feature Extractor 모델 아키텍처
1. **1D-CNN 시계열 특징 추출기 (Temporal 1D-CNN Backbone)**:
   - 입력: $(B, W, F)$ 형상의 시계열 텐서 ($W=20$ 영업일 윈도우, $F=$ 기술적 지표 및 수익률 피처 10~15개).
   - 레이어: `Conv1d(F, 32, kernel=3, padding=1)` $\to$ `BatchNorm1d` $\to$ `ReLU` $\to$ `Conv1d(32, 64, kernel=3, padding=1)` $\to$ `AdaptiveAvgPool1d(1)` $\to$ `Linear(64, latent_dim)`.
   - 장점: 시계열의 단기 추세, 골든크로스, 볼린저 밴드 이탈 등 형태적 패턴 추출에 탁월.
2. **Tabular MLP 특징 추출기 (Dense Tabular Backbone)**:
   - 입력: $(B, F_{tab})$ 형상의 정적/현재 스냅샷 피처 (동적 PER/PBR, ROE, 현금 비중, 보유 주식 비중, 미실현 손익률 등).
   - 레이어: `Linear(F_tab, 128)` $\to$ `LayerNorm` $\to$ `ReLU` $\to$ `Dropout(0.1)` $\to$ `Linear(128, latent_dim)`.
   - 장점: 회계 및 재무 지표와 계좌 상태 변수의 비선형 결합을 효과적으로 임베딩.
3. **Dual-Stream 하이브리드 백본 (추천)**:
   - Stream 1(1D-CNN): 시계열 가격/거래량 피처 처리
   - Stream 2(MLP): 펀더멘털 + 가상 계좌 상태 처리
   - Fusion: 두 잠재 벡터를 Concatenate 후 `Linear(latent_dim * 2, feature_dim)` 투영.

#### B. 지도학습(SL) 사전학습 파이프라인
- **목적함수 (Multi-Task Loss)**:
  $$\mathcal{L}_{SL} = \mathcal{L}_{reg}(y_{ret}, \hat{y}_{ret}) + \lambda_{cls} \mathcal{L}_{cls}(y_{dir}, \hat{y}_{dir})$$
  - $\mathcal{L}_{reg}$: Smooth L1 Loss 또는 MSE (익일 수익률 $r_{t+1}$ 예측)
  - $\mathcal{L}_{cls}$: CrossEntropy Loss (상승/보합/하락 3-Class 방향성 분류)
- **전이(Transfer)**: 학습 완료된 백본 가중치를 RL Actor-Critic의 Feature Extractor로 로드하고, RL 학습 초기에는 백본 가중치를 고정(Freeze)하거나 낮은 학습률($0.1 \times \text{lr}_{RL}$)으로 미세조정.

#### C. Gymnasium Hybrid Action Space 구성 및 디코딩 전략
1. **Gymnasium Action Space 정의**:
   - `spaces.Dict({"action_type": spaces.Discrete(3), "position_size": spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)})`
   - 혹은 `spaces.Tuple((spaces.Discrete(3), spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)))`
2. **액션 디코딩(Decoding) 및 주문 수량 계산 로직**:
   - 입력: $(a_{type}, \alpha) \in \{0, 1, 2\} \times [0.0, 1.0]$
   - **BUY ($a_{type} = 1$)**:
     $$\text{Budget} = \text{CashBalance} \times \alpha$$
     $$P_{eff} = P_{mkt} \times (1 + \text{slippage}) \times (1 + \text{commission})$$
     $$Q_{buy} = \left\lfloor \frac{\text{Budget}}{P_{eff}} \right\rfloor$$
     $Q_{buy} \ge 1$일 때 `OrderSide.BUY` 실행, 잔고 부족 시 주문 거절 방어.
   - **SELL ($a_{type} = 2$)**:
     $$Q_{sell} = \left\lfloor \text{HoldingShares} \times \alpha \right\rfloor$$
     $\alpha > 0$이고 $\text{HoldingShares} \ge 1$이면 최소 1주 매도 (`min(max(1, Q_{sell}), \text{HoldingShares})`).
   - **HOLD ($a_{type} = 0$)**:
     $Q = 0$, 체결 없이 시세 변동만 반영.

#### D. RL 베이스라인 아키텍처 비교 및 추천

| 구분 | Native PyTorch Hybrid PPO (추천 1) | SB3 PPO + Continuous Wrapper (추천 2) |
|---|---|---|
| **액션 분포** | `Categorical(3)` + `Normal(1)` (또는 `Beta`) 독립 결합 | 2D `Normal` Continuous 액션 공간 |
| **로그 확률 계산** | $\log \pi = \log \pi_{disc}(a_{disc}) + \log \pi_{cont}(\alpha)$ | $\log \pi = \sum_{i=1}^2 \log \pi_i(a_i)$ |
| **SL 전이 용이성** | PyTorch 모델 간 가중치 직접 로드 및 부분 Freeze 지원 | `BaseFeaturesExtractor` 상속을 통해 로드 |
| **장점** | 이산 의사결정(매매 여부)과 연속 수량(비중)의 완전한 분리 모델링 | SB3의 검증된 학습 루프 및 콜백 생태계 활용 |

---

## 3. Caveats (주의사항 및 한계)

1. **SB3 내장 정책의 Tuple/Dict 액션 미지원**:
   - SB3를 직접 사용할 경우 `ActionWrapper`를 통해 `Box(low=[-1.0, 0.0], high=[1.0, 1.0], shape=(2,))`로 매핑하거나, 이산 행동을 신호 임계값($[-1.0, -0.33] \to \text{SELL}$, $[-0.33, 0.33] \to \text{HOLD}$, $[0.33, 1.0] \to \text{BUY}$)으로 디코딩해야 합니다.
2. **시계열 데이터 길이 제약**:
   - 현재 `005930_consolidated.parquet`는 100 거래일 데이터입니다. 1D-CNN의 윈도우 크기($W=20$) 적용 시 에피소드당 유효 스텝은 80 스텝이므로, HPO 및 베이스라인 검증 시 오버피팅을 방지하기 위해 정규화(Dropout, LayerNorm)가 필수적입니다.
3. **체결 지연 및 유동성 제약**:
   - 시뮬레이터는 익일 시초가/당일 종가 기준 단일 호가 체결을 가정하므로, 대량 주문 시의 호가 잔량 부족(Market Depth)은 고정 슬리피지(0.1%) 모델로 근사됩니다.

---

## 4. Conclusion (최종 결론 및 추천 구현 사양)

1. **Gymnasium 환경 (`StockTradingGymEnv`) 설계**:
   - 액션 공간: `spaces.Dict({"action_type": spaces.Discrete(3), "position_size": spaces.Box(0.0, 1.0, (1,))})` (또는 Tuple 지원).
   - 관측 공간: `spaces.Box(shape=(obs_dim,))` (정규화된 10개 시계열/기술적 지표 + 4개 계좌 상태 지표).
   - 체결 백엔드: `MockEnvironment` 및 `LiveLearningSimulator` 연동.
2. **SL-RL 결합 모델 아키텍처 (`HybridSLRLModel`)**:
   - 특징 추출기: `TabularMLPFeatureExtractor` 및 `Temporal1DCNNFeatureExtractor` 지원.
   - RL 에이전트: PyTorch 기반 `HybridActorCritic` (이산 로짓 3개 + 연속 비중 평균/표준편차) 및 SB3 호환 `CustomFeaturesExtractor` 이중 제공.
3. **Optuna HPO 파이프라인**:
   - 탐색 공간: `lr` ($10^{-5} \sim 10^{-2}$), `batch_size` ($16, 32, 64$), `feature_dim` ($32, 64, 128$), `entropy_coef` ($0.001 \sim 0.05$), `clip_range` ($0.1 \sim 0.3$).
   - 목적 지표: 검증 에피소드 총 평가금 수익률($\text{Total Equity}$) 및 샤프 지수($\text{Sharpe Ratio}$).
   - 산출물: `etc/hpo_results/baseline_hpo.csv`에 모든 Trial 파라미터와 결과 자동 기록.

---

## 5. Verification Method (독립 검증 방법)

다음 명령어를 통해 환경 호환성, 모델 포워드 패스 및 HPO 프로토타입을 독립적으로 검증할 수 있습니다:

```bash
# 1. 가상환경 라이브러리 및 하이브리드 액션 공간 호환성 테스트
/home/imnyj/venv/bin/python -c "
import gymnasium as gym
from gymnasium import spaces
import torch
import torch.nn as nn
import optuna

# Action Space 확인
action_space = spaces.Dict({
    'action_type': spaces.Discrete(3),
    'position_size': spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=torch.float32)
})
print('Hybrid Action Space verified:', action_space)
"

# 2. Parquet 데이터 로드 및 피처 차원 검증
/home/imnyj/venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('/home/imnyj/Workspace/Auto_Stock/data/raw/005930_consolidated.parquet')
print('Data shape:', df.shape)
assert 'dynamic_per' in df.columns and 'returns_1d' in df.columns
print('Features verified successfully!')
"
```
