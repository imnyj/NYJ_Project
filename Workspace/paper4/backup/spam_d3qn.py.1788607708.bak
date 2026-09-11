# src/baselines/spam_d3qn.py
# ============================================================================
# SPAM-D3QN -- AoI-Aware Joint Scheduling and Power Allocation
#
# G. Bai, L. Qu, J. Liu and D. Sun, "AoI-Aware Joint Scheduling and Power
# Allocation in Intelligent Transportation System: A Deep Reinforcement
# Learning Approach," IEEE Transactions on Vehicular Technology, vol. 73,
# no. 4, pp. 5781--5795, 2024. DOI: 10.1109/TVT.2023.3333825
#
# ---------------------------------------------------------------------------
# WHAT THE ORIGINAL PAPER DOES
# ---------------------------------------------------------------------------
# Bai et al. model AoI minimisation in a Manhattan-grid V2I network as a
# SINGLE-AGENT MDP whose decision maker sits at the infrastructure side. The
# observation is the infrastructure-side view of per-vehicle AoI plus channel
# state; the action is FULLY DISCRETE and factorises as (which vehicle to
# schedule, which transmit-power level). The learner ("SPAM") is a Dueling
# Double DQN trained with Prioritized Experience Replay, PER being motivated by
# the scarcity of high-value transitions in the AoI objective.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION KEEPS
# ---------------------------------------------------------------------------
# * The decision maker's vantage point. Bai's agent already lives exactly where
#   ours lives (the roadside infrastructure), so the observation is our
#   StateVectorizer output UNCHANGED -- no re-derivation, no extra assumption.
# * The dueling architecture: shared trunk, scalar V(s) stream, per-action
#   A(s, a) stream, aggregated as Q = V + (A - mean(A)).
# * Double DQN target selection (online net argmax, target net evaluation).
# * A fully DISCRETE joint action head. This is the point of the baseline: it is
#   the fully-discretised reference against which our continuous Delta and p are
#   measured, so the discretisation is a feature, not a compromise.
# * Prioritized Experience Replay, in the reduced form described below.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION CHANGES OR DROPS, AND WHY
# ---------------------------------------------------------------------------
# * "Which vehicle to schedule" is dropped as an action dimension. Our pipeline
#   invokes the policy once per in-range vehicle and the grant it returns is that
#   vehicle's own grant, so vehicle identity is carried by the observation rather
#   than by the action index. Bai's scheduling decision survives as the choice of
#   Delta: granting a long interval is how this agent de-schedules a vehicle.
# * Two axes that are continuous in our formulation (Delta, p) are quantised onto
#   a fixed grid, and the subchannel becomes a third discrete factor. The paper
#   has no subchannel choice at all; that axis is our addition, required by our
#   4-subchannel contention model.
# * PER IS WEAKENED, and this is a real loss relative to the paper. The replay
#   buffer belongs to the pipeline (src.rl_interface.RetrospectiveReplayBuffer)
#   and samples UNIFORMLY; a baseline is not allowed to replace it. We therefore
#   apply PER's importance-sampling re-weighting WITHIN each uniformly-sampled
#   minibatch: proportional priorities p_i = (|delta_i| + eps)^alpha over the
#   batch, IS weights w_i = (N * P(i))^(-beta) normalised by max. This reproduces
#   PER's loss re-weighting but NOT its non-uniform sampling, so high-TD-error
#   transitions are still only seen as often as uniform replay shows them. Bai et
#   al. report PER as a material contributor to their 22.6% AoI gain, so this
#   baseline is expected to under-perform the published numbers on that account.
#   `self.last_priorities` is exposed so a PER-capable buffer can consume them if
#   one is ever plumbed in.
# ============================================================================

from __future__ import annotations
import copy
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import ActionDecoder, STATE_DIM


