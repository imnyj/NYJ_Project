"""
tests/test_hybrid_env_stress.py
================================
Milestone 1 적대적 챌린저 1 (Challenger 1) 전용 하이브리드 트레이딩 환경 극한 스트레스 테스트 하네스.

검증 항목:
1. 10,000회 이상의 극단적 랜덤 액션 스트림 (경계값 0.0, 1.0, 음수, 과대 비중, 비정상 포맷) 주입
2. 대규모 연속 매수/매도 시 회계 불변식(verify_accounting_invariant) 0원 오차 유지 검증
3. 자산 소진 및 파산 임계값에서의 환경 안정성 및 무결성 스트레스 테스트
4. 연속형 어댑터(ContinuousToHybridActionWrapper) 및 엣지 케이스 방어력 검증
5. 액션 파서의 잠재적 취약점(튜플 길이 미검증 IndexError, NaN/Inf 변환 에러) 실측 증명
"""

import math
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
import pytest

from modules.engine.hybrid_trading_env import (
    ContinuousToHybridActionWrapper,
    HybridTradingEnv,
)
from modules.engine.mock_environment import ActionType, FeeConfig, OrderSide, to_decimal


# ==============================================================================
# Helpers & Synthetic Generators
# ==============================================================================

def create_stress_dataframe(length: int = 15000, seed: int = 42, volatility: float = 0.02) -> pd.DataFrame:
    """대규모 장기 시계열 합성 데이터프레임 생성 (기하 브라운 운동 기반)"""
    np.random.seed(seed)
    returns = np.random.normal(0.0001, volatility, size=length)
    prices = np.round(70000.0 * np.cumprod(1.0 + returns))
    prices = np.maximum(prices, 500.0)  # 최소 500원 방어

    dates = pd.date_range("2020-01-01", periods=length, freq="B")
    return pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": np.round(prices * (1.0 + np.random.normal(0, 0.002, length))),
        "high": np.round(prices * (1.0 + np.abs(np.random.normal(0, 0.005, length)))),
        "low": np.round(prices * (1.0 - np.abs(np.random.normal(0, 0.005, length)))),
        "close": prices,
        "volume": np.random.randint(50000, 2000000, length),
        "returns_1d": returns,
        "log_return": np.log1p(returns),
        "volatility_20d": np.full(length, volatility),
        "ma_5": pd.Series(prices).rolling(5, min_periods=1).mean().values,
        "ma_20": pd.Series(prices).rolling(20, min_periods=1).mean().values,
        "ma_60": pd.Series(prices).rolling(60, min_periods=1).mean().values,
        "dynamic_per": np.full(length, 12.5),
        "dynamic_pbr": np.full(length, 1.2),
        "dynamic_market_cap": prices * 6_000_000_000.0,
    })


# ==============================================================================
# 1. 10,000+ Extreme Random Action Stream Tests
# ==============================================================================

