# tests/test_baselines_action_roundtrip.py
# ============================================================================
# Regression tests for the baseline defects found in critic/critic_baselines.md.
#
# These cover the layer `assert_hparams_reach_model` cannot see: not whether a
# hyper-parameter NAME reaches a constructor, but whether the VALUE changes what
# the model learns, and whether an action that was executed is credited to the
# slot it was actually taken from.
#
#   C-1  encode_action -> recover round trip, EXHAUSTIVE over every joint index
#        (SPAM-D3QN, CARLTON) and over a dense unit grid (MADDPG-MT).
#   C-3  gamma is effective for all nine models.
#   H-2  exploration / annealing state survives a hot swap for all nine models.
#   H-3  the three SB3 baselines accept a hidden width, so capacity parity is
#        expressible at all.
#   H-4  I-HAMAPPO's value_coef changes the critic step.
#   H1   HeuristicScheduler defaults to the decoder's action space.
#
# Nothing here writes to checkpoints/, results/ or logs/; every artefact goes to
# pytest's tmp_path.
# ============================================================================

from __future__ import annotations

import copy
from typing import Any, Dict

import numpy as np
import pytest
import torch

from src.baselines import ALL_BASELINES, get_baseline
from src.baselines.base_agent import BaseRLModel
from src.baselines.carlton import CARLTON
from src.baselines.i_hamappo import IHAMAPPO
from src.baselines.maddpg_mt import MADDPGMT
from src.baselines.spam_d3qn import SPAMD3QN
from src.heuristic_scheduler import HeuristicScheduler
from src.rl_interface import ActionDecoder, RetrospectiveReplayBuffer, STATE_DIM

NUM_CHANNELS = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_model(name: str, seed: int = 0, **hparams: Any) -> BaseRLModel:
    """Deterministic construction on CPU, so two models differing in one
    hyper-parameter start from identical weights."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    cls = get_baseline(name)
    kwargs: Dict[str, Any] = dict(state_dim=STATE_DIM, num_channels=NUM_CHANNELS)
    if name in ("PPO", "SAC", "TD3"):
        kwargs.update(device="cpu", seed=seed)
    kwargs.update(hparams)
    model = cls(**kwargs)
    return model.to(torch.device("cpu"))


def _fill_buffer(model: BaseRLModel, n: int = 24, seed: int = 0) -> RetrospectiveReplayBuffer:
    """A buffer filled through the model's own select_action, so the stored raw
    actions carry exactly the encoding that model's update() has to invert."""
    rng = np.random.default_rng(seed)
    buf = RetrospectiveReplayBuffer(capacity=n)
    for i in range(n):
        s = rng.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32)
        ns = rng.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32)
        _grant, raw, _info = model.select_action(s, deterministic=False)
        buf.push(
            state=s,
            action=np.asarray(raw, dtype=np.float32).reshape(-1),
            reward=float(rng.uniform(-2.0, 0.0)),
            next_state=ns,
            done=False,
            # A wide spread of holding times: gamma**delta_t only separates two
            # gammas if delta_t actually varies.
            delta_t=float(0.1 + 20.0 * (i / max(1, n - 1))),
        )
    return buf


def _weights(model: BaseRLModel) -> Dict[str, torch.Tensor]:
    return {k: v.detach().clone() for k, v in model.state_dict().items()}


def _max_abs_diff(a: Dict[str, torch.Tensor], b: Dict[str, torch.Tensor]) -> float:
    worst = 0.0
    for key, va in a.items():
        vb = b[key]
        if va.dtype.is_floating_point and va.shape == vb.shape:
            worst = max(worst, float((va - vb).abs().max().item()))
    return worst


