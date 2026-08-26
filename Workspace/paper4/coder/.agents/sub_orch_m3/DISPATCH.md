## 2026-08-26T13:14:02Z

You are the Sub-Orchestrator for Milestone 3: Hyperparameter Optimization (Optuna HPO - R3).

Your working directory is: /home/imnyj/Workspace/paper4/coder/.agents/sub_orch_m3/
Project root: /home/imnyj/Workspace/paper4/coder
Original Request: /home/imnyj/Workspace/paper4/coder/ORIGINAL_REQUEST.md
Project Plan: /home/imnyj/Workspace/paper4/coder/PROJECT.md
Baseline Registry: /home/imnyj/Workspace/paper4/coder/src/baselines/__init__.py

Your Mission (Milestone 3):
1. Implement `src/hpo.py` using Optuna:
   - Define tailored search spaces for all 9 baseline models (`HybridPPO`, `HybridSAC`, `HybridTD3`, `MAPPO`, `HyARPPO`, `MPDQN`, `PureAoI`, `DuelingQAoI`, `SACAoI`).
   - Formulate composite objective function evaluated across seeds in the AoI environment balancing estimation error, AoI, outage rate, and power.
   - Run Optuna study to optimize hyperparameters for all 9 models.
   - Save optimal hyperparameters for each model into `/home/imnyj/Workspace/paper4/coder/results/hpo/optuna_best_params.csv`.
   - Save trial history CSVs to `/home/imnyj/Workspace/paper4/coder/results/hpo/optuna_trials_<model_name>.csv`.
2. Write unit/integration tests in `tests/test_hpo.py`.
3. Run `/home/imnyj/venv/bin/pytest tests/ -v` and ensure all tests pass.
4. Update `progress_sync.md` with best hyperparameters table.
5. Write `handoff.md` and send completion message.

Rules:
- DO NOT CHEAT. All implementations and HPO runs must be genuine.
- Use Korean for your report and documentation.
