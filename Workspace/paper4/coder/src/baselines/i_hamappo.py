# src/baselines/i_hamappo.py
"""
I-HAMAPPO -- Importance-based Hybrid-Action Multi-Agent PPO (semantic half removed).

Reference
---------
X. Chen et al., "Hybrid-Action DRL-Based Resource Allocation for Semantic-Aware
Computation Offloading in Vehicular Edge Networks," IEEE Transactions on Wireless
Communications, vol. 25, 2026.
DOI: 10.1109/TWC.2025.3626670

This is a REIMPLEMENTATION ADAPTED TO OUR ENVIRONMENT, not a verbatim reproduction.

What the original paper does
----------------------------
Observation: a per-vehicle view of task queue state, channel state and edge-server state.
Action: mixed -- a discrete offloading / resource selection together with a continuous
semantic compression ratio and a continuous communication-resource share. A utility
function trades off task delay, energy consumption and semantic similarity, and an
importance evaluation module (IEM) scores semantic features so that only task-relevant
information is transmitted. Evaluated on real highD trajectories.

What is KEPT here
-----------------
* The I-HAMAPPO learner named in the title: one shared actor with a discrete branch and
  a continuous branch, trained with a clipped PPO surrogate against a centralised critic.
* Shared-parameter multi-agent instantiation: one actor per in-range vehicle, all hosted
  at the RSU. Our scheduler is centralised at a single RSU, so the centralised critic is
  our ACTUAL DEPLOYMENT, not an extra assumption imported from the paper.
* The importance-sampling ratio that PPO is built on (see `_policy_log_prob`).

What is DROPPED, and why -- STATE THIS IN THE PAPER
---------------------------------------------------
* The importance evaluation module and the continuous semantic-compression-ratio action.
  We transmit mobility state, not semantic features: there is no semantic similarity term
  to optimise and nothing to compress. Roughly HALF OF THE ORIGINAL CONTRIBUTION (the
  semantic / IEM half) is therefore not reproduced, and only the hybrid-action MAPPO
  learner is being compared. Any claim of the form "we compare against Chen et al. 2026"
  must carry that qualification.
* The task-queue / edge-server observation and the delay-energy-similarity utility. Our
  observation is the 18-dim RSU-side vector from `StateVectorizer` and our reward is the
  AoI-based retrospective reward defined by the scheduler.

Adaptations, including two honest weakenings
--------------------------------------------
* The continuous branch emits (Delta, p) instead of (compression ratio, resource share).
  Same 2-dim continuous head; only the semantics of the outputs differ.
* WEAKENING 1 -- the behaviour policy. PPO is on-policy and normally stores the
  behaviour log-probability alongside each transition. `RetrospectiveReplayBuffer` does
  not carry log-probs, so we cannot recover the true behaviour policy. We keep a FROZEN
  SNAPSHOT of the actor, re-synced every `policy_sync_interval` updates, and evaluate the
  denominator of the importance ratio under it. This makes the surrogate a genuine
  clipped ratio rather than the identically-1.0 ratio that a naive
  `exp(logp - logp.detach())` produces, but it is a proximal-policy approximation of the
  paper's on-policy ratio, not the same estimator.
* WEAKENING 2 -- no GAE. Generalised advantage estimation needs contiguous trajectories;
  our buffer samples transitions uniformly at random, so the advantage is a one-step SMDP
  TD residual r + gamma^Delta V(s') - V(s). This is higher-bias than the paper's
  multi-step advantage.
* NOT IN THE PAPER (our addition): the agent count varies as vehicles enter and leave the
  300 m RSU range, so a fixed-size centralised critic input is impossible. We use a
  padded neighbour set with an explicit validity mask and permutation-invariant
  masked-mean pooling (`_pool_neighbourhood`). When the batch carries no neighbour set --
  which is the default, since our buffer stores per-vehicle transitions -- the set
  degenerates to the ego observation alone, which is weaker than a true joint critic.
* The continuous branch is a Gaussian in pre-squash space followed by tanh. The tanh
  Jacobian is independent of the policy parameters and therefore CANCELS inside the
  importance ratio, so log-probabilities are computed in pre-squash space and the raw
  action stores the pre-squash sample. Entropy is likewise the pre-squash Gaussian
  entropy, which is the usual convention.
"""

