# src/baselines/maddpg_mt.py
# ============================================================================
# MADDPG-MT -- AoI-Aware Multi-Agent Multi-Task Deep Deterministic Policy Gradient
#
# M. Parvini, M. R. Javan, N. Mokari, B. Abbasi and E. A. Jorswieck, "AoI-Aware
# Resource Allocation for Platoon-Based C-V2X Networks via Multi-Agent Multi-Task
# Reinforcement Learning," IEEE Transactions on Vehicular Technology, vol. 72,
# no. 8, pp. 9880--9896, 2023. DOI: 10.1109/TVT.2023.3259688
#
# ---------------------------------------------------------------------------
# WHAT THE ORIGINAL PAPER DOES
# ---------------------------------------------------------------------------
# Parvini et al. do AoI-aware radio resource management for C-V2X PLATOONING.
# Each agent is a platoon leader; its observation is a per-platoon-leader local
# view and its action is a per-link (sub-band, power) pair for CAM dissemination
# over intra-platoon V2V links. Two MADDPG variants are proposed:
#   (1) Modified MADDPG -- a GLOBAL critic (to induce cooperation) trained
#       alongside a per-agent EXCLUSIVE LOCAL critic; and
#   (2) Modified MADDPG with TASK DECOMPOSITION -- each agent's holistic reward
#       is split into sub-rewards and a task-wise value function is learned for
#       each, so one head is never asked to explain heterogeneous penalties with
#       a single scalar.
# This module implements variant (2), which is the paper's headline method.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION KEEPS
# ---------------------------------------------------------------------------
# * The dual-critic structure: an exclusive LOCAL critic on the agent's own
#   (observation, action) and a GLOBAL critic that additionally sees the other
#   in-range agents, with the actor gradient taken through a convex combination
#   of the two (`global_critic_weight`).
# * TASK DECOMPOSITION, which is why this paper was selected: our reward is
#   literally a weighted sum of four heterogeneous penalties, so each gets its
#   own value head. The mapping is 1:1 with the pipeline's reward terms
#   (src/hot_swap_trainer.py):
#       head 0 <- e^2         normalised squared estimation error
#       head 1 <- P_tx        normalised transmit power
#       head 2 <- C_freq      normalised channel congestion (CBR)
#       head 3 <- I_redundant binary redundant-update indicator
#   The scalar action-value is the sum over heads, so Q = sum_m Q_m matches
#   r = sum_m r_m.
# * The DDPG machinery: deterministic actor, target actor and target critics,
#   Polyak averaging, exploration noise at acting time.
# * CTDE. All actors and critics execute at the RSU. Our scheduler is centralised
#   at a single RSU by construction, so the "centralised critic" is a description
#   of the real deployment, not an extra assumption bolted on for training.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION DROPS OR ADDS, AND WHY
# ---------------------------------------------------------------------------
# * THE ENTIRE PLATOON STRUCTURE IS DROPPED: platoon leaders, the leader/follower
#   hierarchy, intra-platoon V2V links and the CAM dissemination model. Our SUMO
#   scenario is unstructured urban traffic at a signalised intersection; there
#   are no platoons and no intra-platoon links to allocate. Agents therefore
#   become the individual in-range vehicles. Nothing in the learner depends on
#   the dropped structure, but the paper's cooperation story ("followers benefit
#   from the leader's allocation") has no analogue here, so the global critic has
#   less structured cooperation to discover than it does in the paper.
# * VARIABLE AGENT COUNT IS OUR ADDITION, NOT IN THE ORIGINAL PAPER. Parvini et
#   al. assume a fixed number of platoons, so their global critic can take a
#   fixed-width concatenation. Our agent population changes continuously as
#   vehicles enter and leave the 300 m RSU range. We solve it with a
#   PERMUTATION-INVARIANT POOLING ENCODER (DeepSets style): every other in-range
#   agent's observation is embedded by a shared encoder, then masked mean- and
#   max-pooled into a fixed-width context that the global critic consumes. This
#   is both order- and cardinality-invariant, so no padding artefact can leak
#   into the value estimate. A validity mask is still accepted so a caller may
#   pad the tensor to a fixed N.
# * The discrete subchannel is an extra action factor relative to the paper's
#   sub-band index only in name; it is handled with a straight-through
#   Gumbel-Softmax so the actor gradient can flow through the critic's action
#   input, which a hard argmax would block.
#
# ---------------------------------------------------------------------------
# WEAKENING ADAPTATIONS -- STATED PLAINLY
# ---------------------------------------------------------------------------
# * The task decomposition is only ACTIVE when the batch carries per-term rewards
#   under `batch["reward_terms"]` with shape (B, num_tasks) in the order above.
#   The current pipeline (hot_swap_trainer.TransitionStreamer) streams a single
#   scalar reward, so unless that is plumbed through, the four heads are trained
#   on `task_weights * r` -- their sum is still exactly r, but the heads become
#   copies of one another and the paper's central contribution is INERT. This is
#   a genuine weakening and must not be reported as "task decomposition enabled".
# * Likewise the global critic only sees other agents when the batch carries
#   `batch["others"]` of shape (B, N, state_dim) (optionally with
#   `batch["others_mask"]`, shape (B, N)). Without it the pooled context is the
#   zero vector and the global critic degenerates to a second local critic, which
#   removes the cooperation signal entirely. Both keys are optional so that the
#   model still satisfies the standard batch contract.
# ============================================================================

