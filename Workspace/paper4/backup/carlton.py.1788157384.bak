# src/baselines/carlton.py
# ============================================================================
# CARLTON -- SINR-Aware Multi-Agent RL for Distributed Dynamic Channel Allocation
#
# Y. Cohen, T. Gafni, R. Greenberg and K. Cohen, "SINR-Aware Deep Reinforcement
# Learning for Distributed Dynamic Channel Allocation in Cognitive Interference
# Networks," IEEE Transactions on Wireless Communications, vol. 24, no. 1,
# pp. 228--243, 2025. DOI: 10.1109/TWC.2024.3491035
#
# ---------------------------------------------------------------------------
# WHAT THE ORIGINAL PAPER DOES
# ---------------------------------------------------------------------------
# CARLTON solves distributed dynamic channel allocation in cognitive interference
# networks WITHOUT the usual perfect-orthogonality / one-to-one user-channel
# assumptions: channels are reused across overlapping networks and inter-carrier
# interference is modelled explicitly. Each transmitter's observation is its own
# local SINR / interference measurement; its action is PURELY DISCRETE -- which
# of K channels to occupy. Training is Centralized Training with Decentralized
# Execution over the DeepMellow value-based learner, and the objective is a
# global SINR measure subject to per-network QoS-SINR targets. DeepMellow
# replaces the max in the Bellman backup with the mellowmax operator
# mm_omega(q) = (1/omega) * log((1/n) * sum_i exp(omega * q_i)), whose
# contraction property is what lets the algorithm drop the target network.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION KEEPS
# ---------------------------------------------------------------------------
# * The problem it was built for. Our uplink is one bandwidth split into
#   num_channels frequency-separated subchannels contended by many vehicles under
#   a Rayleigh SINR model with reuse and collisions -- CARLTON's exact setting.
#   The subchannel head IS the paper's original action, unmodified.
# * The DeepMellow learner: mellowmax Bellman backup, and consequently NO target
#   network by default (`use_target_network=False`). This is the paper's learner,
#   not a substitute.
# * CTDE. Agents are the in-range vehicles; one shared-parameter network is
#   trained at the RSU on experience pooled across all of them. Our scheduler is
#   centralised at a single RSU by construction, so "centralised training" here
#   describes the actual deployment rather than adding an assumption the
#   deployment cannot meet.
# * The role of the paper's local interference measurement is played by the
#   contention indicators the StateVectorizer already emits (channel busy ratio
#   and the active-vehicle count), so no observation surgery is needed.
#
# ---------------------------------------------------------------------------
# WHAT THIS REIMPLEMENTATION ADDS OR CHANGES, AND WHY  (OUR EXTENSIONS)
# ---------------------------------------------------------------------------
# * THE TWO CONTINUOUS AXES ARE OUR ADDITION, NOT THE PAPER'S. CARLTON has no
#   power action and no timing action at all. We extend it exactly the way the
#   companion discrete baseline (SPAM-D3QN, Bai et al. 2024) is extended: Delta is
#   quantised onto the same geometric grid and p onto the same linear dBm grid,
#   and the value-based DeepMellow update is kept. The two grids are deliberately
#   IDENTICAL to SPAM-D3QN's so that a comparison between the two baselines
#   isolates the learner rather than the quantisation.
# * A BRANCHING (factored) Q-head is our addition. The paper needs a single
#   K-way head because it has a single action factor; with three factors a joint
#   head would be num_delta * num_power * num_channels wide. We therefore use one
#   Q-branch per factor, aggregated in the Branching-DQN manner
#   (Q(s, a) = mean_b Q_b(s, a_b)), with the mellowmax backup applied per branch.
#   Honest consequence: branching assumes the factors are conditionally
#   independent given s, so cross-factor coupling (e.g. "a high power is only
#   worth paying for on an uncontended subchannel") is representable only through
#   the shared trunk. That is a weakening relative to a joint head.
# * THE REWARD IS SUBSTITUTED. CARLTON maximises a global SINR measure and
#   contributes NO AoI term of its own. The objective optimised here is our
#   pipeline's four-term AoI reward. This substitution must be stated in the
#   paper: what is being compared is CARLTON's learner and channel-allocation
#   formulation, not CARLTON's objective.
# * The exploration policy is the mellowmax-induced Boltzmann policy with the
#   temperature simplified to beta = omega. The exact DeepMellow policy obtains
#   beta by root-finding on sum_i exp(beta * (q_i - mm)) * (q_i - mm) = 0; using
#   beta = omega is the standard practical shortcut and changes only the
#   exploration temperature, not the backup.
# ============================================================================

