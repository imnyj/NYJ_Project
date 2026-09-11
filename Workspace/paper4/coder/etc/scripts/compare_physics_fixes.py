#!/usr/bin/env python
# etc/scripts/compare_physics_fixes.py
# ============================================================================
# THE FOUR PHYSICS FIXES, ONE AT A TIME, AGAINST ONE BASELINE.
#
# ---------------------------------------------------------------------------
# WHY SEPARATELY WHEN THEY WERE APPLIED TOGETHER
# ---------------------------------------------------------------------------
# Two of the four touch the same quantities. The shadowing correction changes how
# many retries a burst needs, which changes delivery, airtime and occupancy; the
# `CBR_REF` recalculation changes the congestion term, which reads occupancy. A
# single before/after run cannot say which of them moved a number. They were
# applied together because each requires the offline dataset to be recollected
# and one recollection is enough for all four -- that is an argument about cost,
# not about attribution.
#
# So each fix is reverted ALONE, on top of the fixed code, and compared against
# the same baseline with the same seed and scenario.
#
# ---------------------------------------------------------------------------
# WHAT EACH REVERSION IS, AND HOW FAITHFUL IT IS
# ---------------------------------------------------------------------------
#   shadowing   EMULATED, not restored. The old code passed the ledger gap, which
#               reached about 80 m for a 10 s interval and gives rho = 0.001. The
#               reversion here draws every sample independently, which is that
#               limit. It reproduces the CONSEQUENCE -- retries as fresh channels
#               -- rather than the exact arithmetic, and the first transmission of
#               an interval is treated the same way, where the old code was
#               approximately right. So this slightly OVERSTATES the defect.
#   cbr_ref     EXACT. One module constant.
#   ledger      EXACT. The one-step subtraction is put back.
#   peak_aoi    NOT run as a pair. The old code appended at every transmission
#               ATTEMPT and the new one only on delivery, so the discarded
#               samples are the ages at failures -- each strictly smaller than the
#               age at the delivery that ends the same interval, because age only
#               falls at a delivery. The direction is therefore a fact about the
#               samples and not something a run needs to establish. What a run
#               contributes is the SIZE: how many samples were spurious, which is
#               attempts minus deliveries.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

METRICS = ("packet_loss_rate", "tx_attempts", "tx_abandoned", "mean_error",
           "max_error", "mean_peak_aoi", "peak_aoi", "avg_tx_power_dbm",
           "mean_reward", "n_observations")


