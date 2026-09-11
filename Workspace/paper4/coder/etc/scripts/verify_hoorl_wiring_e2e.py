#!/usr/bin/env python3
# etc/scripts/verify_hoorl_wiring_e2e.py
# ============================================================================
# Does the offline stage run when the REAL entry points are called?
#
# `verify_hoorl_wiring.py` checks the helper. This checks the two call sites
# that actually run: `run_hot_swap_training` and `evaluate_trial_multiseed`.
# Both drive the genuine SUMO environment, so a pass here means the offline
# stage runs inside the pipeline rather than inside a test harness.
#
# The dataset is SYNTHETIC, written to a scratch path and pointed at through
# PAPER4_HOORL_OFFLINE_DATASET. Collecting the real one is blocked until the
# observation definition settles; what is being checked here is control flow,
# which the contents of the batches do not affect. Its metadata carries the LIVE
# observation constants, because otherwise `verify_compatibility` would reject it
# and the run would fail for a reason unrelated to the wiring.
#
# The decisive check is the last one: a HOORL run with NO dataset must stop,
# because that is precisely the state the pipeline was in -- silently online-only
# while reporting under the method's name.
# ============================================================================

from __future__ import annotations

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.baselines import get_baseline  # noqa: E402
from src.hoorl_offline import OfflineDataset, observation_constants  # noqa: E402
from src.hoorl_wiring import DATASET_ENV_VAR, DEFAULT_OFFLINE_ALGORITHM  # noqa: E402
from src.rl_interface import STATE_DIM, ActionDecoder  # noqa: E402

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append({"check": name, "pass": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""),
          flush=True)
    return ok


def write_synthetic_dataset(path, n=3000, seed=0):
    rng = np.random.default_rng(seed)
    dec = ActionDecoder(num_channels=4)
    deltas = np.exp(rng.uniform(np.log(dec.delta_min), np.log(dec.delta_max), n))
    chans = rng.integers(0, 4, n)
    powers = rng.uniform(dec.p_min, dec.p_max, n)
    actions = np.stack([dec.encode_action(float(d), int(c), float(p))
                        for d, c, p in zip(deltas, chans, powers)]).astype(np.float32)
    arrays = {
        "state": rng.uniform(-1, 1, (n, STATE_DIM)).astype(np.float32),
        "action": actions,
        "reward": rng.normal(-1.0, 0.5, n).astype(np.float32),
        "next_state": rng.uniform(-1, 1, (n, STATE_DIM)).astype(np.float32),
        "done": (rng.random(n) < 0.02).astype(np.float32),
        "delta_t": deltas.astype(np.float32),
        "action_idx": chans.astype(np.int64),
        "behaviour_log_prob": np.full(n, -np.log(4.0), dtype=np.float32),
    }
    # The live constants, so the compatibility gate passes for the right reason.
    meta = {
        "state_dim": STATE_DIM,
        "observation_constants": observation_constants(),
        "synthetic": True,
        "note": "wiring verification only; NOT a collected dataset",
    }
    return OfflineDataset(arrays, meta).save(path)


