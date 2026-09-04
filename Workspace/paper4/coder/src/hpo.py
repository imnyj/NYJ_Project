# src/hpo.py
# ============================================================================
# Hyperparameter Optimization (Optuna HPO) Pipeline for AoI-aware V2I Uplink
#
# Implements Milestone 3 (R3):
# 1. Tailored Optuna search spaces for all 9 baseline algorithms:
#    - Category 1 (Basic 3종): HybridPPO, HybridSAC, HybridTD3
#    - Category 2 (Latest 3종): MAPPO, HyARPPO, MPDQN
#    - Category 3 (SOTA AoI 3종): PureAoI, DuelingQAoI, SACAoI
# 2. Composite objective function balancing:
#    - Position tracking / estimation error integral: mean_error
#    - Average Age of Information: mean_aoi
#    - Uplink outage / packet loss rate: outage_rate
#    - Transmission power consumption: avg_power_norm
# 3. Multi-seed evaluation in the genuine SUMO AoiV2IEnv with Rayleigh-fading SINR contention.
# 4. CSV export of optimal parameters (`optuna_best_params.csv`) and per-model
#    trial history (`optuna_trials_<model_name>.csv`).
# ============================================================================

from __future__ import annotations
import argparse
import gc
import json
import logging
import math
import os
import random
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

import numpy as np
import optuna
import pandas as pd
import src.Communications as comm
from src.baselines import ALL_BASELINES, BASELINE_CATEGORIES, get_baseline
# `normalize_power_dbm` is the single definition of the power term shared by the
# HPO objective and the benchmark leaderboard. They used to normalise over two
# different dBm windows, so HPO optimised one objective and the leaderboard
# ranked by another.
from src.evaluate import (
    LEGACY_OUTAGE_METRIC_KEY,
    OUTAGE_METRIC_KEY,
    normalize_power_dbm,
)
# The divergence rule is imported, never restated. If HPO judged divergence by
# its own threshold, a combination HPO passed could still be aborted by the
# trainer on the same loss trace (or worse, the reverse), and the search would be
# selecting hyperparameters the training loop refuses to run.
from src.divergence_guard import (
    ABORT_DIVERGED,
    DEFAULT_LOSS_ABS_FLOOR as DG_LOSS_ABS_FLOOR,
    DEFAULT_LOSS_PATIENCE as DG_LOSS_PATIENCE,
    DEFAULT_LOSS_RATIO as DG_LOSS_RATIO,
    DEFAULT_MAX_NONFINITE_LOSS_UPDATES,
    DEFAULT_MAX_ZERO_UPDATE_EPISODES as DG_MAX_ZERO_UPDATE_EPISODES,
    DEFAULT_WARMUP_EPISODES as DG_WARMUP_EPISODES,
    AbortVerdict,
    DivergenceMonitor,
    is_finite_number,
)
from src.hot_swap_trainer import (
    DEFAULT_REWARD_WEIGHTS,
    DEFAULT_WARMUP_STEPS,
    REWARD_WEIGHT_KEYS,
    AoiV2IEnv,
    BackgroundTrainer,
)
from src.rl_interface import P_MAX, P_MIN, STATE_DIM, RetrospectiveReplayBuffer
import src.sumo.make_sumo_set as ss

# Communication range of the RSU, sourced from the SUMO scenario generator so HPO
# never drifts from the network that is actually built (300 m urban 5.9 GHz value).
DEFAULT_RSU_RANGE: float = float(getattr(ss, "RSU_RANGE", 300.0))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HPO")

# The nine baselines, taken from src/baselines/__init__.py rather than restated.
# This list used to be a literal copy and went stale when the baselines were
# replaced on 2026-08-28: HPO could not construct a single real model afterwards.
CANONICAL_MODEL_NAMES = list(ALL_BASELINES)

_CATEGORY_LABELS = {
    "basic": "Category 1 (Basic)",
    "latest": "Category 2 (Latest)",
    "similar": "Category 3 (Similar)",
}
MODEL_CATEGORIES = {
    n: _CATEGORY_LABELS.get(g, g)
    for g, names in BASELINE_CATEGORIES.items()
    for n in names
}


_CANONICAL_BY_CLEAN = {
    n.replace("-", "").replace("_", "").lower(): n for n in ALL_BASELINES
}


def normalize_model_name(name: Any) -> str:
    """Resolve an alias, or a model class, to its canonical registry name."""
    if not isinstance(name, str):
        return getattr(name, "__name__", None) or type(name).__name__
    clean = name.replace("-", "").replace("_", "").lower()
    return _CANONICAL_BY_CLEAN.get(clean, name)


# ----------------------------------------------------------------------------
# Reward-weight search space (Conversation.md section 3, line 31)
#
#   R_t = -( w1*Norm(e_t^2) + w2*Norm(P_tx) + w3*Norm(C_freq) + w4*I_redundant )
#
# The design mandates that w1..w4 are NOT fixed heuristically but are part of the
# Optuna search space so the agent finds its own reward balance. Every term is
# already Min-Max normalised to [0, 1] by the environment, so only the RELATIVE
# balance is meaningful; the sampled raw weights are therefore normalised to sum
# to 1.0 before being handed to the environment. That keeps the reward magnitude
# comparable across trials (so lr / entropy_coef stay on a comparable scale) and
# removes any degenerate incentive to shrink all four weights at once.
# The design defaults 0.5 / 0.2 / 0.2 / 0.1 lie inside these ranges.
# ----------------------------------------------------------------------------
# REWARD_WEIGHT_KEYS is owned by `src/hot_swap_trainer.py` and imported above so
# that the search space, the training env and the evaluation env cannot drift.

# Tuning seeds, disjoint from the training seeds (42..141, i.e. base 42 plus the
# episode index) and from the evaluation seeds (5001..5005 in `src/evaluate.py`).
# Selecting hyperparameters on a traffic realisation the models are later scored
# on is the ordinary form of leakage in this pipeline, and it was present until
# 2026-09-01: HPO, training and evaluation all shared seed 42.
HPO_TUNING_SEEDS: Tuple[int, ...] = (1001, 1002, 1003)

REWARD_WEIGHT_RANGES: Dict[str, Tuple[float, float]] = {
    "w1": (0.10, 1.00),   # estimation-error penalty  Norm(e_t^2)
    "w2": (0.02, 0.60),   # transmit-power penalty    Norm(P_tx)
    "w3": (0.02, 0.60),   # channel-congestion penalty Norm(C_freq)
    "w4": (0.02, 0.60),   # redundant-update penalty  I_redundant
}


def sample_reward_weights(trial: optuna.Trial) -> Dict[str, float]:
    """Samples the four reward weights w1..w4 and normalises them to sum to 1.0.

    The raw samples are registered as Optuna parameters `w1_raw`..`w4_raw`; the
    normalised values that the environment actually trains under are recorded as
    trial user attributes `w1`..`w4` so they are exported to CSV.
    """
    raw: Dict[str, float] = {}
    for key in REWARD_WEIGHT_KEYS:
        lo, hi = REWARD_WEIGHT_RANGES[key]
        raw[key] = trial.suggest_float(f"{key}_raw", lo, hi, log=True)

    total = sum(raw.values())
    if total <= 0.0:
        total = 1.0
    weights = {k: round(float(v / total), 6) for k, v in raw.items()}

    for k, v in weights.items():
        trial.set_user_attr(k, v)
    return weights


