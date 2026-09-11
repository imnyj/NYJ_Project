#!/usr/bin/env python3
# etc/scripts/verify_offline_stats.py
# ============================================================================
# Independent checks on src/hoorl_offline_stats.py, against cases whose answers
# are known in closed form rather than against the module's own output.
#
# The checks that matter here are the ones a plausible-looking implementation
# would pass anyway, so each is a case where a wrong implementation gives a
# visibly wrong NUMBER, not merely a wrong sign:
#
#   * Wasserstein-1 between two point masses is the distance between them;
#   * between two Bernoulli samples it is |p - q| exactly, which is the case the
#     three one-hot signal features actually are;
#   * scipy is used as an oracle, not as a dependency of the module;
#   * a pair that differs ONLY in correlation must score ~0 on the mean of
#     marginals and clearly non-zero on the joint measure. That is the stated
#     blind spot of the primary metric, and if the joint measure did not catch
#     it there would be no reason to compute it.
# ============================================================================

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from src.rl_interface import STATE_DIM  # noqa: E402
from src.hoorl_offline_stats import (  # noqa: E402
    FEATURE_HIGH,
    FEATURE_LOW,
    FEATURE_NAMES,
    comparison_report,
    describe_states,
    coverage_warnings,
    energy_distance,
    mean_normalised_w1,
    normalise_states,
    per_feature_w1,
    split_half_floor,
    wasserstein1_1d,
)

FAILURES = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def synth(n, rng, loc=0.0, scale=0.25, p_red=0.3):
    """A state matrix with the right width and plausible per-feature supports."""
    x = np.zeros((n, STATE_DIM))
    for j in range(STATE_DIM):
        lo, hi = FEATURE_LOW[j], FEATURE_HIGH[j]
        x[:, j] = np.clip(rng.normal((lo + hi) / 2 + loc * (hi - lo), scale * (hi - lo), n), lo, hi)
    # the three one-hot signal slots, made genuinely categorical
    red = rng.random(n) < p_red
    yellow = (~red) & (rng.random(n) < 0.1)
    green = ~(red | yellow)
    x[:, FEATURE_NAMES.index("tls_red")] = red.astype(float)
    x[:, FEATURE_NAMES.index("tls_yellow")] = yellow.astype(float)
    x[:, FEATURE_NAMES.index("tls_green")] = green.astype(float)
    return x


