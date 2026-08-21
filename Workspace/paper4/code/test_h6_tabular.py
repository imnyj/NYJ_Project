#!/usr/bin/env python3
"""
test_h6_tabular.py
==================
Independent verification suite for H-6 Tabular Agent State Bounds & Train Step Fix.

Verifies:
1. QLearningAgent and SARSAAgent state_bounds are normalized to [(0.0, 1.0)]*5.
2. Discretization evenly maps [0.0, 1.0] inputs to all bins without collapsing to bin 0.
3. Default action_dim == 24 (etsi_cam_layer.ACTION_DIM) and Q-table shape (bins + (24,)).
4. train_step() is a valid no-op returning 0.0 without AttributeError.
5. select_action and act methods function identically with valid action range [0, 23].
6. store_transition properly updates Q-table for both Q-Learning and SARSA.
7. save/load persistence preserves all agent attributes and Q-values.
8. Integration with ai_dcc_hook.py QLearningHook and SARSAHook.
"""

import os
import sys
import tempfile
import unittest
import numpy as np

# Ensure code path is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from etsi_cam_layer import ACTION_DIM, PTX_GRID_DBM, T_GRID_S
from qlearning_agent import QLearningAgent
from sarsa_agent import SARSAAgent
from ai_dcc_hook import get_hook


