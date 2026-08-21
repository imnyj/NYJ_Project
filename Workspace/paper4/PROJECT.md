# Project: Paper4 17-Model Training, Convergence Verification & Evaluation Pipeline

## Architecture
- **Training Scripts**: `code/train_resnet.py`, `code/train_*.py`, `code/run_*.py`
- **Model Checkpoints**: `data/models/` (`.pth`, `.pkl`)
- **Execution & Training Logs**: `code/` and `data/` (`*_train_log.csv`, `*_convergence.csv`)
- **Evaluation Plan Reference**: `visualizer/evaluation_plan.md`
- **Central Deliverables Directory**: `/home/imnyj/Workspace/paper4/data/` and `/home/imnyj/Workspace/paper4/data/models/`
- **Auxiliary & Logs Directory**: `/home/imnyj/Workspace/paper4/etc/`

## Feature Inventory
| # | Feature | Description | Milestone | Status | Source |
|---|---|---|---|---|---|
| 1 | R1: REMO-DQN Training & Setup | `code/train_resnet.py` 설정 (100 에피소드, 2000 스텝, eps_decay=0.95, random density 30/50/100), 가중치 저장 | M1 | PLANNED | prompt_draft |
| 2 | R1: Programmatic Convergence Verification | 초기 10 에피소드 평균 보상 vs 마지막 10 에피소드 평균 보상 수렴 및 안정화 검증 | M1 | PLANNED | prompt_draft |
| 3 | R2: 16 Baseline Models Training & Execution | 나머지 16개 모델(총 17개) 동일 조건(100 에피소드, 2000 스텝) 훈련/실행 | M2 | PLANNED | prompt_draft |
| 4 | R2: Model Weight Checkpointing & Individual CSVs | 모든 DRL 가중치 `data/models/` 저장 및 17개 개별 실행 로그 CSV 저장 | M2 | PLANNED | prompt_draft |
| 5 | R3: Evaluation Item 1 Data Extraction | Ablation study 5개 모델 (REMO-DQN, MoEDQN, DuelingDQN, DoubleDQN, VanillaDQN) 통합 CSV 병합 | M3 | PLANNED | prompt_draft |
| 6 | R3: Evaluation Item 3 Data Extraction | 17개 전체 모델 Reward vs Step 데이터 통합 CSV 병합 | M3 | PLANNED | prompt_draft |
| 7 | Multi-Agent Verification & Integrity Audit | Reviewer/Challenger/Auditor를 통한 무결성 및 수렴 정밀 검증 | M1, M2, M3 | PLANNED | protocol |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M0 | Survey & Architecture Investigation | 코드베이스 훈련 스크립트, 17개 모델 구조 및 데이터 파이프라인 전수 조사 | None | IN_PROGRESS |
| M1 | R1: REMO-DQN 우선 학습 및 수렴 검증 | REMO-DQN 훈련 파라미터 적용, 학습 실행, 가중치 저장 및 수렴성 프로그램 검증 | M0 | PLANNED |
| M2 | R2: 나머지 16개 모델 전수 학습 및 데이터 수집 | 16개 모델 훈련/실행, `data/models/` 가중치 저장 및 개별 CSV 로깅 | M1 | PLANNED |
| M3 | R3: 평가 계획서 Item 1 & 3 통합 CSV 추출 | 5개 모델 Ablation CSV 및 17개 전체 모델 수렴 CSV 생성 및 정합성 검증 | M2 | PLANNED |

## Interface Contracts & 17 Model Checklist
### 17 Target Models (evaluation_plan.md §2)
1. `REMO-DQN` (Proposed DRL)
2. `Fixed 10Hz` (Static baseline)
3. `ReactDCC` (ETSI Standard)
4. `AdaptDCC` (ETSI Standard)
5. `MoEDQN` (DRL)
6. `MAPPO` (DRL)
7. `PPO` (DRL)
8. `SAC` (DRL)
9. `DDPG` (DRL)
10. `TD3` (DRL)
11. `DuelingDQN` (DRL)
12. `DoubleDQN` (DRL)
13. `VanillaDQN` (DRL)
14. `QLearning` (Tabular RL)
15. `SARSA` (Tabular RL)
16. `ActorCritic` (DRL)
17. `DecisionTransformer` (Offline/Sequence RL)

## Code Layout
- Training Master Scripts: `code/train_resnet.py`, `code/train_*.py`, `code/run_*.py`
- Model Checkpoints: `data/models/`
- Output Logs: `code/*_train_log.csv`, `data/*.csv`
- Evaluation Plan: `visualizer/evaluation_plan.md`
- Auxiliary Scripts & Logs: `etc/`
- Visualizer & Plot Scripts: `visualizer/`
- Data Sources & Consolidated CSVs: `data/`
