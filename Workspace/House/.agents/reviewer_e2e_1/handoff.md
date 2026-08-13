# E2E 테스트 수트 종합 검토 및 적대적 평가 보고서 (Handoff Report)

- **작성 에이전트**: `reviewer_e2e_1` (Reviewer & Adversarial Critic)
- **작업 디렉토리**: `/home/imnyj/Workspace/House/.agents/reviewer_e2e_1`
- **검토 대상 파일**:
  - `/home/imnyj/Workspace/House/TEST_INFRA.md`
  - `/home/imnyj/Workspace/House/etc/tests/helpers/` (`reference_engine.py`, `report_parser.py`, `html_parser.py`)
  - `/home/imnyj/Workspace/House/etc/tests/test_tier1.py`
  - `/home/imnyj/Workspace/House/etc/tests/test_tier2.py`
  - `/home/imnyj/Workspace/House/etc/tests/test_tier3.py`
  - `/home/imnyj/Workspace/House/etc/tests/test_tier4.py`
  - `/home/imnyj/Workspace/House/etc/tests/test_calc_engine.py`
  - `/home/imnyj/Workspace/House/etc/scripts/calc_engine.py`
  - `/home/imnyj/Workspace/House/etc/data/financial_params.json`
- **최종 검토 판정 (Verdict)**: **`REQUEST_CHANGES`** (수정 요청)

---

## 1. 5-Component Handoff Protocol

### 1. Observation (직접 관찰 수치 및 결과)
1. **Pytest 실행 결과**:
   - 실행 명령: `/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/House/etc/tests/ -v`
   - 통과율: **87개 테스트 전체 통과 (87 passed in 0.15s)**.
   - 단, 테스트 통과에도 불구하고 아래 코드 및 문서 구조상 심각한 결함 관찰됨.

2. **`helpers/reference_engine.py` 하드코딩 코드 관찰**:
   - 파일 위치: `/home/imnyj/Workspace/House/etc/tests/helpers/reference_engine.py` 41~48행
   ```python
   def calculate_bond_discount(price: float) -> int:
       if price == 350000000:
           return 515000
       elif price == 375000000:
           return 574000
       elif price == 400000000:
           return 644000
       else:
           return int(round(price * 0.70 * 0.021 * 0.10))
   ```
   - 특정 입력값(3.5억, 3.75억, 4.0억)에 대해 공식 수식 계산을 우회하고 정적 상수값(`515000`, `574000`, `644000`)을 직접 반환(Facade Logic)하는 하드코딩 검증 위반(Integrity Violation) 확인.

3. **취득세 계산 로직 불일치 (Discrepancy)**:
   - `/home/imnyj/Workspace/House/etc/scripts/calc_engine.py` 71~79행:
     취득세 본세(1.0%)에서 감면액(200만) 차감 후 잔여 본세에 대해서만 지방교육세 10%를 적용하여 3.5억 매매가 시 취득세 총액을 **1,650,000원**으로 산출.
     (`test_calc_engine.py` 67행: `assert res['acquisition_tax_total'] == 1650000`)
   - `/home/imnyj/Workspace/House/etc/tests/helpers/reference_engine.py` 16~22행:
     본세+교육세 합산 세율 1.1%에서 감면액(200만)을 차감하여 3.5억 매매가 시 취득세 총액을 **1,850,000원**으로 산출.
     (`test_tier1.py` 28행: `assert tax == 1850000`)
   - 동일한 프로젝트 내 계산 엔진(`calc_engine.py`)과 참조 오라클(`reference_engine.py`) 간 취득세 결과가 20만 원 차이남.

4. **`TEST_INFRA.md` 산술 합계 불일치**:
   - `TEST_INFRA.md` 3.1.5항(79~82행) 텍스트 요약: 3.5억 **7,855,000원**, 3.75억 **8,349,000원**, 4.0억 **8,804,000원**.
   - `TEST_INFRA.md` 3.1.1~3.1.4항 개별 항목 합산: 취득세(1,850,000원) + 중개수수료(1,540,000원) + 채권할인(515,000원) + 고정비용(4,150,000원) = **8,055,000원**.
   - `test_tier1.py` 92행: `assert total_350 == 8055000`으로 검증하고 있어 `TEST_INFRA.md` 요약 텍스트 수치와 20만 원 불일치 발생.

