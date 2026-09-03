"""Regression tests for the defects that blocked the 200,000-step training run.

Every test here corresponds to a specific finding and fails against the code as
it stood on 2026-08-31. The SUMO-backed ones are marked and kept short; the rest
run without a simulator.
"""

import math
import os
import random
import time

import numpy as np
import pytest
import torch
import torch.nn as nn

import src.hot_swap_trainer as H
from src.hot_swap_trainer import (
    DEFAULT_REWARD_WEIGHTS,
    AoiV2IEnv,
    CheckpointMismatchError,
    HotSwapTrainer,
    TransitionStreamer,
    env_param_names,
    prepare_scenario,
    split_env_hparams,
)
from src.rl_interface import STATE_DIM, ActionDecoder, RetrospectiveReplayBuffer

SUMO_STEPS = 300
WARMUP = 350
DENSITY = 25.0
SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class IdxPolicy(nn.Module):
    """Minimal policy with a discrete head that reports `action_idx` in `info`."""

    def __init__(self, state_dim=STATE_DIM, num_channels=4, gamma=0.87, **hparams):
        super().__init__()
        self.state_dim = int(state_dim)
        self.num_channels = int(num_channels)
        self.gamma = float(gamma)
        self.hparams = hparams
        self.decoder = ActionDecoder(num_channels=num_channels)
        self.net = nn.Linear(self.state_dim, 3)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=1e-3)
        self.calls = 0

    def select_action(self, state, deterministic=False):
        self.calls += 1
        idx = self.calls % 8
        delta = self.decoder.delta_from_unit(idx / 8.0)
        grant = (delta, idx % self.num_channels, 15.0)
        raw = np.zeros(3, dtype=np.float32)
        return grant, raw, {"action_idx": idx}

    def update(self, batch):
        loss = self.net(batch["state"]).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return {"loss": float(loss.item())}


@pytest.fixture(scope="module")
def sumo_episode():
    """One real SUMO episode under a random policy. Shared by several tests."""
    prepare_scenario(DENSITY, SUMO_STEPS, WARMUP, SEED, force_regenerate=True)
    env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=SUMO_STEPS, warmup_steps=WARMUP)
    obs, _ = env.reset()
    rng = random.Random(0)

    def grant():
        return (env.decoder.delta_from_unit(rng.random()), rng.randrange(4),
                10.0 + 13.0 * rng.random())

    action = {v: grant() for v in obs}
    closed, deltas = [], []
    for _ in range(SUMO_STEPS):
        obs, _r, _t, _tr, info = env.step(action)
        closed.extend(info["completed"])
        deltas.extend(r["delta_actual"] for r in info["completed"])
        action = {v: grant() for v in info["needs_decision"] if v in obs}
    open_at_end = len(env.interval_start_t)
    finalized = env.finalize_open_intervals()
    metrics = env.get_metrics()
    still_open = len(env.interval_start_t)
    env.close()
    return {
        "closed": closed, "deltas": deltas, "open_at_end": open_at_end,
        "finalized": finalized, "still_open": still_open, "metrics": metrics,
        "step_length": 0.1,
    }


