# src/rl_interface.py
# ============================================================================
# RL Agent Interface for AoI-aware V2I Uplink Scheduling Pipeline
#
# Implements:
# 1. StateVectorizer: 17-dimensional normalized observation vector in [-1.0, 1.0]
#    from the RSU perspective without future / ground-truth estimation error leakage.
# 2. ActionDecoder: Decodes hybrid action space (logits & indices) into valid
#    grant 3-tuple (Delta in [DELTA_MIN, DELTA_MAX]s, ch in {0..3}, p in [P_MIN, P_MAX]dBm).
# 3. RetrospectiveReplayBuffer: SMDP retrospective transition buffer with
#    variable-interval discount gamma^Delta support.
#
# This module is the SINGLE SOURCE OF TRUTH for the observation dimension
# (STATE_DIM) and for the hybrid action bounds (DELTA_MIN/MAX, P_MIN/MAX).
# Downstream code (hot_swap_trainer, hpo, evaluate, baselines) must read those
# from here instead of duplicating literals.
# ============================================================================

from __future__ import annotations
import math
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import xml.etree.ElementTree as ET
import numpy as np
import torch

# ----------------------------------------------------------------------------
# Canonical design constants (Conversation.md sections 1-2, user-approved).
# ----------------------------------------------------------------------------
#: Observation dimension emitted by StateVectorizer.
#: 18 -> 17 (2026-08-29, design_spec_v2 D4): the hand-synthesised
#: `stop/start_imminent` feature was removed. It was an arithmetic mean of two
#: quantities the vector already carries independently (time_to_switch and
#: dist_to_stopline), i.e. a derived feature that pre-computes for the network
#: what the network should learn for itself.
STATE_DIM: int = 21

#: Indices of the RSU-relative position inside the observation vector. They are
#: the two features `NeighbourhoodView` measures agent-to-agent distance with, and
#: they must track `StateVectorizer`'s feature list rather than being restated as
#: literals at the point of use -- a stale index there would silently sort the
#: neighbours by traffic-light state.
FEATURE_REL_X: int = 5
FEATURE_REL_Y: int = 6

#: How many other agents a joint critic is shown for one decision.
#:
#: Three baselines take a neighbourhood as input, and NONE of them requires a
#: fixed width. This comment claimed the opposite until 2026-09-06 -- that
#: RES-MAPDDPG and I-HAMAPPO "need a FIXED width because they concatenate a
#: padded tensor" while only MADDPG-MT pools. Checked against the three
#: implementations, all three pool:
#:
#:   res_mapddpg.py:269   (emb * mask).sum(dim=1) / mask.sum(dim=1)
#:   i_hamappo.py:265     the same masked mean
#:   maddpg_mt.py         does not take `max_agents` at all
#:
#: A masked mean is independent of the padded width, so the cap is not an
#: architectural requirement of any of them. `self.max_agents` appears in exactly
#: two operations in each of the two models that accept it -- a slice and a pad
#: -- and nowhere else, so it allocates a tensor and truncates a list. That is
#: all it does.
#:
#: The wrong version of this comment caused a real error elsewhere in the project:
#: another session built a distinction between "fixed-width" and "pooling" models
#: on the strength of it. Corrected here rather than worked around.
#:
#: 16 is A CAP, NOT A COUNT, and it is OURS, not the papers'. Every one of the
#: three assumes a fixed agent population and none says what to do when it
#: changes, because in their scenarios it does not. Measured 2026-09-06, the
#: in-coverage population peaks at 167 vehicles at density 30
#: (`results/hoorl_offline/n_active_saturation.json`), so at the busy end a joint
#: critic sees the 16 nearest of well over a hundred -- under a tenth of the
#: neighbourhood. All three papers' contribution is a critic that sees more than
#: its actor does, so truncating that view cuts at the mechanism being compared.
#:
#: 192 as of 2026-09-07, from 16. Three things decided it, and the third is a
#: reservation rather than a reason.
#:
#:   1. COST IS NOT A CONSTRAINT ANYWHERE IN THIS RANGE. Inference and the
#:      gradient step were both timed at 16, 32, 64, 128 and 192
#:      (`results/diagnostics/inference_latency_by_cap.csv`,
#:      `update_cost_by_cap.csv`), and again inside a real 600-step run at 16 and
#:      192, three repeats per placement
#:      (`results/diagnostics/live_latency_by_cap.csv`). Buffer memory at 192
#:      with 10,000 transitions is 330 MB.
#:
#:      WHAT THE LIVE MEASUREMENT DOES AND DOES NOT SHOW. 192 read FASTER at
#:      every statistic -- 0.06 ms at the mean, 0.41 ms at the 99th percentile --
#:      while three repeats of one cell spread by 0.92 to 1.16 ms at that
#:      percentile. Twelve runs with an effect that far below the spread cannot
#:      establish that the cap does nothing; they establish that this measurement
#:      CANNOT DETECT what it does. The two statements are different and only the
#:      second is supported.
#:
#:      The decision does not need the first. 0.41 ms is 0.4 % of the 0.1 s
#:      scheduling step, so an effect of that size is not a constraint even if it
#:      is real, and more repeats would only settle whether a quantity too small
#:      to matter is genuine. That is why twelve runs are enough: not "there is no
#:      difference" but "a difference this size does not bear on the choice".
#:   2. ONLY 192 COVERS THE NEIGHBOURHOOD. From
#:      `results/hoorl_offline/neighbour_coverage_by_cap.csv`, the fraction of
#:      rows whose entire neighbourhood fits is 0.0143 at 16, 0.0613 at 64 and
#:      0.0343 at 128 for density 30, against 0.9991 at 192. That is a
#:      qualitative break, not a gradient.
#:   3. LARGER IS NOT KNOWN TO BE BETTER, AND UNDER A MASKED MEAN IT MAY BE
#:      WORSE. I-HAMAPPO and RES-MAPDDPG pool with a plain masked mean, which
#:      cannot weight a near vehicle above a far one; widening the cap therefore
#:      dilutes the near neighbours that dominate interference into an average
#:      over the whole coverage disc. MADDPG-MT is the exception: it
#:      concatenates a masked MAX-pool beside the mean, and a max over more slots
#:      cannot be diluted by them. So the risk is specific to two of the three.
#:
#: WHOSE PROBLEM THE DILUTION IS. Ours. All three papers assume a fixed agent
#: population -- Parvini et al. fix the platoon count outright -- and none
#: specifies a pooling rule for a population that changes, so the masked mean is
#: this project's construction in every case and so is anything it dilutes. It
#: belongs in the porting limitations, not in a description of the methods.
#:
#: WHAT SETTLES IT. An ablation over 16, 64 and 192 after HPO. It is deferred
#: rather than run now because the cap interacts with the tuned hyper-parameters
#: and re-tuning inside an ablation would confound the two. Until then 192 is the
#: choice that DISCARDS the least: a truncated neighbour is information the
#: network cannot recover by any means, whereas a diluted one is information that
#: is present and used badly, and only the second is fixable downstream. The
#: offline dataset stores the neighbourhood BEFORE truncation, so the ablation is
#: a re-read of one collection at three widths rather than three collections.
MAX_NEIGHBOURS: int = 192

#: Divisor for observation feature [15], vehicles queued ahead in the lane.
#:
#: 25 as of 2026-09-06, from 20. At 20 the feature was clipped for 3.46 % of
#: observations; at 25 it is 1.11 % and at 40 it is zero.
#:
#: WHY NOT SIMPLY THE VALUE THAT ELIMINATES CLIPPING. Because the trade here is
#: unlike the one for `N_ACTIVE_MAX_OBS`. Past the point where clipping stops,
#: raising a bound is a pure rescaling -- the distribution's shape and its number
#: of distinct values are preserved and only the standard deviation shrinks --
#: so the only cost that survives is the feature's size RELATIVE TO THE OTHERS,
#: since a feature pressed towards zero contributes little in the first layer
#: while its weights are still small. For `n_active` that cost was slight, and
#: the clipping it removed was 9.31 % concentrated in the congested densities the
#: scheduler exists for. For the queue it is the other way round: eliminating the
#: last of the clipping costs more band than the clipping is worth.
#:
#: Against the other magnitude features of this observation, measured on the
#: 128,223-transition collection:
#:
#:     bound   clipped   std      rank among the 12 magnitude features
#:      20     3.46 %    0.2603   42nd percentile
#:      25     1.11 %    0.2211   42nd percentile
#:      26     0.82 %    0.2138   33rd
#:      30     0.10 %    0.1870   33rd
#:      40     0.00 %    0.1404    8th
#:
#: 25 cuts the clipping by two thirds without leaving the band 20 occupied. 30
#: and beyond buy the remaining one per cent by dropping a band, and there is no
#: evidence that distinguishing "24 queued" from "35 queued" changes a grant --
#: unlike the contention feature, where the clipped region was demonstrably where
#: the decision matters.
#:
#: THE BAND MUST BE RECOMPUTED UNDER THE CONSTANTS IN FORCE. Ranking these
#: candidates against a band measured before `N_ACTIVE_MAX_OBS` and
#: `DIST_TO_STOPLINE_REF_M` moved put 25 at the 25th percentile instead of the
#: 42nd and would have rejected it: those two features' own spreads changed, so
#: the comparison was against a distribution that no longer existed.
#:
#: THIS CONSTANT WAS NEVER A CANDIDATE UNTIL IT WAS MEASURED. It is a code
#: literal, was classified as such, and "code constant" was taken to mean
#: "settled" -- a different claim from "does not clip", which is the one that
#: matters for an observation bound. It was found by sweeping every normalising
#: constant rather than the ones already suspected.
QUEUE_MAX_DEFAULT: float = 25.0

#: Divisor for observation feature [12], metres. NOT `RSU_RANGE`.
#:
#: Separated from the coverage radius on 2026-09-06. Feature [12] divided by
#: `rsu_range` and clipped there, which conflated two unrelated quantities: the
#: RSU's radio reach, which decides who is in coverage, and the distance at which
#: a stop line stops mattering to a scheduling decision. They have no reason to
#: be equal and moving one should not move the other.
#:
#: 900 m, from measurement. Over 128,223 transitions the stop-line distance runs
#: to exactly 900 m and its distribution is BIMODAL: 71.8 % below 300 m, then a
#: gap with zero samples between 300 and 500 m, then 26.0 % between 600 and
#: 900 m. The gap appears at the same place and width on all three road networks
#: the collection visited, so it is the block geometry rather than an accident of
#: one road -- the explanation predicted a recurrence and the recurrence happened.
#:
#: At 300 m the far mode was entirely destroyed: 23.1 % of observations read
#: exactly 1.0 whether the stop line was 300 m or 900 m away. The far mode is not
#: irrelevant either. `DELTA_MAX` is 45 s and `V_MAX_OBS` about 16 m/s, so a
#: vehicle covers 719 m within a single silence interval and a stop line at 900 m
#: is reachable inside the horizon the policy is choosing over.
#:
#: The cost of widening is real and is the usual trade: the near mode now
#: occupies [0, 0.33] instead of [0, 1]. It is milder here than it would be for a
#: unimodal feature, because the two modes land in different parts of the range
#: rather than piling up together.
DIST_TO_STOPLINE_REF_M: float = 900.0

#: Divisor for observation feature [11], seconds.
#:
#: Named on 2026-09-06. It was a literal 60.0 inside `vectorize_from_dict`, which
#: meant `observation_constants()` could not read it and had to recover it by
#: feeding the vectoriser a known value and inverting the answer. A constant that
#: has to be measured to be known is one an offline dataset can be normalised
#: against without anybody noticing it moved.
PHASE_REMAINING_REF_S: float = 60.0

#: Transmit power bounds, dBm.
#: 23 dBm is the 3GPP TS 36.101 / 38.101 power-class-3 UE maximum transmit power;
#: 10 dBm is the design-approved lower bound for a usable V2I uplink.
P_MIN: float = 10.0
P_MAX: float = 23.0

#: Delta (update interval) minimum, seconds (ETSI EN 302 637-2 CAM T_GenCamMin).
DELTA_MIN: float = 0.1


