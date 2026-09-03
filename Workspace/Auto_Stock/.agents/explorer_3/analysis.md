# Phase 2: 가상 체결 엔진(Mock Environment) 요구사항 및 아키텍처 심층 분석 보고서

**작성자**: Explorer 3  
**작성일시**: 2026-09-01T23:02:00+09:00  
**상태**: 완료 (Completed)  

---

## 1. 개요 및 분석 목적

본 보고서는 Auto Stock ML/RL Trader 프로젝트의 **Phase 2: 가상 체결 엔진(Mock Environment)** 구축을 위한 시스템 요구사항(R1, R2, R3) 분석, 세부 컴포넌트 아키텍처 설계, 한국 주식 시장 표준 거래 비용 모델링, 그리고 부동소수점 오차 없는 **엄격한 1원 단위 회계 무결성(Accounting Invariant)의 수학적 증명 및 검증 체계**를 정의합니다.

---

## 2. 핵심 요구사항 분석 (R1, R2, R3)

### R1. Virtual Account Manager (가상 계좌 관리자)

#### 1) 핵심 책임 (Responsibilities)
- 투자 자산(현금 잔고, 종목별 주식 보유 수량, 이동평균 매입단가)의 상태 저장 및 스냅샷 제공.
- 매수/매도 체결에 따른 잔고 차감/가산 및 포지션 갱신.
- 실시간 평가액(Total Equity), 실현 손익(Realized PnL), 미실현 손익(Unrealized PnL) 산출.
- `Decimal` 기반 정밀 회계 관리로 부동소수점 오차 원천 차단.

#### 2) 데이터 모델 설계
```python
@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_buy_price: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")  # quantity * avg_buy_price

@dataclass
class AccountSnapshot:
    timestamp: datetime
    initial_capital: Decimal
    cash_balance: Decimal
    stock_eval_amount: Decimal
    total_equity: Decimal
    total_cost: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    cum_fee: Decimal
    cum_tax: Decimal
    cum_slippage: Decimal
    positions: Dict[str, Position]
```

#### 3) 이동평균 매입단가(평단가) 갱신 알고리즘
- **추가 매수 시**:
  $$Q_{\text{new}} = Q_{\text{old}} + Q_{\text{add}}$$
  $$P_{\text{avg, new}} = \frac{Q_{\text{old}} \cdot P_{\text{avg, old}} + Q_{\text{add}} \cdot P_{\text{exec}}}{Q_{\text{new}}}$$
  $$\text{Total Cost} = Q_{\text{new}} \cdot P_{\text{avg, new}}$$
- **매도 시**:
  - 수량 차감: $Q_{\text{new}} = Q_{\text{old}} - Q_{\text{sell}}$
  - 평단가 유지: $P_{\text{avg, new}} = P_{\text{avg, old}}$ (단, $Q_{\text{new}} == 0$ 일 때 $P_{\text{avg}} = 0$, $\text{Total Cost} = 0$)
  - 매도 시 실현 손익:
    $$\text{Realized PnL} = (P_{\text{exec}} - P_{\text{avg, old}}) \cdot Q_{\text{sell}} - \text{Fee} - \text{Tax}$$

---

### R2. Order Execution Engine (가상 주문 체결기)

#### 1) 주문 수신 및 유효성 검증
- **주문 파라미터**: `symbol`, `side` (BUY/SELL), `order_type` (MARKET/LIMIT), `quantity`, `price` (지정가용), `current_market_price`.
- **거절/예외 처리 규칙**:
  - `quantity <= 0` 또는 `price <= 0`: `InvalidOrderError` / `REJECTED`
  - **매수 주문 시**:
    $$\text{Gross Amount} = P_{\text{exec}} \cdot Q$$
    $$\text{Fee} = \lfloor \text{Gross Amount} \cdot \text{Fee Rate} \rfloor$$
    $$\text{Required Cash} = \text{Gross Amount} + \text{Fee}$$
    만약 $\text{Required Cash} > \text{Cash Balance}$ 이면 즉시 주문 거절(`InsufficientFundsError` / `OrderStatus.REJECTED`).
  - **매도 주문 시**:
    만약 $Q > \text{Current Position Quantity}$ 이면 즉시 주문 거절(`InsufficientSharesError` / `OrderStatus.REJECTED`).

