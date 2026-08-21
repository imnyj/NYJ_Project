# 16개 베이스라인 모델 훈련 및 데이터 수집 파이프라인 전수 분석 보고서

> **문서 버전**: v1.0  
> **작성 일자**: 2026-08-20  
> **작성 에이전트**: explorer_eval_survey_2 (Explorer Subagent)  
> **대상 프로젝트**: Paper 4 (REMO-DQN for Decentralized Congestion Control in V2X)

---

## 1. 개요 및 조사 목적

본 조사는 Paper 4 논문의 성능 평가 및 시각화 계획서(`visualizer/evaluation_plan.md`) 및 요구사항(`prompt_draft.md` R2)에 따라, 제안 모델인 **REMO-DQN**을 포함한 **총 17개 모델(14개 RL/DRL + 3개 표준/휴리스틱 베이스라인)**의 훈련 및 데이터 수집 파이프라인을 전수 조사하고, 100 에피소드 / 2000 스텝 / 랜덤 차량 밀도(30/50/100) 조건 하에서의 실행 및 저장 표준화 방안을 수립하는 것을 목적으로 합니다.

---

## 2. 17개 모델 전체 목록 및 스크립트/메커니즘 매핑

### 2.1 모델 분류 체계
1. **제안 모델 (Proposed DRL, 1종)**: REMO-DQN (ResNet-MoE Dueling DQN)
2. **벤치마크 심층강화학습 (Benchmark DRL, 11종)**: MoEDQN, MAPPO, PPO, SAC, DDPG, TD3, DuelingDQN, DoubleDQN, VanillaDQN, ActorCritic, DecisionTransformer
3. **테이블형 강화학습 (Tabular RL, 2종)**: QLearning, SARSA
4. **표준 및 휴리스틱 비RL 베이스라인 (Standard / Non-RL, 3종)**: Fixed 10Hz, ReactDCC (ETSI Reactive), AdaptDCC (ETSI Adaptive)

---

### 2.2 모델별 상세 사양 및 코드 매핑 매트릭스

