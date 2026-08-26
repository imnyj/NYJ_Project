## 2026-08-26T13:20:53Z

<USER_REQUEST>
You are the Sub-Orchestrator for Milestone 5: Evaluation Harness & Benchmark Verification (S5 / R5).

Your working directory is: /home/imnyj/Workspace/paper4/coder/.agents/sub_orch_m5/
Project root: /home/imnyj/Workspace/paper4/coder
Original Request: /home/imnyj/Workspace/paper4/coder/ORIGINAL_REQUEST.md
Project Plan: /home/imnyj/Workspace/paper4/coder/PROJECT.md
Optimal Hyperparameters: /home/imnyj/Workspace/paper4/coder/results/hpo/optuna_best_params.csv

Your Mission (Milestone 5):
1. Implement `src/evaluate.py`:
   - Load optimal hyperparameters from `/home/imnyj/Workspace/paper4/coder/results/hpo/optuna_best_params.csv` to instantiate the 9 baseline models (`HybridPPO`, `HybridSAC`, `HybridTD3`, `MAPPO`, `HyARPPO`, `MPDQN`, `PureAoI`, `DuelingQAoI`, `SACAoI`) plus the `HeuristicScheduler` (total 10 models).
   - Execute benchmark evaluation across varying vehicle densities (e.g., 15.0, 25.0, 35.0, 45.0, 55.0 veh/km) and random seeds (e.g., 42, 101, 2024, 777, 999).
   - Accurately compute 6 IEEE TWC metrics:
     1. Mean AoI
     2. Peak AoI
     3. Outage / Packet Loss rate
     4. Estimation Error (mean, max, low-speed vs high-speed error)
     5. Power Consumption & Total RF Energy
     6. Jain's Fairness Index for AoI and Error
   - Export CSV results to:
     * `/home/imnyj/Workspace/paper4/coder/results/eval/eval_raw_runs.csv`
     * `/home/imnyj/Workspace/paper4/coder/results/eval/eval_summary_by_density.csv`
     * `/home/imnyj/Workspace/paper4/coder/results/eval/eval_leaderboard.csv`
2. Write unit & integration tests in `tests/test_evaluation.py`.
3. Run `/home/imnyj/venv/bin/pytest tests/ -v` and verify 100% pass rate.
4. Update `progress_sync.md` with evaluation benchmark summary.
5. Write `handoff.md` and send completion message.

Rules:
- DO NOT CHEAT. All evaluation runs, physics simulation, and CSV metrics must be genuine.
- Use Korean for your report and documentation.
</USER_REQUEST>
