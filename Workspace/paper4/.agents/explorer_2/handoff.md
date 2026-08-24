# [Handoff Report] Paper4 전체 17개 모델 훈련 및 평가 파이프라인 전수 조사 보고서

## 1. Observation (직접 관측 사실)

### 1.1. 17개 모델 전체 목록 및 아키텍처 분류
`/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`(28~47줄), `code/ai_dcc_hook.py`(417~460줄), `code/run_parallel_evaluation.py`(45~63줄), `code/etsi_cam_layer.py`(340~410줄)를 통해 확인된 17개 모델의 정의 및 구현 매핑은 다음과 같습니다.

| No. | 모델명 (Method) | 카테고리 | 구현 클래스 및 소스 파일 | Action Dim | Hook 매핑 (`ai_dcc_hook.py`) |
|:---:|:---|:---|:---|:---:|:---|
| 1 | **REMO-DQN (Proposed)** | 제안 하이브리드 DRL | `ResNetMoEAgent` (`code/resnet_moe_agent.py`) | 24 | `ResNetMoEDQNHook` |
| 2 | **Fixed 10Hz** | 비RL 고정 규칙 | `_dcc_fixed_10hz` (`code/etsi_cam_layer.py`) | N/A (10Hz, 20dBm) | 내장 DCC |
| 3 | **ReactDCC** | 비RL ETSI 표준 | `_dcc_reactive` (`code/etsi_cam_layer.py`) | N/A (3상태 천이) | 내장 DCC |
| 4 | **AdaptDCC** | 비RL ETSI 표준 | `_dcc_simplified_adaptive` (`code/etsi_cam_layer.py`) | N/A (적응형 주기) | 내장 DCC |
| 5 | **MoEDQN** | DQN 계열 DRL | `MoEAgent` (`code/moe_agent.py`) | 24 | `MoEDQNHook` |
| 6 | **MAPPO** | Multi-Agent Policy Gradient | `MAPPOAgent` (`code/mappo_agent.py`) | 24 | `MAPPOHook` |
| 7 | **PPO** | Single-Agent Policy Gradient | `PPOAgent` (`code/ppo_agent.py`) | 24 | `PPOHook` |
| 8 | **SAC** | Max-Entropy Actor-Critic | `SACAgent` (`code/sac_agent.py`) | 24 | `SACHook` |
| 9 | **DDPG** | Deterministic Policy Gradient | `DDPGAgent` (`code/ddpg_agent.py`) | 24 | `DDPGHook` |
| 10 | **TD3** | Twin Delayed DDPG | `TD3Agent` (`code/td3_agent.py`) | 24 | `TD3Hook` |
| 11 | **DuelingDQN** | DQN 계열 DRL | `DuelingDQNAgent` (`code/dueling_dqn_agent.py`) | 24 | `DuelingDQNHook` |
| 12 | **DoubleDQN** | DQN 계열 DRL | `DDQNAgent` (`code/ddqn_agent.py`) | 24 | `DDQNHook` |
| 13 | **VanillaDQN** | DQN 계열 DRL | `DQNAgent` (`code/dqn_agent.py`) | 24 | `VanillaDQNHook` |
| 14 | **QLearning** | Tabular RL | `QLearningAgent` (`code/qlearning_agent.py`) | 24 | `QLearningHook` |
| 15 | **SARSA** | Tabular RL | `SARSAAgent` (`code/sarsa_agent.py`) | 24 | `SARSAHook` |
| 16 | **ActorCritic** | Policy Gradient (A2C) | `ActorCriticAgent` (`code/actor_critic_agent.py`) | 24 | `ActorCriticHook` |
| 17 | **DecisionTransformer** | Sequence/Transformer RL | `DTAgent` (`code/dt_agent.py`) | 24 | `DecisionTransformerHook` |

---

### 1.2. 모델 가중치(`data/models/`) 및 훈련 로그 현황

