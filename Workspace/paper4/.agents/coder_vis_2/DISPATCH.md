## 2026-08-19T07:45:29Z
당신은 Paper4 프로젝트의 **Visualization Coder (Worker)**입니다.
작업 디렉토리: `/home/imnyj/Workspace/paper4/.agents/coder_vis_2`
메인 프로젝트 경로: `/home/imnyj/Workspace/paper4`
요구사항 파일: `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
평가 계획 파일: `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
프로젝트 설계: `/home/imnyj/Workspace/paper4/PROJECT.md`

## 🔒 MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 🎯 핵심 임무
이전 Coder의 작업에서 파일이 `/home/imnyj/Workspace/paper4/visualizer/`에 물리적으로 생성되지 않았습니다.
당신은 `/home/imnyj/Workspace/paper4/visualizer/` 디렉토리에 시각화 스크립트(`generate_visualizations.py` 등)를 작성하고, 이를 `python3`로 직접 실행하여 아래 11대 타겟 결과물을 물리적으로 생성 및 검증해야 합니다.

### 11대 타겟 결과물 파일 목록 (반드시 `/home/imnyj/Workspace/paper4/visualizer/`에 생성)
1. `ablation_study.pdf` (Ablation study curves: Structure & Reward)
2. `optuna_sensitivity_table.csv` 및 `optuna_sensitivity_table.tex` (Optuna 하이퍼파라미터 민감도 분석 표)
3. `reward_convergence.pdf` (17개 비교군 전체 보상 수렴 곡선)
4. `tsne_clustering.png` (혼잡 상태별 MoE 잠재 공간 군집화, 300+ DPI PNG)
5. `moe_routing.pdf` (차량 밀도별 3개 전문가 활성화 가중치 분포)
6. `cbr_trace.pdf` (시계열 CBR 궤적 그래프, 17개 비교군)
7. `pdr_vs_density.pdf` (차량 밀도별 PDR 곡선, 17개 비교군)
8. `aoi_vs_density.pdf` (차량 밀도별 AoI 곡선, 17개 비교군)
9. `pdr_vs_distance.pdf` (전송 거리별 PDR 곡선, 17개 비교군)
10. `aoi_vs_distance.pdf` (전송 거리별 AoI 곡선, 17개 비교군)
11. `hardware_feasibility_table.csv` 및 `hardware_feasibility_table.tex` (하드웨어 실효성 프로파일링 표)

### 스타일 및 범례 순서 규격 (`evaluation_plan.md §2` 엄격 준수)
1. `REMO-DQN (Proposed)`: `#FF0000` (`alpha=1.0`, `linewidth=2.2`, `zorder=10`, bold/강조)
2. `Fixed 10Hz`: `#0000FF` (`alpha=0.6`, `linestyle='--'`)
3. `ReactDCC (ETSI Standard)`: `#4D96FF` (`alpha=0.6`, `linestyle='-.'`)
4. `AdaptDCC (ETSI Standard)`: `#2A4B7C` (`alpha=0.6`, `linestyle=':'`)
5. `MoEDQN`: `#9B5DE5` (`alpha=0.6`)
6. `MAPPO`: `#D783FF` (`alpha=0.6`)
7. `PPO`: `#7A49A5` (`alpha=0.6`)
8. `SAC`: `#00FF00` (`alpha=0.6`)
9. `DDPG`: `#6BCB77` (`alpha=0.6`)
10. `TD3`: `#2E8B57` (`alpha=0.6`)
11. `DuelingDQN`: `#FF9F1C` (`alpha=0.6`)
12. `DoubleDQN`: `#FFD166` (`alpha=0.6`)
13. `VanillaDQN`: `#D67229` (`alpha=0.6`)
14. `QLearning`: `#1A1A1A` (`alpha=0.6`)
15. `SARSA`: `#555555` (`alpha=0.6`)
16. `ActorCritic`: `#888888` (`alpha=0.6`)
17. `DecisionTransformer`: `#B5B5B5` (`alpha=0.6`)

### 데이터 소스
- `/home/imnyj/Workspace/paper4/coder/data/` 및 `/home/imnyj/Workspace/paper4/data/`에 존재하는 실제 데이터 CSV들을 로드하여 사용하십시오.
- 만약 특정 비교군 컬럼이나 데이터 파일 경로가 필요하면 `coder/data/`의 파일들을 `/home/imnyj/Workspace/paper4/data/`에 복사/정리하여 사용하십시오.

### 실행 및 최종 확인
- `python3 /home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py`를 실행하여 11개 결과물(총 13개 파일: PDF 8개, CSV 2개, TEX 2개, PNG 1개)이 `/home/imnyj/Workspace/paper4/visualizer/`에 정상 생성되고 파일 크기가 0보다 큰지 `ls -lh`로 확인하십시오.
- 작업 완료 후 `/home/imnyj/Workspace/paper4/.agents/coder_vis_2/handoff.md`에 스크립트 경로, 실행 결과, 생성된 13개 파일의 크기 및 경로를 명시하고 orchestrator에게 보고하십시오.

규칙:
- 모든 산출물 파일은 `/home/imnyj/Workspace/paper4/visualizer/`에 위치해야 합니다.
- 보고서는 한국어로 작성하십시오.
