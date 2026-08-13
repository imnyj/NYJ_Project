# 📊 Financial Data Engine & Analysis Explorer 1 보고서

**작성자:** teamwork_preview_explorer_m1_1  
**작성일시:** 2026-08-12  
**대상 프로젝트:** 청주 방서동 자이 아파트 매입 종합 재무 시뮬레이션  
**저장 경로:** `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1/explorer_m1_1.md`

---

## 1. 개요 및 목적 (Executive Summary)

본 보고서는 Milestone 1(Financial Data Engine & Analysis)의 핵심 산출물로서, 청주 방서동 자이 아파트(<30평 미만, 3.5억/3.75억/4.0억 원) 매입 시 발생하는 일회성 비용(R1)과 시뮬레이션 파라미터를 체계화하고, 데이터 파라미터 파라미터 파일 `etc/data/financial_params.json` 설계 및 파이썬 계산 엔진 `calc_engine.py` 구현을 위한 완벽한 정밀 수학적 공식과 가이드를 제공합니다.

### 주요 분석 요약:
1. **재정 파라미터 통합 설계 (`financial_params.json`)**:
   - 보유 현금 2.3억 원, 월 실수령 소득 330만 원, 연 보너스 1,200만 원 (교연비 1,000만+특강비 200만).
   - 기존 13대 생활비(2,390,708원)에서 월세(31.1만 원) 제거 및 신규 아파트 고정비(24만 원: 관리비 20만+주차 1만+TV/인터넷 3만) 추가 → 변경 후 월 고정지출 **2,319,708원** 확정.
2. **R1 일회성 비용 3개 시나리오 계산 정밀 공식화**:
   - **취득세류**: 본세 1.0% + 지방교육세 0.1% = 1.1% 적용, 생애최초 감면(본세 200만 원 공제).
     - 3.5억 시나리오: Net 취득세 150만 + 지방교육세 15만 = **165만 원**
     - 3.75억 시나리오: Net 취득세 175만 + 지방교육세 17.5만 = **192.5만 원**
     - 4.0억 시나리오: Net 취득세 200만 + 지방교육세 20만 = **220만 원**
   - **중개수수료**: 요율 0.4% + VAT 10% = 0.44% (154만 / 165만 / 176만 원)
   - **법무사 수수료**: 50만 / 52만 / 55만 원
   - **인지세**: 15만 원 (고정)
   - **국민주택채권 할인액**: 시가표준액(70%) × 매입률(2.1% or 2.3%) × 할인율(10%) (51.45만 / 60.375만 / 64.4만 원)
   - **이사비**: 150만 원 (고정), **수리/청소비**: 200만 원 (고정)
   - **R1 일회성 비용 총액**: 3.5억 시나리오 **785.45만 원** (~785.5만 원) / 3.75억 시나리오 **834.875만 원** (~834.9만 원) / 4.0억 시나리오 **880.4만 원** (~880.4만 원)

---

## 2. `etc/data/financial_params.json` 설계 및 JSON 구조 명세

`etc/data/financial_params.json`은 계산 엔진(`calc_engine.py`) 및 웹 시뮬레이터(`ui/index4.html`)가 공통으로 참조할 싱글 소스 오브 트루스(Single Source of Truth) 역할을 수행합니다.

### 2.1. 파라미터 구조 명세
- `scenarios`: 아파트 매매가 시나리오 배열 (`[350000000, 375000000, 400000000]`)
- `cash_reserve`: 초기 보유 현금자산 (`230000000`)
- `monthly_income`: 월 실수령액 (`3300000`)
- `bonuses`: 정기 보너스 배열 (월별, 종류별, 금액)
- `expenses`: 기존 생활비, 제거 항목, 신규 고정비 및 최종 월 고정 지출
- `r1_params`: R1 일회성 비용 관련 모든 요율 및 금액 파라미터
- `r2_params`: R2 대출 상품별 요율, 한도, 차주 부담 부대비용

### 2.2. JSON 완성본 (`etc/data/financial_params.json`)