#### (1) 가중치 파일 (`data/models/`)
총 14종 RL/DRL 모델의 가중치가 저장되어 있음을 확인하였습니다.
- `ActorCritic.pth` (81,607 바이트)
- `DDPG.pth` (88,777 바이트)
- `DecisionTransformer.pth` (422,987 바이트)
- `DoubleDQN.pth` (43,373 바이트)
- `DuelingDQN.pth` (44,151 바이트)
- `MAPPO.pth` (83,355 바이트)
- `MoEDQN.pth` (217,613 바이트)
- `PPO.pth` (80,759 바이트)
- `QLearning.pkl` (6,400,393 바이트)
- `REMO-DQN.pth` (533,661 바이트) / `resnet_moe_dqn.pth` (533,925 바이트)
- `SAC.pth` (125,965 바이트)
- `SARSA.pkl` (6,400,393 바이트)
- `TD3.pth` (134,669 바이트)
- `VanillaDQN.pth` (80,569 바이트)
*(비RL 3종은 학습 가중치가 불필요하므로 가중치 파일 없음)*

#### (2) 훈련 수렴 로그 파일 (`data/models/*_convergence.csv`)
- `REMO-DQN_convergence.csv`: **9개 에피소드** (885 바이트)
  - 컬럼 헤더 (9개 열): `Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean, Loss, Epsilon, Density`
- 13종 베이스라인 DRL/RL 모델 (`ActorCritic_convergence.csv`, `DDPG_convergence.csv` 등 13개): 각각 **100개 에피소드** 존재 (약 5,050 바이트)
  - 컬럼 헤더 (6개 열): `Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean`
  - **결함 사항**: `Loss, Epsilon, Density` 3개 열이 누락되어 있으며, 과거 고정 밀도(50) 실행으로 생성됨.
- `data/reward_convergence.csv`: 100행 × 19열 (17개 모델의 보상 수렴 곡선 집계 데이터). 비RL 3종(Fixed 10Hz, ReactDCC, AdaptDCC)은 각각 `-995000.0`, `-982000.0`, `-978000.0`의 상수 기준선으로 기재됨.

#### (3) 로컬 코드 디렉토리 로그 (`code/*_train_log.csv`)
- `resnet_train_log.csv`: 9행 (REMO-DQN 9개 에피소드, `data/models/REMO-DQN_convergence.csv`와 동기화됨)
- 11종 RL 로그 (`actor_critic`, `ddpg`, `ddqn`, `dt`, `mappo`, `moe`, `ppo`, `qlearning`, `sac`, `sarsa`, `td3` `_train_log.csv`): 5행 (과거 5에피소드 스모크 테스트 로그 잔존)
- `dqn_train_log.csv`: 0행 (헤더만 존재)

#### (4) 백그라운드 프로세스 상태 점검
- `ps aux | grep python` 및 `ps aux | grep sumo` 실행 결과:
  - PID 97001을 포함하여 현재 실행 중인 훈련 또는 SUMO 시뮬레이션 프로세스가 **전혀 없음** (유휴 상태).

---

### 1.3. 훈련 및 평가 파이프라인 스크립트 분석

#### (1) `train_resnet.py` (REMO-DQN 전용 진입점)
- 위치: `/home/imnyj/Workspace/paper4/code/train_resnet.py`
- 파라미터 기본값: `num_episodes=100`, `duration_steps=2000`, `epsilon_decay=0.95`, `min_epsilon=0.01`
- 밀도 샘플링: `density = random.choice([30, 50, 100])`
- 로깅 포맷: `['Episode', 'Global_Step', 'Reward', 'AoI_mean', 'CBR_mean', 'PDR_mean', 'Loss', 'Epsilon', 'Density']` (9개 열 완벽 준수)
- 타겟 저장소: `data/models/REMO-DQN_convergence.csv`, `data/models/resnet_moe_dqn.pth`, `data/models/REMO-DQN.pth`, `code/resnet_train_log.csv`

#### (2) 기존 개별 훈련 스크립트 7종
- 대상: `train_dqn.py`, `train_ddqn.py`, `train_dueling_dqn.py`, `train_moe.py`, `train_qlearning.py`, `train_sarsa.py`, `train_actor_critic.py`
- 상태:
  - 구 M-10 규격(`num_episodes=500`, `duration_steps=1000`, `epsilon_decay=0.995`, 고정 밀도 `n_vehicles=50`)으로 남아 있음.
  - CSV 헤더가 `['Episode', 'Reward', 'Loss', 'Epsilon', 'Steps', 'AoI_mean', 'CBR_mean', 'PDR_mean']` (8개 열)로 되어 있어 `Global_Step`, `Density`가 누락됨.
  - 저장 경로가 로컬 상대 경로 (`dqn_train_log.csv`, `vanilla_dqn.pth` 등)로 분산됨.

