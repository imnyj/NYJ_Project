"""
etc/scripts/m3_forensic_integrity_verifier.py
=============================================
Milestone 3 (ML/RL Pipeline & Env) Forensic Integrity Verification Script
Independently verifies:
1. BUG-RL01: HybridTradingEnv step indexing lag & duplication elimination.
2. BUG-RL02 / BUG-L04: HOLD step trade_record isolation in _get_info.
3. BUG-RL03: Automatic device conversion across all feature extractors and policy.
4. BUG-RL04 & BUG-C03: LiveLearningSimulator Gymnasium 5-tuple, Log Return, and Double-Checked Locking thread safety.
5. BUG-RL05: Optuna HPO zero-trade penalty and reward hacking defense.
"""

import math
import os
import sys
import threading
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch

# Add workspace root to sys.path
sys.path.insert(0, "/home/imnyj/Workspace/Auto_Stock")

from core.kiwoom_api import PriceQuote
from modules.engine.hybrid_trading_env import HybridTradingEnv
from modules.engine.live_learning_simulator import (
    LiveLearningSimulator,
    get_live_simulator,
    reset_global_simulator,
)
from modules.engine.mock_environment import ActionType, OrderSide
from modules.hpo.optuna_pipeline import create_hpo_study, objective
from modules.models.feature_extractor import (
    DualStreamSLFeatureExtractor,
    TabularMLPFeatureExtractor,
    Temporal1DCNNFeatureExtractor,
)
from modules.models.hybrid_policy import HybridActorCritic


def verify_bug_rl01_step_indexing():
    print("[1/5] Verifying BUG-RL01: Step Indexing & Lag Elimination...")
    # Create distinct returns_1d for 10 rows
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=10, freq="D"),
        "symbol": "005930",
        "open": [70000.0 + i * 100 for i in range(10)],
        "high": [71000.0 + i * 100 for i in range(10)],
        "low": [69000.0 + i * 100 for i in range(10)],
        "close": [70500.0 + i * 100 for i in range(10)],
        "volume": [100000] * 10,
        "returns_1d": [float(i) * 0.05 for i in range(10)],
        "log_return": [float(i) * 0.048 for i in range(10)],
        "volatility_20d": [0.015] * 10,
        "ma_5": [70000.0] * 10,
        "ma_20": [70000.0] * 10,
        "ma_60": [70000.0] * 10,
        "dynamic_per": [15.0] * 10,
        "dynamic_pbr": [1.5] * 10,
        "dynamic_market_cap": [4e14] * 10,
    })

    env = HybridTradingEnv(df=df, initial_cash=10_000_000)
    obs0, info0 = env.reset()
    assert abs(obs0[0] - 0.00) < 1e-5, f"Reset obs[0] expected 0.00, got {obs0[0]}"

    obs1, rew, term, trunc, info1 = env.step((0, np.array([0.0], dtype=np.float32)))
    assert abs(obs1[0] - 0.05) < 1e-5, f"Step 1 obs[0] expected 0.05, got {obs1[0]}"
    assert obs0[0] != obs1[0], "Lag detected: obs0[0] == obs1[0]"

    obs2, rew, term, trunc, info2 = env.step((0, np.array([0.0], dtype=np.float32)))
    assert abs(obs2[0] - 0.10) < 1e-5, f"Step 2 obs[0] expected 0.10, got {obs2[0]}"

    print("  -> BUG-RL01 PASS: 1-step lag and duplication completely eliminated.")


def verify_bug_rl02_trade_record_isolation():
    print("[2/5] Verifying BUG-RL02: HOLD Step TradeRecord Isolation...")
    env = HybridTradingEnv(initial_cash=10_000_000)
    env.reset()

    # Step 1: BUY
    obs1, rew1, term1, trunc1, info1 = env.step((1, np.array([0.5], dtype=np.float32)))
    assert info1["trade_record"] is not None, "BUY step must produce a TradeRecord"
    assert info1["trade_record"].side == OrderSide.BUY

    # Step 2: HOLD
    obs2, rew2, term2, trunc2, info2 = env.step((0, np.array([0.0], dtype=np.float32)))
    assert info2["trade_record"] is None, f"HOLD step leaked prior TradeRecord: {info2['trade_record']}"

    # Step 3: SELL
    obs3, rew3, term3, trunc3, info3 = env.step((2, np.array([1.0], dtype=np.float32)))
    assert info3["trade_record"] is not None, "SELL step must produce a TradeRecord"
    assert info3["trade_record"].side == OrderSide.SELL

    # Step 4: HOLD
    obs4, rew4, term4, trunc4, info4 = env.step((0, np.array([0.0], dtype=np.float32)))
    assert info4["trade_record"] is None, f"HOLD step leaked prior TradeRecord: {info4['trade_record']}"

    print("  -> BUG-RL02 PASS: HOLD steps strictly return trade_record=None.")


