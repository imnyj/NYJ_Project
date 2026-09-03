#!/usr/bin/env python3
"""Pick the GPUs this training run may use, leaving other people's work alone.

The workstation is shared. Hard-coding `CUDA_VISIBLE_DEVICES=0,1,2,3` is what a
single-user script does, and on a shared box it either fights someone else for
memory or fails outright once they start. This reads the live state instead and
returns only the devices that are genuinely idle enough to take.

Selection rule, per GPU:
  * at least MIN_FREE_MIB free, so a run cannot OOM someone else out, and
  * at most MAX_UTIL_PCT utilisation, so a device that is busy but not yet
    memory-hungry is still treated as taken.

Both directions matter. Memory alone would let us pile onto a GPU running a
small-but-saturating job; utilisation alone would let us start next to a job
that has reserved most of the memory and is merely between steps.

Usage:
    python gpu_alloc.py            # prints comma-separated indices, e.g. "0,1,3"
    python gpu_alloc.py --json     # prints the full per-GPU decision as JSON
    python gpu_alloc.py --need 2   # exits non-zero unless at least 2 are free
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any, Dict, List

# A 200k-step run of the widest baseline (TD3, ~773k parameters) peaks well under
# 2 GiB, so 8 GiB is generous. The margin is deliberate: it is the room a
# colleague needs to start something ordinary next to us without being evicted.
MIN_FREE_MIB = 8192

# Above this the device is somebody's, even if memory looks available.
MAX_UTIL_PCT = 30

QUERY = "index,memory.total,memory.used,memory.free,utilization.gpu"


def probe() -> List[Dict[str, Any]]:
    """Read the live per-GPU state. Returns [] when no NVIDIA driver is present."""
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []

    gpus: List[Dict[str, Any]] = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 5:
            continue
        try:
            idx, total, used, free, util = (int(float(p)) for p in parts)
        except ValueError:
            continue
        gpus.append({
            "index": idx,
            "memory_total_mib": total,
            "memory_used_mib": used,
            "memory_free_mib": free,
            "utilization_pct": util,
            "free_enough": free >= MIN_FREE_MIB,
            "idle_enough": util <= MAX_UTIL_PCT,
        })
    for g in gpus:
        g["usable"] = bool(g["free_enough"] and g["idle_enough"])
        if g["usable"]:
            g["reason"] = "idle"
        elif not g["free_enough"]:
            g["reason"] = f"only {g['memory_free_mib']} MiB free (< {MIN_FREE_MIB})"
        else:
            g["reason"] = f"{g['utilization_pct']}% utilised (> {MAX_UTIL_PCT})"
    return gpus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="print the full decision as JSON")
    ap.add_argument("--need", type=int, default=1,
                    help="exit non-zero unless at least this many GPUs are usable")
    args = ap.parse_args()

    gpus = probe()
    usable = [g["index"] for g in gpus if g["usable"]]

    if args.json:
        print(json.dumps({"gpus": gpus, "usable": usable,
                          "min_free_mib": MIN_FREE_MIB,
                          "max_util_pct": MAX_UTIL_PCT}, indent=2))
    else:
        print(",".join(str(i) for i in usable))

    if len(usable) < args.need:
        print(f"gpu_alloc: need {args.need} usable GPU(s), found {len(usable)}",
              file=sys.stderr)
        for g in gpus:
            if not g["usable"]:
                print(f"  GPU {g['index']}: {g['reason']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
