"""
modules/engine/live_learning_simulator.py
=========================================
실거래 정보 기반 학습 전용 시뮬레이터.
전역(Global) 가상 계좌를 유지하며, 매수/매도 요청 시 실제 Kiwoom REST API를 호출하여
실시간 주가를 가져온 뒤 가상 체결 엔진을 통해 시뮬레이션 체결을 수행합니다.
머신러닝/강화학습 봇이 실거래 데이터를 기반으로 Paper Trading(모의 훈련)을 할 때 사용됩니다.
Gymnasium 1.2.0 표준 규격 5-tuple (obs, reward, terminated, truncated, info) 및 Log Equity Return을 지원합니다.
Phase 5: Dynamic Stock Screener 연동 인터페이스(inject_triggered_symbol, build_rl_observation, step_symbol) 탑재.
"""

import logging
import queue
import threading
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from core.kiwoom_api import KiwoomClient
from modules.engine.mock_environment import (
    ActionType,
    FeeConfig,
    MockExecutionEngine,
    OrderSide,
    OrderType,
    VirtualAccount,
    to_decimal,
)

logger = logging.getLogger("AutoStock.LiveSimulator")


class LiveLearningSimulator:
    """실시간 주가 연동형 가상 체결 시뮬레이터"""

    def __init__(
        self,
        initial_cash: Union[int, Decimal] = 10_000_000,
        fee_config: Optional[FeeConfig] = None,
    ):
        self.initial_cash = to_decimal(initial_cash)
        self.account = VirtualAccount(initial_cash=self.initial_cash)
        self.fee_config = fee_config or FeeConfig()
        self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)

        # Kiwoom API 클라이언트 (내부적으로 토큰 갱신 등 자동 처리)
        self.api_client = KiwoomClient()
        self._prev_equity = self.initial_cash

        # Phase 5 (R4): Dynamic Stock Screener 연동 속성
        self.active_pool: Dict[str, Dict[str, Any]] = {}
        self.triggered_queue: queue.Queue = queue.Queue()
        self.streamer: Optional[Any] = None
        self._lock = threading.RLock()

    def reset(self, initial_cash: Optional[Union[int, Decimal]] = None) -> Dict[str, Any]:
        """계좌를 초기화하고 초기 상태를 반환합니다."""
        with self._lock:
            if initial_cash is not None:
                self.initial_cash = to_decimal(initial_cash)
            self.account.reset(initial_cash=self.initial_cash)
            self.engine = MockExecutionEngine(account=self.account, fee_config=self.fee_config)
            self._prev_equity = self.initial_cash

            self.active_pool.clear()
            while not self.triggered_queue.empty():
                try:
                    self.triggered_queue.get_nowait()
                except Exception:
                    break

            logger.info(f"시뮬레이터가 초기화되었습니다. (초기 자본금: {self.initial_cash:,.0f}원)")
            return self.get_state(symbol="005930")  # 기본 종목으로 초기 상태 반환 (실제 시세는 아직 미반영)

    def fetch_live_price(self, symbol: str) -> Decimal:
        """Kiwoom API를 통해 종목의 현재가를 조회합니다."""
        try:
            quote = self.api_client.get_current_price(symbol)
            return quote.current_price
        except Exception as e:
            logger.error(f"실시간 주가 조회 실패 ({symbol}): {e}")
            # 통신 실패 시 캐싱된 마지막 시장가를 반환하거나, 없으면 에러 발생
            if symbol in self.engine._last_market_prices:
                return self.engine._last_market_prices[symbol]
            raise

    def step(
        self,
        symbol: str,
        action: Union[int, ActionType],
        quantity: int = 1,
    ) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """
        Gymnasium 1.2.0 표준 규격 강화학습 Step 함수 (기존 하위 호환성 100% 보장).
        실시간 시세를 조회한 뒤, 주어진 액션(매수/매도/관망)을 가상 계좌에 체결시킵니다.

        Args:
            symbol (str): 거래할 종목코드 (예: "005930")
            action (ActionType/int): 0 (HOLD), 1 (BUY), 2 (SELL)
            quantity (int): 거래 수량

        Returns:
            state (dict): 체결 후 계좌 및 시세 상태 (obs dict)
            reward (float): 이번 스텝에서의 Log Equity Return ln(E_t / E_{t-1})
            terminated (bool): 파산 조건 도달 여부 (총 자산 < 초기 자본의 5%)
            truncated (bool): 에피소드 타임아웃/잘림 여부 (기본 False)
            info (dict): 체결 상세 내역 및 감사 정보
        """
        # 1. 실시간 주가 조회
        current_price = self.fetch_live_price(symbol)

        trade_record = None
        act_val = int(action)

        # 2. 가상 주문 체결
        if act_val == int(ActionType.BUY):
            # 매수 가능 수량 체크
            estimated_cost = current_price * quantity * Decimal("1.00015")  # 수수료 대략 포함
            if self.account.cash_balance >= estimated_cost:
                trade_record = self.engine.execute_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=quantity,
                    current_price=current_price,
                )
            else:
                logger.warning(
                    f"매수 실패: 잔고 부족 (필요: {estimated_cost:,.0f}, 잔고: {self.account.cash_balance:,.0f})"
                )

        elif act_val == int(ActionType.SELL):
            pos = self.account.get_position(symbol)
            if pos.quantity >= quantity:
                trade_record = self.engine.execute_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=quantity,
                    current_price=current_price,
                )
            else:
                logger.warning(f"매도 실패: 보유 수량 부족 (보유: {pos.quantity}, 요청: {quantity})")

        # 3. 시장가 업데이트
        self.engine.update_market_price(symbol, current_price)

        # 4. 보상 계산 (Log Equity Return ln(E_t / E_{t-1}))
        curr_equity = self.account.get_total_equity({symbol: current_price})
        if self._prev_equity > 0 and curr_equity > 0:
            reward = float(np.log(float(curr_equity) / float(self._prev_equity)))
        else:
            reward = 0.0
        self._prev_equity = curr_equity

        # 파산(총 자산이 초기 자본금의 5% 미만) 검사
        terminated = bool(curr_equity < (self.initial_cash * Decimal("0.05")))
        truncated = False

        # 5. 상태 및 정보 반환
        state = self.get_state(symbol, current_price)
        info = {
            "trade": trade_record,
            "audit": self.engine.get_accounting_audit({symbol: current_price}),
            "live_price_used": float(current_price),
        }

        return state, reward, terminated, truncated, info

    def get_state(self, symbol: str, current_price: Optional[Decimal] = None) -> Dict[str, Any]:
        """현재 가상 계좌의 관측 상태(Dict)를 반환합니다."""
        p = current_price or self.engine._last_market_prices.get(symbol, Decimal("0"))
        pos = self.account.get_position(symbol)
        tot_eq = self.account.get_total_equity({symbol: p})

        return {
            "symbol": symbol,
            "current_price": float(p),
            "cash_balance": float(self.account.cash_balance),
            "holding_quantity": pos.quantity,
            "avg_buy_price": float(pos.avg_price),
            "total_equity": float(tot_eq),
            "realized_pnl": float(self.account.realized_pnl),
            "unrealized_pnl": float(pos.unrealized_pnl(p)),
            "cumulative_frictions": float(
                self.account.cumulative_commission
                + self.account.cumulative_tax
                + self.account.cumulative_slippage
            ),
        }

    # ==========================================================================
    # Phase 5 (R4) Dynamic Stock Screener Integration Interfaces
    # ==========================================================================

    def inject_triggered_symbol(
        self,
        symbol: str,
        trigger_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        스크리너에서 포착(Trigger)된 종목을 시뮬레이터 활성 풀 및 대기 큐로 동적 등록합니다 (R4).
        스트리머가 연결되어 있다면 해당 종목의 실시간 시세 구독을 지시합니다.

        Args:
            symbol: 등록할 종목코드 (예: "000660")
            trigger_info: 트리거 발생 시점의 시세, 거래량, 시각 메타데이터

        Returns:
            bool: 주입 성공 여부
        """
        clean_sym = str(symbol).strip().zfill(6) if str(symbol).isdigit() else str(symbol).strip()
        with self._lock:
            now = datetime.now()
            info = trigger_info or {}
            self.active_pool[clean_sym] = {
                "injected_at": now,
                "trigger_data": info,
                "status": "ACTIVE",
            }
            self.triggered_queue.put(clean_sym)

            # 스트리머가 연결되어 있다면 해당 종목 실시간 시세 구독 추가
            if self.streamer is not None and hasattr(self.streamer, "subscribe"):
                self.streamer.subscribe(clean_sym)

            # 트리거 가격이 있으면 가상 시장가 즉시 동기화
            if "price" in info:
                try:
                    self.engine.update_market_price(clean_sym, to_decimal(info["price"]))
                except Exception as e:
                    logger.debug(f"시장가 업데이트 오류 ({clean_sym}): {e}")

            logger.info(f"종목 동적 주입 완료: {clean_sym} (현재 활성 풀: {len(self.active_pool)}개)")
            return True

    def build_rl_observation(
        self,
        symbol: str,
        market_features: Optional[Union[List[float], np.ndarray]] = None,
    ) -> np.ndarray:
        """
        지정 종목에 대해 HybridTradingEnv 규격과 일치하는 14차원 float32 관측 벡터(obs)를 생성합니다 (R4).
        - 10개 시장 피처: market_features 또는 트리거 데이터 기반 (returns_1d, volume 등)
        - 4개 계좌 상태 피처: cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress
        """
        clean_sym = str(symbol).strip().zfill(6) if str(symbol).isdigit() else str(symbol).strip()

        # 1. 대상 종목 현재가 획득
        p = self.engine._last_market_prices.get(clean_sym, Decimal("0"))
        if p <= 0:
            try:
                p = self.fetch_live_price(clean_sym)
            except Exception:
                p = Decimal("70000")

        # 2. 10개 시장 피처
        if market_features is not None and len(market_features) == 10:
            m_feats = [float(x) for x in market_features]
        else:
            m_feats = [0.0] * 10
            if clean_sym in self.active_pool and "trigger_data" in self.active_pool[clean_sym]:
                t_data = self.active_pool[clean_sym]["trigger_data"]
                open_p = float(t_data.get("open_price", p if p > 0 else Decimal("70000")))
                curr_p = float(p)
                ret_from_open = (curr_p - open_p) / open_p if open_p > 0 else 0.0
                m_feats[0] = float(np.clip(ret_from_open, -0.3, 0.3))
                vol = float(t_data.get("volume", t_data.get("accum_volume", 500000)))
                m_feats[9] = float(np.clip(vol / 1_000_000.0, 0.0, 50.0))

        # 3. 4개 계좌 상태 피처 (전체 포트폴리오 에쿼티 기준)
        all_prices = dict(self.engine._last_market_prices)
        all_prices[clean_sym] = p
        tot_eq = float(self.account.get_total_equity(all_prices))
        tot_eq_safe = tot_eq if tot_eq > 0 else float(self.initial_cash)

        pos = self.account.get_position(clean_sym)
        pos_val = float(pos.market_value(p))
        cash = float(self.account.cash_balance)

        cash_ratio = float(np.clip(cash / tot_eq_safe, 0.0, 1.0))
        position_ratio = float(np.clip(pos_val / tot_eq_safe, 0.0, 1.0))
        unrealized_pnl_ratio = float(np.clip(float(pos.return_rate(p)), -2.0, 5.0))
        step_progress = 0.5

        acc_feats = [cash_ratio, position_ratio, unrealized_pnl_ratio, step_progress]
        full_obs = np.array(m_feats + acc_feats, dtype=np.float32)
        return np.nan_to_num(full_obs, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)

    def step_symbol(
        self,
        symbol: str,
        action: Union[int, ActionType],
        quantity: Optional[int] = None,
        position_weight: float = 1.0,
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        지정된 종목에 대해 포지션 비중(w) 또는 수량 기반으로 액션을 수행하고
        전체 포트폴리오 에쿼티 기반 5-tuple (obs, reward, terminated, truncated, info)을 반환합니다 (R4).

        Args:
            symbol: 거래 종목코드
            action: 0 (HOLD), 1 (BUY), 2 (SELL)
            quantity: 지정 체결 수량 (None일 경우 position_weight 기반 자동 산정)
            position_weight: 포지션 비중 w in [0.0, 1.0]

        Returns:
            Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
            (14차원 obs, reward, terminated, truncated, info)
        """
        clean_sym = str(symbol).strip().zfill(6) if str(symbol).isdigit() else str(symbol).strip()
        current_price = self.fetch_live_price(clean_sym)
        act_val = int(action)
        trade_record = None
        weight = float(np.clip(position_weight, 0.0, 1.0))

        slip = self.fee_config.slippage_rate
        comm = self.fee_config.commission_rate
        est_cost_per_share = current_price * (Decimal("1") + slip) * (Decimal("1") + comm)

        # 1. 매수 체결
        if act_val == int(ActionType.BUY) and (weight > 0.0 or quantity is not None):
            if quantity is not None:
                exec_qty = quantity
            else:
                budget = self.account.cash_balance * Decimal(str(weight))
                exec_qty = int(budget / est_cost_per_share) if est_cost_per_share > 0 else 0

            if exec_qty > 0 and self.account.cash_balance >= (current_price * exec_qty):
                trade_record = self.engine.execute_order(
                    symbol=clean_sym,
                    side=OrderSide.BUY,
                    quantity=exec_qty,
                    current_price=current_price,
                )
            elif exec_qty > 0:
                logger.warning(f"매수 실패: 잔고 부족 (필요: {current_price * exec_qty}, 잔고: {self.account.cash_balance})")

        # 2. 매도 체결
        elif act_val == int(ActionType.SELL) and (weight > 0.0 or quantity is not None):
            pos = self.account.get_position(clean_sym)
            if pos.quantity > 0:
                if quantity is not None:
                    exec_qty = min(quantity, pos.quantity)
                else:
                    exec_qty = int(Decimal(str(pos.quantity)) * Decimal(str(weight)))
                    if exec_qty == 0 and weight > 0:
                        exec_qty = 1
                if exec_qty > 0:
                    trade_record = self.engine.execute_order(
                        symbol=clean_sym,
                        side=OrderSide.SELL,
                        quantity=exec_qty,
                        current_price=current_price,
                    )

        # 3. 시장가 전체 갱신
        self.engine.update_market_price(clean_sym, current_price)

        # 4. [핵심] 전체 보유 종목의 시장가를 모두 반영하여 Total Equity 계산
        all_prices = dict(self.engine._last_market_prices)
        all_prices[clean_sym] = current_price
        curr_equity = self.account.get_total_equity(all_prices)

        if self._prev_equity > 0 and curr_equity > 0:
            reward = float(np.log(float(curr_equity) / float(self._prev_equity)))
        else:
            reward = 0.0
        self._prev_equity = curr_equity

        terminated = bool(curr_equity < (self.initial_cash * Decimal("0.05")))
        truncated = False

        obs = self.build_rl_observation(clean_sym)
        info = {
            "symbol": clean_sym,
            "trade": trade_record,
            "audit": self.engine.get_accounting_audit(all_prices),
            "live_price_used": float(current_price),
            "total_equity": float(curr_equity),
        }
        return obs, reward, terminated, truncated, info

    def process_triggered_queue(
        self,
        screener_events_or_policy: Optional[Any] = None,
        policy_fn: Optional[Callable[[np.ndarray], Tuple[int, float]]] = None,
        screener_events: Optional[List[Any]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        대기 큐에 쌓인 트리거 종목들을 처리합니다 (R4).
        - callable 전달 시 (또는 policy_fn): 정책 함수(obs -> (action, weight))를 적용하여 순차 매매 수행
        - list 전달 시 (또는 screener_events): screener_events 리스트를 순회하며 종목 주입
        """
        results = []
        target_fn = screener_events_or_policy if callable(screener_events_or_policy) else (policy_fn or kwargs.get("policy"))
        target_events = screener_events or (screener_events_or_policy if isinstance(screener_events_or_policy, list) else kwargs.get("events"))

        if target_fn is not None:
            while not self.triggered_queue.empty():
                sym = self.triggered_queue.get_nowait()
                obs = self.build_rl_observation(sym)
                act, weight = target_fn(obs)
                obs_next, rew, term, trunc, info = self.step_symbol(sym, act, position_weight=weight)
                results.append({
                    "symbol": sym,
                    "action": act,
                    "weight": weight,
                    "reward": rew,
                    "terminated": term,
                    "info": info,
                })
        elif target_events is not None:
            for ev in target_events:
                if isinstance(ev, dict):
                    sym = ev.get("symbol")
                    if sym:
                        self.inject_triggered_symbol(sym, trigger_info=ev)
                        results.append({"symbol": sym, "status": "INJECTED"})
                elif isinstance(ev, str):
                    self.inject_triggered_symbol(ev)
                    results.append({"symbol": ev, "status": "INJECTED"})
        else:
            while not self.triggered_queue.empty():
                sym = self.triggered_queue.get_nowait()
                obs = self.build_rl_observation(sym)
                results.append({"symbol": sym, "observation_shape": obs.shape, "status": "POPPED"})
        return results


# ==============================================================================
# Global Singleton Instance (Thread-Safe with Double-Checked Locking)
# ==============================================================================
_SIMULATOR_LOCK = threading.Lock()
_GLOBAL_SIMULATOR: Optional[LiveLearningSimulator] = None


def get_live_simulator(initial_cash: Union[int, Decimal] = 10_000_000) -> LiveLearningSimulator:
    """전역 시뮬레이터 인스턴스를 스레드 안전하게 반환합니다 (Double-Checked Locking)."""
    global _GLOBAL_SIMULATOR
    if _GLOBAL_SIMULATOR is None:
        with _SIMULATOR_LOCK:
            if _GLOBAL_SIMULATOR is None:
                _GLOBAL_SIMULATOR = LiveLearningSimulator(initial_cash=initial_cash)
    return _GLOBAL_SIMULATOR


def reset_global_simulator() -> None:
    """전역 시뮬레이터 인스턴스를 초기화합니다."""
    global _GLOBAL_SIMULATOR
    with _SIMULATOR_LOCK:
        _GLOBAL_SIMULATOR = None
