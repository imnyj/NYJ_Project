# src/baselines/hybrid_ppo.py
# ============================================================================
# Hybrid Proximal Policy Optimization (H-PPO)
#
# Baseline 1 (Category 1: Basic Models)
# Features:
# - Categorical head for discrete subchannel selection
# - Gaussian heads (mean & state-independent/conditioned log_std) for continuous
#   inter-update interval Delta and transmission power p
# - Critic network for state value estimation V(s)
# - Clipped surrogate objective + entropy bonus + MSE value loss
# - SMDP variable-interval discount support
# ============================================================================

from __future__ import annotations
from typing import Any, Dict, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical, Normal
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM


class HybridPPO(BaseRLModel):
    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 64,
        lr: float = 3e-4,
        gamma: float = 0.99,
        clip_ratio: float = 0.2,
        entropy_coef: float = 0.01,
        value_coef: float = 0.5,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.clip_ratio = float(clip_ratio)
        self.entropy_coef = float(entropy_coef)
        self.value_coef = float(value_coef)

        # Actor trunk & heads
        self.actor_trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
        )
        self.ch_head = nn.Linear(hidden_dim, self.num_channels)
        self.cont_head = nn.Linear(hidden_dim, 2)  # [delta_raw, power_raw]
        self.log_std = nn.Parameter(torch.zeros(2))

        # Critic network
        self.critic = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )

        self.optimizer = optim.Adam(self.parameters(), lr=lr)

    def _get_distributions(self, state: torch.Tensor) -> Tuple[Categorical, Normal, torch.Tensor]:
        feat = self.actor_trunk(state)
        ch_logits = self.ch_head(feat)
        ch_dist = Categorical(logits=ch_logits)
        cont_mean = self.cont_head(feat)
        cont_std = torch.exp(torch.clamp(self.log_std, -20.0, 2.0))
        cont_dist = Normal(cont_mean, cont_std)
        return ch_dist, cont_dist, feat

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            ch_dist, cont_dist, _ = self._get_distributions(state_t)
            v_val = self.critic(state_t).item()

            if deterministic:
                ch = int(torch.argmax(ch_dist.logits, dim=-1).item())
                cont = cont_dist.mean[0]
            else:
                ch = int(ch_dist.sample().item())
                cont = cont_dist.sample()[0]

            delta_raw = float(cont[0].item())
            p_raw = float(cont[1].item())
            raw_action = np.array([delta_raw, float(ch), p_raw], dtype=np.float32)

            ch_logp = ch_dist.log_prob(torch.tensor([ch], device=state_t.device)).item()
            cont_logp = cont_dist.log_prob(cont.unsqueeze(0)).sum(dim=-1).item()
            total_logp = ch_logp + cont_logp

        decoded = self.decoder.decode_action(raw_action)
        info = {"value": v_val, "log_prob": total_logp, "raw_action": raw_action}
        return decoded, raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        actions = batch["action"]  # [B, 3] -> [delta_raw, ch_idx, p_raw]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        delta_ts = batch.get("delta_t", torch.ones_like(rewards))

        # SMDP discount factor gamma^Delta
        if "discount" in batch:
            discounts = batch["discount"]
        else:
            discounts = torch.pow(self.gamma, delta_ts)

        # Target value calculation
        with torch.no_grad():
            next_v = self.critic(next_states)
            target_v = rewards + (1.0 - dones) * discounts * next_v

        v_pred = self.critic(states)
        value_loss = nn.MSELoss()(v_pred, target_v)

        # Advantage
        advantages = (target_v - v_pred).detach()
        adv_std = advantages.std() + 1e-8
        norm_advantages = (advantages - advantages.mean()) / adv_std

        # Action distributions under current policy
        ch_dist, cont_dist, _ = self._get_distributions(states)
        ch_targets = ((actions[:, 1].round().long() % self.num_channels) + self.num_channels) % self.num_channels
        cont_targets = actions[:, [0, 2]]

        ch_log_prob = ch_dist.log_prob(ch_targets).unsqueeze(1)
        cont_log_prob = cont_dist.log_prob(cont_targets).sum(dim=-1, keepdim=True)
        curr_log_prob = ch_log_prob + cont_log_prob

        # Old log prob (use current log prob for single-step standard update)
        old_log_prob = curr_log_prob.detach()
        ratio = torch.exp(curr_log_prob - old_log_prob)
        surr1 = ratio * norm_advantages
        surr2 = torch.clamp(ratio, 1.0 - self.clip_ratio, 1.0 + self.clip_ratio) * norm_advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        entropy = ch_dist.entropy().mean() + cont_dist.entropy().sum(dim=-1).mean()
        total_loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy

        self.optimizer.zero_grad()
        total_loss.backward()
        nn.utils.clip_grad_norm_(self.parameters(), max_norm=0.5)
        self.optimizer.step()

        return {
            "loss": float(total_loss.item()),
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy": float(entropy.item()),
        }
