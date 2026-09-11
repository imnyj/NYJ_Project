# src/baselines/res_mapddpg.py
"""
RES-MAPDDPG -- Residual Multi-Agent Parameterized-Action-Space DDPG.

Reference
---------
J. Li, Q. Leng and M. Cheng, "Resource Allocation in NOMA-V2X Networks With
Multi-Agent Parameterized Action Space Reinforcement Learning," IEEE Transactions on
Vehicular Technology, vol. 75, no. 7, pp. 14775-14790, 2026.
DOI: 10.1109/TVT.2026.3662431

This is a REIMPLEMENTATION ADAPTED TO OUR ENVIRONMENT, not a verbatim reproduction.

What the original paper does
----------------------------
Observation: per-agent LOCAL CSI plus interference measurements, on the V2V side of a
NOMA-enabled V2X network. Action: a parameterized action -- a discrete resource-block
index together with the continuous transmit power attached to that particular block, so
the continuous parameter vector per discrete action is 1-dim. The V2I side is NOT
learned: it is handled by a separate NOMA user-grouping stage followed by convex
optimisation.

What is KEPT here
-----------------
* The res-MAPDDPG learner core: one actor emitting a continuous parameter vector for
  EVERY discrete action, one Q-network scoring all discrete actions conditioned on those
  parameters, and argmax-over-Q discrete selection.
* The residual trunk (see `_ResidualTrunk`) that gives the method its "res-" prefix.
* Shared-parameter multi-agent instantiation: one actor instance per in-range vehicle,
  all hosted at the RSU.

What is DROPPED, and why
------------------------
* The NOMA user-grouping + convex-optimisation V2I stage. Our uplink is
  orthogonal-subchannel with the existing Rayleigh SINR contention model and the
  simulator has no SIC receiver, so that stage has nothing to act on. HONEST
  CONSEQUENCE: without NOMA the method degenerates to a parameterized-action DDPG
  baseline. That is precisely the comparison we want, but the numbers produced here must
  NOT be described as a reproduction of the paper's NOMA-V2X results.
* The paper's local CSI / interference observation. We feed the RSU-side observation
  emitted by `StateVectorizer` instead, because that is what our scheduler can actually
  see. Instantaneous per-subchannel CSI is not something our environment exposes to the
  scheduler at decision time, so the paper's channel-aware advantage is unavailable to
  every baseline here, this one included.

Adaptations
-----------
* Parameter widening: the paper's per-discrete-action parameter is 1-dim (power); ours
  is 2-dim, (Delta, p). This is a pure widening of the parameter vector with no
  architectural change.
* CTDE: the paper assumes centralised training with decentralised execution. Our
  scheduler is centralised at a single RSU, so a centralised critic is our ACTUAL
  DEPLOYMENT rather than an extra assumption we are importing.
* NOT IN THE PAPER (our addition): the agent count varies as vehicles enter and leave the
  300 m RSU range, so a fixed-size joint critic input is impossible. We use a padded
  neighbour set with an explicit validity mask and permutation-invariant masked-mean
  pooling (`_pool_neighbourhood`). The paper does not specify how to handle a varying
  agent population; this is our construction.
* WEAKENING, stated plainly: `RetrospectiveReplayBuffer` stores per-vehicle transitions
  and carries no snapshot of the concurrent neighbour population, so at update time the
  neighbour set degenerates to the ego observation alone unless a caller supplies
  "neighbour_state"/"neighbour_mask" in the batch. The centralised critic is therefore
  weaker than the paper's joint critic in the default training path.
* NAMING AMBIGUITY, flagged rather than silently resolved: the librarian summary reads
  "res-MAPDDPG, a residual multi-agent parameterized-action-space DDPG" while the task
  brief glossed "res-" as "resource-efficient". We implement the residual reading (a
  residual MLP trunk), which is also the parameter-efficient one. If the intended reading
  is a resource-efficiency regulariser on the objective, this module needs revisiting.
"""

