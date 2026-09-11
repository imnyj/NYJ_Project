# src/baselines/hoorl.py
# ============================================================================
# HOORL -- Hybrid Offline-Online Reinforcement Learning for AoI- and
#          Energy-Aware Resource Scheduling
#
# J. Xu, X. Zhou, M. Song, W. Wang, D. Niyato and C. Yuen, "AoI and Energy-Aware
# Resource Scheduling for Crowdsensing: A Hybrid Reinforcement Learning
# Framework," IEEE Transactions on Vehicular Technology, vol. 75, no. 8,
# pp. 18102--18115, 2026. DOI: 10.1109/TVT.2026.3675626
#
# Replaces CARLTON in the "similar" category on 2026-09-05. The reason for the
# replacement is recorded in backup/carlton_replaced_20260905/WHY_REPLACED.md.
#
# ---------------------------------------------------------------------------
# WHAT THE ORIGINAL PAPER DOES
# ---------------------------------------------------------------------------
# An edge server schedules transmissions among heterogeneous energy-harvesting
# mobile devices in a crowdsensing network AND sets each device's sensing period,
# so that end users receive status updates fresh enough for their requirements.
# The server cannot observe a device's battery level, so the problem is stated as
# a partially observable MDP. The objective is to minimise the weighted sum of
# the required AoI and the devices' energy consumption -- AoI is the optimisation
# target, not a reported side metric. The proposed method, HOORL, combines
# OFFLINE reinforcement learning on a previously collected dataset with ONLINE
# reinforcement learning that continues from it, which is what "Hybrid" names in
# the title. The offline stage is what lets the method cope with the sparse
# reward and with the mismatch between the sensing frequency and what users ask
# for; the online stage adapts the resulting policy to the live system.
#
# ---------------------------------------------------------------------------
# THE CORRESPONDENCE TO THIS PIPELINE
# ---------------------------------------------------------------------------
#   edge server                 -> our RSU (a single centralised decision maker)
#   heterogeneous devices       -> the in-range vehicles
#   transmission scheduling     -> the subchannel assignment
#   per-device sensing period   -> our silence interval Delta
#   device energy consumption   -> the transmit power term of our reward
#   unobservable battery level  -> the vehicle-internal state the RSU cannot see
#
# The last row is why the observation is NOT modified: the paper's partial
# observability comes from the server being unable to see inside a device, which
# is the same reason our RSU cannot see inside a vehicle. The 17-dimensional RSU
# observation vector is therefore used verbatim, exactly as every other baseline
# does. See librarian/baselines_v2.json, entry `xu2026`, for the full mapping and
# for the argument this comparison rests on.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION KEEPS
# ---------------------------------------------------------------------------
# * THE TWO-STAGE STRUCTURE. `phase` is either "offline" or "online" and
#   `update()` dispatches on it, so one model object carries both stages and the
#   handover happens inside it (`finish_offline_phase`). Implementing only the
#   online half would discard half of the paper's contribution, which is the very
#   thing that disqualified the method this baseline replaced.
# * The joint decision over (update period, transmission resource, energy), which
#   here is (Delta, subchannel, transmit power).
# * The AoI-and-energy objective, which our four-term interval reward already is.
#   Unlike the replaced baseline, no objective substitution is needed.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION CHANGES, AND WHY  (OUR EXTENSIONS)
# ---------------------------------------------------------------------------
# * CONTINUOUS Delta INSTEAD OF A DISCRETE PERIOD SET. The paper picks each
#   device's sensing period from a discrete candidate set; our Delta is
#   continuous over [0.1, 45] s. We reuse the pipeline's own geometric mapping
#   (`ActionDecoder.delta_from_unit`) so the policy emits a Delta in that range
#   directly, and read it as the silence interval until the next decision epoch.
#   The subchannel stays discrete (one of `num_channels`) and the power is
#   continuous over [10, 23] dBm.
# * A HYBRID MAXIMUM-ENTROPY ACTOR-CRITIC IS THE ONLINE LEARNER. The entry in
#   librarian/baselines_v2.json fixes the two-stage structure and the action
#   correspondence but does not name the online algorithm. An off-policy
#   actor-critic is the only family that can BOTH consume this pipeline's
#   uniformly sampled SMDP replay buffer AND be initialised from an offline
#   policy-plus-value pair, which is what the handover requires, so the choice is
#   forced by the interface rather than picked freely. It is nonetheless our
#   choice and must be reported as such.
#   The discrete factor is handled in expectation rather than by sampling: the
#   critic emits one Q value PER SUBCHANNEL given (state, continuous action), so
#   the channel expectation is exact and no Gumbel relaxation is involved.
# * IMPLICIT Q LEARNING IS THE OFFLINE LEARNER, AND THAT IS OUR CHOICE RATHER
#   THAN THE PAPER'S. See the next section, which is the one place this fact is
#   stated in full; `_offline_update_iql` repeats it so that nobody reading only
#   the method can miss it.
#
# ---------------------------------------------------------------------------
# THE OPEN POINT -- READ BEFORE USING THE OFFLINE STAGE
# ---------------------------------------------------------------------------
# WHICH offline reinforcement learning algorithm the original paper uses IS STILL
# NOT KNOWN. The article is closed access; the literature effort tried Semantic
# Scholar, Unpaywall, the IEEE Xplore document page, general web search and
# citation tracing, and all five failed to yield a copy. The abstract goes no
# further than "combines the advantages of offline and online reinforcement
# learning". So the question this section used to hold open has not been answered
# and cannot currently be answered.
#
# What changed is the decision, not the evidence. Leaving `offline_update()`
# raising means the two-stage structure -- the thing the title's "Hybrid" names,
# and the reason this baseline replaced the previous one -- can never actually
# run, which reduces HOORL to its online half and reintroduces exactly the defect
# that disqualified the replaced method. We therefore fixed an offline learner
# OURSELVES and label it as ours: implicit Q learning (Kostrikov, Nair and
# Levine, "Offline Reinforcement Learning with Implicit Q-Learning", ICLR 2022).
# The three reasons are given in `_offline_update_iql`'s docstring and belong in
# the manuscript verbatim.
#
# WHAT THIS MEANS FOR REPORTING. The comparison table entry is "the paper's
# two-stage offline-then-online framework, with an offline learner of our
# choosing because the original is unavailable", not "the paper's method". Any
# text that drops the qualifier is wrong. `offline_algorithm` is recorded in the
# checkpoint metadata precisely so a run states which learner produced it.
#
# The scaffolding around the hole was already complete and none of it moved:
#
#   * `offline_update()` still raises `OfflineAlgorithmNotSelected` unless
#     `offline_algorithm` names an implemented one. It has no default, so a
#     caller that wants the offline stage must ASK for "iql" by name; the
#     substitution can therefore never happen by accident.
#   * `finish_offline_phase()` and the checkpoint metadata record which algorithm
#     produced the initialisation, so a run cannot later be mistaken for a
#     differently pretrained one.
#   * Everything else -- the dataset format, the collection policy, the online
#     learner, the handover -- never depended on the answer.
#
# If the paper's offline learner is ever recovered and differs, implement it as a
# second method named `_offline_update_<key>` and add the key to
# `IMPLEMENTED_OFFLINE_ALGORITHMS`. Nothing else has to move then either.
# ============================================================================

