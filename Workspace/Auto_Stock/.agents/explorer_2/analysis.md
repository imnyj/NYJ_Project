# Auto Stock Phase 2: 금융 도메인 규칙 및 수수료/세금/슬리피지/정밀 회계 설계 분석 보고서

- **작성자**: Explorer 2 (Financial Domain & Cost Model Analyst)
- **작성일자**: 2026-09-01
- **관련 요구사항**: `ORIGINAL_REQUEST.md` (Phase 2 가상 체결 엔진 및 회계 무결성 검증)

---

## 1. 개요 및 분석 목적 (Executive Summary)

본 보고서는 Auto Stock ML/RL Trader의 **Phase 2: 가상 체결 엔진(Mock Environment)** 구축을 위해 필수적인 한국 주식 시장(KOSPI/KOSDAQ)의 거래 수수료, 증권거래세, 고정 비율 슬리피지 모델, 그리고 부동소수점 오차(Float Precision Issue)를 원천 차단하기 위한 Python `decimal.Decimal` 기반 1원 단위 정밀 회계 설계 표준을 정립합니다.

가상 체결 엔진은 백테스팅 및 강화학습(RL) 에이전트의 보상(Reward) 산출의 기반이 되므로, **실제 한국 증권사 정산 규정과 세법에 부합하는 정밀성**과 **1,000회 이상 연속 매매 시에도 단 1원의 오차도 없는 회계적 무결성(Accounting Invariant)**을 보장해야 합니다.

---

## 2. 한국 주식 시장(KOSPI / KOSDAQ) 거래 비용 체계 분석

### 2.1 증권사 위탁수수료 (Brokerage Commission)
1. **표준 온라인 위탁수수료율**
   - **기본 설정값**: `0.015%` (`0.00015` = `Decimal('0.00015')`)
   - **설정 근거**: 한국 주식 시장의 대표적 개인/기관 API 플랫폼인 키움증권(OpenAPI / 영웅문)의 표준 위탁수수료율(0.015%) 및 주요 대형 증권사(미래에셋, 한국투자 등)의 비대면/온라인 수수료율(0.014%~0.015%)을 표준 벤치마크로 채택.
2. **유관기관 제비용 (KRX + 예탁결제원)**
   - 한국거래소(KRX) 및 한국예탁결제원 제비용율: 약 `0.0036396%` ~ `0.005%` 수준.
   - 통상 증권사 이벤트 수수료(유관기관 제비용만 부과) 시 적용되나, 시뮬레이터 표준 모델에서는 `commission_rate`에 통합하여 단일 파라미터로 처리.
3. **커스터마이징 가능성 (Configurability)**
   - `FeeConfig` 객체를 통해 사용자가 위탁수수료율을 자유롭게 조정(예: `0.0%`, `0.004%`, `0.015%`, `0.05%` 등)할 수 있도록 인터페이스 개방.

### 2.2 증권거래세 및 농어촌특별세 (Securities Transaction Tax)
1. **단방향 과세 원칙**
   - 한국 주식 시장의 증권거래세는 **매도(Sell) 시에만 부과**되며, **매수(Buy) 시에는 전액 비과세(0원)**입니다.
2. **시장별 세율 및 현행 기준**
   - **KOSPI (유가증권시장)**:
     - 증권거래세 `0.03%` + 농어촌특별세 `0.15%` = **합산 세율 `0.18%` (`Decimal('0.0018')`)**
   - **KOSDAQ (코스닥시장)**:
     - 증권거래세 **`0.18%` (`Decimal('0.0018')`)** (농특세 없음)
   - **시뮬레이터 표준 기본값**: `0.18%` (`Decimal('0.0018')`)
   - **과거/커스텀 호환성**: 2023년 이전 기준(`0.20%` = `Decimal('0.0020')`) 및 향후 세법 개정에 대응할 수 있도록 `tax_rate`를 파라미터로 설정 가능하게 설계.

### 2.3 매수/매도 시 거래 정산 프로세스 및 현금 흐름 (Cash Flow Model)
한국 증권사 및 국세징수법의 원 단위 미만 처리 원칙에 따라, 수수료와 세금은 **원 단위 미만 절사(ROUND_FLOOR, Truncate)**를 적용합니다.

