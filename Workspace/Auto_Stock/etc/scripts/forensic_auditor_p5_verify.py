#!/usr/bin/env python3
"""
etc/scripts/forensic_auditor_p5_verify.py
=========================================
Forensic Integrity Audit & Deep Stress-Testing for Auto_Stock Phase 5:
- AST Analysis for hardcoded values, dummy asserts, and facades
- Mathematical Boundary Precision & Filtering Logic
- Multi-threaded Concurrency & Thread-Safety
- RL Simulator Integration & Gymnasium Spec Compliance
- Zero Division & Adversarial Input Robustness
"""

import ast
import inspect
import math
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

PROJECT_ROOT = "/home/imnyj/Workspace/Auto_Stock"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.data.screener import (
    ScreeningCriteria,
    StockScreener,
    TokenBucketLimiter,
    ShardedPollingScheduler,
    DynamicStockScreener,
    ScreenerConfig,
)
from modules.data.streamer import TickData
from modules.engine.live_learning_simulator import LiveLearningSimulator
from modules.engine.mock_environment import ActionType, FeeConfig


def audit_ast_analysis():
    print("==================================================")
    print("1. AST ANALYSIS: Hardcoding & Facade Scan")
    print("==================================================")

    targets = [
        "modules/data/screener.py",
        "modules/engine/live_learning_simulator.py",
        "tests/test_phase5_screener.py",
    ]

    violations = []

    for rel_path in targets:
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=rel_path)

        # 1. Look for suspicious hardcoded string checks in if statements
        # e.g., if symbol == "005930": return ...
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check comparison
                if isinstance(node.test, ast.Compare):
                    left = node.test.left
                    comparators = node.test.comparators
                    for comp in comparators:
                        if isinstance(comp, ast.Constant) and comp.value in ["005930", "000660"]:
                            # Check if it returns a constant or True
                            for stmt in node.body:
                                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                                    if stmt.value.value in [True, "005930", "000660"]:
                                        violations.append(
                                            f"Hardcoded bypass in {rel_path}:{node.lineno} -> {ast.unparse(node.test)}"
                                        )

            # 2. In tests, check for trivial dummy asserts e.g., assert True, assert 1 == 1
            if "test_" in rel_path:
                if isinstance(node, ast.Assert):
                    if isinstance(node.test, ast.Constant) and node.test.value is True:
                        violations.append(f"Dummy 'assert True' in {rel_path}:{node.lineno}")
                    elif isinstance(node.test, ast.Compare):
                        if (
                            isinstance(node.test.left, ast.Constant)
                            and len(node.test.comparators) == 1
                            and isinstance(node.test.comparators[0], ast.Constant)
                        ):
                            if node.test.left.value == node.test.comparators[0].value:
                                violations.append(
                                    f"Trivial self-certifying assert in {rel_path}:{node.lineno} -> {ast.unparse(node.test)}"
                                )

            # 3. Look for facade functions (only pass or return constant)
            if "modules/" in rel_path and isinstance(node, ast.FunctionDef):
                if len(node.body) == 1:
                    stmt = node.body[0]
                    if isinstance(stmt, ast.Pass):
                        violations.append(f"Facade pass-only function in {rel_path}:{node.lineno} -> {node.name}")
                    elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                        # Some helper properties can return a constant, but check method names
                        if node.name in ["update_daily_static_pool", "check_intraday_trigger", "step_symbol"]:
                            violations.append(f"Facade constant-return core method in {rel_path}:{node.lineno} -> {node.name}")

    if violations:
        print(f"❌ AST Violations Detected ({len(violations)}):")
        for v in violations:
            print("  -", v)
        return False
    else:
        print("✅ AST Analysis CLEAN: No hardcoded test bypasses, dummy asserts, or facade core functions detected.")
        return True


