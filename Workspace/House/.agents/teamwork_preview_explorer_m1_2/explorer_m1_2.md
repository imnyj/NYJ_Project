# 🏦 R2 대출 시나리오 비교 분석 수식 모델 및 파이썬 엔진 설계 보고서

**작성일**: 2026-08-12  
**작성자**: teamwork_preview_explorer_m1_2 (Milestone 1 Explorer 2)  
**대상 물건**: 청주 방서동 자이 아파트 (<30평 미만, 국민주택규모)  
**보유 현금**: 2억 3,000만 원 (본인 3천만 + 양가 부모님 지원 2억)  
**매매가 시나리오**: 3.5억 원 / 3.75억 원 / 4.0억 원  

---

## 1. 개요 및 분석 목적

본 보고서는 청주 방서동 자이 아파트 매입 프로젝트의 Milestone 1(Financial Data Engine & Analysis) 핵심 과제인 **R2 대출 시나리오 비교 분석**의 수학적 수식 모델을 도출하고, 이를 수행할 파이썬 엔진 모듈(`etc/scripts/calc_engine.py`)의 객체지향 아키텍처 및 API 구조를 설계한 결과를 명세합니다.

본 설계는 정책 모기지(디딤돌대출)와 일반 시중은행 주택담보대출 간의 상환 부담액 비교, 대출 부대비용(근저당 설정비, 대출 인지세, 보증료)의 법적·금융적 분담 수식, 그리고 반기별 보너스(교연비/특강비 연 1,200만 원) 투입에 따른 조기상환 및 만기 단축 알고리즘을 완전하게 정립합니다.

---

## 2. R2 대출 시나리오 수학적 수식 모델 (Mathematical Formulation)

### 2.1. 대출 필요 원금 및 LTV 산출 수식

- **매매가 시나리오 ($S$)**: $S_1 = 350,000,000$원, $S_2 = 375,000,000$원, $S_3 = 400,000,000$원
- **보유 현금 자산 ($C$)**: $C = 230,000,000$원 (고정)
- **필요 대출 원금 ($P$)**:
  $$ P(S) = \max(0, S - C) $$
  - $P(S_1) = 350,000,000 - 230,000,000 = 120,000,000\text{원 } (1.2\text{억 원})$
  - $P(S_2) = 375,000,000 - 230,000,000 = 145,000,000\text{원 } (1.45\text{억 원})$
  - $P(S_3) = 400,000,000 - 230,000,000 = 170,000,000\text{원 } (1.7\text{억 원})$

- **담보대출비율 (LTV, Loan-To-Value)**:
  $$ \text{LTV}(S) = \frac{P(S)}{S} \times 100\% $$
  - $\text{LTV}(S_1) = \frac{1.2\text{억}}{3.5\text{억}} \approx 34.29\%$
  - $\text{LTV}(S_2) = \frac{1.45\text{억}}{3.75\text{억}} \approx 38.67\%$
  - $\text{LTV}(S_3) = \frac{1.7\text{억}}{4.0\text{억}} = 42.50\%$

---

### 2.2. 상환 방식별 원리금 산출 수식

연 이자율을 $R$ (소수점), 약정 만기 개월 수를 $N = 12 \times N_{\text{years}}$, 월 이자율을 $r = \frac{R}{12}$라 정의할 때, $m$번째 달($m \in \{1, 2, \dots, N\}$)의 원금 및 이자 상환액은 다음과 같습니다.

#### (1) 원리금균등 분할상환 (CPM: Constant Payment Mortgage)
매월 총 상환액 $M$이 약정 기간 동안 일정하게 유지되는 방식입니다.
- **월 총 상환액 ($M$)**:
  $$ M = P \cdot \frac{r(1+r)^N}{(1+r)^N - 1} $$
- **$m$월차 대출 잔액 ($B_{m-1}$ 기준, $B_0 = P$)**:
  - $m$월차 발생 이자: $I_m = B_{m-1} \cdot r$
  - $m$월차 원금 상환액: $A_m = M - I_m$
  - $m$월차 상환 후 잔액: $B_m = B_{m-1} - A_m$

#### (2) 원금균등 분할상환 (CAM: Constant Amortization Mortgage)
매월 상환하는 원금 $A$가 일정하고, 잔액 감소에 따라 이자가 감소하는 방식입니다.
- **고정 월 원금 상환액 ($A$)**:
  $$ A = \frac{P}{N} $$