# ---------------------------------------------------------------------------
# C1 -- open SMDP intervals at episode end
# ---------------------------------------------------------------------------
class TestOpenIntervalsAreClosed:
    @pytest.mark.slow
    def test_no_interval_remains_open_after_finalisation(self, sumo_episode):
        """The count that matters: ZERO intervals unaccounted for at episode end.

        Measured before the fix: 534 intervals closed and 75 still open on a
        600-step episode -- 12.3 % of every decision the policy made, dropped
        before it ever reached the replay buffer.
        """
        assert sumo_episode["still_open"] == 0

    @pytest.mark.slow
    def test_the_leak_was_real_and_is_now_recovered(self, sumo_episode):
        """`finalize_open_intervals` must actually recover transitions.

        If this ever returns zero the test above becomes vacuous, so the size of
        the recovered set is asserted too.
        """
        assert sumo_episode["open_at_end"] > 0
        assert len(sumo_episode["finalized"]) == sumo_episode["open_at_end"]

    @pytest.mark.slow
    def test_recovered_intervals_are_truncation_not_termination(self, sumo_episode):
        """The window ended, the vehicle did not: bootstrapping must continue."""
        for rec in sumo_episode["finalized"]:
            assert rec["done"] is False
            assert rec["transmitted"] is False
            # No radio was used, so only the accrued error is charged.
            assert rec["r_power"] == 0.0 and rec["cbr"] == 0.0 and rec["i_redundant"] == 0.0

    @pytest.mark.slow
    def test_recovered_intervals_are_the_long_ones(self, sumo_episode):
        """Length-biased loss is why C1 was a correctness bug, not an efficiency one.

        Intervals still open at the cut-off are longer on average than those that
        closed, so discarding them biased the learning signal for Delta -- the
        paper's only decision variable -- in one direction.
        """
        closed_mean = float(np.mean([r["delta_actual"] for r in sumo_episode["closed"]]))
        open_mean = float(np.mean([r["delta_actual"] for r in sumo_episode["finalized"]]))
        assert open_mean > closed_mean

    def test_close_warns_rather_than_discarding_silently(self, caplog):
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1)
        env.interval_start_t["ghost"] = 0.0
        env.interval_accum["ghost"] = 0.0
        with caplog.at_level("WARNING"):
            env.close()
        assert any("still" in r.message or "open" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# critic-physics L1 / core M1 -- the one-step bookkeeping offset
# ---------------------------------------------------------------------------
class TestLedgerTimeAlignment:
    @pytest.mark.slow
    def test_full_rate_updates_leave_only_second_order_error(self):
        """Delta = 0.1 s on every vehicle must leave ~centimetre error, not ~metre.

        The regression criterion from the physics review. Before the fix this
        configuration measured `mean_error` 0.8153 m against a mean speed of
        8.099 m/s -- and 8.099 * 0.1 s = 0.810 m, i.e. 99 % of the paper's
        headline accuracy metric was the RSU ledger pairing a pre-step position
        with a post-step timestamp. What should remain is the second-order
        acceleration term, of order 0.5 * a * dt^2 ~ 0.01 m.
        """
        prepare_scenario(DENSITY, SUMO_STEPS, WARMUP, SEED, force_regenerate=True)
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=SUMO_STEPS, warmup_steps=WARMUP)
        obs, _ = env.reset()
        grant = (0.1, 0, 23.0)
        action = {v: grant for v in obs}
        speeds = []
        for _ in range(SUMO_STEPS):
            obs, _r, _t, _tr, info = env.step(action)
            speeds.extend(env.last_speeds[v] for v in obs if v in env.last_speeds)
            action = {v: grant for v in info["needs_decision"] if v in obs}
        env.finalize_open_intervals()
        metrics = env.get_metrics()
        env.close()

        mean_speed = float(np.mean(speeds))
        one_step_floor = mean_speed * 0.1
        assert metrics["n_observations"] > 1000
        # Two bounds. The absolute one keeps the claim concrete; the relative one
        # is the load-bearing check, because how much error is LEFT is a property
        # of this traffic realisation (acceleration, emergency braking) while what
        # was REMOVED is exactly one step of travel.
        assert metrics["mean_error"] < 0.1, (
            f"mean_error {metrics['mean_error']} m; the one-step-stale floor for "
            f"this traffic would be {one_step_floor:.3f} m"
        )
        assert metrics["mean_error"] < 0.1 * one_step_floor

    @pytest.mark.slow
    def test_delta_actual_is_not_inflated_by_a_step(self, sumo_episode):
        """A grant fires before the SUMO step, so the interval closes there.

        Measured before the fix: the smallest `delta_actual` in an episode was
        0.300 s for a requested 0.101 s, because the close time was read after
        `simulationStep()`. `delta_actual` is the exponent of the SMDP discount
        and the denominator of the episode score, so on short intervals the error
        reached 200 %.
        """
        dt = sumo_episode["step_length"]
        smallest = min(sumo_episode["deltas"])
        # ceil quantisation onto the 0.1 s SUMO grid is structural and remains;
        # the extra step is not.
        assert smallest <= 2 * dt + 1e-9, f"smallest delta_actual {smallest}"

    @pytest.mark.slow
    def test_every_interval_lies_on_the_step_grid(self, sumo_episode):
        dt = sumo_episode["step_length"]
        for d in sumo_episode["deltas"]:
            assert abs(d / dt - round(d / dt)) < 1e-6, d


# ---------------------------------------------------------------------------
# H2 / critic-physics L8 -- privileged information in the observation
# ---------------------------------------------------------------------------
class TestNoGroundTruthInObservation:
    def test_n_active_counts_the_rsu_ledger_not_the_simulator(self):
        """Feature [13] must be producible by a roadside unit.

        It used to walk `libsumo.vehicle.getIDList()` and call `getPosition()` on
        every vehicle in the network, counting those inside the disc -- including
        vehicles that had never transmitted and that the RSU had no way of knowing
        existed. That flatly contradicted the feature beside it, whose docstring
        says asking SUMO directly "is information no real roadside unit has".
        """
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1)
        env.is_running = True
        env.sim_time = 5.0
        env.vehicle_tracks = {f"v{i}": {} for i in range(7)}
        assert env._count_active_vehicles() == 7

        env.sim_time = 6.0
        env.vehicle_tracks["v7"] = {}
        assert env._count_active_vehicles() == 8

    def test_n_active_needs_no_simulator_call(self, monkeypatch):
        """The strong form: it must not touch libsumo at all."""
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1)
        env.is_running = True
        env.sim_time = 1.0
        env.vehicle_tracks = {"a": {}, "b": {}}

        def explode(*_a, **_k):  # pragma: no cover - must never run
            raise AssertionError("n_active queried SUMO ground truth")

        monkeypatch.setattr(H, "libsumo", type("Fake", (), {
            "vehicle": type("V", (), {"getIDList": staticmethod(explode),
                                      "getPosition": staticmethod(explode)})
        }))
        assert env._count_active_vehicles() == 2

    def test_vectorize_does_not_prefer_the_sumo_queue_count(self):
        """`vectorize()` used to read the TLS dict's SUMO-measured `n_queue` first.

        `vectorize_from_dict` reads the state dict first, where the environment
        puts its ledger reconstruction, so the production path was safe and the
        node-object path was a dormant leak with the opposite priority.
        """
        from src.rl_interface import StateVectorizer

        class Veh:
            pos = (100.0, 0.0)
            vel = (10.0, 0.0)
            speed = 10.0
            accel = 0.0
            last_pred_err = 0.0

        class Rsu:
            pos = (0.0, 0.0)

        vec = StateVectorizer(rsu_range=300.0, queue_max=20.0).vectorize(
            Veh(), Rsu(), current_time=1.0,
            tls_info={"state": "r", "n_queue": 19.0},   # SUMO ground truth
        )
        assert vec[15] == 0.0, "the TLS dict's SUMO queue count reached the vector"


