## 2026-08-26T13:02:31Z
You are the Sub-Orchestrator for Milestone 1: Signal-based Dynamics Prediction & Heuristic Baseline (S2.5).

Your working directory is: /home/imnyj/Workspace/paper4/coder/.agents/sub_orch_m1/
Project root: /home/imnyj/Workspace/paper4/coder
Original Request: /home/imnyj/Workspace/paper4/coder/ORIGINAL_REQUEST.md
Project Plan: /home/imnyj/Workspace/paper4/coder/PROJECT.md

Your Mission (Milestone 1):
1. Extract traffic light states, distance to stopline, and remaining phase using TraCI (`sumo.vehicle.getNextTLS`, `sumo.trafficlight.getNextSwitch`).
2. Implement dynamics transition indicators ($I_{\text{stop}}, I_{\text{start}}$) in `src/dynamics_predictor.py` to reliably predict when a vehicle is about to stop or start.
3. Implement `src/heuristic_scheduler.py` (`HeuristicScheduler` class):
   - Imminent stop/start: Force immediate state update grant ($\Delta_i = 0.5\text{s}$, low-contention subchannel, $p_i = 25.0\text{dBm}$).
   - Stopped vehicles at long red phase: Backoff ($\Delta_i = \min(\Delta_{\max}, t_{\text{left}} - 1.0\text{s})$) to avoid wasteful updates while zero-velocity extrapolation is accurate.
   - Cruising: Dynamic interval selection.
4. Integrate with `src/aoi_env.py` and verify that the simulation runs with `HeuristicScheduler` seamlessly.
5. Create comprehensive unit tests in `tests/test_dynamics_predictor.py` and run them.
6. Run the Explorer -> Worker -> Reviewer -> Challenger -> Auditor cycle or execute implementation and validation thoroughly.
7. Write `handoff.md` and report back when Milestone 1 passes all checks.