- **$m$월차 잔액 및 총 상환액**:
  - $m$월차 대출 잔액: $B_{m-1} = P - (m-1) \cdot A$
  - $m$월차 발생 이자: $I_m = B_{m-1} \cdot r = \left(P - (m-1)\frac{P}{N}\right) \cdot r$
  - $m$월차 총 상환액: $M_m = A + I_m$
  - $m$월차 상환 후 잔액: $B_m = B_{m-1} - A$

#### (3) 만기일시상환 (Bullet Repayment)
약정 기간 동안 이자만 납부하다가 만기 시점에 원금을 전액 상환하는 방식입니다.
- **$m < N$ 월차 총 상환액**: $M_m = I_m = P \cdot r$ ($A_m = 0$)
- **$m = N$ (만기월) 총 상환액**: $M_N = P + P \cdot r$ ($A_N = P$)

---

### 2.3. 보너스 조기상환 및 만기 단축 알고리즘 (Bonus Prepayment Algorithm)

본 재무 모델의 핵심 상환 화력은 연 4회 지급되는 반기별 정기 보너스입니다.

- **보너스 스케줄 ($S_{\text{bonus}}(m)$)**:
  $$ S_{\text{bonus}}(m) = \begin{cases} 
  1,000,000\text{원} & \text{if } (m \bmod 12) \in \{1, 7\} \quad \text{(1월, 7월 특강비)} \\
  5,000,000\text{원} & \text{if } (m \bmod 12) \in \{2, 8\} \quad \text{(2월, 8월 교연비)} \\
  0\text{원} & \text{otherwise}
  \end{cases} $$

- **월별 상환 실행 순서 및 알고리즘**:
  1. **약정 이자 계산**: $I_m = B_{m-1} \cdot r$
  2. **정기 원리금 상환**: 월 소득(330만 원)에서 정기 원리금 $M_m$ 차감. ($I_m$ 우선 충당 후 잔여액으로 $A_m$ 차감)
  3. **보너스 원금 조기상환 투입**:
     보너스 수입 $S_{\text{bonus}}(m)$은 이자 차감 없이 **100% 원금 직접 차감**에 적용됩니다.
     $$ B_m = \max\left(0, B_{m-1} - A_m - S_{\text{bonus}}(m)\right) $$
  4. **만기 단축 (Term Reduction) 유지**:
     보너스 상환 후에도 약정 월 상환액 $M$을 유지함으로써 잔액 감소 속도를 가속화하여 대출 완납 시점 $m_{\text{payoff}}$를 대폭 단축시킵니다.
  5. **종결 조건**: $B_m \le 0$을 만족하는 최초의 월 index $m_{\text{payoff}}$를 도출합니다.
     - 최종 완납 소요 기간: $\text{완납 년수} = \lfloor m_{\text{payoff}} / 12 \rfloor$년, $\text{완납 개월수} = m_{\text{payoff}} \bmod 12$개월.

---

### 2.4. 대출 부대비용 (Secondary Loan Fees) 정량적 수식

대출 실행 시 1회성 또는 연간 단위로 발생하는 대출 부대비용 수식입니다.

```
+-----------------------------------------------------------------------+
|                       대출 부대비용 구성 및 분담                       |
+--------------------------+--------------------------------------------+
| 근저당권 설정비          | 은행 100% 부담 (차주 실부담: ~2만 원 잡비) |
| 대출 인지세              | 은행 50% / 차주 50% 분담 (차주 실부담 7.5만 원) |
| 주택금융보증료(HF/HUG)   | 차주 100% 부담 (연 0.05% ~ 0.10%)          |
+--------------------------+--------------------------------------------+
```

1. **근저당권 설정비 (Mortgage Setup Fee)**:
   - 채권최고액: $V_{\text{max}} = P \times 120\%$
   - 등록면허세($0.2\%$) + 지방교육세($0.04\%$) + 법무사 설정 수수료 $\rightarrow$ **대출 은행 100% 부담**.
   - 차주 실부담액 ($F_{\text{setup\_borrower}}$): 열람/증명서 발급 등 미시적 등록 잡비 고정 **20,000원**.
