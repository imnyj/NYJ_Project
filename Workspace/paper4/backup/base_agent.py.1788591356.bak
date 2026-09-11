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
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
from src.rl_interface import STATE_DIM, ActionDecoder

logger = logging.getLogger(__name__)

#: Bound on |log(pi_new / pi_behaviour)| before exponentiation, shared by the two
#: PPO-family baselines. exp(20) ~ 4.9e8 is already far outside any clip range,
#: while exp of the few hundred a genuinely off-policy transition can produce is
#: inf in float32. Clamping zeroes the gradient beyond the bound, which is the
#: intended trust-region behaviour rather than a numerical patch.
LOG_RATIO_CLAMP: float = 20.0


class BaseRLModel(nn.Module):
    """
    Standard Baseline Model Interface Contract.
    
    All 9 baselines inherit from this class to guarantee seamless integration
    with hot_swap_trainer (Act/Rest mode) and the evaluation benchmark suite.
    """

    # state_dim defaults to the StateVectorizer's canonical observation dimension
    # (src.rl_interface.STATE_DIM). Never hardcode the literal here or in subclasses.
    #: Reward-weight keys. These configure `AoiV2IEnv`, never a model. Because
    #: every constructor in this package ends in `**hparams`, a caller that
    #: forwards a hyper-parameter CSV row wholesale used to have the MODEL swallow
    #: them while the reward went on using its defaults -- an "optimal w1" that
    #: reached nothing, reported in the paper's table. The routing is done
    #: upstream (`run_all.ENV_ONLY_HPARAM_KEYS`); this is the backstop that makes a
    #: routing regression fail loudly instead of silently.
    _REWARD_WEIGHT_PATTERN = re.compile(r"^w\d+(_raw)?$")

    def __init__(self, state_dim: int = STATE_DIM, num_channels: int = 4, **hparams: Any) -> None:
        super().__init__()
        leaked = sorted(k for k in hparams if self._REWARD_WEIGHT_PATTERN.match(k))
        if leaked:
            raise TypeError(
                f"{type(self).__name__} received environment-only reward weights "
                f"{leaked} as model hyper-parameters. Reward weights configure "
                "AoiV2IEnv, not a baseline; strip them with ENV_ONLY_HPARAM_KEYS "
                "before constructing the model."
            )
        self.state_dim = int(state_dim)
        self.num_channels = int(num_channels)
        self.decoder = ActionDecoder(num_channels=self.num_channels)
        self.hparams = hparams
        #: One warning per model instance when a batch arrives without a stored
        #: behaviour log-probability. See `stored_behaviour_log_prob`.
        self._warned_missing_behaviour_logp = False

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

    # ------------------------------------------------------------------
    # Canonical inversion of ActionDecoder.encode_action
    #
    # `ActionDecoder.encode_action` emits
    #     raw = [logit(unit_from_delta(delta)), ch, logit((p - p_min) / (p_max - p_min))]
    # i.e. the Delta field is the logit of the GEOMETRIC unit coordinate, not of a
    # linear normalisation. Three baselines used to invert it linearly, which put
    # 96 of 128 grid actions in the wrong Q slot. The inversion therefore lives
    # HERE, once, and every subclass that stores `encode_action` output in the
    # replay buffer must go through these helpers instead of copying the algebra.
    #
    # Everything below is expressed in the decoder's own unit coordinate u in
    # [0, 1], because that coordinate is geometry-agnostic: it is exact whether
    # `ActionDecoder` maps u -> Delta geometrically or (in the degenerate
    # delta_min == delta_max case) linearly. Snapping a recovered action onto a
    # quantised grid is likewise done in u space, never in Delta space.
    # ------------------------------------------------------------------
    @staticmethod
    def unit_from_raw(raw_field: torch.Tensor) -> torch.Tensor:
        """Raw logit field -> unit coordinate u in [0, 1]. Inverse of `_logit`."""
        return torch.sigmoid(raw_field.float())

    def raw_units(self, raw_actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Raw replay actions (N, 3) -> (u_delta, u_power), each (N,) in [0, 1].

        This is the exact inverse of `ActionDecoder.encode_action` up to that
        method's 1e-6 logit clamp.
        """
        acts = raw_actions.float()
        if acts.dim() == 1:
            acts = acts.unsqueeze(0)
        return self.unit_from_raw(acts[:, 0]), self.unit_from_raw(acts[:, 2])

    def raw_channel(self, raw_actions: torch.Tensor) -> torch.Tensor:
        """Raw replay actions (N, 3) -> subchannel index (N,) in {0..num_channels-1}."""
        acts = raw_actions.float()
        if acts.dim() == 1:
            acts = acts.unsqueeze(0)
        return acts[:, 1].round().long().remainder(self.num_channels)

    def delta_from_unit_t(self, u: torch.Tensor) -> torch.Tensor:
        """Vectorised `ActionDecoder.delta_from_unit` (bounds read off the decoder)."""
        dec = self.decoder
        u = u.float().clamp(0.0, 1.0)
        ratio = float(getattr(dec, "_log_delta_ratio", 0.0))
        if ratio <= 0.0:
            return dec.delta_min + u * (dec.delta_max - dec.delta_min)
        return dec.delta_min * torch.exp(u * ratio)

    def power_from_unit_t(self, u: torch.Tensor) -> torch.Tensor:
        """Vectorised linear power map (dBm is already a logarithmic unit)."""
        dec = self.decoder
        return dec.p_min + u.float().clamp(0.0, 1.0) * (dec.p_max - dec.p_min)

    @staticmethod
    def unit_grid(num_levels: int) -> List[float]:
        """
        Unit coordinates of an `num_levels`-point grid, endpoints inclusive.

        `build_geometric_delta_grid` / `build_linear_power_grid` construct their
        candidates as `map_from_unit(i / (n - 1))`, so these are exactly the unit
        coordinates of those candidates and snapping in u space is exact.
        """
        n = max(2, int(num_levels))
        return [i / (n - 1) for i in range(n)]

    def snap_unit_to_grid(self, u: torch.Tensor, num_levels: int) -> torch.Tensor:
        """Nearest-grid-point index of each unit coordinate, snapped in u space."""
        grid = torch.as_tensor(
            self.unit_grid(num_levels), dtype=torch.float32, device=u.device
        )
        return torch.argmin((u.float().reshape(-1, 1) - grid.reshape(1, -1)).abs(), dim=1)

    # ------------------------------------------------------------------
    # SMDP discount
    # ------------------------------------------------------------------
    def smdp_discounts(
        self, batch: Dict[str, torch.Tensor], reference: torch.Tensor
    ) -> torch.Tensor:
        """
        Per-transition SMDP discount gamma**delta_t, shaped like `reference`.

        THE MODEL'S OWN `self.gamma` IS THE SINGLE SOURCE. `RetrospectiveReplayBuffer`
        also ships a precomputed "discount" column, but it is computed from the
        buffer's own gamma, which nothing in the pipeline sets from the model. Every
        baseline used to prefer that column, so a per-model `gamma` -- searched by
        Optuna for all nine models and reported as an optimum -- had no effect on
        learning whatsoever. Preferring `delta_t` here makes the constructor
        argument real and makes the result identical to the buffer's column whenever
        the buffer is constructed with the same gamma, so the two wirings agree
        rather than fight.

        Fallback order: `delta_t` (recomputed) -> `discount` (as supplied) ->
        a constant gamma, the last only for hand-built batches that carry neither.
        """
        device = reference.device
        dtype = reference.dtype
        gamma = float(getattr(self, "gamma", 0.99))
        delta_t = batch.get("delta_t")
        if delta_t is not None:
            delta_t = delta_t.to(device=device, dtype=dtype).reshape(reference.shape)
            return torch.pow(torch.as_tensor(gamma, device=device, dtype=dtype), delta_t)
        if "discount" in batch:
            return batch["discount"].to(device=device, dtype=dtype).reshape(reference.shape)
        return torch.full_like(reference, gamma)

    # ------------------------------------------------------------------
    # Behaviour log-probability (importance sampling)
    # ------------------------------------------------------------------
    def stored_behaviour_log_prob(
        self, batch: Dict[str, torch.Tensor], reference: torch.Tensor
    ) -> Optional[torch.Tensor]:
        """
        The behaviour log-probability the acting policy reported, or None.

        `RetrospectiveReplayBuffer.sample` emits "behaviour_log_prob" only when
        EVERY transition in the batch carries one, so the result is either a
        full column shaped like `reference` or nothing at all. It is the
        denominator of the importance ratio pi_new / pi_behaviour that the two
        PPO-family baselines need: this buffer hands out uniformly sampled stale
        transitions, so without it the ratio has to be built from the current
        policy, which pins it at 1 and disables clipping.

        Returning None is a legitimate state -- hand-built batches and buffers
        checkpointed before the key existed have no such column -- but it is
        never a silent one. The caller reports which branch it took, and this
        method logs once per model instance.
        """
        stored = batch.get("behaviour_log_prob")
        if stored is None:
            if not self._warned_missing_behaviour_logp:
                self._warned_missing_behaviour_logp = True
                logger.warning(
                    "%s.update(): the batch carries no 'behaviour_log_prob', so the "
                    "importance ratio is formed against a substitute denominator taken "
                    "from the learner itself instead of the policy that collected the "
                    "data, and the clip range is weakened accordingly -- for PPO it is "
                    "entirely inert on the first inner epoch, where the ratio is then "
                    "exactly 1. Further occurrences are not logged; the returned "
                    "'behaviour_logp_stored' key reports this per update.",
                    type(self).__name__,
                )
            return None
        return stored.to(device=reference.device, dtype=reference.dtype).reshape(reference.shape)

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
        """Write a checkpoint: a detached CPU snapshot plus the geometry it needs.

        Two properties matter and neither is free.

        DETACHED CPU CLONES, not `self.state_dict()` directly. A state dict holds
        references to the live tensors, so serialising it straight to disk records
        whatever those tensors happen to contain while `torch.save` walks them. On
        a model the background trainer is still updating that yields a TORN
        snapshot -- some tensors from the old policy, some from the new -- i.e. a
        policy that was never executed, filed next to a reward it never earned.
        `HotSwapTrainer.save_checkpoint` takes locks for the same reason; cloning
        here makes this entry point safe by construction rather than by protocol.

        CPU, so the file is loadable on a machine without the GPU it was trained
        on. `load()` and `evaluate.load_checkpoint_bundle` both pass
        `map_location="cpu"` and would cope either way, but a bare
        `torch.load(path)` elsewhere would not.

        `state_dim` / `num_channels` are recorded so `load()` can name a geometry
        mismatch instead of dumping a wall of size mismatches, and so
        `evaluate.build_evaluated_model` can rebuild the model from the shape the
        saved tensors were actually trained at rather than from a CSV that may
        disagree.
        """
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        snapshot = {k: v.detach().to("cpu").clone() for k, v in self.state_dict().items()}
        torch.save({
            "state_dict": snapshot,
            "state_dim": self.state_dim,
            "num_channels": self.num_channels,
            "hparams": self.hparams,
        }, filepath)

    #: Weight keys this class can restore from, in priority order.
    #:
    #: "state_dict" is what `save()` above writes. The other two come from
    #: `HotSwapTrainer.save_checkpoint`, which stores BOTH copies of the network:
    #: `rest_model` is the learner that receives every gradient step, `act_model`
    #: is the deployed inference copy, and weights only ever flow rest -> act at a
    #: hot swap. Every reward this project reports -- including the `best_reward`
    #: that decides which episode becomes `_best.pt` -- was produced by acting
    #: with `act_model`, so that is the policy a checkpoint's numbers actually
    #: claim. `rest_state_dict` holds strictly newer but never-validated updates
    #: and is only a fallback. This ordering matches
    #: `evaluate.CHECKPOINT_WEIGHT_KEYS`; the two must not diverge.
    CHECKPOINT_WEIGHT_KEYS: Tuple[str, ...] = ("state_dict", "act_state_dict", "rest_state_dict")

    def load(self, filepath: str) -> None:
        """Restore weights written by `save()` or by `HotSwapTrainer.save_checkpoint`.

        Strict by construction: `load_state_dict` defaults to strict=True and is
        deliberately left that way. A non-strict load leaves every key the file
        does not carry sitting at its freshly initialised value, which is the
        silent-random-weights failure that put untrained numbers in this
        project's results table once already. A shape or key mismatch must be an
        exception, not a warning.
        """
        checkpoint = torch.load(filepath, map_location="cpu", weights_only=False)
        if not isinstance(checkpoint, dict):
            raise TypeError(
                f"Checkpoint {filepath} is a {type(checkpoint).__name__}, not a state dict bundle."
            )

        key = next((k for k in self.CHECKPOINT_WEIGHT_KEYS if k in checkpoint), None)
        if key is None:
            # A bare state dict (no bundle wrapper) is still accepted; anything
            # else is a bundle we do not understand, and guessing would mean
            # feeding metadata keys to load_state_dict for a confusing error.
            if any(isinstance(v, torch.Tensor) for v in checkpoint.values()):
                self.load_state_dict(checkpoint)
                return
            raise KeyError(
                f"Checkpoint {filepath} carries none of {list(self.CHECKPOINT_WEIGHT_KEYS)} "
                f"and is not a bare state dict. Keys present: {sorted(checkpoint)[:10]}"
            )

        # Geometry recorded by `save()`. Checking it first turns an obscure
        # size-mismatch dump into a message that names the actual cause -- the
        # pre-smoke checkpoints in backup/ were all saved at state_dim 18 and are
        # unusable now that the observation is 17 wide.
        stored_dim = checkpoint.get("state_dim")
        if stored_dim is not None and int(stored_dim) != self.state_dim:
            raise ValueError(
                f"Checkpoint {filepath} was saved with state_dim={int(stored_dim)}, but this "
                f"{type(self).__name__} has state_dim={self.state_dim}. The observation "
                "vector changed since that checkpoint was written; it cannot be restored."
            )
        stored_ch = checkpoint.get("num_channels")
        if stored_ch is not None and int(stored_ch) != self.num_channels:
            raise ValueError(
                f"Checkpoint {filepath} was saved with num_channels={int(stored_ch)}, but this "
                f"{type(self).__name__} has num_channels={self.num_channels}."
            )

        self.load_state_dict(checkpoint[key])


# Backward-compatible alias
BaseAgent = BaseRLModel
