# Auto_Stock Phase 5: RL 엔진 탐색 및 실시간 스크리너 연동 인터페이스 설계 보고서

- **작성자**: RL Engine Explorer (teamwork_preview_explorer_survey_p5_2)
- **대상 모듈**: `modules/engine/live_learning_simulator.py`, `modules/engine/hybrid_trading_env.py`, `modules/models/`, `modules/data/streamer.py`
- **목적**: Phase 5 Dynamic Stock Screener의 장중 모멘텀 돌파 트리거(R2) 및 RL 에이전트 동적 주입/실행 파이프라인(R4) 아키텍처 설계
- **작성 일시**: 2026-09-03 (KST)

---

## 1. 개요 및 조사 배경

Phase 5 다이내믹 종목 스크리너(Dynamic Stock Screener)의 핵심 목표는 수천 개의 종목 중 펀더멘털 기준(시총 1,000억 이상, PER/PBR, 수급)을 만족하는 종목으로 정적 감시 풀(Static Daily Pool)을 구성하고, 장중 실시간 틱(Tick) 스트림에서 거래량 300% 폭증 및 시가 대비 3% 급등이 발생하는 모멘텀 돌파(Momentum Breakout) 종목을 포착하여, 강화학습(RL) 트레이딩 에이전트의 관측/행동 루프로 즉시 주입·실행하는 것입니다.

본 조사는 `LiveLearningSimulator`를 중심으로 한 강화학습 엔진의 현재 구조와 제약점을 분석하고, R2(틱 데이터 규격 및 트리거 로직)와 R4(동적 주입 인터페이스 및 시뮬레이터 개선안)의 구체적인 명세를 도출하여 구현 담당 Worker 및 리뷰어/감사자에게 무결한 설계 청사진을 제공합니다.

---

## 2. 기존 트레이딩 엔진 및 모델 아키텍처 심층 분석

### 2.1. `LiveLearningSimulator` (`modules/engine/live_learning_simulator.py`)
- **역할**: Kiwoom REST API 연동 실시간 시세 기반 가상 체결 시뮬레이터 (Paper Trading).
- **핵심 컴포넌트**:
  - `account`: `VirtualAccount` (현금 잔고, 종목별 포지션 및 이동평균 평단가 관리).
  - `engine`: `MockExecutionEngine` (위탁수수료 0.015%, 증권거래세 0.18%, 슬리피지 0.1% 반영 및 1원 단위 정밀 회계 불변식 검증).
  - `api_client`: `KiwoomClient` (실시간 현재가 조회 `get_current_price`).
  - `_SIMULATOR_LOCK` 기반 Double-Checked Locking 스레드 안전 싱글톤 (`get_live_simulator()`, `reset_global_simulator()`).
- **Gymnasium 1.2.0 인터페이스**:
  - `step(symbol, action, quantity=1) -> Tuple[state_dict, reward, terminated, truncated, info_dict]`
  - 보상: Log Equity Return $r_t = \ln(E_t / E_{t-1})$.
  - 파산 판정: 총 평가금이 초기 자본금의 5% 미만 하락 시 `terminated = True`.

### 2.2. `HybridTradingEnv` (`modules/engine/hybrid_trading_env.py`)
- **역할**: Gymnasium 1.2.0 표준 규격의 하이브리드 액션 공간 강화학습 환경.
- **액션 공간 (Action Space)**:
  - `Tuple(Discrete(3), Box(0.0, 1.0, shape=(1,)))`: 0 (HOLD), 1 (BUY), 2 (SELL) 및 포지션 주문 비중 ($w \in [0.0, 1.0]$).
  - `Dict({"action_type": Discrete(3), "position_size": Box(1)})` 모드 지원.
- **관측 공간 (Observation Space)**:
  - 14차원 정규화된 `Box(shape=(14,), dtype=np.float32)` 벡터:
    - **10개 시장 피처**: `returns_1d`, `volatility_20d`, `log_return`, `ma_5 dev`, `ma_20 dev`, `ma_60 dev`, `dynamic_per`, `dynamic_pbr`, `dynamic_market_cap`, `volume`.
    - **4개 계좌 상태 피처**: `cash_ratio`, `position_ratio`, `unrealized_pnl_ratio`, `step_progress`.
- **듀얼 모드**:
  - `mode="offline"`: Parquet/DataFrame 기반 고속 백테스트/학습.
  - `mode="live"`: `LiveLearningSimulator` 연동 실시간 모의 훈련.

