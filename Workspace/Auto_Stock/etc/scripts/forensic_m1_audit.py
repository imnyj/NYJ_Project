"""
etc/scripts/forensic_m1_audit.py
================================
Milestone 1 Forensic Integrity Verification Script
"""

import ast
import inspect
import math
import sys
from decimal import Decimal
import numpy as np
import pandas as pd

from modules.engine.hybrid_trading_env import (
    HybridTradingEnv,
    ContinuousToHybridActionWrapper,
)
from modules.engine.mock_environment import (
    ActionType,
    FeeConfig,
    MockExecutionEngine,
    OrderSide,
    VirtualAccount,
    quantize_krw,
    to_decimal,
)


def run_static_ast_checks():
    print("=== [Check 1] Source Code AST & Static Analysis ===")
    with open("modules/engine/hybrid_trading_env.py", "r", encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src)
    
    # 1. Look for suspicious dummy constants or hardcoded pass-throughs
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check for functions returning constant strings like "PASS" or True unconditionally
            if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                ret_val = node.body[0].value
                if isinstance(ret_val, ast.Constant):
                    # exclude close() or trivial properties if any
                    violations.append(f"Suspicious 1-line constant return in function '{node.name}': {ret_val.value}")
    
    # 2. Check for mocked or fake imports in production code
    if "unittest.mock" in src or "MagicMock" in src or "Mock(" in src:
        violations.append("Production code contains mock imports or mock instances!")
        
    print(f"AST Analysis complete. Found {len(violations)} violations.")
    for v in violations:
        print(f"  [VIOLATION] {v}")
    return len(violations) == 0


def run_runtime_accounting_trace():
    print("\n=== [Check 2] Runtime Dynamic Accounting & Hybrid Sizing Trace ===")
    
    # Create controlled 10-step dataframe with fixed 70,000 KRW price
    dates = pd.date_range("2026-01-01", periods=10, freq="B")
    df = pd.DataFrame({
        "date": dates,
        "symbol": "005930",
        "open": [70000.0] * 10,
        "high": [70000.0] * 10,
        "low": [70000.0] * 10,
        "close": [70000.0] * 10,
        "volume": [500000] * 10,
        "returns_1d": [0.0] * 10,
        "log_return": [0.0] * 10,
        "volatility_20d": [0.015] * 10,
        "ma_5": [70000.0] * 10,
        "ma_20": [70000.0] * 10,
        "ma_60": [70000.0] * 10,
        "dynamic_per": [15.0] * 10,
        "dynamic_pbr": [1.5] * 10,
        "dynamic_market_cap": [4.2e14] * 10,
    })
    
    fee_config = FeeConfig(
        commission_rate=Decimal("0.00015"),  # 0.015%
        tax_rate=Decimal("0.0018"),         # 0.18%
        slippage_rate=Decimal("0.0010"),    # 0.1%
    )
    
    env = HybridTradingEnv(df=df, initial_cash=10_000_000, fee_config=fee_config)
    obs, info = env.reset()
    
    initial_cash = Decimal("10000000")
    assert env.account.cash_balance == initial_cash
    assert env.account.get_position("005930").quantity == 0
    
    # 1. Step 1: BUY 50%
    # Expected cost per share = 70000 * 1.0010 * 1.00015 = 70080.5105
    # Budget = 10,000,000 * 0.5 = 5,000,000
    # Expected target_qty = int(5000000 / 70080.5105) = 71 shares
    obs, rew, term, trunc, info = env.step((1, np.array([0.5], dtype=np.float32)))
    trade = info["trade_record"]
    
    print(f"Step 1 (BUY 50%):")
    print(f"  Executed Qty: {trade.quantity} (Expected: 71)")
    print(f"  Executed Price: {trade.executed_price} (Expected: 70070)")
    print(f"  Gross Amount: {trade.gross_amount} (Expected: 4,974,970)")
    print(f"  Commission: {trade.commission} (Expected: 746)")
    print(f"  Tax: {trade.tax} (Expected: 0)")
    print(f"  Slippage Cost: {trade.slippage_cost} (Expected: 4,970)")
    print(f"  Remaining Cash: {env.account.cash_balance} (Expected: 5,024,284)")
    print(f"  Holdings: {env.account.get_position('005930').quantity} (Expected: 71)")
    print(f"  Total Equity: {info['total_equity']} (Expected: 9,994,284.0)")
    print(f"  Reward (Log Equity Return): {rew:.8f}")
    
    assert trade.quantity == 71
    assert trade.executed_price == Decimal("70070")
    assert trade.gross_amount == Decimal("4974970")
    assert trade.commission == Decimal("746")
    assert trade.tax == Decimal("0")
    assert trade.slippage_cost == Decimal("4970")
    assert env.account.cash_balance == Decimal("5024284")
    assert env.account.get_position("005930").quantity == 71
    assert env.verify_accounting_invariant() is True
    
    # 2. Step 2: SELL 50% of holding (35 shares)
    # Expected target_qty = int(71 * 0.5) = 35 shares
    # Executed price = 70000 * (1 - 0.001) = 69930
    # Gross Amount = 35 * 69930 = 2,447,550
    # Commission = 2,447,550 * 0.00015 = 367
    # Tax = 2,447,550 * 0.0018 = 4,405
    # Net cash added = 2,447,550 - 367 - 4,405 = 2,442,778
    # New Cash = 5,024,284 + 2,442,778 = 7,467,062
    # Remaining Holdings = 71 - 35 = 36 shares
    obs, rew, term, trunc, info = env.step((2, np.array([0.5], dtype=np.float32)))
    trade_sell = info["trade_record"]
    
    print(f"\nStep 2 (SELL 50%):")
    print(f"  Executed Qty: {trade_sell.quantity} (Expected: 35)")
    print(f"  Executed Price: {trade_sell.executed_price} (Expected: 69930)")
    print(f"  Gross Amount: {trade_sell.gross_amount} (Expected: 2,447,550)")
    print(f"  Commission: {trade_sell.commission} (Expected: 367)")
    print(f"  Tax: {trade_sell.tax} (Expected: 4,405)")
    print(f"  Slippage Cost: {trade_sell.slippage_cost} (Expected: 2,450)")
    print(f"  Remaining Cash: {env.account.cash_balance} (Expected: 7,467,062)")
    print(f"  Holdings: {env.account.get_position('005930').quantity} (Expected: 36)")
    print(f"  Realized PnL: {env.account.realized_pnl} (Expected: -11,722)")
    print(f"  Total Equity: {info['total_equity']}")
    
    assert trade_sell.quantity == 35
    assert trade_sell.executed_price == Decimal("69930")
    assert trade_sell.gross_amount == Decimal("2447550")
    assert trade_sell.commission == Decimal("367")
    assert trade_sell.tax == Decimal("4405")
    assert trade_sell.slippage_cost == Decimal("2450")
    assert env.account.cash_balance == Decimal("7467062")
    assert env.account.get_position("005930").quantity == 36
    assert env.verify_accounting_invariant() is True
    
    # 3. Step 3: SELL 100% (remaining 36 shares)
    obs, rew, term, trunc, info = env.step((2, np.array([1.0], dtype=np.float32)))
    trade_sell_all = info["trade_record"]
    assert trade_sell_all.quantity == 36
    assert env.account.get_position("005930").quantity == 0
    assert env.verify_accounting_invariant() is True
    print(f"\nStep 3 (SELL 100%): All shares cleared, holdings = 0, invariant valid.")

    print("Runtime dynamic accounting check: PASSED with 100% exact mathematical match.")
    return True