class TestExtremeRandomActionStream:
    """10,000회 이상의 극단적 랜덤 액션 주입 및 환경 무결성 검증"""

    def test_ten_thousand_extreme_action_stream(self):
        """
        10,000 스텝 이상 극단 경계값 및 다양한 포맷의 액션을 주입하여:
        1. 크래시 없이 5-tuple (obs, rew, term, trunc, info) 정상 반환
        2. 관측값 obs가 NaN/Inf 없는 14차원 정규화 float32 벡터인지 확인
        3. 계좌 잔고 cash_balance >= 0 및 보유 수량 >= 0 불변식 유지 확인
        4. 회계 불변식(verify_accounting_invariant) 오차 0원(또는 <= 1원) 유지 확인
        """
        total_steps = 10500
        df = create_stress_dataframe(length=total_steps, seed=101)
        env = HybridTradingEnv(
            df=df,
            initial_cash=100_000_000,
            bankruptcy_threshold_ratio=0.0,  # 장기 스트림 완주를 위해 파산 종료 비활성화
            max_steps=total_steps,
        )
        obs, info = env.reset(seed=2026)

        assert obs.shape == (14,)
        assert np.all(np.isfinite(obs))

        trades_executed = 0
        invariant_max_error = Decimal("0")

        np.random.seed(777)
        for step_idx in range(total_steps):
            # 5개 카테고리의 극단적 액션 생성
            pattern = step_idx % 5

            if pattern == 0:
                # 경계값 및 초과 가중치 Tuple (음수, 1.0 초과, 0.0, 1.0, 극소값)
                act_type = int(np.random.choice([-100, -1, 0, 1, 2, 3, 50]))
                weight = float(np.random.choice([
                    -1000.0, -1.0, -0.0001, 0.0, 1e-6, 0.333, 0.5, 0.9999, 1.0, 1.0001, 5.0, 1000.0
                ]))
                action = (act_type, np.array([weight], dtype=np.float32))

            elif pattern == 1:
                # Dict 형태 액션 (비정상 키, 초과 가중치, 리스트 래핑)
                act_type = int(np.random.choice([0, 1, 2, 99]))
                weight = float(np.random.choice([-10.0, 0.0, 0.25, 0.5, 0.75, 1.0, 2.0]))
                if step_idx % 2 == 0:
                    action = {"action_type": act_type, "position_size": np.array([weight], dtype=np.float32)}
                else:
                    action = {"action_type": act_type, "weight": weight}

            elif pattern == 2:
                # 2D 연속형 Box Signal [-5.0 ~ 5.0]
                signal = float(np.random.uniform(-5.0, 5.0))
                weight = float(np.random.uniform(-2.0, 2.0))
                action = np.array([signal, weight], dtype=np.float32)

            elif pattern == 3:
                # 1D List / Array 포맷 [type, weight]
                act_type = int(np.random.choice([0, 1, 2]))
                weight = float(np.random.uniform(0.0, 1.0))
                action = [act_type, weight]

            else:
                # 스칼라 액션 (Discrete 정수 또는 Continuous Float)
                action = np.random.choice([0, 1, 2, -1.0, 0.0, 1.0, 0.5, -0.5, ActionType.BUY, ActionType.SELL])

            # 액션 실행
            obs, rew, term, trunc, info = env.step(action)

            # 1. 관측값 무결성 검증
            assert isinstance(obs, np.ndarray)
            assert obs.shape == (14,)
            assert obs.dtype == np.float32
            assert np.all(np.isfinite(obs)), f"Obs has NaN/Inf at step {step_idx}: {obs}"

            # 2. 보상 무결성 검증
            assert isinstance(rew, (float, np.floating))
            assert not math.isnan(rew) and not math.isinf(rew), f"Reward is NaN/Inf at step {step_idx}: {rew}"

            # 3. 계좌 상태 불변식 검증
            assert info["cash_balance"] >= 0.0, f"Cash balance < 0 at step {step_idx}: {info['cash_balance']}"
            assert info["holding_quantity"] >= 0, f"Holding qty < 0 at step {step_idx}: {info['holding_quantity']}"
            assert info["total_equity"] >= 0.0, f"Total equity < 0 at step {step_idx}: {info['total_equity']}"

            # 4. 회계 감사 불변식 검증 (매 스텝 1원 오차 0원 검증)
            audit = env.get_accounting_audit()
            discrepancy = abs(
                (audit["initial_cash"] + audit["cumulative_market_drift_pnl"])
                - (audit["total_equity"] + audit["total_frictions"])
            )
            if discrepancy > invariant_max_error:
                invariant_max_error = discrepancy
            assert discrepancy <= Decimal("1"), f"Accounting discrepancy {discrepancy} > 1 KRW at step {step_idx}"

            if info["trade_record"] is not None and info["trade_record"].is_success:
                trades_executed += 1

            if term or trunc:
                break

        assert trades_executed > 1000, f"Expected > 1000 trades, got {trades_executed}"
        assert invariant_max_error <= Decimal("1")
        assert env.verify_accounting_invariant() is True


# ==============================================================================
# 2. Accounting Invariant & Deep Transaction Stress Tests
# ==============================================================================