def main() -> int:
    scratch = tempfile.mkdtemp(prefix="hoorl_e2e_")
    sumo_dir = os.path.join(scratch, "sumo")
    os.makedirs(sumo_dir, exist_ok=True)
    npz_path = os.path.join(scratch, "offline.npz")

    from src.hot_swap_trainer import prepare_scenario, run_hot_swap_training

    # The scenario has to be written BEFORE the dataset's metadata is, and with
    # the parameters the training run below will use. `V_MAX_OBS` and `E_REF` are
    # read off the generated network, so a dataset whose metadata was captured
    # against a different one is correctly rejected by `verify_compatibility`.
    # Writing it here is not a workaround for that gate: it is the condition the
    # real collection has to satisfy too, and this script proved the gate fires
    # by tripping it first.
    # There used to be a SECOND, earlier call to `write_synthetic_dataset` above
    # the import, before any scenario existed. Its output was overwritten one
    # line later so it changed nothing, and as of 2026-09-06 it raises:
    # `observation_constants` now refuses to report the import-time fallbacks
    # rather than let a file claim a normalisation nothing was ever built with.
    # Writing once, here, is what the comment above always described.
    prepare_scenario(density=10.0, max_steps=120, warmup_steps=300, seed=4242,
                     sumo_dir=sumo_dir)
    write_synthetic_dataset(npz_path)
    print(f"synthetic dataset at {npz_path}\n")

    # ---- 1. the training entry point ---------------------------------------
    os.environ[DATASET_ENV_VAR] = npz_path
    summary = run_hot_swap_training(
        model_name="HOORL", model_cls=get_baseline("HOORL"),
        total_steps=120, episodes=1, density=10.0, batch_size=16,
        warmup_steps=300, seed=4242, sumo_dir=sumo_dir,
        checkpoint_dir=os.path.join(scratch, "ckpt"),
        tensorboard_dir=os.path.join(scratch, "tb"),
        log_dir=os.path.join(scratch, "logs"),
        validate_every_episodes=0,
        offline_pretrain_updates=60, offline_pretrain_batch_size=64,
        hparams={"hidden_dim": 64},
    )
    off = summary.get("offline_stage")
    record("run_hot_swap_training entered the offline stage",
           bool(off) and off.get("offline_stage_ran") is True
           and float(off.get("offline_updates", 0)) == 60.0,
           json.dumps({k: off.get(k) for k in
                       ("offline_stage_ran", "offline_algorithm", "offline_updates",
                        "n_transitions", "wall_clock_s")} if off else None))
    record("the training summary records the offline stage",
           "offline_stage" in summary and summary["offline_stage"] is not None)

    # The checkpoint must carry the flag, or a later evaluation cannot tell a
    # pretrained policy from one that started online.
    ckpts = []
    for dirpath, _d, files in os.walk(os.path.join(scratch, "ckpt")):
        ckpts.extend(os.path.join(dirpath, f) for f in files if f.endswith(".pt"))
    flagged = None
    if ckpts:
        blob = torch.load(sorted(ckpts)[0], map_location="cpu", weights_only=False)
        sd = blob.get("model_state_dict", blob) if isinstance(blob, dict) else {}
        if "offline_pretrained" in sd:
            flagged = float(np.asarray(sd["offline_pretrained"]).reshape(-1)[0])
    record("the checkpoint records that the policy was pretrained",
           flagged == 1.0, f"offline_pretrained={flagged} in {len(ckpts)} checkpoint(s)")

    # ---- 2. the search entry point -----------------------------------------
    from src.hpo import evaluate_trial_multiseed
    score, extra = evaluate_trial_multiseed(
        model_cls=get_baseline("HOORL"),
        hparams={"hidden_dim": 64},
        seeds=[4243], n_steps=60, density=10.0, check_divergence=False,
    )
    ran = extra.get("n_failed_seeds", 0) == 0
    record("evaluate_trial_multiseed completed a HOORL trial with the wiring in place",
           ran and np.isfinite(score), f"score={score:.4f}, failed_seeds={extra.get('n_failed_seeds')}")

    # ---- 3. and a run WITHOUT a dataset stops -------------------------------
    os.environ.pop(DATASET_ENV_VAR, None)
    stopped = ""
    try:
        run_hot_swap_training(
            model_name="HOORL", model_cls=get_baseline("HOORL"),
            total_steps=60, episodes=1, density=10.0, batch_size=16,
            warmup_steps=300, seed=4244, sumo_dir=sumo_dir,
            checkpoint_dir=os.path.join(scratch, "ckpt2"),
            tensorboard_dir=os.path.join(scratch, "tb2"),
            log_dir=os.path.join(scratch, "logs2"),
            validate_every_episodes=0, hparams={"hidden_dim": 64},
        )
    except Exception as exc:  # noqa: BLE001 - the type is the evidence
        stopped = type(exc).__name__
    record("a HOORL run with no dataset STOPS instead of running online-only",
           stopped == "OfflineDatasetMissing", stopped or "it ran anyway")

    # ---- 4. the other eight baselines are unaffected ------------------------
    s2 = run_hot_swap_training(
        model_name="SPAM-D3QN", model_cls=get_baseline("SPAM-D3QN"),
        total_steps=60, episodes=1, density=10.0, batch_size=16,
        warmup_steps=300, seed=4245, sumo_dir=sumo_dir,
        checkpoint_dir=os.path.join(scratch, "ckpt3"),
        tensorboard_dir=os.path.join(scratch, "tb3"),
        log_dir=os.path.join(scratch, "logs3"),
        validate_every_episodes=0, hparams={"hidden_dim": 64},
    )
    record("a single-stage baseline runs unchanged and with no dataset",
           s2.get("offline_stage") is None,
           f"offline_stage={s2.get('offline_stage')}")

    out = os.path.join(ROOT, "results", "hoorl_offline", "wiring_e2e.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump({"checks": RESULTS,
                   "n_pass": sum(r["pass"] for r in RESULTS),
                   "n_total": len(RESULTS),
                   "dataset": "SYNTHETIC; wiring verification only"}, fh, indent=2)
    failed = [r["check"] for r in RESULTS if not r["pass"]]
    print(f"\n{sum(r['pass'] for r in RESULTS)}/{len(RESULTS)} checks passed. wrote {out}")
    if failed:
        print("FAILED:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
