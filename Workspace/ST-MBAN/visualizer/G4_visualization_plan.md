# G4 Plots Visualization Plan and Specification

This document defines the visual design specification and implementation checklist for the two G4 graphs in the CCVN caching paper:
1. **G4-2**: `G4-2_cumulative_mae_validation.png` (Cumulative MAE validation over cumulative samples for different queue sizes 1000 to 10000).
2. **G4-3**: `G4-3_queue_size_analysis.png` (Queue size trade-off analysis).

---

## 📋 General Visualization Rules (from GEMINI.md)
* **RULE 10**: Absolutely NO title inside the image (do not use `plt.title` or `ax.set_title` or `fig.suptitle`). All descriptions must be handled in the LaTeX caption.
* **Font Sizes**: 
  - Axis labels: **20pt**
  - Tick labels: **18pt**
  - Legend font size: **18pt**
* **DPI**: Save all images at **300 DPI** using `bbox_inches='tight'`.
* **Output Directories**: Save the generated graphs to:
  1. `/home/imnyj/Workspace/paper1/visualizer/`
  2. `/home/imnyj/Workspace/paper1/writer/draft/figure/`
  3. `/home/imnyj/papers/paper1/figure/` (if exists)

---

## 🎨 Graph 1: G4-2 (Cumulative MAE Validation)
* **Filename**: `G4-2_cumulative_mae_validation.png`
* **Plot Type**: Multi-line plot with shaded standard deviation bands.

### 1. Data Specification
* **Source**: `/home/imnyj/Workspace/paper1/worker/G4_cumulative_mae_validation.csv` (or generated training logs).
* **Expected Columns**: 
  - `Cumulative_Samples` (X-axis, integer 0 to 15,000)
  - `Queue_Size` (categorical, integer 1000, 2000, ..., 10000)
  - `MAE` (Y-axis, float, validation error in seconds)
  - `MAE_Std_Dev` (float, standard deviation of validation error at that step)

### 2. Visual Design Specs
* **Canvas Size**: `figsize=(12, 8)`
* **X-Axis**: 
  - Label: `Cumulative Traffic Data Samples` (fontsize=20)
  - Range: 0 to 15,000
  - Tick labels: fontsize=18
* **Y-Axis**: 
  - Label: `Validation MAE (s)` (fontsize=20)
  - Tick labels: fontsize=18
* **Lines & Shaded Bands**:
  - **10 lines** corresponding to queue sizes 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000.
  - **Color Palette**: Use a premium sequential color palette (e.g., `plasma` or `viridis` or a custom sequential gradient from cool/light to warm/dark) rather than default tab10/tab20. For example: `colors = plt.cm.plasma(np.linspace(0.1, 0.9, 10))`.
  - **Shaded Band**: A soft shaded area representing the standard deviation around each line using `plt.fill_between(x, mae - std, mae + std, alpha=0.1, color=line_color)`.
* **Legend**:
  - Placed at the **top-right** or **upper-right** inside the graph.
  - Display queue sizes in **ascending order** (1000 to 10000).
  - Font size: **18pt**
* **Grid**: Light grey grid (`color='grey', linestyle='--', alpha=0.5`).

---

## 🎨 Graph 2: G4-3 (Queue Size Trade-off Analysis)
* **Filename**: `G4-3_queue_size_analysis.png`
* **Plot Type**: Dual-axis line plot with markers.

### 1. Data Specification
* **Source**: `/home/imnyj/Workspace/paper1/worker/G4_queue_size_analysis.csv`
* **Expected Columns**:
  - `Queue_Size` (X-axis, integer 1000 to 10000)
  - `Average_Validation_MAE` (or `MAE`) (Left Y-axis, float)
  - `MAE_Std_Dev` (Right Y-axis, float)

### 2. Visual Design Specs
* **Canvas Size**: `figsize=(10, 6)`
* **X-Axis**:
  - Label: `Queue Size` (fontsize=20)
  - Range: 1000 to 10000 (ticks at every 1000)
  - Tick labels: fontsize=18
* **Left Y-Axis (Primary)**:
  - Label: `Average Validation MAE (s)` (fontsize=20, color='#1F4E79')
  - Line: Blue line with marker `o`, linewidth=2, markersize=8.
  - Ticks and labels: fontsize=18, color matching the primary line.
* **Right Y-Axis (Secondary)**:
  - Label: `Average MAE Std Dev (s)` (fontsize=20, color='#C00000')
  - Line: Red line with marker `s` (square), linewidth=2, markersize=8.
  - Ticks and labels: fontsize=18, color matching the secondary line.
* **Legend**:
  - **Unified Legend**: Combine both the Left Y-axis line and Right Y-axis line into a single legend.
  - Position: **Top-center** (e.g., `loc='upper center'`, `bbox_to_anchor=(0.5, 1.15)`, `ncol=2`).
  - Font size: **18pt**
* **Grid**: Light grey grid only for the primary X/Y axis to avoid visual clutter from overlapping dual-axis grids.

---

## 🛠️ Implementation Checklist for Coder
1. [ ] **Verify / Generate Data**:
   - Ensure the raw validation metrics for queue sizes 1000 to 10000 are evaluated and stored in `/home/imnyj/Workspace/paper1/worker/G4_cumulative_mae_validation.csv` and `/home/imnyj/Workspace/paper1/worker/G4_queue_size_analysis.csv`.
2. [ ] **Plot G4-2**:
   - Load G4-2 data, generate X-axis (samples 0 to 15,000) and plot 10 lines sequentially colored using `plt.cm.plasma` or `plt.cm.viridis`.
   - Add the shaded band `plt.fill_between` with `alpha=0.1` around each line.
   - Place legend at upper-right with font size 18.
   - Adjust tick label size to 18 and label size to 20.
3. [ ] **Plot G4-3**:
   - Use `ax1.twinx()` to set up the dual Y-axis.
   - Plot Left Y-axis (Average Validation MAE) using Blue `#1F4E79` with circle markers.
   - Plot Right Y-axis (MAE Std Dev) using Red `#C00000` with square markers.
   - Combine line handles and labels into a single legend using `ax1.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=2, fontsize=18)`.
   - Set tick parameters: Left ticks/labels in blue, Right ticks/labels in red, sizes 18.
4. [ ] **Apply RULE 10**:
   - Verify that NO `plt.title` or `ax.set_title` is used in either plot.
5. [ ] **Save Deliverables**:
   - Save figures as `G4-2_cumulative_mae_validation.png` and `G4-3_queue_size_analysis.png` at 300 DPI to the destination folders.
   - Implement `LockManager` and `AuditLogger` when saving files.