```json
{
  "project": "House Financial Simulation - Cheongju Bangseo XI",
  "version": "1.0.0",
  "scenarios": [350000000, 375000000, 400000000],
  "cash_reserve": 230000000,
  "monthly_income": 3300000,
  "bonuses": [
    {
      "month": 1,
      "name": "특강비 (1차)",
      "amount": 1000000
    },
    {
      "month": 2,
      "name": "교연비 (1차)",
      "amount": 5000000
    },
    {
      "month": 7,
      "name": "특강비 (2차)",
      "amount": 1000000
    },
    {
      "month": 8,
      "name": "교연비 (2차)",
      "amount": 5000000
    }
  ],
  "expenses": {
    "base_13_categories_total": 2390708,
    "removed_rent_and_electricity": 311000,
    "base_living_net": 2079708,
    "apartment_fixed_breakdown": {
      "maintenance_fee": 200000,
      "parking_fee": 10000,
      "tv_internet": 30000
    },
    "apartment_fixed_total": 240000,
    "total_monthly_fixed_expense": 2319708
  },
  "r1_params": {
    "acquisition_tax": {
      "base_rate": 0.010,
      "local_education_tax_rate": 0.001,
      "first_time_buyer_exemption": 2000000
    },
    "legal_fees_by_scenario": {
      "350000000": 500000,
      "375000000": 520000,
      "400000000": 550000
    },
    "brokerage_fee": {
      "statutory_cap_rate": 0.004,
      "vat_rate": 0.10,
      "effective_rate": 0.0044
    },
    "stamp_duty": 150000,
    "national_housing_bond": {
      "public_appraisal_ratio": 0.70,
      "threshold_public_price": 260000000,
      "rate_below_threshold": 0.021,
      "rate_above_threshold": 0.023,
      "discount_rate": 0.10
    },
    "moving_fee": 1500000,
    "repair_cleaning_fee": 2000000
  },
  "r2_params": {
    "loan_products": {
      "didimdol": {
        "name": "내집마련 디딤돌대출 (신혼부부 특례)",
        "min_rate": 0.030,
        "max_rate": 0.033,
        "max_limit": 400000000,
        "max_ltv": 0.70
      },
      "bogeumjari": {
        "name": "아낌e 보금자리론",
        "min_rate": 0.038,
        "max_rate": 0.041,
        "max_limit": 420000000,
        "max_ltv": 0.70
      },
      "commercial": {
        "name": "시중은행 주택담보대출",
        "min_rate": 0.039,
        "max_rate": 0.046,
        "max_ltv": 0.70
      }
    },
    "borrower_secondary_fees": {
      "mortgage_setup_fee": 0,
      "loan_stamp_duty_share": 75000,
      "annual_guarantee_fee_rate": 0.0005
    }
  }
}
```

---

## 3. R1 매입 시 일회성 비용 수학적 공식화 및 알고리즘

매매 가격 $P$ (단위: 원)에 대하여 7가지 일회성 비용 항목을 다음과 같이 엄밀하게 수식화합니다.

### 3.1. 항목별 산출 수식

#### 1. 취득세 및 지방교육세 ($T_{\text{total}}$)
- **기본 취득세 원액**: $T_{\text{base\_raw}} = P \times 0.010$
- **생애최초 감면 적용 취득세**: $T_{\text{acq\_net}} = \max(0, T_{\text{base\_raw}} - 2,000,000)$
- **지방교육세**: $T_{\text{edu}} = T_{\text{acq\_net}} \times 0.10 = \max(0, T_{\text{base\_raw}} - 2,000,000) \times 0.10$
- **취득세류 최종 합계**: $T_{\text{total}} = T_{\text{acq\_net}} + T_{\text{edu}} = T_{\text{acq\_net}} \times 1.10$
  - *참고 수치 검증*:
    - $P = 3.5\text{억}$: $T_{\text{acq\_net}} = 1.5\text{백만 원}$, $T_{\text{edu}} = 15\text{만 원} \implies T_{\text{total}} = 1,650,000$원
    - $P = 3.75\text{억}$: $T_{\text{acq\_net}} = 1.75\text{백만 원}$, $T_{\text{edu}} = 17.5\text{만 원} \implies T_{\text{total}} = 1,925,000$원
    - $P = 4.0\text{억}$: $T_{\text{acq\_net}} = 2.0\text{백만 원}$, $T_{\text{edu}} = 20\text{만 원} \implies T_{\text{total}} = 2,200,000$원

