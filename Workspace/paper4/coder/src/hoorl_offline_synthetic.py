# src/hoorl_offline_synthetic.py
# ============================================================================
# A SYNTHETIC offline dataset, for the test suite and for nothing else.
#
# ---------------------------------------------------------------------------
# WHY THIS EXISTS AND WHY IT IS A SEPARATE FILE
# ---------------------------------------------------------------------------
# `src/hoorl_wiring.py` refuses to run HOORL without an offline dataset, which
# is correct: a HOORL run that skips its first stage is the online-only ablation
# and is indistinguishable from the real method once it has finished. The
# consequence is that every test touching HOORL now depends on a collected
# dataset, and a collected dataset is a multi-minute SUMO run whose output is not
# in the repository.
#
# There were two ways out and only one of them is honest.
#
#   * Pass `require_offline=False` in the tests. The failure disappears, and so
#     does the check: nothing then verifies that the offline stage is reachable,
#     and the wiring could be deleted tomorrow with every test still green. That
#     is the exact defect the wiring was written to prevent, reintroduced one
#     layer up.
#   * Give the tests a small dataset of their own. The wiring is then exercised
#     end to end on every run, and if somebody breaks the path from
#     `pretrain_hoorl` to `HOORL.offline_update` the suite goes red. The check
#     defends something.
#
# This module is the second. It is a SEPARATE FILE from `src/hoorl_offline.py`
# so that no reader and no future edit can confuse manufactured numbers with
# collected ones. The collector never imports this module; this module imports
# the collector, for the dataset container and the provenance helpers only.
#
# ---------------------------------------------------------------------------
# WHAT MAKES IT SAFE TO HAVE MANUFACTURED DATA IN THE REPOSITORY AT ALL
# ---------------------------------------------------------------------------
# Three things, and all three are load-bearing.
#
#   1. IT IS BUILT, NEVER STORED. `build_synthetic_dataset` reads the live
#      observation-normalising constants at the moment it runs, so the file it
#      writes can never be stale. A checked-in npz would have gone stale on
#      2026-09-05, when `N_ACTIVE_MAX_OBS` moved from 100 to 168 and the
#      neighbour cap from 16 to 32, and it would have gone stale silently.
#   2. IT IS MARKED, LOUDLY. The metadata carries `synthetic: true` and a
#      behaviour policy named `SYNTHETIC_NOT_A_POLICY`. `assert_not_synthetic`
#      is the one-line check any results-producing path can call, and a reported
#      result can never rest on this data without somebody having deleted that
#      call.
#   3. IT MAKES NO SCIENTIFIC CLAIM. The states are draws from the nominal range
#      of each feature and the rewards are draws in the reward's sign-correct
#      range. They exercise shapes, dtypes, key sets and code paths. They do not
#      describe traffic, and nothing here should ever be used to argue that the
#      offline stage learns anything.
# ============================================================================

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np

from src.hoorl_offline import (
    ARRAY_KEYS,
    DATASET_FORMAT_VERSION,
    OfflineDataset,
    ScenarioNotGenerated,
    git_provenance,
    observation_constants,
    scenario_provenance,
)
from src.rl_interface import STATE_DIM

logger = logging.getLogger(__name__)

#: The value of `behaviour_policy["kind"]` in a synthetic dataset's metadata.
#: Deliberately not a policy name: it must read as a refusal, not as a variant.
SYNTHETIC_POLICY_KIND: str = "SYNTHETIC_NOT_A_POLICY"

#: Default size. Large enough that `DEFAULT_PRETRAIN_BATCH_SIZE` (256) draws a
#: full batch without replacement, which is what the batch contract is checked
#: against, and small enough to build in milliseconds.
DEFAULT_N_TRANSITIONS: int = 512

#: Per-feature nominal range of the observation, transcribed from
#: `StateVectorizer.vectorize_from_dict`. Indices 8, 9 and 10 are the one-hot
#: signal phase and are generated as a genuine one-hot rather than as three
#: independent uniforms, because a model that consumed three simultaneous
#: "reds" would be exercised on an input the environment cannot produce.
_SIGNED_FEATURES: Tuple[int, ...] = (1, 2, 4, 5, 6, 16)
_ONEHOT_TLS: Tuple[int, ...] = (8, 9, 10)


