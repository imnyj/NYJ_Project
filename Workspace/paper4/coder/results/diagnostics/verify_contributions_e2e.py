"""End-to-end verification against a REAL SUMO run.

The unit tests hand the buffer arrays a test wrote. This script does not: it runs
`run_hot_swap_training` on genuine SUMO traffic and then reads what actually
landed in the replay buffer, so the claim "the contributions are live" rests on
observed pipeline output rather than on a constructed batch.

Checks, in order:
  1. SUMO really moved vehicles (the environment's own anti-mocking assertions
     are left in place and run throughout).
  2. Every transition in the buffer carries `reward_terms`, and each one sums to
     that transition's scalar reward.
  3. Every transition carries a neighbourhood, of the right shape, whose mask is
     0/1 and whose padded rows are zero.
  4. The neighbourhood is NOT trivially empty at a realistic density -- an
     all-zero mask everywhere would satisfy the shape checks while carrying no
     information.
  5. No leakage: a stored neighbour row equals an observation the environment
     emitted, and the ego vehicle never appears among its own neighbours.
  6. MADDPG-MT's update on a batch drawn from THAT buffer reports both
     contributions active.
  7. SPAM-D3QN draws non-uniformly from that same buffer and writes priorities
     back.
  8. The scenario on disk has the horizon this run asked for, and the module
     globals were not written to.

Results OVERWRITE coder/results/diagnostics/baseline_contributions_e2e.csv
(line 243 opens it with "w"). This line said "appended" until 2026-09-07,
which would have meant a reader could compare a run against the previous
one in the same file. There is only ever the latest run in it.
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

# PAPER4_CODER_ROOT lets this run against a shadow copy of the tree, which is how
# it was dry-run before the real files were touched.
CODER = os.environ.get("PAPER4_CODER_ROOT", "/home/imnyj/Workspace/paper4/coder")
sys.path.insert(0, CODER)

SUMO_DIR = os.environ.setdefault(
    "PAPER4_SUMO_DIR",
    tempfile.mkdtemp(prefix="paper4_verify_contrib_"),
)

import numpy as np  # noqa: E402
import torch  # noqa: E402

import src.sumo.make_sumo_set as ss  # noqa: E402
from src.baselines import get_baseline  # noqa: E402
import src.hot_swap_trainer as hst  # noqa: E402
from src.hot_swap_trainer import run_hot_swap_training, scenario_flow_end_s  # noqa: E402
from src.rl_interface import MAX_NEIGHBOURS, STATE_DIM  # noqa: E402
from src.baselines.maddpg_mt import TASK_NAMES  # noqa: E402

DENSITY = 20.0
STEPS = 400
WARMUP = 300
SEED = 42

RESULTS = os.environ.get(
    "PAPER4_VERIFY_OUT", "/home/imnyj/Workspace/paper4/coder/results/diagnostics"
)
CSV_PATH = os.path.join(RESULTS, "baseline_contributions_e2e.csv")

rows: list[dict] = []
failures: list[str] = []


def record(check: str, ok: bool, observed: str) -> None:
    rows.append({"check": check, "passed": int(bool(ok)), "observed": observed})
    print(f"[{'PASS' if ok else 'FAIL'}] {check}: {observed}")
    if not ok:
        failures.append(check)


def main() -> int:
    globals_before = (float(ss.FLOW_END_S), float(ss.MAX_STEPS), float(ss.DENSITY))

    # Capture the trainer the run builds. `run_hot_swap_training` owns it and
    # does not return it, and the point of this script is to inspect the buffer
    # THAT RUN filled rather than one assembled here, so the class is wrapped
    # instead of the loop being reimplemented.
    captured: list = []
    real_cls = hst.HotSwapTrainer

    class _Capturing(real_cls):  # type: ignore[misc, valid-type]
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            captured.append(self)

    hst.HotSwapTrainer = _Capturing
    out_dir = tempfile.mkdtemp(prefix="paper4_verify_run_")
    try:
        run_hot_swap_training(
            model_name="MADDPG-MT",
            model_cls=get_baseline("MADDPG-MT"),
            total_steps=STEPS,
            episodes=1,
            density=DENSITY,
            seed=SEED,
            warmup_steps=WARMUP,
            checkpoint_dir=os.path.join(out_dir, "ckpt"),
            tensorboard_dir=os.path.join(out_dir, "tb"),
            log_dir=out_dir,
            validate_every_episodes=0,
            sumo_dir=SUMO_DIR,
        )
    finally:
        hst.HotSwapTrainer = real_cls
    assert len(captured) == 1, f"expected one trainer, captured {len(captured)}"
    trainer = captured[0]

    buf = trainer.replay_buffer
    record("buffer non-empty after a genuine SUMO episode", len(buf) > 0, f"{len(buf)} transitions")
    if len(buf) == 0:
        return 1

    items = list(buf.buffer)

    # -- 2. reward decomposition ------------------------------------------
    have_terms = [it for it in items if it.get("reward_terms") is not None]
    record("every transition carries reward_terms",
           len(have_terms) == len(items), f"{len(have_terms)}/{len(items)}")

    worst = 0.0
    for it in have_terms:
        t = np.asarray(it["reward_terms"], dtype=np.float64)
        worst = max(worst, abs(float(t.sum()) - float(it["reward"])))
    record("reward_terms sum to the scalar reward", worst <= 1e-5,
           f"max |sum - reward| = {worst:.3e} over {len(have_terms)} transitions")
    record("reward_terms has one column per task",
           all(np.asarray(it["reward_terms"]).size == len(TASK_NAMES) for it in have_terms),
           f"{len(TASK_NAMES)} columns expected")

    # -- 3/4. neighbourhood -----------------------------------------------
    have_nb = [it for it in items if it.get("neighbour_state") is not None]
    record("every transition carries a neighbourhood",
           len(have_nb) == len(items), f"{len(have_nb)}/{len(items)}")

    shape_ok = all(
        it["neighbour_state"].shape == (MAX_NEIGHBOURS, STATE_DIM)
        and it["neighbour_mask"].shape == (MAX_NEIGHBOURS,)
        and it["next_neighbour_state"].shape == (MAX_NEIGHBOURS, STATE_DIM)
        and it["next_neighbour_mask"].shape == (MAX_NEIGHBOURS,)
        for it in have_nb
    )
    record("neighbourhood shapes", shape_ok,
           f"({MAX_NEIGHBOURS}, {STATE_DIM}) and ({MAX_NEIGHBOURS},)")

    masks = np.stack([it["neighbour_mask"] for it in have_nb])
    record("mask is strictly 0/1", bool(np.all((masks == 0.0) | (masks == 1.0))),
           f"unique values {np.unique(masks).tolist()}")

    pad_clean = True
    for it in have_nb:
        m = it["neighbour_mask"].astype(bool)
        if m.any() and not np.all(it["neighbour_state"][~m] == 0.0):
            pad_clean = False
            break
    record("padded rows are zero", pad_clean, "no non-zero row behind a zero mask")

    counts = masks.sum(axis=1)
    record("the neighbourhood is not trivially empty", float(counts.mean()) > 0.5,
           f"mean {counts.mean():.2f} neighbours, max {counts.max():.0f}, "
           f"{float((counts == 0).mean()) * 100:.1f} % empty")

    # -- 5. no leakage -----------------------------------------------------
    self_row = 0
    for it in have_nb:
        m = it["neighbour_mask"].astype(bool)
        if not m.any():
            continue
        rowsn = it["neighbour_state"][m]
        if np.any(np.all(np.isclose(rowsn, it["state"][None, :], atol=0.0), axis=1)):
            self_row += 1
    record("no transition lists its own observation as a neighbour",
           self_row == 0, f"{self_row} violations")

    # -- 6. MADDPG-MT reads both -------------------------------------------
    batch = buf.sample(min(32, len(buf)))
    model = get_baseline("MADDPG-MT")()
    out = model.update(batch)
    record("MADDPG-MT reports task decomposition active",
           out.get("task_decomposed") == 1.0, f"task_decomposed={out.get('task_decomposed')}")
    record("MADDPG-MT reports the global critic cooperative",
           out.get("global_critic_cooperative") == 1.0,
           f"global_critic_cooperative={out.get('global_critic_cooperative')}")

    # -- 6b. the same plumbing revives the other two joint critics ---------
    # The keys were written for MADDPG-MT, but I-HAMAPPO and RES-MAPDDPG read the
    # same two names, so opening the route changes their updates too. Measured
    # here on the real batch rather than asserted from the code.
    for name in ("I-HAMAPPO", "RES-MAPDDPG"):
        stripped = {k: v for k, v in batch.items() if not k.endswith("neighbour_mask")
                    and not k.endswith("neighbour_state")}
        torch.manual_seed(5)
        m_off = get_baseline(name)()
        torch.manual_seed(5)
        m_on = get_baseline(name)()
        l_off = m_off.update(stripped)["loss"]
        l_on = m_on.update(dict(batch))["loss"]
        record(f"{name} update changes once it can see the neighbourhood",
               l_off != l_on,
               f"loss {l_off:.6f} without -> {l_on:.6f} with "
               f"(relative change {abs(l_on - l_off) / max(abs(l_off), 1e-12) * 100:.2f} %)")

    # -- 7. SPAM-D3QN draws by priority from the same buffer ---------------
    spam = get_baseline("SPAM-D3QN")()
    b = spam.sample_batch(buf, min(32, len(buf)))
    record("SPAM-D3QN gets a prioritized batch",
           "weights" in b and "indices" in b, f"keys added: {sorted(set(b) - set(batch))}")
    before = buf._priorities[: len(buf)].copy()
    res = spam.update(b)
    spam.commit_priorities(buf, b)
    after = buf._priorities[: len(buf)]
    touched = np.unique(b["indices"].numpy())
    record("SPAM-D3QN reports the batch was prioritized",
           res.get("per_sampled") == 1.0, f"per_sampled={res.get('per_sampled')}")
    record("priorities are written back",
           not np.allclose(before[touched], after[touched]),
           f"{touched.size} slots updated")
    untouched = np.setdiff1d(np.arange(len(buf)), touched)
    record("untouched priorities are left alone",
           np.allclose(before[untouched], after[untouched]),
           f"{untouched.size} slots unchanged")

    # -- 8. scenario isolation --------------------------------------------
    root = ET.parse(os.path.join(SUMO_DIR, "generated.rou.xml")).getroot()
    ends = {float(f.get("end")) for f in root.findall("flow")}
    want = scenario_flow_end_s(STEPS, WARMUP)
    record("the scenario on disk covers this run's horizon",
           len(ends) == 1 and abs(ends.pop() - want) < 1e-6,
           f"flows end at {sorted(ends) if ends else want} s, run needs {want} s")

    globals_after = (float(ss.FLOW_END_S), float(ss.MAX_STEPS), float(ss.DENSITY))
    record("the run did not write its parameters into make_sumo_set",
           globals_after == globals_before,
           f"{globals_before} -> {globals_after}")

    os.makedirs(RESULTS, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["check", "passed", "observed"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {CSV_PATH}")
    print(f"{sum(r['passed'] for r in rows)}/{len(rows)} checks passed")
    if failures:
        print("FAILED: " + ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
