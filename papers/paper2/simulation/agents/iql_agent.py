"""
iql_agent.py
============
Independent Q-Learning (IQL) baseline.
Each vehicle learns independently without federated model sharing.
"""

import numpy as np
import random
import copy
from typing import Dict, List, Optional, Tuple
from collections import deque

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class IQLAgent:
    """
    Independent Q-Learning agent.
    Separate Q-network per agent; no communication/federation.
    """

    def __init__(
        self,
        agent_id: str,
        obs_dim: int,
        action_dims: Tuple[int, int, int, int],
        lr: float = 1e-3,
        gamma: float = 0.99,
        tau: float = 0.005,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        batch_size: int = 256,
        buffer_size: int = 50000,
        seed: int = 42,
    ):
        self.agent_id    = agent_id
        self.obs_dim     = obs_dim
        self.action_dims = action_dims
        self.gamma       = gamma
        self.tau         = tau
        self.batch_size  = batch_size
        self.epsilon     = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self._rng        = random.Random(seed)

        self._buffer = deque(maxlen=buffer_size)

        if TORCH_AVAILABLE:
            total_act = sum(action_dims)
            # Separate Q-heads for each sub-action
            self.q_net = nn.Sequential(
                nn.Linear(obs_dim, 128), nn.ReLU(),
                nn.Linear(128, 128), nn.ReLU(),
                nn.Linear(128, total_act)
            )
            self.q_target = copy.deepcopy(self.q_net)
            self.opt = optim.Adam(self.q_net.parameters(), lr=lr)

        self.total_steps   = 0
        self.total_updates = 0

    def select_action(self, obs: np.ndarray,
                      deterministic: bool = False) -> np.ndarray:
        if not deterministic and self._rng.random() < self.epsilon:
            return np.array([self._rng.randint(0, d-1) for d in self.action_dims],
                            dtype=np.int32)

        if TORCH_AVAILABLE:
            obs_t = torch.FloatTensor(obs).unsqueeze(0)
            with torch.no_grad():
                q_vals = self.q_net(obs_t).squeeze(0)
            actions = []
            offset = 0
            for d in self.action_dims:
                a = q_vals[offset:offset+d].argmax().item()
                actions.append(a)
                offset += d
            return np.array(actions, dtype=np.int32)
        else:
            return np.array([self._rng.randint(0, d-1) for d in self.action_dims],
                            dtype=np.int32)

    def store_experience(self, obs, action, reward, next_obs, done, cv=0.0):
        self._buffer.append((obs, action, reward, next_obs, done))
        self.total_steps += 1
        # Epsilon decay
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def update(self) -> Optional[dict]:
        if len(self._buffer) < self.batch_size or not TORCH_AVAILABLE:
            return None

        idxs = random.sample(range(len(self._buffer)), self.batch_size)
        batch = [self._buffer[i] for i in idxs]
        obs, acts, rews, next_obs, dones = zip(*batch)
        obs_t   = torch.FloatTensor(np.array(obs))
        nobs_t  = torch.FloatTensor(np.array(next_obs))
        rews_t  = torch.FloatTensor(np.array(rews))
        dones_t = torch.FloatTensor(np.array(dones))
        acts_arr = np.array(acts, dtype=np.int32)

        # Q-values for taken actions
        q_vals = self.q_net(obs_t)
        # Get Q for each sub-action
        q_taken_list = []
        offset = 0
        for i, d in enumerate(self.action_dims):
            sub_q = q_vals[:, offset:offset+d]
            act_i = torch.LongTensor(acts_arr[:, i].astype(int))
            q_i = sub_q.gather(1, act_i.unsqueeze(1)).squeeze(1)
            q_taken_list.append(q_i)
            offset += d
        q_taken = sum(q_taken_list) / len(q_taken_list)

        # Target
        with torch.no_grad():
            next_q = self.q_target(nobs_t)
            next_q_max_list = []
            offset = 0
            for d in self.action_dims:
                sub = next_q[:, offset:offset+d]
                next_q_max_list.append(sub.max(1)[0])
                offset += d
            next_q_max = sum(next_q_max_list) / len(next_q_max_list)
            target = rews_t + self.gamma * (1 - dones_t) * next_q_max

        loss = F.mse_loss(q_taken, target)
        self.opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.q_net.parameters(), 1.0)
        self.opt.step()

        # Soft target update
        for tp, p in zip(self.q_target.parameters(), self.q_net.parameters()):
            tp.data.copy_(self.tau * p.data + (1-self.tau) * tp.data)

        self.total_updates += 1
        return {"loss": loss.item(), "epsilon": self.epsilon}

    def get_critic_params(self):
        if TORCH_AVAILABLE:
            return {k: v.cpu().clone() for k, v in self.q_net.state_dict().items()}
        return {}

    def set_critic_params(self, params):
        if TORCH_AVAILABLE:
            self.q_net.load_state_dict(params)
            self.q_target.load_state_dict(params)