### 2.3. 강화학습 모델 파이프라인 (`modules/models/`)
- **`DualStreamSLFeatureExtractor` (`modules/models/feature_extractor.py`)**:
  - 1D-CNN 시계열 스트림(국소 가격/수익률 패턴)과 MLP 정적 스트림(펀더멘털/계좌 상태)을 결합하여 고차원 잠재 벡터(64차원) 추출.
- **`HybridActorCritic` / `HybridPPO` (`modules/models/hybrid_policy.py`)**:
  - Discrete Head: Categorical(3) 매매 방향 결정.
  - Continuous Head: Beta($\alpha, \beta$) 또는 Truncated Gaussian 분포 기반 주문 비중 결정.
  - Value Head: 상태 가치 $V(s)$ 추정.

### 2.4. 실시간 시세 스트리머 파이프라인 (`modules/data/streamer.py`)
- **`TickData`**: 실시간 틱 데이터 구조체 (`timestamp`, `symbol`, `price`, `volume`, `accum_volume`, `side`, `bid_price`, `ask_price`, `open_price`, `high_price`, `low_price`).
- **`CircularBuffer`**: 종목별 `deque(maxlen=50,000)` 기반 O(1) 메모리 안전 링 버퍼.
- **`BaseStreamer` / `MockStreamer` / `NaverPollingStreamer`**:
  - 종목 구독(`subscribe(symbol)`), 틱 리스너 콜백 전파(`add_listener`), 원형 버퍼 윈도우 조회(`get_cached_window`).

---

## 3. 현재 `LiveLearningSimulator`의 동작 구조 및 한계점 진단

| 구분 | 현재 구현 상태 | 식별된 문제점 및 한계점 | 개선 방향 |
|---|---|---|---|
| **종목 관리** | `reset()`에서 `symbol="005930"` 하드코딩. `step(symbol)`은 호출자가 단일 종목을 명시해야 함. | 스크리너에서 발굴된 신규 종목을 등록하거나 감시 대상 풀을 관리하는 저장소/큐가 없음. | `active_pool` 딕셔너리 및 `triggered_queue` 도입으로 동적 종목 관리 |
| **이벤트 루프** | 외부에서 `step()`을 호출할 때만 동기식 1회 실행. | 실시간 틱 발생 시 자동 반응하거나 스크리너 트리거 이벤트를 비동기 처리하는 파이프라인 부재. | 스크리너 콜백 연동 및 배치/순차 처리 메서드(`process_triggered_stocks`) 추가 |
| **관측 State 구성** | `get_state()`는 계좌 중심의 9개 키 Dict 반환 (`cash_balance`, `holding_quantity`, `avg_buy_price`, `total_equity` 등). | `HybridTradingEnv` 및 `HybridActorCritic`이 요구하는 **14차원 정규화된 NumPy 배열**과 호환되지 않음. | 14차원 정규화 관측 벡터 생성 메서드(`build_rl_observation`) 구현 |
| **액션/수량 결정** | `step(symbol, action, quantity=1)`로 고정 수량 체결. | RL 에이전트의 출력인 하이브리드 액션 `(action_type, position_weight)`을 반영하지 못함. | 포지션 비중($w$) 기반 가용 현금/주수 자동 사이징 로직 내장 |
| **보상 및 에쿼티 계산** | `curr_equity = self.account.get_total_equity({symbol: current_price})` | 다중 종목 포지션을 보유한 상태에서 특정 종목을 스텝할 때 다른 종목의 최신 시세가 누락되어 평단가로 평가됨 (에쿼티 왜곡). | `self.engine._last_market_prices` 전체를 전달하여 포트폴리오 전체 Total Equity 정밀 평가 |

---

## 4. R2 요구사항: 실시간 틱 데이터 포맷 및 모멘텀 돌파 트리거 설계

### 4.1. 실시간 틱 데이터 포맷 규격
스크리너의 `check_intraday_trigger`는 `TickData` 객체 또는 표준 `Dict[str, Any]`를 유연하게 수용해야 합니다.

```python
# 표준 틱 데이터 포맷 명세
{
    "symbol": "005930",                     # 종목코드 (6자리 문자열, 필수)
    "timestamp": datetime.now(),            # 틱 발생 일시 (datetime, 필수)
    "price": 72500.0,                       # 현재 체결가 (float/Decimal, 필수)
    "open_price": 70000.0,                  # 당일 시가 (float/Decimal, 필수)
    "volume": 15000,                        # 이번 틱 체결량 (int)
    "accum_volume": 1200000,                # 당일 누적 거래량 (int, 필수)
    "prev_same_time_volume": 350000,        # 전일 동시간대 누적 거래량 (int, 선택적)
    "high_price": 72800.0,                  # 당일 고가 (선택)
    "low_price": 69800.0,                   # 당일 저가 (선택)
}
```

