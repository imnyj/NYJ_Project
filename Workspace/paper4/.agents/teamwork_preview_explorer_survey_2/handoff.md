# Handoff Report: 17개 모델 아키텍처, Optuna 튜닝, 학습 파이프라인 정밀 조사

**작성일시**: 2026-08-24T01:25:00Z  
**작성자**: Survey 탐색 에이전트 (`explorer_survey_2`)  
**작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/teamwork_preview_explorer_survey_2`  
**전달 대상**: 총괄 오케스트레이터 (`parent`, ID: `7dfea915-378a-49b4-8904-dffe87802547`)

---

## 1. Observation (직접 관찰 결과)

1. **17개 모델 아키텍처 정의 및 액션/상태 공간**:
   - `code/resnet_moe_agent.py` (L13-93): `ResNetMoEDQN`은 2개의 `ResidualBlock`(hidden=128), `gating_network`(입력 detach 처리, Softmax 출력으로 3개 전문가 가중치 산출), 3개의 `DuelingExpert`(Value Stream + Advantage Stream)로 구성.
   - `code/etsi_cam_layer.py` (L46-48): `PTX_GRID_DBM = [-5, 0, 5, 10, 15, 20]`, `T_GRID_S = [0.1, 0.2, 0.5, 1.0]`, `ACTION_DIM = 24` (4개 주기 x 6개 전력 레벨).
   - `code/ai_dcc_hook.py` (L145-165, L169): 5차원 상태 `[cbr_global, n_neighbors, v_norm, dt_since_last_cam, cbr_smoothed]`를 사용하며, C-3 표준 보상 $R = r_{\text{cbr}} + r_{\text{aoi}} + r_{\text{cost}}$에서 $r_{\text{cbr}} = -1.0 \cdot \max(0, \text{CBR}-0.075) - 0.5 \cdot \text{osc}$, $r_{\text{aoi}} = -0.3 \cdot \max(0, \Delta t - 0.5)$, $r_{\text{cost}} = -0.05 \cdot (0.1 / T_{\text{GenCam}})$ 로 구현됨. 수동 offset은 일절 없음.
   - 17개 모델 목록: `REMO-DQN`, `MoEDQN`, `DuelingDQN`, `DoubleDQN`, `VanillaDQN`, `PPO`, `MAPPO`, `SAC`, `DDPG`, `TD3`, `ActorCritic`, `DecisionTransformer`, `QLearning`, `SARSA`, `Fixed 10Hz`, `ReactDCC`, `AdaptDCC`.

2. **기존 체크포인트 및 데이터 오염 현황**:
   - `data/models/` 경로에 15개 모델 가중치 파일(`ActorCritic.pth`, `DDPG.pth`, `DecisionTransformer.pth`, `DoubleDQN.pth`, `DuelingDQN.pth`, `MAPPO.pth`, `MoEDQN.pth`, `PPO.pth`, `QLearning.pkl`, `REMO-DQN.pth`, `resnet_moe_dqn.pth`, `SAC.pth`, `SARSA.pkl`, `TD3.pth`, `VanillaDQN.pth`)과 17개 convergence CSV 파일이 존재.
   - `code/` 및 루트 경로에 다수의 중복/구버전 `.pth`, `.pkl` 파일(`sac.pth`, `dueling_dqn.pth` 등) 잔존.
   - `data/models/VanillaDQN_convergence.csv` (L8-20): 에피소드 7부터 AoI(165.073), CBR(0.073), PDR(87.11) 등이 동일한 값으로 반복 복사된 합성 데이터 오염이 확인됨.

3. **Optuna 튜닝 스크립트 결함 및 구조**:
   - `code/regenerate_optunas.py` (L110, L128, L148 등) 및 개별 `code/optuna_*.py` 파일들에서 `action_dim=16`으로 잘못 하드코딩되어 있어 `ACTION_DIM=24` 표준과 불일치.
   - `code/optuna_remo_dqn.py` (L9, L19): `ResNetMoEAgent`가 아닌 `MoEAgent`를 호출하고 있음.
   - `code/run_optuna_all_baselines.py` (L36, L114-207): 12개 RL 베이스라인 대상 통합 스크립트가 존재하나 `REMO-DQN`이 누락되어 있고, `N_TRIALS = 2`로 지나치게 축소되어 있음.

4. **학습 파이프라인 및 설정**:
   - `code/train_resnet.py` 및 `code/run_parallel_evaluation.py`: 100 에피소드, 2000 스텝/에피소드, `random.choice([30, 50, 100])` 동적 밀도, $\epsilon$-decay 0.95 (1.0 -> 0.01).
   - 로그 포맷: 9컬럼 `[Episode, Global_Step, Reward, AoI_mean, CBR_mean, PDR_mean, Loss, Epsilon, Density]`.

5. **시스템 하드웨어 가용 자원**:
   - `nvidia-smi`: **NVIDIA GeForce RTX 3090 x 4장** (각 24,576 MiB VRAM, 현재 사용률 0%).
   - `lscpu`: **Intel Core i9-10900X CPU @ 3.70GHz** (10 코어, 20 스레드).
   - `free -h`: **128 GB RAM** (108 GB Available).
   - 4개 GPU와 20개 CPU 스레드를 활용한 완전 병렬 학습 및 Sweep 실행이 최적 상태로 지원됨.

---

## 2. Logic Chain (논리 추론 과정)

1. **[관찰 1 기반]** `etsi_cam_layer.py`의 액션 공간은 4개 주기 x 6개 송신 전력 = 24개 액션으로 확정되어 있으며, 모든 에이전트 클래스(`ResNetMoEAgent`, `DQNAgent` 등)는 기본값으로 `ACTION_DIM=24`를 사용하도록 정렬되어 있다.
2. **[관찰 3 기반]** 그러나 `regenerate_optunas.py` 및 개별 `optuna_*.py`는 과거 16차원 액션 그리드 시절 생성되어 `action_dim=16`으로 고정되어 있고, `optuna_remo_dqn.py`는 `ResNetMoEAgent` 대신 `MoEAgent`를 호출하는 심각한 구조적 오류를 포함하고 있다. 이로 인해 이전에 튜닝된 파라미터가 24차원 환경에서 비수렴/스파이크를 유발했을 가능성이 높다.
3. **[관찰 2 기반]** `data/models/` 내 기존 체크포인트 및 convergence CSV 중 일부는 이전 세션에서 불완전하게 완료된 후 임의로 합성/패치된 흔적이 명백히 확인된다. 따라서 R2 요구사항에 따라 기존 `.pth`/`.pkl` 및 오염 CSV를 완전히 삭제하고 정밀 튜닝된 하이퍼파라미터로 전수 재학습해야 한다.
4. **[관찰 1, 4 기반]** 보상 함수는 인위적 $+1000$ 등의 manual offset이 없는 순수 음수 패널티 구조($r_{\text{CBR}} + r_{\text{AoI}} + r_{\text{cost}}$)이며, 에피소드 총 보상이 $-10^6$ 수준에서 점진적으로 $-8 \times 10^5$ 수준으로 수렴하는 물리적 거동을 나타낸다.
5. **[관찰 5 기반]** RTX 3090 4장(총 96GB VRAM)과 20 vCPU, 128GB RAM이 완전 유휴 상태이므로, `run_parallel_evaluation.py`의 멀티프로세싱(`mp.Pool`)에 GPU ID 분배(`gpus=[0, 1, 2, 3]`)를 적용하여 17개 모델 재학습 및 17,000 에피소드 Sweep을 초고속으로 병렬 처리할 수 있다.

---

## 3. Caveats (한계 및 가정 사항)

1. **시뮬레이션 물리 모델 검증 연계**: 본 조사는 모델 아키텍처, Optuna 최적화 및 학습 파이프라인에 집중되었으며, SUMO 물리 레이어(`sim_engine.py`, `aoi_tracker.py`)의 거리/밀도 감쇠 수식 자체의 세부 감사는 병렬 조사 에이전트(explorer_survey_1)의 결과와 교차 검증되어야 합니다.
2. **Tabular RL (QLearning, SARSA) 메모리 크기**: 5차원 각 10구간 이산화 Q-table의 크기는 약 6.2MB로 확인되었으며, GPU가 아닌 CPU/메모리 상에서 정상 구동됩니다.
3. 그 외 추가 가정 없음.

---

## 4. Conclusion (최종 결론 및 제안 조치)

1. **Optuna 튜닝 스크립트 일괄 수정 필수**:
   - `code/regenerate_optunas.py` 및 개별 `optuna_*.py`의 `action_dim=16`을 `action_dim=24`로 수정.
   - `REMO-DQN`을 `ResNetMoEAgent`로 정확히 매핑하고 13개 RL 모델 전체에 대해 충분한 트라이얼 수(예: `n_trials=15~20`)로 Optuna 재실행.
2. **기존 가중치 및 오염 CSV 전면 퍼지(Purge)**:
   - `data/models/*.pth`, `data/models/*.pkl`, `code/*.pth`, `code/*.pkl`, 루트의 `dueling_dqn.pth` 및 기존 `*_convergence.csv` 파일 일괄 삭제.
3. **17개 모델 통합 병렬 재학습 실행**:
   - `run_parallel_evaluation.py`에 `REMO-DQN`을 포함한 17개 모델을 4개 GPU(GPU 0, 1, 2, 3)에 균등 분산하여 100 에피소드(에피소드당 2000 스텝, $\epsilon$-decay 0.95, 동적 밀도 30/50/100) 진성 재학습 수행.

---

## 5. Verification Method (독립 검증 방법)

1. **아키텍처 및 액션 차원 일관성 검증**:
   - `python3 -c "from etsi_cam_layer import ACTION_DIM; from resnet_moe_agent import ResNetMoEAgent; a = ResNetMoEAgent(); print(ACTION_DIM, a.action_dim)"`
   - 기대 출력: `24 24`
2. **하드웨어 가용성 검증**:
   - `nvidia-smi` 및 `python3 -c "import torch; print(torch.cuda.device_count())"`
   - 기대 출력: `4`
3. **상세 분석 보고서 확인**:
   - `/home/imnyj/Workspace/paper4/.agents/teamwork_preview_explorer_survey_2/survey_models.md` 파일 열람.