def _synthetic_states(rng: np.random.Generator, n: int) -> np.ndarray:
    """States inside every feature's nominal range, with a valid signal one-hot."""
    states = rng.uniform(0.0, 1.0, size=(n, STATE_DIM)).astype(np.float32)
    for j in _SIGNED_FEATURES:
        states[:, j] = rng.uniform(-1.0, 1.0, size=n)
    phase = rng.integers(0, len(_ONEHOT_TLS), size=n)
    for k, j in enumerate(_ONEHOT_TLS):
        states[:, j] = (phase == k).astype(np.float32)
    return states


def build_synthetic_dataset(
    n_transitions: int = DEFAULT_N_TRANSITIONS,
    num_channels: int = 4,
    gamma: float = 0.99,
    seed: int = 20260906,
    delta_band: Tuple[float, float] = (0.5, 10.0),
) -> OfflineDataset:
    """A dataset with the CURRENT observation contract and manufactured contents.

    Every column has the dtype and the width the collector produces, so a
    consumer cannot tell the two apart by shape -- which is the point, since the
    thing under test is the consumer. The metadata is where they differ, and it
    differs unmistakably.

    `delta_t` is drawn log-uniformly over `delta_band` because the SMDP discount
    is `gamma ** delta_t`: a constant `delta_t` would leave the discount column
    constant and a bug that ignored it would pass. Rewards are strictly
    non-positive, matching the environment's reward, so a sign error in a
    consumer still shows up here.
    """
    if int(n_transitions) <= 0:
        raise ValueError("a synthetic dataset needs at least one transition")
    # The one thing this fixture must get right is the CURRENT observation
    # normalisation, and before any scenario is generated the normalisers are the
    # import-time fallbacks of an empty directory (V_MAX_OBS 13.32 against a real
    # 15.9). A fixture built then is rejected by the very check it exists to
    # exercise, so the failure is raised here, where the cause is legible, rather
    # than later as a 17 % constant mismatch that reads like a redefinition.
    if not scenario_provenance()["network_present"]:
        raise ScenarioNotGenerated(
            "no SUMO network has been generated, so the observation normalisers "
            "are import-time fallbacks. Call prepare_scenario() before building "
            "the synthetic fixture; a fixture carrying the fallbacks would be "
            "refused by verify_compatibility against any real run."
        )
    rng = np.random.default_rng(int(seed))
    n = int(n_transitions)
    lo, hi = float(delta_band[0]), float(delta_band[1])
    if not (0.0 < lo <= hi):
        raise ValueError(f"delta_band {delta_band} is not a valid interval")

    delta_t = np.exp(rng.uniform(np.log(lo), np.log(hi), size=n)).astype(np.float32)
    arrays: Dict[str, np.ndarray] = {
        "state": _synthetic_states(rng, n),
        # (Delta unit coordinate, channel unit coordinate, power unit coordinate),
        # the same three-vector `ActionDecoder.encode_action` produces.
        "action": rng.uniform(0.0, 1.0, size=(n, 3)).astype(np.float32),
        # The environment's reward is a negative weighted sum of four terms in
        # [0, 1] with weights summing to 1, so it lives in [-1, 0].
        "reward": (-rng.uniform(0.0, 1.0, size=n)).astype(np.float32),
        "next_state": _synthetic_states(rng, n),
        # A few terminals, so the `1 - done` factor is exercised. Never all and
        # never none.
        "done": (rng.uniform(size=n) < 0.05).astype(np.float32),
        "delta_t": delta_t,
        "action_idx": rng.integers(0, int(num_channels), size=n).astype(np.int64),
        # Uniform over the channels; the power factor is uniform on the unit
        # interval and contributes zero, exactly as in the collector.
        "behaviour_log_prob": np.full(
            n, -float(np.log(float(num_channels))), dtype=np.float32
        ),
    }
    missing = [k for k in ARRAY_KEYS if k not in arrays]
    if missing:  # pragma: no cover - guards a future column being added upstream
        raise KeyError(
            f"the synthetic builder does not produce {missing}, which "
            "src.hoorl_offline.ARRAY_KEYS now requires. Add them here rather "
            "than removing them there."
        )

    metadata: Dict[str, Any] = {
        "format_version": DATASET_FORMAT_VERSION,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": "HOORL",
        # The three fields any consumer should key on.
        "synthetic": True,
        "not_for_results": True,
        "purpose": (
            "TEST FIXTURE ONLY. Manufactured numbers with the current observation "
            "contract. No SUMO episode produced these rows, they describe no "
            "traffic, and no measurement, table or figure may rest on them. They "
            "exist so that the HOORL offline wiring is exercised by the test "
            "suite instead of being disabled with require_offline=False."
        ),
        "behaviour_policy": {
            "kind": SYNTHETIC_POLICY_KIND,
            "delta_band": [lo, hi],
            "delta_component_defined": False,
            "num_channels": int(num_channels),
            "note": (
                "There is no behaviour policy. delta_t is drawn log-uniformly "
                "over delta_band to keep the SMDP discount column non-constant, "
                "and behaviour_log_prob carries only the channel factor, matching "
                "the collector's convention so the two are shape-compatible."
            ),
        },
        "n_transitions": n,
        "state_dim": int(STATE_DIM),
        "num_channels": int(num_channels),
        "seed": int(seed),
        "gamma_for_stored_discount": float(gamma),
        # Read LIVE, which is what keeps a regenerated fixture from going stale
        # when the observation normalisation moves.
        "observation_constants": observation_constants(),
        "scenario_provenance": scenario_provenance(),
        "git": git_provenance(),
    }
    dataset = OfflineDataset(arrays, metadata, gamma=float(gamma))
    # The fixture must satisfy the very check the real dataset is judged by;
    # otherwise it would test a path the real dataset never takes.
    dataset.verify_compatibility(strict=True)
    return dataset


