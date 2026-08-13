# 📋 Milestone 1 상세 명세 및 검증 테스트 수트 전략 보고서 (spec_miner_m1_3.md)

**문서 작성일**: 2026-08-12  
**작성자**: teamwork_preview_spec_miner_m1_3 (M1 Verification & Test Suite Strategy 담당)  
**대상 서비스**: 청주 방서동 자이 아파트 매입 종합 재무 시뮬레이션 시스템 (`calc_engine.py` & `financial_params.json`)  
**작업 디렉토리**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_spec_miner_m1_3`  

---

## 💡 개요 (Executive Summary)

본 보고서는 Milestone 1(Financial Data Engine & Analysis)의 명세 마이닝 결과물로서, `financial_params.json` 데이터 스키마 및 `calc_engine.py` 계산 엔진의 정밀한 경계값(Boundary Values), 예외 케이스(Edge Cases), 반올림 동작(Rounding Behavior), 세금/수수료 연산 수법을 체계화하고, 이를 자동 프로그램 방식으로 검증(Programmatic Verification)할 수 있는 단정문(Assertion) 및 테스트 수트 전략을 제시한다.

ORIGINAL_REQUEST.md의 수락 기준(Acceptance Criteria) 중 R1(일회성 비용 전수조사)과 R2(대출 시나리오 비교 분석) 관련 모든 항목을 100% 검증하는 단정 로직을 포함한다.

---

## 1. 🔍 Features Discovered (발견된 기능 및 규정 명세)

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1 세금 | 취득세 본세 계산 | 매매가 기준 1.0% 기본 취득세 산출 | `price` (int, KRW) | `gross_acq_tax` (float/int) | `price <= 0` 시 ValueError 발생 | ORIGINAL_REQUEST §R1, survey_legal_mortgage.md |
| 2 | R1 세금 | 생애최초 취득세 감면 | 무주택 세대 첫 주택 구입 시 최대 200만 원 본세 공제 | `gross_acq_tax`, `is_first_home=True` | `acq_tax_exemption` (min(gross, 2,000,000)) | 감면 미적용 시 0원 반환 | 지방세특례제한법 제36조의2 |
| 3 | R1 세금 | 지방교육세 산출 | 감면 적용 후 취득세액의 10% (또는 0.1%) 산출 | `net_acq_tax` | `local_edu_tax` (net_acq_tax * 0.10) | 음수 발생 불가 | 지방세법 제150조 |
| 4 | R1 중개 | 중개수수료 및 VAT | 상한 요율 0.4% + 부가가치세 10% (총 0.44%) 적용 | `price` | `brokerage_total` (price * 0.0044) | 거래가 2억 미만/9억 이상 구간 요율 변동 처리 | 공인중개사법 시행규칙 [별표 1] |
| 5 | R1 법무 | 법무사 등기대행료 | 등기 대행 기본보수 및 과표 가산 수수료 산출 | `price` | `scrivener_fee` (50만~55만 원) | 가격대별 미정의 시 기본 50만 원 할당 | 대한법무사회 보수기준 |
| 6 | R1 세무 | 소유권이전 인지세 | 매매계약 증서 인지세 (1억~10억 구간 고정) | `price` | `150,000` KRW | 1억 이하 시 7만 원 적용 | 인지세법 제3조 |
| 7 | R1 금융 | 국민주택채권 할인액 | 공시가(70%) × 매입률(2.1%/2.3%) × 할인율(10%) 실부담액 | `price` | `bond_discount_cost` | 공시가 구간별 매입률 자동 분기 | 주택도시기금법 시행령 [별표 12] |
| 8 | R1 기타 | 이사비 및 수리청소비 | 포장이사비(150만 원) 및 입주청소/기본수리비(200만 원) 고정 | N/A | `1,500,000`, `2,000,000` KRW | 음수 입력 불가 | survey_legal_mortgage.md |
| 9 | R2 대출 | 순 필요 대출금 산출 | 아파트 매매가 - 보유 현금 (2.3억 원) | `price`, `cash_reserve` | `required_loan` | `cash_reserve > price` 시 대출금 0원 | ORIGINAL_REQUEST §R2 |
| 10 | R2 대출 | 총 필요 대출금 산출 | (아파트 매매가 + 일회성 비용 총액) - 보유 현금 | `price`, `r1_total`, `cash_reserve` | `required_gross_loan` | 현금 부족분 명확한 구분 출력 | PROJECT.md |
| 11 | R2 자격 | 디딤돌대출 적격성 | 부부합산 소득(8.5천만 이하), 매매가(6억 이하), 면적(85㎡ 이하) 검증 | `combined_income`, `price`, `area` | `eligible` (bool), `max_limit` (4억) | 조건 미달 시 `eligible = False` 및 사유 반환 | 한국주택금융공사(HF) 규정 |
| 12 | R2 부대 | 대출 인지세 차주 부담 | 대출금액 1억 초과 시 인지세 15만 원의 50% (7.5만 원) | `loan_amount` | `75,000` KRW | 대출 1억 이하 시 3.5만 원 | 인지세법 제3조 |
| 13 | R2 부대 | 근저당 설정비 부담 구분 | 근저당 설정비(은행 100% 부담), 차주 실부담액(등기 신청 수수료 등 ~1만 원) | `loan_amount` | `borrower_setup_cost` (10,000 KRW) | 은행 부담 항목을 차주에게 가산하지 않음 | 은행여신거래기본약관 |
| 14 | R2 부대 | 주택금융보증료 | 연 0.05% ~ 0.10% 보증요율 산출 | `loan_amount`, `rate_annual` | `annual_guarantee_fee` | 0원 이하 산출 불가 | HF/HUG 보증규정 |

---

## 2. ⚠️ Edge Cases (예외 및 경계 조건 명세)

| # | Feature | Input | Observed / Expected Behavior | Handling / Business Logic |
|---|---------|-------|------------------------------|---------------------------|
| 1 | 취득세 감면 | `price = 200,000,000` KRW 이하 | 취득세 본세(1% = 200만 원)가 감면액(200만 원)과 동일하여 본세 0원 | `net_acq_tax = max(0, gross_acq_tax - 2000000)`, 지방교육세 = 0원 처리 |
| 2 | 국민주택채권 매입률 | `price = 371,428,571` KRW (공시가 2.6억 원 경계) | 공시가격(70%)이 정확히 2억 6천만 원에 달함 | `official_price < 260,000,000`은 2.1%, `>= 260,000,000`은 2.3% 매입률 부과 |
| 3 | 디딤돌 소득 조건 | 부부합산 소득 `85,000,000` vs `85,000,001` KRW | 8,500만 원 이하 정수 경계에서 자격 유무 변경 | `income <= 85000000` 시 적격, 초과 시 부적격(보금자리론/시중은행으로 전환 권고) |
| 4 | 보유 현금 초과 | `cash_reserve >= price` | 매매가보다 보유 현금이 많은 경우 | `required_loan = max(0, price - cash_reserve)`, 음수 대출금 방지 |
| 5 | 부대비용 산출 | 소수점 발생 (예: 514,500원 또는 603,750원) | 원 단위/천 단위 반올림(round/math.floor) 규칙 미정의 시 오차 발생 | 한국 원화(KRW) 금융 계산 표준에 맞춰 `round()` 또는 원 단위 정수(`int`) 절사/반올림 명시 |
| 6 | 잘못된 입력 | `price <= 0` 또는 문자열 입력 | 계산 엔진 내부 예외 처리 미비 시 프로그램 붕괴 | `TypeError` / `ValueError` 예외 발생 및 명확한 에러 메시지 반환 |

---

## 3. 📐 R1 및 R2 정밀 계산 공식 및 반올림 규칙

### 3.1. R1 일회성 비용 계산 상세 수식

1. **취득세 본세 (`net_acq_tax`)**:
   $$\text{gross\_acq\_tax} = \text{price} \times 0.01$$
   $$\text{acq\_tax\_exemption} = \begin{cases} \min(\text{gross\_acq\_tax}, 2,000,000) & \text{if first-time home buyer} \\ 0 & \text{otherwise} \end{cases}$$
   $$\text{net\_acq\_tax} = \text{gross\_acq\_tax} - \text{acq\_tax\_exemption}$$

2. **지방교육세 (`local_edu_tax`)**:
   $$\text{local\_edu\_tax} = \text{net\_acq\_tax} \times 0.10$$
   *(주의: 감면 후 실제 납부할 취득세 본세의 10%가 적용됨)*

3. **중개수수료 (`brokerage_total`)**:
   $$\text{brokerage\_base} = \text{price} \times 0.004$$
   $$\text{brokerage\_vat} = \text{brokerage\_base} \times 0.10$$
   $$\text{brokerage\_total} = \text{brokerage\_base} + \text{brokerage\_vat} = \text{price} \times 0.0044$$

4. **국민주택채권 할인액 (`bond_discount_cost`)**:
   $$\text{official\_price} = \text{price} \times 0.70$$
   $$\text{bond\_rate} = \begin{cases} 0.021 & \text{if } 160,000,000 \le \text{official\_price} < 260,000,000 \\ 0.023 & \text{if } 260,000,000 \le \text{official\_price} < 600,000,000 \end{cases}$$
   $$\text{bond\_amount} = \text{official\_price} \times \text{bond\_rate}$$
   $$\text{bond\_discount\_cost} = \text{bond\_amount} \times 0.10$$

5. **일회성 비용 총합 (`r1_total`)**:
   $$\text{r1\_total} = \text{net\_acq\_tax} + \text{local\_edu\_tax} + \text{brokerage\_total} + \text{scrivener\_fee} + \text{stamp\_tax} + \text{bond\_discount\_cost} + \text{moving\_cost} + \text{repair\_cost}$$

### 3.2. 시나리오별 R1 기대 수치 검증표 (Expected Baseline Figures)

| 항목 | 3.5억 원 시나리오 | 3.75억 원 시나리오 | 4.0억 원 시나리오 | 검증 단정 수치 |
|---|---|---|---|---|
| **기본 취득세 (1%)** | 3,500,000 원 | 3,750,000 원 | 4,000,000 원 | `gross_acq_tax` |
| **생애최초 감면액** | -2,000,000 원 | -2,000,000 원 | -2,000,000 원 | `acq_tax_exemption` |
| **실부담 취득세** | 1,500,000 원 | 1,750,000 원 | 2,000,000 원 | `net_acq_tax` |
| **지방교육세 (10%)** | 150,000 원 | 175,000 원 | 200,000 원 | `local_edu_tax` |
| **취득세류 합계** | **1,650,000 원** | **1,925,000 원** | **2,200,000 원** | `acq_taxes_total` |
| **중개수수료 (VAT포함)**| **1,540,000 원** | **1,650,000 원** | **1,760,000 원** | `brokerage_total` |
| **법무사 등기대행료** | **500,000 원** | **520,000 원** | **550,000 원** | `scrivener_fee` |
| **소유권이전 인지세** | **150,000 원** | **150,000 원** | **150,000 원** | `stamp_tax` |
| **채권 할인 실부담금** | **515,000 원** (514.5k) | **604,000 원** (603.75k) | **644,000 원** (644k) | `bond_discount_cost` |
| **포장이사비** | **1,500,000 원** | **1,500,000 원** | **1,500,000 원** | `moving_cost` |
| **입주청소/기본수리** | **2,000,000 원** | **2,000,000 원** | **2,000,000 원** | `repair_cost` |
| **일회성 비용 총계** | **7,855,000 원** | **8,349,000 원** | **8,804,000 원** | `r1_total` |
| **필요 현금 총액** | **357,855,000 원** | **383,349,000 원** | **408,804,000 원** | `total_initial_capital` |

---

## 4. 🗄️ `financial_params.json` 계약 규격 (Data Contract Spec)

M1의 핵심 입력 파라미터 파일인 `etc/data/financial_params.json`의 완전한 JSON 구조 및 검증 조건을 정의한다.

```json
{
  "scenarios": [350000000, 375000000, 400000000],
  "cash_reserve": 230000000,
  "monthly_income": 3300000,
  "bonuses": [
    {"month": 1, "name": "특강비", "amount": 1000000},
    {"month": 2, "name": "교연비", "amount": 5000000},
    {"month": 7, "name": "특강비", "amount": 1000000},
    {"month": 8, "name": "교연비", "amount": 5000000}
  ],
  "expenses": {
    "base_living_no_rent": 2079708,
    "apartment_fixed": {
      "maintenance": 200000,
      "parking": 10000,
      "internet_tv": 30000,
      "total": 240000
    },
    "total_monthly_spending_no_loan": 2319708
  },
  "r1_params": {
    "acq_tax_rate": 0.01,
    "local_edu_tax_rate": 0.10,
    "first_home_exemption_max": 2000000,
    "brokerage_rate": 0.004,
    "vat_rate": 0.10,
    "stamp_tax_transfer": 150000,
    "official_price_ratio": 0.70,
    "bond_discount_rate": 0.10,
    "moving_cost": 1500000,
    "repair_cost": 2000000
  },
  "r2_params": {
    "didimdol": {
      "rate_min": 0.030,
      "rate_max": 0.033,
      "max_limit": 400000000,
      "max_income": 85000000,
      "max_price": 600000000
    },
    "bogumjari": {
      "rate_min": 0.038,
      "rate_max": 0.041,
      "max_limit": 420000000
    },
    "commercial": {
      "rate_min": 0.039,
      "rate_max": 0.046
    },
    "loan_stamp_tax_borrower_share": 75000,
    "guarantee_fee_rate_min": 0.0005,
    "guarantee_fee_rate_max": 0.0010
  }
}
```

---

## 5. 🐍 `calc_engine.py` 파이썬 인터페이스 설계 (Engine Spec)

`etc/scripts/calc_engine.py` 모듈이 갖추어야 할 공개 함수 인터페이스 규격이다.

```python
"""
etc/scripts/calc_engine.py - M1 파이낸셜 계산 엔진
"""
from typing import Dict, Any

