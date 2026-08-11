# Paper4 M1: 14개 RL 모델 훈련 실행 환경 및 세부 설정 정밀 조사 보고서

## 1. 개요 (Executive Summary)
본 보고서는 Paper4 프로젝트 마일스톤 1(M1: Checkpoint Resume & Model Training) 달성을 위하여 **14개 RL 모델의 훈련 실행 환경, 멀티프로세싱 및 GPU 할당 구조, 시드 설정, 전체 14개 모델 및 Optuna 파라미터 매핑, 로그 출력 및 예외 처리 로직**을 정밀 조사 및 분석한 결과를 담고 있습니다.

---

## 2. Python 실행 가상환경 및 주요 패키지 버전
- **가상환경 실행 경로**: `/home/imnyj/venv/bin/python`
- **Python 버전**: `3.12.3`
- **PyTorch 및 CUDA 환경**:
  - `PyTorch Version`: `2.11.0+cu130`
  - `CUDA Available`: `True` (CUDA 13.0 지원 환경)
- **주요 관련 패키지 버전**:
  - `NumPy`: `2.4.4`
  - `Pandas`: `2.3.3`
  - `SciPy`: `1.17.1`
  - `Matplotlib`: `3.10.8`
  - `tqdm`: `4.67.3`
  - `gym` / `gymnasium`: 설치되지 않음 (프로젝트 자체 커스텀 V2X 시뮬레이터인 `code/sim_engine.py` 기반으로 작동)

---

## 3. `run_parallel_evaluation.py` 실행 구조, 멀티프로세싱 및 시드 분석

### 3.1 실행 구조 및 엔트리 포인트
- 파일 위치: `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py`
- 별도의 CLI 인자 처리기(`argparse`)는 작성되어 있지 않으며, `python code/run_parallel_evaluation.py` 실행 시 `main()` 함수에서 `PART 1 (훈련 수렴)`과 `PART 2 (병렬 평가)`가 순차적으로 직렬 실행됩니다.

### 3.2 멀티프로세싱 및 GPU 할당 설정
- **프로세스 및 GPU 수**: `num_gpus = 4` (Line 272)
- **병렬 처리 방식**: `multiprocessing.Pool(processes=4)`
- **GPU 라운드로빈 할당**:
  - `train_worker`: 모델 순서 `i` (0~13)에 대해 `gpu_id = i % 4` 할당 후 프로세스 내부에서 `os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)` 설정.
  - `eval_worker`: 평가 태스크 순서 `task_idx`에 대해 `gpu_id = task_idx % 4` 할당.
- **프로세스 동속성(Locking)**:
  - 평가 데이터 파일(`eval_density_results.csv`, `eval_speed_results.csv`) append 시 병렬 작성 충돌 방지를 위해 `multiprocessing.Manager().Lock()`을 `eval_worker`에 전달하여 사용.

### 3.3 시드(Seed) 및 에피소드/스텝 설정
- **훈련 시드 (Training Seed)**:
  - 각 에피소드 `ep` (0~99)마다 시드가 `42 + ep`로 변동 적용됨 (`SimulationRunner(..., seed=42 + ep, ...)`).
  - 에피소드 당 시뮬레이션 스텝: `STEPS_PER_EP = 2000`
  - 총 훈련 에피소드 수: `TOTAL_EPISODES = 100` (총 200,000 global steps)
- **평가 시드 (Evaluation Seed)**:
  - 각 환경 설정(밀도/속도 변수) 및 모델별로 3개 시드 `[111, 222, 333]`를 사용하여 반복 측정.
  - 차량 밀도 sweep: `[20, 40, 60, 80, 100, 120]`
  - 차량 속도 sweep: `[20, 40, 60, 80, 100]`
  - 평가 시 step: `duration_steps = 1000`, `warmup_s = 30.0`

---

## 4. 14개 전체 RL 모델 매핑 및 Optuna 하이퍼파라미터

### 4.1 14개 RL 모델 매핑 현황 (`rl_methods`)
`run_parallel_evaluation.py` (Line 40~55)에 정의된 14개 모델 목록은 다음과 같습니다:

