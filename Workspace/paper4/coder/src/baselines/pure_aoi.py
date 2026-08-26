# src/baselines/pure_aoi.py
# ============================================================================
# Pure-AoI Whittle Index / Age-Greedy Scheduler Baseline
#
# Baseline 7 (Category 3: SOTA AoI Models)
# Features:
# - Classic Age-of-Information Whittle Index and Age-Greedy scheduler
# - Allocates urgent grants (Delta=0.5s, p=30dBm) for stale states (high AoI)
# - Backs off to conservative intervals for fresh states (low AoI)
# - Subchannel load-balancing allocation
# - Compatible with BaseRLModel interface, checkpoints, and evaluation harness
# ============================================================================

from __future__ import annotations
from typing import Any, Dict, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
from src.baselines.base_agent import BaseRLModel


class PureAoI(BaseRLModel):
    def __init__(
        self,
        state_dim: int = 16,
        num_channels: int = 4,
        urgency_threshold: float = 0.3,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.urgency_threshold = float(urgency_threshold)
        # Learnable threshold scale parameter for model compatibility
        self.scale_param = nn.Parameter(torch.tensor([1.0], dtype=torch.float32))
        self.channel_rr = 0

    def _compute_whittle_index(self, age_norm: float, dist_norm: float) -> float:
        """
        Whittle index calculation for AoI minimization under fading:
        W(s) = (Age)^2 / (2 * LinkQuality)
        """
        link_quality = max(0.1, 1.0 - dist_norm * 0.5)
        return float((age_norm ** 2) / (2.0 * link_quality))

    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        if isinstance(state, torch.Tensor):
            state_arr = state.detach().cpu().numpy()
        else:
            state_arr = np.array(state, dtype=np.float32)

        if state_arr.ndim > 1:
            state_arr = state_arr[0]

        age_norm = float(np.clip(state_arr[0], 0.0, 1.0))
        dist_norm = float(np.clip(state_arr[7], 0.0, 1.0))
        whittle_idx = self._compute_whittle_index(age_norm, dist_norm)

        # High urgency: short interval, high power
        if age_norm > self.urgency_threshold or whittle_idx > 0.05:
            delta = max(0.5, min(10.0, 0.5 + (1.0 - age_norm) * 2.0))
            power = 28.0 + min(2.0, age_norm * 2.0)
            ch = int(round(age_norm * 100)) % self.num_channels
        else:
            # Low urgency: backoff to save bandwidth and reduce interference
            delta = min(10.0, max(2.0, 3.0 + (1.0 - age_norm) * 4.0))
            power = 20.0 + age_norm * 5.0
            ch = self.channel_rr % self.num_channels
            self.channel_rr += 1

        decoded = (float(delta), int(ch), float(power))
        raw_action = self.decoder.encode_action(delta, ch, power)
        info = {
            "whittle_index": whittle_idx,
            "age_norm": age_norm,
            "raw_action": raw_action,
        }
        return decoded, raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        # Track batch statistics and perform a soft dummy loss update for scale parameter
        states = batch["state"]
        mean_age = float(states[:, 0].mean().item())
        loss = (self.scale_param * 0.0).sum()
        return {
            "loss": float(loss.item()),
            "mean_batch_age": mean_age,
        }
