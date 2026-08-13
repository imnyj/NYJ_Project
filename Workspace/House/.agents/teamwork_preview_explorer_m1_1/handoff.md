# Handoff Report: Milestone 1 Explorer 1 (Financial Data Engine & Analysis)

**Agent Name**: teamwork_preview_explorer_m1_1  
**Target Path**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1/handoff.md`  
**Date**: 2026-08-12  

---

## 1. Observation

- **Obs 1**: `/home/imnyj/Workspace/House/PROJECT.md` (lines 74-80) defines the Data Contract schema for `etc/data/financial_params.json` including `scenarios` `[350000000, 375000000, 400000000]`, `cash_reserve` `230000000`, `monthly_income` `3300000`, `bonuses`, and `expenses` (`2,319,708` KRW).
- **Obs 2**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_1/survey_budget.md` (lines 41-63, 101-108) breaks down the 13 expense categories totaling `2,390,708` KRW. It confirms that the 3rd rank item "월세 (311,000원)" (rent 300k + electricity 11k) is removed upon purchase and replaced by new fixed costs: apartment maintenance fee (~200,000 KRW), parking fee (10,000 KRW), and TV/Internet (30,000 KRW), totaling `240,000` KRW. The net monthly fixed expense becomes `2,390,708 - 311,000 + 240,000 = 2,319,708` KRW.
- **Obs 3**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md` (lines 31-41, 46-52, 68-80, 93-104) details the exact legal tax rates and fees for R1:
  - Base Acquisition Tax: 1.0%, Local Education Tax: 0.1% (10% of net acquisition tax). First-time buyer exemption: 2,000,000 KRW deducted from base tax. Total tax: 3.5억 scenario = 1.65M KRW, 3.75억 scenario = 1.925M KRW, 4.0억 scenario = 2.2M KRW.
  - Statutory Brokerage Fee Cap: 0.4% base + 10% VAT = 0.44% total. 3.5억 = 1.54M KRW, 3.75억 = 1.65M KRW, 4.0억 = 1.76M KRW.
  - Legal fees: 500k KRW for 3.5억, 520k KRW for 3.75억, 550k KRW for 4.0억.
  - Stamp duty: 150k KRW fixed.
  - National Housing Bond: Public appraisal price (~70%). Bond rate: 2.1% (<2.6억 public price for 3.5억 scenario), 2.3% (>=2.6억 public price for 3.75억 & 4.0억 scenarios). Discount rate: 10%. Bond discount cost: 3.5억 = 514,500 KRW (~51.5만), 3.75억 = 603,750 KRW (~60.4만), 4.0억 = 644,000 KRW (~64.4만).
  - Moving fee: 1.5M KRW fixed; Basic repair & deep cleaning fee: 2.0M KRW fixed.
  - Total R1 costs: 3.5억 = 7,854,500 KRW (~7.855M KRW), 3.75억 = 8,348,750 KRW (~8.349M KRW), 4.0억 = 8,804,000 KRW (~8.804M KRW).

---

## 2. Logic Chain

1. **Parameter Integration (Obs 1, Obs 2)**:
   - Combining the 13 categories from `survey_budget.md` with the contractual requirements in `PROJECT.md`, the monthly fixed living expense baseline is derived as `2,390,708 - 311,000 + 240,000 = 2,319,708` KRW.
   - Bonus structure is mapped to 4 payments per year: Jan (1M), Feb (5M), Jul (1M), Aug (5M), yielding 12M KRW annually.
   - Initial cash reserve is set to 230M KRW (30M personal + 200M parental matching support).

2. **R1 Cost Formulation (Obs 3)**:
   - **Acquisition Tax**: For a price $P$, base tax raw is $P \times 1\%$. Exemption of 2M KRW reduces base tax to $\max(0, P \times 1\% - 2M)$. Local education tax is 10% of net base tax. Total tax is $\text{net\_tax} \times 1.1$.
     - 3.5억: $(3.5M - 2M) \times 1.1 = 1.65M$ KRW.
     - 3.75억: $(3.75M - 2M) \times 1.1 = 1.925M$ KRW.
     - 4.0억: $(4.0M - 2M) \times 1.1 = 2.20M$ KRW.
   - **Brokerage Fee**: $P \times 0.44\%$. (1.54M / 1.65M / 1.76M KRW).
   - **Legal Fee**: Lookup mapping (500k / 520k / 550k KRW).
   - **Stamp Duty**: Fixed 150k KRW.
   - **National Housing Bond Discount**: Public price $P_{\text{pub}} = P \times 70\%$. If $P_{\text{pub}} < 2.6\text{억}$, rate = $2.1\%$; else $2.3\%$. Discount cost = $P_{\text{pub}} \times \text{rate} \times 10\%$. (514.5k / 603.75k / 644k KRW).
   - **Moving & Repair Fees**: Fixed 1.5M KRW + 2.0M KRW = 3.5M KRW.
   - **Summation**: Exact R1 costs evaluate to 7,854,500 KRW (3.5억), 8,348,750 KRW (3.75억), and 8,804,000 KRW (4.0억).

3. **Engine Implementation Design (Obs 1, Obs 3)**:
   - Function signatures for `calc_engine.py` are designed: `load_financial_params()`, `calculate_r1_costs(price)`, `calculate_r2_loans(price, cash_reserve)`, and `run_all_scenarios()`.
   - Integer truncation (`int()`) and float rounding rules are established to eliminate floating-point discrepancies across subagent calculations.

---

## 3. Caveats

- **Tax Law Edge Cases**: First-time homebuyer tax exemption assumes full compliance with 3-month occupancy requirement and 3-year resale restriction.
- **Bond Market Discount Fluctuation**: The bond discount rate is modeled at a standard fixed 10%. Real-world bond market discount rates fluctuate daily between 8% and 12%.
- **Brokerage Fee Negotiation**: Statutory cap rate (0.4%) + VAT (10%) is assumed. Actual brokerage fees might be negotiated lower in practice, but capping at 0.44% provides a safe upper bound.

---

## 4. Conclusion

1. The JSON parameter schema for `etc/data/financial_params.json` has been fully designed and validated against all project documents.
2. Exact mathematical formulas for R1 costs across 3.5억, 3.75억, and 4.0억 purchase scenarios were derived, matching the project baseline totals of 7.855M, 8.349M, and 8.804M KRW.
3. Complete implementation guidelines and code snippets for `calc_engine.py` were written and saved to `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1/explorer_m1_1.md`.

---

## 5. Verification Method

- **Files to Inspect**:
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1/explorer_m1_1.md`
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1/handoff.md`
- **Manual Calculation Check**:
  - 3.5억 scenario: $1.65M (\text{tax}) + 1.54M (\text{brokerage}) + 0.50M (\text{legal}) + 0.15M (\text{stamp}) + 0.5145M (\text{bond}) + 1.50M (\text{moving}) + 2.00M (\text{repair}) = 7.8545M$ KRW ($7,854,500$ KRW).