from __future__ import annotations

import copy
import logging
import math
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM

logger = logging.getLogger(__name__)

#: The two stages of the paper's framework, in the order they run.
PHASES: Tuple[str, str] = ("offline", "online")

#: Offline algorithms this module can actually run. Adding a key here without
#: adding the matching `_offline_update_<key>` method makes `offline_update` fail
#: with an AttributeError, which is why membership is checked against the method
#: too.
#:
#: "iql" is OUR choice of offline learner, not one the source paper names -- see
#: the module header and `_offline_update_iql`. There is deliberately no default:
#: `offline_algorithm` starts at None, so the substitution has to be requested by
#: name and can never be entered by accident.
IMPLEMENTED_OFFLINE_ALGORITHMS: Tuple[str, ...] = ("iql",)

#: Numerical floor/ceiling for the tanh inverse. tanh saturates in float32 well
#: before |z| = 10, so a stored unit coordinate of exactly 0 or 1 would invert to
#: +-inf without this.
_ATANH_LIMIT: float = 1.0 - 1e-6


class OfflineAlgorithmNotSelected(NotImplementedError):
    """Raised when the offline stage runs before its algorithm has been fixed.

    A distinct type rather than a bare NotImplementedError so a caller can tell
    "the literature question is still open" apart from "this method is abstract".
    """