# ---------------------------------------------------------------------------
# C-1 -- exhaustive action round trip
# ---------------------------------------------------------------------------
class TestActionRoundTrip:
    """`ActionDecoder.encode_action` maps Delta through a GEOMETRIC unit
    coordinate. Every baseline that stores its output must invert it the same
    way. Inverting linearly put 96 of 128 joint actions in the wrong Q slot."""

    def test_spam_d3qn_recovers_every_joint_index(self):
        model = _make_model("SPAM-D3QN")
        dec = model.decoder
        wrong = []
        raws = []
        for idx in range(model.num_actions):
            delta, ch, power = model._action_to_tuple(idx)
            raws.append(dec.encode_action(delta, ch, power))
        recovered = model._infer_action_indices(torch.as_tensor(np.stack(raws)))
        for idx in range(model.num_actions):
            if int(recovered[idx].item()) != idx:
                wrong.append((idx, int(recovered[idx].item())))
        assert model.num_actions == 128
        assert wrong == [], (
            f"{len(wrong)}/{model.num_actions} joint indices mis-recovered: {wrong[:8]}"
        )

    def test_carlton_recovers_every_branch_triple(self):
        model = _make_model("CARLTON")
        dec = model.decoder
        triples = [
            (d, p, c)
            for d in range(model.num_delta_levels)
            for p in range(model.num_power_levels)
            for c in range(model.num_channels)
        ]
        raws = []
        for d, p, c in triples:
            delta, ch, power = model._action_to_tuple(d, p, c)
            raws.append(dec.encode_action(delta, ch, power))
        recovered = model._infer_branch_indices(torch.as_tensor(np.stack(raws)))
        wrong = [
            (t, tuple(int(x) for x in recovered[i].tolist()))
            for i, t in enumerate(triples)
            if tuple(int(x) for x in recovered[i].tolist()) != t
        ]
        assert len(triples) == 128
        assert wrong == [], f"{len(wrong)}/128 branch triples mis-recovered: {wrong[:8]}"

    def test_spam_and_carlton_share_one_grid(self):
        """The two discretised baselines must quantise identically, or a
        comparison between them measures the grid instead of the learner."""
        spam = _make_model("SPAM-D3QN")
        carl = _make_model("CARLTON")
        assert spam.delta_candidates == pytest.approx(carl.delta_candidates)
        assert spam.power_candidates == pytest.approx(carl.power_candidates)

    def test_maddpg_mt_critic_sees_the_unit_action_that_was_executed(self):
        model = _make_model("MADDPG-MT")
        dec = model.decoder
        units = np.linspace(0.0, 1.0, 101)
        raws = []
        for u in units:
            delta = dec.delta_from_unit(float(u))
            power = dec.p_min + float(u) * (dec.p_max - dec.p_min)
            raws.append(dec.encode_action(delta, 1, power))
        decoded = model._decode_batch_actions(torch.as_tensor(np.stack(raws)))
        assert decoded[:, 0].numpy() == pytest.approx(units, abs=1e-4)
        assert decoded[:, 1].numpy() == pytest.approx(units, abs=1e-4)
        assert torch.argmax(decoded[:, 2:], dim=1).tolist() == [1] * len(units)

    def test_base_helper_inverts_encode_action_for_arbitrary_grants(self):
        """The canonical inversion itself, independent of any one baseline."""
        model = _make_model("SPAM-D3QN")
        dec = ActionDecoder(num_channels=NUM_CHANNELS)
        rng = np.random.default_rng(7)
        deltas = np.exp(
            rng.uniform(np.log(dec.delta_min), np.log(dec.delta_max), size=200)
        )
        powers = rng.uniform(dec.p_min, dec.p_max, size=200)
        chs = rng.integers(0, NUM_CHANNELS, size=200)
        raws = np.stack(
            [dec.encode_action(float(d), int(c), float(p)) for d, c, p in zip(deltas, chs, powers)]
        )
        u_delta, u_power = model.raw_units(torch.as_tensor(raws))
        rec_delta = model.delta_from_unit_t(u_delta).numpy()
        rec_power = model.power_from_unit_t(u_power).numpy()
        rec_ch = model.raw_channel(torch.as_tensor(raws)).numpy()
        assert rec_delta == pytest.approx(deltas, rel=1e-3)
        assert rec_power == pytest.approx(powers, abs=1e-3)
        assert (rec_ch == chs).all()


# ---------------------------------------------------------------------------
# C-3 -- gamma actually changes learning
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(ALL_BASELINES))
def test_gamma_changes_the_update(name: str):
    """A gamma that only lands in an attribute is a reported optimum that never
    reached training. The replay buffer ships its OWN `discount` column built
    from its own gamma; every baseline used to prefer that column, which made
    all nine models train at gamma=0.99 no matter what Optuna found."""
    low = _make_model(name, seed=3, gamma=0.95)
    high = _make_model(name, seed=3, gamma=0.999)
    assert _max_abs_diff(_weights(low), _weights(high)) == 0.0, "seeding is not deterministic"

    buf = _fill_buffer(low, n=24, seed=11)
    torch.manual_seed(123)
    np.random.seed(123)
    batch = buf.sample(16)
    assert "delta_t" in batch and "discount" in batch

    torch.manual_seed(99)
    np.random.seed(99)
    low.update({k: v.clone() for k, v in batch.items()})
    torch.manual_seed(99)
    np.random.seed(99)
    high.update({k: v.clone() for k, v in batch.items()})

    assert _max_abs_diff(_weights(low), _weights(high)) > 1e-9, (
        f"{name}: gamma had no effect on the update"
    )


