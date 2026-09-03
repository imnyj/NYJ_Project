"""
tests/test_adversarial_m4_challenger1.py
========================================
Milestone 4 적대적 검증(Adversarial Challenger M4-1) 전용 극한 스트레스 테스트 스위트.

검증 항목:
1. 비정상적인 액션 타입(문자열, 음수, 범위 초과 100.0, NaN, Inf, 빈 딕셔너리, None, 이상 튜플/리스트) 주입 시 예외 발생 및 방어 동작 정밀 검증.
2. 단일 주식 잔고 부족 시의 매수/매도 경계 처리 및 1원 단위 회계 항등식(Equity = Cash + Value) 보존 검증.
3. SB3 Continuous Wrapper 변환 및 역변환 시 일관성 및 E2E 학습 연동 검증.
4. 20,000 스텝 이상의 카오스 적대적 액션 스트림(Chaotic Adversarial Walk) 장기 무결성 검증.
"""

import math
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Dict, List, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
import pytest
import torch

from modules.engine.hybrid_trading_env import (
    ContinuousToHybridActionWrapper,
    HybridTradingEnv,
)
from modules.engine.mock_environment import (
    ActionType,
    FeeConfig,
    OrderSide,
    OrderType,
    VirtualAccount,
    MockExecutionEngine,
    quantize_krw,
    to_decimal,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
    SB3HybridPolicyAdapter,
)


# ==============================================================================
# Helper: Synthetic Price Generator
# ==============================================================================

def create_synthetic_data(length: int = 1000, seed: int = 42, volatility: float = 0.02) -> pd.DataFrame:
    """합성 시계열 데이터프레임 생성 (기하 브라운 운동 기반)"""
    np.random.seed(seed)
    returns = np.random.normal(0.0005, volatility, size=length)
    prices = np.round(70000.0 * np.cumprod(1.0 + returns))
    prices = np.maximum(prices, 500.0)

    dates = pd.date_range("2026-01-01", periods=length, freq="B")
    return pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": np.round(prices * (1.0 + np.random.normal(0, 0.002, length))),
        "high": np.round(prices * (1.0 + np.abs(np.random.normal(0, 0.005, length)))),
        "low": np.round(prices * (1.0 - np.abs(np.random.normal(0, 0.005, length)))),
        "close": prices,
        "volume": np.random.randint(100000, 1000000, length),
        "returns_1d": returns,
        "log_return": np.log1p(returns),
        "volatility_20d": np.full(length, volatility),
        "ma_5": pd.Series(prices).rolling(5, min_periods=1).mean().values,
        "ma_20": pd.Series(prices).rolling(20, min_periods=1).mean().values,
        "ma_60": pd.Series(prices).rolling(60, min_periods=1).mean().values,
        "dynamic_per": np.full(length, 15.0),
        "dynamic_pbr": np.full(length, 1.5),
        "dynamic_market_cap": prices * 6_000_000_000.0,
    })


# ==============================================================================
# 1. Abnormal Action Type Stress Tests (비정상 액션 타입 방어 및 클리핑 검증)
# ==============================================================================

