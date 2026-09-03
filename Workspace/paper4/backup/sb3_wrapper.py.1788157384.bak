# src/baselines/sb3_wrapper.py
# ============================================================================
# Stable-Baselines3 Bridge for the Hybrid Uplink-Grant Action Space
#
# Shared infrastructure for the three "basic" baselines:
#     PPO   Schulman et al., arXiv:1707.06347, 2017
#     SAC   Haarnoja et al., ICML 2018 (PMLR 80:1861-1870)
#     TD3   Fujimoto et al., ICML 2018 (PMLR 80:1587-1596)
#
# Our grant is hybrid -- (Delta, ch, p) with Delta and p continuous and ch
# discrete -- and SB3's PPO/SAC/TD3 accept a single Box (SAC and TD3 are
# Box-only). Per librarian/baselines_v2.json the agreed wrapper, identical
# across all three so the basic baselines stay comparable, exposes a
# 3-dim Box in [-1, 1]:
#
#     dim 0 -> Delta, GEOMETRIC over [delta_min, delta_max]
#     dim 1 -> p,     LINEAR    over [p_min, p_max]     (dBm is already log)
#     dim 2 -> binned into the num_channels subchannels (equal-width bins)
#
# Every bound is read off `ActionDecoder`; no literal is restated here.
#
# NOTE on which ActionDecoder entry point is used. `ActionDecoder.decode_action`
# is the legacy path for *logit* heads: it applies a sigmoid and then a LINEAR
# interpolation over [delta_min, delta_max]. The design-mandated mapping is the
# geometric one, which lives in `delta_from_unit` / `unit_from_delta`. Our Box
# dimension is already a bounded unit coordinate rather than a logit, so this
# wrapper composes the affine [-1, 1] -> [0, 1] rescale with those two geometric
# methods and never calls `decode_action` / `encode_action`.
#
# The class hierarchy below (`SB3BaselineModel`) additionally solves the single
# hardest integration constraint: `hot_swap_trainer.DualModelHotSwapManager`
# performs an atomic in-place copy by zipping `act_model.parameters()` against
# `rest_model.parameters()`, so every trainable tensor an SB3 algorithm owns
# must be visible as a parameter of *this* `nn.Module`. We therefore register
# the SB3 policy as a submodule (`self.policy = sb3_model.policy`) instead of
# hiding it inside the SB3 object, and any trainable tensor the algorithm keeps
# outside its policy (SAC's `log_ent_coef`) is re-registered as a real
# `nn.Parameter` and handed back to SB3 by reference.
# ============================================================================

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import gymnasium as gym
import numpy as np
import torch
from gymnasium import spaces

from src.baselines.base_agent import BaseRLModel
from src.rl_interface import STATE_DIM, ActionDecoder

#: Width of the Box exposed to SB3: (Delta, p, subchannel-selector).
SB3_ACTION_DIM: int = 3

#: Index of each semantic quantity inside that Box vector.
DIM_DELTA: int = 0
DIM_POWER: int = 1
DIM_CHANNEL: int = 2

#: Box bounds. SB3's TD3/SAC actors emit tanh-squashed actions, so a symmetric
#: unit box is the natural (and rescale-free) target.
BOX_LOW: float = -1.0
BOX_HIGH: float = 1.0


