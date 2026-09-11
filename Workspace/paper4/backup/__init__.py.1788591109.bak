# src/baselines/__init__.py
# ============================================================================
# Baseline registry for the 9 comparison methods.
#
# Every entry is a real published method whose citation was verified by DOI
# against Crossref; see librarian/baselines_v2.json for the bibliography and
# the per-method implementability notes those implementations were written from.
#
# The trainer constructs models as model_cls(state_dim=..., num_channels=...,
# **hparams), so every class here must accept that signature and satisfy the
# BaseRLModel contract in base_agent.py.
# ============================================================================

from __future__ import annotations

from typing import Dict, Type

from src.baselines.base_agent import BaseAgent, BaseRLModel
from src.baselines.carlton import CARLTON
from src.baselines.i_hamappo import IHAMAPPO
from src.baselines.ma2hdqn import MA2HDQN
from src.baselines.maddpg_mt import MADDPGMT
from src.baselines.res_mapddpg import RESMAPDDPG
from src.baselines.sb3_ppo import PPO
from src.baselines.sb3_sac import SAC
from src.baselines.sb3_td3 import TD3
from src.baselines.spam_d3qn import SPAMD3QN

#: Canonical name -> class. Keys are the method_name values used in the paper's
#: results tables, so a results CSV column and a registry key are the same string.
BASELINE_REGISTRY: Dict[str, Type[BaseRLModel]] = {
    # Basic (Stable-Baselines3, wrapped for the hybrid action space)
    "PPO": PPO,
    "SAC": SAC,
    "TD3": TD3,
    # Latest (2025-2026)
    "RES-MAPDDPG": RESMAPDDPG,
    "MA2HDQN": MA2HDQN,
    "I-HAMAPPO": IHAMAPPO,
    # Similar
    "SPAM-D3QN": SPAMD3QN,
    "CARLTON": CARLTON,
    "MADDPG-MT": MADDPGMT,
}

#: Aliases so a class name or a hyphen-free spelling also resolves.
_ALIASES: Dict[str, str] = {
    "RESMAPDDPG": "RES-MAPDDPG",
    "IHAMAPPO": "I-HAMAPPO",
    "SPAMD3QN": "SPAM-D3QN",
    "MADDPGMT": "MADDPG-MT",
}
for _alias, _canon in _ALIASES.items():
    BASELINE_REGISTRY[_alias] = BASELINE_REGISTRY[_canon]

#: Grouping used by the paper's results tables and by run_all.py.
BASELINE_CATEGORIES: Dict[str, tuple] = {
    "basic": ("PPO", "SAC", "TD3"),
    "latest": ("RES-MAPDDPG", "MA2HDQN", "I-HAMAPPO"),
    "similar": ("SPAM-D3QN", "CARLTON", "MADDPG-MT"),
}

#: The nine canonical names in table order.
ALL_BASELINES: tuple = (
    BASELINE_CATEGORIES["basic"]
    + BASELINE_CATEGORIES["latest"]
    + BASELINE_CATEGORIES["similar"]
)


def get_baseline(name: str) -> Type[BaseRLModel]:
    """Resolve a baseline name to its class, raising a listing on a miss."""
    try:
        return BASELINE_REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Unknown baseline {name!r}. Available: {sorted(set(ALL_BASELINES))}"
        ) from None


__all__ = [
    "BaseAgent",
    "BaseRLModel",
    "BASELINE_REGISTRY",
    "BASELINE_CATEGORIES",
    "ALL_BASELINES",
    "get_baseline",
    "PPO", "SAC", "TD3",
    "RESMAPDDPG", "MA2HDQN", "IHAMAPPO",
    "SPAMD3QN", "CARLTON", "MADDPGMT",
]