2. **대출 인지세 (Loan Stamp Tax)**:
   - 인지세법 제3조 규정에 따라 대출금액 1억 원 초과 ~ 10억 원 이하 시 총 인지세 **150,000원**.
   - 은행 50%, 차주 50% 법정 분담.
   - 차주 실부담액 ($F_{\text{stamp\_borrower}}$):
     $$ F_{\text{stamp\_borrower}} = \frac{150,000\text{원}}{2} = 75,000\text{원 (고정)} $$
     (1.2억, 1.45억, 1.7억 3개 시나리오 모두 동일 적용)
3. **주택금융보증료 (Guarantee Fee - HF/HUG)**:
   - 모기지신용보증(MCG) 또는 한국주택금융공사 보증서 발급 시 적용 보증요율 $g \in [0.0005, 0.0010]$ ($0.05\% \sim 0.10\%$/연).
   - 연간 보증료 산출 수식:
     $$ F_{\text{guarantee\_annual}}(m) = B_{m-1} \times \frac{g}{12} \quad \text{또는} \quad F_{\text{guarantee\_initial}} = P \times g $$
     - 1.2억 대출 시: 연 약 60,000원 ~ 120,000원
     - 1.45억 대출 시: 연 약 72,500원 ~ 145,000원
     - 1.7억 대출 시: 연 약 85,000원 ~ 170,000원

---

## 3. 대출 상품별 조건 비교 및 시나리오별 수치 정량화

### 3.1. 상품 비교 요약표 (Didimdol vs Commercial Bank Mortgage)

| 비교 항목 | (1) 내집마련 디딤돌대출 (신혼부부 특례) | (2) 일반 시중은행 주택담보대출 | 비고 및 시사점 |
|---|---|---|---|
| **소득 자격요건** | 부부합산 연 8,500만 원 이하 | 제한 없음 (DSR 40% 적용) | 본인 연봉 ~5,160만 원으로 **자격 완벽 충족** |
| **대상 주택 조건** | 매매가 6억 이하, 전용 85㎡ 이하 | 제한 없음 | 방서동 자이 <30평 (3.5억~4억) **충족** |
| **대출 한도** | 최대 4.0억 원 (LTV 70~80%) | LTV 70% 이내 | 1.2억~1.7억 대출 신청 시 **한도 여유 극대화** |
| **적용 금리** | **연 3.00% ~ 3.30%** (기본 3.15%) | **연 3.90% ~ 4.60%** (기본 4.25%) | 디딤돌 선택 시 **연 1.1%p 금리 절감** |
| **30년 원리금균등 (1.2억)** | **월 515,643 원** | **월 590,266 원** | 디딤돌이 월 74,623원 (연 89.5만 원) 절감 |
| **30년 원리금균등 (1.45억)** | **월 623,068 원** | **월 713,239 원** | 디딤돌이 월 90,171원 (연 108.2만 원) 절감 |
| **30년 원리금균등 (1.7억)** | **월 730,494 원** | **월 836,211 원** | 디딤돌이 월 105,717원 (연 126.8만 원) 절감 |
| **차주 인지세** | 75,000 원 (고정) | 75,000 원 (고정) | 50:50 법정 분담 동일 |
| **근저당 설정비** | 은행 부담 (차주 잡비 ~2만 원) | 은행 부담 (차주 잡비 ~2만 원) | 동일 |
| **최종 평가** | **최우선 선택 (1순위)** | **대안 (2순위)** | 디딤돌대출 수락 필수 |

---

## 4. `etc/scripts/calc_engine.py` 파이썬 모듈 아키텍처 및 클래스 설계

### 4.1. 모듈 전체 아키텍처 (Module Architecture)

