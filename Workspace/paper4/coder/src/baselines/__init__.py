# src/baselines/__init__.py
# ============================================================================
# 9 Baseline RL Algorithms Module
# ============================================================================

from src.baselines.base_agent import BaseRLModel, BaseAgent
from src.baselines.hybrid_ppo import HybridPPO
from src.baselines.hybrid_sac import HybridSAC
from src.baselines.hybrid_td3 import HybridTD3
from src.baselines.mappo import MAPPO
from src.baselines.hyar_ppo import HyARPPO
from src.baselines.pdqn import MPDQN, PDQN
from src.baselines.pure_aoi import PureAoI
from src.baselines.dueling_q_aoi import DuelingQAoI
from src.baselines.sac_aoi import SACAoI

BASELINE_REGISTRY = {
    # Category 1: Basic Models
    "HybridPPO": HybridPPO,
    "H-PPO": HybridPPO,
    "HybridSAC": HybridSAC,
    "H-SAC": HybridSAC,
    "HybridTD3": HybridTD3,
    "H-TD3": HybridTD3,
    # Category 2: Latest / Hybrid Models
    "MAPPO": MAPPO,
    "HyARPPO": HyARPPO,
    "HyAR-PPO": HyARPPO,
    "MPDQN": MPDQN,
    "PDQN": PDQN,
    "MP-DQN": MPDQN,
    # Category 3: SOTA AoI Models
    "PureAoI": PureAoI,
    "Pure-AoI": PureAoI,
    "DuelingQAoI": DuelingQAoI,
    "Dueling-Q-AoI": DuelingQAoI,
    "SACAoI": SACAoI,
    "SAC-AoI": SACAoI,
}

__all__ = [
    "BaseRLModel",
    "BaseAgent",
    "HybridPPO",
    "HybridSAC",
    "HybridTD3",
    "MAPPO",
    "HyARPPO",
    "MPDQN",
    "PDQN",
    "PureAoI",
    "DuelingQAoI",
    "SACAoI",
    "BASELINE_REGISTRY",
]