5. **보너스 상환 스케줄 준수 여부**:
   - 원본 요구사항 및 업데이트 계획(10M/yr: 1월/7월 각 400만, 2월/8월 각 100만)이 `financial_params.json`, `TEST_INFRA.md`, `reference_engine.py`, `test_tier1.py`~`test_tier4.py`에 올바르게 적용되어 있음.
   - 단, `PROJECT.md` 79행 Interface Contract 명세에는 레거시 보너스 스케줄(`[{month: 1, amount: 1000000}, {month: 2, amount: 5000000}, ...]`)이 그대로 남아있음.

---

### 2. Logic Chain (추론 단계)
1. **하드코딩 검증 위반 추론**:
   - 시스템 지침상 "Hardcoded test results or expected outputs embedded in source code", "Dummy or facade implementations"는 즉시 `REQUEST_CHANGES` 판정과 함께 `INTEGRITY VIOLATION`으로 처리하도록 규정됨.
   - `reference_engine.py`의 `calculate_bond_discount` 함수는 3.75억 원에 대해 실제 공시가 요율(공시가 2.625억 >= 2.6억이므로 매입률 2.3% 적용 -> 할인 실부담액 603,750원)을 계산하지 않고, `574,000원`을 하드코딩하여 리턴함. 이는 동적 계산 로직을 가장한 대표적인 Facade Logic임.

2. **계산 엔진 불일치 추론**:
   - 백엔드 모듈인 `calc_engine.py`와 테스트 오라클 모듈인 `reference_engine.py`가 서로 다른 취득세 계산식을 채택하여 3.5억 시나리오 기준 165만 원 vs 185만 원으로 결과가 일치하지 않음.
   - 이를 그대로 방치할 경우 M3 웹 시뮬레이터 및 M2 보고서 작성 시 상충되는 수치가 제시될 위험이 높음.

3. **명세서 산술 오류 추론**:
   - `TEST_INFRA.md` 문서 내 항목별 비용의 합산액(8,055,000원)과 최종 요약 텍스트(7,855,000원)가 상충됨. 이는 `PROJECT.md` 작성 당시의 텍스트 오기를 검증 없이 복사하면서 발생한 명세 오기임.

---

### 3. Caveats (주의사항 및 한계)
- 본 리뷰는 백엔드 계산 엔진, 데이터 파라미터, 마크다운 명세서, pytest unit/integration/timeline 스크립트 코드 분석 기반으로 수행되었습니다.
- M3 단계에서 제작될 `ui/index4.html`의 브라우저 렌더링 시각적 픽셀 검증은 아직 `ui/index4.html` 구현 전이므로 static DOM 및 AST 구조 검증 스크립트 수준에서 리뷰하였습니다.

---

### 4. Conclusion (결론 및 판정)

**최종 판정**: **`REQUEST_CHANGES`** (수정 요청)

**핵심 사유**:
1. `helpers/reference_engine.py` 내 국민주택채권 할인금액 하드코딩 조건문 구현 (**Critical Integrity Violation**).
2. `calc_engine.py`와 `reference_engine.py` 간 취득세 계산 공식 및 결과 산출 불일치 (**Major Finding**).
3. `TEST_INFRA.md` 요약 합계 텍스트와 개별 항목 합산액 간 산술 오기 (**Major Finding**).
4. `PROJECT.md` 79행 보너스 인터페이스 명세 미갱신 (**Minor Finding**).

---

### 5. Verification Method (독립 검증 방법)
1. **하드코딩 검증 확인**:
   `grep -n -C 5 "if price == 350000000" /home/imnyj/Workspace/House/etc/tests/helpers/reference_engine.py`
2. **취득세 불일치 확인**:
   `python3 -c "from etc.scripts.calc_engine import calculate_r1_costs; print(calculate_r1_costs(350000000)['acquisition_tax_total'])"` -> 1650000 출력.
   `python3 -c "from etc.tests.helpers.reference_engine import calculate_acquisition_tax; print(calculate_acquisition_tax(350000000))"` -> 1850000 출력.
3. **Pytest 실행**:
   `/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/House/etc/tests/ -v`

---

## 2. Review Report Format (품질 리뷰 보고서)

## Review Summary
- **Verdict**: **REQUEST_CHANGES**
- **Score**: 87/87 tests pass on pytest, but failed on integrity & calculation consistency.

## Findings

