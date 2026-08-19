# Dispatch Instructions — Reviewer 1 (Visual & Target Output Verification)

## Identity
- Role: Visual & Target Specification Reviewer (`reviewer_m3_1`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/reviewer_m3_1/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
- `/home/imnyj/Workspace/paper4/.agents/worker_m2_1/handoff.md`

## Review Scope & Objectives
1. Verify all 11 target outputs in `/home/imnyj/Workspace/paper4/visualizer/`:
   - 9 PNG images at 350 DPI (`1_ablation_study.png` ~ `10_aoi_vs_distance.png`).
   - 2 tables in CSV & LaTeX (`2_optuna_sensitivity_table.*`, `11_hardware_feasibility_table.*`).
   - 9 PDF vector graphs.
2. Verify visual requirements:
   - `1_ablation_study.png` and `3_reward_convergence.png` explicitly show 200,000 steps on the x-axis.
   - `Phase I: Convergence & Exploration` and `Phase II: Post-Convergence Steady-State Stability` are clearly marked with shading and labels.
   - 17 models colors, markers, line styles, bold Red `#FF0000` for REMO-DQN on top (`evaluation_plan.md §2`).
3. Run verification commands and inspect the visual outputs.

## Output Requirements
Write `review.md` and `handoff.md` with a clear verdict: `APPROVE` or `REQUEST_CHANGES`.
Notify parent via `send_message`.