```
etc/scripts/calc_engine.py
 ├── Data Classes & Schemas
 │    ├── OneTimeCostResult (R1 산출 결과 데이터클래스)
 │    ├── MortgageLoanResult (R2 대출 상품별 결과 데이터클래스)
 │    ├── MonthlySimRow (R3 월별 현금흐름 1행 데이터클래스)
 │    └── SimulationSummary (최종 재무 시뮬레이션 종합 결과)
 │
 ├── Class OneTimeCostCalculator (R1 일회성 비용 전수조사 연산기)
 │    ├── calculate_acquisition_tax(price, is_first_home=True)
 │    ├── calculate_brokerage_fee(price, vat_rate=0.10)
 │    ├── calculate_bond_discount(price, pub_price_ratio=0.70, bond_rate=0.021, discount_rate=0.10)
 │    └── calculate_all(price, custom_params=None) -> OneTimeCostResult
 │
 ├── Class MortgageLoanCalculator (R2 대출 시나리오 연산기)
 │    ├── calculate_required_loan(price, cash_reserve=2.3e8)
 │    ├── calculate_monthly_payment(principal, rate, term_months, method="CPM")
 │    ├── calculate_secondary_fees(principal, guarantee_rate=0.0005)
 │    └── compare_products(price, cash_reserve=2.3e8) -> MortgageLoanResult
 │
 ├── Class FinancialSimulationEngine (R3 종합 월별/연별 재무 시뮬레이션 엔진)
 │    ├── run_monthly_simulation(price, cash_reserve, product_type, interest_rate, term_years, bonus_enabled=True)
 │    └── generate_yearly_summary(monthly_rows) -> SimulationSummary
 │
 ├── Standalone API Interface Functions
 │    ├── calculate_r1_costs(price, custom_params=None) -> dict
 │    ├── calculate_r2_loans(price, cash_reserve=2.3e8) -> dict
 │    ├── run_financial_simulation(price, cash_reserve, rate, term_years) -> dict
 │    └── run_all_scenarios(params_json_path=None) -> dict
 │
 └── CLI Command-Line Interface (argparse)
      └── main() (--scenario, --json, --export, --verify)
```

---

### 4.2. 핵심 파이썬 클래스 및 메서드 인터페이스 상세 설계