#### (3) 단독 훈련 스크립트 부재 모델 6종
- 대상: `PPO`, `DDPG`, `SAC`, `TD3`, `DecisionTransformer`, `MAPPO`
- 상태: `optuna_*.py` 스크립트만 존재하며, 단독 `train_*.py` 파일은 없음 (`run_parallel_evaluation.py` 내의 `train_worker`를 통해서만 일괄 훈련 가능).

#### (4) 병렬 훈련 및 평가 통합 러너 (`run_parallel_evaluation.py` & `run_full_evaluation.py`)
- 위치: `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py`
- 상태:
  - `TOTAL_EPISODES = 100`, `STEPS_PER_EP = 2000` 설정되어 있음.
  - 하지만 밀도가 고정 `n_vehicles = 50`으로 하드코딩되어 있고, CSV 컬럼이 6열(`Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean`)로 작성됨.
  - 재개 로직(`start_ep >= TOTAL_EPISODES`)으로 인해 이미 100행이 채워진 `data/models/*_convergence.csv` 파일이 있을 경우 훈련을 즉시 Skip함.

#### (5) 비RL 모델 평가 파이프라인 (`Fixed10Hz`, `ReactDCC`, `AdaptDCC`)
- 위치: `code/etsi_cam_layer.py`, `code/sensitivity_runner.py`, `code/run_parallel_evaluation.py`
- 상태:
  - `etsi_cam_layer.py` 내에 ETSI Reactive DCC, Simplified Adaptive DCC, Fixed 10Hz 로직이 완벽히 내장되어 있음.
  - `sensitivity_runner.py` (SA1 밀도 스윕, SA2 DCC 방식 비교) 및 `run_parallel_evaluation.py`(밀도 20~120, 속도 20~100 스윕)를 통해 평가 및 메트릭스 추출이 수행됨.

---

## 2. Logic Chain (논리적 추론 체계)

1. **사용자 최신 요구사항**:
   - 17개 모델(제안 1종, 비RL 3종, RL/DRL 13종) 전수에 대해 100 에피소드 × 2000 스텝 (epsilon decay=0.95, random density 30/50/100) 훈련 및 평가가 요구됨.
   - 훈련 CSV 로그는 `Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean, Loss, Epsilon, Density` (9열) 형식을 반드시 준수해야 함.
2. **현 상태 평가**:
   - **REMO-DQN**: `train_resnet.py`가 100에피소드/2000스텝/랜덤밀도/9열 포맷을 완벽히 구현하였으나, 9에피소드 시점에 중단되어 추가 91에피소드 완료가 필요함.
   - **13종 DRL/RL 모델**: `data/models/`에 100에피소드 로그가 있으나, 과거 구버전 러너로 실행되어 6열 포맷에 고정밀도(50)로 기록되었으며, `code/` 디렉토리에는 5에피소드 스모크 로그만 남아 있음.
   - **훈련 스크립트 정합성 결여**: 개별 `train_*.py` 7종은 500에피소드/8열 포맷에 머물러 있고, 6종 모델은 개별 스크립트조차 없으며, 통합 러너 `run_parallel_evaluation.py` 역시 6열/고정밀도로 작성되어 있어 현재 상태로 재실행 시 9열 포맷 요구사항을 충족할 수 없음.
3. **해결 및 파이프라인 통합 방안 도출**:
   - `run_parallel_evaluation.py` (또는 신규 일괄 파이프라인 러너)의 `train_worker`를 수정하여 `random.choice([30, 50, 100])`, `epsilon_decay=0.95`, `9열 CSV 포맷`을 전 모델에 동일하게 적용해야 함.
   - `train_resnet.py`의 9에피소드 이후 100에피소드 완주 및 수렴 검증(`verify_remo_convergence.py`)이 최우선 선행되어야 함.

