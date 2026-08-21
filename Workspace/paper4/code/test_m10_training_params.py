#!/usr/bin/env python3
"""
Independent Verification Suite for M-10:
Training Episodes (500) and Epsilon Decay (0.995) Standardization.

Tests:
1. Static / AST Inspection: All active training scripts have default episodes=500 and epsilon_decay=0.995
2. CLI Argument Parsing: All training scripts support `--episodes` CLI argument with default 500
3. Mathematical Epsilon Decay Trajectory: Verification of epsilon_decay=0.995 (Ep0: 1.0, Ep100: ~0.606, Ep250: ~0.285, Ep500: ~0.082)
4. Agent Class Epsilon Lifecycle: All agent classes implement correct single-step epsilon decay behavior
5. Smoke Training Execution & Artifact Generation: 2-episode smoke training verifying weight saving and CSV logging
"""

import os
import sys
import ast
import csv
import math
import shutil
import unittest
import importlib

# Ensure code/ is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from dqn_agent import DQNAgent
from ddqn_agent import DDQNAgent
from dueling_dqn_agent import DuelingDQNAgent
from moe_agent import MoEAgent
from resnet_moe_agent import ResNetMoEAgent
from qlearning_agent import QLearningAgent
from sarsa_agent import SARSAAgent
from actor_critic_agent import ActorCriticAgent

TRAIN_SCRIPTS = [
    "train_resnet.py",
    "train_dqn.py",
    "train_ddqn.py",
    "train_dueling_dqn.py",
    "train_moe.py",
    "train_qlearning.py",
    "train_sarsa.py",
    "train_actor_critic.py"
]

