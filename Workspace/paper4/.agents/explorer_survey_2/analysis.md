# Paper4 성능 평가 파이프라인 및 데이터 분석 보고서

본 문서는 Paper4 프로젝트의 성능 평가 관련 스크립트, 데이터 파이프라인, 모델 가중치 로딩 방식, 지표 계산 로직 및 출력 CSV 데이터 스키마에 대한 상세 조사 결과를 담고 있습니다.

---

## 1. 차량 밀도(Density) 및 속도(Speed) 변화에 따른 성능 평가 스크립트 분석

### 1.1 핵심 평가 스크립트 및 구조
- **주요 평가 파일**:
  - `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py` (GPU 4개 활용 멀티프로세스 병렬 평가)
  - `/home/imnyj/Workspace/paper4/code/run_full_evaluation.py` (단일 프로세스 순차 평가 참조용)
- **평가 대상 알고리즘 (총 21종)**:
  - **14개 RL 기반 모델**: `QLearning`, `SARSA`, `ActorCritic`, `VanillaDQN`, `DoubleDQN`, `DuelingDQN`, `DDPG`, `PPO`, `SAC`, `TD3`, `DecisionTransformer`, `MAPPO`, `MoEDQN`, `REMO-DQN` (제안 모델: ResNet-MoE-Dueling DQL)
  - **7개 비교군 / Heuristic 모델**: `Proposed` (TinyMLP), `StdMLP`, `DecTree`, `ReactDCC`, `AdaptDCC`, `Heuristic`, `Fixed10Hz`
- **밀도 변화 평가 (Density Sweep)**:
  - **스윗 변수**: `density` (차량 수 $N_{vehicles}$)
  - **평가 범위**: `[20, 40, 60, 80, 100, 120]`
  - **반복 시드**: `[111, 222, 333]` (각 조합당 3회 시드 실행)
  - **총 평가 횟수**: 21개 모델 $\times$ 6개 밀도 $\times$ 3개 시드 = 378회 평가
- **속도 변화 평가 (Speed Sweep)**:
  - **스윗 변수**: `speed` (차량 속도 $V_{speed}$)
  - **평가 범위**: `[20, 40, 60, 80, 100]`
  - **반복 시드**: `[111, 222, 333]` (각 조합당 3회 시드 실행)
  - **총 평가 횟수**: 21개 모델 $\times$ 5개 속도 $\times$ 3개 시드 = 315회 평가
- **시뮬레이션 환경 및 실행 파라미터**:
  - 시나리오: `urban_grid`
  - 에피소드 스텝: `duration_steps = 1000` (step_length=0.1초 기준 100초)
  - 웜업 구간: `warmup_s = 30.0` (초반 30초 웜업 후 메트릭 트래킹)

---

## 2. 평가 대상 지표 계산 방식 및 데이터 파이프라인 분석

### 2.1 데이터 파이프라인 연동 구조
1. `SimulationRunner` (`sim_engine.py`)가 SUMO 및 libsumo 네트워크를 구동.
2. 매 스텝(0.1초) 차량 상태(위치, 속도, 가속도, 이웃 수)를 추출하여 `ai_dcc_hook.py`의 `Hook.predict()`로 전달.
3. Hook이 결정한 CAM 생성 주기($T_{GenCAM}$) 및 송신 출력($P_{tx}$)을 바탕으로 `ETSICAMLayer` (`etsi_cam_layer.py`)가 CAM 이벤트를 발생시킴.
4. 거리 기반 패킷 전달 확률(Path loss + Nakagami-m fading) 모델로 패킷 수신을 모의(`simulate_receptions`).
5. `AoITracker` (`aoi_tracker.py`)가 수신 기록을 기반으로 AoI 및 PDR 메트릭을 갱신 및 최종 요약 추출.

### 2.2 핵심 평가 지표 계산 상세

| 지표명 | 단위 / 범위 | 계산 위치 | 계산 방식 및 산식 |
| :--- | :--- | :--- | :--- |
| **CBR_mean** | $[0, 1]$ 비율 | `sim_engine.py` (`compute_local_cbr`) | 각 차량 반경 500m 이내 발송된 CAM 패킷 채널 점유 시간 비율($N_{CAM} \times \tau_{TX} / T_{step}$)을 산출 후 전체 차량/시간 평균 |
| **AoI_mean** | 초 (seconds) | `aoi_tracker.py` (`AoITracker`) | 수신차량이 송신차량으로부터 전달받은 CAM 정보의 최신 업데이트 시점 차이($t_{now} - t_{gen\_last}$)를 틱 단위 추적하여 평균 산출 |
| **PDR_mean** | 백분율 (%) | `aoi_tracker.py` (`get_pdr`) | 통신 거리 300m ($COMM\_RANGE\_M$) 이내 이웃 차량으로 발송된 CAM 수 대비 성공적으로 도착된 CAM 패킷 수 비율 |
| **energy_efficiency** | 상대적 지표 | `etsi_cam_layer.py` (`get_energy_efficiency`) | CAM 전송 횟수 및 송신 출력($P_{tx}$)에 따른 총 에너지 소모 측정 지표 |
| **ETSI_compliance** | 백분율 (%) | `etsi_cam_layer.py` (`get_etsi_compliance`) | ETSI EN 302 637-2 규격의 $T_{GenCAM}$ 제약 범위($0.1s \le T \le 1.0s$) 준수율 |

