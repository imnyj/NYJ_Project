# Handoff Report: teamwork_preview_explorer_m2_2 (R3 Financial Simulation Analysis)

## 1. Observation
- Direct examination of `/home/imnyj/Workspace/House/etc/data/financial_params.json` confirmed baseline cashflow parameters:
  - Monthly income: `3,300,000` KRW (Husband).
  - Living expense baseline: `2,390,708` KRW (13 categories total).
  - Removed rent & electricity: `-311,000` KRW.
  - Net living expense: `2,079,708` KRW.
  - Apartment fixed expenses: `240,000` KRW (Maintenance `200,000` + Parking `10,000` + TV/Internet `30,000`).
  - Total monthly fixed expense: `2,319,708` KRW.
  - Monthly surplus before mortgage payment: `3,300,000 - 2,319,708 = 980,292` KRW.
- Direct examination of bonus prepayment schedule in `financial_params.json` (lines 40-67):
  - Month 1 (Jan): `4,000,000` KRW prepayment (`1,000,000` reserved).
  - Month 2 (Feb): `1,000,000` KRW prepayment.
  - Month 7 (Jul): `4,000,000` KRW prepayment (`1,000,000` reserved).
  - Month 8 (Aug): `1,000,000` KRW prepayment.
  - Annual bonus prepayment total: `10,000,000` KRW/year.
- Execution of `/home/imnyj/Workspace/House/etc/scripts/calc_engine.py --verify` returned:
  - `"=== All Self-Verification Checks PASSED (100%) ==="`
- Execution of `/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/House/etc/tests/` returned:
  - `"87 passed in 0.13s"`
- Execution of `/home/imnyj/venv/bin/python /home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/generate_simulation.py` generated exact simulation schedules saved to `simulation_results.json` and compiled into `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/analysis_r3.md`.

## 2. Logic Chain
1. **Observation 1 & 2**: Net monthly fixed expense is verified at 2,319,708 KRW, leaving 980,292 KRW monthly surplus before loan payment. Dedicated annual bonus prepayment is set at 10,000,000 KRW (Jan/Jul 4M + Feb/Aug 1M).
2. **Observation 3 & 4**: Existing calculation engine `calc_engine.py` and test suite `etc/tests/` (87 tests) pass 100% without errors, confirming the mathematical correctness of R1/R2 parameter logic.
3. **Simulation Execution**: Using the authoritative CPM (Constant Payment Mortgage) formula with interest calculated monthly on remaining principal balance and bonus prepayments applied at months 1, 2, 7, and 8:
   - Scenario 1 (3.5억 price, 1.2억 loan @ Didimdol 3.15%): Monthly payment = 515,684 KRW. Net monthly surplus after PMT = +464,608 KRW. Payoff timeframe = 100 months (8.33 years). Total interest = 16,256,886 KRW. Final cash balance = 63,772,314 KRW.
   - Scenario 2 (3.75억 price, 1.45억 loan @ Didimdol 3.15%): Monthly payment = 623,118 KRW. Net monthly surplus after PMT = +357,174 KRW. Payoff timeframe = 115 months (9.58 years). Total interest = 22,617,720 KRW. Final cash balance = 61,075,010 KRW.
   - Scenario 3 (4.0억 price, 1.7억 loan @ Didimdol 3.15%): Monthly payment = 730,553 KRW. Net monthly surplus after PMT = +249,739 KRW. Payoff timeframe = 127 months (10.58 years). Total interest = 29,657,629 KRW. Final cash balance = 53,716,853 KRW.

## 3. Caveats
- The primary baseline assumes Didimdol loan interest rate at 3.15%. Sensitivity calculations for Didimdol minimum (3.00%) and commercial bank rate (4.25%) are included in the report.
- One-time initial transaction fees (R1 costs, ~7.85M ~ 8.80M KRW) are assumed to be paid upfront at purchase, so cash balance tracking begins after purchase settlement with positive monthly net surplus accumulation and bonus reserve additions (+2M KRW/yr).

## 4. Conclusion
- R3 monthly cashflow and annual payoff timeline simulation has been completely executed and verified.
- The 10,000,000 KRW/year bonus prepayment strategy reduces loan duration from 30 years to ~8.3 - 10.6 years across all 3 property price scenarios while maintaining positive cash flow (+250k ~ +465k KRW/month) and building cash reserves (+53.7M ~ +63.8M KRW at payoff).
- The detailed report and data tables are published at `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/analysis_r3.md`.

## 5. Verification Method
- **Pytest command**: `/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/House/etc/tests/`
- **Calculation engine verification**: `/home/imnyj/venv/bin/python /home/imnyj/Workspace/House/etc/scripts/calc_engine.py --verify`
- **Simulation reproduction command**: `/home/imnyj/venv/bin/python /home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/generate_simulation.py`
- **File to inspect**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/analysis_r3.md`
- **Invalidation condition**: Any change in monthly net living expenses (2,319,708 KRW), bonus prepayment inputs (10M KRW/yr), or interest rate parameters.