def test_buffer_discount_column_is_not_the_source_of_truth():
    """Explicit contract for the trainer side of C-3: the model recomputes
    gamma**delta_t from `delta_t`, so a buffer built with a stale gamma cannot
    silently override a searched one. The buffer must supply `delta_t`."""
    model = _make_model("SPAM-D3QN", gamma=0.5)
    rewards = torch.zeros(4, 1)
    batch = {
        "delta_t": torch.tensor([[1.0], [2.0], [3.0], [4.0]]),
        # deliberately inconsistent with gamma=0.5
        "discount": torch.full((4, 1), 0.99),
    }
    got = model.smdp_discounts(batch, rewards)
    assert got.flatten().tolist() == pytest.approx([0.5, 0.25, 0.125, 0.0625])


# ---------------------------------------------------------------------------
# H-2 -- exploration state must cross the hot swap
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(ALL_BASELINES))
def test_annealing_state_survives_a_hot_swap(name: str):
    """`DualModelHotSwapManager` copies parameters and buffers only, and
    `update()` runs on the Rest model. Any annealed scalar kept as a plain Python
    attribute therefore stays frozen on the model that is actually acting."""
    act = _make_model(name, seed=5)
    rest = _make_model(name, seed=5)

    buf = _fill_buffer(rest, n=24, seed=5)
    for _ in range(5):
        rest.update(buf.sample(16))

    act_names = {k for k, _ in act.named_buffers()}
    rest_buffers = dict(rest.named_buffers())
    assert act_names == set(rest_buffers)

    # The swap the trainer performs.
    with torch.no_grad():
        for p_a, p_r in zip(act.parameters(), rest.parameters()):
            p_a.data.copy_(p_r.data)
        for b_a, b_r in zip(act.buffers(), rest.buffers()):
            b_a.data.copy_(b_r.data)

    for key, value in dict(act.named_buffers()).items():
        assert torch.allclose(value, rest_buffers[key]), f"{name}: buffer {key} did not cross"

    # Any epsilon-greedy baseline must have annealed on the Rest model and the
    # acting model must see that anneal.
    if "epsilon" in rest_buffers:
        assert float(rest_buffers["epsilon"].item()) < 0.2
        assert float(dict(act.named_buffers())["epsilon"].item()) == pytest.approx(
            float(rest_buffers["epsilon"].item())
        )


def test_spam_d3qn_exploration_state_is_registered_and_checkpointed(tmp_path):
    """H-2 specifically: epsilon / per_beta / total_updates used to be plain
    attributes, so they neither crossed the swap nor survived a reload."""
    model = _make_model("SPAM-D3QN")
    names = {k for k, _ in model.named_buffers()}
    assert {"epsilon", "per_beta", "total_updates"} <= names

    buf = _fill_buffer(model, n=24, seed=2)
    for _ in range(3):
        model.update(buf.sample(16))
    eps = float(model.epsilon.item())
    beta = float(model.per_beta.item())
    assert eps < 0.2 and beta > 0.4

    path = tmp_path / "spam.pt"
    model.save(str(path))
    reloaded = _make_model("SPAM-D3QN")
    reloaded.load(str(path))
    assert float(reloaded.epsilon.item()) == pytest.approx(eps)
    assert float(reloaded.per_beta.item()) == pytest.approx(beta)
    assert int(reloaded.total_updates.item()) == 3


# ---------------------------------------------------------------------------
# H-3 -- capacity parity is expressible for the SB3 three
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["PPO", "SAC", "TD3"])
def test_sb3_baselines_accept_a_hidden_width(name: str):
    default = _make_model(name)
    narrow = _make_model(name, hidden_dim=64)
    wide = _make_model(name, hidden_dim=256)
    n_narrow = sum(p.numel() for p in narrow.parameters())
    n_wide = sum(p.numel() for p in wide.parameters())
    assert n_wide > n_narrow
    assert default.hidden_dim is None and narrow.hidden_dim == 64


