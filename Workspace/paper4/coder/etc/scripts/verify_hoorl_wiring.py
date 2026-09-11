#!/usr/bin/env python3
# etc/scripts/verify_hoorl_wiring.py
# ============================================================================
# Evidence that HOORL's offline stage actually RUNS, not that code exists to run
# it. The distinction is the whole point: before this wiring, every piece of the
# offline stage was implemented and none of it was ever entered, and nothing in
# the pipeline's output showed that.
#
# The dataset here is SYNTHETIC and deliberately so. Collecting the real one is
# blocked until the observation definition settles, and the questions asked below
# are about control flow and parameter movement, which a synthetic dataset
# answers exactly as well. No number produced here describes HOORL's performance
# and none may be reported as such.
#
# Four claims, each of which failed silently in some earlier form:
#
#   1. the offline stage is entered at all         -> offline_updates > 0
#   2. it changed the policy                       -> actor weights moved
#   3. the online stage inherited that policy      -> weights after the first
#                                                     online step are a
#                                                     CONTINUATION of the
#                                                     pretrained ones, not a
#                                                     fresh initialisation
#   4. offline_lr_scale means something            -> it changes the offline
#                                                     rate WITHOUT changing the
#                                                     online one, so no single
#                                                     learning rate reproduces it
# ============================================================================

from __future__ import annotations

import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402
import torch  # noqa: E402