#### 2. 중개수수료 ($C_{\text{brokerage}}$)
- **법정 상한 요율**: 0.4% ($0.004$), **VAT**: 10% ($0.10$)
- **수식**: $C_{\text{brokerage}} = P \times 0.004 \times (1 + 0.10) = P \times 0.0044$
  - $P = 3.5\text{억} \implies 1,540,000$원
  - $P = 3.75\text{억} \implies 1,650,000$원
  - $P = 4.0\text{억} \implies 1,760,000$원

#### 3. 법무사 등기대행료 ($C_{\text{legal}}$)
- **구간별 고정액**:
  - $P = 350,000,000 \implies C_{\text{legal}} = 500,000$원
  - $P = 375,000,000 \implies C_{\text{legal}} = 520,000$원
  - $P = 400,000,000 \implies C_{\text{legal}} = 550,000$원

#### 4. 소유권이전 인지세 ($C_{\text{stamp}}$)
- **고정액**: $C_{\text{stamp}} = 150,000$원 ($1\text{억} < P \le 10\text{억}$)

#### 5. 국민주택채권 매입 할인 실부담액 ($C_{\text{bond}}$)
- **시가표준액(공시가)**: $P_{\text{public}} = P \times 0.70$
- **매입 요율 ($r_{\text{bond}}$)**:
  $$\text{If } P_{\text{public}} < 260,000,000 \implies r_{\text{bond}} = 0.021 \quad (3.5\text{억 시나리오: } P_{\text{public}} = 2.45\text{억})$$
  $$\text{If } P_{\text{public}} \ge 260,000,000 \implies r_{\text{bond}} = 0.023 \quad (3.75\text{억, } 4.0\text{억 시나리오: } P_{\text{public}} = 2.625\text{억}, 2.8\text{억})$$
- **채권 매입 총액**: $A_{\text{bond\_buy}} = P_{\text{public}} \times r_{\text{bond}}$
- **채권 할인 실부담금 ($C_{\text{bond}}$)** (할인율 10%): $C_{\text{bond}} = A_{\text{bond\_buy}} \times 0.10 = P \times 0.70 \times r_{\text{bond}} \times 0.10$
  - $P = 3.5\text{억} \implies 245,000,000 \times 0.021 \times 0.10 = 514,500$원 (~51.5만 원)
  - $P = 3.75\text{억} \implies 262,500,000 \times 0.023 \times 0.10 = 603,750$원 (~60.4만 원)
  - $P = 4.0\text{억} \implies 280,000,000 \times 0.023 \times 0.10 = 644,000$원 (~64.4만 원)

#### 6. 포장이사비 ($C_{\text{moving}}$)
- **고정액**: $C_{\text{moving}} = 1,500,000$원

#### 7. 기본 수리 및 입주청소비 ($C_{\text{repair}}$)
- **고정액**: $C_{\text{repair}} = 2,000,000$원

#### 8. 일회성 비용 총액 ($R1_{\text{total}}$)
$$R1_{\text{total}} = T_{\text{total}} + C_{\text{brokerage}} + C_{\text{legal}} + C_{\text{stamp}} + C_{\text{bond}} + C_{\text{moving}} + C_{\text{repair}}$$

---

### 3.2. 3개 가격 시나리오별 R1 산출 상세 비교표

