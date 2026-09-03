# src/baselines/base_agent.py
# ============================================================================
# Base RL Agent Interface Contract
#
# Unified class hierarchy for the 9 baselines selected in librarian/baselines_v2.json.
# Every entry is a real published method, verified by DOI against Crossref:
#
# - Basic (via Stable-Baselines3, wrapped for our hybrid action space):
#     PPO          Schulman et al. 2017
#     SAC          Haarnoja et al., ICML 2018
#     TD3          Fujimoto et al., ICML 2018
# - Latest (2025-2026):
#     RES-MAPDDPG  Li et al., IEEE TVT 75(7), 2026
#     MA2HDQN      Hong et al., IEEE TVT 75(6), 2026
#     I-HAMAPPO    Chen et al., IEEE TWC 25, 2026
# - Similar:
#     SPAM-D3QN    Bai et al., IEEE TVT 73(4), 2024
#     CARLTON      Cohen et al., IEEE TWC 24(1), 2025
#     MADDPG-MT    Parvini et al., IEEE TVT 72(8), 2023
#
# The action space every subclass must produce is hybrid: continuous Delta over
# [0.1, 45] s (geometric mapping), continuous power over [10, 23] dBm, and a
# discrete subchannel in {0..3}. ActionDecoder owns those bounds; never restate
# them in a subclass.
# ============================================================================

from __future__ import annotations
import os
from typing import Any, Dict, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
from src.rl_interface import STATE_DIM, ActionDecoder


class BaseRLModel(nn.Module):
    """
    Standard Baseline Model Interface Contract.
    
    All 9 baselines inherit from this class to guarantee seamless integration
    with hot_swap_trainer (Act/Rest mode) and the evaluation benchmark suite.
    """

    # state_dim defaults to the StateVectorizer's canonical observation dimension
    # (src.rl_interface.STATE_DIM). Never hardcode the literal here or in subclasses.
    def __init__(self, state_dim: int = STATE_DIM, num_channels: int = 4, **hparams: Any) -> None:
        super().__init__()
        self.state_dim = int(state_dim)
        self.num_channels = int(num_channels)
        self.decoder = ActionDecoder(num_channels=self.num_channels)
        self.hparams = hparams

    def _prepare_state_tensor(self, state: Union[np.ndarray, torch.Tensor, list]) -> torch.Tensor:
        """Helper to convert input state into a 2D float32 Tensor on model's device."""
        if not isinstance(state, torch.Tensor):
            state = torch.tensor(state, dtype=torch.float32)
        else:
            state = state.to(dtype=torch.float32)
        if state.dim() == 1:
            state = state.unsqueeze(0)
        # Match parameter device
        device = next(self.parameters()).device if list(self.parameters()) else torch.device("cpu")
        return state.to(device)

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        """
        Selects hybrid action given state observation.
        
        Returns:
            decoded_grant: (delta_s, channel_idx, power_dbm)
            raw_action: np.ndarray representation of raw action
            info: dict containing auxiliary outputs (value, log_prob, q_vals, etc.)
        """
        raise NotImplementedError

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """
        Performs one gradient update step given a batch of transitions.
        
        Returns:
            loss_dict: dict of loss components, must include 'loss'
        """
        raise NotImplementedError

    def save(self, filepath: str) -> None:
        """Save model checkpoint."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        torch.save({
            "state_dict": self.state_dict(),
            "state_dim": self.state_dim,
            "num_channels": self.num_channels,
            "hparams": self.hparams,
        }, filepath)

    def load(self, filepath: str) -> None:
        """Load model checkpoint."""
        checkpoint = torch.load(filepath, map_location="cpu")
        if "state_dict" in checkpoint:
            self.load_state_dict(checkpoint["state_dict"])
        else:
            self.load_state_dict(checkpoint)


# Backward-compatible alias
BaseAgent = BaseRLModel