def test_hidden_dim_rejects_a_nonsense_width():
    with pytest.raises(ValueError):
        _make_model("PPO", hidden_dim=0)


# ---------------------------------------------------------------------------
# H-4 -- searched values that did not reach the gradient
# ---------------------------------------------------------------------------
def test_i_hamappo_value_coef_changes_the_critic_step():
    low = _make_model("I-HAMAPPO", seed=4, value_coef=0.2)
    high = _make_model("I-HAMAPPO", seed=4, value_coef=0.8)
    buf = _fill_buffer(low, n=24, seed=4)
    batch = buf.sample(16)
    torch.manual_seed(1)
    low.update({k: v.clone() for k, v in batch.items()})
    torch.manual_seed(1)
    high.update({k: v.clone() for k, v in batch.items()})
    assert _max_abs_diff(_weights(low), _weights(high)) > 1e-9


def test_ma2hdqn_reports_that_n_step_is_inactive():
    """n-step returns cannot be assembled from a uniformly sampled SMDP buffer.
    The model must say so instead of accepting `n_step` silently."""
    model = _make_model("MA2HDQN", n_step=5)
    buf = _fill_buffer(model, n=24, seed=6)
    out = model.update(buf.sample(16))
    assert out["n_step_active"] == 0.0


def test_carlton_policy_temperature_is_separable_from_the_backup():
    """M-1: omega is the mellowmax operator parameter AND used to be the policy
    temperature. They are now separate arguments, and the policy entropy is
    reported so a collapse is visible."""
    model = _make_model("CARLTON", omega=10.0, policy_beta=0.1)
    assert model.omega == 10.0 and model.policy_beta == 0.1
    default = _make_model("CARLTON", omega=3.0)
    assert default.policy_beta == 3.0

    buf = _fill_buffer(model, n=24, seed=8)
    out = model.update(buf.sample(16))
    for branch in ("delta", "power", "channel"):
        key = f"policy_entropy_{branch}"
        assert key in out
        assert 0.0 <= out[key] <= 1.0 + 1e-6
    # A near-uniform temperature must leave the policy near-uniform.
    assert out["policy_entropy_delta"] > 0.9


# ---------------------------------------------------------------------------
# H1 -- the heuristic is evaluated on the RL baselines' action space
# ---------------------------------------------------------------------------
class TestHeuristicActionSpaceParity:
    def test_defaults_come_from_the_decoder(self):
        dec = ActionDecoder(num_channels=NUM_CHANNELS)
        sched = HeuristicScheduler(num_subchannels=NUM_CHANNELS)
        assert sched.delta_min == pytest.approx(dec.delta_min)
        assert sched.delta_max == pytest.approx(dec.delta_max)
        assert sched.p_low == pytest.approx(dec.p_min)
        assert sched.p_high == pytest.approx(dec.p_max)
        assert sched.action_space_handicapped is False

    def test_red_phase_backoff_reaches_the_full_red_duration(self):
        """The scenario's red phase is 45 s and Rule 2 exists to stay silent for
        it. A delta_max of 10 s truncates exactly the behaviour the paper claims
        matters, and that is what the benchmark harness used to pass in."""
        sched = HeuristicScheduler(num_subchannels=NUM_CHANNELS)
        interval, _ch, power = sched.decide_grant(
            "veh0",
            {
                "speed": 0.0,
                "accel": 0.0,
                "dist_to_rsu": 100.0,
                "tls_features": {
                    "state": "r",
                    "time_to_switch": 45.0,
                    "dist_to_stopline": 3.0,
                    "stop_imminent": 0.0,
                    "start_imminent": 0.0,
                },
            },
        )
        assert interval == pytest.approx(44.0)
        assert power == pytest.approx(sched.decoder.p_min)

    def test_a_narrowed_action_space_is_flagged(self):
        sched = HeuristicScheduler(delta_min=0.5, delta_max=10.0, num_subchannels=NUM_CHANNELS)
        assert sched.action_space_handicapped is True


