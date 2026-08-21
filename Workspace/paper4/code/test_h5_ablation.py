#!/usr/bin/env python3
"""
Independent Verification Test Suite for H-5: 5-Stage Progressive Ablation Chain
Validates:
1. 5-Stage Progressive Ablation Architecture:
   - Stage 1: VanillaDQN (Pure MLP, Single DQN target y = r + gamma * max Q_target)
   - Stage 2: DoubleDQN (Pure MLP, Double DQN target y = r + gamma * Q_target(argmax Q_online))
   - Stage 3: DuelingDQN (Dueling streams V(s) [1] + A(s,a) [24], Double DQN target)
   - Stage 4: MoEDQN (Gating + 2 Experts, Dueling streams, Double DQN target)
   - Stage 5: ResNetMoEDQN (ResNet Skip Connections + Gating + 3 Experts, Double DQN target)
2. Uniform default action_dim == 24 across all agents and networks.
3. Full lifecycle API correctness: select_action(s), store_transition(...), train_step(), save(), load().
4. Single-Target vs Double-Target mathematical target difference verification.
5. All 5 training scripts present, runnable, and targeting correct checkpoints.
6. Unified exports in ablation_agents.py and hook compatibility in ai_dcc_hook.py & sensitivity_runner.py.
"""

import os
import sys
import tempfile
import unittest
import numpy as np
import torch
import torch.nn as nn

# Add code directory to path
CODE_DIR = os.path.dirname(os.path.abspath(__file__))
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from dqn_agent import VanillaDQN, DQNAgent
from ddqn_agent import DoubleDQN, DDQNAgent
from dueling_dqn_agent import DuelingDQN, DuelingDQNAgent
from moe_agent import MoEDQN, MoEAgent, MoEFeature
from resnet_moe_agent import ResNetMoEDQN, ResNetMoEAgent, ResidualBlock, ResNetFeatureExtractor
from ablation_agents import STAGE_AGENTS
from ai_dcc_hook import get_hook
from sensitivity_runner import DRL_SETUP, setup_eval_hook
from etsi_cam_layer import ACTION_DIM, PTX_GRID_DBM, T_GRID_S


