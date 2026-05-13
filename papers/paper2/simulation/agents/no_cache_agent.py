"""
no_cache_agent.py
=================
No-Cache baseline.
Pure V2X communication without NDN caching.
"""

import random
import numpy as np
from typing import Tuple


class NoCacheAgent:
    """
    Heuristic agent that never caches content.
    Uses V2I forwarding with maximum power.
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
        No caching: forwarding=V2I (2), cache=0, max power (4), random subchannel.
        """
        fwd   = 2      # always V2I (direct source)
        cache = 0      # never cache
        power = 4      # max power
        subch = self._rng.randint(0, self.action_dims[3]-1)
        return np.array([fwd, cache, power, subch], dtype=np.int32)

    def store_experience(self, obs, action, reward, next_obs, done, cv=0.0):
        self.total_steps += 1

    def update(self):
        return None

    def get_critic_params(self):
        return {}

    def set_critic_params(self, params):
        pass