def build_geometric_delta_grid(decoder: ActionDecoder, num_levels: int) -> List[float]:
    """
    Quantise the decoder's Delta range onto a GEOMETRIC grid of `num_levels`
    points, endpoints inclusive.

    Delta spans a factor of (delta_max / delta_min) -- three orders of magnitude
    in the shipped configuration -- so a linear grid would spend almost every
    level in the long-interval regime and leave the short-interval regime, where
    AoI is actually controlled, with no resolution at all. Geometric spacing
    gives uniform *relative* resolution, matching the geometric mapping that
    ActionDecoder.delta_from_unit applies to the continuous baselines. Levels are
    produced by delta_from_unit itself so there is exactly one definition of the
    mapping in the codebase.

    For the shipped decoder bounds the grid is, to 2 d.p.:
        [0.10, 0.24, 0.57, 1.37, 3.28, 7.85, 18.79, 45.00] seconds
    (illustrative only -- the values are derived from the decoder at run time and
    track it automatically if the bounds change).
    """
    n = max(2, int(num_levels))
    return [float(decoder.delta_from_unit(i / (n - 1))) for i in range(n)]


def build_linear_power_grid(decoder: ActionDecoder, num_levels: int) -> List[float]:
    """
    Quantise the decoder's power range onto a LINEAR grid, endpoints inclusive.
    Linear is correct here: dBm is already a logarithmic unit, so equal steps in
    dBm are equal steps in ratio.
    """
    n = max(2, int(num_levels))
    lo, hi = decoder.p_min, decoder.p_max
    return [float(lo + (hi - lo) * (i / (n - 1))) for i in range(n)]


