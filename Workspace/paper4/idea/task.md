# Task Checklist: V2X Performance Evaluation Update

- [x] **1. Model Training & Convergence Logs**
  - [x] Update `tinymlp_train.py` with Optuna best parameters (`hidden_dim=32`, `lr=0.0002`).
  - [x] Implement epoch-level logging (Train/Val Loss & Accuracy) to `train_log.csv`.
  - [x] Run `tinymlp_train.py` to generate the final model and convergence log.

- [x] **2. Simulator Engine Overhaul (`sim_engine.py`)**
  - [x] Add distance bucket tracking for PDR (0-50m, 50-100m, ... 250-300m).
  - [x] Expose `cbr_history` array per simulation run.
  - [x] Return detailed dictionaries in `sim_engine.py`'s `run()` method.

- [x] **3. Runner Overhaul (`sensitivity_runner.py`)**
  - [x] Expand `SA1` (Density sweep) to evaluate all 7 methods.
  - [x] Enhance data saving logic to export `distance_pdr.json` and `cbr_history.json`.

- [x] **4. Execute Global Simulation**
  - [x] Run `python3 sensitivity_runner.py --sweep all`.

- [x] **5. Generate IEEE-Style Plots**
  - [x] Create `plot_convergence.py` (Epoch vs Loss/Acc).
  - [x] Create `plot_line_density.py` (AoI/CBR vs Vehicle Density).
  - [x] Create `plot_pdr_distance.py` (PDR vs Distance).
  - [x] Create `plot_cbr_cdf.py` (CBR Cumulative Distribution Function).
  - [x] Extract Model Complexity Table metrics.

- [x] **6. Wrap up**
  - [x] Create `walkthrough.md` with final graphs and insights.
