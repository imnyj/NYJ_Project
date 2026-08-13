# Milestone 1 (Financial Data Engine & Analysis) 검증 및 리뷰 보고서

- **검증자**: `teamwork_preview_reviewer_m1_1` (Reviewer 1)
- **검증 일시**: 2026-08-12
- **최종 판정**: **APPROVE (승인)**

---

## 1. 개요 및 최종 판정 Summary

Milestone 1에서 작성된 수치 데이터 파라미터(`etc/data/financial_params.json`) 및 계산 엔진(`etc/scripts/calc_engine.py`), 단위 테스트 수트(`etc/tests/test_calc_engine.py`), 자동 검증 스크립트(`etc/scripts/verify_m1.py`)에 대한 수학적 정밀도, 코드 무결성, 안티패턴 검사, 적대적 에지 케이스 스트레스 테스트를 수행하였습니다.

- **최종 검증 결과**: **APPROVE (승인)**
- **결함 및 위반 사항**: 무결성 위반 0건, 중대 결함 0건, 수학적 오차 0원.
- **테스트 통과율**: Pytest 15개 항목 중 15개 성공 (100% Pass).

---

## 2. 수학적 정밀도 검증 (Mathematical Verification)

요구사항(ORIGINAL_REQUEST.md, PROJECT.md, SCOPE.md)에 명시된 모든 산출 공식과 정밀 수치를 전수 검증하였습니다.

### 2.1 R1. 매입 시 일회성 비용 (3개 시나리오 전수 검증)
생애최초 주택구입 취득세 감면(최대 200만 원), 지방교육세(10%), 법정 중개수수료 상한 요율(0.4% + VAT 10% = 0.44%), 소유권 이전 인지세(15만 원), 국민주택채권 매입/할인(공시가 비율 70%, 매입요율 2.1%/2.3%, 할인율 10%), 이사비(150만 원), 기본 수리/청소비(200만 원)를 전수 검증하였습니다.

| 비용 항목 | 3.5억 원 시나리오 | 3.75억 원 시나리오 | 4.0억 원 시나리오 |
| :--- | :---: | :---: | :---: |
| **취득세 본세 (감면전)** | 3,500,000 원 (1.0%) | 3,750,000 원 (1.0%) | 4,000,000 원 (1.0%) |
| **생애최초 감면액** | -2,000,000 원 | -2,000,000 원 | -2,000,000 원 |
| **실부담 취득세** | 1,500,000 원 | 1,750,000 원 | 2,000,000 원 |
| **지방교육세 (10%)** | 150,000 원 | 175,000 원 | 200,000 원 |
| **취득세 관련 합계** | **1,650,000 원** | **1,925,000 원** | **2,200,000 원** |
| **중개수수료 (0.44%)** | **1,540,000 원** | **1,650,000 원** | **1,760,000 원** |
| **법무사 등기대행료** | **500,000 원** | **520,000 원** | **550,000 원** |
| **소유권이전 인지세** | **150,000 원** | **150,000 원** | **150,000 원** |
| **시가표준액 (70%)** | 245,000,000 원 | 262,500,000 원 | 280,000,000 원 |
| **채권 매입 요율** | 2.1% (<2.6억) | 2.3% (≥2.6억) | 2.3% (≥2.6억) |
| **채권 매입금액** | 5,145,000 원 | 6,037,500 원 | 6,440,000 원 |
| **채권 할인 실부담액 (10%)** | **514,500 원** | **603,750 원** | **644,000 원** |
| **이사비** | **1,500,000 원** | **1,500,000 원** | **1,500,000 원** |
| **기본 수리 / 청소비** | **2,000,000 원** | **2,000,000 원** | **2,000,000 원** |
| **R1 일회성 비용 총액** | **7,854,500 원** | **8,348,750 원** | **8,804,000 원** |
| **초기 필요 총 자금 (매매가+비용)** | **357,854,500 원** | **383,348,750 원** | **408,804,000 원** |