def run_adversarial_stress_tests():
    print("\n=== [Check 3] Adversarial Stress-Tests & Edge-Cases ===")
    
    # 1. Check boundary action clipping
    env = HybridTradingEnv(initial_cash=10_000_000)
    env.reset()
    
    test_cases = [
        ((1, np.array([1.5], dtype=np.float32)), "Weight > 1.0 clipping"),
        ((1, np.array([-0.5], dtype=np.float32)), "Negative weight clipping"),
        ((5, np.array([0.5], dtype=np.float32)), "Invalid action type (5) clipping to SELL(2)"),
        ((-3, np.array([0.5], dtype=np.float32)), "Invalid action type (-3) clipping to HOLD(0)"),
        ((1, np.array([float('nan')], dtype=np.float32)), "NaN weight fallback to 0.0"),
        (np.array([0.8, 0.5]), "Continuous Box Signal [0.8, 0.5] -> BUY 50%"),
        (np.array([-0.8, 0.5]), "Continuous Box Signal [-0.8, 0.5] -> SELL 50%"),
        (np.array([0.0, 0.5]), "Continuous Box Signal [0.0, 0.5] -> HOLD"),
        ({"action_type": 1, "position_size": np.array([0.2], dtype=np.float32)}, "Dict action format"),
        (ActionType.BUY, "Pure Enum ActionType"),
        (0.85, "Scalar continuous float BUY"),
        (-0.85, "Scalar continuous float SELL"),
        (0.05, "Scalar continuous float HOLD"),
    ]
    
    for action, desc in test_cases:
        try:
            obs, rew, term, trunc, info = env.step(action)
            assert np.all(np.isfinite(obs)), f"Obs has non-finite values on {desc}"
            assert not math.isnan(rew), f"Reward is NaN on {desc}"
            print(f"  [PASS] {desc}: step() succeeded cleanly without crashes.")
        except Exception as e:
            print(f"  [FAIL] {desc}: Exception raised: {e}")
            return False
            
    # 2. Check Observation Space Dimension and Integrity
    assert obs.shape == (14,), f"Obs shape is {obs.shape}, expected (14,)"
    print("  [PASS] Observation space shape strictly verified as 14-dimensional vector.")
    
    # 3. Check Live Mode fallback & integration
    env_live = HybridTradingEnv(mode="live", initial_cash=10_000_000, max_steps=5)
    obs_live, info_live = env_live.reset()
    assert obs_live.shape == (14,)
    print("  [PASS] Live mode initialization and reset verified.")

    return True


if __name__ == "__main__":
    c1 = run_static_ast_checks()
    c2 = run_runtime_accounting_trace()
    c3 = run_adversarial_stress_tests()
    
    if c1 and c2 and c3:
        print("\n>>> ALL FORENSIC INTEGRITY CHECKS PASSED <<<")
        sys.exit(0)
    else:
        print("\n>>> FORENSIC INTEGRITY VIOLATION DETECTED <<<")
        sys.exit(1)