from __future__ import annotations
import copy
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical, Normal
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM


class IHAMAPPO(BaseRLModel):
    """
    Hybrid-action multi-agent PPO (Chen et al., IEEE TWC 2026), semantic half removed.

    Discrete branch: Categorical over the subchannels.
    Continuous branch: diagonal Gaussian over (Delta, p) in pre-tanh space.
    Critic: centralised, over the ego observation plus a masked-pooled neighbour set.
    """

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 128,
        ctx_dim: int = 32,
        max_agents: int = 16,
        lr_actor: float = 3e-4,
        lr_critic: float = 3e-4,
        gamma: float = 0.99,
        clip_ratio: float = 0.2,
        entropy_coef: float = 0.01,
        value_coef: float = 0.5,
        policy_sync_interval: int = 4,
        log_std_init: float = -0.5,
        grad_clip: float = 0.5,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.clip_ratio = float(clip_ratio)
        self.entropy_coef = float(entropy_coef)
        self.value_coef = float(value_coef)
        self.policy_sync_interval = max(1, int(policy_sync_interval))
        self.grad_clip = float(grad_clip)
        self.max_agents = max(1, int(max_agents))

        #: Continuous branch width: (Delta, p).
        self.cont_dim = 2

        self.register_buffer("update_count", torch.zeros(1))

        # --- Shared actor trunk with a discrete branch and a continuous branch.
        self.actor_trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
        )
        self.ch_head = nn.Linear(hidden_dim, self.num_channels)
        self.cont_head = nn.Linear(hidden_dim, self.cont_dim)
        self.log_std = nn.Parameter(torch.full((self.cont_dim,), float(log_std_init)))

        # --- Frozen behaviour-policy snapshot (see WEAKENING 1 in the module docstring).
        self.old_actor_trunk = copy.deepcopy(self.actor_trunk)
        self.old_ch_head = copy.deepcopy(self.ch_head)
        self.old_cont_head = copy.deepcopy(self.cont_head)
        self.old_log_std = nn.Parameter(self.log_std.detach().clone(), requires_grad=False)
        for module in (self.old_actor_trunk, self.old_ch_head, self.old_cont_head):
            for p in module.parameters():
                p.requires_grad = False

        # --- Centralised critic over the ego observation plus the pooled neighbourhood.
        self.neighbour_encoder = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, ctx_dim),
        )
        self.central_critic = nn.Sequential(
            nn.Linear(self.state_dim + ctx_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )

        self.actor_params = (
            list(self.actor_trunk.parameters())
            + list(self.ch_head.parameters())
            + list(self.cont_head.parameters())
            + [self.log_std]
        )
        self.critic_params = list(self.central_critic.parameters()) + list(self.neighbour_encoder.parameters())
        self.actor_optimizer = optim.Adam(self.actor_params, lr=lr_actor)
        self.critic_optimizer = optim.Adam(self.critic_params, lr=lr_critic)

    # ------------------------------------------------------------------
    # Action-space plumbing
    # ------------------------------------------------------------------
    def _grant_from_pre_squash(self, z: np.ndarray, ch: int) -> Tuple[float, int, float]:
        """
        Squash the Gaussian sample through tanh and map it onto the environment's grant
        tuple (delta_s, ch_idx, power_dbm).

        Delta goes through `ActionDecoder.delta_from_unit`, the GEOMETRIC map the design
        mandates; `ActionDecoder.decode_action` is not used for Delta because it
        interpolates linearly. Bounds are read off the decoder and never restated here.
        """
        dec = self.decoder
        squashed = np.tanh(np.asarray(z, dtype=np.float64))
        u_delta = 0.5 * (float(squashed[0]) + 1.0)
        u_power = 0.5 * (float(squashed[1]) + 1.0)
        delta = dec.delta_from_unit(u_delta)
        power = dec.p_min + u_power * (dec.p_max - dec.p_min)
        return float(delta), int(ch) % self.num_channels, float(power)

    def _distributions(self, states: torch.Tensor, use_old: bool = False) -> Tuple[Categorical, Normal]:
        trunk = self.old_actor_trunk if use_old else self.actor_trunk
        ch_head = self.old_ch_head if use_old else self.ch_head
        cont_head = self.old_cont_head if use_old else self.cont_head
        log_std = self.old_log_std if use_old else self.log_std

        feat = trunk(states)
        ch_dist = Categorical(logits=ch_head(feat))
        cont_std = torch.exp(torch.clamp(log_std, -20.0, 2.0))
        cont_dist = Normal(cont_head(feat), cont_std)
        return ch_dist, cont_dist

    @staticmethod
    def _policy_log_prob(
        ch_dist: Categorical, cont_dist: Normal, ch_targets: torch.Tensor, cont_targets: torch.Tensor
    ) -> torch.Tensor:
        """
        Joint log-probability of the hybrid action. The tanh Jacobian term is omitted on
        purpose: it does not depend on the policy parameters, so it cancels in the
        importance ratio and in the gradient.
        """
        ch_lp = ch_dist.log_prob(ch_targets).unsqueeze(1)
        cont_lp = cont_dist.log_prob(cont_targets).sum(dim=-1, keepdim=True)
        return ch_lp + cont_lp

    def _pool_neighbourhood(
        self,
        states: torch.Tensor,
        neighbour_states: Optional[torch.Tensor],
        neighbour_mask: Optional[torch.Tensor],
    ) -> torch.Tensor:
        """
        Permutation-invariant masked-mean pooling over a padded neighbour set.

        NOT from the paper: our agent population changes size as vehicles enter and leave
        the RSU range, so the joint critic input is padded to `max_agents` with a 0/1
        validity flag per slot and pooled with a masked mean. With no neighbour set
        supplied the set degenerates to the ego observation alone.
        """
        if neighbour_states is None:
            neighbour_states = states.unsqueeze(1)
            neighbour_mask = torch.ones(states.shape[0], 1, dtype=states.dtype, device=states.device)
        else:
            neighbour_states = neighbour_states.to(dtype=states.dtype, device=states.device)
            if neighbour_states.dim() == 2:
                neighbour_states = neighbour_states.unsqueeze(1)
            neighbour_states = neighbour_states[:, : self.max_agents]
            if neighbour_mask is None:
                neighbour_mask = torch.ones(
                    neighbour_states.shape[:2], dtype=states.dtype, device=states.device
                )
            else:
                neighbour_mask = neighbour_mask.to(dtype=states.dtype, device=states.device)
                neighbour_mask = neighbour_mask.reshape(neighbour_states.shape[0], -1)[:, : self.max_agents]
            pad = self.max_agents - neighbour_states.shape[1]
            if pad > 0:
                neighbour_states = F.pad(neighbour_states, (0, 0, 0, pad))
                neighbour_mask = F.pad(neighbour_mask, (0, pad))

        emb = self.neighbour_encoder(neighbour_states)
        mask = neighbour_mask.unsqueeze(-1)
        return (emb * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)

    def _value(
        self,
        states: torch.Tensor,
        neighbour_states: Optional[torch.Tensor] = None,
        neighbour_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        ctx = self._pool_neighbourhood(states, neighbour_states, neighbour_mask)
        return self.central_critic(torch.cat([states, ctx], dim=-1))

    # ------------------------------------------------------------------
    # BaseRLModel contract
    # ------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            ch_dist, cont_dist = self._distributions(state_t)
            value = float(self._value(state_t).item())

            if deterministic:
                ch_t = torch.argmax(ch_dist.logits, dim=-1)
                z_t = cont_dist.mean
            else:
                ch_t = ch_dist.sample()
                z_t = cont_dist.sample()

            log_prob = float(self._policy_log_prob(ch_dist, cont_dist, ch_t, z_t).item())
            ch = int(ch_t.item())
            z = z_t[0].cpu().numpy()

        decoded = self._grant_from_pre_squash(z, ch)
        # Shared positional convention: [continuous Delta term, subchannel, power term].
        # The continuous entries are PRE-TANH so that update() can recompute log-probs.
        raw_action = np.array([float(z[0]), float(ch), float(z[1])], dtype=np.float32)
        info = {
            "action_idx": int(ch),
            "value": value,
            "log_prob": log_prob,
            "raw_action": raw_action,
        }
        return decoded, raw_action, info

    def _resolve_channel_indices(self, batch: Dict[str, torch.Tensor], device: torch.device) -> torch.Tensor:
        """
        Discrete credit assignment. Preferred path: the verbatim "action_idx" carried by
        the replay buffer. Fallback for transitions predating it: raw_action[1], which
        stores the same subchannel index, so the fallback is exact rather than lossy.
        """
        if "action_idx" in batch:
            idx = batch["action_idx"].to(device=device).long().reshape(-1)
        else:
            idx = batch["action"][:, 1].to(device=device).round().long().reshape(-1)
        return ((idx % self.num_channels) + self.num_channels) % self.num_channels

    def _sync_old_policy(self) -> None:
        with torch.no_grad():
            self.old_actor_trunk.load_state_dict(self.actor_trunk.state_dict())
            self.old_ch_head.load_state_dict(self.ch_head.state_dict())
            self.old_cont_head.load_state_dict(self.cont_head.state_dict())
            self.old_log_std.data.copy_(self.log_std.data)

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        actions = batch["action"]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        device = states.device

        if "discount" in batch:
            discounts = batch["discount"]
        else:
            discounts = torch.pow(self.gamma, batch.get("delta_t", torch.ones_like(rewards)))

        neighbour_states = batch.get("neighbour_state", batch.get("neighbor_state"))
        neighbour_mask = batch.get("neighbour_mask", batch.get("neighbor_mask"))
        next_neighbour_states = batch.get("next_neighbour_state", batch.get("next_neighbor_state"))
        next_neighbour_mask = batch.get("next_neighbour_mask", batch.get("next_neighbor_mask"))

        ch_targets = self._resolve_channel_indices(batch, device)
        cont_targets = actions[:, [0, 2]].to(device)

        # --------------------------------------------------------------------
        # 1. Centralised critic update (one-step SMDP TD target; no GAE available)
        # --------------------------------------------------------------------
        with torch.no_grad():
            next_v = self._value(next_states, next_neighbour_states, next_neighbour_mask)
            target_v = rewards + (1.0 - dones) * discounts * next_v

        v_pred = self._value(states, neighbour_states, neighbour_mask)
        value_loss = F.mse_loss(v_pred, target_v)

        self.critic_optimizer.zero_grad(set_to_none=True)
        value_loss.backward()
        nn.utils.clip_grad_norm_(self.critic_params, self.grad_clip)
        self.critic_optimizer.step()

        # --------------------------------------------------------------------
        # 2. Clipped surrogate against the frozen behaviour snapshot
        # --------------------------------------------------------------------
        advantages = (target_v - v_pred.detach())
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        ch_dist, cont_dist = self._distributions(states, use_old=False)
        new_log_prob = self._policy_log_prob(ch_dist, cont_dist, ch_targets, cont_targets)
        with torch.no_grad():
            old_ch_dist, old_cont_dist = self._distributions(states, use_old=True)
            old_log_prob = self._policy_log_prob(old_ch_dist, old_cont_dist, ch_targets, cont_targets)

        ratio = torch.exp(torch.clamp(new_log_prob - old_log_prob, -20.0, 20.0))
        surr1 = ratio * advantages
        surr2 = torch.clamp(ratio, 1.0 - self.clip_ratio, 1.0 + self.clip_ratio) * advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        entropy = ch_dist.entropy().mean() + cont_dist.entropy().sum(dim=-1).mean()
        actor_loss = policy_loss - self.entropy_coef * entropy

        self.actor_optimizer.zero_grad(set_to_none=True)
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.actor_params, self.grad_clip)
        self.actor_optimizer.step()

        # --------------------------------------------------------------------
        # 3. Behaviour-snapshot refresh
        # --------------------------------------------------------------------
        self.update_count.add_(1.0)
        synced = int(self.update_count.item()) % self.policy_sync_interval == 0
        if synced:
            self._sync_old_policy()

        return {
            "loss": float(actor_loss.item() + self.value_coef * value_loss.item()),
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy": float(entropy.item()),
            "mean_ratio": float(ratio.mean().item()),
            "policy_synced": float(synced),
        }
