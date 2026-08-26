## 2026-08-26T13:14:03Z

You are the Sub-Orchestrator for Milestone 4: Training Loop & Dual Model Hot-swap (S4 / R4).

Your working directory is: /home/imnyj/Workspace/paper4/coder/.agents/sub_orch_m4/
Project root: /home/imnyj/Workspace/paper4/coder
Original Request: /home/imnyj/Workspace/paper4/coder/ORIGINAL_REQUEST.md
Project Plan: /home/imnyj/Workspace/paper4/coder/PROJECT.md

Your Mission (Milestone 4):
1. Implement `src/hot_swap_trainer.py`:
   - Dual-Model Act/Rest architecture: Act model (fast serving/inference, `model.eval()`, <1ms) running on `cuda:0` or CPU; Rest model (background training on replay buffer, `model.train()`) running on `cuda:1` (or dedicated background worker).
   - Non-blocking thread-safe transition queue streaming transitions from simulation steps to background trainer.
   - Zero-downtime atomic hot-swap manager (`DualModelHotSwapManager`) with NaN/Inf guard and in-place tensor copy.
   - Provide full training loop execution function (`run_hot_swap_training(model_name, total_steps, ...)`) integrating with `src/aoi_env.py`.
2. Write unit & integration tests in `tests/test_hot_swap.py`.
3. Run `/home/imnyj/venv/bin/pytest tests/ -v` and verify 100% pass rate.
4. Write `handoff.md` and send completion message.

Rules:
- DO NOT CHEAT. All implementations must be genuine.
- Use Korean for your report and documentation.
