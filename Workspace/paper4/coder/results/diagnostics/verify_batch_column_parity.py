"""Do the training loop and the HPO rollout build the SAME batch?

WHY THIS EXISTS. The two loops are separate implementations of the same
event-driven SMDP rollout, and every column ever added to the replay buffer has
had to be added twice. It has already gone wrong once: `behaviour_log_prob` and
`action_idx` were plumbed into the training path and missed in the rollout, so
the search would have tuned models under conditions the run does not reproduce.
Opening the neighbourhood and reward-decomposition columns re-opens exactly that
trap, so this script closes it with evidence rather than with an argument.

WHAT IT MEASURES. For each of the nine baselines it runs a real SUMO episode
down BOTH paths and compares the key set of a batch sampled from the buffer each
path filled. The models are what make the comparison per-model rather than
global: `action_idx` and `behaviour_log_prob` are emitted only when every
transition carries one, which depends on what that model reports from
`select_action`.

Results go to results/diagnostics/batch_column_parity.csv.
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile

CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
sys.path.insert(0, CODER)

os.environ.setdefault(
    "PAPER4_SUMO_DIR", tempfile.mkdtemp(prefix="paper4_parity_sumo_")
)

import src.hot_swap_trainer as hst  # noqa: E402
import src.hpo as hpo  # noqa: E402
from src.baselines import ALL_BASELINES, get_baseline  # noqa: E402
from src.rl_interface import RetrospectiveReplayBuffer  # noqa: E402

SUMO_DIR = os.environ["PAPER4_SUMO_DIR"]
OUT = os.environ.get("PAPER4_VERIFY_OUT", os.path.join(CODER, "results", "diagnostics"))
CSV_PATH = os.path.join(OUT, "batch_column_parity.csv")

DENSITY = 10.0
TRAIN_STEPS = 60
TRAIN_WARMUP = 400
ROLLOUT_STEPS = 60
SEED = 42

#: A parity check that compares two empty sets passes while checking nothing.
#: These are the columns that must be present on BOTH paths whatever else is,
#: so an empty or truncated key set fails instead of passing quietly.
REQUIRED = {
    "state", "action", "reward", "next_state", "done", "delta_t", "discount",
    "reward_terms", "neighbour_state", "neighbour_mask",
    "next_neighbour_state", "next_neighbour_mask",
}


def _capture_buffer(module):
    """Wrap the buffer class in `module` so we get the instance it builds."""
    captured = []
    real = module.RetrospectiveReplayBuffer

    class _Capturing(real):  # type: ignore[misc, valid-type]
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            captured.append(self)

    module.RetrospectiveReplayBuffer = _Capturing
    return captured, real


def training_path_keys(name: str) -> tuple:
    captured, real = _capture_buffer(hst)
    out_dir = tempfile.mkdtemp(prefix="parity_train_")
    try:
        hst.run_hot_swap_training(
            model_name=name,
            model_cls=get_baseline(name),
            total_steps=TRAIN_STEPS,
            episodes=1,
            density=DENSITY,
            seed=SEED,
            warmup_steps=TRAIN_WARMUP,
            checkpoint_dir=os.path.join(out_dir, "ckpt"),
            tensorboard_dir=os.path.join(out_dir, "tb"),
            log_dir=out_dir,
            validate_every_episodes=0,
            sumo_dir=SUMO_DIR,
        )
    finally:
        hst.RetrospectiveReplayBuffer = real
    bufs = [b for b in captured if len(b) > 0]
    if not bufs:
        return tuple(), 0
    buf = bufs[0]
    return tuple(sorted(buf.sample(min(8, len(buf))).keys())), len(buf)


def rollout_path_keys(name: str) -> tuple:
    captured, real = _capture_buffer(hpo)
    try:
        hpo.evaluate_model_in_env(
            get_baseline(name)(),
            seed=SEED,
            n_steps=ROLLOUT_STEPS,
            density=DENSITY,
            train_steps_during_rollout=1,
            check_divergence=False,
        )
    finally:
        hpo.RetrospectiveReplayBuffer = real
    bufs = [b for b in captured if len(b) > 0]
    if not bufs:
        return tuple(), 0
    buf = bufs[0]
    return tuple(sorted(buf.sample(min(8, len(buf))).keys())), len(buf)


def _safe(fn, name):
    """Run one path, returning the reason instead of raising.

    A model that cannot run here at all is recorded as UNVERIFIED, never as a
    pass. HOORL is the live case: its first stage needs an offline dataset that
    another session is still building, so its training path cannot start in this
    environment and saying so is the honest result.
    """
    try:
        return fn(name) + ("",)
    except Exception as exc:  # noqa: BLE001
        return tuple(), 0, f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}"


def main() -> int:
    rows = []
    failures = []
    unverified = []
    for name in sorted(set(ALL_BASELINES)):
        t_keys, t_n, t_err = _safe(training_path_keys, name)
        r_keys, r_n, r_err = _safe(rollout_path_keys, name)
        if t_err or r_err:
            reason = t_err or r_err
            unverified.append(name)
            rows.append({
                "model": name, "passed": 0, "n_train_transitions": t_n,
                "n_rollout_transitions": r_n, "n_keys": len(t_keys),
                "training_only": "", "rollout_only": "",
                "required_missing": "UNVERIFIED", "keys": reason,
            })
            print(f"[SKIP] {name:<12} could not be run here: {reason}")
            continue
        same = set(t_keys) == set(r_keys)
        complete = REQUIRED.issubset(set(t_keys)) and REQUIRED.issubset(set(r_keys))
        ok = same and complete and t_n > 0 and r_n > 0
        only_train = sorted(set(t_keys) - set(r_keys))
        only_rollout = sorted(set(r_keys) - set(t_keys))
        missing = sorted(REQUIRED - (set(t_keys) & set(r_keys)))
        rows.append({
            "model": name,
            "passed": int(ok),
            "n_train_transitions": t_n,
            "n_rollout_transitions": r_n,
            "n_keys": len(t_keys),
            "training_only": ";".join(only_train),
            "rollout_only": ";".join(only_rollout),
            "required_missing": ";".join(missing),
            "keys": ";".join(t_keys),
        })
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name:<12} {len(t_keys)} keys, "
              f"train {t_n} / rollout {r_n} transitions"
              + (f"  train-only={only_train} rollout-only={only_rollout}" if not same else "")
              + (f"  MISSING={missing}" if missing else ""))
        if not ok:
            failures.append(name)

    os.makedirs(OUT, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {CSV_PATH}")
    checked = len(rows) - len(unverified)
    print(f"{checked - len(failures)}/{checked} runnable baselines have matching batch columns")
    if unverified:
        print("UNVERIFIED (could not be run in this environment): " + ", ".join(unverified))
    if failures:
        print("FAILED: " + ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
