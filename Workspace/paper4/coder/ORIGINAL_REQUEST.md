# Original User Request

## 2026-08-30T15:01:38Z

# Teamwork Project Prompt

> Status: Ready for launch
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: small focused team

This is a single self-contained fix; keep it small and focused.
Update `run_all.py` to load and apply optimal hyperparameters from an HPO CSV file, so that the 9 baselines are trained using their best configurations instead of default values.

Working directory: /home/imnyj/Workspace/paper4/coder
Integrity mode: development

## Requirements

### R1. HPO Parameter Loading
Add a command-line argument `--hparams-csv` to `run_all.py` (default: `results/hpo/optuna_best_params.csv`). Parse this CSV file to extract the `hparams_json` column for each model.

### R2. Application to Training
When initializing the training loop for each model via `run_hot_swap_training`, pass the parsed hyperparameters to the `hparams` argument. If the CSV file is missing or a model has no entry, it should gracefully fall back to the default hyperparameters and log a warning.

## Acceptance Criteria

### Execution Logic
- [ ] `run_all.py` accepts the `--hparams-csv` argument.
- [ ] Models listed in the CSV are trained with their specific hyperparameters.
- [ ] The script does not crash if the CSV file is entirely missing; it logs a warning and proceeds with default parameters.

### Verification
- [ ] Running `python run_all.py --episodes 1 --steps-per-episode 10 --models PPO` completes successfully without crashing, regardless of whether the CSV exists.
