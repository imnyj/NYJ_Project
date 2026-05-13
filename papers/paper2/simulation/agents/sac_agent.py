"""
sac_agent.py
============
SAC-Single baseline: Soft Actor-Critic (single agent).
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


class SACAgent:
    """
    Soft Actor-Critic agent for discrete action spaces.
    Uses entropy regularization for exploration.
    """

    def __init__(
        self,
        agent_id: str,
        obs_dim: int,
        action_dims: Tuple[int, int, int, int],
        actor_lr: float = 3e-4,
        critic_lr: float = 1e-3,
        alpha_lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        target_entropy: float = None,
        batch_size: int = 256,
        buffer_size: int = 100000,
        seed: int = 42,
    ):
        self.agent_id    = agent_id
        self.obs_dim     = obs_dim
        self.action_dims = action_dims
        self.gamma       = gamma
        self.tau         = tau
        self.batch_size  = batch_size
        self._rng        = random.Random(seed)

        # Target entropy: sum of -log(1/d_i)
        if target_entropy is None:
            self.target_entropy = -sum(np.log(d) for d in action_dims)
        else:
            self.target_entropy = target_entropy

        self._buffer = deque(maxlen=buffer_size)

        if TORCH_AVAILABLE:
            total_act = sum(action_dims)
            # Actor outputs logits for all sub-actions
            self.actor = nn.Sequential(
                nn.Linear(obs_dim, 128), nn.ReLU(),
                nn.Linear(128, 128), nn.ReLU(),
                nn.Linear(128, total_act)
            )
            # Twin Q-critics
            q_in = obs_dim + total_act
            self.q1 = nn.Sequential(
                nn.Linear(q_in, 256), nn.ReLU(),
                nn.Linear(256, 256), nn.ReLU(),
                nn.Linear(256, 1)
            )
            self.q2 = nn.Sequential(
                nn.Linear(q_in, 256), nn.ReLU(),
                nn.Linear(256, 256), nn.ReLU(),
                nn.Linear(256, 1)
            )
            self.q1_target = copy.deepcopy(self.q1)
            self.q2_target = copy.deepcopy(self.q2)

            self.actor_opt = optim.Adam(self.actor.parameters(), lr=actor_lr)
            self.q1_opt    = optim.Adam(self.q1.parameters(), lr=critic_lr)
            self.q2_opt    = optim.Adam(self.q2.parameters(), lr=critic_lr)

            # Temperature
            self.log_alpha = torch.zeros(1, requires_grad=True)
            self.alpha_opt = optim.Adam([self.log_alpha], lr=alpha_lr)
            self.alpha = self.log_alpha.exp().item()

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
                sub = logits[offset:offset+d]
                if deterministic:
                    a = sub.argmax().item()
                else:
                    probs = F.softmax(sub, dim=0).numpy()
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

    def _onehot(self, acts: np.ndarray) -> np.ndarray:
        B = acts.shape[0]
        result = np.zeros((B, sum(self.action_dims)), dtype=np.float32)
        offset = 0
        for i, d in enumerate(self.action_dims):
            for b in range(B):
                a = min(int(acts[b, i]), d-1)
                result[b, offset+a] = 1.0
            offset += d
        return result

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
        acts_oh = torch.FloatTensor(self._onehot(acts_arr))

        # Compute alpha
        alpha = self.log_alpha.exp().item()

        # Q-target
        with torch.no_grad():
            next_logits = self.actor(nobs_t)
            next_acts_list, next_log_probs_list = [], []
            for i in range(self.batch_size):
                na, nlp = [], []
                offset = 0
                for d in self.action_dims:
                    sub = next_logits[i, offset:offset+d]
                    dist = torch.distributions.Categorical(logits=sub)
                    a = dist.sample()
                    na.append(a.item())
                    nlp.append(dist.log_prob(a).item())
                    offset += d
                next_acts_list.append(na)
                next_log_probs_list.append(sum(nlp))
            next_acts_arr = np.array(next_acts_list, dtype=np.int32)
            next_acts_oh = torch.FloatTensor(self._onehot(next_acts_arr))
            next_lp = torch.FloatTensor(next_log_probs_list)

            q1_next = self.q1_target(torch.cat([nobs_t, next_acts_oh], -1)).squeeze()
            q2_next = self.q2_target(torch.cat([nobs_t, next_acts_oh], -1)).squeeze()
            min_q   = torch.min(q1_next, q2_next) - alpha * next_lp
            target  = rews_t + self.gamma * (1 - dones_t) * min_q

        q1_val = self.q1(torch.cat([obs_t, acts_oh], -1)).squeeze()
        q2_val = self.q2(torch.cat([obs_t, acts_oh], -1)).squeeze()
        q1_loss = F.mse_loss(q1_val, target)
        q2_loss = F.mse_loss(q2_val, target)

        self.q1_opt.zero_grad(); q1_loss.backward(); self.q1_opt.step()
        self.q2_opt.zero_grad(); q2_loss.backward(); self.q2_opt.step()

        for tp, p in zip(self.q1_target.parameters(), self.q1.parameters()):
            tp.data.copy_(self.tau * p.data + (1-self.tau) * tp.data)
        for tp, p in zip(self.q2_target.parameters(), self.q2.parameters()):
            tp.data.copy_(self.tau * p.data + (1-self.tau) * tp.data)

        # Actor update
        logits = self.actor(obs_t)
        log_probs = []
        offset = 0
        for d in self.action_dims:
            sub = logits[:, offset:offset+d]
            dist = torch.distributions.Categorical(logits=sub)
            a = dist.sample()
            log_probs.append(dist.log_prob(a))
            offset += d
        log_p = sum(log_probs)
        acts_new = []
        for i in range(self.batch_size):
            an = []
            off = 0
            for d in self.action_dims:
                sub = logits[i, off:off+d]
                an.append(sub.argmax().item())
                off += d
            acts_new.append(an)
        acts_new_oh = torch.FloatTensor(self._onehot(np.array(acts_new, dtype=np.int32)))
        q_pi = torch.min(
            self.q1(torch.cat([obs_t, acts_new_oh], -1)).squeeze(),
            self.q2(torch.cat([obs_t, acts_new_oh], -1)).squeeze()
        )
        actor_loss = (alpha * log_p - q_pi).mean()
        self.actor_opt.zero_grad(); actor_loss.backward(); self.actor_opt.step()

        # Alpha update
        alpha_loss = -(self.log_alpha * (log_p.detach() + self.target_entropy)).mean()
        self.alpha_opt.zero_grad(); alpha_loss.backward(); self.alpha_opt.step()

        self.total_updates += 1
        return {"q1_loss": q1_loss.item(), "actor_loss": actor_loss.item(),
                "alpha": self.log_alpha.exp().item()}

    def get_critic_params(self):
        if TORCH_AVAILABLE:
            return {k: v.cpu().clone() for k, v in self.q1.state_dict().items()}
        return {}

    def set_critic_params(self, params):
        if TORCH_AVAILABLE:
            self.q1.load_state_dict(params)
            self.q1_target.load_state_dict(params)
