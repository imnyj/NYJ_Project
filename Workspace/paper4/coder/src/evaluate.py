# src/evaluate.py
# ============================================================================
# Benchmark Evaluation Harness & Verification for AoI-aware V2I Uplink
#
# Implements Milestone 5 (S5 / R5):
# 1. Loads optimal hyperparameters from `results/hpo/optuna_best_params.csv`.
# 2. Instantiates all 10 models:
#    - Heuristic Baseline: HeuristicScheduler
#    - Category 1 (Basic 3종): HybridPPO, HybridSAC, HybridTD3
#    - Category 2 (Latest 3종): MAPPO, HyARPPO, MPDQN
#    - Category 3 (SOTA AoI 3종): PureAoI, DuelingQAoI, SACAoI
# 3. Executes systematic benchmark matrix across vehicle densities
#    (15.0, 25.0, 35.0, 45.0, 55.0 veh/km) and random seeds (42, 101, 2024, 777, 999)
#    on the genuine SUMO AoiV2IEnv.
# 4. Accurately computes 6 IEEE TWC standard metrics:
#    (1) Mean AoI (s)
#    (2) Peak AoI (s)
#    (3) Outage / Packet Loss rate
#    (4) Position Estimation Error (mean, max, low-speed vs high-speed error)
#    (5) Power Consumption (dBm) & Total RF Energy (Joules)
#    (6) Jain's Fairness Index for AoI and Tracking Error
# 5. Generates and exports structured CSV reports:
#    - `results/eval/eval_raw_runs.csv` (250 runs)
#    - `results/eval/eval_summary_by_density.csv` (50 aggregated density records)
#    - `results/eval/eval_leaderboard.csv` (10 model overall leaderboard)
# ============================================================================

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch

from src.baselines import ALL_BASELINES, BASELINE_CATEGORIES, get_baseline
from src.heuristic_scheduler import HeuristicScheduler
from src.hot_swap_trainer import DEFAULT_REWARD_WEIGHTS, AoiV2IEnv
from src.rl_interface import RSU_RANGE, STATE_DIM

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EvaluateHarness")

# Canonical evaluated models: the rule-based reference plus the nine baselines.
# The list is derived from src/baselines/__init__.py rather than restated here.
# It used to be restated, and when the baselines were replaced on 2026-08-28 this
# file kept naming the discarded ones (HybridPPO, MAPPO, PureAoI, ...), so the
# benchmark could not instantiate a single real model.
CANONICAL_EVAL_MODELS = ["HeuristicScheduler"] + list(ALL_BASELINES)

_CATEGORY_LABELS = {
    "basic": "Category 1 (Basic)",
    "latest": "Category 2 (Latest)",
    "similar": "Category 3 (Similar)",
}
MODEL_CATEGORIES = {
    "HeuristicScheduler": "Category 0 (Heuristic)",
    "Heuristic": "Category 0 (Heuristic)",
    "Heuristic-Dynamic": "Category 0 (Heuristic)",
}
for _group, _names in BASELINE_CATEGORIES.items():
    for _n in _names:
        MODEL_CATEGORIES[_n] = _CATEGORY_LABELS.get(_group, _group)

DEFAULT_DENSITIES = [15.0, 25.0, 35.0, 45.0, 55.0]
DEFAULT_SEEDS = [42, 101, 2024, 777, 999]


#: Canonical spelling for every baseline, keyed by its punctuation-free lowercase
#: form, built from the registry so a new baseline needs no edit here.
_CANONICAL_BY_CLEAN = {
    n.replace("-", "").replace("_", "").lower(): n for n in ALL_BASELINES
}


def normalize_model_name(name: Any) -> str:
    """Resolve an alias, or a model class, to its canonical registry name."""
    if not isinstance(name, str):
        # A class or instance was passed straight through; use its own name.
        return getattr(name, "__name__", None) or type(name).__name__
    clean = name.replace("-", "").replace("_", "").lower()
    if clean in ["heuristicscheduler", "heuristic", "heuristicdynamic", "s25heuristic", "rulebased"]:
        return "HeuristicScheduler"
    return _CANONICAL_BY_CLEAN.get(clean, name)


