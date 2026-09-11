# src/baselines/sb3_td3.py
# ============================================================================
# TD3 -- Twin Delayed DDPG
#        (Fujimoto, van Hoof and Meger, ICML 2018, PMLR 80:1587-1596)
#
# Basic baseline 3/3, implemented via Stable-Baselines3 (`stable_baselines3.TD3`)
# and wrapped for our hybrid grant with the SAME 3-dim Box wrapper as PPO and SAC
# (`src/baselines/sb3_wrapper.py`): dims 0,1 -> Delta (geometric) and p (linear),
# dim 2 binned to one of the num_channels subchannels.
#
# ---------------------------------------------------------------------------
# THE DETERMINISTIC-POLICY / DISCRETE-SUBCHANNEL PROBLEM (spec-mandated note).
#
# TD3's actor is deterministic. On dims 0 and 1 that is harmless -- Delta and p
# are genuinely continuous. On dim 2 it is not: the wrapper bins that coordinate,
# so the actor emits ONE hard subchannel and, unlike SAC, has no stochasticity of
# its own to ever try another. All subchannel exploration must therefore come
# from the injected action noise, and the noise on dim 2 has to be large enough
# to actually cross a bin boundary. One bin is `wrapper.channel_bin_width` wide
# in Box units (= 2 / num_channels), so a noise sigma much smaller than that
# leaves the subchannel frozen at its initial value for the whole run and the
# critic never sees an alternative channel to compare against.
#
# `channel_noise_sigma` below therefore defaults to exactly one bin width --
# derived from num_channels, never hardcoded -- and is separated from the
# continuous-dimension sigma so both can be searched independently by Optuna.
#
# This is also the honest reason a purely-continuous method is expected to
# underperform the hybrid-action baselines on the discrete subchannel decision,
# and per librarian/baselines_v2.json it must be flagged as such in the paper:
# the exploration on that dimension is an externally injected hack, not part of
# the algorithm, and the deterministic policy gradient carries no information
# about the discrete structure of the bins.
#
# As with SAC, the update mirrors `stable_baselines3.TD3.train()` with the scalar
# gamma replaced by the per-transition SMDP discount gamma**delta_t supplied by
# `RetrospectiveReplayBuffer` -- the same substitution SB3 2.7 itself makes for
# n-step replay.
# ============================================================================

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn.functional as F
from stable_baselines3 import TD3 as SB3TD3
from stable_baselines3.common.utils import polyak_update

from src.baselines.sb3_wrapper import DIM_CHANNEL, SB3_ACTION_DIM, BOX_HIGH, BOX_LOW, SB3BaselineModel
from src.rl_interface import STATE_DIM


