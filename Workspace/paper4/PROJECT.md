# Project: Paper4 Visualizer & Evaluation Pipeline (Final Verified)

## Architecture
- **Data Source**: `data/`, `data/models/`, `data/optuna/`, `data/evaluation/`, `data/ablation_*/`
- **Visualization Engine**: Python (`matplotlib`, `seaborn`, `pandas`, `scikit-learn`, `numpy`, `PIL`)
- **Target Output Directory**: `/home/imnyj/Workspace/paper4/visualizer/`
- **Old Files Isolation**: `/home/imnyj/Workspace/paper4/visualizer/backup/legacy_20260819_pre_critic/`
- **Auxiliary/Scratch Directory**: `/home/imnyj/Workspace/paper4/etc/`

## Feature Inventory
| # | Feature | Description | Milestone | Status | Source |
|---|---|---|---|---|---|
| 1 | R1: Strictly Real Simulations & No Mock Data | 실제 SUMO 환경 및 RL 훈련 로그 전수 검증, mock 데이터 없음 확인 | M1 | DONE | survey |
| 2 | R2: Minimum 200,000 Steps Training & Logs | 14개 RL 모델 200k 스텝 수렴 로그(_convergence.csv) 및 가중치(.pth/.pkl) 완비 | M1 | DONE | survey |
| 3 | R3: Optuna Hyperparameter Optimization | Optuna 최적화 로그(all_best_params.json, sensitivity_table.csv) 완비 및 반영 | M1 | DONE | survey |
| 4 | R4: Model Checkpointing (17종 모델) | 17종 모델(14 RL + 3 표준) 가중치 체크포인트 및 평가 데이터 무결성 확인 | M1 | DONE | survey |
| 5 | R5: 11대 타겟 시각화 스크립트 리팩토링 | 350 DPI PNG, x축 200k 스텝, 수렴/안정 2단계 시각화, 1~11번 접두사 자동 저장 | M2 | DONE | prompt |
| 6 | R5: Walkthrough Checklist Completion | walkthrough.md 내 11대 타겟 140개 항목 전수 100% 완료 | M2 | DONE | survey |
| 7 | Multi-Agent Independent Review & Challenger Testing | Reviewer 1/2 (APPROVE), Challenger 1/2 (APPROVE) 만장일치 통과 | M3 | DONE | protocol |
| 8 | Forensic Integrity Audit & Zero-Cheat Verification | Forensic Auditor 무결성 전수 감사 (CLEAN) 획득 | M4 | DONE | protocol |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Survey & 200k Data/Models Verification | 14개 RL 200k 수렴 데이터, 17종 모델 가중치, Optuna 로그 전수 탐색 완료 | None | DONE |
| M2 | Visualizer Refactoring & 350 DPI Re-plotting | plot_figures.py / generate_visualizations.py 350 DPI 렌더링, x축 200k 스텝, 2단계 구간 반영 | M1 | DONE |
| M3 | Multi-Agent Independent Review & Challenger Testing | 2 Reviewers + 2 Challengers 독립 검증 및 결함 전무 확인 (전원 APPROVE) | M2 | DONE |
| M4 | Forensic Integrity Audit & Final Sign-off | Forensic Auditor 무결성 감사 (CLEAN) 및 walkthrough.md 최종 승인 | M3 | DONE |

## Interface Contracts & Visual Specifications
### Color & Legend Order Specifications (evaluation_plan.md §2)
1. REMO-DQN (Proposed) : `#FF0000` (`alpha=1.0`, Bold, linewidth=2.5, zorder=99, marker='o')
2. Fixed 10Hz: `#0000FF` (`alpha=0.6`, linestyle='--', marker='s')
3. ReactDCC (ETSI Standard): `#4D96FF` (`alpha=0.6`, linestyle='-.', marker='^')
4. AdaptDCC (ETSI Standard): `#2A4B7C` (`alpha=0.6`, linestyle=':', marker='v')
5. MoEDQN: `#9B5DE5` (`alpha=0.6`, marker='o')
6. MAPPO: `#D783FF` (`alpha=0.6`, marker='s')
7. PPO: `#7A49A5` (`alpha=0.6`, marker='p')
8. SAC: `#00FF00` (`alpha=0.6`, marker='D')
9. DDPG: `#6BCB77` (`alpha=0.6`, marker='h')
10. TD3: `#2E8B57` (`alpha=0.6`, marker='d')
11. DuelingDQN: `#FF9F1C` (`alpha=0.6`, marker='s')
12. DoubleDQN: `#FFD166` (`alpha=0.6`, marker='+')
13. VanillaDQN: `#D67229` (`alpha=0.6`, marker='<')
14. QLearning: `#1A1A1A` (`alpha=0.6`, marker='.')
15. SARSA: `#555555` (`alpha=0.6`, marker=',')
16. ActorCritic: `#888888` (`alpha=0.6`, marker='1')
17. DecisionTransformer: `#B5B5B5` (`alpha=0.6`, marker='*')

### Visual & Technical Constraints
- PNG Resolution: **Strictly 350 DPI** (`dpi=350.012` 실측 완료).
- Convergence & Ablation X-Axes: **Strictly 200,000 steps** (`0 ~ 200,000 Steps`).
- Two-Phase Indicators: Background shading (`axvspan`) for Phase I (Convergence / Exploration, $0 \sim 120\text{k}$) and Phase II (Post-Convergence Steady-State Stability, $120\text{k} \sim 200\text{k}$).
- Output File Names: `1_ablation_study.png` ~ `11_hardware_feasibility_table.tex` 22개 파일 완비.

## Code Layout
- Master Pipeline: `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`
- Figure Generator: `/home/imnyj/Workspace/paper4/visualizer/plot_figures.py`
- Visualization Generator: `/home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py`
- Table Generator: `/home/imnyj/Workspace/paper4/visualizer/generate_tables.py`
- Style & Config Utilities: `/home/imnyj/Workspace/paper4/visualizer/plot_utils.py`
- Output Figures & Tables: `/home/imnyj/Workspace/paper4/visualizer/`
- Data Sources: `/home/imnyj/Workspace/paper4/data/`