| 번호 | 모델명 (Display Name) | 알고리즘 유형 | 에이전트 클래스 / 파일 | 개별 훈련 스크립트 | 훅(Hook) 클래스 (`ai_dcc_hook.py`) | 가중치 포맷 & 파일명 | 개별 로그 파일명 |
|:---:|:---|:---|:---|:---|:---|:---|:---|
| 1 | **REMO-DQN** | Proposed DRL (ResNet + MoE + Dueling) | `ResNetMoEAgent`<br>(`resnet_moe_agent.py`) | `train_resnet.py` | `ResNetMoEDQNHook` | PyTorch `.pth`<br>`REMO-DQN.pth` | `REMO-DQN_convergence.csv` |
| 2 | **Fixed 10Hz** | Non-RL Heuristic (Fixed 10Hz) | N/A (내장 로직) | N/A (Rule-based) | N/A (`_dcc_fixed_10hz`) | N/A (규칙 기반) | N/A (통합 CSV에 기록) |
| 3 | **ReactDCC** | ETSI Standard (EN 302 571 §8.1) | N/A (내장 로직) | N/A (Rule-based) | N/A (`_dcc_reactive`) | N/A (규칙 기반) | N/A (통합 CSV에 기록) |
| 4 | **AdaptDCC** | ETSI Standard (TS 102 687 Adaptive) | N/A (내장 로직) | N/A (Rule-based) | N/A (`_dcc_simplified_adaptive`) | N/A (규칙 기반) | N/A (통합 CSV에 기록) |
| 5 | **MoEDQN** | Benchmark DRL (MoE + Dueling) | `MoEAgent`<br>(`moe_agent.py`) | `train_moe.py` | `MoEDQNHook` | PyTorch `.pth`<br>`MoEDQN.pth` | `MoEDQN_convergence.csv` |
| 6 | **MAPPO** | Benchmark DRL (Multi-Agent PPO) | `MAPPOAgent`<br>(`mappo_agent.py`) | `optuna_mappo.py` (튜닝용) | `MAPPOHook` | PyTorch `.pth`<br>`MAPPO.pth` | `MAPPO_convergence.csv` |
| 7 | **PPO** | Benchmark DRL (On-policy Policy Grad) | `PPOAgent`<br>(`ppo_agent.py`) | `optuna_ppo.py` (튜닝용) | `PPOHook` | PyTorch `.pth`<br>`PPO.pth` | `PPO_convergence.csv` |
| 8 | **SAC** | Benchmark DRL (Off-policy Max-Entropy) | `SACAgent`<br>(`sac_agent.py`) | `optuna_sac.py` (튜닝용) | `SACHook` | PyTorch `.pth`<br>`SAC.pth` | `SAC_convergence.csv` |
| 9 | **DDPG** | Benchmark DRL (Deterministic Policy) | `DDPGAgent`<br>(`ddpg_agent.py`) | `optuna_ddpg.py` (튜닝용) | `DDPGHook` | PyTorch `.pth`<br>`DDPG.pth` | `DDPG_convergence.csv` |
| 10 | **TD3** | Benchmark DRL (Twin Delayed DDPG) | `TD3Agent`<br>(`td3_agent.py`) | `optuna_td3.py` (튜닝용) | `TD3Hook` | PyTorch `.pth`<br>`TD3.pth` | `TD3_convergence.csv` |
| 11 | **DuelingDQN** | Benchmark DRL (Value-Advantage) | `DuelingDQNAgent`<br>(`dueling_dqn_agent.py`) | `train_dueling_dqn.py` | `DuelingDQNHook` | PyTorch `.pth`<br>`DuelingDQN.pth` | `DuelingDQN_convergence.csv` |
| 12 | **DoubleDQN** | Benchmark DRL (Decoupled Target) | `DDQNAgent`<br>(`ddqn_agent.py`) | `train_ddqn.py` | `DDQNHook` | PyTorch `.pth`<br>`DoubleDQN.pth` | `DoubleDQN_convergence.csv` |
| 13 | **VanillaDQN** | Benchmark DRL (Standard DQN) | `DQNAgent`<br>(`dqn_agent.py`) | `train_dqn.py` | `VanillaDQNHook` | PyTorch `.pth`<br>`VanillaDQN.pth` | `VanillaDQN_convergence.csv` |
| 14 | **QLearning** | Tabular RL (Off-policy TD) | `QLearningAgent`<br>(`qlearning_agent.py`) | `train_qlearning.py` | `QLearningHook` | Pickle `.pkl`<br>`QLearning.pkl` | `QLearning_convergence.csv` |
| 15 | **SARSA** | Tabular RL (On-policy TD) | `SARSAAgent`<br>(`sarsa_agent.py`) | `train_sarsa.py` | `SARSAHook` | Pickle `.pkl`<br>`SARSA.pkl` | `SARSA_convergence.csv` |
| 16 | **ActorCritic** | Benchmark DRL (A2C) | `ActorCriticAgent`<br>(`actor_critic_agent.py`) | `train_actor_critic.py` | `ActorCriticHook` | PyTorch `.pth`<br>`ActorCritic.pth` | `ActorCritic_convergence.csv` |
| 17 | **DecisionTransformer** | Offline/Online Transformer DRL | `DTAgent`<br>(`dt_agent.py`) | `optuna_dt.py` (튜닝용) | `DecisionTransformerHook` | PyTorch `.pth`<br>`DecisionTransformer.pth` | `DecisionTransformer_convergence.csv` |

---

## 3. 비RL 및 표준 알고리즘 실행 메커니즘 분석

### 3.1 Fixed 10Hz
- **실행 위치**: `etsi_cam_layer.py` 내 `_dcc_fixed_10hz(self, vs)` (Line 405)
- **동작 방식**: 
  - 생성 주기: $T_{GenCam} = 0.1$ s (10 Hz 고정)
  - 송신 전력: $P_{tx} = +20$ dBm 고정
  - 채널 혼잡도(CBR)나 차량 속도, 이웃 수와 무관하게 일정한 주기로 비콘을 송출하므로, 고밀도 상황에서 채널 과부하(Packet Collision)가 발생함.

