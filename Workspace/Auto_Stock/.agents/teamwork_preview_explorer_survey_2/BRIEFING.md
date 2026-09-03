# BRIEFING — 2026-09-02T10:57:50+09:00

## Mission
Auto_Stock 프로젝트 내 모델 아키텍처, 지도학습(SL) 특징 추출기, 강화학습(RL) PPO/Actor-Critic 베이스라인 및 Gymnasium 하이브리드 액션 공간(Hybrid Action Space: Discrete + Box) 구성 방안 심층 조사 및 최적 아키텍처 제안

## 🔒 My Identity
- Archetype: explorer
- Roles: Survey Explorer 2 (Models & Hybrid Action Explorer)
- Working directory: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_2
- Original parent: 4bbd98eb-a98a-4ec5-814f-ddce91c12362
- Milestone: Survey Phase

## 🔒 Key Constraints
- Read-only investigation — do NOT modify project source code
- Analyze Auto_Stock model architecture, SL/RL integration, Gymnasium hybrid action spaces (Discrete + Continuous)
- Write output handoff to /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_2/handoff.md
- Use Korean language for all reports

## Current Parent
- Conversation ID: 4bbd98eb-a98a-4ec5-814f-ddce91c12362
- Updated: 2026-09-02T10:57:50+09:00

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`, `requirements.txt`
  - `modules/engine/mock_environment.py`, `modules/engine/live_learning_simulator.py`
  - `modules/data/pipeline.py`, `modules/data/consolidator.py`, `data/raw/005930_consolidated.parquet`
  - Python venv library versions & capabilities (`torch 2.11.0`, `gymnasium 1.2.0`, `stable_baselines3 2.7.0`, `optuna 4.8.0`)
- **Key findings**:
  1. SB3 v2.7.0 does not natively support `gymnasium.spaces.Tuple` or `gymnasium.spaces.Dict` action spaces (throws AssertionError). Requires continuous `Box` action wrapper or custom Actor-Critic.
  2. Native PyTorch `HybridActorCritic` effortlessly handles joint `Categorical(3)` + `Normal(1)` / `Beta(1)` policy heads with exact gradient backpropagation.
  3. `data/raw/*_consolidated.parquet` provides 40+ rich columns including technicals, dynamic PER/PBR/MarketCap, log returns, and volatility.
  4. Both 1D-CNN temporal sequence backbone and MLP tabular backbone are highly feasible and can be pretrained via SL return/trend prediction before RL transfer.
- **Unexplored areas**: None. All core investigation targets completed.

## Key Decisions Made
- Recommended Dual-Architecture Strategy:
  - Standard Gymnasium Environment exposing semantic `spaces.Dict` or `spaces.Tuple`
  - Built-in `HybridToContinuousBoxWrapper` for full SB3 compatibility
  - Custom Native PyTorch `HybridActorCritic` / `HybridPPO` for superior joint discrete-continuous modeling and direct SL weight transfer.

## Artifact Index
- handoff.md — Final comprehensive survey report for models and hybrid action space
