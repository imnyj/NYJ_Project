# E2E Test Infra: Paper4 V2X DCC Simulation & Publication Pipeline

## Test Philosophy
- Opaque-box, requirement-driven verification derived from `ORIGINAL_REQUEST.md`.
- Strict integrity enforcement: Zero-tolerance for mock/fake data, hardcoded tables, or synthetic formulas.
- Methodology: Category-Partition + Boundary Value Analysis + Real-World Workload Testing.

## Acceptance Criteria Checklist
1. **R1 Audit**:
   - SUMO mobility dynamically reflects vehicle positions.
   - PDR decays mathematically with distance (Path Loss + Nakagami-m) and density (CBR collision factor).
   - `distance_aoi` is aggregated into 6 distance bins (0~300m in 50m intervals) from real packet timestamps.
   - `ResNetMoEAgent.get_latent_and_gate` returns genuine 128D latent vectors and 3D softmax gate weights.
2. **R2 Data Purge & Optuna Optimization**:
   - `data/models/*.pth` and `*.pkl` are purged and cleanly regenerated.
   - Optuna scripts use `action_dim=24` and optimize 13 RL models across 4 GPUs without synthetic tables.
3. **R3 Full Retraining**:
   - 17 models trained for 100 episodes (2000 steps each) with negative penalty reward structures (no manual offsets).
   - Real `.pth`/`.pkl` checkpoint files exist in `data/models/`.
4. **R4 17,000-Episode Evaluation Sweep**:
   - `run_density_sweep_parallel.py` completes 17,000 episodes (17 models x 10 densities x 100 episodes) using 16 workers on 4 GPUs.
   - `eval_density_results.csv` contains exactly 17,000 rows.
   - 5 JSON trace files (`distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, `moe_routing.json`) extracted from genuine runs.
5. **R5 Visualizations & Mock-Free Validation**:
   - `grep -rn 'np.random' visualizer/prepare_data.py` returns 0 results.
   - 11 target datasets created in `data/`.
   - 22 output files (11 PNGs at 350 DPI + 11 PDFs/TeX) generated in `visualizer/`.
   - PNG images verified to have 350 DPI metadata.