class TestAccountingInvariantDeepStress:
    """대규모 연속 매수/매도 시 회계 불변식(verify_accounting_invariant) 0원 오차 유지 검증"""

    def test_consecutive_ping_pong_accounting_invariant(self):
        """
        5,000회 연속 고빈도 매수 <-> 매도 핑퐁 거래 시 회계 불변식 0원 검증:
        Initial_Capital + Total_Market_Drift_PnL == Total_Equity + Total_Frictions
        """
        length = 5000
        df = create_stress_dataframe(length=length, seed=303, volatility=0.01)
        env = HybridTradingEnv(df=df, initial_cash=50_000_000, max_steps=length)
        env.reset()

        for step in range(length):
            # 짝수 스텝: 전액 매수(1.0), 홀수 스텝: 전액 매도(1.0)
            if step % 2 == 0:
                action = (1, np.array([1.0], dtype=np.float32))
            else:
                action = (2, np.array([1.0], dtype=np.float32))

            obs, rew, term, trunc, info = env.step(action)
            assert env.verify_accounting_invariant(tolerance=Decimal("1")) is True

            if term or trunc:
                break

        audit = env.get_accounting_audit()
        discrepancy = abs(
            (audit["initial_cash"] + audit["cumulative_market_drift_pnl"])
            - (audit["total_equity"] + audit["total_frictions"])
        )
        assert discrepancy <= Decimal("1")

    def test_extreme_price_shock_accounting_invariant(self):
        """
        상한가(+30%), 하한가(-30%), 10배 폭등, 90% 폭락 등 극단 가격 충격 시 회계 불변식 유지 검증
        """
        shock_prices = [
            70000.0, 91000.0, 63700.0, 82810.0, 50000.0,
            500000.0,  # 10배 폭등
            50000.0,   # 90% 폭락
            70000.0, 35000.0, 70000.0,
        ] * 50  # 총 550개 바

        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=len(shock_prices), freq="B"),
            "symbol": "005930",
            "close": shock_prices,
        })

        env = HybridTradingEnv(df=df, initial_cash=10_000_000, max_steps=len(df))
        env.reset()

        for step, p in enumerate(shock_prices):
            # 무작위 매수/매도/홀드
            act_type = (step % 3)
            weight = 0.5
            obs, rew, term, trunc, info = env.step((act_type, np.array([weight], dtype=np.float32)))

            assert env.verify_accounting_invariant(tolerance=Decimal("1")) is True
            assert info["cash_balance"] >= 0.0

            if term or trunc:
                break

        audit = env.get_accounting_audit()
        discrepancy = abs(
            (audit["initial_cash"] + audit["cumulative_market_drift_pnl"])
            - (audit["total_equity"] + audit["total_frictions"])
        )
        assert discrepancy <= Decimal("1")

    def test_custom_fee_config_accounting_invariants(self):
        """수수료 0원 환경 및 초고율 수수료(1% 수수료, 1% 세금, 5% 슬리피지) 환경에서의 불변식 검증"""
        # Case A: Zero fee
        zero_fee = FeeConfig(commission_rate=Decimal("0"), tax_rate=Decimal("0"), slippage_rate=Decimal("0"))
        df = create_stress_dataframe(length=500, seed=404)
        env_zero = HybridTradingEnv(df=df, initial_cash=10_000_000, fee_config=zero_fee)
        env_zero.reset()
        for _ in range(200):
            env_zero.step((1, 0.5))
            env_zero.step((2, 0.5))
            assert env_zero.verify_accounting_invariant() is True
        audit_zero = env_zero.get_accounting_audit()
        assert audit_zero["total_frictions"] == Decimal("0")

        # Case B: High fee
        high_fee = FeeConfig(
            commission_rate=Decimal("0.01"),  # 1%
            tax_rate=Decimal("0.01"),         # 1%
            slippage_rate=Decimal("0.05")     # 5%
        )
        env_high = HybridTradingEnv(df=df, initial_cash=10_000_000, fee_config=high_fee)
        env_high.reset()
        for _ in range(50):
            env_high.step((1, 0.3))
            env_high.step((2, 0.3))
            assert env_high.verify_accounting_invariant() is True


# ==============================================================================
# 3. Asset Exhaustion & Bankruptcy Threshold Stress Tests
# ==============================================================================

