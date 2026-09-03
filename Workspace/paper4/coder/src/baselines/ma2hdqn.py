# src/baselines/ma2hdqn.py
"""
MA2HDQN -- Multi-Agent Hybrid Deep Q-Network (MA-D3QN branch + i-DDPG branch).

Reference
---------
Y. Hong et al., "Joint Sub-Band Allocation and Power Control for Dynamic Vehicular
Networks Based on Multi-Agent Deep Reinforcement Learning," IEEE Transactions on
Vehicular Technology, vol. 75, no. 6, 2026.
DOI: 10.1109/TVT.2025.3640225

This is a REIMPLEMENTATION ADAPTED TO OUR ENVIRONMENT, not a verbatim reproduction.

What the original paper does
----------------------------
Observation: per-link local channel and interference state. Action: a hybrid pair --
a discrete sub-band index and a continuous transmit power. The method splits that hybrid
space across two branches: a multi-agent dueling double DQN (MA-D3QN) for the discrete
sub-band, and an "improved DDPG" (i-DDPG) for the continuous power. On top of that sit
an adaptive learning-rate rule driven by recent environment feedback and multi-step
Q-value updates for faster, more stable convergence.

What is KEPT here
-----------------
* The branch split itself, which is the paper's actual claim: D3QN (dueling + double)
  over the discrete subchannel, DDPG over the continuous variables.
* The adaptive learning-rate rule (algorithm-internal, carries over directly).
* Shared-parameter multi-agent instantiation: one agent instance per in-range vehicle,
  all executed at the RSU. For a single-RSU scheduler this is semantically identical to
  the paper's multi-agent framing, and it is our actual deployment rather than an extra
  assumption.

What is DROPPED / CHANGED, and why
----------------------------------
* The per-link CSI observation is replaced by the RSU-side observation from
  `StateVectorizer`, because that is what our scheduler can see at decision time.
* MULTI-STEP RETURNS ARE NOT AVAILABLE IN THE PAPER'S FORM, and this is a genuine
  weakening. `RetrospectiveReplayBuffer.sample()` draws transitions uniformly at random
  and stores no successor chain, so an n-step return cannot be assembled from it. What we
  do have is the SMDP structure: each stored transition already spans a variable holding
  time Delta and is discounted by gamma^Delta, which aggregates reward over that interval.
  That is a temporal aggregation, but it is NOT the paper's n-step bootstrap and should
  not be described as such. The n-step path below activates only if a future buffer
  supplies "n_step_reward"/"n_step_discount"; otherwise the update is a one-step SMDP
  backup.
* WHICH "improvements" make DDPG "improved" is not pinned down by the material we have.
  We implement the two standard ones -- clipped target-policy smoothing and gradient
  clipping -- and flag that as our reading rather than the paper's specification.
* The exact functional form of the adaptive learning-rate rule is likewise not pinned
  down; see `_adapt_learning_rate` for the form we chose and its stated rationale.

Adaptations
-----------
* The i-DDPG branch output is widened from 1-dim (power) to 2-dim (Delta, p), with Delta
  passed through the ActionDecoder's geometric mapping. This is the only structural
  change to the learner.
* D3QN uses a periodic HARD target sync (`target_sync_interval`), which is the classical
  DQN-family rule; the i-DDPG branch uses Polyak averaging. Consequence for anyone
  diffing weights after a single update: the D3QN target tensors legitimately do not move
  on most steps.
"""

from __future__ import annotations
import copy
import logging
from typing import Any, Dict, Sequence, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM

logger = logging.getLogger(__name__)