# ---------------------------------------------------------------------------
# H3 -- action_idx must survive the trip to the replay buffer
# ---------------------------------------------------------------------------
class TestDiscreteActionIndexSurvives:
    def test_streamer_carries_action_idx_into_the_buffer(self):
        streamer = TransitionStreamer(maxsize=64)
        buf = RetrospectiveReplayBuffer(capacity=64, gamma=0.9)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        for i in range(8):
            streamer.push(s, np.zeros(3, dtype=np.float32), -0.1, s, False, 1.0,
                          action_idx=i)
        assert streamer.push_to_buffer(buf) == 8
        batch = buf.sample(8)
        assert "action_idx" in batch
        assert sorted(batch["action_idx"].tolist()) == list(range(8))

    def test_index_reaches_the_batch_through_the_scheduler(self):
        """End to end: model info -> decide_grant -> push_transition -> batch."""
        trainer = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM,
                                 num_channels=4, buffer_capacity=64, batch_size=8)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        for _ in range(8):
            _grant, raw, idx = trainer.scheduler.decide_grant("v", s)
            assert idx is not None, "decide_grant dropped the discrete action index"
            trainer.scheduler.push_transition(
                state=s, raw_action=raw, reward=-0.1, next_state=s,
                done=False, delta_t=1.0, action_idx=idx,
            )
        trainer.streamer.push_to_buffer(trainer.replay_buffer)
        assert "action_idx" in trainer.replay_buffer.sample(8)

    def test_continuous_only_policies_are_unaffected(self):
        """No index means no key -- batch shapes stay exactly as they were."""
        buf = RetrospectiveReplayBuffer(capacity=8)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        for _ in range(4):
            buf.push(s, np.zeros(3, dtype=np.float32), -0.1, s, False, 1.0)
        assert "action_idx" not in buf.sample(4)


# ---------------------------------------------------------------------------
# gamma -- one source for the SMDP discount
# ---------------------------------------------------------------------------
class TestGammaIsWired:
    def test_buffer_takes_its_gamma_from_the_model(self):
        """The buffer used to keep its 0.99 default forever.

        Every baseline reads the SMDP discount from the batch (or recomputes it
        from `delta_t` with its own gamma), so a buffer built without a gamma made
        the per-model `gamma` Optuna searched, recorded and reported completely
        inert in all nine models.
        """
        trainer = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM,
                                 num_channels=4, hparams={"gamma": 0.87})
        assert trainer.rest_model.gamma == pytest.approx(0.87)
        assert trainer.replay_buffer.gamma == pytest.approx(0.87)
        assert trainer.gamma == pytest.approx(0.87)

    def test_shipped_discount_matches_the_models_own_recomputation(self):
        """The buffer's `discount` column and `gamma**delta_t` must agree."""
        trainer = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM,
                                 num_channels=4, hparams={"gamma": 0.87})
        s = np.zeros(STATE_DIM, dtype=np.float32)
        for d in (0.1, 1.0, 4.0, 45.0):
            trainer.replay_buffer.push(s, np.zeros(3, dtype=np.float32), -1.0, s, False, d)
        batch = trainer.replay_buffer.sample(4)
        expected = torch.pow(torch.tensor(trainer.rest_model.gamma), batch["delta_t"])
        assert torch.allclose(batch["discount"], expected, atol=1e-6)


# ---------------------------------------------------------------------------
# H1 -- anti-mocking assertion 4 must not be an identity
# ---------------------------------------------------------------------------
class TestRewardWeightsAreAudited:
    def test_a_corrupted_positive_weight_is_refused_at_construction(self):
        """0.5 -> 5.0 kept the sign and passed BOTH clauses of the old assertion."""
        with pytest.raises(ValueError, match="BENCHMARK"):
            AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1, w1=5.0)

    def test_a_sign_flip_is_refused_too(self):
        with pytest.raises(ValueError):
            AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1, w1=-5.0)

    def test_the_approved_weights_are_accepted(self):
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1,
                        **DEFAULT_REWARD_WEIGHTS)
        assert env._w_audit == (env.w1, env.w2, env.w3, env.w4)

    def test_a_deliberate_reward_search_must_say_so(self):
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1,
                        w1=0.9, allow_custom_reward_weights=True)
        assert env.w1 == pytest.approx(0.9)

    def test_records_carry_the_terms_the_assertion_re_derives_from(self):
        """r_power / i_redundant / interval_steps must be independently checkable."""
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1)
        env.sim_time = 2.0
        env.interval_start_t["v"] = 1.0
        env.interval_accum["v"] = 0.25
        env.subchannel_cbr = [0.01, 0.0, 0.0, 0.0]
        rec = env._finalize_interval(
            "v", transmitted=True, power_dbm=env.decoder.p_max, channel=0,
            err_at_update_m=0.0, done=False,
        )
        assert rec["r_power"] == pytest.approx(1.0)
        assert rec["i_redundant"] == 1.0           # error 0 m is below the 3.2 m threshold
        assert rec["interval_steps"] == 10         # 1.0 s at a 0.1 s step
        assert rec["r_err"] <= rec["interval_steps"] * env.step_length + 1e-9


