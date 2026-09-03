# Simulator & Data Pipeline Survey Handoff Report

## 1. Observation (직접 관찰 결과)

### 1.1 LiveLearningSimulator 클래스 분석
- **파일 경로**: `/home/imnyj/Workspace/Auto_Stock/modules/engine/live_learning_simulator.py` (Lines 27–169)
- **클래스 정의 및 시그니처**:
  ```python
  class LiveLearningSimulator:
      def __init__(self, initial_cash: Union[int, Decimal] = 10_000_000, fee_config: Optional[FeeConfig] = None):
          self.initial_cash = to_decimal(initial_cash)
          self.account = VirtualAccount(initial_cash=self.initial_cash)
          self.fee_config = fee_config or FeeConfig()
          self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)
          self.api_client = KiwoomClient()
          self._prev_equity = self.initial_cash

      def reset(self, initial_cash: Optional[Union[int, Decimal]] = None) -> Dict[str, Any]: ...
      def fetch_live_price(self, symbol: str) -> Decimal: ...
      def step(self, symbol: str, action: Union[int, ActionType], quantity: int = 1) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]: ...
      def get_state(self, symbol: str, current_price: Optional[Decimal] = None) -> Dict[str, Any]: ...
  ```
- **상태 관리 및 데이터 구조**:
  - `get_state()` 반환 딕셔너리:
    - `symbol`: 종목코드 (str)
    - `current_price`: 현재가 (float)
    - `cash_balance`: 현금 잔고 (float)
    - `holding_quantity`: 보유 수량 (int)
    - `avg_buy_price`: 평균 매입 단가 (float)
    - `total_equity`: 총 평가금액 (float)
    - `realized_pnl`: 실현 손익 (float)
    - `unrealized_pnl`: 미실현 손익 (float)
    - `cumulative_frictions`: 누적 마찰비용(수수료+세금+슬리피지) (float)
- **글로벌 싱글톤 함수**: `get_live_simulator(initial_cash=10_000_000)` (Lines 163–168).

### 1.2 가상 체결 엔진 및 회계 무결성 계층
- **파일 경로**: `/home/imnyj/Workspace/Auto_Stock/modules/engine/mock_environment.py` (Lines 1–1346)
- **주요 구성**:
  1. `VirtualAccount` (Lines 224–509):
     - `Decimal` 기반 1원 단위 엄격한 회계 (`ROUND_FLOOR`, `ROUND_HALF_UP`).
     - 이동평균법(Moving Average Method) 매입 평단가 갱신.
     - `can_buy()`, `can_sell()`, `apply_buy()`, `apply_sell()`, `get_total_equity()`, `get_snapshot()`, `reset()`.
  2. `MockExecutionEngine` (Lines 514–885):
     - 한국 주식 시장 거래비용 모델: 위탁수수료 0.015% (`FeeConfig.commission_rate`), 증권거래세 0.18% (`FeeConfig.tax_rate`, 매도시만), 슬리피지 0.1% (`FeeConfig.slippage_rate`).
     - `execute_order(symbol, side, quantity, current_price, order_type, limit_price)`: 잔고/수량 사전 검증 및 안전 거절(`TradeRecord.is_success=False`).
     - `verify_accounting_invariant()`: 0원 오차 회계 무결성 불변식 검증 기능 내장.
  3. `MockEnvironment` (Lines 1125–1346):
     - 시계열 `pd.DataFrame` / `Iterable` 스트림을 수신하여 `reset()`, `step(action)`, `get_state()`를 제공하는 Facade 환경.

### 1.3 데이터 파이프라인 및 저장 포맷
- **파일 경로**:
  - `modules/data/pipeline.py` (Lines 1–242)
  - `modules/data/consolidator.py` (Lines 1–322)
  - `data/raw/*.parquet`
- **데이터 파이프라인 흐름**:
  - `FundamentalDataCollector` + `PriceDataCollector` -> `DataConsolidator.consolidate_point_in_time()` -> `DataConsolidator.save_to_parquet()`
  - DART 공시일(`announcement_date`) 기준 `pd.merge_asof(direction='backward')`를 통해 Look-ahead bias 원천 차단.
- **실제 저장된 데이터셋 현황 (`data/raw/`)**:
  - `005930_consolidated.parquet` (삼성전자 100행 × 40컬럼)
  - `000660_consolidated.parquet` (SK하이닉스)
  - `005380_consolidated.parquet` (현대차)
