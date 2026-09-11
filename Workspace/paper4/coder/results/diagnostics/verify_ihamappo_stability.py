"""Does opening the neighbourhood destabilise I-HAMAPPO?

WHY THIS MODEL SPECIFICALLY. I-HAMAPPO has a divergence history in this project:
its value loss reached 4.519e7 in an earlier run. It has no target critic and no
GAE, so its value estimate is a one-step TD residual with nothing damping it, and
the neighbourhood widens the critic's input. Two effects then arrive together and
have to be told apart:

  * SCALE. A wider critic input changes the magnitude of V(s) at initialisation,
    so the value loss starts at a different LEVEL. That is arithmetic, not
    instability, and comparing raw losses across the two arms would read it as
    one.
  * STABILITY. Whether the loss GROWS over updates. This is scale-free: the
    trajectory is divided by its own first-window mean, so a model that starts
    ten times higher but stays flat is stable and a model that starts low and
    climbs is not.

CONTROLS. Both arms use the same gamma, the same seed, the same initial weights
and the SAME transitions -- one arm simply has the neighbourhood columns removed
from the batch. Nothing else differs, so any difference is attributable.

The verdict column is not this script's opinion. It is `DivergenceMonitor` from
src/divergence_guard.py, the same rule the training runs abort on and the same
rule the scheduled report re-judges finished runs with.

Results go to results/diagnostics/ihamappo_neighbourhood_stability.csv.
"""
from __future__ import annotations

import csv
import os
import statistics
import sys
import tempfile

CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
sys.path.insert(0, CODER)
os.environ.setdefault("PAPER4_SUMO_DIR", tempfile.mkdtemp(prefix="paper4_ihamappo_"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

import src.hot_swap_trainer as hst  # noqa: E402
from src.baselines import get_baseline  # noqa: E402
from src.divergence_guard import DivergenceMonitor  # noqa: E402

SUMO_DIR = os.environ["PAPER4_SUMO_DIR"]
OUT = os.environ.get("PAPER4_VERIFY_OUT", os.path.join(CODER, "results", "diagnostics"))
CSV_PATH = os.path.join(OUT, "ihamappo_neighbourhood_stability.csv")

#: Fixed across both arms. 0.99 is the model default and also the current search
#: ceiling GAMMA_SEARCH_HIGH, so this is the most aggressive discount the search
#: can now choose -- the worst case under the present configuration. The 4.519e7
#: episode ran at 0.9986, which the ceiling no longer permits.
GAMMA = 0.99
SEED = 42
DENSITY = 20.0
STEPS = 400
WARMUP = 300
N_UPDATES = 200
BATCH = 32

NEIGHBOUR_KEYS = (
    "neighbour_state", "neighbour_mask",
    "next_neighbour_state", "next_neighbour_mask",
)


def collect_buffer():
    """One real SUMO episode. Both arms are trained on transitions from it."""
    captured = []
    real = hst.HotSwapTrainer

    class _Capturing(real):  # type: ignore[misc, valid-type]
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            captured.append(self)

    hst.HotSwapTrainer = _Capturing
    out_dir = tempfile.mkdtemp(prefix="ihamappo_collect_")
    try:
        hst.run_hot_swap_training(
            model_name="I-HAMAPPO",
            model_cls=get_baseline("I-HAMAPPO"),
            total_steps=STEPS, episodes=1, density=DENSITY, seed=SEED,
            warmup_steps=WARMUP,
            checkpoint_dir=os.path.join(out_dir, "ckpt"),
            tensorboard_dir=os.path.join(out_dir, "tb"),
            log_dir=out_dir, validate_every_episodes=0, sumo_dir=SUMO_DIR,
        )
    finally:
        hst.HotSwapTrainer = real
    return captured[0].replay_buffer


def run_arm(buffer, *, with_neighbours: bool):
    """Train one arm and report its loss trajectory."""
    torch.manual_seed(7)
    np.random.seed(7)
    model = get_baseline("I-HAMAPPO")(gamma=GAMMA)

    # The SAME transitions in both arms, drawn in the same order.
    np.random.seed(1234)
    batches = [buffer.sample(min(BATCH, len(buffer))) for _ in range(N_UPDATES)]

    value_losses, total_losses = [], []
    nonfinite = 0
    for b in batches:
        batch = dict(b)
        if not with_neighbours:
            for k in NEIGHBOUR_KEYS:
                batch.pop(k, None)
        out = model.update(batch)
        v, t = float(out["value_loss"]), float(out["loss"])
        if not (np.isfinite(v) and np.isfinite(t)):
            nonfinite += 1
        value_losses.append(v)
        total_losses.append(t)
    return value_losses, total_losses, nonfinite


def growth(series):
    """Last-quarter mean over first-quarter mean. Scale-free by construction."""
    q = max(1, len(series) // 4)
    first = statistics.fmean(series[:q])
    last = statistics.fmean(series[-q:])
    return last / first if abs(first) > 1e-12 else float("nan")


def verdict(series):
    """The project's own divergence rule, applied per pseudo-episode of 20 updates."""
    mon = DivergenceMonitor()
    chunk = 20
    for ep, start in enumerate(range(0, len(series), chunk), start=1):
        window = series[start:start + chunk]
        if not window:
            break
        v = mon.observe(episode=ep, mean_loss=statistics.fmean(window),
                        grad_updates_this_episode=len(window))
        if v is not None:
            return f"ABORT at pseudo-episode {ep}: {v.kind}"
    return "no abort"


def main() -> int:
    buffer = collect_buffer()
    print(f"collected {len(buffer)} transitions from one real SUMO episode "
          f"(density {DENSITY}, seed {SEED})\n")

    rows = []
    results = {}
    for label, flag in (("without_neighbourhood", False), ("with_neighbourhood", True)):
        v, t, nf = run_arm(buffer, with_neighbours=flag)
        results[label] = (v, t, nf)
        rows.append({
            "arm": label,
            "gamma": GAMMA,
            "seed": SEED,
            "n_updates": N_UPDATES,
            "value_loss_first": f"{v[0]:.6g}",
            "value_loss_mean": f"{statistics.fmean(v):.6g}",
            "value_loss_max": f"{max(v):.6g}",
            "value_loss_growth": f"{growth(v):.4f}",
            "total_loss_mean": f"{statistics.fmean(t):.6g}",
            "nonfinite_updates": nf,
            "divergence_verdict": verdict(t),
        })
        print(f"{label}")
        print(f"  value loss   first {v[0]:.6g}   mean {statistics.fmean(v):.6g}   max {max(v):.6g}")
        print(f"  growth (last quarter / first quarter)  {growth(v):.4f}")
        print(f"  non-finite updates  {nf}")
        print(f"  divergence rule  {verdict(t)}\n")

    v_off = results["without_neighbourhood"][0]
    v_on = results["with_neighbourhood"][0]
    scale = statistics.fmean(v_on) / statistics.fmean(v_off)
    g_off, g_on = growth(v_off), growth(v_on)
    print("INTERPRETATION")
    print(f"  scale     mean value loss changed by x{scale:.3f} -- this is the wider")
    print(f"            critic input, not instability")
    print(f"  stability growth {g_off:.4f} without -> {g_on:.4f} with; "
          f"a value above 1 means the loss is climbing")
    print(f"  the historical divergence reached 4.519e+07 at gamma 0.9986; "
          f"the max here is {max(max(v_off), max(v_on)):.6g} at gamma {GAMMA}")

    rows.append({
        "arm": "comparison", "gamma": GAMMA, "seed": SEED, "n_updates": N_UPDATES,
        "value_loss_first": "", "value_loss_mean": f"scale_ratio={scale:.4f}",
        "value_loss_max": "", "value_loss_growth": f"{g_off:.4f}->{g_on:.4f}",
        "total_loss_mean": "", "nonfinite_updates": "",
        "divergence_verdict": "growth above 1.0 means climbing",
    })

    os.makedirs(OUT, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
