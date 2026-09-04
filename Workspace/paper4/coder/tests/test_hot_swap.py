# tests/test_hot_swap.py
# ============================================================================
# Unit and Integration Tests for Dual-Model Hot-Swap Training Pipeline (S4 / R4)
#
# Verifies:
# 1. DualModelHotSwapManager: parameter sync, buffer sync, NaN/Inf guards,
#    cross-device transfers, concurrency safety, statistics, and callbacks.
# 2. TransitionStreamer: non-blocking queue operations, overflow handling,
#    batch draining, and replay buffer ingestion.
# 3. BackgroundTrainer: background training thread, gradient steps, loss logging,
#    scheduled hot-swaps, and graceful shutdown.
# 4. HotSwapRLScheduler: grant generation, latency benchmarking, retrospective
#    reward computation, and transition streaming.
# 5. Full HotSwapTrainer & run_hot_swap_training loop.
# ============================================================================

import threading
import time
import pytest
import numpy as np
import torch
import torch.nn as nn

from src.hot_swap_trainer import (
    DualModelHotSwapManager,
    TransitionStreamer,
    BackgroundTrainer,
    HotSwapRLScheduler,
    HotSwapTrainer,
    run_hot_swap_training,
    select_default_devices,
)
from src.rl_interface import RetrospectiveReplayBuffer
from tests.contract_adapters import DummyPolicy
from src.rl_interface import STATE_DIM


class TestDualModelHotSwapManager:
    """Test suite for atomic hot-swapping and safety guards."""

    def test_hot_swap_parameter_synchronization(self):
        """Verify weights from Rest model are copied to Act model accurately."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)

        # Mutate Rest model weights to differ from Act model
        with torch.no_grad():
            for p in rest_model.parameters():
                p.add_(torch.randn_like(p) + 1.0)

        # Check weights are different before swap
        act_p0 = list(act_model.parameters())[0].clone()
        rest_p0 = list(rest_model.parameters())[0].clone()
        assert not torch.allclose(act_p0, rest_p0)

        manager = DualModelHotSwapManager(act_model, rest_model)
        success = manager.hot_swap()

        assert success is True
        assert manager.swap_count == 1
        assert manager.failed_swaps == 0

        # Check all weights match exactly after swap
        for p_act, p_rest in zip(act_model.parameters(), rest_model.parameters()):
            assert torch.allclose(p_act, p_rest)

    def test_hot_swap_buffer_synchronization(self):
        """Verify model buffers (e.g. running stats) are copied along with parameters."""
        class ModelWithBuffer(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(18, 4)
                self.register_buffer("running_mean", torch.zeros(4))

        act_m = ModelWithBuffer()
        rest_m = ModelWithBuffer()
        rest_m.running_mean.fill_(42.0)

        manager = DualModelHotSwapManager(act_m, rest_m)
        assert manager.hot_swap() is True
        assert torch.allclose(act_m.running_mean, torch.tensor([42.0, 42.0, 42.0, 42.0]))

    def test_hot_swap_nan_guard_rejects_and_preserves_act_model(self):
        """Verify NaN parameters in Rest model are rejected and do not corrupt Act model."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)

        manager = DualModelHotSwapManager(act_model, rest_model)
        assert manager.hot_swap() is True

        # Save clean snapshot of Act model weights
        clean_act_weights = [p.clone() for p in act_model.parameters()]

        # Inject NaN into Rest model
        with torch.no_grad():
            list(rest_model.parameters())[0][0, 0] = float("nan")

        swap_result = manager.hot_swap()
        assert swap_result is False
        assert manager.failed_swaps == 1

        # Check Act model was preserved intact
        for p_act, p_clean in zip(act_model.parameters(), clean_act_weights):
            assert torch.allclose(p_act, p_clean, equal_nan=False)

    def test_hot_swap_inf_guard_rejects_and_preserves_act_model(self):
        """Verify Inf parameters in Rest model are rejected and do not corrupt Act model."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)

        manager = DualModelHotSwapManager(act_model, rest_model)
        clean_act_weights = [p.clone() for p in act_model.parameters()]

        with torch.no_grad():
            list(rest_model.parameters())[0][0, 0] = float("inf")

        assert manager.hot_swap() is False
        assert manager.failed_swaps == 1

        for p_act, p_clean in zip(act_model.parameters(), clean_act_weights):
            assert torch.allclose(p_act, p_clean)

    def test_hot_swap_cross_device_transfer(self):
        """Verify weight synchronization between different devices (CPU and simulated device)."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=16)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=16)

        cpu_dev = torch.device("cpu")
        manager = DualModelHotSwapManager(act_model, rest_model, act_device=cpu_dev, rest_device=cpu_dev)

        with torch.no_grad():
            for p in rest_model.parameters():
                p.fill_(3.14159)

        assert manager.hot_swap() is True
        for p in act_model.parameters():
            assert torch.allclose(p, torch.tensor(3.14159))

    def test_hot_swap_concurrency_thread_safety(self):
        """Verify multi-threaded inference and simultaneous hot-swapping under mutex lock."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        manager = DualModelHotSwapManager(act_model, rest_model)

        stop_threads = threading.Event()
        inference_errors = []
        inference_count = [0]

        def inference_worker():
            s = torch.randn(1, STATE_DIM)
            while not stop_threads.is_set():
                try:
                    with manager.swap_lock:
                        out = act_model.actor(s)
                        assert not torch.isnan(out).any()
                    inference_count[0] += 1
                except Exception as e:
                    inference_errors.append(e)
                time.sleep(0.0001)

        threads = [threading.Thread(target=inference_worker) for _ in range(4)]
        for t in threads:
            t.start()

        # Perform 20 concurrent hot-swaps
        for i in range(20):
            with torch.no_grad():
                for p in rest_model.parameters():
                    p.fill_(float(i))
            success = manager.hot_swap()
            assert success is True
            time.sleep(0.002)

        stop_threads.set()
        for t in threads:
            t.join()

        assert len(inference_errors) == 0
        assert inference_count[0] > 50
        assert manager.swap_count >= 20

    def test_hot_swap_stats_and_callbacks(self):
        """Verify hot-swap statistics tracking and execution of registered callbacks."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=16)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=16)

        callback_invoked = [0]
        def on_swap(count):
            callback_invoked[0] += 1

        manager = DualModelHotSwapManager(act_model, rest_model, on_swap_callback=on_swap)
        manager.hot_swap()
        manager.hot_swap()

        stats = manager.get_stats()
        assert stats["swap_count"] == 2
        assert stats["failed_swaps"] == 0
        assert stats["last_swap_time"] > 0
        assert callback_invoked[0] == 2