def sample_hparams(trial: optuna.Trial, model_name: str) -> Dict[str, Any]:
    """Per-model search space, keyed to each constructor's REAL parameter names.

    Every key below is a named argument of that model's `__init__`. This matters
    more than it looks: all nine constructors end with `**hparams`, so a key that
    does not match a real parameter is silently absorbed and the trial runs with
    library defaults. The previous version of this function was keyed on the
    discarded baseline names (HybridPPO, MAPPO, ...), so no branch ever matched
    the current models -- Optuna would report an "optimal" learning rate while
    the model trained at 3e-4 throughout. `assert_hparams_reach_model` below is
    the regression guard; `tests/test_hpo.py` runs it for all nine.
    """
    canonical_name = normalize_model_name(model_name)
    params: Dict[str, Any] = {}

    # --- Basic three: Stable-Baselines3, so SB3's own argument names ---------
    if canonical_name == "PPO":
        params = {
            # `hidden_dim` maps to SB3's policy_kwargs["net_arch"] via
            # SB3BaselineModel.apply_hidden_dim. Without it the three SB3 models
            # keep their per-algorithm default widths ([64,64] PPO, [256,256]
            # SAC, [400,300] TD3), a 71x parameter-count spread across the nine
            # baselines that makes "lost because on-policy" indistinguishable
            # from "lost because it had 10.9k parameters against 773k".
            # See results/diagnostics/baseline_capacity_parity.csv.
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "clip_range": trial.suggest_float("clip_range", 0.1, 0.3),
            "ent_coef": trial.suggest_float("ent_coef", 1e-4, 0.05, log=True),
            "vf_coef": trial.suggest_float("vf_coef", 0.2, 0.8),
            "n_epochs": trial.suggest_categorical("n_epochs", [4, 10, 20]),
        }
    elif canonical_name == "SAC":
        params = {
            # `hidden_dim` maps to SB3's policy_kwargs["net_arch"] via
            # SB3BaselineModel.apply_hidden_dim. Without it the three SB3 models
            # keep their per-algorithm default widths ([64,64] PPO, [256,256]
            # SAC, [400,300] TD3), a 71x parameter-count spread across the nine
            # baselines that makes "lost because on-policy" indistinguishable
            # from "lost because it had 10.9k parameters against 773k".
            # See results/diagnostics/baseline_capacity_parity.csv.
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "tau": trial.suggest_float("tau", 0.001, 0.02, log=True),
            "target_update_interval": trial.suggest_categorical("target_update_interval", [1, 2, 4]),
        }
    elif canonical_name == "TD3":
        params = {
            # `hidden_dim` maps to SB3's policy_kwargs["net_arch"] via
            # SB3BaselineModel.apply_hidden_dim. Without it the three SB3 models
            # keep their per-algorithm default widths ([64,64] PPO, [256,256]
            # SAC, [400,300] TD3), a 71x parameter-count spread across the nine
            # baselines that makes "lost because on-policy" indistinguishable
            # from "lost because it had 10.9k parameters against 773k".
            # See results/diagnostics/baseline_capacity_parity.csv.
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "tau": trial.suggest_float("tau", 0.001, 0.02, log=True),
            "policy_delay": trial.suggest_categorical("policy_delay", [2, 3, 4]),
            "target_policy_noise": trial.suggest_float("target_policy_noise", 0.1, 0.3),
            "target_noise_clip": trial.suggest_float("target_noise_clip", 0.2, 0.5),
        }

    # --- Latest three -------------------------------------------------------
    elif canonical_name == "RES-MAPDDPG":
        params = {
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "lr_actor": trial.suggest_float("lr_actor", 1e-4, 3e-3, log=True),
            "lr_critic": trial.suggest_float("lr_critic", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "tau": trial.suggest_float("tau", 0.001, 0.02, log=True),
            "num_res_blocks": trial.suggest_categorical("num_res_blocks", [1, 2, 3]),
            "epsilon_decay": trial.suggest_float("epsilon_decay", 0.990, 0.9995),
        }
    elif canonical_name == "MA2HDQN":
        params = {
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "lr_q": trial.suggest_float("lr_q", 1e-4, 3e-3, log=True),
            "lr_actor": trial.suggest_float("lr_actor", 1e-4, 3e-3, log=True),
            "lr_critic": trial.suggest_float("lr_critic", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "tau": trial.suggest_float("tau", 0.001, 0.02, log=True),
            # `n_step` is deliberately NOT searched. The retrospective SMDP buffer
            # samples uniformly and cannot assemble an n-step return, so the model
            # reports `n_step_active=False` and the value would be searched with
            # no effect on learning.
            "epsilon_decay": trial.suggest_float("epsilon_decay", 0.990, 0.9995),
        }
    elif canonical_name == "I-HAMAPPO":
        params = {
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "lr_actor": trial.suggest_float("lr_actor", 1e-4, 3e-3, log=True),
            "lr_critic": trial.suggest_float("lr_critic", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "clip_ratio": trial.suggest_float("clip_ratio", 0.1, 0.3),
            "entropy_coef": trial.suggest_float("entropy_coef", 1e-4, 0.05, log=True),
            "value_coef": trial.suggest_float("value_coef", 0.2, 0.8),
        }

    # --- Similar three ------------------------------------------------------
    elif canonical_name == "SPAM-D3QN":
        params = {
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "target_update_freq": trial.suggest_categorical("target_update_freq", [200, 500, 1000]),
            "epsilon_decay": trial.suggest_float("epsilon_decay", 0.990, 0.9995),
            "per_alpha": trial.suggest_float("per_alpha", 0.4, 0.8),
        }
    elif canonical_name == "CARLTON":
        params = {
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            # Mellowmax temperature. omega -> 0 makes the backup the mean over
            # actions, omega -> inf makes it the max; CARLTON's own default is
            # 10.0, i.e. firmly on the max-like side. The previous range [0.1,
            # 0.9] could not reach it -- the search was confined to the mean-like
            # regime and could never reproduce the configuration the baseline was
            # published with, which is the "crippled baseline" failure a
            # comparison paper cannot afford. Log scale because omega is a
            # temperature and its effect is multiplicative.
            "omega": trial.suggest_float("omega", 0.1, 20.0, log=True),
            # `tau` is deliberately NOT searched. CARLTON is the DeepMellow-style
            # learner that removes the target network (`use_target_network=False`
            # by default), and tau only moves a target network. Searching it would
            # tune a no-op; searching `use_target_network` instead would let HPO
            # reintroduce the exact component the published method removes, i.e.
            # it would stop being this baseline.
        }
    elif canonical_name == "MADDPG-MT":
        params = {
            "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
            "actor_lr": trial.suggest_float("actor_lr", 1e-4, 3e-3, log=True),
            "critic_lr": trial.suggest_float("critic_lr", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "tau": trial.suggest_float("tau", 0.001, 0.02, log=True),
            "global_critic_weight": trial.suggest_float("global_critic_weight", 0.1, 0.9),
            "gumbel_tau": trial.suggest_float("gumbel_tau", 0.5, 2.0),
        }
    else:
        params = {
            "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
            "hidden_dim": trial.suggest_categorical("hidden_dim", [32, 64, 128]),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
        }

    return params


def assert_hparams_reach_model(model_name: str) -> List[str]:
    """Names this model's search space samples that its constructor cannot accept.

    An empty list means every sampled key is a real named argument. A non-empty
    one means those keys would vanish into `**hparams` and the trial would report
    a tuning result it never actually applied.
    """
    import inspect

    canonical_name = normalize_model_name(model_name)
    sampled = set(_search_space_keys(canonical_name))
    accepted = set(inspect.signature(get_baseline(canonical_name).__init__).parameters)
    return sorted(sampled - accepted)


def _search_space_keys(canonical_name: str) -> List[str]:
    """The keys `sample_hparams` would sample, without needing a live trial."""
    class _KeyRecorder:
        def __init__(self) -> None:
            self.keys: List[str] = []

        def suggest_float(self, name, *a, **k):
            self.keys.append(name)
            return 0.0

        def suggest_categorical(self, name, choices, *a, **k):
            self.keys.append(name)
            return choices[0]

        def suggest_int(self, name, *a, **k):
            self.keys.append(name)
            return 0

    rec = _KeyRecorder()
    sample_hparams(rec, canonical_name)  # type: ignore[arg-type]
    return rec.keys


#: Score handed to a trial that measured nothing, or whose loss diverged. It has
#: to be far above any attainable real score because the study minimises and an
#: unmeasured run scores 0.0 on every term.
#:
#: The range of real scores, read out of the nine committed
#: `results/hpo/optuna_trials_*.csv` (135 trials, of which 130 produced a score
#: below the penalty): 0.925 (MADDPG-MT) to 35.815 (PPO). An earlier version of
#: this comment claimed 0.887..1.459, which was the scale of a superseded
#: objective and is 24x too small. The difference matters: at the real scale a
#: per-seed penalty on one seed of three averages to 33.3, which does NOT beat
#: PPO's worst healthy trial at 35.815, so a single penalised seed is not on its
#: own enough to put a trial out of contention. That is why
#: `evaluate_trial_multiseed` applies the penalty at the trial level as well.
FAILED_RUN_PENALTY: float = 100.0


# ----------------------------------------------------------------------------
# Divergence detection inside an HPO rollout
#
# Why this is here at all. On 2026-09-02 four 200,000-step training runs were
# lost to on-policy divergence, and every one of the four learning rates that
# caused it had been SELECTED BY THIS FILE (PPO learning_rate 1.08e-3,
# I-HAMAPPO lr_actor 8.43e-4, against the 3e-4 that is customary for both). HPO
# could not have known: it scored `mean_error / mean_aoi / outage / power`, and a
# policy whose loss has run away still produces perfectly ordinary values for all
# four -- it just stops improving. Nothing in the objective reads the loss.
#
# The unit that matters. The four failures are usually quoted in environment
# steps (8,000 / 22,000 / 32,000 / 34,000), which makes a 350-step rollout look
# hopelessly short. That comparison is wrong, because training and HPO run
# gradient updates at completely different rates:
#
#     training   `updates_per_env_step` uncapped, wall-clock bound; measured
#                23..800 updates per 2,000-step episode, i.e. ~0.01..0.4 per step
#     HPO        `train_steps_during_rollout=2`, i.e. ~2 per step
#
# Counted in gradient updates -- which is what actually moves the weights -- the
# four divergences happened at 631, 1,445, 1,697 and 6,798 cumulative updates
# (measured from `runs/*/lg/{PPO,IHAMAPPO}_progress.csv`, column
# `grad_updates_this_episode`, cumulated up to the first episode whose
# `mean_loss` exceeded the guard floor). At ~2 updates per environment step an
# HPO rollout reaches that range far sooner than the env-step figures suggest.
# `DEFAULT_HPO_N_STEPS` below is set from that arithmetic and then confirmed by
# actually running the two offending configurations; see
# `results/hpo/divergence_detection_check.csv`.
# ----------------------------------------------------------------------------

#: Environment steps in one HPO "pseudo-episode" -- the granularity at which
#: `DivergenceMonitor` is fed, because the monitor is episode-granular and an HPO
#: rollout is a single continuous episode. At ~2 updates per environment step
#: this is ~400 gradient updates per pseudo-episode, more evidence than the
#: 23..800 updates a real 2,000-step training episode contained, so a
#: pseudo-episode is not a weaker sample than the thing it stands in for.
HPO_CHECK_INTERVAL_STEPS: int = 200

#: Length of the loss window averaged into the value handed to the monitor.
#: `BackgroundTrainer.get_metrics` averages `loss_history[-50:]`, so using the
#: same 50 makes the HPO `mean_loss` the same statistic as the training one.
HPO_LOSS_WINDOW: int = 50

#: Environment steps per seed for HPO. See the block comment above for how it was
#: chosen and `results/hpo/divergence_detection_check.csv` for the measurement
#: that confirms both known-diverging configurations are caught within it.
DEFAULT_HPO_N_STEPS: int = 4000


class RolloutLossTracker:
    """Loss bookkeeping for one HPO rollout, mirroring `BackgroundTrainer`.

    Two quantities, both of which the trainer already maintains and neither of
    which HPO used to look at:

      * `mean_recent_loss` -- mean of the `loss` key over the last
        `HPO_LOSS_WINDOW` updates, the exact statistic `DivergenceMonitor` is
        fed at the end of every training episode;
      * a consecutive non-finite-update counter, which is how the trainer catches
        a NaN at the update that produced it rather than at the end of an
        episode. An HPO rollout is one episode long, so without this counter a
        model that went NaN on its second update would not be judged until the
        next pseudo-episode boundary.

    Finiteness is decided by `BackgroundTrainer._loss_dict_is_finite` rather than
    by a second copy of the same predicate, for the same reason the thresholds
    are imported: two definitions drift.
    """

    def __init__(
        self,
        window: int = HPO_LOSS_WINDOW,
        max_nonfinite_updates: int = DEFAULT_MAX_NONFINITE_LOSS_UPDATES,
    ) -> None:
        self.window = max(1, int(window))
        self.max_nonfinite_updates = max(1, int(max_nonfinite_updates))
        self.losses: Deque[float] = deque(maxlen=self.window)
        self.n_updates = 0
        self.consecutive_nonfinite = 0
        self.max_seen_nonfinite = 0

    def observe_update(self, loss_dict: Any) -> None:
        """Record one gradient update's reported scalars."""
        self.n_updates += 1
        if isinstance(loss_dict, dict) and "loss" in loss_dict:
            try:
                self.losses.append(float(loss_dict["loss"]))
            except (TypeError, ValueError):
                pass
        if BackgroundTrainer._loss_dict_is_finite(loss_dict):
            self.consecutive_nonfinite = 0
        else:
            self.consecutive_nonfinite += 1
            self.max_seen_nonfinite = max(self.max_seen_nonfinite, self.consecutive_nonfinite)

    @property
    def mean_recent_loss(self) -> float:
        """Same aggregation as `BackgroundTrainer.get_metrics()['mean_recent_loss']`."""
        if not self.losses:
            return 0.0
        return round(float(np.mean(list(self.losses))), 4)

    def nonfinite_verdict(self, episode: int) -> Optional[AbortVerdict]:
        """A verdict once enough consecutive updates have reported NaN/Inf."""
        if self.consecutive_nonfinite < self.max_nonfinite_updates:
            return None
        return AbortVerdict(
            kind=ABORT_DIVERGED,
            episode=int(episode),
            reason=(
                f"{self.consecutive_nonfinite} consecutive gradient updates produced a "
                "non-finite loss during the HPO rollout; the weights are already poisoned"
            ),
            detail={
                "consecutive_nonfinite_losses": self.consecutive_nonfinite,
                "n_updates": self.n_updates,
                "rule": "non_finite_update_streak",
            },
        )


def make_divergence_monitor() -> DivergenceMonitor:
    """A monitor configured exactly as `run_hot_swap_training` configures its own.

    Written as a function so there is one place to look when asking whether HPO
    and training judge divergence identically.
    """
    return DivergenceMonitor(
        warmup_episodes=DG_WARMUP_EPISODES,
        loss_ratio=DG_LOSS_RATIO,
        loss_abs_floor=DG_LOSS_ABS_FLOOR,
        loss_patience=DG_LOSS_PATIENCE,
        max_zero_update_episodes=DG_MAX_ZERO_UPDATE_EPISODES,
    )


def run_diverged(metrics: Dict[str, Any]) -> bool:
    """True when this rollout's loss ran away, so its metrics are not a policy.

    Kept separate from `run_is_empty`: an empty run measured nothing, whereas a
    diverged run measured a great deal about a model that has stopped learning.
    Both are scored `FAILED_RUN_PENALTY`, for different reasons that the trial
    CSV keeps distinct.
    """
    return bool(metrics.get("diverged"))


def run_is_empty(metrics: Dict[str, Any]) -> bool:
    """True when this rollout observed nothing, so its metrics mean nothing.

    `AoiV2IEnv.get_metrics` degrades gracefully when no vehicle was ever in
    range: mean_aoi 0.0, mean_error 0.0, packet_loss 0/max(1,0) = 0.0 and the
    power falling back to the decoder floor, which normalises to 0.0. Fed to the
    composite that is a score of exactly 0.0 -- the global minimum of a
    minimisation study. Any hyperparameter combination that happens to kill the
    environment would therefore be selected as "optimal". `n_observations` and
    `tx_attempts` are the two signals that say the run was empty; both are
    already produced by `get_metrics` and were simply never read here.

    Keys that are absent are not treated as zero: callers that score a
    pre-aggregated metric dict are not claiming anything about emptiness.
    """
    if metrics.get("run_failed"):
        return True
    for key in ("n_observations", "tx_attempts"):
        val = metrics.get(key, None)
        if val is not None and float(val) <= 0.0:
            return True
    return False


def compute_composite_objective(
    metrics: Dict[str, float],
    w_error: float = 1.0,
    w_aoi: float = 0.5,
    w_outage: float = 2.0,
    w_power: float = 0.2,
) -> float:
    """
    Formulates the composite objective function balancing:
    1. Tracking estimation error (m)
    2. Age of Information (s)
    3. Outage rate (packet loss ratio in [0, 1])
    4. Normalized transmission power (in [0, 1] mapped from [P_MIN, P_MAX] dBm)

    A run that measured nothing is scored `FAILED_RUN_PENALTY`, never 0.0. So is
    a run whose loss diverged: the four metrics above stay entirely plausible
    while the policy behind them has stopped learning, which is precisely how the
    learning rates that destroyed the 2026-09-02 training runs were selected as
    optimal here.
    """
    if run_is_empty(metrics) or run_diverged(metrics):
        return float(FAILED_RUN_PENALTY)

    mean_err = metrics.get("mean_error", 0.0)
    mean_aoi = metrics.get("mean_aoi", 0.0)
    outage_rate = metrics.get("outage_rate", metrics.get("packet_loss_rate", 0.0))
    power_norm = metrics.get("avg_power_norm", 0.5)

    objective_val = (
        w_error * mean_err
        + w_aoi * mean_aoi
        + w_outage * outage_rate
        + w_power * power_norm
    )
    return float(objective_val)


def _decision_record(s_vec: Any, info: Any, raw_action: Any) -> Dict[str, Any]:
    """One open SMDP decision, with everything the buffer needs when it closes.

    `info` is the third element of `select_action`, and this rollout used to
    discard it entirely. Two things travel in it, both known exactly at the
    moment of the decision and both unrecoverable once the policy has taken
    another gradient step:

      * `info["log_prob"]`, the behaviour log-probability the two PPO-family
        baselines need as the denominator of their importance ratio. Without it
        the ratio is identically 1 and the clipping is inert, which is what made
        both models diverge (`results/hpo/onpolicy_fix_check.csv`).
      * `info["action_idx"]`, the combined discrete index the five discrete-head
        baselines actually selected. Without it they fall back to re-deriving the
        index from the decoded continuous action.

    Both are what `hot_swap_trainer` already forwards on the training path. They
    are forwarded here for the same reason the tuned reward weights had to be:
    a search that measures a model under different conditions than training runs
    it does not tell us that its chosen hyper-parameters transfer.
    """
    logp: Optional[float] = None
    if isinstance(info, dict) and info.get("log_prob") is not None:
        try:
            value = float(info["log_prob"])
        except (TypeError, ValueError):
            value = float("nan")
        if math.isfinite(value):
            logp = value

    action_idx: Optional[int] = None
    if isinstance(info, dict) and info.get("action_idx") is not None:
        try:
            action_idx = int(info["action_idx"])
        except (TypeError, ValueError):
            action_idx = None

    return {
        "state": np.asarray(s_vec, dtype=np.float32),
        "raw_action": raw_action,
        "behaviour_log_prob": logp,
        "action_idx": action_idx,
    }


def evaluate_model_in_env(
    model: Any,
    seed: int = 42,
    n_steps: int = 35,
    density: float = 25.0,
    rsu_range: float = DEFAULT_RSU_RANGE,
    train_steps_during_rollout: int = 0,
    reward_weights: Optional[Dict[str, float]] = None,
    check_divergence: bool = True,
    divergence_check_interval: int = HPO_CHECK_INTERVAL_STEPS,
) -> Dict[str, float]:
    """
    Evaluates a baseline model in the genuine SUMO AoiV2IEnv for a specific seed.
    Runs real vehicle kinematics, TraCI TLS phase transitions, hybrid action scheduling,
    Rayleigh-SINR co-channel contention, retrospective position estimation error, and AoI.

    `reward_weights` are the sampled w1..w4 of the design reward; when given they are
    passed to the environment constructor so the trial actually trains under them.

    The vehicle population is set by `density`; the `n_vehicles` and `rsu_pos`
    arguments this function used to accept were never read, and the tests that
    passed them believed they were controlling something they were not.

    With `check_divergence` on (the default) the losses reported by
    `model.update()` are watched by the same `DivergenceMonitor` the training loop
    uses. The monitor is episode-granular and an HPO rollout is one continuous
    episode, so the rollout is divided into pseudo-episodes of
    `divergence_check_interval` steps and the monitor is fed at each boundary,
    exactly as `run_hot_swap_training` feeds it at each episode boundary. The
    first pseudo-episode boundary is only counted once a gradient update has
    actually happened: the replay buffer needs 16 closed SMDP intervals before
    the first update, and treating those opening steps as zero-update episodes
    would trip the stall rule on every healthy rollout.

    A rollout that is condemned stops immediately -- there is nothing left to
    measure, and stopping is what keeps a longer rollout affordable, since the
    trials that cost the most time are exactly the ones that have already failed.
    """
    effective_weights = reward_weights if reward_weights else DEFAULT_REWARD_WEIGHTS
    env_kwargs: Dict[str, Any] = {
        key: float(effective_weights[key])
        for key in REWARD_WEIGHT_KEYS
        if key in effective_weights
    }

    env = AoiV2IEnv(
        density=density,
        seed=seed,
        max_steps=n_steps,
        rsu_range=rsu_range,
        warmup_steps=DEFAULT_WARMUP_STEPS,
        **env_kwargs,
    )
    obs, info = env.reset()
    # The uplink success draw uses the process-wide `random` stream, and SUMO
    # scenario generation consumes a variable number of draws from it before we
    # get here. Re-seeding after reset() pins the simulation stream to
    # (density, seed) whatever ran before.
    random.seed(seed)
    buffer = RetrospectiveReplayBuffer(capacity=1000) if train_steps_during_rollout > 0 else None
    n_update_failures = 0

    # Divergence bookkeeping. Only meaningful when this rollout trains at all;
    # a pure-inference rollout has no loss to watch.
    watch_divergence = bool(check_divergence) and buffer is not None
    loss_tracker = RolloutLossTracker()
    monitor = make_divergence_monitor()
    check_interval = max(1, int(divergence_check_interval))
    verdict: Optional[AbortVerdict] = None
    pseudo_episode = 0
    updates_this_pseudo_episode = 0
    steps_since_first_update = 0
    steps_completed = 0

    # Event-driven SMDP rollout, matching run_hot_swap_training. Granting every
    # vehicle on every step -- what this loop used to do -- makes Delta inert, so
    # every trial would have measured the same fixed transmit schedule and Optuna
    # would have optimised hyperparameters against a constant.
    open_decision: Dict[str, Dict[str, Any]] = {}
    action_dict: Dict[str, Any] = {}
    for vid, s_vec in obs.items():
        grant, raw_action, info = model.select_action(s_vec, deterministic=False)
        open_decision[vid] = _decision_record(s_vec, info, raw_action)
        action_dict[vid] = grant

    # The rollout runs under a try/except because divergence does not always
    # announce itself as a large loss. It can also arrive as an exception: once
    # NaN is in the policy weights, SB3's `Normal(loc=nan, ...)` raises out of
    # `select_action` on the very next step, which is exactly how the PPO
    # background worker died on 2026-09-02. That exception used to propagate to
    # `evaluate_trial_multiseed`, which scored the seed FAILED_RUN_PENALTY and
    # logged it as an unexplained error -- the right score for the wrong reason,
    # with no record that the cause was divergence. A crash that follows a
    # non-finite loss is relabelled here; a crash with no non-finite loss behind
    # it is a real bug and is re-raised untouched.
    try:
        for step in range(n_steps):
            next_obs, rewards, terminateds, truncateds, step_info = env.step(action_dict)

            # Close the intervals that finished, then re-decide for whoever needs it.
            if buffer is not None:
                for rec in step_info["completed"]:
                    vid = rec["vid"]
                    prev = open_decision.get(vid)
                    if prev is None:
                        continue
                    s2 = next_obs.get(vid)
                    done = rec["done"] if s2 is not None else True
                    if s2 is None:
                        s2 = np.zeros(STATE_DIM, dtype=np.float32)
                    buffer.push(prev["state"], prev["raw_action"], rec["reward"],
                                np.asarray(s2, dtype=np.float32), bool(done), rec["delta_actual"],
                                action_idx=prev.get("action_idx"),
                                behaviour_log_prob=prev.get("behaviour_log_prob"))

                if len(buffer) >= 16 and train_steps_during_rollout > 0:
                    for _ in range(train_steps_during_rollout):
                        batch = buffer.sample(batch_size=16)
                        try:
                            loss_dict = model.update(batch)
                            # The return value used to be discarded. It is the only
                            # signal in this whole rollout that says whether the
                            # model is still learning, and the objective does not
                            # contain it.
                            if watch_divergence:
                                loss_tracker.observe_update(loss_dict)
                                updates_this_pseudo_episode += 1
                        except Exception:
                            # This used to be `pass`. A baseline whose update always
                            # raised (a batch-format mismatch, say) would finish HPO
                            # normally and report "tuned" hyperparameters for a model
                            # that never took a single gradient step. The count is
                            # returned and recorded as a trial user attribute.
                            n_update_failures += 1
                            if n_update_failures == 1:
                                logger.exception(
                                    "%s: model.update() raised on the first training batch; "
                                    "further failures in this rollout are counted, not logged.",
                                    type(model).__name__,
                                )

            for rec in step_info["completed"]:
                open_decision.pop(rec["vid"], None)

            action_dict = {}
            for vid in step_info["needs_decision"]:
                s_vec = next_obs.get(vid)
                if s_vec is None:
                    continue
                grant, raw_action, info = model.select_action(s_vec, deterministic=False)
                open_decision[vid] = _decision_record(s_vec, info, raw_action)
                action_dict[vid] = grant

            for vid in [v for v in open_decision if v not in next_obs]:
                open_decision.pop(vid, None)

            obs = next_obs
            steps_completed = step + 1

            # --- divergence check, at the pseudo-episode boundary ---------------
            if watch_divergence:
                # A NaN loss is not a matter of degree, so it is not made to wait for
                # the boundary: the update that produced it has already written
                # non-finite values into the weights.
                verdict = loss_tracker.nonfinite_verdict(episode=pseudo_episode + 1)

                if verdict is None and loss_tracker.n_updates > 0:
                    steps_since_first_update += 1
                    if steps_since_first_update % check_interval == 0:
                        pseudo_episode += 1
                        verdict = monitor.observe(
                            episode=pseudo_episode,
                            mean_loss=loss_tracker.mean_recent_loss,
                            grad_updates_this_episode=updates_this_pseudo_episode,
                        )
                        updates_this_pseudo_episode = 0

                if verdict is not None:
                    logger.error(
                        "Diverging rollout stopped at step %d/%d (seed=%s): %s",
                        steps_completed, n_steps, seed, verdict,
                    )
                    break
    except Exception as exc:
        if not watch_divergence or loss_tracker.max_seen_nonfinite == 0:
            raise
        verdict = AbortVerdict(
            kind=ABORT_DIVERGED,
            episode=pseudo_episode + 1,
            reason=(
                f"the rollout raised {type(exc).__name__} at step {steps_completed} "
                "after a gradient update reported a non-finite loss; the policy "
                f"weights are NaN/Inf ({exc})"
            ),
            detail={
                "exception": type(exc).__name__,
                "max_consecutive_nonfinite_losses": loss_tracker.max_seen_nonfinite,
                "n_updates": loss_tracker.n_updates,
                "rule": "crash_after_nonfinite_loss",
            },
        )
        logger.error(
            "Diverging rollout crashed at step %d/%d (seed=%s): %s",
            steps_completed, n_steps, seed, verdict,
        )

    # Close the SMDP intervals still in flight when the step budget ran out, and
    # push their transitions like any other completed interval. `close()` used to
    # discard them: 12.3 % of the decisions made in a 600-step episode never
    # reached the buffer, and the loss is length-biased (an interval is likelier
    # to still be open the longer its Delta), so what went missing was
    # disproportionately the long-Delta decisions carrying the largest accrued
    # penalty. The buffer therefore saw long-Delta successes but not long-Delta
    # failures. These records come back with done=False and transmitted=False.
    for rec in env.finalize_open_intervals():
        if buffer is None:
            continue
        prev = open_decision.pop(rec["vid"], None)
        if prev is None:
            continue
        s2 = obs.get(rec["vid"])
        if s2 is None:
            s2 = np.zeros(STATE_DIM, dtype=np.float32)
        buffer.push(prev["state"], prev["raw_action"], rec["reward"],
                    np.asarray(s2, dtype=np.float32), bool(rec["done"]), rec["delta_actual"],
                    action_idx=prev.get("action_idx"),
                    behaviour_log_prob=prev.get("behaviour_log_prob"))

    metrics = env.get_metrics()
    env.close()
    gc.collect()

    # Normalise against the ACTUAL decoder power bounds (design range [10, 23] dBm),
    # not a hardcoded [20, 30] window. `normalize_power_dbm` is imported from
    # src/evaluate.py so the HPO objective and the leaderboard that ranks the
    # tuned models cannot use two different power scales; they used to.
    avg_p = metrics.get("avg_tx_power_dbm", 0.5 * (P_MIN + P_MAX))
    metrics["avg_power_dbm"] = avg_p
    metrics["avg_power_norm"] = round(normalize_power_dbm(avg_p), 4)
    metrics["n_update_failures"] = int(n_update_failures)

    # Divergence verdict, written into the metrics dict so it reaches
    # `compute_composite_objective`, the per-seed user attributes and the trial
    # CSV without any caller having to reach back into the loop's locals.
    metrics["diverged"] = bool(verdict is not None)
    metrics["divergence_kind"] = verdict.kind if verdict is not None else ""
    metrics["divergence_reason"] = verdict.reason if verdict is not None else ""
    metrics["divergence_rule"] = (
        str(verdict.detail.get("rule", "")) if verdict is not None else ""
    )
    metrics["divergence_episode"] = int(verdict.episode) if verdict is not None else -1
    metrics["divergence_mean_loss"] = (
        float(verdict.detail["mean_loss"])
        if verdict is not None and is_finite_number(verdict.detail.get("mean_loss"))
        else float("nan")
    )
    metrics["steps_completed"] = int(steps_completed)
    metrics["n_grad_updates"] = int(loss_tracker.n_updates)
    metrics["mean_recent_loss"] = float(loss_tracker.mean_recent_loss)
    metrics["max_consecutive_nonfinite_losses"] = int(loss_tracker.max_seen_nonfinite)
    # The threshold this rollout was actually judged against, and the per-model
    # baseline it was derived from. A rollout that passed by a hair and one that
    # passed comfortably are otherwise indistinguishable, and the relative rule
    # makes that difference large: the threshold is 1000x the model's own early
    # median, so a model whose loss starts high is judged leniently.
    monitor_state = monitor.state()
    metrics["divergence_threshold"] = float(monitor_state["loss_threshold"])
    metrics["divergence_baseline_loss"] = monitor_state["baseline_loss"]
    metrics["divergence_pseudo_episodes_seen"] = int(monitor_state["episodes_seen"])

    # Outage is COVERAGE outage (user decision, 2026-08-31): the fraction of
    # vehicle-time spent outside the RSU range, where no AoI update can happen.
    # `packet_loss_rate` is the link-layer frame error rate and is a different
    # quantity; this line used to alias one to the other, which is why the two
    # columns in results/hpo/optuna_trials_*.csv were identical. The environment
    # owns the measurement and must export `OUTAGE_METRIC_KEY`.
    if OUTAGE_METRIC_KEY in metrics:
        metrics["outage_rate"] = metrics[OUTAGE_METRIC_KEY]
        metrics["outage_metric"] = OUTAGE_METRIC_KEY
    else:
        metrics["outage_rate"] = metrics.get(LEGACY_OUTAGE_METRIC_KEY, 0.0)
        metrics["outage_metric"] = LEGACY_OUTAGE_METRIC_KEY
        logger.warning(
            "AoiV2IEnv.get_metrics() did not return '%s'; the HPO objective is scoring "
            "'%s' (link-layer frame error rate) instead. These are different quantities "
            "and the tuned hyperparameters inherit the substitution.",
            OUTAGE_METRIC_KEY, LEGACY_OUTAGE_METRIC_KEY,
        )

    # Emptiness check, immediately before returning. `n_observations == 0` or
    # `tx_attempts == 0` means the rollout measured nothing: no AoI sample was
    # recorded, or the policy never transmitted. Every remaining metric has
    # degraded to a flattering zero, and `compute_composite_objective` would
    # score that 0.0 -- the global minimum of a minimisation study.
    metrics["run_failed"] = bool(run_is_empty(metrics))
    if metrics["run_failed"]:
        logger.warning(
            "Empty rollout (seed=%s, density=%s, n_steps=%s): n_observations=%s, "
            "tx_attempts=%s. Scoring it %.1f instead of 0.0.",
            seed, density, n_steps, metrics.get("n_observations"),
            metrics.get("tx_attempts"), FAILED_RUN_PENALTY,
        )

    return metrics


def evaluate_trial_multiseed(
    model_cls: Any,
    hparams: Dict[str, Any],
    seeds: List[int],
    n_steps: int = 35,
    density: float = 25.0,
    rsu_range: float = DEFAULT_RSU_RANGE,
    reward_weights: Optional[Dict[str, float]] = None,
    trial: Optional[optuna.Trial] = None,
    check_divergence: bool = True,
) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluates a set of hyperparameters across multiple seeds and returns the mean composite score.

    When `trial` is given, every per-seed diagnostic that the CSV needs in order
    to tell a healthy trial from a dead one is written as a user attribute:
    `n_observations_seed<S>`, `tx_attempts_seed<S>`, `n_failed_seeds` (rollouts
    that raised or measured nothing) and `n_update_failures`. Without them a
    study where two of three seeds died looked exactly like a healthy one.

    A seed whose rollout diverged is scored `FAILED_RUN_PENALTY`, in the same
    place and for the same reason an empty rollout is: its metrics describe a
    model that has stopped learning. The penalty is applied per seed rather than
    flattened over the whole trial, so a combination that diverges on one seed of
    three still ranks above one that diverges on all three, and TPE keeps a
    gradient to steer by. Either way the trial is out of contention: the worst
    real committed score is 1.459, and one penalised seed of three already puts
    the mean above 33.

    `n_vehicles` used to be an argument here and was never read; the population
    is set by `density`.
    """
    scores = []
    seed_metrics: List[Dict[str, float]] = []
    n_failed_seeds = 0
    n_update_failures = 0
    n_diverged_seeds = 0
    first_divergence: Optional[Dict[str, Any]] = None

    for i, seed in enumerate(seeds):
        try:
            # Instantiate model
            model = model_cls(state_dim=STATE_DIM, num_channels=comm.NUM_SUBCHANNELS, **hparams)
            metrics = evaluate_model_in_env(
                model=model,
                seed=seed,
                n_steps=n_steps,
                density=density,
                rsu_range=rsu_range,
                train_steps_during_rollout=2,
                reward_weights=reward_weights,
                check_divergence=check_divergence,
            )
            score = compute_composite_objective(metrics)
            scores.append(score)
            seed_metrics.append(metrics)
            n_update_failures += int(metrics.get("n_update_failures", 0) or 0)
            if metrics.get("run_failed"):
                n_failed_seeds += 1
            if run_diverged(metrics):
                n_diverged_seeds += 1
                if first_divergence is None:
                    first_divergence = {
                        "seed": int(seed),
                        "kind": metrics.get("divergence_kind", ""),
                        "rule": metrics.get("divergence_rule", ""),
                        "reason": metrics.get("divergence_reason", ""),
                        "episode": int(metrics.get("divergence_episode", -1)),
                        "steps_completed": int(metrics.get("steps_completed", 0)),
                        "n_grad_updates": int(metrics.get("n_grad_updates", 0)),
                        "mean_loss": metrics.get("divergence_mean_loss"),
                    }
            if trial is not None:
                trial.set_user_attr(f"n_observations_seed{seed}", int(metrics.get("n_observations", 0) or 0))
                trial.set_user_attr(f"tx_attempts_seed{seed}", int(metrics.get("tx_attempts", 0) or 0))
                trial.set_user_attr(f"diverged_seed{seed}", bool(run_diverged(metrics)))
                trial.set_user_attr(f"n_grad_updates_seed{seed}", int(metrics.get("n_grad_updates", 0) or 0))
                trial.set_user_attr(f"steps_completed_seed{seed}", int(metrics.get("steps_completed", 0) or 0))
        except Exception as e:
            logger.exception(f"Error during rollout for seed {seed}: {e}")
            scores.append(FAILED_RUN_PENALTY)
            n_failed_seeds += 1
            if trial is not None:
                trial.set_user_attr(f"n_observations_seed{seed}", -1)
                trial.set_user_attr(f"tx_attempts_seed{seed}", -1)
                trial.set_user_attr(f"diverged_seed{seed}", False)
                trial.set_user_attr(f"n_grad_updates_seed{seed}", -1)
                trial.set_user_attr(f"steps_completed_seed{seed}", -1)

        if trial is not None and scores:
            # Report the running mean so a pruner has something to act on. With
            # the default NopPruner this is inert bookkeeping; it exists so that
            # configuring a real pruner actually prunes.
            trial.report(float(np.mean(scores)), step=i)
            if trial.should_prune():
                raise optuna.TrialPruned()

    mean_score = float(np.mean(scores)) if scores else FAILED_RUN_PENALTY

    # A trial that diverged on ANY seed is scored the full penalty, not the mean
    # of a penalised seed and two healthy ones. Measured from the nine committed
    # studies, real scores reach 35.815 (PPO) while one penalised seed of three
    # averages to at least 33.3, so the mean does not reliably rank a diverging
    # combination below a healthy one -- and PPO is precisely the model whose
    # diverging learning rate this is meant to reject. The per-seed penalty stays
    # in place underneath; `n_diverged_seeds` keeps 1-of-3 distinguishable from
    # 3-of-3 in the CSV even though both score the same.
    if n_diverged_seeds > 0:
        mean_score = float(FAILED_RUN_PENALTY)

    # Average individual metrics across seeds
    avg_metrics: Dict[str, Any] = {}
    if seed_metrics:
        for k in ["mean_error", "mean_aoi", "outage_rate", OUTAGE_METRIC_KEY,
                  "packet_loss_rate", "avg_tx_power_dbm", "avg_power_norm",
                  "n_observations", "tx_attempts"]:
            if k in seed_metrics[0]:
                avg_metrics[k] = round(float(np.mean([m.get(k, 0.0) for m in seed_metrics])), 4)
    avg_metrics["n_failed_seeds"] = int(n_failed_seeds)
    avg_metrics["n_update_failures"] = int(n_update_failures)

    # Divergence, aggregated to the trial. `diverged` is the single column a
    # reader of optuna_trials_<model>.csv can sort on; the rest says why, so the
    # verdict does not have to be taken on trust.
    avg_metrics["n_diverged_seeds"] = int(n_diverged_seeds)
    avg_metrics["diverged"] = bool(n_diverged_seeds > 0)
    avg_metrics["divergence_kind"] = (first_divergence or {}).get("kind", "")
    avg_metrics["divergence_rule"] = (first_divergence or {}).get("rule", "")
    avg_metrics["divergence_reason"] = (first_divergence or {}).get("reason", "")
    avg_metrics["divergence_seed"] = int((first_divergence or {}).get("seed", -1))
    avg_metrics["divergence_pseudo_episode"] = int((first_divergence or {}).get("episode", -1))
    avg_metrics["divergence_at_env_step"] = int((first_divergence or {}).get("steps_completed", -1))
    avg_metrics["divergence_at_grad_update"] = int((first_divergence or {}).get("n_grad_updates", -1))
    if first_divergence is not None:
        logger.error(
            "Trial diverged on %d/%d seed(s); scoring each diverged seed %.1f. First: %s",
            n_diverged_seeds, len(seeds), FAILED_RUN_PENALTY, first_divergence,
        )

    if seed_metrics:
        # Which outage definition the objective actually scored, so the trial CSV
        # is unambiguous even if the environment changes underneath it.
        avg_metrics["outage_metric"] = seed_metrics[0].get("outage_metric", "")

    return mean_score, avg_metrics


def run_hpo_study(
    model_name: Union[str, type, Any],
    model_cls: Optional[Any] = None,
    n_trials: int = 15,
    seeds: Optional[List[int]] = None,
    storage: Optional[str] = None,
    study_name: Optional[str] = None,
    n_steps: int = DEFAULT_HPO_N_STEPS,
    sampler: Optional[optuna.samplers.BaseSampler] = None,
    pruner: Optional[optuna.pruners.BasePruner] = None,
    tune_reward_weights: bool = False,
    check_divergence: bool = True,
) -> optuna.Study:
    """
    Runs an Optuna study to optimize hyperparameters for a given model.

    `tune_reward_weights` is off by default: w1..w4 stay pinned to
    `DEFAULT_REWARD_WEIGHTS` so all nine baselines are searched against one
    identical reward. Turn it on only for a reward-shaping ablation, never for
    the numbers that go into the cross-model comparison table.
    """
    if model_cls is None:
        if callable(model_name) and not isinstance(model_name, str):
            model_cls = model_name
            canonical_name = getattr(model_cls, "__name__", "CustomModel")
        else:
            # Resolve through the baseline registry; it raises with a listing on a miss.
            canonical_name = normalize_model_name(model_name)
            model_cls = get_baseline(canonical_name)
    else:
        canonical_name = normalize_model_name(model_name) if isinstance(model_name, str) else getattr(model_cls, "__name__", "CustomModel")
    eval_seeds = seeds if seeds is not None else list(HPO_TUNING_SEEDS)

    if sampler is None:
        sampler = optuna.samplers.TPESampler(seed=42)
    if pruner is None:
        # Explicitly no pruning. The previous default was a MedianPruner that
        # could never fire because nothing in the objective called
        # `trial.report()`, so the configuration only looked like pruning.
        # `evaluate_trial_multiseed` now reports the running mean per seed, so
        # passing a real pruner in works; the default stays off because pruning
        # on a 3-seed mean would drop trials on one unlucky seed.
        pruner = optuna.pruners.NopPruner()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        study_name=study_name or f"hpo_{canonical_name}",
        direction="minimize",
        storage=storage,
        sampler=sampler,
        pruner=pruner,
        load_if_exists=True,
    )

    def objective(trial: optuna.Trial) -> float:
        hparams = sample_hparams(trial, canonical_name)
        # Reward weights are a property of the benchmark, so by default every
        # trial of every model runs under the same fixed reward and only the
        # model hyperparameters are searched. Tuning them per model would give
        # each baseline its own objective and break the cross-model comparison.
        if tune_reward_weights:
            reward_weights = sample_reward_weights(trial)
        else:
            reward_weights = dict(DEFAULT_REWARD_WEIGHTS)
            for k, v in reward_weights.items():
                trial.set_user_attr(k, v)
        score, avg_metrics = evaluate_trial_multiseed(
            model_cls=model_cls,
            hparams=hparams,
            seeds=eval_seeds,
            n_steps=n_steps,
            reward_weights=reward_weights,
            trial=trial,
            check_divergence=check_divergence,
        )
        for k, v in avg_metrics.items():
            trial.set_user_attr(k, v)
        trial.set_user_attr("composite_score", score)
        return score

    study.optimize(objective, n_trials=n_trials, n_jobs=1)
    logger.info(
        f"[{canonical_name}] HPO Complete! Best Trial #{study.best_trial.number}: "
        f"Value={study.best_value:.4f}, Params={study.best_params}"
    )
    return study


def save_study_results(
    study: optuna.Study,
    model_name: str,
    output_dir: str = "/home/imnyj/Workspace/paper4/coder/results/hpo",
) -> Tuple[str, Dict[str, Any]]:
    """
    Saves Optuna study trial history to CSV.
    """
    os.makedirs(output_dir, exist_ok=True)
    canonical_name = normalize_model_name(model_name)

    trials_csv_path = os.path.join(output_dir, f"optuna_trials_{canonical_name}.csv")
    df_trials = study.trials_dataframe()

    # Guarantee the four *normalised* reward weights appear as plain w1..w4 columns.
    # `trials_dataframe()` only carries the raw suggestions (params_w1_raw ...) and
    # `user_attrs_w1 ...`; the audit found the effective weights were absent entirely.
    attr_by_number = {t.number: t.user_attrs for t in study.trials}
    if "number" in df_trials.columns:
        for key in REWARD_WEIGHT_KEYS:
            df_trials[key] = [
                attr_by_number.get(int(n), {}).get(key) for n in df_trials["number"]
            ]
    df_trials.to_csv(trials_csv_path, index=False)

    best_params = dict(study.best_params)
    best_weights = {
        k: study.best_trial.user_attrs[k]
        for k in REWARD_WEIGHT_KEYS
        if k in study.best_trial.user_attrs
    }
    # Deliberately NOT merged into best_params: `hparams_json` is consumed by
    # run_all.py and forwarded to a model constructor, and w1..w4 are AoiV2IEnv
    # arguments. They stay in their own `w1`..`w4` / `reward_weights_json`
    # columns, which is where the environment reads them from.

    # The winning trial should never be a diverged one -- a diverged seed costs
    # FAILED_RUN_PENALTY and no real score comes near it -- but "should never"
    # is exactly the kind of claim this pipeline has been wrong about before.
    # If every trial diverged, `study.best_trial` is a diverged trial and the
    # hyperparameters below would be handed straight to a 200,000-step run.
    best_diverged = bool(study.best_trial.user_attrs.get("diverged", False))
    if best_diverged:
        logger.error(
            "[%s] the BEST trial (#%d, value %.4f) diverged: %s. Every trial in this "
            "study must have diverged, because a single diverged seed scores %.1f. "
            "These hyperparameters must not be trained on.",
            canonical_name, study.best_trial.number, float(study.best_value),
            study.best_trial.user_attrs.get("divergence_reason", "(no reason recorded)"),
            FAILED_RUN_PENALTY,
        )

    best_record = {
        "model_name": canonical_name,
        "category": MODEL_CATEGORIES.get(canonical_name, "Baseline"),
        "best_value": round(float(study.best_value), 4),
        "best_trial_number": int(study.best_trial.number),
        "best_params": best_params,
        "best_reward_weights": best_weights,
        "best_trial_diverged": best_diverged,
        "n_diverged_trials": sum(
            1 for t in study.trials if t.user_attrs.get("diverged", False)
        ),
    }
    return trials_csv_path, best_record


def run_all_baselines_hpo(
    n_trials: int = 15,
    output_dir: str = "/home/imnyj/Workspace/paper4/coder/results/hpo",
    models: Optional[List[str]] = None,
    seeds: Optional[List[int]] = None,
    n_steps: int = DEFAULT_HPO_N_STEPS,
    tune_reward_weights: bool = False,
    check_divergence: bool = True,
) -> Tuple[str, pd.DataFrame]:
    """
    Runs hyperparameter optimization across all baseline models, generates per-model trial CSVs,
    and consolidates the optimal hyperparameters into optuna_best_params.csv.
    """
    os.makedirs(output_dir, exist_ok=True)
    target_models = [normalize_model_name(m) for m in (models or CANONICAL_MODEL_NAMES)]
    eval_seeds = seeds or list(HPO_TUNING_SEEDS)

    best_records: List[Dict[str, Any]] = []

    for model_name in target_models:
        logger.info(f"===> Starting Optuna HPO for baseline: {model_name} (trials={n_trials})")
        study = run_hpo_study(
            model_name=model_name,
            n_trials=n_trials,
            seeds=eval_seeds,
            n_steps=n_steps,
            tune_reward_weights=tune_reward_weights,
            check_divergence=check_divergence,
        )
        _, record = save_study_results(study, model_name=model_name, output_dir=output_dir)

        # Flatten record for master CSV
        flat_row: Dict[str, Any] = {
            "model_name": record["model_name"],
            "category": record["category"],
            "best_value": record["best_value"],
            "best_trial_number": record["best_trial_number"],
        }
        for k, v in record["best_params"].items():
            flat_row[k] = v
        # Explicit reward-weight columns (Conversation.md line 31 requires w1..w4 to be
        # searched; the audit found them missing from results/hpo/*.csv).
        for k in REWARD_WEIGHT_KEYS:
            flat_row[k] = record.get("best_reward_weights", {}).get(k)
        flat_row["reward_weights_json"] = json.dumps(record.get("best_reward_weights", {}))
        flat_row["hparams_json"] = json.dumps(record["best_params"])
        # Read by whoever launches training from this file: a True here means the
        # row's hyperparameters were the least bad of a set that all diverged.
        flat_row["best_trial_diverged"] = bool(record.get("best_trial_diverged", False))
        flat_row["n_diverged_trials"] = int(record.get("n_diverged_trials", 0))
        best_records.append(flat_row)

    df_best = pd.DataFrame(best_records)
    best_csv_path = os.path.join(output_dir, "optuna_best_params.csv")
    df_best.to_csv(best_csv_path, index=False)
    logger.info(f"All baselines HPO complete! Master parameters saved to {best_csv_path}")

    return best_csv_path, df_best


def main() -> None:
    parser = argparse.ArgumentParser(description="Optuna HPO Pipeline for AoI Baseline Models")
    parser.add_argument("--n-trials", type=int, default=15, help="Number of trials per model")
    parser.add_argument("--output-dir", type=str, default="/home/imnyj/Workspace/paper4/coder/results/hpo")
    parser.add_argument("--models", nargs="+", default=CANONICAL_MODEL_NAMES, help="List of models to optimize")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(HPO_TUNING_SEEDS),
                        help="Tuning seeds (disjoint from training 42..141 and evaluation 5001..5005)")
    # This is the MEASUREMENT window, not the warmup; the warmup is
    # `DEFAULT_WARMUP_STEPS` and is applied identically here, in training and in
    # evaluation. An earlier comment here read "350 matches the training warmup",
    # which conflated the two: it was never a warmup and it no longer matches one.
    #
    # Why 350 and not 35: 35 steps is 3.5 simulated seconds, and a vehicle needs
    # ~35 s from its spawn edge to reach the RSU disc, so a 35-step window scores
    # almost no traffic and the search optimises noise.
    #
    # Why it is no longer 350: 350 steps was decided when the objective was the
    # four end-of-rollout metrics alone. The rollout now also has to be long
    # enough for a diverging loss to declare itself, and the guard needs
    # `DEFAULT_LOSS_PATIENCE` consecutive pseudo-episodes of
    # `HPO_CHECK_INTERVAL_STEPS` steps each, i.e. 600 steps of sustained
    # over-threshold loss on top of however long the model takes to get there.
    # 350 could not have produced a verdict at all. `DEFAULT_HPO_N_STEPS` is the
    # replacement; the block comment above `HPO_CHECK_INTERVAL_STEPS` says where
    # it comes from. It is also 2x the 2000-step training/evaluation episode, so
    # the objective is no longer measured over a window shorter than the score it
    # is a proxy for.
    parser.add_argument("--n-steps", type=int, default=DEFAULT_HPO_N_STEPS,
                        help="Simulation steps per seed")
    parser.add_argument("--no-divergence-guard", action="store_true",
                        help="score diverging trials on their metrics instead of "
                             "penalising them (diagnostics only -- this is how the "
                             "learning rates that destroyed the 2026-09-02 training "
                             "runs were selected)")
    parser.add_argument("--tune-reward-weights", action="store_true",
                        help="search w1..w4 per model instead of pinning them to the "
                             "benchmark defaults (ablation only -- makes cross-model "
                             "comparison invalid)")
    args = parser.parse_args()

    run_all_baselines_hpo(
        n_trials=args.n_trials,
        output_dir=args.output_dir,
        models=args.models,
        seeds=args.seeds,
        n_steps=args.n_steps,
        tune_reward_weights=args.tune_reward_weights,
        check_divergence=not args.no_divergence_guard,
    )


if __name__ == "__main__":
    main()