from __future__ import annotations
import copy
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM

#: Order of the task heads; mirrors the pipeline's four reward terms.
TASK_NAMES: Tuple[str, ...] = ("est_error", "tx_power", "congestion", "redundant")


class MADDPGMT(BaseRLModel):
    """
    Multi-agent multi-task DDPG with a task-decomposed dual critic.

    Action representation. The actor emits a unit-interval pair (u_delta, u_p)
    and num_channels channel logits. The unit values are mapped to the grant by
    the decoder: Delta geometrically via ActionDecoder.delta_from_unit, power
    linearly over [p_min, p_max]. `raw_action` is serialised through
    ActionDecoder.encode_action so that any consumer decoding it with
    ActionDecoder.decode_action recovers exactly the grant that was issued;
    update() converts it back into the actor's unit space before feeding the
    critics, so behaviour actions and actor proposals live in one space.
    """

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 128,
        num_tasks: int = len(TASK_NAMES),
        actor_lr: float = 1e-4,
        critic_lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        global_critic_weight: float = 0.5,
        exploration_noise: float = 0.1,
        gumbel_tau: float = 1.0,
        grad_clip: float = 0.5,
        task_weights: Optional[List[float]] = None,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.global_critic_weight = float(global_critic_weight)
        self.exploration_noise = float(exploration_noise)
        self.gumbel_tau = float(gumbel_tau)
        self.grad_clip = float(grad_clip)
        self.num_tasks = int(num_tasks)
        self.total_updates = 0

        # Fallback split of a scalar reward across the task heads (see the
        # module docstring: with a scalar reward the decomposition is inert).
        if task_weights is None:
            weights = [1.0 / self.num_tasks] * self.num_tasks
        else:
            weights = [float(w) for w in task_weights]
            if len(weights) != self.num_tasks:
                raise ValueError(f"task_weights must have {self.num_tasks} entries, got {len(weights)}")
        self.register_buffer("task_weights", torch.tensor(weights, dtype=torch.float32))

        # Geometric span of the Delta range, read off the decoder. This is the
        # vectorised twin of ActionDecoder.delta_from_unit / unit_from_delta; the
        # scalar path in select_action calls the decoder itself.
        if self.decoder.delta_min > 0.0 and self.decoder.delta_max > self.decoder.delta_min:
            self._log_delta_ratio = math.log(self.decoder.delta_max / self.decoder.delta_min)
        else:
            self._log_delta_ratio = 0.0

        #: [u_delta, u_p] + one-hot subchannel.
        self.action_dim = 2 + self.num_channels

        # ------------------------------------------------------------------
        # Actor (shared across agents; one forward per in-range vehicle)
        # ------------------------------------------------------------------
        self.actor = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 2 + self.num_channels),
        )

        # ------------------------------------------------------------------
        # Permutation-invariant encoder over the other in-range agents.
        # OUR ADDITION -- the paper has a fixed agent count and needs none.
        # ------------------------------------------------------------------
        self.context_dim = 2 * hidden_dim  # masked mean-pool || masked max-pool
        self.others_encoder = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )

        # ------------------------------------------------------------------
        # Task-decomposed critics: each emits num_tasks value heads.
        # ------------------------------------------------------------------
        self.local_critic = self._build_critic(self.state_dim + self.action_dim, hidden_dim)
        self.global_critic = self._build_critic(
            self.state_dim + self.action_dim + self.context_dim, hidden_dim
        )

        self.actor_target = copy.deepcopy(self.actor)
        self.local_critic_target = copy.deepcopy(self.local_critic)
        self.global_critic_target = copy.deepcopy(self.global_critic)
        self.others_encoder_target = copy.deepcopy(self.others_encoder)
        for module in (
            self.actor_target,
            self.local_critic_target,
            self.global_critic_target,
            self.others_encoder_target,
        ):
            for p in module.parameters():
                p.requires_grad = False

        self._actor_params = list(self.actor.parameters())
        self._critic_params = (
            list(self.local_critic.parameters())
            + list(self.global_critic.parameters())
            + list(self.others_encoder.parameters())
        )
        self.actor_optimizer = optim.Adam(self._actor_params, lr=float(actor_lr))
        self.critic_optimizer = optim.Adam(self._critic_params, lr=float(critic_lr))
        #: Alias so generic tooling that expects a single `optimizer` still works.
        self.optimizer = self.critic_optimizer

    def _build_critic(self, in_dim: int, hidden_dim: int) -> nn.Module:
        return nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, self.num_tasks),
        )

    # ----------------------------------------------------------------------
    # Action-space helpers (all bounds come from the decoder)
    # ----------------------------------------------------------------------
    def _delta_from_unit_t(self, u: torch.Tensor) -> torch.Tensor:
        """Vectorised ActionDecoder.delta_from_unit."""
        u = u.clamp(0.0, 1.0)
        if self._log_delta_ratio <= 0.0:
            return self.decoder.delta_min + u * (self.decoder.delta_max - self.decoder.delta_min)
        return self.decoder.delta_min * torch.exp(u * self._log_delta_ratio)

    def _unit_from_delta_t(self, delta: torch.Tensor) -> torch.Tensor:
        """Vectorised ActionDecoder.unit_from_delta."""
        d = delta.clamp(min=self.decoder.delta_min, max=self.decoder.delta_max)
        if self._log_delta_ratio <= 0.0:
            span = max(1e-6, self.decoder.delta_max - self.decoder.delta_min)
            return (d - self.decoder.delta_min) / span
        return torch.log(d / self.decoder.delta_min) / self._log_delta_ratio

    def _decode_batch_actions(self, actions: torch.Tensor) -> torch.Tensor:
        """
        Raw replay actions -> the critic's action vector [u_delta, u_p, one_hot(ch)].

        Raw actions are ActionDecoder.encode_action output, whose Delta field is a
        logit of the LINEARLY normalised Delta; it is inverted linearly and then
        re-expressed in the GEOMETRIC unit space the actor works in, so both
        halves of the critic input agree.
        """
        dec = self.decoder
        acts = actions.float()
        delta = dec.delta_min + torch.sigmoid(acts[:, 0]) * (dec.delta_max - dec.delta_min)
        u_delta = self._unit_from_delta_t(delta).unsqueeze(1)
        u_p = torch.sigmoid(acts[:, 2]).unsqueeze(1)
        ch = acts[:, 1].round().long().remainder(self.num_channels)
        one_hot = F.one_hot(ch, num_classes=self.num_channels).to(acts.dtype)
        return torch.cat([u_delta, u_p, one_hot], dim=1)

    def _actor_action(
        self,
        state: torch.Tensor,
        use_target: bool = False,
        differentiable_channel: bool = False,
    ) -> torch.Tensor:
        """Actor forward -> action vector in the critic's input format."""
        out = (self.actor_target if use_target else self.actor)(state)
        units = torch.sigmoid(out[:, :2])
        ch_logits = out[:, 2:]
        if differentiable_channel:
            # Straight-through Gumbel-Softmax: a hard argmax would sever the
            # actor gradient at the critic's channel input.
            ch_vec = F.gumbel_softmax(ch_logits, tau=self.gumbel_tau, hard=True)
        else:
            ch_vec = F.one_hot(torch.argmax(ch_logits, dim=-1), num_classes=self.num_channels).to(out.dtype)
        return torch.cat([units, ch_vec], dim=1)

    # ----------------------------------------------------------------------
    # Permutation-invariant context over the other in-range agents
    # ----------------------------------------------------------------------
    def _encode_others(
        self,
        others: Optional[torch.Tensor],
        mask: Optional[torch.Tensor],
        batch_size: int,
        device: torch.device,
        use_target: bool = False,
    ) -> torch.Tensor:
        """
        (B, N, state_dim) [+ (B, N) validity mask] -> (B, 2 * hidden) context.

        Masked mean- and max-pooling make the result invariant to both the order
        and the number of other agents, so a batch may mix steps with 0 and with
        many neighbours. An absent / fully-masked set yields the zero context.
        """
        zero = torch.zeros(batch_size, self.context_dim, device=device)
        if others is None or others.numel() == 0:
            return zero
        oth = others.to(device).float()
        if oth.dim() == 2:  # (N, state_dim) broadcast to the whole batch
            oth = oth.unsqueeze(0).expand(batch_size, -1, -1)
        if mask is None:
            m = torch.ones(oth.shape[0], oth.shape[1], device=device)
        else:
            m = mask.to(device).float().reshape(oth.shape[0], oth.shape[1])

        encoder = self.others_encoder_target if use_target else self.others_encoder
        emb = encoder(oth) * m.unsqueeze(-1)
        counts = m.sum(dim=1, keepdim=True).clamp_min(1.0)
        mean_pool = emb.sum(dim=1) / counts
        # -inf on invalid slots so they can never win the max.
        neg_inf = torch.finfo(emb.dtype).min
        max_pool = torch.where(m.unsqueeze(-1) > 0.0, emb, torch.full_like(emb, neg_inf)).max(dim=1).values
        max_pool = torch.where(torch.isfinite(max_pool), max_pool, torch.zeros_like(max_pool))
        empty = (m.sum(dim=1, keepdim=True) <= 0.0)
        ctx = torch.cat([mean_pool, max_pool], dim=1)
        return torch.where(empty, torch.zeros_like(ctx), ctx)

    # ----------------------------------------------------------------------
    # Contract methods
    # ----------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            out = self.actor(state_t)
            units = torch.sigmoid(out[0, :2])
            ch_logits = out[0, 2:]
            if deterministic:
                u_delta, u_p = float(units[0].item()), float(units[1].item())
                ch = int(torch.argmax(ch_logits).item())
            else:
                noise = torch.randn(2, device=units.device) * self.exploration_noise
                noisy = (units + noise).clamp(0.0, 1.0)
                u_delta, u_p = float(noisy[0].item()), float(noisy[1].item())
                probs = torch.softmax(ch_logits, dim=-1)
                ch = int(torch.multinomial(probs, 1).item())

        # Geometric Delta, linear power -- both through the decoder's own mapping.
        delta = float(self.decoder.delta_from_unit(u_delta))
        power = float(self.decoder.p_min + u_p * (self.decoder.p_max - self.decoder.p_min))
        raw_action = self.decoder.encode_action(delta, ch, power)

        info: Dict[str, Any] = {
            "u_delta": u_delta,
            "u_power": u_p,
            "channel_idx": int(ch),
            "channel_logits": ch_logits.detach().cpu().numpy(),
            "raw_action": raw_action,
        }
        return (delta, int(ch), power), raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        device = next(self.parameters()).device
        states = batch["state"].to(device).float()
        next_states = batch["next_state"].to(device).float()
        rewards = batch["reward"].to(device).float()
        dones = batch["done"].to(device).float()
        batch_size = states.shape[0]

        if "discount" in batch:
            discounts = batch["discount"].to(device).float()
        else:
            delta_ts = batch.get("delta_t", torch.ones_like(rewards)).to(device).float()
            discounts = torch.pow(torch.as_tensor(self.gamma, device=device), delta_ts)

        # -- Task-decomposed rewards (B, num_tasks) ---------------------------
        if "reward_terms" in batch:
            r_tasks = batch["reward_terms"].to(device).float().reshape(batch_size, -1)
            if r_tasks.shape[1] != self.num_tasks:
                raise ValueError(
                    f"reward_terms must have {self.num_tasks} columns, got {r_tasks.shape[1]}"
                )
            decomposed = True
        else:
            # Inert fallback: the heads sum to the scalar reward but carry no
            # per-task information. See the module docstring.
            r_tasks = rewards.reshape(batch_size, 1) * self.task_weights.to(device).reshape(1, -1)
            decomposed = False

        actions = self._decode_batch_actions(batch["action"].to(device))
        others = batch.get("others")
        others_mask = batch.get("others_mask")
        next_others = batch.get("next_others", others)
        next_others_mask = batch.get("next_others_mask", others_mask)

        # -- Critic update -----------------------------------------------------
        with torch.no_grad():
            next_actions = self._actor_action(next_states, use_target=True, differentiable_channel=False)
            next_ctx = self._encode_others(
                next_others, next_others_mask, batch_size, device, use_target=True
            )
            q_next_local = self.local_critic_target(torch.cat([next_states, next_actions], dim=1))
            q_next_global = self.global_critic_target(
                torch.cat([next_states, next_actions, next_ctx], dim=1)
            )
            # One shared bootstrap per task, from the convex combination of the
            # two critics -- Parvini's global/local blend, applied per task head.
            q_next = (
                self.global_critic_weight * q_next_global
                + (1.0 - self.global_critic_weight) * q_next_local
            )
            y = r_tasks + (1.0 - dones) * discounts * q_next

        ctx = self._encode_others(others, others_mask, batch_size, device, use_target=False)
        q_local = self.local_critic(torch.cat([states, actions], dim=1))
        q_global = self.global_critic(torch.cat([states, actions, ctx], dim=1))
        critic_loss = F.mse_loss(q_local, y) + F.mse_loss(q_global, y)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self._critic_params, self.grad_clip)
        self.critic_optimizer.step()

        # -- Actor update: maximise the summed task values ---------------------
        pi_actions = self._actor_action(states, use_target=False, differentiable_channel=True)
        ctx_detached = ctx.detach()
        q_pi_local = self.local_critic(torch.cat([states, pi_actions], dim=1)).sum(dim=1)
        q_pi_global = self.global_critic(torch.cat([states, pi_actions, ctx_detached], dim=1)).sum(dim=1)
        actor_loss = -(
            self.global_critic_weight * q_pi_global
            + (1.0 - self.global_critic_weight) * q_pi_local
        ).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self._actor_params, self.grad_clip)
        self.actor_optimizer.step()

        # -- Polyak target updates --------------------------------------------
        with torch.no_grad():
            for online, target in (
                (self.actor, self.actor_target),
                (self.local_critic, self.local_critic_target),
                (self.global_critic, self.global_critic_target),
                (self.others_encoder, self.others_encoder_target),
            ):
                for p, pt in zip(online.parameters(), target.parameters()):
                    pt.data.copy_(self.tau * p.data + (1.0 - self.tau) * pt.data)

        self.total_updates += 1

        out = {
            "loss": float(critic_loss.item() + actor_loss.item()),
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "mean_q_local": float(q_local.sum(dim=1).mean().item()),
            "mean_q_global": float(q_global.sum(dim=1).mean().item()),
            "task_decomposed": float(decomposed),
        }
        for i, name in enumerate(TASK_NAMES[: self.num_tasks]):
            out[f"q_{name}"] = float(q_global[:, i].mean().item())
        return out
