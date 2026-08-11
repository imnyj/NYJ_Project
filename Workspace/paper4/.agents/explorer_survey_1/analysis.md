# Paper4 Codebase & Model Training Resume Analysis Report

## 1. Codebase Architecture & Key Modules

`/home/imnyj/Workspace/paper4` 프로젝트는 V2X (Vehicle-to-Everything) 통신 환경에서 ETSI CAM (Cooperative Awareness Message) 전송 주기 및 전송 파워를 동적으로 제어하여 차량 혼잡(CBR, Channel Busy Ratio) 및 정보 최신성(AoI, Age of Information)을 최적화하기 위한 하이브리드 DRL 기반 모델(ResNet-MoE-Dueling DQL, 본 논문 제안 REMO-DQN) 및 13종의 비교군 모델을 포함하고 있습니다.

### 핵심 디렉토리 및 모듈 구상
- **`code/` (핵심 실행 및 연구 코드)**:
  - `run_parallel_evaluation.py`: 14개 RL 모델의 병렬 훈련 및 밀도/속도 스위프 평가를 총괄 수행하는 마스터 스크립트.
  - `sim_engine.py` (`SimulationRunner`): 도시 격자(Urban Grid) V2X 통신 환경 기반 시뮬레이션 엔진. 차량 밀도, 이동 속도, CAM 생성 이벤트, PDR/CBR/AoI 지표 계산 수행.
  - `ai_dcc_hook.py`: ETSI CAM DCC 규격과 RL Agent 간의 인터페이스. 각 에피소드 및 스텝별 상태(State) 추출 및 액션(Action) 적용 hook 클래스 제공 (`ResNetMoEDQNHook`, `DuelingDQNHook` 등).
  - 14개 RL Agent 구현체:
    - `resnet_moe_agent.py` (`ResNetMoEAgent` / `ResNetMoEDQN`): 제안 모델 (REMO-DQN)
    - `qlearning_agent.py` (`QLearningAgent`), `sarsa_agent.py` (`SARSAAgent`)
    - `actor_critic_agent.py` (`ActorCriticAgent`), `dqn_agent.py` (`DQNAgent`), `ddqn_agent.py` (`DDQNAgent`), `dueling_dqn_agent.py` (`DuelingDQNAgent`)
    - `ddpg_agent.py` (`DDPGAgent`), `ppo_agent.py` (`PPOAgent`), `sac_agent.py` (`SACAgent`), `td3_agent.py` (`TD3Agent`)
    - `dt_agent.py` (`DTAgent`), `mappo_agent.py` (`MAPPOAgent`), `moe_agent.py` (`MoEAgent`)
- **`data/` (데이터 및 모델 체크포인트 저장소)**:
  - `data/models/`: 모델 convergence 훈련 로그 (`*_convergence.csv`) 및 최종/중간 가중치 파일 (`*.pth`, `*.pkl`) 저장 디렉토리.
  - `data/optuna/`: 모델별 Optuna 하이퍼파라미터 최적화 결과 (`best_params_*.csv`).
  - `data/evaluation/`: 평가 스크립트의 실행 결과 (`eval_density_results.csv`, `eval_speed_results.csv`).
- **`.agents/` (에이전트 메타데이터 및 핸드오프 저장소)**:
  - `/home/imnyj/Workspace/paper4/.agents/`: 멀티 에이전트 시스템 메타데이터 및 `ORIGINAL_REQUEST.md`.

---

## 2. 14개 전체 모델 종류 및 구성 파악

`run_parallel_evaluation.py`에서 정의된 `rl_methods` 14개 모델의 구성은 다음과 같습니다:

| 순번 | 모델 식별자 (Method Name) | Agent 클래스 | 주요 구조 및 특성 |
|-----|-------------------------|-------------|-----------------|
| 1 | **REMO-DQN** (제안 기법) | `ResNetMoEAgent` (`ResNetMoEDQN`) | ResNet Feature Extractor (128 hidden, 2 Residual Blocks) + Gating Network + 3 Dueling Experts (Value & Advantage Stream 분리) |
| 2 | **QLearning** | `QLearningAgent` | Tabular Q-Learning (상태 공간 10-bin 이산화) |
| 3 | **SARSA** | `SARSAAgent` | Tabular SARSA (상태 공간 10-bin 이산화) |
| 4 | **ActorCritic** | `ActorCriticAgent` | Advantage Actor-Critic (A2C, Policy Network + Value Network) |
| 5 | **VanillaDQN** | `DQNAgent` | Standard Deep Q-Network (Replay Buffer + Target Network) |
| 6 | **DoubleDQN** | `DDQNAgent` | Double DQN (액션 선택과 Q-값 평가 분리) |
| 7 | **DuelingDQN** | `DuelingDQNAgent` | Dueling Architecture (State Value $V(s)$와 Advantage $A(s,a)$ 분리) |
| 8 | **DDPG** | `DDPGAgent` | Deep Deterministic Policy Gradient |
| 9 | **PPO** | `PPOAgent` | Proximal Policy Optimization (Clipped Surrogate Objective) |
| 10 | **SAC** | `SACAgent` | Soft Actor-Critic (Maximum Entropy RL) |
| 11 | **TD3** | `TD3Agent` | Twin Delayed Deep Deterministic Policy Gradient |
| 12 | **DecisionTransformer** | `DTAgent` | Sequence Modeling / Offline RL Transformer 구조 |
| 13 | **MAPPO** | `MAPPOAgent` | Multi-Agent PPO (Centralized Critic, Decentralized Actor) |
| 14 | **MoEDQN** | `MoEAgent` | Standard MoE DQN (2 experts, Softmax Gating) |