- **피처 목록 (40개 컬럼)**:
  - 가격 시계열: `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, `value`, `timeframe`, `adj_factor`, `is_trading_halt`
  - 펀더멘털 지표: `period_end`, `announcement_date`, `revenue`, `operating_income`, `net_income`, `assets`, `liabilities`, `equity`, `per`, `pbr`, `roe`, `eps`, `bps`, `div_yield`, `is_consensus`, `source`, `validation_status`
  - 동적 파생 피처: `dynamic_per`, `dynamic_pbr`, `dynamic_market_cap`
  - 기술적 지표: `returns_1d`, `return_1d`, `volatility_20d`, `log_return`, `ma_5`, `ma_20`, `ma_60`
  - 검증 플래그: `is_cross_verified`, `warning_flags`

### 1.4 실행 환경 및 라이브러리 버전
- Python 3.12 (가상환경: `/home/imnyj/venv`)
- `gymnasium`: **1.2.0**
- `stable-baselines3`: **2.7.0**
- `torch`: **2.11.0+cu130**
- `optuna`: **4.8.0**
- `pyarrow`: 설치 완료, ZSTD Parquet 고속 I/O 지원
- 엔진 단위 테스트(`tests/test_live_learning_simulator.py`, `tests/test_phase2.py`, `tests/test_consolidator.py`): **84 passed in 2.08s (100% 통과)**

---

## 2. Logic Chain (추론 체인)

1. **[Observation 1.1 + 1.2 기반]**
   - `LiveLearningSimulator`는 `VirtualAccount`와 `MockExecutionEngine`을 활용하여 실시간 Kiwoom API 주가에 기반한 Paper Trading을 수행합니다.
   - 하지만 실시간 API 호출(`fetch_live_price`)은 장 마감 시간(주말/야간) 및 네트워크 API 지연(레이턴시)에 종속되어 오프라인 강화학습(RL) 대량 에피소드 및 Optuna HPO(수백~수천 회 Trial)를 고속으로 수행하기 어렵습니다.

2. **[Observation 1.2 + 1.3 기반]**
   - `MockEnvironment` 및 `DataConsolidator`를 통해 이미 고품질의 Look-ahead bias 없는 40개 컬럼 시계열 Parquet 데이터셋(`data/raw/*.parquet`)이 준비되어 있습니다.
   - 따라서 새로운 Gymnasium 환경(`HybridTradingEnv`)은 내부 체결 및 회계 코어(`VirtualAccount`, `MockExecutionEngine`)를 공유하면서, **오프라인 Parquet 데이터 기반 고속 훈련 모드(`mode="offline"`)**와 **실시간 Kiwoom 연동 모드(`mode="live"`)**를 모두 지원하는 듀얼 백엔드 구조로 설계하는 것이 가장 적합합니다.

3. **[요구사항 R1 Action Space 설계 추론]**
   - 사용자 요구사항: 이산형(0: HOLD, 1: BUY, 2: SELL)과 연속형 비중(0.0 ~ 1.0)이 결합된 하이브리드 Action Space.
   - Gymnasium 1.2.0 표준:
     `spaces.Tuple((spaces.Discrete(3), spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)))` 혹은 `spaces.Dict({"action_type": spaces.Discrete(3), "weight": spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)})`.
   - 체결 수량 환산 논리:
     - BUY: `max_buy_qty = int(cash_balance / (price * (1 + commission + slippage)))`, `order_qty = int(max_buy_qty * weight)`
     - SELL: `order_qty = int(holding_qty * weight)`
     - HOLD: `order_qty = 0`
     - 만약 `order_qty <= 0`인 경우 안전하게 No-op(관망) 처리.

4. **[Observation Space 및 정규화 추론]**
   - 머신러닝/강화학습(SL-RL) 모델 입력의 안정성을 위해 원시 가격(수만 원) 대신 정규화된 스케일의 지표들을 관측 벡터로 결합:
     - 시장 피처 ($k$개): `log_return`, `volatility_20d`, `(close - ma_5)/ma_5`, `(close - ma_20)/ma_20`, `(close - ma_60)/ma_60`, `dynamic_per_norm`, `dynamic_pbr_norm`
     - 계좌 피처 ($m$개): `cash_ratio` ($Cash/Equity$), `position_ratio` ($HoldingsVal/Equity$), `unrealized_pnl_ratio` ($(Price-AvgPrice)/AvgPrice$), `step_progress` ($t/T$)
   - 최종 관측 공간: `spaces.Box(low=-np.inf, high=np.inf, shape=(feature_dim,), dtype=np.float32)` (윈도우 적용 시 `shape=(window_size, feature_dim)`).

5. **[Reward 함수 및 에피소드 종료 조건 추론]**
   - Step 단위 보상: 포트폴리오 에쿼티의 로그 수익률 $\ln(\text{Equity}_t / \text{Equity}_{t-1})$에 마찰비용 페널티를 결합.
   - `terminated`: 파산 조건 ($\text{Equity}_t < 0.05 \times \text{InitialCash}$).
   - `truncated`: 시계열 데이터 종료 시점 ($t \ge T$).

---

## 3. Caveats (주의사항 및 한계점)

1. **실시간 API 호출 경계 조건 (Live Mode)**:
   - `LiveLearningSimulator.fetch_live_price()`는 장외 시간이나 키움 API 미접속 시 HTTP 401/Network 에러를 발생시킬 수 있으므로, 오프라인 시뮬레이션 환경에서는 Parquet 데이터셋 기반 모드가 기본이어야 합니다.
2. **소수점 비중 매매 양자화 (Fractional Order Handling)**:
   - 연속형 비중 $w \in [0, 1]$ 적용 시 소수점 수량은 한국 주식 시장 특성에 맞추어 `int(floor(...))`로 정수 1주 단위로 절사되어야 하며, 잔고 부족으로 0주가 계산되는 경우 에러를 내지 않고 안전하게 거절(No-op)되어야 합니다.
3. **결측치(NaN/NaT) 및 무한대(Inf) 방어**:
   - 펀더멘털 공시 전 기간(`PRE_ANNOUNCEMENT_PERIOD`)이나 적자 기업의 `dynamic_per`는 `np.nan`이 될 수 있으므로, 피처 추출 단계에서 `fillna(0.0)` 또는 클리핑(`np.clip`) 처리가 필수적입니다.

---

## 4. Conclusion (결론 및 제안)

### 4.1 제안 클래스: `HybridTradingEnv` (Gymnasium 1.2.0 호환)
`modules/engine/hybrid_trading_env.py`에 구현할 표준 인터페이스 구조는 다음과 같습니다:

```python
"""
modules/engine/hybrid_trading_env.py
Gymnasium 1.2.0 호환 하이브리드 액션 공간 트레이딩 환경
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional, Union
from decimal import Decimal

from modules.engine.mock_environment import (
    VirtualAccount, MockExecutionEngine, FeeConfig, OrderSide, to_decimal
)
from modules.engine.live_learning_simulator import LiveLearningSimulator

class HybridTradingEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        initial_cash: float = 10_000_000.0,
        symbol: str = "005930",
        fee_config: Optional[FeeConfig] = None,
        window_size: int = 20,
        mode: str = "offline",  # "offline" or "live"
        live_sim: Optional[LiveLearningSimulator] = None
    ):
        super().__init__()
        self.mode = mode
        self.symbol = symbol
        self.initial_cash = initial_cash
        self.fee_config = fee_config or FeeConfig()
        self.window_size = window_size
        
        # 1. Action Space 정의 (Hybrid: Discrete(3) + Box(1,))
        # Tuple: (ActionType: 0=HOLD, 1=BUY, 2=SELL, Weight: 0.0~1.0)
        self.action_space = spaces.Tuple((
            spaces.Discrete(3),
            spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)
        ))
        
        # 2. Observation Space 정의
        # [피처 예시: log_return, volatility_20d, ma_dev_5, ma_dev_20, ma_dev_60, dynamic_per, dynamic_pbr, cash_ratio, holding_ratio, unrealized_pnl_ratio, step_progress]
        self.feature_cols = [
            "log_return", "volatility_20d", "returns_1d",
            "dynamic_per", "dynamic_pbr", "dynamic_market_cap"
        ]
        self.num_market_features = len(self.feature_cols) + 3 # + 3 ma deviations
        self.num_account_features = 4
        self.obs_dim = self.num_market_features + self.num_account_features
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.obs_dim,), dtype=np.float32
        )
        
        # 엔진 및 상태 초기화
        self.account = VirtualAccount(initial_cash=self.initial_cash)
        self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)
        self.live_sim = live_sim
        self.df = df
        self._current_step = 0
        self._prev_equity = Decimal(str(initial_cash))

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.account.reset(initial_cash=self.initial_cash)
        self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)
        self._current_step = self.window_size
        self._prev_equity = Decimal(str(self.initial_cash))
        
        obs = self._get_observation()
        info = self._get_info()
        return obs, info

    def step(self, action: Tuple[int, Union[float, np.ndarray]]) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        act_type = int(action[0])
        weight = float(action[1][0] if isinstance(action[1], (list, np.ndarray)) else action[1])
        weight = np.clip(weight, 0.0, 1.0)
        
        current_price = self._get_current_price()
        trade_record = None
        
        # 하이브리드 주문 실행
        if act_type == 1 and weight > 0:  # BUY
            slip = self.fee_config.slippage_rate
            comm = self.fee_config.commission_rate
            est_cost_per_share = current_price * (Decimal("1") + slip) * (Decimal("1") + comm)
            max_buy_qty = int(self.account.cash_balance / est_cost_per_share)
            target_qty = int(max_buy_qty * weight)
            if target_qty > 0:
                trade_record = self.engine.execute_order(
                    symbol=self.symbol, side=OrderSide.BUY, quantity=target_qty, current_price=current_price
                )
        elif act_type == 2 and weight > 0:  # SELL
            pos = self.account.get_position(self.symbol)
            target_qty = int(pos.quantity * weight)
            if target_qty > 0:
                trade_record = self.engine.execute_order(
                    symbol=self.symbol, side=OrderSide.SELL, quantity=target_qty, current_price=current_price
                )
                
        self.engine.update_market_price(self.symbol, current_price)
        
        # 보상 계산 (Log Return)
        curr_equity = self.account.get_total_equity({self.symbol: current_price})
        reward = float(np.log(float(curr_equity) / float(self._prev_equity))) if self._prev_equity > 0 and curr_equity > 0 else 0.0
        self._prev_equity = curr_equity
        
        # 다음 스텝 이동
        self._current_step += 1
        terminated = bool(curr_equity < (Decimal(str(self.initial_cash)) * Decimal("0.05"))) # 95% 손실 파산
        truncated = bool(self._current_step >= len(self.df) - 1) if self.df is not None else False
        
        obs = self._get_observation()
        info = self._get_info(trade_record=trade_record)
        return obs, reward, terminated, truncated, info
```

### 4.2 SL & RL 베이스라인 및 HPO 파이프라인 연계 방안
- **SL 특징 추출기 (MLP / 1D-CNN)**:
  - `data/raw/*.parquet`로부터 시계열 피처를 슬라이딩 윈도우로 추출하여 다음 날 수익률 방향(Up/Down/Neutral)을 예측하는 지도학습 모델 사전 학습.
- **RL 에이전트 (Stable-Baselines3 PPO 또는 PyTorch Actor-Critic)**:
  - `HybridTradingEnv`의 `action_space`를 활용하여 정책 신경망(Policy Network)이 Action Logits(3개)와 Beta/Gaussian Continuous Weight를 동시에 출력하는 구조.
- **Optuna HPO 연계**:
  - 목적 함수(Objective): `n_trials` 동안 학습률(`lr`), `batch_size`, `gamma`, `net_arch` 등을 탐색하여 검증 데이터셋 에피소드 종료 시의 `total_equity` 및 `Sharpe Ratio`를 최대화.
  - 결과 저장: `etc/hpo_results/baseline_hpo.csv`에 `trial.number`, `params`, `final_equity`, `sharpe_ratio`, `pnl_rate` 저장.

---

## 5. Verification Method (독립적 검증 방법)

### 5.1 검증 명령어
```bash
# 1. 가상환경 활성화 및 기존 테스트 통과 확인
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/Auto_Stock/tests/test_live_learning_simulator.py /home/imnyj/Workspace/Auto_Stock/tests/test_phase2.py /home/imnyj/Workspace/Auto_Stock/tests/test_consolidator.py -v

# 2. Gymnasium 및 데이터셋 무결성 확인
/home/imnyj/venv/bin/python -c "
import gymnasium as gym
import pandas as pd
df = pd.read_parquet('/home/imnyj/Workspace/Auto_Stock/data/raw/005930_consolidated.parquet')
print('Parquet Loaded:', df.shape)
"
```

### 5.2 신규 환경 유효성 판정 기준 (Invalidation Conditions)
- `action_space`가 `spaces.Tuple` 혹은 `spaces.Dict` 형태의 하이브리드 공간(Discrete + Box)이 아닐 경우 실패.
- `step()` 실행 시 5개 튜플 `(obs, reward, terminated, truncated, info)`가 Gymnasium 1.x 표준 규격과 불일치할 경우 실패.
- `VirtualAccount`의 `verify_accounting_invariant()` 검증 시 1원 이상의 회계 오차가 발생할 경우 실패.