### 3.2 ReactDCC (ETSI DCC Reactive)
- **실행 위치**: `etsi_cam_layer.py` 내 `_dcc_reactive(self, vs, cbr)` (Line 359)
- **동작 방식**: 
  - ETSI EN 302 571 표준 3-State 상태 천이 기계.
  - $CBR < 0.40$: `RELAXED` 상태 $\rightarrow T_{GenCam} = 0.1$ s (10 Hz)
  - $0.40 \le CBR < 0.60$: `ACTIVE` 상태 $\rightarrow T_{GenCam} = 0.4$ s (2.5 Hz)
  - $CBR \ge 0.60$: `RESTRICTED` 상태 $\rightarrow T_{GenCam} = 1.0$ s (1 Hz)
  - 송신 전력은 $+20$ dBm 고정. 이산적인 임계값 전환으로 인해 CBR 오실레이션이 심하게 발생함.

### 3.3 AdaptDCC (ETSI DCC Adaptive)
- **실행 위치**: `etsi_cam_layer.py` 내 `_dcc_simplified_adaptive(self, vs, cbr)` (Line 373)
- **동작 방식**: 
  - ETSI TS 102 687 표준 폐루프 선형 제어기.
  - 지수 이동 평균으로 $CBR_{smoothed}$ 산출 ($\lambda_s = 0.05$).
  - $error = CBR_{smoothed} - CBR_{target}$ ($CBR_{target} = 0.60$ 또는 튜닝값).
  - $error > 0$ 이면 $T_{GenCam} \leftarrow \min(T_{GenCam} + \delta_T, T_{max})$ ($T_{max} = 1.0$ s, $\delta_T = 0.05$ s).
  - $error < 0$ 이면 $T_{GenCam} \leftarrow \max(T_{GenCam} - \delta_T, T_{min})$ ($T_{min} = 0.1$ s).

### 3.4 비RL 모델의 수렴 데이터 생성 원리
- 비RL 알고리즘은 가중치 갱신(Learning)이 없으므로 '학습 곡선'은 일정하거나 시뮬레이션 환경(밀도, 이동성)에 따른 에피소드 보상 변동을 나타냅니다.
- 17개 모델 비교 수렴 그래프 생성을 위해, 비RL 모델들도 RL 에이전트와 동일한 100개 에피소드 시뮬레이션(시드 및 랜덤 밀도 동일)을 구동하여 에피소드별 보상 $R$을 측정함으로써 공정한 비교 기준선을 형성합니다.

---

## 4. 기존 훈련/실행 파이프라인의 불일치 및 문제점 분석

기존 코드베이스를 정밀 조사한 결과, R2 요구사항 충족을 위해 해결해야 할 4가지 주요 불일치 사항이 식별되었습니다.

### 4.1 불일치 1: 차량 밀도 조건 (랜덤 밀도 30/50/100 누락)
- **현상**:
  - `train_resnet.py`, `train_moe.py`, `train_dueling_dqn.py`, `train_ddqn.py`, `train_dqn.py`, `train_qlearning.py`, `train_sarsa.py`, `train_actor_critic.py`, `run_parallel_evaluation.py` 등 모든 기존 훈련 스크립트가 `n_vehicles=50`으로 고정되어 있습니다.
- **요구사항**:
  - 매 에피소드마다 차량 밀도를 `[30, 50, 100]` 중 랜덤하게 선택(`np.random.choice([30, 50, 100])`)하여 다양한 혼잡도 조건에서 강건하게 학습되도록 해야 합니다.

### 4.2 불일치 2: 에피소드 수 및 스텝 수 불일치
- **현상**:
  - 기존 개별 스크립트(`train_dqn.py` 등)는 `num_episodes=500`, `duration_steps=1000`을 기본값으로 사용합니다.
  - `run_parallel_evaluation.py`는 `TOTAL_EPISODES=100`, `STEPS_PER_EP=2000` (총 200,000 스텝)을 사용합니다.