---

## 3. 체크포인트 저장/로드 방식 및 에피소드 52 부근 현황 분석

### (1) 기존 코드 (`run_parallel_evaluation.py`)의 훈련 및 체크포인트 로직
- `MODELS_DIR = "/home/imnyj/Workspace/paper4/data/models"`
- `train_worker` 함수에서:
  1. `model_path`와 `log_path` 존재 여부를 확인하고, `len(lines) > 95` (완료)인 경우에만 skipping.
  2. 만약 완료되지 않았거나 중단된 경우 (`len(lines) <= 95`):
     - `with open(log_path, 'w')`로 열어서 **기존 CSV 로그를 전부 덮어써서 초기화**.
     - `for ep in range(TOTAL_EPISODES):` (즉, `ep = 0`부터 다시 시작).
     - **중간 체크포인트 저장 부재**: `agent.save(model_path)`가 100 에피소드 루프가 완전히 종료된 후(line 186)에만 호출됨.

### (2) 기존 체크포인트/로그 파일 실측 현황 (`/home/imnyj/Workspace/paper4/data/models/`)
현재 `/home/imnyj/Workspace/paper4/data/models/` 디렉토리에 존재하는 수렴 로그 파일 검토 결과:
- `QLearning_convergence.csv`: 63개 에피소드 완료 (Line 53에 Episode 52 데이터 존재)
- `SARSA_convergence.csv`: 63개 에피소드 완료 (Line 53에 Episode 52 데이터 존재)
- `VanillaDQN_convergence.csv`: 50개 에피소드 완료
- `ActorCritic_convergence.csv`: 34개 에피소드 완료
- 나머지 10개 모델: GPU 4개 프로세스 풀(`num_gpus = 4`)에 밀려 대기 중 중단되어 로그 파일 미생성 상태.

**문제 원인 파악**:
이전 실행 시 GPU 4개로 multiprocessing Pool이 실행되며 0~3번 모델(QLearning, SARSA, ActorCritic, VanillaDQN)이 동시에 훈련 진행 중, 에피소드 50~63 부근에서 작업이 중단(Interrupted)되었습니다. 그러나 `agent.save()`가 에피소드 100 종료 시점에만 작성되어 있었기 때문에 `.pth` / `.pkl` 모델 가중치는 `data/models/`에 저장되지 못했고, 로그 파일만 CSV로 에피소드 34~63까지 기록된 상태입니다.

---

## 4. 훈련 재개(Resume)를 위한 코드 수정 포인트 분석

`run_parallel_evaluation.py`의 `train_worker` 스크립트를 재개 가능하도록 수정하기 위해 필요한 구체적 변경사항:

### 수정 포인트 1: 기존 완료 에피소드 수 자동 감지 (Resume Point Detection)
`log_path` (`*_convergence.csv`)가 존재하는 경우, 헤더를 제외한 유효 데이터 행(line) 수를 파악하여 `start_ep`를 계산합니다.
```python
start_ep = 0
if os.path.exists(log_path):
    with open(log_path, 'r') as f:
        lines = [l for l in f.readlines() if l.strip()]
        if len(lines) > 1:
            start_ep = len(lines) - 1 # 헤더 제외
```

### 수정 포인트 2: 체크포인트 가중치 로드 & 덮어쓰기 방지 (Append Mode & Model Load)
- `start_ep >= TOTAL_EPISODES` (100 에피소드 이상): 훈련 완료로 판정하고 Skip.
- `0 < start_ep < TOTAL_EPISODES`:
  - 기존 모델 파일 (`model_path`)이 존재하는 경우 `agent.load(model_path)` 호출.
  - `agent.epsilon` 값을 복원된 에피소드 수에 맞춰 감쇠 업데이트: `agent.epsilon = max(agent.epsilon_end, agent.epsilon * (agent.epsilon_decay ** start_ep))`.
  - `log_path` 파일을 `'a'` (append) 모드로 오픈하여 기존 로그 보존.
  - `global_step`을 `start_ep * STEPS_PER_EP`로 설정.
- `start_ep == 0`: `'w'` 모드로 신규 오픈 및 헤더 기록.

### 수정 포인트 3: 주기적 체크포인트 저장 (Periodic Checkpointing)
훈련 도중 프로세스 중단에 대비하여, 에피소드 루프 내부에서 매 에피소드(또는 매 5~10 에피소드 및 최종 종료 시)마다 `agent.save(model_path)`를 호출하도록 수정합니다.
```python
# 에피소드 루프 내부
if (ep + 1) % 5 == 0 or (ep + 1) == TOTAL_EPISODES:
    agent.save(model_path)
```

---

## 5. 결론 및 향후 계획

1. **상태 종합**: 현재 `paper4` 프로젝트는 14개 전체 모델의 훈련 재개 준비 상태이며, `run_parallel_evaluation.py` 스크립트 수정 시 에피소드 52 부근(34~63 에피소드)부터 손실 없이 훈련을 이어서 완료할 수 있습니다.
2. **오케스트레이터 전달 내용**: Coder 에지언트가 `run_parallel_evaluation.py` 수정 후 훈련을 실행하고, 이후 Evaluator 및 Visualizer 에이전트가 성능 평가 csv 및 IEEE 스타일 그래프를 생성할 수 있도록 명확한 전략 보고서를 구성함.