def load_financial_params(params_path: str = "etc/data/financial_params.json") -> Dict[str, Any]:
    """JSON 파라미터 파일을 로드하고 스키마를 검증한다."""
    pass

def calculate_r1_costs(price: int, is_first_home: bool = True, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    아파트 매매가 기준 R1 일회성 비용 전 항목을 계산한다.
    Returns dict containing itemized costs, r1_total, and total_initial_capital.
    """
    pass

def calculate_r2_loans(price: int, cash_reserve: int = 230000000, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    매매가 및 보유 현금 기준 필요 대출금, LTV, 대출 상품 비교, 부대비용을 계산한다.
    """
    pass

def run_all_scenarios(params_path: str = "etc/data/financial_params.json") -> Dict[int, Dict[str, Any]]:
    """
    3.5억, 3.75억, 4.0억 3개 시나리오 전체에 대한 R1 및 R2 통합 계산 결과를 반환한다.
    """
    pass
```

---

## 6. 🧪 검증 테스트 수트 설계 (`etc/tests/test_calc_engine.py` / `verify_m1.py`)

Milestone 1의 구현이 완료된 직후 단 한 번의 명령 실행으로 100% 자동 검증이 가능하도록 설계된 pytest 기반 검증 스크립트 코드이다.

```python
"""
etc/tests/test_calc_engine.py - Milestone 1 자동 검증 테스트 수트
"""
import pytest
import json
import os
from etc.scripts.calc_engine import (
    load_financial_params,
    calculate_r1_costs,
    calculate_r2_loans,
    run_all_scenarios
)

PARAMS_PATH = "etc/data/financial_params.json"

class TestFinancialParamsSchema:
    """financial_params.json 데이터 정합성 검증"""

    def test_json_file_exists(self):
        assert os.path.exists(PARAMS_PATH), f"파일 누락: {PARAMS_PATH}"

    def test_json_structure_and_values(self):
        params = load_financial_params(PARAMS_PATH)
        assert params["scenarios"] == [350000000, 375000000, 400000000]
        assert params["cash_reserve"] == 230000000
        assert params["monthly_income"] == 3300000
        assert len(params["bonuses"]) == 4
        
        # 생활비 검증: 2,390,708 - 311,000 = 2,079,708
        assert params["expenses"]["base_living_no_rent"] == 2079708
        # 신규 아파트 고정비: 20만(관리비) + 1만(주차비) + 3만(TV/인터넷) = 24만
        assert params["expenses"]["apartment_fixed"]["total"] == 240000
        # 대출 제외 변경 후 총 고정 지출: 2,319,708원
        assert params["expenses"]["total_monthly_spending_no_loan"] == 2319708


class TestR1OneTimeCosts:
    """R1 일회성 비용 계산 정확성 검증 (Acceptance Criteria 1~3)"""

    @pytest.mark.parametrize("price, expected_r1_total, expected_acq_tax_net, expected_brokerage", [
        (350000000, 7855000, 1500000, 1540000),
        (375000000, 8349000, 1750000, 1650000),
        (400000000, 8804000, 2000000, 1760000),
    ])
    def test_r1_baseline_scenarios(self, price, expected_r1_total, expected_acq_tax_net, expected_brokerage):
        res = calculate_r1_costs(price, is_first_home=True)
        assert res["net_acq_tax"] == expected_acq_tax_net
        assert res["brokerage_total"] == expected_brokerage
        # 오차 1000원 이내 정밀 검증 (반올림 허용)
        assert abs(res["r1_total"] - expected_r1_total) <= 1000

    def test_first_home_exemption_cap(self):
        """취득세 감면 한도 200만 원 적용 검증"""
        # 3.5억 매매 시 취득세 350만 중 200만 감면 -> 150만
        res = calculate_r1_costs(350000000, is_first_home=True)
        assert res["acq_tax_exemption"] == 2000000
        assert res["net_acq_tax"] == 1500000

        # 감면 미적용 시 취득세 350만 전액
        res_no_exempt = calculate_r1_costs(350000000, is_first_home=False)
        assert res_no_exempt["acq_tax_exemption"] == 0
        assert res_no_exempt["net_acq_tax"] == 3500000

    def test_national_housing_bond_discount(self):
        """국민주택채권 할인액 구간별 매입률 및 실부담액 검증"""
        # 3.5억 시나리오: 공시가 2.45억 (2.1% 매입률) -> 할인액 약 515,000원
        res_35 = calculate_r1_costs(350000000)
        assert 514000 <= res_35["bond_discount_cost"] <= 516000

        # 4.0억 시나리오: 공시가 2.80억 (2.3% 매입률) -> 할인액 약 644,000원
        res_40 = calculate_r1_costs(400000000)
        assert 643000 <= res_40["bond_discount_cost"] <= 645000

    def test_invalid_price_raises_exception(self):
        """음수 또는 0원 매매가 예외 발생 검증"""
        with pytest.raises(ValueError):
            calculate_r1_costs(0)
        with pytest.raises(ValueError):
            calculate_r1_costs(-100000)


class TestR2LoanComparison:
    """R2 대출 시나리오 및 부대비용 비교 검증"""

    @pytest.mark.parametrize("price, cash, expected_loan, expected_ltv", [
        (350000000, 230000000, 120000000, 34.29),
        (375000000, 230000000, 145000000, 38.67),
        (400000000, 230000000, 170000000, 42.50),
    ])
    def test_required_loan_and_ltv(self, price, cash, expected_loan, expected_ltv):
        res = calculate_r2_loans(price, cash_reserve=cash)
        assert res["required_loan"] == expected_loan
        assert abs(res["ltv_percent"] - expected_ltv) <= 0.05

    def test_didimdol_qualification_and_secondary_fees(self):
        """디딤돌대출 자격 및 부대비용(인지세 7.5만 원) 검증"""
        res = calculate_r2_loans(350000000, cash_reserve=230000000)
        assert res["didimdol"]["eligible"] is True
        # 대출 인지세 차주 부담액: 75,000원 고정
        assert res["secondary_fees"]["loan_stamp_tax_borrower"] == 75000
        # 근저당 설정비 차주 실부담: 0원 또는 3만원 이하
        assert res["secondary_fees"]["mortgage_setup_borrower"] <= 30000
```

---

## 7. 🎯 Acceptance Criteria (R1, R2) 추적성 매트릭스

ORIGINAL_REQUEST.md의 수락 기준(Acceptance Criteria)과 본 명세서의 검증 단정문 간 100% 매핑 표이다.

| 수락 기준 분류 | 세부 수락 기준 요구사항 | 대응되는 검증 함수 / 단정문 | 통과 조건 (Assertion Criteria) |
|---|---|---|---|
| **비용 정확성** | 취득세 계산이 현행 세법(2025~2026 기준)의 세율과 감면 조건을 정확히 반영 | `test_first_home_exemption_cap()` | `gross_acq_tax == price * 0.01`, `exemption == min(gross, 2M)`, `net_acq_tax` 차감 정확 반영 |
| **비용 정확성** | 중개수수료가 법정 요율(0.4%) 및 VAT 10%를 준수하며 3개 시나리오별 정확히 계산 | `test_r1_baseline_scenarios()` | 3.5억: 154만 원 / 3.75억: 165만 원 / 4.0억: 176만 원 일치 |
| **비용 정확성** | 국민주택채권 매입비가 시가 기준 매입비율과 할인율을 반영한 실부담액으로 산출 | `test_national_housing_bond_discount()` | 공시가(70%) 기준 1.6억~2.6억 2.1%, 2.6억~6억 2.3% 매입률 및 10% 할인액 정밀 산출 |
| **데이터 정합성**| 기존 13대 카테고리 중 월세(31.1만)가 제거되고 관리비 등 신규 항목(24만)으로 올바르게 대체 | `test_json_structure_and_values()` | `base_living_no_rent == 2079708`, `apartment_fixed == 240000`, 총합 `2319708` 일치 |
| **대출 시나리오**| 보유 현금 2.3억 기준 필요 대출금 및 디딤돌/보금자리론 비교, 대출 부대비용 산출 | `test_required_loan_and_ltv()`, `test_didimdol_qualification()` | 필요대출금 1.2억/1.45억/1.7억 및 인지세 차주 부담 7.5만 원 고정 반영 |

---

## 8. 🏁 결론 및 구현 팀 전달 사항

1. **파라미터 표준화**: `etc/data/financial_params.json`을 작성할 때 본 보고서의 JSON 스키마 구조를 엄격히 준수할 것.
2. **계산 엔진 구현**: `etc/scripts/calc_engine.py` 작성 시 float 반올림으로 인한 1원 단위 오차 방지를 위해 `round(val)` 또는 `int()` 절사 규칙을 정밀하게 적용할 것.
3. **자동 검증 실행**: `etc/tests/test_calc_engine.py` 스크립트를 즉시 실행 가능하도록 배치하고 `pytest` 실행을 통해 M1 검증 100% 통과를 확인할 것.
