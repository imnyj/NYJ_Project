#!/usr/bin/env python3
"""
run_training.py
===============
Training-only script for MAFAC and baseline algorithms.

Usage:
  python run_training.py --algorithm MAFAC --episodes 500
  python run_training.py --algorithm IQL --episodes 200 --num-vehicles 50
  python run_training.py --algorithm SAC-Single --episodes 300
"""

import sys
import argparse
import random
import numpy as np
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from training.trainer import Trainer

ALGORITHMS = ["MAFAC", "Centralized-AoI", "SAC-Single", "IQL", "NDN-LRU", "No-Cache"]


def main():
    parser = argparse.ArgumentParser(description="Run MAFAC training")
    parser.add_argument("--algorithm",     type=str, default="MAFAC",
                        choices=ALGORITHMS, help="Algorithm to train")
    parser.add_argument("--episodes",      type=int, default=500,
                        help="Number of training episodes")
    parser.add_argument("--num-vehicles",  type=int, default=50,
                        help="Number of vehicles")
    parser.add_argument("--cache-size",    type=int, default=50,
                        help="NDN cache size per node")
    parser.add_argument("--num-contents",  type=int, default=200,
                        help="Number of distinct content types")
    parser.add_argument("--zipf-alpha",    type=float, default=1.0,
                        help="Zipf exponent for content popularity")
    parser.add_argument("--rician-K",      type=float, default=7.0,
                        help="Rician K-factor (dB) for V2V channel")
    parser.add_argument("--content-update-rate", type=float, default=0.5,
                        help="Content update rate (Hz)")
    parser.add_argument("--episode-duration", type=float, default=300.0,
                        help="Episode duration (seconds)")
    parser.add_argument("--fed-interval",  type=int, default=10,
                        help="Federated round interval (episodes)")
    parser.add_argument("--seed",          type=int, default=42)
    parser.add_argument("--output-dir",    type=str,
                        default="home/nyj/0_paper/paper/data")
    parser.add_argument("--checkpoint-dir", type=str,
                        default="home/nyj/0_paper/simulation/checkpoints")
    parser.add_argument("--sumo-cfg",      type=str, default=None,
                        help="Path to SUMO .sumocfg file")
    parser.add_argument("--verbose",       action="store_true", default=True)
    args = parser.parse_args()

    # Reproducibility
    random.seed(args.seed)
    np.random.seed(args.seed)

    # Environment config
    env_config = {
        "num_vehicles":         args.num_vehicles,
        "cache_size":           args.cache_size,
        "num_contents":         args.num_contents,
        "zipf_alpha":           args.zipf_alpha,
        "rician_K_db":          args.rician_K,
        "content_update_rate":  args.content_update_rate,
        "episode_duration_s":   args.episode_duration,
        "headless":             True,
    }
    if args.sumo_cfg:
        env_config["sumo_cfg"] = args.sumo_cfg

    print(f"=" * 60)
    print(f"MAFAC Training: {args.algorithm}")
    print(f"  Episodes:       {args.episodes}")
    print(f"  Vehicles:       {args.num_vehicles}")
    print(f"  Cache size:     {args.cache_size}")
    print(f"  Contents:       {args.num_contents}")
    print(f"  Zipf alpha:     {args.zipf_alpha}")
    print(f"  Rician K:       {args.rician_K} dB")
    print(f"  Seed:           {args.seed}")
    print(f"  Output dir:     {args.output_dir}")
    print(f"=" * 60)

    trainer = Trainer(
        algorithm=args.algorithm,
        env_config=env_config,
        total_episodes=args.episodes,
        federated_round_interval=args.fed_interval,
        checkpoint_dir=args.checkpoint_dir,
        output_dir=args.output_dir,
        seed=args.seed,
        verbose=args.verbose,
    )

    metrics = trainer.train()

    # Print summary
    if metrics:
        last = metrics[-1]
        print(f"\nTraining complete!")
        print(f"  Final average AoI:   {last.get('average_aoi', 0):.3f} s")
        print(f"  Final cache hit:     {last.get('cache_hit_ratio', 0):.3f}")
        print(f"  Final TX success:    {last.get('tx_success_rate', 0):.3f}")
        print(f"  Final Lagrange λ:    {last.get('lagrange_lambda', 0):.4f}")


if __name__ == "__main__":
    main()