def load_optimal_hparams(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads optimal hyperparameters from the HPO best params CSV file.
    Parses JSON strings and casts integer hyperparameters appropriately.
    """
    hparams_by_model: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(csv_path):
        logger.warning(f"HPO params CSV not found at {csv_path}. Using default hyperparameters.")
        return hparams_by_model

    try:
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            raw_name = str(row.get("model_name", "")).strip()
            canonical_name = normalize_model_name(raw_name)

            hparams: Dict[str, Any] = {}
            if "hparams_json" in row and pd.notna(row["hparams_json"]):
                try:
                    hparams = json.loads(str(row["hparams_json"]))
                except Exception:
                    hparams = {}

            # Fallback / merge with individual columns
            for col in df.columns:
                if col in ["model_name", "category", "best_value", "best_trial_number", "hparams_json"]:
                    continue
                val = row.get(col)
                if pd.notna(val) and col not in hparams:
                    hparams[col] = val

            # Type conversions for integer hyperparameters
            int_keys = ["hidden_dim", "embed_dim", "policy_freq"]
            for k in int_keys:
                if k in hparams and hparams[k] is not None:
                    hparams[k] = int(float(hparams[k]))

            hparams_by_model[canonical_name] = hparams
        logger.info(f"Successfully loaded optimal hyperparameters for {len(hparams_by_model)} models from {csv_path}.")
    except Exception as e:
        logger.error(f"Error reading HPO params from {csv_path}: {e}. Proceeding with defaults.")

    return hparams_by_model


def instantiate_model(
    model_name: Union[str, Any],
    hparams: Optional[Dict[str, Any]] = None,
    state_dim: int = STATE_DIM,
    num_channels: int = 4,
) -> Union[torch.nn.Module, HeuristicScheduler]:
    """
    Instantiates an evaluated model (HeuristicScheduler or user-provided instantiated Module/callable)
    with specified or optimal hyperparameters.
    """
    if isinstance(model_name, (torch.nn.Module, HeuristicScheduler)):
        return model_name

    if callable(model_name) and not isinstance(model_name, str):
        params = dict(hparams) if hparams is not None else {}
        return model_name(state_dim=state_dim, num_channels=num_channels, **params)

    if not isinstance(model_name, str):
        raise TypeError(f"Invalid model_name type: {type(model_name)}")

    canonical_name = normalize_model_name(model_name)
    params = dict(hparams) if hparams is not None else {}

    if canonical_name == "HeuristicScheduler":
        return HeuristicScheduler(
            delta_min=params.get("delta_min", 0.5),
            delta_max=params.get("delta_max", 10.0),
            delta_cruise_steady=params.get("delta_cruise_steady", 3.5),
            delta_cruise_accel=params.get("delta_cruise_accel", 1.5),
            p_high=params.get("p_high", 23.0),
            p_mid=params.get("p_mid", 20.0),
            p_low=params.get("p_low", 10.0),
            num_subchannels=num_channels,
        )

    # Every other name is a baseline; the registry raises with a listing on a miss.
    model_cls = get_baseline(canonical_name)
    return model_cls(state_dim=state_dim, num_channels=num_channels, **params)


def calculate_jains_fairness(values: List[float]) -> float:
    """
    Computes Jain's Fairness Index: J(x) = (sum(x))^2 / (N * sum(x^2)).
    Returns 1.0 if all values are zero or list is empty.
    """
    if not values:
        return 1.0
    n = len(values)
    sum_v = sum(values)
    sum_sq = sum(v ** 2 for v in values)
    if sum_sq <= 1e-12:
        return 1.0
    jain = (sum_v ** 2) / (n * sum_sq)
    return float(np.clip(jain, 0.0, 1.0))


def evaluate_single_run(
    model: Union[torch.nn.Module, HeuristicScheduler, Any],
    density: float,
    seed: int,
    n_steps: int = 100,
    dt: float = 1.0,
    rsu_pos: Tuple[float, float] = (0.0, 0.0),
    rsu_range: float = RSU_RANGE,
) -> Dict[str, Any]:
    """
    Executes a single benchmark evaluation run on the genuine SUMO AoiV2IEnv.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    # The benchmark reward, identical to the one every model was trained under
    # (`hot_swap_trainer.DEFAULT_REWARD_WEIGHTS`). Scoring a model against a
    # reward other than the one it optimised would invalidate the comparison.
    env = AoiV2IEnv(
        density=density,
        seed=seed,
        max_steps=n_steps,
        rsu_range=rsu_range,
        warmup_steps=350,
        **{k: float(v) for k, v in DEFAULT_REWARD_WEIGHTS.items()},
    )
    obs, info = env.reset()

    def _grant_for(vid: str, s_vec) -> Any:
        """One grant, from whichever policy kind we were handed."""
        if isinstance(model, HeuristicScheduler):
            veh_pos = env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))
            veh_speed = float(getattr(env, "last_speeds", {}).get(vid, 0.0))
            st_dict = {
                "vid": vid,
                "pos": veh_pos,
                "speed": veh_speed,
                "dist_to_rsu": math.hypot(
                    veh_pos[0] - env.target_rsu_pos[0],
                    veh_pos[1] - env.target_rsu_pos[1],
                ),
                "current_time": env.sim_time,
            }
            return model.decide_grant(vid, st_dict)
        with torch.no_grad():
            grant, _, _ = model.select_action(s_vec, deterministic=True)
        return grant

    # Event-driven rollout, mirroring run_hot_swap_training. Granting every
    # vehicle on every step -- which this loop used to do -- makes Delta inert
    # and would benchmark all nine baselines on an identical transmit schedule.
    action_dict = {vid: _grant_for(vid, s_vec) for vid, s_vec in obs.items()}

    for step in range(n_steps):
        next_obs, rewards, terminateds, truncateds, step_info = env.step(action_dict)
        action_dict = {
            vid: _grant_for(vid, next_obs[vid])
            for vid in step_info["needs_decision"]
            if vid in next_obs
        }
        obs = next_obs

    metrics = env.get_metrics()
    env.close()
    del env
    import gc
    gc.collect()

    return {
        "density": float(density),
        "seed": int(seed),
        **metrics,
    }