class TestTransitionStreamer:
    """Test suite for non-blocking lock-free transition queue."""

    def test_streamer_push_and_drain(self):
        """Verify FIFO ordering and drain batch extraction."""
        streamer = TransitionStreamer(maxsize=100)
        assert streamer.is_empty()

        for i in range(10):
            streamer.push(
                state=np.full(STATE_DIM, i, dtype=np.float32),
                action=np.array([1.0, i % 4, 20.0], dtype=np.float32),
                reward=-float(i),
                next_state=np.full(STATE_DIM, i + 1, dtype=np.float32),
                done=(i == 9),
                delta_t=1.5,
            )

        assert streamer.qsize() == 10
        assert not streamer.is_empty()

        # Drain batch
        batch = streamer.drain(max_items=6)
        assert len(batch) == 6
        assert streamer.qsize() == 4
        assert batch[0]["reward"] == 0.0
        assert batch[5]["reward"] == -5.0

        # Drain remaining
        remaining = streamer.drain()
        assert len(remaining) == 4
        assert streamer.is_empty()

    def test_streamer_overflow_drops_oldest(self):
        """Verify bounded queue drops item when full without blocking."""
        streamer = TransitionStreamer(maxsize=5)

        for i in range(10):
            streamer.push(
                state=np.zeros(STATE_DIM),
                action=np.zeros(3),
                reward=float(i),
                next_state=np.zeros(STATE_DIM),
                done=False,
                delta_t=1.0,
            )

        assert streamer.qsize() == 5
        assert streamer.pushed_count == 5
        assert streamer.dropped_count == 5

        items = streamer.drain()
        assert len(items) == 5

    def test_streamer_drain_to_replay_buffer(self):
        """Verify direct bulk transfer from streamer to RetrospectiveReplayBuffer."""
        streamer = TransitionStreamer(maxsize=50)
        buffer = RetrospectiveReplayBuffer(capacity=100)

        for i in range(10):
            streamer.push(np.zeros(STATE_DIM), np.zeros(3), float(i), np.zeros(STATE_DIM), False, 1.0)

        n_drained = streamer.push_to_buffer(buffer)
        assert n_drained == 10
        assert len(buffer) == 10
        assert streamer.is_empty()


