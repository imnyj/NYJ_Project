# Scope: Milestone 1 (Financial Data Engine & Analysis)

## Architecture
Financial Data Engine: `etc/data/financial_params.json` 및 `etc/scripts/calc_engine.py`
Milestone 1 focuses on:
1. `etc/data/financial_params.json` parameter schema definition.
2. `etc/scripts/calc_engine.py` exact calculation implementation for R1 (one-time purchase costs) and R2 (mortgage comparison and secondary loan fees).
3. Verification scripts in `etc/scripts/verify_m1.py` or `etc/tests/test_calc_engine.py` to ensure zero calculation errors and full test compliance.

## Feature Inventory (Milestone 1 Scope)
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1. 일회성 비용 전수조사 | 3개 가격 시나리오별 취득세(감면 포함), 법무사비, 중개수수료, 인지세, 채권할인액, 이사비, 수리청소비 산출 근거 및 파이썬 로직 | M1 | ORIGINAL_REQUEST §R1 |
| 2 | R2. 대출 시나리오 비교 | 디딤돌/보금자리론 vs 시중은행 금리, 한도, 소득요건 및 근저당설정비, 인지세, 보증료 비교 계산 | M1 | ORIGINAL_REQUEST §R2 |

## Interface Contracts
### Data Contract: `etc/data/financial_params.json`
- `scenarios`: `[350000000, 375000000, 400000000]`
- `cash_reserve`: `230000000`
- `monthly_income`: `3300000`
- `bonuses`: `[ {month: 1, amount: 1000000}, {month: 2, amount: 5000000}, {month: 7, amount: 1000000}, {month: 8, amount: 5000000} ]`
- `expenses`: base living expense without rent (2,079,708) + apartment fixed (240,000) = 2,319,708
- `r1_params`: tax rates, exemptions, statutory broker fees, bond discount, legal fees, moving fees, repair fees.
- `r2_params`: didimdol vs commercial mortgage specs, stamp tax split, guarantee fee rates.

### Python Engine Contract: `etc/scripts/calc_engine.py`
Functions:
- `calculate_r1_costs(price)` -> dict of itemized costs and total
- `calculate_r2_loans(price, cash_reserve)` -> dict of loan scenarios, required loan, rates, secondary loan fees
- `run_all_scenarios()` -> aggregated calculations output matching project spec