- **검증 결론**: 요구사항에 정의된 3.5억(7,854,500원), 3.75억(8,348,750원), 4.0억(8,804,000원)과 **원 단위까지 100% 일치**함을 확인하였습니다.

---

### 2.2 순수 월 고정 생활비 (Net Living Expenses)
- **기존 13대 카테고리 지출**: 2,390,708 원/월 (`8. 학기 중 예상 지출 보고서.md` 기반)
- **제거 항목**: 월세 31.1만 원 (311,000 원)
- **변경 후 순수 기본 생활비**: $2,390,708 - 311,000 = 2,079,708$ 원/월
- **아파트 신규 고정비**: 관리비 200,000 원 + 주차비 10,000 원 + TV/인터넷 30,000 원 = 240,000 원/월
- **최종 월 고정 지출 (대출 원리금 제외)**: $2,079,708 + 240,000 = \mathbf{2,319,708}$ 원/월
- **검증 결론**: 정확히 2,319,708 원/월로 계산되어 반영됨을 확인하였습니다.

---

### 2.3 보너스 상환 스케줄 (Bonus Repayment Schedule)
- **연간 보너스 투입 총액**: 연 **10,000,000 원** (1,000만 원)
- **월별 투입 세부 스케줄**:
  - **1월 / 7월**: 교연비 500만 원 중 **400만 원** 원금 상환 투입 (100만 원 유보)
  - **2월 / 8월**: 특강비/부가소득 **100만 원** 원금 상환 투입
- **검증 결론**: `financial_params.json` 내 `prepayment_schedule`에 정확히 반영되었음을 확인하였습니다.

---

### 2.4 R2. 대출 시나리오 비교, LTV 및 원리금 균등상환 (CPM)
보유 현금 2.3억 원(본인 3천만 + 본인 부모 1억 + 처가 부모 1억) 기준 필요 대출금 및 상환액 검증:

1. **필요 대출금 및 LTV**:
   - 3.5억 매매 시: 필요 대출금 **1.2억 원** (LTV **34.29%**)
   - 3.75억 매매 시: 필요 대출금 **1.45억 원** (LTV **38.67%**)
   - 4.0억 매매 시: 필요 대출금 **1.7억 원** (LTV **42.50%**)

2. **차주 부담 대출 부대비용**:
   - 대출 인지세 차주 부담분 (50%): **75,000 원** (대출금 > 1억 원 기준)
   - 근저당 설정 시 차주 부담 부대비용 (주택채권/등기신청수수료 등): **20,000 원**
   - 대출 초기업무 부대비용 합계: **95,000 원**
   - 연간 주택금융공사(HF/HUG) 보증료율: 연 **0.05%** (1.2억 대출 기준 연 60,000 원)

3. **30년 원리금 균등분할상환(CPM) 월 상환액 비교**:
   - **디딤돌대출 (신혼부부 특례, 연 3.15% 적용)**:
     - 3.5억 매매 (1.2억 대출): **515,684 원/월** (총 이자: 65,646,240 원)
     - 3.75억 매매 (1.45억 대출): **623,118 원/월** (총 이자: 79,322,480 원)
     - 4.0억 매매 (1.7억 대출): **730,553 원/월** (총 이자: 92,999,080 원)
   - **아낌e 보금자리론 (연 3.95% 적용)**:
     - 3.5억 매매 (1.2억 대출): 569,445 원/월
     - 3.75억 매매 (1.45억 대출): 688,079 원/월
     - 4.0억 매매 (1.7억 대출): 806,713 원/월
   - **시중은행 주택담보대출 (연 4.25% 적용)**:
     - 3.5억 매매 (1.2억 대출): 590,328 원/월
     - 3.75억 매매 (1.45억 대출): 713,313 원/월
     - 4.0억 매매 (1.7억 대출): 836,298 원/월

- **검증 결론**: CPM 월 상환액 및 대출 인지세 차주 부담금(7.5만 원) 등 모든 수치가 수학적으로 완벽히 일치합니다.

