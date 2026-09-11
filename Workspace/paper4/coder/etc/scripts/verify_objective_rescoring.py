"""What the objective change does to the nine committed studies, re-scored.

Independent of `hpo.py`'s own arithmetic where it matters: the OLD objective is
re-implemented here from the pre-2026-09-05 source line, while the NEW one is
called through `compute_composite_objective` so the file under test is the file
that ships. If the two agreed on every trial the change would be inert, and the
point of the script is to show, per model, which trial each objective picks.

Only the trials of `results/hpo/optuna_trials_*.csv` are read. Nothing is
retrained, no rollout is run and no committed file is modified; the re-scoring is
arithmetic over columns Optuna already wrote. Output goes to
`results/hpo/objective_rescoring_20260905.csv`.

Trials that scored the failure penalty are re-scored but reported separately: a
penalised trial carries no measurement, so including it in the "which trial
wins" comparison would compare an arithmetic result against a constant.
"""
from __future__ import annotations

import csv
import glob
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd  # noqa: E402

from src.hpo import compute_composite_objective, is_penalty_score  # noqa: E402

RESULTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "results", "hpo")
)
OUT_PATH = os.path.join(RESULTS_DIR, "objective_rescoring_20260905.csv")

#: The weights, unchanged by this edit. The third slot moved from the coverage
#: outage rate to the packet loss rate; its weight of 2.0 stayed where it was.
W_ERROR, W_AOI, W_THIRD, W_POWER = 1.0, 0.5, 2.0, 0.2


def old_objective(row: Dict[str, float]) -> float:
    """The pre-2026-09-05 line, transcribed:

        outage_rate = metrics.get("outage_rate", metrics.get("packet_loss_rate", 0.0))
        objective   = 1.0*mean_error + 0.5*mean_aoi + 2.0*outage_rate + 0.2*avg_power_norm

    where the rollout had already set `outage_rate = coverage_outage_rate`.
    """
    return (
        W_ERROR * row["mean_error"]
        + W_AOI * row["mean_aoi"]
        + W_THIRD * row["outage_rate"]
        + W_POWER * row["avg_power_norm"]
    )


def main() -> None:
    rows: List[Dict[str, Any]] = []
    summary: List[Dict[str, Any]] = []

    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "optuna_trials_*.csv"))):
        model = os.path.basename(path)[len("optuna_trials_"):-len(".csv")]
        df = pd.read_csv(path)
        per_model: List[Dict[str, Any]] = []
        for _, r in df.iterrows():
            metrics = {
                "mean_error": float(r["user_attrs_mean_error"]),
                "mean_aoi": float(r["user_attrs_mean_aoi"]),
                "outage_rate": float(r["user_attrs_outage_rate"]),
                "coverage_outage_rate": float(r["user_attrs_coverage_outage_rate"]),
                "packet_loss_rate": float(r["user_attrs_packet_loss_rate"]),
                "avg_power_norm": float(r["user_attrs_avg_power_norm"]),
                # The emptiness and divergence guards must not fire during a
                # re-scoring: these trials were scored live and their verdicts
                # are already in `value`. Supplying the counts Optuna recorded
                # keeps `run_is_empty` from condemning a healthy trial here.
                "n_observations": float(r["user_attrs_n_observations"]),
                "tx_attempts": float(r["user_attrs_tx_attempts"]),
            }
            penalised = is_penalty_score(r["value"])
            rec = {
                "model": model,
                "trial": int(r["number"]),
                "recorded_value": float(r["value"]),
                "penalised_trial": penalised,
                "mean_error": metrics["mean_error"],
                "mean_aoi": metrics["mean_aoi"],
                "coverage_outage_rate": metrics["coverage_outage_rate"],
                "packet_loss_rate": metrics["packet_loss_rate"],
                "avg_power_norm": metrics["avg_power_norm"],
                "old_score": round(old_objective(metrics), 6),
                "new_score": round(compute_composite_objective(metrics), 6),
            }
            rec["delta"] = round(rec["new_score"] - rec["old_score"], 6)
            rows.append(rec)
            if not penalised:
                per_model.append(rec)

        if not per_model:
            summary.append({"model": model, "n_usable_trials": 0, "old_best_trial": -1,
                            "new_best_trial": -1, "winner_changed": "",
                            "old_best_packet_loss": "", "new_best_packet_loss": "",
                            "coverage_outage_unique_values": ""})
            continue

        old_best = min(per_model, key=lambda x: x["old_score"])
        new_best = min(per_model, key=lambda x: x["new_score"])
        summary.append({
            "model": model,
            "n_usable_trials": len(per_model),
            "old_best_trial": old_best["trial"],
            "new_best_trial": new_best["trial"],
            "winner_changed": old_best["trial"] != new_best["trial"],
            "old_best_packet_loss": old_best["packet_loss_rate"],
            "new_best_packet_loss": new_best["packet_loss_rate"],
            # 1 means the term was a constant over the whole study, so the old
            # objective's largest weight ranked nothing at all.
            "coverage_outage_unique_values": df["user_attrs_coverage_outage_rate"].nunique(),
        })

    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("WROTE", OUT_PATH, flush=True)

    print()
    print(pd.DataFrame(summary).to_string(index=False), flush=True)

    all_rows = pd.DataFrame(rows)
    real = all_rows[~all_rows["penalised_trial"]]
    print()
    print(f"trials read: {len(all_rows)}, usable: {len(real)}")
    print("coverage_outage_rate over ALL trials: "
          f"min={all_rows['coverage_outage_rate'].min()} "
          f"max={all_rows['coverage_outage_rate'].max()} "
          f"distinct={all_rows['coverage_outage_rate'].nunique()}")
    print("packet_loss_rate over ALL trials: "
          f"min={all_rows['packet_loss_rate'].min()} "
          f"max={all_rows['packet_loss_rate'].max()} "
          f"distinct={all_rows['packet_loss_rate'].nunique()}")
    changed = sum(1 for s in summary if s["winner_changed"] is True)
    print(f"studies whose selected trial changes: {changed}/"
          f"{sum(1 for s in summary if s['n_usable_trials'] > 0)}")


if __name__ == "__main__":
    main()
