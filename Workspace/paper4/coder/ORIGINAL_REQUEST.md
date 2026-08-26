# Original User Request

## Initial Request — 2026-08-26T21:58:24+09:00

You are the Project Orchestrator for the AoI-aware V2I uplink RL scheduling pipeline project.

### Working Directory and Workspace
- Working directory: `/home/imnyj/Workspace/paper4/coder/.agents/orchestrator_1/`
- Project root: `/home/imnyj/Workspace/paper4/coder`
- Request file: `/home/imnyj/Workspace/paper4/coder/ORIGINAL_REQUEST.md`

### Core Mission & Requirements
Implement the complete reinforcement learning scheduling pipeline (S2.5 through S5) for the AoI-aware V2I uplink project:
1. **R1. Signal-based Dynamics Prediction & Heuristic Baseline (S2.5)**:
   - Extract traffic light states, distance to stopline, and remaining phase using TraCI.
   - Implement heuristic scheduler that forces an update when a vehicle is about to stop or start.
2. **R2. RL Agent Interface & Baselines**:
   - Vectorize the state, decode hybrid action space (continuous interval/power, discrete subchannel), assemble transitions with retrospective estimation error.
   - Implement 9 baselines:
     * 3 basic models (PPO, SAC, TD3)
     * 3 latest models (e.g., MAPPO, etc.)
     * 3 state-of-the-art similar models
3. **R3. Hyperparameter Optimization (Optuna)**:
   - Use Optuna to search and find optimal hyperparameters for each of the 9 baseline models.
   - Save best hyperparameters for each model into CSV files.
4. **R4. Training Loop & Dual Model Hot-swap (S4)**:
   - Implement Act/Rest mode training pipeline with hardware isolation (training does not impact fast inference).
5. **R5. Evaluation Harness (S5)**:
   - Evaluation script running benchmarks (Baselines vs Heuristic) across varying vehicle densities and seeds, outputting metrics to CSV.
6. **R6. Halt Before Proposed Method**:
   - CRITICAL: Do NOT begin designing the novel proposed architecture. Stop execution and await explicit user permission after all baselines are optimized and evaluated.
7. **R7. Handover Documentation**:
   - Continuously maintain `/home/imnyj/Workspace/paper4/coder/progress_sync.md` detailing completed tasks, optimal hyperparameters, errors, and next goals.

### Guidelines
- Decompose tasks recursively into atomic sub-tasks and spawn specialist subagents.
- Continuously update your `progress.md` and `BRIEFING.md` in your directory, and `/home/imnyj/Workspace/paper4/coder/progress_sync.md`.
- Ensure all acceptance criteria are verified:
  * R1-R2: Verification script verifying all 9 baseline models instantiate correctly with hybrid action space.
  * R3: Optuna runs successfully on baselines and generates CSV.
  * R4-R5: Dual-mode training and evaluation harness executes without crashing and logs metrics to CSV.
  * R6-R7: `progress_sync.md` is complete and halts before proposed method.
- Use Korean for documentation/progress reporting per workspace rules.
- When finished, summarize your work and send a completion report back.
 
+## Follow-up — 2026-08-26T15:02:00Z
+
+Use a very large team of agents.
+
+Implement the genuine V2I AoI scheduling RL pipeline using the real SUMO simulator (`NetSim.py`, `Communications.py`, `make_sumo_set.py`), completely discarding prior synthetic mock implementations. The pipeline must strictly train and evaluate 9 baseline models for a minimum of 200,000 steps each, rigorously enforcing anti-cheating integration checks.
+
+Working directory: /home/imnyj/Workspace/paper4/coder
+Integrity mode: demo
+
+## Requirements
+
+### R1. Genuine Environment Integration
+Construct the simulation environment adhering strictly to `scenario.md` and `Conversation.md` (State, Action, Reward structures). The environment MUST use `make_sumo_set.py` for setup, and MUST invoke `NetSim.py` and `Communications.py` at every single step to calculate vehicle coordinates and RSSI, respectively.
+
+### R2. Baseline Implementations
+Implement the 9 selected baselines (3 foundation models like PPO/SAC/TD3 via SB3/CleanRL, and 6 advanced models) adapting them to the hybrid action space (continuous \Delta and power, discrete subchannel). 
+
+### R3. Rigorous Training & Optimization (HPO) Setup
+Set up a robust training loop and Optuna hyperparameter optimization framework designed to run for a minimum of 200,000 steps (e.g., 2000 steps * 100 episodes). Prepare the logging (TensorBoard, CSV).
+
+### R4. Implement First, Run Later (Review Phase)
+First, write all the code for the environment, the 9 baselines, the Optuna harness, and the `verify_environment.py` script. Run short dummy tests (e.g., 10 steps) to mathematically and functionally prove the integration works without crashing. **Do NOT start the massive 200,000-step training loops yet.** You must halt execution and await manual user code review and approval before the heavy compute phase begins.
+
+## Acceptance Criteria
+
+### Verification & Anti-Mocking
+- [ ] A script `verify_environment.py` exists and automatically tests that stepping the RL environment triggers actual coordinate changes inside the SUMO simulation (proving `NetSim.py` is active).
+- [ ] Hardcoded assertions exist in the `step()` function that crash the training loop if `NetSim.py` and `Communications.py` are bypassed.
+- [ ] The pipeline is structurally ready to support 200,000 steps of real execution data per evaluated model.
+- [ ] Execution has halted, and the user has been notified to review the codebase before giving the green light for the heavy run.

