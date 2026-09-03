"""
modules/engine/hybrid_trading_env.py
====================================
Gymnasium 1.2.0 호환 하이브리드 액션 공간(Tuple/Dict: Discrete + Box) 트레이딩 환경.

주요 특징:
1. Gymnasium 1.2.0 표준 인터페이스 준수:
   - reset(seed=seed, options=options) -> (obs, info)
   - step(action) -> (obs, reward, terminated, truncated, info)
2. 하이브리드 액션 공간 (Hybrid Action Space):
   - Discrete(3): 0 (HOLD), 1 (BUY), 2 (SELL)
   - Box(0.0 ~ 1.0, shape=(1,)): 포지션 비중 (Order weight / position sizing)
   - spaces.Tuple, spaces.Dict 및 2D Continuous Box 모두 유연하게 처리 가능한 디코더 지원
3. 정밀 가상 체결 및 회계 무결성 (1원 오차 0원 검증):
   - VirtualAccount & MockExecutionEngine 연동
   - 위탁수수료 0.015%, 증권거래세 0.18%(매도시), 고정 슬리피지 0.1% 반영
4. 정규화된 관측 공간 (Observation Space):
   - 10개 시장/기술적/밸류에이션 피처 + 4개 계좌 상태 피처 (cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress) = 14차원
5. 듀얼 모드 지원:
   - mode="offline": Parquet / DataFrame 시계열 스트림 기반 고속 백테스트 및 RL/SL 학습
   - mode="live": Kiwoom REST API / LiveLearningSimulator 연동 실시간 Paper Trading
"""

import logging
import math
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces
from gymnasium.utils import RecordConstructorArgs

from modules.engine.live_learning_simulator import LiveLearningSimulator
from modules.engine.mock_environment import (
    ActionType,
    FeeConfig,
    MockExecutionEngine,
    OrderSide,
    TradeRecord,
    VirtualAccount,
    quantize_krw,
    to_decimal,
)

logger = logging.getLogger("AutoStock.HybridTradingEnv")


