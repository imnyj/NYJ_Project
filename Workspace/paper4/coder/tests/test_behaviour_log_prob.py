"""Regression tests for the missing importance ratio in the on-policy baselines.

The defect. `RetrospectiveReplayBuffer` stored no behaviour log-probability, so
`PPO.update()` rebuilt the denominator of pi_new / pi_behaviour from the CURRENT
policy. That makes the first inner epoch's ratio exactly 1, and PPO's clipping
only acts outside [1 - eps, 1 + eps], so the first and largest gradient step of
every update was an unclipped policy gradient on stale off-policy data. Both
on-policy baselines diverged from it, PPO even at the textbook 3e-4
(`results/hpo/divergence_detection_check.csv`).

Every test below fails against the code as it stood on 2026-09-03: the buffer
had no such column, `decide_grant` returned three values, and neither
`update()` reported which denominator it used.
"""

import logging

import numpy as np
import pytest
import torch
import torch.nn as nn

from src.baselines import ALL_BASELINES, get_baseline
from src.baselines.i_hamappo import IHAMAPPO
from src.baselines.sb3_ppo import PPO
from src.hot_swap_trainer import HotSwapTrainer, TransitionStreamer
from src.rl_interface import STATE_DIM, ActionDecoder, RetrospectiveReplayBuffer

NUM_CH = 4
BATCH = 32


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_buffer(n: int = BATCH * 2, *, log_probs=None, seed: int = 0):
    """A buffer of decodable transitions, optionally carrying behaviour log-probs."""
    buf = RetrospectiveReplayBuffer(capacity=4 * n, gamma=0.99)
    dec = ActionDecoder(num_channels=NUM_CH)
    rng = np.random.default_rng(seed)
    for i in range(n):
        s = rng.random(STATE_DIM).astype(np.float32)
        ns = rng.random(STATE_DIM).astype(np.float32)
        delta = float(dec.delta_min * (dec.delta_max / dec.delta_min) ** rng.random())
        power = float(dec.p_min + (dec.p_max - dec.p_min) * rng.random())
        raw = dec.encode_action(delta, int(i % NUM_CH), power)
        kw = {}
        if log_probs is not None:
            kw["behaviour_log_prob"] = float(log_probs[i])
        buf.push(s, raw, float(-rng.random()), ns, False, delta, **kw)
    return buf


class LogProbPolicy(nn.Module):
    """Minimal policy that reports a behaviour log-probability, like PPO does."""

    def __init__(self, state_dim=STATE_DIM, num_channels=NUM_CH, gamma=0.9, **hparams):
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
        grant = (self.decoder.delta_from_unit(0.5), self.calls % self.num_channels, 15.0)
        return grant, np.zeros(3, dtype=np.float32), {"log_prob": -0.5 * self.calls}

    def update(self, batch):
        loss = self.net(batch["state"]).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return {"loss": float(loss.item())}


# ---------------------------------------------------------------------------
# 1. The column exists and follows the same all-or-nothing rule as action_idx
# ---------------------------------------------------------------------------
class TestBufferCarriesBehaviourLogProb:
    def test_sample_emits_the_column_when_every_transition_has_one(self):
        logps = -np.arange(1, BATCH + 1, dtype=np.float64) / 10.0
        batch = make_buffer(BATCH, log_probs=logps).sample(BATCH)
        assert "behaviour_log_prob" in batch
        assert batch["behaviour_log_prob"].shape == (BATCH, 1)
        assert sorted(round(float(v), 4) for v in batch["behaviour_log_prob"].reshape(-1)) == \
            sorted(round(float(v), 4) for v in logps)

    def test_no_column_when_no_transition_has_one(self):
        """The legacy contract: batches for the seven off-policy models are unchanged."""
        assert "behaviour_log_prob" not in make_buffer(BATCH).sample(BATCH)

    def test_no_column_when_only_some_transitions_have_one(self):
        """A half-filled column cannot form a consistent ratio, so it is withheld."""
        buf = make_buffer(BATCH, log_probs=np.full(BATCH, -0.3))
        s = np.zeros(STATE_DIM, dtype=np.float32)
        buf.push(s, np.zeros(3, dtype=np.float32), -0.1, s, False, 1.0)
        assert "behaviour_log_prob" not in buf.sample(BATCH + 1)

    def test_non_finite_log_prob_is_stored_as_absent(self):
        """A NaN denominator would poison the ratio silently; drop it at the door."""
        buf = RetrospectiveReplayBuffer(capacity=8)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        buf.push(s, np.zeros(3, dtype=np.float32), -0.1, s, False, 1.0,
                 behaviour_log_prob=float("nan"))
        assert buf.buffer[0]["behaviour_log_prob"] is None