#### 2) 슬리피지(Slippage) 모델
- **요구사항**: 현재가 대비 항상 일정한 비율(고정 비율)로 불리하게 체결되는 슬리피지 적용.
- **기본 슬리피지율**: $\text{slippage\_rate} = 0.001$ (0.1%, 설정 가능 0.001 ~ 0.003)
- **체결 단가 계산**:
  - 매수(BUY): $P_{\text{exec}} = P_{\text{market}} \cdot (1 + \text{slippage\_rate})$
  - 매도(SELL): $P_{\text{exec}} = P_{\text{market}} \cdot (1 - \text{slippage\_rate})$
- **슬리피지 비용(Slippage Cost)**:
  - 매수 시: $\text{Slippage Cost} = (P_{\text{exec}} - P_{\text{market}}) \cdot Q = P_{\text{market}} \cdot \text{slippage\_rate} \cdot Q$
  - 매도 시: $\text{Slippage Cost} = (P_{\text{market}} - P_{\text{exec}}) \cdot Q = P_{\text{market}} \cdot \text{slippage\_rate} \cdot Q$
  - 항상 $\ge 0$ 인 트랜잭션 마찰 비용으로 계상.

#### 3) 한국 주식 시장 거래비용 모델
- **증권거래세 (Securities Transaction Tax)**:
  - 매수 시: 0%
  - 매도 시: 0.18% ~ 0.20% (기본값: $\text{tax\_rate} = 0.0018$)
  - $\text{Tax} = \lfloor P_{\text{exec}} \cdot Q \cdot \text{tax\_rate} \rfloor$ (원 단위 절사)
- **매매 수수료 (Brokerage Commission)**:
  - 매수/매도 양방향 적용
  - 기본값: $\text{fee\_rate} = 0.00015$ (0.015% = 1.5bp)
  - $\text{Fee} = \lfloor P_{\text{exec}} \cdot Q \cdot \text{fee\_rate} \rfloor$ (원 단위 절사)

#### 4) 체결 이력(Trade History) 로깅 구조
```python
@dataclass
class TradeRecord:
    trade_id: str
    order_id: str
    timestamp: datetime
    symbol: str
    side: OrderSide
    order_type: OrderType
    market_price: Decimal
    executed_price: Decimal
    quantity: int
    gross_amount: Decimal
    fee: Decimal
    tax: Decimal
    slippage_cost: Decimal
    cash_after: Decimal
    position_qty_after: int
    avg_buy_price_after: Decimal
```

---

### R3. Dummy Strategy Simulator (더미 룰 기반 검증 래퍼)

#### 1) 목적
- 복잡한 ML/RL 모델 탑재 전 가상 체결 엔진의 회계 무결성, 1,000회 연속 주문 처리 내구성, 메모리 안정성 검증.

#### 2) 전략 구현 유형
1. **Ping-Pong Strategy (기계적 핑퐁 매매)**:
   - 고정 또는 밴드 가격에서 매수($Q$) -> 매도($Q$)를 1,000회 이상 연속 실행.
   - 포지션을 0으로 종료시키며 회계 무결성 공식($C_0 == C_{\text{final}} + \sum \text{Costs}$)을 1원의 오차 없이 증명.
2. **SMA Crossover Strategy (단순 이동평균 교차 매매)**:
   - 단기(5)/장기(20) 이동평균선 골든크로스 시 매수, 데드크로스 시 매도.
   - Phase 1에서 수집된 실제 삼성전자 Parquet 데이터(`data/raw/005930_consolidated.parquet`) 기반 시뮬레이션 지원.