- **요구사항**:
  - 모든 모델의 훈련 파라미터를 `num_episodes=100`, `duration_steps=2000` (누적 200,000 스텝)으로 일관되게 통일해야 합니다.

### 4.3 불일치 3: 개별 훈련 스크립트의 파편화
- **현상**:
  - DQN 계열(REMO-DQN, MoEDQN, DuelingDQN, DoubleDQN, VanillaDQN), Tabular RL(QLearning, SARSA), ActorCritic은 개별 `train_*.py` 스크립트가 존재합니다.
  - 반면, PPO, SAC, DDPG, TD3, MAPPO, DecisionTransformer는 Optuna 튜닝 스크립트(`optuna_*.py`)만 존재하고 독립 실행용 `train_*.py`가 별도로 분리되어 있지 않으며, `run_parallel_evaluation.py` 및 `run_full_evaluation.py` 내부의 `train_worker`를 통해서만 일괄 훈련됩니다.
- **해결 방안**:
  - `run_parallel_evaluation.py` (또는 통합 배치 스크립트)를 표준 실행 진입점으로 활용하거나, 누락된 개별 훈련 스크립트를 표준화된 템플릿으로 보완해야 합니다.

### 4.4 불일치 4: 가중치 및 로그 저장 경로와 CSV 포맷 불일치
- **현상**:
  - 개별 스크립트는 `code/` 디렉토리에 소문자 파일명(`vanilla_dqn.pth`, `dqn_train_log.csv`)으로 저장하고 컬럼은 `['Episode', 'Reward', 'Loss', 'Epsilon', 'Steps', 'AoI_mean', 'CBR_mean', 'PDR_mean']`을 출력합니다.
  - 배치 러너(`run_parallel_evaluation.py`)는 `data/models/` 디렉토리에 PascalCase/대문자 파일명(`VanillaDQN.pth`, `VanillaDQN_convergence.csv`)으로 저장하며 컬럼은 `['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean']`을 출력합니다.
- **요구사항**:
  - 모든 가중치 파일은 `/home/imnyj/Workspace/paper4/data/models/{ModelName}.pth` (또는 `.pkl`)로 통일되어야 합니다.
  - 모든 개별 수렴 로그는 `/home/imnyj/Workspace/paper4/data/models/{ModelName}_convergence.csv`로 저장되고 100행의 데이터를 포함해야 합니다.

---

## 5. 16개 모델 전수 실행 및 저장 표준화 구현 방안

### 5.1 훈련 파라미터 표준 규격 (Configuration Matrix)

| 파라미터 | 표준 설정값 | 비고 |
|:---|:---|:---|
| `num_episodes` | 100 | 총 100개 에피소드 |
| `duration_steps` | 2000 | 에피소드당 2,000 스텝 |
| `total_steps` | 200,000 | 누적 20만 환경 스텝 |
| `n_vehicles` (밀도) | `random.choice([30, 50, 100])` | 매 에피소드 시작 시 랜덤 추출 |
| `seed` | `42 + episode` | 에피소드별 재현성 보장 시드 |
| `warmup_s` | 30.0 s | SUMO 네트워크 차량 진입 안정화 시간 |
| `action_dim` | 24 | 4개 주기 ($T$) $\times$ 6개 전력 ($P$) |
| `state_dim` | 5 | `cbr_global`, `n_neighbors`, `v_norm`, `dt_since_last_cam`, `cbr_smoothed` |

---

### 5.2 가중치 및 로그 파일 표준 저장 경로