from __future__ import annotations
import copy
from typing import Any, Dict, Optional, Sequence, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM


class _ResidualBlock(nn.Module):
    """Pre-norm residual MLP block: x + W2 ReLU(W1 LayerNorm(x))."""

    def __init__(self, dim: int) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.fc2 = nn.Linear(dim, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.fc2(F.relu(self.fc1(self.norm(x))))


class _ResidualTrunk(nn.Module):
    """Input projection -> stacked residual blocks -> linear read-out."""

    def __init__(self, in_dim: int, hidden_dim: int, out_dim: int, num_blocks: int = 2) -> None:
        super().__init__()
        self.inp = nn.Linear(in_dim, hidden_dim)
        self.blocks = nn.ModuleList([_ResidualBlock(hidden_dim) for _ in range(num_blocks)])
        self.out = nn.Linear(hidden_dim, out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.inp(x))
        for block in self.blocks:
            h = block(h)
        return self.out(h)


class RESMAPDDPG(BaseRLModel):
    """
    Residual multi-agent parameterized-action-space DDPG (Li et al., IEEE TVT 2026).

    Action layout produced by this model:
      * discrete: one subchannel in {0 .. num_channels-1}, chosen by argmax over Q;
      * continuous: the 2-dim parameter vector (Delta, p) attached to that subchannel,
        emitted in tanh space and mapped onto the environment's bounds by the
        ActionDecoder (geometric for Delta, linear for power).
    """

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 128,
        num_res_blocks: int = 2,
        ctx_dim: int = 32,
        max_agents: int = 16,
        lr_actor: float = 1e-4,
        lr_critic: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        epsilon_initial: float = 0.2,
        epsilon_decay: float = 0.999,
        epsilon_min: float = 0.01,
        param_noise_std: float = 0.1,
        grad_clip: float = 0.5,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.epsilon_decay = float(epsilon_decay)
        self.epsilon_min = float(epsilon_min)
        self.param_noise_std = float(param_noise_std)
        self.grad_clip = float(grad_clip)
        self.max_agents = max(1, int(max_agents))

        # Continuous parameters per discrete action: (Delta, p) -> 2 per subchannel.
        self.param_dim = 2
        self.total_param_dim = self.num_channels * self.param_dim

        # Exploration state lives in a buffer so the hot-swap manager, which copies
        # parameters AND buffers between the Act and Rest models, carries it across.
        self.register_buffer("epsilon", torch.tensor(float(epsilon_initial)))

        # --- Parameterized-action actor: state -> parameters of EVERY discrete action.
        self.param_actor = _ResidualTrunk(self.state_dim, hidden_dim, self.total_param_dim, num_res_blocks)

        # --- Permutation-invariant neighbourhood encoder (our addition, see docstring).
        self.neighbour_encoder = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, ctx_dim),
        )

        # --- Centralised critic: Q(s, x_0..x_{K-1}, pooled neighbourhood) -> one Q per subchannel.
        self.critic = _ResidualTrunk(
            self.state_dim + self.total_param_dim + ctx_dim, hidden_dim, self.num_channels, num_res_blocks
        )

        self.param_actor_target = copy.deepcopy(self.param_actor)
        self.neighbour_encoder_target = copy.deepcopy(self.neighbour_encoder)
        self.critic_target = copy.deepcopy(self.critic)
        for module in (self.param_actor_target, self.neighbour_encoder_target, self.critic_target):
            for p in module.parameters():
                p.requires_grad = False

        self.actor_optimizer = optim.Adam(self.param_actor.parameters(), lr=lr_actor)
        self.critic_params = list(self.critic.parameters()) + list(self.neighbour_encoder.parameters())
        self.critic_optimizer = optim.Adam(self.critic_params, lr=lr_critic)

    # ------------------------------------------------------------------
    # Action-space plumbing
    # ------------------------------------------------------------------
    def _grant_from_unit_action(
        self, cont: Union[np.ndarray, torch.Tensor, Sequence[float]], ch: int
    ) -> Tuple[float, int, float]:
        """
        Map a bounded continuous pair in [-1, 1] plus a subchannel index onto the
        environment's grant tuple (delta_s, ch_idx, power_dbm).

        Delta goes through `ActionDecoder.delta_from_unit`, i.e. the GEOMETRIC map the
        design mandates. `ActionDecoder.decode_action` is deliberately NOT used for Delta
        because it interpolates linearly; the bounds themselves are still read off the
        decoder and never restated here. Power is linear because dBm is already a
        logarithmic unit.
        """
        dec = self.decoder
        u_delta = 0.5 * (float(np.clip(float(cont[0]), -1.0, 1.0)) + 1.0)
        u_power = 0.5 * (float(np.clip(float(cont[1]), -1.0, 1.0)) + 1.0)
        delta = dec.delta_from_unit(u_delta)
        power = dec.p_min + u_power * (dec.p_max - dec.p_min)
        return float(delta), int(ch) % self.num_channels, float(power)

    def _pool_neighbourhood(
        self,
        states: torch.Tensor,
        neighbour_states: Optional[torch.Tensor],
        neighbour_mask: Optional[torch.Tensor],
        encoder: nn.Module,
    ) -> torch.Tensor:
        """
        Permutation-invariant masked-mean pooling over a padded neighbour set.

        NOT from the paper. The paper's centralised critic assumes a fixed agent count;
        ours varies as vehicles enter and leave the RSU range, so the set is padded to
        `max_agents` and every slot carries a 0/1 validity flag. Pooling is a masked mean,
        which is invariant to the ordering of the padded slots.

        When no neighbour set is supplied (the default: our replay buffer stores
        per-vehicle transitions only) the set degenerates to the ego observation alone.
        """
        if neighbour_states is None:
            neighbour_states = states.unsqueeze(1)
            neighbour_mask = torch.ones(
                states.shape[0], 1, dtype=states.dtype, device=states.device
            )
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

        emb = encoder(neighbour_states)
        mask = neighbour_mask.unsqueeze(-1)
        return (emb * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)

    def _q_values(
        self,
        states: torch.Tensor,
        params: torch.Tensor,
        neighbour_states: Optional[torch.Tensor] = None,
        neighbour_mask: Optional[torch.Tensor] = None,
        use_target: bool = False,
    ) -> torch.Tensor:
        encoder = self.neighbour_encoder_target if use_target else self.neighbour_encoder
        critic = self.critic_target if use_target else self.critic
        ctx = self._pool_neighbourhood(states, neighbour_states, neighbour_mask, encoder)
        return critic(torch.cat([states, params, ctx], dim=-1))

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
            params = torch.tanh(self.param_actor(state_t))
            if not deterministic and self.param_noise_std > 0.0:
                params = (params + self.param_noise_std * torch.randn_like(params)).clamp(-1.0, 1.0)
            q_values = self._q_values(state_t, params)

            if not deterministic and np.random.rand() < eps:
                ch = int(np.random.randint(0, self.num_channels))
            else:
                ch = int(torch.argmax(q_values, dim=-1).item())

            cont = params[0, ch * self.param_dim : (ch + 1) * self.param_dim].cpu().numpy()

        decoded = self._grant_from_unit_action(cont, ch)
        # Positional convention shared by every baseline in this package:
        # raw_action = [continuous Delta term, subchannel index, continuous power term].
        raw_action = np.array([float(cont[0]), float(ch), float(cont[1])], dtype=np.float32)
        info = {
            "action_idx": int(ch),
            "q_values": q_values[0].cpu().numpy(),
            "raw_action": raw_action,
            "epsilon": eps,
        }
        return decoded, raw_action, info

    def _resolve_channel_indices(self, batch: Dict[str, torch.Tensor], device: torch.device) -> torch.Tensor:
        """
        The discrete index this model committed to. Preferred path: the verbatim
        "action_idx" carried by the replay buffer. Fallback for older transitions that
        predate the index: raw_action[1], which stores the same subchannel index, so the
        fallback is exact rather than approximate here.
        """
        if "action_idx" in batch:
            idx = batch["action_idx"].to(device=device).long().reshape(-1)
        else:
            idx = batch["action"][:, 1].to(device=device).round().long().reshape(-1)
        return ((idx % self.num_channels) + self.num_channels) % self.num_channels

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        actions = batch["action"]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        device = states.device

        # SMDP discount from THIS model's gamma (see BaseRLModel.smdp_discounts).
        discounts = self.smdp_discounts(batch, rewards)

        neighbour_states = batch.get("neighbour_state", batch.get("neighbor_state"))
        neighbour_mask = batch.get("neighbour_mask", batch.get("neighbor_mask"))
        next_neighbour_states = batch.get("next_neighbour_state", batch.get("next_neighbor_state"))
        next_neighbour_mask = batch.get("next_neighbour_mask", batch.get("next_neighbor_mask"))

        ch_indices = self._resolve_channel_indices(batch, device).unsqueeze(1)
        cont_executed = actions[:, [0, 2]].to(device).clamp(-1.0, 1.0)

        # --------------------------------------------------------------------
        # 1. Centralised critic update
        # --------------------------------------------------------------------
        with torch.no_grad():
            next_params = torch.tanh(self.param_actor_target(next_states))
            next_q = self._q_values(
                next_states, next_params, next_neighbour_states, next_neighbour_mask, use_target=True
            )
            target_q = rewards + (1.0 - dones) * discounts * next_q.max(dim=-1, keepdim=True)[0]

        # Off-policy credit assignment: the critic must score the parameter vector that
        # was ACTUALLY executed on the chosen subchannel, not the one the current actor
        # would emit today. The other subchannels keep the actor's present parameters,
        # which is what P-DQN-style critics condition on.
        params_now = torch.tanh(self.param_actor(states)).detach()
        params_executed = params_now.clone()
        rows = torch.arange(states.shape[0], device=device)
        flat_ch = ch_indices.reshape(-1)
        params_executed[rows, flat_ch * self.param_dim] = cont_executed[:, 0]
        params_executed[rows, flat_ch * self.param_dim + 1] = cont_executed[:, 1]

        q_all = self._q_values(states, params_executed, neighbour_states, neighbour_mask)
        q_pred = q_all.gather(1, ch_indices)
        critic_loss = F.mse_loss(q_pred, target_q)

        self.critic_optimizer.zero_grad(set_to_none=True)
        self.actor_optimizer.zero_grad(set_to_none=True)
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.critic_params, self.grad_clip)
        self.critic_optimizer.step()

        # --------------------------------------------------------------------
        # 2. Parameter-actor update (deterministic policy gradient through Q)
        # --------------------------------------------------------------------
        params_grad = torch.tanh(self.param_actor(states))
        q_actor = self._q_values(states, params_grad, neighbour_states, neighbour_mask)
        actor_loss = -q_actor.mean()

        self.actor_optimizer.zero_grad(set_to_none=True)
        self.critic_optimizer.zero_grad(set_to_none=True)
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.param_actor.parameters(), self.grad_clip)
        self.actor_optimizer.step()

        # --------------------------------------------------------------------
        # 3. Polyak target updates and exploration decay
        # --------------------------------------------------------------------
        with torch.no_grad():
            for online, target in (
                (self.param_actor, self.param_actor_target),
                (self.neighbour_encoder, self.neighbour_encoder_target),
                (self.critic, self.critic_target),
            ):
                for p, p_t in zip(online.parameters(), target.parameters()):
                    p_t.data.mul_(1.0 - self.tau).add_(p.data, alpha=self.tau)
            self.epsilon.fill_(max(self.epsilon_min, float(self.epsilon.item()) * self.epsilon_decay))

        return {
            "loss": float(critic_loss.item() + actor_loss.item()),
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "mean_q": float(q_all.mean().item()),
            "epsilon": float(self.epsilon.item()),
        }
