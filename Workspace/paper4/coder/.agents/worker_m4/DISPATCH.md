## 2026-08-27T02:04:00Z

You are Worker 4 for Milestone M4 (Baseline Scraping & Test Adaptation).
Your working directory is /home/imnyj/Workspace/paper4/coder/.agents/worker_m4/

Read the following reference documents:
1. /home/imnyj/Workspace/paper4/coder/.agents/ORIGINAL_REQUEST.md
2. /home/imnyj/Workspace/paper4/coder/PROJECT.md
3. /home/imnyj/Workspace/paper4/coder/.agents/worker_m1/handoff.md
4. /home/imnyj/Workspace/paper4/coder/.agents/worker_m2/handoff.md
5. /home/imnyj/Workspace/paper4/coder/.agents/worker_m3/handoff.md
6. /home/imnyj/Workspace/paper4/Conversation.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CONCURRENCY & SAFETY RULES:
- Use file locking via `/home/imnyj/Command/core/lock_manager.py` before modifying files.
- Log every modification using `/home/imnyj/Command/core/audit_logger.py`.

TASKS FOR M4:
1. BASELINE SCRAPING (R4):
   - Completely delete the `src/baselines/` directory and all 11 files in it.
   - Do NOT implement any new baselines at this time (the user will provide new baselines later).
   - In `src/hot_swap_trainer.py`, `src/evaluate.py`, `src/hpo.py`, `run_all.py`:
     * Remove all `from src.baselines import ...` statements and `BASELINE_REGISTRY` lookups.
     * In `src/evaluate.py`: `CANONICAL_EVAL_MODELS = ["HeuristicScheduler"]`. If a model is requested that is not HeuristicScheduler and not provided as an instantiated nn.Module, raise `NotImplementedError("Baseline models scraped. New IEEE baselines to be provided.")`.
     * In `run_all.py`: remove the 9 baseline training loop and replace with a clear message that baseline models are removed awaiting user-provided IEEE baselines.

2. TEST SUITE & VERIFICATION SCRIPTS ADAPTATION (18D & New Bounds & No Baselines):
   - Delete `tests/test_baselines_instantiation.py` and `etc/scripts/verify_dueling_q_action_idx.py` (or move to `backup/` per GEMINI.md rule 5).
   - In `tests/test_rl_interface.py`:
     * Update tests to verify `STATE_DIM == 18`, `n_queue` and `heading`.
     * Update `TestActionDecoder` tests to verify `DELTA_MIN=0.1, DELTA_MAX=45.0, P_MIN=10.0, P_MAX=23.0`.
   - In `verify_environment.py`:
     * Update `assert state_vec.shape == (18,)` and `assert rsu.comm_range == 300.0` (or dynamic constants).
   - In `tests/contract_adapters.py`:
     * Remove fake baseline implementations and update dummy vectorizer/decoder to 18D and `[10, 23] dBm, [0.1, 45.0] s`.
   - In `tests/test_hot_swap.py`, `tests/test_dummy_verification.py`, `tests/test_evaluation.py`, `tests/test_hpo.py`, `tests/test_tier1_features.py`, `tests/test_tier2_boundaries.py`, `tests/test_tier3_integration.py`, `tests/test_dynamics_predictor.py`, `tests/test_e2e_pipeline.py`:
     * Replace any `from src.baselines import ...` with a simple generic torch `nn.Module` (e.g. `DummyPolicy(nn.Module)`) with `state_dim=18` or `HeuristicScheduler`.
     * Ensure tests test genuine functionality (AoiV2IEnv, HotSwapTrainer, ActionDecoder, StateVectorizer, HeuristicScheduler, DynamicsPredictor).

3. VERIFICATION:
   - Run `/home/imnyj/venv/bin/pytest tests/ -v`
   - Ensure `pytest tests/` runs and passes 100% of tests with 0 failures.
   - Verify `src/baselines/` does not exist.