class TestBackgroundTrainer:
    """Test suite for background training worker and scheduled swaps."""

    def test_background_trainer_lifecycle(self):
        """Verify background training loop performs updates and scheduled hot-swaps."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        manager = DualModelHotSwapManager(act_model, rest_model)
        buffer = RetrospectiveReplayBuffer(capacity=1000)
        streamer = TransitionStreamer(maxsize=1000)

        # Seed replay buffer with initial random transitions
        s = np.random.uniform(-1, 1, size=(STATE_DIM,)).astype(np.float32)
        a = np.array([0.0, 1.0, 20.0], dtype=np.float32)
        for _ in range(64):
            buffer.push(s, a, -0.5, s, False, 1.0)

        trainer = BackgroundTrainer(
            rest_model=rest_model,
            replay_buffer=buffer,
            streamer=streamer,
            hot_swap_manager=manager,
            batch_size=16,
            swap_interval_steps=5,
        )

        # Execute 10 manual training steps
        for step in range(10):
            loss = trainer.train_step()
            assert loss is not None
            assert "loss" in loss

        assert trainer.training_steps == 10
        assert manager.swap_count == 2  # Swapped at step 5 and step 10

        # Test background thread start & stop
        trainer.start()
        # Stream additional transitions while thread is running
        for _ in range(32):
            streamer.push(s, a, -0.2, s, False, 1.0)
        time.sleep(0.05)
        trainer.stop()

        metrics = trainer.get_metrics()
        assert metrics["training_steps"] >= 10
        assert metrics["loss_history_len"] >= 10


class TestHotSwapRLScheduler:
    """Test suite for fast serving scheduler and retrospective transition assembly."""

    def test_scheduler_decide_grant_takes_environment_observations(self):
        """Grants come from the environment's own observation vector, not a re-vectorized dict.

        The scheduler used to accept a partial state dict and build its own
        vector; anything the dict omitted silently became a default, which is how
        15 of 17 dimensions reached the policy as constants. It now takes the
        vector the environment produced and rejects anything of the wrong width.
        """
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        manager = DualModelHotSwapManager(act_model, rest_model)
        streamer = TransitionStreamer(maxsize=100)

        scheduler = HotSwapRLScheduler(
            act_model=act_model,
            hot_swap_manager=manager,
            streamer=streamer,
        )

        s_vec = np.random.uniform(-1.0, 1.0, size=(STATE_DIM,)).astype(np.float32)
        # Four values now. The discrete action index the policy's discrete head
        # selected travels with the grant -- dropping it is what forced the five
        # discrete-head baselines onto a lossy index-reconstruction path -- and so
        # does the behaviour log-probability, without which the two PPO-family
        # baselines have no importance ratio and their clipping is inert.
        grant, raw_action, action_idx, behaviour_log_prob = scheduler.decide_grant("veh_0", s_vec)
        delta, ch, power = grant

        assert 0.1 <= delta <= 45.0
        assert 0 <= ch <= 3
        assert 10.0 <= power <= 23.0
        assert raw_action is not None
        # Pure inference: deciding a grant must not queue a transition by itself.
        assert streamer.is_empty()

        # A vector of the wrong width means someone re-vectorized upstream.
        with pytest.raises(AssertionError):
            scheduler.decide_grant("veh_0", np.zeros(STATE_DIM + 1, dtype=np.float32))

    def test_scheduler_push_transition_uses_measured_interval(self):
        """The environment prices the interval; the scheduler only forwards it."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        manager = DualModelHotSwapManager(act_model, rest_model)
        streamer = TransitionStreamer(maxsize=100)
        scheduler = HotSwapRLScheduler(
            act_model=act_model, hot_swap_manager=manager, streamer=streamer
        )

        s = np.zeros(STATE_DIM, dtype=np.float32)
        s2 = np.ones(STATE_DIM, dtype=np.float32)
        # delta_t is the MEASURED interval: a retried uplink runs past the
        # requested Delta, and gamma**delta_t must discount by what happened.
        scheduler.push_transition(
            state=s, raw_action=np.zeros(3, dtype=np.float32), reward=-0.42,
            next_state=s2, done=False, delta_t=2.7,
        )
        assert streamer.qsize() == 1
        item = streamer.drain()[0]
        assert item["reward"] == pytest.approx(-0.42)
        assert item["delta_t"] == pytest.approx(2.7)
        assert item["done"] is False

        scheduler.push_transition(
            state=s2, raw_action=np.zeros(3, dtype=np.float32), reward=-1.0,
            next_state=np.zeros(STATE_DIM, dtype=np.float32), done=True, delta_t=0.5,
        )
        assert streamer.drain()[0]["done"] is True

    def test_scheduler_latency_benchmarking(self):
        """Verify scheduler tracks inference latency and achieves sub-10ms serving latency."""
        act_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        rest_model = DummyPolicy(state_dim=STATE_DIM, num_channels=4, hidden_dim=32)
        manager = DualModelHotSwapManager(act_model, rest_model)
        streamer = TransitionStreamer(maxsize=500)

        scheduler = HotSwapRLScheduler(act_model=act_model, hot_swap_manager=manager, streamer=streamer)

        s_vec = np.random.uniform(-1.0, 1.0, size=(STATE_DIM,)).astype(np.float32)
        for _ in range(50):
            scheduler.decide_grant("v0", s_vec)

        lat_stats = scheduler.get_latency_stats()
        assert lat_stats["mean_latency_ms"] < 10.0
        assert scheduler.total_inferences == 50