| # | Model Display Name | Internal Hook Name | Agent Class | Model File Extension |
|---|--------------------|-------------------|-------------|---------------------|
| 1 | `QLearning` | `QLearning` | `QLearningAgent` | `.pkl` |
| 2 | `SARSA` | `SARSA` | `SARSAAgent` | `.pkl` |
| 3 | `ActorCritic` | `ActorCritic` | `ActorCriticAgent` | `.pth` |
| 4 | `VanillaDQN` | `VanillaDQN` | `DQNAgent` | `.pth` |
| 5 | `DoubleDQN` | `DoubleDQN` | `DDQNAgent` | `.pth` |
| 6 | `DuelingDQN` | `DuelingDQN` | `DuelingDQNAgent` | `.pth` |
| 7 | `DDPG` | `DDPG` | `DDPGAgent` | `.pth` |
| 8 | `PPO` | `PPO` | `PPOAgent` | `.pth` |
| 9 | `SAC` | `SAC` | `SACAgent` | `.pth` |
| 10 | `TD3` | `TD3` | `TD3Agent` | `.pth` |
| 11 | `DecisionTransformer` | `DecisionTransformer` | `DTAgent` | `.pth` |
| 12 | `MAPPO` | `MAPPO` | `MAPPOAgent` | `.pth` |
| 13 | `MoEDQN` | `MoEAgent` | `MoEAgent` | `.pth` |
| 14 | `REMO-DQN` *(Proposed)* | `ResNetMoEDQN` | `ResNetMoEAgent` | `.pth` |

* 추가 비 RL 비교군 (7개): `["Proposed", "StdMLP", "DecTree", "ReactDCC", "AdaptDCC", "Heuristic", "Fixed10Hz"]`

### 4.2 Optuna 하이퍼파라미터 자동 로딩
- `load_optuna_params(method_name)` 함수는 `/home/imnyj/Workspace/paper4/data/optuna/best_params_{method_name}.csv`에서 파라미터를 파싱하여 `create_agent()`에 적용합니다.
- `data/optuna/` 디렉토리에 14개 모든 모델의 `best_params_*.csv` 파일이 준비되어 있음을 확인하였습니다.

### 4.3 현재 훈련 중단 및 기존 수렴 파일 현황 (`data/models/`)
현재 `/home/imnyj/Workspace/paper4/data/models/` 디렉토리 조사 결과, 진행되다 중단된 수렴 로그 파일이 확인되었습니다:
- `ActorCritic_convergence.csv`: 34 에피소드 기록
- `QLearning_convergence.csv`: 63 에피소드 기록
- `SARSA_convergence.csv`: 63 에피소드 기록
- `VanillaDQN_convergence.csv`: 50 에피소드 기록

---

## 5. 훈련 실행 시 로그 출력 및 예외 처리 방안 확인

### 5.1 로그 출력 및 저장 구조
1. **콘솔 로그 (stdout)**:
   - 훈련 시작: `--- Training {name} on GPU {gpu_id} ---`
   - 매 10 에피소드 마다: `[{name}] Ep {ep+1}/100 - Reward: {ep_reward:.2f}`
   - 훈련 완료: `Saved {name} to {model_path}`
   - 건너뜀 조건 달성 시: `[{name}] Already trained. Skipping...`
2. **CSV 파일 로그 (`{name}_convergence.csv`)**:
   - 저장 위치: `data/models/{name}_convergence.csv`
   - 컬럼: `Episode`, `Global_Step`, `Reward`, `AoI_mean`, `CBR_mean`, `PDR_mean`
   - 저장 시점: 매 에피소드 종료 직후 `csv.writer`를 사용해 append 방식으로 기록.

### 5.2 예외 처리 및 취약점 방안 분석
1. **현재 예외 처리 구조**:
   - `train_worker`와 `eval_worker` 함수 전체가 `try ... except Exception as e:` 블록으로 감싸져 있습니다.
   - 예외 발생 시 `traceback.print_exc()`로 에러 로그를 출력하고 `None`(훈련) 또는 `False`(평가)를 반환합니다.
   - 이를 통해 멀티프로세싱 풀(Pool) 전체가 일방적으로 비정상 종료되는 것을 방지합니다.

2. **개선이 시급한 취약점 요인**:
   - **체크포인트 Overwrite 이슈 (R1 결함)**:
     - 현재 `train_worker`는 훈련을 시작할 때 `open(log_path, 'w')`로 파일 쓰기를 시작합니다 (Line 144).
     - 이는 이미 에피소드 50~63까지 훈련되어 있던 `QLearning`, `SARSA`, `VanillaDQN`, `ActorCritic` 등의 진행 기록을 에피소드 0으로 초기화 덮어쓰게 만듭니다.
     - 기존 로그가 존재할 경우 마지막 기록된 에피소드 지점을 감지하고 `open(log_path, 'a')`로 이어쓰며, 에피소드 루프 시작을 `start_ep`부터 100까지 수행하고 모델 가중치를 load하는 **Checkpoint Resume** 기능 개선이 필요합니다.
   - **중간 모델 가중치 미저장**:
     - 현재는 100 에피소드가 모두 완료된 후에만 `agent.save(model_path)`가 호출됩니다 (Line 186).
     - 훈련 도중 타임아웃이나 예외가 발생하는 경우 가중치가 저장되지 않는 위험이 있습니다. 매 10 에피소드 또는 에피소드 완료 시 중간 가중치 저장 기능이 보완되어야 합니다.