---

## 3. 코드 무결성 및 적대적 평가 (Integrity & Adversarial Review)

### 3.1 무결성 위반 검사 (Integrity Violation Check)
- **테스트 결과 하드코딩 여부**: `calc_engine.py` 내의 모든 수치는 입력값(`price`, `cash_reserve`, `annual_rate` 등)에 기반하여 동적 수학 공식으로 계산됩니다. 하드코딩된 거짓 구현이나 가짜(Facade) 객체가 존재하지 않습니다.
- **우회 지름길 사용 여부**: 외부 블랙박스 도구를 호출하지 않고 파이썬 표준 라이브러리(`math`, `json`, `pathlib`)만으로 원리금 상환액, 채권 할인, 세금을 정밀하게 구현하였습니다.
- **자가 인증 위반 여부**: Pytest 수트 및 CLI 독립 실행을 통해 검증 가능하도록 투명하게 구성되었습니다.

### 3.2 적대적 에지 케이스 검증 (Adversarial Stress Testing)
- **시나리오 외 매매가 테스트**: 매매가 5억 원 입력 시 디딤돌 대출 한도/자격 조건 체크 및 일반 세율/채권 할인 정상 동작 확인.
- **디딤돌 자격 제한 상한 초과**: 매매가 6억 원 초과 시 `eligible: false` 및 사유(`Price exceeds Didimdol cap`) 정상 출력.
- **보유 현금 > 매매가 케이스**: 필요 대출금 0 원 처리 및 원리금 상환액 0 원 정상 반환.
- **잘못된 입력값 처리**: 음수 가격 또는 음수 현금 입력 시 `ValueError` 예외 정상 발생.

---

## 4. 테스트 실행 결과 (Verification Execution)

### 4.1 Pytest 실행 결과
```shell
$ /home/imnyj/venv/bin/python3 -m pytest etc/tests/test_calc_engine.py -v
============================= test session starts ==============================
collected 15 items

etc/tests/test_calc_engine.py::TestFinancialParamsSchema::test_json_file_exists PASSED [  6%]
etc/tests/test_calc_engine.py::TestFinancialParamsSchema::test_json_structure_and_values PASSED [ 13%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_r1_350m_scenario PASSED [ 20%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_r1_375m_scenario PASSED [ 26%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_r1_400m_scenario PASSED [ 33%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_first_time_buyer_exemption_toggle PASSED [ 40%]
etc/tests/test_calc_engine.py::TestR1OneTimeCosts::test_invalid_price_raises_error PASSED [ 46%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_loan_requirements_and_ltv[350000000-230000000-120000000-34.29] PASSED [ 53%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_loan_requirements_and_ltv[375000000-230000000-145000000-38.67] PASSED [ 60%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_loan_requirements_and_ltv[400000000-230000000-170000000-42.5] PASSED [ 66%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_secondary_loan_fees PASSED [ 73%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_didimdol_vs_commercial_product_details PASSED [ 80%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_cpm_calculation_helper PASSED [ 86%]
etc/tests/test_calc_engine.py::TestR2LoanScenarios::test_invalid_cash_reserve_raises_error PASSED [ 93%]
etc/tests/test_calc_engine.py::TestRunAllScenarios::test_run_all_scenarios PASSED [100%]

============================== 15 passed in 0.03s ==============================
```

### 4.2 CLI Runner 실행 결과
```shell
$ /home/imnyj/venv/bin/python3 etc/scripts/calc_engine.py --all --json
# JSON output produced without any errors, correctly returning all 3 scenarios.
```

---

## 5. 결론 (Conclusion)

Milestone 1의 Financial Data Engine & Analysis 구현물은 제반 법정 요율, 세법 감면 규칙, 원리금 상환 알고리즘, 부대비용 및 생활비 데이터를 정확하게 반영하고 있으며, 모든 테스트를 100% 통과하였습니다.

따라서 **APPROVE (승인)** verdict를 부여합니다.
