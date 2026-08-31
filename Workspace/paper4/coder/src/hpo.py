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
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import optuna
import pandas as pd
import src.Communications as comm
from src.baselines import ALL_BASELINES, BASELINE_CATEGORIES, get_baseline
from src.hot_swap_trainer import DEFAULT_REWARD_WEIGHTS, REWARD_WEIGHT_KEYS, AoiV2IEnv
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
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "clip_range": trial.suggest_float("clip_range", 0.1, 0.3),
            "ent_coef": trial.suggest_float("ent_coef", 1e-4, 0.05, log=True),
            "vf_coef": trial.suggest_float("vf_coef", 0.2, 0.8),
            "n_epochs": trial.suggest_categorical("n_epochs", [4, 10, 20]),
        }
    elif canonical_name == "SAC":
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 3e-3, log=True),
            "gamma": trial.suggest_float("gamma", 0.95, 0.999),
            "tau": trial.suggest_float("tau", 0.001, 0.02, log=True),
            "target_update_interval": trial.suggest_categorical("target_update_interval", [1, 2, 4]),
        }
    elif canonical_name == "TD3":
        params = {
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
            "n_step": trial.suggest_categorical("n_step", [1, 3, 5]),
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
            "omega": trial.suggest_float("omega", 0.1, 0.9),
            "tau": trial.suggest_float("tau", 0.001, 0.02, log=True),
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
    """
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


def evaluate_model_in_env(
    model: Any,
    seed: int = 42,
    n_steps: int = 35,
    density: float = 25.0,
    n_vehicles: Optional[int] = None,
    rsu_pos: Tuple[float, float] = (0.0, 0.0),
    rsu_range: float = DEFAULT_RSU_RANGE,
    train_steps_during_rollout: int = 0,
    reward_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Evaluates a baseline model in the genuine SUMO AoiV2IEnv for a specific seed.
    Runs real vehicle kinematics, TraCI TLS phase transitions, hybrid action scheduling,
    Rayleigh-SINR co-channel contention, retrospective position estimation error, and AoI.

    `reward_weights` are the sampled w1..w4 of the design reward; when given they are
    passed to the environment constructor so the trial actually trains under them.
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
        warmup_steps=350,
        **env_kwargs,
    )
    obs, info = env.reset()
    buffer = RetrospectiveReplayBuffer(capacity=1000) if train_steps_during_rollout > 0 else None

    # Event-driven SMDP rollout, matching run_hot_swap_training. Granting every
    # vehicle on every step -- what this loop used to do -- makes Delta inert, so
    # every trial would have measured the same fixed transmit schedule and Optuna
    # would have optimised hyperparameters against a constant.
    open_decision: Dict[str, Dict[str, Any]] = {}
    action_dict: Dict[str, Any] = {}
    for vid, s_vec in obs.items():
        grant, raw_action, _ = model.select_action(s_vec, deterministic=False)
        open_decision[vid] = {"state": np.asarray(s_vec, dtype=np.float32), "raw_action": raw_action}
        action_dict[vid] = grant

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
                            np.asarray(s2, dtype=np.float32), bool(done), rec["delta_actual"])

            if len(buffer) >= 16 and train_steps_during_rollout > 0:
                for _ in range(train_steps_during_rollout):
                    batch = buffer.sample(batch_size=16)
                    try:
                        model.update(batch)
                    except Exception:
                        pass

        for rec in step_info["completed"]:
            open_decision.pop(rec["vid"], None)

        action_dict = {}
        for vid in step_info["needs_decision"]:
            s_vec = next_obs.get(vid)
            if s_vec is None:
                continue
            grant, raw_action, _ = model.select_action(s_vec, deterministic=False)
            open_decision[vid] = {"state": np.asarray(s_vec, dtype=np.float32), "raw_action": raw_action}
            action_dict[vid] = grant

        for vid in [v for v in open_decision if v not in next_obs]:
            open_decision.pop(vid, None)

        obs = next_obs

    metrics = env.get_metrics()
    env.close()
    del env
    import gc
    gc.collect()

    # Normalise against the ACTUAL decoder power bounds (design range [10, 23] dBm),
    # not a hardcoded [20, 30] window, so the objective stays correct if the bounds move.
    avg_p = metrics.get("avg_tx_power_dbm", 0.5 * (P_MIN + P_MAX))
    avg_p_norm = float(np.clip((avg_p - P_MIN) / max(1e-6, P_MAX - P_MIN), 0.0, 1.0))
    metrics["avg_power_dbm"] = avg_p
    metrics["avg_power_norm"] = round(avg_p_norm, 4)
    metrics["outage_rate"] = metrics.get("packet_loss_rate", 0.0)

    return metrics


def evaluate_trial_multiseed(
    model_cls: Any,
    hparams: Dict[str, Any],
    seeds: List[int],
    n_steps: int = 35,
    density: float = 25.0,
    n_vehicles: Optional[int] = None,
    rsu_range: float = DEFAULT_RSU_RANGE,
    reward_weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    Evaluates a set of hyperparameters across multiple seeds and returns the mean composite score.
    """
    scores = []
    seed_metrics: List[Dict[str, float]] = []

    for seed in seeds:
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
            )
            score = compute_composite_objective(metrics)
            scores.append(score)
            seed_metrics.append(metrics)
        except Exception as e:
            logger.warning(f"Error during rollout for seed {seed}: {e}")
            scores.append(100.0)

    mean_score = float(np.mean(scores)) if scores else 100.0

    # Average individual metrics across seeds
    avg_metrics: Dict[str, float] = {}
    if seed_metrics:
        for k in ["mean_error", "mean_aoi", "outage_rate", "packet_loss_rate", "avg_tx_power_dbm", "avg_power_norm"]:
            if k in seed_metrics[0]:
                avg_metrics[k] = round(float(np.mean([m.get(k, 0.0) for m in seed_metrics])), 4)

    return mean_score, avg_metrics