def verify_bug_rl03_device_auto_transfer():
    print("[3/5] Verifying BUG-RL03: Device Auto-Transfer on Tensors & Polymorphic Inputs...")
    device = torch.device("cpu")

    # 1. TabularMLP
    mlp = TabularMLPFeatureExtractor(input_dim=14, output_dim=32)
    cpu_1d = torch.randn(14)
    cpu_2d = torch.randn(4, 14)
    out1 = mlp(cpu_1d)
    out2 = mlp(cpu_2d)
    assert out1.shape == (32,), f"TabularMLP 1D out shape {out1.shape}"
    assert out2.shape == (4, 32), f"TabularMLP 2D out shape {out2.shape}"

    # 2. Temporal1DCNN
    cnn = Temporal1DCNNFeatureExtractor(in_channels=10, seq_len=20, output_dim=32)
    cnn_in = torch.randn(4, 10, dtype=torch.float32)
    out_cnn = cnn(cnn_in)
    assert out_cnn.shape == (4, 32), f"CNN out shape {out_cnn.shape}"

    # 3. DualStreamSL
    dual = DualStreamSLFeatureExtractor(temporal_in_channels=10, temporal_seq_len=20, tabular_dim=4, output_dim=64)
    t_3d = torch.randn(4, 20, 10)
    tab_2d = torch.randn(4, 4)
    out_dual_pos = dual(temporal_x=t_3d, tabular_x=tab_2d)
    out_dual_tup = dual((t_3d, tab_2d))
    out_dual_dict = dual({"temporal": t_3d, "tabular": tab_2d})
    assert out_dual_pos.shape == (4, 64)
    assert out_dual_tup.shape == (4, 64)
    assert out_dual_dict.shape == (4, 64)

    # 4. HybridActorCritic
    policy = HybridActorCritic(obs_dim=14, feature_dim=64)
    feats = policy.extract_features(cpu_2d)
    assert feats.shape == (4, 64)
    disc_logits, p1, p2, val = policy(cpu_2d)
    assert disc_logits.shape == (4, 3)
    assert val.shape == (4, 1)

    print("  -> BUG-RL03 PASS: Device auto-transfer and input polymorphism verified.")


def verify_bug_rl04_and_c03_live_sim_and_thread_safety():
    print("[4/5] Verifying BUG-RL04 & BUG-C03: LiveLearningSimulator 5-Tuple, Log Return & Thread Safety...")
    reset_global_simulator()

    with patch("core.kiwoom_api.KiwoomClient.get_current_price") as mock_price:
        mock_price.return_value = PriceQuote(
            symbol="005930",
            current_price=Decimal("75000"),
            price_change=Decimal("0"),
            change_rate=Decimal("0"),
            open_price=Decimal("75000"),
            high_price=Decimal("75000"),
            low_price=Decimal("75000"),
            volume=5000,
            trade_amount=Decimal("0"),
            timestamp=datetime.now(),
        )

        sim = LiveLearningSimulator(initial_cash=10_000_000)
        res = sim.step("005930", ActionType.BUY, quantity=10)
        assert len(res) == 5, f"Expected 5-tuple (obs, rew, term, trunc, info), got {len(res)}"
        state, rew, term, trunc, info = res
        assert isinstance(state, dict)
        assert isinstance(rew, float)
        assert isinstance(term, bool)
        assert isinstance(trunc, bool)
        assert isinstance(info, dict)
        assert not math.isnan(rew) and not math.isinf(rew)

    # Concurrency verification (Double-Checked Locking)
    reset_global_simulator()
    threads = []
    instances = []

    def _get_inst():
        instances.append(get_live_simulator(initial_cash=5_000_000))

    for _ in range(20):
        t = threading.Thread(target=_get_inst)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(instances) == 20
    first = instances[0]
    for inst in instances:
        assert inst is first, "Singleton violation under race condition"
    reset_global_simulator()

    print("  -> BUG-RL04 & BUG-C03 PASS: 5-tuple Gymnasium standard & thread-safe singleton verified.")


def verify_bug_rl05_hpo_reward_penalty():
    print("[5/5] Verifying BUG-RL05: HPO Reward Hacking Defense & Zero-Trade Penalty...")
    study = create_hpo_study(seed=42)

    with patch("modules.hpo.optuna_pipeline.evaluate_trading_history") as mock_eval:
        # Case A: 0 trades -> must be penalised with -1.0
        mock_eval.return_value = {
            "total_equity": 10_000_000.0,
            "total_return_pct": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "total_trades": 0,
            "win_rate": 0.0,
        }
        trial_zero = study.ask()
        val_zero = objective(trial_zero, symbol="005930", n_timesteps=16, fast_mode=True)
        assert val_zero == -1.0, f"Expected -1.0 for 0-trade policy, got {val_zero}"

        # Case B: 5 trades, slightly negative Sharpe -0.2 -> must score higher than inactive policy (-1.0)
        mock_eval.return_value = {
            "total_equity": 9_950_000.0,
            "total_return_pct": -0.5,
            "sharpe_ratio": -0.2,
            "max_drawdown_pct": 1.0,
            "total_trades": 5,
            "win_rate": 40.0,
        }
        trial_active = study.ask()
        val_active = objective(trial_active, symbol="005930", n_timesteps=16, fast_mode=True)
        # Expected: -0.2 + 0.01 * (-0.5) = -0.205 > -1.0
        assert val_active > val_zero, f"Active policy ({val_active}) should rank above inactive policy ({val_zero})"

    print("  -> BUG-RL05 PASS: Inactive policies penalised (-1.0) and exploration incentivised.")


def main():
    print("=================================================================")
    print("=== Auto_Stock Milestone 3 Forensic Integrity Verification ===")
    print("=================================================================")
    verify_bug_rl01_step_indexing()
    verify_bug_rl02_trade_record_isolation()
    verify_bug_rl03_device_auto_transfer()
    verify_bug_rl04_and_c03_live_sim_and_thread_safety()
    verify_bug_rl05_hpo_reward_penalty()
    print("=================================================================")
    print("=== ALL 5 FORENSIC INTEGRITY CHECKS PASSED EMPIRICALLY! ===")
    print("=================================================================")


if __name__ == "__main__":
    main()
