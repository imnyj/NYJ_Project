# House Financial Simulation Project — E2E Test Automation Infrastructure Specification (`TEST_INFRA.md`)

## 1. Overview & Architecture
This document defines the End-to-End (E2E) Test Automation Infrastructure for the **Cheongju Bangseo-dong Xi Apartment (<30 Pyeong) Financial Simulation Project**.

The E2E test suite validates all financial calculations, tax rates, brokerage fees, bond discounts, mortgage options, living expense updates, administrative timeline requirements, web UI DOM structures, JavaScript calculation engines, pairwise combinations, and multi-year timeline simulations against official Korean tax/real estate regulations and project requirements.

```
/home/imnyj/Workspace/House/
├── TEST_INFRA.md                          # Project Root E2E Test Infrastructure Specification
├── etc/
│   ├── tests/
│   │   ├── helpers/
│   │   │   ├── reference_engine.py       # Pure Python Financial Calculator & Reference Oracle
│   │   │   ├── report_parser.py          # Markdown Report & Budget Reference Parser
│   │   │   └── html_parser.py            # BeautifulSoup HTML DOM & JS Script Parser
│   │   ├── test_tier1.py                 # Tier 1: Feature Coverage Tests (25+ TCs)
│   │   ├── test_tier2.py                 # Tier 2: Boundary & Corner Cases (25+ TCs)
│   │   ├── test_tier3.py                 # Tier 3: Pairwise Matrix & UI/JS Structure (12+ TCs)
│   │   ├── test_tier4.py                 # Tier 4: Timeline Simulations (5+ Scenarios)
│   │   └── run_e2e_tests.py              # Master E2E Test Runner & JSON Reporter
│   └── logs/
│       └── e2e_results.json              # E2E Test Run Audit Log Output
```

---

## 2. Default Financial & Parameter Specifications

### 2.1 Asset & Income Parameters
- **Cash Reserve (보유 현금)**: 230,000,000 KRW (Self 30M KRW + Self Parents 100M KRW + Spouse Parents 100M KRW).
- **Monthly Income (월 소득)**: 3,300,000 KRW (Net monthly take-home salary).
- **Monthly Housing Repayment Capacity (월 주거 부담 가능액)**: 500,000 KRW/month (For loan principal & interest).

### 2.2 Bonus Prepayment Plan (Updated Spec)
- **Annual Bonus Prepayment Total**: 10,000,000 KRW / year.
- **January (1월)**: 4,000,000 KRW (Out of 5M KRW 교연비, 1M KRW personal reserve).
- **February (2월)**: 1,000,000 KRW (Out of 2M KRW 부가소득).
- **July (7월)**: 4,000,000 KRW (Out of 5M KRW 교연비, 1M KRW personal reserve).
- **August (8월)**: 1,000,000 KRW (Out of 2M KRW 부가소득).

### 2.3 Living Budget & Apartment Fixed Costs
- **Original 13-Category Budget**: 2,390,708 KRW.
- **Rent Removal (월세 제거)**: -311,000 KRW -> **Base Living Budget**: 2,079,708 KRW.
- **New Apartment Fixed Expenses**:
  - Apartment Management Fee (아파트 관리비): 200,000 KRW
  - Parking Registration (주차비): 10,000 KRW
  - TV / Internet (TV/인터넷): 30,000 KRW
  - **Subtotal New Fixed Costs**: 240,000 KRW.
- **Total Monthly Fixed Expenses (excl. loan)**: 2,079,708 + 240,000 = **2,319,708 KRW**.

---

## 3. Financial Calculation Oracles & Formulas

### 3.1 One-Time Acquisition Costs (R1)
1. **Acquisition Tax (취득세)**:
   - Rates: Base Tax 1.0% + Local Education Tax 0.1% = **1.1%**.
   - First-Home Exemption (생애최초 감면): **-2,000,000 KRW**.
   - 3.5억 Scenario: 350,000,000 × 1.1% - 2,000,000 = **1,850,000 KRW**.
   - 3.75억 Scenario: 375,000,000 × 1.1% - 2,000,000 = **2,125,000 KRW**.
   - 4.0억 Scenario: 400,000,000 × 1.1% - 2,000,000 = **2,400,000 KRW**.
2. **Brokerage Fee (중개수수료)**:
   - Legal Cap (200M ~ 900M KRW): 0.4% + VAT 10% = **0.44%**.
   - 3.5억: 1,540,000 KRW.
   - 3.75억: 1,650,000 KRW.
   - 4.0억: 1,760,000 KRW.