---

## 3. 훈련된 14개 모델 가중치 파일 로딩 방식 분석

### 3.1 저장 위치 및 가중치 확장자
- **기본 저장 디렉토리**: `/home/imnyj/Workspace/paper4/data/models/`
- **가중치 파일 확장자 규칙**:
  - Table-based RL (`QLearning`, `SARSA`): `.pkl` (예: `QLearning.pkl`, `SARSA.pkl`)
  - Neural Network-based RL (12종): `.pth` (예: `REMO-DQN.pth`, `DuelingDQN.pth`, `PPO.pth`, `SAC.pth` 등)

### 3.2 로딩 및 평가 파이프라인
1. **Optuna 하이퍼파라미터 주입**: `load_optuna_params(method_name)` 함수가 `/home/imnyj/Workspace/paper4/data/optuna/best_params_<method>.csv`에서 최적 파라미터를 읽어와 agent 생성을 준비함.
2. **에이전트 인스턴스 생성**: `create_agent(method_name)`가 해당 알고리즘 클래스 인스턴스(예: `ResNetMoEAgent`)를 생성함.
3. **가중치 복원**: `agent.load(model_path)`를 호출하여 PyTorch `torch.load` 또는 Pickle load 수행.
   - *주의 사항*: 가중치 파일 미존재 시 경고 문구를 출력하고 임의 초기화 상태로 진행되므로, 평가 전 14개 모델 가중치 파일 완비가 필수적임.
4. **Hook 연결 및 평가 모드 전환**:
   ```python
   hook = get_hook(hook_name)
   hook.set_agent(agent)
   hook.is_training = False
   hook.reset_episode()
   ```
5. **실시간 행동 결정**: 시뮬레이션 매 스텝마다 $s_t = [\text{cbr\_global}, \text{n\_neighbors}, \text{v\_norm}, \text{dt\_since\_last\_cam}, \text{cbr\_smoothed}]$ 상태 벡터를 기반으로 action index 산출 $\to (T_{GenCAM}, P_{tx})$ 매핑.

---

## 4. 출력 요구 파일 (`eval_density_results.csv`, `eval_speed_results.csv`) 분석

### 4.1 저장 디렉토리 및 경로
- **저장 위치**: `/home/imnyj/Workspace/paper4/data/evaluation/`
- **출력 파일명**:
  - `eval_density_results.csv`
  - `eval_speed_results.csv`

### 4.2 CSV 스키마 및 컬럼 구조

| 컬럼 순서 | 컬럼명 | 데이터 타입 | 설명 |
| :---: | :--- | :--- | :--- |
| 1 | `method` | `string` | 평가 대상 모델/알고리즘 명 (21종) |
| 2 | `density` / `speed` | `int` | 밀도 스윗값 ($N_{vehicles}$) 또는 속도 스윗값 ($V_{speed}$) |
| 3 | `seed` | `int` | 난수 시드 번호 (111, 222, 333) |
| 4 | `runtime_sec` | `float` | 시뮬레이션 실행 소요 시간 (초) |
| 5 | `n_cam_events` | `int` | 시뮬레이션 동안 발생한 총 CAM 전송 이벤트 수 |
| 6 | `Reward` | `float` | 에피소드 누적 리워드 (Hook 수집) |
| 7 | `CBR_mean` | `float` | 에피소드 평균 채널 점유율 |
| 8 | `AoI_mean` | `float` | 에피소드 평균 정보 연령 (초) |
| 9 | `PDR_mean` | `float` | 에피소드 평균 패킷 전달 성공률 (%) |
| 10 | `energy_efficiency` | `float` | 에너지 효율 지표 |
| 11 | `ETSI_compliance` | `float` | ETSI 규격 준수율 (%) |

### 4.3 데이터 생성 및 멀티프로세스 쓰기 로직
- **Lock 제어**: 멀티프로세싱 환경(`multiprocessing.Pool`)에서 파일 동시 쓰기 충돌을 방지하기 위해 `multiprocessing.Manager().Lock()`을 주입받아 쓰기 작업을 직렬화.
- **헤더 생성**: 파일 존재 여부 확인 후 파일 미존재 시 11개 컬럼 헤더 라인을 먼저 작성.
- **Null 방지 및 무결성**: 단일 에피소드 완료 시 `metrics.get(..., 0)` 방식으로 예외 방지 및 즉시 `f.flush()` / `writerow` 수행.

---

## 5. 종합 결론 및 제언
- 성능 평가 스크립트(`run_parallel_evaluation.py`)는 이미 밀도 및 속도 변화에 따른 21종 알고리즘의 multi-seed 평가 및 CSV 파일 생성 로직을 포함하고 있음.
- 따라서 모델 훈련(R1)이 완료되어 14개 가중치 파일(`.pth`/`.pkl`)이 `data/models/` 디렉토리에 정상 저장된 직후, `run_parallel_evaluation.py`의 `PART 2` (또는 `evaluate_all()`)를 실행하면 `eval_density_results.csv` 및 `eval_speed_results.csv` 파일이 정상적으로 추출될 수 있음.
