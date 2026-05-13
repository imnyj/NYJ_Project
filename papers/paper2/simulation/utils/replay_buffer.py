"""
replay_buffer.py
================
Experience Replay Buffer implementations.
"""

import random
import numpy as np
from collections import deque
from typing import Tuple, Optional


class ReplayBuffer:
    """Standard circular replay buffer."""

    def __init__(self, capacity: int = 100000, seed: int = 42):
        self._buf = deque(maxlen=capacity)
        self._rng = random.Random(seed)

    def push(self, obs, action, reward, next_obs, done,
             constraint_violation: float = 0.0):
        """Store a transition."""
        self._buf.append({
            "obs":    np.array(obs, dtype=np.float32),
            "action": np.array(action, dtype=np.int32),
            "reward": float(reward),
            "next_obs": np.array(next_obs, dtype=np.float32),
            "done":   float(done),
            "cv":     float(constraint_violation),
        })

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        """Sample a random batch."""
        batch = self._rng.sample(list(self._buf), min(batch_size, len(self._buf)))
        obs      = np.stack([b["obs"]      for b in batch])
        actions  = np.stack([b["action"]   for b in batch])
        rewards  = np.array([b["reward"]   for b in batch], dtype=np.float32)
        next_obs = np.stack([b["next_obs"] for b in batch])
        dones    = np.array([b["done"]     for b in batch], dtype=np.float32)
        cvs      = np.array([b["cv"]       for b in batch], dtype=np.float32)
        return obs, actions, rewards, next_obs, dones, cvs

    def __len__(self):
        return len(self._buf)

    def is_ready(self, batch_size: int) -> bool:
        return len(self._buf) >= batch_size


class PrioritizedReplayBuffer:
    """Proportional prioritized experience replay (simplified)."""

    def __init__(self, capacity: int = 100000, alpha: float = 0.6,
                 beta: float = 0.4, seed: int = 42):
        self.capacity = capacity
        self.alpha    = alpha
        self.beta     = beta
        self._rng     = random.Random(seed)
        self._buf     = []
        self._priorities = []
        self._max_p   = 1.0

    def push(self, obs, action, reward, next_obs, done, cv=0.0):
        entry = (np.array(obs, np.float32), np.array(action, np.int32),
                 float(reward), np.array(next_obs, np.float32),
                 float(done), float(cv))
        if len(self._buf) < self.capacity:
            self._buf.append(entry)
            self._priorities.append(self._max_p)
        else:
            idx = self._rng.randint(0, self.capacity-1)
            self._buf[idx] = entry
            self._priorities[idx] = self._max_p

    def sample(self, batch_size: int):
        N = len(self._buf)
        if N == 0:
            return None
        probs = np.array(self._priorities[:N]) ** self.alpha
        probs /= probs.sum()
        idxs = self._rng.choices(range(N), weights=probs.tolist(),
                                  k=min(batch_size, N))
        batch = [self._buf[i] for i in idxs]
        obs, acts, rews, next_obs, dones, cvs = zip(*batch)
        return (np.stack(obs), np.stack(acts), np.array(rews, dtype=np.float32),
                np.stack(next_obs), np.array(dones, dtype=np.float32),
                np.array(cvs, dtype=np.float32))

    def update_priorities(self, indices, errors):
        for i, e in zip(indices, errors):
            if i < len(self._priorities):
                self._priorities[i] = abs(e) + 1e-6
                self._max_p = max(self._max_p, self._priorities[i])

    def __len__(self):
        return len(self._buf)