def scenario_dir(base_path: Optional[str] = None) -> str:
    """Directory holding the generated SUMO scenario these constants describe.

    `make_sumo_set.resolve_base_path` is the single owner of that decision, so
    this defers to it rather than deciding again. The three readers below used to
    hardcode `os.path.dirname(__file__) + "/sumo"`, i.e. the PACKAGE directory,
    which is not where the scenario is whenever `PAPER4_SUMO_DIR` is set or a
    caller passes an explicit path. DELTA_MAX, V_LIMIT, V_MAX_OBS and E_REF would
    then describe a network on disk that the simulation was not running: an
    isolated process generated its own net.xml and normalised against somebody
    else's, silently, because the two happen to agree while every run uses the
    same AV_SPEED and signal plan.

    Falls back to the package directory only when the sumo package cannot be
    imported, which reproduces the previous behaviour rather than guessing.
    """
    try:
        from src.sumo.make_sumo_set import resolve_base_path
    except Exception:  # pragma: no cover - only when the sumo package is unavailable
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "sumo")
    return resolve_base_path(base_path)


def get_sumo_max_red_phase_duration(
    net_file: Optional[str] = None,
    default_duration: float = 45.0,
    base_path: Optional[str] = None,
) -> float:
    """
    Dynamically extract the maximum Red traffic light phase duration (seconds)
    from SUMO's generated network XML file (generated.net.xml) or TraCI.

    Parses all <tlLogic> program definitions in the net file, computes for each
    signal link across cyclic phases the maximum consecutive duration of 'r'/'R'
    phases (handling cycle wrap-around), and returns the overall maximum.

    If the network file is not yet generated or cannot be parsed, falls back
    safely to `default_duration` (45.0 s).
    """
    if net_file is None:
        net_file = os.path.join(scenario_dir(base_path), "generated.net.xml")

    if not os.path.exists(net_file):
        return default_duration

    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
        max_red = 0.0

        for tl in root.findall("tlLogic"):
            phases = tl.findall("phase")
            if not phases:
                continue
            durations = [float(p.get("duration", 0.0)) for p in phases]
            states = [p.get("state", "") for p in phases]
            if not states or not durations:
                continue
            num_links = max(len(s) for s in states)
            n_phases = len(phases)

            for link_idx in range(num_links):
                curr_red = 0.0
                max_link_red = 0.0
                # Double the cycle to handle cyclic wrap-around
                for step in range(2 * n_phases):
                    p_idx = step % n_phases
                    char = states[p_idx][link_idx] if link_idx < len(states[p_idx]) else "g"
                    if char in ("r", "R"):
                        curr_red += durations[p_idx]
                        if curr_red > max_link_red:
                            max_link_red = curr_red
                    else:
                        curr_red = 0.0
                total_cycle = sum(durations)
                max_link_red = min(max_link_red, total_cycle)
                if max_link_red > max_red:
                    max_red = max_link_red

        return float(max_red) if max_red > 0.0 else default_duration
    except Exception:
        return default_duration


#: Delta (update interval) maximum, dynamically extracted from SUMO net XML.
DELTA_MAX: float = get_sumo_max_red_phase_duration()


def get_sumo_max_edge_speed(
    net_file: Optional[str] = None,
    default_speed: float = 13.32,
    base_path: Optional[str] = None,
) -> float:
    """
    Maximum lane speed limit (m/s) declared anywhere in the generated network.

    Read from the net file for the same reason `DELTA_MAX` is: a normalisation
    constant that is silently inconsistent with the scenario it normalises is a
    defect waiting to happen. `make_sumo_set.py` randomises each edge's speed
    around `AV_SPEED` with +/- `DEL_SPEED`, so the effective limit is a property
    of the generated network, not a literal anyone can restate correctly.

    Falls back to `default_speed` (the 40 km/h + 20 % case) when the network has
    not been generated yet.
    """
    if net_file is None:
        net_file = os.path.join(scenario_dir(base_path), "generated.net.xml")

    if not os.path.exists(net_file):
        return default_speed

    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
        speeds = []
        for edge in root.findall("edge"):
            # Internal junction edges inherit their speed from the corner limit
            # and would drag the maximum down; they are not where vehicles cruise.
            if edge.get("function") == "internal":
                continue
            for lane in edge.findall("lane"):
                v = lane.get("speed")
                if v is not None:
                    speeds.append(float(v))
        return float(max(speeds)) if speeds else default_speed
    except Exception:
        return default_speed


#: Scenario speed limit (m/s), derived from the generated network.
V_LIMIT: float = get_sumo_max_edge_speed()


def get_sumo_max_speed_factor(rou_file: Optional[str] = None,
                              default_factor: float = 1.0,
                              base_path: Optional[str] = None) -> float:
    """Upper bound of the `speedFactor` distribution declared in the route file.

    SUMO's DEFAULT_VEHTYPE draws `speedFactor` from a truncated normal
    `normc(1, 0.1, 0.2, 2)`, so vehicles legitimately exceed the lane speed limit.
    Measured on this scenario: the fastest observed vehicle ran at 14.768 m/s
    against a lane limit of 13.32 m/s (+11 %), and 8.62 % of all observations were
    clipped to exactly 1.0 in the normalised speed feature -- i.e. the fastest
    vehicles, which are precisely the ones whose constant-velocity extrapolation
    decays quickest, were indistinguishable from each other in the observation.

    `make_sumo_set.py` therefore declares an explicit `<vType>` with a *bounded*
    speedFactor, and this reads that bound back so the normaliser is a property of
    the scenario on disk rather than a literal. Falls back to 1.0 (no headroom)
    when no explicit vType is declared, which reproduces the pre-existing
    behaviour rather than silently inventing headroom.
    """
    if rou_file is None:
        rou_file = os.path.join(scenario_dir(base_path), "generated.rou.xml")

    if not os.path.exists(rou_file):
        return default_factor

    try:
        tree = ET.parse(rou_file)
        root = tree.getroot()
        best = 0.0
        for vtype in root.findall("vType"):
            spec = vtype.get("speedFactor")
            if spec is None:
                continue
            text = str(spec).strip()
            if text.lower().startswith("normc"):
                # normc(mean, dev, min, max) -- the fourth field is the hard cap.
                inner = text[text.find("(") + 1: text.rfind(")")]
                parts = [p.strip() for p in inner.split(",")]
                if len(parts) >= 4:
                    best = max(best, float(parts[3]))
                elif parts:
                    best = max(best, float(parts[0]))
            else:
                best = max(best, float(text))
        return float(best) if best > 0.0 else default_factor
    except Exception:
        return default_factor


#: Highest speed a vehicle can actually reach in this scenario (m/s).
#:
#: Kept separate from `V_LIMIT` on purpose. `V_LIMIT` is the *road's* declared
#: limit and is what `E_REF` means ("one second of travel at the scenario speed
#: limit"), so moving it would silently rescale the reward. `V_MAX_OBS` is the
#: observable ceiling and is only ever used to normalise the speed/velocity
#: features, which is where the saturation was.
V_MAX_OBS: float = V_LIMIT * get_sumo_max_speed_factor()

#: RSU communication range (m). `src/sumo/make_sumo_set.py` owns this value --
#: it is what actually builds the network geometry (EDGE_LENGTH is derived from
#: it) -- so every consumer must read it from there instead of restating 300.0.
#: A literal here would go stale the moment anyone sweeps the range, and the
#: mismatch would be silent: observations would normalise distances against one
#: radius while the environment admitted vehicles using another.
try:
    from src.sumo.make_sumo_set import RSU_RANGE as _SS_RSU_RANGE
    RSU_RANGE: float = float(_SS_RSU_RANGE)
except Exception:  # pragma: no cover - only when the sumo package is unavailable
    RSU_RANGE = 300.0


def get_n_active_max_obs(default_max: float = 100.0) -> float:
    """Highest vehicle count the RSU's ledger can hold in this scenario.

    Normaliser for observation feature [13] (`n_active`, the contention level).
    It was the literal 100.0, and the measured in-range counts run 22.2, 36.7,
    68.2, 91.5, 123.0, 138.3, 141.7 across the density grid 5..35, so the feature
    was pinned to exactly 1.0 at densities 25, 30 and 35 -- three of the seven
    training densities, about 43 % of all episodes, and precisely the congested
    regime the scheduler exists to handle. The congestion signal died where
    congestion mattered.

    Same treatment as `V_MAX_OBS`, which removed the 8.62 % saturation in the
    speed feature: the ceiling is derived from the scenario rather than restated.
    Here it is the road capacity inside the coverage disc at the busiest density
    the study is defined over,

        max(DENSITY_GRID) [veh/km/lane] * rsu_coverage_lane_km() [km-lane]

    = 35 * 4.8 = 168 vehicles.

    THAT FORMULA DOES NOT HOLD, and 168 was superseded on 2026-09-06. It computes
    a FREE-FLOW capacity: density times length assumes vehicles spread evenly.
    They do not. Signals pack them, and the measured in-coverage count reaches
    194 -- twenty-six vehicles past the ceiling the formula gives -- clipping
    9.31 % of a 128,223-transition collection, concentrated at densities 25 to 35.
    The formula is not wrong arithmetic; the condition it rests on is false in
    this environment. Its own evidence said so and was read the other way: the
    141.7 quoted above is a MEAN, and a ceiling meant to prevent saturation has to
    clear a TAIL.

    `N_ACTIVE_MAX_OBS_MEASURED` replaces it. The derivation is in that constant.

    Falls back to the historical 100.0 only when the sumo package cannot be
    imported, which reproduces the previous behaviour instead of inventing a
    ceiling. Kept as `n_active_free_flow_capacity()` for reference and for the
    manuscript's account of why the formula was abandoned.
    """
    try:
        from src.sumo.make_sumo_set import DENSITY_GRID, rsu_coverage_lane_km
    except Exception:  # pragma: no cover - only when the sumo package is unavailable
        return float(default_max)
    grid = [float(d) for d in DENSITY_GRID if float(d) > 0.0]
    lane_km = float(rsu_coverage_lane_km())
    if not grid or lane_km <= 0.0:
        return float(default_max)
    return max(grid) * lane_km


#: Observable ceiling of the contention feature, vehicles. MEASURED, not derived.
#:
#: 250 as of 2026-09-06, replacing the free-flow capacity of 168. The derivation,
#: with every step's evidence:
#:
#:   1. The collection of 128,223 transitions -- 2000 steps per cell, three flow
#:      seeds, road cycles 0 to 2 -- peaks at 194 in-coverage vehicles and clips
#:      9.31 % of its rows at 168.
#:   2. Training walks road cycles 0 to 14, not 0 to 2. The per-cycle maxima at
#:      full episode length are 169, 194 and 187, a standard deviation of 10.4.
#:      The expected maximum of fifteen such draws is about 1.74 standard
#:      deviations above their mean, i.e. 183.3 + 1.74 * 10.4 = 201.
#:   3. A separate fifteen-cycle sweep peaked at 160, and that figure is NOT
#:      usable directly: it ran 600 steps on one flow seed against the
#:      collection's 2000 steps on three, and a shorter look sees less of the
#:      tail. The ratio between the two conditions is 1.212. What the sweep
#:      contributes is the cycle-to-cycle SPREAD, which is what step 2 needs.
#:   4. 250 clears the extrapolated 201 by 24 %.
#:
#: WHY SUCH A WIDE MARGIN IS AFFORDABLE. Once nothing is clipped, dividing by a
#: larger ceiling is a pure rescaling: measured across candidates from 200 to 400,
#: the variation within the occupied span stays at 0.2254 and the number of
#: distinct values at 184, with only the standard deviation shrinking. The
#: remaining cost is the feature's size relative to the others, and against this
#: observation's magnitude features (median standard deviation 0.299) 200, 220 and
#: 250 all sit at the 17th percentile while 300 and above drop to the 8th. 250 is
#: the largest value that buys margin without leaving that band.
#:
#: LIMITS, STATED. Only three road cycles were measured at full episode length,
#: so the standard deviation of 10.4 rests on three points; the extrapolation
#: assumes the per-cycle maxima are roughly normal; and the fifteen-cycle sweep
#: used a single flow seed.
#:
#: THE NORMAL ASSUMPTION IN STEP 2 IS KNOWN TO BE WRONG, AND THE MARGIN COVERS
#: IT. 1.74 is the expected maximum of fifteen standard normal draws, but the
#: quantities being maximised are THEMSELVES per-cycle maxima, and maxima follow
#: an extreme-value law whose right tail is heavier than the normal's. So 201 is
#: closer to a lower bound than to a central estimate. What makes it usable is
#: the size of the gap that was actually taken: 250 - 201 = 49 is 4.7 standard
#: deviations, not the 2 the normal calculation would have asked for, and that
#: width absorbs the error in the assumption. Fitting an extreme-value
#: distribution instead was considered and rejected: three points cannot identify
#: its shape parameter, so the fit would replace a stated approximation with an
#: unstated one.
N_ACTIVE_MAX_OBS_MEASURED: float = 250.0

