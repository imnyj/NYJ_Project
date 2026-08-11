# Handoff Report — Survey Explorer 2

## 1. Observation
- **평가 스크립트 위치 및 라인**:
  - `/home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py`:
    - Line 40-55: 14개 RL 알고리즘 (`rl_methods`) 및 7개 비교군 (`heuristic_methods`) 정의.
    - Line 196-265: `eval_worker()` 함수 — 모델 로드, SUMO 시뮬레이션 구동 및 결과 수집.
    - Line 270-331: `main()` 함수 — PART 2에서 Density Sweep (`densities = [20, 40, 60, 80, 100, 120]`) 및 Speed Sweep (`speeds = [20, 40, 60, 80, 100]`)을 실행하고 `eval_density_results.csv`, `eval_speed_results.csv` 생성.
  - `/home/imnyj/Workspace/paper4/code/run_full_evaluation.py`: 순차 평가 버전 스크립트.
- **가중치 파일 요구사항 및 현황**:
  - 가중치 저장 경로: `/home/imnyj/Workspace/paper4/data/models/`
  - 확장자: `QLearning`, `SARSA`는 `.pkl`, 나머지 12개 RL 모델은 `.pth`.
  - 현황: 현재 `data/models/` 디렉토리에는 가중치 파일(`.pth`/`.pkl`)이 생성 대기 중이며, 수렴 로그 파일만 일부 확인됨. `eval_worker()` (Line 205-208)에 의해 가중치 파일이 없을 시 경고 출력 후 임의의 미훈련 모델로 평가가 진행되므로 훈련 완료 후 평가가 실행되어야 함.
- **지표 계산 모듈**:
  - `/home/imnyj/Workspace/paper4/code/sim_engine.py`: `SimulationRunner` 클래스가 `compute_local_cbr()`, `simulate_receptions()`, `AoITracker` 등을 총괄하여 `CBR_mean`, `AoI_mean`, `PDR_mean`, `energy_efficiency`, `ETSI_compliance` 집계.
  - `/home/imnyj/Workspace/paper4/code/ai_dcc_hook.py`: `get_hook()`을 통해 알고리즘별 Hook을 매핑하고, 매 스텝 상태값을 받아 행동 $(T_{GenCAM}, P_{tx})$ 산출.
- **출력 CSV 스키마**:
  - 경로: `/home/imnyj/Workspace/paper4/data/evaluation/`
  - 파일명: `eval_density_results.csv`, `eval_speed_results.csv`
  - 컬럼 구조 (11개): `["method", "density"/"speed", "seed", "runtime_sec", "n_cam_events", "Reward", "CBR_mean", "AoI_mean", "PDR_mean", "energy_efficiency", "ETSI_compliance"]`

## 2. Logic Chain
1. `run_parallel_evaluation.py`의 PART 2 평가 로직은 14개 RL 모델 및 7개 Heuristic 모델을 대상으로 밀도(6단계: 20~120) 및 속도(5단계: 20~100) 스윗 실험을 3개 시드(111, 222, 333)에 대해 병렬 수행하도록 설계되어 있다.
2. `eval_worker`는 `data/models/{method_display}{.pth|.pkl}` 경로에서 훈련 완료된 모델 가중치를 로드하고, `ai_dcc_hook.py`와 `sim_engine.py`를 연동하여 시뮬레이션을 수행한다.
3. 시뮬레이션 중 `etsi_cam_layer.py`, `aoi_tracker.py`, `sim_engine.py`가 CBR, AoI, PDR, 에너지 효율, ETSI 준수율 등의 지표를 정밀 계산하여 요약한다.
4. 계산된 11개 메트릭 항목은 `multiprocessing.Manager().Lock()`으로 보호되는 쓰기 과정을 통해 `eval_density_results.csv` 및 `eval_speed_results.csv` 파일로 차례로 누적 저장된다.
5. 따라서 14개 모델의 훈련(R1)이 완료된 후 `run_parallel_evaluation.py`의 PART 2 평가를 구동하면 요구되는 모든 지표를 포함한 CSV 결과 파일들이 생성된다.

## 3. Caveats
- 현재 `/home/imnyj/Workspace/paper4/data/models/` 디렉토리에 훈련 완료된 가중치 파일(`.pth`/`.pkl`)이 없어, 현 시점에서 평가 스크립트를 실행하면 미훈련 모델로 동작할 수 있음 (R1 훈련 완료 필수).
- SUMO 기반 시뮬레이션이 다수의 프로세스로 동시 실행되므로, 평가 구동 시 시스템 CPU/GPU 자원 점유 상태를 모니터링해야 함.

## 4. Conclusion
- R2 요구사항인 차량 밀도 및 속도 변화에 따른 성능 평가 스크립트/함수 분석, 지표 계산 방식, 가중치 로드 방식, CSV 출력 스키마 파악이 완료되었으며, 해당 조사 결과 및 분석 리포트는 `.agents/explorer_survey_2/analysis.md`에 최종 정리되었다.
- 훈련 단계(R1) 완료 후 `run_parallel_evaluation.py`의 PART 2 평가를 실행하면 `eval_density_results.csv` 및 `eval_speed_results.csv`가 정해진 11개 컬럼 규격에 맞게 생성된다.

## 5. Verification Method
- **분석 파일 검증**:
  - `view_file /home/imnyj/Workspace/paper4/.agents/explorer_survey_2/analysis.md` 실행하여 4가지 주요 조사 항목 및 정밀 분석 내용 확인.
- **코드 검증**:
  - `grep -n "out_file_density" /home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py` 명령으로 CSV 파일 경로 및 컬럼 리스트 확인.
  - `grep -n "create_agent" /home/imnyj/Workspace/paper4/code/run_parallel_evaluation.py` 명령으로 가중치 로딩 로직 확인.