### 4.2. 모멘텀 돌파(Momentum Breakout) 트리거 판정 알고리즘
트리거 조건은 다음 4가지 검증 단계를 모두 통과해야 합니다:

1. **감시 풀 적격성 검증 (Candidate Pool Membership)**:
   - 해당 종목이 R1에서 추출된 정적 감시 풀(`self.candidate_pool`)에 포함되어 있는지 확인. 미포함 시 즉시 무시 (`None`).
2. **시가 대비 3% 급등 검증 (Price Surge $\ge 3.0\%$)**:
   $$	ext{price\_surge\_ratio} = rac{	ext{price} - 	ext{open\_price}}{	ext{open\_price}}$$
   $$	ext{price\_surge\_ratio} \ge 0.03 \quad (3.0\%)$$
   - 방어 로직: `open_price <= 0`이거나 결측인 경우 `False`.
3. **거래량 300% 폭증 검증 (Volume Surge $\ge 300\%$)**:
   - 기준 A (전일 동시간대 누적 거래량 대비):
     $$	ext{accum\_volume} \ge 	ext{prev\_same\_time\_volume} 	imes 3.0$$
   - 기준 B (기준 프로파일 캐시 또는 전달된 파라미터):
     스크리너가 관리하는 `self.volume_profiles[symbol][hhmm]` 또는 인자로 전달된 `prev_same_time_volume` 활용.
   - 방어 로직: 기준 거래량이 0 이하이거나 결측일 경우, 최소 거래량 임계치(`min_volume_threshold`, 예: 50,000주) 및 직전 5분 평균 대비 폭증 여부로 대체 검증.
4. **채터링 방지 및 쿨다운 (Trigger Cooldown / Debounce)**:
   - 고빈도 틱 환경에서 동일 종목의 연속 중복 트리거로 인한 RL 엔진 과부하를 방지.
   - `self._triggered_history: Dict[str, datetime]`을 관리하여 최소 쿨다운 시간(예: 300초 = 5분) 내 재트리거 차단.
   - 또는 1일 1회 트리거 모드(`trigger_once_per_day=True`) 지원.

### 4.3. `check_intraday_trigger` 권장 시그니처
```python
def check_intraday_trigger(
    self,
    tick: Union[TickData, Dict[str, Any]],
    prev_same_time_volume: Optional[int] = None,
    price_surge_threshold: float = 0.03,      # 3%
    volume_surge_ratio: float = 3.0,          # 300% (3배)
    min_volume_threshold: int = 10_000,
) -> Optional[str]:
    """
    실시간 틱 데이터를 검사하여 모멘텀 돌파 조건 충족 시 해당 종목코드(str) 반환.
    조건 미충족 또는 쿨다운 중일 경우 None 반환.
    """
```

---

## 5. R4 요구사항: RL 엔진 동적 주입 및 실행 루프 연동 인터페이스 설계

### 5.1. 시스템 연동 아키텍처 다이어그램

```
┌────────────────────────────────────────────────────────┐
│  DynamicStockScreener (modules/data/screener.py)       │
│  - R1: update_daily_static_pool(...)                   │
│  - R2: check_intraday_trigger(tick) ──> [Triggered!]   │
└───────────────────────────┬────────────────────────────┘
                            │
              inject_triggered_symbol(symbol, tick_data)
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  LiveLearningSimulator (modules/engine/live_learning_simulator.py) │
│  - Active Watchlist: self.active_pool[symbol]          │
│  - Trigger Queue: self.triggered_queue.put(symbol)     │
│  - Market Price Sync: engine.update_market_price(...)  │
│  - 14-dim Obs Builder: build_rl_observation(symbol)    │
│  - Portfolio Total Equity: get_total_equity(all_prices)│
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│  RL Agent Policy / HybridTradingEnv                    │
│  - obs = sim.build_rl_observation(symbol)              │
│  - action, weight = policy.sample_action(obs)          │
│  - sim.step_symbol(symbol, action, weight)             │
│  - VirtualAccount Order Execution & PnL Logging        │
└────────────────────────────────────────────────────────┘
```

### 5.2. `LiveLearningSimulator` 수정 및 신규 메서드 상세 설계

#### (1) 신규 속성 추가 (`__init__`)
```python
self.active_pool: Dict[str, Dict[str, Any]] = {}   # 활성화된 종목 메타데이터
self.triggered_queue: queue.Queue = queue.Queue()  # 트리거된 종목 대기 큐
self.streamer: Optional[BaseStreamer] = None       # 실시간 시세 스트리머 참조
```