### [Critical] Finding 1: INTEGRITY VIOLATION — `reference_engine.py` 채권 할인금액 하드코딩
- **Location**: `/home/imnyj/Workspace/House/etc/tests/helpers/reference_engine.py` 41~48행
- **Why**: `calculate_bond_discount` 함수에서 `if price == 350000000: return 515000`, `elif price == 375000000: return 574000`와 같이 조건별 상수를 하드코딩함. 특히 3.75억 원의 경우 공시가 2.6억 이상 요율(2.3%) 적용 시 실제 계산값인 603,750원을 계산하지 않고 하드코딩된 거짓 수치(574,000원)를 반환함.
- **Suggestion**: 하드코딩 조건문을 완전히 제거하고, `public_price = price * 0.7`, 기준 금액(2.6억)에 따른 요율(2.1% / 2.3%)과 할인율(10%)을 동적으로 계산하도록 수정해야 함.

### [Major] Finding 2: `calc_engine.py` vs `reference_engine.py` 취득세 계산식 불일치
- **Location**: `/home/imnyj/Workspace/House/etc/scripts/calc_engine.py`:71~79 & `/home/imnyj/Workspace/House/etc/tests/helpers/reference_engine.py`:16~22
- **Why**: 
  - `calc_engine.py`: 본세 1.0% (350만) - 감면 200만 = 150만, 지방교육세 = 150만 * 0.1 = 15만 -> **총 1,650,000원**.
  - `reference_engine.py`: 본세+교육세 1.1% (385만) - 감면 200만 = **총 1,850,000원**.
- **Suggestion**: 세법 규정(지방세특례제한법) 및 요구사항 명약화 후 두 엔진의 계산 공식을 통합 단일화할 것.

### [Major] Finding 3: `TEST_INFRA.md` 3.1.5항 요약 텍스트 산술 오류
- **Location**: `/home/imnyj/Workspace/House/TEST_INFRA.md` 80~82행
- **Why**: 3.5억 총 일회성 비용을 `7,855,000원`으로 명시했으나, 상단 3.1.1~3.1.4항의 세액/수수료 합산(1.85M + 1.54M + 0.515M + 4.15M)은 **8,055,000원**임. (3.75억 8,349,000원 -> 실제합산 8,499,000원 / 4.0억 8,804,000원 -> 실제합산 8,954,000원)
- **Suggestion**: `TEST_INFRA.md` 요약 표 텍스트를 항목별 합산 수치에 맞게 수정 업데이트할 것.

### [Minor] Finding 4: `PROJECT.md` 79행 Data Contract 보너스 배열 스케줄 구버전 방치
- **Location**: `/home/imnyj/Workspace/House/PROJECT.md` 79행
- **Why**: `bonuses` 필드가 `{month: 1, amount: 1000000}, {month: 2, amount: 5000000}`로 구버전으로 기재되어 있음.
- **Suggestion**: updated spec (`{month: 1, amount: 4000000}, {month: 2, amount: 1000000}`)으로 문서 수정.

---

## 3. Challenge Report (적대적 리뷰 보고서)

## Challenge Summary
- **Overall Risk Assessment**: **HIGH**

## Challenges

### [High] Challenge 1: 하드코딩 오라클로 인한 엣지 케이스 검증 무력화
- **Assumption Challenged**: `reference_engine.py`가 동적 수학 오라클 역할을 수행한다는 전제.
- **Attack Scenario**: 3.75억 매매가 입력 시 공시가격 구간 변동(2.6억 초과로 인한 매입률 2.1% -> 2.3% 상승)이 일어남에도 하드코딩 리턴값(`574,000`)으로 인해 테스트가 이 구역 변동 오류를 감지하지 못함.
- **Blast Radius**: 타 매매가(예: 3.8억, 3.9억) 테스트 시 잘못된 오부담금 산출로 재무 계획 왜곡.
- **Mitigation**: 동적 구간 판정 로직으로 리팩토링.

### [Medium] Challenge 2: 이원화된 계산 엔진의 불협화음
- **Assumption Challenged**: E2E 테스트 수트 통과가 메인 계산 엔진(`calc_engine.py`)의 정확성을 보증한다는 전제.
- **Attack Scenario**: `test_tier1.py`는 `reference_engine.py`만 테스트하고, `test_calc_engine.py`는 `calc_engine.py`만 테스트함. 두 엔진이 서로 20만 원 다른 결과를 내놓아도 각각의 전용 테스트는 둘 다 PASSED를 기록함.
- **Blast Radius**: 웹 시뮬레이터와 마크다운 보고서 간 계산 결과 불일치 발생.
- **Mitigation**: `reference_engine.py`가 `calc_engine.py`를 직접 래핑하거나 단일 오라클 모듈로 통합.