# ---------------------------------------------------------------------------
# M6 -- hyper-parameter routing
# ---------------------------------------------------------------------------
class TestHparamRouting:
    def test_environment_arguments_are_routed_by_signature(self):
        """The blacklist only knew about w1..w4; `density` leaked past it."""
        model_hp, env_hp = split_env_hparams(
            {"lr": 1e-3, "density": 55.0, "warmup_steps": 9, "w1": 0.4, "w1_raw": 3.0}
        )
        assert env_hp == {"density": 55.0, "warmup_steps": 9, "w1": 0.4, "w1_raw": 3.0}
        assert model_hp == {"lr": 1e-3}

    def test_every_env_constructor_argument_is_covered(self):
        names = env_param_names()
        for expected in ("density", "seed", "max_steps", "num_channels",
                         "rsu_range", "warmup_steps", "w1", "w2", "w3", "w4"):
            assert expected in names

    def test_a_key_no_constructor_names_is_an_error_not_a_warning(self):
        """`total_nonsense=1` used to be accepted in silence by all nine models."""
        with pytest.raises(ValueError, match="total_nonsense"):
            HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM, num_channels=4,
                           hparams={"total_nonsense": 1})

    def test_a_typo_of_a_real_key_is_an_error(self):
        with pytest.raises(ValueError, match="learnign_rate"):
            HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM, num_channels=4,
                           hparams={"learnign_rate": 1e-3})


# ---------------------------------------------------------------------------
# M3 -- resuming across a configuration change
# ---------------------------------------------------------------------------
class TestCheckpointCompatibility:
    def _trainer(self, **hp):
        # Pinned to CPU: this class exercises checkpoint bookkeeping, and the
        # default multi-GPU placement would put the Rest model on cuda:1 while the
        # probe tensors below stay on the host.
        return HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM,
                              num_channels=4, hparams=hp,
                              act_device="cpu", rest_device="cpu")

    def test_a_changed_hyperparameter_refuses_the_resume(self, tmp_path):
        path = str(tmp_path / "ckpt.pt")
        self._trainer(gamma=0.99).save_checkpoint(path, best_reward=-1.0)
        with pytest.raises(CheckpointMismatchError, match="hparams"):
            self._trainer(gamma=0.5).load_checkpoint(path)

    def test_a_matching_configuration_loads(self, tmp_path):
        path = str(tmp_path / "ckpt.pt")
        self._trainer(gamma=0.99).save_checkpoint(path, best_reward=-1.0)
        ckpt = self._trainer(gamma=0.99).load_checkpoint(path)
        assert ckpt["best_reward"] == pytest.approx(-1.0)

    def test_optimizer_moments_are_saved_and_restored(self, tmp_path):
        path = str(tmp_path / "ckpt.pt")
        a = self._trainer(gamma=0.99)
        # Take one real optimiser step so Adam has non-empty state.
        a.rest_model.update({"state": torch.zeros(4, STATE_DIM)})
        a.save_checkpoint(path)
        b = self._trainer(gamma=0.99)
        assert not b.rest_model.optimizer.state_dict()["state"]
        ckpt = b.load_checkpoint(path)
        assert "optimizer" in ckpt["_restored_optimizers"]
        assert b.rest_model.optimizer.state_dict()["state"]

    def test_the_reward_weights_are_recorded_with_the_weights(self, tmp_path):
        path = str(tmp_path / "ckpt.pt")
        self._trainer(gamma=0.99).save_checkpoint(path)
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        assert ckpt["reward_weights"] == dict(DEFAULT_REWARD_WEIGHTS)
        assert ckpt["gamma"] == pytest.approx(0.99)


# ---------------------------------------------------------------------------
# M7 -- a frozen Act model must stop the run
# ---------------------------------------------------------------------------
class TestFailedSwapsAreSurfaced:
    def test_initial_sync_is_not_counted_as_a_hot_swap(self):
        trainer = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM, num_channels=4)
        assert trainer.hot_swap_manager.swap_count == 0

    def test_refused_swaps_are_counted_and_eventually_fatal(self):
        trainer = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM,
                                 num_channels=4, batch_size=1, swap_interval=1)
        bg = trainer.background_trainer
        bg.max_consecutive_failed_swaps = 3
        # Poison the Rest model exactly as a diverging run would.
        with torch.no_grad():
            for p in trainer.rest_model.parameters():
                p.fill_(float("nan"))
        s = np.zeros(STATE_DIM, dtype=np.float32)
        for _ in range(8):
            trainer.replay_buffer.push(s, np.zeros(3, dtype=np.float32), -0.1, s, False, 1.0)
        for _ in range(3):
            bg.train_step()
        assert bg.consecutive_failed_swaps >= 3
        assert bg.fatal_error is not None
        assert bg.get_metrics()["hot_swap_stats"]["failed_swaps"] >= 3


# ---------------------------------------------------------------------------
# Coverage outage, as defined by the user on 2026-08-31
# ---------------------------------------------------------------------------
class TestCoverageOutage:
    @pytest.mark.slow
    def test_outage_is_the_uncovered_fraction_of_vehicle_steps(self, sumo_episode):
        """Outage = time spent outside EVERY RSU disc, where no AoI update happens.

        The scenario geometry fixes the expectation: EDGE_LENGTH is
        2 * RSU_RANGE + OUTAGE_ZONE = 900 m with OUTAGE_ZONE = 300 m, so one third
        of every edge is uncovered.
        """
        m = sumo_episode["metrics"]
        assert m["total_vehicle_steps"] > 0
        assert 0.2 < m["coverage_outage_rate"] < 0.6
        assert m["coverage_outage_rate"] == pytest.approx(
            m["outage_vehicle_steps"] / m["total_vehicle_steps"], abs=1e-6
        )

    @pytest.mark.slow
    def test_outage_is_not_the_frame_error_rate(self, sumo_episode):
        """The two used to be conflated; they are different quantities.

        `hpo.py` aliased `outage_rate = packet_loss_rate`, which is why the two
        columns were always identical. The environment now publishes the coverage
        definition under its own name and never the alias.
        """
        m = sumo_episode["metrics"]
        assert "packet_loss_rate" in m and "coverage_outage_rate" in m
        assert "outage_rate" not in m, (
            "the ambiguous legacy key is back; downstream would silently pick up "
            "the frame error rate again"
        )
        assert m["coverage_outage_rate"] != m["packet_loss_rate"]

    @pytest.mark.slow
    def test_the_three_transmission_counters_stay_distinct(self, sumo_episode):
        """The evaluation tables need all three, separately."""
        m = sumo_episode["metrics"]
        for key in ("tx_attempts", "tx_fails", "tx_abandoned"):
            assert key in m
        assert m["tx_attempts"] >= m["tx_fails"] >= m["tx_abandoned"]