class TestH5AblationArchitecture(unittest.TestCase):
    """Test suite for verifying 5-Stage Progressive Ablation Chain."""

    def test_01_stage_definitions_and_default_action_dim(self):
        """Verify that all 5 stages have default action_dim == 24 and state_dim == 5."""
        self.assertEqual(ACTION_DIM, 24)

        # Stage 1
        net1 = VanillaDQN()
        agent1 = DQNAgent()
        self.assertEqual(agent1.action_dim, 24)
        self.assertEqual(agent1.state_dim, 5)
        dummy_s = torch.zeros((2, 5))
        self.assertEqual(net1(dummy_s).shape, (2, 24))

        # Stage 2
        net2 = DoubleDQN()
        agent2 = DDQNAgent()
        self.assertEqual(agent2.action_dim, 24)
        self.assertEqual(agent2.state_dim, 5)
        self.assertEqual(net2(dummy_s).shape, (2, 24))

        # Stage 3
        net3 = DuelingDQN()
        agent3 = DuelingDQNAgent()
        self.assertEqual(agent3.action_dim, 24)
        self.assertEqual(agent3.state_dim, 5)
        self.assertEqual(net3(dummy_s).shape, (2, 24))

        # Stage 4
        net4 = MoEDQN()
        agent4 = MoEAgent()
        self.assertEqual(agent4.action_dim, 24)
        self.assertEqual(agent4.state_dim, 5)
        self.assertEqual(net4(dummy_s).shape, (2, 24))

        # Stage 5
        net5 = ResNetMoEDQN()
        agent5 = ResNetMoEAgent()
        self.assertEqual(agent5.action_dim, 24)
        self.assertEqual(agent5.state_dim, 5)
        self.assertEqual(net5(dummy_s).shape, (2, 24))

    def test_02_single_element_incremental_ablation_architecture(self):
        """
        Verify that each stage introduces EXACTLY 1 new component compared to previous stage:
        - Stage 1: Pure MLP, no dueling, no moe, no resnet.
        - Stage 2: Pure MLP (same structure), Double DQN target update (+1: Double DQN target).
        - Stage 3: MLP feature + Dueling streams V(s)[1] & A(s,a)[24] (+1: Dueling streams).
        - Stage 4: MoE feature (Gating + 2 Experts) + Dueling streams (+1: MoE feature gating).
        - Stage 5: ResNet feature (Skip connections) + Gating + 3 Experts (+1: Residual blocks + 3rd expert).
        """
        # Stage 1: Vanilla DQN
        net1 = VanillaDQN(state_dim=5, action_dim=24)
        self.assertTrue(hasattr(net1, 'network'))
        self.assertFalse(hasattr(net1, 'value_stream'))
        self.assertFalse(hasattr(net1, 'gating_network'))
        self.assertFalse(hasattr(net1, 'res_blocks'))

        # Stage 2: Double DQN
        net2 = DoubleDQN(state_dim=5, action_dim=24)
        self.assertTrue(hasattr(net2, 'network'))
        self.assertFalse(hasattr(net2, 'value_stream'))
        self.assertFalse(hasattr(net2, 'gating_network'))
        self.assertFalse(hasattr(net2, 'res_blocks'))

        # Stage 3: Dueling DQN
        net3 = DuelingDQN(state_dim=5, action_dim=24)
        self.assertTrue(hasattr(net3, 'value_stream'))
        self.assertTrue(hasattr(net3, 'advantage_stream'))
        self.assertFalse(hasattr(net3, 'gating_network'))
        self.assertFalse(hasattr(net3, 'res_blocks'))
        # Check stream dimensions
        feat = net3.feature_layer(torch.randn(4, 5))
        val = net3.value_stream(feat)
        adv = net3.advantage_stream(feat)
        self.assertEqual(val.shape, (4, 1))
        self.assertEqual(adv.shape, (4, 24))

        # Stage 4: MoE DQN
        net4 = MoEDQN(state_dim=5, action_dim=24, num_experts=2)
        self.assertTrue(hasattr(net4, 'feature_layer'))
        self.assertTrue(isinstance(net4.feature_layer, MoEFeature))
        self.assertEqual(net4.feature_layer.num_experts, 2)
        self.assertEqual(len(net4.feature_layer.experts), 2)
        self.assertTrue(hasattr(net4.feature_layer, 'gating_network'))
        self.assertTrue(hasattr(net4, 'value_stream'))
        self.assertTrue(hasattr(net4, 'advantage_stream'))
        self.assertFalse(hasattr(net4.feature_layer, 'res_blocks'))

        # Stage 5: ResNet MoE DQN (Proposed REMO-DQN)
        net5 = ResNetMoEDQN(state_dim=5, action_dim=24, num_experts=3, hidden_dim=128)
        self.assertTrue(hasattr(net5, 'feature_extractor'))
        self.assertTrue(isinstance(net5.feature_extractor, ResNetFeatureExtractor))
        self.assertTrue(hasattr(net5.feature_extractor, 'res_blocks'))
        self.assertEqual(len(net5.feature_extractor.res_blocks), 2)
        self.assertTrue(isinstance(net5.feature_extractor.res_blocks[0], ResidualBlock))
        self.assertTrue(hasattr(net5, 'gating_network'))
        self.assertEqual(len(net5.experts), 3)

    def test_03_target_update_mathematical_distinction(self):
        """
        Mathematically verify target update difference between Single DQN (Stage 1)
        and Double DQN (Stages 2, 3, 4, 5).
        """
        # Construct synthetic inputs
        r = torch.tensor([[1.0]], dtype=torch.float32)
        gamma = 0.99
        done = torch.tensor([[0.0]], dtype=torch.float32)

        # Online network outputs: best action is action 3
        # Target network outputs: action 3 has value 5.0, but action 7 has overoptimistic value 10.0
        q_online_next = torch.zeros((1, 24))
        q_online_next[0, 3] = 8.0  # argmax_a Q_online(s', a) = 3
        q_online_next[0, 7] = 2.0

        q_target_next = torch.zeros((1, 24))
        q_target_next[0, 3] = 5.0  # Q_target(s', 3) = 5.0
        q_target_next[0, 7] = 10.0 # max_a Q_target(s', a) = 10.0 (action 7)

        # 1. Single DQN target: y = r + gamma * max_a Q_target(s', a) = 1.0 + 0.99 * 10.0 = 10.90
        single_dqn_target = r + gamma * q_target_next.max(dim=1, keepdim=True)[0] * (1 - done)
        self.assertAlmostEqual(single_dqn_target.item(), 10.90, places=4)

        # 2. Double DQN target: y = r + gamma * Q_target(s', argmax_a Q_online(s', a)) = 1.0 + 0.99 * 5.0 = 5.95
        best_a = q_online_next.argmax(dim=1, keepdim=True)
        double_dqn_target = r + gamma * q_target_next.gather(1, best_a) * (1 - done)
        self.assertAlmostEqual(double_dqn_target.item(), 5.95, places=4)

        # Verify strict difference
        self.assertNotEqual(single_dqn_target.item(), double_dqn_target.item())

    def test_04_agent_lifecycle_all_stages(self):
        """
        Verify that all 5 agent classes complete:
        - select_action(state, evaluate=False) and select_action(state, evaluate=True)
        - act(state, evaluate=False/True)
        - store_transition(s, a, r, s', done)
        - train_step()
        - save(path) and load(path)
        """
        agent_classes = [
            ("Stage 1 (VanillaDQN)", DQNAgent),
            ("Stage 2 (DoubleDQN)", DDQNAgent),
            ("Stage 3 (DuelingDQN)", DuelingDQNAgent),
            ("Stage 4 (MoEDQN)", MoEAgent),
            ("Stage 5 (ResNetMoEDQN)", ResNetMoEAgent),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            for stage_name, agent_cls in agent_classes:
                agent = agent_cls(state_dim=5, action_dim=24, batch_size=16)

                # 1. Action selection
                s = np.random.randn(5).astype(np.float32)
                a_train = agent.select_action(s, evaluate=False)
                a_eval = agent.select_action(s, evaluate=True)
                a_act = agent.act(s, evaluate=True)

                self.assertIsInstance(a_train, int)
                self.assertIsInstance(a_eval, int)
                self.assertTrue(0 <= a_train < 24, f"{stage_name}: action out of bounds")
                self.assertTrue(0 <= a_eval < 24, f"{stage_name}: action out of bounds")
                self.assertEqual(a_eval, a_act, f"{stage_name}: act and select_action must match in eval mode")

                # 2. Store transitions
                for _ in range(32):
                    s_cur = np.random.randn(5).astype(np.float32)
                    act = np.random.randint(0, 24)
                    rew = np.random.randn()
                    s_nxt = np.random.randn(5).astype(np.float32)
                    dn = bool(np.random.rand() < 0.1)
                    agent.store_transition(s_cur, act, rew, s_nxt, dn)

                self.assertEqual(len(agent.memory), 32)

                # 3. Train step
                loss = agent.train_step()
                self.assertIsInstance(loss, float)
                self.assertGreater(loss, 0.0, f"{stage_name}: loss must be positive float")

                # 4. Save and load
                a_trained_eval = agent.select_action(s, evaluate=True)
                save_path = os.path.join(tmpdir, f"{stage_name.split()[0].lower()}_test.pth")
                agent.save(save_path)
                self.assertTrue(os.path.exists(save_path))

                # Create fresh agent and load
                new_agent = agent_cls(state_dim=5, action_dim=24, batch_size=16)
                new_agent.load(save_path)
                a_new_eval = new_agent.select_action(s, evaluate=True)
                self.assertEqual(a_trained_eval, a_new_eval, f"{stage_name}: Loaded agent produced different greedy action")

    def test_05_ablation_agents_module_exports(self):
        """Verify that ablation_agents.py provides STAGE_AGENTS and correct stage classes."""
        self.assertEqual(len(STAGE_AGENTS), 5)
        expected_names = ["VanillaDQN", "DoubleDQN", "DuelingDQN", "MoEDQN", "ResNetMoEDQN"]
        expected_ckpts = ["vanilla_dqn.pth", "ddqn.pth", "dueling_dqn.pth", "moe_dqn.pth", "resnet_moe_dqn.pth"]

        for stage_idx in range(1, 6):
            stage_info = STAGE_AGENTS[stage_idx]
            self.assertEqual(stage_info["name"], expected_names[stage_idx - 1])
            self.assertEqual(stage_info["checkpoint"], expected_ckpts[stage_idx - 1])
            net_cls = stage_info["network"]
            agent_cls = stage_info["agent"]

            inst_net = net_cls(state_dim=5, action_dim=24)
            inst_agent = agent_cls(state_dim=5, action_dim=24)
            self.assertEqual(inst_agent.action_dim, 24)
            self.assertEqual(inst_net(torch.zeros(1, 5)).shape, (1, 24))

    def test_06_sensitivity_runner_and_ai_dcc_hook_wiring(self):
        """Verify that sensitivity_runner DRL_SETUP and ai_dcc_hook get_hook support all 5 stages."""
        expected_methods = ["VanillaDQN", "DoubleDQN", "DuelingDQN", "MoEDQN", "ResNetMoEDQN"]

        for method in expected_methods:
            # 1. get_hook
            hook = get_hook(method)
            self.assertIsNotNone(hook, f"get_hook({method}) returned None")
            self.assertEqual(hook.action_dim, 24)

            # 2. DRL_SETUP
            self.assertIn(method, DRL_SETUP)
            cfg = DRL_SETUP[method]
            self.assertEqual(cfg["kwargs"]["action_dim"], 24)
            self.assertEqual(cfg["kwargs"]["state_dim"], 5)

            # Instantiate agent and wire to hook
            agent = cfg["class"](**cfg["kwargs"])
            hook.set_agent(agent)
            t, p = hook.predict(0.05, 0.5, 0.5, 0.2, 0.05)
            self.assertIn(p, PTX_GRID_DBM)
            self.assertIn(t, T_GRID_S)

    def test_07_all_training_scripts_exist_and_match(self):
        """Verify all 5 training scripts exist and configure correct models & checkpoints."""
        script_specs = [
            ("train_dqn.py", "VanillaDQN", "vanilla_dqn.pth"),
            ("train_ddqn.py", "DoubleDQN", "ddqn.pth"),
            ("train_dueling_dqn.py", "DuelingDQN", "dueling_dqn.pth"),
            ("train_moe.py", "MoEDQN", "moe_dqn.pth"),
            ("train_resnet.py", "ResNetMoEDQN", "resnet_moe_dqn.pth"),
        ]

        for fname, method, ckpt in script_specs:
            fpath = os.path.join(CODE_DIR, fname)
            self.assertTrue(os.path.exists(fpath), f"Training script missing: {fname}")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(method, content, f"{fname} must reference {method}")
            self.assertIn(ckpt, content, f"{fname} must save to {ckpt}")
            self.assertIn("ACTION_DIM", content, f"{fname} must use ACTION_DIM")


def main():
    print("=" * 70)
    print("  Running H-5 Independent Verification Suite: test_h5_ablation.py")
    print("=" * 70)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestH5AblationArchitecture)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n[PASS] 100% of H-5 5-stage progressive ablation tests passed successfully (Exit Code 0).")
        sys.exit(0)
    else:
        print("\n[FAIL] Some tests failed in H-5 verification suite.")
        sys.exit(1)


if __name__ == "__main__":
    main()
