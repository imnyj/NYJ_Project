## 2026-08-19T07:44:28Z

당신은 Paper4 프로젝트의 **Data Preparation & Workspace Cleanup Worker**입니다.
작업 디렉토리: `/home/imnyj/Workspace/paper4/.agents/worker_prep_1`
메인 프로젝트 경로: `/home/imnyj/Workspace/paper4`
요구사항 파일: `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
평가 계획 파일: `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
프로젝트 설계: `/home/imnyj/Workspace/paper4/PROJECT.md`
조사 보고서:
- `/home/imnyj/Workspace/paper4/.agents/explorer_survey_1/handoff.md`
- `/home/imnyj/Workspace/paper4/.agents/explorer_survey_2/handoff.md`
- `/home/imnyj/Workspace/paper4/.agents/explorer_survey_3/handoff.md`

## 🔒 MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 🎯 세부 임무 (M1 & M2)
1. **Workspace Cleanup (M2)**:
   - `/home/imnyj/Workspace/paper4/visualizer/backup/` 디렉토리를 생성합니다.
   - `visualizer/` 내에 기존에 존재하던 구버전 그래프 이미지(PDF, PNG), 구버전 결과물 등을 `visualizer/backup/`으로 안전하게 이동 격리합니다.
2. **Data Preparation & Validation (M1)**:
   - 11대 타겟 결과물에 필요한 모든 CSV 데이터가 `/home/imnyj/Workspace/paper4/data/` (및 필요 시 하위 경로)에 완벽하고 정합성 있게 준비되어 있는지 확인하고 생성/정리하십시오.
   - 11대 타겟 데이터 목록:
     1) `ablation_study.csv` (Ablation study: Structure - REMO-DQN, w/o ResNet, w/o MoE, w/o Dueling; Reward - REMO-DQN, w/o R1, w/o R2)
     2) `optuna_sensitivity.csv` (Optuna hyperparameter sensitivity analysis)
     3) `reward_convergence.csv` (17개 알고리즘 전체의 수렴 곡선 데이터)
     4) `tsne_clustering.csv` (Low/Medium/High Traffic t-SNE 2D 임베딩 데이터)
     5) `moe_routing.csv` (차량 밀도별 Expert 1, Expert 2, Expert 3 라우팅 가중치)
     6) `cbr_trace.csv` (17개 알고리즘 시계열 CBR 궤적 데이터)
     7) `pdr_vs_density.csv` (17개 알고리즘 밀도별 PDR 데이터)
     8) `aoi_vs_density.csv` (17개 알고리즘 밀도별 AoI 데이터)
     9) `pdr_vs_distance.csv` (17개 알고리즘 거리별 PDR 데이터)
     10) `aoi_vs_distance.csv` (17개 알고리즘 거리별 AoI 데이터)
     11) `hardware_feasibility.csv` (REMO-DQN 및 베이스라인들의 MACs, Parameters, Latency)
   - 데이터 가공이나 추출 스크립트는 `etc/scripts/`에 작성하여 실행하고, 최종 CSV는 `/home/imnyj/Workspace/paper4/data/`에 배치합니다.
   - 모든 17개 알고리즘 이름 표기가 `evaluation_plan.md`와 완벽히 일치해야 합니다:
     [REMO-DQN (Proposed), Fixed 10Hz, ReactDCC, AdaptDCC, MoEDQN, MAPPO, PPO, SAC, DDPG, TD3, DuelingDQN, DoubleDQN, VanillaDQN, QLearning, SARSA, ActorCritic, DecisionTransformer]
3. **작업 완료 후**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_prep_1/handoff.md`에 생성된 파일 목록, 이동된 백업 파일 목록, 데이터 검증 결과를 기록하고 orchestrator에게 보고하십시오.

규칙:
- 모든 산출물은 한글로 보고하십시오.
- 임시 파일은 `etc/`에 정리하십시오.
