"""What does a DISCARDED pretraining actually look like, measured?

`verify_hoorl_offline_wiring.py` check W2 decides whether a run's online stage
really started from the offline result, by comparing the weights snapshotted at
`finish_offline_phase()` against the weights the online stage went on to use. The
decision needs a threshold, and the threshold in the first draft of that script
was a guess. A guessed threshold is the whole failure mode W2 exists to catch,
one level up: a check that returns green because its number was chosen to let the
observed case through.

So both cases are constructed here and measured.

  PRESERVED  the model that was pretrained is the model that continues online.
             Its weights drift away from the handover snapshot only by however
             far the online updates move them.

  DISCARDED  the pretrained model is thrown away and a freshly initialised one
             runs online instead -- the failure where the offline loss curve
             looks healthy, `offline_pretrained` is set on an object nobody kept,
             and the online stage starts from noise.

The separation between the two, as a function of how many online updates have
happened by the time the comparison is made, is what sets the threshold. If the
two overlap at realistic update counts then W2 cannot work as designed and needs
a different comparison, which is a thing worth knowing BEFORE the wiring lands
rather than after.

WHICH TENSORS COUNT. Parameters only. The counter buffers (`total_updates`,
`offline_updates`, `offline_pretrained`) are excluded and measured separately,
because they are not weights and they wreck the statistic in both directions:
`total_updates` grows without bound as the online stage runs, so it reports a
huge drift even when the pretraining was perfectly preserved, and
`offline_updates` sits at 0 in the discarded case against several hundred in the
snapshot, so it reports a drift of exactly 1.0 for a reason that has nothing to
do with the weights. A metric dominated by counters would answer a different
question than the one asked.

No SUMO. Writes `results/diagnostics/hoorl_handover_drift_calibration.csv`.
"""
from __future__ import annotations

import csv
import math
import os
import sys
import tempfile
from typing import Any, Dict, List, Tuple

os.environ.setdefault(
    "PAPER4_SUMO_DIR", os.path.join(tempfile.gettempdir(), "hoorl_drift_calib_sumo")
)
os.makedirs(os.environ["PAPER4_SUMO_DIR"], exist_ok=True)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.baselines.hoorl import HOORL  # noqa: E402
from src.hoorl_offline import OfflineDataset  # noqa: E402
from src.rl_interface import ActionDecoder, STATE_DIM  # noqa: E402

RESULTS = os.path.join(ROOT, "results", "diagnostics", "hoorl_handover_drift_calibration.csv")

NUM_CHANNELS = 4
PRETRAIN_UPDATES = 300
ONLINE_UPDATE_COUNTS = (0, 25, 50, 100, 200, 500, 1000)

#: Buffers that are counters rather than weights. Excluded from the drift
#: statistic and reported on their own; see the module docstring.
COUNTER_BUFFERS = ("total_updates", "offline_updates", "offline_pretrained")


def make_arrays(n: int, seed: int) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    dec = ActionDecoder(num_channels=NUM_CHANNELS)
    deltas = np.exp(rng.uniform(math.log(dec.delta_min), math.log(dec.delta_max), size=n))
    chans = rng.integers(0, NUM_CHANNELS, size=n)
    powers = rng.uniform(dec.p_min, dec.p_max, size=n)
    return {
        "state": rng.normal(size=(n, STATE_DIM)).astype(np.float32),
        "action": np.stack(
            [dec.encode_action(float(deltas[i]), int(chans[i]), float(powers[i])) for i in range(n)]
        ).astype(np.float32),
        "reward": rng.normal(size=n).astype(np.float32),
        "next_state": rng.normal(size=(n, STATE_DIM)).astype(np.float32),
        "done": (rng.random(n) < 0.05).astype(np.float32),
        "delta_t": deltas.astype(np.float32),
        "action_idx": chans.astype(np.int64),
        "behaviour_log_prob": np.full(n, -math.log(NUM_CHANNELS), dtype=np.float32),
    }


def make_model(seed: int) -> HOORL:
    torch.manual_seed(seed)
    return HOORL(
        state_dim=STATE_DIM, num_channels=NUM_CHANNELS, hidden_dim=64,
        offline_algorithm="iql", phase="online",
    )


def snapshot(model: HOORL) -> Dict[str, torch.Tensor]:
    return {k: v.detach().to("cpu").clone() for k, v in model.state_dict().items()}


