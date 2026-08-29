# src/baselines/pure_aoi.py
# ============================================================================
# Pure-AoI Whittle Index / Age-Greedy Scheduler Baseline
#
# Baseline 7 (Category 3: SOTA AoI Models)
# Features:
# - Classic Age-of-Information Whittle Index and Age-Greedy scheduler
# - Allocates urgent grants (short Delta, near-max p) for stale states (high AoI)
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
from src.rl_interface import STATE_DIM


class PureAoI(BaseRLModel):
    def __init__(
        self,
        state_dim: int = STATE_DIM,
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

        # Action bounds come from the decoder (single source of truth, Conversation.md S2):
        # Delta in [0.1, 5.0]s, power in [10.0, 23.0]dBm.
        d_lo, d_hi = self.decoder.delta_min, self.decoder.delta_max
        p_lo, p_hi = self.decoder.p_min, self.decoder.p_max
        d_span = d_hi - d_lo
        p_span = p_hi - p_lo

        # High urgency: short interval, high power
        if age_norm > self.urgency_threshold or whittle_idx > 0.05:
            # Fastest end of the interval range, scaled up slightly as the age drops.
            delta = float(np.clip(d_lo + (1.0 - age_norm) * 0.2 * d_span, d_lo, d_hi))
            # Top of the power range (>= 90% of span), capped at the class-3 max.
            power = float(np.clip(p_lo + (0.9 + 0.1 * age_norm) * p_span, p_lo, p_hi))
            ch = int(round(age_norm * 100)) % self.num_channels
        else:
            # Low urgency: backoff to save bandwidth and reduce interference
            delta = float(np.clip(d_lo + (0.5 + (1.0 - age_norm) * 0.5) * d_span, d_lo, d_hi))
            power = float(np.clip(p_lo + (0.3 + age_norm * 0.3) * p_span, p_lo, p_hi))
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
