# src/baselines/hybrid_sac.py
# ============================================================================
# Hybrid Soft Actor-Critic (H-SAC)
#
# Baseline 2 (Category 1: Basic Models)
# Features:
# - Gumbel-Softmax differentiable discrete channel distribution
# - Squashed Gaussian (Tanh / reparameterized) continuous interval & power heads
# - Twin Q-critics Q1(s, a), Q2(s, a) with Polyak target network soft updates
# - Auto-tuned entropy temperature (alpha) optimization
# - SMDP variable-interval discount support
# ============================================================================

from __future__ import annotations
import copy
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Normal
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM


class HybridSAC(BaseRLModel):
    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 64,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        target_entropy: Optional[float] = None,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.tau = float(tau)

        # Total action representation dimension for Q-critics:
        # num_channels (one-hot or logits) + 2 (delta_raw, power_raw) = num_channels + 2
        self.act_dim = self.num_channels + 2

        # Actor Network: produces discrete logits + continuous mean & log_std
        self.actor_trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.ch_head = nn.Linear(hidden_dim, self.num_channels)
        self.cont_mean_head = nn.Linear(hidden_dim, 2)
        self.cont_log_std_head = nn.Linear(hidden_dim, 2)

        # Twin Q-Critics
        self.q1 = nn.Sequential(
            nn.Linear(self.state_dim + 3, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.q2 = nn.Sequential(
            nn.Linear(self.state_dim + 3, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

        # Target Q-Critics
        self.q1_target = copy.deepcopy(self.q1)
        self.q2_target = copy.deepcopy(self.q2)
        for p in self.q1_target.parameters():
            p.requires_grad = False
        for p in self.q2_target.parameters():
            p.requires_grad = False

        # Entropy temperature alpha
        self.target_entropy = target_entropy if target_entropy is not None else -float(2 + np.log(self.num_channels))
        self.log_alpha = nn.Parameter(torch.zeros(1))

        self.actor_optimizer = optim.Adam(
            list(self.actor_trunk.parameters())
            + list(self.ch_head.parameters())
            + list(self.cont_mean_head.parameters())
            + list(self.cont_log_std_head.parameters()),
            lr=lr,
        )
        self.critic_optimizer = optim.Adam(
            list(self.q1.parameters()) + list(self.q2.parameters()), lr=lr
        )
        self.alpha_optimizer = optim.Adam([self.log_alpha], lr=lr)

    @property
    def alpha(self) -> torch.Tensor:
        return torch.exp(self.log_alpha)

    def _sample_action(
        self, state: torch.Tensor, deterministic: bool = False
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        feat = self.actor_trunk(state)
        ch_logits = self.ch_head(feat)
        cont_mean = self.cont_mean_head(feat)
        cont_log_std = torch.clamp(self.cont_log_std_head(feat), -20.0, 2.0)
        cont_std = torch.exp(cont_log_std)

        if deterministic:
            ch_idx = torch.argmax(ch_logits, dim=-1, keepdim=True).float()
            cont_action = cont_mean
            log_prob = torch.zeros((state.shape[0], 1), device=state.device)
        else:
            # Gumbel-Softmax discrete sample
            ch_probs = F.softmax(ch_logits, dim=-1)
            ch_dist = torch.distributions.Categorical(probs=ch_probs)
            ch_sample = ch_dist.sample()
            ch_idx = ch_sample.unsqueeze(1).float()
            ch_log_p = ch_dist.log_prob(ch_sample).unsqueeze(1)

            # Continuous Gaussian sample with reparameterization
            norm_dist = Normal(cont_mean, cont_std)
            cont_action = norm_dist.rsample()
            cont_log_p = norm_dist.log_prob(cont_action).sum(dim=-1, keepdim=True)

            log_prob = ch_log_p + cont_log_p

        # Full 3-dim action representation: [delta_raw, ch_idx, p_raw]
        full_action = torch.cat([cont_action[:, :1], ch_idx, cont_action[:, 1:2]], dim=-1)
        return full_action, log_prob, ch_logits

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            act_t, log_p, _ = self._sample_action(state_t, deterministic=deterministic)
            raw_action = act_t[0].cpu().numpy().astype(np.float32)

        decoded = self.decoder.decode_action(raw_action)
        info = {"raw_action": raw_action, "log_prob": float(log_p[0].item())}
        return decoded, raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        actions = batch["action"]  # [B, 3]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        delta_ts = batch.get("delta_t", torch.ones_like(rewards))

        if "discount" in batch:
            discounts = batch["discount"]
        else:
            discounts = torch.pow(self.gamma, delta_ts)

        # --------------------------------------------------------------------
        # 1. Update Critics
        # --------------------------------------------------------------------
        with torch.no_grad():
            next_actions, next_log_p, _ = self._sample_action(next_states, deterministic=False)
            sa_next = torch.cat([next_states, next_actions[:, :3]], dim=-1)
            target_q1 = self.q1_target(sa_next)
            target_q2 = self.q2_target(sa_next)
            target_q = torch.min(target_q1, target_q2) - self.alpha * next_log_p
            target_q_val = rewards + (1.0 - dones) * discounts * target_q

        sa = torch.cat([states, actions[:, :3]], dim=-1)
        q1_pred = self.q1(sa)
        q2_pred = self.q2(sa)
        q1_loss = F.mse_loss(q1_pred, target_q_val)
        q2_loss = F.mse_loss(q2_pred, target_q_val)
        critic_loss = q1_loss + q2_loss

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(list(self.q1.parameters()) + list(self.q2.parameters()), 0.5)
        self.critic_optimizer.step()

        # --------------------------------------------------------------------
        # 2. Update Actor
        # --------------------------------------------------------------------
        sampled_actions, log_p, _ = self._sample_action(states, deterministic=False)
        sa_sampled = torch.cat([states, sampled_actions[:, :3]], dim=-1)
        q_sampled = torch.min(self.q1(sa_sampled), self.q2(sa_sampled))
        actor_loss = (self.alpha.detach() * log_p - q_sampled).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.actor_trunk.parameters(), 0.5)
        self.actor_optimizer.step()

        # --------------------------------------------------------------------
        # 3. Update Temperature Alpha
        # --------------------------------------------------------------------
        alpha_loss = -(self.log_alpha * (log_p + self.target_entropy).detach()).mean()
        self.alpha_optimizer.zero_grad()
        alpha_loss.backward()
        self.alpha_optimizer.step()

        # --------------------------------------------------------------------
        # 4. Soft Target Update
        # --------------------------------------------------------------------
        with torch.no_grad():
            for p, p_target in zip(self.q1.parameters(), self.q1_target.parameters()):
                p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)
            for p, p_target in zip(self.q2.parameters(), self.q2_target.parameters()):
                p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)

        total_loss = float(critic_loss.item() + actor_loss.item())
        return {
            "loss": total_loss,
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "alpha": float(self.alpha.item()),
        }
