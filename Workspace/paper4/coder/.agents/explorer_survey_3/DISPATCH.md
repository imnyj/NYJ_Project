## 2026-08-26T12:59:12Z
You are Explorer Survey 3 (Optuna HPO, Hot-swap S4 & Evaluation S5 Infra Explorer).

Your working directory is: /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_3/
Please read the original request at: /home/imnyj/Workspace/paper4/coder/ORIGINAL_REQUEST.md

Your Mission:
1. Investigate Optuna availability, search space design, objective function formulation, and CSV logging schema for R3 (Hyperparameter Optimization).
2. Investigate requirements and architecture for R4 (Training Loop & Dual Model Hot-swap S4):
   - Act/Rest mode training pipeline.
   - Hardware isolation mechanism (ensuring heavy training does not block fast real-time inference during simulation steps).
   - Hot-swap mechanism between Act model (active inference) and Rest model (background training).
3. Investigate requirements and architecture for R5 (Evaluation Harness S5):
   - Benchmark execution across varying vehicle densities and random seeds.
   - Comparative evaluation: Heuristic baseline vs 9 optimized RL baselines.
   - Metric definitions: Mean AoI, Peak AoI, Outage/Packet Loss rate, Estimation Error, Power Consumption, Fairness.
   - CSV output structure and summary tables.
4. Write your comprehensive analysis to `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_3/handoff.md` and send a message when done.

Rules:
- Read-only exploration! Do NOT modify any existing source code.
- Write your metadata and reports ONLY into `/home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_3/`.
- Use Korean for your report and findings.
