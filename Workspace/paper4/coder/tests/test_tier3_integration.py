# tests/test_tier3_integration.py
# ============================================================================
# Tier 3: Cross-Feature Integration Test Suite
# Tests multi-module feedback loops, multi-threaded hot-swap, and HPO pipelines.
# ============================================================================

import math
import time
import threading
import numpy as np
import pytest
import torch
from tests.contract_adapters import (
    extract_tls_features,
    predict_dynamics,
    HeuristicScheduler,
    StateVectorizer,
    ActionDecoder,
    RetrospectiveReplayBuffer,
    DummyPolicy,
    run_hpo_study,
    DualModelHotSwapManager,
    calculate_metrics,
)
from tests.conftest import DummyNode


class TestTier3Integration:
    """Tier 3: Cross-Feature Integration Verification."""

    def test_01_dynamics_and_heuristic_closed_loop(self):
        """Verify seamless pipeline: TLS dynamics extraction -> prediction -> heuristic grant adaptation."""
        scheduler = HeuristicScheduler(num_channels=4)

        # Scenario: Vehicle cruises, approaches red light, stops, and starts on green
        scenario_steps = [
            # (speed, tls_dict, expected_delta_range)
            (15.0, {"state": "g", "dist_to_stopline": 300.0, "time_to_switch": 20.0}, (1.0, 2.0)),   # Cruise
            (10.0, {"state": "r", "dist_to_stopline": 20.0, "time_to_switch": 15.0}, (0.1, 1.0)),    # Urgent stop
            (0.0,  {"state": "r", "dist_to_stopline": 5.0, "time_to_switch": 10.0}, (3.0, 45.0)),   # Backoff at red
            (0.0,  {"state": "r", "dist_to_stopline": 5.0, "time_to_switch": 1.5}, (0.1, 1.0)),     # Urgent start
        ]

        for step_idx, (speed, tls_info, expected_range) in enumerate(scenario_steps):
            stop_imm, start_imm = predict_dynamics(tls_info, current_speed=speed)
            state_dict = {
                "speed": speed,
                "stop_imminent": stop_imm,
                "start_imminent": start_imm,
                "time_to_switch": tls_info["time_to_switch"],
            }
            delta, ch, power = scheduler.decide_grant(f"veh_{step_idx}", state_dict)
            assert expected_range[0] <= delta <= expected_range[1], (
                f"Step {step_idx}: expected delta in {expected_range}, got {delta}"
            )
            assert 0 <= ch < 4
            assert 10.0 <= power <= 23.0

    def test_02_vectorizer_decoder_baselines_buffer_loop(self, synthetic_vehicle_node, synthetic_rsu_node):
        """Verify complete RL feedback loop: State -> Vectorizer -> Actor -> Decoder -> Buffer -> Update."""
        vectorizer = StateVectorizer(rsu_range=300.0)
        buffer = RetrospectiveReplayBuffer(capacity=500)
        agent = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)

        # Simulate 20 environment interaction steps
        cur_t = 0.0
        for step in range(20):
            # 1. State vectorization
            s = vectorizer.vectorize(synthetic_vehicle_node, synthetic_rsu_node, current_time=cur_t)

            # 2. Agent action selection
            grant, raw_action, _ = agent.select_action(s, deterministic=False)
            delta, ch, p = grant

            # 3. Step forward
            cur_t += delta
            synthetic_vehicle_node.pos[0] += synthetic_vehicle_node.vel[0] * delta
            s_next = vectorizer.vectorize(synthetic_vehicle_node, synthetic_rsu_node, current_time=cur_t)
            reward = -(delta * 0.5 + (p - 10.0) * 0.02)
            done = step == 19

            # 4. Push to SMDP replay buffer
            buffer.push(s, raw_action, reward, s_next, done, delta_t=delta)

        assert len(buffer) == 20
        # 5. Sample batch and train agent
        batch = buffer.sample(batch_size=8)
        loss_dict = agent.update(batch)
        assert "loss" in loss_dict
        assert not math.isnan(loss_dict["loss"])

    def test_03_concurrent_simulation_hot_swap(self):
        """Verify hot-swapping model parameters in the background while inference loop runs concurrently."""
        act_model = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=18, num_channels=4, hidden_dim=32)
        manager = DualModelHotSwapManager(act_model, rest_model)

        inference_count = 0
        stop_event = threading.Event()
        errors = []

        def serving_worker():
            nonlocal inference_count
            dummy_state = np.random.uniform(-1, 1, size=(18,)).astype(np.float32)
            while not stop_event.is_set():
                try:
                    grant, raw, _ = act_model.select_action(dummy_state)
                    inference_count += 1
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(e)

        serving_thread = threading.Thread(target=serving_worker, daemon=True)
        serving_thread.start()

        # Background training & hot-swap updates
        for swap_round in range(5):
            # Mutate rest model weights
            with torch.no_grad():
                for p in rest_model.parameters():
                    p.add_(torch.randn_like(p) * 0.01)
            time.sleep(0.01)
            success = manager.hot_swap()
            assert success is True

        stop_event.set()
        serving_thread.join(timeout=2.0)

        assert len(errors) == 0, f"Errors occurred during concurrent inference/hot-swap: {errors}"
        assert inference_count > 10, "Inference thread did not execute sufficient iterations"
        assert manager.swap_count == 5

    def test_04_optuna_to_evaluation_pipeline(self, temp_results_dir):
        """Verify end-to-end flow: Optuna searches params -> best model trained -> evaluated with 6 metrics."""
        # 1. Run quick HPO study
        study = run_hpo_study("DummyPolicy", model_cls=DummyPolicy, n_trials=3)
        best_params = study.best_params

        # 2. Instantiate model with best hyperparameters
        best_model = DummyPolicy(state_dim=18, num_channels=4, **best_params)

        # 3. Run evaluation benchmark loop
        sim_records = []
        for veh_id in range(10):
            dummy_state = np.random.uniform(-0.5, 0.5, size=(18,)).astype(np.float32)
            grant, raw, _ = best_model.select_action(dummy_state, deterministic=True)
            delta, ch, p = grant
            sim_records.append({
                "aoi": float(delta * 1.2),
                "peak_aoi": float(delta * 1.5),
                "error": float(np.random.exponential(scale=0.5)),
                "tx_attempts": 1,
                "tx_fails": 0,
                "power_dbm": float(p),
            })

        # 4. Calculate 6 IEEE TWC metrics
        metrics = calculate_metrics(sim_records)
        assert metrics["mean_aoi"] > 0
        assert metrics["packet_loss_rate"] == 0.0
        assert metrics["mean_error"] >= 0.0
        assert 10.0 <= metrics["avg_tx_power_dbm"] <= 23.0
