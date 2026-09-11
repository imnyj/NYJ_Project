# Visualization Refinement Goal Tracker

## Global Rule
- **Consistent Model Order**: Match the G6 model ordering for all legends across all plots. (LR, RF, XGB, CatBoost, NGBoost, TabPFN, MLP, ResNet, LSTM, GRU, FTT, TabR, H-ST-MBAN).

## Task 1: G1 & G2 Fixes
- [ ] **G1 (Learning Curves)**
  - Y-axis: Change "Validation MAE" to "MAE"
  - X-axis: Change "Epochs / Trees" to "Epochs"
- [ ] **G2 (Ablation Study)**
  - Y-axis: Change "Validation MAE" to "MAE"

## Task 2: G3 Split & Rename
- [ ] **G3 (Pred vs True)**
  - Rename axes/labels to use LaTeX math symbols: $\hat{\tau}_\text{cur}$ and $\hat{\tau}_\text{nxt}$
  - Split into two separate image files: `G3-1_pred_vs_true_cur.png` and `G3-2_pred_vs_true_nxt.png`

## Task 3: G4 Refinements
- [ ] **G4 Cumulative** (`G4_cumulative_mae_validation.png`)
  - Move legend from outside to the top-right inside the graph.
- [ ] **G4 Queue Size** (`G4_queue_size_analysis.png`)
  - Combine the two legends into a single legend containing both "MAE Std. Dev." and "Update Delay".
  - Place the unified legend at the top-center inside the graph.

## Task 4: G5 & G6 Refinements
- [ ] **G5 (Online Fine-Tuning)**
  - Remove graph title.
  - Y-axis: Change to "MAE"
  - X-axis: Change to "Round" (from Cumulative Processed Samples)
  - Move legend from outside to the top-right inside the graph.
- [ ] **G6 (Cache Metrics Avg)**
  - Remove graph title.
  - Split into 3 separate graphs: `G6-1_hit_rate.png`, `G6-2_access_delay.png`, `G6-3_traffic_waste.png`.
  - Y-axis labels: "Hit rate (%)", "Average access delay (sec)", "Traffic waste (MB)".

## Task 5: LaTeX Text Updates
- [ ] **G1 Text Update**: Add text stating that machine learning iterations were converted/scaled to align with deep learning epochs for fair comparison.
- [ ] **G4 Text Update**: Add text explaining that "MAE Std. Dev." represents how unstably the MAE fluctuates during updates.
- [ ] **G3 & G6 Structure Update**: Update the `\includegraphics` commands in `main.tex` to reflect the split images (G3-1, G3-2, G6-1, G6-2, G6-3).

## Task 6: G7 
- [ ] **G7 Evaluation**: Ask the user for specific instructions on G7 after Tasks 1-5 are complete.
