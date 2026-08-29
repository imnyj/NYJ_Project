# src/baselines/hybrid_td3.py
# ============================================================================
# Hybrid Twin Delayed Deep Deterministic Policy Gradient (H-TD3)
#
# Baseline 3 (Category 1: Basic Models)
# Features:
# - Twin Q-critics Q1(s, a), Q2(s, a) with target networks
# - Target action smoothing with clipped Gaussian noise
# - Delayed policy updates (policy_freq=2)
# - Continuous interval/power + relaxed channel actor
# - SMDP variable-interval discount support
# ============================================================================

from __future__ import annotations
import copy
from typing import Any, Dict, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from src.baselines.base_agent import BaseRLModel


class HybridTD3(BaseRLModel):
    def __init__(
        self,
        state_dim: int = 16,
        num_channels: int = 4,
        hidden_dim: int = 64,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        policy_noise: float = 0.2,
        noise_clip: float = 0.5,
        policy_freq: int = 2,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.policy_noise = float(policy_noise)
        self.noise_clip = float(noise_clip)
        self.policy_freq = int(policy_freq)
        self.total_it = 0

        # Actor: outputs [delta_raw, ch_raw, p_raw]
        self.actor = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 3),
        )
        self.actor_target = copy.deepcopy(self.actor)
        for p in self.actor_target.parameters():
            p.requires_grad = False

        # Twin Q-Critics: Q(s, a)
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
        self.q1_target = copy.deepcopy(self.q1)
        self.q2_target = copy.deepcopy(self.q2)
        for p in self.q1_target.parameters():
            p.requires_grad = False
        for p in self.q2_target.parameters():
            p.requires_grad = False

        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)
        self.critic_optimizer = optim.Adam(
            list(self.q1.parameters()) + list(self.q2.parameters()), lr=lr
        )

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            act = self.actor(state_t)[0]
            if not deterministic:
                noise = torch.randn_like(act) * 0.1
                act = act + noise
            raw_action = act.cpu().numpy().astype(np.float32)

        # Discretize channel index
        ch = int(round(float(raw_action[1]))) % self.num_channels
        raw_action_formatted = np.array([raw_action[0], float(ch), raw_action[2]], dtype=np.float32)

        decoded = self.decoder.decode_action(raw_action_formatted)
        return decoded, raw_action_formatted, {"raw_action": raw_action_formatted}

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        self.total_it += 1
        states = batch["state"]
        actions = batch["action"][:, :3]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        delta_ts = batch.get("delta_t", torch.ones_like(rewards))

        if "discount" in batch:
            discounts = batch["discount"]
        else:
            discounts = torch.pow(self.gamma, delta_ts)

        # --------------------------------------------------------------------
        # 1. Target Action Smoothing & Target Q
        # --------------------------------------------------------------------
        with torch.no_grad():
            noise = (torch.randn_like(actions) * self.policy_noise).clamp(
                -self.noise_clip, self.noise_clip
            )
            next_actions = self.actor_target(next_states) + noise
            sa_next = torch.cat([next_states, next_actions], dim=-1)
            target_q1 = self.q1_target(sa_next)
            target_q2 = self.q2_target(sa_next)
            target_q = torch.min(target_q1, target_q2)
            target_q_val = rewards + (1.0 - dones) * discounts * target_q

        sa = torch.cat([states, actions], dim=-1)
        q1_pred = self.q1(sa)
        q2_pred = self.q2(sa)
        critic_loss = F.mse_loss(q1_pred, target_q_val) + F.mse_loss(q2_pred, target_q_val)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(list(self.q1.parameters()) + list(self.q2.parameters()), 0.5)
        self.critic_optimizer.step()

        actor_loss_val = 0.0
        # --------------------------------------------------------------------
        # 2. Delayed Policy Updates
        # --------------------------------------------------------------------
        if self.total_it % self.policy_freq == 0:
            actor_actions = self.actor(states)
            sa_actor = torch.cat([states, actor_actions], dim=-1)
            actor_loss = -self.q1(sa_actor).mean()

            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            nn.utils.clip_grad_norm_(self.actor.parameters(), 0.5)
            self.actor_optimizer.step()
            actor_loss_val = float(actor_loss.item())

            # Soft target updates
            with torch.no_grad():
                for p, p_target in zip(self.actor.parameters(), self.actor_target.parameters()):
                    p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)
                for p, p_target in zip(self.q1.parameters(), self.q1_target.parameters()):
                    p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)
                for p, p_target in zip(self.q2.parameters(), self.q2_target.parameters()):
                    p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)

        return {
            "loss": float(critic_loss.item()),
            "critic_loss": float(critic_loss.item()),
            "actor_loss": actor_loss_val,
        }
