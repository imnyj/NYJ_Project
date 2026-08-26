# 강화학습 훈련 파이프라인, 20만 스텝 준비성, Optuna HPO 및 검증/Halt 하네스 정밀 분석 보고서 (analysis.md)

## 1. 개요 및 분석 배경
본 조사는 IEEE TWC 논문 규격 및 요구사항(`ORIGINAL_REQUEST.md`, `scenario.md`, `Conversation.md`)에 따라, 가짜(Mock/Synthetic) 환경을 전면 배제하고 실제 SUMO 시뮬레이터(`NetSim.py`, `Communications.py`, `make_sumo_set.py`)와 연동되는 **실제 200,000 스텝 강화학습 훈련 파이프라인**, **Optuna 하이퍼파라미터 최적화(HPO) 하네스**, **Short Dummy Run 검증 전략**, 그리고 **훈련 착수 전 정밀 Halt 및 사용자 코드 리뷰 프로토콜**을 정밀 분석하고 설계안을 도출하는 것을 목적으로 합니다.

---

## 2. 조사 영역별 심층 분석 결과

### [영역 1] 기존 코드베이스 상세 점검
1. **`src/hpo.py`**:
   - **현재 상태**: 9개 베이스라인 알고리즘에 대한 Optuna 탐색 공간(`sample_hparams`), 복합 목적함수(`compute_composite_objective`), 다중 시드 평가(`evaluate_trial_multiseed`), CSV 저장(`save_study_results`, `run_all_baselines_hpo`)이 구현되어 있음.
   - **문제점 및 개선사항**:
     - 내부 구현에 `class SyntheticVehicle` 및 자체 더미 롤아웃 루프가 잔존함. 이는 Follow-up 요구사항 R1("completely discarding prior synthetic mock implementations")에 위배되므로, HPO 롤아웃 환경을 `aoi_env.py` 및 실제 SUMO(`SumoNetSim`) 기반으로 교체하거나 연동해야 함.
     - 목적함수에 $w_1 \sim w_4$ 보상 가중치 탐색 파라미터가 `sample_hparams`에 포함되어 에이전트가 보상 밸런스를 스스로 찾도록 확장되어야 함(`Conversation.md` 3항).
2. **`src/hot_swap_trainer.py`**:
   - **현재 상태**: 무중단 듀얼 모델 핫스왑 매니저(`DualModelHotSwapManager`), 스레드 안전 비동기 큐(`TransitionStreamer`), 백그라운드 학습기(`BackgroundTrainer`), 고속 서빙 스케줄러(`HotSwapRLScheduler`), 통합 오케스트레이터(`HotSwapTrainer`)가 체계적으로 구현되어 있음.
   - **문제점 및 개선사항**:
     - `run_hot_swap_training` 함수 내부에 좌표를 선형 증가시키는 더미 트래픽 루프(`v_pos = {v: ...}`)가 잔존함. 실제 훈련 루프는 `aoi_env.py`의 SUMO 스텝과 연동되어야 함.
     - `torch.utils.tensorboard.SummaryWriter`를 통한 텐서보드 로깅(손실, 보상, 오차, AoI 등)이 부재함.
     - 20만 스텝(2000 steps $\times$ 100 episodes) 동안의 주기적 체크포인트 저장(`models/checkpoints/<model>_ep{ep}.pt`) 및 최고 성능 모델 자동 저장 로직이 누락되어 있음.
