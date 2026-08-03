---
name: simulation-tuner
description: Skill for running continuous hyperparameter tuning simulation loops.
---
# Simulation Tuner Skill

- **Goal Loop Protocol**: When tasked with finding an optimal parameter trade-off (e.g., performance vs complexity in `paper4`), iterate through bash scripts (like `./run_simulation.sh`) continuously until the sweet spot is found.
- **Worker Delegation**: Delegate script modifications to `worker_coder` and result analysis to `worker_analyst`.
- **Iterative Refinement**: Analyze CSV outputs after each run. If a parameter configuration fails to meet the criteria, adjust and run again.
- **Result Reporting**: Report the final optimal configuration, evaluation metrics (e.g., Accuracy, PDR, Delay), and generated plots. Do not stop execution until the goal is fully satisfied.
