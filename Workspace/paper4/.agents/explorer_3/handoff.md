# Paper4 Ablation Study 및 평가 데이터 파이프라인 정밀 조사 보고서 (Handoff Report)

## 1. Observation (직접 관찰 사실)

### 1.1. Ablation Study 현황 및 스크립트 상태 (R3)
- **Structure Ablation 스크립트 (`code/run_ablation_structure.py`)**:
  - `action_dim = 16` (라인 15): 최근 H-4/H-5 개정(액션 공간 $4 \times 6 = 24$)이 반영되지 않고 16으로 하드코딩되어 있음.
  - `num_episodes = 2`, `duration_steps = 500` (라인 20, 50): 100 에피소드 $\times$ 2,000 스텝(총 200,000 스텝) 요구사항 미달.
  - `n_vehicles = 50` 고정 (라인 50): 다이내믹 랜덤 밀도(`random.choice([30, 50, 100])`) 미적용.
  - CSV 헤더 (라인 44): `['Episode', 'Reward', 'Loss', 'Epsilon', 'AoI_mean', 'CBR_mean', 'PDR_mean']`으로 `Global_Step` 및 `Density` 컬럼이 누락됨.
  - 디렉토리 상태: `data/ablation_structure/` 내 `REMO-DQN_train_log.csv`, `wo_Dueling_train_log.csv`, `wo_MoE_train_log.csv`, `wo_ResNet_train_log.csv`는 각 2 에피소드 데이터만 수록됨.
- **Reward Ablation 스크립트 (`code/run_ablation_reward.py`) 및 Hook (`code/ai_dcc_hook.py`)**:
  - `run_ablation_reward.py:33-36`: `CustomHook(DuelingDQNHook)`에서 `super().__init__(agent, is_training, reward_variant)`를 호출하나, `ai_dcc_hook.py:109`의 `AIDCCHookBase.__init__`은 `(self, agent=None, is_training=False)`만 허용하여 `reward_variant` 인자 전달 시 `TypeError` 발생 구조임.
  - `ai_dcc_hook.py:144-150`: `compute_reward`가 고정 수식 `reward = -1.0 * over - 0.5 * osc - 0.3 * stale - 0.05 * cost`로 하드코딩되어 있어 `w/o R1`, `w/o R2`, `w/o R3`에 따른 분기 계산 로직이 부재함.
  - `action_dim = 16`, `num_episodes = 2`, `duration_steps = 500` (라인 15, 20, 50): 구조 소거와 동일한 매개변수 불일치 존재.
  - 디렉토리 상태: `data/ablation_reward/Base_train_log.csv` (1 에피소드만 존재, `wo_R1`, `wo_R2`, `wo_R3` 로그 없음).
- **병합 Ablation CSV (`data/ablation_study.csv`)**:
  - 현재 파일 크기 14,282 B, 총 101행 (헤더 + 1~100 에피소드, `Global_Step` 2,000 ~ 200,000).
  - 컬럼 구성: `Episode, Global_Step, REMO-DQN, w/o ResNet, w/o MoE, w/o Dueling, w/o R1, w/o R2, w/o R3` (총 9개).
  - 생성 메커니즘 (`visualizer/prepare_data.py:108-139`): `data/models/`의 수렴 로그와 수식 분해(`cbr_term`, `aoi_term`)로 가공 생성됨.

### 1.2. 평가 데이터 파이프라인 현황 및 데이터 위치 (R4)
- **17개 모델 Reward Convergence 병합 CSV (`data/reward_convergence.csv`)**:
  - 총 101행 (100 에피소드 $\times$ 2,000 스텝 = 200,000 스텝).
  - 컬럼 구성: `Episode, Global_Step` + 17개 베이스라인 (`REMO-DQN, Fixed 10Hz, ReactDCC, AdaptDCC, MoEDQN, MAPPO, PPO, SAC, DDPG, TD3, DuelingDQN, DoubleDQN, VanillaDQN, QLearning, SARSA, ActorCritic, DecisionTransformer`).
  - `data/models/*_convergence.csv`에 14개 RL 모델의 100행 수렴 로그 완비, 3개 비RL 기준선은 `visualizer/prepare_data.py:97-99`에서 상수 보상으로 병합.