```
[매수 (Buy) 프로세스]
1. 체결 단가 산출: Executed Price = Round(Current Price * (1 + Slippage Rate))
2. 매수 총 대금: Gross Buy Amount = Executed Price * Quantity
3. 위탁 수수료: Buy Commission = Floor(Gross Buy Amount * Commission Rate)
4. 증권거래세: Buy Tax = 0 원 (비과세)
5. 총 지출 현금 (Cash Outflow) = Gross Buy Amount + Buy Commission

[매도 (Sell) 프로세스]
1. 체결 단가 산출: Executed Price = Round(Current Price * (1 - Slippage Rate))
2. 매도 총 대금: Gross Sell Amount = Executed Price * Quantity
3. 위탁 수수료: Sell Commission = Floor(Gross Sell Amount * Commission Rate)
4. 증권거래세: Sell Tax = Floor(Gross Sell Amount * Tax Rate)
5. 순 입금 현금 (Cash Inflow) = Gross Sell Amount - Sell Commission - Sell Tax
```

---

## 3. 슬리피지(Slippage) 고정 비율 모델 및 페널티 비용 산출

### 3.1 고정 비율 슬리피지 모델 (Fixed Ratio Slippage Model)
시장가(Market Order) 주문 시 발생하는 유동성 격차 및 체결 지연으로 인한 불리한 체결을 시뮬레이션하기 위해 항상 현재가(Benchmark Price) 대비 일정 비율로 불리하게 체결되는 모델을 적용합니다.

- **기본 슬리피지 비율 (`slippage_rate`)**: `0.1%` (`Decimal('0.0010')`) ~ `0.3%` (`Decimal('0.0030')`), 기본값 `0.1%`
- **매수(Buy) 체결 단가**:
  $$P_{buy\_exec} = \text{Round}\big(P_{market} \times (1 + \text{slippage\_rate})\big)$$
  *(매수자는 시장가보다 비싸게 구매)*
- **매도(Sell) 체결 단가**:
  $$P_{sell\_exec} = \text{Round}\big(P_{market} \times (1 - \text{slippage\_rate})\big)$$
  *(매도자는 시장가보다 싸게 판매)*

### 3.2 슬리피지로 인한 실질적 손실(페널티 비용) 계산
슬리피지는 증권사 영수증에 별도로 청구되는 항목이 아니라 **체결 단가 자체에 내재화(Embedded)**되어 반영됩니다. 그러나 전략 평가 및 회계적 비용 분해를 위해 원본 시장가 대비 발생한 손실을 명시적인 '누적 슬리피지 페널티 비용(Cumulative Slippage Cost)'으로 추적 집계해야 합니다.

1. **매수 1회당 슬리피지 손실액 (Buy Slippage Penalty)**:
   $$\text{Slippage Cost}_{buy} = (P_{buy\_exec} - P_{market}) \times Q$$
2. **매도 1회당 슬리피지 손실액 (Sell Slippage Penalty)**:
   $$\text{Slippage Cost}_{sell} = (P_{market} - P_{sell\_exec}) \times Q$$
3. **누적 슬리피지 비용 (Total Slippage Cost)**:
   $$\text{Cumulative Slippage Cost} = \sum \text{Slippage Cost}_{buy} + \sum \text{Slippage Cost}_{sell}$$

---

## 4. 회계적 무결성 불변식 (Accounting Invariant Proof)

가상 체결 엔진의 신뢰성을 검증하기 위한 핵심 수식입니다.

### 4.1 불변식의 증명 (Proof of Accounting Invariant)
총 자산 가치(Total Equity)는 다음과 같이 정의됩니다:
$$\text{Total Equity} = \text{Cash Balance} + \sum (\text{Holdings} \times P_{market})$$

#### A. 단일 매수 거래 시 자산 변화
- 현금 지출: $-(P_{buy\_exec} \cdot Q + \text{Comm}_{buy}) = -((P_{market} + \Delta P_{slip}) \cdot Q + \text{Comm}_{buy})$
- 보유 주식 평가액 증가: $+ (P_{market} \cdot Q)$
- 순 자산 변동 ($\Delta \text{Equity}$):
  $$\Delta \text{Equity} = -(\Delta P_{slip} \cdot Q + \text{Comm}_{buy}) = -(\text{Slippage Cost}_{buy} + \text{Comm}_{buy})$$

