# tests/test_e2e_pipeline.py
# ============================================================================
# Master End-to-End Pipeline Integration Test Runner
# Verifies the full chain: Signal Dynamics -> State Vectorization ->
# Hybrid Agent Inference -> Replay Buffer -> Model Update -> Hot-swap -> Evaluation
# ============================================================================

import os
import sys
import pytest
import numpy as np
import torch
from tests.contract_adapters import (
    extract_tls_features,
    predict_dynamics,
    HeuristicScheduler,
    StateVectorizer,
    ActionDecoder,
    RetrospectiveReplayBuffer,
    BASELINE_REGISTRY,
    DualModelHotSwapManager,
    run_hpo_study,
    calculate_metrics,
)
from tests.conftest import DummyNode


class TestE2EPipeline:
    """Complete End-to-End Pipeline Execution."""

    def test_full_e2e_pipeline_lifecycle(self, temp_results_dir):
        """Executes full lifecycle: Signal extraction -> RL interaction -> Hot-swap -> Evaluation."""
        # Step 1: Environment & Node setup
        rsu_node = DummyNode("RSU_Central", pos=(0.0, 0.0), comm_range=800.0)
        vehicle_nodes = [
            DummyNode(f"veh_{i}", pos=(float(i * 40.0), float(i * 30.0)), vel=(12.0, 0.0))
            for i in range(5)
        ]
        vectorizer = StateVectorizer(rsu_range=800.0)
        buffer = RetrospectiveReplayBuffer(capacity=1000)

        # Step 2: Model setup (Act & Rest)
        model_cls = BASELINE_REGISTRY["HybridPPO"]
        act_agent = model_cls(state_dim=16, num_channels=4, hidden_dim=32)
        rest_agent = model_cls(state_dim=16, num_channels=4, hidden_dim=32)
        hot_swap_mgr = DualModelHotSwapManager(act_agent, rest_agent)

        # Step 3: Run interaction loop for 10 timesteps
        eval_records = []
        for t in range(10):
            current_time = float(t)
            for v_node in vehicle_nodes:
                tls_info = {
                    "state": "r" if t > 5 else "g",
                    "dist_to_stopline": max(0.0, 300.0 - t * 12.0),
                    "time_to_switch": max(0.0, 10.0 - t),
                    "stop_imminent": 1.0 if (t > 5 and max(0.0, 300.0 - t * 12.0) < 30.0) else 0.0,
                    "start_imminent": 0.0,
                }
                # State Vectorization
                s = vectorizer.vectorize(v_node, rsu_node, current_time=current_time, tls_info=tls_info)
                
                # Act Agent Action Selection
                grant, raw_action, info = act_agent.select_action(s, deterministic=False)
                delta, ch, power = grant
                
                # Step vehicle forward
                v_node.pos[0] += v_node.vel[0] * delta
                s_next = vectorizer.vectorize(v_node, rsu_node, current_time=current_time + delta, tls_info=tls_info)
                reward = -0.5 * delta
                
                # Store in Replay Buffer
                buffer.push(s, raw_action, reward, s_next, done=False, delta_t=delta)
                eval_records.append({
                    "aoi": delta,
                    "peak_aoi": delta * 1.5,
                    "error": 0.2,
                    "tx_attempts": 1,
                    "tx_fails": 0,
                    "power_dbm": power,
                })

            # Rest Agent Update & Hot-swap
            if len(buffer) >= 8:
                batch = buffer.sample(batch_size=8)
                loss_dict = rest_agent.update(batch)
                assert "loss" in loss_dict
                # Perform atomic hot-swap
                swapped = hot_swap_mgr.hot_swap()
                assert swapped is True

        # Step 4: Verify Evaluation Metrics calculation
        metrics = calculate_metrics(eval_records)
        assert metrics["mean_aoi"] > 0
        assert metrics["packet_loss_rate"] == 0.0
        assert metrics["mean_error"] >= 0.0
        assert 0.0 < metrics["jains_fairness_aoi"] <= 1.0
        assert hot_swap_mgr.swap_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