3. **`src/evaluate.py`**:
   - **현재 상태**: 10개 모델(휴리스틱 + 9개 RL 모델)을 5개 차량 밀도(15, 25, 35, 45, 55 veh/km)와 5개 시드(42, 101, 2024, 777, 999)에 걸쳐 총 250회 벤치마크 수행하고 6대 IEEE TWC 지표(Mean/Peak AoI, Outage rate, Error, Power/Energy, Jain's fairness)를 계산하여 3종의 CSV(`eval_raw_runs.csv`, `eval_summary_by_density.csv`, `eval_leaderboard.csv`)로 출력하는 파이프라인이 완성되어 있음.
   - **문제점 및 개선사항**:
     - 평가 롤아웃 역시 `EvalSyntheticVehicle`을 사용 중이므로 실제 SUMO 트래픽 환경 위에서의 벤치마크 모드를 지원해야 함.
4. **`tests/` (12개 테스트 파일, 174개 테스트 케이스)**:
   - 모든 174개 테스트가 pytest 상에서 100% 통과(Pass)함을 직접 확인(`pytest` 174 passed in 5.43s).
   - 기능 검증, 경계치 검증, 계약 어댑터, 핫스왑 동시성 검증 등이 촘촘히 구축되어 있으나, 가짜 환경을 제거한 실제 SUMO 연동 테스트(`verify_environment.py`)가 추가되어야 함.

---

### [영역 2] Optuna 하이퍼파라미터 최적화(HPO) 프레임워크 점검
1. **9개 베이스라인 탐색 공간 (Hyperparameter Search Space)**:
   - **기본 모델 3종**:
     - `HybridPPO`: `lr` $\in [10^{-4}, 3\times 10^{-3}]$ (log), `hidden_dim` $\in \{32, 64, 128\}$, `gamma` $\in [0.95, 0.999]$, `clip_ratio` $\in [0.1, 0.3]$, `entropy_coef` $\in [10^{-4}, 0.05]$ (log), `value_coef` $\in [0.2, 0.8]$
     - `HybridSAC`: `lr` $\in [10^{-4}, 3\times 10^{-3}]$ (log), `hidden_dim` $\in \{32, 64, 128\}$, `gamma` $\in [0.95, 0.999]$, `tau` $\in [10^{-3}, 0.02]$ (log)
     - `HybridTD3`: `lr` $\in [10^{-4}, 3\times 10^{-3}]$ (log), `hidden_dim` $\in \{32, 64, 128\}$, `gamma` $\in [0.95, 0.999]$, `tau` $\in [10^{-3}, 0.02]$ (log), `policy_noise` $\in [0.1, 0.3]$, `noise_clip` $\in [0.2, 0.5]$, `policy_freq` $\in \{2, 3, 4\}$
   - **최신/유사 모델 6종**:
     - `MAPPO`: `lr`, `hidden_dim`, `gamma`, `clip_ratio`, `entropy_coef`, `value_coef`
     - `HyARPPO`: `lr`, `hidden_dim`, `embed_dim` $\in \{4, 8, 16\}$, `gamma`, `clip_ratio`, `entropy_coef`, `value_coef`
     - `MPDQN`: `lr_actor`, `lr_critic`, `hidden_dim`, `gamma`, `tau`, `epsilon_initial` $\in [0.1, 0.4]$, `epsilon_decay` $\in [0.99, 0.999]$
     - `PureAoI`: `urgency_threshold` $\in [0.1, 0.7]$
     - `DuelingQAoI`: `lr`, `hidden_dim`, `gamma`, `tau`, `epsilon_initial`, `epsilon_decay`
     - `SACAoI`: `lr`, `hidden_dim`, `gamma`, `tau`, `lyapunov_v` $\in [0.2, 5.0]$ (log), `aoi_thresh` $\in [0.2, 0.6]$
   - **보상 가중치($w_1 \sim w_4$) 탐색 공간 추가**:
     - $w_1 \in [0.5, 2.0]$ (오차 가중치), $w_2 \in [0.05, 0.5]$ (전력 가중치), $w_3 \in [0.1, 1.0]$ (혼잡 가중치), $w_4 \in [0.5, 3.0]$ (중복 갱신 패널티 가중치).
2. **복합 목적 함수 (Composite Objective Function)**:
   $$\text{Score} = w_{\text{err}} \cdot \text{MeanError} + w_{\text{aoi}} \cdot \text{MeanAoI} + w_{\text{outage}} \cdot \text{OutageRate} + w_{\text{power}} \cdot \text{PowerNorm}$$
   - $w_{\text{err}} = 1.0, w_{\text{aoi}} = 0.5, w_{\text{outage}} = 2.0, w_{\text{power}} = 0.2$
   - 모든 메트릭에 대해 단조 증가 패널티 구조를 가지며 `minimize` 방향으로 수렴.
3. **Study 관리 및 CSV 로깅**:
   - `optuna.samplers.TPESampler(seed=42)` 및 `optuna.pruners.MedianPruner` 운용.
   - SQLite DB 스토리지(`sqlite:///results/hpo/optuna_study.db`) 지원으로 프로세스 비정상 종료 시 재개 및 다중 스레드/프로세스 확장 가능.
   - 출력: `results/hpo/optuna_trials_<model>.csv` (개별 트라이얼 이력) 및 `results/hpo/optuna_best_params.csv` (모델별 최적 파라미터 마스터 CSV).

---

### [영역 3] 200,000 스텝 실제 훈련 루프 구조 설계
1. **훈련 규모 및 에피소드 구조**:
   - 1개 모델당 **최소 200,000 스텝** 보장: **2,000 스텝 $\times$ 100 에피소드**.
   - 에피소드당 SUMO 시뮬레이션 초기화 (`make_sumo_set.py`로 네트워크 및 플로우 생성 $\to$ TraCI/libsumo 구동 $\to$ 2000 스텝 수행 $\to$ 정상 종료 및 클린업).
2. **듀얼 모델 핫스왑 및 하드웨어 격리**:
   - **Act Model**: 서빙 전용 모드 (`model.eval()`). 빠른 추론 보장 (지연시간 < 1ms), 멀티 GPU 시 `cuda:0` 할당.
   - **Rest Model**: 백그라운드 그래디언트 훈련 모드 (`model.train()`). 멀티 GPU 시 `cuda:1` 할당, 단일 GPU/CPU 시 디바이스 공유.
   - **TransitionStreamer & Retrospective Buffer**: 서빙 스텝에서 생성된 전이 튜플을 비차단(Non-blocking) 큐로 전송하고, 백그라운드 훈련 워커가 Replay Buffer(용량: 50,000~100,000)로 배치 수집 후 주기적(예: 20 그래디언트 스텝마다) 파라미터 동기화(Hot-Swap).
   - **무결성 및 안정성 가드**: `validate_weights()`로 NaN/Inf 검출 시 스왑 즉시 차단 및 이전 정상 가중치 유지.
3. **TensorBoard 및 CSV 로깅 구조**:
   - **TensorBoard** (`torch.utils.tensorboard.SummaryWriter`):
     - 스칼라 기록: `Loss/Total`, `Loss/Actor`, `Loss/Critic`, `Loss/Entropy`, `Reward/Step`, `Reward/EpisodicMean`, `AoI/Mean`, `AoI/Peak`, `Outage/Rate`, `Error/Mean`, `Error/Max`, `Power/Mean_dBm`, `Latency/Inference_ms`, `HotSwap/Count`.
     - 50,000 스텝 부근의 수렴 곡선 시각화 지원 (`Conversation.md` 5항).
   - **CSV 로깅**: `logs/training/<model_name>_progress.csv`에 에피소드별 집계 메트릭 자동 append.
4. **체크포인팅 및 리소스 관리**:
   - 디렉토리: `results/checkpoints/<model_name>/`
   - 매 10 에피소드(20,000 스텝)마다 `ep_{ep:03d}.pt` 저장.
   - 이동 평균 평가 보상이 가장 높은 에피소드에 대해 `best_model.pt` 자동 갱신.
   - 20만 스텝 완료 시 `final_model.pt` 저장.
   - 메모리 누수 방지: 매 에피소드 종료 시 TraCI 프로세스 안전 종료(`traci.close()`) 및 Python GC/PyTorch CUDA 캐시 정리(`torch.cuda.empty_cache()`).

---

### [영역 4] Short Dummy Run (10-step) 검증 전략
실제 200,000 스텝의 대규모 연산에 돌입하기 전, 전체 파이프라인이 코드 결함이나 누락 없이 100% 정상 작동함을 수학적/기능적으로 입증하기 위한 초경량 검증 하네스:

| 검증 단계 | 검증 내용 | 검증 기준 및 성공 조건 |
| :--- | :--- | :--- |
| **D1. SUMO 실제 환경 연동** | `aoi_env.py` + `make_sumo_set.py` + `NetSim.py` 10스텝 구동 | 실제 차량 좌표가 스텝마다 갱신되고, `Communications.py`가 실제 RSSI를 계산함 (가짜 환경 미사용 증명). |
| **D2. 9개 모델 인스턴스화 & 추론** | 9개 베이스라인 모델 전체 16차원 상태 입력 $\to$ 하이브리드 액션 $(\Delta, ch, p)$ 출력 | NaN/Inf 없이 유효 범위 $(\Delta \in [0.5, 10.0], ch \in \{0..3\}, p \in [20, 30])$ 준수. |
| **D3. 핫스왑 & 그래디언트 1스텝** | 10개 전이 수집 $\to$ Rest 모델 1회 update $\to$ Act 모델로 핫스왑 복사 | `loss` 산출 정상, NaN 없음, `swap_count` 증가, 가중치 동기화 일치. |
| **D4. Optuna HPO 1 Trial** | 1개 모델에 대해 1 Trial, 10스텝 HPO 실행 $\to$ CSV 저장 | `optuna_best_params.csv` 생성, 파라미터 JSON 역직렬화 정상. |
| **D5. Benchmark Eval 1 Run** | 1개 모델, 1개 밀도, 1개 시드, 10스텝 평가 $\to$ 6대 메트릭 산출 | 6대 IEEE TWC 메트릭 정상 산출 및 CSV 출력 완료. |
| **소요 시간** | 전체 검증 5단계 통합 실행 | **15초 이내 완료** (컴퓨팅 자원 낭비 제로). |

---

### [영역 5] 200k-step 전 정밀 Halt 메커니즘 및 사용자 코드 리뷰 프로토콜
대규모 200k 스텝 연산 시작 전 시스템이 스스로 정지하고 사용자의 승인을 받기 위한 명시적 제어 프로토콜:

1. **Strict Execution Halt Barrier (엄격한 정지 장벽)**:
   - 환경, 모델 9종, Optuna HPO, 핫스왑 훈련기, 평가 하네스, `verify_environment.py` 작성이 완료되고 Short Dummy Test(10스텝)가 모두 통과하면, 스크립트는 **자동으로 200,000 스텝 훈련을 시작하지 않고 즉시 종료(Halt)**되어야 함.
   - `progress_sync.md`의 최상단에 `[HALT: Awaiting User Code Review Approval]` 상태를 명시적으로 기록.
2. **사용자 코드 리뷰 체크리스트 (User Review Protocol)**:
   - [ ] **SUMO 실물 연동성 검증**: `verify_environment.py`를 실행하여 TraCI/NetSim 실좌표 이동 및 Communications RSSI 계산 통과 여부 확인.
   - [ ] **치팅 방지 단언문 확인**: `aoi_env.py` 내부 `step()`에 가짜 데이터 통과 시 즉시 크래시하는 Hardcoded Assertions 탑재 확인.
   - [ ] **9개 베이스라인 수학적 무결성**: 9개 모델의 Actor/Critic 손실 수식, 그래디언트 역전파, 하이브리드 디코딩 로직 검토.
   - [ ] **200,000 스텝 지원 구조**: 에피소드 루프(2000 steps $\times$ 100 eps), TensorBoard 로깅, CSV 저장, `checkpoints/` 저장소 설정 검토.
   - [ ] **사용자 최종 실행 승인**: 사용자가 "Proceed with 200k training" 명령을 입력할 때까지 대기.

---

## 3. 요약 및 권장 조치 사항
1. `src/hpo.py`, `src/hot_swap_trainer.py`, `src/evaluate.py` 내부에 잔존하는 `SyntheticVehicle` 및 로컬 선형 좌표 이동 더미 루프를 완전히 폐기하고, `aoi_env.py`의 실제 SUMO 시뮬레이션 루프로 대체해야 함.
2. `src/hot_swap_trainer.py`에 `torch.utils.tensorboard.SummaryWriter` 및 에피소드별 `checkpoints/` 저장 기능을 표준 탑재해야 함.
3. 10스텝 Short Dummy Run 스크립트(`tests/test_dummy_verification.py` 또는 `verify_dummy_run.py`)를 통해 15초 내에 전 구간 통합을 검증한 뒤, 200k 스텝 훈련에 진입하지 않고 안전하게 Halt하여 사용자에게 코드 리뷰를 요청해야 함.