#### B. 단일 매도 거래 시 자산 변화
- 현금 유입: $+(P_{sell\_exec} \cdot Q - \text{Comm}_{sell} - \text{Tax}_{sell}) = +((P_{market} - \Delta P_{slip}) \cdot Q - \text{Comm}_{sell} - \text{Tax}_{sell})$
- 보유 주식 평가액 감소: $-(P_{market} \cdot Q)$
- 순 자산 변동 ($\Delta \text{Equity}$):
  $$\Delta \text{Equity} = -(\Delta P_{slip} \cdot Q + \text{Comm}_{sell} + \text{Tax}_{sell}) = -(\text{Slippage Cost}_{sell} + \text{Comm}_{sell} + \text{Tax}_{sell})$$

#### C. 최종 회계 불변식 (The Grand Invariant)
1. **[시나리오 1] 가격 고정 상태에서의 연속 매매 (Acceptance Criteria)**:
   주가 변동이 없는 상태($P_{market} = \text{const}$)에서 $N$회 연속 매수/매도를 수행했을 때:
   $$\text{Initial Cash} - (\text{Final Cash} + \text{Final Stock Valuation}) = \sum \text{Commission} + \sum \text{Tax} + \sum \text{Slippage Cost}$$
   **오차 허용 범위: 정확히 0원 (1원의 불일치도 불허)**

2. **[시나리오 2] 가격 변동 상태에서의 연속 매매 (일반 시장 거래)**:
   시장의 가격 변동으로 인한 시장 매매 손익(Market Realized/Unrealized PnL)을 고려할 때:
   $$\text{Final Total Equity} = \text{Initial Cash} + \text{Total Market PnL} - (\sum \text{Commission} + \sum \text{Tax} + \sum \text{Slippage Cost})$$

### 4.2 평단가(Average Purchase Price) 관리 모델
보유 주식의 평단가는 **이동평균법(Moving Average Method)**으로 관리합니다:
- 신규 매수 시 평단가 갱신 공식:
  $$\text{AvgPrice}_{new} = \frac{(\text{Holdings}_{old} \times \text{AvgPrice}_{old}) + (\text{Executed Price} \times Q_{buy})}{\text{Holdings}_{old} + Q_{buy}}$$
- 전량 매도 시: $\text{Holdings} = 0 \implies \text{AvgPrice} = 0$
- 부분 매도 시: 평단가는 변하지 않음 ($\text{AvgPrice}_{new} = \text{AvgPrice}_{old}$)

---

## 5. 부동소수점 오차 방지 및 Python `Decimal` 정밀 회계 설계 표준

### 5.1 Python `float` 사용의 치명적 위험성
Python의 기본 `float`은 IEEE 754 부동소수점 배정밀도(64-bit binary float) 방식을 사용하므로 `0.1 + 0.2 != 0.3`, `75000 * 0.00015 = 11.249999999999998` 등의 2진수 변환 오차가 필연적으로 발생합니다. 1,000회 이상의 주문 체결 시 이러한 미세 오차가 누적되어 계좌 잔고 불일치 및 회계 왜곡을 초래합니다.

### 5.2 `decimal.Decimal` 표준 데이터 규약
가상 계좌(`VirtualAccountManager`) 및 체결 엔진(`OrderExecutionEngine`) 내부의 모든 통화, 수량, 단가, 세율, 수수료율은 **`decimal.Decimal`** 타입을 필수로 사용해야 합니다.

1. **상수 및 비율 정의 규칙**:
   - ❌ 금지: `Decimal(0.00015)` (float 생성자 호출 시 이미 정밀도 오손)
   - ✅ 필수: `Decimal('0.00015')`, `Decimal('0.0018')`, `Decimal('0.001')` (문자열 리터럴 사용)
2. **반올림 및 절사 규약 (Quantization Policy)**:
   - **체결 단가 (Executed Price)**: 1원 단위 반올림
     `price.quantize(Decimal('1'), rounding=ROUND_HALF_UP)`
   - **수수료 (Commission)**: 1원 미만 절사 (한국 세법/증권사 관행)
     `commission.quantize(Decimal('1'), rounding=ROUND_FLOOR)`
   - **증권거래세 (Tax)**: 1원 미만 절사
     `tax.quantize(Decimal('1'), rounding=ROUND_FLOOR)`
   - **현금 잔고 및 슬리피지 손실액**: 1원 단위 정수 유지

---

## 6. 제안 인터페이스 및 데이터 클래스 명세 (Proposed Interface Contracts)

Worker(구현 에이전트)가 참조할 수 있도록 핵심 데이터 구조와 클래스 계약을 제안합니다.