#: The superseded free-flow formula, kept so the manuscript can say what was
#: replaced and why. Not used to normalise anything.
n_active_free_flow_capacity = get_n_active_max_obs

N_ACTIVE_MAX_OBS: float = N_ACTIVE_MAX_OBS_MEASURED

def refresh_scenario_constants(base_path: Optional[str] = None) -> Dict[str, float]:
    """Re-read the scenario-derived constants from the generated network.

    DELTA_MAX, V_LIMIT and E_REF describe the network on disk, not this module.
    They are computed once at import, which is wrong the moment `make_sumo_files()`
    writes a different network afterwards -- a changed signal plan moves DELTA_MAX,
    a changed AV_SPEED moves V_LIMIT and E_REF, and nothing would notice. The
    environment calls this right after generating its network, so the constants
    describe the scenario actually being simulated.

    Consumers must read these through a live lookup rather than capturing them in
    a default argument, which binds at definition time. `ActionDecoder` and
    `StateVectorizer` take 0.0 to mean "resolve now"; `norm_sq_error` reads the
    module global on every call.

    `base_path` says WHICH scenario directory to describe. `AoiV2IEnv` passes the
    directory it generated into, so a process running an isolated scenario does
    not normalise against the shared one.
    """
    global DELTA_MAX, V_LIMIT, V_MAX_OBS, E_REF
    # One resolved directory for all three reads, so the signal plan, the lane
    # limit and the speedFactor bound cannot come from different scenarios.
    target_dir = scenario_dir(base_path)
    DELTA_MAX = get_sumo_max_red_phase_duration(base_path=target_dir)
    V_LIMIT = get_sumo_max_edge_speed(base_path=target_dir)
    V_MAX_OBS = V_LIMIT * get_sumo_max_speed_factor(base_path=target_dir)
    E_REF = V_LIMIT * 1.0
    return {"DELTA_MAX": DELTA_MAX, "V_LIMIT": V_LIMIT,
            "V_MAX_OBS": V_MAX_OBS, "E_REF": E_REF}


#: Estimation-error reference scale (metres), design_spec_v2 D5.
#:
#: One second of travel at the scenario speed limit. The point of dividing a
#: position error by a speed is that it converts metres into an *equivalent age*:
#: `e = E_REF` means the RSU's belief about this vehicle is as wrong as if it had
#: simply not heard from it for one second. That is the natural unit for an AoI
#: paper, and unlike a bare literal it follows the scenario automatically -- raise
#: `AV_SPEED` in make_sumo_set.py and this tracks it.
#:
#: NOT the RSU communication range: `e` is a positioning error, the range is a
#: link-budget quantity, and normalising one by the other pushes the error term
#: roughly two orders of magnitude below the power term. Since `hpo.py` normalises
#: w1..w4 to sum to 1, no weight Optuna can sample recovers from that.
E_REF: float = V_LIMIT * 1.0


def extrapolate(last_pos: Tuple[float, float],
                last_vel: Tuple[float, float],
                age: float) -> Tuple[float, float]:
    """The RSU's dead-reckoned belief: last reported position carried forward.

        p_hat(t) = p_last + v_last * age

    Constant-velocity extrapolation is deliberate, not a simplification to
    apologise for: it is what makes a stopped vehicle's stale record stay exact
    (v = 0 so the belief never drifts) while a manoeuvring one decays. That
    asymmetry is the whole premise of scheduling updates by need.
    """
    return (float(last_pos[0]) + float(last_vel[0]) * float(age),
            float(last_pos[1]) + float(last_vel[1]) * float(age))


def estimation_error(true_pos: Tuple[float, float],
                     last_pos: Tuple[float, float],
                     last_vel: Tuple[float, float],
                     age: float) -> float:
    """Euclidean distance between ground truth and the RSU's extrapolation.

    This is `e` in the reward: the quantity `norm_sq_error` squashes and the
    quantity `I_redundant` thresholds. One definition, one function, so the
    paper's symbol and the code cannot drift apart.
    """
    ex, ey = extrapolate(last_pos, last_vel, age)
    return math.hypot(float(true_pos[0]) - ex, float(true_pos[1]) - ey)


def norm_sq_error(err_m: float, e_ref: float = 0.0) -> float:
    """Normalise a squared position error into [0, 1) -- design_spec_v2 D5.

        Norm(e^2) = e^2 / (e^2 + e_ref^2)

    Chosen over `min(1, e^2 / e_max^2)` because the clipped form has zero
    gradient everywhere past `e_max`. With Delta reaching 45 s a moving vehicle
    leaves that region within about a second, so the clipped form would stop
    distinguishing "slightly stale" from "hopelessly stale" exactly where the
    scheduling decision matters. This form is strictly monotone in `e`, equals
    0.5 at `e = e_ref`, and never saturates.
    """
    ref = float(e_ref) if e_ref and e_ref > 0.0 else E_REF
    e2 = float(err_m) ** 2
    return float(e2 / (e2 + ref * ref)) if (e2 + ref * ref) > 0.0 else 0.0