def audit_mathematical_filtering_precision():
    print("\n==================================================")
    print("2. MATHEMATICAL BOUNDARY & FILTERING LOGIC AUDIT")
    print("==================================================")

    screener = StockScreener()

    # Boundary test dataset: exactly 1000억 vs 999.999999억
    # PER exactly 1.0, 15.0 vs 0.9999, 15.0001
    # PBR exactly 0.1, 2.0 vs 0.0999, 2.0001
    df = pd.DataFrame([
        # 1. Pass: exactly at lower boundaries (1000억, PER 1.0, PBR 0.1)
        {"symbol": "100001", "market_cap": 100_000_000_000, "per": 1.0, "pbr": 0.1, "foreign_net_buy": 0, "inst_net_buy": 0},
        # 2. Pass: exactly at upper boundaries (1000억, PER 15.0, PBR 2.0)
        {"symbol": "100002", "market_cap": 100_000_000_000, "per": 15.0, "pbr": 2.0, "foreign_net_buy": 0, "inst_net_buy": 0},
        # 3. Fail: market cap 99,999,999,999
        {"symbol": "200001", "market_cap": 99_999_999_999, "per": 5.0, "pbr": 1.0, "foreign_net_buy": 0, "inst_net_buy": 0},
        # 4. Fail: PER 0.9999
        {"symbol": "200002", "market_cap": 200_000_000_000, "per": 0.9999, "pbr": 1.0, "foreign_net_buy": 0, "inst_net_buy": 0},
        # 5. Fail: PER 15.0001
        {"symbol": "200003", "market_cap": 200_000_000_000, "per": 15.0001, "pbr": 1.0, "foreign_net_buy": 0, "inst_net_buy": 0},
        # 6. Fail: PBR 0.0999
        {"symbol": "200004", "market_cap": 200_000_000_000, "per": 5.0, "pbr": 0.0999, "foreign_net_buy": 0, "inst_net_buy": 0},
        # 7. Fail: PBR 2.0001
        {"symbol": "200005", "market_cap": 200_000_000_000, "per": 5.0, "pbr": 2.0001, "foreign_net_buy": 0, "inst_net_buy": 0},
        # 8. Fail: foreign_net_buy negative
        {"symbol": "200006", "market_cap": 200_000_000_000, "per": 5.0, "pbr": 1.0, "foreign_net_buy": -1, "inst_net_buy": 100},
        # 9. Fail: inst_net_buy negative
        {"symbol": "200007", "market_cap": 200_000_000_000, "per": 5.0, "pbr": 1.0, "foreign_net_buy": 100, "inst_net_buy": -1},
    ])

    pool = screener.update_daily_static_pool(df)
    expected_pass = ["100001", "100002"]
    unexpected_pass = [s for s in pool if s not in expected_pass]
    missing_pass = [s for s in expected_pass if s not in pool]

    if unexpected_pass or missing_pass:
        print(f"❌ Filtering Logic Failure! unexpected: {unexpected_pass}, missing: {missing_pass}")
        return False
    print("✅ Static Daily Filter boundary precision verified: Exact lower/upper boundaries included, off-by-one/infinitesimal out-of-bounds excluded.")

    # Trigger boundary test
    screener.candidate_pool = ["100001"]
    screener.candidate_set = {"100001"}

    # Base: open_price=10000, base_volume=10000
    # Exactly 3% gain -> price=10300
    # Exactly 300% volume surge -> accum_volume = 30000 (3.0x)
    t0 = datetime(2026, 9, 3, 10, 0, 0)
    
    # 1. Exact boundary -> Triggered!
    trig_exact = screener.check_intraday_trigger({
        "symbol": "100001", "open_price": 10000, "price": 10300,
        "accum_volume": 30000, "prev_same_time_volume": 10000,
        "timestamp": t0
    })
    assert trig_exact == "100001", f"Exact boundary trigger failed: got {trig_exact}"

    # 2. 2.999% gain -> Not triggered
    screener._last_triggered_time.clear()
    trig_low_price = screener.check_intraday_trigger({
        "symbol": "100001", "open_price": 10000, "price": 10299.9,
        "accum_volume": 30000, "prev_same_time_volume": 10000,
        "timestamp": t0
    })
    assert trig_low_price is None, f"Price below threshold triggered: got {trig_low_price}"

    # 3. 2.999x volume -> Not triggered
    screener._last_triggered_time.clear()
    trig_low_vol = screener.check_intraday_trigger({
        "symbol": "100001", "open_price": 10000, "price": 10300,
        "accum_volume": 29999, "prev_same_time_volume": 10000,
        "timestamp": t0
    })
    assert trig_low_vol is None, f"Volume below threshold triggered: got {trig_low_vol}"

    print("✅ Dynamic Momentum Trigger boundary precision verified: 3.00x volume & +3.00% price strictly enforced.")
    return True


