#!/usr/bin/env python3
"""
test_c3_reward.py
=================
Independent Verification Suite for C-3 Reward Function Redesign & State Tracking.

Verifies:
  1. Exact mathematical formulation:
       over = max(0.0, cbr_smoothed - CBR_TARGET)
       osc = abs(cbr_smoothed - prev_cbr)
       stale = max(0.0, dt_since_last_cam - T_STALE)
       cost = 0.1 / max(T_GenCam, 1e-3)
       reward = -1.0 * over - 0.5 * osc - 0.3 * stale - 0.05 * cost
  2. Low-density trade-off:
       Confirms T_GenCam=0.1 (maximum rate) is NOT the unique optimum at low density.
       Verifies balance between transmission cost and staleness penalty.
  3. High-density congestion penalty:
       Confirms over-target CBR is strictly penalized.
  4. Oscillation suppression:
       Confirms rapid changes in CBR between steps are penalized.
  5. Hook class verification & State lifecycle:
       Tests DuelingDQNHook, SARSAHook, DecisionTransformerHook, MAPPOHook,
       ResNetMoEDQNHook, MoEDQNHook, VanillaDQNHook, etc.
       Verifies prev_cbr and prev_t_gencam tracking, reset_episode() clearing,
       and terminate_vehicle() cleanup.
"""

import os
import sys
import unittest
import numpy as np

# Ensure code directory is in sys.path
_code_dir = os.path.dirname(os.path.abspath(__file__))
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

from ai_dcc_hook import (
    CBR_TARGET,
    T_STALE,
    get_hook,
    DuelingDQNHook,
    SARSAHook,
    DecisionTransformerHook,
    MAPPOHook,
    ResNetMoEDQNHook,
    MoEDQNHook,
    VanillaDQNHook,
    DDQNHook,
    QLearningHook,
    ActorCriticHook,
    PPOHook,
    DDPGHook,
    SACHook,
    TD3Hook
)


class MockAgent:
    """Mock agent for testing transition storage and action execution."""
    def __init__(self, action_return=0):
        self.action_return = action_return
        self.transitions = []
        
    def act(self, *args, **kwargs):
        return self.action_return
        
    def store_transition(self, *args, **kwargs):
        self.transitions.append((args, kwargs))


