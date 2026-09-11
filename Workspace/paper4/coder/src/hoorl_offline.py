# src/hoorl_offline.py
# ============================================================================
# Offline dataset for HOORL's first stage.
#
# J. Xu, X. Zhou, M. Song, W. Wang, D. Niyato and C. Yuen, "AoI and Energy-Aware
# Resource Scheduling for Crowdsensing: A Hybrid Reinforcement Learning
# Framework," IEEE TVT 75(8), pp. 18102--18115, 2026. DOI: 10.1109/TVT.2026.3675626
#
# ---------------------------------------------------------------------------
# WHY THIS MODULE EXISTS AT ALL
# ---------------------------------------------------------------------------
# HOORL learns offline from a previously collected dataset and then continues
# online. Offline reinforcement learning is only defined relative to a KNOWN
# behaviour policy: every offline method reasons about how far the learned policy
# has drifted from the one that produced the data, and that reasoning is vacuous
# if nobody can say what produced the data. So the behaviour policy is written
# down here as code, its parameters are recorded in the dataset's metadata, and
# the collection is reproducible from that metadata alone.
#
# ---------------------------------------------------------------------------
# WHY NOT REUSE ANOTHER BASELINE'S TRAINING LOG
# ---------------------------------------------------------------------------
# Because a learner's replay buffer is not a dataset from a fixed policy. Its
# contents were produced by a policy that changed continuously while it was being
# filled, and by exploration schedules that were annealing at the same time, so
# the distribution shift between "the behaviour policy" and the learned policy is
# neither stationary nor measurable. Pretraining on that and calling the result
# HOORL would reproduce something the paper does not describe.
#
# ---------------------------------------------------------------------------
# THE BEHAVIOUR POLICY
# ---------------------------------------------------------------------------
# A documented fixed-period heuristic, per the specification in
# librarian/baselines_v2.json (`xu2026`, `implementability`):
#
#     Delta    = a FIXED value, the same at every decision epoch
#     channel  ~ Uniform{0, ..., num_channels - 1}
#     power    ~ Uniform[p_min, p_max]        (dBm, the decoder's own range)
#
# `delta_fixed` has NO default. The specification says "a fixed value" without
# saying which, and a default here would silently become the answer.
#
# HONEST LIMITATION, STATED WHERE IT CANNOT BE MISSED: with a single fixed Delta
# the dataset has ZERO coverage of the Delta axis. Every transition in it was
# taken at the same silence interval, so no offline method can learn anything
# about how the return varies with Delta -- it can only learn about the channel
# and the power at that one interval. `delta_jitter` is provided so that the
# collection can instead draw Delta log-uniformly inside a band around the fixed
# value, which keeps the behaviour policy fully documented and known while giving
# the Delta axis non-zero support. It defaults to 0.0, i.e. the literal
# specification, and the value used is recorded in the metadata either way.
#
# ---------------------------------------------------------------------------
# WHAT THE METADATA PINS DOWN
# ---------------------------------------------------------------------------
# The behaviour-policy parameters, the transition count, the density mix, the
# seeds, AND two things that are not properties of the collection but of the code
# that ran it:
#
#   * the git commit hash at collection time, and whether the tree was dirty;
#   * `N_ACTIVE_MAX_OBS`, together with the rest of the observation-normalising
#     constants.
#
# The second one is the reason this section exists. If the observation
# normalisation changes, every stored state vector silently means something
# different from what a freshly built model will produce, and the dataset is
# void -- but nothing about the file itself would show it. `verify_compatibility`
# turns that into a loud failure at load time. The same failure mode has already
# invalidated a hyper-parameter search in this project once.
# ============================================================================

from __future__ import annotations

import argparse
import gc
import json
import logging
import math
import os
import random
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from src.sumo.make_sumo_set import road_seed as _road_seed
from src.rl_interface import (
    observation_constants_live as rli_observation_constants_live,
)
from src.rl_interface import RAW_OBSERVATION_FIELDS
from src.rl_interface import observation_constants_live as rli_observation_constants_live
from src.rl_interface import (
    ActionDecoder,
    N_ACTIVE_MAX_OBS,
    STATE_DIM,
    RetrospectiveReplayBuffer,
)

logger = logging.getLogger(__name__)

#: Version of the on-disk layout. Bump it when a stored column changes meaning.
#:
#: 2 (2026-09-06, morning) added `close_reason` and the two subchannel-occupancy
#: columns, on a 17-dimensional observation and with no raw columns.
#: 3 (2026-09-06, evening) is the 21-dimensional observation with the raw
#: columns, `cell_index` and the relative per-channel features.
#:
#: WHY 3 AND NOT 2 AGAIN. The bump to 2 was DECIDED for a change that also
#: included the state going to 21 and the raw columns, and then a collection was
#: taken after only the first third of that change had landed. So a version-2
#: file on disk may be either thing, and a loader that branches on the number
#: cannot tell them apart. Leaving both at 2 and branching on which columns are
#: present would work, but then the version number decides nothing and may as
#: well not exist.
#:
#: THE FILE WRITTEN AT 12:52 KEEPS ITS 2. Rewriting a number in a file that has
#: already been read is worse than the ambiguity: anything that recorded "version
#: 2" would then disagree with the file. `contents_manifest` below is what makes
#: that file self-describing without touching it.
#:
#: A version-1 or -2 file simply lacks the newer columns, and `OfflineDataset`
#: reports them as ABSENT rather than filling a value. Filling would repeat the
#: mistake three other columns already made here: a zero behaviour
#: log-probability reads as "chosen with probability one", a zero action index
#: reads as "used subchannel 0", and a zero occupancy would read as "that channel
#: was idle" when the truth is "nobody recorded it".
#: 5 as of 2026-09-07. The bump does NOT record a new column: it records that a
#: format-5 file was collected under a DIFFERENT ENVIRONMENT from a format-4 one,
#: and the two must never be pooled.
#:
#:   * correlated shadowing was repaired, so retransmissions are no longer
#:     independent channel draws. Packet loss at density 25 measured 0.0666 before
#:     and 0.0889 after, i.e. every earlier delivery figure was optimistic by
#:     about a third;
#:   * `CBR_REF` went from 0.60 to 0.02, so the congestion term of the reward is
#:     about thirty times larger and no reward is comparable across the boundary;
#:   * a vehicle entering mid-episode has its ledger timestamp paired with the
#:     position it was read with.
#:
#: The raw columns absorb a changed normalisation constant; they cannot absorb a
#: changed physical model or a changed reward, because the stored `reward` and
#: `next_state` were produced under the old ones. That is the difference between
#: a file that can be renormalised and a file that must be recollected.
DATASET_FORMAT_VERSION: int = 5

#: The format version from which recording each constant became mandatory.
#:
#: WHY A VERSION ALONE IS NOT ENOUGH. The rule "a file at the current format must
#: record every constant, so a gap is a collector defect" assumes the format
#: number rises whenever a constant is added. It did not:
#: `DIST_TO_STOPLINE_REF_M` was introduced four hours after the format-3
#: collection of 2026-09-06 18:17, so that file is format 3 and legitimately
#: cannot know about it -- yet the rule would have called it defective and
#: blocked 128,223 transitions.
#:
#: The fix is to make the version track what it claims to track. Adding a
#: constant now bumps `DATASET_FORMAT_VERSION` and adds a row here, so "was this
#: file written before the constant existed" has an exact answer instead of an
#: assumed one. A constant absent from this mapping is required from 3, the
#: version at which full recording began.
CONSTANT_REQUIRED_FROM_FORMAT: Dict[str, int] = {
    "DIST_TO_STOPLINE_REF_M": 4,
}
#: Every other constant has been recorded since format 3.
DEFAULT_CONSTANT_REQUIRED_FROM: int = 3


def contents_manifest(arrays: Dict[str, Any], state_dim: int) -> Dict[str, Any]:
    """What this file actually contains, derived from the file itself.

    A version number says which change was INTENDED. This says what ARRIVED, and
    it is computed from the arrays rather than declared alongside them, so it
    cannot claim a column the file does not have. That distinction is not
    hypothetical: the 12:52 collection carries `format_version: 2` for a change
    that was two thirds unimplemented at the time.

    Everything a reader needs in order to decide whether the file is usable is
    here, so a consumer never has to know the history behind a version number.
    """
    from src.rl_interface import RAW_OBSERVATION_FIELDS

    present = [k for k in OPTIONAL_ARRAY_KEYS if k in arrays]
    return {
        "state_dim": int(state_dim),
        "optional_columns": present,
        "has_raw_columns": bool({"state_raw", "next_state_raw"} <= set(present)),
        "raw_observation_fields": (
            list(RAW_OBSERVATION_FIELDS) if "state_raw" in present else []),
        "raw_action_fields": list(RAW_ACTION_FIELDS) if "action_raw" in present else [],
        "has_cell_index": "cell_index" in present,
        "per_channel_features_are_relative_to_mean": int(state_dim) >= 21,
        "note": (
            "Derived from the arrays, not declared. `format_version` records "
            "which change was intended; this records what the file holds. They "
            "disagree for the collection of 2026-09-06 12:52, which carries "
            "version 2 with a 17-wide observation and no raw columns because the "
            "version was raised before the rest of that change landed."
        ),
    }

#: Columns introduced after version 1. Absent from an older file, never defaulted.
#:
#: `state_raw`, `next_state_raw` and `action_raw` are what make this dataset
#: survive a change to a normalisation bound. Three of the twenty-one observation
#: features destroy information -- the stop-line distance is clipped at
#: `rsu_range`, the in-coverage count at `N_ACTIVE_MAX_OBS`, and the signal
#: character is collapsed into a three-way one-hot -- and the action's Delta is
#: stored as a unit coordinate whose meaning in SECONDS depends on `DELTA_MAX`.
#: With the raw values beside them, moving any of those bounds is a matter of
#: re-reading the file rather than repeating a 21-minute collection.
#:
#: The NORMALISED vectors are still stored, and the redundancy is the point: the
#: normalised value recomputed from the raw one must reproduce what was stored,
#: and if it does not then the offline path and the online path have reached
#: different normalisation code. That is a fact worth learning immediately rather
#: than from a training curve.
OPTIONAL_ARRAY_KEYS: Tuple[str, ...] = (
    "close_reason",
    "cbr_used_channel",
    "cbr_max_channel",
    "state_raw",
    "next_state_raw",
    "action_raw",
    "cell_index",
)

#: `action_raw` columns: the grant in the units the environment was given, before
#: `ActionDecoder.encode_action` turned it into unit coordinates.
#:
#: Delta is stored in SECONDS. The stored `action` column holds a logit whose
#: inverse depends on `delta_min` and `delta_max`, so a dataset that recorded
#: only that would silently re-interpret every action if the decoder's range
#: moved -- a stored 0.5 would stop meaning 2.1 s and start meaning something
#: else, with the reward and next state still describing the original interval.
RAW_ACTION_FIELDS: Tuple[str, ...] = ("delta_s", "power_dbm")

#: How an SMDP interval ended. Stored as a small integer per transition.
#:
#: Until 2026-09-06 the dataset stored no reason at all, and the analysis of the
#: 757 sub-band Delta samples had to INFER truncation from the `done` flag. That
#: inference is indirect and it is not equivalent: `done` is about the vehicle
#: leaving the observation, while what the Delta analysis needed to know was
#: whether the interval the action requested actually completed.
CLOSE_REASON_TRANSMITTED: int = 0     # a report landed; the requested Delta ran out
CLOSE_REASON_COVERAGE_EXIT: int = 1   # the vehicle left RSU range first
CLOSE_REASON_EPISODE_BOUNDARY: int = 2  # finalised because the episode ended
CLOSE_REASON_LABELS: Dict[int, str] = {
    CLOSE_REASON_TRANSMITTED: "transmitted",
    CLOSE_REASON_COVERAGE_EXIT: "coverage_exit",
    CLOSE_REASON_EPISODE_BOUNDARY: "episode_boundary",
}

#: Columns stored in the npz, in the order the loader expects them.
ARRAY_KEYS: Tuple[str, ...] = (
    "state",
    "action",
    "reward",
    "next_state",
    "done",
    "delta_t",
    "action_idx",
    "behaviour_log_prob",
)


