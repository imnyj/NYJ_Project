# Original User Request

## 2026-08-24T01:20:11Z

# Teamwork Project Prompt

> Status: Launched
> Goal: Complete the entire simulation fix, Optuna optimization, retraining, and 17,000-episode evaluation pipeline.
> Requested team: Full team (Massive evaluation and parallel processing)

This project requires completely wiping out the previous fake/hardcoded evaluation results, validating the SUMO simulation environment, re-optimizing hyperparameters, and running a massive, fully-authentic 17,000-episode evaluation across 17 models to generate 22 high-resolution paper-ready visualizations.

Working directory: /home/imnyj/Workspace/paper4
Integrity mode: benchmark

## Requirements

### R1. Simulation Environment & Metrics Audit (Pre-requisite)
- Before any training begins, audit the `sim_engine.py`, `aoi_tracker.py`, and `etsi_cam_layer.py`.
- Verify that SUMO mobility is correctly reflected and that communication performance (PDR) mathematically decays with distance and density.
- Modify the engine to correctly export `distance_aoi`, `cbr_history`, and add real TSNE/MoE gating logs to `resnet_moe_agent.py`.

### R2. Purge Fake Data & Re-Optimize (Optuna)
- Delete all `prepare_data.py` fake/mock arrays and analytical formulas.
- Delete all existing `data/models/*.pth` and `*.pkl`.
- Re-run Optuna optimization for the 13 RL models to ensure hyperparameter validity (to fix the non-convergence and spike issues).

### R3. Full Retraining (17 Models)
- Train all 17 models for 100 episodes (2000 steps each).
- Ensure convergence logs correctly reflect the negative penalty reward structure without manual offsets.

### R4. Massive Evaluation Sweep (17,000 Episodes)
- Write and execute a highly parallel `run_density_sweep_parallel.py`.
- Evaluate all 17 models across 10 densities (5, 10, ..., 50) for 100 episodes each.
- Extract 100% real `eval_density_results.csv`, `distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, and `moe_routing.json`.

### R5. Visualization Generation
- Run the cleaned `prepare_data.py` and `generate_visualizations.py`.
- Output 11 target datasets and 22 visual files (PNG/PDF, 350 DPI) completely devoid of mock data.

## Acceptance Criteria

### Verification & Audit
- [ ] R1 Audit Report confirms that distance/density penalties correctly affect PDR and AoI in the SUMO environment.
- [ ] `grep -rn 'np.random' visualizer/prepare_data.py` returns 0 results.

### Training & Evaluation
- [ ] 17 new `.pth`/`.pkl` files exist in `data/models/`.
- [ ] The `eval_density_results.csv` contains data for all 17 models across densities 5, 10, 15, 20, 25, 30, 35, 40, 45, 50.
- [ ] Evaluation sweep completes 17,000 episodes without crashes.

### Final Outputs
- [ ] 22 output files (11 PNGs, 11 PDFs) generated in `visualizer/`.
- [ ] TSNE and MoE Routing plots reflect genuine neural network activation data, not hardcoded arrays.