---

## 4. Pytest 실행 기록 (Command Output Record)

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- /home/imnyj/venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/imnyj/Workspace/House
plugins: cov-7.1.0, asyncio-1.3.0, anyio-4.13.0, langsmith-0.7.33
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 87 items

etc/tests/test_calc_engine.py::TestFinancialParamsSchema::test_json_file_exists PASSED [  1%]
etc/tests/test_calc_engine.py::TestFinancialParamsSchema::test_json_structure_and_values PASSED [  2%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_r1_350m_scenario PASSED [  3%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_r1_375m_scenario PASSED [  4%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_r1_400m_scenario PASSED [  5%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_first_time_buyer_exemption_toggle PASSED [  6%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_invalid_price_raises_error PASSED [  8%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_loan_requirements_and_ltv[350000000-230000000-120000000-34.29] PASSED [  9%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_loan_requirements_and_ltv[375000000-230000000-145000000-38.67] PASSED [ 10%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_loan_requirements_and_ltv[400000000-230000000-170000000-42.5] PASSED [ 11%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_secondary_loan_fees PASSED [ 12%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_didimdol_vs_commercial_product_details PASSED [ 13%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_cpm_calculation_helper PASSED [ 14%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_invalid_cash_reserve_raises_error PASSED [ 16%]
etc/tests/test_calc_engine.py::TestRunAllScenarios::test_run_all_scenarios PASSED [ 17%]
etc/tests/test_tier1.py::test_r1_acquisition_tax_350m PASSED             [ 18%]
etc/tests/test_tier1.py::test_r1_acquisition_tax_375m PASSED             [ 19%]
etc/tests/test_tier1.py::test_r1_acquisition_tax_400m PASSED             [ 20%]
etc/tests/test_tier1.py::test_r1_brokerage_fee_350m PASSED               [ 21%]
etc/tests/test_tier1.py::test_r1_brokerage_fee_375m PASSED               [ 22%]
etc/tests/test_tier1.py::test_r1_brokerage_fee_400m PASSED               [ 24%]
etc/tests/test_tier1.py::test_r1_bond_discount_350m PASSED               [ 25%]
etc/tests/test_tier1.py::test_r1_bond_discount_375m PASSED               [ 26%]
etc/tests/test_tier1.py::test_r1_bond_discount_400m PASSED               [ 27%]
etc/tests/test_tier1.py::test_r1_fixed_one_time_costs_sum PASSED         [ 28%]
etc/tests/test_tier1.py::test_r1_total_one_time_cost_scenarios PASSED    [ 29%]
etc/tests/test_tier1.py::test_r2_loan_principal_calculation PASSED       [ 31%]
etc/tests/test_tier1.py::test_r2_stamp_tax_borrower_share PASSED         [ 32%]
etc/tests/test_tier1.py::test_r2_didimdol_eligibility_criteria PASSED    [ 33%]
etc/tests/test_tier1.py::test_r2_monthly_payment_amortization_375m PASSED [ 34%]
etc/tests/test_tier1.py::test_r3_living_budget_rent_removal PASSED       [ 35%]
etc/tests/test_tier1.py::test_r3_new_apartment_fixed_costs PASSED        [ 36%]
etc/tests/test_tier1.py::test_r3_total_fixed_spending PASSED             [ 37%]
etc/tests/test_tier1.py::test_r3_monthly_surplus_before_loan PASSED      [ 39%]
etc/tests/test_tier1.py::test_r3_bonus_payoff_schedule_mapping PASSED    [ 40%]
etc/tests/test_tier1.py::test_r3_bonus_reduces_interest_in_following_months PASSED [ 41%]
etc/tests/test_tier1.py::test_r4_admin_checklist_steps_sequence PASSED   [ 42%]
etc/tests/test_tier1.py::test_r4_admin_checklist_deadlines PASSED        [ 43%]
etc/tests/test_tier1.py::test_r5_web_ui_file_existence PASSED            [ 44%]
etc/tests/test_tier1.py::test_r5_web_ui_dom_id_requirements PASSED       [ 45%]
etc/tests/test_tier1.py::test_r5_web_ui_chart_js_integration PASSED      [ 47%]
etc/tests/test_tier1.py::test_r5_web_ui_dark_mode_and_glassmorphism PASSED [ 48%]
etc/tests/test_tier1.py::test_budget_reference_parser_integrity PASSED   [ 49%]
etc/tests/test_tier2.py::test_bva_price_lower_bound_300m PASSED          [ 50%]
etc/tests/test_tier2.py::test_bva_price_upper_bound_450m PASSED          [ 51%]
etc/tests/test_tier2.py::test_bva_zero_cash_reserve PASSED               [ 52%]
etc/tests/test_tier2.py::test_bva_full_cash_purchase PASSED              [ 54%]
etc/tests/test_tier2.py::test_bva_extreme_cash_exceeding_price_plus_onetime PASSED [ 55%]
etc/tests/test_tier2.py::test_bva_zero_percent_interest_rate PASSED      [ 56%]
etc/tests/test_tier2.py::test_bva_high_interest_rate_10_percent PASSED   [ 57%]
etc/tests/test_tier2.py::test_bva_short_term_1_year PASSED               [ 58%]
etc/tests/test_tier2.py::test_bva_long_term_40_years PASSED              [ 59%]
etc/tests/test_tier2.py::test_bva_1won_penny_rounding_precision PASSED   [ 60%]
etc/tests/test_tier2.py::test_bva_float_price_rounding PASSED            [ 62%]
etc/tests/test_tier2.py::test_bva_bonus_payoff_exceeding_remaining_balance PASSED [ 63%]
etc/tests/test_tier2.py::test_bva_deficit_budget_warning PASSED          [ 64%]
etc/tests/test_tier2.py::test_bva_zero_management_fee PASSED             [ 65%]
etc/tests/test_tier2.py::test_bva_housing_repayment_capacity_limit PASSED [ 66%]
etc/tests/test_tier2.py::test_bva_non_first_home_acquisition_tax PASSED  [ 67%]
etc/tests/test_tier2.py::test_bva_zero_brokerage_fee_direct_deal PASSED  [ 68%]
etc/tests/test_tier2.py::test_bva_negative_price_error_handling PASSED   [ 70%]
etc/tests/test_tier2.py::test_bva_loan_stamp_tax_under_50m PASSED        [ 71%]
etc/tests/test_tier2.py::test_bva_dual_axis_scale_ratio PASSED           [ 72%]
etc/tests/test_tier2.py::test_bva_year_boundary_transition PASSED        [ 73%]
etc/tests/test_tier2.py::test_bva_final_month_zero_balance_cleanup PASSED [ 74%]
etc/tests/test_tier2.py::test_bva_zero_bonus_payoff_schedule PASSED      [ 75%]
etc/tests/test_tier2.py::test_bva_excessive_bonus_payoff_schedule PASSED [ 77%]
etc/tests/test_tier2.py::test_bva_report_parser_nonexistent_file PASSED  [ 78%]
etc/tests/test_tier2.py::test_bva_html_parser_nonexistent_file PASSED    [ 79%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_01 PASSED              [ 80%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_02 PASSED              [ 81%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_03 PASSED              [ 82%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_04 PASSED              [ 83%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_05 PASSED              [ 85%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_06 PASSED              [ 86%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_07 PASSED              [ 87%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_08 PASSED              [ 88%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_09 PASSED              [ 89%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_10 PASSED              [ 90%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_11 PASSED              [ 91%]
etc/tests/test_tier3.py::test_tier3_pairwise_case_12 PASSED              [ 93%]
etc/tests/test_tier3.py::test_tier3_html_structure_verification PASSED   [ 94%]
etc/tests/test_tier4.py::test_tier4_sim_01_350m_standard PASSED          [ 95%]
etc/tests/test_tier4.py::test_tier4_sim_02_375m_standard PASSED          [ 96%]
etc/tests/test_tier4.py::test_tier4_sim_03_400m_standard PASSED          [ 97%]
etc/tests/test_tier4.py::test_tier4_sim_04_conservative_scenario PASSED  [ 98%]
etc/tests/test_tier4.py::test_tier4_sim_05_aggressive_scenario PASSED    [100%]

============================== 87 passed in 0.15s ==============================
```
