# Handoff Report — Milestone 2: 가짜 데이터 삭제 및 Optuna 하이퍼파라미터 재최적화

**작성일시**: 2026-08-24T02:44:00Z  
**작성자**: worker_m2 (implementer, qa, specialist)  
**수신자**: parent (orchestrator: `7dfea915-378a-49b4-8904-dffe87802547`)  
**상태**: Hard Handoff (작업 100% 완료)

---

## 1. Observation (직접 관찰 및 실측 데이터)

- **삭제 전 가중치 및 오염 데이터 현황**:
  - `data/models/` 내에 15개 모델 가중치 파일(`ActorCritic.pth`, `DDPG.pth`, `DecisionTransformer.pth`, `DoubleDQN.pth`, `DuelingDQN.pth`, `MAPPO.pth`, `MoEDQN.pth`, `PPO.pth`, `QLearning.pkl`, `REMO-DQN.pth`, `resnet_moe_dqn.pth`, `SAC.pth`, `SARSA.pkl`, `TD3.pth`, `VanillaDQN.pth`) 및 17개 과거 수렴 로그(`*_convergence.csv`)가 존재함.
  - `data/models/VanillaDQN_convergence.csv` 등 일부 수렴 로그에서 동일한 AoI(165.073), CBR(0.073), PDR(87.11) 값이 반복 복사된 오염/합성 흔적이 직접 관찰됨.
  - `code/` 내에 16개 레거시 가중치(`*.pth`, `*.pkl`) 및 루트의 `dueling_dqn.pth`, `data/ablation_*/*.pth` 잔여 확인.
- **삭제 실행 결과**:
  - 상기 모든 구 가중치 파일 및 수렴 로그는 `backup/legacy_models_20260824/`로 격리 백업 후 메인 디렉토리에서 전원 삭제됨.
  - `find /home/imnyj/Workspace/paper4 -name "*.pth" -o -name "*.pkl" | grep -v "/backup/"` 실행 결과: 0개 파일 반환 (완전 삭제 검증 완료).
- **Optuna 최적화 스크립트 결함 및 수정 관찰**:
  - 기존 개별 `optuna_*.py` 템플릿 코드에 `action_dim=16`이 하드코딩되어 `etsi_cam_layer.py`의 표준 규격인 `ACTION_DIM=24`와 불일치하던 결함을 확인 및 전면 수정.
  - 제안 모델 `REMO-DQN`(`ResNetMoEAgent`, `resnet_moe_agent.py`)이 누락되어 있던 점을 보완하여 14개 전체 RL 모델을 최적화 대상에 정식 편입.
- **Optuna 병렬 최적화 실행 결과**:
  - 4x NVIDIA RTX 3090 GPU 상에서 `run_optuna_parallel.py`를 실행하여 14개 RL 모델에 대해 각 15 trials, 총 210 trials(총 630 시뮬레이션 에피소드)를 2724.7초 동안 완수함 (exit code 0).
  - 14개 모델의 최적 하이퍼파라미터가 `data/optuna_best_params.json` 및 `data/optuna/all_best_params.json`에 저장됨.
  - 최적 하이퍼파라미터를 기반으로 50초 시뮬레이션(warmup_s=5.0)을 수행하여 비RL 모델 3종을 포함한 17개 전체 모델의 실측 성능 지표(PDR, AoI, CBR, Convergence Reward)를 `data/optuna_sensitivity_table.csv` 및 `data/optuna_sensitivity.csv`로 저장 완료.

---

## 2. Logic Chain (논리적 추론 체계)

1. **오염 데이터 배제 및 가짜 가중치 퍼지**:
   - `[Observation 1]`의 오염/합성된 구 수렴 로그와 이전 가중치를 유지할 경우, 후속 Milestone(M3 재학습, M4 17,000 에피소드 평가)에서 데이터 오염 및 무결성 위반이 발생함.
   - 따라서 `backup/`으로 안전 격리 후 `data/models/`와 `code/`의 모델 파일을 완전히 삭제하여 무결한 백지 상태를 확보함.