- **REMO-DQN 학습 진행 상태 및 프로세스 상태**:
  - `code/resnet_train_log.csv` 및 `data/models/REMO-DQN_convergence.csv`는 총 9개 에피소드(18,000 스텝)까지만 기록됨 (최종 기록 시각: 2026-08-21 12:42).
  - `ps aux | grep python3` 확인 결과, PID 97001 프로세스는 이미 종료되어 현재 실행 중인 학습 프로세스가 없음. 100 에피소드 완주를 위한 재실행 필요.
- **CBR Trace, PDR vs Density, AoI vs Density CSV**:
  - `data/cbr_trace.csv`: 100행 $\times$ 18열 (`Time` + 17개 모델).
  - `data/pdr_vs_density.csv`: 6개 밀도(`20, 40, 60, 80, 100, 120`) $\times$ 18열 (`Density` + 17개 모델).
  - `data/aoi_vs_density.csv`: 6개 밀도(`20, 40, 60, 80, 100, 120`) $\times$ 18열 (`Density` + 17개 모델).
  - 원천 평가 데이터: `data/evaluation/eval_density_results.csv` (380행 실측 데이터)에서 `visualizer/prepare_data.py`를 통해 집계 도출됨.
- **CSV 파일들의 `data/` 디렉토리 배치 규칙**:
  - 모든 11대 시각화용 통합 CSV는 `data/` 루트에 위치 (`prepare_data.py`의 `save_dual()` 함수로 `coder/data/`에도 미러링).
  - 개별 모델 가중치 및 수렴 로그는 `data/models/`에 위치 (`*.pth`, `*.pkl`, `*_convergence.csv`).
  - 소거 연구 원천 로그는 `data/ablation_structure/`, `data/ablation_reward/`, `data/ablation_state/`에 분리 저장.
  - 밀도/속도 스윕 평가 결과는 `data/evaluation/`에 저장 (`eval_density_results.csv`, `eval_speed_results.csv`).

---

## 2. Logic Chain (논리적 인과 분석)

1. **[관찰: `run_ablation_structure.py` & `run_ablation_reward.py`의 파라미터 불일치]**
   $\rightarrow$ 액션 공간이 16으로 설정되어 있고 에피소드가 2로 되어 있어, 현재 스크립트를 그대로 실행하면 최신 액션 공간(24)과 충돌하거나 200,000 스텝 요구사항을 충족할 수 없음.
   $\rightarrow$ `train_resnet.py`의 구현 패턴(`ACTION_DIM = 24`, `num_episodes = 100`, `duration_steps = 2000`, `random.choice([30, 50, 100])`, `Global_Step/Density` 포함 헤더)으로 수정해야 함.

2. **[관찰: `ai_dcc_hook.py` 내 `reward_variant` 미지원 및 `run_ablation_reward.py`의 Type 불일치]**
   $\rightarrow$ `AIDCCHookBase`의 `__init__` 및 `compute_reward`에 `reward_variant` 매개변수와 조건부 보상 계산 로직이 없으므로, Reward Ablation(`wo_R1`, `wo_R2`, `wo_R3`) 학습 시 실제 보상 분해가 일어나지 않거나 런타임 오류가 발생함.
   $\rightarrow$ `AIDCCHookBase`에 `reward_variant`를 주입받아 $R_1$(Over-CBR), $R_2$(Oscillation), $R_3$(Staleness/AoI) 항을 선택적으로 소거하는 보상 산출 로직 구현이 선행되어야 함.

3. **[관찰: `REMO-DQN` 학습 프로세스(PID 97001) 종료 및 9 에피소드 정지]**
   $\rightarrow$ `data/models/REMO-DQN_convergence.csv`가 9 에피소드까지만 생성되어 있어, 최종 100 에피소드(200k 스텝) 수렴 및 가중치 업데이트가 미완료 상태임.
   $\rightarrow$ `train_resnet.py`를 재실행하여 100 에피소드를 완주한 후 `visualizer/prepare_data.py`를 실행하여 11대 CSV 및 시각화 산출물을 최종 갱신해야 함.