class TestAbnormalActionTypeStress:
    """비정상적인 액션 타입 주입 시의 방어력 및 클리핑 동작 검증"""

    @pytest.fixture
    def test_env(self):
        df = create_synthetic_data(length=500, seed=1001)
        return HybridTradingEnv(df=df, initial_cash=10_000_000)

    def test_string_actions_graceful_handling(self, test_env):
        """문자열 액션 주입 시 기본 HOLD(0, 0.0)로 안전 폴백되는지 검증"""
        test_env.reset(seed=42)

        string_actions = [
            "BUY",
            "SELL",
            "HOLD",
            "INVALID_ACTION",
            "",
            "   ",
            "123",
        ]

        for s_act in string_actions:
            act_type, weight = test_env._parse_action(s_act)
            assert act_type == 0, f"Expected act_type 0 for string '{s_act}', got {act_type}"
            assert weight == 0.0, f"Expected weight 0.0 for string '{s_act}', got {weight}"

            obs, rew, term, trunc, info = test_env.step(s_act)
            assert isinstance(obs, np.ndarray)
            assert obs.shape == (14,)
            assert np.all(np.isfinite(obs))
            assert math.isfinite(rew)

    def test_negative_and_excessive_bounds_clipping(self, test_env):
        """음수 및 과대 범위(100.0 등) 액션 주입 시 [0, 2] 및 [0.0, 1.0]으로 정확히 클리핑되는지 검증"""
        test_env.reset(seed=42)

        test_cases = [
            # (raw_action, expected_type, expected_weight)
            ((-100, -50.0), 0, 0.0),
            ((-1, -0.5), 0, 0.0),
            ((5, 100.0), 2, 1.0),
            ((100, 9999.0), 2, 1.0),
            ([10, 50.0], 2, 1.0),
            ([-10, -50.0], 0, 0.0),
            (np.array([99, 100.0]), 2, 1.0),
            (np.array([-99, -100.0]), 0, 0.0),
            (100.0, 1, 1.0),
            (-100.0, 2, 1.0),
        ]

        for raw_act, exp_type, exp_weight in test_cases:
            act_type, weight = test_env._parse_action(raw_act)
            assert act_type == exp_type, f"Action {raw_act}: expected type {exp_type}, got {act_type}"
            assert weight == pytest.approx(exp_weight, abs=1e-5), f"Action {raw_act}: expected weight {exp_weight}, got {weight}"

            obs, rew, term, trunc, info = test_env.step(raw_act)
            assert np.all(np.isfinite(obs))
            assert math.isfinite(rew)

    def test_discrete_integer_negative_behavior_observation(self, test_env):
        """
        [적대적 관찰] 음수 정수 액션(-500) 주입 시 act_type은 0(HOLD)로 클리핑되나,
        weight는 1.0으로 산출되는 구현 특성 확인 및 step 시 HOLD로 인해 매매 미발생 무결성 입증
        """
        test_env.reset(seed=42)
        act_type, weight = test_env._parse_action(-500)
        assert act_type == 0  # np.clip(-500, 0, 2) -> 0 (HOLD)
        # weight는 1.0 if -500 != 0 else 0.0으로 1.0이 됨
        assert weight == 1.0

        # step 실행 시 act_type이 0이므로 체결 없이 안전 통과
        obs, rew, term, trunc, info = test_env.step(-500)
        assert info["trade_record"] is None
        assert info["holding_quantity"] == 0

    def test_empty_and_irregular_structure_actions(self, test_env):
        """빈 딕셔너리, None, 빈 리스트 등 비정형 액션 주입 시 안전 폴백 검증"""
        test_env.reset(seed=42)

        irregular_actions = [
            {},
            {"unknown_key": 123},
            {"action_type": 1, "unknown_field": 0.5},
            None,
            [],
            [1],
            [1, 2, 3, 4],
        ]

        for irr_act in irregular_actions:
            act_type, weight = test_env._parse_action(irr_act)
            assert act_type in (0, 1, 2)
            assert 0.0 <= weight <= 1.0
            obs, rew, term, trunc, info = test_env.step(irr_act)
            assert np.all(np.isfinite(obs))

    def test_dict_with_string_and_array_weights(self, test_env):
        """Dict 액션 내부의 numpy array, float, int 가중치 정규화 파싱 검증"""
        test_env.reset(seed=42)

        dict_actions = [
            ({"action_type": 1, "position_size": np.array([0.75])}, 1, 0.75),
            ({"action_type": 2, "position_size": np.array([1.5])}, 2, 1.0),
            ({"action_type": 0, "weight": 0.5}, 0, 0.5),
            ({"action_type": 1, "position_size": []}, 1, 0.0),
        ]

        for d_act, exp_type, exp_weight in dict_actions:
            act_type, weight = test_env._parse_action(d_act)
            assert act_type == exp_type
            assert weight == pytest.approx(exp_weight, abs=1e-5)

    def test_nan_weight_sanitization(self, test_env):
        """가중치에 NaN이 주입되었을 때 0.0으로 안전하게 치환되는지 검증"""
        test_env.reset(seed=42)

        nan_actions = [
            (1, float("nan")),
            (2, np.nan),
            {"action_type": 1, "position_size": float("nan")},
            {"action_type": 2, "weight": np.nan},
        ]

        for n_act in nan_actions:
            act_type, weight = test_env._parse_action(n_act)
            assert not math.isnan(weight), f"Weight was not sanitized from NaN for {n_act}"
            assert weight == 0.0
            obs, rew, term, trunc, info = test_env.step(n_act)
            assert np.all(np.isfinite(obs))
            assert not math.isnan(rew)

    def test_torch_tensor_action_compatibility(self, test_env):
        """PyTorch Tensor 형태의 액션 주입 시 정상 변환 및 스텝 실행 검증"""
        test_env.reset(seed=42)

        tensor_actions = [
            torch.tensor([1, 0.5]),
            torch.tensor([2, 0.8]),
            torch.tensor([0, 0.0]),
        ]

        for t_act in tensor_actions:
            obs, rew, term, trunc, info = test_env.step(t_act.numpy())
            assert np.all(np.isfinite(obs))
            assert math.isfinite(rew)