def _run(density: float, steps: int, seed: int, variant: str) -> Dict[str, Any]:
    """One episode under the fixed behaviour policy, with `variant` reverted."""
    import src.Communications as comm
    import src.hot_swap_trainer as hst
    from src.hoorl_offline import FixedPeriodBehaviourPolicy, OfflineDataset
    from src.rl_interface import ActionDecoder
    from src.sumo.make_sumo_set import road_seed, seed_road_network

    bp = OfflineDataset.load(
        "/home/imnyj/Workspace/paper4/data/hoorl_offline/hoorl_offline.npz"
    ).metadata["behaviour_policy"]
    # Both spellings are accepted: files collected before the 2026-09-07 rename
    # carry only the old keys, and newer ones carry both.
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=float(bp.get("delta_band_center", bp.get("delta_fixed"))),
        num_channels=int(bp["num_channels"]),
        p_min=float(bp["p_min"]), p_max=float(bp["p_max"]),
        delta_log_halfwidth=float(
            bp.get("delta_log_halfwidth", bp.get("delta_jitter"))))

    restore: List[Any] = []
    if variant == "shadowing_old":
        original = comm.draw_shadowing_db_correlated

        def independent(link_id, distance_moved_m=None, sigma_db=comm.SHADOWING_SIGMA_DB,
                        decorr_m=comm.SHADOWING_DECORR_M, position=None):
            # The limit the ledger gap reached: rho -> 0, a fresh channel per draw.
            return comm.draw_shadowing_db(sigma_db)

        comm.draw_shadowing_db_correlated = independent
        restore.append(lambda: setattr(comm, "draw_shadowing_db_correlated", original))
    elif variant == "cbr_ref_old":
        original_ref = hst.CBR_REF
        hst.CBR_REF = 0.60
        restore.append(lambda: setattr(hst, "CBR_REF", original_ref))
    elif variant == "ledger_old":
        original_reg = hst.AoiV2IEnv._register_vehicle

        def old_register(self, vid, st, t_update):
            original_reg(self, vid, st, t_update)
            if getattr(self, "_stepped_once", False):
                self.vehicle_tracks[vid]["t_update"] = self.sim_time - self.step_length

        hst.AoiV2IEnv._register_vehicle = old_register
        restore.append(lambda: setattr(hst.AoiV2IEnv, "_register_vehicle", original_reg))

    try:
        seed_road_network(density, 0)
        hst.prepare_scenario(density=density, max_steps=steps,
                             warmup_steps=hst.DEFAULT_WARMUP_STEPS,
                             seed=road_seed(density, 0))
        comm.reset_shadowing_state()
        comm.seed_channel(seed)
        env = hst.AoiV2IEnv(density=density, seed=seed, max_steps=steps,
                            warmup_steps=hst.DEFAULT_WARMUP_STEPS)
        obs, _info = env.reset()
        env._stepped_once = True
        decoder = ActionDecoder()
        rng = np.random.default_rng(seed)
        open_vids, actions = set(), {}
        for vid in obs:
            grant, _ch, _lp = policy.sample(rng, decoder)
            actions[vid] = grant
            open_vids.add(vid)
        for _step in range(steps):
            obs, _r, _t, _tr, info = env.step(actions)
            actions = {}
            for rec in info["completed"]:
                open_vids.discard(rec["vid"])
            for vid in obs:
                if vid not in open_vids:
                    grant, _ch, _lp = policy.sample(rng, decoder)
                    actions[vid] = grant
                    open_vids.add(vid)
            open_vids &= set(obs)
        env.finalize_open_intervals()
        metrics = env.get_metrics()
        env.close()
    finally:
        for fn in restore:
            fn()

    out = {"variant": variant}
    out.update({k: metrics.get(k) for k in METRICS})
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--density", type=float, default=25.0)
    p.add_argument("--steps", type=int, default=400)
    p.add_argument("--seed", type=int, default=2001)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    variants = ["fixed", "shadowing_old", "cbr_ref_old", "ledger_old"]
    rows = []
    for v in variants:
        row = _run(args.density, args.steps, args.seed, v)
        rows.append(row)
        print(f"{v:16s} loss {row['packet_loss_rate']}  attempts {row['tx_attempts']}  "
              f"abandoned {row['tx_abandoned']}  mean_error {row['mean_error']}  "
              f"mean_peak_aoi {row['mean_peak_aoi']}  reward {row['mean_reward']}",
              flush=True)

    base = rows[0]
    deltas = []
    for row in rows[1:]:
        d = {"variant": row["variant"]}
        for k in METRICS:
            a, b = base.get(k), row.get(k)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                d[k] = round(float(a) - float(b), 6)
                d[f"{k}_rel"] = (round((float(a) - float(b)) / abs(float(b)), 4)
                                 if b else None)
        deltas.append(d)

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "physics_fix_comparison.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    attempts = float(base.get("tx_attempts") or 0)
    loss = float(base.get("packet_loss_rate") or 0.0)
    deliveries = attempts * (1.0 - loss)
    summary = {
        "density": args.density, "steps": args.steps, "seed": args.seed,
        "predictions": "results/diagnostics/physics_fix_expected_changes.md",
        "reading": "each delta is (fixed - reverted), so a positive number means "
                   "the fixed code reports MORE of that quantity",
        "deltas_vs_fixed": deltas,
        "peak_aoi_sample_inflation": {
            "tx_attempts": attempts,
            "estimated_deliveries": round(deliveries, 1),
            "spurious_samples_under_old_rule": round(attempts - deliveries, 1),
            "note": ("the old rule appended once per ATTEMPT. Every discarded "
                     "sample is the age at a failure, which is strictly smaller "
                     "than the age at the delivery closing the same interval, so "
                     "the old mean was strictly lower. This run gives the size of "
                     "the inflation, not its direction, which is a property of "
                     "the samples."),
        },
    }
    json_path = os.path.join(args.out_dir, "physics_fix_comparison.json")
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=float)
    print("\n" + json.dumps(summary["deltas_vs_fixed"], indent=2, sort_keys=True))
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
