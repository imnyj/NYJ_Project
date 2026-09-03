#!/usr/bin/env python3
"""
scripts/run_hpo.py
==================
Auto Stock ML/RL Trader — Milestone 3: Optuna HPO CLI 실행 스크립트.

사용 예시:
    python scripts/run_hpo.py --n-trials 3 --symbol 005930 --output etc/hpo_results/baseline_hpo.csv --seed 42
"""

import argparse
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from modules.hpo.optuna_pipeline import run_hpo_optimization


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AutoStock Hybrid SL-RL Baseline Optuna HPO Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=3,
        help="Number of HPO trials to optimize",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="005930",
        help="Stock symbol to train and evaluate on",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="etc/hpo_results/baseline_hpo.csv",
        help="Output CSV file path to export trial results",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampler and environment reproducibility",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=200,
        help="Number of RL timesteps to train per trial",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Optional custom path to Parquet/CSV dataset",
    )
    parser.add_argument(
        "--fast-mode",
        action="store_true",
        default=True,
        help="Enable fast training mode with reduced epochs and batch size",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed logs during optimization",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"[AutoStock HPO CLI] Initiating HPO with {args.n_trials} trials for {args.symbol}...")

    study, best_trial = run_hpo_optimization(
        n_trials=args.n_trials,
        symbol=args.symbol,
        data_path=args.data_path,
        output_csv=args.output,
        seed=args.seed,
        n_timesteps=args.timesteps,
        fast_mode=args.fast_mode,
        verbose=not args.quiet,
    )

    print("\n" + "=" * 60)
    print("🏆 [AutoStock HPO] Optimization Successfully Finished!")
    print(f"Total Trials: {len(study.trials)}")
    print(f"Best Trial ID: {best_trial.number}")
    print(f"Best Objective Value: {best_trial.value:.6f}")
    print("Best Hyperparameters:")
    for param_name, param_val in best_trial.params.items():
        print(f"  • {param_name}: {param_val}")
    print(f"CSV Export: {os.path.abspath(args.output)}")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
