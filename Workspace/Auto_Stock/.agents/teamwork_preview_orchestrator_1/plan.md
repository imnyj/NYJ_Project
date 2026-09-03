# Execution Plan: Hybrid SL-RL Baseline & Optuna HPO Pipeline

## 1. Survey Phase (Step 0)
- Dispatch 3 Explorers:
  1. `explorer_survey_sim`: Investigate `LiveLearningSimulator`, current data pipelines, market simulators, environment structures.
  2. `explorer_survey_models`: Investigate existing models, feature extractors, PyTorch / Stable-Baselines3 integration, dependencies.
  3. `explorer_survey_hpo_tests`: Investigate existing test setups, Optuna usage, logging/output directories (`etc/hpo_results/`), verification mechanisms.

## 2. Synthesis & Architecture Definition (Step 1)
- Create `PROJECT.md` at `/home/imnyj/Workspace/Auto_Stock/PROJECT.md` with:
  - Feature Inventory (R1 ~ R4 and beyond)
  - Architectural contracts (Gymnasium interface, State/Action space signatures, Hybrid action mapping)
  - Milestone decomposition
  - Code layout convention
- Create `TEST_INFRA.md` for the E2E Testing Track.

## 3. Milestones Execution (Steps 2A / 2B)
- **Milestone 1**: Hybrid Action Space Environment (`HybridTradingEnv` wrapping `LiveLearningSimulator` or equivalent). Action Space: `spaces.Tuple((spaces.Discrete(3), spaces.Box(0.0, 1.0, shape=(1,))))` or `spaces.Dict`.
- **Milestone 2**: SL Feature Extractor (MLP/1D-CNN) & RL Baseline (PPO / Actor-Critic handling hybrid action space).
- **Milestone 3**: Optuna HPO Pipeline (`scripts/optimize_hpo.py` / `hpo/` pipeline) & Results Export to `etc/hpo_results/baseline_hpo.csv`.
- **Milestone 4 (Final)**: Pass 100% E2E tests (`tests/test_hpo_pipeline.py`, `n_trials=3` validation, CSV validation, assertion on action space) + Adversarial hardening.

## 4. Verification & Audit Gating
- Reviewers, Challengers, and Forensic Auditor verification on each milestone.
- Binary veto on integrity violations.
- Final human report to Sentinel.