| 항목 구분 | 3.5억 원 시나리오 | 3.75억 원 시나리오 | 4.0억 원 시나리오 | 산출 수식 및 비고 |
|---|:---:|:---:|:---:|---|
| **매매가 ($P$)** | **350,000,000원** | **375,000,000원** | **400,000,000원** | 기준 거래 금액 |
| **취득세 본세 (감면 후)** | 1,500,000원 | 1,750,000원 | 2,000,000원 | $\max(0, P \times 1\% - 200만)$ |
| **지방교육세** | 150,000원 | 175,000원 | 200,000원 | 감면 취득세액의 10% ($0.1\%$) |
| **취득세류 소계 ($T_{\text{total}}$)** | **1,650,000원** | **1,925,000원** | **2,200,000원** | **세금 소계** |
| **중개수수료 ($C_{\text{brokerage}}$)** | **1,540,000원** | **1,650,000원** | **1,760,000원** | $P \times 0.44\%$ (VAT 10% 포함) |
| **법무사 수수료 ($C_{\text{legal}}$)** | **500,000원** | **520,000원** | **550,000원** | 소유권 이전 등기 대행 |
| **인지세 ($C_{\text{stamp}}$)** | **150,000원** | **150,000원** | **150,000원** | 정부 수입인지 (고정) |
| **국민주택채권 할인 실부담금** | **514,500원** | **603,750원** | **644,000원** | 공시가(70%) × 매입률 × 10% |
| **포장이사비 ($C_{\text{moving}}$)** | **1,500,000원** | **1,500,000원** | **1,500,000원** | 30평 미만 포장이사 (고정) |
| **기본 수리/청소비 ($C_{\text{repair}}$)** | **2,000,000원** | **2,000,000원** | **2,000,000원** | 입주청소 및 기본정비 (고정) |
| **R1 일회성 비용 총계** | **7,854,500원** | **8,348,750원** | **8,804,000원** | **매입 부대비용 합계** |
| *(반올림 표시 기준 총계)* | *(7,855,000원)* | *(8,349,000원)* | *(8,804,000원)* | 프로젝트 문서 호환 표기 |
| **매입 시 초기 필요 자금 총액** | **357,854,500원** | **383,348,750원** | **408,804,000원** | **매매가 + R1 비용 총계** |

---

## 4. `calc_engine.py` 구현 지침 및 인터페이스 설계

`calc_engine.py`는 모듈화되어 파이썬 테스트 스크립트(`test_calc_engine.py`) 및 시뮬레이션 보고서 생성기에서 직접 호출 가능해야 합니다.

### 4.1. 권장 모듈 구조 및 함수 인터페이스

```python
"""
calc_engine.py - House Financial Simulation Calculation Engine
Location: /home/imnyj/Workspace/House/etc/scripts/calc_engine.py
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Union


def load_financial_params(json_path: Union[str, Path] = None) -> Dict[str, Any]:
    """financial_params.json 로드 및 반환"""
    if json_path is None:
        json_path = Path(__file__).parent.parent / "data" / "financial_params.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_r1_costs(price: int, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    R1 매입 시 일회성 비용 산출
    
    :param price: 아파트 매매 가격 (원)
    :param params: financial_params.json 데이터 (None시 자동 로드)
    :return: 항목별 산출 비용 및 총합 딕셔너리
    """
    if params is None:
        params = load_financial_params()
        
    r1 = params["r1_params"]
    
    # 1. 취득세 및 지방교육세
    acq_cfg = r1["acquisition_tax"]
    base_tax_raw = int(price * acq_cfg["base_rate"])
    net_acq_tax = max(0, base_tax_raw - acq_cfg["first_time_buyer_exemption"])
    local_edu_tax = int(net_acq_tax * 0.10)  # 감면 후 취득세액의 10% (0.1%)
    tax_total = net_acq_tax + local_edu_tax
    
    # 2. 중개수수료
    broker_cfg = r1["brokerage_fee"]
    brokerage_fee = int(price * broker_cfg["effective_rate"])
    
    # 3. 법무사 등기대행료
    legal_fees_map = r1["legal_fees_by_scenario"]
    price_str = str(price)
    legal_fee = legal_fees_map.get(price_str, 500000)
    
    # 4. 인지세
    stamp_duty = r1["stamp_duty"]
    
    # 5. 국민주택채권 할인액
    bond_cfg = r1["national_housing_bond"]
    public_price = price * bond_cfg["public_appraisal_ratio"]
    bond_rate = (bond_cfg["rate_above_threshold"] 
                 if public_price >= bond_cfg["threshold_public_price"] 
                 else bond_cfg["rate_below_threshold"])
    bond_buy_amount = public_price * bond_rate
    bond_discount_fee = int(bond_buy_amount * bond_cfg["discount_rate"])
    
    # 6. 이사비 & 청소/수리비
    moving_fee = r1["moving_fee"]
    repair_cleaning_fee = r1["repair_cleaning_fee"]
    
    # 총계 산출
    total_r1_cost = (tax_total + brokerage_fee + legal_fee + stamp_duty + 
                     bond_discount_fee + moving_fee + repair_cleaning_fee)
    
    return {
        "purchase_price": price,
        "net_acquisition_tax": net_acq_tax,
        "local_education_tax": local_edu_tax,
        "acquisition_tax_total": tax_total,
        "brokerage_fee": brokerage_fee,
        "legal_fee": legal_fee,
        "stamp_duty": stamp_duty,
        "bond_discount_fee": bond_discount_fee,
        "moving_fee": moving_fee,
        "repair_cleaning_fee": repair_cleaning_fee,
        "total_r1_cost": total_r1_cost,
        "total_initial_capital_needed": price + total_r1_cost
    }


def calculate_r2_loans(price: int, cash_reserve: int = 230000000, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    R2 대출 시나리오별 대출 필요액 및 부대비용 계산
    """
    if params is None:
        params = load_financial_params()
        
    pure_required_loan = max(0, price - cash_reserve)
    r2 = params["r2_params"]
    borrower_fees = r2["borrower_secondary_fees"]
    
    # 차주 부담 부대비용
    loan_stamp_duty = borrower_fees["loan_stamp_duty_share"] if pure_required_loan > 100000000 else 0
    annual_guarantee_fee = int(pure_required_loan * borrower_fees["annual_guarantee_fee_rate"])
    
    products = {}
    for key, prod in r2["loan_products"].items():
        products[key] = {
            "name": prod["name"],
            "required_loan": pure_required_loan,
            "ltv": round(pure_required_loan / price, 4),
            "min_rate": prod["min_rate"],
            "max_rate": prod["max_rate"],
            "loan_stamp_duty": loan_stamp_duty,
            "annual_guarantee_fee": annual_guarantee_fee
        }
        
    return {
        "purchase_price": price,
        "cash_reserve": cash_reserve,
        "pure_required_loan": pure_required_loan,
        "products": products
    }


def run_all_scenarios(json_path: Union[str, Path] = None) -> Dict[str, Any]:
    """전체 3개 가격 시나리오에 대한 R1, R2 통합 계산 실행"""
    params = load_financial_params(json_path)
    results = []
    for price in params["scenarios"]:
        r1_res = calculate_r1_costs(price, params)
        r2_res = calculate_r2_loans(price, params["cash_reserve"], params)
        results.append({
            "scenario_price": price,
            "r1": r1_res,
            "r2": r2_res
        })
    return {
        "cash_reserve": params["cash_reserve"],
        "monthly_income": params["monthly_income"],
        "total_monthly_fixed_expense": params["expenses"]["total_monthly_fixed_expense"],
        "scenarios_results": results
    }
```

