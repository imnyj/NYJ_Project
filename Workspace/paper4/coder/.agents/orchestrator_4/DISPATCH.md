## 2026-08-27T01:53:58Z

You are the Project Orchestrator (orchestrator_4) for the AoI-aware V2I uplink RL scheduling pipeline architectural fixes and baseline scraping milestone.

### Working Directory and Workspace
- Working directory: /home/imnyj/Workspace/paper4/coder/.agents/orchestrator_4/
- Project root: /home/imnyj/Workspace/paper4/coder
- Request file: /home/imnyj/Workspace/paper4/coder/.agents/ORIGINAL_REQUEST.md (specifically the latest request under ## 2026-08-27T01:53:03Z)
- Conversation / Architecture Reference: /home/imnyj/Workspace/paper4/Conversation.md
- Scenario Reference: /home/imnyj/Workspace/paper4/idea/scenario.md

### Core Mission & Requirements
Take over and complete the architectural fixes that Claude started, aligning the codebase exactly with Conversation.md:

1. **R1. Complete Agent A's Tasks (Trainer & Env Fixes)**:
   In `src/hot_swap_trainer.py` and `src/aoi_env.py`:
   - Restore the 4-term reward formula by re-adding the $I_{\text{redundant}}$ penalty.
   - Generalize power normalization to `(p - p_min) / (p_max - p_min)`.
   - Fix the `tx_powers[-1]` bug so each vehicle uses its own transmission power.
   - Update the Anti-Mocking Assertion A4 to strictly match the new 4-term reward formula.
   - Fix the `resume` logic so it tracks `best_reward` inside the `.pt` checkpoint file to prevent weak episodes from overwriting `best.pt`.

2. **R2. Complete Agent B's Tasks (Action/State Bounds)**:
   In `src/rl_interface.py`:
   - Hardcode the single source of truth for action bounds: Power $\in [10.0, 23.0]$ dBm. For the update interval $\Delta$ (Delta), the maximum upper bound MUST be set to match the maximum length of the Red traffic light phase in the SUMO environment.
   - Ensure `StateVectorizer` strictly outputs 18 dimensions (including `n_queue` and `heading`).

3. **R3. Complete Agent C's Tasks (Environment Knobs & HPO)**:
   In `src/sumo/make_sumo_set.py`, `src/hpo.py`, `src/evaluate.py`:
   - Ensure `RSU_RANGE = 300.0`.
   - Ensure SUMO `step-length = 0.1`.
   - Fix the hardcoded `"speed": 10.0` in `evaluate.py` to use the actual vehicle speed.
   - In `hpo.py`, add `w1, w2, w3, w4` into the Optuna search space so the reward weights are optimized.

4. **R4. Baseline Scraping & Initialization**:
   - Delete all existing baseline implementations (including the `src/baselines/` directory) and remove any code in the training/evaluation scripts that attempts to load them.
   - Do NOT implement any new baselines (neither the basic ones nor the IEEE ones) at this time. The user will re-evaluate and provide new baselines later.

5. **Acceptance Criteria & Verification**:
   - Running `pytest tests/` passes successfully, specifically proving that the 4-term reward assertion (A4) does not crash the environment.
   - `src/rl_interface.py` correctly defines $P_{max} = 23.0$ and dynamically links $\Delta_{max}$ to the Red light phase maximum.
   - The `src/baselines/` directory and all fake/old baseline codes are completely deleted.
   - Execution halts and notifies the user for code review upon completion.