class MA2HDQN(BaseRLModel):
    """
    Branch-split hybrid-action agent (Hong et al., IEEE TVT 2026).

    Discrete subchannel <- MA-D3QN branch (dueling streams, double-DQN target).
    Continuous (Delta, p) <- i-DDPG branch (deterministic actor + Q critic).
    """

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 128,
        lr_q: float = 3e-4,
        lr_actor: float = 1e-4,
        lr_critic: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        target_sync_interval: int = 200,
        epsilon_initial: float = 0.2,
        epsilon_decay: float = 0.999,
        epsilon_min: float = 0.01,
        action_noise_std: float = 0.1,
        target_noise_std: float = 0.2,
        target_noise_clip: float = 0.5,
        lr_feedback_beta: float = 0.05,
        lr_adapt_gain: float = 0.5,
        lr_factor_min: float = 0.5,
        lr_factor_max: float = 2.0,
        n_step: int = 1,
        grad_clip: float = 0.5,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.target_sync_interval = max(1, int(target_sync_interval))
        self.epsilon_decay = float(epsilon_decay)
        self.epsilon_min = float(epsilon_min)
        self.action_noise_std = float(action_noise_std)
        self.target_noise_std = float(target_noise_std)
        self.target_noise_clip = float(target_noise_clip)
        self.lr_feedback_beta = float(lr_feedback_beta)
        self.lr_adapt_gain = float(lr_adapt_gain)
        self.lr_factor_min = float(lr_factor_min)
        self.lr_factor_max = float(lr_factor_max)
        self.n_step = max(1, int(n_step))
        self.grad_clip = float(grad_clip)
        #: True only when the replay batch actually carries an n-step return.
        #: `RetrospectiveReplayBuffer` never does (see the module header), so on
        #: the shipped pipeline `n_step` is INERT: it selects nothing, and an
        #: Optuna study that searches it reports an "optimal n_step" that had no
        #: effect on any trial. The flag is set per `update()` call so the
        #: condition is observable in the returned dict instead of being assumed.
        self.n_step_active = False
        if self.n_step > 1:
            logger.warning(
                "MA2HDQN: n_step=%d was requested, but n-step returns require the "
                "replay buffer to supply 'n_step_reward'/'n_step_discount'. "
                "RetrospectiveReplayBuffer does not, so this update stays a one-step "
                "SMDP backup. Remove `n_step` from the search space or extend the buffer.",
                self.n_step,
            )

        #: Continuous branch width: (Delta, p). The paper's is 1 -- power only.
        self.cont_dim = 2

        # Scalars that must ride along with a hot-swap are buffers, because the swap
        # manager copies parameters AND buffers between the Act and Rest models.
        self.register_buffer("epsilon", torch.tensor(float(epsilon_initial)))
        self.register_buffer("reward_ema", torch.zeros(1))
        self.register_buffer("reward_ema_init", torch.zeros(1))
        self.register_buffer("lr_scale", torch.ones(1))
        self.register_buffer("update_count", torch.zeros(1))

        # --- MA-D3QN branch: dueling value / advantage streams over the subchannels.
        self.q_trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.q_value_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.q_adv_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, self.num_channels),
        )

        # --- i-DDPG branch: deterministic actor over the continuous pair + its critic.
        # The critic is conditioned on the subchannel one-hot as well, because in our
        # environment the value of a given (Delta, p) depends on which subchannel it runs
        # on -- the two branches are not independent even though the policies are split.
        self.cont_actor = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, self.cont_dim),
        )
        self.cont_critic = nn.Sequential(
            nn.Linear(self.state_dim + self.cont_dim + self.num_channels, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

        self.q_trunk_target = copy.deepcopy(self.q_trunk)
        self.q_value_head_target = copy.deepcopy(self.q_value_head)
        self.q_adv_head_target = copy.deepcopy(self.q_adv_head)
        self.cont_actor_target = copy.deepcopy(self.cont_actor)
        self.cont_critic_target = copy.deepcopy(self.cont_critic)
        for module in (
            self.q_trunk_target,
            self.q_value_head_target,
            self.q_adv_head_target,
            self.cont_actor_target,
            self.cont_critic_target,
        ):
            for p in module.parameters():
                p.requires_grad = False

        self.q_params = (
            list(self.q_trunk.parameters())
            + list(self.q_value_head.parameters())
            + list(self.q_adv_head.parameters())
        )
        self.q_optimizer = optim.Adam(self.q_params, lr=lr_q)
        self.actor_optimizer = optim.Adam(self.cont_actor.parameters(), lr=lr_actor)
        self.critic_optimizer = optim.Adam(self.cont_critic.parameters(), lr=lr_critic)
        self._base_lrs = {
            "q": float(lr_q),
            "actor": float(lr_actor),
            "critic": float(lr_critic),
        }

    # ------------------------------------------------------------------
    # Action-space plumbing
    # ------------------------------------------------------------------
    def _grant_from_unit_action(
        self, cont: Union[np.ndarray, torch.Tensor, Sequence[float]], ch: int
    ) -> Tuple[float, int, float]:
        """
        Map the i-DDPG branch's bounded output in [-1, 1]^2 plus the D3QN branch's
        subchannel index onto the environment's grant tuple.

        Delta goes through `ActionDecoder.delta_from_unit` -- the GEOMETRIC map the design
        mandates. `ActionDecoder.decode_action` is not used for Delta because it
        interpolates linearly; bounds are still read off the decoder and never restated.
        """
        dec = self.decoder
        u_delta = 0.5 * (float(np.clip(float(cont[0]), -1.0, 1.0)) + 1.0)
        u_power = 0.5 * (float(np.clip(float(cont[1]), -1.0, 1.0)) + 1.0)
        delta = dec.delta_from_unit(u_delta)
        power = dec.p_min + u_power * (dec.p_max - dec.p_min)
        return float(delta), int(ch) % self.num_channels, float(power)

    def _q_values(self, states: torch.Tensor, use_target: bool = False) -> torch.Tensor:
        """Dueling aggregation Q(s, k) = V(s) + (A(s, k) - mean_k A(s, k))."""
        trunk = self.q_trunk_target if use_target else self.q_trunk
        v_head = self.q_value_head_target if use_target else self.q_value_head
        a_head = self.q_adv_head_target if use_target else self.q_adv_head
        h = trunk(states)
        adv = a_head(h)
        return v_head(h) + (adv - adv.mean(dim=-1, keepdim=True))

    def _channel_one_hot(self, ch_indices: torch.Tensor, dtype: torch.dtype) -> torch.Tensor:
        return F.one_hot(ch_indices.reshape(-1), num_classes=self.num_channels).to(dtype)

    # ------------------------------------------------------------------
    # BaseRLModel contract
    # ------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        eps = float(self.epsilon.item())
        with torch.no_grad():
            q_values = self._q_values(state_t)
            if not deterministic and np.random.rand() < eps:
                ch = int(np.random.randint(0, self.num_channels))
            else:
                ch = int(torch.argmax(q_values, dim=-1).item())

            cont_t = torch.tanh(self.cont_actor(state_t))
            if not deterministic and self.action_noise_std > 0.0:
                cont_t = (cont_t + self.action_noise_std * torch.randn_like(cont_t)).clamp(-1.0, 1.0)
            cont = cont_t[0].cpu().numpy()

        decoded = self._grant_from_unit_action(cont, ch)
        # Shared positional convention: [continuous Delta term, subchannel, power term].
        raw_action = np.array([float(cont[0]), float(ch), float(cont[1])], dtype=np.float32)
        info = {
            "action_idx": int(ch),
            "q_values": q_values[0].cpu().numpy(),
            "raw_action": raw_action,
            "epsilon": eps,
            "lr_scale": float(self.lr_scale.item()),
        }
        return decoded, raw_action, info

    def _resolve_channel_indices(self, batch: Dict[str, torch.Tensor], device: torch.device) -> torch.Tensor:
        """
        Discrete credit assignment. Preferred path: the verbatim "action_idx" the replay
        buffer carries. Fallback for transitions stored before the index existed:
        raw_action[1], which holds the same subchannel index, so the fallback is exact.
        """
        if "action_idx" in batch:
            idx = batch["action_idx"].to(device=device).long().reshape(-1)
        else:
            idx = batch["action"][:, 1].to(device=device).round().long().reshape(-1)
        return ((idx % self.num_channels) + self.num_channels) % self.num_channels

    def _adapt_learning_rate(self, batch_reward_mean: float) -> float:
        """
        Adaptive learning-rate rule driven by recent environment feedback.

        The paper states the rule qualitatively; the functional form below is ours and is
        flagged as such. We keep an EMA of the batch reward as the "recent feedback"
        signal. When the current batch beats that EMA the policy is on track, so the step
        size is annealed DOWN for stability; when it falls short the environment has moved
        under us, so the step size is scaled UP to re-adapt faster. `tanh` on a
        scale-free relative improvement keeps the factor bounded regardless of the reward
        magnitude, which matters because our reward is an unnormalised negative cost.
        """
        beta = self.lr_feedback_beta
        if float(self.reward_ema_init.item()) < 0.5:
            self.reward_ema.fill_(batch_reward_mean)
            self.reward_ema_init.fill_(1.0)
        prev_ema = float(self.reward_ema.item())
        denom = abs(prev_ema) + 1e-6
        improvement = (batch_reward_mean - prev_ema) / denom
        factor = 1.0 - self.lr_adapt_gain * float(np.tanh(improvement))
        factor = float(np.clip(factor, self.lr_factor_min, self.lr_factor_max))
        self.lr_scale.fill_(factor)
        self.reward_ema.fill_((1.0 - beta) * prev_ema + beta * batch_reward_mean)

        for key, optimizer in (
            ("q", self.q_optimizer),
            ("actor", self.actor_optimizer),
            ("critic", self.critic_optimizer),
        ):
            for group in optimizer.param_groups:
                group["lr"] = self._base_lrs[key] * factor
        return factor

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        actions = batch["action"]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        device = states.device

        # SMDP discount from THIS model's gamma (see BaseRLModel.smdp_discounts).
        discounts = self.smdp_discounts(batch, rewards)

        # Multi-step return, only if a buffer ever supplies one. Our
        # RetrospectiveReplayBuffer does not (see module docstring), so in the normal
        # training path this is a one-step SMDP backup.
        self.n_step_active = "n_step_reward" in batch and "n_step_discount" in batch
        if self.n_step_active:
            rewards = batch["n_step_reward"]
            discounts = batch["n_step_discount"]

        ch_indices = self._resolve_channel_indices(batch, device)
        ch_col = ch_indices.unsqueeze(1)
        cont_executed = actions[:, [0, 2]].to(device).clamp(-1.0, 1.0)
        ch_one_hot = self._channel_one_hot(ch_indices, states.dtype)

        # Environment feedback drives the adaptive learning rate BEFORE the step, so the
        # step actually taken uses the adapted rate.
        lr_factor = self._adapt_learning_rate(float(rewards.mean().item()))

        # --------------------------------------------------------------------
        # 1. MA-D3QN branch: double-DQN target over the discrete subchannel
        # --------------------------------------------------------------------
        with torch.no_grad():
            next_q_online = self._q_values(next_states, use_target=False)
            next_best = torch.argmax(next_q_online, dim=-1, keepdim=True)
            next_q_target = self._q_values(next_states, use_target=True).gather(1, next_best)
            q_target = rewards + (1.0 - dones) * discounts * next_q_target

        q_pred = self._q_values(states).gather(1, ch_col)
        q_loss = F.mse_loss(q_pred, q_target)

        self.q_optimizer.zero_grad(set_to_none=True)
        q_loss.backward()
        nn.utils.clip_grad_norm_(self.q_params, self.grad_clip)
        self.q_optimizer.step()

        # --------------------------------------------------------------------
        # 2. i-DDPG branch: critic with clipped target-policy smoothing
        # --------------------------------------------------------------------
        with torch.no_grad():
            next_cont = torch.tanh(self.cont_actor_target(next_states))
            if self.target_noise_std > 0.0:
                noise = (self.target_noise_std * torch.randn_like(next_cont)).clamp(
                    -self.target_noise_clip, self.target_noise_clip
                )
                next_cont = (next_cont + noise).clamp(-1.0, 1.0)
            next_ch = torch.argmax(next_q_online, dim=-1)
            next_one_hot = self._channel_one_hot(next_ch, states.dtype)
            next_cq = self.cont_critic_target(torch.cat([next_states, next_cont, next_one_hot], dim=-1))
            cq_target = rewards + (1.0 - dones) * discounts * next_cq

        cq_pred = self.cont_critic(torch.cat([states, cont_executed, ch_one_hot], dim=-1))
        critic_loss = F.mse_loss(cq_pred, cq_target)

        self.critic_optimizer.zero_grad(set_to_none=True)
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.cont_critic.parameters(), self.grad_clip)
        self.critic_optimizer.step()

        # --------------------------------------------------------------------
        # 3. i-DDPG branch: deterministic policy gradient through the critic
        # --------------------------------------------------------------------
        cont_pi = torch.tanh(self.cont_actor(states))
        actor_loss = -self.cont_critic(torch.cat([states, cont_pi, ch_one_hot], dim=-1)).mean()

        self.actor_optimizer.zero_grad(set_to_none=True)
        self.critic_optimizer.zero_grad(set_to_none=True)
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.cont_actor.parameters(), self.grad_clip)
        self.actor_optimizer.step()

        # --------------------------------------------------------------------
        # 4. Target maintenance: hard sync for D3QN, Polyak for i-DDPG
        # --------------------------------------------------------------------
        self.update_count.add_(1.0)
        synced = int(self.update_count.item()) % self.target_sync_interval == 0
        with torch.no_grad():
            if synced:
                for online, target in (
                    (self.q_trunk, self.q_trunk_target),
                    (self.q_value_head, self.q_value_head_target),
                    (self.q_adv_head, self.q_adv_head_target),
                ):
                    for p, p_t in zip(online.parameters(), target.parameters()):
                        p_t.data.copy_(p.data)
            for online, target in (
                (self.cont_actor, self.cont_actor_target),
                (self.cont_critic, self.cont_critic_target),
            ):
                for p, p_t in zip(online.parameters(), target.parameters()):
                    p_t.data.mul_(1.0 - self.tau).add_(p.data, alpha=self.tau)
            self.epsilon.fill_(max(self.epsilon_min, float(self.epsilon.item()) * self.epsilon_decay))

        return {
            "loss": float(q_loss.item() + critic_loss.item() + actor_loss.item()),
            "q_loss": float(q_loss.item()),
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "lr_scale": float(lr_factor),
            "target_synced": float(synced),
            "n_step_active": float(self.n_step_active),
            "epsilon": float(self.epsilon.item()),
        }