# ---------------------------------------------------------------------------
# The test suite must not write into the production tree
# ---------------------------------------------------------------------------
class TestNoProductionTreePollution:
    """Compare CONTENT HASHES, not file listings.

    A listing comparison misses the case an overwrite creates -- same name, new
    content -- which is exactly how `logs/training/PPO_progress.csv` was being
    rewritten by the suite without anyone noticing.
    """

    @staticmethod
    def _fingerprint(root):
        import hashlib
        out = {}
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(dirpath, f)
                try:
                    with open(p, "rb") as fh:
                        out[p] = (os.path.getmtime(p), hashlib.sha256(fh.read()).hexdigest())
                except OSError:
                    continue
        return out

    @pytest.mark.slow
    def test_a_training_run_writes_nothing_outside_its_output_dirs(self, tmp_path):
        from src.hot_swap_trainer import run_hot_swap_training

        base = os.path.dirname(os.path.dirname(os.path.abspath(H.__file__)))
        watched = [os.path.join(base, d) for d in ("logs/training", "checkpoints", "results")]
        watched = [d for d in watched if os.path.isdir(d)]
        before = {d: self._fingerprint(d) for d in watched}

        run_hot_swap_training(
            model_name="PollutionProbe",
            model_cls=IdxPolicy,
            total_steps=40,
            episodes=1,
            batch_size=8,
            swap_interval=5,
            seed=SEED,
            warmup_steps=WARMUP,
            checkpoint_dir=str(tmp_path / "ckpt"),
            tensorboard_dir=str(tmp_path / "tb"),
            log_dir=str(tmp_path / "logs"),
        )

        after = {d: self._fingerprint(d) for d in watched}
        for d in watched:
            assert after[d] == before[d], f"the training run modified files under {d}"
        assert (tmp_path / "logs").exists()


# ---------------------------------------------------------------------------
# critic-physics L4 -- the same seed must give the same run
# ---------------------------------------------------------------------------
class TestReproducibility:
    def test_network_generation_does_not_consume_the_global_random_stream(self):
        """Generation used to draw 200 `random.uniform` from the GLOBAL stream.

        Whether those draws happened depended on whether the cached SUMO files
        were reusable, so the stream position at the start of an episode -- and
        therefore every Bernoulli uplink-success draw that followed -- was a
        function of what happened to be on disk. Episode 1 (signature miss,
        regenerate) and episode 2 (cache hit) of the SAME seed got different
        channel realisations.
        """
        import src.sumo.make_sumo_set as ss

        random.seed(7)
        ss.make_sumo_files(force_regenerate=True)
        after_regenerate = random.random()

        random.seed(7)
        ss.make_sumo_files(force_regenerate=False)
        after_cache_hit = random.random()

        assert after_regenerate == after_cache_hit

    def test_the_environment_owns_its_bernoulli_stream(self):
        env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=10, warmup_steps=1)
        assert isinstance(env._rng, random.Random)
        first = [env._rng.random() for _ in range(5)]
        env._rng.seed(env.seed)
        assert [env._rng.random() for _ in range(5)] == first

    @pytest.mark.slow
    def test_same_seed_gives_the_same_episode_either_side_of_the_cache(self):
        def run(force):
            prepare_scenario(DENSITY, 120, WARMUP, SEED, force_regenerate=force)
            env = AoiV2IEnv(density=DENSITY, seed=SEED, max_steps=120, warmup_steps=WARMUP)
            obs, _ = env.reset()
            rng = random.Random(0)

            def grant():
                return (env.decoder.delta_from_unit(rng.random()), rng.randrange(4),
                        10.0 + 13.0 * rng.random())

            action = {v: grant() for v in obs}
            for _ in range(120):
                obs, _r, _t, _tr, info = env.step(action)
                action = {v: grant() for v in info["needs_decision"] if v in obs}
            env.finalize_open_intervals()
            metrics = env.get_metrics()
            env.close()
            return metrics

        regenerated = run(True)    # signature miss
        cached = run(False)        # signature hit, nothing regenerated
        for key in ("mean_error", "mean_aoi", "packet_loss_rate", "tx_attempts",
                    "tx_fails", "coverage_outage_rate"):
            assert regenerated[key] == cached[key], (
                f"{key} depends on whether the SUMO file cache was warm"
            )


