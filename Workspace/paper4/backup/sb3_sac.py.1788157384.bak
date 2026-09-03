# src/baselines/sb3_sac.py
# ============================================================================
# SAC -- Soft Actor-Critic (Haarnoja et al., ICML 2018, PMLR 80:1861-1870)
#
# Basic baseline 2/3, implemented via Stable-Baselines3 (`stable_baselines3.SAC`)
# and wrapped for our hybrid grant with the SAME 3-dim Box wrapper as PPO and TD3
# (`src/baselines/sb3_wrapper.py`): dims 0,1 -> Delta (geometric) and p (linear),
# dim 2 binned to one of the num_channels subchannels. SB3's SAC is Box-only, so
# per librarian/baselines_v2.json the binning wrapper is mandatory here rather
# than optional.
#
# ENTROPY TARGET. SB3's `target_entropy="auto"` resolves to -dim(A), i.e. -3.0
# for our 3-dim Box. That heuristic was tuned for MuJoCo-style action spaces
# where every dimension is a genuine continuous control; here dim 2 is a
# *binned discrete* selector, so the entropy the policy needs on that dimension
# is qualitatively different from what it needs on Delta and p -- too little and
# the subchannel choice freezes, too much and the tanh-Gaussian smears Delta and
# p uniformly. The spec therefore requires `target_entropy` to be re-tuned; it is
# exposed verbatim as a constructor hparam so `src/hpo.py` can put it in the
# Optuna search space alongside the reward weights w1-w4.
#
# The update below mirrors `stable_baselines3.SAC.train()` with one substitution:
# the scalar `self.gamma` is replaced by the per-transition SMDP discount
# gamma**delta_t carried in the batch. SB3 2.7 already makes exactly this
# substitution for n-step replay
# (`discounts = replay_data.discounts if replay_data.discounts is not None else self.gamma`),
# so this is the sanctioned insertion point, not a deviation from the algorithm.
# ============================================================================

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from stable_baselines3 import SAC as SB3SAC
from stable_baselines3.common.utils import polyak_update

from src.baselines.sb3_wrapper import SB3BaselineModel
from src.rl_interface import STATE_DIM


