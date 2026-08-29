## 2026-08-27T01:58:25Z
Worker 3 for Milestone M3 (Environment Knobs & HPO).
Working directory: /home/imnyj/Workspace/paper4/coder/.agents/worker_m3/

Read reference documents:
1. /home/imnyj/Workspace/paper4/coder/.agents/ORIGINAL_REQUEST.md
2. /home/imnyj/Workspace/paper4/coder/PROJECT.md
3. /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_3/handoff.md
4. /home/imnyj/Workspace/paper4/Conversation.md

YOUR EXCLUSIVELY OWNED FILES:
- src/NetSim.py
- src/sumo/make_sumo_set.py
- src/evaluate.py
- src/hpo.py

TASKS FOR M3:
1. `src/NetSim.py`:
   - In `pre_define()`, set `sumo_set.RSU_RANGE = 300.0`, `sumo_set.OUTAGE_ZONE = 300.0` (eliminate 800.0 override).
   - In SUMO CLI command args, change `"--step-length", "1.0"` to `"--step-length", "0.1"`.
2. `src/sumo/make_sumo_set.py`:
   - Ensure `RSU_RANGE: float = 300.0`, `STEP_LENGTH: float = 0.1`.
   - Regenerate SUMO configuration files if necessary.
3. `src/evaluate.py`:
   - Set `rsu_range = 300.0` default.
   - In `evaluate_single_run`, fix `"speed": 10.0` to use actual vehicle speed `float(getattr(env, "last_speeds", {}).get(vid, 0.0))`.
4. `src/hpo.py`:
   - Ensure `sample_reward_weights(trial)` samples `w1, w2, w3, w4` with ranges (w1 in [0.10, 1.00], w2, w3, w4 in [0.02, 0.60]), normalized so sum(w_i) = 1.0.
   - Pass `reward_weights` to `AoiV2IEnv` and ensure `w1..w4` are recorded in Optuna trial CSVs.
5. VERIFICATION:
   - Run verification commands to ensure `RSU_RANGE=300.0` and `step-length=0.1`.
   - Verify `evaluate_single_run` passes with `HeuristicScheduler`.
   - Verify `sample_reward_weights` works with Optuna.
