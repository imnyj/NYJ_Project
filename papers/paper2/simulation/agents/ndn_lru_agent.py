"""
ndn_lru_agent.py
================
NDN-LRU heuristic baseline.
Uses LRU cache replacement + random forwarding (no learning).
"""

import random
import numpy as np
from typing import Tuple


class NDNLRUAgent:
    """
    NDN with LRU caching policy. No AoI-awareness. No learning.
    Random forwarding strategy.
    """

    def __init__(
        self,
        agent_id: str,
        action_dims: Tuple[int, int, int, int],
        seed: int = 42,
    ):
        self.agent_id    = agent_id
        self.action_dims = action_dims
        self._rng        = random.Random(seed)
        self.total_steps = 0

    def select_action(self, obs: np.ndarray,
                      deterministic: bool = False) -> np.ndarray:
        """
        Heuristic: random forwarding, always cache (LRU), medium power, random subchannel.
        """
        fwd   = self._rng.randint(0, self.action_dims[0]-1)  # random forwarding
        cache = 1      # always cache
        power = 2      # medium power (index 2 = 15 dBm)
        subch = self._rng.randint(0, self.action_dims[3]-1)  # random subchannel
        return np.array([fwd, cache, power, subch], dtype=np.int32)

    def store_experience(self, obs, action, reward, next_obs, done, cv=0.0):
        self.total_steps += 1

    def update(self):
        return None  # No learning

    def get_critic_params(self):
        return {}

    def set_critic_params(self, params):
        pass
