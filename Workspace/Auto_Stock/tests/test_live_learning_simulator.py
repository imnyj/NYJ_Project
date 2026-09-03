import threading
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from core.kiwoom_api import PriceQuote
from modules.engine.live_learning_simulator import (
    LiveLearningSimulator,
    get_live_simulator,
    reset_global_simulator,
)
from modules.engine.mock_environment import ActionType


@patch("core.kiwoom_api.KiwoomClient.get_current_price")
def test_live_learning_simulator(mock_get_price):
    # Mocking the KiwoomClient response
    mock_get_price.return_value = PriceQuote(
        symbol="005930",
        current_price=Decimal("80000"),
        price_change=Decimal("0"),
        change_rate=Decimal("0"),
        open_price=Decimal("80000"),
        high_price=Decimal("80000"),
        low_price=Decimal("80000"),
        volume=1000,
        trade_amount=Decimal("0"),
        timestamp=datetime.now(),
    )

    # Initialize Simulator
    sim = LiveLearningSimulator(initial_cash=1000000)

    # Check initial state
    state = sim.get_state("005930")
    assert state["cash_balance"] == 1000000.0

    # 1. Buy action (Gymnasium 1.2.0 5-tuple: obs, reward, terminated, truncated, info)
    state, reward, terminated, truncated, info = sim.step("005930", ActionType.BUY, quantity=10)

    assert info["trade"].is_success is True
    assert info["trade"].quantity == 10
    assert state["holding_quantity"] == 10
    assert state["cash_balance"] < 1000000.0
    assert isinstance(reward, float)
    assert terminated is False
    assert truncated is False

    # 2. Hold action
    state, reward, terminated, truncated, info = sim.step("005930", ActionType.HOLD)
    assert info["trade"] is None
    assert isinstance(reward, float)
    assert terminated is False
    assert truncated is False

    # 3. Sell action
    state, reward, terminated, truncated, info = sim.step("005930", ActionType.SELL, quantity=5)
    assert info["trade"].is_success is True
    assert state["holding_quantity"] == 5
    assert isinstance(reward, float)
    assert terminated is False
    assert truncated is False


def test_global_singleton():
    reset_global_simulator()
    sim1 = get_live_simulator(initial_cash=500000)
    sim2 = get_live_simulator()
    assert sim1 is sim2
    assert sim1.initial_cash == Decimal("500000")
    reset_global_simulator()


def test_global_singleton_thread_safety():
    """다중 스레드 환경에서 싱글톤 인스턴스 원자적 생성 및 동일성 검증"""
    reset_global_simulator()
    instances = []

    def _worker():
        instances.append(get_live_simulator(initial_cash=777000))

    threads = [threading.Thread(target=_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(instances) == 10
    first_inst = instances[0]
    for inst in instances:
        assert inst is first_inst
    assert first_inst.initial_cash == Decimal("777000")
    reset_global_simulator()