class HOORL(BaseRLModel):
    """
    Two-stage (offline then online) hybrid-action scheduler.

    Action representation. The actor emits a pre-squash Gaussian sample
    `z = (z_delta, z_power)` and `num_channels` channel logits. The unit
    coordinates are `u = (tanh(z) + 1) / 2`, which the decoder maps to the grant:
    Delta geometrically via `ActionDecoder.delta_from_unit`, power linearly over
    [p_min, p_max]. `raw_action` is serialised with `ActionDecoder.encode_action`,
    so any consumer that decodes it recovers exactly the grant that was issued,
    and `update()` inverts it with `BaseRLModel.raw_units` -- the canonical
    inversion, never re-derived here.

    Wiring flags. `offline_pretrained` and `behaviour_logp_stored` are
    CONDITIONAL and should average 1.0; the first is the whole reason this
    method is two-stage, and a run with it at 0 is the online-only ablation
    wearing this method's name. `phase_offline` is neither conditional nor
    periodic: it reports WHICH stage each update belonged to, so its window mean
    is the offline share of that window and is expected to fall from 1 to 0 once
    the offline stage closes.

    Contract notes that matter to the trainer:
      * `select_action` reports BOTH `action_idx` (the subchannel the discrete
        head chose) and `log_prob` (the joint behaviour log-probability at
        selection time), so `HotSwapRLScheduler.decide_grant` stores them and the
        replay batch carries both columns.
      * `update()` accepts exactly the batch `RetrospectiveReplayBuffer.sample`
        emits and reads no key outside it.
    """

    #: See the "Wiring flags" paragraph above. Both `update()` paths -- the
    #: offline one and the online one -- return all three, which is what lets a
    #: single window mean be read without knowing which stage produced it.
    WIRING_FLAG_KEYS: Tuple[str, ...] = (
        "offline_pretrained", "behaviour_logp_stored", "phase_offline",
    )

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 128,
        actor_lr: float = 3e-4,
        critic_lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        alpha: float = 0.05,
        offline_lr_scale: float = 1.0,
        offline_algorithm: Optional[str] = None,
        phase: str = "online",
        grad_clip: float = 0.5,
        log_std_min: float = -5.0,
        log_std_max: float = 2.0,
        iql_expectile: float = 0.7,
        iql_beta: float = 3.0,
        iql_adv_clip: float = 100.0,
        value_lr: Optional[float] = None,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.tau = float(tau)
        #: Temperature of the maximum-entropy term, shared by the continuous and
        #: the discrete factor. One scalar rather than two because the two
        #: entropies enter the same objective and a second free temperature would
        #: only be identifiable from data the offline stage does not have.
        self.alpha = float(alpha)
        self.grad_clip = float(grad_clip)
        self.log_std_min = float(log_std_min)
        self.log_std_max = float(log_std_max)
        #: Learning-rate multiplier applied while `phase == "offline"`. The
        #: offline stage sees a fixed dataset and typically wants a gentler step
        #: than the online stage; 1.0 leaves the two identical.
        self.offline_lr_scale = float(offline_lr_scale)
        self._actor_lr = float(actor_lr)
        self._critic_lr = float(critic_lr)

        # ------------------------------------------------------------------
        # Implicit-Q-learning hyper-parameters. Exposed as constructor arguments
        # rather than written into `_offline_update_iql` as literals, so `hpo.py`
        # can search them the way it searches every other model's; a number
        # buried in a method body is a number no search can reach. Each default
        # is the value the IQL paper reports for its locomotion suite, which is
        # the closest of its two regimes to ours: dense per-interval reward and a
        # behaviour policy that is mediocre rather than adversarially bad. The
        # antmaze settings (expectile 0.9, beta 10.0) are tuned for sparse
        # terminal reward and do not describe this problem.
        # ------------------------------------------------------------------
        #: Expectile of the asymmetric least-squares regression that fits V. At
        #: 0.5 this is plain least squares and V becomes the behaviour policy's
        #: value; as it approaches 1 the fit chases the maximum of Q over the
        #: actions the DATA contains, which is the in-sample stand-in for the max
        #: that ordinary Q learning would take over all actions. Must lie in
        #: (0, 1) and only values above 0.5 are meaningful for control.
        self.iql_expectile = float(iql_expectile)
        if not 0.0 < self.iql_expectile < 1.0:
            raise ValueError(f"iql_expectile must lie in (0, 1), got {self.iql_expectile}")
        #: Inverse temperature of the advantage weighting in the policy
        #: extraction step. 0 would make the extraction plain behaviour cloning;
        #: large values make it near-greedy on the advantage and high variance.
        self.iql_beta = float(iql_beta)
        if self.iql_beta < 0.0:
            raise ValueError(f"iql_beta must be non-negative, got {self.iql_beta}")
        #: Ceiling on the advantage weight exp(beta * A). The IQL reference
        #: implementation uses 100.0. It is a variance control, not a numerical
        #: patch: without it one transition with a large positive advantage can
        #: dominate the whole batch's regression.
        self.iql_adv_clip = float(iql_adv_clip)
        if self.iql_adv_clip <= 1.0:
            raise ValueError(f"iql_adv_clip must exceed 1.0, got {self.iql_adv_clip}")
        #: Learning rate of the state-value network. Defaults to the critic's,
        #: because V is fitted to the same targets the critics are and there is no
        #: reason to give it a different step size before evidence says so.
        self._value_lr = float(critic_lr if value_lr is None else value_lr)

        self.offline_algorithm = None if offline_algorithm is None else str(offline_algorithm)
        if phase not in PHASES:
            raise ValueError(f"phase must be one of {PHASES}, got {phase!r}")
        self.phase = str(phase)

        # Buffers, not plain ints: the hot-swap manager copies parameters and
        # buffers only, `update()` runs on the Rest model, and a plain counter
        # would neither cross a swap nor survive a checkpoint reload.
        self.register_buffer("total_updates", torch.zeros(1))
        self.register_buffer("offline_updates", torch.zeros(1))
        #: 1.0 once `finish_offline_phase()` has run. Recorded in the checkpoint
        #: so an online run started from scratch can never be mistaken for one
        #: that inherited an offline initialisation.
        self.register_buffer("offline_pretrained", torch.zeros(1))

        # ------------------------------------------------------------------
        # Actor: shared trunk, a Gaussian head over the two continuous factors
        # and a categorical head over the subchannel.
        # ------------------------------------------------------------------
        self.actor_trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.mean_head = nn.Linear(hidden_dim, 2)
        self.log_std_head = nn.Linear(hidden_dim, 2)
        self.channel_head = nn.Linear(hidden_dim, self.num_channels)

        # ------------------------------------------------------------------
        # Twin critics. Input is (state, u_delta, u_power); output is one Q per
        # subchannel, so the expectation over the discrete factor is exact.
        # ------------------------------------------------------------------
        self.critic_1 = self._build_critic(hidden_dim)
        self.critic_2 = self._build_critic(hidden_dim)
        self.critic_1_target = copy.deepcopy(self.critic_1)
        self.critic_2_target = copy.deepcopy(self.critic_2)
        for module in (self.critic_1_target, self.critic_2_target):
            for p in module.parameters():
                p.requires_grad = False

        self._actor_params = (
            list(self.actor_trunk.parameters())
            + list(self.mean_head.parameters())
            + list(self.log_std_head.parameters())
            + list(self.channel_head.parameters())
        )
        self._critic_params = list(self.critic_1.parameters()) + list(self.critic_2.parameters())

        # ------------------------------------------------------------------
        # State-value network V(s). The ONE component the offline stage needed
        # that the online stage did not already provide: implicit Q learning fits
        # it by expectile regression and then bootstraps the critics off V(s')
        # instead of off max_a Q(s', a), which is precisely how it avoids ever
        # evaluating an action the dataset does not contain.
        #
        # Built unconditionally rather than lazily on the first offline update,
        # for two reasons that are both about this pipeline rather than about
        # IQL. `HotSwapTrainer` copies parameters and buffers between the Act and
        # the Rest model, and a module that appears on one of them partway
        # through training would make the two copies structurally different.
        # `BaseRLModel.load` is strict, so the set of state-dict keys has to be a
        # property of the class and not of how far a run has got. Online-only
        # runs therefore carry an untrained V that no online code path reads,
        # which costs a few thousand parameters and nothing else.
        # ------------------------------------------------------------------
        self.value_net = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self._value_params = list(self.value_net.parameters())

        self._build_optimizers()
        # Kept OUT of `_build_optimizers`. That method is rebuilt at the offline
        # -> online handover in order to discard the offline moment estimates, and
        # V is not used online at all, so rebuilding its optimiser there would be
        # meaningless work on a network nothing will read again. The offline
        # learning-rate scale is applied here once and then re-asserted at the
        # start of every offline step by `_apply_offline_lr_scale`.
        self.value_optimizer = optim.Adam(
            self._value_params, lr=self._value_lr * self.offline_lr_scale
        )

    # ----------------------------------------------------------------------
    # Construction helpers
    # ----------------------------------------------------------------------
    def _build_critic(self, hidden_dim: int) -> nn.Module:
        return nn.Sequential(
            nn.Linear(self.state_dim + 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, self.num_channels),
        )

    def _build_optimizers(self) -> None:
        """(Re)create the optimisers at the learning rate the current phase wants.

        Called at construction and again at the offline -> online handover. The
        moment estimates are deliberately NOT carried across the handover: they
        were accumulated on a fixed dataset under a different objective, and
        reusing them would let the offline gradient statistics steer the first
        online steps.
        """
        scale = self.offline_lr_scale if self.phase == "offline" else 1.0
        self.actor_optimizer = optim.Adam(self._actor_params, lr=self._actor_lr * scale)
        self.critic_optimizer = optim.Adam(self._critic_params, lr=self._critic_lr * scale)
        #: Alias so generic tooling that expects a single `optimizer` still works.
        self.optimizer = self.critic_optimizer

    # ----------------------------------------------------------------------
    # Policy
    # ----------------------------------------------------------------------
    def _policy(self, states: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """states -> (mean, log_std, channel logits), all pre-squash."""
        h = self.actor_trunk(states)
        mean = self.mean_head(h)
        log_std = self.log_std_head(h).clamp(self.log_std_min, self.log_std_max)
        return mean, log_std, self.channel_head(h)

    @staticmethod
    def _gaussian_log_prob(z: torch.Tensor, mean: torch.Tensor, log_std: torch.Tensor) -> torch.Tensor:
        """log N(z; mean, exp(log_std)), summed over the continuous factors."""
        var = torch.exp(2.0 * log_std)
        lp = -0.5 * ((z - mean) ** 2 / var + 2.0 * log_std + math.log(2.0 * math.pi))
        return lp.sum(dim=-1, keepdim=True)

    @staticmethod
    def _squash_correction(z: torch.Tensor) -> torch.Tensor:
        """Log absolute Jacobian of z -> u = (tanh(z) + 1) / 2, summed.

        d u / d z = (1 - tanh(z)^2) / 2, so the correction subtracted from the
        Gaussian log density is sum(log(1 - tanh(z)^2) - log 2). Written through
        `softplus` in the numerically stable form
        log(1 - tanh(z)^2) = 2 * (log 2 - z - softplus(-2z)).
        """
        stable = 2.0 * (math.log(2.0) - z - F.softplus(-2.0 * z))
        return (stable - math.log(2.0)).sum(dim=-1, keepdim=True)

    def _continuous_log_prob(
        self, z: torch.Tensor, mean: torch.Tensor, log_std: torch.Tensor
    ) -> torch.Tensor:
        """log density of the SQUASHED continuous action u, given its pre-squash z."""
        return self._gaussian_log_prob(z, mean, log_std) - self._squash_correction(z)

    @staticmethod
    def _units_from_z(z: torch.Tensor) -> torch.Tensor:
        """Pre-squash sample -> unit coordinates in (0, 1)."""
        return 0.5 * (torch.tanh(z) + 1.0)

    @staticmethod
    def _z_from_units(u: torch.Tensor) -> torch.Tensor:
        """Unit coordinates -> pre-squash value. Exact inverse of `_units_from_z`.

        Used to recover the pre-squash sample of a REPLAYED action, whose raw
        form stores only the unit coordinate. The clamp is what keeps a stored
        0.0 or 1.0 -- produced by `ActionDecoder`'s own 1e-6 logit clamp -- from
        inverting to an infinity that would poison the whole batch.
        """
        return torch.atanh((2.0 * u.clamp(0.0, 1.0) - 1.0).clamp(-_ATANH_LIMIT, _ATANH_LIMIT))

    def _sample_policy(
        self, states: torch.Tensor, deterministic: bool = False
    ) -> Dict[str, torch.Tensor]:
        """One reparameterised draw of the hybrid policy at `states`.

        Returns the continuous unit action, its log density, the channel
        log-probabilities and the channel distribution's entropy. The discrete
        factor is NOT sampled here: the caller takes its expectation against
        `channel_probs`, which is exact and lower-variance than a sample.
        """
        mean, log_std, ch_logits = self._policy(states)
        if deterministic:
            z = mean
        else:
            z = mean + torch.randn_like(mean) * torch.exp(log_std)
        return {
            "u": self._units_from_z(z),
            "z": z,
            "cont_log_prob": self._continuous_log_prob(z, mean, log_std),
            "channel_log_probs": F.log_softmax(ch_logits, dim=-1),
            "channel_probs": F.softmax(ch_logits, dim=-1),
            "channel_logits": ch_logits,
        }

    # ----------------------------------------------------------------------
    # Batch helpers
    # ----------------------------------------------------------------------
    def _resolve_channel_indices(
        self, batch: Dict[str, torch.Tensor], device: torch.device
    ) -> torch.Tensor:
        """
        Discrete credit assignment. Preferred path: the verbatim "action_idx" the
        replay buffer carries. Fallback for transitions that predate it:
        `raw_action[1]`, which stores the same subchannel index, so the fallback
        is exact rather than lossy. Identical in form to I-HAMAPPO's, on purpose:
        the two must not disagree about what `action_idx` means.
        """
        if "action_idx" in batch:
            idx = batch["action_idx"].to(device=device).long().reshape(-1)
        else:
            idx = batch["action"][:, 1].to(device=device).round().long().reshape(-1)
        return ((idx % self.num_channels) + self.num_channels) % self.num_channels

    def _replay_units(self, actions: torch.Tensor) -> torch.Tensor:
        """Raw replay actions (N, 3) -> the critic's continuous input (N, 2).

        Goes through `BaseRLModel.raw_units`, the canonical inverse of
        `ActionDecoder.encode_action`. Three baselines once inverted the Delta
        field linearly and conditioned their critics on an action the actor had
        never taken; that algebra exists in exactly one place and this is not it.
        """
        u_delta, u_power = self.raw_units(actions)
        return torch.stack([u_delta, u_power], dim=1)

    def _q_values(
        self, states: torch.Tensor, units: torch.Tensor, use_target: bool = False
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """(B, state) x (B, 2) -> two (B, num_channels) Q tables."""
        x = torch.cat([states, units], dim=1)
        if use_target:
            return self.critic_1_target(x), self.critic_2_target(x)
        return self.critic_1(x), self.critic_2(x)

    # ----------------------------------------------------------------------
    # Phase control -- the "hybrid" of the paper's title lives here
    # ----------------------------------------------------------------------
    def set_phase(self, phase: str) -> None:
        """Switch the stage `update()` dispatches to, rebuilding the optimisers."""
        if phase not in PHASES:
            raise ValueError(f"phase must be one of {PHASES}, got {phase!r}")
        if phase == self.phase:
            return
        self.phase = str(phase)
        self._build_optimizers()

    def finish_offline_phase(self) -> Dict[str, float]:
        """Hand the offline result over to the online stage.

        This is the join the paper's "Hybrid" refers to, so it is one explicit
        call rather than an implicit side effect. Three things happen and each
        matters:

          1. The target critics are synchronised HARD with the online critics, so
             the online stage bootstraps from the values the offline stage
             actually learned rather than from a Polyak average that still
             carries the random initialisation.
          2. The optimisers are rebuilt at the online learning rate WITHOUT the
             offline moment estimates (see `_build_optimizers`).
          3. `offline_pretrained` is set, so a checkpoint records that this policy
             inherited an offline initialisation and from which algorithm.

        Returns a small summary for the run log. Calling it having done no
        offline update at all is allowed but warned about, because that produces
        a model that IS the online-only ablation while still being named HOORL.
        """
        if float(self.offline_updates.item()) <= 0.0:
            logger.warning(
                "HOORL.finish_offline_phase() called after 0 offline updates. The "
                "resulting policy is the online-only ablation, not the paper's "
                "hybrid method; do not report it under the method's name."
            )
        with torch.no_grad():
            self.critic_1_target.load_state_dict(self.critic_1.state_dict())
            self.critic_2_target.load_state_dict(self.critic_2.state_dict())
            self.offline_pretrained.fill_(1.0)
        self.phase = "online"
        self._build_optimizers()
        return {
            "offline_updates": float(self.offline_updates.item()),
            "offline_pretrained": float(self.offline_pretrained.item()),
        }

    # ----------------------------------------------------------------------
    # BaseRLModel contract
    # ----------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            out = self._sample_policy(state_t, deterministic=bool(deterministic))
            u = out["u"][0]
            ch_log_probs = out["channel_log_probs"][0]
            if deterministic:
                ch = int(torch.argmax(ch_log_probs).item())
            else:
                ch = int(torch.multinomial(ch_log_probs.exp(), 1).item())
            # Joint behaviour log-probability of the action actually emitted:
            # the squashed-Gaussian density of the continuous factors plus the
            # categorical log-probability of the chosen subchannel. This is the
            # denominator every importance ratio downstream needs, and it is
            # knowable only here.
            log_prob = float(out["cont_log_prob"][0].item() + ch_log_probs[ch].item())

        u_delta, u_power = float(u[0].item()), float(u[1].item())
        delta = float(self.decoder.delta_from_unit(u_delta))
        power = float(self.decoder.p_min + u_power * (self.decoder.p_max - self.decoder.p_min))
        raw_action = self.decoder.encode_action(delta, ch, power)

        info: Dict[str, Any] = {
            "action_idx": int(ch),
            "channel_idx": int(ch),
            "u_delta": u_delta,
            "u_power": u_power,
            "log_prob": log_prob,
            "phase": self.phase,
            "raw_action": raw_action,
        }
        return (delta, int(ch), power), raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """Dispatch one gradient step to the stage this model is currently in."""
        if self.phase == "offline":
            return self.offline_update(batch)
        return self.online_update(batch)

    # ----------------------------------------------------------------------
    # Offline stage -- INTERFACE ONLY. See the module header.
    # ----------------------------------------------------------------------
    def offline_update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """One offline gradient step on a batch drawn from the logged dataset.

        Dispatches to `_offline_update_<offline_algorithm>`. The only implemented
        key is "iql", and it is OUR choice of offline learner rather than one the
        source paper names, because the source paper is unavailable; see the
        module header and `_offline_update_iql` for the full statement of that.

        `offline_algorithm` has no default, so this raises
        `OfflineAlgorithmNotSelected` until a caller names a learner. That is
        intentional and is what keeps the substitution from being entered by
        accident: an offline stage that ran a learner nobody asked for would be
        indistinguishable, in the checkpoint and in the results table, from one
        the paper prescribed.
        """
        key = self.offline_algorithm
        method = getattr(self, f"_offline_update_{key}", None) if key else None
        if key is None or key not in IMPLEMENTED_OFFLINE_ALGORITHMS or method is None:
            raise OfflineAlgorithmNotSelected(
                "HOORL's offline stage was entered without naming an offline learner "
                f"(offline_algorithm={key!r}, implemented="
                f"{list(IMPLEMENTED_OFFLINE_ALGORITHMS)}). The source paper's own offline "
                "learner is still unknown -- the article is closed access and no copy was "
                "obtainable -- so this argument has no default on purpose: pass "
                "offline_algorithm='iql' to accept the substitute learner documented in "
                "`_offline_update_iql`, which is ours and must be reported as ours."
            )
        out = method(batch)
        self.offline_updates.add_(1.0)
        return out

    def _apply_offline_lr_scale(self) -> Dict[str, float]:
        """Force all three offline learning rates to base * `offline_lr_scale`.

        WHICH OPTIMISERS THE SCALE APPLIES TO: ALL THREE. Implicit Q learning
        fits a state value, two critics and a policy, and all three fits are
        offline-stage fits made against the same fixed dataset. Scaling only some
        of them would not make the offline stage gentler, it would change the
        RATIO between the three learning rates, which changes the balance of the
        algorithm rather than the size of its steps -- and it would leave anyone
        reading a search result unable to say which of the two the number meant.
        A single scale on all three keeps the argument's meaning exactly what its
        name says: the offline stage's step size relative to the online stage's.

        WHY THIS IS RE-ASSERTED HERE AND NOT LEFT TO `_build_optimizers`. That
        method applies the scale when it runs, and it runs only at construction
        and at a phase change. Two of the three optimisers therefore carry the
        right rate only if the phase was set the way the intended path sets it.
        The value optimiser, which lives outside that method, carries the scale
        unconditionally. So a model constructed at `phase="online"` and driven
        into an offline update without `set_phase` would step V at the offline
        rate while stepping the actor and the critics at the online rate -- a
        silent disagreement between the three, and not one any test of the
        constructor could see.

        Re-asserting the invariant at the point of USE closes that gap and, more
        importantly, keeps it closed: `offline_lr_scale` is a searched
        hyper-parameter, and this project has already published an Optuna optimum
        for a learning rate the model never applied. Three float assignments per
        update is the price of that not happening again. Returns the rates
        actually in force so the caller can report them.
        """
        rates = {
            "actor_lr": self._actor_lr * self.offline_lr_scale,
            "critic_lr": self._critic_lr * self.offline_lr_scale,
            "value_lr": self._value_lr * self.offline_lr_scale,
        }
        for optimizer, lr in (
            (self.actor_optimizer, rates["actor_lr"]),
            (self.critic_optimizer, rates["critic_lr"]),
            (self.value_optimizer, rates["value_lr"]),
        ):
            for group in optimizer.param_groups:
                group["lr"] = lr
        return rates

    def _offline_update_iql(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """One implicit-Q-learning step. THE ALGORITHM IS OUR CHOICE, NOT THE PAPER'S.

        ------------------------------------------------------------------
        READ THIS BEFORE CITING ANY NUMBER THIS METHOD PRODUCES
        ------------------------------------------------------------------
        Which offline reinforcement learning algorithm J. Xu et al. use in the
        first stage of HOORL is NOT KNOWN to us. The article is closed access;
        Semantic Scholar, Unpaywall, the IEEE Xplore document page, general web
        search and citation tracing were all tried and none produced a copy, and
        the abstract says only that the method "combines the advantages of
        offline and online reinforcement learning". Implicit Q learning
        (Kostrikov, Nair and Levine, ICLR 2022) is therefore OUR substitution.
        It is not what the paper claims, it may not be what the paper does, and
        every report of this baseline has to carry that qualifier.

        ------------------------------------------------------------------
        WHY IQL AND NOT SOMETHING ELSE -- the three reasons, which belong in the
        manuscript
        ------------------------------------------------------------------
        1. IT NEVER QUERIES AN OUT-OF-DISTRIBUTION ACTION. The value target is an
           expectile of Q AT THE ACTIONS THE DATA CONTAINS, never a maximum over
           actions the data does not contain, so the offline stage learns
           entirely inside the dataset's support. That makes the offline-to-
           online handover smooth, and that handover is exactly the join the
           title's "Hybrid" names. An offline learner whose values are
           extrapolated off-support hands the online stage a critic that is
           confidently wrong about the first thing the online policy tries.

        2. OUR OFFLINE DATASET IS NARROW ALONG THE STATE AXIS, WHICH IS THE AXIS
           THAT MATTERS HERE. The logging policy (`hoorl_offline.
           FixedPeriodBehaviourPolicy`) holds Delta at one fixed value and draws
           only the subchannel and the power at random, so the ACTION coverage is
           broad but the STATE coverage is confined to the trajectory distribution
           that one fixed silence interval induces. The online stage runs a policy
           that varies Delta with the situation and therefore immediately visits
           states the offline data never contained. A learner that does not
           extrapolate off-support degrades gracefully when that happens; one that
           does extrapolate carries its errors straight into the transition.

        3. THE ALTERNATIVES ARE EACH WORSE FOR THIS SPECIFIC HANDOVER.
           Conservative Q learning's pessimism penalty is known to suppress
           exploration during online fine-tuning, which is a direct cost to a
           method whose whole point is that the online stage continues from the
           offline one. Behaviour cloning would imitate a logging policy that is
           deliberately mediocre -- uniform channel and power at a fixed Delta --
           and hand the online stage a bad initialisation rather than a useful
           one. TD3+BC assumes a purely continuous action space; our action is
           hybrid, and bolting a separate treatment of the discrete factor onto
           it would leave us reporting something that is no longer TD3+BC.

        ------------------------------------------------------------------
        THE THREE LOSSES, AND THE SMDP CORRECTION
        ------------------------------------------------------------------
        All three are computed from ONE snapshot of the value parameters, taken
        before any optimiser steps, which is what the reference implementation's
        single fused step does. Doing otherwise would make the advantage used for
        policy extraction inconsistent with the value that defined it.

          V step. Expectile regression of V(s) onto min(Q1_target, Q2_target)
            evaluated at the DATASET action. The asymmetric weight
            |expectile - 1[u < 0]| on the squared residual u = Q - V pushes V
            towards the upper expectile of the in-sample Q distribution, i.e.
            towards the best of what the data did rather than the best of what is
            imaginable.

          Q step. Ordinary temporal-difference regression, but bootstrapped off
            V(s') rather than off any Q(s', a'). This is the step where the
            absence of an out-of-distribution query is actually purchased.

          Policy step. Advantage-weighted regression: maximise
            exp(beta * A) * log pi(a | s) on the dataset action, with
            A = min(Q1_target, Q2_target)(s, a) - V(s). The log density is the
            JOINT one -- the squashed-Gaussian density of (Delta, power) plus the
            categorical log-probability of the subchannel -- recovered from the
            stored raw action through `BaseRLModel.raw_units` and
            `_z_from_units`, never re-derived here.

        SMDP. The decision interval varies, so the discount is gamma ** delta_t
        with delta_t in seconds, supplied per transition by
        `BaseRLModel.smdp_discounts` from THIS model's own gamma. A constant
        gamma would value a 45-second silence the same as a 0.1-second one and
        would misprice exactly the long intervals this scheduler exists to
        choose between. Only the Q step discounts; the V and policy steps are
        both within a single decision epoch and carry no discount.

        `batch["behaviour_log_prob"]` is deliberately NOT consumed. IQL forms no
        importance ratio, so it needs no denominator, and that is a fourth point
        in its favour here: the stored behaviour density omits the Delta factor
        whenever the logging policy's `delta_jitter` is 0, because a point mass
        has no Lebesgue density, so any ratio built from it would be a ratio over
        a subset of the action's factors. The column is only reported on, as a
        flag, so a reader can see it was available and unused.

        LEARNING RATE. Every step below runs at its base rate multiplied by
        `offline_lr_scale`, applied to the value, the critic AND the actor
        optimiser alike; `_apply_offline_lr_scale` states why all three and why
        the invariant is asserted here rather than trusted from construction. The
        rates actually in force are returned in the loss dict, so a search result
        can be read against the rate that produced it instead of against the rate
        that was requested.
        """
        # Asserted before any step, not after: `offline_lr_scale` is searched, and
        # a searched value that does not reach the update is the failure this
        # project has already reported an optimum for once.
        offline_rates = self._apply_offline_lr_scale()

        device = next(self.parameters()).device
        states = batch["state"].to(device).float()
        next_states = batch["next_state"].to(device).float()
        rewards = batch["reward"].to(device).float()
        dones = batch["done"].to(device).float()

        # Variable-interval discount, from this model's gamma (see the docstring).
        discounts = self.smdp_discounts(batch, rewards)

        units = self._replay_units(batch["action"].to(device))
        channels = self._resolve_channel_indices(batch, device)
        idx = channels.reshape(-1, 1)

        # -- One snapshot of the pre-update quantities every step below reads ---
        with torch.no_grad():
            q1_t, q2_t = self._q_values(states, units, use_target=True)
            # The twin minimum at the dataset action. In-sample by construction:
            # `units` and `channels` both come out of the replay row.
            q_target_taken = torch.min(q1_t, q2_t).gather(1, idx)
            v_next = self.value_net(next_states)

        # -- 1. Value: expectile regression --------------------------------------
        v = self.value_net(states)
        residual = q_target_taken - v
        # |tau - 1[u < 0]|: weight tau on the residuals where Q exceeds V and
        # (1 - tau) on the rest, so tau > 0.5 leans the fit upward.
        expectile_weight = torch.abs(
            self.iql_expectile - (residual < 0.0).to(residual.dtype)
        )
        value_loss = (expectile_weight * residual.pow(2)).mean()

        self.value_optimizer.zero_grad()
        value_loss.backward()
        nn.utils.clip_grad_norm_(self._value_params, self.grad_clip)
        self.value_optimizer.step()

        # -- 2. Critics: TD regression bootstrapped off V(s') ---------------------
        with torch.no_grad():
            y = rewards + (1.0 - dones) * discounts * v_next

        q1, q2 = self._q_values(states, units, use_target=False)
        q1_taken = q1.gather(1, idx)
        q2_taken = q2.gather(1, idx)
        critic_loss = F.mse_loss(q1_taken, y) + F.mse_loss(q2_taken, y)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self._critic_params, self.grad_clip)
        self.critic_optimizer.step()

        # -- 3. Policy: advantage-weighted regression -----------------------------
        with torch.no_grad():
            advantage = q_target_taken - v.detach()
            # Clamp the EXPONENT, not only its image. exp of a few hundred is inf
            # in float32, and an inf weight multiplied by a finite log density
            # produces the NaN loss that has already killed two models in this
            # project. Bounding the exponent by log(clip) makes the ceiling
            # exact and the intermediate finite.
            exp_advantage = torch.exp(
                (self.iql_beta * advantage).clamp(max=math.log(self.iql_adv_clip))
            )

        mean, log_std, ch_logits = self._policy(states)
        # Pre-squash coordinate of the action that was actually logged. The
        # clamp inside `_z_from_units` is what stops a stored unit coordinate
        # that saturated to exactly 0 or 1 from inverting to an infinity.
        z_data = self._z_from_units(units)
        cont_log_prob = self._continuous_log_prob(z_data, mean, log_std)
        ch_log_probs = F.log_softmax(ch_logits, dim=-1)
        log_pi_data = cont_log_prob + ch_log_probs.gather(1, idx)
        actor_loss = -(exp_advantage * log_pi_data).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self._actor_params, self.grad_clip)
        self.actor_optimizer.step()

        # -- Polyak target update -------------------------------------------------
        # The offline stage moves the targets exactly as the online stage does, so
        # the expectile regression in step 1 tracks the critics it is fitted to.
        # `finish_offline_phase` then hard-synchronises them at the handover.
        with torch.no_grad():
            for online, target in (
                (self.critic_1, self.critic_1_target),
                (self.critic_2, self.critic_2_target),
            ):
                for p, pt in zip(online.parameters(), target.parameters()):
                    pt.data.copy_(self.tau * p.data + (1.0 - self.tau) * pt.data)

        self.total_updates.add_(1.0)

        with torch.no_grad():
            ch_probs = ch_log_probs.exp()
            ch_entropy = -(ch_probs * ch_log_probs).sum(dim=1).mean()
            normalised_entropy = float(ch_entropy.item() / math.log(max(2, self.num_channels)))
            stored_logp = self.stored_behaviour_log_prob(batch, rewards)

        return {
            "loss": float(value_loss.item() + critic_loss.item() + actor_loss.item()),
            "value_loss": float(value_loss.item()),
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "mean_q": float(q1_taken.mean().item()),
            "mean_v": float(v.mean().item()),
            "target_mean": float(y.mean().item()),
            "advantage_mean": float(advantage.mean().item()),
            # Fraction of the batch sitting on the weight ceiling. A value near 1
            # means `iql_beta` is too large for this advantage scale and the
            # regression has collapsed onto a handful of transitions; near 0 with
            # a tiny spread means it is too small and the extraction is drifting
            # towards plain behaviour cloning. Neither is visible from the loss.
            "adv_weight_mean": float(exp_advantage.mean().item()),
            "adv_weight_clipped_frac": float(
                (exp_advantage >= self.iql_adv_clip * (1.0 - 1e-6)).float().mean().item()
            ),
            # Log density the CURRENT policy assigns to the logged action. It
            # should rise while the extraction runs; if it collapses, the policy
            # has walked away from the data the critics were fitted on.
            "log_pi_data": float(log_pi_data.mean().item()),
            "channel_entropy": normalised_entropy,
            # Available but unused by IQL, on purpose. See the docstring.
            "behaviour_logp_stored": float(stored_logp is not None),
            "offline_pretrained": float(self.offline_pretrained.item()),
            "phase_offline": 1.0,
            # The rates this step ACTUALLY ran at, and the multiplier that
            # produced them. Reported rather than assumed so that a trial's log
            # shows whether the searched `offline_lr_scale` reached the update.
            "offline_lr_scale": float(self.offline_lr_scale),
            "offline_actor_lr": float(offline_rates["actor_lr"]),
            "offline_critic_lr": float(offline_rates["critic_lr"]),
            "offline_value_lr": float(offline_rates["value_lr"]),
        }

    def pretrain(
        self,
        dataset: Any,
        num_updates: int,
        batch_size: int = 256,
        log_every: int = 0,
    ) -> Dict[str, float]:
        """Run the offline stage over `dataset`, then hand over to the online one.

        `dataset` only has to expose `sample(batch_size) -> dict` with the same
        keys `RetrospectiveReplayBuffer.sample` emits;
        `src.hoorl_offline.OfflineDataset` does. The loop is written here rather
        than in the collection module so that the phase bookkeeping and the
        handover stay inside the model that owns them.

        Raises `OfflineAlgorithmNotSelected` on the first batch until the offline
        algorithm is fixed. That is the intended behaviour: a silent no-op would
        produce a checkpoint that claims a pretraining that never happened.
        """
        self.set_phase("offline")
        last: Dict[str, float] = {}
        for step in range(int(num_updates)):
            last = self.offline_update(dataset.sample(int(batch_size)))
            if log_every and (step + 1) % int(log_every) == 0:
                logger.info("HOORL offline update %d/%d: %s", step + 1, num_updates, last)
        summary = self.finish_offline_phase()
        summary.update({f"final_{k}": v for k, v in last.items()})
        return summary

    # ----------------------------------------------------------------------
    # Online stage -- hybrid maximum-entropy actor-critic
    # ----------------------------------------------------------------------
    def online_update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        device = next(self.parameters()).device
        states = batch["state"].to(device).float()
        next_states = batch["next_state"].to(device).float()
        rewards = batch["reward"].to(device).float()
        dones = batch["done"].to(device).float()

        # SMDP discount from THIS model's gamma (see BaseRLModel.smdp_discounts).
        discounts = self.smdp_discounts(batch, rewards)

        units = self._replay_units(batch["action"].to(device))
        channels = self._resolve_channel_indices(batch, device)

        # -- Critic target -----------------------------------------------------
        with torch.no_grad():
            nxt = self._sample_policy(next_states, deterministic=False)
            q1_t, q2_t = self._q_values(next_states, nxt["u"], use_target=True)
            q_t = torch.min(q1_t, q2_t)
            ch_probs = nxt["channel_probs"]
            ch_log_probs = nxt["channel_log_probs"]
            # Exact expectation over the discrete factor, minus its entropy
            # bonus; then the continuous factor's entropy bonus, which does not
            # depend on the channel and so leaves the expectation.
            v_next = (ch_probs * (q_t - self.alpha * ch_log_probs)).sum(dim=1, keepdim=True)
            v_next = v_next - self.alpha * nxt["cont_log_prob"]
            y = rewards + (1.0 - dones) * discounts * v_next

        q1, q2 = self._q_values(states, units, use_target=False)
        idx = channels.reshape(-1, 1)
        q1_taken = q1.gather(1, idx)
        q2_taken = q2.gather(1, idx)
        critic_loss = F.mse_loss(q1_taken, y) + F.mse_loss(q2_taken, y)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self._critic_params, self.grad_clip)
        self.critic_optimizer.step()

        # -- Actor update ------------------------------------------------------
        cur = self._sample_policy(states, deterministic=False)
        q1_pi, q2_pi = self._q_values(states, cur["u"], use_target=False)
        q_pi = torch.min(q1_pi, q2_pi)
        ch_probs = cur["channel_probs"]
        ch_log_probs = cur["channel_log_probs"]
        actor_objective = (ch_probs * (q_pi - self.alpha * ch_log_probs)).sum(dim=1, keepdim=True)
        actor_objective = actor_objective - self.alpha * cur["cont_log_prob"]
        actor_loss = -actor_objective.mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self._actor_params, self.grad_clip)
        self.actor_optimizer.step()

        # -- Polyak target update ---------------------------------------------
        with torch.no_grad():
            for online, target in (
                (self.critic_1, self.critic_1_target),
                (self.critic_2, self.critic_2_target),
            ):
                for p, pt in zip(online.parameters(), target.parameters()):
                    pt.data.copy_(self.tau * p.data + (1.0 - self.tau) * pt.data)

        self.total_updates.add_(1.0)

        with torch.no_grad():
            ch_entropy = -(ch_probs * ch_log_probs).sum(dim=1).mean()
            normalised_entropy = float(ch_entropy.item() / math.log(max(2, self.num_channels)))
            stored_logp = self.stored_behaviour_log_prob(batch, rewards)

        return {
            "loss": float(critic_loss.item() + actor_loss.item()),
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "mean_q": float(q1_taken.mean().item()),
            "target_mean": float(y.mean().item()),
            "cont_log_prob": float(cur["cont_log_prob"].mean().item()),
            # Normalised so 1.0 is uniform over subchannels and 0.0 is a collapse.
            # This policy has no epsilon-greedy fallback, so a collapse has to be
            # visible in the log rather than inferred afterwards.
            "channel_entropy": normalised_entropy,
            "behaviour_logp_stored": float(stored_logp is not None),
            "offline_pretrained": float(self.offline_pretrained.item()),
            "phase_offline": 0.0,
        }
