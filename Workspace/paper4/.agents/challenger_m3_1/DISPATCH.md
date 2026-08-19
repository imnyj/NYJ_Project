# Dispatch Instructions — Challenger 1 (Empirical Data & Resolution Challenger)

## Identity
- Role: Empirical Data & DPI Challenger (`challenger_m3_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/challenger_m3_1/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`

## Challenge Objectives
1. Perform empirical verification of 350 DPI resolution on all 9 PNG files in `visualizer/` using PIL and independent image inspection scripts.
2. Empirically verify that data points plotted in `3_reward_convergence.png` and `1_ablation_study.png` exactly match `data/models/*_convergence.csv` and `data/ablation_study.csv` spanning 0 to 200,000 steps.
3. Test edge cases: verify that no files are empty, no NaN values exist, and that all 17 algorithms have valid numeric trajectories.

## Output Requirements
Write `challenge_report.md` and `handoff.md` with a clear verdict: `APPROVE` or `REJECT`.
Notify parent via `send_message`.