# ---------------------------------------------------------------------------
# Reference table: parameter count per baseline (H-3 evidence).
# ---------------------------------------------------------------------------
def test_parameter_counts_are_recorded(tmp_path):
    rows = []
    for name in ALL_BASELINES:
        model = _make_model(name)
        rows.append((name, sum(p.numel() for p in model.parameters())))
    out = tmp_path / "baseline_param_counts.csv"
    out.write_text(
        "model_name,num_parameters\n" + "\n".join(f"{n},{c}" for n, c in rows) + "\n"
    )
    assert len(rows) == 9
    assert all(c > 0 for _n, c in rows)


# ---------------------------------------------------------------------------
# Low-density robustness (density sweep goes down to 5 vehicles).
#
# At density 5 only a handful of vehicles are ever inside the RSU range, so a
# minibatch can be a single transition and its entries can be almost identical.
# Neither may produce NaN weights or a silently exploding step.
# ---------------------------------------------------------------------------
def _degenerate_buffer(model: BaseRLModel, n: int) -> RetrospectiveReplayBuffer:
    """Every transition identical: the worst case a near-empty RSU range produces."""
    buf = RetrospectiveReplayBuffer(capacity=max(1, n))
    s = np.zeros(STATE_DIM, dtype=np.float32)
    for _ in range(n):
        _grant, raw, _info = model.select_action(s, deterministic=True)
        buf.push(
            state=s,
            action=np.asarray(raw, dtype=np.float32).reshape(-1),
            reward=-1.0,
            next_state=s.copy(),
            done=False,
            delta_t=1.0,
        )
    return buf


@pytest.mark.parametrize("name", list(ALL_BASELINES))
@pytest.mark.parametrize("batch_size", [1, 2, 16])
def test_update_survives_a_tiny_batch(name: str, batch_size: int):
    model = _make_model(name, seed=batch_size)
    buf = _fill_buffer(model, n=batch_size, seed=batch_size)
    out = model.update(buf.sample(batch_size))
    assert np.isfinite(out["loss"]), f"{name}: non-finite loss at batch_size={batch_size}"
    for param in model.parameters():
        assert torch.isfinite(param).all(), (
            f"{name}: non-finite weights after a batch of {batch_size}"
        )


@pytest.mark.parametrize("name", list(ALL_BASELINES))
def test_update_survives_a_degenerate_batch(name: str):
    """Zero-variance advantages must not be divided away to infinity."""
    model = _make_model(name, seed=1)
    buf = _degenerate_buffer(model, n=16)
    out = model.update(buf.sample(16))
    assert np.isfinite(out["loss"])
    for param in model.parameters():
        assert torch.isfinite(param).all(), f"{name}: non-finite weights on a degenerate batch"


# ---------------------------------------------------------------------------
# M-5 backstop: reward weights configure the environment, never a model.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", ["w1", "w4", "w2_raw"])
def test_reward_weights_cannot_be_absorbed_by_a_model(key: str):
    with pytest.raises(TypeError, match="reward weights"):
        get_baseline("CARLTON")(state_dim=STATE_DIM, num_channels=NUM_CHANNELS, **{key: 0.5})


def test_genuine_unknown_hparams_are_still_absorbed():
    """The guard must be narrow: only the reward-weight family is rejected."""
    model = get_baseline("CARLTON")(
        state_dim=STATE_DIM, num_channels=NUM_CHANNELS, some_future_key=1.0
    )
    assert model.hparams == {"some_future_key": 1.0}


# ---------------------------------------------------------------------------
# The two credit-assignment paths must agree.
#
# `hot_swap_trainer` now plumbs `info["action_idx"]` through the streamer, so a
# live batch carries the verbatim index and `update()` takes the explicit path.
# The inferred path still runs for any transition without one (the HPO buffer,
# anything replayed from an older store). If the two disagree, the model credits
# a different slot depending on which producer filled the buffer -- exactly the
# C-1 failure mode, just moved one layer out.
# ---------------------------------------------------------------------------
_DISCRETE_HEADS = ["SPAM-D3QN", "CARLTON", "RES-MAPDDPG", "MA2HDQN", "I-HAMAPPO"]


def _inferred_index(model: BaseRLModel, raw: np.ndarray) -> int:
    t = torch.as_tensor(np.asarray(raw, dtype=np.float32).reshape(1, -1))
    if isinstance(model, SPAMD3QN):
        return int(model._infer_action_indices(t)[0].item())
    if isinstance(model, CARLTON):
        branch = model._infer_branch_indices(t)[0]
        return model.pack_action_index(int(branch[0]), int(branch[1]), int(branch[2]))
    return int(model._resolve_channel_indices({"action": t}, torch.device("cpu"))[0].item())