def audit_adversarial_inputs_and_robustness():
    print("\n==================================================")
    print("3. ADVERSARIAL INPUTS & EXCEPTION ROBUSTNESS AUDIT")
    print("==================================================")

    screener = StockScreener()
    screener.candidate_pool = ["005930"]
    screener.candidate_set = {"005930"}

    # Stress test zero division, NaN, Inf, None, negative numbers
    adversarial_ticks = [
        {"symbol": "005930", "open_price": 0, "price": 10000, "accum_volume": 10000, "prev_same_time_volume": 1000},
        {"symbol": "005930", "open_price": 10000, "price": float("nan"), "accum_volume": 10000, "prev_same_time_volume": 1000},
        {"symbol": "005930", "open_price": float("nan"), "price": 10000, "accum_volume": 10000, "prev_same_time_volume": 1000},
        {"symbol": "005930", "open_price": 10000, "price": float("inf"), "accum_volume": 10000, "prev_same_time_volume": 1000},
        {"symbol": "005930", "open_price": 10000, "price": 10500, "accum_volume": 50000, "prev_same_time_volume": 0},
        {"symbol": "005930", "open_price": 10000, "price": 10500, "accum_volume": 50000, "prev_same_time_volume": -500},
        {"symbol": "005930", "open_price": -10000, "price": 10500, "accum_volume": 50000, "prev_same_time_volume": 1000},
        {"symbol": "", "open_price": 10000, "price": 10500, "accum_volume": 50000, "prev_same_time_volume": 1000},
        {"symbol": None, "open_price": 10000, "price": 10500, "accum_volume": 50000, "prev_same_time_volume": 1000},
        {"symbol": "000000", "open_price": 10000, "price": 10500, "accum_volume": 50000, "prev_same_time_volume": 1000},
    ]

    for i, t in enumerate(adversarial_ticks):
        try:
            res = screener.check_intraday_trigger(t)
            assert res is None, f"Adversarial tick #{i} returned unexpected trigger: {res}"
        except Exception as e:
            print(f"❌ Adversarial tick #{i} raised exception: {type(e).__name__}: {e}")
            return False

    print("✅ Adversarial inputs handled safely: 0 exceptions, 0 unintended triggers on dirty/corrupted inputs.")
    return True


def audit_multithreaded_concurrency():
    print("\n==================================================")
    print("4. MULTITHREADED CONCURRENCY & DEADLOCK AUDIT")
    print("==================================================")

    screener = StockScreener()
    symbols = [f"{i:06d}" for i in range(50)]
    screener.candidate_pool = list(symbols)
    screener.candidate_set = set(symbols)

    errors = []
    triggers = []

    def worker_thread(thread_id: int):
        try:
            for s_idx in range(50):
                sym = f"{s_idx:06d}"
                tick = {
                    "symbol": sym,
                    "price": 10500.0,
                    "open_price": 10000.0,
                    "accum_volume": 40000,
                    "prev_same_time_volume": 10000,
                    "timestamp": datetime.now(),
                }
                trig = screener.check_intraday_trigger(tick)
                if trig:
                    triggers.append((thread_id, trig))
                time.sleep(0.0001)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker_thread, args=(i,)) for i in range(20)]
    start_t = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    elapsed = time.time() - start_t

    if errors:
        print(f"❌ Concurrency errors encountered: {errors}")
        return False
    if elapsed > 5.0:
        print(f"❌ Possible deadlock or contention timeout: {elapsed:.2f}s")
        return False

    print(f"✅ Concurrency audit PASSED: 20 threads, 1,000 tick evaluations in {elapsed:.3f}s, 0 errors, 0 deadlocks.")
    return True


