# Handoff Report - teamwork_preview_spec_miner_m3_3

## 1. Observation
- **Input Files Examined**:
  - `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`: Specified property target (청주 방서동 자이 <30평), preset prices (3.5억, 3.75억, 4.0억), cash reserve default 2.3억 원, Didimdol interest rates (3.0%~3.3%), commercial rates (3.8%~4.5%), term (10~30 years), annual bonus prepayment plan (연 1,000만 원: 1월/7월 400만 원, 2월/8월 100만 원), Chart.js dual-axis graph with Glassmorphism UI styling, and output path `/home/imnyj/Workspace/House/ui/index4.html`.
  - `/home/imnyj/Workspace/House/PROJECT.md` & `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m3/SCOPE.md`: Milestone 3 scope and interface contracts. KPI cards required: Initial Cash Needed, Monthly Expenditure, Monthly Remaining Income, Loan Payoff Timeline.
  - `/home/imnyj/Workspace/House/ui/index3.html` (lines 465–612): Chart.js initialization logic using `mainChart.destroy()` before creating new `new Chart()`, dual Y-axes `yLeft` and `yRight` with `grid: { drawOnChartArea: false }`.
  - `/home/imnyj/Workspace/House/etc/data/financial_params.json` & `/home/imnyj/Workspace/House/etc/tests/helpers/reference_engine.py`: Baseline math rules for R1 costs (tax exemption 200M KRW, brokerage 0.44% VAT included, legal fee 500k~550k, stamp duty 150k, bond discount) and monthly CPM loan formulas.

## 2. Logic Chain
1. **Control Component Logic**:
   - The user interface requires both coarse selection (3.5억, 3.75억, 4.0억 preset buttons) and granular selection (3.0억~5.0억 range slider with step 5,000,000 KRW).
   - Cash reserve defaults to 2.3억 KRW with description break-down (3,000만 self + 1억 parents self + 1억 parents spouse).
   - Bonus prepayment toggle allows switching between default 1,000만 KRW/year (Jan/Jul 400만 KRW + Feb/Aug 100만 KRW) and 0 KRW.
2. **Chart.js Dual-axis Logic**:
   - To show monthly cash outflow components without visual clutter, `yLeft` scale uses Stacked Bar (`stacked: true`) for Interest (Red), Regular Principal (Blue), and Bonus Prepayment (Green).
   - To track remaining debt, `yRight` uses Line chart (`type: 'line'`, Orange) with `grid: { drawOnChartArea: false }` to avoid overlapping grid lines across axes.
3. **Memory & Lifecycle Safety**:
   - Creating a new `Chart` instance on an already initialized canvas throws `Canvas is already in use` error in Chart.js.
   - The spec mandates checking `if (chartInstance !== null) chartInstance.destroy();` before instantiation or calling `chartInstance.update('none')` for array updates.

## 3. Caveats
- No caveats. All specs are grounded in `ORIGINAL_REQUEST.md`, `PROJECT.md`, `SCOPE.md`, `index3.html`, and `financial_params.json`.

## 4. Conclusion
- Comprehensive specification document for Chart.js Dual-axis graph and Interactive Controls for `index4.html` has been authored and published at `/home/imnyj/Workspace/House/.agents/teamwork_preview_spec_miner_m3_3/chart_controls_spec.md`.

## 5. Verification Method
- **File Inspection**: Verify `/home/imnyj/Workspace/House/.agents/teamwork_preview_spec_miner_m3_3/chart_controls_spec.md` exists and contains:
  - Preset buttons (3.5억, 3.75억, 4.0억) & range slider specs.
  - Cash slider (2.3억 default), Didimdol rate (3.0~3.3%), Commercial rate (3.8~4.5%), Term (10~30y).
  - Bonus prepayment toggle and monthly inputs structure (1월/7월 400만, 2월/8월 100만).
  - Chart.js `yLeft` (stacked bar) & `yRight` (`drawOnChartArea: false`) options & lifecycle destroy/update code.
  - Edge cases matrix (E1~E7).
- **Execution Test Command**:
  - Run python test runner to ensure financial calculation assumptions hold:
    `python3 /home/imnyj/Workspace/House/etc/scripts/calc_engine.py --verify`
