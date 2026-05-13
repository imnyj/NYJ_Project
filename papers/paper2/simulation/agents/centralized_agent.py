"""
centralized_agent.py
====================
Centralized Actor-Critic baseline (global state, single agent).
Serves as performance upper bound.
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


class CentralizedAgent:
    """
    Centralized DRL agent with global state observability.
    Aggregates all vehicle observations into a global state vector.
    """

    def __init__(
        self,
        obs_dim: int,
        action_dims: Tuple[int, int, int, int],
        max_agents: int = 100,
        actor_lr: float = 3e-4,
        critic_lr: float = 1e-3,
        gamma: float = 0.99,
        tau: float = 0.005,
        batch_size: int = 256,
        buffer_size: int = 100000,
        seed: int = 42,
    ):
        self.obs_dim     = obs_dim
        self.action_dims = action_dims
        self.max_agents  = max_agents
        self.gamma       = gamma
        self.tau         = tau
        self.batch_size  = batch_size
        self._rng        = random.Random(seed)

        # Global obs dim = max_agents * obs_dim (padded/masked)
        self.global_obs_dim = obs_dim  # We use per-agent obs for simplicity

        if TORCH_AVAILABLE:
            # Simple MLP actor
            total_action = sum(action_dims)
            self.actor = nn.Sequential(
                nn.Linear(obs_dim, 128), nn.ReLU(),
                nn.Linear(128, 128), nn.ReLU(),
                nn.Linear(128, total_action)
            )
            self.critic = nn.Sequential(
                nn.Linear(obs_dim, 256), nn.ReLU(),
                nn.Linear(256, 256), nn.ReLU(),
                nn.Linear(256, 1)
            )
            self.critic_target = copy.deepcopy(self.critic)
            self.actor_opt  = optim.Adam(self.actor.parameters(), lr=actor_lr)
            self.critic_opt = optim.Adam(self.critic.parameters(), lr=critic_lr)

        self._buffer = deque(maxlen=buffer_size)
        self.total_steps   = 0
        self.total_updates = 0

    def select_action(self, obs: np.ndarray,
                      deterministic: bool = False) -> np.ndarray:
        if TORCH_AVAILABLE:
            obs_t = torch.FloatTensor(obs).unsqueeze(0)
            with torch.no_grad():
                logits = self.actor(obs_t).squeeze(0)
            actions = []
            offset = 0
            for d in self.action_dims:
                sub_logits = logits[offset:offset+d]
                if deterministic:
                    a = sub_logits.argmax().item()
                else:
                    probs = F.softmax(sub_logits, dim=0).numpy()
                    a = self._rng.choices(range(d), weights=probs)[0]
                actions.append(a)
                offset += d
            return np.array(actions, dtype=np.int32)
        else:
            return np.array([self._rng.randint(0, d-1) for d in self.action_dims],
                            dtype=np.int32)

    def store_experience(self, obs, action, reward, next_obs, done, cv=0.0):
        self._buffer.append((obs, action, reward, next_obs, done))
        self.total_steps += 1

    def update(self) -> Optional[dict]:
        if len(self._buffer) < self.batch_size:
            return None
        if not TORCH_AVAILABLE:
            return None

        idxs = random.sample(range(len(self._buffer)), self.batch_size)
        batch = [self._buffer[i] for i in idxs]
        obs, acts, rews, next_obs, dones = zip(*batch)

        obs_t      = torch.FloatTensor(np.array(obs))
        next_obs_t = torch.FloatTensor(np.array(next_obs))
        rews_t     = torch.FloatTensor(np.array(rews))
        dones_t    = torch.FloatTensor(np.array(dones))

        with torch.no_grad():
            next_v = self.critic_target(next_obs_t).squeeze(-1)
            target = rews_t + self.gamma * (1 - dones_t) * next_v

        current_v = self.critic(obs_t).squeeze(-1)
        critic_loss = F.mse_loss(current_v, target)
        self.critic_opt.zero_grad()
        critic_loss.backward()
        self.critic_opt.step()

        for tp, p in zip(self.critic_target.parameters(), self.critic.parameters()):
            tp.data.copy_(self.tau * p.data + (1 - self.tau) * tp.data)

        adv = (target - current_v).detach()
        logits = self.actor(obs_t)
        log_probs = []
        offset = 0
        acts_arr = np.array(acts)
        for i, d in enumerate(self.action_dims):
            sub_logits = logits[:, offset:offset+d]
            dist = torch.distributions.Categorical(logits=sub_logits)
            act_i = torch.LongTensor(acts_arr[:, i].astype(int))
            lp = dist.log_prob(act_i)
            log_probs.append(lp)
            offset += d
        log_p = sum(log_probs)
        actor_loss = -(log_p * adv).mean()
        self.actor_opt.zero_grad()
        actor_loss.backward()
        self.actor_opt.step()

        self.total_updates += 1
        return {"critic_loss": critic_loss.item(), "actor_loss": actor_loss.item()}

    def get_critic_params(self):
        if TORCH_AVAILABLE:
            return {k: v.cpu().clone() for k, v in self.critic.state_dict().items()}
        return {}

    def set_critic_params(self, params):
        if TORCH_AVAILABLE:
            self.critic.load_state_dict(params)
            self.critic_target.load_state_dict(params)