```python
"""
calc_engine.py - House Financial Simulation Engine Module
Author: teamwork_preview_explorer_m1_2
Date: 2026-08-12
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
import math
import json
import argparse


@dataclass
class OneTimeCostResult:
    price: int
    acquisition_tax_base: int
    acquisition_tax_exemption: int
    acquisition_tax_final: int
    local_education_tax: int
    total_taxes: int
    brokerage_fee_base: int
    brokerage_vat: int
    total_brokerage_fee: int
    judicial_scrivener_fee: int
    stamp_duty: int
    bond_discount_fee: int
    moving_cost: int
    cleaning_repair_cost: int
    total_one_time_cost: int
    total_initial_cash_required: int


@dataclass
class MortgageProductSpec:
    product_name: str
    interest_rate: float
    max_limit: int
    term_years: int
    repayment_method: str  # "CPM", "CAM", "Bullet"


@dataclass
class SecondaryLoanFees:
    mortgage_setup_fee_borrower: int  # ~20,000 KRW
    loan_stamp_tax_borrower: int      # 75,000 KRW fixed
    annual_guarantee_fee: int         # HF/HUG guarantee fee
    total_upfront_fees: int           # setup + stamp tax


@dataclass
class LoanComparisonDetail:
    product_name: str
    loan_principal: int
    interest_rate: float
    ltv_percent: float
    monthly_payment: int
    secondary_fees: SecondaryLoanFees
    total_interest_full_term: int


@dataclass
class MortgageLoanResult:
    price: int
    cash_reserve: int
    required_loan: int
    didimdol: LoanComparisonDetail
    commercial: LoanComparisonDetail


class OneTimeCostCalculator:
    """R1: 매입 시 1회성 제반 비용 계산기"""

    def __init__(self, custom_params: Optional[Dict[str, Any]] = None):
        self.params = custom_params or {}

    def calculate_all(self, price: int) -> OneTimeCostResult:
        # 1. 취득세 (1.0%), 지방교육세 (0.1%), 생애최초 감면 (최대 200만 원)
        tax_base = int(price * 0.01)
        tax_exemption = min(2000000, tax_base)
        tax_final = tax_base - tax_exemption
        local_edu_tax = int(tax_final * 0.10)
        total_taxes = tax_final + local_edu_tax

        # 2. 중개수수료 (0.4% + VAT 10%)
        brokerage_base = int(price * 0.004)
        brokerage_vat = int(brokerage_base * 0.10)
        total_brokerage = brokerage_base + brokerage_vat

        # 3. 법무사 대행료 (시나리오별 추정)
        judicial_fee = 500000 if price <= 350000000 else (520000 if price <= 375000000 else 550000)

        # 4. 인지세 (15만 원 고정)
        stamp_duty = 150000

        # 5. 국민주택채권 할인액 (공시가 70%, 매입률 2.1~2.3%, 할인율 10%)
        pub_price = price * 0.70
        bond_rate = 0.021 if pub_price < 260000000 else 0.023
        bond_amount = pub_price * bond_rate
        bond_discount = int(bond_amount * 0.10)

        # 6. 이사비 및 청소/수리비
        moving_cost = 1500000
        cleaning_repair = 2000000

        total_cost = total_taxes + total_brokerage + judicial_fee + stamp_duty + bond_discount + moving_cost + cleaning_repair
        total_cash_req = price + total_cost

        return OneTimeCostResult(
            price=price,
            acquisition_tax_base=tax_base,
            acquisition_tax_exemption=tax_exemption,
            acquisition_tax_final=tax_final,
            local_education_tax=local_edu_tax,
            total_taxes=total_taxes,
            brokerage_fee_base=brokerage_base,
            brokerage_vat=brokerage_vat,
            total_brokerage_fee=total_brokerage,
            judicial_scrivener_fee=judicial_fee,
            stamp_duty=stamp_duty,
            bond_discount_fee=bond_discount,
            moving_cost=moving_cost,
            cleaning_repair_cost=cleaning_repair,
            total_one_time_cost=total_cost,
            total_initial_cash_required=total_cash_req
        )


class MortgageLoanCalculator:
    """R2: 대출 시나리오 및 부대비용 연산기"""

    def __init__(self, cash_reserve: int = 230000000):
        self.cash_reserve = cash_reserve

    def calculate_cpm_monthly_payment(self, principal: int, annual_rate: float, term_years: int) -> int:
        """원리금균등상환(CPM) 월 상환액 계산"""
        if principal <= 0:
            return 0
        r = annual_rate / 12.0
        n = term_years * 12
        monthly_pmt = principal * (r * (1 + r)**n) / ((1 + r)**n - 1)
        return int(round(monthly_pmt))

    def calculate_secondary_fees(self, principal: int, guarantee_rate: float = 0.0005) -> SecondaryLoanFees:
        """대출 부대비용 계산"""
        setup_fee_borrower = 20000  # 근저당 설정 관련 잡비
        stamp_tax_borrower = 75000  # 1.5억 대출 인지세 50% 분담 고정
        annual_guarantee = int(principal * guarantee_rate)
        return SecondaryLoanFees(
            mortgage_setup_fee_borrower=setup_fee_borrower,
            loan_stamp_tax_borrower=stamp_tax_borrower,
            annual_guarantee_fee=annual_guarantee,
            total_upfront_fees=setup_fee_borrower + stamp_tax_borrower
        )

    def compare_products(self, price: int, didimdol_rate: float = 0.0315, commercial_rate: float = 0.0425, term_years: int = 30) -> MortgageLoanResult:
        required_loan = max(0, price - self.cash_reserve)
        ltv = (required_loan / price) * 100.0 if price > 0 else 0.0

        # 디딤돌 대출 계산
        didimdol_pmt = self.calculate_cpm_monthly_payment(required_loan, didimdol_rate, term_years)
        didimdol_fees = self.calculate_secondary_fees(required_loan, guarantee_rate=0.0005)
        didimdol_total_interest = (didimdol_pmt * term_years * 12) - required_loan

        didimdol_detail = LoanComparisonDetail(
            product_name="디딤돌대출 (신혼부부 특례)",
            loan_principal=required_loan,
            interest_rate=didimdol_rate,
            ltv_percent=round(ltv, 2),
            monthly_payment=didimdol_pmt,
            secondary_fees=didimdol_fees,
            total_interest_full_term=didimdol_total_interest
        )

        # 시중은행 주담대 계산
        commercial_pmt = self.calculate_cpm_monthly_payment(required_loan, commercial_rate, term_years)
        commercial_fees = self.calculate_secondary_fees(required_loan, guarantee_rate=0.0008)
        commercial_total_interest = (commercial_pmt * term_years * 12) - required_loan

        commercial_detail = LoanComparisonDetail(
            product_name="시중은행 주택담보대출",
            loan_principal=required_loan,
            interest_rate=commercial_rate,
            ltv_percent=round(ltv, 2),
            monthly_payment=commercial_pmt,
            secondary_fees=commercial_fees,
            total_interest_full_term=commercial_total_interest
        )

        return MortgageLoanResult(
            price=price,
            cash_reserve=self.cash_reserve,
            required_loan=required_loan,
            didimdol=didimdol_detail,
            commercial=commercial_detail
        )
```

---

### 4.3. 단독 실행 함수 (Standalone API Functions) 규격

외부 스크립트나 E2E 검증용 스크립트에서 직접 호출 가능한 함수 사양입니다.