class SAC(SB3BaselineModel):
    """SAC baseline backed by `stable_baselines3.SAC`'s SACPolicy."""

    SB3_ALGO = SB3SAC

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        ent_coef: Union[str, float] = "auto",
        target_entropy: Union[str, float] = "auto",
        target_update_interval: int = 1,
        policy: str = "MlpPolicy",
        policy_kwargs: Optional[Dict[str, Any]] = None,
        device: Union[str, torch.device] = "auto",
        seed: Optional[int] = None,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)

        # buffer_size=1: SB3 allocates its own ReplayBuffer at construction, but our
        # transitions come from RetrospectiveReplayBuffer, so the default 1e6-slot
        # buffer would be pure waste (twice over -- Act and Rest are both built).
        self._build_sb3(
            SB3SAC,
            policy=policy,
            device=device,
            seed=seed,
            learning_rate=learning_rate,
            buffer_size=1,
            gamma=self.gamma,
            tau=tau,
            ent_coef=ent_coef,
            target_entropy=target_entropy,
            target_update_interval=int(target_update_interval),
            policy_kwargs=policy_kwargs,
        )

        # --------------------------------------------------------------
        # Make the entropy temperature hot-swappable.
        #
        # SB3 keeps `log_ent_coef` as a bare leaf tensor on the ALGORITHM object,
        # where DualModelHotSwapManager (which zips act/rest `.parameters()`)
        # cannot see it -- the Act model would then serve with a temperature that
        # never tracks the Rest model's. Re-registering it as a real nn.Parameter
        # of this module and handing the same object back to SB3 (nn.Parameter is
        # a Tensor subclass, so SB3's arithmetic is untouched) puts it into
        # parameters()/state_dict() and therefore into the swap.
        # --------------------------------------------------------------
        if self._sb3.ent_coef_optimizer is not None:
            self.log_ent_coef = nn.Parameter(self._sb3.log_ent_coef.detach().clone())
            self._sb3.log_ent_coef = self.log_ent_coef
            self._sb3.ent_coef_optimizer = torch.optim.Adam(
                [self.log_ent_coef], lr=self._sb3.lr_schedule(1)
            )

    # ------------------------------------------------------------------
    @property
    def target_entropy(self) -> float:
        """Resolved entropy target (SB3 turns 'auto' into -dim(A) at setup time)."""
        return float(self._sb3.target_entropy)

    def sb3_optimizers(self) -> List[torch.optim.Optimizer]:
        opts = [self._sb3.actor.optimizer, self._sb3.critic.optimizer]
        if self._sb3.ent_coef_optimizer is not None:
            opts.append(self._sb3.ent_coef_optimizer)
        return opts

    def _sync_device(self, device: torch.device) -> None:
        super()._sync_device(device)
        # Fixed-temperature mode keeps a standalone tensor outside the policy.
        ent_coef_tensor = getattr(self._sb3, "ent_coef_tensor", None)
        if isinstance(ent_coef_tensor, torch.Tensor):
            self._sb3.ent_coef_tensor = ent_coef_tensor.to(device)

    # ------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        """
        Sample from the tanh-squashed Gaussian actor and decode via the wrapper.

        Exploration on the binned subchannel dimension is intrinsic here: the
        squashed Gaussian keeps mass across bin boundaries as long as the entropy
        term keeps log_std up -- which is exactly why `target_entropy` matters.
        """
        obs = self._prepare_state_tensor(state)
        was_training = self.policy.training
        self.policy.set_training_mode(False)
        with torch.no_grad():
            if deterministic:
                actions = self._sb3.actor(obs, deterministic=True)
                log_prob = None
            else:
                actions, log_prob = self._sb3.actor.action_log_prob(obs)
            q_values = torch.cat(self._sb3.critic(obs, actions), dim=1)
            min_q = torch.min(q_values, dim=1).values
        self.policy.set_training_mode(was_training)

        raw_action = actions.detach().cpu().numpy().reshape(-1).astype(np.float32)
        grant = self.decode(raw_action)
        info: Dict[str, Any] = {
            "q_value": float(min_q.detach().cpu().reshape(-1)[0]),
            "log_prob": None if log_prob is None else float(log_prob.detach().cpu().reshape(-1)[0]),
            "ent_coef": float(self._current_ent_coef().detach().cpu().reshape(-1)[0]),
            "delta_s": grant[0],
            "channel_idx": grant[1],
            "power_dbm": grant[2],
        }
        return grant, raw_action, info

    def _current_ent_coef(self) -> torch.Tensor:
        if self._sb3.ent_coef_optimizer is not None and self._sb3.log_ent_coef is not None:
            return torch.exp(self._sb3.log_ent_coef.detach()).reshape(-1)
        return self._sb3.ent_coef_tensor.detach().reshape(-1)

    # ------------------------------------------------------------------
    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """
        One SAC gradient step on a batch from `RetrospectiveReplayBuffer.sample()`.

        Mirrors `stable_baselines3.SAC.train()` (temperature step -> twin-critic
        step -> actor step -> polyak target update) with the scalar gamma replaced
        by the per-sample SMDP discount.
        """
        states, actions, rewards, next_states, dones, discounts = self.unpack_batch(batch)
        sb3 = self._sb3
        self.policy.set_training_mode(True)

        actor, critic, critic_target = sb3.actor, sb3.critic, sb3.critic_target

        # Action of the current actor for the sampled states (also reused by the
        # actor loss below, exactly as SB3 does).
        actions_pi, log_prob = actor.action_log_prob(states)
        log_prob = log_prob.reshape(-1, 1)

        ent_coef_loss_val = 0.0
        if sb3.ent_coef_optimizer is not None and sb3.log_ent_coef is not None:
            ent_coef = torch.exp(sb3.log_ent_coef.detach())
            ent_coef_loss = -(sb3.log_ent_coef * (log_prob + sb3.target_entropy).detach()).mean()
            sb3.ent_coef_optimizer.zero_grad()
            ent_coef_loss.backward()
            sb3.ent_coef_optimizer.step()
            ent_coef_loss_val = float(ent_coef_loss.item())
        else:
            ent_coef = sb3.ent_coef_tensor

        with torch.no_grad():
            next_actions, next_log_prob = actor.action_log_prob(next_states)
            next_q_values = torch.cat(critic_target(next_states, next_actions), dim=1)
            next_q_values, _ = torch.min(next_q_values, dim=1, keepdim=True)
            next_q_values = next_q_values - ent_coef * next_log_prob.reshape(-1, 1)
            target_q_values = rewards + (1.0 - dones) * discounts * next_q_values

        current_q_values = critic(states, actions)
        critic_loss = 0.5 * sum(F.mse_loss(current_q, target_q_values) for current_q in current_q_values)
        critic.optimizer.zero_grad()
        critic_loss.backward()
        critic.optimizer.step()

        q_values_pi = torch.cat(critic(states, actions_pi), dim=1)
        min_qf_pi, _ = torch.min(q_values_pi, dim=1, keepdim=True)
        actor_loss = (ent_coef * log_prob - min_qf_pi).mean()
        actor.optimizer.zero_grad()
        actor_loss.backward()
        actor.optimizer.step()

        sb3._n_updates += 1
        if sb3._n_updates % sb3.target_update_interval == 0:
            polyak_update(critic.parameters(), critic_target.parameters(), sb3.tau)
            polyak_update(sb3.batch_norm_stats, sb3.batch_norm_stats_target, 1.0)

        return {
            # 'loss' is the scalar the trainer logs; the critic loss is the one
            # that is comparable across off-policy baselines.
            "loss": float(critic_loss.item()),
            "critic_loss": float(critic_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "ent_coef_loss": ent_coef_loss_val,
            "ent_coef": float(ent_coef.detach().reshape(-1)[0].item()),
            "target_entropy": float(sb3.target_entropy),
        }