@pytest.mark.parametrize("name", _DISCRETE_HEADS)
def test_live_action_idx_matches_the_inferred_one(name: str):
    model = _make_model(name)
    rng = np.random.default_rng(0)
    for _ in range(200):
        s = rng.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32)
        _grant, raw, info = model.select_action(s, deterministic=False)
        assert int(info["action_idx"]) == _inferred_index(model, raw), (
            f"{name}: the index the model reported and the index recovered from "
            "its own raw action disagree"
        )


@pytest.mark.parametrize("name", _DISCRETE_HEADS)
def test_update_is_identical_with_and_without_action_idx(name: str):
    """Dropping the explicit index must change nothing, because the fallback
    recovers the same slot."""
    with_idx = _make_model(name, seed=2)
    without = _make_model(name, seed=2)

    buf = _fill_buffer(with_idx, n=24, seed=2)
    # Re-push with the verbatim index, the way the live streamer now does.
    indexed = RetrospectiveReplayBuffer(capacity=len(buf.buffer))
    for item in buf.buffer:
        indexed.push(
            state=item["state"],
            action=item["action"],
            reward=item["reward"],
            next_state=item["next_state"],
            done=bool(item["done"]),
            delta_t=item["delta_t"],
            action_idx=_inferred_index(with_idx, item["action"]),
        )

    torch.manual_seed(7)
    batch_idx = indexed.sample(16)
    assert "action_idx" in batch_idx
    batch_plain = {k: v.clone() for k, v in batch_idx.items() if k != "action_idx"}

    torch.manual_seed(9)
    with_idx.update({k: v.clone() for k, v in batch_idx.items()})
    torch.manual_seed(9)
    without.update(batch_plain)
    assert _max_abs_diff(_weights(with_idx), _weights(without)) == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Benchmark numbers must not depend on exploration state.
#
# `run_hot_swap_training` cycles the density schedule over episodes, and the
# gradient-update budget an episode receives scales with its density (measured:
# 2 updates at density 5 against 36 at density 50 for a 300-step episode). That
# skew is a training-budget question (H-1, BackgroundTrainer). It must NOT also
# reach the reported table: `evaluate_single_run` calls every model with
# `deterministic=True`, so a model whose greedy action still moved with epsilon,
# a Boltzmann temperature or an exploration sigma would let the annealing
# trajectory -- and therefore the density mixture -- leak into the benchmark.
# ---------------------------------------------------------------------------
_EXPLORATION_BUFFERS = ("epsilon", "per_beta")
_EXPLORATION_ATTRS = (
    "policy_beta",
    "exploration_noise",
    "param_noise_std",
    "action_noise_std",
    "gumbel_tau",
)


@pytest.mark.parametrize("name", list(ALL_BASELINES))
def test_deterministic_action_ignores_exploration_state(name: str):
    model = _make_model(name)
    rng = np.random.default_rng(0)
    states = [rng.uniform(-1.0, 1.0, size=STATE_DIM).astype(np.float32) for _ in range(40)]
    before = [model.select_action(s, deterministic=True)[0] for s in states]

    with torch.no_grad():
        for buf_name, buf in model.named_buffers():
            if buf_name in _EXPLORATION_BUFFERS:
                buf.fill_(1.0)
    for attr in _EXPLORATION_ATTRS:
        if hasattr(model, attr):
            setattr(model, attr, 50.0)

    after = [model.select_action(s, deterministic=True)[0] for s in states]
    for (d0, c0, p0), (d1, c1, p1) in zip(before, after):
        assert d0 == pytest.approx(d1) and c0 == c1 and p0 == pytest.approx(p1), (
            f"{name}: the greedy action moved when exploration state changed"
        )