class TestBankruptcyAndExhaustionResilience:
    """자산 소진 및 파산 임계값에서의 환경 안정성 및 무결성 스트레스 테스트"""

    def test_micro_capital_exhaustion_no_negative_cash(self):
        """
        극소 자본금(100원, 10원, 1원) 환경에서 매수 시도 시 1주 미만 주문 방어 및 잔고 음수 방지
        """
        for init_cash in [1, 10, 100, 1000, 50000]:  # 주가 70,000원 대비 부족한 금액
            df = create_stress_dataframe(length=50, seed=505)
            env = HybridTradingEnv(df=df, initial_cash=init_cash)
            obs, info = env.reset()

            # 매수 100% 시도 50회 연속
            for _ in range(30):
                obs, rew, term, trunc, info = env.step((1, np.array([1.0], dtype=np.float32)))
                assert info["cash_balance"] == float(init_cash)
                assert info["holding_quantity"] == 0
                assert info["cash_balance"] >= 0.0
                assert np.all(np.isfinite(obs))
                assert rew == 0.0

    def test_zero_shares_sell_protection(self):
        """보유 주식이 0주일 때 매도 시도 시 무차입 공매도 원천 차단 및 no-op 확인"""
        df = create_stress_dataframe(length=50, seed=606)
        env = HybridTradingEnv(df=df, initial_cash=10_000_000)
        env.reset()

        for _ in range(30):
            obs, rew, term, trunc, info = env.step((2, np.array([1.0], dtype=np.float32)))
            assert info["holding_quantity"] == 0
            assert info["cash_balance"] == 10_000_000.0
            assert info["trade_record"] is None

    def test_bankruptcy_termination_trigger_and_state(self):
        """
        에쿼티가 초기 자본금의 5% 미만으로 폭락 시 정확히 terminated=True 트리거 및 관측값 안정성 검증
        """
        df = create_stress_dataframe(length=100, seed=707)
        env = HybridTradingEnv(df=df, initial_cash=10_000_000, bankruptcy_threshold_ratio=0.05)
        obs, info = env.reset()

        # 정상 매수
        obs, rew, term, trunc, info = env.step((1, np.array([0.9], dtype=np.float32)))
        assert term is False

        # 강제로 계좌 잔고 및 보유 주식 가치를 파산 임계치(50만원) 미만으로 하락 조작
        env.account.cash_balance = Decimal("100000")
        env.account.positions["005930"].quantity = 0
        env.account.positions["005930"].total_cost = Decimal("0")
        env.account.positions["005930"].avg_price = Decimal("0")

        obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
        assert term is True
        assert info["total_equity"] == 100000.0
        assert np.all(np.isfinite(obs))

    def test_zero_equity_observation_stability(self):
        """에쿼티가 정확히 0원일 때 _get_observation()에서 0 나누기(ZeroDivisionError) 방어 검증"""
        df = create_stress_dataframe(length=10, seed=808)
        env = HybridTradingEnv(df=df, initial_cash=0)
        obs, info = env.reset()

        assert np.all(np.isfinite(obs))
        assert obs.shape == (14,)

        obs, rew, term, trunc, info = env.step((0, np.array([0.0], dtype=np.float32)))
        assert np.all(np.isfinite(obs))
        assert rew == 0.0

    def test_multi_episode_resets(self):
        """50 에피소드 연속 reset 및 step 실행 시 메모리 누수 및 상태 간섭 부재 검증"""
        df = create_stress_dataframe(length=100, seed=909)
        env = HybridTradingEnv(df=df, initial_cash=10_000_000)

        for ep in range(50):
            obs, info = env.reset(seed=ep, options={"initial_cash": 10_000_000 + ep * 100_000})
            assert info["step"] == 0
            assert info["holding_quantity"] == 0
            assert info["cash_balance"] == 10_000_000 + ep * 100_000

            for _ in range(10):
                obs, rew, term, trunc, info = env.step((1, 0.1))
                assert np.all(np.isfinite(obs))


# ==============================================================================
# 4. Continuous Wrapper & Action Decoder Resilience Tests
# ==============================================================================

