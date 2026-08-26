# DISPATCH LOG

## 2026-08-26T22:02:31+09:00

**Task**: E2E Testing Orchestration for AoI-aware V2I uplink RL scheduling pipeline
**Mission**:
1. Design and build a requirement-driven, opaque-box E2E testing track for the AoI-aware V2I uplink RL pipeline.
2. Formulate test cases covering all 4 tiers:
   - Tier 1: Feature Coverage (Signal extraction, Stop/start prediction, Heuristic grants, State vectorization, Action decoding, Replay buffer, Baselines forward passes, Optuna trial execution, Hot-swap synchronization, Benchmark metrics calculation)
   - Tier 2: Boundary & Corner Cases (zero/max speed, extreme distances, signal phase boundaries, zero contention, max contention/interference, empty batches, NaN/Inf guard in hot-swap)
   - Tier 3: Cross-Feature Combinations (Dynamics prediction + Heuristic grants, Vectorizer + Hybrid decoder + Baselines, Hot-swap during simulation, Optuna study + Model export + Evaluation harness)
   - Tier 4: Real-World Simulation Workload (Multi-density full simulation run with heuristic vs RL baselines, verifying metric convergence and CSV outputs)
3. Create `TEST_INFRA.md` at project root.
4. Implement test scripts in `/home/imnyj/Workspace/paper4/coder/tests/` using pytest or standalone runners.
5. Publish `TEST_READY.md` at project root when complete, summarizing test coverage and providing the execution command.
6. When done, write `handoff.md` and send a message.