### 4.2. 수수료 및 단올림/단내림 정밀도 가이드
1. **원 단위 처리**: 모든 최종 금액 산출 시 `int()` 정수 형변환을 적용하여 절사/정수화합니다.
2. **소수점 표시**: 비율 및 LTV 표현 시 소수점 4자리(`round(x, 4)`)로 정리합니다.
3. **오류 처리 (Exception Handling)**:
   - JSON 파일 미존재 시 `FileNotFoundError` 발생 및 유용한 에러 메시지 제공.
   - 가격이 0 이하이거나 보유 현금이 0 이하인 경우 `ValueError` 발생.

### 4.3. 테스트 전략 (`etc/tests/test_calc_engine.py`)
- `pytest` 수트로 작성.
- 3.5억 매매가 입력 시 `total_r1_cost`가 `7854500`원 (또는 1,000원 미만 단위 반올림 범위 `7855000`원 이내)인지 어서션(Assertion) 검증.
- 보유 현금 2.3억 입력 시 3.5억 가격에 대해 순수 대출 필요액이 exact 1.2억 원(`120000000`)인지 검증.

---

## 5. 결론 및 추천 개발 가이드

1. **파라미터 표준 확정**: 본 보고서 섹션 2.2에서 제시된 JSON 명세를 `/home/imnyj/Workspace/House/etc/data/financial_params.json`에 반영하도록 조치합니다.
2. **계산 엔진 구현 규칙**: `calc_engine.py` 작성자는 섹션 4.1의 함수 구조를 정확히 준수하여 독립적이고 재사용 가능하게 구현합니다.
3. **E2E 검증 부합**: 본 계산 결과 수치는 `PROJECT.md` 및 `survey_legal_mortgage.md`의 수치와 100% 상호 호환되며, M2 보고서 및 M3 HTML 시뮬레이터로의 이관 준비가 완결되었습니다.
