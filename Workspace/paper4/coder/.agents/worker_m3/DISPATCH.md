## 2026-08-27T00:07:32+09:00

You are worker_m3.
Working directory: /home/imnyj/Workspace/paper4/coder/.agents/worker_m3/
Request file: /home/imnyj/Workspace/paper4/coder/.agents/ORIGINAL_REQUEST.md
Scenario reference: /home/imnyj/Workspace/paper4/idea/scenario.md
Conversation design: /home/imnyj/Workspace/paper4/Conversation.md
Project plan: /home/imnyj/Workspace/paper4/coder/PROJECT.md
Explorer 3 handoff: /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_genuine_3/handoff.md
Explorer 3 analysis: /home/imnyj/Workspace/paper4/coder/.agents/explorer_survey_genuine_3/analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE OWNERSHIP:
- /home/imnyj/Workspace/paper4/coder/src/hot_swap_trainer.py
- /home/imnyj/Workspace/paper4/coder/src/hpo.py
- /home/imnyj/Workspace/paper4/coder/src/evaluate.py
- /home/imnyj/Workspace/paper4/coder/tests/test_dummy_verification.py

TASK:
1. Read Explorer 3's analysis and handoff report.
2. Discard all mock/synthetic bypass code (`SyntheticVehicle`, `EvalSyntheticVehicle`, local kinematic dummy loops) from `src/hot_swap_trainer.py`, `src/hpo.py`, and `src/evaluate.py`.
3. Update `src/hot_swap_trainer.py`:
   - Connect training loop directly to `AoiV2IEnv` (real SUMO).
   - Add TensorBoard logging via `torch.utils.tensorboard.SummaryWriter` (logging episodic reward, loss, AoI, estimation error, etc. to `logs/tensorboard/`).
   - Add periodic checkpointing saving models to `checkpoints/<model>_ep{ep:03d}.pt` and `checkpoints/<model>_best.pt`.
   - Architect and configure the training loop to support 200,000 steps (e.g. 2,000 steps * 100 episodes) with robust memory management (`torch.cuda.empty_cache()`, clean env reset).
   - Ensure the Act/Rest dual-model hot-swap mechanism works seamlessly with the genuine environment.
4. Update `src/hpo.py`:
   - Connect Optuna objective evaluation directly to `AoiV2IEnv` (discarding all synthetic vehicles).
   - Ensure trials run real simulation rollouts across multiple seeds, logging trials to `results/hpo/optuna_trials_<model>.csv` and best parameters to `results/hpo/optuna_best_params.csv`.
5. Update `src/evaluate.py`:
   - Connect evaluation benchmark directly to real `AoiV2IEnv` across densities (15..55 veh/km) and seeds (42..999).
   - Calculate 6 IEEE TWC metrics and export to `results/eval/`.
6. Implement `tests/test_dummy_verification.py`:
   - Short Dummy Run test (10 steps) that runs all 9 baseline models on `AoiV2IEnv`, performs 1 hot-swap step, 1 Optuna trial step, and 1 evaluation step to mathematically and functionally prove 100% crash-free integration in <15 seconds.
7. Run `pytest tests/test_dummy_verification.py tests/test_hot_swap.py tests/test_hpo.py` and existing test suites to verify everything passes.
8. Write your handoff report to `/home/imnyj/Workspace/paper4/coder/.agents/worker_m3/handoff.md` and report back via send_message. Use Korean for reports as per GEMINI.md.
