"""Train all nine comparison baselines on the genuine SUMO AoI environment.

Each model runs 100 episodes x 2,000 steps = 200,000 real env.step() calls.

Two things here are easy to get wrong and have been got wrong before:

  * `run_hot_swap_training` treats `total_steps` as the TOTAL across all episodes and
    derives steps_per_ep = total_steps // episodes. Passing the per-episode figure
    silently caps every model at 2,000 steps, i.e. 1% of the requirement.
  * Models are injected as CLASSES, not name strings. The registry in
    src/baselines/__init__.py maps the paper's table names to those classes.

Run detached so an SSH drop cannot kill it:
    setsid nohup /home/imnyj/venv/bin/python run_all.py > training_full.log 2>&1 < /dev/null &
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Set

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.baselines import ALL_BASELINES, get_baseline
from src.divergence_guard import STATUS_COMPLETED  # noqa: E402
from src.hot_swap_trainer import (
    DEFAULT_ERROR_MODE,
    ENV_ONLY_HPARAM_KEYS,
    REWARD_ERROR_MODES,
)  # noqa: E402
from src.hot_swap_trainer import run_hot_swap_training  # noqa: E402

EPISODES = 100
STEPS_PER_EPISODE = 2000
TOTAL_STEPS = EPISODES * STEPS_PER_EPISODE  # 200,000


INT_HPARAM_KEYS = frozenset({
    "hidden_dim", "embed_dim", "policy_freq", "n_epochs",
    "policy_delay", "target_update_freq", "target_update_interval",
    "target_sync_interval", "policy_sync_interval",
    "num_res_blocks", "n_step", "num_delta_levels", "num_power_levels",
    "ctx_dim", "max_agents", "num_tasks", "rollout_n_steps", "n_steps",
    "batch_size", "buffer_capacity",
})

BOOL_HPARAM_KEYS = frozenset({
    "use_target_network", "normalize_advantage", "deterministic",
})


def _is_valid_hparam_value(val: Any) -> bool:
    """Check if a hyperparameter value is valid (non-null, non-NaN, non-infinite)."""
    if val is None:
        return False
    if isinstance(val, (list, tuple, set, dict, np.ndarray)):
        # pd.isna returns an ARRAY for these, and `if <array>` raises
        # "truth value of an array is ambiguous". Containers are never valid
        # hyperparameter scalars here anyway.
        return False
    if pd.isna(val):
        return False
    if isinstance(val, (float, int)):
        try:
            val_f = float(val)
            return not (math.isnan(val_f) or math.isinf(val_f))
        except (ValueError, TypeError):
            return False
    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned in ("nan", "none", "null", "inf", "-inf", ""):
            return False
    return True


def _cast_hparam_value(key: str, val: Any) -> Any:
    """Cast hyperparameter value to its expected type based on key heuristics."""
    if key in INT_HPARAM_KEYS:
        try:
            val_f = float(val)
            if not (math.isnan(val_f) or math.isinf(val_f)):
                return int(round(val_f))
        except (ValueError, TypeError):
            pass
    elif key in BOOL_HPARAM_KEYS:
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "t")
        try:
            return bool(val)
        except Exception:
            pass
    return val


def _clean_key(name: str) -> str:
    return str(name).strip().replace("-", "").replace("_", "").lower()


CANONICAL_BY_CLEAN: Dict[str, str] = {_clean_key(n): n for n in ALL_BASELINES}

LEGACY_NAME_MAP: Dict[str, str] = {
    "hybridppo": "PPO",
    "hybridsac": "SAC",
    "hybridtd3": "TD3",
}


def normalize_model_name(name: Any) -> str:
    """Resolve an alias, or a model class, to its canonical registry name."""
    if not isinstance(name, str):
        name = getattr(name, "__name__", None) or type(name).__name__
    clean = _clean_key(name)
    if clean in LEGACY_NAME_MAP:
        return LEGACY_NAME_MAP[clean]
    return CANONICAL_BY_CLEAN.get(clean, str(name).strip())


def load_hparams_from_csv(csv_path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Load hyperparameters for each model from the HPO best-params CSV.

    Parses the `hparams_json` column and/or individual hyperparameter columns
    for each model entry. Gracefully handles missing files, malformed JSON, NaN/Inf
    values, and duplicate model entries by selecting the highest-performing trial.
    """
    if not csv_path or not str(csv_path).strip():
        logging.warning("No HPO params CSV path provided; falling back to default hyperparameters.")
        return {}

    resolved_path = os.path.expanduser(str(csv_path).strip())
    if not os.path.isfile(resolved_path) and not os.path.isabs(resolved_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(base_dir, resolved_path)
        if os.path.isfile(candidate):
            resolved_path = candidate

    if not os.path.isfile(resolved_path):
        logging.warning("HPO params CSV '%s' not found or is not a regular file; falling back to default hyperparameters.", csv_path)
        return {}

    try:
        df = pd.read_csv(resolved_path)
    except Exception as exc:
        logging.warning("Failed to read HPO params CSV '%s': %s; falling back to default hyperparameters.", resolved_path, exc)
        return {}

    if df.empty:
        logging.warning("HPO params CSV '%s' is empty; falling back to default hyperparameters.", resolved_path)
        return {}

    hparams_by_model: Dict[str, Dict[str, Any]] = {}
    best_score_by_model: Dict[str, float] = {}

    # `ENV_ONLY_HPARAM_KEYS` (w1..w4 and their raw samples) are AoiV2IEnv
    # arguments. Every baseline constructor ends in `**hparams`, so letting them
    # through here would have the model swallow them and the reward never see
    # them. Reward weights come from `DEFAULT_REWARD_WEIGHTS`, not from this CSV.
    ignored_cols = frozenset({
        "model_name", "model", "name", "baseline", "category",
        "best_value", "value", "score", "reward", "best_trial_number", "number",
        "hparams_json", "reward_weights_json", "datetime_start", "datetime_complete",
        "duration", "state",
    }) | ENV_ONLY_HPARAM_KEYS

    for _, row in df.iterrows():
        raw_name = ""
        for col_cand in ("model_name", "model", "name", "baseline"):
            if col_cand in row and pd.notna(row[col_cand]):
                cand_val = str(row[col_cand]).strip()
                if cand_val and cand_val.lower() != "nan":
                    raw_name = cand_val
                    break

        if not raw_name:
            continue

        canonical_name = normalize_model_name(raw_name)

        # Track score if available for multi-trial CSV deduplication (higher is better)
        score = None
        for score_col in ("best_value", "value", "score", "reward"):
            if score_col in row and pd.notna(row[score_col]):
                try:
                    score = float(row[score_col])
                    break
                except (ValueError, TypeError):
                    pass

        # `src/hpo.py` creates its study with direction="minimize" (the composite
        # objective sums error, AoI, outage and power), so on a multi-row CSV the
        # better trial is the one with the LOWER best_value. A row that carries no
        # score at all must never displace one that does.
        if canonical_name in hparams_by_model:
            prev_score = best_score_by_model.get(canonical_name)
            if score is None:
                if prev_score is not None:
                    continue
            elif prev_score is not None and score >= prev_score:
                continue

        raw_hparams: Dict[str, Any] = {}

        # 1. Parse hparams_json
        if "hparams_json" in row and pd.notna(row["hparams_json"]):
            val = row["hparams_json"]
            if isinstance(val, dict):
                raw_hparams.update(val)
            elif isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        raw_hparams.update({
                            k: v for k, v in parsed.items()
                            if k not in ENV_ONLY_HPARAM_KEYS
                        })
                    else:
                        logging.warning("hparams_json for model '%s' is not a JSON object: %s", raw_name, type(parsed).__name__)
                except Exception as exc:
                    logging.warning("Failed to parse hparams_json for model '%s': %s", raw_name, exc)

        # `reward_weights_json` is deliberately NOT merged here. Those weights
        # configure AoiV2IEnv, and this dict is forwarded to a model constructor.
        # The benchmark reward is fixed for every baseline; see
        # `hot_swap_trainer.DEFAULT_REWARD_WEIGHTS`.

        # 3. Fallback / merge with individual parameter columns
        for col in df.columns:
            if col in ignored_cols:
                continue
            val = row.get(col)
            if not _is_valid_hparam_value(val):
                continue
            col_name = str(col)
            if col_name.startswith("params_"):
                col_name = col_name[7:]
            if col_name not in raw_hparams:
                raw_hparams[col_name] = val

        # 4. Filter invalid values and apply type casting
        clean_hparams: Dict[str, Any] = {}
        for k, v in raw_hparams.items():
            if _is_valid_hparam_value(v):
                clean_hparams[k] = _cast_hparam_value(k, v)

        # Keyed by canonical name only. `get_hparams_for_model` resolves aliases,
        # so a second entry under the raw name would just inflate this dict and
        # the count in the log line below.
        hparams_by_model[canonical_name] = clean_hparams
        if score is not None:
            best_score_by_model[canonical_name] = score

    logging.info("Successfully loaded HPO hyperparameters for %d model entry(ies) from '%s'", len(hparams_by_model), resolved_path)
    return hparams_by_model


def get_hparams_for_model(hparams_by_model: Dict[str, Dict[str, Any]], model_name: Any) -> Optional[Dict[str, Any]]:
    """Look up hyperparameters for a model name with canonical and alias fallback."""
    if not hparams_by_model:
        return None
    name_str = getattr(model_name, "__name__", None) or str(model_name)
    name_str = name_str.strip()
    if name_str in hparams_by_model:
        return hparams_by_model[name_str]
    canonical_name = normalize_model_name(name_str)
    if canonical_name in hparams_by_model:
        return hparams_by_model[canonical_name]
    clean = _clean_key(name_str)
    for k, v in hparams_by_model.items():
        if _clean_key(k) == clean:
            return v
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="*", default=list(ALL_BASELINES),
                    help="subset of baselines to train (default: all nine)")
    ap.add_argument("--episodes", type=int, default=EPISODES)
    ap.add_argument("--steps-per-episode", type=int, default=STEPS_PER_EPISODE)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-resume", action="store_true",
                    help="start every model from scratch instead of the latest checkpoint")
    ap.add_argument("--hparams-csv", type=str, default="results/hpo/optuna_best_params.csv",
                    help="path to HPO best parameters CSV (default: results/hpo/optuna_best_params.csv)")
    # Overridable so a test run cannot write into the real checkpoint tree and
    # leave a one-episode smoke checkpoint for the next --resume to pick up.
    ap.add_argument("--checkpoint-dir", type=str, default=None,
                    help="where to write checkpoints (default: the trainer's own checkpoints/ dir)")
    ap.add_argument("--tensorboard-dir", type=str, default=None,
                    help="where to write TensorBoard logs (default: the trainer's own logs/tensorboard dir)")
    ap.add_argument("--log-dir", type=str, default=None,
                    help="where to write per-episode progress CSVs (default: the trainer's own logs/training dir)")
    # Seven densities over 100 episodes: each is visited 14 times (the last two
    # get 15). The grid stops at 35 because the road saturates there -- measured
    # in-range counts flatten at 138-142 for requests of 35 and above and go
    # non-monotone, so a larger request does not make a busier network. Training on
    # a single density and evaluating across a range would have made every
    # reported cell but one an extrapolation.
    ap.add_argument("--density", type=float, nargs="+",
                    default=[5, 10, 15, 20, 25, 30, 35],
                    help="traffic densities to cycle through, one per episode")
    # The two reward-aggregation arms are trained separately and compared; a run
    # must say which arm it belongs to because their rewards are not on the same
    # scale. See hot_swap_trainer.REWARD_ERROR_MODES.
    ap.add_argument("--error-mode", type=str, default=DEFAULT_ERROR_MODE,
                    choices=list(REWARD_ERROR_MODES),
                    help="how the error term aggregates over an SMDP interval")
    # Without this, each model trains as fast as its own forward/backward pass
    # allows, so a cheap model receives many more gradient updates than an
    # expensive one over the same 200k environment steps -- measured at 18x
    # across the density schedule. For a comparison table that is a confound.
    # The cap only slows the fast models, so no baseline is ever handed less
    # training than it would otherwise have had; the cost is wall-clock time.
    ap.add_argument("--updates-per-env-step", type=float, default=None,
                    help="cap gradient updates at this ratio of environment steps "
                         "so every baseline gets an equal training budget "
                         "(default: uncapped, i.e. wall-clock bound)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if args.episodes <= 0 or args.steps_per_episode <= 0:
        logging.error("Episodes (%d) and steps-per-episode (%d) must both be positive integers.",
                      args.episodes, args.steps_per_episode)
        return 1

    total_steps = args.episodes * args.steps_per_episode

    # Parse and expand models argument (supporting "ALL", comma-separated, etc.)
    raw_models = args.models if args.models else list(ALL_BASELINES)
    target_models: List[str] = []
    for item in raw_models:
        tokens = str(item).replace(",", " ").split()
        for token in tokens:
            t = token.strip()
            if not t:
                continue
            if t.upper() in ("ALL", "ALL_BASELINES", "*"):
                target_models.extend(list(ALL_BASELINES))
            else:
                target_models.append(t)
    if not target_models:
        target_models = list(ALL_BASELINES)

    # Deduplicate while preserving order
    seen: Set[str] = set()
    deduped_models: List[str] = []
    for m in target_models:
        canon = normalize_model_name(m)
        if canon not in seen:
            seen.add(canon)
            deduped_models.append(m)

    logging.info("Training %d model(s): %s", len(deduped_models), ", ".join(deduped_models))
    logging.info("Per model: %d episodes x %d steps = %d total env steps",
                 args.episodes, args.steps_per_episode, total_steps)
    logging.info("Reward error mode: %s | density schedule: %s",
                 args.error_mode, args.density)

    # Load HPO best hyperparameters
    hparams_by_model = load_hparams_from_csv(args.hparams_csv)

    failures = []
    for raw_name in deduped_models:
        canonical_name = normalize_model_name(raw_name)
        try:
            model_cls = get_baseline(canonical_name)
        except KeyError as exc:
            logging.error("Unknown baseline '%s' (from '%s'): %s", canonical_name, raw_name, exc)
            failures.append((raw_name, str(exc)))
            continue

        model_hparams = get_hparams_for_model(hparams_by_model, canonical_name)
        if model_hparams is not None:
            logging.info("Applying HPO hyperparameters for %s: %s", canonical_name, model_hparams)
        else:
            logging.warning("No HPO parameters found for %s in '%s'; falling back to default hyperparameters.", canonical_name, args.hparams_csv)

        logging.info("=" * 70)
        logging.info("Starting training for %s (%s)", canonical_name, model_cls.__name__)
        try:
            extra_dirs: Dict[str, Any] = {}
            if args.checkpoint_dir:
                extra_dirs["checkpoint_dir"] = args.checkpoint_dir
            if args.tensorboard_dir:
                extra_dirs["tensorboard_dir"] = args.tensorboard_dir
            if args.log_dir:
                extra_dirs["log_dir"] = args.log_dir

            summary = run_hot_swap_training(
                model_name=model_cls,
                total_steps=total_steps,
                episodes=args.episodes,
                hparams=model_hparams,
                seed=args.seed,
                resume=not args.no_resume,
                density=list(args.density),
                error_mode=args.error_mode,
                updates_per_env_step=args.updates_per_env_step,
                **extra_dirs,
            )
            # A run can finish its function call without having finished its
            # training. `run_hot_swap_training` stops a model whose loss has
            # diverged, whose gradient updates have stopped, or whose background
            # thread has died, and reports it here instead of raising, so that
            # this loop still moves on to the next model. What must NOT happen is
            # the 2026-09-02 outcome, where PPO trained for 11 episodes, spent
            # 8.8 hours doing nothing, and was logged as finished.
            status = summary.get("status", STATUS_COMPLETED)
            if status != STATUS_COMPLETED:
                # Phrased "Failed training <name>:" because that is the string the
                # scheduled report already greps out of the supervisor log.
                logging.error(
                    "Failed training %s: ABORTED (%s) at episode %s of %d -- %s",
                    canonical_name, status, summary.get("abort_episode"),
                    args.episodes, summary.get("abort_reason"),
                )
                logging.error("Partial summary for %s | %s", canonical_name, summary)
                failures.append((canonical_name,
                                 f"{status}: {summary.get('abort_reason')}"))
                continue
            logging.info("Finished %s | %s", canonical_name, summary)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed training %s: %s", canonical_name, exc, exc_info=True)
            failures.append((canonical_name, repr(exc)))

    logging.info("=" * 70)
    if failures:
        logging.error("%d/%d model(s) failed:", len(failures), len(deduped_models))
        for name, err in failures:
            logging.error("  %s: %s", name, err)
        return 1
    logging.info("All %d model(s) trained successfully.", len(deduped_models))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
