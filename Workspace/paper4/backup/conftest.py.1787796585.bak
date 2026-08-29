# tests/conftest.py
# ============================================================================
# Pytest Fixtures for 4-Tier AoI-aware V2I Uplink RL Testing Suite
# ============================================================================

import os
import shutil
import tempfile
import pytest
import numpy as np
import torch
from tests.contract_adapters import BASELINE_REGISTRY, StateVectorizer, ActionDecoder, RetrospectiveReplayBuffer


class DummyNode:
    def __init__(self, node_id: str, pos=(0.0, 0.0), vel=(10.0, 0.0), comm_range=800.0) -> None:
        self.id = node_id
        self.pos = list(pos)
        self.vel = list(vel)
        self.comm_range = comm_range
        self._prev_pos = list(pos)
        self._prev_t = 0.0
        self.accel = 0.0

    def speed(self) -> float:
        return float(np.hypot(self.vel[0], self.vel[1]))

    def distance_to(self, other) -> float:
        return float(np.hypot(self.pos[0] - other.pos[0], self.pos[1] - other.pos[1]))


@pytest.fixture
def synthetic_vehicle_node():
    return DummyNode("veh_test_01", pos=(150.0, 200.0), vel=(12.0, 0.0))


@pytest.fixture
def synthetic_rsu_node():
    return DummyNode("rsu_test_01", pos=(0.0, 0.0), comm_range=800.0)


@pytest.fixture
def sample_state_vector():
    # 16-dim normalized observation vector
    return np.random.uniform(-0.5, 0.5, size=(16,)).astype(np.float32)


@pytest.fixture
def sample_batch():
    batch_size = 32
    return {
        "state": torch.randn(batch_size, 16, dtype=torch.float32),
        "action": torch.randn(batch_size, 3, dtype=torch.float32),
        "reward": torch.randn(batch_size, 1, dtype=torch.float32),
        "next_state": torch.randn(batch_size, 16, dtype=torch.float32),
        "done": torch.zeros(batch_size, 1, dtype=torch.float32),
        "delta_t": torch.ones(batch_size, 1, dtype=torch.float32) * 1.5,
    }


@pytest.fixture
def model_factory():
    def _create_model(model_name: str, **kwargs):
        if model_name not in BASELINE_REGISTRY:
            raise KeyError(f"Unknown baseline model: {model_name}")
        cls = BASELINE_REGISTRY[model_name]
        return cls(**kwargs)
    return _create_model


@pytest.fixture
def temp_results_dir():
    d = tempfile.mkdtemp(prefix="aoi_test_results_")
    yield d
    shutil.rmtree(d, ignore_errors=True)
