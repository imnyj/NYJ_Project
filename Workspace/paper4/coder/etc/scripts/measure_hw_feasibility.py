"""Measure whether Act and Rest can share one GPU without hurting inference latency.

The design (idea/scenario.md) requires that background training must not degrade the
serving path, and that inference must stay short. The trainer places Act and Rest on
separate GPUs when two are visible, but an RSU deployment realistically has one
accelerator, so the question is whether the shared-GPU configuration still meets the
requirement. This runs the same model under both placements and compares the
inference latency distribution the trainer already records.

Usage: measure_hw_feasibility.py [model_name] [steps]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import torch  # noqa: E402

from src.baselines import get_baseline  # noqa: E402
from src.hot_swap_trainer import run_hot_swap_training  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "TD3"
STEPS = int(sys.argv[2]) if len(sys.argv) > 2 else 600
OUT = "/home/imnyj/Workspace/paper4/coder/results/hw_feasibility.json"


def run(tag: str, act: str, rest: str) -> dict:
    print(f"\n--- {tag}: act={act} rest={rest} ---")
    summary = run_hot_swap_training(
        model_name=get_baseline(MODEL),
        total_steps=STEPS,
        episodes=1,
        seed=42,
        act_device=act,
        rest_device=rest,
        checkpoint_dir="/home/imnyj/Workspace/paper4/coder/etc/temp/hwfeas_ckpt",
        tensorboard_dir="/home/imnyj/Workspace/paper4/coder/etc/temp/hwfeas_tb",
        log_csv_path=f"/home/imnyj/Workspace/paper4/coder/etc/temp/hwfeas_{tag}.csv",
    )
    lat = summary.get("inference_latency", {})
    print(f"  training_steps      : {summary.get('training_steps')}")
    print(f"  throughput steps/s  : {summary.get('throughput_steps_per_sec')}")
    print(f"  inference mean (ms) : {lat.get('mean_latency_ms')}")
    print(f"  inference p50 (ms)  : {lat.get('p50_latency_ms')}")
    print(f"  inference p95 (ms)  : {lat.get('p95_latency_ms')}")
    print(f"  inference p99 (ms)  : {lat.get('p99_latency_ms')}")
    return {
        "tag": tag, "act_device": act, "rest_device": rest,
        "training_steps": summary.get("training_steps"),
        "throughput_steps_per_sec": summary.get("throughput_steps_per_sec"),
        "swap_count": summary.get("swap_count"),
        "inference_latency": lat,
    }


def main() -> int:
    n_gpu = torch.cuda.device_count()
    print(f"model={MODEL} steps={STEPS} visible GPUs={n_gpu}")
    if n_gpu < 2:
        print("Need at least 2 visible GPUs to compare shared vs isolated. "
              "Run without restricting CUDA_VISIBLE_DEVICES.")
        return 2

    os.makedirs("/home/imnyj/Workspace/paper4/coder/etc/temp", exist_ok=True)
    results = [
        run("isolated", "cuda:0", "cuda:1"),
        run("shared", "cuda:0", "cuda:0"),
    ]

    iso, sha = results[0]["inference_latency"], results[1]["inference_latency"]
    print("\n" + "=" * 64)
    print(f"{'metric':>14} {'isolated':>12} {'shared':>12} {'delta':>12}")
    for key in ("mean_latency_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms"):
        a, b = iso.get(key), sha.get(key)
        if a is None or b is None:
            continue
        d = f"{(b - a):+.4f}" if a or b else "n/a"
        print(f"{key:>14} {a:>12.4f} {b:>12.4f} {d:>12}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"model": MODEL, "steps": STEPS, "runs": results}, fh, indent=2)
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