class TestC3RewardDesign(unittest.TestCase):

    def test_01_constants_and_defaults(self):
        """Verify calibrated CBR_TARGET and T_STALE constants."""
        self.assertGreater(CBR_TARGET, 0.0)
        self.assertLess(CBR_TARGET, 0.3)
        self.assertEqual(T_STALE, 0.5)

    def test_02_low_density_tradeoff_no_forced_maximum_rate(self):
        """
        Verify that at low density, T_GenCam=0.1 is NOT the unique optimal action.
        Due to frequency cost (0.05 * cost) and staleness threshold (T_STALE=0.5),
        T_GenCam=0.5 gives higher reward than T_GenCam=0.1 while keeping stale penalty = 0.
        """
        hook = DuelingDQNHook()
        hook.reset_episode()
        
        cbr_low = 0.02
        vid = "veh_test_tradeoff"
        
        # Test reward for T_GenCam = 0.1s (dt = 0.1s)
        hook.prev_cbr[vid] = cbr_low
        r_01 = hook.compute_reward(cbr_smoothed=cbr_low, dt_since_last_cam=0.1, vid=vid, t_gencam=0.1)
        
        # Test reward for T_GenCam = 0.2s (dt = 0.2s)
        r_02 = hook.compute_reward(cbr_smoothed=cbr_low, dt_since_last_cam=0.2, vid=vid, t_gencam=0.2)
        
        # Test reward for T_GenCam = 0.5s (dt = 0.5s)
        r_05 = hook.compute_reward(cbr_smoothed=cbr_low, dt_since_last_cam=0.5, vid=vid, t_gencam=0.5)
        
        # Test reward for T_GenCam = 1.0s (dt = 1.0s) -> staleness penalty applies (1.0 - 0.5 = 0.5)
        r_10 = hook.compute_reward(cbr_smoothed=cbr_low, dt_since_last_cam=1.0, vid=vid, t_gencam=1.0)
        
        # Calculations:
        # r_01 = -0.05 * (0.1/0.1) = -0.050
        # r_02 = -0.05 * (0.1/0.2) = -0.025
        # r_05 = -0.05 * (0.1/0.5) = -0.010
        # r_10 = -0.3 * (1.0 - 0.5) - 0.05 * (0.1/1.0) = -0.150 - 0.005 = -0.155
        
        self.assertAlmostEqual(r_01, -0.050, places=4)
        self.assertAlmostEqual(r_02, -0.025, places=4)
        self.assertAlmostEqual(r_05, -0.010, places=4)
        self.assertAlmostEqual(r_10, -0.155, places=4)
        
        # Assert trade-off properties
        self.assertGreater(r_05, r_01, "T_GenCam=0.5 must yield higher reward than T_GenCam=0.1 at low density")
        self.assertGreater(r_02, r_01, "T_GenCam=0.2 must yield higher reward than T_GenCam=0.1 at low density")
        self.assertGreater(r_05, r_10, "T_GenCam=0.5 must yield higher reward than T_GenCam=1.0 due to staleness penalty")

    def test_03_high_density_over_target_penalty(self):
        """Verify strict over-target congestion penalty when CBR > CBR_TARGET."""
        hook = DuelingDQNHook()
        hook.reset_episode()
        vid = "veh_test_high_cbr"
        
        cbr_high = CBR_TARGET + 0.05  # 0.05 above target
        hook.prev_cbr[vid] = cbr_high
        
        r_congested = hook.compute_reward(cbr_smoothed=cbr_high, dt_since_last_cam=0.1, vid=vid, t_gencam=0.1)
        # over = 0.05 * (-1.0) = -0.05
        # cost = -0.05 * (0.1/0.1) = -0.05
        # total = -0.10
        self.assertAlmostEqual(r_congested, -0.100, places=4)

    def test_04_oscillation_penalty(self):
        """Verify oscillation penalty when CBR fluctuates rapidly."""
        hook = DuelingDQNHook()
        hook.reset_episode()
        vid = "veh_test_osc"
        
        hook.prev_cbr[vid] = 0.02
        cbr_new = 0.06  # jump of 0.04
        
        r_osc = hook.compute_reward(cbr_smoothed=cbr_new, dt_since_last_cam=0.1, vid=vid, t_gencam=0.1)
        # over = 0.0 (0.06 <= CBR_TARGET 0.075)
        # osc = 0.04 * (-0.5) = -0.02
        # cost = -0.05 * 1.0 = -0.05
        # total = -0.07
        self.assertAlmostEqual(r_osc, -0.070, places=4)

    def test_05_multi_step_prediction_and_state_tracking(self):
        """Verify sequential predict calls update prev_cbr and prev_t_gencam correctly."""
        hook = DuelingDQNHook(is_training=True)
        agent = MockAgent(action_return=0)  # action 0 -> t_act = 0.1, p_act = 0.0
        hook.set_agent(agent)
        hook.reset_episode()
        
        vid = "veh_seq_1"
        
        # Step 1: initial observation (no reward yet because no prior state)
        t_act1, p_act1 = hook.predict(cbr_global=0.02, n_neighbors=0.1, v_norm=0.5,
                                      dt_since_last_cam=0.1, cbr_smoothed=0.02, vid=vid)
        self.assertEqual(t_act1, 0.1)
        self.assertEqual(hook.prev_cbr[vid], 0.02)
        self.assertEqual(hook.prev_t_gencam[vid], 0.1)
        self.assertEqual(len(agent.transitions), 0)
        
        # Step 2: second observation (transitions recorded with new reward)
        t_act2, p_act2 = hook.predict(cbr_global=0.03, n_neighbors=0.2, v_norm=0.5,
                                      dt_since_last_cam=0.1, cbr_smoothed=0.03, vid=vid)
        self.assertEqual(len(agent.transitions), 1)
        self.assertEqual(hook.prev_cbr[vid], 0.03)
        
        # Verify transition contents
        args, kwargs = agent.transitions[0]
        s, a, r, s_next, done = args
        self.assertEqual(a, 0)
        self.assertFalse(done)
        # r = -1.0*0.0 - 0.5*abs(0.03-0.02) - 0.3*0.0 - 0.05*(0.1/0.1) = -0.005 - 0.05 = -0.055
        self.assertAlmostEqual(r, -0.055, places=4)

    def test_06_reset_and_termination_lifecycle(self):
        """Verify reset_episode and terminate_vehicle properly clean up dictionaries."""
        hook = DuelingDQNHook(is_training=True)
        agent = MockAgent()
        hook.set_agent(agent)
        
        vid1, vid2 = "v1", "v2"
        hook.predict(0.02, 0.1, 0.5, 0.1, 0.02, vid=vid1)
        hook.predict(0.03, 0.2, 0.5, 0.1, 0.03, vid=vid2)
        
        self.assertIn(vid1, hook.prev_cbr)
        self.assertIn(vid2, hook.prev_cbr)
        self.assertIn(vid1, hook.prev_t_gencam)
        self.assertIn(vid2, hook.prev_t_gencam)
        
        # Terminate vid1
        hook.terminate_vehicle(vid1)
        self.assertNotIn(vid1, hook.prev_cbr)
        self.assertNotIn(vid1, hook.prev_t_gencam)
        self.assertIn(vid2, hook.prev_cbr)
        
        # Reset episode
        hook.reset_episode()
        self.assertEqual(len(hook.prev_cbr), 0)
        self.assertEqual(len(hook.prev_t_gencam), 0)
        self.assertEqual(len(hook.prev_states), 0)
        self.assertEqual(len(hook.prev_actions), 0)
        self.assertEqual(hook.episode_reward, 0.0)

    def test_07_all_drl_hooks_reward_consistency(self):
        """Verify that all DRL hook classes share identical C-3 reward formulation."""
        hook_classes = [
            DuelingDQNHook,
            SARSAHook,
            DecisionTransformerHook,
            MAPPOHook,
            ResNetMoEDQNHook,
            MoEDQNHook,
            VanillaDQNHook,
            DDQNHook,
            QLearningHook,
            ActorCriticHook,
            PPOHook,
            DDPGHook,
            SACHook,
            TD3Hook
        ]
        
        for cls in hook_classes:
            hook = cls(is_training=True)
            hook.reset_episode()
            self.assertTrue(hasattr(hook, "prev_cbr"), f"{cls.__name__} missing prev_cbr")
            self.assertTrue(hasattr(hook, "prev_t_gencam"), f"{cls.__name__} missing prev_t_gencam")
            
            # Compute test reward
            r = hook.compute_reward(cbr_smoothed=0.08, dt_since_last_cam=0.6, vid=None, t_gencam=0.2)
            # over = 0.08 - 0.075 = 0.005 -> -0.005
            # osc = 0.0 -> 0.0
            # stale = 0.6 - 0.5 = 0.1 -> -0.03
            # cost = 0.1 / 0.2 = 0.5 -> -0.025
            # total = -0.060
            self.assertAlmostEqual(r, -0.060, places=4, msg=f"{cls.__name__} reward mismatch")


if __name__ == "__main__":
    print("=" * 70)
    print("  Running C-3 Independent Verification Suite: test_c3_reward.py")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestC3RewardDesign)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n[PASS] 100% of C-3 reward verification tests passed successfully (Exit Code 0).")
        sys.exit(0)
    else:
        print("\n[FAIL] Some tests failed.")
        sys.exit(1)