class TestHotSwapTrainerAndLoop:
    """Test suite for full HotSwapTrainer class and run_hot_swap_training loop."""

    def test_hotswap_trainer_instantiation(self):
        """Verify HotSwapTrainer instantiates and runs with DummyPolicy."""
        trainer = HotSwapTrainer(
            model_cls=DummyPolicy,
            state_dim=STATE_DIM,
            num_channels=4,
            buffer_capacity=500,
            batch_size=8,
            swap_interval=5,
            hparams={"hidden_dim": 16, "lr": 1e-3},
        )

        assert trainer.act_model is not None
        assert trainer.rest_model is not None
        # The Rest -> Act synchronisation performed in __init__ is a
        # synchronisation, not a scheduled hot swap, and it is excluded from the
        # count. This assertion used to require the opposite, which meant every
        # swap-count assertion in the suite was satisfied by that one sync and
        # never actually observed a swap; it also put an off-by-one into any
        # swap count the paper reported.
        assert trainer.hot_swap_manager.swap_count == 0

        # Test feeding transitions and stepping
        s = np.zeros(STATE_DIM, dtype=np.float32)
        a = np.array([0.0, 0.0, 20.0], dtype=np.float32)
        for _ in range(16):
            trainer.replay_buffer.push(s, a, -0.1, s, False, 1.0)

        loss_dict = trainer.step_training_sync()
        assert loss_dict is not None
        assert "loss" in loss_dict

    def test_run_hot_swap_training_end_to_end(self, tmp_path):
        """Verify full run_hot_swap_training executes, triggers hot swaps, and returns summary metrics."""
        # Checkpoints and TensorBoard events go to a throwaway tree. Writing into
        # the real checkpoints/ would leave an 80-step DummyPolicy checkpoint for
        # the next `run_all.py --resume` to find.
        summary = run_hot_swap_training(
            model_name="DummyPolicy",
            model_cls=DummyPolicy,
            total_steps=80,
            batch_size=16,
            swap_interval=5,
            hparams={"hidden_dim": 16, "lr": 1e-3},
            num_vehicles=4,
            seed=42,
            checkpoint_dir=str(tmp_path / "checkpoints"),
            tensorboard_dir=str(tmp_path / "tensorboard"),
            # Third production path this test used to write into: without it the
            # run rewrites coder/logs/training/DummyPolicy_progress.csv.
            log_dir=str(tmp_path / "logs"),
        )

        assert summary["model_name"] == "DummyPolicy"
        assert summary["total_steps"] == 80
        assert summary["elapsed_seconds"] > 0
        assert summary["throughput_steps_per_sec"] > 0
        # >= 0, not >= 1: the initial Rest -> Act sync is no longer counted, so
        # this assertion is only satisfied by a genuinely scheduled swap. An
        # 80-step smoke run may or may not reach one, which is why the meaningful
        # check is the dedicated test below rather than a threshold here.
        assert summary["swap_count"] >= 0
        assert summary["failed_swaps"] == 0
        # C2: the summary reports the reward RATE, which is what selects _best.pt.
        assert "mean_reward_per_second" in summary
        assert "mean_reward_per_decision" in summary
        assert summary["inference_latency"]["mean_latency_ms"] < 10.0

    def test_select_default_devices(self):
        """Verify device selection logic handles CUDA and CPU seamlessly."""
        act_dev, rest_dev = select_default_devices()
        assert isinstance(act_dev, torch.device)
        assert isinstance(rest_dev, torch.device)
        if torch.cuda.is_available() and torch.cuda.device_count() >= 2:
            assert act_dev.type == "cuda" and act_dev.index == 0
            assert rest_dev.type == "cuda" and rest_dev.index == 1
        elif torch.cuda.is_available():
            assert act_dev.type == "cuda"
            assert rest_dev.type == "cuda"
        else:
            assert act_dev.type == "cpu"
            assert rest_dev.type == "cpu"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