from __future__ import annotations
import copy
import math
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from src.baselines.base_agent import BaseRLModel
from src.rl_interface import ActionDecoder, STATE_DIM


# The two grid builders below are duplicated verbatim from
# src/baselines/spam_d3qn.py rather than imported, so the two baseline modules
# stay independent of one another. The librarian note requires the grids to be
# IDENTICAL across the two discretised baselines; that equality is asserted in
# etc/scripts/verify_baselines_similar.py rather than enforced by an import.
def build_geometric_delta_grid(decoder: ActionDecoder, num_levels: int) -> List[float]:
    """
    Geometric quantisation of the decoder's Delta range, endpoints inclusive.
    Built through ActionDecoder.delta_from_unit so there is one definition of the
    mapping. For the shipped bounds the grid is, to 2 d.p.:
        [0.10, 0.24, 0.57, 1.37, 3.28, 7.85, 18.79, 45.00] seconds
    (illustrative; the values are derived from the decoder at run time).
    """
    n = max(2, int(num_levels))
    return [float(decoder.delta_from_unit(i / (n - 1))) for i in range(n)]


def build_linear_power_grid(decoder: ActionDecoder, num_levels: int) -> List[float]:
    """Linear quantisation of the decoder's power range (dBm is already log-scaled)."""
    n = max(2, int(num_levels))
    lo, hi = decoder.p_min, decoder.p_max
    return [float(lo + (hi - lo) * (i / (n - 1))) for i in range(n)]


def mellowmax(q: torch.Tensor, omega: float, dim: int = -1, keepdim: bool = False) -> torch.Tensor:
    """
    DeepMellow's mellowmax operator, computed via logsumexp for stability:

        mm_omega(q) = (logsumexp(omega * q) - log(n)) / omega

    It is a non-expansion for every omega > 0 and interpolates between the mean
    (omega -> 0) and the max (omega -> inf). Substituting it for max in the
    Bellman backup is what removes the need for a target network.
    """
    n = q.shape[dim]
    w = max(float(omega), 1e-6)
    return (torch.logsumexp(w * q, dim=dim, keepdim=keepdim) - math.log(n)) / w


