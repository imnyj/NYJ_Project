# Original User Request

## Initial Request — 2026-08-26T12:57:52Z

Use a very large team of agents.

Implement the complete reinforcement learning scheduling pipeline (S2.5 through S5) for the AoI-aware V2I uplink project. Ensure that a detailed progress and handover document (`progress_sync.md`) is continuously updated to allow seamless transition between different AI assistants in case of usage limits. 

Working directory: /home/imnyj/Workspace/paper4/coder
Integrity mode: benchmark

## Requirements

### R1. Signal-based Dynamics Prediction & Heuristic Baseline (S2.5)
Extract traffic light states, distance to stopline, and remaining phase using TraCI. Implement a heuristic scheduler that forces an update when a vehicle is about to stop or start.

### R2. RL Agent Interface & Baselines
Vectorize the state, decode the hybrid action space (continuous interval/power, discrete subchannel), and assemble transitions with retrospective estimation error. Implement 9 baselines: 3 basic models (PPO, SAC, TD3), 3 latest models (e.g., MAPPO), and 3 state-of-the-art similar models.

### R3. Hyperparameter Optimization (Optuna)
Use Optuna to search and find the optimal hyperparameters for each of the 9 baseline models. Save the best hyperparameters for each model into a CSV file.

### R4. Training Loop & Dual Model Hot-swap (S4)
Implement an Act/Rest mode training pipeline with hardware isolation, ensuring training does not impact fast inference times.

### R5. Evaluation Harness (S5)
Build an evaluation script to run benchmarks (Baselines vs. Heuristic) across varying vehicle densities and seeds, outputting the metrics to a CSV file.

### R6. Halt Before Proposed Method
**CRITICAL**: Do NOT begin designing the novel proposed architecture. You must stop execution and await explicit user permission after all baselines are optimized and evaluated.

### R7. Handover Documentation
Maintain a `progress_sync.md` file detailing completed tasks, optimal hyperparameters, errors, and next goals.

## Acceptance Criteria

### R1-R2 Verification
- [ ] A script verifies all 9 baseline models instantiate correctly with the hybrid action space.

### R3 Verification
- [ ] Optuna runs successfully for a few trials on a baseline and generates a CSV file with the selected hyperparameters.

### R4-R5 Verification
- [ ] The dual-mode training and evaluation harness executes without crashing and logs metrics to a CSV.

### R6-R7 Verification
- [ ] `progress_sync.md` exists, is up-to-date, and execution naturally halts for user input before the proposed method design phase.

## Follow-up — 2026-08-26T15:02:00Z

Use a very large team of agents.

Implement the genuine V2I AoI scheduling RL pipeline using the real SUMO simulator (`NetSim.py`, `Communications.py`, `make_sumo_set.py`), completely discarding prior synthetic mock implementations. The pipeline must strictly train and evaluate 9 baseline models for a minimum of 200,000 steps each, rigorously enforcing anti-cheating integration checks.

Working directory: /home/imnyj/Workspace/paper4/coder
Integrity mode: demo

## Requirements

### R1. Genuine Environment Integration
Construct the simulation environment adhering strictly to `scenario.md` and `Conversation.md` (State, Action, Reward structures). The environment MUST use `make_sumo_set.py` for setup, and MUST invoke `NetSim.py` and `Communications.py` at every single step to calculate vehicle coordinates and RSSI, respectively.

### R2. Baseline Implementations
Implement the 9 selected baselines (3 foundation models like PPO/SAC/TD3 via SB3/CleanRL, and 6 advanced models) adapting them to the hybrid action space (continuous \Delta and power, discrete subchannel). 

### R3. Rigorous Training & Optimization (HPO) Setup
Set up a robust training loop and Optuna hyperparameter optimization framework designed to run for a minimum of 200,000 steps (e.g., 2000 steps * 100 episodes). Prepare the logging (TensorBoard, CSV).

### R4. Implement First, Run Later (Review Phase)
First, write all the code for the environment, the 9 baselines, the Optuna harness, and the `verify_environment.py` script. Run short dummy tests (e.g., 10 steps) to mathematically and functionally prove the integration works without crashing. **Do NOT start the massive 200,000-step training loops yet.** You must halt execution and await manual user code review and approval before the heavy compute phase begins.

## Acceptance Criteria

### Verification & Anti-Mocking
- [ ] A script `verify_environment.py` exists and automatically tests that stepping the RL environment triggers actual coordinate changes inside the SUMO simulation (proving `NetSim.py` is active).
- [ ] Hardcoded assertions exist in the `step()` function that crash the training loop if `NetSim.py` and `Communications.py` are bypassed.
- [ ] The pipeline is structurally ready to support 200,000 steps of real execution data per evaluated model.
- [ ] Execution has halted, and the user has been notified to review the codebase before giving the green light for the heavy run.

## 2026-08-27T01:53:03Z

Use a very large team of agents.

Take over and complete the architectural fixes that Claude started but left incomplete due to a quota limit. Specifically, align the codebase exactly with `Conversation.md` by fixing the reward logic, adjusting action/state bounds, fixing the evaluate/resume bugs, and replacing the unauthorized baselines with the 6 verified IEEE baselines.

Working directory: /home/imnyj/Workspace/paper4/coder
Integrity mode: demo

## Requirements

### R1. Complete Agent A's Tasks (Trainer & Env Fixes)
In `src/hot_swap_trainer.py` and `src/aoi_env.py`:
- Restore the 4-term reward formula by re-adding the $I_{\text{redundant}}$ penalty.
- Generalize power normalization to `(p - p_min) / (p_max - p_min)`.
- Fix the `tx_powers[-1]` bug so each vehicle uses its own transmission power.
- Update the Anti-Mocking Assertion A4 to strictly match the new 4-term reward formula.
- Fix the `resume` logic so it tracks `best_reward` inside the `.pt` checkpoint file to prevent weak episodes from overwriting `best.pt`.

### R2. Complete Agent B's Tasks (Action/State Bounds)
In `src/rl_interface.py`:
- Hardcode the single source of truth for action bounds: Power $\in [10.0, 23.0]$ dBm. For the update interval $\Delta$ (Delta), the maximum upper bound MUST be set to match the maximum length of the Red traffic light phase in the SUMO environment.
- Ensure `StateVectorizer` strictly outputs 18 dimensions (including `n_queue` and `heading`).

### R3. Complete Agent C's Tasks (Environment Knobs & HPO)
In `src/sumo/make_sumo_set.py`, `src/hpo.py`, `src/evaluate.py`:
- Ensure `RSU_RANGE = 300.0`.
- Ensure SUMO `step-length = 0.1`.
- Fix the hardcoded `"speed": 10.0` in `evaluate.py` to use the actual vehicle speed.
- In `hpo.py`, add `w1, w2, w3, w4` into the Optuna search space so the reward weights are optimized.

### R4. Baseline Scraping & Initialization
Delete all existing baseline implementations (including the `src/baselines/` directory) and remove any code in the training/evaluation scripts that attempts to load them. Do NOT implement any new baselines (neither the basic ones nor the IEEE ones) at this time. The user will re-evaluate and provide new baselines later.

## Acceptance Criteria

### Verification
- [ ] Running `pytest tests/` passes successfully, specifically proving that the 4-term reward assertion (A4) does not crash the environment.
- [ ] `src/rl_interface.py` correctly defines $P_{max} = 23.0$ and dynamically links $\Delta_{max}$ to the Red light phase maximum.
- [ ] The `src/baselines/` directory and all fake/old baseline codes are completely deleted.
- [ ] Execution halts and notifies the user for code review upon completion.

