# Teamwork Project Prompt — Final

> Status: Launched
> Goal: Execute the ENTIRE training, Optuna optimization, and data extraction pipeline using ONLY real simulations. NO mock data allowed.

Working directory: /home/imnyj/Workspace/paper4

## Requirements

### R1. Strictly Real Simulations & No Mock Data
- The Coder MUST NOT generate mock CSV files using `numpy.random` or mathematical formulas.
- ALL data must be extracted by actually running the SUMO simulation scripts and RL environments located in the codebase.
- The user will audit the source of the simulation files later to ensure actual SUMO/RL code was executed.

### R2. Minimum 200,000 Steps for Training
- Every single RL model (all baselines and proposed REMO-DQN) must be trained for a MINIMUM of 200,000 steps.
- The resulting `reward_convergence.csv` and `ablation_study.csv` MUST contain actual data points spanning 200,000 steps, clearly demonstrating the convergence point and post-convergence stability.

### R3. Optuna Hyperparameter Optimization
- Before the final 200,000-step training, every model must undergo Optuna hyperparameter optimization.
- The models must be trained using the optimal hyperparameters found by Optuna to ensure they are evaluated in their best state.
- The Optuna results must be saved, as the user will audit this optimization process.

### R4. Model Checkpointing
- Once a model completes its 200,000-step training, its final weights must be saved (e.g., `.pth` or `.pkl`) in the `data/models/` directory so they can be loaded for future evaluation graphs (CBR, PDR, AoI vs Density/Distance).

### R5. Visualization & Walkthrough
- After all real data is collected, generate the 11 target graphs (as numbered 350 DPI PNGs).
- The Coder-Critic loop must ensure the graphs accurately reflect the 200,000 steps and the Optuna-optimized performance.

## Acceptance Criteria
- [ ] No mock data generation scripts exist; all data comes from `sim_engine.py` or equivalent simulation runners.
- [ ] All models are trained for $\ge$ 200,000 steps.
- [ ] Optuna optimization logs/CSVs are generated and used for the final training.
- [ ] All 17 trained models are saved in `data/models/`.
- [ ] All graphs correctly visualize this rigorously collected data.