def audit_rl_simulator_integration():
    print("\n==================================================")
    print("5. RL SIMULATOR INTEGRATION & CONSERVATION AUDIT")
    print("==================================================")

    from core.kiwoom_api import PriceQuote

    with patch("core.kiwoom_api.KiwoomClient.get_current_price") as mock_get_price:
        mock_get_price.return_value = PriceQuote(
            symbol="005930",
            current_price=Decimal("70000"),
            price_change=Decimal("0"),
            change_rate=Decimal("0"),
            open_price=Decimal("68000"),
            high_price=Decimal("71000"),
            low_price=Decimal("68000"),
            volume=50000,
            trade_amount=Decimal("0"),
            timestamp=datetime.now(),
        )

        sim = LiveLearningSimulator(initial_cash=10_000_000)

        # 1. Inject symbol
        injected = sim.inject_triggered_symbol("005930", trigger_info={
            "price": 70000, "open_price": 68000, "accum_volume": 500000
        })
        assert injected is True
        assert "005930" in sim.active_pool

        # 2. Build RL Observation
        obs = sim.build_rl_observation("005930")
        assert obs.shape == (14,), f"Invalid obs shape: {obs.shape}"
        assert obs.dtype == np.float32, f"Invalid obs dtype: {obs.dtype}"
        assert not np.isnan(obs).any(), "NaN found in observation"
        assert not np.isinf(obs).any(), "Inf found in observation"

        # Check market feature return from open: (70000 - 68000) / 68000 = 0.0294117...
        expected_ret = (70000.0 - 68000.0) / 68000.0
        assert math.isclose(obs[0], expected_ret, rel_tol=1e-3), f"Observation feature 0 mismatch: {obs[0]} vs {expected_ret}"

        # 3. Step symbol BUY 50%
        init_equity = float(sim.account.get_total_equity({"005930": Decimal("70000")}))
        obs, reward, terminated, truncated, info = sim.step_symbol(
            "005930", ActionType.BUY, position_weight=0.5
        )
        assert obs.shape == (14,)
        assert info["trade"] is not None
        assert info["trade"].is_success is True
        assert info["trade"].quantity > 0
        assert terminated is False
        assert truncated is False

        # Equity accounting check
        post_equity = float(sim.account.get_total_equity({"005930": Decimal("70000")}))
        friction = (
            float(sim.account.cumulative_commission)
            + float(sim.account.cumulative_tax)
            + float(sim.account.cumulative_slippage)
        )
        # Total equity post trade should be init_equity - friction
        assert math.isclose(post_equity + friction, init_equity, rel_tol=1e-3), (
            f"Equity conservation violated: post_equity={post_equity}, friction={friction}, init_equity={init_equity}"
        )

    print("✅ RL Simulator Integration & Equity Conservation verified: 14-dim observation valid, trading order executed, equity conserved minus exact transaction frictions.")
    return True


if __name__ == "__main__":
    t1 = audit_ast_analysis()
    t2 = audit_mathematical_filtering_precision()
    t3 = audit_adversarial_inputs_and_robustness()
    t4 = audit_multithreaded_concurrency()
    t5 = audit_rl_simulator_integration()

    all_passed = t1 and t2 and t3 and t4 and t5
    print("\n" + "="*50)
    print(f"FINAL AUDIT VERDICT: {'ALL CLEAN (PASS)' if all_passed else 'INTEGRITY VIOLATION (FAIL)'}")
    print("="*50)
    sys.exit(0 if all_passed else 1)