class TestH6TabularAgents(unittest.TestCase):
    """Test suite for H-6 Tabular Agent fixes."""

    def test_01_state_bounds_normalization(self):
        """Verify all 5 dimensions of state_bounds are (0.0, 1.0)."""
        expected_bounds = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]
        
        q_agent = QLearningAgent(state_bins=[5, 5, 5, 5, 5])
        sarsa_agent = SARSAAgent(state_bins=[5, 5, 5, 5, 5])
        
        self.assertEqual(len(q_agent.state_bounds), 5, "QLearning state_bounds must be 5-dimensional")
        self.assertEqual(q_agent.state_bounds, expected_bounds, 
                         f"QLearning state_bounds must be {expected_bounds}, got {q_agent.state_bounds}")
        
        self.assertEqual(len(sarsa_agent.state_bounds), 5, "SARSA state_bounds must be 5-dimensional")
        self.assertEqual(sarsa_agent.state_bounds, expected_bounds, 
                         f"SARSA state_bounds must be {expected_bounds}, got {sarsa_agent.state_bounds}")

    def test_02_discretization_uniform_spread_and_no_bin0_collapse(self):
        """Verify normalized neighbor density inputs map evenly across all bins without collapsing to bin 0."""
        state_bins = [10, 10, 10, 10, 10]
        q_agent = QLearningAgent(state_bins=state_bins)
        sarsa_agent = SARSAAgent(state_bins=state_bins)
        
        # Test 10 evenly spaced values in [0.0, 1.0] for the 2nd feature (n_neighbors)
        # (cbr, n_neighbors, v_norm, dt, cbr_smooth)
        test_density_values = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
        expected_bins = list(range(10))  # Should map to bin 0, 1, 2, ..., 9
        
        q_bins = []
        sarsa_bins = []
        for val in test_density_values:
            state = [0.5, val, 0.5, 0.5, 0.5]
            q_d = q_agent.discretize_state(state)
            s_d = sarsa_agent.discretize_state(state)
            q_bins.append(q_d[1])
            sarsa_bins.append(s_d[1])
            
        self.assertEqual(q_bins, expected_bins, 
                         f"QLearning n_neighbors discretization failed: expected {expected_bins}, got {q_bins}")
        self.assertEqual(sarsa_bins, expected_bins, 
                         f"SARSA n_neighbors discretization failed: expected {expected_bins}, got {sarsa_bins}")
        
        # Verify boundary clipping
        # Exactly 0.0 -> bin 0
        self.assertEqual(q_agent.discretize_state([0.0]*5), (0, 0, 0, 0, 0))
        # Exactly 1.0 -> bin 9 (max bin index is state_bins[i] - 1 = 9)
        self.assertEqual(q_agent.discretize_state([1.0]*5), (9, 9, 9, 9, 9))
        self.assertEqual(sarsa_agent.discretize_state([1.0]*5), (9, 9, 9, 9, 9))
        # Out-of-bounds clipping: < 0.0 -> bin 0, > 1.0 -> bin 9
        self.assertEqual(q_agent.discretize_state([-0.5]*5), (0, 0, 0, 0, 0))
        self.assertEqual(q_agent.discretize_state([2.5]*5), (9, 9, 9, 9, 9))

    def test_03_default_action_dim_and_q_table_shape(self):
        """Verify default action_dim == 24 and Q-table shape matches."""
        self.assertEqual(ACTION_DIM, 24, "ACTION_DIM must be 24")
        
        bins = [4, 5, 3, 6, 2]
        q_agent = QLearningAgent(state_bins=bins)
        sarsa_agent = SARSAAgent(state_bins=bins)
        
        self.assertEqual(q_agent.action_dim, 24, f"QLearning default action_dim should be 24, got {q_agent.action_dim}")
        self.assertEqual(sarsa_agent.action_dim, 24, f"SARSA default action_dim should be 24, got {sarsa_agent.action_dim}")
        
        expected_shape = (4, 5, 3, 6, 2, 24)
        self.assertEqual(q_agent.q_table.shape, expected_shape, 
                         f"QLearning Q-table shape mismatch: expected {expected_shape}, got {q_agent.q_table.shape}")
        self.assertEqual(sarsa_agent.q_table.shape, expected_shape, 
                         f"SARSA Q-table shape mismatch: expected {expected_shape}, got {sarsa_agent.q_table.shape}")

    def test_04_train_step_noop(self):
        """Verify train_step() returns 0.0 and raises no exceptions."""
        q_agent = QLearningAgent(state_bins=[3, 3, 3, 3, 3])
        sarsa_agent = SARSAAgent(state_bins=[3, 3, 3, 3, 3])
        
        self.assertTrue(hasattr(q_agent, "train_step"), "QLearningAgent must have train_step method")
        self.assertTrue(hasattr(sarsa_agent, "train_step"), "SARSAAgent must have train_step method")
        
        q_loss = q_agent.train_step()
        sarsa_loss = sarsa_agent.train_step()
        
        self.assertEqual(q_loss, 0.0, "QLearningAgent.train_step() must return 0.0")
        self.assertEqual(sarsa_loss, 0.0, "SARSAAgent.train_step() must return 0.0")

    def test_05_select_action_and_exploration(self):
        """Verify select_action, act, evaluation deterministic greediness and valid action bounds [0, 23]."""
        bins = [4, 4, 4, 4, 4]
        q_agent = QLearningAgent(state_bins=bins, epsilon=0.0)
        sarsa_agent = SARSAAgent(state_bins=bins, epsilon=0.0)
        
        state = [0.2, 0.4, 0.6, 0.8, 0.5]
        d_state = q_agent.discretize_state(state)
        
        # Set a specific best action in Q-table
        target_action = 17
        q_agent.q_table[d_state][target_action] = 100.0
        sarsa_agent.q_table[d_state][target_action] = 100.0
        
        # Greedy act and select_action must choose target_action
        self.assertEqual(q_agent.act(state, evaluate=True), target_action)
        self.assertEqual(q_agent.select_action(state, evaluate=True), target_action)
        self.assertEqual(sarsa_agent.act(state, evaluate=True), target_action)
        self.assertEqual(sarsa_agent.select_action(state, evaluate=True), target_action)
        
        # In exploration mode (epsilon=1.0), actions must always fall within [0, 23]
        q_agent_explore = QLearningAgent(state_bins=bins, epsilon=1.0)
        for _ in range(100):
            act_val = q_agent_explore.act(state, evaluate=False)
            self.assertTrue(0 <= act_val < 24, f"Action {act_val} out of bounds [0, 23]")

    def test_06_store_transition_and_td_update(self):
        """Verify store_transition performs genuine TD updates for Q-learning and SARSA."""
        bins = [3, 3, 3, 3, 3]
        alpha = 0.5
        gamma = 0.9
        
        # Q-Learning TD update test
        q_agent = QLearningAgent(state_bins=bins, alpha=alpha, gamma=gamma)
        s = [0.1, 0.1, 0.1, 0.1, 0.1]
        next_s = [0.8, 0.8, 0.8, 0.8, 0.8]
        d_s = q_agent.discretize_state(s)
        d_next_s = q_agent.discretize_state(next_s)
        
        # Set initial Q-values
        q_agent.q_table[d_s][5] = 2.0
        q_agent.q_table[d_next_s][10] = 6.0  # max in next state
        
        # store_transition: r = 4.0, done = False
        # td_target = 4.0 + 0.9 * 6.0 = 9.4
        # td_error = 9.4 - 2.0 = 7.4
        # new_q = 2.0 + 0.5 * 7.4 = 5.7
        q_agent.store_transition(s, 5, 4.0, next_s, False)
        self.assertAlmostEqual(q_agent.q_table[d_s][5], 5.7, places=4, 
                               msg="QLearning TD update mismatch")
        
        # SARSA TD update test
        sarsa_agent = SARSAAgent(state_bins=bins, alpha=alpha, gamma=gamma)
        sarsa_agent.q_table[d_s][5] = 2.0
        sarsa_agent.q_table[d_next_s][8] = 4.0  # chosen next action
        sarsa_agent.q_table[d_next_s][10] = 10.0 # max (should be ignored when next_action=8)
        
        # store_transition with next_action=8:
        # td_target = 4.0 + 0.9 * 4.0 = 7.6
        # td_error = 7.6 - 2.0 = 5.6
        # new_q = 2.0 + 0.5 * 5.6 = 4.8
        sarsa_agent.store_transition(s, 5, 4.0, next_s, False, next_action=8)
        self.assertAlmostEqual(sarsa_agent.q_table[d_s][5], 4.8, places=4, 
                               msg="SARSA TD update with next_action mismatch")

    def test_07_save_and_load_persistence(self):
        """Verify save and load faithfully persist Q-tables, bounds, and hyperparameters."""
        bins = [4, 4, 4, 4, 4]
        q_agent = QLearningAgent(state_bins=bins, alpha=0.25, gamma=0.95, epsilon=0.45)
        state = [0.25, 0.5, 0.75, 0.1, 0.9]
        d_s = q_agent.discretize_state(state)
        q_agent.q_table[d_s][12] = 42.5
        
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "test_qlearning.pkl")
            q_agent.save(model_path)
            self.assertTrue(os.path.exists(model_path), "Model file should exist after save")
            
            # Load into fresh agent
            loaded_agent = QLearningAgent(state_bins=[2, 2, 2, 2, 2])
            loaded_agent.load(model_path)
            
            self.assertEqual(loaded_agent.action_dim, 24)
            self.assertEqual(loaded_agent.state_bins, bins)
            self.assertEqual(loaded_agent.state_bounds, [(0.0, 1.0)]*5)
            self.assertEqual(loaded_agent.alpha, 0.25)
            self.assertEqual(loaded_agent.gamma, 0.95)
            self.assertEqual(loaded_agent.epsilon, 0.45)
            self.assertAlmostEqual(loaded_agent.q_table[d_s][12], 42.5, places=5)
            self.assertEqual(loaded_agent.act(state, evaluate=True), 12)

    def test_08_hook_integration_with_ai_dcc(self):
        """Verify QLearningHook and SARSAHook interact properly with updated tabular agents."""
        q_agent = QLearningAgent(state_bins=[5, 5, 5, 5, 5], epsilon=0.0)
        sarsa_agent = SARSAAgent(state_bins=[5, 5, 5, 5, 5], epsilon=0.0)
        
        # Test QLearningHook
        q_hook = get_hook("QLearning")
        q_hook.set_agent(q_agent)
        q_hook.is_training = True
        q_hook.reset_episode()
        
        # First predict call for vid="veh_1"
        t1, p1 = q_hook.predict(0.04, 0.3, 0.5, 0.2, 0.04, vid="veh_1")
        self.assertIn(t1, T_GRID_S)
        self.assertIn(p1, PTX_GRID_DBM)
        
        # Second predict call (triggers store_transition)
        t2, p2 = q_hook.predict(0.05, 0.4, 0.5, 0.2, 0.05, vid="veh_1")
        self.assertIn(t2, T_GRID_S)
        self.assertIn(p2, PTX_GRID_DBM)
        
        # Test SARSAHook
        s_hook = get_hook("SARSA")
        s_hook.set_agent(sarsa_agent)
        s_hook.is_training = True
        s_hook.reset_episode()
        
        st1, sp1 = s_hook.predict(0.04, 0.3, 0.5, 0.2, 0.04, vid="veh_2")
        self.assertIn(st1, T_GRID_S)
        self.assertIn(sp1, PTX_GRID_DBM)
        
        st2, sp2 = s_hook.predict(0.05, 0.4, 0.5, 0.2, 0.05, vid="veh_2")
        self.assertIn(st2, T_GRID_S)
        self.assertIn(sp2, PTX_GRID_DBM)


if __name__ == "__main__":
    unittest.main(verbosity=2)