# ---------------------------------------------------------------------------
# Behaviour policy
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FixedPeriodBehaviourPolicy:
    """The documented logging policy. Every field is recorded in the metadata.

    `log_prob` returns the log density of the CHANNEL and POWER factors only.
    That is not an omission and it is not a bug:

      * the channel is a fair draw over `num_channels`, so its log-probability is
        -log(num_channels);
      * the power is uniform on [p_min, p_max] in dBm, and the stored action is
        the unit coordinate of that same linear range, so its density in unit
        coordinates is exactly 1 and contributes 0;
      * Delta is DETERMINISTIC when `delta_jitter == 0`, so its distribution is a
        point mass whose density with respect to Lebesgue measure does not exist.
        There is no finite number to store. With `delta_jitter > 0` Delta is
        log-uniform inside the band, which in the decoder's unit coordinate is
        again uniform, so it contributes a finite constant and IS included.

    A consumer that needs a full joint density must therefore know which case it
    is in; `delta_component_defined` says so, and the metadata records it.
    """

    #: Geometric CENTRE of the Delta band. Named `delta_fixed` until 2026-09-07,
    #: which described the policy as originally specified -- one fixed Delta --
    #: and stopped being true when the band was widened. No transition takes this
    #: value; it is the midpoint of the interval they are drawn from.
    delta_band_center: float
    num_channels: int
    p_min: float
    p_max: float
    #: Half-width of the Delta band IN LOG SPACE, so the band is
    #: [center * exp(-h), center * exp(+h)] clipped to the decoder's range. 0.0
    #: reproduces the literal specification, a single Delta with zero coverage of
    #: the Delta axis. Named `delta_jitter` until 2026-09-07: "jitter" suggests a
    #: small perturbation around a nominal value, while the value in use is 1.498,
    #: which spans [0.5, 10] s -- a band covering the action range, not a wobble.
    delta_log_halfwidth: float = 0.0

    #: Read-only aliases for the two names above. Datasets collected before
    #: 2026-09-07 record the old keys in their metadata and scripts outside this
    #: file read them, so removing the names outright would break files that are
    #: still valid. They are properties rather than fields so nothing can be
    #: constructed under the old spelling and drift from the new one.
    @property
    def delta_fixed(self) -> float:
        return self.delta_band_center

    @property
    def delta_jitter(self) -> float:
        return self.delta_log_halfwidth

    @property
    def delta_component_defined(self) -> bool:
        return self.delta_log_halfwidth > 0.0

    def delta_band(self, decoder: ActionDecoder) -> Tuple[float, float]:
        """The [low, high] Delta band, clipped to the decoder's own range."""
        if not self.delta_component_defined:
            return (float(self.delta_band_center), float(self.delta_band_center))
        lo = max(float(decoder.delta_min), self.delta_band_center * math.exp(-self.delta_log_halfwidth))
        hi = min(float(decoder.delta_max), self.delta_band_center * math.exp(self.delta_log_halfwidth))
        if hi < lo:
            lo = hi = float(min(max(self.delta_band_center, decoder.delta_min), decoder.delta_max))
        return (lo, hi)

    def sample(
        self, rng: np.random.Generator, decoder: ActionDecoder
    ) -> Tuple[Tuple[float, int, float], int, float]:
        """Draw one grant. Returns ((Delta, ch, power), ch, behaviour log-prob)."""
        lo, hi = self.delta_band(decoder)
        if hi > lo:
            delta = float(np.exp(rng.uniform(math.log(lo), math.log(hi))))
        else:
            delta = float(lo)
        ch = int(rng.integers(0, int(self.num_channels)))
        power = float(rng.uniform(self.p_min, self.p_max))
        return (delta, ch, power), ch, self.log_prob()

    def log_prob(self) -> float:
        """Log density of one draw, in the unit coordinates the decoder uses.

        Channel: -log(num_channels). Power: uniform on the unit interval, density
        1, contributing 0. Delta: included only when the band is non-degenerate,
        where it is uniform over a sub-interval of the unit coordinate of width
        `w`, contributing -log(w). Since the exact `w` depends on the decoder's
        range, the Delta term is folded in by `_delta_unit_width` at collection
        time and stored per transition; this method returns the part that does
        not depend on the decoder.
        """
        return -math.log(float(self.num_channels))


def _delta_unit_log_density(policy: FixedPeriodBehaviourPolicy, decoder: ActionDecoder) -> float:
    """The Delta factor's contribution to the behaviour log density, or 0.0.

    Log-uniform Delta over [lo, hi] is uniform in the decoder's unit coordinate
    (the mapping is exponential), and the unit width of that band is
    (log hi - log lo) / log(delta_max / delta_min). Its log density is therefore
    -log(width). Returns 0.0 for the degenerate single-Delta case, where the
    factor has no density at all; `delta_component_defined` is what tells a
    consumer which of the two it is looking at.
    """
    if not policy.delta_component_defined:
        return 0.0
    lo, hi = policy.delta_band(decoder)
    if hi <= lo:
        return 0.0
    full = math.log(float(decoder.delta_max) / float(decoder.delta_min))
    if full <= 0.0:
        return 0.0
    width = (math.log(hi) - math.log(lo)) / full
    return -math.log(max(width, 1e-12))


