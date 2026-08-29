# src/baselines/dueling_q_aoi.py
# ============================================================================
# Deep Dueling Q-Network for AoI Scheduling (Dueling-Q-AoI)
#
# Baseline 8 (Category 3: SOTA AoI Models)
# Features:
# - Separate Value V(s) and Advantage A(s, a) streams
# - Discretized action grid: channels x intervals
# - Dueling aggregation: Q(s, a) = V(s) + (A(s, a) - mean(A(s, :)))
# - Double DQN target value computation with SMDP discount support
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


class DuelingQAoI(BaseRLModel):
    def __init__(
        self,
        state_dim: int = 16,
        num_channels: int = 4,
        hidden_dim: int = 64,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        epsilon_initial: float = 0.2,
        epsilon_decay: float = 0.999,
        epsilon_min: float = 0.01,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.tau = float(tau)
        self.epsilon = float(epsilon_initial)
        self.epsilon_decay = float(epsilon_decay)
        self.epsilon_min = float(epsilon_min)

        # Quantized action space grid: 5 interval levels x num_channels
        self.interval_candidates = [0.5, 1.0, 2.0, 4.0, 8.0]
        self.num_intervals = len(self.interval_candidates)
        self.num_actions = self.num_channels * self.num_intervals

        # Dueling Network
        self.trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.adv_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, self.num_actions),
        )

        # Target Network
        self.target_trunk = copy.deepcopy(self.trunk)
        self.target_value_head = copy.deepcopy(self.value_head)
        self.target_adv_head = copy.deepcopy(self.adv_head)
        for p in self.target_trunk.parameters():
            p.requires_grad = False
        for p in self.target_value_head.parameters():
            p.requires_grad = False
        for p in self.target_adv_head.parameters():
            p.requires_grad = False

        self.optimizer = optim.Adam(
            list(self.trunk.parameters())
            + list(self.value_head.parameters())
            + list(self.adv_head.parameters()),
            lr=lr,
        )

    def _forward_q(self, state: torch.Tensor, use_target: bool = False) -> torch.Tensor:
        trunk = self.target_trunk if use_target else self.trunk
        v_head = self.target_value_head if use_target else self.value_head
        a_head = self.target_adv_head if use_target else self.adv_head

        h = trunk(state)
        v = v_head(h)
        a = a_head(h)
        q = v + (a - a.mean(dim=-1, keepdim=True))
        return q

    def _action_to_tuple(self, action_idx: int) -> Tuple[float, int, float]:
        ch = action_idx % self.num_channels
        iv_idx = min(self.num_intervals - 1, action_idx // self.num_channels)
        delta = self.interval_candidates[iv_idx]
        power = 25.0
        return (float(delta), int(ch), float(power))

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            q_vals = self._forward_q(state_t, use_target=False)
            if not deterministic and np.random.rand() < self.epsilon:
                act_idx = int(np.random.randint(0, self.num_actions))
            else:
                act_idx = int(torch.argmax(q_vals, dim=-1).item())

            delta, ch, power = self._action_to_tuple(act_idx)
            raw_action = self.decoder.encode_action(delta, ch, power)

        info = {
            "action_idx": act_idx,
            "q_values": q_vals[0].cpu().numpy(),
            "raw_action": raw_action,
            "epsilon": self.epsilon,
        }
        return (delta, ch, power), raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        delta_ts = batch.get("delta_t", torch.ones_like(rewards))

        if "discount" in batch:
            discounts = batch["discount"]
        else:
            discounts = torch.pow(self.gamma, delta_ts)

        # --------------------------------------------------------------------
        # 1. Double DQN Target Calculation
        # --------------------------------------------------------------------
        with torch.no_grad():
            next_q_online = self._forward_q(next_states, use_target=False)
            next_best_actions = torch.argmax(next_q_online, dim=-1, keepdim=True)

            next_q_target = self._forward_q(next_states, use_target=True)
            target_q_val = next_q_target.gather(1, next_best_actions)
            y = rewards + (1.0 - dones) * discounts * target_q_val

        # Current Q-values
        curr_q = self._forward_q(states, use_target=False)
        # Approximate action mapping if raw action is given in batch
        if "action_idx" in batch:
            action_indices = batch["action_idx"].long().unsqueeze(1)
        else:
            # Map batch continuous action to nearest discrete action index
            actions = batch["action"]
            ch_raw = ((actions[:, 1].round().long() % self.num_channels) + self.num_channels) % self.num_channels
            action_indices = ch_raw.unsqueeze(1)

        q_pred = curr_q.gather(1, action_indices)
        loss = F.mse_loss(q_pred, y)

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(
            list(self.trunk.parameters())
            + list(self.value_head.parameters())
            + list(self.adv_head.parameters()),
            0.5,
        )
        self.optimizer.step()

        # --------------------------------------------------------------------
        # 2. Soft Target Network Update
        # --------------------------------------------------------------------
        with torch.no_grad():
            for p, p_target in zip(self.trunk.parameters(), self.target_trunk.parameters()):
                p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)
            for p, p_target in zip(self.value_head.parameters(), self.target_value_head.parameters()):
                p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)
            for p, p_target in zip(self.adv_head.parameters(), self.target_adv_head.parameters()):
                p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        return {
            "loss": float(loss.item()),
            "mean_q": float(curr_q.mean().item()),
            "epsilon": self.epsilon,
        }
