# Dispatch Instructions — Explorer 2 (Visualizer & 11 Targets Survey)

## Identity
- Role: Visualizer & 11 Target Figures Explorer (`explorer_o5_2`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/explorer_o5_2/`

## Objective
Survey `/home/imnyj/Workspace/paper4/visualizer/` scripts, output images, and tables to verify adherence to the latest user requirements (350 DPI PNGs, 200k steps on x-axis with two phases, color/legend order specs, LaTeX tables).

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/visualizer/evaluation_plan.md`
- `/home/imnyj/Workspace/paper4/visualizer/plot_figures.py`
- `/home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py`
- `/home/imnyj/Workspace/paper4/visualizer/prepare_data.py`
- `/home/imnyj/Workspace/paper4/visualizer/generate_tables.py`
- `/home/imnyj/Workspace/paper4/walkthrough.md`

## Specific Investigation Tasks
1. Check all 11 target outputs in `/home/imnyj/Workspace/paper4/visualizer/`:
   - `1_ablation_study.png`
   - `2_optuna_sensitivity_table.csv` & `.tex`
   - `3_reward_convergence.png`
   - `4_tsne_clustering.png`
   - `5_moe_routing.png`
   - `6_cbr_trace.png`
   - `7_pdr_vs_density.png`
   - `8_aoi_vs_density.png`
   - `9_pdr_vs_distance.png`
   - `10_aoi_vs_distance.png`
   - `11_hardware_feasibility_table.csv` & `.tex`
2. Verify:
   - Are `1_ablation_study.png` and `3_reward_convergence.png` plotted with an x-axis showing 200,000 steps/iterations?
   - Do the convergence graphs clearly visualize both (1) Convergence phase and (2) Post-Convergence stability phase?
   - Are all PNGs generated at 350 DPI?
   - Are the 17 models colors, line styles, markers, and legend order strictly matching `evaluation_plan.md §2`?
   - Are the scripts clean and reproducible?

## Output Requirements
Write `analysis.md` and `handoff.md` in your working directory.
Include clear sections: Observation, Logic Chain, Caveats, Conclusion, Verification Method.
Notify parent via `send_message`.