# ---------------------------------------------------------------------------
# Checkpoint contract.
#
# `evaluate.build_evaluated_model` loads training weights with strict=True and
# treats the checkpoint's own hparams as authoritative, because a non-strict
# load silently leaves un-restored tensors at their random initialisation --
# the failure that put random-weight numbers in the results table. Registering
# exploration scalars as buffers (H-2) added keys to these state dicts, so the
# round trip has to be asserted for all nine, not just the model that changed.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(ALL_BASELINES))
def test_checkpoint_round_trip_is_strict_and_complete(name: str, tmp_path):
    trained = _make_model(name, seed=13)
    buf = _fill_buffer(trained, n=24, seed=13)
    for _ in range(3):
        trained.update(buf.sample(16))

    path = tmp_path / f"{name.replace('-', '')}.pt"
    trained.save(str(path))

    fresh = _make_model(name, seed=99)
    # A strict load must accept the bundle: identical key sets, identical shapes.
    fresh.load_state_dict(torch.load(str(path), map_location="cpu")["state_dict"], strict=True)
    assert _max_abs_diff(_weights(trained), _weights(fresh)) == pytest.approx(0.0, abs=0.0)

    # And every buffer -- the annealed exploration state included -- comes back.
    trained_buffers = dict(trained.named_buffers())
    for key, value in dict(fresh.named_buffers()).items():
        assert torch.equal(value, trained_buffers[key]), f"{name}: buffer {key} not restored"


@pytest.mark.parametrize("name", list(ALL_BASELINES))
def test_checkpoint_records_the_hparams_it_was_shaped_by(name: str, tmp_path):
    """`build_evaluated_model` reconstructs from the checkpoint's hparams, so the
    bundle must carry the geometry the tensors were built with."""
    model = _make_model(name, seed=1)
    path = tmp_path / "m.pt"
    model.save(str(path))
    bundle = torch.load(str(path), map_location="cpu", weights_only=False)
    assert bundle["state_dim"] == STATE_DIM
    assert bundle["num_channels"] == NUM_CHANNELS
    assert isinstance(bundle["hparams"], dict)


# ---------------------------------------------------------------------------
# `BaseRLModel.load()` must understand the bundle the trainer actually writes.
#
# `save()` writes {"state_dict": ...}; `HotSwapTrainer.save_checkpoint` writes
# {"act_state_dict": ..., "rest_state_dict": ..., ...}. Handed the latter, load()
# used to fall through to `load_state_dict(bundle)` and feed metadata keys to
# the loader, producing an error that named nothing useful.
# ---------------------------------------------------------------------------
def test_load_prefers_the_acting_policy_from_a_trainer_bundle(tmp_path):
    """`act_model` is the copy that produced every reward the checkpoint claims;
    `rest_state_dict` holds newer but never-validated updates."""
    acting = _make_model("SPAM-D3QN", seed=21)
    learner = _make_model("SPAM-D3QN", seed=22)
    assert _max_abs_diff(_weights(acting), _weights(learner)) > 0.0

    path = tmp_path / "trainer_bundle.pt"
    torch.save(
        {
            "model_name": "SPAM-D3QN",
            "hparams": {},
            "act_state_dict": acting.state_dict(),
            "rest_state_dict": learner.state_dict(),
            "training_steps": 7,
        },
        str(path),
    )

    fresh = _make_model("SPAM-D3QN", seed=99)
    fresh.load(str(path))
    assert _max_abs_diff(_weights(fresh), _weights(acting)) == pytest.approx(0.0, abs=0.0)
    assert _max_abs_diff(_weights(fresh), _weights(learner)) > 0.0


def test_load_names_a_state_dim_mismatch_instead_of_dumping_shapes(tmp_path):
    """The pre-smoke checkpoints in backup/ were all written at state_dim 18 and
    became unusable when the observation dropped to 17. That cause must be in the
    message, not inferred from a wall of size mismatches."""
    model = _make_model("SPAM-D3QN")
    path = tmp_path / "wrong_width.pt"
    model.save(str(path))
    bundle = torch.load(str(path), map_location="cpu", weights_only=False)
    bundle["state_dim"] = STATE_DIM + 1
    torch.save(bundle, str(path))

    with pytest.raises(ValueError, match="state_dim"):
        _make_model("SPAM-D3QN").load(str(path))


def test_load_rejects_a_bundle_it_does_not_understand(tmp_path):
    path = tmp_path / "junk.pt"
    torch.save({"model_name": "SPAM-D3QN", "training_steps": 3}, str(path))
    with pytest.raises(KeyError):
        _make_model("SPAM-D3QN").load(str(path))


def test_load_still_accepts_a_bare_state_dict(tmp_path):
    trained = _make_model("CARLTON", seed=31)
    path = tmp_path / "bare.pt"
    torch.save(trained.state_dict(), str(path))
    fresh = _make_model("CARLTON", seed=32)
    fresh.load(str(path))
    assert _max_abs_diff(_weights(fresh), _weights(trained)) == pytest.approx(0.0, abs=0.0)