4. **[관찰: `prepare_data.py` 파이프라인의 완성도 및 데이터 일관성]**
   $\rightarrow$ 17개 모델의 Reward Convergence, CBR Trace, PDR vs Density, AoI vs Density, 거리별 지표, t-SNE, MoE Routing 등 11개 타겟 데이터 변환 파이프라인이 `visualizer/prepare_data.py`에 잘 구조화되어 있음.
   $\rightarrow$ 학습 및 평가 원천 데이터가 `data/models/`와 `data/evaluation/`에 배치되면 `prepare_data.py` 실행 한 번으로 모든 `data/*.csv`와 `visualizer/*.png/pdf`가 일관되게 생성됨.

---

## 3. Caveats (주의사항 및 미탐색 영역)

1. **시뮬레이션 소요 시간**:
   - `REMO-DQN` 1개 에피소드(2,000 스텝) 시뮬레이션에 약 60~70분이 소요되므로, 100 에피소드 전체 재학습에는 상당한 시간이 소요됩니다 (병렬화 또는 에피소드 지속시간 튜닝 필요성 검토 권장).
2. **State Ablation (`code/run_ablation_state.py`)**:
   - R3 범위 외이나, `run_ablation_state.py` 역시 `action_dim = 16`, `num_episodes = 2` 상태이므로 향후 상태 소거 연구 실행 시 동일한 수정이 필요합니다.
3. **Non-RL 모델(Fixed10Hz, ReactDCC, AdaptDCC)의 수렴 곡선**:
   - 비RL 알고리즘은 학습 단계가 없으므로 `reward_convergence.csv`에서 정상 상태(Steady-state)의 고정 보상값으로 플롯됩니다 (`prepare_data.py:97-99`).

---

## 4. Conclusion (결론 및 권장 조치 사항)

1. **Ablation Study 스크립트 긴급 수정 권장**:
   - `code/ai_dcc_hook.py`: `AIDCCHookBase`에 `reward_variant` 속성 추가 및 `compute_reward`에 $R_1, R_2, R_3$ 분기 수식 반영.
   - `code/run_ablation_structure.py` & `code/run_ablation_reward.py`: `ACTION_DIM = 24`, `num_episodes = 100`, `duration_steps = 2000`, 랜덤 밀도(30/50/100), `Global_Step/Density` 컬럼 규격 일치화.
2. **REMO-DQN 및 잔여 모델 100 에피소드 학습 재개**:
   - 중단된 `train_resnet.py`를 재실행하여 100 에피소드(200k 스텝) 완주 및 `resnet_moe_dqn.pth` 획득.
   - 소거 연구 모델(Structure 4종, Reward 4종) 100 에피소드 학습 실행.
3. **데이터 동기화 및 시각화 갱신**:
   - 학습 완료 후 `python3 visualizer/prepare_data.py` $\rightarrow$ `python3 visualizer/generate_visualizations.py` 순차 실행으로 11대 타겟 CSV 및 350 DPI PNG 완전 갱신.

---

## 5. Verification Method (독립 검증 방법)

1. **Ablation 스크립트 파라미터 및 규격 검증**:
   ```bash
   grep -rn 'ACTION_DIM' code/run_ablation_structure.py code/run_ablation_reward.py
   grep -rn 'num_episodes' code/run_ablation_structure.py code/run_ablation_reward.py
   ```
2. **REMO-DQN 및 17개 모델 수렴 로그 100행 검증**:
   ```bash
   wc -l data/models/*_convergence.csv
   wc -l data/reward_convergence.csv data/ablation_study.csv
   ```
3. **평가 데이터 CSV 무결성 및 NaN/Null 결측치 검사**:
   ```bash
   python3 -c "
   import pandas as pd
   for f in ['data/reward_convergence.csv', 'data/ablation_study.csv', 'data/cbr_trace.csv', 'data/pdr_vs_density.csv', 'data/aoi_vs_density.csv']:
       df = pd.read_csv(f)
       print(f'{f}: shape={df.shape}, nulls={df.isnull().sum().sum()}')
   "
   ```
4. **시각화 산출물 일괄 렌더링 테스트**:
   ```bash
   cd /home/imnyj/Workspace/paper4 && python3 visualizer/prepare_data.py && python3 visualizer/generate_visualizations.py
   ```