def is_synthetic(dataset_or_metadata: Any) -> bool:
    """True for a dataset built here, by metadata rather than by filename."""
    meta = getattr(dataset_or_metadata, "metadata", dataset_or_metadata)
    if not isinstance(meta, dict):
        return False
    if bool(meta.get("synthetic", False)):
        return True
    policy = meta.get("behaviour_policy") or {}
    return isinstance(policy, dict) and policy.get("kind") == SYNTHETIC_POLICY_KIND


def assert_not_synthetic(dataset_or_metadata: Any, context: str = "") -> None:
    """Refuse to proceed on manufactured data. For any path that reports numbers."""
    if is_synthetic(dataset_or_metadata):
        where = f" ({context})" if context else ""
        raise ValueError(
            f"This is the SYNTHETIC test fixture, not a collected dataset{where}. "
            "It contains manufactured numbers that describe no traffic. Collect a "
            "real dataset with `python -m src.hoorl_offline` and point "
            "PAPER4_HOORL_OFFLINE_DATASET at it."
        )


def write_synthetic_dataset(
    npz_path: str, n_transitions: int = DEFAULT_N_TRANSITIONS, **kwargs: Any
) -> Tuple[str, str]:
    """Build one and write it, with its metadata. Returns (npz_path, meta_path).

    Used by the test fixture, which regenerates it into a temporary directory on
    every session rather than keeping one in the repository. That is what makes
    "the constants are current" a property of the code instead of a promise
    somebody has to remember to renew.
    """
    dataset = build_synthetic_dataset(n_transitions=n_transitions, **kwargs)
    paths = dataset.save(npz_path)
    logger.info("wrote a SYNTHETIC HOORL dataset of %d transitions to %s",
                len(dataset), paths[0])
    return paths


def main(argv: Optional[Any] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="Regenerate the SYNTHETIC HOORL offline dataset used by the tests. "
                    "This is NOT a collection; see src/hoorl_offline.py for that.",
    )
    p.add_argument("--out", required=True, help="npz path; metadata goes beside it")
    p.add_argument("--n-transitions", type=int, default=DEFAULT_N_TRANSITIONS)
    p.add_argument("--num-channels", type=int, default=4)
    p.add_argument("--seed", type=int, default=20260906)
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    npz_path, meta_path = write_synthetic_dataset(
        os.path.abspath(args.out),
        n_transitions=int(args.n_transitions),
        num_channels=int(args.num_channels),
        seed=int(args.seed),
    )
    print(f"SYNTHETIC dataset: {npz_path}\nmetadata:          {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