class TestM10TrainingParams(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.join(SCRIPT_DIR, "etc", "temp_test_m10")
        os.makedirs(self.temp_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_01_static_ast_default_episodes_and_decay(self):
        """Verify that all training scripts define default episodes=500 and epsilon_decay=0.995."""
        for script_name in TRAIN_SCRIPTS:
            script_path = os.path.join(SCRIPT_DIR, script_name)
            self.assertTrue(os.path.exists(script_path), f"Script {script_name} must exist")
            
            with open(script_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source, filename=script_path)
            
            # Check function definitions for default args or argparse defaults
            has_episodes_500 = False
            has_decay_0995 = False
            
            for node in ast.walk(tree):
                # Check function default arguments
                if isinstance(node, ast.FunctionDef):
                    for default in node.args.defaults:
                        if isinstance(default, ast.Constant):
                            if default.value == 500:
                                has_episodes_500 = True
                            elif isinstance(default.value, float) and abs(default.value - 0.995) < 1e-6:
                                has_decay_0995 = True
                # Check argparse default arguments
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
                        for kw in node.keywords:
                            if kw.arg == "default":
                                if isinstance(kw.value, ast.Constant):
                                    if kw.value.value == 500:
                                        has_episodes_500 = True
                                    elif isinstance(kw.value, float) and abs(kw.value - 0.995) < 1e-6:
                                        has_decay_0995 = True

            self.assertTrue(has_episodes_500, f"{script_name} must have default episodes=500")
            if script_name != "train_actor_critic.py":  # ActorCritic uses policy distribution, no epsilon
                self.assertTrue(has_decay_0995, f"{script_name} must have default epsilon_decay=0.995")

    def test_02_cli_argument_parser_support(self):
        """Verify that parse_args() in all training scripts supports --episodes and returns default 500."""
        for script_name in TRAIN_SCRIPTS:
            mod_name = script_name.replace(".py", "")
            mod = importlib.import_module(mod_name)
            self.assertTrue(hasattr(mod, "parse_args"), f"{script_name} must have parse_args()")
            
            # Test default parsing
            sys_argv_bak = sys.argv
            sys.argv = [script_name]
            try:
                args = mod.parse_args()
                self.assertEqual(args.episodes, 500, f"{script_name} default --episodes must be 500")
            finally:
                sys.argv = sys_argv_bak
                
            # Test explicit --episodes CLI override
            sys.argv = [script_name, "--episodes", "10"]
            try:
                args = mod.parse_args()
                self.assertEqual(args.episodes, 10, f"{script_name} custom --episodes 10 must be parsed")
            finally:
                sys.argv = sys_argv_bak

    def test_03_mathematical_epsilon_decay_trajectory(self):
        """Verify the exact mathematical decay curve for epsilon_decay=0.995."""
        decay = 0.995
        eps_0 = 1.0
        min_eps = 0.01
        
        # Ep 0
        self.assertAlmostEqual(eps_0, 1.0, places=4)
        
        # Ep 100: 1.0 * (0.995)^100 = 0.6057704...
        eps_100 = eps_0 * (decay ** 100)
        self.assertAlmostEqual(eps_100, 0.6058, places=3)
        self.assertTrue(0.60 <= eps_100 <= 0.61)
        
        # Ep 250: 1.0 * (0.995)^250 = 0.2856078...
        eps_250 = eps_0 * (decay ** 250)
        self.assertAlmostEqual(eps_250, 0.2856, places=3)
        self.assertTrue(0.28 <= eps_250 <= 0.29)
        
        # Ep 500: 1.0 * (0.995)^500 = 0.0815718...
        eps_500 = eps_0 * (decay ** 500)
        self.assertAlmostEqual(eps_500, 0.0816, places=3)
        self.assertTrue(0.080 <= eps_500 <= 0.083)
        
        # Ep 1000 with min_epsilon clipping
        eps_1000 = max(min_eps, eps_0 * (decay ** 1000))
        self.assertAlmostEqual(eps_1000, 0.01, places=3)

    def test_04_agent_classes_epsilon_lifecycle(self):
        """Verify that all agent classes follow the single-step decay per episode correctly."""
        agents = [
            DQNAgent(state_dim=5, action_dim=24, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995),
            DDQNAgent(state_dim=5, action_dim=24, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995),
            DuelingDQNAgent(state_dim=5, action_dim=24, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995),
            MoEAgent(state_dim=5, action_dim=24, num_experts=2, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995),
            ResNetMoEAgent(state_dim=5, action_dim=24, num_experts=3, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995),
            QLearningAgent(state_bins=[5, 5, 5, 5, 5], action_dim=24, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.01),
            SARSAAgent(state_bins=[5, 5, 5, 5, 5], action_dim=24, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.01)
        ]
        
        for agent in agents:
            cls_name = agent.__class__.__name__
            self.assertEqual(agent.epsilon, 1.0, f"{cls_name} initial epsilon must be 1.0")
            
            # Run 100 updates
            for _ in range(100):
                agent.update_epsilon()
            self.assertAlmostEqual(agent.epsilon, 0.6058, places=2, msg=f"{cls_name} at Ep 100 must be ~0.606")
            
            # Run up to 250 updates (150 more)
            for _ in range(150):
                agent.update_epsilon()
            self.assertAlmostEqual(agent.epsilon, 0.2856, places=2, msg=f"{cls_name} at Ep 250 must be ~0.286")
            
            # Run up to 500 updates (250 more)
            for _ in range(250):
                agent.update_epsilon()
            self.assertAlmostEqual(agent.epsilon, 0.0816, places=2, msg=f"{cls_name} at Ep 500 must be ~0.082")
            
            # Run up to 1000 updates (500 more) - should hit min_epsilon
            for _ in range(500):
                agent.update_epsilon()
            self.assertAlmostEqual(agent.epsilon, 0.01, places=2, msg=f"{cls_name} at Ep 1000 must be clamped to min_epsilon 0.01")

    def test_05_smoke_training_drl_resnet(self):
        """Run a 2-episode smoke training of ResNetMoEDQN and verify model weight & CSV log integrity."""
        import train_resnet
        out_model = os.path.join(self.temp_dir, "smoke_resnet.pth")
        out_log = os.path.join(self.temp_dir, "smoke_resnet_log.csv")
        
        agent = train_resnet.train(
            num_episodes=2,
            seed=42,
            duration_steps=50,
            output_model=out_model,
            output_log=out_log,
            epsilon_decay=0.995,
            min_epsilon=0.01
        )
        
        # Check model file
        self.assertTrue(os.path.exists(out_model), "Model checkpoint must be created")
        self.assertGreater(os.path.getsize(out_model), 1000, "Model checkpoint must have non-zero size")
        
        # Check CSV log
        self.assertTrue(os.path.exists(out_log), "CSV training log must be created")
        with open(out_log, "r") as f:
            reader = list(csv.reader(f))
            self.assertEqual(len(reader), 3, "CSV must have header + 2 episode rows")
            header = reader[0]
            self.assertIn("Episode", header)
            self.assertIn("Reward", header)
            self.assertIn("Loss", header)
            self.assertIn("Epsilon", header)
            self.assertIn("Steps", header)
            
            # Row 1 (Episode 1)
            row1 = reader[1]
            self.assertEqual(int(row1[0]), 1)
            eps_ep1 = float(row1[3])
            self.assertAlmostEqual(eps_ep1, 0.995, places=3)
            
            # Row 2 (Episode 2)
            row2 = reader[2]
            self.assertEqual(int(row2[0]), 2)
            eps_ep2 = float(row2[3])
            self.assertAlmostEqual(eps_ep2, 0.995 * 0.995, places=3)

    def test_06_smoke_training_tabular_qlearning(self):
        """Run a 2-episode smoke training of Q-Learning and verify model pickle & CSV log integrity."""
        import train_qlearning
        out_model = os.path.join(self.temp_dir, "smoke_qlearning.pkl")
        out_log = os.path.join(self.temp_dir, "smoke_qlearning_log.csv")
        
        agent = train_qlearning.train(
            num_episodes=2,
            seed=42,
            duration_steps=50,
            output_model=out_model,
            output_log=out_log,
            epsilon_decay=0.995,
            min_epsilon=0.01
        )
        
        self.assertTrue(os.path.exists(out_model), "Q-learning model pickle must be created")
        self.assertGreater(os.path.getsize(out_model), 100, "Model pickle must have non-zero size")
        
        self.assertTrue(os.path.exists(out_log), "Q-learning CSV log must be created")
        with open(out_log, "r") as f:
            reader = list(csv.reader(f))
            self.assertEqual(len(reader), 3, "CSV must have header + 2 episode rows")
            row1 = reader[1]
            self.assertEqual(int(row1[0]), 1)
            self.assertAlmostEqual(float(row1[3]), 0.995, places=3)

    def test_07_smoke_training_actor_critic(self):
        """Run a 2-episode smoke training of ActorCritic and verify model weight & CSV log integrity."""
        import train_actor_critic
        out_model = os.path.join(self.temp_dir, "smoke_actor_critic.pth")
        out_log = os.path.join(self.temp_dir, "smoke_actor_critic_log.csv")
        
        agent = train_actor_critic.train(
            num_episodes=2,
            seed=42,
            duration_steps=50,
            output_model=out_model,
            output_log=out_log
        )
        
        self.assertTrue(os.path.exists(out_model), "ActorCritic model checkpoint must be created")
        self.assertGreater(os.path.getsize(out_model), 1000, "Model checkpoint must have non-zero size")
        
        self.assertTrue(os.path.exists(out_log), "ActorCritic CSV log must be created")
        with open(out_log, "r") as f:
            reader = list(csv.reader(f))
            self.assertEqual(len(reader), 3, "CSV must have header + 2 episode rows")
            header = reader[0]
            self.assertIn("Episode", header)
            self.assertIn("Reward", header)
            self.assertIn("ActorLoss", header)
            self.assertIn("CriticLoss", header)

if __name__ == "__main__":
    unittest.main()