class HybridTradingEnv(gym.Env):
    """
    Gymnasium 1.2.0 호환 하이브리드 액션 공간 트레이딩 환경 클래스.
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 30}

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        data_path: Optional[str] = None,
        initial_cash: Union[Decimal, int, float, str] = 10_000_000,
        symbol: str = "005930",
        fee_config: Optional[FeeConfig] = None,
        window_size: int = 1,
        mode: str = "offline",  # "offline" or "live"
        live_sim: Optional[LiveLearningSimulator] = None,
        action_space_type: str = "tuple",  # "tuple" or "dict"
        bankruptcy_threshold_ratio: float = 0.05,
        max_steps: Optional[int] = None,
        feature_cols: Optional[List[str]] = None,
        render_mode: Optional[str] = None,
    ):
        super().__init__()

        self.mode = mode.lower()
        if self.mode not in ("offline", "live"):
            raise ValueError(f"지원하지 않는 모드입니다: {mode}. 'offline' 또는 'live'여야 합니다.")

        self.symbol = symbol
        self.initial_cash = to_decimal(initial_cash)
        self.fee_config = fee_config or FeeConfig()
        self.window_size = max(1, int(window_size))
        self.action_space_type = action_space_type.lower()
        self.bankruptcy_threshold_ratio = float(bankruptcy_threshold_ratio)
        self._custom_max_steps = max_steps
        self.feature_cols = feature_cols
        self.render_mode = render_mode

        # Spec 설정 (Gymnasium env_checker 등록 및 재생성 호환)
        self.spec = gym.envs.registration.EnvSpec(
            id="HybridTradingEnv-v0",
            entry_point="modules.engine.hybrid_trading_env:HybridTradingEnv",
            nondeterministic=True,
        )

        # 1. Action Space 정의 (Hybrid: Discrete(3) + Box(0.0~1.0, shape=(1,)))
        self._tuple_action_space = spaces.Tuple((
            spaces.Discrete(3),  # 0: HOLD, 1: BUY, 2: SELL
            spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32),
        ))
        self._dict_action_space = spaces.Dict({
            "action_type": spaces.Discrete(3),
            "position_size": spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32),
        })

        if self.action_space_type == "dict":
            self.action_space = self._dict_action_space
        else:
            self.action_space = self._tuple_action_space

        # 2. Observation Space 정의 (10 Market Features + 4 Account Features = 14 dims)
        self.num_market_features = 10 if self.feature_cols is None else len(self.feature_cols)
        self.num_account_features = 4
        self.obs_dim = self.num_market_features + self.num_account_features

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.obs_dim,),
            dtype=np.float32,
        )

        # 3. 가상 체결 엔진 및 계좌 초기화
        self.account = VirtualAccount(initial_cash=self.initial_cash)
        self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)
        self.live_sim = live_sim

        # 4. 데이터 로드 및 전처리 (offline 모드)
        self.df: Optional[pd.DataFrame] = None
        self._current_step = 0
        self._prev_equity = self.initial_cash
        self._last_trade_record: Optional[TradeRecord] = None
        self._last_price = Decimal("70000")

        if self.mode == "offline":
            self._load_offline_data(df=df, data_path=data_path)
        elif self.mode == "live":
            if self.live_sim is None:
                self.live_sim = LiveLearningSimulator(
                    initial_cash=self.initial_cash, fee_config=self.fee_config
                )
            self.account = self.live_sim.account
            self.engine = self.live_sim.engine
            self._max_steps = self._custom_max_steps if self._custom_max_steps is not None else 1000

    def _load_offline_data(self, df: Optional[pd.DataFrame] = None, data_path: Optional[str] = None) -> None:
        """오프라인 시계열 데이터를 로드하고 캐싱합니다."""
        if df is not None:
            self.df = df.copy().reset_index(drop=True)
        elif data_path is not None and os.path.exists(data_path):
            if data_path.endswith(".parquet"):
                self.df = pd.read_parquet(data_path).reset_index(drop=True)
            else:
                self.df = pd.read_csv(data_path).reset_index(drop=True)
        else:
            default_path = f"/home/imnyj/Workspace/Auto_Stock/data/raw/{self.symbol}_consolidated.parquet"
            if os.path.exists(default_path):
                self.df = pd.read_parquet(default_path).reset_index(drop=True)
            else:
                # 데이터 파일이 없는 경우 자체 합성 시계열 생성 (100일)
                logger.warning(f"데이터셋을 찾을 수 없어 합성 데이터를 생성합니다: {default_path}")
                self.df = self._generate_synthetic_dataframe(length=100)

        # 데이터 유효성 검증
        if len(self.df) == 0:
            raise ValueError("제공된 데이터프레임이 비어있습니다.")

        # 기본 필수 컬럼 보완
        if "close" not in self.df.columns and "price" in self.df.columns:
            self.df["close"] = self.df["price"]
        elif "close" not in self.df.columns:
            self.df["close"] = 70000.0

        if self._custom_max_steps is not None:
            self._max_steps = min(self._custom_max_steps, len(self.df))
        else:
            self._max_steps = len(self.df)

    def _generate_synthetic_dataframe(self, length: int = 100) -> pd.DataFrame:
        """테스트 및 백업용 합성 시계열 데이터프레임을 생성합니다."""
        np.random.seed(42)
        base_price = 70000.0
        returns = np.random.normal(0.0005, 0.015, size=length)
        prices = np.round(base_price * np.cumprod(1.0 + returns))

        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=length, freq="B"),
            "symbol": self.symbol,
            "open": np.round(prices * (1.0 + np.random.normal(0, 0.002, length))),
            "high": np.round(prices * (1.0 + np.abs(np.random.normal(0, 0.005, length)))),
            "low": np.round(prices * (1.0 - np.abs(np.random.normal(0, 0.005, length)))),
            "close": prices,
            "volume": np.random.randint(100000, 1000000, length),
            "returns_1d": returns,
            "log_return": np.log1p(returns),
            "volatility_20d": np.full(length, 0.015),
            "ma_5": pd.Series(prices).rolling(5, min_periods=1).mean().values,
            "ma_20": pd.Series(prices).rolling(20, min_periods=1).mean().values,
            "ma_60": pd.Series(prices).rolling(60, min_periods=1).mean().values,
            "dynamic_per": np.full(length, 15.0),
            "dynamic_pbr": np.full(length, 1.5),
            "dynamic_market_cap": prices * 6_000_000_000.0,
        })
        return df

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Gymnasium 1.2.0 규격 reset 메서드.
        - 계좌 및 체결 엔진을 초기 자본금으로 리셋합니다.
        - Returns: (obs, info)
        """
        super().reset(seed=seed)

        if options and "initial_cash" in options:
            self.initial_cash = to_decimal(options["initial_cash"])

        if self.mode == "offline":
            self.account.reset(initial_cash=self.initial_cash)
            self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)
            self._current_step = 0
            self._prev_equity = self.initial_cash
            self._last_trade_record = None
            if self.df is not None and len(self.df) > 0:
                raw_p0 = self.df.iloc[0].get("close", 70000)
                try:
                    p0_f = float(raw_p0)
                    if math.isnan(p0_f) or math.isinf(p0_f) or p0_f <= 0.0:
                        self._last_price = Decimal("70000")
                    else:
                        self._last_price = quantize_krw(to_decimal(p0_f), rounding=ROUND_HALF_UP)
                except Exception:
                    self._last_price = Decimal("70000")
        elif self.mode == "live":
            if self.live_sim is not None:
                self.live_sim.reset(initial_cash=self.initial_cash)
                self.account = self.live_sim.account
                self.engine = self.live_sim.engine
            else:
                self.account.reset(initial_cash=self.initial_cash)
                self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)
            self._current_step = 0
            self._prev_equity = self.initial_cash
            self._last_trade_record = None
            self._last_price = self._fetch_current_price()

        obs = self._get_observation()
        info = self._get_info()
        return obs, info

    def _fetch_current_price(self) -> Decimal:
        """현재 스텝의 주가를 조회합니다 (NaN/Inf 및 부동소수점 방어)."""
        if self.mode == "offline":
            if self.df is None or len(self.df) == 0:
                return self._last_price
            idx = min(self._current_step, len(self.df) - 1)
            raw_p = self.df.iloc[idx].get("close", None)
            if raw_p is None or pd.isna(raw_p):
                raw_p = self.df.iloc[idx].get("price", None)

            try:
                p_float = float(raw_p)
                if math.isnan(p_float) or math.isinf(p_float) or p_float <= 0.0:
                    p = self._last_price
                else:
                    p = quantize_krw(to_decimal(p_float), rounding=ROUND_HALF_UP)
            except Exception:
                p = self._last_price

            self._last_price = p
            return p
        elif self.mode == "live":
            if self.live_sim is not None:
                try:
                    p = self.live_sim.fetch_live_price(self.symbol)
                    p_float = float(p)
                    if math.isnan(p_float) or math.isinf(p_float) or p_float <= 0.0:
                        p = self._last_price
                    else:
                        p = quantize_krw(to_decimal(p), rounding=ROUND_HALF_UP)
                    self._last_price = p
                    return p
                except Exception as e:
                    logger.warning(f"실시간 시세 조회 실패, 캐시된 가격 사용: {e}")
                    return self._last_price
            return self._last_price
        return Decimal("70000")

    def _parse_action(self, action: Any) -> Tuple[int, float]:
        """
        다양한 형태(Tuple, Dict, ndarray, int 등)의 액션을 (action_type: int, weight: float)로 정규화 파싱합니다.

        - action_type: 0 (HOLD), 1 (BUY), 2 (SELL)
        - weight: 0.0 ~ 1.0
        """
        act_type = 0
        weight = 0.0

        if isinstance(action, tuple) or (
            isinstance(action, (list, np.ndarray))
            and len(action) == 2
            and not isinstance(action[0], (list, np.ndarray, dict))
        ):
            # Tuple: (action_type, weight)
            raw_type = action[0]
            raw_weight = action[1]
            if isinstance(raw_weight, (list, np.ndarray)):
                raw_weight = raw_weight[0] if len(raw_weight) > 0 else 0.0

            # Continuous Box[-1, 1] 변환 케이스 방어
            if (
                isinstance(raw_type, (float, np.floating))
                and -1.0 <= raw_type <= 1.0
                and not isinstance(raw_type, (int, np.integer))
            ):
                if raw_type > 0.333:
                    act_type = 1
                elif raw_type < -0.333:
                    act_type = 2
                else:
                    act_type = 0
            else:
                act_type = int(raw_type)

            weight = float(raw_weight)

        elif isinstance(action, dict):
            # Dict: {"action_type": ..., "position_size" or "weight": ...}
            raw_type = action.get("action_type", 0)
            raw_weight = action.get("position_size", action.get("weight", 0.0))
            if isinstance(raw_weight, (list, np.ndarray)):
                raw_weight = raw_weight[0] if len(raw_weight) > 0 else 0.0
            act_type = int(raw_type)
            weight = float(raw_weight)

        elif isinstance(action, (int, np.integer, ActionType)):
            # Pure discrete action
            act_type = int(action)
            weight = 1.0 if act_type != 0 else 0.0

        elif isinstance(action, (float, np.floating)):
            # Pure continuous action [-1.0, 1.0]
            if action > 0.333:
                act_type = 1
                weight = float(action)
            elif action < -0.333:
                act_type = 2
                weight = float(abs(action))
            else:
                act_type = 0
                weight = 0.0

        # Boundary clipping
        act_type = int(np.clip(act_type, 0, 2))
        weight = float(np.clip(weight, 0.0, 1.0))
        if math.isnan(weight):
            weight = 0.0

        return act_type, weight

    def step(self, action: Any) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Gymnasium 1.2.0 표준 규격 step 메서드.
        - Returns: (obs, reward, terminated, truncated, info)
        """
        act_type, weight = self._parse_action(action)
        current_price = self._fetch_current_price()
        trade_record: Optional[TradeRecord] = None

        # 타임스탬프 추출
        ts = None
        if self.mode == "offline" and self.df is not None and len(self.df) > 0:
            idx = min(self._current_step, len(self.df) - 1)
            raw_date = self.df.iloc[idx].get("date", None)
            if raw_date is not None:
                try:
                    ts = pd.to_datetime(raw_date).to_pydatetime()
                except Exception:
                    ts = None

        # 1. 하이브리드 주문 수량 계산 및 가상 체결
        if act_type == 1 and weight > 0.0:  # BUY
            slip = self.fee_config.slippage_rate
            comm = self.fee_config.commission_rate
            # 1주 매수에 필요한 예상 비용 (슬리피지 상방 + 위탁수수료)
            est_cost_per_share = current_price * (Decimal("1") + slip) * (Decimal("1") + comm)
            if est_cost_per_share > 0:
                available_cash = self.account.cash_balance
                budget = available_cash * Decimal(str(weight))
                target_qty = int(budget / est_cost_per_share)
                if target_qty > 0:
                    trade_record = self.engine.execute_order(
                        symbol=self.symbol,
                        side=OrderSide.BUY,
                        quantity=target_qty,
                        current_price=current_price,
                        timestamp=ts,
                    )
        elif act_type == 2 and weight > 0.0:  # SELL
            pos = self.account.get_position(self.symbol)
            if pos.quantity > 0:
                target_qty = int(Decimal(str(pos.quantity)) * Decimal(str(weight)))
                # 비중이 0보다 큰데 수량이 0으로 절사된 경우 1주 매도 시도
                if target_qty == 0 and weight > 0.0:
                    target_qty = 1
                target_qty = min(target_qty, pos.quantity)
                if target_qty > 0:
                    trade_record = self.engine.execute_order(
                        symbol=self.symbol,
                        side=OrderSide.SELL,
                        quantity=target_qty,
                        current_price=current_price,
                        timestamp=ts,
                    )

        self._last_trade_record = trade_record

        # 2. 시장 가격 업데이트 (Drift 추적 및 평가금 산정)
        self.engine.update_market_price(self.symbol, current_price)

        # 3. 에쿼티 및 보상(Log Equity Change) 계산
        curr_equity = self.account.get_total_equity({self.symbol: current_price})
        if self._prev_equity > 0 and curr_equity > 0:
            reward = float(np.log(float(curr_equity) / float(self._prev_equity)))
        else:
            reward = 0.0
        self._prev_equity = curr_equity

        # 4. 스텝 증가 및 에피소드 종료 조건 판정
        self._current_step += 1

        # Terminated: 파산 조건 (총 평가금이 초기 자본금의 5% 미만으로 하락)
        bankruptcy_threshold = self.initial_cash * to_decimal(self.bankruptcy_threshold_ratio)
        terminated = bool(curr_equity < bankruptcy_threshold)

        # Truncated: 데이터 소진 또는 max_steps 도달
        if self.mode == "offline":
            truncated = bool(
                self._current_step >= self._max_steps
                or (self.df is not None and self._current_step >= len(self.df))
            )
        else:
            truncated = bool(
                self._custom_max_steps is not None
                and self._current_step >= self._custom_max_steps
            )

        # 5. 관측값 및 추가 정보 반환
        obs = self._get_observation()
        info = self._get_info(current_price=current_price, trade_record=trade_record)

        if self.render_mode == "human":
            self.render()

        return obs, reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """
        정규화된 관측 벡터를 추출합니다.
        - 시장 피처 (10개) + 계좌 상태 피처 (4개) = 14차원 np.float32 벡터
        """
        current_price = self._last_price
        market_feats: List[float] = []

        if self.mode == "offline" and self.df is not None and len(self.df) > 0:
            idx = min(self._current_step, len(self.df) - 1)
            row = self.df.iloc[idx]

            if self.feature_cols is not None:
                for col in self.feature_cols:
                    val = float(row.get(col, 0.0))
                    market_feats.append(val if not math.isnan(val) and not math.isinf(val) else 0.0)
            else:
                # 1. returns_1d
                r1 = float(row.get("returns_1d", row.get("return_1d", 0.0)))
                market_feats.append(r1 if not math.isnan(r1) and not math.isinf(r1) else 0.0)
                # 2. volatility_20d
                v20 = float(row.get("volatility_20d", 0.015))
                market_feats.append(v20 if not math.isnan(v20) and not math.isinf(v20) else 0.015)
                # 3. log_return
                lr = float(row.get("log_return", 0.0))
                market_feats.append(lr if not math.isnan(lr) and not math.isinf(lr) else 0.0)
                # 4. ma_5 deviation
                c = float(self._last_price)
                raw_ma5 = float(row.get("ma_5", c))
                ma5 = raw_ma5 if not math.isnan(raw_ma5) and not math.isinf(raw_ma5) and raw_ma5 > 0 else c
                ma5_dev = (c - ma5) / (ma5 + 1e-8) if ma5 > 0 else 0.0
                market_feats.append(ma5_dev if not math.isnan(ma5_dev) and not math.isinf(ma5_dev) else 0.0)
                # 5. ma_20 deviation
                raw_ma20 = float(row.get("ma_20", c))
                ma20 = raw_ma20 if not math.isnan(raw_ma20) and not math.isinf(raw_ma20) and raw_ma20 > 0 else c
                ma20_dev = (c - ma20) / (ma20 + 1e-8) if ma20 > 0 else 0.0
                market_feats.append(ma20_dev if not math.isnan(ma20_dev) and not math.isinf(ma20_dev) else 0.0)
                # 6. ma_60 deviation
                raw_ma60 = float(row.get("ma_60", c))
                ma60 = raw_ma60 if not math.isnan(raw_ma60) and not math.isinf(raw_ma60) and raw_ma60 > 0 else c
                ma60_dev = (c - ma60) / (ma60 + 1e-8) if ma60 > 0 else 0.0
                market_feats.append(ma60_dev if not math.isnan(ma60_dev) and not math.isinf(ma60_dev) else 0.0)
                # 7. dynamic_per (normalized)
                d_per = float(row.get("dynamic_per", row.get("per", 15.0)))
                d_per_norm = (
                    float(np.clip(d_per / 50.0, -5.0, 5.0))
                    if not math.isnan(d_per) and not math.isinf(d_per)
                    else 0.3
                )
                market_feats.append(d_per_norm)
                # 8. dynamic_pbr (normalized)
                d_pbr = float(row.get("dynamic_pbr", row.get("pbr", 1.5)))
                d_pbr_norm = (
                    float(np.clip(d_pbr / 5.0, -5.0, 5.0))
                    if not math.isnan(d_pbr) and not math.isinf(d_pbr)
                    else 0.3
                )
                market_feats.append(d_pbr_norm)
                # 9. dynamic_market_cap (log normalized)
                d_mcap = float(row.get("dynamic_market_cap", 1e12))
                d_mcap_norm = (
                    float(np.clip(np.log1p(max(0.0, d_mcap)) / 35.0, 0.0, 2.0))
                    if not math.isnan(d_mcap) and not math.isinf(d_mcap)
                    else 1.0
                )
                market_feats.append(d_mcap_norm)
                # 10. volume (normalized)
                vol = float(row.get("volume", 500000.0))
                vol_norm = (
                    float(np.clip(vol / 1_000_000.0, 0.0, 50.0))
                    if not math.isnan(vol) and not math.isinf(vol)
                    else 0.5
                )
                market_feats.append(vol_norm)
        else:
            # Live mode or fallback
            market_feats = [0.0] * self.num_market_features

        # 4개 계좌 상태 피처 계산
        tot_eq = float(self.account.get_total_equity({self.symbol: current_price}))
        tot_eq_safe = tot_eq if tot_eq > 0 else 1.0
        pos = self.account.get_position(self.symbol)
        pos_val = float(pos.market_value(current_price))
        cash = float(self.account.cash_balance)

        # 1. cash_ratio
        cash_ratio = float(np.clip(cash / tot_eq_safe, 0.0, 1.0))
        # 2. position_ratio
        position_ratio = float(np.clip(pos_val / tot_eq_safe, 0.0, 1.0))
        # 3. unrealized_pnl_ratio
        unrealized_pnl_ratio = float(np.clip(float(pos.return_rate(current_price)), -2.0, 5.0))
        # 4. step_progress
        max_s = self._max_steps if self._max_steps and self._max_steps > 0 else 100
        step_progress = float(np.clip(self._current_step / max_s, 0.0, 1.0))

        account_feats = [cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress]

        full_obs = np.array(market_feats + account_feats, dtype=np.float32)
        sanitized_obs = np.nan_to_num(full_obs, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)
        return sanitized_obs

    def _get_info(
        self,
        current_price: Optional[Decimal] = None,
        trade_record: Optional[TradeRecord] = None,
    ) -> Dict[str, Any]:
        """환경 상태 및 체결 정보를 담은 Dict를 반환합니다."""
        p = current_price or self._last_price
        pos = self.account.get_position(self.symbol)
        tot_eq = self.account.get_total_equity({self.symbol: p})

        return {
            "step": self._current_step,
            "symbol": self.symbol,
            "current_price": float(p),
            "total_equity": float(tot_eq),
            "cash_balance": float(self.account.cash_balance),
            "holding_quantity": int(pos.quantity),
            "avg_buy_price": float(pos.avg_price),
            "realized_pnl": float(self.account.realized_pnl),
            "unrealized_pnl": float(pos.unrealized_pnl(p)),
            "cumulative_frictions": float(
                self.account.cumulative_commission
                + self.account.cumulative_tax
                + self.account.cumulative_slippage
            ),
            "trade_record": trade_record,
            "audit": self.engine.get_accounting_audit({self.symbol: p}),
        }

    def get_state(self) -> Dict[str, Any]:
        """현재 계좌 및 시장 상태를 요약 반환합니다."""
        return self._get_info()

    def get_accounting_audit(self) -> Dict[str, Any]:
        """체결 엔진의 1원 단위 회계 감사 내역을 반환합니다."""
        return self.engine.get_accounting_audit({self.symbol: self._last_price})

    def verify_accounting_invariant(self, tolerance: Union[Decimal, float, int] = Decimal("1")) -> bool:
        """가상 계좌와 체결 엔진 간의 회계 불변식(1원 오차 방어)을 검증합니다."""
        return self.engine.verify_accounting_invariant(
            current_market_prices={self.symbol: self._last_price},
            tolerance=to_decimal(tolerance),
        )

    def render(self) -> Optional[str]:
        """현재 환경의 상태를 텍스트로 요약 출력합니다."""
        state = self._get_info()
        lines = [
            f"=== HybridTradingEnv Step {state['step']} ===",
            f"Mode: {self.mode.upper()} | Symbol: {state['symbol']} | Current Price: {state['current_price']:,.0f} KRW",
            f"Cash: {state['cash_balance']:,.0f} KRW | Holdings: {state['holding_quantity']} shares (Avg: {state['avg_buy_price']:,.0f} KRW)",
            f"Total Equity: {state['total_equity']:,.0f} KRW | Realized PnL: {state['realized_pnl']:,.0f} KRW | Unrealized PnL: {state['unrealized_pnl']:,.0f} KRW",
            f"Cumulative Frictions: {state['cumulative_frictions']:,.0f} KRW",
        ]
        text = "\n".join(lines)
        if self.render_mode == "human":
            print(text)
            return None
        return text

    def set_data(self, df: pd.DataFrame) -> None:
        """데이터프레임을 동적으로 교체합니다."""
        self._load_offline_data(df=df)
        self.reset()

    def close(self) -> None:
        """환경 리소스를 정리합니다."""
        pass


class ContinuousToHybridActionWrapper(gym.ActionWrapper, RecordConstructorArgs):
    """
    Stable-Baselines3 등 연속형(Continuous) 액션 공간만 지원하는 알고리즘을 위한 어댑터 Wrapper.
    - Action Space: Box(low=np.array([-1.0, 0.0]), high=np.array([1.0, 1.0]), dtype=np.float32)
    - action[0]: trade direction signal (<-0.33: SELL, >0.33: BUY, else HOLD)
    - action[1]: position weight (0.0 ~ 1.0)
    """

    def __init__(self, env: gym.Env):
        RecordConstructorArgs.__init__(self)
        gym.ActionWrapper.__init__(self, env)
        self.action_space = spaces.Box(
            low=np.array([-1.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

    def action(self, action: np.ndarray) -> Tuple[int, np.ndarray]:
        signal = float(action[0])
        weight = float(np.clip(action[1], 0.0, 1.0))

        if signal > 0.333:
            act_type = 1  # BUY
        elif signal < -0.333:
            act_type = 2  # SELL
        else:
            act_type = 0  # HOLD

        return act_type, np.array([weight], dtype=np.float32)
