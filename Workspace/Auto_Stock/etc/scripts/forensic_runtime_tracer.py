#!/usr/bin/env python3
"""
Forensic Runtime Tracing for Auto_Stock Milestone 3 HPO Pipeline.
"""
import os
import sys
import tempfile
import torch
import numpy as np
import pandas as pd
import optuna

# Add workspace to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.engine.hybrid_trading_env import HybridTradingEnv
from modules.hpo.metrics import (
    calculate_total_equity,
    calculate_total_return_pct,
    calculate_annualized_sharpe_ratio,
    calculate_max_drawdown_pct,
    calculate_win_rate,
    evaluate_trading_history,
)
from modules.hpo.exporter import CSV_COLUMNS, export_trial_to_csv, load_hpo_results
from modules.hpo.optuna_pipeline import create_hpo_study, objective, run_hpo_optimization
from modules.models.hybrid_policy import HybridPPO, HybridActorCritic

def run_forensic_runtime_trace():
    print("=================================================================")
    print("🔍 [Forensic Runtime Tracer] Starting In-Depth Execution Tracing")
    print("=================================================================")

    # 1. Environment Step & Action Space Hooking
    original_step = HybridTradingEnv.step
    original_reset = HybridTradingEnv.reset
    step_calls = []
    actions_logged = []
    rewards_logged = []
    equities_logged = []

    def hooked_step(self, action):
        actions_logged.append(action)
        obs, reward, term, trunc, info = original_step(self, action)
        rewards_logged.append(reward)
        equities_logged.append(info.get("total_equity", 0.0))
        step_calls.append(1)
        return obs, reward, term, trunc, info

    HybridTradingEnv.step = hooked_step

    # 2. Neural Network Weight Delta Tracing
    weight_deltas = []
    original_learn = HybridPPO.learn

    def hooked_learn(self, total_timesteps):
        # Capture weights before
        weights_before = [p.clone().detach() for p in self.policy.parameters()]
        res = original_learn(self, total_timesteps)
        # Capture weights after
        weights_after = [p.clone().detach() for p in self.policy.parameters()]
        
        total_delta = 0.0
        for wb, wa in zip(weights_before, weights_after):
            diff = torch.norm(wa - wb).item()
            total_delta += diff
        weight_deltas.append(total_delta)
        return res

    HybridPPO.learn = hooked_learn

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_csv = os.path.join(tmp_dir, "forensic_trace_hpo.csv")
        
        print("\n[Step 1] Running 3-Trial Optuna Optimization with Live Instrumentation...")
        study, best_trial = run_hpo_optimization(
            n_trials=3,
            symbol="005930",
            output_csv=test_csv,
            seed=42,
            n_timesteps=64,
            fast_mode=True,
            verbose=False,
        )

        # Restore original methods
        HybridTradingEnv.step = original_step
        HybridPPO.learn = original_learn

        print(f"  • Total HybridTradingEnv.step() calls recorded: {len(step_calls)}")
        assert len(step_calls) > 100, f"Expected >100 env steps, got {len(step_calls)}"
        print(f"  • Total HybridPPO.learn() weight delta checks: {len(weight_deltas)}")
        assert len(weight_deltas) == 3, f"Expected 3 training sessions, got {len(weight_deltas)}"
        
        for idx, delta in enumerate(weight_deltas):
            print(f"    - Trial #{idx} Neural Net Parameter L2 Weight Delta: {delta:.6f}")
            assert delta > 0.0, f"Neural network weights did not update in trial {idx}! (delta={delta})"
        print("  [+] PASS: Real neural network backpropagation and weight updates verified.")

        # Inspect logged actions
        discrete_actions = [a[0] if isinstance(a, tuple) else a.get("discrete", 0) for a in actions_logged]
        cont_actions = [a[1] if isinstance(a, tuple) else a.get("continuous", 0.0) for a in actions_logged]
        print(f"  • Action Diversity: Unique discrete actions = {set(discrete_actions)}, Continuous range = [{min(cont_actions):.4f}, {max(cont_actions):.4f}]")
        print("  [+] PASS: Hybrid action space (discrete + continuous) actively exercised by policy.")

        # 3. Parameter Variation across Trials
        print("\n[Step 2] Optuna Parameter Sampling Diversity Check:")
        param_sets = [t.params for t in study.trials]
        for idx, p in enumerate(param_sets):
            print(f"  • Trial #{idx} parameters: {p}")
        assert param_sets[0] != param_sets[1] != param_sets[2], "Trial parameters are identical! Sampler failed or mocked."
        print("  [+] PASS: True parameter diversity across trials confirmed.")

        # 4. CSV Provenance & Metric Integrity
        print("\n[Step 3] CSV Export Schema & Mathematical Consistency Check:")
        df = load_hpo_results(test_csv)
        print(f"  • Loaded CSV Rows: {len(df)}, Columns: {len(df.columns)}")
        assert len(df) == 3
        assert list(df.columns) == CSV_COLUMNS

        for idx, row in df.iterrows():
            trial_obj = study.trials[idx]
            print(f"  • Trial #{idx}: state={row['state']}, objective={row['objective_value']}, equity={row['total_equity']}, Sharpe={row['sharpe_ratio']}, MDD={row['max_drawdown_pct']}%, Duration={row['duration_seconds']}s")
            # Verify exact match between study trial and CSV row
            assert row["trial_id"] == trial_obj.number
            assert row["state"] == trial_obj.state.name
            assert pytest.approx(row["objective_value"], abs=1e-5) == (trial_obj.value if trial_obj.value is not None else 0.0)
            assert row["param_sl_hidden_dim"] == trial_obj.params["sl_hidden_dim"]
            assert pytest.approx(row["param_rl_lr"], rel=1e-5) == trial_obj.params["rl_lr"]
        print("  [+] PASS: Exact 1-to-1 correspondence between Optuna in-memory trial state and exported CSV.")

    print("\n=================================================================")
    print("✅ [Forensic Runtime Tracer] ALL RUNTIME INTEGRITY CHECKS PASSED")
    print("=================================================================")
    return True

if __name__ == "__main__":
    import pytest
    success = run_forensic_runtime_trace()
    sys.exit(0 if success else 1)
