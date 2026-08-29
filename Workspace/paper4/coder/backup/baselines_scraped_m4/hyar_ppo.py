# src/baselines/hyar_ppo.py
# ============================================================================
# Hybrid Action Representation PPO (HyAR-PPO / Branching PPO)
#
# Baseline 5 (Category 2: Latest / Hybrid Models)
# Features:
# - Channel selection discrete head
# - Discrete channel embedding layer
# - Channel-conditioned continuous branch for inter-update interval & power
# - Joint PPO policy optimization with SMDP discount support
# ============================================================================

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical, Normal
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM


class HyARPPO(BaseRLModel):
    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 64,
        embed_dim: int = 8,
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
        self.embed_dim = int(embed_dim)

        # Shared Trunk
        self.trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
        )

        # Discrete Channel Head & Embedding
        self.ch_head = nn.Linear(hidden_dim, self.num_channels)
        self.ch_embed = nn.Embedding(self.num_channels, self.embed_dim)

        # Channel-Conditioned Continuous Head
        self.cont_branch = nn.Sequential(
            nn.Linear(hidden_dim + self.embed_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 2),  # [delta_raw, power_raw]
        )
        self.log_std = nn.Parameter(torch.zeros(2))

        # Critic
        self.critic = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )

        self.optimizer = optim.Adam(self.parameters(), lr=lr)

    def _forward_actor(
        self, state: torch.Tensor, ch_given: Optional[torch.Tensor] = None
    ) -> Tuple[Categorical, Normal, torch.Tensor]:
        h = self.trunk(state)
        ch_logits = self.ch_head(h)
        ch_dist = Categorical(logits=ch_logits)

        if ch_given is None:
            ch_idx = ch_dist.sample()
        else:
            ch_idx = ch_given

        ch_emb = self.ch_embed(ch_idx)
        cont_feat = torch.cat([h, ch_emb], dim=-1)
        cont_mean = self.cont_branch(cont_feat)
        cont_std = torch.exp(torch.clamp(self.log_std, -20.0, 2.0))
        cont_dist = Normal(cont_mean, cont_std)

        return ch_dist, cont_dist, ch_idx

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            h = self.trunk(state_t)
            ch_logits = self.ch_head(h)
            ch_dist = Categorical(logits=ch_logits)

            if deterministic:
                ch = int(torch.argmax(ch_logits, dim=-1).item())
            else:
                ch = int(ch_dist.sample().item())

            ch_tensor = torch.tensor([ch], device=state_t.device)
            ch_emb = self.ch_embed(ch_tensor)
            cont_feat = torch.cat([h, ch_emb], dim=-1)
            cont_mean = self.cont_branch(cont_feat)
            cont_std = torch.exp(torch.clamp(self.log_std, -20.0, 2.0))
            cont_dist = Normal(cont_mean, cont_std)

            if deterministic:
                cont = cont_mean[0]
            else:
                cont = cont_dist.sample()[0]

            delta_raw = float(cont[0].item())
            p_raw = float(cont[1].item())
            raw_action = np.array([delta_raw, float(ch), p_raw], dtype=np.float32)

            ch_logp = ch_dist.log_prob(ch_tensor).item()
            cont_logp = cont_dist.log_prob(cont.unsqueeze(0)).sum(dim=-1).item()
            total_logp = ch_logp + cont_logp
            v_val = self.critic(state_t).item()

        decoded = self.decoder.decode_action(raw_action)
        info = {"value": v_val, "log_prob": total_logp, "raw_action": raw_action}
        return decoded, raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        actions = batch["action"]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        delta_ts = batch.get("delta_t", torch.ones_like(rewards))

        if "discount" in batch:
            discounts = batch["discount"]
        else:
            discounts = torch.pow(self.gamma, delta_ts)

        # Critic Target
        with torch.no_grad():
            next_v = self.critic(next_states)
            target_v = rewards + (1.0 - dones) * discounts * next_v

        v_pred = self.critic(states)
        value_loss = nn.MSELoss()(v_pred, target_v)

        advantages = (target_v - v_pred).detach()
        adv_std = advantages.std() + 1e-8
        norm_advantages = (advantages - advantages.mean()) / adv_std

        # Actor evaluation conditioned on taken actions
        ch_targets = ((actions[:, 1].round().long() % self.num_channels) + self.num_channels) % self.num_channels
        cont_targets = actions[:, [0, 2]]

        ch_dist, cont_dist, _ = self._forward_actor(states, ch_given=ch_targets)
        ch_log_prob = ch_dist.log_prob(ch_targets).unsqueeze(1)
        cont_log_prob = cont_dist.log_prob(cont_targets).sum(dim=-1, keepdim=True)
        curr_log_prob = ch_log_prob + cont_log_prob

        old_log_prob = curr_log_prob.detach()
        ratio = torch.exp(curr_log_prob - old_log_prob)
        surr1 = ratio * norm_advantages
        surr2 = torch.clamp(ratio, 1.0 - self.clip_ratio, 1.0 + self.clip_ratio) * norm_advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        entropy = ch_dist.entropy().mean() + cont_dist.entropy().sum(dim=-1).mean()
        total_loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy

        self.optimizer.zero_grad()
        total_loss.backward()
        nn.utils.clip_grad_norm_(self.parameters(), 0.5)
        self.optimizer.step()

        return {
            "loss": float(total_loss.item()),
            "policy_loss": float(policy_loss.item()),
            "value_loss": float(value_loss.item()),
            "entropy": float(entropy.item()),
        }
