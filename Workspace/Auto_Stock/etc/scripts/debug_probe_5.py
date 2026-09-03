"""
etc/scripts/debug_probe_5.py
============================
Probe 5 Discrepancy 심층 디버깅 및 원인 규명
"""
import sys
import os
import math
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/imnyj/Workspace/Auto_Stock")

from modules.engine.mock_environment import (
    VirtualAccount,
    MockExecutionEngine,
    MockEnvironment,
    to_decimal,
    quantize_krw
)

# Test 1: Float vs Quantized Price in MockEnvironment
def test_mock_env_with_integer_prices():
    print("--- Test A: MockEnvironment with Quantized Integer Prices ---")
    np.random.seed(42)
    n_bars = 10000
    base_price = 70000.0
    returns = np.random.normal(0, 0.005, n_bars)
    price_series = np.round(base_price * np.cumprod(1.0 + returns)) # 1원 단위 반올림

    dates = pd.date_range("2026-01-01", periods=n_bars, freq="1min")
    df_bars = pd.DataFrame({
        "timestamp": dates,
        "symbol": "005930",
        "open": price_series,
        "high": price_series + 10,
        "low": price_series - 10,
        "close": price_series,
        "volume": np.random.randint(100, 10000, n_bars)
    })

    env = MockEnvironment(data_stream=df_bars, initial_capital=Decimal("100000000"), default_trade_quantity=10)
    obs = env.reset()

    for step in range(n_bars):
        action = np.random.choice([0, 1, 2], p=[0.4, 0.4, 0.2])
        obs, reward, done, info = env.step(action)

    audit = env.get_accounting_audit()
    last_p = to_decimal(price_series[-1])
    inv_passed = env.engine.verify_accounting_invariant(
        initial_capital=Decimal("100000000"),
        current_market_prices={"005930": last_p}
    )
    print(f"Quantized prices result: Invariant Passed = {inv_passed}")
    if not inv_passed:
        init_cap = Decimal("100000000")
        total_eq = env.account.get_total_equity({"005930": last_p})
        total_frictions = env.account.cumulative_commission + env.account.cumulative_tax + env.account.cumulative_slippage
        drift = env.engine._cumulative_market_drift_pnl
        print(f"LHS (init + drift) = {init_cap + drift}")
        print(f"RHS (equity + frict) = {total_eq + total_frictions}")
        print(f"Discrepancy = {init_cap + drift - (total_eq + total_frictions)}")


def test_mock_env_with_float_prices():
    print("\n--- Test B: MockEnvironment with Unquantized Float Prices ---")
    np.random.seed(42)
    n_bars = 10000
    base_price = 70000.0
    returns = np.random.normal(0, 0.005, n_bars)
    price_series = base_price * np.cumprod(1.0 + returns) # 소수점 포함 float

    dates = pd.date_range("2026-01-01", periods=n_bars, freq="1min")
    df_bars = pd.DataFrame({
        "timestamp": dates,
        "symbol": "005930",
        "open": price_series,
        "high": price_series * 1.002,
        "low": price_series * 0.998,
        "close": price_series,
        "volume": np.random.randint(100, 10000, n_bars)
    })

    env = MockEnvironment(data_stream=df_bars, initial_capital=Decimal("100000000"), default_trade_quantity=10)
    obs = env.reset()

    for step in range(n_bars):
        action = np.random.choice([0, 1, 2], p=[0.4, 0.4, 0.2])
        obs, reward, done, info = env.step(action)

    audit = env.get_accounting_audit()
    last_p = to_decimal(price_series[-1])
    inv_passed = env.engine.verify_accounting_invariant(
        initial_capital=Decimal("100000000"),
        current_market_prices={"005930": last_p}
    )
    print(f"Float prices result: Invariant Passed = {inv_passed}")
    if not inv_passed:
        init_cap = Decimal("100000000")
        total_eq = env.account.get_total_equity({"005930": last_p})
        total_frictions = env.account.cumulative_commission + env.account.cumulative_tax + env.account.cumulative_slippage
        drift = env.engine._cumulative_market_drift_pnl
        print(f"LHS (init + drift) = {init_cap + drift}")
        print(f"RHS (equity + frict) = {total_eq + total_frictions}")
        print(f"Discrepancy = {init_cap + drift - (total_eq + total_frictions)}")


if __name__ == "__main__":
    test_mock_env_with_integer_prices()
    test_mock_env_with_float_prices()