class StateVectorizer:
    """
    Normalized State Vectorizer; the width is STATE_DIM, never a literal.

    Transforms raw vehicle kinematics, RSU spatial metrics, TraCI TLS signal states,
    and channel congestion indicators into a normalized feature vector in [-1.0, 1.0].

    Features:
    [0]  Last prediction error, normalized: norm_sq_error(e_last) in [0.0, 1.0).
         How wrong the RSU's dead reckoning was at this vehicle's most recent
         update. Replaces the former normalized-age slot, which is identically
         zero at every SMDP decision epoch and therefore carried no signal.
    [1]  Normalized Vx: clip(vx / v_max, -1.0, 1.0)
    [2]  Normalized Vy: clip(vy / v_max, -1.0, 1.0)
    [3]  Normalized Speed: clip(speed / v_max, 0.0, 1.0)
    [4]  Normalized Acceleration: clip(accel / a_max, -1.0, 1.0)
    [5]  Relative X: clip(dx / rsu_range, -1.0, 1.0)
    [6]  Relative Y: clip(dy / rsu_range, -1.0, 1.0)
    [7]  Normalized Distance: clip(dist / rsu_range, 0.0, 1.0)
    [8]  TLS Red one-hot: 1.0 if red else 0.0
    [9]  TLS Yellow one-hot: 1.0 if yellow else 0.0
    [10] TLS Green one-hot: 1.0 if green else 0.0
    [11] Phase remaining time: clip(time_to_switch / 60.0, 0.0, 1.0)
    [12] Distance to stopline: clip(dist_to_stopline / DIST_TO_STOPLINE_REF_M,
         0.0, 1.0). The divisor is NOT `rsu_range`; see that constant for why the
         two were separated and how 900 m was measured.
    [13] Active vehicles in cell: clip(n_active / n_active_max, 0.0, 1.0), where
         n_active_max is N_ACTIVE_MAX_OBS (the coverage disc's road capacity at
         the busiest density in the grid), NOT a literal 100
    [14] MEAN channel busy ratio over the subchannels: clip(cbr, 0.0, 1.0).
         Named `cbr_mean_channels` in the feature table. It is the ABSOLUTE
         congestion level; [17..20] carry the per-channel deviation from it, and
         the two are not interchangeable. Calling this one simply "cbr" is how
         it went unnoticed that the reward charges a decision against a SINGLE
         channel's occupancy while the observation only ever showed their
         average.
    [15] n_queue (Conversation.md S1): normalized number of vehicles queued ahead in the
         same lane -- clip(n_queue / queue_max, 0.0, 1.0)
    [16] heading (Conversation.md S1): signed approach/recede indicator w.r.t. the RSU --
         cos(angle between velocity vector and the vehicle->RSU vector) in [-1.0, 1.0].
         +1.0 = driving straight at the RSU, -1.0 = driving straight away, 0.0 = stopped
         or moving tangentially.
    [17..20] PER-SUBCHANNEL busy ratio RELATIVE TO THE MEAN:
         subchannel_cbr[k] / mean(subchannel_cbr) for k = 0..3, and 1.0 for every
         k when that mean is zero. Added 2026-09-06.

         WHY THESE EXIST WHEN [14] ALREADY REPORTS CONGESTION. Because [14] is
         the MEAN over the subchannels and the action space contains a discrete
         subchannel choice. The reward charges that choice against the occupancy
         of the ONE channel it used (`hot_swap_trainer._finalize_interval`, via
         `subchannel_cbr[ch_idx] / CBR_REF`), so the policy was being penalised
         on a quantity it could not observe: every channel looked equally busy to
         it because it only ever saw their average.

         THE SPREAD IS NOT SMALL. Measured 2026-09-06 over 4,200 environment
         steps across the density grid
         (`etc/scripts/measure_observation_gaps.py`,
         `results/hoorl_offline/observation_gaps_by_cell.csv`): the gap between
         the busiest and the idlest subchannel averages 1.81x to 3.20x the mean
         occupancy itself, and that is under a policy choosing channels at
         random. Averaged over a whole episode the four channels are used
         equally, which is why [14] looks stable; at any given instant they are
         not, and the instant is when the decision is made.

         [14] IS KEPT rather than replaced by these four. The mean is what the
         Delta and power decisions need -- a network-wide congestion level -- and
         removing it would change the learning conditions of those two axes at
         the same time as adding the four, leaving no way to attribute a change
         in results to either.
    """

    #: Canonical observation dimension (module-level single source of truth).
    STATE_DIM: int = STATE_DIM

    def __init__(
        self,
        rsu_range: float = 0.0,
        v_max: float = 0.0,
        a_max: float = 5.0,
        queue_max: float = QUEUE_MAX_DEFAULT,
        n_active_max: float = 0.0,
    ) -> None:
        # 0 means "derive from the scenario", same convention as v_max below.
        self.rsu_range = float(rsu_range) if rsu_range and rsu_range > 0.0 else RSU_RANGE
        # 0 means "derive from the scenario". The former literal 30.0 m/s was
        # 2.3x the fastest lane in the generated network, so the speed features
        # only ever used the bottom 44 % of their range.
        #
        # V_MAX_OBS, not V_LIMIT: vehicles exceed the lane limit by their
        # `speedFactor`, and normalising by the limit clipped 8.62 % of all
        # observations to exactly 1.0 -- the fastest vehicles, the ones this
        # paper most needs to tell apart. E_REF stays on V_LIMIT so the reward
        # scale is untouched by this fix.
        self.v_max = float(v_max) if v_max and v_max > 0.0 else V_MAX_OBS
        self.a_max = float(a_max)
        self.queue_max = max(1.0, float(queue_max))
        # 0 means "derive from the scenario", same convention as v_max. The
        # former literal 100.0 saturated feature [13] at densities 25, 30 and 35
        # (measured in-range counts 123.0, 138.3, 141.7), i.e. in 43 % of the
        # training episodes the contention input was the constant 1.0.
        self.n_active_max = (
            float(n_active_max) if n_active_max and n_active_max > 0.0 else N_ACTIVE_MAX_OBS
        )

    @property
    def state_dim(self) -> int:
        """Dimension of the emitted observation vector. Read this instead of hardcoding."""
        return STATE_DIM

    # ------------------------------------------------------------------
    # Feature helpers for the two design-mandated features (n_queue, heading)
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_queue_count(*sources: Optional[Dict[str, Any]]) -> float:
        """
        Recover the number of vehicles queued ahead in the same lane from whatever
        telemetry the dynamics/TLS feature dicts expose.

        Preferred keys are a real halting count published by the SUMO layer
        (TraCI lane.getLastStepHaltingNumber). If none is present, fall back to the
        leader-vehicle signal already produced by dynamics_predictor.extract_tls_features:
        a stopped/crawling leader within a plausible queue gap implies at least one
        vehicle queued ahead.
        """
        for src in sources:
            if not src:
                continue
            for key in ("n_queue", "queue_length", "lane_halting_number", "halting_number"):
                val = src.get(key)
                if val is not None:
                    try:
                        return max(0.0, float(val))
                    except (TypeError, ValueError):
                        continue
        for src in sources:
            if not src:
                continue
            gap = src.get("leader_gap")
            lspd = src.get("leader_speed")
            if gap is None or lspd is None:
                continue
            try:
                gap_f, lspd_f = float(gap), float(lspd)
            except (TypeError, ValueError):
                continue
            if math.isfinite(gap_f) and gap_f <= 30.0 and lspd_f <= 1.0:
                return 1.0
            return 0.0
        return 0.0

    @staticmethod
    def _compute_heading(vx: float, vy: float, dx: float, dy: float) -> float:
        """
        Signed approach/recede indicator in [-1.0, 1.0].

        dx, dy are the RSU-relative coordinates of the vehicle (vehicle - RSU), so the
        vehicle->RSU direction is (-dx, -dy). Returns the normalized dot product of the
        velocity vector with that direction: +1 approaching head-on, -1 receding,
        0 when stopped or exactly at the RSU.
        """
        speed = math.hypot(vx, vy)
        dist = math.hypot(dx, dy)
        if speed < 1e-6 or dist < 1e-6:
            return 0.0
        cos_theta = (vx * (-dx) + vy * (-dy)) / (speed * dist)
        return float(np.clip(cos_theta, -1.0, 1.0))

    def vectorize(
        self,
        vehicle_node: Any,
        rsu_node: Any,
        current_time: float,
        tls_info: Optional[Dict[str, Any]] = None,
        cbr: float = 0.0,
        n_active: int = 1,
        n_queue: Optional[float] = None,
    ) -> np.ndarray:
        """Node-object adapter over `vectorize_from_dict`. Not the production path.

        There used to be two independent implementations of the same 17-dim
        layout, which violated design principle P1 ("the observation vector is
        built in exactly one place") and had already drifted apart: this one
        resolved `n_queue` by looking at the TLS feature dict FIRST, and that
        dict's `n_queue` is `dynamics_predictor.extract_queue_features`, i.e. a
        live `lane.getLastStepVehicleIDs` + `vehicle.getSpeed` measurement that no
        real roadside unit can make. `vectorize_from_dict` looks at the state dict
        first, and the environment puts its ledger-reconstructed count there (D3),
        so the production path was safe while this one was a dormant leak.

        It is now a translation layer: it builds a state dict and defers, so there
        is one implementation of the layout, and `n_queue` is taken from the
        explicit argument or from the vehicle node itself -- never from the TLS
        dict, which is privileged information.
        """
        vec = np.zeros(STATE_DIM, dtype=np.float32)
        if vehicle_node is None or rsu_node is None:
            return vec

        vel = getattr(vehicle_node, "vel", (0.0, 0.0))
        if hasattr(vehicle_node, "speed"):
            spd_val = vehicle_node.speed() if callable(vehicle_node.speed) else vehicle_node.speed
        else:
            spd_val = math.hypot(vel[0], vel[1])

        tls = tls_info or {}
        if not tls and hasattr(vehicle_node, "_state_dict"):
            tls = (vehicle_node._state_dict() or {}).get("tls_features", {})

        if n_queue is None:
            # Vehicle-owned telemetry only. The TLS dict is deliberately NOT a
            # source here (see docstring).
            q_cnt = self._extract_queue_count(getattr(vehicle_node, "__dict__", None))
        else:
            q_cnt = max(0.0, float(n_queue))

        rsu_pos = getattr(rsu_node, "pos", (0.0, 0.0))
        state_dict: Dict[str, Any] = {
            "pos": getattr(vehicle_node, "pos", (0.0, 0.0)),
            "vel": vel,
            "speed": float(spd_val),
            "accel": float(getattr(vehicle_node, "accel", 0.0)),
            "current_time": current_time,
            "last_pred_err": float(getattr(vehicle_node, "last_pred_err", 0.0)),
            "tls_features": tls,
            "cbr": cbr,
            "n_active": n_active,
            "n_queue": q_cnt,
        }
        return self.vectorize_from_dict(state_dict, tuple(rsu_pos))

    def vectorize_from_dict(self, state_dict: Dict[str, Any], rsu_pos: Tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
        """
        Convenience method to vectorize directly from a state dictionary.
        """
        vec = np.zeros(STATE_DIM, dtype=np.float32)
        pos = state_dict.get("pos", (0.0, 0.0))
        vel = state_dict.get("vel", (0.0, 0.0))
        speed = state_dict.get("speed", math.hypot(vel[0], vel[1]))
        accel = state_dict.get("accel", 0.0)
        # [0] Quality of the RSU's last prediction for this vehicle.
        #
        # This slot used to hold normalized age. Under the SMDP formulation age
        # is structurally zero at every decision epoch -- the RSU decides right
        # after an update lands -- so the feature reached the policy as a
        # constant and carried nothing. Measured: 1 unique value over a full run.
        #
        # What the RSU does know at that instant, for free, is how wrong its
        # dead-reckoned belief turned out to be just before the report arrived.
        # That is a direct read on how far this particular vehicle can be trusted
        # to stay predictable, which is exactly what choosing Delta needs.
        vec[0] = norm_sq_error(float(state_dict.get("last_pred_err", 0.0)))
        vec[1] = np.clip(vel[0] / self.v_max, -1.0, 1.0)
        vec[2] = np.clip(vel[1] / self.v_max, -1.0, 1.0)
        vec[3] = np.clip(float(speed) / self.v_max, 0.0, 1.0)
        vec[4] = np.clip(float(accel) / self.a_max, -1.0, 1.0)

        dx = float(pos[0] - rsu_pos[0])
        dy = float(pos[1] - rsu_pos[1])
        dist = state_dict.get("dist_to_rsu", math.hypot(dx, dy))
        vec[5] = np.clip(dx / self.rsu_range, -1.0, 1.0)
        vec[6] = np.clip(dy / self.rsu_range, -1.0, 1.0)
        vec[7] = np.clip(float(dist) / self.rsu_range, 0.0, 1.0)

        tls = state_dict.get("tls_features", state_dict)
        state = str(tls.get("state", "g")).lower()
        vec[8] = 1.0 if state in ["r", "red"] else 0.0
        vec[9] = 1.0 if state in ["y", "yellow"] else 0.0
        vec[10] = 1.0 if state in ["g", "green"] else 0.0
        # [11] and [12] when there is NO SIGNAL AHEAD.
        #
        # `getNextTLS` returns nothing for 2.63 % of observations (measured
        # 2026-09-06 over 352,980 samples), and `extract_tls_features` reports
        # that as state "none" with an infinite distance. The two slots used to
        # be filled with 30.0 s and `self.rsu_range`, which normalise to 0.5 and
        # 1.0 -- and both of those are values a REAL reading produces. A signal
        # thirty seconds from switching and a stop line at the coverage edge are
        # ordinary situations, so the observation asserted a specific traffic
        # situation for a vehicle that had no signal at all.
        #
        # BOTH ARE NOW 0.0, and the point is that they AGREE rather than that 0.0
        # is the true value. There is no true value; what a policy has to learn is
        # "when [8], [9] and [10] are all zero, ignore [11] and [12]", and that
        # rule is simplest when the ignored slots hold one constant. 0.0 is chosen
        # because it is the value least likely to arise legitimately alongside an
        # all-zero signal one-hot: a signal switching in zero seconds is red,
        # yellow or green by definition, and a stop line at zero metres likewise.
        #
        # NO SEPARATE VALIDITY FLAG. The all-zero one-hot at [8..10] already is
        # one -- it occurs only in this case -- so a twenty-second feature would
        # carry information the vector already holds, at the cost of invalidating
        # every checkpoint.
        #
        # `self.rsu_range` as the `.get` default was dead code and is gone. The
        # key is always present (`extract_tls_features` always sets it, to `inf`
        # when there is no signal), so the default never fired; it merely looked
        # like the fallback while `inf` was silently clipping to the same 1.0.
        tts = tls.get("time_to_switch", None)
        dts = tls.get("dist_to_stopline", None)
        has_signal = bool(vec[8] or vec[9] or vec[10])
        if not has_signal:
            vec[11] = 0.0
            vec[12] = 0.0
        else:
            vec[11] = np.clip(
                (float(tts) if tts is not None and np.isfinite(float(tts)) else 0.0)
                / PHASE_REMAINING_REF_S, 0.0, 1.0)
            vec[12] = np.clip(
                (float(dts) if dts is not None and np.isfinite(float(dts))
                 else DIST_TO_STOPLINE_REF_M) / DIST_TO_STOPLINE_REF_M, 0.0, 1.0)

        # [13] Contention. Normalised by the coverage disc's road capacity at the
        # busiest density in the grid (N_ACTIVE_MAX_OBS = 168 vehicles here), not
        # by a literal 100: measured in-range counts reach 141.7, so /100 clipped
        # this feature to exactly 1.0 at densities 25, 30 and 35.
        vec[13] = np.clip(float(state_dict.get("n_active", 1)) / self.n_active_max, 0.0, 1.0)
        vec[14] = np.clip(float(state_dict.get("cbr", 0.0)), 0.0, 1.0)

        # [15] n_queue: vehicles queued ahead in the same lane (design S1).
        # Prefer an explicit count on the state dict, then the TLS/dynamics feature
        # dict, then the leader-vehicle fallback.
        q_cnt = self._extract_queue_count(state_dict, tls)
        vec[15] = np.clip(q_cnt / self.queue_max, 0.0, 1.0)

        # [16] heading: signed approach (+) / recede (-) indicator w.r.t. the RSU (design S1)
        vec[16] = self._compute_heading(float(vel[0]), float(vel[1]), dx, dy)

        # [17..20] Per-subchannel busy ratio. `subchannel_cbr` is the raw
        # occupancy of each channel at this instant, the same list the reward
        # indexes with the chosen channel, so the policy now observes the
        # quantity it is charged against.
        #
        # ABSENT IS NOT ZERO. A caller that supplies no per-channel list gets the
        # MEAN broadcast across the four slots, not zeros. Zero would assert
        # "these channels were idle", which is a claim; the mean asserts "no finer
        # information than [14] was available", which is the truth. The same
        # reasoning is why the offline dataset refuses to default a missing
        # behaviour log-probability or action index.
        # RELATIVE to the mean, not absolute. `cbr_ch / mean(cbr)`.
        #
        # WHY NOT THE ABSOLUTE OCCUPANCY. Because the two quantities answer
        # different questions and therefore need different scales. Feature [14]
        # answers "how busy is the network", and its absolute value is the right
        # answer there -- 0.005 is genuinely what this scenario produces. These
        # four answer "WHICH channel is quieter", and that lives entirely in the
        # differences between them.
        #
        # Those differences are tiny in absolute terms. Occupancy moves in steps
        # of 0.00448, one frame's airtime over one 0.1 s step, so the whole
        # feature takes about ten discrete values below 0.045. Asking a network to
        # separate 0.00448 from 0.00896 inside a [0, 1] input means asking it to
        # learn very large weights for that input alone. Dividing by the mean puts
        # the same information around 1.0 where it is legible.
        #
        # IT ALSO REMOVES A REDUNDANCY. Four absolute occupancies contain their
        # own mean, so [14] would have been recoverable from [17..20] and the five
        # features would have overlapped. Four RATIOS cannot reconstruct the mean,
        # so [14] and these carry strictly different information: absolute level
        # and relative deviation.
        #
        # ALL FOUR ARE 1.0 WHEN NOTHING TRANSMITTED (about 1.7 % of steps). The
        # ratio is undefined there, and 1.0 states "every channel equals the
        # mean", which is true when all four are zero. No validity flag is needed
        # because [14] is then 0 and already says so -- the same structure as the
        # all-zero signal one-hot standing in for "no traffic light".
        #
        # The RANGE is left alone deliberately. Four channels means the ratio can
        # reach 4.0 if one channel carries everything; a random policy was measured
        # between 0.5 and 2.0, and a trained one may spread further. Whether to
        # clip at 4, divide by 4, or leave it is a decision for data from a trained
        # policy. The offline dataset stores the ABSOLUTE occupancies, so that
        # decision can be revisited by re-reading rather than recollecting.
        per_ch = state_dict.get("subchannel_cbr")
        if per_ch is None:
            # No per-channel information at all. Every slot is 1.0, i.e. "equal to
            # the mean", which is the same claim the all-zero case makes and is
            # the weakest one available: it asserts no channel is preferable.
            for k in range(4):
                vec[17 + k] = 1.0
        else:
            values = [float(c) for c in per_ch]
            mean_cbr = float(np.mean(values)) if values else 0.0
            for k in range(4):
                if mean_cbr <= 0.0:
                    vec[17 + k] = 1.0
                else:
                    v_k = values[k] if k < len(values) else mean_cbr
                    vec[17 + k] = float(v_k) / mean_cbr

        return vec


class ActionDecoder:
    """
    Hybrid Action Space Decoder.
    
    Decodes raw model logits or tensor outputs into a concrete uplink grant 3-tuple:
    (Delta in [0.1, 45.0]s, ch in {0, 1, 2, 3}, power in [10.0, 23.0]dBm).

    These bounds are the user-approved design (Conversation.md S2) and are the SINGLE
    SOURCE OF TRUTH for the action space. Rationale for the record:
      * p_max = 23 dBm -- 3GPP TS 36.101/38.101 power-class-3 UE maximum transmit power.
      * delta_min = 0.1 s -- ETSI EN 302 637-2 CAM minimum generation interval
        (T_GenCamMin); generating faster than this is not standards-compliant.
      * delta_max = 45.0 s -- worst-case standstill duration in the actual SUMO
        scenario (generated.net.xml tlLogic: green 42 s + yellow 3 s => 45 s red per
        approach), i.e. the longest interval over which a stopped vehicle's mobility
        state provably need not be refreshed.

    Delta mapping is GEOMETRIC, not linear. The Delta range spans a factor of 450, so a
    linear interpolation of sigmoid(logit) would need u ~= 0.0089 just to emit 0.5 s and
    would destroy all resolution in the short-interval regime. Instead:

        u     = sigmoid(raw_delta)                              in [0, 1]
        delta = delta_min * (delta_max / delta_min) ** u        (inverse: u = log(d/d_min)/log(d_max/d_min))

    which gives uniform *relative* resolution across u. Power stays linear: dBm is
    already a logarithmic unit.

    Downstream code must read delta_min/delta_max/p_min/p_max off the decoder
    instance rather than duplicating the literals.
    """

    def __init__(
        self,
        num_channels: int = 4,
        delta_min: float = DELTA_MIN,
        delta_max: float = 0.0,
        p_min: float = P_MIN,
        p_max: float = P_MAX,
    ) -> None:
        self.num_channels = int(num_channels)
        self.delta_min = float(delta_min)
        # 0.0 means "resolve from the scenario on every read". A snapshot taken
        # here is wrong whenever the decoder outlives the network it was built
        # against: `run_hot_swap_training` constructs the nine models (and their
        # decoders) BEFORE `AoiV2IEnv._init_sumo` writes the network and calls
        # `refresh_scenario_constants()`, so a model built at import time held a
        # stale DELTA_MAX while the environment asserted against the fresh one.
        # `norm_sq_error` already reads its module global per call; this matches.
        self._delta_max_fixed: Optional[float] = (
            float(delta_max) if delta_max and delta_max > 0.0 else None
        )
        self.p_min = float(p_min)
        self.p_max = float(p_max)

    @property
    def delta_max(self) -> float:
        """Upper Delta bound: the pinned value, else the live scenario constant."""
        return self._delta_max_fixed if self._delta_max_fixed is not None else DELTA_MAX

    @delta_max.setter
    def delta_max(self, value: float) -> None:
        self._delta_max_fixed = float(value) if value and float(value) > 0.0 else None

    @property
    def _log_delta_ratio(self) -> float:
        """log(delta_max / delta_min): the geometric span used by the Delta mapping.

        Guarded so a degenerate delta_min == delta_max decoder still works.
        """
        d_max = self.delta_max
        if self.delta_min > 0.0 and d_max > self.delta_min:
            return math.log(d_max / self.delta_min)
        return 0.0

    def delta_from_unit(self, u: float) -> float:
        """Geometric map u in [0, 1] -> Delta in [delta_min, delta_max]."""
        u = min(max(float(u), 0.0), 1.0)
        if self._log_delta_ratio <= 0.0:
            # Degenerate range: fall back to linear interpolation.
            return self.delta_min + u * (self.delta_max - self.delta_min)
        if u <= 0.0:
            return self.delta_min
        if u >= 1.0:
            return self.delta_max
        return self.delta_min * math.exp(u * self._log_delta_ratio)

    def unit_from_delta(self, delta: float) -> float:
        """Inverse geometric map Delta -> u in [0, 1]."""
        d = min(max(float(delta), self.delta_min), self.delta_max)
        if self._log_delta_ratio <= 0.0:
            return (d - self.delta_min) / max(1e-6, self.delta_max - self.delta_min)
        return math.log(d / self.delta_min) / self._log_delta_ratio

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x < -50.0:
            return 0.0
        if x > 50.0:
            return 1.0
        return 1.0 / (1.0 + math.exp(-x))

    @staticmethod
    def _logit(p: float) -> float:
        p_clamped = min(max(p, 1e-6), 1.0 - 1e-6)
        return math.log(p_clamped / (1.0 - p_clamped))

    def decode_action(self, raw_action: Any) -> Tuple[float, int, float]:
        """
        Decodes raw action into (delta_s, channel_idx, power_dbm).
        """
        if isinstance(raw_action, dict):
            raw_delta = raw_action.get("delta", raw_action.get("delta_raw", 0.0))
            raw_ch = raw_action.get("ch", raw_action.get("channel_idx", 0))
            raw_p = raw_action.get("power", raw_action.get("tx_power_dbm", 0.0))
        elif isinstance(raw_action, (list, tuple, np.ndarray, torch.Tensor)):
            if isinstance(raw_action, torch.Tensor):
                raw_action = raw_action.detach().cpu().numpy().flatten()
            raw_list = list(raw_action)
            if len(raw_list) >= 3:
                raw_delta, raw_ch, raw_p = raw_list[0], raw_list[1], raw_list[2]
            elif len(raw_list) == 2:
                raw_delta, raw_ch, raw_p = raw_list[0], 0, raw_list[1]
            elif len(raw_list) == 1:
                raw_delta, raw_ch, raw_p = raw_list[0], 0, 0.0
            else:
                raw_delta, raw_ch, raw_p = 0.0, 0, 0.0
        else:
            raw_delta, raw_ch, raw_p = 0.0, 0, 0.0

        # Continuous delta mapping, GEOMETRIC over [delta_min, delta_max].
        # This used to be a linear interpolation of the sigmoid, which contradicted
        # this class's own docstring and `delta_from_unit`. The two disagree by an
        # order of magnitude in the region the scheduler lives in: at logit 0 the
        # linear form emits 22.55 s where the geometric one emits 2.12 s. Every
        # baseline calls `delta_from_unit` directly, so the linear form never
        # reached a run -- but it was one fallback away from silently halving the
        # resolution of the short-interval regime the paper is about.
        sig_d = self._sigmoid(float(raw_delta))
        delta = self.delta_from_unit(sig_d)

        # Discrete channel mapping {0..num_channels-1}
        ch = int(round(float(raw_ch))) % self.num_channels

        # Continuous power mapping [p_min, p_max]
        sig_p = self._sigmoid(float(raw_p))
        power = self.p_min + sig_p * (self.p_max - self.p_min)

        return (float(delta), int(ch), float(power))

    def encode_action(self, delta: float, ch: int, power: float) -> np.ndarray:
        """Inverse of `decode_action`: (delta, ch, power) back to raw logits.

        Delta inverts through `unit_from_delta` so the pair stays geometric on
        both sides. Power stays linear because dBm is already a log unit.
        """
        norm_d = self.unit_from_delta(delta)
        norm_p = (power - self.p_min) / max(1e-6, self.p_max - self.p_min)
        raw_d = self._logit(norm_d)
        raw_p = self._logit(norm_p)
        return np.array([raw_d, float(ch), raw_p], dtype=np.float32)


#: SUMO signal characters, encoded as small integers so a raw character survives
#: into a numeric dataset column. Measured 2026-09-06 over 352,980 observations,
#: the generated networks emit only these five, and `none` -- meaning
#: `getNextTLS` returned nothing, i.e. no upcoming signal -- accounts for 2.63 %:
#:
#:     r 51.22 %   G 29.21 %   g 13.26 %   y 3.68 %   none 2.63 %
#:
#: `s`, `u`, `o` and `O` do NOT occur here, although SUMO defines them. That was
#: worth measuring rather than assuming: the three-way one-hot at [8..10] leaves
#: three zeros for anything outside {r, y, g}, and the working hypothesis had been
#: that those zeros were unmapped characters needing a mapping rule. They are not.
#: Every one of them is "no traffic light ahead", which is a different fact and
#: needs a different remedy.
#:
#: -1 is reserved for a character this table does not list, so a future network
#: that does emit `s` shows up as -1 in the data instead of being silently folded
#: into an existing class.
TLS_STATE_CODES: Dict[str, int] = {
    "none": 0, "r": 1, "y": 2, "g": 3, "G": 4, "s": 5, "u": 6, "o": 7, "O": 8,
}


def tls_state_code(char: Any) -> int:
    """The integer code for a SUMO signal character. -1 for anything unlisted."""
    return TLS_STATE_CODES.get(str(char), -1)


#: The raw fields stored beside every observation, in this order. Each one is a
#: value that `StateVectorizer` clips, collapses or averages away.
#: EVERY feature that divides by a constant is represented, not only the ones
#: thought likely to change. The selection rule is "does this feature use a
#: normalising constant", not "will that constant move": on 2026-09-06 alone,
#: `N_ACTIVE_MAX_OBS` went from a literal 100 to a scenario-derived 168 and
#: `CBR_REF` from 0.25 to 0.60, and both had been treated as settled. Judgements
#: about what will not change have a poor record in this file.
#:
#: By that rule the constants in play are `E_REF` at [0], `V_MAX_OBS` at
#: [1][2][3], `a_max` at [4], `rsu_range` at [5][6][7] and [12],
#: `PHASE_REMAINING_REF_S` at [11], `N_ACTIVE_MAX_OBS` at [13] and `queue_max` at
#: [15]. Only the signal one-hot [8..10] and the heading cosine [16] use none, so
#: only those two cannot be rebuilt -- and neither has a constant to move.
RAW_OBSERVATION_FIELDS: Tuple[str, ...] = (
    "last_pred_err_m",           # [0] squashed by norm_sq_error against E_REF
    "vx_mps", "vy_mps", "speed_mps",   # [1][2][3] divided by V_MAX_OBS
    "accel_mps2",                # [4] divided by a_max
    "rel_x_m", "rel_y_m", "dist_to_rsu_m",   # [5][6][7] divided by rsu_range
    "time_to_switch_s",          # [11] divided by PHASE_REMAINING_REF_S
    "dist_to_stopline_m",        # [12] divided by rsu_range and clipped
    "dist_to_stopline_measured",  # 1.0 if SUMO reported one, 0.0 if there is none
    "tls_state_code",            # see TLS_STATE_CODES; [8..10] lose the character
    "n_active",                  # [13] divided by N_ACTIVE_MAX_OBS and clipped
    "n_queue",                   # [15] divided by queue_max and clipped
    "cbr_ch0", "cbr_ch1", "cbr_ch2", "cbr_ch3",  # [17..20] clip, [14] averages
    "n_neighbours",              # in-coverage vehicles other than this one
)


def raw_observation_fields(state_dict: Dict[str, Any],
                           rsu_pos: Tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    """The pre-normalisation values, in `RAW_OBSERVATION_FIELDS` order.

    `dist_to_stopline_measured` exists because the distance alone cannot be read.
    `extract_tls_features` reports `inf` when there is no upcoming signal, and
    `StateVectorizer` maps that to the same 1.0 as a stop line exactly
    `rsu_range` away -- the default and a real reading are the same number, which
    is the fourth time that pattern has hidden a fact in this project. The flag
    separates them, so a consumer never has to infer "no signal" from a value.
    """
    tls = state_dict.get("tls_features") or {}
    d = tls.get("dist_to_stopline", None)
    measured = d is not None and np.isfinite(float(d))
    per_ch = state_dict.get("subchannel_cbr") or []
    mean_cbr = float(state_dict.get("cbr", 0.0))
    pos = state_dict.get("pos", (0.0, 0.0))
    vel = state_dict.get("vel", (0.0, 0.0))
    dx = float(pos[0]) - float(rsu_pos[0])
    dy = float(pos[1]) - float(rsu_pos[1])
    tts = tls.get("time_to_switch", None)
    q = state_dict.get("n_queue", None)
    if q is None:
        q = tls.get("n_queue", None)
    out = [
        float(state_dict.get("last_pred_err", 0.0)),
        float(vel[0]), float(vel[1]),
        float(state_dict.get("speed", math.hypot(vel[0], vel[1]))),
        float(state_dict.get("accel", 0.0)),
        dx, dy,
        float(state_dict.get("dist_to_rsu", math.hypot(dx, dy))),
        # NaN, not a substitute number: `time_to_switch` is absent exactly when
        # there is no signal, and any finite stand-in here would be
        # indistinguishable from a real reading of that value.
        float(tts) if tts is not None and np.isfinite(float(tts)) else float("nan"),
        float(d) if measured else float("nan"),
        1.0 if measured else 0.0,
        float(tls_state_code(tls.get("state", "none"))),
        float(state_dict.get("n_active", 0)),
        float(q) if q is not None else float("nan"),
    ]
    out += [float(per_ch[k]) if k < len(per_ch) else mean_cbr for k in range(4)]
    # The neighbourhood SIZE, not its contents. Storing the neighbour states
    # themselves was considered and rejected: the offline dataset is read only by
    # HOORL, HOORL does not consume `neighbour_state`, and the three baselines
    # that do have no offline stage -- so the rows would be 168 MB to 1.7 GB that
    # nothing could ever read. The count is what a decision about `MAX_NEIGHBOURS`
    # actually needs, and it costs four bytes.
    n_nb = state_dict.get("n_active", None)
    out.append(float(max(0.0, float(n_nb) - 1.0)) if n_nb is not None else float("nan"))
    return np.asarray(out, dtype=np.float32)


#: Which observation feature each raw field rebuilds, and under which constant.
#: The names on the right are keys of `observation_constants()`; `None` marks a
#: divisor that is a `StateVectorizer` attribute rather than a scenario constant.
RENORMALISABLE_FEATURES: Tuple[Tuple[int, str], ...] = (
    (0, "E_REF"), (1, "V_MAX_OBS"), (2, "V_MAX_OBS"), (3, "V_MAX_OBS"),
    (4, "A_MAX"), (5, "RSU_RANGE"), (6, "RSU_RANGE"), (7, "RSU_RANGE"),
    (11, "PHASE_REMAINING_REF_S"), (12, "DIST_TO_STOPLINE_REF_M"),
    (13, "N_ACTIVE_MAX_OBS"), (15, "QUEUE_MAX"),
    (17, None), (18, None), (19, None), (20, None),
)


#: WHAT EACH CONSTANT DOES BESIDES NORMALISE AN OBSERVATION.
#:
#: The reason this table exists is a near miss. The argument "this is an
#: observation bound, so moving it only rescales a feature" is sound exactly when
#: the constant normalises an observation AND NOTHING ELSE. `E_REF` looks like
#: one of those and is not: `norm_sq_error` is called by the REWARD as well as by
#: feature [0], so changing it would have changed what the agent optimises while
#: appearing to change only an input scale. It was caught by asking what else
#: reads the constant, and the answer is worth writing down once rather than
#: rediscovering per constant.
#:
#: Roles:
#:   "observation"  normalises a feature and does nothing else. Safe to move on
#:                  the evidence of a clipping measurement alone.
#:   "reward"       also enters the reward. Moving it changes the objective.
#:   "action"       defines the action space. Moving it re-interprets every
#:                  stored action and invalidates a collected dataset's actions.
#:   "environment"  decides something about the simulation itself, such as who is
#:                  in coverage, so moving it changes the episode and not just
#:                  its description.
CONSTANT_ROLES: Dict[str, Tuple[str, ...]] = {
    "N_ACTIVE_MAX_OBS": ("observation",),
    "QUEUE_MAX": ("observation",),
    "DIST_TO_STOPLINE_REF_M": ("observation",),
    "PHASE_REMAINING_REF_S": ("observation",),
    "A_MAX": ("observation",),
    "V_MAX_OBS": ("observation",),
    # `norm_sq_error` is the reward's error term as well as feature [0].
    "E_REF": ("observation", "reward"),
    # The decoder's Delta range: a stored unit coordinate means a different
    # number of seconds if this moves.
    "DELTA_MAX": ("observation", "action"),
    "DELTA_MIN": ("action",),
    # Feature [7] divides by it, and `AoiV2IEnv` decides coverage membership with
    # it -- which vehicles exist in an observation at all.
    "RSU_RANGE": ("observation", "environment"),
}


class UnclassifiedConstant(KeyError):
    """A constant reached this module without a role in `CONSTANT_ROLES`."""


def constants_safe_to_rescale(known: Optional[Iterable[str]] = None) -> Tuple[str, ...]:
    """Constants whose ONLY job is normalising an observation.

    A clipping measurement is sufficient grounds to move one of these and is not
    sufficient for any other: the others carry a second meaning that the
    measurement says nothing about.

    AN UNCLASSIFIED CONSTANT IS REFUSED, NOT ASSUMED SAFE. The absent case has to
    be decided rather than left to fall out of a lookup, and the two possible
    defaults are not symmetric. Defaulting to safe means a constant added next
    month is rescaled by a path that never considered what else it does, and the
    result is a silently wrong dataset. Defaulting to refuse means somebody has
    to spend a line classifying it. `observation_constants` already takes this
    shape with `CONSTANT_ORIGIN`, and the judgement being protected is one this
    project has already got wrong: "it is a normalisation bound, so moving it
    only changes the scale" is false for `RSU_RANGE`, which decides which
    vehicles are in an observation at all, and for `E_REF`, which is also the
    reward's error term.

    `known` is the set that must be classified, and defaults to the constants a
    run is actually using.
    """
    if known is None:
        known = set(observation_constants_live())
    names = set(known) | {n for _j, n in RENORMALISABLE_FEATURES if n}
    unclassified = sorted(names - set(CONSTANT_ROLES))
    if unclassified:
        raise UnclassifiedConstant(
            f"{unclassified} have no entry in CONSTANT_ROLES. Add one saying what "
            "each affects -- observation, reward, action, environment -- before "
            "anything rescales them. Refusing rather than assuming they only "
            "scale an observation, which is the assumption that is false for "
            "RSU_RANGE and E_REF.")
    return tuple(sorted(k for k, roles in CONSTANT_ROLES.items()
                        if tuple(roles) == ("observation",)))


def observation_constants_live() -> Dict[str, float]:
    """The nine normalising constants as this process currently has them.

    Defined here rather than imported from `src.hoorl_offline` because that
    module imports this one; the offline module's `observation_constants()` adds
    the scenario-presence guard on top of these values and remains the entry
    point for anything that WRITES them into a file.
    """
    vec = StateVectorizer()
    return {
        "N_ACTIVE_MAX_OBS": float(vec.n_active_max),
        "V_MAX_OBS": float(vec.v_max),
        "E_REF": float(E_REF),
        "DELTA_MAX": float(DELTA_MAX),
        "DELTA_MIN": float(DELTA_MIN),
        "RSU_RANGE": float(vec.rsu_range),
        "A_MAX": float(vec.a_max),
        "QUEUE_MAX": float(vec.queue_max),
        "PHASE_REMAINING_REF_S": float(PHASE_REMAINING_REF_S),
        "DIST_TO_STOPLINE_REF_M": float(DIST_TO_STOPLINE_REF_M),
    }


def renormalise_states(stored_states: np.ndarray,
                       state_raw: np.ndarray,
                       target_constants: Dict[str, float]) -> np.ndarray:
    """Rebuild the constant-normalised features from their raw values.

    ---------------------------------------------------------------------------
    WHAT THIS IS FOR
    ---------------------------------------------------------------------------
    The entire reason an offline dataset stores raw columns is that a
    normalisation bound can then be moved without recollecting: apply the new
    bound to the raw value on READ. This is the code that applies it. Without it
    the raw columns are storage with no consumer, which is the shape a defect in
    this project has taken more than once -- a module that is complete and that
    nothing calls.

    ---------------------------------------------------------------------------
    WHY IT TAKES THE STORED VECTOR AS WELL AS THE RAW ONE
    ---------------------------------------------------------------------------
    Because a state cannot be rebuilt from raw alone, and that is correct rather
    than a gap. Five of the twenty-one features use no constant: [8], [9] and
    [10] are the signal one-hot, [14] is a clip with no divisor, and [16] is a
    cosine. Nothing about them changes when a constant moves, so the right value
    for them is the one already stored. Storing raw copies of them would add
    columns that could only ever equal what is beside them.

    So this copies the stored vector and overwrites only the columns listed in
    `RENORMALISABLE_FEATURES`.

    ---------------------------------------------------------------------------
    THE DUPLICATION, AND WHAT KEEPS IT HONEST
    ---------------------------------------------------------------------------
    The formulas below MUST match `vectorize_from_dict`, and nothing in the type
    system makes them. What keeps them together is that renormalising to the
    constants a dataset was COLLECTED under has to reproduce the stored vector
    exactly -- `verify_renormalisation` does that, the offline dataset tests run
    it on real collected data, and a divergence between the two implementations
    shows up there as a numerical mismatch rather than as a silently different
    training input.
    """
    if stored_states.shape[0] != state_raw.shape[0]:
        raise ValueError(
            f"{stored_states.shape[0]} states against {state_raw.shape[0]} raw "
            "rows; they must be the same transitions in the same order."
        )
    if state_raw.shape[1] != len(RAW_OBSERVATION_FIELDS):
        raise ValueError(
            f"state_raw has {state_raw.shape[1]} columns, expected "
            f"{len(RAW_OBSERVATION_FIELDS)} ({RAW_OBSERVATION_FIELDS})."
        )
    idx = {name: i for i, name in enumerate(RAW_OBSERVATION_FIELDS)}
    raw = np.asarray(state_raw, dtype=np.float64)
    out = np.array(stored_states, dtype=np.float64, copy=True)

    def _c(key: str) -> np.ndarray:
        """A constant as a column, so per-row and scalar callers share one path."""
        v = target_constants[key]
        return np.asarray(v, dtype=np.float64).reshape(-1) if np.ndim(v) else             np.full(raw.shape[0], float(v))

    e_ref = _c("E_REF")
    v_max = _c("V_MAX_OBS")
    rsu = _c("RSU_RANGE")
    a_max = _c("A_MAX")
    q_max = _c("QUEUE_MAX")
    n_act = _c("N_ACTIVE_MAX_OBS")
    phase = _c("PHASE_REMAINING_REF_S")
    stop_ref = _c("DIST_TO_STOPLINE_REF_M")

    err = raw[:, idx["last_pred_err_m"]]
    out[:, 0] = err ** 2 / (err ** 2 + e_ref ** 2)
    out[:, 1] = np.clip(raw[:, idx["vx_mps"]] / v_max, -1.0, 1.0)
    out[:, 2] = np.clip(raw[:, idx["vy_mps"]] / v_max, -1.0, 1.0)
    out[:, 3] = np.clip(raw[:, idx["speed_mps"]] / v_max, 0.0, 1.0)
    out[:, 4] = np.clip(raw[:, idx["accel_mps2"]] / a_max, -1.0, 1.0)
    out[:, 5] = np.clip(raw[:, idx["rel_x_m"]] / rsu, -1.0, 1.0)
    out[:, 6] = np.clip(raw[:, idx["rel_y_m"]] / rsu, -1.0, 1.0)
    out[:, 7] = np.clip(raw[:, idx["dist_to_rsu_m"]] / rsu, 0.0, 1.0)

    # [11] and [12] are zero when there is no signal ahead, and the STORED
    # one-hot is what says so -- the raw `tls_state_code` says the same thing but
    # reading it here would make this function disagree with the vectoriser for a
    # row whose one-hot was built from a character the code table did not list.
    has_signal = out[:, 8:11].sum(axis=1) > 0
    tts = np.nan_to_num(raw[:, idx["time_to_switch_s"]])
    dts = np.nan_to_num(raw[:, idx["dist_to_stopline_m"]], nan=0.0)
    measured = raw[:, idx["dist_to_stopline_measured"]] > 0
    out[:, 11] = np.where(has_signal, np.clip(tts / phase, 0.0, 1.0), 0.0)
    out[:, 12] = np.where(
        has_signal,
        np.clip(np.where(measured, dts, stop_ref) / stop_ref, 0.0, 1.0), 0.0)
    out[:, 13] = np.clip(raw[:, idx["n_active"]] / n_act, 0.0, 1.0)
    out[:, 15] = np.clip(np.nan_to_num(raw[:, idx["n_queue"]]) / q_max, 0.0, 1.0)

    # [17..20] are RELATIVE to the mean of the four, so no external constant is
    # involved; they are rebuilt because the raw columns hold ABSOLUTE occupancy
    # and the relative definition itself is a thing that may change.
    absolute = raw[:, [idx[f"cbr_ch{k}"] for k in range(4)]]
    mean_ch = absolute.mean(axis=1, keepdims=True)
    out[:, 17:21] = np.where(mean_ch > 0.0,
                             absolute / np.where(mean_ch > 0.0, mean_ch, 1.0), 1.0)

    # ----------------------------------------------------------------------
    # A ROW WITH NO RAW OBSERVATION AT ALL KEEPS WHAT WAS STORED.
    # ----------------------------------------------------------------------
    # A terminal transition has no successor to observe, so its `next_state_raw`
    # is NaN in every one of the nineteen fields and its stored `next_state` is
    # the zero vector -- the usual convention, and harmless because the Bellman
    # target multiplies it by (1 - done). Rebuilding such a row from raw produces
    # NaN in every renormalised feature instead, and NaN in a training batch is
    # not a bad value but an unrecoverable one: it reaches the loss, the loss
    # reaches the weights, and every subsequent forward pass returns NaN.
    #
    # Measured on the 128,223-transition collection: 3,639 rows, exactly the rows
    # with `done` set and `close_reason == 1`, no others. Before this guard those
    # rows entered HOORL's offline stage as NaN, the IQL losses were NaN from the
    # first update, and the rollout that followed died on `probability tensor
    # contains either inf, nan`.
    #
    # This is deliberately narrow. Only an ENTIRELY absent observation is
    # substituted. A row with some fields missing is the no-signal case handled
    # above, and a row with an unexplained NaN in one field is a fault that must
    # not be papered over -- the assertion below is what says so.
    absent = np.isnan(raw).all(axis=1)
    if absent.any():
        out[absent] = np.asarray(stored_states, dtype=np.float64)[absent]

    introduced = ~np.isfinite(out) & np.isfinite(
        np.asarray(stored_states, dtype=np.float64))
    if introduced.any():
        rows = np.where(introduced.any(axis=1))[0]
        cols = np.where(introduced.any(axis=0))[0]
        raise ValueError(
            f"renormalising turned {int(introduced.sum())} finite stored values "
            f"into non-finite ones, in {rows.size} row(s) and feature(s) "
            f"{cols.tolist()} (first rows {rows[:5].tolist()}). The raw columns "
            "for those rows do not describe the observation beside them. Refusing "
            "rather than returning a batch that would make every weight NaN.")
    return out.astype(np.float32)


def verify_renormalisation(stored_states: np.ndarray, state_raw: np.ndarray,
                           source_constants: Dict[str, float],
                           atol: float = 1e-5) -> Dict[str, Any]:
    """Rebuild with the constants the data was COLLECTED under and compare.

    The result must equal the stored vector. It is the only check that the raw
    columns describe the same observation the normalised ones do, and therefore
    the only thing standing between "the raw columns are usable" and "the raw
    columns are numbers of unknown provenance".

    Returns the per-feature worst error rather than a bare pass/fail, because a
    single feature failing while the rest agree is a specific and diagnosable
    fault -- a changed formula in one branch -- while everything failing points
    at the wrong constants having been passed.
    """
    rebuilt = renormalise_states(stored_states, state_raw, source_constants)
    per_feature = {
        int(j): float(np.abs(rebuilt[:, j].astype(np.float64)
                             - np.asarray(stored_states)[:, j].astype(np.float64)).max())
        for j, _ in RENORMALISABLE_FEATURES
    }
    worst = max(per_feature.values()) if per_feature else 0.0
    return {
        "matches": bool(worst <= atol),
        "worst_abs_error": worst,
        "worst_feature": int(max(per_feature, key=per_feature.get)) if per_feature else -1,
        "per_feature_abs_error": per_feature,
        "atol": float(atol),
        "n_rows": int(np.asarray(stored_states).shape[0]),
    }


class NeighbourhoodView:
    """Fixed-width view of the other in-range agents at ONE decision instant.

    WHY THIS EXISTS. Three of the nine baselines are multi-agent methods whose
    published contribution is a critic that sees more than the acting agent's own
    observation: MADDPG-MT's global critic (Parvini et al., IEEE TVT 72(8), 2023),
    I-HAMAPPO's joint critic and RES-MAPDDPG's centralised critic. All three
    already accepted a neighbourhood tensor; nothing in the pipeline produced one,
    so all three trained with the zero context and degenerated into their
    single-agent counterparts. This class is the producer.

    WHAT IS OURS AND WHAT IS THE PAPERS'. The pooling, masking and truncation are
    OURS. All three papers assume a FIXED agent population -- platoons, or a fixed
    vehicle set -- so a fixed-width concatenation is well defined for them and the
    question never arises. Our population changes every step as vehicles cross the
    300 m RSU boundary, so a fixed-width input needs a padding convention and a
    validity mask, and a cap needs a rule for WHICH agents to keep. Those three
    decisions are additions and are recorded here because they belong in the
    paper's statement of how far each baseline was ported.

    NO INFORMATION IS INVENTED AND NONE IS BORROWED FROM THE FUTURE. The rows are
    the observation vectors the environment emitted for THIS step and nothing
    else, so a neighbour row is identical to what that neighbour's own transition
    stored, and a view built from the step-k observation dict cannot contain a
    quantity from step k+1. The transition for a closed interval pairs the view
    taken when the interval OPENED with the view taken when it CLOSED, matching
    `state` and `next_state` exactly.

    It is built once per environment step and queried per vehicle. Building it per
    vehicle instead would put a Python loop over all in-range vehicles inside a
    loop over all in-range vehicles, which is the exact shape of the O(V^2)
    regression that cost this pipeline a 7x slowdown once already (CODE_GUIDE A-11).
    """

    __slots__ = ("vids", "max_neighbours", "state_dim", "_index", "_matrix", "_pos")

    def __init__(
        self,
        obs: Dict[str, Any],
        max_neighbours: int = MAX_NEIGHBOURS,
        state_dim: int = STATE_DIM,
    ) -> None:
        self.max_neighbours = max(1, int(max_neighbours))
        self.state_dim = int(state_dim)
        # Sorted, so a distance tie resolves identically in every process and the
        # buffer's contents do not depend on dictionary insertion order.
        self.vids: List[str] = sorted(obs)
        self._index: Dict[str, int] = {vid: i for i, vid in enumerate(self.vids)}
        if self.vids:
            self._matrix = np.stack(
                [np.asarray(obs[v], dtype=np.float32).reshape(-1) for v in self.vids]
            )
            self._pos = self._matrix[:, (FEATURE_REL_X, FEATURE_REL_Y)]
        else:
            self._matrix = np.zeros((0, self.state_dim), dtype=np.float32)
            self._pos = np.zeros((0, 2), dtype=np.float32)

    def __len__(self) -> int:
        return len(self.vids)

    def view(self, ego_vid: str) -> Tuple[np.ndarray, np.ndarray]:
        """(max_neighbours, state_dim) padded rows and a (max_neighbours,) 0/1 mask.

        The rows are the other agents CLOSEST TO THE EGO VEHICLE, nearest first,
        padded with zeros; the mask is 1 on a real row and 0 on padding, so a
        consumer that pools under the mask cannot read a padding artefact as an
        agent. A vehicle that is alone in range, or that is not in `obs` at all,
        gets an all-zero mask, which every one of the three consumers already
        treats as "no neighbourhood".

        Nearest-first is a modelling choice and is ours. The cap bites at the busy
        end of the density grid, so *which* agents are kept has to be decided;
        the nearest are the ones whose transmissions contend for the same airtime
        and whose positions the ego vehicle's own error term is most coupled to.
        Distance is computed between the RSU-relative positions the observation
        already carries, so no quantity is introduced that the critic could not
        have derived from its own inputs.
        """
        rows = np.zeros((self.max_neighbours, self.state_dim), dtype=np.float32)
        mask = np.zeros((self.max_neighbours,), dtype=np.float32)
        i = self._index.get(ego_vid)
        if i is None or len(self.vids) <= 1:
            return rows, mask
        d2 = np.sum((self._pos - self._pos[i]) ** 2, axis=1)
        d2[i] = np.inf  # a vehicle is not its own neighbour
        n_take = min(self.max_neighbours, len(self.vids) - 1)
        order = np.argsort(d2, kind="stable")[:n_take]
        rows[:n_take] = self._matrix[order]
        mask[:n_take] = 1.0
        return rows, mask


def _as_f32(arr: Optional[Any]) -> Optional[np.ndarray]:
    """Contiguous float32 copy, or None. Used for the optional batch columns."""
    if arr is None:
        return None
    return np.ascontiguousarray(np.asarray(arr, dtype=np.float32))


class RetrospectiveReplayBuffer:
    """
    SMDP Retrospective Replay Buffer with variable-interval discount gamma^Delta support.
    """

    def __init__(self, capacity: int = 10000, gamma: float = 0.99) -> None:
        self.capacity = int(capacity)
        self.gamma = float(gamma)
        self.buffer: List[Dict[str, Any]] = []
        self.position = 0
        #: Raw priority per slot, read ONLY by `sample_prioritized`. Kept as a
        #: dense array rather than inside the item dicts so that the uniform
        #: path does not touch it at all.
        self._priorities = np.zeros(self.capacity, dtype=np.float64)
        self._max_priority = 1.0

    def push(
        self,
        state: Union[np.ndarray, torch.Tensor, List[float]],
        action: Union[np.ndarray, torch.Tensor, List[float], Tuple[float, ...]],
        reward: float,
        next_state: Union[np.ndarray, torch.Tensor, List[float]],
        done: bool,
        delta_t: float,
        action_idx: Optional[int] = None,
        behaviour_log_prob: Optional[float] = None,
        reward_terms: Optional[Union[np.ndarray, List[float], Tuple[float, ...]]] = None,
        neighbour_state: Optional[np.ndarray] = None,
        neighbour_mask: Optional[np.ndarray] = None,
        next_neighbour_state: Optional[np.ndarray] = None,
        next_neighbour_mask: Optional[np.ndarray] = None,
    ) -> None:
        """
        Push a transition tuple (s, a, r, s', done, delta_t) into buffer.

        action_idx (optional): the combined *discrete* action index that a
        discrete-action agent (e.g. DuelingQAoI, whose grid is
        interval_idx * num_channels + channel_idx) actually selected. It is
        stored verbatim so that credit assignment in update() targets the true
        action instead of a lossy reconstruction from the decoded continuous
        action. Agents with purely continuous / factorized action heads simply
        leave it as None; sample() then omits the "action_idx" key entirely,
        so batch contents are unchanged for every other baseline.

        behaviour_log_prob (optional): log pi_behaviour(a | s) UNDER THE POLICY
        THAT ACTUALLY EMITTED `action`, i.e. the Act model as of the last
        hot-swap, evaluated at selection time. It exists for the same reason
        `action_idx` does -- the value is known exactly at the moment of the
        decision and is unrecoverable afterwards -- and the two travel the same
        route from `select_action` through the streamer to here.

        Why it matters: this buffer is off-policy in shape (uniformly sampled
        stale transitions), so the two PPO-family baselines need the true
        importance weight pi_new / pi_behaviour. Without it they were reduced to
        recomputing the denominator from the CURRENT policy, which makes the
        ratio identically 1 on the first inner epoch and therefore disables
        clipping altogether -- a clip-free policy-gradient step on stale data,
        which is how both models diverged (results/hpo/onpolicy_fix_check.csv).
        Off-policy baselines ignore the key; agents that never report a
        log-probability leave it None and `sample()` omits the key entirely.

        reward_terms (optional): the interval reward SPLIT INTO ITS SIGNED,
        WEIGHTED COMPONENTS, in the environment's own order
        (-w1*e^2, -w2*P_tx, -w3*C_freq, -w4*I_redundant). They sum to `reward`
        exactly and the environment asserts that before handing them over
        (`AoiV2IEnv._finalize_interval`). MADDPG-MT's task decomposition -- one
        value head per term, which is the headline contribution of Parvini et al.
        -- is only active when this column is present; without it the four heads
        are trained on shares of the same scalar, become copies of one another,
        and the paper's contribution is inert while the loss log says nothing.

        neighbour_state / neighbour_mask (optional): the padded observations of
        the other in-range agents at the instant this interval OPENED, with a 0/1
        validity mask, as produced by `NeighbourhoodView`. `next_neighbour_*` is
        the same view at the instant it CLOSED, so the pair lines up with
        `state` / `next_state`. The joint critics of MADDPG-MT, I-HAMAPPO and
        RES-MAPDDPG read them; without them all three see a zero context and
        collapse to their single-agent equivalents. Every other baseline ignores
        the keys, and `sample()` omits them unless every transition in the batch
        carries one, so no batch can mix a real neighbourhood with a fabricated
        empty one.
        """
        s_arr = np.array(state, dtype=np.float32) if not isinstance(state, np.ndarray) else state.astype(np.float32)
        if isinstance(action, torch.Tensor):
            a_arr = action.detach().cpu().numpy().astype(np.float32)
        elif isinstance(action, (list, tuple)):
            a_arr = np.array(action, dtype=np.float32)
        else:
            a_arr = np.array(action, dtype=np.float32)

        ns_arr = np.array(next_state, dtype=np.float32) if not isinstance(next_state, np.ndarray) else next_state.astype(np.float32)

        item = {
            "state": s_arr,
            "action": a_arr,
            "reward": float(reward),
            "next_state": ns_arr,
            "done": float(done),
            "delta_t": float(delta_t),
            "action_idx": None if action_idx is None else int(action_idx),
            "behaviour_log_prob": (
                None
                if behaviour_log_prob is None or not np.isfinite(float(behaviour_log_prob))
                else float(behaviour_log_prob)
            ),
            "reward_terms": (
                None if reward_terms is None
                else np.asarray(reward_terms, dtype=np.float32).reshape(-1)
            ),
            "neighbour_state": _as_f32(neighbour_state),
            "neighbour_mask": _as_f32(neighbour_mask),
            "next_neighbour_state": _as_f32(next_neighbour_state),
            "next_neighbour_mask": _as_f32(next_neighbour_mask),
        }

        if len(self.buffer) < self.capacity:
            self.buffer.append(item)
        else:
            self.buffer[self.position] = item
        # A transition nothing has evaluated yet enters at the highest priority
        # seen so far, so the prioritized sampler is guaranteed to show it at
        # least once (Schaul et al.'s convention). Nothing reads this unless a
        # model asks for `sample_prioritized`, so the uniform path is unaffected.
        self._priorities[self.position] = self._max_priority
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> Dict[str, torch.Tensor]:
        """
        Sample a random batch of transitions as PyTorch Tensors.
        Raises ValueError if buffer is empty.
        """
        if len(self.buffer) == 0:
            raise ValueError("Cannot sample from an empty buffer.")

        batch_size = min(batch_size, len(self.buffer))
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        return self._batch_from_indices(indices)

    def _batch_from_indices(self, indices: np.ndarray) -> Dict[str, torch.Tensor]:
        """Assemble the batch dict for already-chosen buffer slots.

        Split out of `sample()` so the uniform and the prioritized draw build
        IDENTICAL batches and differ only in how the slots were chosen. Two
        copies of this assembly would be two places for an optional key to be
        forgotten.
        """
        batch = [self.buffer[i] for i in indices]

        states = np.array([b["state"] for b in batch], dtype=np.float32)
        actions = np.array([b["action"] for b in batch], dtype=np.float32)
        rewards = np.array([[b["reward"]] for b in batch], dtype=np.float32)
        next_states = np.array([b["next_state"] for b in batch], dtype=np.float32)
        dones = np.array([[b["done"]] for b in batch], dtype=np.float32)
        delta_ts = np.array([[b["delta_t"]] for b in batch], dtype=np.float32)
        discounts = np.power(self.gamma, delta_ts).astype(np.float32)

        out = {
            "state": torch.from_numpy(states),
            "action": torch.from_numpy(actions),
            "reward": torch.from_numpy(rewards),
            "next_state": torch.from_numpy(next_states),
            "done": torch.from_numpy(dones),
            "delta_t": torch.from_numpy(delta_ts),
            "discount": torch.from_numpy(discounts),
        }

        # Optional discrete action indices. Emitted only when EVERY sampled
        # transition carries one, so batches for continuous-action baselines
        # keep exactly the legacy key set / tensor shapes.
        idx_list = [b.get("action_idx") for b in batch]
        if len(idx_list) > 0 and all(i is not None for i in idx_list):
            out["action_idx"] = torch.from_numpy(np.array(idx_list, dtype=np.int64))

        # Optional behaviour log-probabilities, same all-or-nothing rule: a batch
        # in which only some transitions know their behaviour policy cannot form a
        # consistent importance ratio, so the key is withheld and the consumer
        # takes its (loudly reported) fallback for the whole batch.
        logp_list = [b.get("behaviour_log_prob") for b in batch]
        if len(logp_list) > 0 and all(p is not None for p in logp_list):
            out["behaviour_log_prob"] = torch.from_numpy(
                np.array([[p] for p in logp_list], dtype=np.float32)
            )

        # Optional multi-task reward decomposition and neighbourhood context.
        # Same all-or-nothing rule as the two keys above, and for the same reason:
        # a batch in which only some rows know their neighbours would have the
        # others silently padded with an empty neighbourhood, which is not
        # "unknown" but a positive claim that the vehicle was alone in range.
        self._emit_optional_stack(out, batch, "reward_terms")
        self._emit_optional_stack(out, batch, "neighbour_state")
        self._emit_optional_stack(out, batch, "neighbour_mask")
        self._emit_optional_stack(out, batch, "next_neighbour_state")
        self._emit_optional_stack(out, batch, "next_neighbour_mask")

        return out

    @staticmethod
    def _emit_optional_stack(
        out: Dict[str, torch.Tensor], batch: List[Dict[str, Any]], key: str
    ) -> None:
        """Stack `key` across the batch, but only when every row carries it."""
        values = [b.get(key) for b in batch]
        if not values or any(v is None for v in values):
            return
        out[key] = torch.from_numpy(np.stack(values).astype(np.float32))

    # ------------------------------------------------------------------
    # Prioritized sampling (Schaul et al. 2016), used by SPAM-D3QN only
    # ------------------------------------------------------------------
    def sample_prioritized(
        self, batch_size: int, alpha: float = 0.6, beta: float = 0.4
    ) -> Dict[str, torch.Tensor]:
        """Draw in proportion to priority^alpha and return the matching IS weights.

        WHY A SECOND ENTRY POINT RATHER THAN A FLAG. The buffer is owned by the
        pipeline and shared by all nine baselines, and the comparison is only
        meaningful while the other eight see exactly the replay distribution they
        have always seen. `sample()` above is untouched -- same uniform draw, same
        `replace=False`, same key set, same RNG calls -- and a model gets this
        path only by overriding `BaseRLModel.sample_batch`, which exactly one
        model does. A flag on the buffer would have put the two behaviours on one
        code path where a default could drift.

        The returned batch is the same dict `sample()` builds plus two keys:
        `weights`, the importance-sampling correction (N * P(i))^-beta normalised
        by its maximum, which is what makes the non-uniform draw unbiased; and
        `indices`, the buffer slots drawn, which `update_priorities` needs to
        write the new TD errors back to.

        Sampling is WITH replacement, as in Schaul et al.: the point is to revisit
        informative transitions, and the duplicate rate for a batch of 32 against
        a buffer of thousands is negligible in any case.
        """
        if len(self.buffer) == 0:
            raise ValueError("Cannot sample from an empty buffer.")
        n = len(self.buffer)
        batch_size = min(int(batch_size), n)
        scaled = np.power(np.maximum(self._priorities[:n], 1e-12), float(alpha))
        total = scaled.sum()
        if not np.isfinite(total) or total <= 0.0:
            # Degenerate priorities are not a reason to stop training; fall back
            # to the uniform draw and say so rather than emitting NaN weights.
            probs = np.full(n, 1.0 / n)
        else:
            probs = scaled / total
        indices = np.random.choice(n, batch_size, replace=True, p=probs)
        weights = np.power(np.maximum(n * probs[indices], 1e-12), -float(beta))
        weights = weights / max(float(weights.max()), 1e-12)

        out = self._batch_from_indices(indices)
        out["weights"] = torch.from_numpy(weights.astype(np.float32))
        out["indices"] = torch.from_numpy(indices.astype(np.int64))
        return out

    def update_priorities(
        self,
        indices: Union[np.ndarray, List[int]],
        priorities: Union[np.ndarray, List[float]],
    ) -> None:
        """Write freshly measured RAW priorities (|TD| + eps) onto those slots.

        RAW, not raised to alpha: the exponent is applied by `sample_prioritized`,
        so it has exactly one application point and cannot be squared by a caller
        that also applies it.

        Out-of-range indices are dropped rather than raising. The ring can wrap
        between a draw and a write-back in principle; in the training loop it
        cannot, because the same thread drains the streamer, samples and updates,
        but a caller that does something else should not crash the run over it.
        """
        idx = np.asarray(indices, dtype=np.int64).reshape(-1)
        pri = np.asarray(priorities, dtype=np.float64).reshape(-1)
        if idx.size != pri.size:
            raise ValueError(
                f"update_priorities: {idx.size} indices against {pri.size} priorities"
            )
        keep = (idx >= 0) & (idx < len(self.buffer)) & np.isfinite(pri)
        idx, pri = idx[keep], np.maximum(pri[keep], 1e-12)
        if idx.size == 0:
            return
        self._priorities[idx] = pri
        self._max_priority = max(self._max_priority, float(pri.max()))

    def is_ready(self, batch_size: int) -> bool:
        return len(self.buffer) >= batch_size

    def clear(self) -> None:
        self.buffer.clear()
        self.position = 0
        self._priorities[:] = 0.0
        self._max_priority = 1.0

    def __len__(self) -> int:
        return len(self.buffer)
