# Project: Paper4 V2X Congestion Control DRL

## Architecture
- V2X Environment & Congestion Control (DCC) simulation framework.
- Core models: REMO-DQN (ResNet-MoE-Dueling DQL) + 13 RL baselines + 7 non-RL baselines.
- Main entry point & runner: `code/run_parallel_evaluation.py` (handles training & parallel evaluation).
- Evaluation output path: `data/evaluation/eval_density_results.csv`, `data/evaluation/eval_speed_results.csv`.
- Visualization module: `visualizer/` (`generate_ieee_plots.py`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Checkpoint Resume | Auto-detect existing episode logs (`*_convergence.csv`) and resume training from episode ~52 to 100 without overwriting | M1 | ORIGINAL_REQUEST R1 |
| 2 | 14 Model Training Completion | Complete training for all 14 RL models to reward convergence and save `.pth`/`.pkl` weights and logs | M1 | ORIGINAL_REQUEST R1 |
| 3 | Density Performance Evaluation | Evaluate all models across vehicle density sweep [20,40,60,80,100,120] and extract `eval_density_results.csv` | M2 | ORIGINAL_REQUEST R2 |
| 4 | Speed Performance Evaluation | Evaluate all models across vehicle speed sweep [20,40,60,80,100] and extract `eval_speed_results.csv` | M2 | ORIGINAL_REQUEST R2 |
| 5 | Data Integrity Verification | Ensure CSVs have no nulls, complete metrics (PDR, CBR, AoI, energy, ETSI compliance) | M2 | ORIGINAL_REQUEST R2 |
| 6 | IEEE Visualization Automation | Develop script to auto-generate publication-grade IEEE comparison plots (Convergence, CBR Trace, PDR vs Density, AoI vs Density, CBR CDF, etc.) | M3 | ORIGINAL_REQUEST R3 |
| 7 | IEEE Compliance Review | Agent-as-judge Critic review of generated plots for IEEE font, legend, axis, grayscale contrast, and visual clarity | M3 | ORIGINAL_REQUEST R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Checkpoint Resume & Model Training | Modify `run_parallel_evaluation.py` for resume support, train all 14 models to ep 100, verify weights & logs | none | IN_PROGRESS |
| 2 | Performance Evaluation (Density & Speed) | Run density and speed evaluation sweeps, extract complete `eval_density_results.csv` and `eval_speed_results.csv` | M1 | PLANNED |
| 3 | IEEE Visualization & Review | Develop `generate_ieee_plots.py`, generate 10 IEEE comparison plots, Critic review & gate pass | M2 | PLANNED |

## Interface Contracts
### `run_parallel_evaluation.py`
- Inputs: `--mode train` / `--mode eval` (or combined workflow)
- Intermediate Checkpoints: `data/models/{model_name}_weights.pth` / `.pkl`, `data/models/{model_name}_convergence.csv`
- Evaluation Outputs: `data/evaluation/eval_density_results.csv`, `data/evaluation/eval_speed_results.csv`

### `generate_ieee_plots.py`
- Inputs: `data/models/*_convergence.csv`, `data/evaluation/eval_density_results.csv`, `data/evaluation/eval_speed_results.csv`
- Outputs: `visualizer/plots/*.png`, `visualizer/plots/*.pdf`

## Code Layout
- `code/run_parallel_evaluation.py`: Training and evaluation orchestrator script
- `code/sim_engine.py`: V2X simulation engine & metric logging
- `code/ai_dcc_hook.py`: Agent hook interface
- `code/models/`: DRL model implementations
- `data/models/`: Weight files (.pth, .pkl) and training convergence logs (*_convergence.csv)
- `data/evaluation/`: Evaluation result CSVs
- `visualizer/`: Visualization utilities and plot generator