class CARLTON(BaseRLModel):
    """
    DeepMellow branching Q-learner over (Delta, power, subchannel).

    Branch layout and the combined index are kept bit-compatible with SPAM-D3QN:

        idx = (delta_idx * num_power_levels + power_idx) * num_channels + ch

    so the same replay transitions, and the same optional `action_idx`, are
    interpretable by either baseline.
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
        omega: float = 10.0,
        use_target_network: bool = False,
        tau: float = 0.005,
        grad_clip: float = 0.5,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        self.omega = float(omega)
        self.use_target_network = bool(use_target_network)
        self.tau = float(tau)
        self.grad_clip = float(grad_clip)
        self.total_updates = 0

        # ------------------------------------------------------------------
        # Shared discretisation grid (identical to SPAM-D3QN's by construction)
        # ------------------------------------------------------------------
        self.delta_candidates = build_geometric_delta_grid(self.decoder, num_delta_levels)
        self.power_candidates = build_linear_power_grid(self.decoder, num_power_levels)
        self.num_delta_levels = len(self.delta_candidates)
        self.num_power_levels = len(self.power_candidates)
        #: Branch cardinalities, ordered (Delta, power, subchannel).
        self.branch_sizes: Tuple[int, int, int] = (
            self.num_delta_levels,
            self.num_power_levels,
            self.num_channels,
        )
        self.num_actions = self.num_delta_levels * self.num_power_levels * self.num_channels

        if self.decoder.delta_min > 0.0 and self.decoder.delta_max > self.decoder.delta_min:
            self._log_delta_ratio = math.log(self.decoder.delta_max / self.decoder.delta_min)
        else:
            self._log_delta_ratio = 0.0

        # ------------------------------------------------------------------
        # Shared trunk + one Q-branch per action factor
        # ------------------------------------------------------------------
        self.trunk = nn.Sequential(
            nn.Linear(self.state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.branches = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim // 2),
                    nn.ReLU(),
                    nn.Linear(hidden_dim // 2, size),
                )
                for size in self.branch_sizes
            ]
        )

        # DeepMellow needs no target network; one is available for ablation only.
        if self.use_target_network:
            self.target_trunk = copy.deepcopy(self.trunk)
            self.target_branches = copy.deepcopy(self.branches)
            for module in (self.target_trunk, self.target_branches):
                for p in module.parameters():
                    p.requires_grad = False

        self._online_params = list(self.trunk.parameters()) + list(self.branches.parameters())
        self.optimizer = optim.Adam(self._online_params, lr=float(lr))

        self._last_action_indices: np.ndarray = np.zeros(0, dtype=np.int64)
        self._last_branch_indices: np.ndarray = np.zeros((0, 3), dtype=np.int64)

    # ----------------------------------------------------------------------
    # Index packing (kept identical to SPAM-D3QN)
    # ----------------------------------------------------------------------
    def pack_action_index(self, delta_idx: int, power_idx: int, ch: int) -> int:
        return int((int(delta_idx) * self.num_power_levels + int(power_idx)) * self.num_channels + int(ch))

    def unpack_action_index(self, action_idx: int) -> Tuple[int, int, int]:
        idx = int(action_idx) % self.num_actions
        ch = idx % self.num_channels
        rest = idx // self.num_channels
        return int(rest // self.num_power_levels), int(rest % self.num_power_levels), int(ch)

    def _branch_indices_from_combined(self, idx: torch.Tensor) -> torch.Tensor:
        """Vectorised combined-index -> (B, 3) branch indices."""
        idx = idx.long().remainder(self.num_actions)
        ch = idx.remainder(self.num_channels)
        rest = torch.div(idx, self.num_channels, rounding_mode="floor")
        p_idx = rest.remainder(self.num_power_levels)
        d_idx = torch.div(rest, self.num_power_levels, rounding_mode="floor")
        return torch.stack([d_idx, p_idx, ch], dim=1)

    def _action_to_tuple(self, delta_idx: int, power_idx: int, ch: int) -> Tuple[float, int, float]:
        return (
            float(self.delta_candidates[int(delta_idx)]),
            int(ch),
            float(self.power_candidates[int(power_idx)]),
        )

    # ----------------------------------------------------------------------
    # Forward
    # ----------------------------------------------------------------------
    def _forward_branches(self, state: torch.Tensor, use_target: bool = False) -> List[torch.Tensor]:
        if use_target and self.use_target_network:
            h = self.target_trunk(state)
            return [branch(h) for branch in self.target_branches]
        h = self.trunk(state)
        return [branch(h) for branch in self.branches]

    def _infer_branch_indices(self, actions: torch.Tensor) -> torch.Tensor:
        """
        Recover (B, 3) branch indices from a raw action produced by
        ActionDecoder.encode_action. All three factors are recovered: dropping
        the Delta and power factors would leave two of the three Q-branches with
        no gradient at all. Delta is snapped in log space (its grid is
        geometric), power linearly.
        """
        dec = self.decoder
        acts = actions.float()
        delta = dec.delta_min + torch.sigmoid(acts[:, 0]) * (dec.delta_max - dec.delta_min)
        delta = delta.clamp(min=dec.delta_min, max=dec.delta_max)
        d_cands = torch.as_tensor(self.delta_candidates, dtype=delta.dtype, device=delta.device)
        if self._log_delta_ratio > 0.0:
            d_idx = torch.argmin((torch.log(delta).unsqueeze(1) - torch.log(d_cands).unsqueeze(0)).abs(), dim=1)
        else:
            d_idx = torch.argmin((delta.unsqueeze(1) - d_cands.unsqueeze(0)).abs(), dim=1)

        power = dec.p_min + torch.sigmoid(acts[:, 2]) * (dec.p_max - dec.p_min)
        p_cands = torch.as_tensor(self.power_candidates, dtype=power.dtype, device=power.device)
        p_idx = torch.argmin((power.unsqueeze(1) - p_cands.unsqueeze(0)).abs(), dim=1)

        ch = acts[:, 1].round().long().remainder(self.num_channels)
        return torch.stack([d_idx, p_idx, ch], dim=1)

    # ----------------------------------------------------------------------
    # Contract methods
    # ----------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        state_t = self._prepare_state_tensor(state)
        with torch.no_grad():
            q_branches = self._forward_branches(state_t, use_target=False)
            chosen: List[int] = []
            for q in q_branches:
                if deterministic:
                    chosen.append(int(torch.argmax(q, dim=-1)[0].item()))
                else:
                    # Mellowmax-induced Boltzmann policy with beta = omega
                    # (see the module docstring for the simplification).
                    probs = torch.softmax(self.omega * q[0], dim=-1)
                    chosen.append(int(torch.multinomial(probs, 1).item()))

        delta_idx, power_idx, ch = chosen[0], chosen[1], chosen[2]
        delta, ch, power = self._action_to_tuple(delta_idx, power_idx, ch)
        raw_action = self.decoder.encode_action(delta, ch, power)
        act_idx = self.pack_action_index(delta_idx, power_idx, ch)

        info: Dict[str, Any] = {
            "action_idx": act_idx,
            "delta_idx": int(delta_idx),
            "power_idx": int(power_idx),
            "channel_idx": int(ch),
            "q_branches": [q[0].detach().cpu().numpy() for q in q_branches],
            "raw_action": raw_action,
        }
        return (float(delta), int(ch), float(power)), raw_action, info

    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        device = next(self.parameters()).device
        states = batch["state"].to(device).float()
        rewards = batch["reward"].to(device).float()
        next_states = batch["next_state"].to(device).float()
        dones = batch["done"].to(device).float()

        if "discount" in batch:
            discounts = batch["discount"].to(device).float()
        else:
            delta_ts = batch.get("delta_t", torch.ones_like(rewards)).to(device).float()
            discounts = torch.pow(torch.as_tensor(self.gamma, device=device), delta_ts)

        # -- DeepMellow backup: mellowmax per branch, averaged (BDQ aggregation) --
        with torch.no_grad():
            next_branches = self._forward_branches(next_states, use_target=self.use_target_network)
            next_v = torch.stack(
                [mellowmax(q, self.omega, dim=-1, keepdim=True) for q in next_branches], dim=0
            ).mean(dim=0)
            y = rewards + (1.0 - dones) * discounts * next_v

        if "action_idx" in batch:
            branch_idx = self._branch_indices_from_combined(batch["action_idx"].to(device).reshape(-1))
        else:
            branch_idx = self._infer_branch_indices(batch["action"].to(device))
        self._last_branch_indices = branch_idx.detach().cpu().numpy()
        self._last_action_indices = (
            (branch_idx[:, 0] * self.num_power_levels + branch_idx[:, 1]) * self.num_channels + branch_idx[:, 2]
        ).detach().cpu().numpy()

        q_branches = self._forward_branches(states, use_target=False)
        losses = []
        q_taken_mean = 0.0
        for b, q in enumerate(q_branches):
            idx_b = branch_idx[:, b].clamp(0, self.branch_sizes[b] - 1).unsqueeze(1)
            q_taken = q.gather(1, idx_b)
            losses.append(torch.nn.functional.mse_loss(q_taken, y))
            q_taken_mean += float(q_taken.mean().item())
        loss = torch.stack(losses).mean()

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self._online_params, self.grad_clip)
        self.optimizer.step()

        self.total_updates += 1
        if self.use_target_network:
            with torch.no_grad():
                for p, pt in zip(self.trunk.parameters(), self.target_trunk.parameters()):
                    pt.data.copy_(self.tau * p.data + (1.0 - self.tau) * pt.data)
                for p, pt in zip(self.branches.parameters(), self.target_branches.parameters()):
                    pt.data.copy_(self.tau * p.data + (1.0 - self.tau) * pt.data)

        out = {
            "loss": float(loss.item()),
            "mean_q": float(q_taken_mean / max(1, len(q_branches))),
            "target_mean": float(y.mean().item()),
            "n_distinct_actions": float(np.unique(self._last_action_indices).size),
        }
        for name, branch_loss in zip(("delta", "power", "channel"), losses):
            out[f"loss_{name}"] = float(branch_loss.item())
        return out