```
/home/imnyj/Workspace/paper4/data/
├── models/
│   ├── REMO-DQN.pth
│   ├── REMO-DQN_convergence.csv
│   ├── MoEDQN.pth
│   ├── MoEDQN_convergence.csv
│   ├── MAPPO.pth
│   ├── MAPPO_convergence.csv
│   ├── PPO.pth
│   ├── PPO_convergence.csv
│   ├── SAC.pth
│   ├── SAC_convergence.csv
│   ├── DDPG.pth
│   ├── DDPG_convergence.csv
│   ├── TD3.pth
│   ├── TD3_convergence.csv
│   ├── DuelingDQN.pth
│   ├── DuelingDQN_convergence.csv
│   ├── DoubleDQN.pth
│   ├── DoubleDQN_convergence.csv
│   ├── VanillaDQN.pth
│   ├── VanillaDQN_convergence.csv
│   ├── QLearning.pkl
│   ├── QLearning_convergence.csv
│   ├── SARSA.pkl
│   ├── SARSA_convergence.csv
│   ├── ActorCritic.pth
│   ├── ActorCritic_convergence.csv
│   ├── DecisionTransformer.pth
│   └── DecisionTransformer_convergence.csv
├── reward_convergence.csv   # (R3) 17개 모델 전체 통합 CSV
└── ablation_study.csv       # (R3) Ablation 5개 모델 통합 CSV
```

---

### 5.3 개별 로그 CSV 표준 헤더 형식
모든 개별 모델 수렴 로그는 다음 6개 기본 컬럼을 반드시 포함하도록 규격화합니다:
```csv
Episode,Global_Step,Reward,AoI_mean,CBR_mean,PDR_mean
```
- `Episode`: 1부터 100까지의 에피소드 인덱스
- `Global_Step`: 누적 스텝 수 ($2,000, 4,000, \dots, 200,000$)
- `Reward`: 에피소드 누적 보상 ($R_{total}$)
- `AoI_mean`: 평균 정보 연령 (Age of Information, ms)
- `CBR_mean`: 평균 채널 사용률 (Channel Busy Ratio, 0.0 ~ 1.0)
- `PDR_mean`: 평균 패킷 전달률 (Packet Delivery Ratio, %)

---

### 5.4 R3 통합 데이터 추출 파이프라인 연계 방안

1. **Item 3: Comparing Reward Convergence (`data/reward_convergence.csv`)**
   - 17개 모델 전체의 에피소드별 보상을 하나의 DataFrame으로 병합:
   - Header: `Episode,Global_Step,REMO-DQN,Fixed 10Hz,ReactDCC,AdaptDCC,MoEDQN,MAPPO,PPO,SAC,DDPG,TD3,DuelingDQN,DoubleDQN,VanillaDQN,QLearning,SARSA,ActorCritic,DecisionTransformer`
   - 총 100행 (Global_Step 2,000 ~ 200,000)

2. **Item 1: Ablation Study Convergence (`data/ablation_study.csv`)**
   - 5개 핵심 DQN 구조 모델의 수렴 데이터를 병합:
   - Header: `Episode,Global_Step,REMO-DQN,MoEDQN,DuelingDQN,DoubleDQN,VanillaDQN`
   - 총 100행

---

## 6. 결론 및 후속 작업자(Coder) 권고사항

1. **병렬 훈련 파이프라인(`run_parallel_evaluation.py`) 업데이트 권고**:
   - `train_worker` 함수 내에서 `n_vehicles=50`으로 고정된 부분을 `n_vehicles = int(np.random.choice([30, 50, 100]))`로 수정.
   - `TOTAL_EPISODES=100`, `STEPS_PER_EP=2000` 설정이 완벽히 유지되는지 확인.
   - 비RL 3개 모델(Fixed 10Hz, ReactDCC, AdaptDCC)에 대해서도 동일한 100 에피소드 랜덤 밀도 조건 시뮬레이션을 수행하여 기준선 보상 데이터를 추출하고 병합하도록 확장.
2. **가중치 및 로그 정합성 유지**:
   - 모든 가중치 파일은 `data/models/*.pth` 및 `data/models/*.pkl`에 저장.
   - 14개 RL 모델의 개별 로그와 3개 비RL 기준선 데이터를 취합하여 R3 요구사항인 `data/reward_convergence.csv` 및 `data/ablation_study.csv`를 자동으로 생성하는 aggregation 로직 추가.
