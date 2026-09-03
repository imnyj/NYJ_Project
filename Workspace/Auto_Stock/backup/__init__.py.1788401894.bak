"""
modules/engine/__init__.py
==========================
Auto Stock ML/RL Trader — Phase 2 & Phase 3: 엔진 패키지

- Phase 2: 가상 체결 엔진 (VirtualAccount, MockExecutionEngine, DummyStrategySimulator, MockEnvironment)
- Phase 3: 수동 매매 제어기 (ManualTrader)
"""

from modules.engine.manual_trader import ManualTrader
from modules.engine.hybrid_trading_env import HybridTradingEnv, ContinuousToHybridActionWrapper
from modules.engine.mock_environment import (
    # Data Models & Enums
    AccountingInvariantError,
    AccountSnapshot,
    ActionType,
    DummyStrategySimulator,
    EngineError,
    FeeConfig,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidOrderError,
    MockEnvironment,
    MockExecutionEngine,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TradeRecord,
    VirtualAccount,
    quantize_krw,
    to_decimal,
)

__all__ = [
    # Phase 2 Enums
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "ActionType",
    # Phase 2 Config & Models
    "FeeConfig",
    "Position",
    "Order",
    "TradeRecord",
    "AccountSnapshot",
    # Phase 2 Exceptions
    "EngineError",
    "InsufficientFundsError",
    "InsufficientSharesError",
    "InvalidOrderError",
    "AccountingInvariantError",
    # Phase 2 Utilities
    "to_decimal",
    "quantize_krw",
    # Phase 2 Core Classes
    "VirtualAccount",
    "MockExecutionEngine",
    "DummyStrategySimulator",
    "MockEnvironment",
    # Phase 3 Core Classes
    "ManualTrader",
    # Milestone 1 Core Classes
    "HybridTradingEnv",
    "ContinuousToHybridActionWrapper",
]