class TestContinuousWrapperAndActionDecoder:
    """연속형 어댑터(ContinuousToHybridActionWrapper) 및 디코더 엣지 케이스 방어력 검증"""

    def test_continuous_wrapper_ten_thousand_steps(self):
        """ContinuousToHybridActionWrapper 환경에서 10,000 스텝 연속 스트레스 테스트"""
        total_steps = 10000
        df = create_stress_dataframe(length=total_steps, seed=1001)
        base_env = HybridTradingEnv(
            df=df,
            initial_cash=50_000_000,
            bankruptcy_threshold_ratio=0.0,
            max_steps=total_steps,
        )
        wrapped_env = ContinuousToHybridActionWrapper(base_env)
        obs, info = wrapped_env.reset(seed=42)

        np.random.seed(1234)
        for step in range(total_steps):
            # Box([-1.0, 0.0] ~ [1.0, 1.0]) 샘플링 + 극단치
            if step % 10 == 0:
                action = np.array([-1.0, 0.0], dtype=np.float32)
            elif step % 10 == 1:
                action = np.array([1.0, 1.0], dtype=np.float32)
            elif step % 10 == 2:
                action = np.array([0.3333, 0.5], dtype=np.float32)
            elif step % 10 == 3:
                action = np.array([-0.3333, 0.5], dtype=np.float32)
            else:
                action = np.random.uniform(low=[-1.5, -0.5], high=[1.5, 1.5], size=(2,)).astype(np.float32)

            obs, rew, term, trunc, info = wrapped_env.step(action)
            assert np.all(np.isfinite(obs))
            assert not math.isnan(rew)
            assert info["cash_balance"] >= 0.0

            if term or trunc:
                break

        assert wrapped_env.unwrapped.verify_accounting_invariant(tolerance=Decimal("1")) is True

    def test_action_decoder_graceful_fallbacks(self):
        """비정상 포맷(None, 문자열, 불완전 리스트, 딕셔너리 등)의 그레이스풀 폴백 검증"""
        df = create_stress_dataframe(length=50, seed=1101)
        env = HybridTradingEnv(df=df, initial_cash=10_000_000)
        env.reset()

        graceful_actions = [
            [],
            {},
            "INVALID_STRING",
            None,
            [1],
            [1, 2, 3],
            {"unknown_key": 123},
            -999,
            999,
            1.5,
            -1.5,
        ]

        for act in graceful_actions:
            act_type, weight = env._parse_action(act)
            assert act_type in (0, 1, 2)
            assert 0.0 <= weight <= 1.0
            obs, rew, term, trunc, info = env.step(act)
            assert np.all(np.isfinite(obs))


# ==============================================================================
# 5. Empirical Vulnerability & Edge Case Demonstrations
# ==============================================================================

class TestEmpiricalVulnerabilities:
    """
    적대적 분석을 통해 실측 발견된 잠재적 취약점 및 엣지 케이스 증명 테스트
    """

    def test_tuple_length_vulnerability_demonstration(self):
        """
        [발견된 취약점 1] _parse_action에서 isinstance(action, tuple) 분기에 len(action) == 2 체크 누락
        - 현상: () 또는 (1,) 전달 시 IndexError 발생
        """
        df = create_stress_dataframe(length=10, seed=1201)
        env = HybridTradingEnv(df=df)
        env.reset()

        # 빈 튜플 주입 시 IndexError 확인
        with pytest.raises(IndexError):
            env._parse_action(())

        # 1개 요소 튜플 주입 시 IndexError 확인
        with pytest.raises(IndexError):
            env._parse_action((1,))

    def test_nan_inf_type_conversion_vulnerability_demonstration(self):
        """
        [발견된 취약점 2] _parse_action에서 float('nan') 또는 float('inf')를 act_type으로 전달 시 int() 변환 에러
        - 현상: (nan, 0.5) 전달 시 ValueError, (inf, 0.5) 전달 시 OverflowError 발생
        """
        df = create_stress_dataframe(length=10, seed=1301)
        env = HybridTradingEnv(df=df)
        env.reset()

        # (NaN, 0.5) 전달 시 ValueError 확인
        with pytest.raises(ValueError, match="cannot convert float NaN to integer"):
            env._parse_action((float("nan"), 0.5))

        # (Inf, 0.5) 전달 시 OverflowError 확인
        with pytest.raises(OverflowError, match="cannot convert float infinity to integer"):
            env._parse_action((float("inf"), 0.5))

        # {'action_type': NaN, 'position_size': 0.5} 전달 시 ValueError 확인
        with pytest.raises(ValueError, match="cannot convert float NaN to integer"):
            env._parse_action({"action_type": float("nan"), "position_size": 0.5})