def main() -> int:
    rng = np.random.default_rng(7)

    # ---- 1. closed-form Wasserstein-1 --------------------------------------
    a = np.full(500, 0.2)
    b = np.full(300, 0.9)
    got = wasserstein1_1d(a, b)
    check("W1 between two point masses equals their separation",
          abs(got - 0.7) < 1e-9, f"got {got:.12f}, expected 0.7")

    got = wasserstein1_1d(a, a)
    check("W1 of a sample against itself is exactly zero",
          got == 0.0, f"got {got}")

    p, q = 0.3, 0.75
    ba = (rng.random(200000) < p).astype(float)
    bb = (rng.random(200000) < q).astype(float)
    got = wasserstein1_1d(ba, bb)
    exact = abs(ba.mean() - bb.mean())
    check("W1 between two Bernoulli samples equals |p_hat - q_hat|",
          abs(got - exact) < 1e-9, f"got {got:.9f}, expected {exact:.9f}")

    # ---- 2. scipy as an independent oracle ---------------------------------
    try:
        from scipy.stats import wasserstein_distance as scipy_w1
        worst = 0.0
        for _ in range(30):
            xa = rng.normal(0, 1, rng.integers(50, 400))
            xb = rng.gamma(2.0, 1.5, rng.integers(50, 400))
            worst = max(worst, abs(wasserstein1_1d(xa, xb) - scipy_w1(xa, xb)))
        check("W1 matches scipy.stats.wasserstein_distance on 30 random pairs",
              worst < 1e-9, f"worst absolute difference {worst:.3e}")
    except ImportError:
        print("[SKIP] scipy oracle unavailable")

    # ---- 3. normalisation --------------------------------------------------
    edges = np.vstack([FEATURE_LOW, FEATURE_HIGH])
    norm = normalise_states(edges)
    check("nominal bounds map to exactly 0 and 1",
          np.allclose(norm[0], 0.0) and np.allclose(norm[1], 1.0),
          f"low->{norm[0].min():.3g}..{norm[0].max():.3g}, high->{norm[1].min():.3g}..{norm[1].max():.3g}")

    # ---- 4. identical vs shifted samples -----------------------------------
    x1 = synth(4000, rng)
    x2 = synth(4000, rng)
    x_shift = synth(4000, rng, loc=0.15, p_red=0.7)
    d_same = mean_normalised_w1(x1, x2)
    d_shift = mean_normalised_w1(x1, x_shift)
    check("a real shift scores well above two draws of the same distribution",
          d_shift > 5 * d_same,
          f"same-distribution {d_same:.5f}, shifted {d_shift:.5f}, ratio {d_shift / d_same:.1f}x")

    e_same = energy_distance(x1, x2, max_samples=1500, seed=1)
    e_shift = energy_distance(x1, x_shift, max_samples=1500, seed=1)
    check("the joint measure separates the same two cases",
          e_shift > 5 * e_same,
          f"same {e_same:.5f}, shifted {e_shift:.5f}, ratio {e_shift / max(e_same, 1e-12):.1f}x")

    # ---- 5. the stated blind spot is real, and the joint measure covers it --
    n = 6000
    z = rng.normal(0, 0.2, n)
    w = rng.normal(0, 0.2, n)
    ca = np.zeros((n, STATE_DIM))
    cb = np.zeros((n, STATE_DIM))
    for j in range(STATE_DIM):
        mid = (FEATURE_LOW[j] + FEATURE_HIGH[j]) / 2
        ca[:, j] = np.clip(mid + z, FEATURE_LOW[j], FEATURE_HIGH[j])
        cb[:, j] = np.clip(mid + z, FEATURE_LOW[j], FEATURE_HIGH[j])
    # Identical marginals in every column -- `w` and `z` are drawn from the same
    # law -- but in `ca` column 1 is INDEPENDENT of the other sixteen while in
    # `cb` it is a deterministic copy of them. Only the dependence differs.
    mid1 = (FEATURE_LOW[1] + FEATURE_HIGH[1]) / 2
    ca[:, 1] = np.clip(mid1 + w, FEATURE_LOW[1], FEATURE_HIGH[1])
    cb[:, 1] = np.clip(mid1 + z, FEATURE_LOW[1], FEATURE_HIGH[1])
    d_marg = mean_normalised_w1(ca, cb)
    d_joint = energy_distance(ca, cb, max_samples=2000, seed=2)
    floor_j = split_half_floor(ca, repeats=3, subsample=2000, max_samples=2000, seed=3)
    check("correlation-only difference is invisible to the mean of marginals",
          d_marg < 5e-3, f"mean normalised W1 = {d_marg:.6f}")
    # The margin is stated on the reported scale AND on the underlying statistic.
    # `energy_distance` returns a square root, which compresses ratios: a factor
    # of 5.5 on the statistic itself shows up as a factor of 2.3 here. The claim
    # under test is only that the joint measure clears its own noise floor on a
    # difference the marginals cannot see, so the threshold is set on that.
    floor_j_val = floor_j["energy_distance_max"]
    check("correlation-only difference IS visible to the joint measure",
          d_joint > 2.0 * floor_j_val,
          f"joint {d_joint:.5f} vs its own split-half floor {floor_j_val:.5f} "
          f"({d_joint / max(floor_j_val, 1e-12):.2f}x reported, "
          f"{(d_joint / max(floor_j_val, 1e-12)) ** 2:.2f}x on the statistic)")

    # ---- 6. the noise floor shrinks as the sample grows --------------------
    big = synth(20000, rng)
    f_small = split_half_floor(big, repeats=5, subsample=250, max_samples=250, seed=4)
    f_large = split_half_floor(big, repeats=5, subsample=5000, max_samples=1500, seed=4)
    check("the split-half floor is smaller at a larger sample size",
          f_large["mean_normalised_w1_mean"] < f_small["mean_normalised_w1_mean"],
          f"n=250 -> {f_small['mean_normalised_w1_mean']:.5f}, "
          f"n=5000 -> {f_large['mean_normalised_w1_mean']:.5f}")

    # ---- 7. coverage diagnostics fire on the cases they exist for ----------
    degenerate = synth(3000, rng)
    degenerate[:, 11] = 0.5                       # a constant feature
    # Heavily but not entirely clipped at the ceiling. Not a constant: a feature
    # that is constant AND clipped is reported as constant, which is the more
    # informative of the two complaints, so the clipping branch needs a case
    # where the feature still varies.
    clipped = rng.random(degenerate.shape[0]) < 0.4
    degenerate[clipped, 13] = 1.0
    degenerate[~clipped, 13] = rng.uniform(0.0, 0.9, int((~clipped).sum()))
    rows = describe_states(degenerate)
    warns = coverage_warnings(rows)
    joined = " | ".join(warns)
    check("a constant feature is reported as constant",
          any("phase_remaining_norm" in w and "constant" in w for w in warns), joined[:160])
    check("a feature pinned at its ceiling is reported as clipped",
          any("n_active_norm" in w and "clip bound" in w for w in warns), joined[:160])
    check("the row count equals the observation width",
          len(rows) == STATE_DIM, f"{len(rows)} rows, STATE_DIM {STATE_DIM}")
    check("every row is named, none is a bare index",
          all(isinstance(r["feature"], str) and not r["feature"].isdigit() for r in rows))

    # ---- 8. the report refuses to look interpretable without controls ------
    rep_nc = comparison_report({"a": x1, "b": x_shift}, [("a", "b")], max_samples=800)
    check("a report with no control says so in its own text",
          "NO CONTROL" in rep_nc["interpretability_note"],
          rep_nc["interpretability_note"][:80])
    rep = comparison_report(
        {"a": x1, "b": x_shift, "c": x2}, [("a", "b"), ("a", "c")],
        reference_pair=("a", "c"), floor_on="a", max_samples=800,
    )
    row_ab = [r for r in rep["rows"] if r["sample_b"] == "b"][0]
    check("with controls, every row carries both ratio columns",
          row_ab["w1_over_sampling_floor"] is not None
          and row_ab["w1_over_reference_shift"] is not None,
          f"floor ratio {row_ab['w1_over_sampling_floor']:.2f}, "
          f"reference ratio {row_ab['w1_over_reference_shift']:.2f}")
    check("the metric definition travels with the numbers",
          "primary" in rep["distance_spec"] and "definition" in rep["distance_spec"]["primary"])

    # ---- 9. per-feature vector is the right length and labelled ------------
    pf = per_feature_w1(x1, x_shift)
    check("per-feature distance has one entry per observation feature",
          pf.shape == (STATE_DIM,), f"shape {pf.shape}")
    check("per-feature keys in a report are prefixed feature names",
          all(f"w1_{n}" in row_ab for n in FEATURE_NAMES))

    print("\n" + json.dumps({
        "checks_run": len(FAILURES) + sum(1 for _ in []) or None,
        "failures": FAILURES,
    }, indent=2) if FAILURES else "\nAll checks passed.")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