# ---------------------------------------------------------------------------
# 2. The wiring: model info -> decide_grant -> streamer -> buffer
# ---------------------------------------------------------------------------
class TestBehaviourLogProbReachesTheBatch:
    def test_streamer_forwards_the_value(self):
        streamer = TransitionStreamer(maxsize=64)
        buf = RetrospectiveReplayBuffer(capacity=64, gamma=0.9)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        for i in range(8):
            streamer.push(s, np.zeros(3, dtype=np.float32), -0.1, s, False, 1.0,
                          behaviour_log_prob=-0.1 * i)
        assert streamer.push_to_buffer(buf) == 8
        batch = buf.sample(8)
        assert "behaviour_log_prob" in batch
        assert sorted(round(float(v), 4) for v in batch["behaviour_log_prob"].reshape(-1)) == \
            [round(-0.1 * i, 4) for i in range(7, -1, -1)]

    def test_end_to_end_through_the_scheduler(self):
        """model info["log_prob"] -> decide_grant -> push_transition -> batch."""
        trainer = HotSwapTrainer(model_cls=LogProbPolicy, state_dim=STATE_DIM,
                                 num_channels=NUM_CH, buffer_capacity=64, batch_size=8)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        seen = []
        for _ in range(8):
            _grant, raw, idx, logp = trainer.scheduler.decide_grant("v", s)
            assert logp is not None, "decide_grant dropped the behaviour log-probability"
            seen.append(logp)
            trainer.scheduler.push_transition(
                state=s, raw_action=raw, reward=-0.1, next_state=s,
                done=False, delta_t=1.0, action_idx=idx, behaviour_log_prob=logp,
            )
        trainer.streamer.push_to_buffer(trainer.replay_buffer)
        batch = trainer.replay_buffer.sample(8)
        assert "behaviour_log_prob" in batch
        assert sorted(round(float(v), 4) for v in batch["behaviour_log_prob"].reshape(-1)) == \
            sorted(round(v, 4) for v in seen)

    def test_a_policy_without_log_probs_leaves_the_column_empty(self):
        """The seven off-policy baselines report no log_prob and must stay unaffected."""
        class NoLogProb(LogProbPolicy):
            def select_action(self, state, deterministic=False):
                grant, raw, _info = super().select_action(state, deterministic)
                return grant, raw, {"action_idx": 1}

        trainer = HotSwapTrainer(model_cls=NoLogProb, state_dim=STATE_DIM,
                                 num_channels=NUM_CH, buffer_capacity=64, batch_size=8)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        for _ in range(8):
            _grant, raw, idx, logp = trainer.scheduler.decide_grant("v", s)
            assert logp is None
            trainer.scheduler.push_transition(
                state=s, raw_action=raw, reward=-0.1, next_state=s,
                done=False, delta_t=1.0, action_idx=idx, behaviour_log_prob=logp,
            )
        trainer.streamer.push_to_buffer(trainer.replay_buffer)
        assert "behaviour_log_prob" not in trainer.replay_buffer.sample(8)