# ---------------------------------------------------------------------------
# Stale checkpoints must degrade to a fresh start, not to a dead run
# ---------------------------------------------------------------------------
class TestStaleCheckpointsDegradeGracefully:
    def test_a_weight_shape_mismatch_raises_the_handled_error(self, tmp_path):
        """A torch RuntimeError here escaped the resume guard and killed the run.

        Verified against backup/checkpoints_presmoke_20260828_155837/: all six
        stored checkpoints fail against today's class definitions, three of them
        with `Missing key(s) in state_dict: "total_updates"` / `"epsilon"` /
        `"per_beta"` -- buffers the baselines have grown since. `run_all.py`
        resumes by default, so this is the ordinary path after any model change.
        """
        path = str(tmp_path / "ckpt.pt")
        a = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM, num_channels=4,
                           act_device="cpu", rest_device="cpu")
        a.save_checkpoint(path)

        blob = torch.load(path, map_location="cpu", weights_only=False)
        # A buffer the current class does not have -- the `total_updates` case.
        blob["rest_state_dict"]["a_buffer_this_class_no_longer_has"] = torch.zeros(3)
        torch.save(blob, path)

        b = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM, num_channels=4,
                           act_device="cpu", rest_device="cpu")
        with pytest.raises(CheckpointMismatchError, match="do not fit"):
            b.load_checkpoint(path)

    def test_the_resume_path_survives_an_unloadable_checkpoint(self, tmp_path, caplog):
        """The run must start over, loudly -- not die."""
        from src.hot_swap_trainer import run_hot_swap_training

        ckpt_dir = tmp_path / "ckpt"
        ckpt_dir.mkdir()
        a = HotSwapTrainer(model_cls=IdxPolicy, state_dim=STATE_DIM, num_channels=4,
                           act_device="cpu", rest_device="cpu")
        a.save_checkpoint(str(ckpt_dir / "StaleProbe_ep001.pt"))
        blob = torch.load(ckpt_dir / "StaleProbe_ep001.pt", map_location="cpu",
                          weights_only=False)
        blob["rest_state_dict"]["a_buffer_this_class_no_longer_has"] = torch.zeros(3)
        torch.save(blob, ckpt_dir / "StaleProbe_ep001.pt")

        with caplog.at_level("ERROR"):
            summary = run_hot_swap_training(
                model_name="StaleProbe", model_cls=IdxPolicy,
                total_steps=40, episodes=1, batch_size=8, swap_interval=5,
                seed=SEED, warmup_steps=WARMUP, resume=True,
                checkpoint_dir=str(ckpt_dir), tensorboard_dir=str(tmp_path / "tb"),
                log_dir=str(tmp_path / "logs"),
            )
        assert summary["resumed_from_checkpoint"] is None
        assert summary["start_episode"] == 0
        assert any("from scratch" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Gradient budget must be observable after the fact
# ---------------------------------------------------------------------------
class TestGradientBudgetIsRecorded:
    @pytest.mark.slow
    def test_the_summary_says_how_many_updates_each_density_received(self, tmp_path):
        """Without this the cross-model fairness claim cannot be checked at all.

        Measured over 300 steps: 2 gradient updates at density 5 against 36 at
        density 50, an 18x spread driven purely by how fast the replay buffer
        fills. That number was not recorded anywhere.
        """
        import pandas as pd
        from src.hot_swap_trainer import run_hot_swap_training

        summary = run_hot_swap_training(
            model_name="BudgetProbe", model_cls=IdxPolicy,
            total_steps=80, episodes=2, density=[5.0, 50.0],
            batch_size=8, swap_interval=5, seed=SEED, warmup_steps=WARMUP,
            checkpoint_dir=str(tmp_path / "ckpt"),
            tensorboard_dir=str(tmp_path / "tb"), log_dir=str(tmp_path / "logs"),
        )
        assert set(summary["grad_updates_by_density"]) == {5.0, 50.0}
        assert "zero_update_episodes" in summary

        df = pd.read_csv(summary["log_csv_path"])
        assert list(df["density"]) == [5.0, 50.0], "the density schedule did not cycle"
        for col in ("grad_updates_this_episode", "grad_updates_total"):
            assert col in df.columns
        # Monotone: the running total never goes backwards.
        assert df["grad_updates_total"].is_monotonic_increasing


# ---------------------------------------------------------------------------
# A checkpoint must never capture a half-swapped model
# ---------------------------------------------------------------------------
class UniformPolicy(nn.Module):
    """Several parameter tensors that are always all set to the same scalar.

    That invariant is the detector: a consistent snapshot has every tensor equal
    to one value, while a snapshot taken during a parameter-by-parameter copy has
    a mix of the outgoing and incoming values.
    """

    def __init__(self, state_dim=STATE_DIM, num_channels=4, gamma=0.99, **hparams):
        super().__init__()
        self.state_dim = int(state_dim)
        self.num_channels = int(num_channels)
        self.gamma = float(gamma)
        self.hparams = hparams
        self.decoder = ActionDecoder(num_channels=num_channels)
        # Many separate tensors widen the window a torn read can land in.
        self.layers = nn.ModuleList([nn.Linear(32, 32, bias=False) for _ in range(24)])
        self.optimizer = torch.optim.SGD(self.parameters(), lr=0.0)
        self._tick = 0.0

    def fill(self, value: float) -> None:
        with torch.no_grad():
            for p in self.parameters():
                p.fill_(value)

    def select_action(self, state, deterministic=False):
        return (1.0, 0, 15.0), np.zeros(3, dtype=np.float32), {}

    def update(self, batch):
        # Mutates every parameter, like a real gradient step, so the atomicity
        # probe below sees the same window a real update opens.
        self._tick += 1.0
        self.fill(self._tick)
        return {"loss": 0.0}


class TestCheckpointSnapshotIsAtomic:
    def test_saving_during_a_hot_swap_never_captures_a_torn_model(self, tmp_path):
        """`_best.pt` is the artefact the paper's numbers come from.

        `save_checkpoint` used to read `act_model.state_dict()` with neither
        `swap_lock` nor the trainer's update lock held, while the background
        thread copied Rest into Act one parameter at a time. A checkpoint written
        mid-swap therefore stored a policy that never existed and never earned the
        `best_reward` recorded beside it -- and `evaluate.py` prefers
        `act_state_dict` exactly because Act is supposed to be the validated copy
        that produced the reported reward.
        """
        trainer = HotSwapTrainer(model_cls=UniformPolicy, state_dim=STATE_DIM,
                                 num_channels=4, batch_size=1, swap_interval=1,
                                 act_device="cpu", rest_device="cpu")
        trainer.act_model.fill(0.0)
        trainer.rest_model.fill(0.0)

        # Drive the REAL production path: the background worker runs
        # `train_step`, which updates the Rest weights and then hot-swaps them
        # into Act, exactly as it does during a 200k-step run.
        s_vec = np.zeros(STATE_DIM, dtype=np.float32)
        for _ in range(8):
            trainer.replay_buffer.push(s_vec, np.zeros(3, dtype=np.float32),
                                       -0.1, s_vec, False, 1.0)
        swap_errors = []
        trainer.start()
        try:
            torn = []
            for i in range(40):
                path = str(tmp_path / f"c{i}.pt")
                trainer.save_checkpoint(path)
                blob = torch.load(path, map_location="cpu", weights_only=False)
                for which in ("act_state_dict", "rest_state_dict"):
                    values = {float(t.flatten()[0]) for t in blob[which].values()}
                    if len(values) != 1:
                        torn.append((i, which, sorted(values)))
        finally:
            trainer.stop()

        assert trainer.background_trainer.training_steps > 0, (
            "the background trainer never ran, so nothing was raced against"
        )
        assert not swap_errors, swap_errors
        assert not torn, f"checkpoint captured a half-swapped model: {torn[:3]}"

    def test_the_detector_would_actually_fire(self, tmp_path):
        """Guard against the test above passing because the probe is blind."""
        trainer = HotSwapTrainer(model_cls=UniformPolicy, state_dim=STATE_DIM,
                                 num_channels=4, act_device="cpu", rest_device="cpu")
        trainer.act_model.fill(1.0)
        # Hand-build the torn state the locking prevents.
        params = list(trainer.act_model.parameters())
        with torch.no_grad():
            params[0].fill_(2.0)
        values = {float(t.flatten()[0]) for t in trainer.act_model.state_dict().values()}
        assert len(values) == 2, "the probe cannot distinguish a mixed snapshot"

    def test_the_snapshot_does_not_alias_the_live_tensors(self, tmp_path):
        """A saved checkpoint must not keep changing after it is written."""
        trainer = HotSwapTrainer(model_cls=UniformPolicy, state_dim=STATE_DIM,
                                 num_channels=4, act_device="cpu", rest_device="cpu")
        trainer.act_model.fill(3.0)
        trainer.rest_model.fill(3.0)
        path = str(tmp_path / "c.pt")
        trainer.save_checkpoint(path)
        trainer.act_model.fill(9.0)
        blob = torch.load(path, map_location="cpu", weights_only=False)
        for tensor in blob["act_state_dict"].values():
            assert float(tensor.flatten()[0]) == 3.0


# ---------------------------------------------------------------------------
# The NaN guard must be sound, not merely present
# ---------------------------------------------------------------------------
class PoisonPolicy(nn.Module):
    """Rest model whose weights can be driven clean -> NaN -> clean on demand."""

    def __init__(self, state_dim=STATE_DIM, num_channels=4, gamma=0.99, **hparams):
        super().__init__()
        self.state_dim = int(state_dim)
        self.num_channels = int(num_channels)
        self.gamma = float(gamma)
        self.hparams = hparams
        self.decoder = ActionDecoder(num_channels=num_channels)
        self.layers = nn.ModuleList([nn.Linear(16, 16, bias=False) for _ in range(12)])
        self.optimizer = torch.optim.SGD(self.parameters(), lr=0.0)

    def fill(self, value: float) -> None:
        with torch.no_grad():
            for p in self.parameters():
                p.fill_(value)

    def select_action(self, state, deterministic=False):
        return (1.0, 0, 15.0), np.zeros(3, dtype=np.float32), {}

    def update(self, batch):
        return {"loss": 0.0}


class TestNaNGuardIsSound:
    """The check and the copy must be ONE critical section.

    `hot_swap()` used to run `validate_weights()` with no lock held and only then
    take `swap_lock` to copy. A gradient step landing in that window wrote its
    NaNs into Rest AFTER the guard had already said "clean", and the copy carried
    them into the serving model -- past the check that exists to stop exactly
    that. `failed_swaps` stays 0, so M7's abort never fires either, and the run
    continues on a poisoned Act model while its metrics still look plausible.

    Timing alone does not demonstrate this: with the GIL and a short update
    window the interleaving is essentially never sampled, and a test that merely
    races threads passes whether or not the bug is present (verified). The
    interleaving is therefore FORCED with events, so the test fails
    deterministically when the locking is removed.
    """

    def test_a_swap_cannot_copy_weights_poisoned_after_the_check(self):
        import threading

        trainer = HotSwapTrainer(model_cls=PoisonPolicy, state_dim=STATE_DIM,
                                 num_channels=4, act_device="cpu", rest_device="cpu")
        manager = trainer.hot_swap_manager
        trainer.act_model.fill(1.0)
        trainer.rest_model.fill(1.0)

        validated = threading.Event()
        poisoned = threading.Event()

        real_validate = manager.validate_weights

        def spy_validate():
            result = real_validate()
            validated.set()          # the guard has now made its decision
            poisoned.wait(1.0)       # let the writer poison Rest before we copy
            return result

        manager.validate_weights = spy_validate

        def writer():
            # Exactly what BackgroundTrainer.train_step does: mutate the Rest
            # weights while holding `update_lock`.
            with manager.update_lock:
                trainer.rest_model.fill(1.0)
                validated.wait(1.0)          # let the guard see a clean model
                trainer.rest_model.fill(float("nan"))
                poisoned.set()
                time.sleep(0.05)             # hold the poisoned state
                trainer.rest_model.fill(1.0)

        t_writer = threading.Thread(target=writer, daemon=True)
        t_writer.start()
        swapped = manager.hot_swap()
        t_writer.join(timeout=5)

        act_has_nan = any(torch.isnan(p).any().item()
                          for p in trainer.act_model.parameters())
        assert not act_has_nan, (
            "the NaN guard passed on a clean model and the copy then carried "
            "weights that were poisoned after the check"
        )
        # Either the swap was serialised behind the writer and succeeded on clean
        # weights, or it saw the NaN and refused. Both are sound; carrying NaN is not.
        assert swapped or manager.failed_swaps > 0

    def test_the_probe_would_detect_nan_in_the_act_model(self):
        """Guard against the assertion above being unable to see the failure."""
        trainer = HotSwapTrainer(model_cls=PoisonPolicy, state_dim=STATE_DIM,
                                 num_channels=4, act_device="cpu", rest_device="cpu")
        trainer.act_model.fill(float("nan"))
        assert any(torch.isnan(p).any().item()
                   for p in trainer.act_model.parameters())

    def test_a_genuinely_diverged_model_is_still_refused(self):
        """The guard must keep doing its ordinary job."""
        trainer = HotSwapTrainer(model_cls=PoisonPolicy, state_dim=STATE_DIM,
                                 num_channels=4, act_device="cpu", rest_device="cpu")
        trainer.act_model.fill(1.0)
        trainer.rest_model.fill(float("nan"))
        before = trainer.hot_swap_manager.failed_swaps
        assert trainer.hot_swap_manager.hot_swap() is False
        assert trainer.hot_swap_manager.failed_swaps == before + 1
        assert not any(torch.isnan(p).any().item()
                       for p in trainer.act_model.parameters())


# ---------------------------------------------------------------------------
# C2 -- which number chooses {model}_best.pt
# ---------------------------------------------------------------------------
class TestCheckpointSelectionUsesTheRewardRate:
    """The selection metric is the whole point of C2, and it was untested.

    `mean(ep_rewards)` is the average penalty PER CLOSED INTERVAL and is not
    normalised by how long the interval lasted, so a policy that spams short
    updates always scores better. Measured on one episode: Delta in [0.1, 0.5)
    averaged -0.194 per decision against -3.159 for Delta in [10, 45) -- a 16x
    gap -- but per simulated second those are -0.734/s and -0.165/s and the
    ranking REVERSES. Since this number picks `{model}_best.pt`, the old metric
    pointed the paper's headline artefact at the opposite of its own thesis.

    Asserting on the stored `best_reward` is what makes this discriminating: the
    two candidate metrics are numerically far apart, so a revert to the
    per-decision mean changes the value written into the file.
    """

    @pytest.mark.slow
    def test_best_checkpoint_stores_the_per_second_rate(self, tmp_path):
        import pandas as pd
        from src.hot_swap_trainer import run_hot_swap_training

        ckpt_dir = tmp_path / "ckpt"
        summary = run_hot_swap_training(
            model_name="SelectProbe", model_cls=IdxPolicy,
            total_steps=120, episodes=2, density=[25.0, 50.0],
            batch_size=8, swap_interval=5, seed=SEED, warmup_steps=WARMUP,
            checkpoint_dir=str(ckpt_dir), tensorboard_dir=str(tmp_path / "tb"),
            log_dir=str(tmp_path / "logs"),
        )
        df = pd.read_csv(summary["log_csv_path"])
        assert len(df) == 2

        per_sec = df["reward_per_sec_selected"]
        per_decision = df["reward_per_decision"]
        # The control: the two metrics must actually disagree here, or this test
        # could not tell them apart no matter what selection did.
        assert not np.allclose(per_sec, per_decision), (
            "the two candidate metrics coincide in this run, so the assertion "
            "below would be vacuous"
        )

        blob = torch.load(ckpt_dir / "SelectProbe_best.pt", map_location="cpu",
                          weights_only=False)
        stored = float(blob["best_reward"])
        assert stored == pytest.approx(float(per_sec.max()), abs=1e-5), (
            f"best.pt was selected on {stored}, which is not the per-second rate "
            f"{float(per_sec.max())}"
        )
        assert stored != pytest.approx(float(per_decision.max()), abs=1e-5), (
            "best.pt was selected on the per-decision mean, the metric C2 replaced"
        )

    @pytest.mark.slow
    def test_both_metrics_are_reported_side_by_side(self, tmp_path):
        """A reader must be able to see the two disagree, not just the winner."""
        import pandas as pd
        from src.hot_swap_trainer import run_hot_swap_training

        summary = run_hot_swap_training(
            model_name="BothMetricsProbe", model_cls=IdxPolicy,
            total_steps=60, episodes=1, batch_size=8, swap_interval=5,
            seed=SEED, warmup_steps=WARMUP,
            checkpoint_dir=str(tmp_path / "ckpt"),
            tensorboard_dir=str(tmp_path / "tb"), log_dir=str(tmp_path / "logs"),
        )
        df = pd.read_csv(summary["log_csv_path"])
        for col in ("reward_per_sec_selected", "reward_per_decision"):
            assert col in df.columns
        assert "mean_reward_per_second" in summary
        assert "mean_reward_per_decision" in summary
