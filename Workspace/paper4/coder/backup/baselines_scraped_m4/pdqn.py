# src/baselines/pdqn.py
# ============================================================================
# Multi-Pass Parameterized Action Deep Q-Network (P-DQN / MP-DQN)
#
# Baseline 6 (Category 2: Latest / Hybrid Models)
# Features:
# - Parameter Actor: outputs channel-specific continuous parameters [Delta_k, p_k] for each channel k
# - Multi-Pass Q-Network: evaluates Q(s, k, x_k) for all discrete channels
# - Argmax channel selection with epsilon-greedy exploration
# - Target Q and Parameter networks with Polyak soft updates
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
from src.rl_interface import STATE_DIM


class MPDQN(BaseRLModel):
    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 64,
        lr_actor: float = 1e-4,
        lr_critic: float = 3e-4,
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

        # Parameter Actor: outputs [delta_k, p_k] for all k in 0..num_channels-1 (total size: num_channels * 2)
        self.param_actor = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, self.num_channels * 2),
        )
        self.param_actor_target = copy.deepcopy(self.param_actor)
        for p in self.param_actor_target.parameters():
            p.requires_grad = False

        # Q-Network: takes state + all parameters and predicts Q-value for each channel
        self.q_net = nn.Sequential(
            nn.Linear(self.state_dim + self.num_channels * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, self.num_channels),
        )
        self.q_net_target = copy.deepcopy(self.q_net)
        for p in self.q_net_target.parameters():
            p.requires_grad = False

        self.actor_optimizer = optim.Adam(self.param_actor.parameters(), lr=lr_actor)
        self.critic_optimizer = optim.Adam(self.q_net.parameters(), lr=lr_critic)

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            all_params = self.param_actor(state_t)  # [1, num_channels * 2]
            q_values = self.q_net(torch.cat([state_t, all_params], dim=-1))  # [1, num_channels]

            if not deterministic and np.random.rand() < self.epsilon:
                ch = int(np.random.randint(0, self.num_channels))
            else:
                ch = int(torch.argmax(q_values, dim=-1).item())

            delta_raw = float(all_params[0, ch * 2].item())
            p_raw = float(all_params[0, ch * 2 + 1].item())
            raw_action = np.array([delta_raw, float(ch), p_raw], dtype=np.float32)

        decoded = self.decoder.decode_action(raw_action)
        info = {
            "q_values": q_values[0].cpu().numpy(),
            "raw_action": raw_action,
            "epsilon": self.epsilon,
        }
        return decoded, raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        states = batch["state"]
        actions = batch["action"]  # [B, 3] -> [delta_raw, ch, p_raw]
        rewards = batch["reward"]
        next_states = batch["next_state"]
        dones = batch["done"]
        delta_ts = batch.get("delta_t", torch.ones_like(rewards))

        if "discount" in batch:
            discounts = batch["discount"]
        else:
            discounts = torch.pow(self.gamma, delta_ts)

        ch_indices = (((actions[:, 1].round().long() % self.num_channels) + self.num_channels) % self.num_channels).unsqueeze(1)  # [B, 1]

        # --------------------------------------------------------------------
        # 1. Critic (Q-Network) Update
        # --------------------------------------------------------------------
        with torch.no_grad():
            next_params = self.param_actor_target(next_states)
            next_q_all = self.q_net_target(torch.cat([next_states, next_params], dim=-1))
            next_max_q = torch.max(next_q_all, dim=-1, keepdim=True)[0]
            target_q = rewards + (1.0 - dones) * discounts * next_max_q

        curr_params = self.param_actor(states)
        q_all = self.q_net(torch.cat([states, curr_params.detach()], dim=-1))
        q_pred = q_all.gather(1, ch_indices)

        critic_loss = F.mse_loss(q_pred, target_q)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        nn.utils.clip_grad_norm_(self.q_net.parameters(), 0.5)
        self.critic_optimizer.step()

        # --------------------------------------------------------------------
        # 2. Parameter Actor Update
        # --------------------------------------------------------------------
        curr_params_grad = self.param_actor(states)
        q_all_actor = self.q_net(torch.cat([states, curr_params_grad], dim=-1))
        actor_loss = -q_all_actor.mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        nn.utils.clip_grad_norm_(self.param_actor.parameters(), 0.5)
        self.actor_optimizer.step()

        # --------------------------------------------------------------------
        # 3. Soft Target Update & Epsilon Decay
        # --------------------------------------------------------------------
        with torch.no_grad():
            for p, p_target in zip(self.q_net.parameters(), self.q_net_target.parameters()):
                p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)
            for p, p_target in zip(self.param_actor.parameters(), self.param_actor_target.parameters()):
                p_target.data.copy_(self.tau * p.data + (1.0 - self.tau) * p_target.data)

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        total_loss = float(critic_loss.item() + actor_loss.item())
        return {
            "loss": total_loss,
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "epsilon": self.epsilon,
        }


# Alias for PDQN
PDQN = MPDQN