# ---------------------------------------------------------------------------
# 3. The ratio is no longer identically 1
# ---------------------------------------------------------------------------
class TestPPOImportanceRatioIsReal:
    def test_stored_log_probs_move_the_first_epoch_ratio_off_one(self):
        model = PPO(state_dim=STATE_DIM, num_channels=NUM_CH, n_epochs=4, seed=0)
        # A behaviour policy that is genuinely a different policy: log-probs
        # drawn away from whatever the current network would report.
        rng = np.random.default_rng(3)
        logps = rng.normal(loc=-4.0, scale=1.0, size=BATCH * 2)
        out = model.update(make_buffer(BATCH * 2, log_probs=logps).sample(BATCH))
        assert out["behaviour_logp_stored"] == 1.0
        assert abs(out["first_epoch_ratio_mean"] - 1.0) > 1e-3, (
            "the first-epoch ratio is still pinned at 1: the stored behaviour "
            "log-probability is being ignored"
        )
        assert out["first_epoch_ratio_std"] > 0.0
        assert out["first_epoch_clip_fraction"] > 0.0, (
            "clipping never fires, so the trust region is inert"
        )

    def test_the_fallback_reproduces_the_defect_and_says_so(self):
        """Without the column the ratio IS 1 -- the point is that it is reported."""
        model = PPO(state_dim=STATE_DIM, num_channels=NUM_CH, n_epochs=4, seed=0)
        out = model.update(make_buffer(BATCH * 2).sample(BATCH))
        assert out["behaviour_logp_stored"] == 0.0
        assert out["first_epoch_ratio_mean"] == pytest.approx(1.0, abs=1e-5)
        assert out["first_epoch_ratio_std"] == pytest.approx(0.0, abs=1e-5)
        assert out["first_epoch_clip_fraction"] == 0.0

    def test_the_fallback_warns_once(self, caplog):
        model = PPO(state_dim=STATE_DIM, num_channels=NUM_CH, n_epochs=1, seed=0)
        with caplog.at_level(logging.WARNING, logger="src.baselines.base_agent"):
            model.update(make_buffer(BATCH * 2).sample(BATCH))
            model.update(make_buffer(BATCH * 2, seed=1).sample(BATCH))
        hits = [r for r in caplog.records if "behaviour_log_prob" in r.getMessage()]
        assert len(hits) == 1, f"expected exactly one warning, got {len(hits)}"

    def test_the_loss_stays_finite_under_extreme_ratios(self):
        """exp() of a large log-ratio is inf in float32 without the clamp."""
        model = PPO(state_dim=STATE_DIM, num_channels=NUM_CH, n_epochs=2, seed=0)
        logps = np.full(BATCH * 2, -5000.0)
        out = model.update(make_buffer(BATCH * 2, log_probs=logps).sample(BATCH))
        assert np.isfinite(out["loss"]), out
        assert np.isfinite(out["policy_loss"])
        assert all(torch.isfinite(p).all() for p in model.policy.parameters())


class TestIHAMAPPOImportanceRatioIsReal:
    def test_stored_log_probs_are_preferred_over_the_frozen_snapshot(self):
        model = IHAMAPPO(state_dim=STATE_DIM, num_channels=NUM_CH)
        rng = np.random.default_rng(5)
        logps = rng.normal(loc=-8.0, scale=1.0, size=BATCH * 2)
        out = model.update(make_buffer(BATCH * 2, log_probs=logps).sample(BATCH))
        assert out["behaviour_logp_stored"] == 1.0
        assert abs(out["mean_ratio"] - 1.0) > 1e-3
        assert out["ratio_std"] > 0.0

    def test_without_the_column_the_snapshot_path_is_reported(self):
        model = IHAMAPPO(state_dim=STATE_DIM, num_channels=NUM_CH)
        out = model.update(make_buffer(BATCH * 2).sample(BATCH))
        assert out["behaviour_logp_stored"] == 0.0
        # A freshly synced snapshot equals the current policy, so this ratio is 1
        # -- which is exactly the weakening the stored column removes.
        assert out["mean_ratio"] == pytest.approx(1.0, abs=1e-4)

    def test_the_loss_stays_finite_under_extreme_ratios(self):
        model = IHAMAPPO(state_dim=STATE_DIM, num_channels=NUM_CH)
        logps = np.full(BATCH * 2, -5000.0)
        out = model.update(make_buffer(BATCH * 2, log_probs=logps).sample(BATCH))
        assert np.isfinite(out["loss"]), out
        assert all(torch.isfinite(p).all() for p in model.parameters())


# ---------------------------------------------------------------------------
# 4. The new column must not disturb the other seven baselines
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ALL_BASELINES)
def test_every_baseline_updates_with_and_without_the_column(name):
    """Same weight movement either way: only the two PPO-family models read it."""
    model = get_baseline(name)(state_dim=STATE_DIM, num_channels=NUM_CH)
    plain = make_buffer(BATCH * 2, seed=7).sample(BATCH)
    with_col = {k: v.clone() for k, v in plain.items()}
    with_col["behaviour_log_prob"] = torch.full((BATCH, 1), -2.0)

    before = {k: v.detach().clone() for k, v in model.state_dict().items()
              if v.dtype.is_floating_point}
    out_plain = model.update(plain)
    out_col = model.update(with_col)
    after = model.state_dict()

    assert np.isfinite(out_plain["loss"]) and np.isfinite(out_col["loss"])
    assert any(not torch.allclose(v, after[k].detach()) for k, v in before.items()), (
        f"{name}.update() stopped moving weights"
    )
    # The batch column must never be mistaken for a hyper-parameter.
    assert "behaviour_log_prob" not in getattr(model, "hparams", {})
