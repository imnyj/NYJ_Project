# tests/test_rl_interface.py
# ============================================================================
# Comprehensive Unit & Integration Tests for RL Interface (S3 / R2)
#
# Tests:
# - StateVectorizer: 17-dim observation vector, normalization, n_queue, heading, no-leakage
# - ActionDecoder: Hybrid action mapping bounds ([0.1, 45.0]s, [10.0, 23.0]dBm), inverse encoding
# - RetrospectiveReplayBuffer: SMDP transition assembly, variable discount gamma^Delta, ring buffer
# ============================================================================

import math
import numpy as np
import pytest
import torch
from src.rl_interface import (
    StateVectorizer,
    ActionDecoder,
    RetrospectiveReplayBuffer,
    STATE_DIM,
    E_REF,
    DELTA_MIN,
    DELTA_MAX,
    P_MIN,
    P_MAX,
    get_sumo_max_red_phase_duration,
)


class DummyVehicle:
    def __init__(
        self,
        pos=(100.0, 200.0),
        vel=(12.0, -5.0),
        accel=-1.5,
        prev_t=10.0,
        n_queue=0.0,
    ) -> None:
        self.pos = list(pos)
        self.vel = list(vel)
        self.accel = accel
        self._prev_t = prev_t
        self.n_queue = n_queue

    def speed(self) -> float:
        return math.hypot(self.vel[0], self.vel[1])


class DummyRSU:
    def __init__(self, pos=(0.0, 0.0), comm_range=300.0) -> None:
        self.pos = list(pos)
        self.comm_range = comm_range


class TestStateVectorizer:
    """Test suite for StateVectorizer."""

    def test_vectorizer_shape_dtype_and_bounds(self):
        vectorizer = StateVectorizer(rsu_range=300.0, v_max=30.0, a_max=5.0)
        veh = DummyVehicle(pos=(150.0, 200.0), vel=(10.0, 10.0), accel=1.0, prev_t=5.0, n_queue=3.0)
        rsu = DummyRSU(pos=(0.0, 0.0), comm_range=300.0)
        tls_info = {
            "state": "r",
            "time_to_switch": 15.0,
            "dist_to_stopline": 50.0,
            "stop_imminent": 1.0,
            "start_imminent": 0.0,
            "n_queue": 3.0,
        }

        vec = vectorizer.vectorize(veh, rsu, current_time=8.0, tls_info=tls_info, cbr=0.4, n_active=20)
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (STATE_DIM,)
        assert vec.shape == (17,)
        assert vec.dtype == np.float32
        assert np.all(vec >= -1.0) and np.all(vec <= 1.0)

    def test_vectorizer_exact_feature_mapping(self):
        vectorizer = StateVectorizer(rsu_range=1000.0, v_max=20.0, a_max=4.0, queue_max=20.0)
        veh = DummyVehicle(pos=(300.0, 400.0), vel=(12.0, -16.0), accel=-2.0, prev_t=10.0, n_queue=5.0)
        # Feature [0] is the RSU's last prediction error, not age (design_spec_v2 D4/P4:
        # age is identically zero at every SMDP decision epoch, so the slot carried nothing).
        veh.last_pred_err = E_REF  # norm_sq_error(E_REF) == 0.5 by construction
        rsu = DummyRSU(pos=(0.0, 0.0), comm_range=1000.0)
        tls_info = {
            "state": "g",
            "time_to_switch": 30.0,
            "dist_to_stopline": 200.0,
            "stop_imminent": 0.0,
            "start_imminent": 1.0,
            "n_queue": 5.0,
        }

        vec = vectorizer.vectorize(veh, rsu, current_time=15.0, tls_info=tls_info, cbr=0.25, n_active=50)

        # [0] Last prediction error: e = E_REF -> e^2/(e^2 + E_REF^2) = 0.5
        assert np.isclose(vec[0], 0.5)
        # [1] Vx norm: 12.0 / 20.0 = 0.6
        assert np.isclose(vec[1], 0.6)
        # [2] Vy norm: -16.0 / 20.0 = -0.8
        assert np.isclose(vec[2], -0.8)
        # [3] Speed norm: hypot(12, -16) = 20.0 / 20.0 = 1.0
        assert np.isclose(vec[3], 1.0)
        # [4] Accel norm: -2.0 / 4.0 = -0.5
        assert np.isclose(vec[4], -0.5)
        # [5] Rel X: 300 / 1000 = 0.3
        assert np.isclose(vec[5], 0.3)
        # [6] Rel Y: 400 / 1000 = 0.4
        assert np.isclose(vec[6], 0.4)
        # [7] Distance: 500 / 1000 = 0.5
        assert np.isclose(vec[7], 0.5)
        # [8-10] TLS one-hot (green: [0, 0, 1])
        assert vec[8] == 0.0 and vec[9] == 0.0 and vec[10] == 1.0
        # [11] Switch time: 30 / 60 = 0.5
        assert np.isclose(vec[11], 0.5)
        # [12] Stopline dist: 200 / 1000 = 0.2
        assert np.isclose(vec[12], 0.2)
        # [13] Contention: 50 / 100 = 0.5
        assert np.isclose(vec[13], 0.5)
        # [14] CBR: 0.25
        assert np.isclose(vec[14], 0.25)
        # [15] n_queue norm: 5.0 / 20.0 = 0.25
        assert np.isclose(vec[15], 0.25)
        # [16] heading cosine: -(300*12 + 400*(-16)) / (500 * 20) = -(-2800) / 10000 = 0.28
        assert np.isclose(vec[16], 0.28)

    def test_vectorizer_no_future_or_error_leakage(self):
        vectorizer = StateVectorizer()
        veh = DummyVehicle()
        rsu = DummyRSU()
        vec = vectorizer.vectorize(veh, rsu, current_time=10.0)
        # Verify vectorizer contains strictly local observations (17 dimensions)
        assert len(vec) == 17
        # Check no inf/nan
        assert not np.any(np.isnan(vec))
        assert not np.any(np.isinf(vec))

    def test_vectorizer_dict_interface(self):
        vectorizer = StateVectorizer(rsu_range=300.0, v_max=30.0, a_max=5.0)
        state_dict = {
            "pos": (200.0, 100.0),
            "vel": (15.0, 0.0),
            "speed": 15.0,
            "accel": 0.0,
            "current_time": 20.0,
            "last_update_time": 18.0,
            "tls_features": {
                "state": "y",
                "time_to_switch": 6.0,
                "dist_to_stopline": 100.0,
                "stop_imminent": 1.0,
                "start_imminent": 0.0,
                "n_queue": 2.0,
            },
            "cbr": 0.5,
            "n_active": 30,
            "n_queue": 2.0,
            "heading": 0.8,
            "last_pred_err": E_REF,
        }
        vec = vectorizer.vectorize_from_dict(state_dict)
        assert vec.shape == (17,)
        # [0] last prediction error: e = E_REF -> 0.5 (was normalized age, now
        # structurally zero at every decision epoch -- see design_spec_v2 P4)
        assert vec[0] == pytest.approx(0.5)
        assert vec[8] == 0.0 and vec[9] == 1.0 and vec[10] == 0.0  # yellow