3. **Random Walk Stress Strategy (무작위 스트레스 테스트)**:
   - 무작위 수량 매수/매도/홀드 주문을 1,000~10,000회 난사하여 잔고 부족, 수량 부족 거절 예외 처리 및 계좌 음수화 방지 검증.

---

## 3. 회계 무결성 검증 공식 및 수학적 증명 (Accounting Invariant)

### 1) 회계 무결성 기본 정리
요구사항 검증 공식:
$$\text{Initial Capital} == (\text{Final Cash} + \text{Final Stock Valuation}) + (\text{Cum Fee} + \text{Cum Tax} + \text{Cum Slippage})$$

### 2) 수학적 불변성 증명 (Step-by-Step Proof)

- **초기 상태 ($t=0$)**:
  - $C_0 = \text{Initial Capital}$
  - $S_0 = 0$, $V_0 = 0$
  - $\text{CumFee}_0 = 0, \text{CumTax}_0 = 0, \text{CumSlip}_0 = 0$

- **매수 거래 ($t=k$, 수량 $q_k$, 시장가 $p_k$)**:
  - 체결가: $p_{\text{exec}, k} = p_k + \Delta p_k \quad (\Delta p_k = p_k \cdot \text{slip})$
  - 비용: $\text{Slip}_k = q_k \cdot \Delta p_k$, $\text{Fee}_k = \text{Fee}(p_{\text{exec}, k} \cdot q_k)$, $\text{Tax}_k = 0$
  - 현금: $C_k = C_{k-1} - (q_k \cdot p_{\text{exec}, k} + \text{Fee}_k) = C_{k-1} - q_k \cdot p_k - \text{Slip}_k - \text{Fee}_k$
  - 주식수: $S_k = S_{k-1} + q_k$
  - 수식을 정리하면:
    $$C_k + S_k \cdot p_k + \text{CumFee}_k + \text{CumSlip}_k + \text{CumTax}_k = C_{k-1} + S_{k-1} \cdot p_k + \text{CumFee}_{k-1} + \text{CumSlip}_{k-1} + \text{CumTax}_{k-1}$$

- **매도 거래 ($t=m$, 수량 $q_m$, 시장가 $p_m$)**:
  - 체결가: $p_{\text{exec}, m} = p_m - \Delta p_m \quad (\Delta p_m = p_m \cdot \text{slip})$
  - 비용: $\text{Slip}_m = q_m \cdot \Delta p_m$, $\text{Fee}_m = \text{Fee}(p_{\text{exec}, m} \cdot q_m)$, $\text{Tax}_m = \text{Tax}(p_{\text{exec}, m} \cdot q_m)$
  - 현금: $C_m = C_{m-1} + (q_m \cdot p_{\text{exec}, m} - \text{Fee}_m - \text{Tax}_m) = C_{m-1} + q_m \cdot p_m - \text{Slip}_m - \text{Fee}_m - \text{Tax}_m$
  - 주식수: $S_m = S_{m-1} - q_m$
  - 수식을 정리하면:
    $$C_m + S_m \cdot p_m + \text{CumFee}_m + \text{CumSlip}_m + \text{CumTax}_m = C_{m-1} + S_{m-1} \cdot p_m + \text{CumFee}_{m-1} + \text{CumSlip}_{m-1} + \text{CumTax}_{m-1}$$

- **결론 (Theorem)**:
  - 주가 변동 손익(Market Price Drift PnL)이 없는 고정 가격 거래 또는 핑퐁 매매의 경우:
    $$C_0 == C_{\text{final}} + S_{\text{final}} \cdot P_{\text{final}} + \text{CumFee} + \text{CumTax} + \text{CumSlippage}$$
    가 정확히 성립하며, 어떠한 1원의 불일치도 허용되지 않습니다.
  - 변동 가격 시계열 매매의 경우:
    $$C_0 + \sum_{t=1}^N S_{t-1} \cdot (p_t - p_{t-1}) == C_{\text{final}} + S_{\text{final}} \cdot p_N + \text{CumFee} + \text{CumTax} + \text{CumSlippage}$$
    로 일반화됩니다.

