# G4 Plots Visualization Plan and Specification (v3)

This document defines the visual design specification and implementation checklist for the three G4 graphs in the CCVN caching paper. It has been updated to reflect precise layout constraints, Y-axis labeling, X-axis bounds/margins, and initial pre-trained value alignment.

1. **G4-1**: `G4-1_cumulative_mae_validation.png` (Cumulative MAE validation over cumulative samples for different queue sizes 1000 to 10000).
2. **G4-2**: `G4-2_queue_size_analysis.png` (Dual-axis trade-off plot showing Queue Size vs. MAE standard deviation (SEM) and Update Delay).
3. **G4-3**: `G4-3_baseline_comparison.png` (Cumulative fine-tuning comparison of all 13 models at the optimal queue size Q=4000).

---

## 📋 General Visualization Rules (from GEMINI.md)
* **RULE 10**: Absolutely NO title inside the image (do not use `plt.title` or `ax.set_title` or `fig.suptitle`). All descriptions must be handled in the LaTeX caption.
* **Font Sizes**: 
  - Axis labels: **20pt**
  - Tick labels: **18pt**
  - Legend font size: **18pt**
* **Colors for H-ST-MBAN**: Must be solid red (`#FF0000`).
* **DPI**: Save all images at **300 DPI** using `bbox_inches='tight'`.
* **Output Directories**: Save the generated graphs to:
  1. `/home/imnyj/Workspace/paper1/visualizer/`
  2. `/home/imnyj/Workspace/paper1/writer/draft/figure/`
  3. `/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/` (Main agent's brain directory)

---

## 🎨 Graph 1: G4-1 (Cumulative MAE Validation)
* **Filename**: `G4-1_cumulative_mae_validation.png`
* **Plot Type**: Multi-line plot with shaded Standard Error of the Mean (SEM) bands.

### 1. Data Specification
* **Source**: `/home/imnyj/Workspace/paper1/worker/G4_cumulative_mae_validation.csv`
* **Expected Columns**: 
  - `Queue_Size` (categorical: 1000, 2000, ..., 10000)
  - `Cumulative_Samples` (X-axis, integer 0 to 60000)
  - `Validation_MAE` (Y-axis, float, validation error in seconds)
  - `MAE_Std` (representing the standard error of the mean (SEM) of the validation error at that step)
* **Initial State Constraint**:
  - All 10 curves **must start** at `Cumulative_Samples = 0` showing the exact same initial validation MAE value of approximately **34.77s** (`34.765628814697266` in the data, where `Round = -1`). This aligns the models to their pre-trained baseline state prior to receiving any fine-tuning samples.

### 2. Visual Design Specs
* **Canvas Size**: `figsize=(12, 8)`
* **X-Axis**: 
  - Label: `Cumulative Traffic Data Samples` (fontsize=20)
  - Limit: **Strictly `[0, 60000]`** with no margins on the left or right side (the lines must touch the borders of the plot).
  - Implementation: Use `ax.set_xlim(0, 60000)` and remove default margins using `ax.margins(x=0)`.
  - Ticks: Font size 18pt
* **Y-Axis**: 
  - Label: **Exactly `Validation MAE (s)`** (fontsize=20)
  - Ticks: Font size 18pt
* **Lines & Shaded Bands**:
  - **10 lines** corresponding to queue sizes: 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000.
  - **Color Palette**: Use a premium sequential color palette (e.g., `viridis` or `plasma`). E.g., `colors = plt.cm.plasma(np.linspace(0.1, 0.9, 10))`.
  - **Shaded Band**: Soft shaded area representing the SEM around each line using `ax.fill_between(x, mae - sem, mae + sem, alpha=0.1, color=line_color)`.
* **Legend**:
  - Placed at the **upper-right** inside the graph.
  - Display queue sizes in **ascending order** (1000 to 10000).
  - Font size: **18pt**
* **Grid**: Light grey grid (`color='grey', linestyle='--', alpha=0.5`).

---

## 🎨 Graph 2: G4-2 (Queue Size Analysis)
* **Filename**: `G4-2_queue_size_analysis.png`
* **Plot Type**: Dual-axis line plot with markers.

### 1. Data Specification
* **Source**: `/home/imnyj/Workspace/paper1/worker/G4_queue_size_analysis.csv`
* **Expected Columns**:
  - `Queue_Size` (X-axis, integer 1000 to 10000)
  - `MAE_Std_Dev` (Left Y-axis, representing the standard deviation of validation MAE)
  - `Update_Delay_Minutes` (Right Y-axis, representing the update delay in minutes)

### 2. Visual Design Specs
* **Canvas Size**: `figsize=(10, 6)`
* **X-Axis**:
  - Label: `Queue Size` (fontsize=20)
  - Limit & Ticks: Ticks at every 1000 (from 1000 to 10000).
  - Ticks: Font size 18pt
* **Left Y-Axis (Y1 - MAE Std. Dev.)**:
  - Label: **Exactly `Validation MAE Std. Dev. (s)`** (fontsize=20, color='#1F4E79')
  - Data: Plots the standard deviation of MAE (`MAE_Std_Dev` column, which drops from ~1.01 to ~0.33).
  - Line: Blue line with circle markers `o`, linewidth=2, markersize=8, color='#1F4E79'.
  - Ticks: Font size 18pt, matching the left axis color `#1F4E79`.
* **Right Y-Axis (Y2 - Update Delay)**:
  - Label: **Exactly `Update Delay (min)`** (fontsize=20, color='#C00000')
  - Data: Plots the update delay in minutes (`Update_Delay_Minutes` column, which rises from 8.0 to 83.33).
  - Line: Red line with square markers `s`, linewidth=2, markersize=8, color='#C00000'.
  - Ticks: Font size 18pt, matching the right axis color `#C00000`.
* **Legend**:
  - **Unified Legend**: Combine both lines (Left Y1 and Right Y2) into a single legend.
  - Position: **Top-center** (e.g., `loc='lower center'`, `bbox_to_anchor=(0.5, 1.15)`, `ncol=2`).
  - Font size: **18pt**
* **Grid**: Light grey grid only for the primary X/Y axis to avoid visual clutter from overlapping dual-axis grids.

---

## 🎨 Graph 3: G4-3 (Baseline Comparison)
* **Filename**: `G4-3_baseline_comparison.png`
* **Plot Type**: Multi-line comparison plot of baselines.

### 1. Data Specification
* **Source**: `/home/imnyj/Workspace/paper1/worker/G5_all_mae_by_round.csv` (contains data from fine-tuning at Q=4000).
* **Pre-trained MAE Source**: Final validation MAEs from G1 pre-training learning curves.
* **Pre-trained Values Table (at X=0)**:
  To construct a starting point at `Cumulative_Samples = 0` (before fine-tuning), the coder must prepend a point `(0, Pretrained_MAE)` for each model using the following exact values:

  | Model | G1 Pre-trained MAE (s) |
  | :--- | :---: |
  | **H-ST-MBAN** | **36.56** (or **34.77** to match G4-1 initial state) |
  | **MLP** | **47.13** |
  | **ResNet** | **43.97** |
  | **LSTM** | **57.11** |
  | **GRU** | **70.56** |
  | **FTT** | **42.83** |
  | **TabR** | **39.98** |
  | **LR** | **87.39** |
  | **RF** | **47.52** |
  | **XGBoost** | **44.46** |
  | **CatBoost** | **59.90** |
  | **NGBoost** | **69.90** |
  | **TabPFN** | **65.57** |

* **Data Integration**:
  Prepend these $X=0$ values to the data loaded from `G5_all_mae_by_round.csv` (which starts at $X=4000$) for each model.

### 2. Visual Design Specs
* **Canvas Size**: `figsize=(12, 8)`
* **X-Axis**:
  - Label: `Cumulative Traffic Data Samples` (fontsize=20).
  - Limit: **Strictly `[0, 60000]`** with no margins on the left or right side (the lines must touch the borders of the plot).
  - Implementation: Use `ax.set_xlim(0, 60000)` and remove default margins using `ax.margins(x=0)`.
  - Ticks: Font size 18pt
* **Y-Axis**:
  - Label: **Exactly `Validation MAE (s)`** (fontsize=20).
  - Ticks: Font size 18pt
* **Lines**:
  - **13 lines** representing each model's validation MAE over cumulative samples.
  - **Proposed Model (H-ST-MBAN)**:
    - Color: Solid Red `#FF0000`.
    - Line: Highlighted with **`linewidth=3`** to stand out clearly from the baselines.
  - **12 Baselines**:
    - Color: Thin lines in distinct categorical colors (e.g. using a palette like `tab20` or specific line colors to avoid overlap clutter).
    - Line: Thin linewidth (e.g., **`linewidth=1.0`** or **`1.5`**).
* **Legend**:
  - Positioned at the most appropriate clear position (e.g., upper-right or lower-left depending on curve distribution).
  - Font size: **18pt**
* **Grid**: Light grey grid (`color='grey', linestyle='--', alpha=0.5`).

---

## 🛠️ Implementation Checklist for Coder

1. [ ] **Verify / Preprocess Data**:
   - For **G4-1**: Load `G4_cumulative_mae_validation.csv`. Filter out dwell times > 300s if raw data contains them. Verify that all 10 lines start at `Cumulative_Samples = 0` with the initial validation MAE of ~34.77s.
   - For **G4-3**: Load `G5_all_mae_by_round.csv`. For each model, prepend a row at `Cumulative_Samples = 0` using the corresponding pre-trained model MAE from the pre-trained values table.
2. [ ] **Implement G4-1 (Cumulative MAE validation curves)**:
   - Plot the 10 lines from queue size 1000 to 10000.
   - Use a sequential color palette (`plasma` or `viridis`).
   - Draw shaded error bands (SEM) around each line using `ax.fill_between(x, mae - sem, mae + sem, alpha=0.1)`.
   - Set X-axis limit to `[0, 60000]` strictly, and set `ax.margins(x=0)` so lines touch the y-axis and the right border.
   - Set Y-axis label to exactly `Validation MAE (s)`.
   - Set font sizes: Axis labels 20pt, ticks 18pt, legend 18pt.
   - Verify that there is **NO title** inside the image.
3. [ ] **Implement G4-2 (Queue Size Analysis)**:
   - Use dual Y-axes with `ax1.twinx()`.
   - Set left Y-axis label to exactly `Validation MAE Std. Dev. (s)` (fontsize=20, color `#1F4E79`). Plot `MAE_Std_Dev` column in blue with circle markers.
   - Set right Y-axis label to exactly `Update Delay (min)` (fontsize=20, color `#C00000`). Plot `Update_Delay_Minutes` column in red with square markers.
   - Combine both plots' handles/labels to create a single unified legend. Position it top-center (`loc='lower center'`, `bbox_to_anchor=(0.5, 1.15)`).
   - Set font sizes: Axis labels 20pt, ticks 18pt, legend 18pt.
   - Verify that there is **NO title** inside the image.
4. [ ] **Implement G4-3 (Baseline Comparison)**:
   - Plot 13 lines representing all models.
   - Highlight **H-ST-MBAN** in red `#FF0000` with **`linewidth=3`**.
   - Make all 12 baselines thin with **`linewidth=1.0`** or **`1.5`** using distinct categorical colors.
   - Set X-axis limit to `[0, 60000]` strictly, and set `ax.margins(x=0)` so lines touch the borders.
   - Set Y-axis label to exactly `Validation MAE (s)`.
   - Set font sizes: Axis labels 20pt, ticks 18pt, legend 18pt.
   - Verify that there is **NO title** inside the image.
5. [ ] **Apply Concurrency & Audit Logging**:
   - Use `LockManager` to acquire write locks before saving files.
   - Save all plots to:
     - `/home/imnyj/Workspace/paper1/visualizer/`
     - `/home/imnyj/Workspace/paper1/writer/draft/figure/`
     - `/home/imnyj/.gemini/antigravity-cli/brain/bd55b32a-994c-49a9-a934-ac0a05baf976/`
   - Use 300 DPI and `bbox_inches='tight'`.
   - Log all modifications using `AuditLogger` under the agent ID `worker_g4`.