def run_hpo_study(
    model_name: Union[str, type, Any],
    model_cls: Optional[Any] = None,
    n_trials: int = 15,
    seeds: Optional[List[int]] = None,
    storage: Optional[str] = None,
    study_name: Optional[str] = None,
    n_steps: int = 350,
    sampler: Optional[optuna.samplers.BaseSampler] = None,
    pruner: Optional[optuna.pruners.BasePruner] = None,
    tune_reward_weights: bool = False,
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
    eval_seeds = seeds if seeds is not None else [42, 101, 2024]

    if sampler is None:
        sampler = optuna.samplers.TPESampler(seed=42)
    if pruner is None:
        pruner = optuna.pruners.MedianPruner(n_startup_trials=3, n_warmup_steps=1)

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

    best_record = {
        "model_name": canonical_name,
        "category": MODEL_CATEGORIES.get(canonical_name, "Baseline"),
        "best_value": round(float(study.best_value), 4),
        "best_trial_number": int(study.best_trial.number),
        "best_params": best_params,
        "best_reward_weights": best_weights,
    }
    return trials_csv_path, best_record


def run_all_baselines_hpo(
    n_trials: int = 15,
    output_dir: str = "/home/imnyj/Workspace/paper4/coder/results/hpo",
    models: Optional[List[str]] = None,
    seeds: Optional[List[int]] = None,
    n_steps: int = 350,
    tune_reward_weights: bool = False,
) -> Tuple[str, pd.DataFrame]:
    """
    Runs hyperparameter optimization across all baseline models, generates per-model trial CSVs,
    and consolidates the optimal hyperparameters into optuna_best_params.csv.
    """
    os.makedirs(output_dir, exist_ok=True)
    target_models = [normalize_model_name(m) for m in (models or CANONICAL_MODEL_NAMES)]
    eval_seeds = seeds or [42, 101, 2024]

    best_records: List[Dict[str, Any]] = []

    for model_name in target_models:
        logger.info(f"===> Starting Optuna HPO for baseline: {model_name} (trials={n_trials})")
        study = run_hpo_study(
            model_name=model_name,
            n_trials=n_trials,
            seeds=eval_seeds,
            n_steps=n_steps,
            tune_reward_weights=tune_reward_weights,
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
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 101, 2024], help="Evaluation seeds")
    # 35 steps is 3.5 simulated seconds of measurement. A vehicle needs ~35 s from
    # its spawn edge to reach the RSU disc, so a 35-step window scores almost no
    # traffic and the search optimises noise. 350 matches the training warmup.
    parser.add_argument("--n-steps", type=int, default=350, help="Simulation steps per seed")
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
    )


if __name__ == "__main__":
    main()