#### (2) 종목 주입 인터페이스: `inject_triggered_symbol`
```python
def inject_triggered_symbol(
    self,
    symbol: str,
    trigger_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    스크리너에서 모멘텀 돌파로 포착된 종목을 시뮬레이터 활성 풀 및 대기 큐로 동적 주입.
    
    Args:
        symbol: 종목코드 (예: "000660")
        trigger_data: 트리거 발생 시점의 시세, 거래량, 시각 정보
    Returns:
        bool: 정상 주입 성공 여부
    """
    clean_sym = str(symbol).strip().zfill(6) if str(symbol).isdigit() else str(symbol).strip()
    
    with self._lock:
        now = datetime.now()
        data = trigger_data or {}
        
        self.active_pool[clean_sym] = {
            "injected_at": now,
            "trigger_data": data,
            "status": "ACTIVE",
        }
        self.triggered_queue.put(clean_sym)
        
        # 스트리머가 연결되어 있다면 해당 종목 실시간 시세 구독 추가
        if self.streamer is not None:
            self.streamer.subscribe(clean_sym)
            
        # 트리거 가격이 있으면 시장가 즉시 갱신
        if "price" in data:
            self.engine.update_market_price(clean_sym, to_decimal(data["price"]))
            
        logger.info(f"종목 동적 주입 완료: {clean_sym} (현재 활성 풀: {len(self.active_pool)}개)")
        return True
```

#### (3) 14차원 RL 관측 벡터 생성기: `build_rl_observation`
`HybridTradingEnv`의 14차원 규격(10 Market + 4 Account)과 완벽히 호환되는 정규화 벡터 산출:
```python
def build_rl_observation(
    self,
    symbol: str,
    market_features: Optional[Union[List[float], np.ndarray]] = None,
) -> np.ndarray:
    """
    지정 종목에 대한 Gymnasium 1.2.0 호환 14차원 정규화 관측 벡터(obs) 생성.
    - 10개 시장 피처: 인자로 전달받거나 캐시된 틱/분봉 데이터에서 계산
    - 4개 계좌 피처: cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress
    """
    current_price = self.engine._last_market_prices.get(symbol, Decimal("0"))
    if current_price <= 0:
        current_price = self.fetch_live_price(symbol)
        
    # 1. 10개 시장 피처 (없을 경우 기본 모멘텀/변동성 피처 구성)
    if market_features is not None and len(market_features) == 10:
        m_feats = list(market_features)
    else:
        # 링 버퍼 등에서 최근 틱 기반 기본 피처 계산 또는 안전한 기본값
        m_feats = [0.0] * 10
        if symbol in self.active_pool and "trigger_data" in self.active_pool[symbol]:
            t_data = self.active_pool[symbol]["trigger_data"]
            open_p = float(t_data.get("open_price", current_price))
            curr_p = float(current_price)
            ret_from_open = (curr_p - open_p) / open_p if open_p > 0 else 0.0
            m_feats[0] = float(np.clip(ret_from_open, -0.3, 0.3))  # returns_1d proxy
            m_feats[9] = float(t_data.get("volume", 1000)) / 1_000_000.0  # volume norm
            
    # 2. 4개 계좌 상태 피처 (포트폴리오 전체 에쿼티 기준)
    all_prices = dict(self.engine._last_market_prices)
    all_prices[symbol] = current_price
    tot_equity = float(self.account.get_total_equity(all_prices))
    tot_eq_safe = tot_equity if tot_equity > 0 else float(self.initial_cash)
    
    pos = self.account.get_position(symbol)
    pos_val = float(pos.market_value(current_price))
    cash = float(self.account.cash_balance)
    
    cash_ratio = float(np.clip(cash / tot_eq_safe, 0.0, 1.0))
    position_ratio = float(np.clip(pos_val / tot_eq_safe, 0.0, 1.0))
    unrealized_pnl_ratio = float(np.clip(float(pos.return_rate(current_price)), -2.0, 5.0))
    step_progress = 0.5  # 실시간 모의 환경에서는 0.5 또는 타임스탬프 기반 정규화
    
    acc_feats = [cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress]
    full_obs = np.array(m_feats + acc_feats, dtype=np.float32)
    return np.nan_to_num(full_obs, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)
```

