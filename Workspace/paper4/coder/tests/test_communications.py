"""PHY numeric regression tests (critic-physics L10).

Every constant in `src/Communications.py` is claimed in the paper to be DERIVED
FROM THE STANDARD rather than tuned. That claim is only as good as a test that
notices when one of them moves: before this file there was no test anywhere in
the suite that pinned `path_loss_db`, `noise_floor_dbm`, `frame_airtime_s`,
`sensitivity_dbm` or `rayleigh_success_prob` against their closed forms, so a
change to `PL_EXP` or `OPERATING_RATE_MBPS` would have propagated silently into
every number in the results tables.

Each expected value below is recomputed here from the standard's own formula, not
copied from the implementation.
"""

import math

import pytest

import src.Communications as comm


class TestPhysicalConstants:
    def test_free_space_reference_loss_at_1m(self):
        expected = 20.0 * math.log10(4.0 * math.pi * comm.FREQ_HZ / comm.C_LIGHT)
        assert comm._PL_REF_DB == pytest.approx(47.8588, abs=1e-4)
        assert comm._PL_REF_DB == pytest.approx(expected, rel=1e-12)

    def test_path_loss_follows_log_distance_model(self):
        # PL(d) = PL(1 m) + 10 n log10(d)
        for d in (1.0, 10.0, 100.0, 300.0):
            expected = comm._PL_REF_DB + 10.0 * comm.PL_EXP * math.log10(d)
            assert comm.path_loss_db(d) == pytest.approx(expected, rel=1e-12)
        # Doubling the distance costs exactly 10 n log10(2) dB.
        step = comm.path_loss_db(200.0) - comm.path_loss_db(100.0)
        assert step == pytest.approx(10.0 * comm.PL_EXP * math.log10(2.0), rel=1e-12)

    def test_noise_floor_is_ktb_plus_noise_figure(self):
        # -174 dBm/Hz + 10log10(10 MHz) + NF 9 dB = -95.0 dBm
        expected = -174.0 + 10.0 * math.log10(comm.SUBCHANNEL_BW_HZ) + comm.NOISE_FIGURE_DB
        assert comm.noise_floor_dbm() == pytest.approx(-95.0, abs=1e-9)
        assert comm.noise_floor_dbm() == pytest.approx(expected, rel=1e-12)

    def test_noise_floor_uses_subchannel_bandwidth_not_the_aggregate(self):
        """`num_subchannels` is deliberately ignored -- an 802.11p channel is 10 MHz.

        Dividing TOTAL_BW_HZ by the channel count would make a 3-channel
        configuration report a 13.3 MHz channel the PHY cannot produce.
        """
        assert comm.noise_floor_mw(3) == comm.noise_floor_mw(4) == comm.noise_floor_mw(1)

    def test_sensitivity_is_noise_floor_plus_mcs_threshold(self):
        assert comm.SINR_TH_DB == pytest.approx(10.0, abs=1e-9)
        expected = comm.noise_floor_dbm() + comm.get_mcs(comm.OPERATING_RATE_MBPS).req_sinr_db
        assert comm.sensitivity_dbm() == pytest.approx(-85.0, abs=1e-9)
        assert comm.sensitivity_dbm() == pytest.approx(expected, rel=1e-12)

    def test_frame_airtime_from_ofdm_symbol_count(self):
        # N_sym = ceil((16 + 8L + 6) / N_DBPS); airtime = 40 us + 8 us * N_sym
        mcs = comm.get_mcs(comm.OPERATING_RATE_MBPS)
        bits = comm.SERVICE_BITS + 8 * comm.STATUS_UPDATE_BYTES + comm.TAIL_BITS
        n_sym = math.ceil(bits / mcs.bits_per_symbol)
        expected = comm.PREAMBLE_SIGNAL_TIME_S + comm.OFDM_SYMBOL_TIME_S * n_sym
        assert comm.frame_symbols() == n_sym
        assert comm.frame_airtime_s() == pytest.approx(448.0e-6, abs=1e-12)
        assert comm.frame_airtime_s() == pytest.approx(expected, rel=1e-12)

    def test_mcs_rate_is_consistent_with_its_symbol_payload(self):
        for rate in (3.0, 6.0, 12.0):
            mcs = comm.get_mcs(rate)
            assert mcs.bits_per_symbol / comm.OFDM_SYMBOL_TIME_S == pytest.approx(
                mcs.rate_mbps * 1e6, rel=1e-9
            )