from src.baselines import get_baseline  # noqa: E402
from src.hoorl_offline import ARRAY_KEYS, OfflineDataset  # noqa: E402
from src.hoorl_wiring import (  # noqa: E402
    DEFAULT_OFFLINE_ALGORITHM,
    OfflineDatasetMissing,
    is_hoorl,
    offline_hparams,
    pretrain_hoorl,
    wire_and_pretrain,
)
from src.rl_interface import STATE_DIM, ActionDecoder  # noqa: E402

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append({"check": name, "pass": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def synthetic_dataset(n=4000, seed=0, gamma=0.99):
    """A dataset with the right columns and plausible ranges. Not real data."""
    rng = np.random.default_rng(seed)
    dec = ActionDecoder(num_channels=4)
    deltas = np.exp(rng.uniform(np.log(dec.delta_min), np.log(dec.delta_max), n))
    chans = rng.integers(0, 4, n)
    powers = rng.uniform(dec.p_min, dec.p_max, n)
    actions = np.stack(
        [dec.encode_action(float(d), int(c), float(p))
         for d, c, p in zip(deltas, chans, powers)]
    ).astype(np.float32)
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
    meta = {"state_dim": STATE_DIM, "synthetic": True,
            "note": "wiring verification only; not a collected dataset"}
    return OfflineDataset(arrays, meta, gamma=gamma)


def actor_snapshot(model):
    return {k: v.detach().clone() for k, v in model.state_dict().items()
            if k.startswith(("actor_trunk", "mean_head", "log_std_head", "channel_head"))}


def max_abs_delta(a, b):
    return max(float((a[k] - b[k]).abs().max().item()) for k in a)


def main() -> int:
    HOORL = get_baseline("HOORL")
    torch.manual_seed(0)

    # ---- 0. the wiring helper recognises the model and injects the learner --
    record("HOORL is recognised as a two-stage model", is_hoorl(HOORL))
    other = get_baseline("SPAM-D3QN")
    record("a single-stage baseline is not", not is_hoorl(other))

    hp = offline_hparams(HOORL, {"hidden_dim": 64})
    record("offline_algorithm is injected for HOORL",
           hp.get("offline_algorithm") == DEFAULT_OFFLINE_ALGORITHM, json.dumps(hp))
    hp_other = offline_hparams(other, {"hidden_dim": 64})
    record("no key is injected for other baselines",
           "offline_algorithm" not in hp_other, json.dumps(hp_other))
    hp_explicit = offline_hparams(HOORL, {"offline_algorithm": None})
    record("an explicit caller choice is not overwritten",
           hp_explicit["offline_algorithm"] is None)

    # ---- 1. without the wiring the offline stage refuses to start -----------
    bare = HOORL(state_dim=STATE_DIM, num_channels=4, hidden_dim=64)
    ds = synthetic_dataset()
    try:
        bare.pretrain(ds, num_updates=1, batch_size=32)
        started = True
        err = ""
    except Exception as exc:  # noqa: BLE001 - the type is the evidence
        started = False
        err = f"{type(exc).__name__}"
    record("an unwired model refuses to pretrain rather than doing nothing",
           not started and err == "OfflineAlgorithmNotSelected", err)
    record("and its offline_updates stayed at zero",
           float(bare.offline_updates.item()) == 0.0,
           f"offline_updates={float(bare.offline_updates.item())}")

    # ---- 2. with the wiring it runs, and it MOVES the policy ----------------
    torch.manual_seed(0)
    model = HOORL(state_dim=STATE_DIM, num_channels=4, hidden_dim=64,
                  **{"offline_algorithm": DEFAULT_OFFLINE_ALGORITHM})
    before = actor_snapshot(model)
    summary = pretrain_hoorl(model, dataset=ds, num_updates=200, batch_size=128)
    after = actor_snapshot(model)

    record("the offline stage was entered",
           float(model.offline_updates.item()) == 200.0,
           f"offline_updates={float(model.offline_updates.item())}")
    moved = max_abs_delta(before, after)
    record("pretraining changed the policy weights", moved > 1e-6,
           f"max |dw| over the actor = {moved:.3e}")
    record("the handover was recorded on the model",
           float(model.offline_pretrained.item()) == 1.0 and model.phase == "online",
           f"offline_pretrained={float(model.offline_pretrained.item())}, phase={model.phase}")
    record("the summary reports the run, not a silent skip",
           summary and summary.get("offline_stage_ran") is True
           and summary.get("offline_updates") == 200.0,
           json.dumps({k: summary[k] for k in
                       ("offline_stage_ran", "offline_algorithm", "offline_updates",
                        "n_transitions", "wall_clock_s")}))

    # ---- 3. the online stage CONTINUES from the pretrained weights ----------
    # The test is not "did the weights change during the online step" -- they
    # would change from a fresh init too. It is whether the online step started
    # from the pretrained values. Compared against a model that never pretrained:
    # a continuation stays close to `after`, a restart does not.
    pretrained_ref = {k: v.clone() for k, v in after.items()}
    batch = ds.sample(128)
    model.online_update(batch)
    after_online = actor_snapshot(model)
    drift_from_pretrained = max_abs_delta(pretrained_ref, after_online)

    torch.manual_seed(0)
    fresh = HOORL(state_dim=STATE_DIM, num_channels=4, hidden_dim=64,
                  offline_algorithm=DEFAULT_OFFLINE_ALGORITHM)
    fresh.online_update(ds.sample(128))
    distance_to_fresh = max_abs_delta(actor_snapshot(fresh), after_online)
    record("the online stage continued from the pretrained weights",
           drift_from_pretrained < distance_to_fresh,
           f"one online step moved the policy by {drift_from_pretrained:.3e}, while "
           f"its distance to a never-pretrained model is {distance_to_fresh:.3e}")
    record("the online step did not reset the offline bookkeeping",
           float(model.offline_pretrained.item()) == 1.0
           and float(model.offline_updates.item()) == 200.0)

    # ---- 4. offline_lr_scale is not reproducible by one learning rate -------
    # Two configurations with the SAME offline rate and DIFFERENT online rates.
    # If a single learning rate could absorb the scale, these two would be
    # indistinguishable in both stages; they must agree offline and differ online.
    def rates(actor_lr, scale):
        m = HOORL(state_dim=STATE_DIM, num_channels=4, hidden_dim=64,
                  actor_lr=actor_lr, critic_lr=actor_lr, offline_lr_scale=scale,
                  offline_algorithm=DEFAULT_OFFLINE_ALGORITHM)
        m.set_phase("offline")
        off = m.actor_optimizer.param_groups[0]["lr"]
        m.set_phase("online")
        on = m.actor_optimizer.param_groups[0]["lr"]
        return off, on

    off_a, on_a = rates(3e-4, 2.0)
    off_b, on_b = rates(6e-4, 1.0)
    record("offline_lr_scale sets a stage RATIO no single rate reproduces",
           abs(off_a - off_b) < 1e-12 and abs(on_a - on_b) > 1e-9,
           f"(actor_lr=3e-4, scale=2) -> offline {off_a:.2e} / online {on_a:.2e}; "
           f"(actor_lr=6e-4, scale=1) -> offline {off_b:.2e} / online {on_b:.2e}")

    # ---- 5. a missing dataset is an error, not a silent online-only run -----
    torch.manual_seed(0)
    m2 = HOORL(state_dim=STATE_DIM, num_channels=4, hidden_dim=64,
               offline_algorithm=DEFAULT_OFFLINE_ALGORITHM)
    os.environ.pop("PAPER4_HOORL_OFFLINE_DATASET", None)
    try:
        pretrain_hoorl(m2, dataset_path=None, require_offline=True)
        raised = ""
    except OfflineDatasetMissing:
        raised = "OfflineDatasetMissing"
    except Exception as exc:  # noqa: BLE001
        raised = type(exc).__name__
    record("a missing dataset stops the run by default",
           raised == "OfflineDatasetMissing", raised or "nothing was raised")

    abl = pretrain_hoorl(m2, dataset_path=None, require_offline=False)
    record("the deliberate ablation is recorded rather than silent",
           abl is not None and abl["offline_stage_ran"] is False
           and float(m2.offline_pretrained.item()) == 0.0,
           json.dumps(abl))

    # ---- 6. non-HOORL models pass through untouched -------------------------
    d3qn = other(state_dim=STATE_DIM, num_channels=4)
    record("pretrain_hoorl is a no-op for other baselines",
           pretrain_hoorl(d3qn, dataset=ds) is None)

    # ---- 7. the one-call form both sites will use --------------------------
    torch.manual_seed(0)
    built, summ = wire_and_pretrain(
        HOORL, {"hidden_dim": 64},
        build=lambda hp: HOORL(state_dim=STATE_DIM, num_channels=4, **hp),
        dataset=ds, num_updates=50, batch_size=64,
    )
    record("wire_and_pretrain constructs AND pretrains in one call",
           built.offline_algorithm == DEFAULT_OFFLINE_ALGORITHM
           and float(built.offline_updates.item()) == 50.0
           and float(built.offline_pretrained.item()) == 1.0,
           f"offline_algorithm={built.offline_algorithm}, "
           f"offline_updates={float(built.offline_updates.item())}")

    out = os.path.join(ROOT, "results", "hoorl_offline", "wiring_verification.json")
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
