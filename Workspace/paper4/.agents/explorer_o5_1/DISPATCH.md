# Dispatch Instructions — Explorer 1 (200k Steps Data & Models Survey)

## Identity
- Role: Data & RL Training Explorer (`explorer_o5_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/explorer_o5_1/`

## Objective
Survey all 200,000-step training data, model checkpoints (`.pth`/`.pkl`), Optuna optimization logs, and ablation datasets in `/home/imnyj/Workspace/paper4/data/`.

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
- `/home/imnyj/Workspace/paper4/walkthrough.md`

## Specific Investigation Tasks
1. Check `/home/imnyj/Workspace/paper4/data/models/` for all 17 models (14 RL + 3 non-RL or all checkpoints):
   - Verify if `.pth` / `.pkl` weight files exist for all models.
   - Verify if `*_convergence.csv` files have 200,000 steps (100 episodes x 2,000 steps = 200,000 steps).
   - Check if the data points are authentic simulation results (reward, AoI, CBR, PDR).
2. Check `/home/imnyj/Workspace/paper4/data/optuna/`:
   - Verify `all_best_params.json` and individual `best_params_*.csv` files.
   - Check if Optuna hyperparameter optimization was executed and logged.
3. Check `/home/imnyj/Workspace/paper4/data/ablation_structure/`, `data/ablation_reward/`, `data/ablation_state/`:
   - Verify train logs, eval metrics, and models.
4. Check `/home/imnyj/Workspace/paper4/data/evaluation/eval_density_results.csv` and `eval_speed_results.csv`:
   - Verify data coverage for all 17 methods across 6 densities (20, 40, 60, 80, 100, 120 veh/km) and 3 seeds.

## Output Requirements
Write `analysis.md` and `handoff.md` in your working directory.
Include clear sections: Observation, Logic Chain, Caveats, Conclusion, Verification Method.
Notify parent via `send_message`.