class TestRayleighSuccessProbability:
    """P_succ = exp(-th*N0/S) * PROD_k 1/(1 + th*I_k/S)."""

    def test_no_interferer_matches_closed_form(self):
        s, n0, th = 1e-6, 1e-9, 10.0
        assert comm.rayleigh_success_prob(s, [], n0, th) == pytest.approx(
            math.exp(-th * n0 / s), rel=1e-12
        )

    def test_one_and_two_interferers_match_closed_form(self):
        s, n0, th = 1e-6, 1e-9, 10.0
        i1, i2 = 2e-7, 5e-8
        one = math.exp(-th * n0 / s) / (1.0 + th * i1 / s)
        two = one / (1.0 + th * i2 / s)
        assert comm.rayleigh_success_prob(s, [i1], n0, th) == pytest.approx(one, rel=1e-12)
        assert comm.rayleigh_success_prob(s, [i1, i2], n0, th) == pytest.approx(two, rel=1e-12)

    def test_zero_signal_never_succeeds(self):
        assert comm.rayleigh_success_prob(0.0, [], 1e-9, 10.0) == 0.0

    def test_link_budget_makes_the_power_floor_genuinely_risky(self):
        """The [10, 23] dBm action range must be a real trade-off, not decoration."""
        comm.seed_channel(7)
        p_low = comm.judge_uplink([("v", 10.0, 300.0)], shadowing_sigma_db=0.0)["v"]
        p_high = comm.judge_uplink([("v", 23.0, 300.0)], shadowing_sigma_db=0.0)["v"]
        assert 0.4 < p_low < 0.7
        assert p_high > 0.95
        assert p_high > p_low


class TestOverlapAndInterferenceContract:
    def test_overlap_graph_is_symmetric(self):
        """A's frame collides with B's iff B's collides with A's.

        The environment used to draw `draw_overlap` per ORDERED pair, producing
        one-sided collisions that cannot physically occur.
        """
        comm.seed_channel(11)
        ids = [f"v{i}" for i in range(12)]
        graph = comm.draw_overlap_graph(ids, 0.5)
        for a in ids:
            for b in graph[a]:
                assert a in graph[b], f"{a}->{b} is not mirrored"
        assert any(graph[i] for i in ids), "0.5 overlap probability drew no edges at all"

    def test_isolated_member_receives_no_interference(self):
        comm.seed_channel(3)
        group = [("a", 23.0, 100.0), ("b", 23.0, 100.0), ("c", 23.0, 100.0)]
        probs = comm.judge_uplink(
            group, interferers_of={"a": ["b"], "b": ["a"], "c": []},
            shadowing_sigma_db=0.0,
        )
        alone = comm.judge_uplink(
            [("c", 23.0, 100.0)], shadowing_sigma_db=0.0
        )["c"]
        assert probs["c"] == pytest.approx(alone, rel=1e-12)
        assert probs["a"] < probs["c"]

    def test_one_shadowing_sample_per_link_per_group(self):
        """The docstring's guarantee: shadowing is a property of the path.

        Resolving the whole group in one call must consume exactly one shadowing
        draw per member. The previous per-tagged-vehicle calling pattern consumed
        one per member PER JUDGEMENT, which gave the same link a different
        propagation realisation in each neighbour's view.
        """
        group = [("a", 23.0, 100.0), ("b", 23.0, 150.0), ("c", 20.0, 200.0)]
        comm.seed_channel(5)
        comm.judge_uplink(group)
        after_group_call = comm._shadow_rng.random()

        comm.seed_channel(5)
        for _ in group:
            comm.draw_shadowing_db()
        assert comm._shadow_rng.random() == pytest.approx(after_group_call)


class TestRetiredSymbols:
    """Constants whose referent was deleted must not linger (critic-physics L12)."""

    @pytest.mark.parametrize("name", [
        "TX_POWER_LEVELS_DBM",   # stated the retired [20, 30] dBm power range
        "MAX_FRAME_SIZE", "FRAG_LIMIT", "STREAM_THRESHOLD",  # NetSim.py, deleted
        "REFRACTIVE_INDEX_FIBER", "FIBER_PROPAGATION_SPEED",  # fibre backhaul, deleted
    ])
    def test_symbol_is_gone(self, name):
        assert not hasattr(comm, name), (
            f"{name} has no referent left and misstates the current design"
        )

    def test_c_light_is_retained_because_the_path_loss_reference_needs_it(self):
        assert comm.C_LIGHT > 0