def drift(reference: Dict[str, torch.Tensor], other: Dict[str, torch.Tensor]) -> Tuple[float, str]:
    """Worst per-tensor relative drift over PARAMETERS, and which tensor it was."""
    worst, where = 0.0, "none"
    for key, tensor in reference.items():
        if key in COUNTER_BUFFERS:
            continue
        candidate = other.get(key)
        if not isinstance(candidate, torch.Tensor) or candidate.shape != tensor.shape:
            return float("inf"), f"{key} missing or misshapen"
        denom = float(tensor.abs().mean().item()) + 1e-8
        value = float((candidate - tensor).abs().mean().item()) / denom
        if value > worst:
            worst, where = value, key
    return worst, where


def run_online(model: HOORL, dataset: OfflineDataset, steps: int, seed: int) -> None:
    """Online updates fed from the same synthetic distribution.

    The batch source does not matter here. What is being calibrated is how far
    ordinary online gradient steps move the weights, not what they learn.
    """
    torch.manual_seed(seed)
    for _ in range(steps):
        model.update(dataset.sample(64))


def main() -> int:
    arrays = make_arrays(2048, seed=11)
    dataset = OfflineDataset(arrays, {"state_dim": STATE_DIM}, gamma=0.99)

    rows: List[Dict[str, Any]] = []
    print(f"Pretraining {PRETRAIN_UPDATES} offline updates, then measuring both cases.\n")

    for online_steps in ONLINE_UPDATE_COUNTS:
        # -- PRESERVED: the pretrained model continues online -------------------
        kept = make_model(seed=101)
        kept.pretrain(dataset, num_updates=PRETRAIN_UPDATES, batch_size=64)
        handover = snapshot(kept)
        run_online(kept, dataset, online_steps, seed=7)
        d_keep, where_keep = drift(handover, snapshot(kept))

        # -- DISCARDED: a fresh model runs online instead ------------------------
        fresh = make_model(seed=202)
        fresh.set_phase("online")
        run_online(fresh, dataset, online_steps, seed=7)
        d_drop, where_drop = drift(handover, snapshot(fresh))

        separation = d_drop / d_keep if d_keep > 0 else float("inf")
        rows.append({
            "online_updates": online_steps,
            "drift_preserved": round(d_keep, 6),
            "drift_discarded": round(d_drop, 6),
            "separation_ratio": round(separation, 3) if math.isfinite(separation) else "inf",
            "worst_tensor_preserved": where_keep,
            "worst_tensor_discarded": where_drop,
        })
        print(
            f"  online updates {online_steps:5d} | preserved {d_keep:.6f} "
            f"| discarded {d_drop:.6f} | ratio {separation:>9.1f}"
        )

    # The threshold has to sit above every preserved value and below every
    # discarded one. Report the room actually available rather than asserting a
    # number, so a reader can see whether the choice was forced or comfortable.
    max_keep = max(float(r["drift_preserved"]) for r in rows)
    min_drop = min(float(r["drift_discarded"]) for r in rows)
    print(f"\nworst PRESERVED drift  = {max_keep:.6f}")
    print(f"smallest DISCARDED drift = {min_drop:.6f}")
    if min_drop > max_keep:
        print(f"the two do not overlap; any threshold in ({max_keep:.6f}, {min_drop:.6f}) separates them")
        print(f"geometric midpoint = {math.sqrt(max_keep * min_drop):.6f}" if max_keep > 0 else "")
    else:
        print("THE TWO OVERLAP -- W2 cannot use this statistic as designed.")

    # And the counters, excluded above, reported so the exclusion is visible.
    kept = make_model(seed=101)
    kept.pretrain(dataset, num_updates=PRETRAIN_UPDATES, batch_size=64)
    handover = snapshot(kept)
    run_online(kept, dataset, 200, seed=7)
    after = snapshot(kept)
    print("\nCounter buffers, excluded from the statistic (this is why):")
    for key in COUNTER_BUFFERS:
        a, b = float(handover[key].item()), float(after[key].item())
        rel = abs(b - a) / (abs(a) + 1e-8)
        print(f"  {key:20s} handover={a:8.1f} after 200 online updates={b:8.1f} relative={rel:.3f}")
        rows.append({
            "online_updates": "counter_buffer",
            "drift_preserved": round(rel, 6),
            "drift_discarded": "",
            "separation_ratio": "",
            "worst_tensor_preserved": key,
            "worst_tensor_discarded": "",
        })

    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    with open(RESULTS, "w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "online_updates", "drift_preserved", "drift_discarded",
                "separation_ratio", "worst_tensor_preserved", "worst_tensor_discarded",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWritten to {RESULTS}")
    return 0 if min_drop > max_keep else 1


if __name__ == "__main__":
    raise SystemExit(main())
