# Survey Report: 모델 아키텍처, Optuna 하이퍼파라미터 최적화 및 학습 파이프라인 정밀 분석 보고서

**작성일시**: 2026-08-24T01:25:00Z  
**작성자**: Survey 탐색 에이전트 (`explorer_survey_2`)  
**대상 프로젝트**: `/home/imnyj/Workspace/paper4`  
**보고서 목적**: 17개 모델 아키텍처 전수 조사, 기존 체크포인트 현황 및 삭제 대상 목록화, Optuna 하이퍼파라미터 튜닝 파이프라인 분석, 학습 파이프라인 및 보상 체계 분석, 하드웨어 자원 및 병렬화 타당성 평가.

---

## 1. 17개 모델 정의 및 아키텍처 전수 조사

Paper4 프로젝트에는 총 17개의 통신 혼잡 제어(DCC: Decentralized Congestion Control) 모델이 정의되어 있습니다. (제안 DRL 1개 + 베이스라인 DRL 10개 + 시퀀스/오프라인 RL 1개 + 타뷸라 RL 2개 + 비RL 규칙기반/표준 3개)

### 1.1 모델별 아키텍처 명세표

| # | 모델명 | 유형 | 소스 파일 / 클래스 | 신경망 / 알고리즘 구조 | 상태 차원 (State) | 액션 차원 (Action) | 주요 특징 및 손실함수 |
|---|---|---|---|---|---|---|---|
| **1** | **REMO-DQN** *(Proposed)* | DRL (ResNet-MoE) | `resnet_moe_agent.py`<br>`ResNetMoEDQN`<br>`ResNetMoEAgent` | **Feature Extractor**: Linear(5,128) + 2 Residual Blocks (각 128→128→128, Skip Connection)<br>**Gating Net**: Linear(128,64)→ReLU→Linear(64,3)→Softmax (Detached Input)<br>**3 Dueling Experts**: 각 Expert는 Value Stream(128→64→1) + Advantage Stream(128→64→24) | 5D | 24D | Double DQN Target Update + Load Balancing Loss ($0.01 \cdot CV^2$) |
| **2** | **MoEDQN** | DRL (MoE) | `moe_agent.py`<br>`MoEDQN`<br>`MoEAgent` | **MoEFeature**: 2 Experts (Linear(5,128)→ReLU→128) + Gating(5→64→2)<br>**Dueling Output**: Value(128→64→1) + Advantage(128→64→24) | 5D | 24D | Feature-level MoE + Dueling DQN 구조 |
| **3** | **DuelingDQN** | DRL | `dueling_dqn_agent.py`<br>`DuelingDQN`<br>`DuelingDQNAgent` | **Feature**: Linear(5,128)→ReLU→Linear(128,128)→ReLU<br>**Value**: Linear(128,64)→ReLU→Linear(64,1)<br>**Advantage**: Linear(128,64)→ReLU→Linear(64,24) | 5D | 24D | $Q(s,a) = V(s) + (A(s,a) - \bar{A}(s))$ |
| **4** | **DoubleDQN** | DRL | `ddqn_agent.py`<br>`DoubleDQN`<br>`DDQNAgent` | **MLP**: Linear(5,128)→ReLU→Linear(128,128)→ReLU→Linear(128,24) | 5D | 24D | 타깃 네트워크와 행동 선택 분리 (Double DQN update) |
| **5** | **VanillaDQN** | DRL | `dqn_agent.py`<br>`VanillaDQN`<br>`DQNAgent` | **MLP**: Linear(5,128)→ReLU→Linear(128,128)→ReLU→Linear(128,24) | 5D | 24D | 표준 Deep Q-Network (Standard Bellman max update) |
| **6** | **PPO** | DRL (On-Policy) | `ppo_agent.py`<br>`PPO`<br>`PPOAgent` | **Actor**: Linear(5,128)→ReLU→Linear(128,64)→ReLU→Linear(64,24)→Softmax<br>**Critic**: Linear(5,128)→ReLU→Linear(128,64)→ReLU→Linear(64,1) | 5D | 24D | Clipped Surrogate Objective ($\epsilon=0.2$, $K=4$ epochs) |
| **7** | **MAPPO** | DRL (Multi-Agent) | `mappo_agent.py`<br>`MAPPO`<br>`MAPPOAgent` | **Actor (Decentralized)**: Linear(5,128)→ReLU→Linear(128,64)→ReLU→Linear(64,24)→Softmax<br>**Critic (Centralized)**: Linear(10,128)→ReLU→Linear(128,64)→ReLU→Linear(64,1) | Local 5D,<br>Global 5D | 24D | 중앙 집중형 Critic + 분산 액터 구조 |
| **8** | **SAC** | DRL (Max Entropy) | `sac_agent.py`<br>`QNetwork`, `PolicyNetwork`<br>`SACAgent` | **Twin Critic (Q1, Q2)**: Linear(5,128)→ReLU→Linear(128,64)→Linear(64,24)<br>**Policy Net**: Linear(5,128)→ReLU→Linear(128,64)→Linear(64,24)→Softmax | 5D | 24D | 이산 액션 공간용 Discrete SAC, 엔트로피 온도 $\alpha=0.2$ |
| **9** | **DDPG** | DRL (Actor-Critic) | `ddpg_agent.py`<br>`Actor`, `Critic`<br>`DDPGAgent` | **Actor**: Linear(5,128)→ReLU→Linear(128,64)→Linear(64,24) + Gumbel Softmax(tau=1.0, hard=True)<br>**Critic**: Linear(29,128)→ReLU→Linear(128,64)→Linear(64,1) | 5D | 24D | 이산 액션을 Gumbel-Softmax One-Hot으로 연속 미분 가능화 |
| **10** | **TD3** | DRL (Twin Delayed) | `td3_agent.py`<br>`Actor`, `QNetwork`<br>`TD3Agent` | **Actor**: Linear(5,128)→ReLU→Linear(128,64)→Linear(64,24)<br>**Twin Critic (Q1, Q2)**: Linear(29,128)→ReLU→Linear(128,64)→Linear(64,1) | 5D | 24D | Delayed Policy Update (policy_delay=2) + Target Action Clipped Noise |
| **11** | **ActorCritic** | DRL (A2C) | `actor_critic_agent.py`<br>`ActorCritic`<br>`ActorCriticAgent` | **Actor**: Linear(5,128)→ReLU→Linear(128,64)→ReLU→Linear(64,24)→Softmax<br>**Critic**: Linear(5,128)→ReLU→Linear(128,64)→ReLU→Linear(64,1) | 5D | 24D | Advantage Actor-Critic ($A = R + \gamma V(s') - V(s)$) |
| **12** | **DecisionTransformer** | Offline / Sequence RL | `dt_agent.py`<br>`DecisionTransformer`<br>`DTAgent` | **State/Action/RTG Embeddings**: Linear(dim, 64)<br>**Transformer**: 2 layers, nhead=4, d_model=64, dim_feedforward=256<br>**Action Head**: Linear(64, 24) | 5D | 24D | Return-to-go (RTG) 조건부 시퀀스 모델링 기반 행동 예측 |
| **13** | **QLearning** | Tabular RL | `qlearning_agent.py`<br>`QLearningAgent` | **Q-Table**: Shape $(10, 10, 10, 10, 10, 24)$의 6차원 넘파이 배열. 5개 상태 변수를 각 10개 구간으로 이산화 | 5D (이산화) | 24D | $Q(s,a) \leftarrow Q(s,a) + \alpha [r + \gamma \max_{a'} Q(s',a') - Q(s,a)]$ |
| **14** | **SARSA** | Tabular RL | `sarsa_agent.py`<br>`SARSAAgent` | **Q-Table**: Shape $(10, 10, 10, 10, 10, 24)$의 6차원 넘파이 배열. 5개 상태 변수를 각 10개 구간으로 이산화 | 5D (이산화) | 24D | On-policy 업데이트: $Q(s,a) \leftarrow Q(s,a) + \alpha [r + \gamma Q(s',a') - Q(s,a)]$ |
| **15** | **Fixed 10Hz** | Static Baseline (Non-RL) | `etsi_cam_layer.py`<br>`ETSICAMLayer` | 고정 주기 및 송신 전력 규칙:<br>$T_{\text{GenCam}} = 0.1\,\text{s}$ (10 Hz), $p_{\text{tx}} = +20\,\text{dBm}$ (100 mW) | N/A | 고정 액션 (0.1s, +20dBm) | DCC 제어가 없는 표준 10Hz 연속 브로드캐스트 |
| **16** | **ReactDCC** | ETSI Standard (Non-RL) | `etsi_cam_layer.py`<br>`ETSICAMLayer` | **ETSI EN 302 571 DCC Reactive 3-State FSM**:<br>- Relaxed ($CBR < 0.40$): $T_{\text{GenCam}} = 0.1\,\text{s}$<br>- Active ($0.40 \le CBR < 0.60$): $T_{\text{GenCam}} = 0.3\,\text{s}$<br>- Restricted ($CBR \ge 0.60$): $T_{\text{GenCam}} = 1.0\,\text{s}$<br>- $p_{\text{tx}} = +20\,\text{dBm}$ 고정 | N/A | FSM 결정 (0.1s, 0.3s, 1.0s) | ETSI 유럽 지능형교통시스템 표준 반응형 DCC |
| **17** | **AdaptDCC** | ETSI Standard (Non-RL) | `etsi_cam_layer.py`<br>`ETSICAMLayer` | **Simplified Adaptive DCC**:<br>- $CBR_{\text{smooth}} = (1-\lambda)CBR_{\text{smooth}} + \lambda CBR$<br>- $error = CBR_{\text{smooth}} - 0.60$<br>- $error > 0 \Rightarrow T_{\text{GenCam}} = \min(T + \Delta_T, 1.0\,\text{s})$<br>- $error < 0 \Rightarrow T_{\text{GenCam}} = \max(T - \Delta_T, 0.1\,\text{s})$ | N/A | 선형 적응 결정 | CBR 0.60 타깃 추종 비례 제어기 |

### 1.2 공통 상태 공간 (State Space: 5D)
모든 AI/RL 모델은 동일한 5차원 정규화 상태 벡터를 공유합니다:
1. `cbr_global`: 전역 채널 점유율 $[0.0, 1.0]$
2. `n_neighbors`: 이웃 차량 밀도 정규화 ($n_{\text{est}} / 50.0$)
3. `v_norm`: 차량 속도 정규화 ($v / 25.0\,\text{m/s}$)
4. `dt_since_last_cam`: 마지막 CAM 송신 이후 경과 시간 정규화 ($\Delta t / 1.0\,\text{s}$)
5. `cbr_smoothed`: 지수이동평균(EMA, $\lambda_s=0.5$)으로 평활화된 CBR $[0.0, 1.0]$

### 1.3 공통 액션 공간 (Action Space: 24D)
모든 AI/RL 모델은 ETSI CAM 표준 그리드 기반 24차원 이산 액션 공간을 공유합니다:
- **전송 주기 ($T_{\text{GenCam}}$)**: 4단계 $[0.1, 0.2, 0.5, 1.0]\,\text{s}$ (10Hz, 5Hz, 2Hz, 1Hz)
- **송신 전력 ($p_{\text{tx}}$)**: 6단계 $[-5, 0, 5, 10, 15, 20]\,\text{dBm}$ (0.316mW ~ 100mW)
- **총 액션 수**: $4 \times 6 = 24$개 (`action_idx = interval_idx * 6 + power_idx`)

---

## 2. 기존 체크포인트 및 데이터 현황과 삭제 대상 목록

### 2.1 `data/models/` 내 기존 체크포인트 현황
현재 `data/models/` 경로에 총 15개 모델 가중치 파일(약 15MB)과 17개 convergence CSV 파일이 존재합니다.

| 파일명 | 파일 크기 | 형식 | 설명 및 상태 |
|---|---|---|---|
| `ActorCritic.pth` | 80 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `DDPG.pth` | 93 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `DecisionTransformer.pth` | 414 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `DoubleDQN.pth` | 83 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `DuelingDQN.pth` | 144 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `MAPPO.pth` | 82 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `MoEDQN.pth` | 215 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `PPO.pth` | 81 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `QLearning.pkl` | 6.2 MB | Pickle NumPy Q-table | 이전 실행 체크포인트 (삭제 대상) |
| `REMO-DQN.pth` | 522 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `resnet_moe_dqn.pth` | 522 KB | PyTorch state_dict | 이전 실행 체크포인트 (`REMO-DQN.pth`와 동일, 삭제 대상) |
| `SAC.pth` | 130 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `SARSA.pkl` | 6.2 MB | Pickle NumPy Q-table | 이전 실행 체크포인트 (삭제 대상) |
| `TD3.pth` | 132 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |
| `VanillaDQN.pth` | 83 KB | PyTorch state_dict | 이전 실행 체크포인트 (삭제 대상) |

### 2.2 기타 경로의 잔여 체크포인트
- `code/*.pth`, `code/*.pkl`: `sac.pth`, `moe_dqn.pth`, `resnet_moe_dqn.pth`, `qlearning_model.pkl`, `ddqn.pth`, `sarsa_model.pkl`, `dt_model.pth`, `actor_critic.pth`, `dueling_dqn.pth`, `td3.pth`, `ppo.pth`, `vanilla_dqn.pth`, `mappo.pth`, `ddpg_model.pth`, `stdmlp_model.pkl`, `dectree_model.pkl` (삭제 대상)
- `/home/imnyj/Workspace/paper4/dueling_dqn.pth` (루트 위치, 삭제 대상)
- `data/ablation_structure/*.pth` (Ablation 체크포인트, 삭제 대상)

### 2.3 오염 데이터 발견 및 삭제 필요성
- `data/models/VanillaDQN_convergence.csv` 등 일부 수렴 로그에서 에피소드 1~6과 7~100 사이의 급격한 값 불일치 및 다수 에피소드에 걸쳐 동일한 AoI(165.073), CBR(0.073), PDR(87.11) 값이 반복 복사된 **합성/조작 데이터 흔적**이 확인되었습니다.
- 따라서 원본 요구사항 R2에 명시된 대로 **모든 기존 `.pth` 및 `.pkl` 파일과 과거 convergence CSV 파일을 완전 삭제하고 재훈련 및 재평가를 수행해야 합니다.**

---

## 3. Optuna 하이퍼파라미터 최적화 스크립트 정밀 분석

### 3.1 스크립트 구조 및 현황
- **`code/run_optuna_all_baselines.py`**:
  - 12개 RL 베이스라인 대상 통합 Optuna 튜닝 스크립트.
  - `SimulationRunner` 기반의 2-Episode Train + 1-Episode Eval 목적함수 실행.
  - 최적 파라미터를 `data/optuna/best_params_<ModelName>.csv`로 저장.
  - **주의 발견점**: `REMO-DQN`이 목록에서 누락되어 있으며, 탐색 트라이얼 수가 `N_TRIALS = 2`로 지나치게 작아 수렴/스파이크 문제 해결을 위한 정밀 탐색이 이루어지지 못했음.
- **`code/regenerate_optunas.py` 및 개별 `optuna_*.py`**:
  - **중대한 결함 발견**: 개별 `optuna_*.py` 템플릿 코드에 `action_dim=16`이 하드코딩되어 있어 `etsi_cam_layer.py`의 표준 24차원 액션 공간과 불일치함.
  - 또한 `optuna_remo_dqn.py`가 `resnet_moe_agent.py`의 `ResNetMoEAgent`가 아닌 `moe_agent.py`의 `MoEAgent`를 호출하고 있음.
- **`code/optuna_optimize.py`**:
  - 이전 레거시 분류기 모델(TinyMLP, StdMLP, DecTree) 전용 지도학습 튜닝 스크립트로 현재 17개 DRL 프레임워크와는 무관.

### 3.2 모델별 하이퍼파라미터 탐색 공간 (Search Space)

| 모델군 | 최적화 대상 파라미터 | 탐색 범위 및 분포 | 비고 |
|---|---|---|---|
| **공통 DRL** | `lr` | $10^{-5} \sim 10^{-2}$ (Log-uniform) | 학습률 |
| | `gamma` | $0.90 \sim 0.999$ (Uniform) | 할인율 |
| | `batch_size` | $[32, 64, 128]$ (Categorical) | 미니배치 크기 |
| | `buffer_size` | $[10000, 50000, 100000]$ (Categorical) | 리플레이 버퍼 크기 |
| **DQN 계열**<br>(REMO, MoE, Dueling, Double, Vanilla) | `target_update_freq` | $[1, 2, 5]$ (Categorical) | 타깃 네트워크 업데이트 주기 |
| **MoE 계열**<br>(REMO-DQN, MoEDQN) | `num_experts` | $[2, 3, 4, 5]$ (Categorical) | Expert 서브네트워크 개수 |
| **PPO / MAPPO** | `eps_clip` | $0.1 \sim 0.3$ (Uniform) | PPO 클리핑 파라미터 |
| | `k_epochs` | $[3, 4, 6, 8, 10]$ (Categorical/Int) | 정책 업데이트 에포크 |
| **SAC** | `tau` | $0.001 \sim 0.01$ (Uniform) | 타깃 네트워크 소프트 업데이트 계수 |
| | `alpha` | $0.05 \sim 0.5$ (Uniform) | 엔트로피 온도 파라미터 |
| **DDPG** | `lr_actor`, `lr_critic` | $10^{-5} \sim 10^{-2}$ (Log-uniform) | 액터/크리틱 학습률 분리 |
| | `tau` | $0.001 \sim 0.01$ (Uniform) | 소프트 타깃 업데이트 계수 |
| **TD3** | `tau` | $0.001 \sim 0.01$ (Uniform) | 소프트 타깃 업데이트 계수 |
| | `policy_delay` | $[1, 2, 3]$ (Categorical/Int) | 정책 지연 업데이트 주기 |
| | `target_noise` | $0.1 \sim 0.3$ (Uniform) | 타깃 액션 노이즈 크기 |
| | `noise_clip` | $0.3 \sim 0.7$ (Uniform) | 노이즈 클리핑 상한 |
| **Tabular RL**<br>(QLearning, SARSA) | `alpha` | $0.01 \sim 0.5$ (Uniform) | Q-Learning 학습률 |
| | `gamma` | $0.90 \sim 0.999$ (Uniform) | 할인율 |
| | `epsilon_decay` | $0.90 \sim 0.999$ (Uniform) | $\epsilon$-greedy 감쇠율 |

### 3.3 목적함수 및 Pruning 전략
- **목적함수 (Objective)**:
  - 훈련 페이즈: `SimulationRunner(n_vehicles=10, duration_steps=200)` 환경에서 2 에피소드 실행 후 배치 업데이트.
  - 평가 페이즈: `SimulationRunner(n_vehicles=15, duration_steps=200)` 환경에서 1 에피소드 평가 후 `hook.episode_reward` 평균값 반환 (방향: `direction="maximize"`).
- **Pruning 설정**:
  - 현재는 시뮬레이션 예외 발생 시 `raise optuna.exceptions.TrialPruned()`로 처리.
  - 재최적화 시에는 `optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1)` 적용 및 트라이얼 수 상향(예: `n_trials=20~30`)이 권장됨.

---

## 4. 모델 학습 파이프라인 및 보상 체계 정밀 분석

### 4.1 학습 설정 규격
- **에피소드 및 스텝**: 100 에피소드, 에피소드당 2000 스텝 (총 200,000 환경 상호작용 스텝).
- **동적 차량 밀도 (Dynamic Density)**: 매 에피소드마다 `random.choice([30, 50, 100])`로 차량 수를 동적으로 무작위 전환하여 다양한 혼잡 환경에서의 일반화 성능 확보.
- **Epsilon 감쇠**: 초기 $\epsilon=1.0$에서 매 에피소드마다 $0.95$를 곱하여 최소 $\epsilon=0.01$까지 지수 감쇠 ($1.0 \rightarrow 0.95 \rightarrow 0.9025 \rightarrow \dots \rightarrow 0.01$).

### 4.2 보상 함수 (C-3 표준 구조)
- **보상 산출식** (`ai_dcc_hook.py`):
  $$R_t = r_{\text{CBR}} + r_{\text{AoI}} + r_{\text{cost}}$$
  - $r_{\text{CBR}} = -1.0 \cdot \max(0, CBR_{\text{smooth}} - 0.075) - 0.5 \cdot |CBR_{\text{smooth}} - CBR_{\text{prev}}|$
  - $r_{\text{AoI}} = -0.3 \cdot \max(0, \Delta t_{\text{cam}} - 0.5)$
  - $r_{\text{cost}} = -0.05 \cdot \frac{0.1}{\max(T_{\text{GenCam}}, 10^{-3})}$
- **음수 패널티 구조 vs 오프셋(Offset) 분석**:
  - 인위적인 $+100$이나 $+1000$ 등의 **수동 오프셋(manual offset)은 일절 포함되지 않음**.
  - 모든 항이 물리적 패널티(혼잡 초과, 채널 진동, 정보 지연, 송신 전송 비용)로 구성된 순수 음수 패널티 구조임.
  - 1 에피소드(2000 스텝, 30~100대 차량) 동안 수천 건의 CAM 송신에 대해 누적되므로 에피소드 누적 보상은 약 $-1,100,000 \sim -800,000$ 범위의 대형 음수 값을 나타내며, 정책이 개선될수록 $-800,000$ 수준으로 점진적 수렴함.

### 4.3 로깅 및 체크포인트 저장 로직
- **로그 형식**: 9컬럼 표준 CSV 포맷
  `['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean', 'Loss', 'Epsilon', 'Density']`
- **저장 경로**: `data/models/<ModelName>_convergence.csv`
- **체크포인트 저장**:
  - 매 10 에피소드 및 최종 100 에피소드 완료 시 `data/models/<ModelName>.pth` (또는 `.pkl`)에 저장.
  - 비RL 모델(Fixed10Hz, ReactDCC, AdaptDCC)은 가중치 저장 없이 `data/models/<ModelName>_convergence.csv`에 동일한 9컬럼 형식으로 평가 데이터 기록.

---

## 5. 시스템 하드웨어 가용 자원 및 병렬 학습 타당성 분석

### 5.1 하드웨어 사양 실측치

| 자원 항목 | 사양 및 실측값 | 현재 상태 및 가용성 |
|---|---|---|
| **GPU** | **NVIDIA GeForce RTX 3090 x 4개**<br>(총 96 GB VRAM, 각 24,576 MiB) | GPU 점유율 0%, VRAM 사용량 각 15~38 MiB (완전 유휴 상태) |
| **CPU** | **Intel(R) Core(TM) i9-10900X @ 3.70GHz**<br>(1 Socket, 10 Cores, 20 Threads) | 20 vCPU 전체 가용 |
| **RAM** | **128 GB (125 GiB Total)** | 현재 89 GiB Free, 108 GiB Available (매우 여유로움) |
| **CUDA / Driver** | CUDA 13.0 / Driver 580.173.02 | PyTorch CUDA 가속 정상 지원 |

### 5.2 병렬 학습 및 Sweep 실행 타당성 평가
1. **GPU 분산 병렬 학습**:
   - 4개의 RTX 3090 GPU에 13개 RL 모델을 3~4개씩 균등 분배 (`CUDA_VISIBLE_DEVICES` 지정)하여 동시 병렬 학습 가능.
   - 각 모델의 네트워크 크기가 수십 KB~수백 KB(파라미터 2만~10만 개) 수준이므로 GPU당 VRAM 점유는 1GB 미만으로 극히 안정적임.
2. **CPU 멀티프로세싱 시뮬레이션**:
   - SUMO/TraCI 시뮬레이션 환경은 CPU-bound 성격이 강하므로 20개의 가용 CPU 스레드를 활용하여 `multiprocessing.Pool(processes=8~16)` 수준으로 안전하게 동시 구동 가능.
3. **17,000 에피소드 대규모 Sweep**:
   - 17개 모델 x 10개 밀도(5, 10, ..., 50) x 100 에피소드 = 17,000 에피소드 평가를 4 GPU + 16 CPU 워커로 병렬 스케줄링 시 수 시간 내에 무결하게 완수할 수 있는 충분한 하드웨어 역량을 보유함.

---

## 6. 핵심 결함 발견 및 후속 작업 권고사항

1. **Optuna 하이퍼파라미터 튜닝 스크립트 수정**:
   - 개별 `optuna_*.py` 및 `regenerate_optunas.py`의 `action_dim=16` 하드코딩 오류를 `action_dim=24`로 일괄 수정.
   - `REMO-DQN`을 `resnet_moe_agent.py`의 `ResNetMoEAgent`를 정확히 호출하도록 수정 및 튜닝 대상에 포함.
2. **기존 가중치 및 오염 CSV 전면 퍼지(Purge)**:
   - `data/models/*.pth`, `data/models/*.pkl`, `code/*.pth`, `code/*.pkl` 및 기존 `*_convergence.csv` 파일 삭제.
3. **통합 병렬 학습 파이프라인 정비**:
   - `run_parallel_evaluation.py`에 `REMO-DQN`을 포함한 17개 전체 모델을 한 번에 제어할 수 있도록 정비하고, 4개 GPU에 분산하여 100 에피소드 재학습 진행.