# ---------------------------------------------------------------------------
# Dataset container
# ---------------------------------------------------------------------------
class OfflineDataset:
    """An in-memory offline dataset that samples like `RetrospectiveReplayBuffer`.

    `sample()` emits EXACTLY the key set and tensor shapes that
    `RetrospectiveReplayBuffer.sample` emits, so a model cannot tell the two
    apart and the offline and online stages consume one batch contract. The
    discount column is recomputed here from this dataset's own gamma for the same
    reason the buffer computes one; every baseline in this project prefers
    `delta_t` and its own gamma anyway (`BaseRLModel.smdp_discounts`).
    """

    def __init__(
        self,
        arrays: Dict[str, np.ndarray],
        metadata: Dict[str, Any],
        gamma: float = 0.99,
    ) -> None:
        missing = [k for k in ARRAY_KEYS if k not in arrays]
        if missing:
            raise KeyError(f"offline dataset is missing columns {missing}")
        n = int(arrays["state"].shape[0])
        # The optional columns arrived in format version 2. A version-1 file has
        # none of them, and that is recorded as ABSENCE. Nothing is filled in:
        # a zero `close_reason` would claim every interval ended in a
        # transmission, and a zero occupancy would claim an idle channel, so a
        # default here would be a false statement about the data rather than a
        # missing one.
        present_optional = [k for k in OPTIONAL_ARRAY_KEYS if k in arrays]
        for key in list(ARRAY_KEYS) + present_optional:
            if int(arrays[key].shape[0]) != n:
                raise ValueError(
                    f"column {key!r} has {arrays[key].shape[0]} rows, expected {n}"
                )
        self.optional_columns: Tuple[str, ...] = tuple(present_optional)
        self.arrays = {k: np.asarray(arrays[k])
                       for k in list(ARRAY_KEYS) + present_optional}
        self.metadata = dict(metadata)
        self.gamma = float(gamma)
        self._n = n

    def __len__(self) -> int:
        return self._n

    # -- renormalisation ---------------------------------------------------
    def per_row_constants(self) -> Dict[str, np.ndarray]:
        """The normalising constants each row was collected under, as columns.

        Joined through `cell_index`: the scenario-derived constants `V_MAX_OBS`
        and `E_REF` are read off the generated road, so a collection that visited
        several roads normalised its rows against several values. Using one set
        for all of them reproduces only the last cell and leaves the rest wrong by
        a small systematic amount -- measured at 3.2e-3 on a [-1, 1] feature the
        first time this was tried.
        """
        if "cell_index" not in self.arrays:
            raise KeyError(
                "this dataset has no `cell_index`, so a row cannot be joined to "
                "the constants that normalised it. Format-1 and -2 files must be "
                "recollected before they can be renormalised."
            )
        per_cell = {int(r["cell_index"]): r.get("observation_constants")
                    for r in self.metadata.get("per_episode", [])}
        missing = [c for c, v in per_cell.items() if not v]
        if missing:
            raise KeyError(
                f"cells {sorted(missing)} record no observation_constants; the "
                "collection predates per-cell constants and cannot be renormalised."
            )
        cells = np.asarray(self.arrays["cell_index"], dtype=int)
        keys = sorted(next(iter(per_cell.values())))
        out = {k: np.array([float(per_cell[int(c)][k]) for c in cells]) for k in keys}
        # A constant introduced after this collection has no recorded value, and
        # the live one is substituted so the caller can still rebuild. The
        # identity check cannot cover those features -- there is nothing to
        # reproduce -- and `unverifiable_constants` says which, so a report can
        # state what it did not check instead of implying it checked everything.
        from src.rl_interface import observation_constants_live

        live = observation_constants_live()
        self.unverifiable_constants = sorted(set(live) - set(out))
        for k in self.unverifiable_constants:
            out[k] = np.full(cells.shape[0], float(live[k]))
        return out

    def renormalised_states(self, target_constants: Optional[Dict[str, float]] = None,
                            key: str = "state") -> np.ndarray:
        """The state matrix under a DIFFERENT set of normalising constants.

        This is what the raw columns are for. `target_constants=None` means the
        constants live in this process, i.e. "re-read this dataset under the
        bounds the code uses now", which is the case that lets a bound move
        without a new collection.
        """
        from src.rl_interface import observation_constants_live, renormalise_states

        raw_key = "state_raw" if key == "state" else "next_state_raw"
        if raw_key not in self.arrays:
            raise KeyError(
                f"this dataset has no `{raw_key}`; only a format-3 collection can "
                "be renormalised."
            )
        target = target_constants or observation_constants_live()
        return renormalise_states(self.arrays[key], self.arrays[raw_key], target)

    def reconcile_to_current_constants(self, atol: float = 1e-5) -> Dict[str, Any]:
        """Bring the stored vectors up to date with the constants in force NOW.

        THIS IS WHAT THE RAW COLUMNS ARE FOR, and until it existed they were
        storage with no consumer. `verify_compatibility` refuses a dataset whose
        recorded constants differ from the live ones, which is right for a
        dataset that cannot be repaired -- and wrong for one that can. A format-3
        file carries the pre-normalisation values, so a changed bound is a reason
        to RE-DERIVE the affected features, not to discard 128,000 transitions
        and spend twenty minutes collecting them again.

        The distinction it draws is between constants that can be re-applied and
        constants that cannot. `RENORMALISABLE_FEATURES` lists the first kind. A
        change to anything else -- the observation width, the meaning of a column
        -- is not a rescaling and this refuses it, because re-deriving would
        require information the file does not hold.

        Returns a report rather than mutating quietly. A run whose dataset was
        renormalised on load is not the same as one whose dataset already
        matched, and the difference has to reach the run log.
        """
        from src.rl_interface import (RENORMALISABLE_FEATURES,
                                      constants_safe_to_rescale,
                                      observation_constants_live)

        stored = self.metadata.get("observation_constants", {})
        live = observation_constants_live()
        # EVERY constant a run uses must have a declared role before any of them
        # is re-applied. `constants_safe_to_rescale` raises on one that does not,
        # and calling it here is what makes the role table load-bearing rather
        # than advisory -- it had no caller at all until 2026-09-07, which is the
        # state this project keeps rediscovering: a module that is complete,
        # correct and unreachable.
        safe = set(constants_safe_to_rescale(set(live) | set(stored)))
        renormalisable = {name for _j, name in RENORMALISABLE_FEATURES if name}
        #: Constants that normalise a feature AND do something else. They are
        #: re-derivable in the mechanical sense and must not be re-derived; see
        #: the branch below for why the two are different questions.
        dual_role = renormalisable - safe
        moved, blocking, tolerated = {}, {}, {}
        has_raw = bool(self.metadata.get("contents_manifest", {}).get("has_raw_columns"))
        for key, now in live.items():
            was = stored.get(key)
            if was is None:
                # NOT RECORDED is repairable for a re-derivable constant, and
                # this is the ordinary case for a constant that did not exist at
                # collection time. `DIST_TO_STOPLINE_REF_M` was introduced on
                # 2026-09-06 to separate feature [12]'s divisor from the coverage
                # radius; the collection two hours earlier could not have
                # recorded it, and yet its raw stop-line distances are exactly
                # what the new divisor needs. Re-deriving needs the NEW constant
                # and the RAW value; the old constant is required only to check
                # the identity case, which is not available here and is reported
                # as such rather than assumed.
                # TWO KINDS OF "NOT RECORDED", and only one is innocent.
                #
                # A constant introduced AFTER a collection cannot appear in that
                # collection's metadata. `DIST_TO_STOPLINE_REF_M` was created two
                # hours after the file that needs it, and re-deriving needs the
                # NEW constant and the RAW value, not the old constant -- so the
                # absence is expected and repairable.
                #
                # A constant that existed at collection time and is missing is a
                # COLLECTOR BUG, and the repair would hide it: every load would
                # renormalise, every result would be correct, and nobody would
                # learn that the writer is dropping a field. The format version
                # separates the two. A file at version 3 or later was written by a
                # collector that records `observation_constants_live()` in full,
                # so a gap there is a defect and blocks; an older file may have
                # legitimate gaps.
                #
                # The writing side is checked too, at collection time, because
                # "the reader can repair it" is not a licence for the writer to be
                # wrong.
                fmt = int(self.metadata.get("format_version", 0))
                required_from = CONSTANT_REQUIRED_FROM_FORMAT.get(
                    key, DEFAULT_CONSTANT_REQUIRED_FROM)
                predates = fmt < required_from
                if key in renormalisable and has_raw and predates:
                    moved[key] = ["not recorded (constant introduced at format "
                                  f"{required_from}, file is format {fmt})", float(now)]
                elif key in renormalisable and has_raw:
                    blocking[key] = [
                        f"not recorded, and this file is format {fmt} while {key} "
                        f"has been mandatory since format {required_from}. The gap "
                        "is a collector defect rather than a constant introduced "
                        "later, and renormalising would conceal it", now]
                else:
                    blocking[key] = ["not recorded", now]
                continue
            if math.isclose(float(was), float(now), rel_tol=1e-9, abs_tol=1e-12):
                continue
            if key not in renormalisable:
                blocking[key] = [float(was), float(now)]
            elif key in dual_role:
                # ----------------------------------------------------------
                # A CONSTANT WITH A SECOND ROLE IS NOT RE-DERIVED, EVEN THOUGH
                # IT COULD BE.
                # ----------------------------------------------------------
                # `E_REF` normalises feature [0] AND is the reward's error term.
                # Re-deriving [0] under the new value while `reward` keeps the
                # number computed under the old one leaves the two describing
                # different scales, and an offline learner reads exactly that
                # pair: it would learn "this much error goes with this much
                # reward" from a relation the data no longer holds. Leaving [0]
                # at the constant it was collected under keeps the observation
                # and the reward consistent WITH EACH OTHER, which is the
                # relation being learned; the remaining difference from the live
                # constant is a scale offset in the initialisation that the
                # online stage goes on to correct.
                #
                # THE REASON IS THE SECOND ROLE, NOT STABILITY. `E_REF` moves --
                # 13.33 to 13.27 between two scenarios, 0.45 % -- and it is
                # skipped anyway. `RSU_RANGE` is here for the same reason and a
                # sharper one: it decides which vehicles are inside coverage at
                # all, so a changed value does not rescale an observation, it
                # describes a different population.
                #
                # Only a difference small enough to be scenario-to-scenario
                # variation is tolerated. Anything larger is a real change of
                # meaning and blocks, because then the stored reward and the live
                # constant disagree about more than sampling.
                rel_tol = (SCENARIO_CONSTANT_REL_TOL
                           if CONSTANT_ORIGIN.get(key) == "scenario" else 1e-9)
                if math.isclose(float(was), float(now), rel_tol=rel_tol,
                                abs_tol=1e-12):
                    tolerated[key] = [float(was), float(now)]
                else:
                    blocking[key] = [float(was), float(now)]
            else:
                moved[key] = [float(was), float(now)]

        report: Dict[str, Any] = {
            "constants_moved": moved, "constants_blocking": blocking,
            "constants_kept_at_collection_value": tolerated,
            "renormalised": False, "n_transitions": int(len(self)),
        }
        if blocking:
            report["reason"] = (
                "these constants changed and are not re-derivable from the stored "
                "raw columns, so the dataset must be recollected: "
                f"{sorted(blocking)}")
            return report
        if not moved:
            # Nothing to re-derive. Say which of the two cases that is: a file
            # that already matched, or one whose only differences are in
            # constants deliberately left at their collection value.
            report["reason"] = (
                "every recorded constant already matches the live one"
                if not tolerated else
                f"{sorted(tolerated)} differ but carry a second role, so they are "
                "kept at their collection value rather than re-derived; nothing "
                "else changed")
            return report
        if not has_raw:
            report["reason"] = (
                f"{sorted(moved)} changed and this file has no raw columns, so the "
                "affected features cannot be re-derived. Recollect.")
            return report

        # The tolerated constants are re-applied AT THEIR COLLECTION VALUE, so
        # their features come back exactly as stored while everything else moves.
        #
        # PER ROW, NOT AS ONE NUMBER. Both tolerated constants are scenario-drawn,
        # and a collection spans several roads, so the value a row was normalised
        # under is the value of ITS cell. Substituting the single figure recorded
        # in the file's metadata reproduces one cell and leaves every other cell
        # shifted by a small systematic amount -- which defeats the point of
        # keeping the constant, since the whole reason it is kept is that the
        # feature and the stored reward must agree.
        target = dict(live)
        if tolerated:
            per_row = self.per_row_constants()
            for key in tolerated:
                target[key] = per_row[key]
        for key in ("state", "next_state"):
            self.arrays[key] = self.renormalised_states(target, key=key)
        # RECORDED AS SCALARS. `target` carries per-row columns for the tolerated
        # constants, which is right for the rebuild and wrong for the metadata: a
        # 128,000-long array does not belong in a header, and every reader of
        # `observation_constants` expects one number per name. The scalar to
        # record is the one already in the file, since that is what the vectors
        # now carry.
        recorded = dict(live)
        for key, (was, _now) in tolerated.items():
            recorded[key] = float(was)
        self.metadata["observation_constants"] = recorded
        self.metadata["renormalised_on_load"] = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "constants_moved": moved,
            "constants_kept_at_collection_value": tolerated}
        report["renormalised"] = True
        report["reason"] = (
            f"re-derived the features depending on {sorted(moved)} from the raw "
            "columns; the collection itself is unchanged and still valid")
        return report

    def verify_raw_columns(self, atol: float = 1e-5) -> Dict[str, Any]:
        """Rebuild with the collection's OWN constants; the result must match.

        Run on every dataset that is about to be used, not only in tests: it is
        the one check that the raw columns and the normalised ones describe the
        same observation.

        IT IS ONLY MEANINGFUL BEFORE `reconcile_to_current_constants`. The
        comparison rebuilds from raw using the constants RECORDED IN THE FILE, so
        it holds only while the stored vectors still carry the normalisation
        those constants produced. Run it after reconciliation and it compares
        current-constant vectors against collection-time constants and fails for
        a reason that says nothing about the raw columns -- which is exactly what
        happened on 2026-09-07 when a measurement script was asked to report on
        reconciled data and moved this call after the reconcile. The failure
        looks like a broken dataset and is a broken order.

        BOTH HALVES OF EVERY TRANSITION ARE CHECKED. This verified `state` alone
        until 2026-09-07, and the half it skipped was the half that was broken:
        `next_state_raw` is NaN in all nineteen fields for the 3,639 terminal
        transitions, so reconciliation rebuilt those successors as NaN while
        `state` came out clean and the check reported a match. The failure
        surfaced two stages later, as NaN IQL losses and a rollout dying inside a
        `torch.multinomial`. A verification that covers half the columns reports
        on the half that happens to be right.
        """
        from src.rl_interface import verify_renormalisation

        from src.rl_interface import RENORMALISABLE_FEATURES

        constants = self.per_row_constants()

        # Features whose constant this file never recorded cannot be verified
        # against it. They are removed from the verdict and named, because a
        # check that quietly counted them would be reporting agreement with a
        # value it had supplied itself.
        unverifiable = set(getattr(self, "unverifiable_constants", ()))
        skipped = sorted(j for j, name in RENORMALISABLE_FEATURES
                         if name in unverifiable)

        def _verify(states_key: str, raw_key: str) -> Dict[str, Any]:
            rep = verify_renormalisation(self.arrays[states_key],
                                         self.arrays[raw_key], constants, atol=atol)
            for j in skipped:
                rep["per_feature_abs_error"].pop(int(j), None)
            errors = rep["per_feature_abs_error"]
            worst = max(errors.values()) if errors else 0.0
            rep["matches"] = bool(worst <= atol)
            rep["worst_abs_error"] = worst
            rep["worst_feature"] = int(max(errors, key=errors.get)) if errors else -1
            return rep

        report = _verify("state", "state_raw")
        report["state_only_matches"] = bool(report["matches"])
        if "next_state_raw" in self.arrays:
            nxt = _verify("next_state", "next_state_raw")
            report["next_state"] = {k: nxt[k] for k in
                                    ("matches", "worst_abs_error", "worst_feature",
                                     "per_feature_abs_error")}
            report["matches"] = bool(report["matches"] and nxt["matches"])
        else:
            report["next_state"] = None
        report["unverifiable_constants"] = sorted(unverifiable)
        report["features_not_verified"] = skipped
        return report

    @property
    def state_dim(self) -> int:
        return int(self.arrays["state"].shape[1])

    def sample(self, batch_size: int) -> Dict[str, torch.Tensor]:
        if self._n == 0:
            raise ValueError("Cannot sample from an empty offline dataset.")
        size = min(int(batch_size), self._n)
        idx = np.random.choice(self._n, size, replace=False)
        delta_t = self.arrays["delta_t"][idx].astype(np.float32).reshape(-1, 1)
        out = {
            "state": torch.from_numpy(self.arrays["state"][idx].astype(np.float32)),
            "action": torch.from_numpy(self.arrays["action"][idx].astype(np.float32)),
            "reward": torch.from_numpy(self.arrays["reward"][idx].astype(np.float32).reshape(-1, 1)),
            "next_state": torch.from_numpy(self.arrays["next_state"][idx].astype(np.float32)),
            "done": torch.from_numpy(self.arrays["done"][idx].astype(np.float32).reshape(-1, 1)),
            "delta_t": torch.from_numpy(delta_t),
            "discount": torch.from_numpy(np.power(self.gamma, delta_t).astype(np.float32)),
            "action_idx": torch.from_numpy(self.arrays["action_idx"][idx].astype(np.int64).reshape(-1)),
            "behaviour_log_prob": torch.from_numpy(
                self.arrays["behaviour_log_prob"][idx].astype(np.float32).reshape(-1, 1)
            ),
        }
        return out

    # -- persistence -------------------------------------------------------
    def save(self, npz_path: str) -> Tuple[str, str]:
        """Write the arrays and a sibling `<name>.meta.json`. Returns both paths."""
        npz_path = os.path.abspath(npz_path)
        os.makedirs(os.path.dirname(npz_path), exist_ok=True)
        np.savez_compressed(npz_path, **self.arrays)
        meta_path = os.path.splitext(npz_path)[0] + ".meta.json"
        with open(meta_path, "w") as fh:
            json.dump(self.metadata, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        return npz_path, meta_path

    @classmethod
    def load(cls, npz_path: str, gamma: float = 0.99) -> "OfflineDataset":
        npz_path = os.path.abspath(npz_path)
        meta_path = os.path.splitext(npz_path)[0] + ".meta.json"
        if not os.path.exists(meta_path):
            raise FileNotFoundError(
                f"{npz_path} has no sibling metadata at {meta_path}. An offline dataset "
                "whose behaviour policy and observation normalisation are unknown cannot "
                "be used for offline reinforcement learning; recollect it."
            )
        with np.load(npz_path) as data:
            arrays = {k: data[k] for k in ARRAY_KEYS}
            # Present only in format version 2 and later. Absent is absent.
            for key in OPTIONAL_ARRAY_KEYS:
                if key in data.files:
                    arrays[key] = data[key]
        with open(meta_path) as fh:
            metadata = json.load(fh)
        return cls(arrays, metadata, gamma=gamma)

    # -- validity ----------------------------------------------------------
    def verify_compatibility(self, strict: bool = True) -> List[str]:
        """Complaints about using this dataset with the CURRENT code.

        The stored observation width and the observation-normalising constants
        are compared against what this process would produce now. A mismatch
        means every state vector in the file denotes something different from
        what a freshly constructed model will see, which voids the dataset
        silently unless it is checked. `strict` raises instead of returning.
        """
        problems: List[str] = []
        stored_dim = int(self.metadata.get("state_dim", -1))
        if stored_dim != STATE_DIM:
            problems.append(
                f"state_dim: dataset {stored_dim}, current {STATE_DIM}"
            )
        if self.state_dim != STATE_DIM:
            problems.append(
                f"stored state array width {self.state_dim}, current STATE_DIM {STATE_DIM}"
            )
        # A dataset whose constants were recorded before any scenario existed
        # carries the import-time fallbacks, and comparing them against live
        # values produces a difference of 17 % that reads like a redefinition
        # while being nothing of the kind. Named for what it is instead.
        stored_provenance = self.metadata.get("scenario_provenance")
        if isinstance(stored_provenance, dict) and \
                stored_provenance.get("network_present") is False:
            problems.append(
                "scenario_provenance: this dataset's observation constants were "
                "recorded before any SUMO network existed, so they are the "
                "import-time fallbacks and describe no scenario. Recollect after "
                "prepare_scenario()."
            )

        # `require_scenario=False` HERE, and only here.
        #
        # The guard exists to stop the import-time fallbacks being WRITTEN into a
        # dataset, and both write sites know which scenario directory they used.
        # This is a READ, and it does not: the live constants are module globals
        # refreshed by whichever `prepare_scenario` ran last, which may have used
        # an explicit `sumo_dir` that has nothing to do with the process default.
        # `run_hot_swap_training` does exactly that, so raising on "no network in
        # the default directory" rejected a correctly refreshed process for
        # looking in the wrong place -- measured 2026-09-06: V_MAX_OBS was already
        # 15.984 from the run's own scenario when the guard fired.
        #
        # Nothing is lost by softening it. If the constants really ARE unrefreshed
        # they will not match a dataset collected against a real scenario, and the
        # comparison below reports that with both numbers. `_fallback_hint` adds
        # the likely cause to that report rather than asserting it, because the
        # fallback value 13.32 is inside the range real networks produce
        # (13.23 to 13.33 over 90 scenarios) and cannot be identified with
        # certainty from its value alone.
        stored_norm = self.metadata.get("observation_constants", {})
        current_norm = observation_constants(require_scenario=False)
        for key, current in current_norm.items():
            stored = stored_norm.get(key)
            if stored is None:
                problems.append(f"{key}: not recorded in the dataset metadata")
                continue
            # A `code` constant must match exactly; a `scenario` one is a draw
            # from the generated road network and only has to match within the
            # measured, justified tolerance. See CONSTANT_ORIGIN and
            # SCENARIO_CONSTANT_REL_TOL for the measurements behind both.
            origin = CONSTANT_ORIGIN.get(key, "code")
            rel_tol = SCENARIO_CONSTANT_REL_TOL if origin == "scenario" else 1e-9
            if not math.isclose(float(stored), float(current),
                                rel_tol=rel_tol, abs_tol=1e-12):
                problems.append(
                    f"{key} ({origin}): dataset {stored}, current {current}, "
                    f"relative difference "
                    f"{abs(float(stored) - float(current)) / max(abs(float(current)), 1e-12):.4g} "
                    f"exceeds the tolerance {rel_tol:g}"
                )
        hint = _fallback_hint(current_norm, problems)
        if hint:
            problems.append(hint)
        if problems and strict:
            raise ValueError(
                "This offline dataset was collected under a different observation "
                "definition and is void:\n  " + "\n  ".join(problems)
            )
        return problems


def filter_actions_in_range(dataset: "OfflineDataset",
                            decoder: Optional[ActionDecoder] = None
                            ) -> Tuple["OfflineDataset", Dict[str, Any]]:
    """Drop transitions whose raw action lies outside the CURRENT action space.

    ---------------------------------------------------------------------------
    WHY DROPPED AND NOT CLIPPED
    ---------------------------------------------------------------------------
    Clipping produces a transition that lies. A row collected at Delta = 12 s
    carries a reward accumulated over twelve seconds and a next state observed
    twelve seconds later. Rewriting its action to 10 s leaves both untouched, so
    the dataset then asserts that a 10 s silence produced a twelve-second
    penalty and a twelve-second displacement. A learner cannot detect that; it
    will fit it.
    ---------------------------------------------------------------------------
    WHY NOT KEPT EITHER
    ---------------------------------------------------------------------------
    Because the usual protection does not apply here. Implicit Q-learning is
    chosen partly for never querying the value of an action outside the data, but
    the offending action IS inside the data -- that is the whole problem. Its
    being out of the DECODER's range is what makes it unreachable by the policy
    being initialised, so the offline stage would be fitting a return the online
    policy can never obtain.
    ---------------------------------------------------------------------------
    WHAT IS REPORTED, AND WHY A COUNT IS NOT ENOUGH
    ---------------------------------------------------------------------------
    A count invites "one per cent, therefore harmless". It is not harmless if
    that one per cent sits at one end of the Delta axis: a range that shrank at
    the top removes exactly the long silences, and this paper's claim is about
    choosing long silences ahead of time. So the return value carries the Delta
    DISTRIBUTION before and after, in log-spaced bins, plus the shift in its
    geometric mean and in its upper percentiles. No threshold is applied. There
    is no measured basis for one, and a number invented here would be the kind of
    unfounded constant this file has already had to remove three of.
    """
    if "action_raw" not in dataset.arrays:
        raise KeyError(
            "this dataset has no `action_raw`, so the action cannot be compared "
            "against the current range in the units it was issued in. A format-1 "
            "file stores only the decoder's unit coordinate, whose meaning moves "
            "with the range; it must be recollected rather than filtered."
        )
    decoder = decoder or ActionDecoder(num_channels=int(
        dataset.metadata.get("num_channels", 4)))
    delta_s = np.asarray(dataset.arrays["action_raw"][:, 0], dtype=np.float64)
    power = np.asarray(dataset.arrays["action_raw"][:, 1], dtype=np.float64)
    keep = (
        (delta_s >= float(decoder.delta_min) - 1e-9)
        & (delta_s <= float(decoder.delta_max) + 1e-9)
        & (power >= float(decoder.p_min) - 1e-9)
        & (power <= float(decoder.p_max) + 1e-9)
    )
    kept = dict(dataset.arrays)
    kept = {k: v[keep] for k, v in kept.items()}
    filtered = OfflineDataset(kept, dict(dataset.metadata), gamma=dataset.gamma)

    def _profile(a: np.ndarray) -> Dict[str, Any]:
        if a.size == 0:
            return {"n": 0}
        return {
            "n": int(a.size),
            "geomean_s": float(np.exp(np.log(np.maximum(a, 1e-12)).mean())),
            "p50_s": float(np.percentile(a, 50)),
            "p90_s": float(np.percentile(a, 90)),
            "p99_s": float(np.percentile(a, 99)),
            "max_s": float(a.max()),
            "min_s": float(a.min()),
        }

    edges = np.geomspace(max(1e-3, delta_s.min()), max(delta_s.max(), 1e-2), 13)
    before_hist, _ = np.histogram(delta_s, bins=edges)
    after_hist, _ = np.histogram(delta_s[keep], bins=edges)
    report = {
        "decoder_range_s": [float(decoder.delta_min), float(decoder.delta_max)],
        "decoder_power_dbm": [float(decoder.p_min), float(decoder.p_max)],
        "n_before": int(delta_s.size),
        "n_dropped": int((~keep).sum()),
        "fraction_dropped": float((~keep).mean()) if delta_s.size else 0.0,
        "delta_before": _profile(delta_s),
        "delta_after": _profile(delta_s[keep]),
        "delta_bin_edges_s": [float(e) for e in edges],
        "delta_hist_before": [int(x) for x in before_hist],
        "delta_hist_after": [int(x) for x in after_hist],
        "dropped_delta_profile": _profile(delta_s[~keep]),
        "note": (
            "No threshold is applied. Read `dropped_delta_profile` against "
            "`delta_before`: a drop concentrated at one end removes that end of "
            "the Delta axis whatever the count says."
        ),
    }
    return filtered, report


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------
#: Which normalisers are properties of the CODE and which are draws from the
#: GENERATED ROAD NETWORK. The distinction decides how `verify_compatibility`
#: compares them and it is not a matter of taste: `make_sumo_set` randomises each
#: edge's speed limit around `AV_SPEED`, so `V_MAX_OBS = V_LIMIT * speedFactor`
#: and `E_REF = V_LIMIT` are re-drawn every time a network is generated.
#:
#: Measured over 90 scenarios (3 directories x 5 seeds x 3 densities x forced and
#: cached generation) in `results/hoorl_offline/observation_constant_spread.csv`:
#: every `code` constant took exactly ONE value, while `V_MAX_OBS` and `E_REF`
#: each took five, spanning 0.756 % relative. `DELTA_MAX` is scenario-derived in
#: principle -- it is the longest red phase in the generated signal plan -- and
#: took one value across all 90, so it is compared exactly until a scenario is
#: seen that moves it.
CONSTANT_ORIGIN: Dict[str, str] = {
    "N_ACTIVE_MAX_OBS": "code",
    "DELTA_MIN": "code",
    "DELTA_MAX": "code",
    "RSU_RANGE": "code",
    "A_MAX": "code",
    "QUEUE_MAX": "code",
    "PHASE_REMAINING_REF_S": "code",
    "DIST_TO_STOPLINE_REF_M": "code",
    "V_MAX_OBS": "scenario",
    "E_REF": "scenario",
}

#: Relative tolerance for the two scenario-drawn normalisers. NOT a guess and not
#: a convenience: `etc/scripts/measure_normalisation_drift_effect.py` renormalises
#: a real sample of 2,925 observations by a sweep of drifts and measures the
#: resulting state-distribution distance against the split-half sampling floor,
#: which is what a finite sample already scores against itself.
#:
#:      drift    mean normalised W1    as a multiple of the sampling floor
#:      0.00756           0.000335                                   0.035
#:      0.02              0.000877                                   0.092
#:      0.05              0.002131                                   0.223
#:      0.25              0.008974                                   0.940
#:      0.68              0.018243                                   1.912
#:
#: At 2 % the induced change sits at a tenth of the noise a finite sample shows,
#: so no consumer of the dataset can tell the two apart; a drift only becomes
#: detectable at all near 25 %. The tolerance is therefore 2.6x the measured
#: scenario spread of 0.756 % and still an order of magnitude inside the noise.
#:
#: EXACT equality stays in force for every `code` constant, which is where the
#: failure this check exists for actually lives: `N_ACTIVE_MAX_OBS` moving from
#: 100 to 168 redefines feature [13] for every stored row, and that comparison is
#: unchanged.
SCENARIO_CONSTANT_REL_TOL: float = 0.02


def fallback_observation_constants() -> Dict[str, float]:
    """What the scenario-derived normalisers read when NO network exists.

    Computed by pointing the same getters `src.rl_interface` uses at an empty
    directory, so the numbers come from the code's own defaults rather than from
    a copy of them here. `get_sumo_max_edge_speed`'s `default_speed` is one edit
    away from being wrong in a comment and cannot be wrong when it is called.
    """
    import tempfile

    import src.rl_interface as rli

    with tempfile.TemporaryDirectory(prefix="obs_fallback_") as empty:
        v_limit = float(rli.get_sumo_max_edge_speed(base_path=empty))
        factor = float(rli.get_sumo_max_speed_factor(base_path=empty))
        delta_max = float(rli.get_sumo_max_red_phase_duration(base_path=empty))
    return {"V_MAX_OBS": v_limit * factor, "E_REF": v_limit, "DELTA_MAX": delta_max}


def _fallback_hint(current: Dict[str, float], problems: List[str]) -> Optional[str]:
    """A LIKELY-cause note when the live constants look unrefreshed. Never a verdict.

    Offered only when the comparison already failed, and worded as a possibility,
    because the fallback speed of 13.32 m/s sits inside the range real generated
    networks produce -- 13.23 to 13.33 over the 90 scenarios in
    `results/hoorl_offline/observation_constant_spread.csv`. A value alone
    therefore cannot prove the constants were never refreshed, and a check that
    claimed otherwise would sometimes accuse a perfectly good scenario.
    """
    if not problems:
        return None
    fallback = fallback_observation_constants()
    looks_unrefreshed = all(
        math.isclose(float(current.get(key, float("nan"))), float(value),
                     rel_tol=1e-9, abs_tol=1e-12)
        for key, value in fallback.items()
    )
    if not looks_unrefreshed:
        return None
    return (
        "LIKELY CAUSE: the LIVE constants equal the values the code produces when "
        f"no SUMO network exists ({fallback}), so this process may never have run "
        "prepare_scenario() and the mismatch may be in the live values rather "
        "than in the dataset. Not a verdict: that fallback speed is inside the "
        "range real networks produce. Generate the scenario and re-check."
    )


class ScenarioNotGenerated(RuntimeError):
    """The observation normalisers were read before any scenario existed.

    Raised rather than warned about, because the values in that state are the
    import-time fallbacks of an empty directory and are indistinguishable, once
    written into a file, from constants a real scenario produced.
    """


def scenario_provenance(base_path: Optional[str] = None) -> Dict[str, Any]:
    """WHICH scenario the normalisers were read from, and whether one existed.

    `V_MAX_OBS`, `E_REF` and `DELTA_MAX` are module-level values computed once
    when `src.rl_interface` is imported, by parsing `generated.net.xml`. With no
    such file, `get_sumo_max_edge_speed` returns its `default_speed` of 13.32 and
    the other two fall back likewise, and `refresh_scenario_constants` replaces
    them the first time `prepare_scenario` runs. Between import and that first
    refresh the constants are real floats describing nothing.

    Measured on 2026-09-06: read before any scenario, V_MAX_OBS is 13.32; read
    after, it is between 15.876 and 15.996. A dataset carrying 13.32 in its
    metadata is not a dataset with a slightly different normalisation, it is a
    dataset whose metadata was written before the normalisation was known.
    """
    import src.rl_interface as rli

    directory = rli.scenario_dir(base_path)
    net_file = os.path.join(directory, "generated.net.xml")
    return {
        "scenario_dir": directory,
        "network_path": net_file,
        "network_present": os.path.exists(net_file),
    }


def observation_constants(require_scenario: bool = True,
                          base_path: Optional[str] = None) -> Dict[str, float]:
    """Every constant that changes what an observation MEANS, read live.

    Recorded in the dataset metadata and re-read at load time. `N_ACTIVE_MAX_OBS`
    is the one that motivated this: it is derived from the density grid and the
    RSU coverage, so regenerating the scenario differently moves it, and every
    stored contention feature would then be normalised against a ceiling the
    current code no longer uses.

    `RSU_RANGE`, `A_MAX` and `QUEUE_MAX` were missing from this mapping and are
    here now. They divide features [4], [5], [6], [7], [12] and [15], which is
    six of the seventeen, so a dataset could previously have been recorded under
    a different value of any of them and passed `verify_compatibility` without a
    complaint. They are read off a live `StateVectorizer` rather than from module
    globals because the vectoriser is where the division happens and where a
    default could be overridden.

    `PHASE_REMAINING_REF_S` divides feature [11] and has no module constant at
    all -- it is a literal inside `vectorize_from_dict`. It is therefore PROBED:
    the vectoriser is handed a known `time_to_switch` and the divisor is
    recovered from the answer. A number copied beside the code would agree with
    it exactly until somebody changed one of the two, which is the failure mode
    this whole mapping exists to prevent.

    WHEN THIS MUST BE CALLED. After `prepare_scenario`, never before.
    `V_MAX_OBS`, `E_REF` and `DELTA_MAX` are module-level values computed once at
    import from the scenario ON DISK and refreshed by `refresh_scenario_constants`.
    Read before the first scenario exists they return the import-time fallback of
    an empty directory -- measured as E_REF 13.32 against the post-refresh 13.26 --
    and the metadata would then describe a different observation from the one
    that was collected. `collect_offline_dataset` calls this after the last
    episode for exactly that reason.
    """
    import src.rl_interface as rli

    vec = rli.StateVectorizer()
    # Read, not probed. It was a bare literal inside `vectorize_from_dict` until
    # 2026-09-06 and had to be recovered by inverting the vectoriser's answer;
    # it is `PHASE_REMAINING_REF_S` now, so this reads the same object the
    # vectoriser divides by and the two cannot drift.
    phase_ref = float(rli.PHASE_REMAINING_REF_S)

    constants = {
        "N_ACTIVE_MAX_OBS": float(rli.N_ACTIVE_MAX_OBS),
        "V_MAX_OBS": float(getattr(rli, "V_MAX_OBS", float("nan"))),
        "E_REF": float(getattr(rli, "E_REF", float("nan"))),
        "DELTA_MAX": float(getattr(rli, "DELTA_MAX", float("nan"))),
        "DELTA_MIN": float(getattr(rli, "DELTA_MIN", float("nan"))),
        "RSU_RANGE": float(vec.rsu_range),
        "A_MAX": float(vec.a_max),
        "QUEUE_MAX": float(vec.queue_max),
        "PHASE_REMAINING_REF_S": float(phase_ref),
        "DIST_TO_STOPLINE_REF_M": float(rli.DIST_TO_STOPLINE_REF_M),
    }
    # `base_path` names WHICH scenario directory to look in, and it matters: a
    # caller that passed an explicit `sumo_dir` to `prepare_scenario` refreshed
    # the constants from THAT directory, while `scenario_dir(None)` resolves the
    # process default. Checking the wrong one would clear a directory that has a
    # network while the constants came from one that does not.
    if require_scenario and not scenario_provenance(base_path)["network_present"]:
        raise ScenarioNotGenerated(
            "no generated.net.xml exists in the scenario directory, so V_MAX_OBS, "
            "E_REF and DELTA_MAX are the import-time FALLBACKS of an empty "
            f"directory (V_MAX_OBS reads {constants['V_MAX_OBS']}; a generated "
            "network gives about 15.9). Recording them would describe normalisers "
            "that no observation was ever built with. Call prepare_scenario() "
            "first, or pass require_scenario=False if you genuinely want the "
            "fallbacks and will not store them."
        )
    unclassified = set(constants) - set(CONSTANT_ORIGIN)
    if unclassified:  # pragma: no cover - guards a future constant being added
        raise KeyError(
            f"{sorted(unclassified)} is normalised into the observation but "
            "CONSTANT_ORIGIN does not say whether it is a property of the code or "
            "of the generated scenario, so verify_compatibility cannot know how to "
            "compare it. Classify it."
        )
    return constants


def git_provenance(repo_dir: Optional[str] = None) -> Dict[str, Any]:
    """The commit the collection ran at, and whether the tree was modified.

    A dataset that records only a commit hash while the tree was dirty records a
    code state that never existed, so `dirty` is stored alongside it. Failures
    are recorded as such rather than raising: a missing git is a reason to note
    "unknown", not a reason to lose a collection run.
    """
    repo_dir = repo_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _run(args: Sequence[str]) -> Optional[str]:
        try:
            out = subprocess.run(
                list(args), cwd=repo_dir, capture_output=True, text=True, timeout=15
            )
        except Exception:  # noqa: BLE001 - provenance must not break collection
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    commit = _run(["git", "rev-parse", "HEAD"])
    status = _run(["git", "status", "--porcelain"])
    return {
        "commit": commit or "unknown",
        "dirty": None if status is None else bool(status.strip()),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown",
    }


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------
def limit_cpu_threads(num_threads: int = 1) -> None:
    """Pin this process to `num_threads` BLAS/torch threads.

    Collection runs no gradient step and is dominated by SUMO, so more threads
    buy nothing while taking cores away from the hyper-parameter searches this is
    meant to run alongside. The environment variables are set as well because
    several numerical backends read them once at import.
    """
    n = str(max(1, int(num_threads)))
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[var] = n
    torch.set_num_threads(max(1, int(num_threads)))


def collect_offline_dataset(
    delta_band_center: float,
    densities: Sequence[float],
    seeds: Sequence[int],
    steps_per_episode: int,
    warmup_steps: int = 1200,
    delta_log_halfwidth: float = 0.0,
    num_channels: int = 4,
    error_mode: Optional[str] = None,
    sumo_dir: Optional[str] = None,
    gamma: float = 0.99,
    max_transitions: Optional[int] = None,
    progress_every: int = 0,
    num_threads: Optional[int] = None,
    road_seed: Optional[int] = None,
    n_cells: Optional[int] = None,
) -> OfflineDataset:
    """Roll the fixed-period behaviour policy through the real SUMO environment.

    ---------------------------------------------------------------------------
    WHICH ROAD NETWORK THE COLLECTION RUNS ON
    ---------------------------------------------------------------------------
    `road_seed` decides, and it is a different thing from the `seeds` argument.
    They control different halves of the scenario and the split was measured on
    2026-09-06 (`etc/scripts/measure_road_network_provenance.py`):

      * `prepare_scenario(seed=S)` calls `make_sumo_set.seed_generation(S)`, which
        reseeds the module-global `_gen_rng`. That generator draws every edge's
        SPEED LIMIT, so it decides the ROAD;
      * `AoiV2IEnv(seed=s)` seeds `random`, `numpy`, SUMO's own `--seed` and the
        channel model. It decides the TRAFFIC and the CHANNEL, and never touches
        `_gen_rng`.

    With `road_seed` set, this reproduces exactly what `run_hot_swap_training`
    does: ONE `prepare_scenario` at the start, and after that every episode simply
    asks for its density and lets `AoiV2IEnv._init_sumo` regenerate. That matters
    because the road is NOT a function of the density alone. `make_sumo_files`
    regenerates whenever the density changes, each regeneration advances
    `_gen_rng`, and coming back to a density therefore yields a DIFFERENT road.
    Measured over three cycles of the seven-density schedule, one training run
    visits eight distinct roads and each density sees two or three of them. What
    makes the comparison fair is not that the road is fixed but that the whole
    SEQUENCE is, and it is fixed because every run re-seeds at its start.

    So an offline dataset that reseeds per cell -- which is what this function did
    until 2026-09-06 -- walks a different road sequence from the training run it
    is meant to initialise, and offline reinforcement learning assumes both halves
    are the same MDP. `road_seed=None` keeps the old per-cell behaviour for
    callers that want it and is recorded in the metadata either way.

    `n_cells` selects the schedule. With it, the collection walks the TRAINER's
    episode loop -- cell `i` takes density `densities[i % len(densities)]`, the
    same round-robin `hot_swap_trainer` line 3907 uses -- so the roads it sees are
    the roads training episodes 0..n_cells-1 see. `seeds` then supplies the flow
    seed, one per pass through the density list. Without it the old grid is used:
    one episode per (density, seed) pair, which visits a road sequence that
    matches no training run.

    ---------------------------------------------------------------------------
    THE LOOP
    ---------------------------------------------------------------------------
    The loop is the same event-driven SMDP
    loop the trainer runs -- a transition is assembled and stored only when the
    environment reports the interval CLOSED, so the reward and the measured
    `delta_t` are the environment's, never the requested Delta and never a value
    computed here. In-flight intervals are finalised at the episode boundary for
    the same reason the trainer does it: dropping them would discard exactly the
    long-Delta decisions.

    No model is constructed and no gradient is taken. CPU only.

    `num_threads` limits the BLAS and torch thread pools for THIS process. It is
    an argument rather than something the CLI does on its own because the CLI is
    not the only caller: a script or a test that imports this function got no
    limit at all, and collection is meant to run beside the hyper-parameter
    searches without taking cores from them. `None` leaves the process as it is,
    so a caller that has already set its own limits is not overridden.

    `error_mode` defaults to the ENVIRONMENT's own default rather than to a
    literal. The previous default here was the string "raw", which
    `AoiV2IEnv.__init__` rejects outright -- it accepts only "accumulate" and
    "mean" -- so every call that did not pass the argument raised on the first
    episode. Deferring to `DEFAULT_ERROR_MODE` also means the collection cannot
    silently use a different reward definition from the training runs.
    """
    # Imported here, not at module import time: `hot_swap_trainer` starts SUMO
    # machinery and pulls in libsumo, and this module is also imported by tests
    # that never collect anything.
    import src.Communications as _comm
    import src.hot_swap_trainer as _hst
    from src.hot_swap_trainer import (
        AoiV2IEnv,
        DEFAULT_ERROR_MODE,
        REWARD_ERROR_MODES,
        prepare_scenario,
    )

    if num_threads is not None:
        limit_cpu_threads(int(num_threads))

    error_mode = DEFAULT_ERROR_MODE if error_mode is None else str(error_mode)
    if error_mode not in REWARD_ERROR_MODES:
        raise ValueError(
            f"error_mode must be one of {REWARD_ERROR_MODES}, got {error_mode!r}. "
            "The environment owns the reward definition; a mode it does not accept "
            "would fail on the first episode after the scenario had been generated."
        )

    if float(delta_band_center) <= 0.0:
        raise ValueError(
            "delta_band_center must be positive; there is no default for it")
    densities = [float(d) for d in densities]
    seeds = [int(s) for s in seeds]
    if not densities or not seeds:
        raise ValueError("collection needs at least one density and one seed")

    # A transition budget is spent EVENLY over the cells, not first-come.
    #
    # `max_transitions` used to be a single running total checked inside the
    # episode loop, and the loop walks densities in order. A budget smaller than
    # the full collection therefore filled the first densities and left the last
    # ones with zero rows, while the metadata went on listing every density in
    # `densities` as though all had been covered. The distribution mismatch that
    # produced would have been read later as a property of the method rather than
    # of the collection.
    #
    # The per-cell share makes the truncation uniform instead: every (density,
    # seed) pair stops at its own quota, so a halved budget halves each cell
    # rather than deleting the tail of the grid. The global total is still
    # honoured, and `per_episode` below records what each cell actually produced,
    # so the claim is auditable rather than asserted.
    # The cells, in the order they will be visited. Building the list up front
    # rather than nesting two loops is what lets the episode schedule and the
    # grid share one body, and it makes the visit ORDER an explicit, recordable
    # object -- which it has to be, because with `road_seed` set the order is
    # what determines the road each cell runs on.
    if n_cells is not None:
        # The trainer's own round-robin: `hot_swap_trainer` line 3907,
        # `density_schedule[ep % len(density_schedule)]`. The flow seed advances
        # once per completed pass, so each pass over the density list is a
        # different traffic realisation on a different road.
        cells = [
            (densities[i % len(densities)], seeds[(i // len(densities)) % len(seeds)])
            for i in range(int(n_cells))
        ]
        schedule_kind = "trainer_episode_round_robin"
    else:
        cells = [(d, s) for d in densities for s in seeds]
        schedule_kind = "density_seed_grid"

    # The road is NAMED per cell, not inherited from the previous one.
    #
    # This used to reseed once at the start and let `_gen_rng` carry the sequence
    # forward, which reproduced the training run only because the training run
    # had the same accidental structure. Since `make_sumo_set.road_seed(density,
    # cycle)` exists the dependence on order is gone from both sides: cell `i`
    # asks for cycle `i // len(densities)`, training episode `ep` asks for cycle
    # `ep // len(density_schedule)`, and identical arguments give identical roads
    # however either loop is arranged.
    #
    # `road_seed` is therefore no longer a seed to pass through. It survives as a
    # BOOLEAN-ish switch for the legacy path and is recorded either way; a caller
    # that wants the trainer's roads sets `n_cells` and leaves the rest alone.

    per_cell_cap: Optional[int] = None
    if max_transitions is not None:
        per_cell_cap = max(1, int(math.ceil(float(max_transitions) / float(len(cells)))))

    decoder = ActionDecoder(num_channels=int(num_channels))
    if not (decoder.delta_min <= float(delta_band_center) <= decoder.delta_max):
        raise ValueError(
            f"delta_band_center={delta_band_center} is outside the decoder's range "
            f"[{decoder.delta_min}, {decoder.delta_max}]"
        )
    policy = FixedPeriodBehaviourPolicy(
        delta_band_center=float(delta_band_center),
        num_channels=int(num_channels),
        p_min=float(decoder.p_min),
        p_max=float(decoder.p_max),
        delta_log_halfwidth=float(delta_log_halfwidth),
    )

    columns: Dict[str, List[Any]] = {k: [] for k in ARRAY_KEYS + OPTIONAL_ARRAY_KEYS}
    per_episode: List[Dict[str, Any]] = []
    #: The observation normalisers as they stood in the FIRST cell, and every
    #: later cell's disagreement with them. `prepare_scenario` refreshes the
    #: scenario-derived constants per cell, and the metadata can only record one
    #: set; if the cells disagree, the rows collected before the change are
    #: normalised differently from the rows after it, and the single recorded set
    #: describes neither. Recording the disagreements makes that visible instead
    #: of averaging it away.
    first_cell_constants: Optional[Dict[str, float]] = None
    constant_drift: List[Dict[str, Any]] = []
    started = time.time()
    stop = False

    for cell_index, (density, seed) in enumerate(cells):
        # One flat loop over a precomputed visit order, where there used to be a
        # `for density: for seed:` nest. The order is the thing that decides the
        # road under `road_seed`, so it has to be an object the metadata can
        # record rather than an emergent property of two nested loops.
        if not stop:
            if road_seed is None:
                # LEGACY PATH. The road is a function of the FLOW seed, which is
                # how this collector behaved before 2026-09-06 and which walks a
                # road sequence no training run walks. Kept only for a caller
                # that asks for it explicitly.
                cell_road_cycle = None
                cell_road_seed = int(seed)
            else:
                # The road is the one training episode `cell_index` runs on.
                # `cell_index // len(densities)` is the trainer's own
                # `ep // len(density_schedule)` (hot_swap_trainer line 3962), so
                # a 21-cell collection covers exactly the roads of training
                # episodes 0..20.
                cell_road_cycle = cell_index // len(densities)
                cell_road_seed = int(_road_seed(float(density), cell_road_cycle))
            prepare_scenario(
                density=float(density),
                max_steps=int(steps_per_episode),
                warmup_steps=int(warmup_steps),
                seed=cell_road_seed,
                sumo_dir=sumo_dir,
            )
            cell_constants = observation_constants(base_path=sumo_dir)
            if first_cell_constants is None:
                first_cell_constants = dict(cell_constants)
            else:
                differing = {
                    key: [float(first_cell_constants[key]), float(value)]
                    for key, value in cell_constants.items()
                    if not math.isclose(
                        float(first_cell_constants[key]), float(value),
                        rel_tol=(SCENARIO_CONSTANT_REL_TOL
                                 if CONSTANT_ORIGIN.get(key) == "scenario" else 1e-9),
                        abs_tol=1e-12,
                    )
                }
                if differing:
                    constant_drift.append({
                        "cell_index": int(cell_index),
                        "density": float(density), "seed": int(seed),
                        "differs_from_first_cell": differing,
                    })
                    logger.warning(
                        "observation normalisers moved at density %.1f seed %d: %s. "
                        "Rows collected before and after this cell are normalised "
                        "differently and the metadata can record only one set.",
                        density, seed, differing,
                    )
            # The Delta band is re-clipped against the refreshed decoder, so a
            # scenario whose DELTA_MAX moved cannot silently push the behaviour
            # policy outside the action space.
            live_decoder = ActionDecoder(num_channels=int(num_channels))
            delta_logp = _delta_unit_log_density(policy, live_decoder)

            rng = np.random.default_rng(int(seed))
            env: Optional[Any] = None
            n_before = len(columns["state"])
            cell_truncated = False
            try:
                env = AoiV2IEnv(
                    density=float(density),
                    seed=int(seed),
                    max_steps=int(steps_per_episode),
                    warmup_steps=int(warmup_steps),
                    num_channels=int(num_channels),
                    error_mode=str(error_mode),
                    sumo_dir=sumo_dir,
                )
                obs, _info = env.reset()
                # Same reason the validation episode does it: the uplink success
                # draw consumes the process-wide `random` stream, whose position
                # depends on whether the scenario was regenerated.
                random.seed(int(seed))

                open_decision: Dict[str, Dict[str, Any]] = {}
                action_dict: Dict[str, Any] = {}
                for vid, s_vec in obs.items():
                    grant, ch, base_logp = policy.sample(rng, live_decoder)
                    raw = live_decoder.encode_action(grant[0], grant[1], grant[2])
                    open_decision[vid] = {
                        "state": np.asarray(s_vec, dtype=np.float32),
                        "raw_action": raw,
                        # The grant in the units it was issued in. `raw_action`
                        # is the decoder's unit coordinate and stops meaning the
                        # same interval if the decoder's range moves.
                        "delta_s": float(grant[0]),
                        "power_dbm": float(grant[2]),
                        "state_raw": np.asarray(
                            env.last_raw_observation.get(
                                vid, np.full(len(RAW_OBSERVATION_FIELDS), np.nan)),
                            dtype=np.float32),
                        "action_idx": int(ch),
                        "behaviour_log_prob": float(base_logp + delta_logp),
                    }
                    action_dict[vid] = grant

                for _step in range(int(steps_per_episode)):
                    next_obs, _r, _term, _trunc, step_info = env.step(action_dict)

                    action_dict = {}
                    for rec in step_info["completed"]:
                        vid = rec["vid"]
                        prev = open_decision.pop(vid, None)
                        if prev is None:
                            continue
                        s2 = next_obs.get(vid)
                        if s2 is None:
                            s2 = np.zeros(int(prev["state"].shape[0]), dtype=np.float32)
                            done = True
                        else:
                            done = bool(rec["done"])
                        _append(
                            columns, prev, rec, s2, done,
                            close_reason=(CLOSE_REASON_TRANSMITTED
                                          if rec.get("transmitted")
                                          else CLOSE_REASON_COVERAGE_EXIT),
                            subchannel_cbr=env.subchannel_cbr,
                            state_raw=prev["state_raw"],
                            next_state_raw=env.last_raw_observation.get(
                                vid, np.full(len(RAW_OBSERVATION_FIELDS), np.nan)),
                            cell_index=cell_index,
                        )

                    for vid in step_info["needs_decision"]:
                        s_vec = next_obs.get(vid)
                        if s_vec is None:
                            continue
                        grant, ch, base_logp = policy.sample(rng, live_decoder)
                        raw = live_decoder.encode_action(grant[0], grant[1], grant[2])
                        open_decision[vid] = {
                            "state": np.asarray(s_vec, dtype=np.float32),
                            "raw_action": raw,
                            "delta_s": float(grant[0]),
                            "power_dbm": float(grant[2]),
                            "state_raw": np.asarray(
                                env.last_raw_observation.get(
                                    vid, np.full(len(RAW_OBSERVATION_FIELDS), np.nan)),
                                dtype=np.float32),
                            "action_idx": int(ch),
                            "behaviour_log_prob": float(base_logp + delta_logp),
                        }
                        action_dict[vid] = grant

                    for vid in [v for v in open_decision if v not in next_obs]:
                        open_decision.pop(vid, None)

                    obs = next_obs
                    if progress_every and len(columns["state"]) and \
                            len(columns["state"]) % int(progress_every) == 0:
                        logger.info(
                            "HOORL offline collection: %d transitions after %.1f s",
                            len(columns["state"]), time.time() - started,
                        )
                    # Two independent stops. The per-cell quota ends THIS
                    # episode and lets the grid continue, which is what keeps a
                    # truncated collection covering every density. The global
                    # total ends the collection outright and is only reachable
                    # through rounding of the per-cell share.
                    if per_cell_cap is not None and \
                            len(columns["state"]) - n_before >= per_cell_cap:
                        cell_truncated = True
                        break
                    if max_transitions is not None and \
                            len(columns["state"]) >= int(max_transitions):
                        stop = True
                        break

                # ALWAYS finalised, including when a budget ended the episode
                # early. Skipping it does not merely lose rows, it loses a
                # BIASED set of them: the intervals still open at the cut are
                # exactly the long ones, so a truncated cell that skipped this
                # would carry a Delta distribution shifted towards short
                # silences while its metadata claimed a log-uniform band. The
                # few extra rows can push the total slightly past
                # `max_transitions`, which is a budget rather than a contract.
                for rec in env.finalize_open_intervals():
                    vid = rec["vid"]
                    prev = open_decision.pop(vid, None)
                    if prev is None:
                        continue
                    s2 = obs.get(vid)
                    if s2 is None:
                        s2 = np.zeros(int(prev["state"].shape[0]), dtype=np.float32)
                    _append(
                        columns, prev, rec, s2, bool(rec.get("done", False)),
                        close_reason=(CLOSE_REASON_TRANSMITTED
                                      if rec.get("transmitted")
                                      else CLOSE_REASON_EPISODE_BOUNDARY),
                        subchannel_cbr=env.subchannel_cbr,
                        state_raw=prev["state_raw"],
                        next_state_raw=env.last_raw_observation.get(
                            vid, np.full(len(RAW_OBSERVATION_FIELDS), np.nan)),
                        cell_index=cell_index,
                    )

                metrics = env.get_metrics()
            finally:
                if env is not None:
                    try:
                        env.close()
                    except Exception:  # noqa: BLE001 - closing must not mask a failure
                        logger.warning("could not close the collection environment", exc_info=True)
                    del env
                    gc.collect()

            per_episode.append({
                # The visit index, so the road each cell ran on can be traced
                # back: under `road_seed` the road is a function of this index,
                # not of the density.
                "cell_index": int(cell_index),
                "density": float(density),
                "seed": int(seed),
                "road_cycle": cell_road_cycle,
                "road_seed": int(cell_road_seed),
                # The complete normalising set for THIS cell. `cell_index` in the
                # arrays joins a row to this record, which is what makes the raw
                # columns invertible for the scenario-derived constants.
                "observation_constants": {k: float(v) for k, v in cell_constants.items()},
                "V_MAX_OBS": float(cell_constants["V_MAX_OBS"]),
                "transitions": len(columns["state"]) - n_before,
                "truncated_by_per_cell_cap": bool(cell_truncated),
                "mean_aoi": float(metrics.get("mean_aoi", float("nan"))),
                "mean_update_error": float(metrics.get("mean_update_error", float("nan"))),
            })
            logger.info(
                "HOORL offline collection: density %.1f seed %d gave %d transitions",
                density, seed, per_episode[-1]["transitions"],
            )

    arrays = {
        "state": np.asarray(columns["state"], dtype=np.float32).reshape(-1, STATE_DIM),
        "action": np.asarray(columns["action"], dtype=np.float32).reshape(-1, 3),
        "reward": np.asarray(columns["reward"], dtype=np.float32).reshape(-1),
        "next_state": np.asarray(columns["next_state"], dtype=np.float32).reshape(-1, STATE_DIM),
        "done": np.asarray(columns["done"], dtype=np.float32).reshape(-1),
        "delta_t": np.asarray(columns["delta_t"], dtype=np.float32).reshape(-1),
        "action_idx": np.asarray(columns["action_idx"], dtype=np.int64).reshape(-1),
        "behaviour_log_prob": np.asarray(
            columns["behaviour_log_prob"], dtype=np.float32
        ).reshape(-1),
        "close_reason": np.asarray(columns["close_reason"], dtype=np.int8).reshape(-1),
        "cbr_used_channel": np.asarray(
            columns["cbr_used_channel"], dtype=np.float32).reshape(-1),
        "cbr_max_channel": np.asarray(
            columns["cbr_max_channel"], dtype=np.float32).reshape(-1),
        "state_raw": np.asarray(columns["state_raw"], dtype=np.float32).reshape(
            -1, len(RAW_OBSERVATION_FIELDS)),
        "next_state_raw": np.asarray(
            columns["next_state_raw"], dtype=np.float32).reshape(
            -1, len(RAW_OBSERVATION_FIELDS)),
        "action_raw": np.asarray(columns["action_raw"], dtype=np.float32).reshape(
            -1, len(RAW_ACTION_FIELDS)),
        # WHICH CELL each row came from, and therefore which SCENARIO CONSTANTS
        # normalised it.
        #
        # Without this the raw columns are not invertible for the four features
        # that divide by a scenario-derived constant. `V_MAX_OBS` and `E_REF` are
        # read off the generated road and differ between cells -- measured
        # 2026-09-06, they span 0.756 % over the roads one collection visits --
        # so re-normalising [0], [1], [2] and [3] with the constants that happen
        # to be live at read time reproduces the stored value only for the last
        # cell. Observed: a 3.2e-3 discrepancy on a [-1, 1] feature, small but
        # systematic and entirely explained by the row having been normalised on a
        # different road.
        #
        # `per_episode` in the metadata carries the constants for each cell, so
        # this index is what joins a row to them. int16 because a collection has
        # tens of cells, not thousands.
        "cell_index": np.asarray(columns["cell_index"], dtype=np.int16).reshape(-1),
    }

    band = policy.delta_band(ActionDecoder(num_channels=int(num_channels)))
    metadata: Dict[str, Any] = {
        "format_version": DATASET_FORMAT_VERSION,
        # The environment this collection was produced by, recorded so that a
        # file carries its own physics rather than relying on its date.
        "environment_provenance": {
            "CBR_REF": float(_hst.CBR_REF),
            "shadowing_decorrelation_m": float(_comm.SHADOWING_DECORR_M),
            "shadowing_reference": (
                "position of the link's last draw, held in Communications; "
                "before 2026-09-07 the caller passed the gap to the ledger, "
                "which accumulated across retransmissions"),
        },
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": "HOORL",
        "reference_doi": "10.1109/TVT.2026.3675626",
        "behaviour_policy": {
            "kind": "fixed_period_uniform_channel_power",
            **asdict(policy),
            "delta_band": [float(band[0]), float(band[1])],
            "delta_component_defined": bool(policy.delta_component_defined),
            # READ `delta_band`. The two scalars beside it reconstruct it and
            # neither is a value any transition took: the centre is the geometric
            # midpoint, sqrt(5) = 2.2360680 for the band [0.5, 10], and the
            # half-width is 0.5*ln(20) = 1.4978661.
            #
            # THE OLD NAMES ARE STILL WRITTEN, deliberately. `delta_fixed` and
            # `delta_jitter` were renamed on 2026-09-07 because both had stopped
            # describing what they hold -- the specification's "fixed value" became
            # a band centre, and a "jitter" of 1.498 spans [0.5, 10] s, which is
            # the whole action range rather than a wobble. Files collected before
            # the rename carry the old keys and are otherwise valid, and readers
            # outside this module use them, so the new file writes both. A
            # consumer can be updated on its own schedule instead of on this one.
            "delta_fixed": float(policy.delta_band_center),
            "delta_jitter": float(policy.delta_log_halfwidth),
            "delta_names_renamed_2026_09_07": (
                "delta_fixed -> delta_band_center, delta_jitter -> "
                "delta_log_halfwidth. Both spellings are written; the old ones "
                "are aliases kept for files and readers that predate the rename."
            ),
            "delta_band_is": (
                "delta_band = [center*exp(-halfwidth), center*exp(+halfwidth)] "
                "clipped to the decoder range. The centre is NOT a value any "
                "transition took. Consumers should read delta_band."
            ),
            "note": (
                "Delta is deterministic when delta_log_halfwidth == 0, so the "
                "stored behaviour_log_prob covers the channel factor only and the "
                "Delta axis has zero coverage. Above 0 Delta is log-uniform "
                "inside delta_band and its (finite) log density is included."
            ),
        },
        "n_transitions": int(arrays["state"].shape[0]),
        "contents_manifest": contents_manifest(arrays, STATE_DIM),
        "optional_columns": [k for k in OPTIONAL_ARRAY_KEYS if k in arrays],
        "raw_observation_fields": list(RAW_OBSERVATION_FIELDS),
        "raw_action_fields": list(RAW_ACTION_FIELDS),
        "raw_storage_note": (
            "state_raw / next_state_raw / action_raw hold the values BEFORE "
            "normalisation, so a change to rsu_range, N_ACTIVE_MAX_OBS, the "
            "subchannel count or the decoder's Delta range can be applied by "
            "re-reading this file instead of recollecting. The normalised "
            "vectors are stored too, deliberately: recomputing them from the raw "
            "values must reproduce what is stored, and a mismatch means the "
            "offline and online normalisation paths have diverged."
        ),
        "close_reason_labels": {str(k): v for k, v in CLOSE_REASON_LABELS.items()},
        "cbr_column_note": (
            "cbr_used_channel and cbr_max_channel are RAW subchannel occupancy "
            "ratios at the instant the interval closed. They are neither "
            "observation feature [14], which is the MEAN over subchannels, nor "
            "the reward's congestion term, which divides the used channel's "
            "occupancy by CBR_REF. The maximum is stored because the mean cannot "
            "distinguish a policy that spreads grants over the subchannels from "
            "one that concentrates them."
        ),
        "state_dim": int(STATE_DIM),
        "num_channels": int(num_channels),
        # REQUESTED and COVERED are separate keys, and neither is a synonym for
        # the other. `densities` used to be the only one, so a run that stopped
        # early still listed the whole grid and a reader had no way to tell that
        # the last densities held zero rows. `transitions_by_density` is counted
        # from what was actually stored, so the claim is derived from the data
        # rather than restated from the arguments.
        "densities_requested": [float(d) for d in densities],
        "densities_covered": sorted({
            float(rec["density"]) for rec in per_episode if rec["transitions"] > 0
        }),
        "transitions_by_density": {
            f"{d:g}": int(sum(rec["transitions"] for rec in per_episode
                              if float(rec["density"]) == float(d)))
            for d in densities
        },
        "seeds": [int(s) for s in seeds],
        # WHICH ROAD NETWORK the rows were collected on, and how the visit order
        # was built. `road_seed` reseeds `make_sumo_set._gen_rng` ONCE at the
        # start, exactly as `run_hot_swap_training` does, so the road sequence is
        # a training run's; `None` is the legacy per-cell reseed, which walks a
        # sequence no training run walks. `cell_order` is recorded because under
        # `road_seed` the road is a function of the visit index rather than of
        # the density, so the order IS part of what produced the data.
        "road_seed": None if road_seed is None else int(road_seed),
        "schedule": schedule_kind,
        "n_cells": len(cells),
        "cell_order": [[float(d), int(s)] for d, s in cells],
        "road_note": (
            "prepare_scenario(seed=S) seeds the edge-speed generator and decides "
            "the ROAD; AoiV2IEnv(seed=s) seeds SUMO, numpy, random and the channel "
            "model and decides the TRAFFIC. Measured 2026-09-06, "
            "etc/scripts/measure_road_network_provenance.py. A density does not "
            "determine a road: each regeneration advances the generator, so "
            "returning to a density gives a different road."
        ),
        "seeds_covered": sorted({
            int(rec["seed"]) for rec in per_episode if rec["transitions"] > 0
        }),
        # "Every cell the SCHEDULE planned produced rows", not "every seed in the
        # --seeds list was used". The two differ under the episode schedule: with
        # 14 cells and three seeds the third is simply never reached, which is a
        # property of the requested schedule and not a failure. Conflating them
        # would report a healthy collection as incomplete and teach the reader to
        # ignore the flag. `seeds_never_scheduled` says the other thing
        # separately, so neither question has to be answered by guessing.
        "coverage_complete": bool(
            {float(d) for d, _ in cells}
            == {float(rec["density"]) for rec in per_episode if rec["transitions"] > 0}
            and {int(sd) for _, sd in cells}
            == {int(rec["seed"]) for rec in per_episode if rec["transitions"] > 0}
        ),
        "seeds_never_scheduled": sorted(set(seeds) - {int(sd) for _, sd in cells}),
        "densities_never_scheduled": sorted(set(densities) - {float(d) for d, _ in cells}),
        "max_transitions_requested": None if max_transitions is None else int(max_transitions),
        "per_cell_transition_cap": None if per_cell_cap is None else int(per_cell_cap),
        "steps_per_episode": int(steps_per_episode),
        "warmup_steps": int(warmup_steps),
        "error_mode": str(error_mode),
        "sumo_dir": None if sumo_dir is None else os.path.abspath(sumo_dir),
        "gamma_for_stored_discount": float(gamma),
        # Read AFTER the last episode, so these are the constants the scenarios
        # were actually normalised by rather than the import-time fallback of an
        # empty scenario directory. See `observation_constants`.
        "observation_constants": observation_constants(base_path=sumo_dir),
        "observation_constant_origin": dict(CONSTANT_ORIGIN),
        "scenario_provenance": scenario_provenance(sumo_dir),
        "scenario_constant_rel_tol": float(SCENARIO_CONSTANT_REL_TOL),
        # Empty in a healthy collection. A non-empty list means the normalisers
        # moved between cells, so the single recorded set above does not describe
        # every stored row and the dataset should be recollected in one scenario
        # directory.
        "observation_constant_drift_between_cells": constant_drift,
        "git": git_provenance(),
        "per_episode": per_episode,
        "wall_clock_s": round(time.time() - started, 2),
        "truncated_by_max_transitions": bool(stop),
        "cells_truncated_by_per_cell_cap": int(
            sum(1 for rec in per_episode if rec.get("truncated_by_per_cell_cap"))
        ),
        "num_threads": None if num_threads is None else int(num_threads),
    }
    # THE WRITER IS CHECKED, NOT ONLY THE READER.
    #
    # `reconcile_to_current_constants` can rebuild a feature whose constant moved,
    # which makes a missing constant survivable on load -- and that is exactly why
    # it must be caught here instead. A collector that silently stopped recording
    # a constant would produce files that load, renormalise and give correct
    # numbers forever, with nothing anywhere reporting the gap.
    recorded = set(metadata["observation_constants"])
    expected = set(rli_observation_constants_live())
    if recorded != expected:
        raise ValueError(
            "the collection did not record the same constants the code defines: "
            f"missing {sorted(expected - recorded)}, unexpected "
            f"{sorted(recorded - expected)}. A dataset whose metadata omits a "
            "normaliser cannot be checked against a future change to it, and the "
            "reader's ability to repair the omission is not a reason to write it."
        )
    return OfflineDataset(arrays, metadata, gamma=float(gamma))


def _append(
    columns: Dict[str, List[Any]],
    prev: Dict[str, Any],
    rec: Dict[str, Any],
    next_state: np.ndarray,
    done: bool,
    close_reason: int,
    subchannel_cbr: Sequence[float],
    state_raw: np.ndarray,
    next_state_raw: np.ndarray,
    cell_index: int,
) -> None:
    """Store one CLOSED interval. Reward and delta_t come from the environment.

    `close_reason` says WHY the interval ended, which the stored columns could
    previously only hint at. `cbr_used_channel` is the raw occupancy of the
    subchannel this grant actually used and `cbr_max_channel` the busiest of the
    four at the same instant. Both are raw ratios, NOT the `CBR_REF`-normalised
    quantity the reward uses and NOT observation feature [14], which is the mean
    over subchannels. The distinction is the point: a policy that spreads its
    grants evenly and one that piles them onto a single subchannel produce the
    same mean, and only the maximum separates them.

    They are read from the environment at the step the interval closed, so they
    describe the instant of closure rather than the whole interval.
    """
    columns["state"].append(np.asarray(prev["state"], dtype=np.float32))
    columns["action"].append(np.asarray(prev["raw_action"], dtype=np.float32))
    columns["reward"].append(float(rec["reward"]))
    columns["next_state"].append(np.asarray(next_state, dtype=np.float32))
    columns["done"].append(float(bool(done)))
    columns["delta_t"].append(float(rec["delta_actual"]))
    columns["action_idx"].append(int(prev["action_idx"]))
    columns["behaviour_log_prob"].append(float(prev["behaviour_log_prob"]))
    columns["close_reason"].append(int(close_reason))
    ch = int(prev["action_idx"])
    raw = [float(c) for c in subchannel_cbr]
    columns["cbr_used_channel"].append(float(raw[ch]) if 0 <= ch < len(raw) else float("nan"))
    columns["cbr_max_channel"].append(float(max(raw)) if raw else float("nan"))
    columns["state_raw"].append(np.asarray(state_raw, dtype=np.float32))
    columns["next_state_raw"].append(np.asarray(next_state_raw, dtype=np.float32))
    # The grant as the environment received it: Delta in seconds, power in dBm.
    columns["action_raw"].append(
        np.asarray([prev["delta_s"], prev["power_dbm"]], dtype=np.float32))
    columns["cell_index"].append(int(cell_index))


def dataset_from_buffer(
    buffer: RetrospectiveReplayBuffer, metadata: Dict[str, Any]
) -> OfflineDataset:
    """Adapter for tests and for replaying a hand-built buffer as a dataset.

    NOT a route for turning another baseline's training log into an offline
    dataset: that log has no fixed behaviour policy, which is the one thing the
    offline stage requires. The caller supplies the metadata and is responsible
    for what it claims.

    A TRANSITION THAT DOES NOT KNOW ITS BEHAVIOUR PROBABILITY IS REFUSED, and so
    is one that does not know its channel. Both used to be filled in:
    `float(item.get("behaviour_log_prob") or 0.0)` and
    `int(item.get("action_idx") or 0)`.

    Neither default is neutral. A log-probability of 0.0 is not "unknown", it is
    the assertion that the behaviour policy chose that action with probability
    one, so every importance ratio formed against it is wrong by exactly the
    factor the ratio was there to correct. And `or 0` collapses a genuine channel
    0 into the same value as a missing channel, so a buffer with no indices at
    all comes out claiming that every transmission used subchannel 0 -- a
    positive, false statement about the data rather than an absent one.

    There is no third option here. The values are knowable only at the instant of
    the decision and are unrecoverable afterwards, so a dataset that lacks them
    cannot be repaired; it can only be recollected.
    """
    # Only the REQUIRED columns. A replay buffer records no close reason and no
    # per-subchannel occupancy, so a dataset built this way is a version-1 file
    # in content whatever the header says, and `OfflineDataset` will report those
    # three as absent. That is the honest outcome; manufacturing them here would
    # put invented values behind a real-looking column name.
    columns: Dict[str, List[Any]] = {k: [] for k in ARRAY_KEYS}
    for position, item in enumerate(buffer.buffer):
        logp = item.get("behaviour_log_prob")
        if logp is None:
            raise ValueError(
                f"transition {position} carries no behaviour_log_prob. An offline "
                "dataset is defined relative to a KNOWN behaviour policy, and a "
                "missing log-probability cannot be defaulted: 0.0 asserts that the "
                "action was chosen with probability one. Recollect with a policy "
                "that records it."
            )
        idx = item.get("action_idx")
        if idx is None:
            raise ValueError(
                f"transition {position} carries no action_idx. It cannot be "
                "defaulted to 0, which is a real subchannel; a dataset of "
                "defaulted indices would claim every grant used subchannel 0."
            )
        columns["state"].append(np.asarray(item["state"], dtype=np.float32))
        columns["action"].append(np.asarray(item["action"], dtype=np.float32))
        columns["reward"].append(float(item["reward"]))
        columns["next_state"].append(np.asarray(item["next_state"], dtype=np.float32))
        columns["done"].append(float(item["done"]))
        columns["delta_t"].append(float(item["delta_t"]))
        columns["action_idx"].append(int(idx))
        columns["behaviour_log_prob"].append(float(logp))
    arrays = {
        "state": np.asarray(columns["state"], dtype=np.float32),
        "action": np.asarray(columns["action"], dtype=np.float32),
        "reward": np.asarray(columns["reward"], dtype=np.float32),
        "next_state": np.asarray(columns["next_state"], dtype=np.float32),
        "done": np.asarray(columns["done"], dtype=np.float32),
        "delta_t": np.asarray(columns["delta_t"], dtype=np.float32),
        "action_idx": np.asarray(columns["action_idx"], dtype=np.int64),
        "behaviour_log_prob": np.asarray(columns["behaviour_log_prob"], dtype=np.float32),
    }
    return OfflineDataset(arrays, metadata, gamma=float(buffer.gamma))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect HOORL's offline dataset with the documented fixed-period policy.",
    )
    parser.add_argument(
        "--delta-band-center", "--delta-fixed", type=float, required=True,
        dest="delta_band_center",
        help="Geometric CENTRE of the behaviour policy's Delta band, in seconds. "
             "REQUIRED: the specification says 'a fixed value' without saying which, "
             "so there is deliberately no default. `--delta-fixed` is the old "
             "spelling and still works.",
    )
    parser.add_argument(
        "--delta-log-halfwidth", "--delta-jitter", type=float, default=0.0,
        dest="delta_log_halfwidth",
        help="Half-width of the log-uniform Delta band IN LOG SPACE, so the band "
             "is centre*exp(-h) to centre*exp(+h). 0.0 (default) is the literal "
             "specification and leaves the Delta axis with zero coverage. "
             "`--delta-jitter` is the old spelling and still works.",
    )
    # The WHOLE benchmark grid, not a subset of it. A collection over four of the
    # seven densities leaves part of the offline-to-online distribution distance
    # coming from the collection design rather than from the method, and no later
    # analysis can separate the two.
    from src.sumo.make_sumo_set import DENSITY_GRID

    parser.add_argument("--densities", type=float, nargs="+",
                        default=[float(d) for d in DENSITY_GRID])
    parser.add_argument("--seeds", type=int, nargs="+", default=[2001, 2002, 2003])
    parser.add_argument("--steps", type=int, default=2000, help="steps per episode")
    parser.add_argument("--warmup-steps", type=int, default=1200)
    parser.add_argument("--num-channels", type=int, default=4)
    parser.add_argument(
        "--error-mode", type=str, default=None,
        help="reward error mode; the default defers to the environment's own "
             "DEFAULT_ERROR_MODE so the collection cannot use a different reward "
             "definition from the training runs",
    )
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--max-transitions", type=int, default=None)
    parser.add_argument(
        "--road-seed", type=int, default=None,
        help="seed the ROAD network once at the start, the way "
             "run_hot_swap_training does. Set this to the TRAINING seed so the "
             "offline data and the online run share one road sequence; offline "
             "reinforcement learning assumes both halves are the same MDP. "
             "Omitting it reseeds per cell, which walks a sequence no training "
             "run walks.",
    )
    parser.add_argument(
        "--n-cells", type=int, default=None,
        help="walk the TRAINER's episode schedule for this many cells "
             "(density = densities[i %% len(densities)], flow seed advancing once "
             "per pass) instead of the (density x seed) grid. Only this schedule "
             "reproduces the roads training episodes see, because the road "
             "depends on the visit order rather than on the density.",
    )
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--sumo-dir", type=str, default=None)
    parser.add_argument(
        "--out", type=str,
        default="data/hoorl_offline/hoorl_offline.npz",
        help="npz path; the metadata goes to the sibling .meta.json",
    )
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    # CPU only, by construction: this must be able to run alongside the GPU
    # hyper-parameter searches without competing with them. The thread limit is
    # ALSO passed to the collector, which applies it itself, so an importing
    # caller gets the same treatment as this entry point.
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    limit_cpu_threads(int(args.threads))

    dataset = collect_offline_dataset(
        delta_band_center=float(args.delta_band_center),
        densities=args.densities,
        seeds=args.seeds,
        steps_per_episode=int(args.steps),
        warmup_steps=int(args.warmup_steps),
        delta_log_halfwidth=float(args.delta_log_halfwidth),
        num_channels=int(args.num_channels),
        error_mode=args.error_mode,
        sumo_dir=args.sumo_dir,
        gamma=float(args.gamma),
        max_transitions=args.max_transitions,
        progress_every=1000,
        num_threads=int(args.threads),
        road_seed=args.road_seed,
        n_cells=args.n_cells,
    )
    npz_path, meta_path = dataset.save(args.out)
    logger.info(
        "wrote %d transitions to %s (metadata: %s)", len(dataset), npz_path, meta_path
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
