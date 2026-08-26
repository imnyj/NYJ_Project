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

from src.baselines import (
    BASELINE_REGISTRY,
    BaseRLModel,
)
import src.Communications as comm
from src.heuristic_scheduler import HeuristicScheduler
from src.hot_swap_trainer import AoiV2IEnv
from src.rl_interface import StateVectorizer

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EvaluateHarness")

# Canonical 10 evaluated models
CANONICAL_EVAL_MODELS = [
    "HeuristicScheduler",
    "HybridPPO",
    "HybridSAC",
    "HybridTD3",
    "MAPPO",
    "HyARPPO",
    "MPDQN",
    "PureAoI",
    "DuelingQAoI",
    "SACAoI",
]

MODEL_CATEGORIES = {
    "HeuristicScheduler": "Category 0 (Heuristic)",
    "Heuristic": "Category 0 (Heuristic)",
    "Heuristic-Dynamic": "Category 0 (Heuristic)",
    "HybridPPO": "Category 1 (Basic)",
    "HybridSAC": "Category 1 (Basic)",
    "HybridTD3": "Category 1 (Basic)",
    "MAPPO": "Category 2 (Latest)",
    "HyARPPO": "Category 2 (Latest)",
    "MPDQN": "Category 2 (Latest)",
    "PureAoI": "Category 3 (SOTA AoI)",
    "DuelingQAoI": "Category 3 (SOTA AoI)",
    "SACAoI": "Category 3 (SOTA AoI)",
}

DEFAULT_DENSITIES = [15.0, 25.0, 35.0, 45.0, 55.0]
DEFAULT_SEEDS = [42, 101, 2024, 777, 999]


def normalize_model_name(name: str) -> str:
    """Resolve aliases to canonical model name."""
    clean = name.replace("-", "").replace("_", "").lower()
    if clean in ["heuristicscheduler", "heuristic", "heuristicdynamic", "s25heuristic", "rulebased"]:
        return "HeuristicScheduler"
    if clean in ["hybridppo", "hppo", "ppo"]:
        return "HybridPPO"
    if clean in ["hybridsac", "hsac", "sac"]:
        return "HybridSAC"
    if clean in ["hybridtd3", "htd3", "td3"]:
        return "HybridTD3"
    if clean in ["mappo"]:
        return "MAPPO"
    if clean in ["hyarppo", "hyar"]:
        return "HyARPPO"
    if clean in ["mpdqn", "pdqn"]:
        return "MPDQN"
    if clean in ["pureaoi", "whittle"]:
        return "PureAoI"
    if clean in ["duelingqaoi", "duelingq"]:
        return "DuelingQAoI"
    if clean in ["sacaoi"]:
        return "SACAoI"
    return name


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
    model_name: str,
    hparams: Optional[Dict[str, Any]] = None,
    state_dim: int = 16,
    num_channels: int = 4,
) -> Union[BaseRLModel, HeuristicScheduler]:
    """
    Instantiates an evaluated model (either HeuristicScheduler or one of the 9 Baseline RL models)
    with specified or optimal hyperparameters.
    """
    canonical_name = normalize_model_name(model_name)
    params = dict(hparams) if hparams is not None else {}

    if canonical_name == "HeuristicScheduler":
        return HeuristicScheduler(
            delta_min=params.get("delta_min", 0.5),
            delta_max=params.get("delta_max", 10.0),
            delta_cruise_steady=params.get("delta_cruise_steady", 3.5),
            delta_cruise_accel=params.get("delta_cruise_accel", 1.5),
            p_high=params.get("p_high", 25.0),
            p_mid=params.get("p_mid", 25.0),
            p_low=params.get("p_low", 20.0),
            num_subchannels=num_channels,
        )

    if canonical_name not in BASELINE_REGISTRY:
        raise ValueError(
            f"Unknown model name '{model_name}'. Available: {list(BASELINE_REGISTRY.keys())} + HeuristicScheduler"
        )

    model_cls = BASELINE_REGISTRY[canonical_name]
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
    model: Union[BaseRLModel, HeuristicScheduler],
    density: float,
    seed: int,
    n_steps: int = 100,
    dt: float = 1.0,
    rsu_pos: Tuple[float, float] = (0.0, 0.0),
    rsu_range: float = 800.0,
) -> Dict[str, Any]:
    """
    Executes a single benchmark evaluation run on the genuine SUMO AoiV2IEnv.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    env = AoiV2IEnv(
        density=density,
        seed=seed,
        max_steps=n_steps,
        rsu_range=rsu_range,
        warmup_steps=35,
    )
    obs, info = env.reset()

    for step in range(n_steps):
        action_dict = {}
        for vid, s_vec in obs.items():
            if isinstance(model, HeuristicScheduler):
                st_dict = {
                    "vid": vid,
                    "pos": env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0)),
                    "speed": 10.0,
                    "dist_to_rsu": math.hypot(
                        env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))[0] - env.target_rsu_pos[0],
                        env.vehicle_tracks.get(vid, {}).get("pos", (0.0, 0.0))[1] - env.target_rsu_pos[1],
                    ),
                    "current_time": env.sim_time,
                }
                grant = model.decide_grant(vid, st_dict)
            else:
                with torch.no_grad():
                    grant, _, _ = model.select_action(s_vec, deterministic=True)
            action_dict[vid] = grant

        next_obs, rewards, terminateds, truncateds, step_info = env.step(action_dict)
        obs = next_obs

    metrics = env.get_metrics()
    env.close()

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