---

## 4. 부동소수점 오차 방지 아키텍처 (Decimal Precision)

1. **Python Decimal 모듈 표준화**:
   - 모든 금액, 단가, 수수료, 세금, 슬리피지 계산에 `from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP` 적용.
   - 문자열 생성자(`Decimal(str(price))`)를 사용하여 float 변환 시의 미세 오차 방지.
2. **단위 및 절사 규정**:
   - 수수료/세금: 원 단위 내림 `ROUND_FLOOR` (한국 증권사 실무 표준).
   - 슬리피지 비용: 원 단위 또는 고정 정밀도(Decimal 4자리 유지 후 집계).
   - 잔고 검증: `abs(left - right) < Decimal('0.0001')` 또는 완전 일치 `left == right`.

---

## 5. 모듈 인터페이스 및 클래스 다이어그램 설계

```
modules/engine/
├── __init__.py
└── mock_environment.py
    ├── [Enums] OrderSide, OrderType, OrderStatus
    ├── [DataClasses] Position, AccountSnapshot, Order, TradeRecord, SimulationResult
    ├── [Exceptions] EngineError, InsufficientFundsError, InsufficientSharesError, InvalidOrderError
    ├── [Class] VirtualAccount (R1)
    │   ├── deposit(amount)
    │   ├── withdraw(amount)
    │   ├── update_buy(symbol, qty, price, fee)
    │   ├── update_sell(symbol, qty, price, fee, tax)
    │   ├── get_portfolio_value(prices)
    │   └── snapshot(prices)
    ├── [Class] ExecutionEngine (R2)
    │   ├── submit_order(order, market_price) -> TradeRecord
    │   ├── calculate_slippage(side, market_price) -> (exec_price, slippage_cost)
    │   ├── calculate_fee(gross_amount) -> fee
    │   ├── calculate_tax(gross_amount, side) -> tax
    │   └── get_trade_history() -> List[TradeRecord]
    ├── [Class] DummyStrategySimulator (R3)
    │   ├── run_ping_pong(steps=1000, price=70000, qty=10) -> SimulationResult
    │   ├── run_sma_crossover(df_ohlcv, short_w=5, long_w=20) -> SimulationResult
    │   └── run_stress_random(steps=1000, price_series=...) -> SimulationResult
    └── [Facade] MockEnvironment
        ├── reset(initial_capital)
        ├── step(action) -> (observation, reward, done, info)
        └── get_accounting_audit() -> Dict[str, Any]
```

---

## 6. 테스트 및 검증 전략 (`tests/test_phase2.py`)

1. **단위 테스트 (Unit Tests)**:
   - 계좌 잔고 입출금, 포지션 추가/감소, 평단가 이동평균 계산 검증.
   - 슬리피지 고정 비율(0.1%, 0.2%) 불리한 체결 방향성 검증.
   - 수수료(0.015%), 거래세(0.18% 매도만) 원 단위 절사 계산 검증.
   - 잔고 부족/수량 부족 주문 거절 및 예외 발생 검증.
2. **통합 및 스트레스 테스트 (Integration & Stress Tests)**:
   - 핑퐁 매매 1,000회 연속 실행 후 회계 무결성 1원 단위 일치 검증 (`accounting_delta == 0`).
   - 현금 잔고 음수 미발생 검증 (`cash_balance >= 0`).
   - 실제 삼성전자 Parquet 데이터 연동 1,000스텝 이상 시뮬레이션 완주 검증.
3. **적대적 경계값 테스트 (Adversarial Edge Cases)**:
   - 잔고 0원 상태에서 매수 시도.
   - 보유 수량 0주 상태에서 매도 시도.
   - 수량 1주, 가격 1원 등 초미세 주문 시 수수료/세금 절사 처리 검증.
   - 단일 종목 전량 매도 후 평단가 및 수량 정상 0 리셋 검증.