class HybridActionBoxWrapper:
    """
    Bidirectional bridge between a 3-dim Box in [-1, 1] and the grant 3-tuple
    (delta_s, channel_idx, power_dbm).

    Both directions are needed: `to_grant` decodes what an SB3 policy emitted so
    the environment can act on it, and `from_grant` re-encodes a grant that was
    produced elsewhere (e.g. replayed from a checkpoint or a heuristic) back into
    the Box coordinates the SB3 networks consume during `update()`.

    All ranges are read from the supplied `ActionDecoder`, which is the single
    source of truth for the action space.
    """

    def __init__(self, decoder: ActionDecoder) -> None:
        self.decoder = decoder
        self.num_channels = int(decoder.num_channels)

    # ------------------------------------------------------------------
    # Space definitions
    # ------------------------------------------------------------------
    @property
    def action_space(self) -> spaces.Box:
        """The Box that SB3's PPO/SAC/TD3 actually see."""
        return spaces.Box(
            low=BOX_LOW,
            high=BOX_HIGH,
            shape=(SB3_ACTION_DIM,),
            dtype=np.float32,
        )

    @staticmethod
    def observation_space(state_dim: int) -> spaces.Box:
        """StateVectorizer emits a normalized vector in [-1, 1] of width `state_dim`."""
        return spaces.Box(low=-1.0, high=1.0, shape=(int(state_dim),), dtype=np.float32)

    @property
    def channel_bin_width(self) -> float:
        """
        Width, in Box units, of one subchannel bin.

        TD3 is deterministic, so this is the scale its exploration noise on
        `DIM_CHANNEL` has to beat before the subchannel choice can change at all.
        """
        return (BOX_HIGH - BOX_LOW) / float(self.num_channels)

    # ------------------------------------------------------------------
    # Box -> grant
    # ------------------------------------------------------------------
    @staticmethod
    def _to_unit(value: float) -> float:
        """Affine rescale [-1, 1] -> [0, 1], clipped (PPO's Gaussian is unbounded)."""
        u = (float(value) - BOX_LOW) / (BOX_HIGH - BOX_LOW)
        return float(min(max(u, 0.0), 1.0))

    @staticmethod
    def _from_unit(u: float) -> float:
        """Affine rescale [0, 1] -> [-1, 1]."""
        return float(BOX_LOW + min(max(float(u), 0.0), 1.0) * (BOX_HIGH - BOX_LOW))

    def channel_from_box(self, value: float) -> int:
        """Equal-width binning of one Box coordinate into {0 .. num_channels-1}."""
        idx = int(self._to_unit(value) * self.num_channels)
        return int(min(max(idx, 0), self.num_channels - 1))

    def channel_to_box(self, ch: int) -> float:
        """Inverse binning: the *centre* of bin `ch`, i.e. the maximally robust
        representative of that bin under the noise TD3 adds on top."""
        ch = int(ch) % self.num_channels
        return self._from_unit((ch + 0.5) / float(self.num_channels))

    def to_grant(self, box_action: Union[np.ndarray, Sequence[float], torch.Tensor]) -> Tuple[float, int, float]:
        """
        Decode a Box action into (delta_s, channel_idx, power_dbm).

        Delta uses the geometric map (`ActionDecoder.delta_from_unit`); power is
        linear over [p_min, p_max]; the subchannel is the equal-width bin index.
        """
        arr = self._as_vector(box_action)
        dec = self.decoder

        delta = dec.delta_from_unit(self._to_unit(arr[DIM_DELTA]))
        power = dec.p_min + self._to_unit(arr[DIM_POWER]) * (dec.p_max - dec.p_min)
        ch = self.channel_from_box(arr[DIM_CHANNEL])
        return (float(delta), int(ch), float(power))

    # ------------------------------------------------------------------
    # grant -> Box
    # ------------------------------------------------------------------
    def from_grant(self, delta_s: float, ch: int, power_dbm: float) -> np.ndarray:
        """Encode a grant 3-tuple back into the Box coordinates SB3 trains on."""
        dec = self.decoder
        u_delta = dec.unit_from_delta(float(delta_s))
        u_power = (float(power_dbm) - dec.p_min) / max(1e-9, dec.p_max - dec.p_min)
        return np.array(
            [
                self._from_unit(u_delta),
                self._from_unit(u_power),
                self.channel_to_box(ch),
            ],
            dtype=np.float32,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _as_vector(box_action: Union[np.ndarray, Sequence[float], torch.Tensor]) -> np.ndarray:
        """Flatten any accepted action container to a length-SB3_ACTION_DIM float array."""
        if isinstance(box_action, torch.Tensor):
            arr = box_action.detach().cpu().numpy()
        else:
            arr = np.asarray(box_action, dtype=np.float32)
        arr = np.asarray(arr, dtype=np.float32).reshape(-1)
        if arr.size < SB3_ACTION_DIM:
            arr = np.concatenate([arr, np.zeros(SB3_ACTION_DIM - arr.size, dtype=np.float32)])
        return arr[:SB3_ACTION_DIM]


class HybridGrantSpecEnv(gym.Env):
    """
    A specification-only `gymnasium.Env`.

    SB3 algorithms are constructed against an env because that is where they read
    `observation_space` / `action_space` from and how they size their internal
    buffers. Our training loop is driven by `hot_swap_trainer` (SUMO on one side,
    `RetrospectiveReplayBuffer` on the other), so this env is never stepped: it
    exists purely to declare the two spaces to SB3.
    """

    metadata: Dict[str, Any] = {"render_modes": []}

    def __init__(self, observation_space: spaces.Box, action_space: spaces.Box) -> None:
        super().__init__()
        self.observation_space = observation_space
        self.action_space = action_space

    def _zero_obs(self) -> np.ndarray:
        return np.zeros(self.observation_space.shape, dtype=np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None):
        super().reset(seed=seed)
        return self._zero_obs(), {}

    def step(self, action):
        return self._zero_obs(), 0.0, False, False, {}


def move_optimizer_state(optimizer: Optional[torch.optim.Optimizer], device: torch.device) -> None:
    """
    Follow an optimizer's state tensors (Adam moments, step counters) onto `device`.

    `nn.Module.to()` moves parameters in place and keeps their identity, so the
    optimizer's parameter references stay valid; its *state* tensors, however,
    are plain tensors it allocated itself and have to be moved explicitly.
    """
    if optimizer is None:
        return
    for state in optimizer.state.values():
        for key, value in list(state.items()):
            if isinstance(value, torch.Tensor):
                state[key] = value.to(device)


class SB3BaselineModel(BaseRLModel):
    """
    Common base for the SB3-backed baselines.

    Responsibilities:

    1. Build the real SB3 algorithm object against `HybridGrantSpecEnv`, so the
       networks, their initialization, their optimizers and every default
       hyper-parameter come from Stable-Baselines3 rather than a re-implementation.
    2. Register `sb3_model.policy` as a submodule of `self`, which is what makes
       `self.parameters()`, `self.state_dict()`, `self.to()` and therefore
       `DualModelHotSwapManager.hot_swap()` see the SB3 weights at all.
    3. Own the `HybridActionBoxWrapper` and expose the batch unpacking that
       `RetrospectiveReplayBuffer.sample()` feeds into `update()`.

    Subclasses implement `select_action` and `update`, and drive the gradient
    step through the SB3 policy's own optimizers.
    """

    #: SB3 algorithm class, set by each subclass.
    SB3_ALGO: Any = None

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.wrapper = HybridActionBoxWrapper(self.decoder)
        self._sb3: Any = None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_sb3(
        self,
        algo_cls: Any,
        policy: str = "MlpPolicy",
        device: Union[str, torch.device] = "auto",
        seed: Optional[int] = None,
        **algo_kwargs: Any,
    ) -> Any:
        """
        Instantiate the SB3 algorithm and expose its policy as our submodule.

        Must be called by every subclass' `__init__`.
        """
        spec_env = HybridGrantSpecEnv(
            observation_space=HybridActionBoxWrapper.observation_space(self.state_dim),
            action_space=self.wrapper.action_space,
        )
        sb3_model = algo_cls(
            policy,
            spec_env,
            device=device,
            seed=seed,
            verbose=0,
            **algo_kwargs,
        )
        # Plain attribute: an SB3 algorithm is not an nn.Module, so this does not
        # register anything. The next line is the one that matters.
        self._sb3 = sb3_model
        # Registering the SB3 policy as a submodule is what makes its weights
        # part of our state_dict()/parameters() and hence hot-swappable.
        self.policy = sb3_model.policy
        return sb3_model

    # ------------------------------------------------------------------
    # Device handling
    # ------------------------------------------------------------------
    def sb3_optimizers(self) -> List[torch.optim.Optimizer]:
        """Every optimizer the SB3 algorithm owns (overridden per algorithm)."""
        opt = getattr(self.policy, "optimizer", None)
        return [opt] if opt is not None else []

    def _sync_device(self, device: torch.device) -> None:
        """
        Keep SB3's bookkeeping in step with `nn.Module.to()`.

        `hot_swap_trainer` constructs Act and Rest models and immediately moves
        them to different devices, so the SB3 algorithm's own `device` attribute
        (used by its tensor helpers) and its optimizer state must follow.
        `policy.device` is a read-only property derived from the parameters, so
        it tracks automatically.
        """
        if self._sb3 is None:
            return
        self._sb3.device = device
        for opt in self.sb3_optimizers():
            move_optimizer_state(opt, device)

    def to(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        module = super().to(*args, **kwargs)
        try:
            device, _dtype, _non_blocking, _fmt = torch._C._nn._parse_to(*args, **kwargs)
        except Exception:
            device = None
        if device is not None:
            module._sync_device(torch.device(device))
        return module

    @property
    def device(self) -> torch.device:
        """Device the policy parameters currently live on."""
        for param in self.parameters():
            return param.device
        return torch.device("cpu")

    # ------------------------------------------------------------------
    # Batch plumbing
    # ------------------------------------------------------------------
    def unpack_batch(
        self, batch: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Unpack exactly what `RetrospectiveReplayBuffer.sample()` produces.

        Returns (states, actions, rewards, next_states, dones, discounts) with
        shapes (N, state_dim), (N, 3), (N, 1), (N, state_dim), (N, 1), (N, 1).

        `discount` is the SMDP factor gamma**delta_t supplied per transition; it
        replaces the scalar `self.gamma` in the SB3 update rules. SB3 2.7 already
        takes exactly this substitution for n-step replay
        (`discounts = replay_data.discounts if ... else self.gamma`), so the
        variable-interval discount is applied at the same place SB3 applies its own.

        The optional `action_idx` key is emitted only for discrete-action
        baselines; our action head is fully continuous, so it is ignored.
        """
        device = self.device
        states = batch["state"].to(device=device, dtype=torch.float32)
        actions = batch["action"].to(device=device, dtype=torch.float32)
        rewards = batch["reward"].to(device=device, dtype=torch.float32)
        next_states = batch["next_state"].to(device=device, dtype=torch.float32)
        dones = batch["done"].to(device=device, dtype=torch.float32)

        if "discount" in batch:
            discounts = batch["discount"].to(device=device, dtype=torch.float32)
        else:
            # Buffers that predate the SMDP discount key fall back to gamma**delta_t.
            gamma = float(getattr(self, "gamma", 0.99))
            delta_t = batch.get("delta_t")
            if delta_t is None:
                discounts = torch.full_like(rewards, gamma)
            else:
                discounts = torch.pow(
                    torch.as_tensor(gamma, device=device),
                    delta_t.to(device=device, dtype=torch.float32),
                )

        if states.dim() == 1:
            states = states.unsqueeze(0)
        if next_states.dim() == 1:
            next_states = next_states.unsqueeze(0)
        if actions.dim() == 1:
            actions = actions.unsqueeze(0)
        if actions.shape[-1] != SB3_ACTION_DIM:
            raise ValueError(
                f"{type(self).__name__}.update() expects {SB3_ACTION_DIM}-dim Box actions "
                f"(the shared SB3 wrapper), got shape {tuple(actions.shape)}. The replay "
                "buffer was filled by a model with a different action encoding."
            )
        rewards = rewards.reshape(-1, 1)
        dones = dones.reshape(-1, 1)
        discounts = discounts.reshape(-1, 1)
        return states, actions, rewards, next_states, dones, discounts

    # ------------------------------------------------------------------
    def decode(self, box_action: Union[np.ndarray, torch.Tensor]) -> Tuple[float, int, float]:
        """Box vector -> (delta_s, channel_idx, power_dbm)."""
        return self.wrapper.to_grant(box_action)

    def encode(self, delta_s: float, ch: int, power_dbm: float) -> np.ndarray:
        """(delta_s, channel_idx, power_dbm) -> Box vector."""
        return self.wrapper.from_grant(delta_s, ch, power_dbm)