class TestActionDecoder:
    """Test suite for ActionDecoder."""

    def test_action_decoder_bounds(self):
        decoder = ActionDecoder(num_channels=4, delta_min=0.1, delta_max=45.0, p_min=10.0, p_max=23.0)
        
        # Test various extreme logit inputs
        test_cases = [
            [-100.0, 0, -100.0],
            [100.0, 3, 100.0],
            [0.0, 2, 0.0],
            [-5.0, 1, 5.0],
            [10.0, 7, -10.0],
        ]
        for raw in test_cases:
            delta, ch, power = decoder.decode_action(raw)
            assert 0.1 <= delta <= 45.0
            assert ch in [0, 1, 2, 3]
            assert 10.0 <= power <= 23.0

    def test_action_decoder_various_types(self):
        decoder = ActionDecoder(num_channels=4)
        
        # Midpoint raw logits: sigmoid(0) = 0.5.
        # Delta is GEOMETRIC (design_spec_v2 section 3), so the midpoint is the
        # geometric mean of the bounds, not the arithmetic one:
        #     delta = 0.1 * (45.0 / 0.1) ** 0.5 = sqrt(0.1 * 45.0) = 2.1213
        # This assertion used to expect 22.55, the arithmetic midpoint, and so
        # pinned `decode_action` to a linear mapping that contradicted both the
        # design and the decoder's own `delta_from_unit`. Power stays linear
        # because dBm is already logarithmic:
        #     power = 10.0 + 0.5 * (23.0 - 10.0) = 16.5
        t_raw = torch.tensor([0.0, 2.0, 0.0])
        d1, ch1, p1 = decoder.decode_action(t_raw)
        assert np.isclose(d1, math.sqrt(0.1 * 45.0))
        assert ch1 == 2
        assert np.isclose(p1, 16.5)

        # Dictionary
        d_raw = {"delta": 0.0, "ch": 1, "power": 0.0}
        d2, ch2, p2 = decoder.decode_action(d_raw)
        assert ch2 == 1
        assert np.isclose(d2, math.sqrt(0.1 * 45.0))
        assert np.isclose(p2, 16.5)

        # Numpy array
        np_raw = np.array([0.0, 3.0, 0.0], dtype=np.float32)
        d3, ch3, p3 = decoder.decode_action(np_raw)
        assert ch3 == 3
        assert np.isclose(d3, math.sqrt(0.1 * 45.0))
        assert np.isclose(p3, 16.5)

    def test_action_decoder_encode_decode_cycle(self):
        decoder = ActionDecoder(num_channels=4, delta_min=0.1, delta_max=45.0, p_min=10.0, p_max=23.0)
        delta_in = 5.5
        ch_in = 2
        p_in = 18.0

        raw = decoder.encode_action(delta_in, ch_in, p_in)
        delta_out, ch_out, p_out = decoder.decode_action(raw)

        assert np.isclose(delta_in, delta_out, atol=1e-3)
        assert ch_in == ch_out
        assert np.isclose(p_in, p_out, atol=1e-3)


