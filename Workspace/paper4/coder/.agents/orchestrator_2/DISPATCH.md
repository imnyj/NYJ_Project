# Dispatch Assignment

## 2026-08-26T15:02:40Z
You are the Project Orchestrator for the genuine SUMO V2I AoI RL Scheduling Pipeline project.

### Working Directory and Workspace
- Working directory: `/home/imnyj/Workspace/paper4/coder/.agents/orchestrator_2/`
- Project root: `/home/imnyj/Workspace/paper4/coder`
- Request file: `/home/imnyj/Workspace/paper4/coder/.agents/ORIGINAL_REQUEST.md`
- Scenario Reference: `/home/imnyj/Workspace/paper4/idea/scenario.md`
- Design Reference: `/home/imnyj/Workspace/paper4/Conversation.md`
- Existing Simulator Code: `/home/imnyj/Workspace/paper4/coder/src/NetSim.py`, `/home/imnyj/Workspace/paper4/coder/src/Communications.py`, `/home/imnyj/Workspace/paper4/coder/src/sumo/make_sumo_set.py`

### User Request & Requirements
Implement the genuine V2I AoI scheduling RL pipeline using the real SUMO simulator (`NetSim.py`, `Communications.py`, `make_sumo_set.py`), completely discarding prior synthetic mock implementations. The pipeline must strictly train and evaluate 9 baseline models for a minimum of 200,000 steps each, rigorously enforcing anti-cheating integration checks.

1. **R1. Genuine Environment Integration**:
   - Construct the simulation environment adhering strictly to `scenario.md` and `Conversation.md` (State, Action, Reward structures).
   - The environment MUST use `make_sumo_set.py` for setup, and MUST invoke `NetSim.py` and `Communications.py` at every single step to calculate vehicle coordinates and RSSI, respectively.
   - Hardcoded assertions exist in the `step()` function that crash the training loop if `NetSim.py` and `Communications.py` are bypassed.

2. **R2. Baseline Implementations**:
   - Implement the 9 selected baselines (3 foundation models like PPO/SAC/TD3 via SB3/CleanRL, and 6 advanced models) adapting them to the hybrid action space (continuous \Delta and power, discrete subchannel).

3. **R3. Rigorous Training & Optimization (HPO) Setup**:
   - Set up a robust training loop and Optuna hyperparameter optimization framework designed to run for a minimum of 200,000 steps (e.g., 2000 steps * 100 episodes).
   - Prepare logging (TensorBoard, CSV).

4. **R4. Implement First, Run Later (Review Phase)**:
   - First, write all the code for the environment, the 9 baselines, the Optuna harness, and the `verify_environment.py` script.
   - `verify_environment.py` must automatically test that stepping the RL environment triggers actual coordinate changes inside the SUMO simulation (proving `NetSim.py` is active).
   - Run short dummy tests (e.g., 10 steps) to mathematically and functionally prove the integration works without crashing.
   - **CRITICAL**: Do NOT start the massive 200,000-step training loops yet. You must halt execution and await manual user code review and approval before the heavy compute phase begins.

5. **Anti-Mocking & Verification Acceptance Criteria**:
   - `verify_environment.py` exists and automatically tests coordinate changes from real SUMO.
   - Hardcoded assertions in `step()` prevent any bypass of `NetSim.py` / `Communications.py`.
   - Pipeline structurally ready for 200,000 steps.
   - Continuously update `/home/imnyj/Workspace/paper4/coder/progress_sync.md` and your own `progress.md` and `BRIEFING.md`.