# ==============================================================================
# 2. Insufficient Balance, Boundary Liquidity & Exact Accounting Identity
# ==============================================================================

class TestAccountingIdentityAndBoundaryLiquidity:
    """단일 주식 잔고 부족 시 매수/매도 경계 처리 및 1원 단위 회계 항등식 보존 검증"""

    def test_buy_rejection_on_zero_cash_preserves_accounting_identity(self):
        """현금 잔고가 0원일 때 매수 시도 시 안전 거절 및 회계 불변식(0원 오차) 유지 검증"""
        df = create_synthetic_data(length=50, seed=2001)
        env = HybridTradingEnv(df=df, initial_cash=0)
        env.reset()

        assert env.account.cash_balance == Decimal("0")

        # 전액 매수 시도
        obs, rew, term, trunc, info = env.step((1, 1.0))

        # 거절 확인: 매수 체결 없음, 현금 여전히 0, 보유 수량 0
        assert info["trade_record"] is None
        assert info["cash_balance"] == 0.0
        assert info["holding_quantity"] == 0
        assert env.account.cash_balance == Decimal("0")
        assert env.verify_accounting_invariant(tolerance=Decimal("0")) is True

    def test_buy_rejection_when_cash_insufficient_for_fees_and_slippage(self):
        """현금이 1주 체결 필요 금액 미만(수수료/슬리피지 고려 시 부족)일 때 안전 거절 검증"""
        df = create_synthetic_data(length=50, seed=2002)
        p0 = Decimal(str(df.iloc[0]["close"]))
        # 1주에 필요한 최소 예상 비용보다 10원 적은 금액을 initial_cash로 설정
        est_cost_1share = quantize_krw(p0 * Decimal("1.00115"), rounding=ROUND_CEILING)
        insufficient_cash = est_cost_1share - Decimal("10")
        env = HybridTradingEnv(df=df, initial_cash=insufficient_cash)
        env.reset()

        # 100% 매수 시도 -> 1주 매수 비용 부족으로 target_qty = 0 되어 미체결
        obs, rew, term, trunc, info = env.step((1, 1.0))

        assert info["holding_quantity"] == 0
        assert info["cash_balance"] == float(insufficient_cash)
        assert env.account.cash_balance == insufficient_cash
        assert env.verify_accounting_invariant(tolerance=Decimal("0")) is True

    def test_sell_rejection_on_zero_holdings_preserves_accounting_identity(self):
        """보유 주식이 0주일 때 매도 시도 시 안전 거절 및 잔고 불변식 검증"""
        df = create_synthetic_data(length=50, seed=2003)
        env = HybridTradingEnv(df=df, initial_cash=10_000_000)
        env.reset()

        # 보유 0주 상태에서 매도 시도
        obs, rew, term, trunc, info = env.step((2, 1.0))

        assert info["trade_record"] is None
        assert info["holding_quantity"] == 0
        assert info["cash_balance"] == 10_000_000.0
        assert env.account.cash_balance == Decimal("10000000")
        assert env.verify_accounting_invariant(tolerance=Decimal("0")) is True

    def test_fractional_weight_sell_boundary_single_share(self):
        """1주 보유 상태에서 매우 작은 비중(0.0001) 매도 시 1주 매도 정상 실행 및 회계 보존 검증"""
        df = create_synthetic_data(length=100, seed=2004)
        env = HybridTradingEnv(df=df, initial_cash=10_000_000)
        env.reset()

        # 1. 100% 매수 실행
        env.step((1, 1.0))
        pos_qty = env.account.get_position(env.symbol).quantity
        assert pos_qty > 0

        # 2. 전량 매도하여 0주로 만든 후 1주 매수
        env.step((2, 1.0))
        assert env.account.get_position(env.symbol).quantity == 0

        # 1주에 해당하는 아주 작은 비중 매수
        p0 = env._fetch_current_price()
        est_cost = p0 * Decimal("1.00115")
        tiny_buy_weight = float((est_cost * Decimal("1.5")) / env.account.cash_balance)
        env.step((1, tiny_buy_weight))

        curr_qty = env.account.get_position(env.symbol).quantity
        assert curr_qty >= 1

        # 3. 극소 비중(0.0001)으로 매도 시도 -> 1주 매도 절사 방어 동작 확인
        env.step((2, 0.0001))
        after_qty = env.account.get_position(env.symbol).quantity
        assert after_qty == curr_qty - 1

        # 회계 불변식 검증
        assert env.verify_accounting_invariant(tolerance=Decimal("1")) is True

    def test_strict_equity_cash_plus_value_identity_every_step(self):
        """모든 스텝에서 step 직후의 Total Equity == Cash + Stock Value가 1원의 오차도 없이 일치하는지 검증"""
        df = create_synthetic_data(length=300, seed=2005)
        env = HybridTradingEnv(df=df, initial_cash=20_000_000)
        env.reset()

        np.random.seed(42)
        for step in range(250):
            act_type = int(np.random.choice([0, 1, 2]))
            weight = float(np.random.uniform(0.0, 1.0))

            obs, rew, term, trunc, info = env.step((act_type, weight))

            # info에 기록된 해당 스텝의 체결 및 종가 기준 가격
            step_price = to_decimal(info["current_price"])
            cash = env.account.cash_balance
            pos = env.account.get_position(env.symbol)
            stock_val = quantize_krw(step_price * Decimal(pos.quantity), rounding=ROUND_FLOOR)
            tot_equity = env.account.get_total_equity({env.symbol: step_price})

            # Equity = Cash + Stock Value (0원 일치)
            assert tot_equity == cash + stock_val, f"Discrepancy at step {step}: {tot_equity} != {cash} + {stock_val}"

            # float info와의 정합성
            assert abs(info["total_equity"] - float(tot_equity)) < 1.0
            assert abs(info["cash_balance"] - float(cash)) < 1.0

            # 체결 엔진 불변식 검증
            assert env.verify_accounting_invariant(tolerance=Decimal("1")) is True

            if term or trunc:
                break

    def test_bankruptcy_threshold_and_zero_negative_cash(self):
        """주가 99% 폭락 시 파산 임계값(초기자본 5%)에서 terminated 발생 및 음수 잔고 원천 방어 검증"""
        length = 100
        prices = [70000.0 * (0.8 ** i) for i in range(length)]
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=length, freq="B"),
            "symbol": "005930",
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": 100000,
            "returns_1d": -0.2,
            "log_return": np.log(0.8),
            "volatility_20d": 0.05,
            "ma_5": prices,
            "ma_20": prices,
            "ma_60": prices,
            "dynamic_per": 5.0,
            "dynamic_pbr": 0.5,
            "dynamic_market_cap": 1e12,
        })

        env = HybridTradingEnv(df=df, initial_cash=10_000_000, bankruptcy_threshold_ratio=0.05)
        env.reset()

        # 첫 스텝에서 전액 매수
        env.step((1, 1.0))

        terminated_seen = False
        for step in range(1, length):
            obs, rew, term, trunc, info = env.step((0, 0.0))  # 지속 HOLD로 가치 하락 방치

            assert info["cash_balance"] >= 0.0, f"Cash balance became negative: {info['cash_balance']}"
            assert env.account.cash_balance >= Decimal("0")

            if term:
                terminated_seen = True
                assert info["total_equity"] < 10_000_000 * 0.05
                break

        assert terminated_seen is True, "Environment should have terminated upon hitting bankruptcy threshold"