class TD3(SB3BaselineModel):
    """TD3 baseline backed by `stable_baselines3.TD3`'s TD3Policy."""

    SB3_ALGO = SB3TD3

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        num_channels: int = 4,
        learning_rate: float = 1e-3,
        gamma: float = 0.99,
        tau: float = 0.005,
        policy_delay: int = 2,
        target_policy_noise: float = 0.2,
        target_noise_clip: float = 0.5,
        exploration_noise: float = 0.1,
        channel_noise_sigma: Optional[float] = None,
        policy: str = "MlpPolicy",
        policy_kwargs: Optional[Dict[str, Any]] = None,
        hidden_dim: Optional[int] = None,
        device: Union[str, torch.device] = "auto",
        seed: Optional[int] = None,
        **hparams: Any,
    ) -> None:
        super().__init__(state_dim=state_dim, num_channels=num_channels, **hparams)
        self.gamma = float(gamma)
        #: Requested hidden width; None means "keep SB3's own default net_arch".
        self.hidden_dim = None if hidden_dim is None else int(hidden_dim)

        # buffer_size=1: SB3 allocates its own ReplayBuffer at construction, which we
        # never use -- transitions arrive from RetrospectiveReplayBuffer via update().
        self._build_sb3(
            SB3TD3,
            policy=policy,
            device=device,
            seed=seed,
            learning_rate=learning_rate,
            buffer_size=1,
            gamma=self.gamma,
            tau=tau,
            policy_delay=int(policy_delay),
            target_policy_noise=float(target_policy_noise),
            target_noise_clip=float(target_noise_clip),
            policy_kwargs=self.apply_hidden_dim(policy_kwargs, hidden_dim),
        )

        # Exploration noise, per Box dimension. dim 2 gets its own (much larger)
        # sigma because it has to cross a subchannel bin boundary to change the
        # action at all; see the module header.
        self.exploration_noise = float(exploration_noise)
        self.channel_noise_sigma = (
            float(self.wrapper.channel_bin_width)
            if channel_noise_sigma is None
            else float(channel_noise_sigma)
        )
        self._noise_sigma = np.full(SB3_ACTION_DIM, self.exploration_noise, dtype=np.float32)
        self._noise_sigma[DIM_CHANNEL] = self.channel_noise_sigma

    # ------------------------------------------------------------------
    @property
    def noise_sigma(self) -> np.ndarray:
        """Per-dimension exploration noise standard deviation, in Box units."""
        return self._noise_sigma.copy()

    def sb3_optimizers(self) -> List[torch.optim.Optimizer]:
        return [self._sb3.actor.optimizer, self._sb3.critic.optimizer]

    # ------------------------------------------------------------------
    def select_action(
        self,
        state: Union[np.ndarray, torch.Tensor],
        deterministic: bool = False,
    ) -> Tuple[Tuple[float, int, float], np.ndarray, Dict[str, Any]]:
        """
        Deterministic actor output plus (optionally) Gaussian exploration noise.

        The Box is symmetric-unit, so the actor's tanh output needs no rescaling;
        the noisy action is clipped back into the box before decoding, matching
        what SB3's `NormalActionNoise` + `clip` does inside `predict()`.
        """
        obs = self._prepare_state_tensor(state)
        was_training = self.policy.training
        self.policy.set_training_mode(False)
        with torch.no_grad():
            mean_action = self._sb3.actor(obs)
            q_value = self._sb3.critic.q1_forward(obs, mean_action)
        self.policy.set_training_mode(was_training)

        raw_action = mean_action.detach().cpu().numpy().reshape(-1).astype(np.float32)
        noise = np.zeros_like(raw_action)
        if not deterministic:
            noise = np.random.normal(0.0, self._noise_sigma).astype(np.float32)
            raw_action = np.clip(raw_action + noise, BOX_LOW, BOX_HIGH).astype(np.float32)

        grant = self.decode(raw_action)
        info: Dict[str, Any] = {
            "q_value": float(q_value.detach().cpu().reshape(-1)[0]),
            "noise": noise.tolist(),
            "channel_noise_sigma": self.channel_noise_sigma,
            "channel_bin_width": float(self.wrapper.channel_bin_width),
            "delta_s": grant[0],
            "channel_idx": grant[1],
            "power_dbm": grant[2],
        }
        return grant, raw_action, info

    # ------------------------------------------------------------------
    def update(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """
        One TD3 gradient step on a batch from `RetrospectiveReplayBuffer.sample()`.

        Mirrors `stable_baselines3.TD3.train()`: target-policy smoothing, clipped
        double-Q target, twin-critic regression, and a delayed actor + polyak
        update every `policy_delay` steps -- with the per-sample SMDP discount in
        place of the scalar gamma.
        """
        states, actions, rewards, next_states, dones, discounts = self.unpack_batch(batch)
        sb3 = self._sb3
        self.policy.set_training_mode(True)

        actor, actor_target = sb3.actor, sb3.actor_target
        critic, critic_target = sb3.critic, sb3.critic_target

        sb3._n_updates += 1

        with torch.no_grad():
            # Target policy smoothing (Fujimoto et al., Sec. 5.3).
            noise = actions.clone().data.normal_(0.0, sb3.target_policy_noise)
            noise = noise.clamp(-sb3.target_noise_clip, sb3.target_noise_clip)
            next_actions = (actor_target(next_states) + noise).clamp(BOX_LOW, BOX_HIGH)

            next_q_values = torch.cat(critic_target(next_states, next_actions), dim=1)
            next_q_values, _ = torch.min(next_q_values, dim=1, keepdim=True)
            target_q_values = rewards + (1.0 - dones) * discounts * next_q_values

        current_q_values = critic(states, actions)
        critic_loss = sum(F.mse_loss(current_q, target_q_values) for current_q in current_q_values)
        critic.optimizer.zero_grad()
        critic_loss.backward()
        critic.optimizer.step()

        actor_loss_val = float("nan")
        if sb3._n_updates % sb3.policy_delay == 0:
            actor_loss = -critic.q1_forward(states, actor(states)).mean()
            actor.optimizer.zero_grad()
            actor_loss.backward()
            actor.optimizer.step()
            actor_loss_val = float(actor_loss.item())

            polyak_update(critic.parameters(), critic_target.parameters(), sb3.tau)
            polyak_update(actor.parameters(), actor_target.parameters(), sb3.tau)
            polyak_update(sb3.critic_batch_norm_stats, sb3.critic_batch_norm_stats_target, 1.0)
            polyak_update(sb3.actor_batch_norm_stats, sb3.actor_batch_norm_stats_target, 1.0)

        return {
            # The critic loss is the every-step scalar; the actor only fires every
            # `policy_delay` steps, so reporting it as 'loss' would be intermittent.
            "loss": float(critic_loss.item()),
            "critic_loss": float(critic_loss.item()),
            # NaN on the steps where the delayed actor update is skipped. Only
            # "loss" (the critic loss) is aggregated by the trainer; this key is a
            # diagnostic, and `actor_updated` says whether it is meaningful.
            "actor_loss": actor_loss_val,
            "actor_updated": float(sb3._n_updates % sb3.policy_delay == 0),
            "n_updates": float(sb3._n_updates),
        }
