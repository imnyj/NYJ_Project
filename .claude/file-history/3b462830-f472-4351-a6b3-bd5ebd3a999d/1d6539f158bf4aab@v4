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
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.baselines import ALL_BASELINES, get_baseline  # noqa: E402
from src.hot_swap_trainer import run_hot_swap_training  # noqa: E402

EPISODES = 100
STEPS_PER_EPISODE = 2000
TOTAL_STEPS = EPISODES * STEPS_PER_EPISODE  # 200,000


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="*", default=list(ALL_BASELINES),
                    help="subset of baselines to train (default: all nine)")
    ap.add_argument("--episodes", type=int, default=EPISODES)
    ap.add_argument("--steps-per-episode", type=int, default=STEPS_PER_EPISODE)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-resume", action="store_true",
                    help="start every model from scratch instead of the latest checkpoint")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    total_steps = args.episodes * args.steps_per_episode
    logging.info("Training %d model(s): %s", len(args.models), ", ".join(args.models))
    logging.info("Per model: %d episodes x %d steps = %d total env steps",
                 args.episodes, args.steps_per_episode, total_steps)

    failures = []
    for name in args.models:
        try:
            model_cls = get_baseline(name)
        except KeyError as exc:
            logging.error("%s", exc)
            failures.append((name, str(exc)))
            continue

        logging.info("=" * 70)
        logging.info("Starting training for %s (%s)", name, model_cls.__name__)
        try:
            summary = run_hot_swap_training(
                model_name=model_cls,
                total_steps=total_steps,
                episodes=args.episodes,
                seed=args.seed,
                resume=not args.no_resume,
            )
            logging.info("Finished %s | %s", name, summary)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed training %s: %s", name, exc, exc_info=True)
            failures.append((name, repr(exc)))

    logging.info("=" * 70)
    if failures:
        logging.error("%d/%d model(s) failed:", len(failures), len(args.models))
        for name, err in failures:
            logging.error("  %s: %s", name, err)
        return 1
    logging.info("All %d model(s) trained successfully.", len(args.models))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