3. **National Housing Bond Discount (국민주택채권 매입 할인 실부담액)**:
   - Formula: Market Price × 70% (Official Price Ratio) × Purchase Rate (2.1%~2.3%) × Discount Rate (10%).
   - 3.5억: 515,000 KRW.
   - 3.75억: 574,000 KRW.
   - 4.0억: 644,000 KRW.
4. **Other Fixed One-Time Costs**:
   - Legal Registration (법무사비): 500,000 KRW.
   - Stamp Tax (인지세): 150,000 KRW.
   - Moving Expenses (이사비): 1,500,000 KRW.
   - Repair & Cleaning (수리청소비): 2,000,000 KRW.
   - **Fixed Subtotal**: 4,150,000 KRW.
5. **Total One-Time Costs**:
   - 3.5억: **7,855,000 KRW**.
   - 3.75억: **8,349,000 KRW**.
   - 4.0억: **8,804,000 KRW**.

---

## 4. 4-Tier Test Specifications

### Tier 1: Feature Coverage (Category-Partition Method, 25+ TCs)
- **R1 (One-time Costs)**: 3.5억 / 3.75억 / 4.0억 tax, brokerage, bond discount, fixed costs.
- **R2 (Loan Comparisons)**: Mortgage principal (`Price - Cash`), LTV checks, Didimdol eligibility (income cap <= 85M joint, <= 60M single), stamp tax (75k borrower share).
- **R3 (Monthly Simulation)**: Living budget 2,079,708 KRW, fixed costs 240,000 KRW, total 2,319,708 KRW, bonus schedule (Jan/Jul 400M, Feb/Aug 100M), unpaid interest settlement & principal reduction.
- **R4 (Admin Timeline)**: Sequential steps (Balance payment -> Ownership registration -> Acquisition tax -> Move-in report -> Fixed date -> Property tax), deadlines, responsible agencies, required documents.
- **R5 (Web UI DOM & JS Structure)**: HTML elements `#price-slider`, `#cash-slider`, `#rate-slider`, `#term-slider`, `#total-initial-cost`, `#monthly-spending`, `#remaining-income`, `#payoff-timeline`, Chart.js script, dark mode toggle.

### Tier 2: Boundary & Corner Cases (BVA Method, 25+ TCs)
- Edge values for price (3.0억 ~ 4.5억), cash (0 KRW, full cash), interest rate (0.0%, 10.0%), term (1 yr, 40 yrs), penny rounding (1 KRW), bonus exceeding remaining balance, negative monthly budget warning, zero management fee, non-first-home tax exemption edge.

### Tier 3: Pairwise Combinations & Web Integration (12+ TCs)
- Pairwise matrix over Factor levels: Price (3.5억, 3.75억, 4.0억) × Rate (3.0%, 4.0%, 4.5%) × Term (30y, 35y, 40y) × Bonus Ratio (100%, 50%, 0%) × Investment Option (Keep, Stop).
- HTML/JS structure integration and static analysis.

### Tier 4: Timeline Simulations (5+ Scenarios)
- Full multi-year timeline simulations:
  1. 3.5억 standard scenario (Didimdol 3.0%, 30 yr, 1,000만 bonus).
  2. 3.75억 standard scenario (Didimdol 3.15%, 30 yr, 1,000만 bonus).
  3. 4.0억 standard scenario (Didimdol 3.3%, 30 yr, 1,000만 bonus).
  4. Conservative scenario (3.75억, 4.5% bank rate, 50% bonus payoff).
  5. Aggressive scenario (3.5억, 3.0%, expense cut + 100% bonus payoff).

---

## 5. Assertion Tolerances & Environment Setup

- **Currency (KRW) Tolerance**: Absolute exact match or `abs=1` rounding tolerance for 1-KRW floating point variances (`pytest.approx(expected, abs=1)`).
- **Timeline Month Tolerance**: Exact match on payoff month (`abs=0`).
- **DOM / Console Error**: 0 uncaught exceptions or syntax errors.
- **Execution Command**:
  ```bash
  /home/imnyj/venv/bin/pytest /home/imnyj/Workspace/House/etc/tests/ -v
  /home/imnyj/venv/bin/python /home/imnyj/Workspace/House/etc/tests/run_e2e_tests.py
  ```
- **Exit Code**: Must return `0` on 100% pass and output results to `etc/logs/e2e_results.json`.
