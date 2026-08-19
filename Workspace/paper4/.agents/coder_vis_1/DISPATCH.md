## 2026-08-19T07:45:00Z
당신은 Paper4 프로젝트의 **Visualization Coder**입니다.
작업 디렉토리: `/home/imnyj/Workspace/paper4/.agents/coder_vis_1`
메인 프로젝트 경로: `/home/imnyj/Workspace/paper4`
요구사항 파일: `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
평가 계획 파일: `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
프로젝트 설계: `/home/imnyj/Workspace/paper4/PROJECT.md`

## 🔒 MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 🎯 세부 임무 (R2 & R3 구현)

1. **Workspace Cleanup (R3)**:
   - `visualizer/` 내에 남아있는 기존 구버전 `.png` 파일들(`10_pdr_vs_distance.png`, `1_reward_convergence.png`, `2_ablation_study.png`, `3_moe_routing.png`, `4_tsne_clustering.png`, `5_hardware_feasibility.png`, `7_cbr_trace.png`, `8_pdr_vs_density.png`, `9_aoi_vs_density.png` 등)을 `visualizer/backup/` 디렉토리로 이동(격리)하십시오.

2. **Data Verification & Harmonization**:
   - `data/` 및 `coder/data/`에 존재하는 데이터 파일들을 활용하여 11대 타겟 결과물에 필요한 모든 입력 데이터를 완벽히 구성하십시오.
   - `data/` 디렉토리에도 11개 타겟의 공식 CSV 파일이 모두 존재하도록 동기화하십시오.

3. **Python Visualization Scripts & 11 Target Outputs Generation (R2)**:
   - `/home/imnyj/Workspace/paper4/visualizer/` 디렉토리에 모듈화된 고품질 시각화 스크필트(예: `plot_all.py`, `plot_figures.py`, `generate_tables.py` 등)를 작성하고 직접 실행하여 11대 타겟 결과물을 완벽히 생성하십시오.
   - **규격 요구사항**:
     - **그래프 (8종)**: 반드시 **PDF (.pdf)** 포맷으로 저장 (벡터 그래픽, 고해상도, IEEE 논문용 폰트/크기 적용).
     - **표 (2종)**: **CSV (.csv)** 및 **LaTeX 표 (.tex)** 포맷으로 각각 저장.
     - **군집화 (1종, t-SNE)**: **PNG (.png, 300+ DPI)** 포맷으로 저장.
     - **색상 및 범례 순서 규격 (`evaluation_plan.md §2` 엄격 준수)**:
       1. `REMO-DQN (Proposed)`: `#FF0000` (`alpha=1.0`, linewidth=2.2, zorder=10, bold)
       2. `Fixed 10Hz`: `#0000FF` (`alpha=0.6`, linestyle='--')
       3. `ReactDCC (ETSI Standard)`: `#4D96FF` (`alpha=0.6`, linestyle='-.')
       4. `AdaptDCC (ETSI Standard)`: `#2A4B7C` (`alpha=0.6`, linestyle=':')
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
   
   - **11대 타겟 결과물 상세 목록**:
     1. `ablation_study.pdf`: Ablation study curves (Structure: REMO-DQN, w/o ResNet, w/o MoE, w/o Dueling; Reward: REMO-DQN, w/o R1, w/o R2)
     2. `optuna_sensitivity_table.csv` & `optuna_sensitivity_table.tex`: Sensitivity analysis table by Optuna
     3. `reward_convergence.pdf`: 17개 비교군 전체 보상 수렴 곡선
     4. `tsne_clustering.png`: MoE 잠재 공간 t-SNE 군집화 (PNG 300 DPI)
     5. `moe_routing.pdf`: 밀도별 MoE Expert 활성화 가중치 분포
     6. `cbr_trace.pdf`: 시간대별 CBR 궤적 및 채널 안정성 (17개 비교군)
     7. `pdr_vs_density.pdf`: 차량 밀도별 PDR 곡선 (17개 비교군)
     8. `aoi_vs_density.pdf`: 차량 밀도별 AoI 곡선 (17개 비교군)
     9. `pdr_vs_distance.pdf`: 거리별 PDR 곡선 (17개 비교군)
     10. `aoi_vs_distance.pdf`: 거리별 AoI 곡선 (17개 비교군)
     11. `hardware_feasibility_table.csv` & `hardware_feasibility_table.tex`: 하드웨어 실효성 프로파일링 표

4. **실행 및 검증**:
   - 스크립트를 직접 실행하여 모든 11개 결과물 파일이 `visualizer/`에 정상적으로 에러 없이 생성되는지 확인하십시오.
   - 작업 내역과 생성된 파일 목록을 `/home/imnyj/Workspace/paper4/.agents/coder_vis_1/handoff.md`에 상세히 기록하고 보고하십시오.
