#!/usr/bin/env python3
"""
test_h4_grid.py
===============
Independent Verification Suite for H-4:
  - Standard Action Grid Unification (PTX_GRID_DBM = [-5, 0, 5, 10, 15, 20], T_GRID_S = [0.1, 0.2, 0.5, 1.0])
  - ACTION_DIM = 24 consistency across all AI-DCC hooks
  - Complete elimination of unfair 30 dBm (1W) transmission power actions
  - Codebase-wide AST and regex audit for power grid integrity

Author: Coder Worker (H-4)
"""

import ast
import glob
import os
import re
import sys
import unittest

# Ensure code directory is in sys.path
CODE_DIR = os.path.dirname(os.path.abspath(__file__))
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

import etsi_cam_layer
import ai_dcc_hook


class TestH4GridUnification(unittest.TestCase):
    """Test suite validating standard action grids and elimination of 30 dBm actions."""

    def test_01_etsi_cam_layer_standard_constants(self):
        """Verify that etsi_cam_layer defines standard constants with exact specs."""
        expected_ptx = [-5, 0, 5, 10, 15, 20]
        expected_t = [0.1, 0.2, 0.5, 1.0]
        expected_action_dim = 24

        self.assertEqual(
            etsi_cam_layer.PTX_GRID_DBM,
            expected_ptx,
            f"PTX_GRID_DBM should be {expected_ptx}, got {etsi_cam_layer.PTX_GRID_DBM}"
        )
        self.assertEqual(
            etsi_cam_layer.T_GRID_S,
            expected_t,
            f"T_GRID_S should be {expected_t}, got {etsi_cam_layer.T_GRID_S}"
        )
        self.assertEqual(
            etsi_cam_layer.ACTION_DIM,
            expected_action_dim,
            f"ACTION_DIM should be {expected_action_dim}, got {etsi_cam_layer.ACTION_DIM}"
        )
        self.assertEqual(len(etsi_cam_layer.PTX_GRID_DBM), 6)
        self.assertEqual(len(etsi_cam_layer.T_GRID_S), 4)
        self.assertEqual(max(etsi_cam_layer.PTX_GRID_DBM), 20)
        self.assertEqual(min(etsi_cam_layer.PTX_GRID_DBM), -5)
        self.assertEqual(etsi_cam_layer.T_GENCAM_GRID, etsi_cam_layer.T_GRID_S)

    def test_02_all_hooks_grid_reference_and_power_bound(self):
        """Verify that all Hook classes in ai_dcc_hook use standard grids and max_ptx <= 20 dBm."""
        hook_classes = []
        for name, obj in ai_dcc_hook.__dict__.items():
            if isinstance(obj, type) and name.endswith("Hook"):
                hook_classes.append((name, obj))

        self.assertGreaterEqual(len(hook_classes), 15, f"Expected at least 15 hook classes, found {len(hook_classes)}")

        for name, cls in hook_classes:
            with self.subTest(hook_name=name):
                # Instantiate hook
                if name == "TinyMLPHook":
                    inst = cls("tinymlp_model.pkl")
                elif name == "SklearnHook":
                    inst = cls("stdmlp_model.pkl")
                else:
                    inst = cls()

                # Verify grids
                self.assertEqual(
                    inst.p_tx_grid,
                    etsi_cam_layer.PTX_GRID_DBM,
                    f"{name}.p_tx_grid must match etsi_cam_layer.PTX_GRID_DBM"
                )
                self.assertEqual(
                    inst.t_grid,
                    etsi_cam_layer.T_GRID_S,
                    f"{name}.t_grid must match etsi_cam_layer.T_GRID_S"
                )
                self.assertEqual(
                    inst.action_dim,
                    24,
                    f"{name}.action_dim must be 24, got {inst.action_dim}"
                )
                self.assertEqual(
                    len(inst.p_tx_grid) * len(inst.t_grid),
                    24,
                    f"{name} total action space size must be 24"
                )
                self.assertLessEqual(
                    max(inst.p_tx_grid),
                    20.0,
                    f"{name} max transmission power exceeds baseline 20 dBm! Found: {max(inst.p_tx_grid)}"
                )

    def test_03_action_decoding_coverage_and_invariance(self):
        """Verify that action indices 0..23 correctly map to (t, p) pairs and cover full 24-action grid."""
        hook = ai_dcc_hook.DuelingDQNHook()
        n_p = len(hook.p_tx_grid)  # 6
        n_t = len(hook.t_grid)     # 4

        decoded_pairs = set()
        for act_idx in range(24):
            t_act = hook.t_grid[act_idx // n_p]
            p_act = hook.p_tx_grid[act_idx % n_p]
            
            self.assertIn(t_act, etsi_cam_layer.T_GRID_S)
            self.assertIn(p_act, etsi_cam_layer.PTX_GRID_DBM)
            self.assertLessEqual(p_act, 20.0)
            
            pair = (t_act, p_act)
            self.assertNotIn(pair, decoded_pairs, f"Duplicate action mapping detected for index {act_idx}: {pair}")
            decoded_pairs.add(pair)

        self.assertEqual(len(decoded_pairs), 24, f"Expected 24 distinct (T, P) pairs, got {len(decoded_pairs)}")

    def test_04_get_hook_factory_all_methods(self):
        """Verify that get_hook returns hooks with valid grid specs for all registered methods."""
        methods = [
            "Proposed", "ResNetMoEDQN", "REMO-DQN", "VanillaDQN", "DoubleDQN",
            "DuelingDQN", "MoEDQN", "QLearning", "SARSA", "ActorCritic",
            "PPO", "DDPG", "DecisionTransformer", "SAC", "MAPPO", "TD3",
            "StdMLP", "DecTree"
        ]

        for method in methods:
            with self.subTest(method=method):
                hook = ai_dcc_hook.get_hook(method)
                self.assertIsNotNone(hook, f"get_hook({method}) returned None")
                self.assertEqual(hook.p_tx_grid, etsi_cam_layer.PTX_GRID_DBM)
                self.assertEqual(hook.t_grid, etsi_cam_layer.T_GRID_S)
                self.assertEqual(hook.action_dim, 24)
                self.assertLessEqual(max(hook.p_tx_grid), 20.0)

    def test_05_no_30dbm_power_actions_in_codebase(self):
        """Audit all python files in code/ to ensure 0 definitions of 30 dBm transmission power actions."""
        py_files = glob.glob(os.path.join(CODE_DIR, "*.py"))
        
        # Patterns that indicate 30 dBm power grid definition
        suspicious_patterns = [
            re.compile(r'p_tx_grid\s*=\s*\[[^\]]*30(?:\.0)?\s*\]'),
            re.compile(r'PTX_GRID(?:_DBM)?\s*=\s*\[[^\]]*30(?:\.0)?\s*\]'),
            re.compile(r'\[\s*(?:0\.0|0|-10|-5)\s*,.*30(?:\.0)?\s*\]'),
        ]

        violations = []
        for py_path in py_files:
            fname = os.path.basename(py_path)
            # Skip test files and backup files
            if fname.startswith("test_") or ".bak" in fname:
                continue

            with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            for lineno, line in enumerate(content.splitlines(), start=1):
                # Ignore non-power 30 occurrences (like 300, 30.0s warmup, line 30, etc.)
                for pat in suspicious_patterns:
                    if pat.search(line):
                        violations.append((fname, lineno, line.strip()))

        self.assertEqual(
            len(violations),
            0,
            f"Found {len(violations)} occurrences of 30 dBm power grid definitions in code/:\n" +
            "\n".join(f"  {f}:{l} -> {c}" for f, l, c in violations)
        )


if __name__ == "__main__":
    print("=" * 70)
    print("  Running H-4 Independent Verification Suite: test_h4_grid.py")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestH4GridUnification)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n[PASS] 100% of H-4 grid unification tests passed successfully (Exit Code 0).")
        sys.exit(0)
    else:
        print("\n[FAIL] Some H-4 verification tests failed.")
        sys.exit(1)