#### (4) 다중 종목 및 하이브리드 비중 지원 스텝: `step_symbol`
기존 `step()`의 시그니처와 하위 호환성을 100% 유지하면서, 포지션 비중($w$) 및 전체 포트폴리오 에쿼티 기반 정밀 보상을 지원:
```python
def step_symbol(
    self,
    symbol: str,
    action: Union[int, ActionType],
    quantity: Optional[int] = None,
    position_weight: float = 1.0,
) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
    """
    지정된 종목에 대해 액션을 수행하고, 전체 포트폴리오 에쿼티 기반 5-tuple 반환.
    """
    current_price = self.fetch_live_price(symbol)
    act_val = int(action)
    trade_record = None
    weight = float(np.clip(position_weight, 0.0, 1.0))
    
    slip = self.fee_config.slippage_rate
    comm = self.fee_config.commission_rate
    est_cost_per_share = current_price * (Decimal("1") + slip) * (Decimal("1") + comm)
    
    if act_val == int(ActionType.BUY) and weight > 0.0:
        if quantity is not None:
            exec_qty = quantity
        else:
            budget = self.account.cash_balance * Decimal(str(weight))
            exec_qty = int(budget / est_cost_per_share) if est_cost_per_share > 0 else 0
            
        if exec_qty > 0 and self.account.cash_balance >= (current_price * exec_qty):
            trade_record = self.engine.execute_order(
                symbol=symbol, side=OrderSide.BUY, quantity=exec_qty, current_price=current_price
            )
    elif act_val == int(ActionType.SELL) and weight > 0.0:
        pos = self.account.get_position(symbol)
        if pos.quantity > 0:
            if quantity is not None:
                exec_qty = min(quantity, pos.quantity)
            else:
                exec_qty = int(Decimal(str(pos.quantity)) * Decimal(str(weight)))
                if exec_qty == 0 and weight > 0:
                    exec_qty = 1
            if exec_qty > 0:
                trade_record = self.engine.execute_order(
                    symbol=symbol, side=OrderSide.SELL, quantity=exec_qty, current_price=current_price
                )
                
    # 시장가 업데이트
    self.engine.update_market_price(symbol, current_price)
    
    # [핵심 개선] 전체 보유 종목의 시장가를 모두 반영하여 Total Equity 계산
    all_prices = dict(self.engine._last_market_prices)
    all_prices[symbol] = current_price
    curr_equity = self.account.get_total_equity(all_prices)
    
    if self._prev_equity > 0 and curr_equity > 0:
        reward = float(np.log(float(curr_equity) / float(self._prev_equity)))
    else:
        reward = 0.0
    self._prev_equity = curr_equity
    
    terminated = bool(curr_equity < (self.initial_cash * Decimal("0.05")))
    truncated = False
    
    obs = self.build_rl_observation(symbol)
    info = {
        "symbol": symbol,
        "trade": trade_record,
        "audit": self.engine.get_accounting_audit(all_prices),
        "live_price_used": float(current_price),
        "total_equity": float(curr_equity),
    }
    return obs, reward, terminated, truncated, info
```

#### (5) 대기 큐 배치 처리 편의 메서드: `process_triggered_queue`
```python
def process_triggered_queue(
    self,
    policy_fn: Callable[[np.ndarray], Tuple[int, float]],
) -> List[Dict[str, Any]]:
    """
    대기 큐에 쌓인 모든 트리거 종목에 대해 RL 에이전트 정책을 적용하여 순차 매매 수행.
    """
    results = []
    while not self.triggered_queue.empty():
        symbol = self.triggered_queue.get_nowait()
        obs = self.build_rl_observation(symbol)
        act_type, weight = policy_fn(obs)
        obs, reward, term, trunc, info = self.step_symbol(symbol, act_type, position_weight=weight)
        results.append({"symbol": symbol, "action": act_type, "weight": weight, "info": info})
    return results
```

---

## 6. 결론 및 다운스트림 작업자(Worker) 가이드라인

1. **하위 호환성 100% 보장**:
   기존 `LiveLearningSimulator.step(symbol, action, quantity=1)` 및 `get_state(symbol)` 메서드는 기존 테스트(`test_live_learning_simulator.py`, `test_hybrid_trading_env.py`)가 의존하므로 시그니처와 반환값을 변경하지 않고 그대로 유지하거나 내부에서 `step_symbol`을 위임 호출하도록 구현해야 합니다.
2. **`screener.py` 연동 표준화**:
   `screener.py`는 `LiveLearningSimulator` 인스턴스를 주입받거나, `get_live_simulator()` 싱글톤을 활용하여 트리거 발생 시 `inject_triggered_symbol(symbol, trigger_data)`를 호출하도록 설계하면 두 모듈 간 결합도를 최소화하면서도 즉각적인 이벤트 전파가 가능합니다.
3. **회계 불변식 및 에쿼티 무결성**:
   다중 종목 매매 시 `get_total_equity`에 반드시 전체 시장가 딕셔너리(`self.engine._last_market_prices`)를 전달하여 1원의 오차 없는 회계 무결성을 유지해야 합니다.