class TestRetrospectiveReplayBuffer:
    """Test suite for RetrospectiveReplayBuffer."""

    def test_buffer_push_and_sample(self):
        buffer = RetrospectiveReplayBuffer(capacity=50, gamma=0.95)
        assert len(buffer) == 0

        for i in range(20):
            s = np.ones(STATE_DIM, dtype=np.float32) * i
            a = np.array([0.0, i % 4, 0.0], dtype=np.float32)
            r = -float(i) * 0.1
            ns = np.ones(STATE_DIM, dtype=np.float32) * (i + 1)
            done = (i == 19)
            delta_t = 1.0 + (i % 3) * 0.5
            buffer.push(s, a, r, ns, done, delta_t)

        assert len(buffer) == 20
        assert buffer.is_ready(10) is True
        assert buffer.is_ready(30) is False

        batch = buffer.sample(batch_size=8)
        assert batch["state"].shape == (8, STATE_DIM)
        assert batch["action"].shape == (8, 3)
        assert batch["reward"].shape == (8, 1)
        assert batch["next_state"].shape == (8, STATE_DIM)
        assert batch["done"].shape == (8, 1)
        assert batch["delta_t"].shape == (8, 1)
        assert batch["discount"].shape == (8, 1)

        # Check SMDP discount calculation: gamma^delta_t
        for dt, disc in zip(batch["delta_t"].flatten(), batch["discount"].flatten()):
            expected = 0.95 ** dt.item()
            assert np.isclose(disc.item(), expected, atol=1e-5)

    def test_buffer_ring_overwrite(self):
        buffer = RetrospectiveReplayBuffer(capacity=5, gamma=0.99)
        for i in range(12):
            buffer.push(np.full(STATE_DIM, i), np.array([0, 0, 0]), 1.0, np.full(STATE_DIM, i + 1), False, 1.0)
        assert len(buffer) == 5

    def test_buffer_empty_sample_raises_error(self):
        buffer = RetrospectiveReplayBuffer(capacity=10)
        with pytest.raises(ValueError):
            buffer.sample(4)

    def test_buffer_clear(self):
        buffer = RetrospectiveReplayBuffer(capacity=10)
        buffer.push(np.zeros(STATE_DIM), np.zeros(3), 0.0, np.zeros(STATE_DIM), False, 1.0)
        assert len(buffer) == 1
        buffer.clear()
        assert len(buffer) == 0


class TestDeltaMappingIsGeometricEverywhere:
    """Both decode paths must agree, and both must be geometric.

    `ActionDecoder` exposes two ways to turn a raw action into Delta:
    `delta_from_unit`, which every baseline calls, and `decode_action`, the
    fallback for logit-shaped actions. They disagreed by an order of magnitude
    at the midpoint (2.12 s vs 22.55 s) because only the first was geometric,
    while the class docstring claimed both were. Nothing exercised the fallback,
    so nothing caught it.
    """

    def test_decode_action_matches_delta_from_unit(self):
        decoder = ActionDecoder(num_channels=4)
        for logit in (-6.0, -4.0, -2.0, -0.5, 0.0, 0.5, 2.0, 4.0, 6.0):
            via_decode = decoder.decode_action([logit, 0, 0.0])[0]
            via_unit = decoder.delta_from_unit(1.0 / (1.0 + math.exp(-logit)))
            assert via_decode == pytest.approx(via_unit, rel=1e-9), (
                f"the two Delta paths disagree at logit {logit}"
            )

    def test_encode_decode_round_trip(self):
        decoder = ActionDecoder(num_channels=4)
        for delta in (0.1, 0.5, 2.0, 10.0, 30.0, 45.0):
            raw = decoder.encode_action(delta, 1, 15.0)
            back, ch, power = decoder.decode_action(raw)
            assert back == pytest.approx(delta, rel=1e-4), f"Delta {delta} did not survive"
            assert ch == 1
            assert power == pytest.approx(15.0, rel=1e-4)

    def test_relative_resolution_is_uniform(self):
        """The point of the geometric map: equal u steps give equal ratios.

        A linear map spends nearly all its resolution above 20 s and cannot
        express the sub-second intervals that a moving vehicle needs.
        """
        decoder = ActionDecoder(num_channels=4)
        ratios = [
            decoder.delta_from_unit(u + 0.1) / decoder.delta_from_unit(u)
            for u in (0.0, 0.2, 0.4, 0.6, 0.8)
        ]
        for r in ratios:
            assert r == pytest.approx(ratios[0], rel=1e-6)