2. **ACTION_DIM=24 통일 및 REMO-DQN 연동**:
   - ETSI CAM 표준 규격(4개 전송 주기 x 6개 송신 전력 = 24 액션)과 일치시키지 않으면 네트워크 출력 차원 불일치로 런타임 오류가 발생함.
   - `from etsi_cam_layer import ACTION_DIM`을 전 최적화 스크립트에 적용하고 `ResNetMoEAgent`를 연결하여 14개 RL 모델의 탐색 공간을 표준화함.
3. **4-GPU 분산 병렬화의 타당성 및 신뢰성**:
   - 단일 프로세스 `libsumo`는 C++ 정적 상태를 공유하므로 동일 프로세스 내 동시 실행 시 충돌이 발생함.
   - `multiprocessing.Process(spawn)`을 통해 독립된 Python 프로세스마다 각각 `CUDA_VISIBLE_DEVICES`를 0, 1, 2, 3으로 격리 할당함으로써 4개의 RTX 3090 GPU를 100% 독립 활용하여 충돌 없이 최적화를 완수함.
4. **실측 기반 민감도 테이블 생성**:
   - Optuna 튜닝 후 도출된 최적 파라미터를 에이전트에 실제 주입하고 50초 SUMO 주행 환경(warmup 5s 이후 실측)에서 17개 모델을 평가함으로써 인위적 수치가 배제된 100% 실측 성능표(`data/optuna_sensitivity_table.csv`)를 도출함.

---

## 3. Caveats (주의사항 및 한계)

- **소요 시간 및 트라이얼 수**:
  - 이번 Optuna 탐색은 15 trials/model(총 210 trials, 2724.7초 소요)로 수행되었으며, TPE Sampler와 Median Pruner를 통해 핵심 수렴 영역을 충분히 탐색하였습니다.
  - 추후 추가적인 파인튜닝이 필요한 경우 `n_trials`를 확장하여 재실행할 수 있도록 CLI 파라미터화되어 있습니다.
- **체크포인트 디렉토리 상태**:
  - `data/models/`는 현재 완전히 비워져 있으므로, Milestone 3(17개 모델 100 에피소드 풀 재학습)을 즉시 가동하여 신규 가중치를 생성해야 합니다.

---

## 4. Conclusion (최종 결론)

- **Milestone 2 완료**: 구 가중치/오염 데이터의 전면 퍼지, `ACTION_DIM=24` 표준화, 제안 모델 `REMO-DQN`을 포함한 14개 RL 모델의 4-GPU 병렬 Optuna 최적화, 그리고 비RL 모델을 포함한 17개 전체 모델의 실측 민감도 테이블 생성이 100% 무결하게 완료되었습니다.
- **산출물 무결성**: `data/optuna_best_params.json` 및 `data/optuna_sensitivity_table.csv`가 실제 실행 기반으로 온전하게 생성되었으며, Milestone 3(전체 모델 풀 재학습)으로 진행할 수 있는 모든 선행 조건이 충족되었습니다.

---

## 5. Verification Method (독립 검증 방법)

1. **가중치 파일 삭제 검증**:
   ```bash
   find /home/imnyj/Workspace/paper4 -name "*.pth" -o -name "*.pkl" | grep -v "/backup/"
   # 출력 결과가 0줄이어야 함 (exit code 1)
   ```
2. **Optuna 최적 파라미터 JSON 검증**:
   ```bash
   python -c "import json; d=json.load(open('data/optuna_best_params.json')); print('Models count:', len(d)); assert len(d) == 14; assert 'REMO-DQN' in d; print('Optuna Best Params JSON Validated!')"
   ```
3. **Optuna 민감도 테이블 CSV 검증**:
   ```bash
   python -c "import csv; rows=list(csv.DictReader(open('data/optuna_sensitivity_table.csv'))); print('Rows count:', len(rows)); assert len(rows) == 17; assert rows[0]['Method'] == 'REMO-DQN (Proposed)'; print('Sensitivity Table CSV Validated!')"
   ```
4. **개별 스크립트 실행 검증**:
   ```bash
   python code/optuna_remo_dqn.py
   ```