```python
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from enum import Enum
from typing import Dict, Optional

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

@dataclass(frozen=True)
class FeeConfig:
    commission_rate: Decimal = Decimal('0.00015')  # 0.015% (매수/매도 공통)
    tax_rate: Decimal = Decimal('0.0018')          # 0.18% (매도 시에만 부과)
    slippage_rate: Decimal = Decimal('0.0010')     # 0.1% (시장가 체결 시)

@dataclass
class Position:
    symbol: str
    quantity: Decimal = Decimal('0')
    average_price: Decimal = Decimal('0')  # 체결가 기준 평단가

@dataclass(frozen=True)
class ExecutionResult:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    benchmark_price: Decimal    # 주문 시점 시장 기준가
    executed_price: Decimal     # 슬리피지 반영 체결단가
    gross_amount: Decimal       # executed_price * quantity
    commission: Decimal         # 수수료 (절사)
    tax: Decimal                # 거래세 (절사)
    slippage_cost: Decimal      # abs(executed_price - benchmark_price) * quantity
    net_cash_flow: Decimal      # 매수: -(gross + comm), 매도: +(gross - comm - tax)
    is_success: bool
    error_message: Optional[str] = None
```

---

## 7. 가상 계좌 관리자 및 체결 엔진 아키텍처 제안

### 7.1 `VirtualAccount` (가상 계좌 관리자)
- **주요 속성**:
  - `initial_cash: Decimal`: 초기 자본금 (불변)
  - `cash: Decimal`: 현재 사용 가능 현금 잔고
  - `positions: Dict[str, Position]`: 종목별 보유 수량 및 평단가
  - `accumulated_commission: Decimal`: 누적 지불 수수료
  - `accumulated_tax: Decimal`: 누적 지불 거래세
  - `accumulated_slippage_cost: Decimal`: 누적 슬리피지 페널티 비용
- **주요 메서드**:
  - `get_total_equity(current_prices: Dict[str, Decimal]) -> Decimal`: 총 자산 가치 산출
  - `can_afford_buy(symbol: str, price: Decimal, qty: Decimal, fee_config: FeeConfig) -> bool`: 매수 가능 잔고 검증 (매수금액 + 수수료 포함)
  - `has_enough_shares(symbol: str, qty: Decimal) -> bool`: 매도 가능 수량 검증
  - `apply_execution(result: ExecutionResult) -> None`: 체결 결과 계좌 반영 (원자적 갱신)
  - `verify_invariant(current_prices: Dict[str, Decimal]) -> bool`: 회계 무결성 자체 검증

### 7.2 `MockExecutionEngine` (가상 주문 체결 엔진)
- **주요 기능**:
  - 시장가(MARKET) 및 지정가(LIMIT) 주문 처리
  - 매수 주문 시 잔고 부족 거부 (No Negative Cash)
  - 매도 주문 시 보유 주식 부족 거부 (No Naked Short Selling)
  - 슬리피지 적용 체결가 산출 -> 수수료/세금 절사 계산 -> 계좌 원자적 반영

### 7.3 `DummyStrategySimulator` (더미 룰 기반 검증 래퍼)
- 1,000회 이상 연속 매수/매도 핑퐁 주문 생성
- 현금 고갈 방지 로직 (현금 부족 시 매도 유도, 주식 없을 시 매수 유도)
- 최종 회계 불변식(`Initial Cash - Total Equity == Cumulative Frictions`) 자동 assert 검증

---

## 8. 결론 및 다운스트림 에이전트를 위한 권고사항

1. **Implementer(Worker) 권고사항**:
   - `modules/engine/mock_environment.py` 작성 시 모든 내부 수치 타입을 `Decimal`로 통일하십시오.
   - 나눗셈 연산(평단가 등) 시 제로 디비전(`ZeroDivisionError`) 방지 및 소수점 자리수 유지 정책을 철저히 적용하십시오.
   - 매수 시 현금 잔고 검사 조건: `cash >= gross_amount + commission` (수수료를 고려하지 않고 주식 대금만 비교하면 잔고가 마이너스가 될 수 있음).
2. **Tester(Challenger) 권고사항**:
   - 고정 가격 1,000회 매매 테스트: `Initial Cash - Final Total Equity == Cumulative Frictions` 0원 오차 검증.
   - 잔고 부족 경계값 테스트: `cash - (gross_amount + commission) == -1` 원일 때 정확히 거절되는지 검증.
   - 무차입 공매도 차단 테스트: 보유량 초과 매도 주문 시 거절 검증.
   - 세금 0원 매수 검증 및 매도 시에만 거래세 부과 검증.