def run_full_benchmark(
    models: Optional[List[str]] = None,
    densities: Optional[List[float]] = None,
    seeds: Optional[List[int]] = None,
    hparams_csv: str = "/home/imnyj/Workspace/paper4/coder/results/hpo/optuna_best_params.csv",
    output_dir: str = "/home/imnyj/Workspace/paper4/coder/results/eval",
    n_steps: int = 100,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Executes the full benchmark evaluation across models, densities, and seeds.
    Generates 3 DataFrames: raw_runs, summary_by_density, and leaderboard.
    """
    target_models = models if models is not None else CANONICAL_EVAL_MODELS
    target_densities = densities if densities is not None else DEFAULT_DENSITIES
    target_seeds = seeds if seeds is not None else DEFAULT_SEEDS

    logger.info(
        f"Starting Benchmark Matrix: {len(target_models)} models x {len(target_densities)} densities x {len(target_seeds)} seeds = {len(target_models) * len(target_densities) * len(target_seeds)} total runs."
    )

    # 1. Load optimal hyperparameters
    hparams_map = load_optimal_hparams(hparams_csv)

    # 2. Run all combinations
    raw_records: List[Dict[str, Any]] = []

    for model_name in target_models:
        canonical_name = normalize_model_name(model_name)
        category = MODEL_CATEGORIES.get(canonical_name, "Baseline")
        hparams = hparams_map.get(canonical_name, {})

        logger.info(f"Evaluating model: {canonical_name} ({category})...")
        model = instantiate_model(canonical_name, hparams)

        for density in target_densities:
            for seed in target_seeds:
                metrics = evaluate_single_run(
                    model=model,
                    density=density,
                    seed=seed,
                    n_steps=n_steps,
                )
                record = {
                    "model_name": canonical_name,
                    "category": category,
                    **metrics,
                }
                raw_records.append(record)

    df_raw = pd.DataFrame(raw_records)

    # 3. Create summary by density (mean across seeds)
    agg_cols = [
        "mean_aoi",
        "peak_aoi",
        "packet_loss_rate",
        "mean_error",
        "max_error",
        "low_speed_error",
        "high_speed_error",
        "avg_tx_power_dbm",
        "total_energy_joules",
        "jains_fairness_aoi",
        "jains_fairness_err",
    ]
    df_summary = df_raw.groupby(["model_name", "category", "density"], as_index=False)[agg_cols].mean()
    for c in agg_cols:
        if c == "total_energy_joules":
            df_summary[c] = df_summary[c].round(6)
        else:
            df_summary[c] = df_summary[c].round(4)

    # 4. Create overall leaderboard (mean across all densities and seeds)
    df_leaderboard_agg = df_raw.groupby(["model_name", "category"], as_index=False)[agg_cols].mean()

    # Calculate composite score: 1.0 * mean_err + 0.5 * mean_aoi + 2.0 * loss + 0.2 * normalized_power
    p_norm = (df_leaderboard_agg["avg_tx_power_dbm"] - 20.0).clip(lower=0.0) / 10.0
    composite = (
        1.0 * df_leaderboard_agg["mean_error"]
        + 0.5 * df_leaderboard_agg["mean_aoi"]
        + 2.0 * df_leaderboard_agg["packet_loss_rate"]
        + 0.2 * p_norm
    )
    df_leaderboard_agg["composite_score"] = composite.round(4)
    df_leaderboard_sorted = df_leaderboard_agg.sort_values(by="composite_score", ascending=True).reset_index(drop=True)
    df_leaderboard_sorted.insert(0, "rank", range(1, len(df_leaderboard_sorted) + 1))

    for c in agg_cols:
        if c == "total_energy_joules":
            df_leaderboard_sorted[c] = df_leaderboard_sorted[c].round(6)
        else:
            df_leaderboard_sorted[c] = df_leaderboard_sorted[c].round(4)

    # 5. Export to CSV files if output_dir specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        raw_path = os.path.join(output_dir, "eval_raw_runs.csv")
        summary_path = os.path.join(output_dir, "eval_summary_by_density.csv")
        leaderboard_path = os.path.join(output_dir, "eval_leaderboard.csv")

        df_raw.to_csv(raw_path, index=False)
        df_summary.to_csv(summary_path, index=False)
        df_leaderboard_sorted.to_csv(leaderboard_path, index=False)
        logger.info(
            f"Exported evaluation datasets:\n  - {raw_path} ({len(df_raw)} rows)\n  - {summary_path} ({len(df_summary)} rows)\n  - {leaderboard_path} ({len(df_leaderboard_sorted)} rows)"
        )

    return df_raw, df_summary, df_leaderboard_sorted


def main() -> None:
    parser = argparse.ArgumentParser(description="AoI-aware V2I Uplink RL Benchmark Evaluation Harness")
    parser.add_argument(
        "--hparams-csv",
        type=str,
        default="/home/imnyj/Workspace/paper4/coder/results/hpo/optuna_best_params.csv",
    )
    parser.add_argument("--output-dir", type=str, default="/home/imnyj/Workspace/paper4/coder/results/eval")
    parser.add_argument("--densities", type=float, nargs="+", default=DEFAULT_DENSITIES)
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument("--n-steps", type=int, default=100)
    parser.add_argument("--models", type=str, nargs="+", default=None)
    args = parser.parse_args()

    df_raw, df_summary, df_leaderboard = run_full_benchmark(
        models=args.models,
        densities=args.densities,
        seeds=args.seeds,
        hparams_csv=args.hparams_csv,
        output_dir=args.output_dir,
        n_steps=args.n_steps,
    )

    print("\n" + "=" * 80)
    print("🏆 IEEE TWC EVALUATION LEADERBOARD (Composite Ranking)")
    print("=" * 80)
    print(
        df_leaderboard[
            [
                "rank",
                "model_name",
                "category",
                "mean_aoi",
                "peak_aoi",
                "packet_loss_rate",
                "mean_error",
                "avg_tx_power_dbm",
                "composite_score",
            ]
        ].to_string(index=False)
    )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