# ---------------------------------------------------------------------------
# `save()` must snapshot, not alias.
#
# A state dict holds references to the live tensors. Serialising it directly
# records whatever they contain while torch.save walks them, so on a model the
# background trainer is still updating the file gets a TORN snapshot: some
# tensors from the old policy, some from the new -- a policy that never ran,
# stored next to a reward it never earned. `HotSwapTrainer.save_checkpoint`
# takes locks for the same reason.
# ---------------------------------------------------------------------------
def test_save_snapshots_do_not_alias_live_parameters(tmp_path):
    model = _make_model("SPAM-D3QN", seed=41)
    path = tmp_path / "snap.pt"
    model.save(str(path))

    # Move the live model far away from what was written.
    with torch.no_grad():
        for param in model.parameters():
            param.fill_(123.0)

    bundle = torch.load(str(path), map_location="cpu", weights_only=False)
    saved = bundle["state_dict"]
    float_tensors = [v for v in saved.values() if v.dtype.is_floating_point and v.numel()]
    assert float_tensors, "no float tensors in the snapshot"
    assert not all(torch.all(v == 123.0) for v in float_tensors), (
        "the checkpoint followed the live tensors instead of snapshotting them"
    )


@pytest.mark.parametrize("name", list(ALL_BASELINES))
def test_saved_tensors_are_cpu_resident(name: str, tmp_path):
    """The file must load on a machine without the GPU it was trained on."""
    model = _make_model(name, seed=1)
    path = tmp_path / "cpu.pt"
    model.save(str(path))
    bundle = torch.load(str(path), map_location="cpu", weights_only=False)
    for key, value in bundle["state_dict"].items():
        assert value.device.type == "cpu", f"{name}: {key} was saved on {value.device}"


# ---------------------------------------------------------------------------
# H-3 core claim, tested directly.
#
# `test_sb3_baselines_accept_a_hidden_width` only checks that the parameter
# count MOVES. That would still pass if `hidden_dim` produced some arbitrary
# width, and it says nothing about the two contracts the docstring states: that
# an explicit `net_arch` wins, and that the caller's dict is not mutated. A
# claim covered only by adjacent assertions is a claim with no test.
# ---------------------------------------------------------------------------
from src.baselines.sb3_wrapper import SB3BaselineModel


class TestHiddenDimContract:
    def test_none_leaves_policy_kwargs_untouched(self):
        assert SB3BaselineModel.apply_hidden_dim(None, None) is None
        kwargs = {"activation_fn": "relu"}
        assert SB3BaselineModel.apply_hidden_dim(kwargs, None) is kwargs

    def test_scalar_width_becomes_two_equal_layers(self):
        assert SB3BaselineModel.apply_hidden_dim(None, 128) == {"net_arch": [128, 128]}

    def test_an_explicit_net_arch_wins(self):
        """Otherwise a capacity-parity sweep would silently overwrite a width the
        caller chose deliberately."""
        got = SB3BaselineModel.apply_hidden_dim({"net_arch": [8, 8]}, 256)
        assert got["net_arch"] == [8, 8]

    def test_the_callers_dict_is_not_mutated(self):
        caller = {"activation_fn": "relu"}
        got = SB3BaselineModel.apply_hidden_dim(caller, 64)
        assert got["net_arch"] == [64, 64]
        assert caller == {"activation_fn": "relu"}, "apply_hidden_dim mutated its argument"

    @pytest.mark.parametrize("name", ["PPO", "SAC", "TD3"])
    def test_the_requested_width_reaches_the_network(self, name: str):
        """The first weight matrix must actually be (hidden_dim, state_dim)."""
        model = _make_model(name, hidden_dim=128)
        two_d = [tuple(p.shape) for _n, p in model.policy.named_parameters() if p.ndim == 2]
        assert (128, STATE_DIM) in two_d, f"{name}: no (128, {STATE_DIM}) layer; got {two_d[:4]}"

    @pytest.mark.parametrize("name", ["PPO", "SAC", "TD3"])
    def test_explicit_net_arch_wins_end_to_end(self, name: str):
        wide = _make_model(name, hidden_dim=128)
        pinned = _make_model(name, hidden_dim=128, policy_kwargs={"net_arch": [8, 8]})
        assert sum(p.numel() for p in pinned.parameters()) < sum(
            p.numel() for p in wide.parameters()
        )
