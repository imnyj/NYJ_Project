#!/usr/bin/env python3
"""
test_m11_benchmark_models.py - Independent Verification Suite for M-11.

Verifies:
1. Exact ACTION_DIM = 24 consistency and 0 residual 25-class definitions in benchmark files.
2. Proposed model naming as 'REMO-DQN (Proposed)' or 'ResNetMoEDQN' (no 'TinyMLP (Proposed)').
3. Forward pass / inference correctness on (N, 5) inputs yielding (N, 24) outputs across all 7 models.
4. calc_flops.py analytical accuracy, parameter counts, and MACs/FLOPs computation.
5. train_7_models.py benchmarking execution, latency measurement, and CSV/JSON output generation.
6. plot_complexity.py visualization generation.
7. Complexity / parameter scaling hierarchy across all 7 models.
"""

import os
import sys
import unittest
import tempfile
import shutil
import re
import numpy as np
import torch
import pandas as pd

# Add code directory to path
_code_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_code_dir)
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from etsi_cam_layer import ACTION_DIM
from dqn_agent import VanillaDQN
from ddqn_agent import DoubleDQN
from dueling_dqn_agent import DuelingDQN
from moe_agent import MoEDQN
from resnet_moe_agent import ResNetMoEDQN
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from calc_flops import get_model_stats, get_all_7_models_stats
from train_7_models import run_benchmark


