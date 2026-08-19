## 2026-08-19T07:46:02Z
당신은 Paper4 프로젝트의 **Visualization Implementation Worker**입니다.
작업 디렉토리: `/home/imnyj/Workspace/paper4/.agents/worker_vis_exec_1`
메인 프로젝트 경로: `/home/imnyj/Workspace/paper4`
요구사항 파일: `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
평가 계획 파일: `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
프로젝트 설계: `/home/imnyj/Workspace/paper4/PROJECT.md`

## 🔒 MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 🎯 세부 실행 단계 (반드시 순서대로 도구를 호출하여 실행하십시오!)

### 1단계: `/home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py` 파일 작성
`write_to_file` 도구를 사용하여 `/home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py`를 생성하십시오.
스크립트는 다음 11대 타겟 결과물(총 13개 파일)을 생성해야 합니다:
1. `ablation_study.pdf` (Ablation study curves: Structure & Reward)
2. `optuna_sensitivity_table.csv` & `optuna_sensitivity_table.tex` (Optuna hyperparameter sensitivity analysis)
3. `reward_convergence.pdf` (17개 비교군 전체 보상 수렴 곡선)
4. `tsne_clustering.png` (MoE 잠재 공간 t-SNE 군집화, 300+ DPI PNG)
5. `moe_routing.pdf` (차량 밀도별 MoE 3개 전문가 활성화 가중치 분포)
6. `cbr_trace.pdf` (시계열 CBR 궤적 그래프, 17개 비교군 + 0.60 Target line)
7. `pdr_vs_density.pdf` (차량 밀도별 PDR 곡선, 17개 비교군)
8. `aoi_vs_density.pdf` (차량 밀도별 AoI 곡선, 17개 비교군)
9. `pdr_vs_distance.pdf` (전송 거리별 PDR 곡선, 17개 비교군)
10. `aoi_vs_distance.pdf` (전송 거리별 AoI 곡선, 17개 비교군)
11. `hardware_feasibility_table.csv` & `hardware_feasibility_table.tex` (하드웨어 실효성 프로파일링 표)

**스타일 및 범례 순서 (`evaluation_plan.md §2` 엄격 준수)**:
- 1. REMO-DQN (Proposed): `#FF0000` (alpha=1.0, lw=2.5, zorder=10, Bold)
- 2. Fixed 10Hz: `#0000FF` (alpha=0.6, ls='--')
- 3. ReactDCC (ETSI Standard): `#4D96FF` (alpha=0.6, ls='-.')
- 4. AdaptDCC (ETSI Standard): `#2A4B7C` (alpha=0.6, ls=':')
- 5. MoEDQN: `#9B5DE5` (alpha=0.6)
- 6. MAPPO: `#D783FF` (alpha=0.6)
- 7. PPO: `#7A49A5` (alpha=0.6)
- 8. SAC: `#00FF00` (alpha=0.6)
- 9. DDPG: `#6BCB77` (alpha=0.6)
- 10. TD3: `#2E8B57` (alpha=0.6)
- 11. DuelingDQN: `#FF9F1C` (alpha=0.6)
- 12. DoubleDQN: `#FFD166` (alpha=0.6)
- 13. VanillaDQN: `#D67229` (alpha=0.6)
- 14. QLearning: `#1A1A1A` (alpha=0.6)
- 15. SARSA: `#555555` (alpha=0.6)
- 16. ActorCritic: `#888888` (alpha=0.6)
- 17. DecisionTransformer: `#B5B5B5` (alpha=0.6)

데이터 소스: `/home/imnyj/Workspace/paper4/coder/data/` 및 `/home/imnyj/Workspace/paper4/data/`의 CSV들을 로드하십시오. 필요한 경우 `coder/data/`의 CSV들을 `/home/imnyj/Workspace/paper4/data/`에도 복사하십시오.

### 2단계: 스크립트 실행
`run_command` 도구를 사용하여 다음 명령을 실행하십시오:
```bash
python3 /home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py
```

### 3단계: 파일 생성 검증
`run_command` 도구를 사용하여 `ls -lh /home/imnyj/Workspace/paper4/visualizer/`를 실행하고 13개 산출물 파일이 생성되고 크기가 0보다 큰지 확인하십시오.

### 4단계: Handoff 보고서 작성
`write_to_file` 도구를 사용하여 `/home/imnyj/Workspace/paper4/.agents/worker_vis_exec_1/handoff.md`에 실행 결과와 파일 목록을 작성하고 orchestrator에게 `send_message`로 보고하십시오.
