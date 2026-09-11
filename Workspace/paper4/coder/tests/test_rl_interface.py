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
import src.rl_interface as rli
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
        # The width is pinned to a LITERAL exactly once, here, so that an
        # unintended change to the observation still fails a test. Everywhere
        # else the assertion reads STATE_DIM, because restating the number in
        # several places tests the literal rather than the code and makes an
        # intended change look like a dozen failures.
        #
        # 21 as of 2026-09-06: 17 plus the four per-subchannel busy ratios at
        # [17..20]. Those were added because the action space contains a discrete
        # subchannel choice and the reward charges it against the occupancy of the
        # ONE chosen channel, while the observation carried only the mean over the
        # four -- measured at 1.81x to 3.20x the mean in spread, so the policy was
        # penalised on a quantity it could not see.
        assert STATE_DIM == 21, (
            f"the observation width is now {STATE_DIM}. If that was intended, "
            "update this literal and the reason above; if it was not, something "
            "changed src/rl_interface.py without meaning to."
        )
        assert vec.dtype == np.float32
        assert np.all(vec >= -1.0) and np.all(vec <= 1.0)

    def test_vectorizer_exact_feature_mapping(self):
        vectorizer = StateVectorizer(rsu_range=1000.0, v_max=20.0, a_max=4.0, queue_max=20.0)
        veh = DummyVehicle(pos=(300.0, 400.0), vel=(12.0, -16.0), accel=-2.0, prev_t=10.0, n_queue=5.0)
        # Feature [0] is the RSU's last prediction error, not age (design_spec_v2 D4/P4:
        # age is identically zero at every SMDP decision epoch, so the slot carried nothing).
        # Read E_REF LIVE, not from the import-time binding. `norm_sq_error`
        # resolves the module global on every call (so it tracks
        # `refresh_scenario_constants()`), and any test that ran a real SUMO
        # episode first will have moved it. Comparing a live computation against a
        # stale snapshot made this assertion depend on test ordering.
        veh.last_pred_err = rli.E_REF  # norm_sq_error(E_REF) == 0.5 by construction
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
        # [12] Stopline dist: 200 / DIST_TO_STOPLINE_REF_M.
        #
        # The divisor is NOT this vectoriser's `rsu_range`, and that separation is
        # the point of the assertion. Until 2026-09-06 feature [12] divided by the
        # coverage radius, which tied the distance at which a stop line stops
        # mattering to the distance at which a radio stops reaching -- two
        # unrelated quantities that then could not be changed independently.
        # Derived from the constant rather than restated as a literal, so moving
        # the bound does not require editing an expected number here.
        from src.rl_interface import DIST_TO_STOPLINE_REF_M

        assert np.isclose(vec[12], 200.0 / DIST_TO_STOPLINE_REF_M)
        assert not np.isclose(DIST_TO_STOPLINE_REF_M, vectorizer.rsu_range), (
            "the stop-line divisor has been set back to the coverage radius; the "
            "two were separated deliberately and share no reason to be equal"
        )
        # [13] Contention: normalised by the vectorizer's own ceiling, not by a
        # literal. It used to be `50 / 100 == 0.5`, and that 100 was the bug:
        # measured in-range counts reach 141.7, so the feature saturated at
        # densities 25, 30 and 35. Derive the expectation from the instance so a
        # future change to N_ACTIVE_MAX_OBS is reported by the assertion below
        # rather than by this line failing for the wrong reason.
        assert np.isclose(vec[13], 50.0 / vectorizer.n_active_max)
        assert vectorizer.n_active_max == pytest.approx(rli.N_ACTIVE_MAX_OBS)
        # [14] CBR: 0.25
        assert np.isclose(vec[14], 0.25)
        # [15] n_queue norm: 5.0 / 20.0 = 0.25
        assert np.isclose(vec[15], 0.25)
        # [16] heading cosine: -(300*12 + 400*(-16)) / (500 * 20) = -(-2800) / 10000 = 0.28
        assert np.isclose(vec[16], 0.28)

    # ------------------------------------------------------------------
    # Feature [13] saturation. The normaliser used to be a literal 100.0.
    # ------------------------------------------------------------------

    #: In-range vehicle counts measured on this scenario for the density grid
    #: 5, 10, 15, 20, 25, 30, 35 (recorded in src/evaluate.py and in the
    #: DENSITY_GRID docstring). The point of the fix is that NONE of these may
    #: reach the clip.
    MEASURED_IN_RANGE_COUNTS = [22.2, 36.7, 68.2, 91.5, 123.0, 138.3, 141.7]

    def test_contention_feature_does_not_saturate_at_any_trained_density(self):
        """[13] was clipped to exactly 1.0 at densities 25, 30 and 35.

        Three of the seven training densities, about 43 % of all episodes, and
        precisely the congested regime the scheduler exists for: the contention
        input reached the policy as the constant 1.0 wherever contention actually
        mattered. Same failure the speed feature had before `V_MAX_OBS`.
        """
        vectorizer = StateVectorizer()
        values = [
            float(vectorizer.vectorize_from_dict({"n_active": n})[13])
            for n in self.MEASURED_IN_RANGE_COUNTS
        ]
        assert all(v < 1.0 for v in values), (
            f"feature [13] still saturates: {values}"
        )
        # Strictly increasing, i.e. the busiest densities are still told apart.
        assert all(b > a for a, b in zip(values, values[1:])), values
        # The old literal is what this test exists to forbid: under /100 the last
        # three would all be 1.0.
        assert sum(1 for n in self.MEASURED_IN_RANGE_COUNTS if n / 100.0 >= 1.0) == 3, (
            "the measured counts no longer reproduce the bug this test guards"
        )

    def test_contention_normaliser_clears_the_measured_tail(self):
        """It must clear the measured PEAK, which the free-flow formula did not.

        This test used to require `N_ACTIVE_MAX_OBS` to EQUAL
        `max(DENSITY_GRID) * rsu_coverage_lane_km()`, and that requirement was the
        defect. The formula computes a free-flow capacity -- density times length
        presumes vehicles spread evenly -- and signals pack them instead. Measured
        over 128,223 transitions the in-coverage count reaches 194 against the
        formula's 168, clipping 9.31 % of rows, concentrated at exactly the
        densities the scheduler exists for.

        The formula's own evidence had said so and was read the wrong way round:
        the 141.7 it was checked against is a MEAN, and a ceiling that exists to
        prevent saturation has to clear a TAIL.

        So the property asserted now is the one that matters -- the ceiling clears
        the largest count anyone has measured, with margin -- rather than
        agreement with a particular derivation. `n_active_free_flow_capacity` is
        still exercised, because the manuscript describes what was replaced and a
        broken formula would make that description wrong too.
        """
        peak = 194.0   # measured 2026-09-06; see N_ACTIVE_MAX_OBS_MEASURED
        assert rli.N_ACTIVE_MAX_OBS >= peak, (
            f"the ceiling {rli.N_ACTIVE_MAX_OBS} does not clear the measured peak "
            f"of {peak}, so feature [13] saturates where congestion matters"
        )
        assert rli.N_ACTIVE_MAX_OBS >= peak * 1.15, (
            "no margin over the measured peak. Only three of the fifteen road "
            "cycles training uses were measured at full episode length, and the "
            "per-cycle maxima have a standard deviation of 10.4, so the peak on "
            "an unmeasured road is expected to be higher."
        )
        # The superseded formula still has to compute, because the manuscript
        # explains what it gave and why that was abandoned.
        assert rli.n_active_free_flow_capacity() == pytest.approx(
            max(float(d) for d in
                __import__("src.sumo.make_sumo_set", fromlist=["x"]).DENSITY_GRID)
            * __import__("src.sumo.make_sumo_set", fromlist=["x"]).rsu_coverage_lane_km()
        )
        assert rli.N_ACTIVE_MAX_OBS > max(self.MEASURED_IN_RANGE_COUNTS)

        # AND IT MUST NOT BE ARBITRARILY LARGE. Everything above is a floor, and
        # floors alone accept any ceiling whatever: 700, the physical-capacity
        # figure this project examined and rejected, passes every assertion above
        # it. A ceiling that clears the tail by a wide enough margin stops
        # clipping and starts erasing -- the surviving samples compress into the
        # bottom of [0, 1] and the feature shrinks relative to the rest of the
        # vector, which is the same loss of resolution by a different route.
        #
        # The property is stated on the normalised MEAN because that is what
        # "resolution" means here: how much of the unit interval the typical
        # observation occupies. The measured mean in-coverage count is 121.7, so
        # the ceiling in force gives 0.487 and 700 would give 0.174.
        #
        # 0.3 IS A CHOSEN THRESHOLD, NOT A MEASURED ONE. It was set by the team
        # lead on 2026-09-07 to sit between those two values; no experiment says
        # that a feature whose mean falls to 0.29 is harmed. It is recorded as a
        # decision so that whoever next raises the ceiling meets the reason for
        # the bound rather than only the bound.
        mean_in_range = 121.7
        floor = 0.3
        assert mean_in_range / rli.N_ACTIVE_MAX_OBS >= floor, (
            f"ceiling {rli.N_ACTIVE_MAX_OBS} puts the mean in-coverage count at "
            f"{mean_in_range / rli.N_ACTIVE_MAX_OBS:.3f} of the range, below the "
            f"{floor} floor: past clipping the cost of a larger ceiling is the "
            f"feature's size relative to the other twenty, and this is where that "
            f"cost was judged to start mattering."
        )
        # An explicit argument still wins, same convention as v_max / queue_max.
        assert StateVectorizer(n_active_max=333.0).n_active_max == pytest.approx(333.0)
        assert StateVectorizer(n_active_max=0.0).n_active_max == pytest.approx(
            rli.N_ACTIVE_MAX_OBS
        )

    def test_vectorizer_no_future_or_error_leakage(self):
        vectorizer = StateVectorizer()
        veh = DummyVehicle()
        rsu = DummyRSU()
        vec = vectorizer.vectorize(veh, rsu, current_time=10.0)
        # Verify vectorizer contains strictly local observations (17 dimensions)
        assert len(vec) == STATE_DIM
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
            "last_pred_err": rli.E_REF,  # live value; see note above
        }
        vec = vectorizer.vectorize_from_dict(state_dict)
        assert vec.shape == (STATE_DIM,)
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
