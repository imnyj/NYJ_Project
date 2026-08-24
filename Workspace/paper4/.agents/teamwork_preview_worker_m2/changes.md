# Milestone 2: 가짜 데이터 삭제 및 Optuna 하이퍼파라미터 재최적화 상세 변경 보고서

## 1. 가짜 데이터 및 구 가중치 전면 퍼지(Purge)
- **삭제 대상 목록**:
  - `data/models/*.pth`, `data/models/*.pkl` (총 15개 모델 체크포인트)
  - `data/models/*_convergence.csv` (과거 오염/합성 수렴 로그 17개 파일)
  - `code/*.pth`, `code/*.pkl` (루트 및 레거시 가중치 16개 파일)
  - `data/ablation_structure/*.pth`, `data/ablation_reward/*.pth`
- **보관 및 추적 조치**:
  - GEMINI.md 규칙에 따라 삭제 전 모든 이전 파일들을 `backup/legacy_models_20260824/` 디렉토리로 안전하게 격리 백업 완료.
  - `audit_logger`를 통해 모든 삭제 파일에 대한 `DELETE` 액션 로깅 완료.
  - 현재 `data/models/` 디렉토리는 완전히 비워져 신규 100 에피소드 학습(Milestone 3) 준비가 완료됨.

## 2. Optuna 최적화 파이프라인 전면 개편 및 수정
- **ACTION_DIM=24 표준화**:
  - 이전 스크립트 중 일부 템플릿에 잔존하던 `action_dim=16` 하드코딩 결함을 전면 수정.
  - `etsi_cam_layer.py`의 공식 ETSI 표준 규격인 `ACTION_DIM=24` (4개 생성 주기 x 6개 송신 전력)를 전체 14개 RL 모델에 일관되게 적용.
- **제안 모델 REMO-DQN 정식 편입**:
  - `resnet_moe_agent.py`의 `ResNetMoEAgent` 및 `REMO-DQN` 훅을 Optuna 최적화 파이프라인에 정식 연동.
  - `num_experts` (2~4), `lr` (1e-5~1e-2), `gamma` (0.90~0.999), `batch_size`, `buffer_size`, `target_update_freq` 등 핵심 하이퍼파라미터 탐색 공간 정의.
- **4-GPU 분산 병렬 최적화 엔진 신규 구축**:
  - `code/run_optuna_parallel.py`: 4x NVIDIA RTX 3090 GPU를 완전히 활용하여 14개 모델을 병렬로 분산 최적화하는 엔진 구현.
  - `code/regenerate_optunas.py`: 14개 모델에 대한 독립 실행형 개별 최적화 스크립트(`optuna_*.py`) 생성기 정비.
  - `code/run_optuna_all_baselines.py`: CLI 인자 기반 단일/전체 최적화 지원 통합 스크립트 업데이트.

## 3. Optuna 최적화 실행 결과 (14개 RL 모델)
4x RTX 3090 GPU 상에서 각 모델당 15 trials씩 실제 시뮬레이션을 수행하여 도출된 최적 파라미터:

1. **REMO-DQN (Proposed)**:
   - `num_experts`: 3
   - `lr`: 0.002267
   - `gamma`: 0.9198
   - `batch_size`: 64
   - `buffer_size`: 10000
   - `target_update_freq`: 2
2. **MoEDQN**:
   - `num_experts`: 2, `lr`: 0.0009288, `gamma`: 0.9576, `batch_size`: 64, `buffer_size`: 100000, `target_update_freq`: 1
3. **DuelingDQN**:
   - `lr`: 0.0009099, `gamma`: 0.9177, `batch_size`: 64, `buffer_size`: 50000, `target_update_freq`: 1
4. **DoubleDQN**:
   - `lr`: 0.0002258, `gamma`: 0.9238, `batch_size`: 32, `buffer_size`: 100000, `target_update_freq`: 2
5. **VanillaDQN**:
   - `lr`: 0.005829, `gamma`: 0.9088, `batch_size`: 128, `buffer_size`: 100000, `target_update_freq`: 5
6. **MAPPO**:
   - `lr`: 0.0006647, `gamma`: 0.9169, `eps_clip`: 0.1130, `k_epochs`: 10, `batch_size`: 32, `buffer_size`: 50000
7. **PPO**:
   - `lr`: 0.008153, `gamma`: 0.9006, `eps_clip`: 0.2135, `k_epochs`: 8, `batch_size`: 64, `buffer_size`: 100000
8. **SAC**:
   - `lr`: 0.003986, `gamma`: 0.9451, `tau`: 0.009937, `alpha`: 0.2712, `batch_size`: 64, `buffer_size`: 100000
9. **DDPG**:
   - `lr_actor`: 0.0006647, `lr_critic`: 0.00003248, `gamma`: 0.9064, `tau`: 0.00954, `batch_size`: 32, `buffer_size`: 50000
10. **TD3**:
    - `lr`: 0.00002227, `gamma`: 0.9327, `tau`: 0.005474, `policy_delay`: 1, `target_noise`: 0.2004, `noise_clip`: 0.4214, `batch_size`: 32, `buffer_size`: 10000
11. **ActorCritic**:
    - `lr`: 0.001999, `gamma`: 0.9636, `batch_size`: 64, `buffer_size`: 10000
12. **DecisionTransformer**:
    - `lr`: 0.001568, `gamma`: 0.9298, `batch_size`: 32, `buffer_size`: 100000
13. **QLearning**:
    - `alpha`: 0.01729, `gamma`: 0.9803, `epsilon_decay`: 0.9472
14. **SARSA**:
    - `alpha`: 0.03846, `gamma`: 0.9858, `epsilon_decay`: 0.9595

## 4. 최종 산출물 파일 목록
- `data/optuna_best_params.json` (14개 모델 최적 파라미터 JSON)
- `data/optuna/all_best_params.json` (동일 내용 JSON)
- `data/optuna_sensitivity_table.csv` (17개 전체 모델 아키텍처, 튜닝 파라미터, 실측 수렴 보상 및 PDR/AoI/CBR 성능 테이블)
- `data/optuna_sensitivity.csv` (동기화된 민감도 CSV)
- `data/optuna/best_params_<ModelName>.csv` (14개 개별 모델 최적 파라미터 CSV)
- `code/evaluate_optuna_sensitivity.py` (최적 파라미터 기반 17개 모델 성능 평가 스크립트)