1. **`calculate_r1_costs(price: int) -> Dict[str, Any]`**
   - **입력**: `price` (예: 350000000, 375000000, 400000000)
   - **출력**: `OneTimeCostResult`를 dict로 변환한 데이터 (세금, 수수료, 채권, 합계 등)
2. **`calculate_r2_loans(price: int, cash_reserve: int = 230000000) -> Dict[str, Any]`**
   - **입력**: `price`, `cash_reserve`
   - **출력**: 디딤돌 vs 시중은행 필요 대출금, LTV, 월 원리금, 대출 인지세(7.5만 원), 보증료 등 상세 비교 딕셔너리
3. **`run_all_scenarios(params_json_path: Optional[str] = None) -> Dict[str, Any]`**
   - **입력**: 파라미터 JSON 파일 경로 (기본값: `etc/data/financial_params.json`)
   - **출력**: 3.5억, 3.75억, 4.0억 3개 시나리오 전 전체 R1 및 R2 계산 통합 결과

---

### 4.4. CLI 명령행 인터페이스 (CLI Interface) 사양

`etc/scripts/calc_engine.py`는 CLI로도 직접 실행하여 JSON 결과를 출력하거나 검증할 수 있도록 지원합니다.

```bash
# 기본 3개 시나리오 통합 계산 및 JSON 출력
python etc/scripts/calc_engine.py --all --json

# 특정 가격 시나리오 (예: 3.75억 원) R2 대출 비교 실행
python etc/scripts/calc_engine.py --price 375000000 --r2

# 결과 데이터를 특정 경로에 저장
python etc/scripts/calc_engine.py --all --export etc/data/simulation_results.json

# 자가 검증 (Self-Verification / Unit Check) 수행
python etc/scripts/calc_engine.py --verify
```

---

## 5. 예외 상황 및 검증 전략 (Edge Cases & Verification)

| 번호 | 예외 및 검증 포인트 | 발생 상황 | 수학적/로직 처리 방식 |
|---|---|---|---|
| 1 | **잔액 Zero 도달 (Zero Balance)** | 보너스 조기상환으로 대출 잔액이 0원 이하가 됨 | `B_m = max(0, B_{m-1} - A_m - S_{bonus})`. `B_m == 0` 시 즉시 시뮬레이션 종료 처리 |
| 2 | **대출 인지세 고정액** | 대출 원금이 1.2억/1.45억/1.7억으로 상이함 | 인지세법상 1억 초과 ~ 10억 이하 구간은 총 15만 원으로 동일하므로, 차주 부담액은 **7.5만 원 고정** 검증 |
| 3 | **이자 우선 충당 원칙** | 조기상환 시 이자가 미납될 위험 | 월 소득에서 해당 월 발생 이자 $I_m$을 100% 우선 차감한 후, 보너스는 전액 순수 원금 차감에 적용하도록 순서 강제 |
| 4 | **소득 요건 초과 예외** | 부부합산 소득이 8.5천만 원을 초과하는 케이스 | `MortgageLoanCalculator` 내 소득 조건 플래그 검사 후, 디딤돌 이용 불가 시 시중은행 대출로 자동 전환 유도 안내 |

---

## 6. 결론 및 다음 단계 제언

1. **R2 대출 수식 모델 완성**:
   - 보유 현금 2.3억 원 기준 필요 대출금은 **3.5억 시나리오 1.2억 원**, **3.75억 시나리오 1.45억 원**, **4.0억 시나리오 1.7억 원**으로 명확히 정립되었습니다.
   - 디딤돌대출(신혼부부 특례 3.15%) 적용 시 30년 원리금균등 월 상환액은 각각 **51.5만 원 / 62.3만 원 / 73.0만 원**으로 시중은행 주담대(4.25%) 대비 **월 약 7.4만~10.5만 원의 이자를 절감**합니다.
2. **부대비용 정율화**:
   - 대출 인지세는 차주 **75,000원 고정**, 근저당 설정비는 **은행 100% 부담**, 보증료는 **연 0.05%** 반영 모델을 구축하였습니다.
3. **다음 구현 단계**:
   - 본 보고서의 설계 아키텍처에 따라 M1 구현 담당 에이전트가 `etc/scripts/calc_engine.py` 모듈 및 `etc/data/financial_params.json` 파일을 즉시 작성할 수 있습니다.