# ==============================================================================
# 3. SB3 Continuous Wrapper Consistency & Interoperability
# ==============================================================================

class TestSB3ContinuousWrapperConsistency:
    """SB3 Continuous Wrapper 변환/역변환 일관성 및 PPO E2E 학습 연동 검증"""

    def test_wrapper_action_mapping_boundaries(self):
        """ContinuousToHybridActionWrapper의 신호 구간별 이산/연속 변환 검증"""
        df = create_synthetic_data(length=50, seed=3001)
        base_env = HybridTradingEnv(df=df)
        wrapped_env = ContinuousToHybridActionWrapper(base_env)

        # Action Space 확인
        assert isinstance(wrapped_env.action_space, gym.spaces.Box)
        assert wrapped_env.action_space.shape == (2,)
        assert np.all(wrapped_env.action_space.low == np.array([-1.0, 0.0], dtype=np.float32))
        assert np.all(wrapped_env.action_space.high == np.array([1.0, 1.0], dtype=np.float32))

        # 신호별 매핑 테스트 케이스 (부동소수점 오차 방어 및 엄격 구간 검증)
        test_signals = [
            # signal, weight -> expected (act_type, weight)
            (np.array([1.0, 0.8], dtype=np.float32), 1, 0.8),       # BUY
            (np.array([0.5, 0.5], dtype=np.float32), 1, 0.5),       # BUY
            (np.array([0.334, 0.5], dtype=np.float32), 1, 0.5),     # BUY boundary (> 0.333)
            (np.array([0.0, 0.0], dtype=np.float32), 0, 0.0),       # HOLD center
            (np.array([-0.334, 0.5], dtype=np.float32), 2, 0.5),    # SELL boundary (< -0.333)
            (np.array([-0.5, 0.5], dtype=np.float32), 2, 0.5),      # SELL
            (np.array([-1.0, 1.0], dtype=np.float32), 2, 1.0),      # SELL
        ]

        for cont_act, exp_type, exp_weight in test_signals:
            parsed_type, parsed_weight_arr = wrapped_env.action(cont_act)
            assert parsed_type == exp_type
            assert parsed_weight_arr[0] == pytest.approx(exp_weight, abs=1e-5)

    def test_float32_boundary_precision_observation(self):
        """
        [적대적 관찰] np.float32(0.333) 주입 시 float32 -> float64 변환 과정에서
        0.33300000429153442 > 0.333이 되어 HOLD가 아닌 BUY로 판정되는 부동소수점 임계값 특성 실측
        """
        df = create_synthetic_data(length=50, seed=3002)
        base_env = HybridTradingEnv(df=df)
        wrapped_env = ContinuousToHybridActionWrapper(base_env)

        act_f32 = np.array([0.333, 0.5], dtype=np.float32)
        parsed_type, parsed_weight_arr = wrapped_env.action(act_f32)
        # float(np.float32(0.333)) = 0.33300000429... > 0.333 이므로 1(BUY)로 평가됨
        assert parsed_type == 1

        # 반면 명시적인 0.0 또는 0.332는 정확히 HOLD(0)로 평가됨
        act_hold = np.array([0.332, 0.5], dtype=np.float32)
        parsed_hold_type, _ = wrapped_env.action(act_hold)
        assert parsed_hold_type == 0

    def test_wrapper_out_of_bounds_clipping(self):
        """ContinuousToHybridActionWrapper에서 경계 초과 액션 클리핑 검증"""
        df = create_synthetic_data(length=50, seed=3002)
        base_env = HybridTradingEnv(df=df)
        wrapped_env = ContinuousToHybridActionWrapper(base_env)

        # 1. 과대 양수 신호 및 가중치
        act_high = np.array([5.0, 10.0], dtype=np.float32)
        p_type, p_weight = wrapped_env.action(act_high)
        assert p_type == 1  # BUY
        assert p_weight[0] == 1.0  # Clipped to 1.0

        # 2. 과대 음수 신호 및 음수 가중치
        act_low = np.array([-5.0, -10.0], dtype=np.float32)
        p_type, p_weight = wrapped_env.action(act_low)
        assert p_type == 2  # SELL
        assert p_weight[0] == 0.0  # Clipped to 0.0

    def test_sb3_ppo_1000_steps_rollout_training(self):
        """SB3 PPO 에이전트와 ContinuousToHybridActionWrapper 간 1,000 스텝 E2E 롤아웃 및 학습 검증"""
        df = create_synthetic_data(length=500, seed=3003)
        base_env = HybridTradingEnv(df=df, initial_cash=10_000_000, max_steps=200)

        model = SB3HybridPolicyAdapter.create_sb3_ppo(
            env=base_env,
            features_dim=32,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=32,
            seed=42,
            device="cpu",
        )

        # 1,000 스텝 학습 수행
        SB3HybridPolicyAdapter.train_sb3_agent(model, total_timesteps=1000)

        # 추론 테스트 (50 스텝)
        obs, _ = base_env.reset(seed=42)
        for _ in range(50):
            hybrid_act, raw_act = SB3HybridPolicyAdapter.predict_hybrid(model, obs, deterministic=True)
            act_type, weight = hybrid_act

            assert act_type in (0, 1, 2)
            assert 0.0 <= weight <= 1.0
            assert len(raw_act) == 2

            obs, rew, term, trunc, info = base_env.step(hybrid_act)
            if term or trunc:
                obs, _ = base_env.reset()