---

## 3. Caveats (제약 사항 및 고려 요소)

1. **소요 시간 (Runtime Budget)**:
   - SUMO 시뮬레이션 기반 에피소드당 약 40~70초(2000스텝)가 소요되므로, 1개 모델 100에피소드 완주에 약 1.5~2시간 소요됨.
   - 14개 RL 모델을 순차 실행하면 20시간 이상 소요되므로, 반드시 다중 GPU/멀티프로세싱 병렬화(`run_parallel_evaluation.py` 구조)가 필수적임.
2. **비RL 모델 처리**:
   - `Fixed10Hz`, `ReactDCC`, `AdaptDCC`는 정책 학습 및 가중치 업데이트가 없으므로 수렴 훈련 대상이 아니며, 시뮬레이션 평가(스윕) 데이터 추출 대상임.
3. **가중치 호환성**:
   - 액션 차원이 `ACTION_DIM = 24`로 통일되었으므로, 모든 DRL 모델이 `action_dim=24`로 초기화 및 훈련되어야 함 (`check: ACTION_DIM=24 verified`).

---

## 4. Conclusion (결론 및 실행 계획)

1. **17개 모델 분류 체계 및 상태 확정**:
   - 제안 모델 1종 (`REMO-DQN`)
   - 비RL 표준/베이스라인 3종 (`Fixed10Hz`, `ReactDCC`, `AdaptDCC`)
   - DRL/RL 벤치마크 13종 (`VanillaDQN`, `DoubleDQN`, `DuelingDQN`, `MoEDQN`, `PPO`, `MAPPO`, `SAC`, `DDPG`, `TD3`, `QLearning`, `SARSA`, `ActorCritic`, `DecisionTransformer`)
2. **훈련 파이프라인 개정 필요성**:
   - `run_parallel_evaluation.py`의 `train_worker`를 업데이트하여 **100에피소드 × 2000스텝**, **랜덤 밀도 `[30, 50, 100]`**, **`epsilon_decay=0.95`**, **9열 CSV (`Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean, Loss, Epsilon, Density`)** 저장을 전 모델에 일괄 적용하도록 수정해야 함.
3. **우선순위 실행 순서**:
   - **Step 1**: `train_resnet.py`를 실행하여 REMO-DQN 잔여 에피소드(10~100) 훈련 완료 및 `verify_remo_convergence.py`로 수렴 통계 검증.
   - **Step 2**: 13종 RL 모델의 일괄 병렬 훈련 실행 (100 Ep × 2000 Step, 9열 CSV 저장).
   - **Step 3**: 3종 비RL 및 14종 RL 전체에 대한 평가 스윕(`eval_density_results.csv`, `eval_speed_results.csv`) 실행 및 시각화 데이터 병합.

---

## 5. Verification Method (독립 검증 방법)

오케스트레이터 및 후속 에이전트는 다음 명령어를 통해 본 보고서의 내용을 물리적으로 즉시 재검증할 수 있습니다.

1. **14종 가중치 및 CSV 파일 목록 검증**:
   ```bash
   python3 -c "import glob, os, pandas as pd; [print(os.path.basename(f), len(pd.read_csv(f)) if f.endswith('.csv') else os.path.getsize(f)) for f in sorted(glob.glob('/home/imnyj/Workspace/paper4/data/models/*'))]"
   ```
2. **REMO-DQN 로그 9열 포맷 및 행수 확인**:
   ```bash
   head -n 2 /home/imnyj/Workspace/paper4/data/models/REMO-DQN_convergence.csv
   wc -l /home/imnyj/Workspace/paper4/data/models/REMO-DQN_convergence.csv
   ```
3. **14개 RL 에이전트 인스턴스화 및 ACTION_DIM=24 검증**:
   ```bash
   python3 -c "import sys; sys.path.insert(0, '/home/imnyj/Workspace/paper4/code'); from etsi_cam_layer import ACTION_DIM; print('ACTION_DIM:', ACTION_DIM)"
   ```
4. **프로세스 유휴 상태 검증**:
   ```bash
   ps aux | grep -E 'python|sumo' | grep -v grep
   ```