class SPAMD3QN(BaseRLModel):
    """
    Dueling Double DQN with within-batch prioritized replay over a discretised
    joint (Delta, power, subchannel) action space.

    The joint action index is packed as

        idx = (delta_idx * num_power_levels + power_idx) * num_channels + ch

    so that a single argmax over the advantage head selects all three factors at
    once, exactly as Bai's single Q-head selects (vehicle, power) at once. The
    index is returned in `info["action_idx"]` and is what `update()` gathers on;
    when the replay batch carries no explicit index, `_infer_action_indices`
    recovers the FULL index -- all three factors -- from the stored raw action.
    Recovering only the subchannel factor would leave the delta and power slices
    of the advantage head permanently untrained; that bug was found and fixed in
    the previous generation's dueling-Q model. The exhaustive
    encode -> recover round trip over all `num_actions` indices is asserted in
    `tests/test_baselines_action_roundtrip.py`.
    """

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        hidden_dim: int = 128,
        num_delta_levels: int = 8,
        num_power_levels: int = 4,
        lr: float = 3e-4,
        gamma: float = 0.99,
        target_update_freq: int = 100,
        epsilon_initial: float = 0.2,
        epsilon_decay: float = 0.999,
        epsilon_min: float = 0.01,
        per_alpha: float = 0.6,
        per_beta: float = 0.4,
        per_beta_increment: float = 1e-4,
        per_eps: float = 1e-6,
        grad_clip: float = 0.5,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.target_update_freq = max(1, int(target_update_freq))
        self.epsilon_decay = float(epsilon_decay)
        self.epsilon_min = float(epsilon_min)
        self.per_alpha = float(per_alpha)
        self.per_beta_increment = float(per_beta_increment)
        self.per_eps = float(per_eps)
        self.grad_clip = float(grad_clip)

        # Exploration / annealing state rides in BUFFERS, not plain attributes.
        # `DualModelHotSwapManager.hot_swap()` copies parameters and buffers from
        # the Rest model onto the Act model, and `update()` only ever runs on the
        # Rest model. As plain attributes these three never crossed the swap, so
        # the ACTING model's epsilon stayed pinned at `epsilon_initial` for the
        # whole run while the other epsilon-greedy baselines annealed to
        # `epsilon_min`, and neither epsilon nor per_beta survived a checkpoint
        # reload. Same rule as res_mapddpg.py / ma2hdqn.py.
        self.register_buffer("epsilon", torch.tensor(float(epsilon_initial)))
        self.register_buffer("per_beta", torch.tensor(float(per_beta)))
        self.register_buffer("total_updates", torch.zeros(1))

        # ------------------------------------------------------------------
        # Discretised joint action grid. Bounds come from the decoder only.
        # ------------------------------------------------------------------
        self.delta_candidates = build_geometric_delta_grid(self.decoder, num_delta_levels)
        self.power_candidates = build_linear_power_grid(self.decoder, num_power_levels)
        self.num_delta_levels = len(self.delta_candidates)
        self.num_power_levels = len(self.power_candidates)
        self.num_actions = self.num_delta_levels * self.num_power_levels * self.num_channels

        # ------------------------------------------------------------------
        # Dueling network
        # ------------------------------------------------------------------
        self.trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.adv_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, self.num_actions),
        )

        # Target network. Bai et al. use the standard periodic hard copy rather
        # than Polyak averaging, so the target parameters are legitimately frozen
        # between refreshes.
        self.target_trunk = copy.deepcopy(self.trunk)
        self.target_value_head = copy.deepcopy(self.value_head)
        self.target_adv_head = copy.deepcopy(self.adv_head)
        for module in (self.target_trunk, self.target_value_head, self.target_adv_head):
            for p in module.parameters():
                p.requires_grad = False

        self._online_params = (
            list(self.trunk.parameters())
            + list(self.value_head.parameters())
            + list(self.adv_head.parameters())
        )
        self.optimizer = optim.Adam(self._online_params, lr=float(lr))

        # Diagnostics consumed by the verification script.
        self.last_priorities: np.ndarray = np.zeros(0, dtype=np.float32)
        self._last_action_indices: np.ndarray = np.zeros(0, dtype=np.int64)

    # ----------------------------------------------------------------------
    # Action-index packing / unpacking
    # ----------------------------------------------------------------------
    def pack_action_index(self, delta_idx: int, power_idx: int, ch: int) -> int:
        """(delta_idx, power_idx, ch) -> combined index in [0, num_actions)."""
        return int((int(delta_idx) * self.num_power_levels + int(power_idx)) * self.num_channels + int(ch))

    def unpack_action_index(self, action_idx: int) -> Tuple[int, int, int]:
        """Combined index -> (delta_idx, power_idx, ch)."""
        idx = int(action_idx) % self.num_actions
        ch = idx % self.num_channels
        rest = idx // self.num_channels
        power_idx = rest % self.num_power_levels
        delta_idx = rest // self.num_power_levels
        return int(delta_idx), int(power_idx), int(ch)

    def _action_to_tuple(self, action_idx: int) -> Tuple[float, int, float]:
        """Combined index -> the contract's decoded grant (delta_s, ch, power_dbm)."""
        delta_idx, power_idx, ch = self.unpack_action_index(action_idx)
        return (float(self.delta_candidates[delta_idx]), int(ch), float(self.power_candidates[power_idx]))

    def _forward_q(self, state: torch.Tensor, use_target: bool = False) -> torch.Tensor:
        trunk = self.target_trunk if use_target else self.trunk
        v_head = self.target_value_head if use_target else self.value_head
        a_head = self.target_adv_head if use_target else self.adv_head
        h = trunk(state)
        v = v_head(h)
        a = a_head(h)
        return v + (a - a.mean(dim=-1, keepdim=True))

    def _infer_action_indices(self, actions: torch.Tensor) -> torch.Tensor:
        """
        Recover the FULL combined action index from the stored raw action.

        Raw actions are produced by `ActionDecoder.encode_action`, whose Delta
        field is `logit(unit_from_delta(delta))` -- the logit of the GEOMETRIC
        unit coordinate, NOT of a linear normalisation. This method used to
        invert it linearly, which mapped 6 of the 8 Delta levels onto the wrong
        grid slot and so trained the wrong column of the advantage head for
        96 of the 128 joint actions.

        The inversion now goes through `BaseRLModel.raw_units`, and the snap onto
        the grid happens in the decoder's unit coordinate rather than in Delta or
        log-Delta space. That coordinate is where both grids are actually built
        (`delta_from_unit(i / (n - 1))`, `p_min + (p_max - p_min) * i / (n - 1)`),
        so the round trip is exact by construction and stays exact if the decoder
        ever changes its Delta geometry again.

        All THREE factors are recovered -- recovering only `ch` would train a
        1/(num_delta_levels * num_power_levels) prefix-slice of the advantage head
        and silently freeze the rest.

        Only used when the batch carries no explicit "action_idx"; note that the
        live pipeline (hot_swap_trainer.TransitionStreamer) does not currently
        plumb the index through, so this IS the path that runs in training.
        """
        u_delta, u_power = self.raw_units(actions)
        d_idx = self.snap_unit_to_grid(u_delta, self.num_delta_levels)
        p_idx = self.snap_unit_to_grid(u_power, self.num_power_levels)
        ch = self.raw_channel(actions)
        return (d_idx * self.num_power_levels + p_idx) * self.num_channels + ch

    # ----------------------------------------------------------------------
    # Contract methods
    # ----------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        eps = float(self.epsilon.item())
        with torch.no_grad():
            q_vals = self._forward_q(state_t, use_target=False)
            if (not deterministic) and np.random.rand() < eps:
                act_idx = int(np.random.randint(0, self.num_actions))
            else:
                act_idx = int(torch.argmax(q_vals, dim=-1)[0].item())

        delta, ch, power = self._action_to_tuple(act_idx)
        raw_action = self.decoder.encode_action(delta, ch, power)
        delta_idx, power_idx, _ = self.unpack_action_index(act_idx)

        info: Dict[str, Any] = {
            "action_idx": act_idx,
            "delta_idx": delta_idx,
            "power_idx": power_idx,
            "channel_idx": int(ch),
            "q_values": q_vals[0].detach().cpu().numpy(),
            "raw_action": raw_action,
            "epsilon": eps,
        }
        return (float(delta), int(ch), float(power)), raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        device = next(self.parameters()).device
        states = batch["state"].to(device).float()
        rewards = batch["reward"].to(device).float()
        next_states = batch["next_state"].to(device).float()
        dones = batch["done"].to(device).float()

        # SMDP discount from THIS model's gamma (see BaseRLModel.smdp_discounts).
        discounts = self.smdp_discounts(batch, rewards)

        # -- Double DQN target -------------------------------------------------
        with torch.no_grad():
            next_best = torch.argmax(self._forward_q(next_states, use_target=False), dim=-1, keepdim=True)
            next_q = self._forward_q(next_states, use_target=True).gather(1, next_best)
            y = rewards + (1.0 - dones) * discounts * next_q

        curr_q = self._forward_q(states, use_target=False)

        if "action_idx" in batch:
            action_indices = batch["action_idx"].to(device).long().reshape(-1)
        else:
            action_indices = self._infer_action_indices(batch["action"].to(device))
        action_indices = action_indices.clamp(0, self.num_actions - 1)
        self._last_action_indices = action_indices.detach().cpu().numpy().reshape(-1)

        q_pred = curr_q.gather(1, action_indices.unsqueeze(1))
        td_error = q_pred - y

        # -- Within-batch PER re-weighting (see module docstring for the caveat) --
        with torch.no_grad():
            priorities = (td_error.abs() + self.per_eps).pow(self.per_alpha).reshape(-1)
            probs = priorities / priorities.sum().clamp_min(1e-12)
            n = float(priorities.numel())
            is_weights = (n * probs).clamp_min(1e-12).pow(-float(self.per_beta.item()))
            is_weights = is_weights / is_weights.max().clamp_min(1e-12)
            self.last_priorities = priorities.detach().cpu().numpy()
        if "weights" in batch:  # honour an externally supplied PER weight vector
            is_weights = batch["weights"].to(device).float().reshape(-1)

        loss = (is_weights * td_error.pow(2).reshape(-1)).mean()

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self._online_params, self.grad_clip)
        self.optimizer.step()

        # -- Periodic hard target refresh (Bai et al. use a hard copy) ----------
        self.total_updates.add_(1.0)
        if int(self.total_updates.item()) % self.target_update_freq == 0:
            with torch.no_grad():
                self.target_trunk.load_state_dict(self.trunk.state_dict())
                self.target_value_head.load_state_dict(self.value_head.state_dict())
                self.target_adv_head.load_state_dict(self.adv_head.state_dict())

        # In-place so the registered buffers keep their identity (a plain
        # assignment would shadow them with Python floats and break the hot swap).
        with torch.no_grad():
            self.epsilon.fill_(max(self.epsilon_min, float(self.epsilon.item()) * self.epsilon_decay))
            self.per_beta.fill_(min(1.0, float(self.per_beta.item()) + self.per_beta_increment))

        return {
            "loss": float(loss.item()),
            "td_error": float(td_error.abs().mean().item()),
            "mean_q": float(curr_q.mean().item()),
            "epsilon": float(self.epsilon.item()),
            "per_beta": float(self.per_beta.item()),
            "n_distinct_actions": float(np.unique(self._last_action_indices).size),
        }