class TestM11BenchmarkModels(unittest.TestCase):
    """Test suite for M-11 7-model benchmarking, complexity calculation, and class dimension alignment."""

    def test_01_no_25_classes_in_codebase(self):
        """Verify that train_7_models.py, calc_flops.py, and plot_complexity.py have 0 residual 25-class definitions."""
        target_files = [
            os.path.join(_code_dir, "train_7_models.py"),
            os.path.join(_code_dir, "calc_flops.py"),
            os.path.join(_code_dir, "plot_complexity.py"),
        ]
        
        # Patterns indicative of 25 classes
        bad_patterns = [
            r"randint\s*\(\s*0\s*,\s*25\s*\)",
            r"num_classes\s*=\s*25\b",
            r"action_dim\s*=\s*25\b",
            r"n_classes\s*=\s*25\b",
            r"classes\s*=\s*25\b"
        ]
        
        for fpath in target_files:
            self.assertTrue(os.path.exists(fpath), f"File missing: {fpath}")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                
            for pat in bad_patterns:
                matches = re.findall(pat, content)
                self.assertEqual(len(matches), 0, f"Found 25-class pattern '{pat}' in {fpath}: {matches}")
                
        # Confirm ACTION_DIM is 24
        self.assertEqual(ACTION_DIM, 24, "ACTION_DIM must be exactly 24")

    def test_02_proposed_model_naming_and_no_tinymlp_proposed(self):
        """Verify proposed model is labeled 'REMO-DQN (Proposed)' or 'ResNetMoEDQN' and 'TinyMLP (Proposed)' is eliminated."""
        target_files = [
            os.path.join(_code_dir, "train_7_models.py"),
            os.path.join(_code_dir, "calc_flops.py"),
            os.path.join(_code_dir, "plot_complexity.py"),
        ]
        
        for fpath in target_files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Must not contain "TinyMLP (Proposed)"
            self.assertNotIn("TinyMLP (Proposed)", content, f"'TinyMLP (Proposed)' found in {fpath}")
            
            # Must contain REMO-DQN or ResNetMoEDQN
            has_proposed = ("REMO-DQN" in content) or ("ResNetMoEDQN" in content)
            self.assertTrue(has_proposed, f"Neither 'REMO-DQN' nor 'ResNetMoEDQN' found in {fpath}")

    def test_03_7_models_instantiation_and_forward_shapes(self):
        """Verify all 7 benchmark models can be instantiated and produce 24-dimensional outputs on 5-dim inputs."""
        batch_size = 16
        dummy_state = torch.randn(batch_size, 5)
        
        # 1. REMO-DQN (Proposed)
        m1 = ResNetMoEDQN(state_dim=5, action_dim=24, hidden_dim=128, num_experts=3)
        m1.eval()
        with torch.no_grad():
            out1 = m1(dummy_state)
        self.assertEqual(out1.shape, (batch_size, 24))
        
        # 2. MoEDQN
        m2 = MoEDQN(state_dim=5, action_dim=24, num_experts=2)
        m2.eval()
        with torch.no_grad():
            out2 = m2(dummy_state)
        self.assertEqual(out2.shape, (batch_size, 24))
        
        # 3. DuelingDQN
        m3 = DuelingDQN(state_dim=5, action_dim=24)
        m3.eval()
        with torch.no_grad():
            out3 = m3(dummy_state)
        self.assertEqual(out3.shape, (batch_size, 24))
        
        # 4. DoubleDQN
        m4 = DoubleDQN(state_dim=5, action_dim=24)
        m4.eval()
        with torch.no_grad():
            out4 = m4(dummy_state)
        self.assertEqual(out4.shape, (batch_size, 24))
        
        # 5. VanillaDQN
        m5 = VanillaDQN(state_dim=5, action_dim=24)
        m5.eval()
        with torch.no_grad():
            out5 = m5(dummy_state)
        self.assertEqual(out5.shape, (batch_size, 24))
        
        # 6. StdMLP (Sklearn)
        X_synth = np.random.rand(500, 5)
        y_synth = np.random.randint(0, 24, 500)
        # Ensure all 24 classes are represented in synthetic train set
        for c in range(24):
            y_synth[c] = c
            
        m6 = MLPClassifier(hidden_layer_sizes=(64, 64, 64), max_iter=20, random_state=42)
        m6.fit(X_synth, y_synth)
        preds6 = m6.predict(X_synth[:batch_size])
        self.assertEqual(preds6.shape, (batch_size,))
        self.assertTrue(np.all(preds6 >= 0) and np.all(preds6 < 24))
        
        # 7. DecTree (Sklearn)
        m7 = DecisionTreeClassifier(max_depth=10, random_state=42)
        m7.fit(X_synth, y_synth)
        preds7 = m7.predict(X_synth[:batch_size])
        self.assertEqual(preds7.shape, (batch_size,))
        self.assertTrue(np.all(preds7 >= 0) and np.all(preds7 < 24))

    def test_04_calc_flops_stats_integrity_and_math(self):
        """Verify calc_flops computes exact parameters and FLOPs for all 7 models."""
        stats = get_all_7_models_stats(state_dim=5, action_dim=24)
        self.assertEqual(len(stats), 7, "Must return stats for exactly 7 models")
        
        stats_map = {s["Model"]: s for s in stats}
        expected_models = [
            "REMO-DQN (Proposed)",
            "MoEDQN",
            "DuelingDQN",
            "DoubleDQN",
            "VanillaDQN",
            "StdMLP",
            "DecTree"
        ]
        for name in expected_models:
            self.assertIn(name, stats_map, f"Model {name} missing from stats")
            
        # Verify exact parameters and FLOPs
        # 1. REMO-DQN: ResNet (768 + 66048) + Gate (8256 + 195) + 3 Experts (3 * 18137) = 129,678
        self.assertEqual(stats_map["REMO-DQN (Proposed)"]["Parameters"], 129678)
        self.assertEqual(stats_map["REMO-DQN (Proposed)"]["MACs"], 128512)
        self.assertEqual(stats_map["REMO-DQN (Proposed)"]["FLOPs"], 257024)
        
        # 2. MoEDQN: 2 Experts Feature (34560) + Gate (514) + Streams (18137) = 53,211
        self.assertEqual(stats_map["MoEDQN"]["Parameters"], 53211)
        self.assertEqual(stats_map["MoEDQN"]["MACs"], 52480)
        self.assertEqual(stats_map["MoEDQN"]["FLOPs"], 104960)
        
        # 3. DuelingDQN: Feature (17280) + Streams (18137) = 35,417
        self.assertEqual(stats_map["DuelingDQN"]["Parameters"], 35417)
        self.assertEqual(stats_map["DuelingDQN"]["MACs"], 35008)
        self.assertEqual(stats_map["DuelingDQN"]["FLOPs"], 70016)
        
        # 4. DoubleDQN: 5->128->128->24 = 768 + 16512 + 3096 = 20,376
        self.assertEqual(stats_map["DoubleDQN"]["Parameters"], 20376)
        self.assertEqual(stats_map["DoubleDQN"]["MACs"], 20096)
        self.assertEqual(stats_map["DoubleDQN"]["FLOPs"], 40192)
        
        # 5. VanillaDQN: 5->128->128->24 = 20,376
        self.assertEqual(stats_map["VanillaDQN"]["Parameters"], 20376)
        self.assertEqual(stats_map["VanillaDQN"]["MACs"], 20096)
        self.assertEqual(stats_map["VanillaDQN"]["FLOPs"], 40192)
        
        # 6. StdMLP: 5->64->64->64->24 = 384 + 4160 + 4160 + 1560 = 10,264
        self.assertEqual(stats_map["StdMLP"]["Parameters"], 10264)
        self.assertEqual(stats_map["StdMLP"]["MACs"], 10048)
        self.assertEqual(stats_map["StdMLP"]["FLOPs"], 20096)
        
        # 7. DecTree: > 0
        self.assertGreater(stats_map["DecTree"]["Parameters"], 0)
        self.assertGreater(stats_map["DecTree"]["FLOPs"], 0)

    def test_05_train_7_models_benchmark_execution(self):
        """Verify train_7_models.py benchmark executes cleanly and saves CSV/JSON with 7 models."""
        tmp_dir = tempfile.mkdtemp(prefix="test_m11_bench_")
        try:
            df_res, res_list = run_benchmark(
                n_samples=500,
                n_test=50,
                epochs=1,
                batch_size=32,
                output_dir=tmp_dir
            )
            
            self.assertEqual(len(df_res), 7, "DataFrame must contain 7 rows")
            self.assertEqual(len(res_list), 7, "Result list must contain 7 dictionaries")
            
            # Check CSV exists and is non-empty
            csv_path = os.path.join(tmp_dir, "edge_profiling_benchmark.csv")
            self.assertTrue(os.path.exists(csv_path))
            df_read = pd.read_csv(csv_path)
            self.assertEqual(len(df_read), 7)
            
            # Check JSON exists
            json_path = os.path.join(tmp_dir, "edge_profiling_benchmark.json")
            self.assertTrue(os.path.exists(json_path))
            
            # Verify columns
            required_cols = ["Model", "Parameters", "Memory (KB)", "MACs", "FLOPs", "Latency (us)", "Train Time (s)"]
            for col in required_cols:
                self.assertIn(col, df_read.columns, f"Missing column: {col}")
                
            # Verify positive latencies and parameters
            for _, row in df_read.iterrows():
                self.assertGreater(row["Parameters"], 0)
                self.assertGreater(row["Latency (us)"], 0.0)
                self.assertGreater(row["FLOPs"], 0)
                
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_06_plot_complexity_execution_and_file_generation(self):
        """Verify plot_complexity.py executes and generates fig_complexity.png."""
        import subprocess
        script_path = os.path.join(_code_dir, "plot_complexity.py")
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"plot_complexity.py failed:\n{res.stderr}")
        
        plot_path = os.path.join(_project_root, "data", "plots", "fig_complexity.png")
        self.assertTrue(os.path.exists(plot_path), f"Plot image missing: {plot_path}")
        self.assertGreater(os.path.getsize(plot_path), 1000, "Plot image size is too small")

    def test_07_parameter_and_complexity_hierarchy(self):
        """Verify the monotonic complexity scaling hierarchy across the 7 models."""
        stats = get_all_7_models_stats(state_dim=5, action_dim=24)
        stats_map = {s["Model"]: s for s in stats}
        
        p_tree = stats_map["DecTree"]["Parameters"]
        p_mlp = stats_map["StdMLP"]["Parameters"]
        p_vanilla = stats_map["VanillaDQN"]["Parameters"]
        p_double = stats_map["DoubleDQN"]["Parameters"]
        p_dueling = stats_map["DuelingDQN"]["Parameters"]
        p_moe = stats_map["MoEDQN"]["Parameters"]
        p_remo = stats_map["REMO-DQN (Proposed)"]["Parameters"]
        
        # Verify hierarchy: DecTree < StdMLP < Vanilla == Double < Dueling < MoE < REMO-DQN
        self.assertLess(p_tree, p_mlp)
        self.assertLess(p_mlp, p_vanilla)
        self.assertEqual(p_vanilla, p_double)
        self.assertLess(p_double, p_dueling)
        self.assertLess(p_dueling, p_moe)
        self.assertLess(p_moe, p_remo)
        
        # Verify FLOPs hierarchy
        f_tree = stats_map["DecTree"]["FLOPs"]
        f_mlp = stats_map["StdMLP"]["FLOPs"]
        f_vanilla = stats_map["VanillaDQN"]["FLOPs"]
        f_double = stats_map["DoubleDQN"]["FLOPs"]
        f_dueling = stats_map["DuelingDQN"]["FLOPs"]
        f_moe = stats_map["MoEDQN"]["FLOPs"]
        f_remo = stats_map["REMO-DQN (Proposed)"]["FLOPs"]
        
        self.assertLess(f_tree, f_mlp)
        self.assertLess(f_mlp, f_vanilla)
        self.assertEqual(f_vanilla, f_double)
        self.assertLess(f_double, f_dueling)
        self.assertLess(f_dueling, f_moe)
        self.assertLess(f_moe, f_remo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