# ==============================================================================
# 4. Chaotic 20,000-Step Adversarial Stress Walk
# ==============================================================================

class TestChaotic20kAdversarialWalk:
    """20,000 스텝 이상의 카오스 적대적 액션 스트림 장기 무결성 검증"""

    def test_20000_steps_chaotic_stress_walk(self):
        """
        20,000 스텝에 걸쳐 온갖 비정상/경계값 액션을 무작위 주입하며:
        1. 무예외/무크래시 완주
        2. 관측값 finite 및 14차원 불변
        3. 계좌 잔고 >= 0 및 보유 수량 >= 0 유지
        4. 1원 단위 회계 불변식(verify_accounting_invariant) 0~1원 이내 보존
        """
        total_steps = 20000
        df = create_synthetic_data(length=total_steps + 100, seed=4001, volatility=0.015)
        env = HybridTradingEnv(
            df=df,
            initial_cash=50_000_000,
            bankruptcy_threshold_ratio=0.0,  # 20k 스텝 완주를 위해 파산 종료 비활성화
            max_steps=total_steps,
        )
        obs, info = env.reset(seed=999)

        np.random.seed(12345)
        trades_count = 0
        max_discrepancy = Decimal("0")

        for step_idx in range(total_steps):
            mod = step_idx % 8

            if mod == 0:
                # 경계 튜플 (음수, 과대 가중치)
                act = (int(np.random.choice([-10, 0, 1, 2, 10])), float(np.random.choice([-5.0, 0.0, 0.5, 1.0, 5.0])))
            elif mod == 1:
                # Dict 포맷
                act = {"action_type": int(np.random.choice([0, 1, 2])), "position_size": float(np.random.uniform(0.0, 1.0))}
            elif mod == 2:
                # Continuous Box 2D
                act = np.array([float(np.random.uniform(-3.0, 3.0)), float(np.random.uniform(-2.0, 2.0))], dtype=np.float32)
            elif mod == 3:
                # 문자열 액션
                act = str(np.random.choice(["BUY", "SELL", "HOLD", "INVALID", ""]))
            elif mod == 4:
                # NaN 가중치
                act = (int(np.random.choice([0, 1, 2])), float("nan"))
            elif mod == 5:
                # 스칼라 액션
                act = np.random.choice([0, 1, 2, 0.5, -0.5, ActionType.BUY, ActionType.SELL])
            elif mod == 6:
                # 빈 딕셔너리 또는 비정형
                act = {} if step_idx % 2 == 0 else {"unknown": 999}
            else:
                # 1D 리스트
                act = [int(np.random.choice([0, 1, 2])), float(np.random.uniform(0.0, 1.0))]

            obs, rew, term, trunc, info = env.step(act)

            # 무결성 단언
            assert obs.shape == (14,)
            assert np.all(np.isfinite(obs)), f"Obs has NaN/Inf at step {step_idx}: {obs}"
            assert not math.isnan(rew) and not math.isinf(rew), f"Reward NaN/Inf at step {step_idx}: {rew}"
            assert info["cash_balance"] >= 0.0
            assert info["holding_quantity"] >= 0

            if info["trade_record"] is not None and info["trade_record"].is_success:
                trades_count += 1

            # 회계 감사 불변식 검증 (매 50스텝마다 정밀 검증)
            if step_idx % 50 == 0:
                audit = env.get_accounting_audit()
                disc = abs(
                    (audit["initial_cash"] + audit["cumulative_market_drift_pnl"])
                    - (audit["total_equity"] + audit["total_frictions"])
                )
                if disc > max_discrepancy:
                    max_discrepancy = disc
                assert disc <= Decimal("1"), f"Discrepancy {disc} KRW > 1 KRW at step {step_idx}"

            if term or trunc:
                break

        assert trades_count > 1000, f"Expected > 1000 trades, got {trades_count}"
        assert max_discrepancy <= Decimal("1")
        assert env.verify_accounting_invariant(tolerance=Decimal("1")) is True
