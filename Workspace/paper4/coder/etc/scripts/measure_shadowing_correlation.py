#!/usr/bin/env python
# etc/scripts/measure_shadowing_correlation.py
# ============================================================================
# DOES A RETRANSMISSION KEEP THE SHADOW IT IS BEHIND?
#
# ---------------------------------------------------------------------------
# WHAT WENT WRONG, AND WHY A CLAIM IS NOT ENOUGH HERE
# ---------------------------------------------------------------------------
# `draw_shadowing_db_correlated` needs the distance travelled SINCE THE LAST
# DRAW ON THIS LINK. The trainer supplied the distance between the vehicle's
# current position and the position in its ledger, which is the dead-reckoning
# error. The two agree on a first transmission and diverge on every retry,
# because a failed transmission does not update the ledger -- so the value grew
# with each retry and rho collapsed toward zero, which is precisely the
# independent-draw behaviour this module was written to remove.
#
# That behaviour was measured once before at an 88-fold difference in final
# delivery failure (0.08 % against 7.06 % at the cell edge). A defect of that
# size, fixed twice, is not something to accept on the strength of a diff. This
# measures the quantity itself.
#
# ---------------------------------------------------------------------------
# WHAT IS MEASURED
# ---------------------------------------------------------------------------
#   1. THE DISTANCE THE MODULE ACTUALLY USES, per retry, read back from
#      `shadowing_reference_position`. Under the defect it grows with the retry
#      index; correct, it is the movement between consecutive draws.
#   2. THE RESULTING rho, so the consequence is stated in the terms the physics
#      is in rather than in metres.
#   3. THE CORRELATION OF THE SAMPLES THEMSELVES over many repetitions, which is
#      the property the distance exists to produce. A number that survives the
#      arithmetic and fails here would mean the AR(1) step is broken elsewhere.
#
# The old behaviour is reproduced alongside by driving the same sequence through
# the distance form with the ledger-style accumulating value, so the two columns
# can be read against each other rather than against memory.
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from typing import Any, Dict, List, Optional, Sequence

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: A vehicle at urban speed, one 0.1 s step between retries.
SPEED_MPS = 8.0
STEP_S = 0.1

#: Retries within one second, the window the original fix was measured over.
N_RETRIES = 10

#: Seconds since the last successful report when the burst starts. This is what
#: made the defect grow: the ledger is this far behind before the first retry.
INTERVAL_S = 10.0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repeats", type=int, default=4000)
    p.add_argument("--out-dir", default=os.path.join(ROOT, "results", "diagnostics"))
    args = p.parse_args(argv)

    import src.Communications as comm

    rows: List[Dict[str, Any]] = []

    # ---- 1 and 2: the distance the module uses, and the rho it implies -----
    comm.reset_shadowing_state()
    comm.seed_channel(20260907)
    x = 0.0
    for k in range(N_RETRIES + 1):
        before = comm.shadowing_reference_position("veh0")
        comm.draw_shadowing_db_correlated("veh0", position=(x, 0.0))
        after = comm.shadowing_reference_position("veh0")
        used = (math.hypot(after[0] - before[0], after[1] - before[1])
                if before is not None else float("inf"))
        # What the old code would have handed over: the gap to the ledger, which
        # has not been updated since the interval opened.
        ledger_gap = SPEED_MPS * (INTERVAL_S + k * STEP_S)
        rows.append({
            "retry": k,
            "distance_used_m": (None if math.isinf(used) else round(used, 4)),
            "rho_now": (0.0 if math.isinf(used)
                        else round(math.exp(-used / comm.SHADOWING_DECORR_M), 6)),
            "old_distance_m": round(ledger_gap, 4),
            "old_rho": round(math.exp(-ledger_gap / comm.SHADOWING_DECORR_M), 6),
        })
        x += SPEED_MPS * STEP_S

    # ---- 3: the correlation of consecutive samples, both ways --------------
    def _sequence(use_position: bool) -> List[List[float]]:
        out: List[List[float]] = []
        for r in range(args.repeats):
            comm.reset_shadowing_state()
            comm.seed_channel(1000 + r)
            link, pos, seq = f"v{r}", 0.0, []
            for k in range(N_RETRIES + 1):
                if use_position:
                    seq.append(comm.draw_shadowing_db_correlated(
                        link, position=(pos, 0.0)))
                else:
                    seq.append(comm.draw_shadowing_db_correlated(
                        link, SPEED_MPS * (INTERVAL_S + k * STEP_S)))
                pos += SPEED_MPS * STEP_S
            out.append(seq)
        return out

    def _corr(seqs: List[List[float]], lag: int) -> float:
        a = [s[i] for s in seqs for i in range(len(s) - lag)]
        b = [s[i + lag] for s in seqs for i in range(len(s) - lag)]
        ma, mb = statistics.mean(a), statistics.mean(b)
        num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
        da = math.sqrt(sum((p - ma) ** 2 for p in a))
        db = math.sqrt(sum((q - mb) ** 2 for q in b))
        return num / (da * db) if da > 0 and db > 0 else 0.0

    fixed = _sequence(True)
    old = _sequence(False)
    corr = {
        "lag1_fixed": round(_corr(fixed, 1), 4),
        "lag1_old": round(_corr(old, 1), 4),
        "lag1_expected_fixed": round(math.exp(-(SPEED_MPS * STEP_S)
                                              / comm.SHADOWING_DECORR_M), 4),
        "sd_fixed": round(statistics.pstdev([v for s in fixed for v in s]), 4),
        "sd_old": round(statistics.pstdev([v for s in old for v in s]), 4),
        "sigma_db": comm.SHADOWING_SIGMA_DB,
    }

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "shadowing_correlation.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    json_path = os.path.join(args.out_dir, "shadowing_correlation.json")
    used_vals = [r["distance_used_m"] for r in rows if r["distance_used_m"] is not None]
    summary = {
        "speed_mps": SPEED_MPS, "step_s": STEP_S, "retries": N_RETRIES,
        "interval_s": INTERVAL_S, "repeats": args.repeats,
        "decorr_m": comm.SHADOWING_DECORR_M,
        "distance_used_is_constant": bool(max(used_vals) - min(used_vals) < 1e-9),
        "distance_used_m": round(used_vals[0], 4) if used_vals else None,
        "old_distance_grew_from_to": [rows[0]["old_distance_m"],
                                      rows[-1]["old_distance_m"]],
        "rho_now": rows[-1]["rho_now"], "rho_old_at_last_retry": rows[-1]["old_rho"],
        "sample_correlation": corr,
    }
    with open(json_path, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=float)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\n{csv_path}\n{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
