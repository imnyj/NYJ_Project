#!/usr/bin/env python3
"""Gate that must pass before the nine-model HPO re-search is allowed to start.

The run costs about nine hours on four GPUs. Every check below exists because
something in that window has already been lost once, and each failure was only
visible after the fact -- in a CSV of penalty scores, or in a directory that had
been quietly overwritten. The point of this script is to move those discoveries
to the front, where they cost a second instead of a night.

What is checked, and why:

  1. N_ACTIVE_MAX_OBS == 168.0. The contention feature normalised against 100.0
     saturated at exactly 1.0 for densities 25, 30 and 35, so three of the seven
     training densities showed the model an identical congestion signal. Any HPO
     started against the old ceiling tunes for observations the main training run
     will never see.

  2. The composite objective reads `packet_loss_rate`. It used to read a key that
     the rollout filled with a constant, which made that whole term a fixed
     offset and left the search ranking models on three terms instead of four.

  3. The discount search range no longer carries its undecided upper bound. The
     placeholder 0.999 has an effective horizon of 1000 decisions against 50 to
     54 s of measured RSU dwell, and the bound is being settled by a separate
     experiment. The check also requires all nine models to search the same
     range, because the other way this week went wrong was a change reaching two
     of three code paths.

  4. The groups between them schedule each of the nine baselines exactly once.
     The lists are hand-maintained strings that get rearranged whenever the cost
     balance is revisited, and a model dropped in that edit is invisible until
     the merge refuses, twelve hours later.

  5. Every scenario on disk carries flows long enough to outlast warm-up plus the
     measured window. On 2026-09-05 the shared `coder/src/sumo/` held flows ending
     at 131 s against the 530 s a rollout needs, so the road would have begun
     draining while the measurement ran. Both the signature and the rou.xml are
     read, because they were observed disagreeing (51 s against 138 s) and either
     one alone looks consistent.

  6. The scenario directories sit OUTSIDE the git work tree. `.gitignore` is no
     defence: `git clean -fdx` deletes ignored files by design, and even without
     -x a plain `git clean -nd Workspace/paper4` lists 175 entries on this tree.
     Containment is the test, because `git check-ignore` cannot answer it.

  7. Each group gets its OWN SUMO directory, PAPER4_SUMO_DIR actually redirects
     the scenario path, and the generation lock creates its parent directory. On
     2026-09-04 the g1 group's scenario directory vanished mid-run; the lock
     opened its file with O_CREAT into a directory that no longer existed, and
     the 62 remaining rollouts died on FileNotFoundError. SAC lost all 45 of its
     rollouts, I-HAMAPPO lost 15 of 45.

  8. The four GPUs are free. The box is shared. Starting on someone's device
     either evicts them or dies at the first allocation.

  9. The output and log destinations are empty or new. `results/hpo_parallel/` is
     the control group for this comparison; a run that writes into it destroys
     the thing it is being compared against, and does so silently.

 10. Which code files differ from the commit about to be recorded. This one warns
     rather than blocks: several sessions edit this tree at once, so requiring a
     clean tree would stop everything, and the point is that the operator knows.
     `etc/write_run_metadata.py` records the same list beside the results.

Usage:
    etc/preflight_hpo.py --output-root results/hpo_parallel_v2 \\
        --log-root /home/imnyj/Workspace/paper4/logs/hpo_parallel_v2 \\
        --sumo-dirs results/hpo_parallel_v2/g0/sumo ... --gpus 0 1 2 3 \\
        --group-models "PPO MADDPG-MT" "I-HAMAPPO SAC" ...

Exit code is 0 when every check passes and 1 otherwise. The launcher refuses to
start on a non-zero exit; run it by hand to see the same report.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import textwrap
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Largest in-coverage vehicle count anyone has measured: 128,223 transitions
#: over road cycles 0-2. The ceiling has to clear it with margin, because
#: training walks cycles 0-14 and twelve of those were never measured at full
#: episode length.
MEASURED_N_ACTIVE_PEAK = 194.0

#: Mean in-coverage count over the same collection. Used for the OTHER side of
#: the bound: it says where the typical observation lands once divided.
MEASURED_N_ACTIVE_MEAN = 121.7

#: How little of [0, 1] the typical contention observation may occupy. A DECIDED
#: value (team lead, 2026-09-07), not a measured one: it sits between the 0.487
#: the ceiling in force gives and the 0.174 that the rejected physical-capacity
#: figure of 700 would have given. Nothing establishes that 0.29 would harm
#: learning; the threshold exists so that raising the ceiling again has to pass
#: an argument rather than a floor that any large number satisfies.
N_ACTIVE_RESOLUTION_FLOOR = 0.3

#: Files whose presence means a directory already holds results. `sumo/` is
#: excluded on purpose: it is a scratch scenario directory, not an artefact.
RESULT_GLOB_MARKERS = ("optuna_", "hpo_failed_models.csv", ".log")

#: The discount upper bound that has NOT been decided yet. A separate experiment
#: is choosing it; until then this is the value every model would search up to,
#: and its presence is what the gamma check refuses. It is written as "the
#: placeholder that must be gone" rather than "the answer must equal X" so the
#: gate does not have to be edited the moment the decision lands, and so it never
#: asserts a number nobody has agreed to.
UNRESOLVED_GAMMA_HI = 0.999

#: Seconds a vehicle spends inside RSU coverage, measured on this scenario. Used
#: only to state what a discount horizon means in the terms of the problem.
RSU_DWELL_S = (50.0, 54.0)

#: Repository root. The coder tree is a subdirectory of it, so the git state has
#: to be read from here rather than from `ROOT`.
GIT_REPO_DIR = "/home/imnyj"

#: Uncommitted changes under these prefixes change what a run computes, as opposed
#: to changing notes or logs. Relative to GIT_REPO_DIR, matching git's own output.
WATCHED_CODE_PATHS = ("Workspace/paper4/coder/src/", "Workspace/paper4/coder/etc/")

#: The collection the normalisation checks measure against. Outside the work tree
#: for the same reason the scenarios are.
DEFAULT_OFFLINE_DATASET = "/home/imnyj/Workspace/paper4/data/hoorl_offline/hoorl_offline.npz"


class CheckResult:
    """One named check, its verdict, and the lines a human needs to act on it.

    `blocking` separates the two kinds of bad news this gate reports. Most checks
    describe a condition under which the run's numbers would be wrong, so they
    stop it. The working-tree check describes a condition under which the numbers
    are merely unattributable later, and several sessions are editing this tree
    right now, so demanding a clean tree would mean nothing could ever start. It
    reports and lets the operator decide.

    `examined` is how many things the check actually looked at. It exists because
    a check that iterates over an empty list passes, and on 2026-09-06 one did:
    it was supposed to inspect nine models, inspected none, and reported the same
    green line as a check that had inspected all nine. A count in the report makes
    those two distinguishable, and `examined == 0` is treated as a failure rather
    than a pass, because a check that examined nothing has not established its
    property. Checks that have no natural count leave it None and are unaffected.
    """

    def __init__(self, name: str, passed: bool, detail: List[str],
                 blocking: bool = True, examined: Optional[int] = None) -> None:
        self.name = name
        self.examined = examined
        if examined is not None and examined <= 0:
            passed = False
            detail = list(detail) + [
                "examined 0 items, so this check established nothing. A green line "
                "here would mean 'found no problems in a list that was empty'."]
        self.passed = passed
        self.detail = detail
        self.blocking = blocking

    @property
    def stops_launch(self) -> bool:
        return self.blocking and not self.passed

    def render(self) -> str:
        if self.passed:
            mark = "PASS"
        else:
            mark = "FAIL" if self.blocking else "WARN"
        head = f"[{mark}] {self.name}"
        if self.examined is not None:
            head += f"  (examined {self.examined})"
        body = "\n".join(f"       {line}" for line in self.detail)
        return f"{head}\n{body}" if body else head


# --------------------------------------------------------------------------
# 1. observation normalisers: does any of them CLIP?
# --------------------------------------------------------------------------
#: What fraction of samples a feature is allowed to lose at its clipping bound.
#: Anything not listed is allowed none.
#:
#: Both entries are DECISIONS, not tolerances, and each names the trade it lost.
#:
#: [15] QUEUE_MAX clips 1.11 % of rows at 25. Removing the rest of that clipping
#: costs more resolution than it buys: at 30 the feature loses a rank among the
#: twelve magnitude features and at 40 it falls to the bottom of them
#: (`results/hoorl_offline/queue_max_candidates.csv`). Written at 0.02 rather
#: than 0.0111 so ordinary variation between collections does not trip it.
#:
#: [4] A_MAX clips 0.002 %, and this check is what found it: the bound table had
#: been testing `>= 1.0` on a SIGNED feature and could only ever see the positive
#: end, while every clipped sample is on the negative one.
#:
#: WHAT THE CLIPPED ROWS ARE, measured rather than supposed. Exactly two rows of
#: 128,223, and both hold exactly -9.000 m/s2. That is SUMO's emergency
#: deceleration, the value it reports in `performs emergency braking with
#: decel=9.00`, so these are two collision-avoidance manoeuvres and not a
#: population of hard braking that the bound is cutting through. The rest of the
#: distribution is nowhere near: acceleration never exceeds +2.6 m/s2 and the
#: next largest magnitude is below 5.0. So `A_MAX = 5.0` is generous on the
#: positive side and is exceeded only by a discrete safety intervention.
#:
#: Raising the bound does not fix it cheaply. 8.0 clips exactly the same two rows
#: -- the manoeuvre is at 9.0 -- and only 10.0 reaches zero, at the cost of
#: halving the feature's spread from 0.154 to 0.077. Two rows are not worth half
#: a feature. Written at 0.0005 so a real increase in emergency braking, which
#: would say something about the scenario rather than about the bound, still
#: trips it.
CLIPPING_ALLOWANCE: Dict[int, float] = {15: 0.02, 4: 0.0005}


def check_normalisation_clipping(dataset_path: str) -> CheckResult:
    """Every normalising constant, measured against real data for clipping.

    WHY THE TEST IS "DOES IT CLIP" AND NOT "IS IT THE EXPECTED VALUE". This check
    used to assert `N_ACTIVE_MAX_OBS == 168.0`. That form has to be edited every
    time a bound is legitimately revised, it says nothing about the bounds it does
    not name, and it would have passed throughout the period when 168 was clipping
    9.31 % of all rows -- the value was exactly as expected and exactly wrong.
    `QUEUE_MAX` was found the other way round, by measuring what it destroyed,
    and it had never been examined at all because it was filed as a code constant.

    So the property is measured on the data: for every constant that normalises a
    feature, how much of the collection sits at the bound. A constant added later
    is covered automatically, because the map comes from
    `rl_interface.RENORMALISABLE_FEATURES` rather than from a list here.
    """
    name = "observation normalisers do not clip"
    try:
        from src.hoorl_offline import OfflineDataset
        from src.rl_interface import (
            RENORMALISABLE_FEATURES, observation_constants_live,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import: {type(exc).__name__}: {exc}"])
    if not os.path.exists(dataset_path):
        return CheckResult(name, False, [
            f"{dataset_path} does not exist, so no bound can be measured. HOORL's "
            "offline stage needs this file anyway; the launch has a larger problem "
            "than this check."])

    try:
        ds = OfflineDataset.load(dataset_path)
        report = ds.reconcile_to_current_constants()
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, [
            f"reading {dataset_path} raised {type(exc).__name__}: {exc}"])

    live = observation_constants_live()
    states = ds.arrays["state"]
    detail: List[str] = [
        f"{len(ds)} transitions, reconciled to the constants now in force"
        f"{' (moved: ' + ', '.join(sorted(report['constants_moved'])) + ')' if report.get('constants_moved') else ''}"]
    offenders: List[str] = []
    examined = 0
    for j, constant in RENORMALISABLE_FEATURES:
        if constant is None:
            # Ratio features have no bound to clip against.
            continue
        examined += 1
        col = states[:, j].astype("float64")
        # Signed features occupy [-1, 1]; the magnitude is what the bound clips.
        frac = float((abs(col) >= 1.0).mean())
        allowed = CLIPPING_ALLOWANCE.get(j, 0.0)
        mark = "ok" if frac <= allowed else "CLIPS"
        detail.append(f"  [{j:>2}] {constant:<24} = {live.get(constant)!s:<8} "
                      f"clipped {frac:.5f} (allowed {allowed:.5f})  {mark}")
        if frac > allowed:
            offenders.append(f"[{j}] {constant}")

    if offenders:
        detail.append(
            f"{', '.join(offenders)} reach their bound on more of the data than is "
            "allowed. A saturated feature is a constant input, and HPO tuned "
            "against one tunes for an observation the training run will not "
            "produce -- which is what happened to feature [13] under the ceiling "
            "of 100.")
    return CheckResult(name, not offenders, detail, examined=examined)


def check_n_active_max_obs() -> CheckResult:
    """The contention ceiling sits between the tail it must clear and the
    resolution it must not spend.

    Both sides are asserted because each alone admits a value that ruins the
    feature. A floor alone accepts 700, which stops all clipping and leaves the
    typical observation at 0.17 of the range; a ceiling alone accepts 168, which
    keeps the feature large and clips 9.31 % of the collection. The interval
    between them is where the decision lives, and it is narrow enough to state.
    """
    name = "contention ceiling N_ACTIVE_MAX_OBS"
    try:
        from src.rl_interface import N_ACTIVE_MAX_OBS
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import src.rl_interface: "
                            f"{type(exc).__name__}: {exc}"])

    value = float(N_ACTIVE_MAX_OBS)
    lo = MEASURED_N_ACTIVE_PEAK * 1.15
    hi = MEASURED_N_ACTIVE_MEAN / N_ACTIVE_RESOLUTION_FLOOR
    ok = lo <= value <= hi
    detail = [
        f"N_ACTIVE_MAX_OBS = {value}",
        f"  lower bound {lo:.1f} = measured peak {MEASURED_N_ACTIVE_PEAK} x 1.15, "
        f"the margin for the twelve road cycles never measured at full length",
        f"  upper bound {hi:.1f} = mean in-coverage count "
        f"{MEASURED_N_ACTIVE_MEAN} / {N_ACTIVE_RESOLUTION_FLOOR}, the point past "
        f"which the feature is too small next to the other twenty",
        f"  the typical observation lands at "
        f"{MEASURED_N_ACTIVE_MEAN / value:.3f} of the range",
    ]
    if not ok:
        detail.append(
            "fix in src/rl_interface.py N_ACTIVE_MAX_OBS_MEASURED. The same two "
            "bounds are asserted by "
            "tests/test_rl_interface.py::test_contention_normaliser_clears_the_measured_tail; "
            "if they disagree, one of the two was edited alone.")
    return CheckResult(name, ok, detail, examined=1)


# --------------------------------------------------------------------------
# 2. objective function
# --------------------------------------------------------------------------
def _body_without_docstring(fn: ast.AST) -> List[ast.stmt]:
    body = list(getattr(fn, "body", []))
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def _reachable_code_literals(func: Callable[..., Any], max_depth: int = 4) -> Tuple[set, List[str]]:
    """String literals reachable from a function, following calls within its module.

    Two reasons this is not a single-function read. Comments and docstrings must
    be excluded, because the docstring here argues at length about the very metric
    keys being looked for and a text search cannot tell the argument from the code.
    And the arithmetic does not have to stay in the entry function: on 2026-09-05
    the body of `compute_composite_objective` was reduced to
    `sum(composite_objective_terms(...).values())`, at which point a reader that
    stopped at the entry function would report the key as absent from a file that
    still uses it correctly. Following the calls one module deep tracks that kind
    of refactor instead of mistaking it for a regression.

    Returns the literal set and the names of the functions that were read, so the
    report can say where it looked.
    """
    module = inspect.getmodule(func)
    try:
        tree = ast.parse(inspect.getsource(module))
        defs = {n.name: n for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    except (OSError, TypeError, SyntaxError):
        # Fall back to the entry function alone rather than reporting nothing.
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
        defs = {func.__name__: tree.body[0]}

    literals: set = set()
    visited: List[str] = []
    frontier = [(func.__name__, 0)]
    while frontier:
        name, depth = frontier.pop()
        if name in visited or name not in defs or depth > max_depth:
            continue
        visited.append(name)
        for stmt in _body_without_docstring(defs[name]):
            for node in ast.walk(stmt):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    literals.add(node.value)
                elif isinstance(node, ast.Call):
                    callee = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    if callee and callee in defs:
                        frontier.append((callee, depth + 1))
    return literals, visited


def check_objective_reads_packet_loss() -> CheckResult:
    name = "HPO objective reads packet_loss_rate"
    try:
        from src.hpo import compute_composite_objective
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, [f"could not import src.hpo: {type(exc).__name__}: {exc}"])

    detail: List[str] = []

    # Read the literals out of the AST rather than grepping the text. The
    # function's docstring explains at length why the `outage_rate` fallback was
    # removed, and a substring search cannot tell that explanation apart from the
    # code it describes. The AST drops comments outright and the docstring is
    # discarded below, so what is left is what actually executes.
    reads_key, reads_alias = False, False
    try:
        literals, visited = _reachable_code_literals(compute_composite_objective)
        reads_key = "packet_loss_rate" in literals
        reads_alias = "outage_rate" in literals
        detail.append(f"read {' -> '.join(visited)}")
        detail.append(f"executable code references 'packet_loss_rate': {reads_key}")
    except (OSError, SyntaxError, TypeError) as exc:
        return CheckResult(name, False, detail + [f"could not read the source: {type(exc).__name__}: {exc}"])
    if reads_alias:
        detail.append(
            "executable code still references 'outage_rate'; that alias carries a "
            "constant, so a fallback onto it would put the constant back in the objective."
        )

    # Static reading is not proof. Score two metric dicts that differ only in the
    # loss term and require the objective to move.
    base: Dict[str, float] = {
        "mean_error": 1.0, "mean_aoi": 1.0, "avg_power_norm": 0.5,
        "packet_loss_rate": 0.0,
    }
    high = dict(base, packet_loss_rate=0.30)
    try:
        v_low = float(compute_composite_objective(base))
        v_high = float(compute_composite_objective(high))
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, detail + [f"scoring raised {type(exc).__name__}: {exc}"])

    responds = v_high > v_low
    detail.append(
        f"packet_loss_rate 0.00 -> objective {v_low:.6f}; "
        f"0.30 -> {v_high:.6f}; delta {v_high - v_low:+.6f}"
    )
    if not responds:
        detail.append(
            "the objective does not increase with packet loss, so the loss term is "
            "constant or absent. fix: src/hpo.py compute_composite_objective()."
        )
    ok = reads_key and responds and not reads_alias
    if reads_alias and reads_key and responds:
        detail.append("blocked on the lingering 'outage_rate' mention above; inspect it before launching.")
    return CheckResult(name, ok, detail)


# --------------------------------------------------------------------------
# 3. discount factor search range
# --------------------------------------------------------------------------
def _module_constants(tree: ast.Module) -> Dict[str, Any]:
    """Module-level `NAME = <literal>` bindings, so a refactor stays readable.

    The bounds are literals in the call today. If someone lifts them to a named
    constant, a literal-only reader would report 'cannot tell' on a file that is
    perfectly clear, so names are resolved one level.
    """
    consts: Dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    consts[tgt.id] = node.value.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.target, ast.Name):
            consts[node.target.id] = node.value.value
    return consts


def _gamma_ranges(path: str) -> List[Tuple[str, Any, Any]]:
    """Every `suggest_float("gamma", lo, hi)` in a file, with its enclosing function.

    Read from the AST of the file on disk rather than by importing it: this must
    describe the source the launcher is about to run, and it must work while
    another session has the module in an unimportable intermediate state.
    """
    with open(path) as fh:
        tree = ast.parse(fh.read())
    consts = _module_constants(tree)

    def literal(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and node.id in consts:
            return consts[node.id]
        if isinstance(node, ast.Attribute):
            return f"<{node.attr}>"
        return None

    found: List[Tuple[str, Any, Any]] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name not in ("suggest_float", "suggest_uniform", "suggest_loguniform"):
                continue
            args = list(node.args)
            if not args or not isinstance(args[0], ast.Constant) or args[0].value != "gamma":
                continue
            lo = literal(args[1]) if len(args) > 1 else None
            hi = literal(args[2]) if len(args) > 2 else None
            found.append((fn.name, lo, hi))
    return found


def check_gamma_range(hpo_path: str, unresolved_hi: float,
                      dwell_s: Tuple[float, float]) -> CheckResult:
    """Refuse to launch while the discount range still carries its placeholder top.

    The upper bound is being decided by a separate experiment. Until that lands,
    every model searches up to `unresolved_hi`, whose effective horizon 1/(1-gamma)
    is 1000 decisions -- against a measured 50 to 54 s of RSU dwell, a scheduler
    optimising a return it can never collect. This gate does not assert the answer,
    which nobody has yet; it asserts that the placeholder is gone, so a decision
    taken in discussion cannot fail to reach the code before nine hours start.

    It also requires all models to agree. The other way this week's runs went
    wrong was a change applied to two of three paths, which is invisible in any
    single-site check but obvious the moment the sites are compared.
    """
    name = "discount factor search range is resolved"
    detail: List[str] = []
    try:
        ranges = _gamma_ranges(hpo_path)
    except (OSError, SyntaxError) as exc:
        return CheckResult(name, False, [f"could not parse {hpo_path}: {type(exc).__name__}: {exc}"])

    if not ranges:
        return CheckResult(name, False, [
            f"no gamma search range found in {os.path.basename(hpo_path)}.",
            "expected suggest_float('gamma', lo, hi) inside sample_hparams; if the "
            "search moved elsewhere this check is looking at the wrong place and "
            "must be pointed at the new site rather than deleted.",
        ])

    sites = {fn for fn, _, _ in ranges}
    bounds = {(lo, hi) for _, lo, hi in ranges}
    detail.append(
        f"{len(ranges)} gamma range(s) in {os.path.basename(hpo_path)}, "
        f"declared in: {', '.join(sorted(sites))}"
    )

    ok = True
    if len(bounds) > 1:
        ok = False
        detail.append("the models do NOT all search the same range:")
        for lo, hi in sorted(bounds, key=str):
            models = [fn for fn, l, h in ranges if (l, h) == (lo, hi)]
            detail.append(f"  ({lo}, {hi}) at {len(models)} site(s)")
        detail.append(
            "a bound changed at some sites and not others makes the nine studies "
            "incomparable. Apply it everywhere or nowhere."
        )
    else:
        lo, hi = next(iter(bounds))
        detail.append(f"all sites search gamma in ({lo}, {hi})")
        if isinstance(hi, (int, float)):
            horizon = 1.0 / (1.0 - float(hi)) if float(hi) < 1.0 else float("inf")
            detail.append(
                f"upper bound {hi} -> effective horizon 1/(1-gamma) = {horizon:.0f} decisions; "
                f"measured RSU dwell is {dwell_s[0]:.0f} to {dwell_s[1]:.0f} s"
            )
        if isinstance(hi, (int, float)) and abs(float(hi) - unresolved_hi) < 1e-12:
            ok = False
            detail.append(
                f"this is still the UNRESOLVED placeholder {unresolved_hi}. The upper "
                f"bound is under active investigation and has not been decided."
            )
            detail.append(
                "launching now spends nine hours tuning against a horizon roughly "
                "nineteen times the time a vehicle is in range."
            )
            detail.append(
                "fix: set the decided bound at the gamma entry in sample_hparams "
                "(src/hpo.py), then run this gate again. Lower this script's "
                "UNRESOLVED_GAMMA_HI only if the decision is to keep 0.999."
            )
        elif isinstance(hi, (int, float)):
            detail.append(f"placeholder {unresolved_hi} is gone; the bound has been decided")
        else:
            ok = False
            detail.append(
                f"the upper bound is not a literal this check can read (got {hi!r}); "
                f"it cannot confirm the placeholder is gone."
            )
    return CheckResult(name, ok, detail)


# --------------------------------------------------------------------------
# 4. model coverage
# --------------------------------------------------------------------------
def check_model_coverage(groups: List[str]) -> CheckResult:
    """The four groups between them must run each of the nine baselines once.

    The group lists are hand-maintained strings in the launcher, and they get
    rearranged whenever the cost balance is revisited -- MA2HDQN moved from g2 to
    g3 on 2026-09-05. A model dropped or duplicated in that edit produces no
    error: the run starts, four logs look healthy, and it surfaces twelve hours
    later when `merge_hpo_results.py` refuses because nothing produced it. Same
    check, moved to the front.

    Checked against `src.baselines.ALL_BASELINES` rather than a list retyped here,
    so adding a tenth baseline makes this fail until the groups are updated.
    """
    name = "the groups cover all nine baselines exactly once"
    try:
        from src.baselines import ALL_BASELINES
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, [f"could not import src.baselines: {type(exc).__name__}: {exc}"])

    scheduled: List[str] = []
    for spec in groups:
        scheduled.extend(spec.split())

    registry = list(ALL_BASELINES)
    missing = [m for m in registry if m not in scheduled]
    unknown = [m for m in scheduled if m not in registry]
    duplicated = sorted({m for m in scheduled if scheduled.count(m) > 1})

    detail = [f"{len(groups)} group(s), {len(scheduled)} model slot(s), "
              f"registry has {len(registry)}"]
    for i, spec in enumerate(groups):
        detail.append(f"  g{i}: {spec}")

    ok = True
    if missing:
        ok = False
        detail.append(f"NOT scheduled by any group: {', '.join(missing)}")
        detail.append("the run would finish with a baseline absent, and the merge "
                      "would refuse afterwards rather than now.")
    if duplicated:
        ok = False
        detail.append(f"scheduled more than once: {', '.join(duplicated)}")
        detail.append("two groups would each write a best-params row for it and "
                      "the merge cannot tell which answer to keep.")
    if unknown:
        ok = False
        detail.append(f"not in the registry: {', '.join(unknown)}")
        detail.append("a typo here starts a study for a model that does not exist.")
    if ok:
        detail.append("every baseline scheduled exactly once")
    # THE COUNT IS ASSERTED, NOT ONLY REPORTED. A check that counts nine passes
    # trivially when its list is empty -- and this is the check that caught
    # CARLTON, so a silent pass here is expensive. `examined` makes an empty run
    # fail; requiring it to equal the registry makes a SHORT run fail too, which
    # a bare count would not.
    if len(scheduled) != len(registry):
        ok = False
        detail.append(
            f"examined {len(scheduled)} model slot(s) against a registry of "
            f"{len(registry)}. The two must match: fewer slots means the check "
            "looked at part of the run and reported on all of it.")
    return CheckResult(name, ok, detail, examined=len(scheduled))


#: Below this many sampled keys, a model is being tuned on the generic fallback
#: rather than on its own search space. NOT a guess: the fallback branch of
#: `sample_hparams` offers exactly `lr`, `hidden_dim` and `gamma`, so three is the
#: fallback's own width and anything at or below it is indistinguishable from
#: having no tailored space at all. Every model that HAS a space defines strictly
#: more, which is what makes the threshold discriminate.
MIN_SEARCH_SPACE_KEYS = 4


def check_search_space_reaches_every_group_model(groups: List[str]) -> CheckResult:
    """Each scheduled name must draw its OWN search space, not the fallback.

    THE FAILURE THIS CATCHES IS SILENT AND PRODUCES A COMPLETE-LOOKING STUDY.
    `normalize_model_name` maps an alias to a canonical name by stripping `-` and
    `_` and lowercasing. It does not strip whitespace, and it does not reject a
    name it fails to resolve -- it returns the string unchanged. So a group entry
    with a stray space, or a name that has been retired from the registry, falls
    through every explicit branch of `sample_hparams` into the generic fallback,
    and the study runs fifteen trials over three hyper-parameters instead of the
    seven that model needs. Measured 2026-09-06:

        'MA2HDQN'  -> 7 keys
        'MA2HDQN ' -> 3 keys

    Nothing in the logs distinguishes the two. The trials complete, the CSV has a
    best-params row, and the result is a model tuned on a fraction of its space.

    WHY THIS DUPLICATES A FIX BEING MADE ELSEWHERE, DELIBERATELY. The normaliser
    is being taught to strip whitespace and to raise on an unknown name in
    `src/hpo.py`. This check asks the same question from the other side, by
    SAMPLING the space rather than by reasoning about the name, so the two fail
    independently: if the normaliser fix regresses, or resolves a name in a way
    that still misses its branch, this still reports it. A gate that shares its
    implementation with the thing it gates cannot do that.

    It reads `_search_space_keys`, which drives `sample_hparams` with a recording
    stand-in for the Optuna trial. No study is created and nothing is sampled for
    real, so the check costs milliseconds.
    """
    name = "every scheduled model draws its own search space, not the fallback"
    try:
        from src.hpo import _search_space_keys, normalize_model_name
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import src.hpo: {type(exc).__name__}: {exc}"])

    scheduled: List[str] = []
    for spec in groups:
        scheduled.extend(spec.split())
    if not scheduled:
        return CheckResult(name, False, ["no group models given; nothing to check"])

    detail: List[str] = []
    ok = True
    for raw in scheduled:
        canonical = normalize_model_name(raw)
        try:
            keys = _search_space_keys(canonical)
        except Exception as exc:  # noqa: BLE001
            ok = False
            detail.append(f"  {raw!r}: sampling raised {type(exc).__name__}: {exc}")
            continue
        n = len(keys)
        flag = ""
        if canonical != raw:
            flag += f" (normalised from {raw!r})"
        if n < MIN_SEARCH_SPACE_KEYS:
            ok = False
            flag += ("  <-- FALLBACK. This model is being tuned on the generic "
                     "three-key space, not its own.")
        detail.append(f"  {canonical}: {n} key(s){flag} -> {sorted(keys)}")

    # The whitespace case is probed directly rather than waited for, because the
    # group lists are hand-edited strings and a trailing space is invisible in a
    # diff. If a future normaliser stops being fooled by it this reports so and
    # the check can be simplified; until then it is a live hazard.
    probe = scheduled[0]
    padded_keys = _search_space_keys(normalize_model_name(probe + " "))
    clean_keys = _search_space_keys(normalize_model_name(probe))
    if len(padded_keys) != len(clean_keys):
        detail.append(
            f"HAZARD: {probe + ' '!r} resolves to a {len(padded_keys)}-key space "
            f"while {probe!r} resolves to {len(clean_keys)}. A trailing space in "
            "the group list would silently shrink the search space; it is "
            "invisible in a diff and produces a complete-looking study."
        )
    else:
        detail.append(f"whitespace is tolerated by the normaliser (probed with {probe!r})")

    if ok:
        detail.insert(0, f"all {len(scheduled)} scheduled model(s) draw "
                         f"{MIN_SEARCH_SPACE_KEYS}+ keys")
    return CheckResult(name, ok, detail, examined=len(scheduled))


def check_hpo_prepares_scenario_before_models() -> CheckResult:
    """The search must generate its scenario BEFORE it constructs a model.

    THE CONTRACT. `prepare_scenario`'s own docstring states it: "Must run BEFORE
    any model is constructed. `ActionDecoder` and `StateVectorizer` read
    `DELTA_MAX` / `V_MAX_OBS` / `E_REF`, and those describe the network on disk."
    A model built before the scenario exists carries a decoder whose Delta range
    describes a network that was never simulated.

    WHY THE SEARCH IS THE PATH THAT BREAKS IT. `run_hot_swap_training` honours the
    contract at line 3736. `src/hpo.py` contained no call to `prepare_scenario` at
    all, and `run_hpo_parallel.sh` hands every group an EMPTY scenario directory,
    so the first trial in each process built its model against the import-time
    fallback constants. For HOORL that is fatal rather than subtle: loading the
    offline dataset compares its stored `V_MAX_OBS` of 15.912 against the fallback
    13.32, a 19.5 % difference, and refuses. `hpo.py` catches the exception and
    records `FAILED_RUN_PENALTY`, which in the trial CSV is indistinguishable from
    a genuinely poor trial.

    WHY IT HAS NOT SHOWN UP. Group g3 lists `SPAM-D3QN HOORL MA2HDQN`, so
    SPAM-D3QN runs first and generates the scenario on HOORL's behalf. The run is
    correct today because of the ORDER OF A HAND-EDITED STRING. Reordering that
    list, or running HOORL alone, loses all fifteen trials -- and loses them
    silently, because a trial that dies before reaching `evaluate_model_in_env`
    never generates the scenario the next trial would have needed either.

    HOW THIS IS CHECKED WITHOUT DEPENDING ON THAT ORDER. Two stages. The first is
    static and cheap: `src/hpo.py` must contain a `prepare_scenario` call at all,
    which is what was missing. The second runs the study entry point in a
    genuinely EMPTY scenario directory with the model listed alone, and records
    whether `refresh_scenario_constants` fired before the first model was
    constructed. Running the model alone is the point: it removes the neighbour
    that currently masks the defect, so the check measures the entry point rather
    than the group list.
    """
    name = "the HPO entry point prepares its scenario before constructing a model"
    hpo_path = os.path.join(ROOT, "src", "hpo.py")
    try:
        text = open(hpo_path, encoding="utf-8").read()
    except OSError as exc:
        return CheckResult(name, False, [f"could not read {hpo_path}: {exc}"])

    if "prepare_scenario(" not in text:
        return CheckResult(name, False, [
            "src/hpo.py contains no call to prepare_scenario().",
            "Every group process is handed an EMPTY scenario directory by "
            "run_hpo_parallel.sh, so the first trial builds its model against the "
            "import-time fallback constants (V_MAX_OBS 13.32 against a real "
            "15.9x). For HOORL the offline dataset is then refused as incompatible "
            "and the trial is recorded as FAILED_RUN_PENALTY, which looks like a "
            "bad trial rather than a broken run.",
            "It does not fail today only because SPAM-D3QN precedes HOORL in g3 "
            "and generates the scenario first. That is the order of a hand-edited "
            "string, not a guarantee.",
        ])

    # Stage two: does it actually happen, and in the right order?
    import tempfile as _tempfile

    detail = ["src/hpo.py calls prepare_scenario()"]
    scratch = _tempfile.mkdtemp(prefix="preflight_hpo_order_")
    empty_sumo = os.path.join(scratch, "sumo")
    os.makedirs(empty_sumo, exist_ok=True)
    previous = os.environ.get("PAPER4_SUMO_DIR")
    os.environ["PAPER4_SUMO_DIR"] = empty_sumo
    order: List[str] = []
    try:
        import src.hot_swap_trainer as hst
        import src.rl_interface as rli
        import src.sumo.make_sumo_set as ss
        from src.baselines import get_baseline
        from src.hpo import run_hpo_study

        # ------------------------------------------------------------------
        # REDIRECT THE MODULE, NOT ONLY THE ENVIRONMENT.
        # ------------------------------------------------------------------
        # `make_sumo_set.BASE_PATH` is bound at IMPORT from PAPER4_SUMO_DIR, and
        # by the time this check runs the module has already been imported by an
        # earlier one. Setting the variable now therefore redirects nothing, and
        # the one-trial probe below generates its scenario into the SHARED
        # directory instead of the scratch one.
        #
        # That is not hypothetical and it is not harmless: the probe runs with
        # `n_steps=10`, so it writes a scenario whose flows end at
        # (10 + 1200 + 100) x 0.1 = 131.0 s, and 131 s in `coder/src/sumo` is
        # precisely the state the scenario-horizon check condemns. THE GATE WAS
        # POLLUTING THE DIRECTORY IT THEN REFUSED TO LAUNCH OVER: a clean run
        # passed, and every run after it failed on damage the previous run had
        # done. Found on 2026-09-07 by regenerating the shared scenario, watching
        # it come back at 131 s after a single preflight, and matching the
        # arithmetic.
        #
        # `BASE_PATH` is read through an accessor at call time, so assigning to it
        # is the supported way to move it after import.
        previous_base = ss.BASE_PATH
        ss.BASE_PATH = empty_sumo

        original_refresh = rli.refresh_scenario_constants
        model_cls = get_baseline("SPAM-D3QN")
        original_init = model_cls.__init__

        def recording_refresh(*a, **k):
            order.append("refresh_scenario_constants")
            return original_refresh(*a, **k)

        def recording_init(self, *a, **k):
            order.append("model_constructed")
            return original_init(self, *a, **k)

        rli.refresh_scenario_constants = recording_refresh
        hst.refresh_scenario_constants = recording_refresh
        model_cls.__init__ = recording_init
        try:
            run_hpo_study(model_name="SPAM-D3QN", model_cls=model_cls,
                          n_trials=1, seeds=[42], n_steps=10)
        finally:
            rli.refresh_scenario_constants = original_refresh
            hst.refresh_scenario_constants = original_refresh
            model_cls.__init__ = original_init
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, detail + [
            f"the one-trial probe raised {type(exc).__name__}: {exc}"])
    finally:
        try:
            import src.sumo.make_sumo_set as ss  # noqa: F811
            ss.BASE_PATH = previous_base
        except (ImportError, NameError):
            pass
        if previous is None:
            os.environ.pop("PAPER4_SUMO_DIR", None)
        else:
            os.environ["PAPER4_SUMO_DIR"] = previous
        shutil.rmtree(scratch, ignore_errors=True)

    if "model_constructed" not in order:
        return CheckResult(name, False, detail + [
            f"the probe never constructed a model; call order was {order}"])
    if "refresh_scenario_constants" not in order:
        return CheckResult(name, False, detail + [
            "the scenario constants were never refreshed during a trial, so the "
            f"model was built against import-time values. Call order: {order}"])
    ok = order.index("refresh_scenario_constants") < order.index("model_constructed")
    detail.append(
        f"first three calls in an EMPTY scenario directory: {order[:3]} "
        f"(refresh before model construction = {ok})"
    )
    if not ok:
        detail.append(
            "The model was constructed first, so its ActionDecoder describes a "
            "network that did not exist yet. Move the prepare_scenario call above "
            "the model construction in evaluate_trial_multiseed."
        )
    return CheckResult(name, ok, detail)


# --------------------------------------------------------------------------
# 5. scenario horizon
# --------------------------------------------------------------------------
def _rou_flow_end(path: str) -> Any:
    """The latest `end=` on any <flow> in a rou.xml, in seconds.

    The flows are what put vehicles on the road. Once the last one ends the
    network drains, and everything measured after that is measured on a road that
    is emptying for reasons nothing in the experiment controls.
    """
    tree = ET.parse(path)
    ends = []
    for flow in tree.getroot().iter("flow"):
        value = flow.get("end")
        if value is not None:
            try:
                ends.append(float(value))
            except ValueError:
                pass
    return max(ends) if ends else None


def _scenario_horizon(directory: str) -> Dict[str, Any]:
    """What a scenario directory claims, and what it actually contains.

    Both are read because they have been observed to disagree: on 2026-09-05 the
    signature in `coder/src/sumo/` said FLOW_END_S 51.0 while the rou.xml beside
    it carried end="138.0". A check that trusted either one alone would have
    reported a consistent scenario.
    """
    out: Dict[str, Any] = {"dir": directory, "exists": os.path.isdir(directory)}
    sig_path = os.path.join(directory, ".sumo_gen_signature.json")
    rou_path = os.path.join(directory, "generated.rou.xml")
    out["has_scenario"] = os.path.isfile(rou_path)

    if os.path.isfile(sig_path):
        try:
            with open(sig_path) as fh:
                out["signature_flow_end_s"] = float(json.load(fh).get("FLOW_END_S"))
        except (OSError, ValueError, TypeError):
            out["signature_flow_end_s"] = None
    else:
        out["signature_flow_end_s"] = None

    if out["has_scenario"]:
        try:
            out["rou_flow_end_s"] = _rou_flow_end(rou_path)
        except (OSError, ET.ParseError):
            out["rou_flow_end_s"] = None
    else:
        out["rou_flow_end_s"] = None
    return out


def check_scenario_horizon(directories: List[str]) -> CheckResult:
    """Every scenario on disk must outlast warm-up plus the measured window.

    The warm-up was raised from 350 to 1200 steps so that what gets measured is a
    settled network. At a 0.1 s step that is 120 s of warm-up before the first
    measurement, and an HPO rollout adds 4000 steps on top. A scenario whose flows
    stop at 131 s therefore begins draining while the measurement is still running,
    and the density axis the whole study is defined over stops meaning anything --
    silently, because a short scenario raises no error, it just runs out of cars.

    Directories are checked, not constants, because `prepare_scenario` overwrites
    `ss.FLOW_END_S` per run and the value in `make_sumo_set.py` is only the
    default a run starts from. What matters is what is on disk where the run will
    read it. The shared `coder/src/sumo/` is always included: any process that
    does not set PAPER4_SUMO_DIR falls back to it.
    """
    name = "scenario flows outlast warm-up plus the measured window"
    detail: List[str] = []
    try:
        import src.sumo.make_sumo_set as ss
        from src.hot_swap_trainer import DEFAULT_WARMUP_STEPS
        from src.hpo import DEFAULT_HPO_N_STEPS
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, [f"could not read the run constants: {type(exc).__name__}: {exc}"])

    step = float(ss.STEP_LENGTH)
    # The same arithmetic `prepare_scenario` uses, so the requirement is the one
    # the run will itself generate against rather than a second opinion.
    required = (int(DEFAULT_HPO_N_STEPS) + int(DEFAULT_WARMUP_STEPS) + 100) * step
    detail.append(
        f"need >= {required:.1f} s = ({DEFAULT_HPO_N_STEPS} rollout + "
        f"{DEFAULT_WARMUP_STEPS} warm-up + 100) x {step} s"
    )
    detail.append(f"make_sumo_set.FLOW_END_S default is {float(ss.FLOW_END_S):.1f} s")

    ok = True
    if float(ss.FLOW_END_S) < required:
        ok = False
        detail.append(
            f"the module default itself is shorter than one rollout; any run that "
            f"does not override it generates a scenario that drains mid-measurement."
        )

    seen = []
    for d in directories:
        info = _scenario_horizon(d)
        if not info["has_scenario"]:
            detail.append(f"{d}: no scenario yet; the run will generate one")
            continue
        seen.append(info)
        sig, rou = info["signature_flow_end_s"], info["rou_flow_end_s"]
        detail.append(f"{d}: signature {sig} s, rou.xml flows end {rou} s")
        if sig is None or rou is None:
            ok = False
            detail.append("  could not read one of the two; treat the scenario as unknown")
            continue
        if abs(sig - rou) > 1e-6:
            ok = False
            detail.append(
                "  the signature and the file DISAGREE. The signature is what "
                "`generation_signature_matches` consults to decide whether to "
                "regenerate, so a run can skip regeneration and then drive a "
                "network built for different parameters."
            )
        if min(sig, rou) < required:
            ok = False
            detail.append(
                f"  shorter than the {required:.1f} s the run needs; vehicles stop "
                f"being inserted {required - min(sig, rou):.1f} s before the "
                f"measurement window closes."
            )
    if ok and seen:
        detail.append("every scenario on disk covers the full run")
    if not ok:
        detail.append(
            "fix: regenerate with the canonical parameters, e.g. "
            "`make_sumo_files(force_regenerate=True)` with FLOW_END_S left at its "
            "module default, and check that the signature and rou.xml then agree."
        )
    return CheckResult(name, ok, detail)


# --------------------------------------------------------------------------
# 6. scenario directories outside the git work tree
# --------------------------------------------------------------------------
def check_scenario_outside_worktree(directories: List[str]) -> CheckResult:
    """A scenario directory inside the work tree is one `git clean` from gone.

    `.gitignore` is not a defence. `git clean -fdx` deletes ignored files by
    design -- being ignored is what `-x` targets -- and `git check-ignore` will
    happily report a directory as ignored right up until it is deleted, so it
    cannot answer this question. Nor is `-x` the whole risk: measured on this
    tree, `git clean -nd Workspace/paper4` alone lists 175 entries, of which only
    37 need `-x`. The rest are merely untracked, which a fresh scenario directory
    always is.

    This is not hypothetical. On 2026-09-04 the g1 group's scenario directory
    disappeared two and a half hours into its run and every remaining rollout
    died; 62 rollouts and the entire SAC study went with it.

    The test is containment, not ignore status: anything at or below
    `git rev-parse --show-toplevel` is reachable. That top level is /home/imnyj
    here, so every path under Workspace/ qualifies and the scenarios have to live
    somewhere else entirely.
    """
    name = "scenario directories are outside the git work tree"
    if not directories:
        return CheckResult(name, False, ["no scenario directories given; nothing to check"])
    try:
        top = subprocess.run(
            ["git", "-C", GIT_REPO_DIR, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(name, False, [
            f"could not locate the work tree: {type(exc).__name__}: {exc}",
            "without it there is no way to tell whether the scenarios are exposed.",
        ])

    top_real = os.path.realpath(top)
    detail = [f"work tree top level: {top_real}"]
    inside: List[str] = []
    for d in directories:
        # realpath, so a symlink pointing back into the tree is not a way past this.
        real = os.path.realpath(os.path.abspath(d))
        exposed = real == top_real or (real + os.sep).startswith(top_real + os.sep)
        detail.append(f"  {'INSIDE ' if exposed else 'outside'}  {real}")
        if exposed:
            inside.append(real)

    if inside:
        detail.append(
            f"{len(inside)} scenario directory(ies) sit inside the work tree. A "
            f"`git clean` run by anyone, with or without -x, removes them mid-run "
            f"and every subsequent rollout dies on a missing network."
        )
        detail.append(
            "fix: pass --sumo-root pointing outside the tree, e.g. /var/tmp/paper4_sumo."
        )
        return CheckResult(name, False, detail)

    detail.append("no scenario directory is reachable by a git clean in this repository")
    detail.append(
        "note: this only covers the directories this run will use. The shared "
        "coder/src/sumo/ is inside the tree by construction and stays exposed."
    )
    return CheckResult(name, True, detail, examined=len(directories))


# --------------------------------------------------------------------------
# 7. SUMO isolation and the generation lock
# --------------------------------------------------------------------------
def check_sumo_isolation(sumo_dirs: List[str]) -> CheckResult:
    name = "SUMO scenario directories isolated and self-healing"
    detail: List[str] = []
    ok = True

    if not sumo_dirs:
        return CheckResult(name, False, ["no --sumo-dirs given; nothing to check"])

    # (a) the group directories must be distinct paths.
    resolved = [os.path.realpath(os.path.abspath(d)) for d in sumo_dirs]
    duplicates = {p for p in resolved if resolved.count(p) > 1}
    if duplicates:
        ok = False
        detail.append("group SUMO directories are NOT distinct; these repeat:")
        for p in sorted(duplicates):
            detail.append(f"  {p}")
        detail.append(
            "two processes sharing one directory regenerate the same "
            "generated.net.xml and silently read a network they did not ask for."
        )
    else:
        detail.append(f"{len(resolved)} group directories, all distinct:")
        for p in resolved:
            detail.append(f"  {p}")

    # (b) none of them may sit inside another, which would share a lock file.
    for i, a in enumerate(resolved):
        for j, b in enumerate(resolved):
            if i != j and (a + os.sep).startswith(b + os.sep):
                ok = False
                detail.append(f"{a} is nested inside {b}; they would share generated files")

    # (c) PAPER4_SUMO_DIR must actually redirect BASE_PATH. Checked in a
    #     subprocess because the constant is read at import time.
    probe_dir = tempfile.mkdtemp(prefix="preflight_sumo_")
    target = os.path.join(probe_dir, "redirected")
    env = dict(os.environ, PAPER4_SUMO_DIR=target, PYTHONPATH=ROOT)
    try:
        out = subprocess.run(
            [sys.executable, "-c",
             "import src.sumo.make_sumo_set as ss; print(ss.BASE_PATH)"],
            capture_output=True, text=True, timeout=180, env=env, cwd=ROOT,
        )
        got = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
        if os.path.realpath(got) == os.path.realpath(target):
            detail.append(f"PAPER4_SUMO_DIR redirects BASE_PATH -> {got}")
        else:
            ok = False
            detail.append(f"PAPER4_SUMO_DIR did NOT redirect BASE_PATH: got {got!r}, wanted {target!r}")
            if out.stderr.strip():
                detail.append(f"stderr tail: {out.stderr.strip().splitlines()[-1]}")
    except (OSError, subprocess.SubprocessError) as exc:
        ok = False
        detail.append(f"probing PAPER4_SUMO_DIR failed: {type(exc).__name__}: {exc}")
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)

    # (d) the generation lock must create its own parent directory. This is the
    #     exact failure that killed the g1 group: the directory disappeared under
    #     a running process and every later rollout raised FileNotFoundError.
    lock_dir = tempfile.mkdtemp(prefix="preflight_lock_")
    missing = os.path.join(lock_dir, "vanished", "sumo")
    try:
        import src.sumo.make_sumo_set as ss
        with ss._generation_lock(missing):
            created = os.path.isdir(missing)
            has_lock = os.path.exists(os.path.join(missing, ss.GENERATION_LOCK_FILE))
        if created and has_lock:
            detail.append("generation lock recreated an absent parent directory and took its flock")
        else:
            ok = False
            detail.append(
                f"generation lock did not restore the directory "
                f"(dir={created}, lockfile={has_lock}); a directory lost mid-run "
                f"would kill every remaining rollout."
            )
    except Exception as exc:  # noqa: BLE001
        ok = False
        detail.append(
            f"generation lock raised {type(exc).__name__}: {exc} on an absent "
            f"parent directory. fix: src/sumo/make_sumo_set.py _generation_lock()."
        )
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)

    return CheckResult(name, ok, detail, examined=len(sumo_dirs))


# --------------------------------------------------------------------------
# 8. GPUs
# --------------------------------------------------------------------------
def check_gpus(wanted: List[int]) -> CheckResult:
    name = "requested GPUs are free"
    try:
        sys.path.insert(0, os.path.join(ROOT, "etc"))
        from gpu_alloc import MAX_UTIL_PCT, MIN_FREE_MIB, probe
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, [f"could not import etc/gpu_alloc.py: {type(exc).__name__}: {exc}"])

    gpus = probe()
    if not gpus:
        return CheckResult(name, False, ["nvidia-smi returned nothing; no driver, or the query failed"])

    by_index = {g["index"]: g for g in gpus}
    detail = [f"thresholds: >= {MIN_FREE_MIB} MiB free and <= {MAX_UTIL_PCT}% utilised"]
    ok = True
    for idx in wanted:
        g = by_index.get(idx)
        if g is None:
            ok = False
            detail.append(f"GPU {idx}: not present on this machine")
            continue
        state = "idle" if g["usable"] else g["reason"]
        detail.append(
            f"GPU {idx}: {g['memory_used_mib']:>6} / {g['memory_total_mib']} MiB used, "
            f"{g['utilization_pct']:>3}% util -> {state}"
        )
        if not g["usable"]:
            ok = False
    if not ok:
        detail.append(
            "someone else is on at least one device. Starting anyway either evicts "
            "their job or dies at the first allocation, hours in."
        )
    # An empty GPU list would otherwise pass: no device to find busy. A run that
    # requested no devices is not a run whose GPUs are free.
    return CheckResult(name, ok, detail, examined=len(wanted))


# --------------------------------------------------------------------------
# 9. destinations
# --------------------------------------------------------------------------
def _existing_artefacts(path: str) -> List[str]:
    """Files under `path` that look like results, ignoring scratch SUMO dirs."""
    found: List[str] = []
    if not os.path.isdir(path):
        return found
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d != "sumo"]
        for fn in filenames:
            if any(m in fn for m in RESULT_GLOB_MARKERS):
                found.append(os.path.relpath(os.path.join(dirpath, fn), path))
    return sorted(found)


def check_destination(path: str, label: str, protect: List[str]) -> CheckResult:
    name = f"{label} is empty or new"
    abs_path = os.path.abspath(path)
    detail = [f"path: {abs_path}"]

    for guarded in protect:
        g = os.path.abspath(guarded)
        if abs_path == g or (abs_path + os.sep).startswith(g + os.sep):
            detail.append(
                f"this is inside the protected control directory {g}. Those results "
                f"are the comparison baseline for the new normaliser; writing here "
                f"destroys what the new run is supposed to be measured against."
            )
            detail.append("choose a different --output-root, e.g. results/hpo_parallel_v2.")
            return CheckResult(name, False, detail)

    if not os.path.exists(abs_path):
        detail.append("does not exist yet; the launcher will create it")
        return CheckResult(name, True, detail)

    artefacts = _existing_artefacts(abs_path)
    if artefacts:
        detail.append(f"already holds {len(artefacts)} result file(s); the run would overwrite them:")
        for a in artefacts[:12]:
            detail.append(f"  {a}")
        if len(artefacts) > 12:
            detail.append(f"  ... and {len(artefacts) - 12} more")
        detail.append("move them aside, or point --output-root/--log-root somewhere new.")
        return CheckResult(name, False, detail)

    detail.append("exists and holds no result files")
    return CheckResult(name, True, detail)


# --------------------------------------------------------------------------
# 10. provenance
# --------------------------------------------------------------------------
def check_working_tree(watched: List[str]) -> CheckResult:
    """Report, without blocking, which code differs from the commit being recorded.

    Not blocking, deliberately. Two sessions are editing this tree, so a clean-tree
    requirement would mean nothing could ever launch. What it buys is that the
    operator knows before starting, and `run_metadata.json` records the same list
    beside the results. The failure this addresses was not a dirty tree; it was a
    run whose outputs could not later be attributed to any particular code at all
    -- the previous main training finished four hours before the divergence guard
    it was credited with even existed, and no artefact said so.
    """
    name = "working tree matches the commit that will be recorded"
    try:
        head = subprocess.run(
            ["git", "-C", GIT_REPO_DIR, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout.strip()
        porcelain = subprocess.run(
            ["git", "-C", GIT_REPO_DIR, "status", "--porcelain"],
            capture_output=True, text=True, timeout=120, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(name, False, [
            f"could not read git state: {type(exc).__name__}: {exc}",
            "the run would be recorded with no commit at all.",
        ], blocking=False)

    entries = [ln for ln in porcelain.splitlines() if ln.strip()]
    dirty_code = [ln for ln in entries if any(ln[3:].startswith(p) for p in watched)]

    detail = [f"HEAD is {head}", f"{len(entries)} uncommitted path(s) in the repository"]
    if not dirty_code:
        detail.append("none of them are under the watched code paths:")
        for p in watched:
            detail.append(f"  {p}")
        detail.append("the recorded commit describes the code that will run")
        return CheckResult(name, True, detail, blocking=False)

    detail.append(f"{len(dirty_code)} of them ARE code this run executes:")
    for ln in dirty_code[:15]:
        detail.append(f"  {ln}")
    if len(dirty_code) > 15:
        detail.append(f"  ... and {len(dirty_code) - 15} more")
    detail.append(
        f"commit {head} therefore does NOT describe what will run. The same list is "
        f"written to run_metadata.json in every group directory, so the results stay "
        f"attributable, but check that these edits are the ones you intend to measure."
    )
    detail.append("not blocking: concurrent sessions make a clean tree impractical right now.")
    return CheckResult(name, False, detail, blocking=False)


# --------------------------------------------------------------------------
# 11. scenario-isolation bypasses
# --------------------------------------------------------------------------
#: Directories scanned for isolation bypasses. `etc/` and `tests/` are excluded
#: on purpose: this gate and the test suite handle the shared scenario directory
#: deliberately, and flagging them would train the reader to ignore the check.
ISOLATION_SCAN_ROOTS = ("src",)

#: A literal containing this is a hardcoded route to the package scenario
#: directory, which no isolation mechanism can redirect.
SHARED_SCENARIO_MARKER = "src/sumo"

#: Scenario files. A literal naming one is fine when it is joined to a resolved
#: base; it is a bypass when it is handed straight to a file-opening call, where
#: it resolves against the process's working directory instead.
SCENARIO_FILE_MARKER = "generated."

#: Calls that open a path. The first positional argument of each is the one that
#: has to have been resolved against the run's own scenario directory.
PATH_OPENING_CALLS = ("open", "parse", "iterparse", "read_text", "read_bytes")


def _docstring_nodes(tree: ast.AST) -> set:
    """Every docstring Constant node, so a literal in prose is not a finding.

    Docstrings survive parsing as ordinary string constants, which is exactly the
    false-positive source that pushed the objective check off plain text search;
    a module that merely *describes* `src/sumo` must not be reported as reaching
    for it.
    """
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            out.add(id(body[0].value))
    return out


def _scan_isolation_bypasses(path: str) -> Tuple[List[str], List[str]]:
    """(blocking findings, advisory findings) for one file. Syntax tree only."""
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)
    docstrings = _docstring_nodes(tree)
    blocking: List[str] = []
    advisory: List[str] = []
    is_generator = os.path.basename(path) == "make_sumo_set.py"

    for node in ast.walk(tree):
        # (a) a hardcoded route to the package scenario directory.
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings \
                and SHARED_SCENARIO_MARKER in node.value:
            blocking.append(
                f"line {node.lineno}: literal {node.value!r} hardcodes the shared "
                f"scenario directory; no isolation can redirect it"
            )

        # (b) a scenario file handed straight to a path-opening call, i.e. resolved
        # against the working directory rather than against the run's own
        # directory. `os.path.join(base, "generated.nod.xml")` is not this and is
        # deliberately not reported.
        if isinstance(node, ast.Call):
            fname = node.func.attr if isinstance(node.func, ast.Attribute) else \
                (node.func.id if isinstance(node.func, ast.Name) else "")
            if fname in PATH_OPENING_CALLS and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str) \
                        and (SCENARIO_FILE_MARKER in first.value
                             or SHARED_SCENARIO_MARKER in first.value):
                    blocking.append(
                        f"line {node.lineno}: {fname}({first.value!r}) resolves against "
                        f"the working directory, not the run's scenario directory"
                    )

        # (c) BASE_PATH read directly. Correct under PAPER4_SUMO_DIR, wrong under
        # argument isolation; see the check's docstring for why it warns.
        if isinstance(node, ast.Attribute) and node.attr == "BASE_PATH" \
                and not is_generator:
            advisory.append(
                f"line {node.lineno}: reads make_sumo_set.BASE_PATH, the process-wide "
                f"default; a caller isolating by `sumo_dir=` argument is not honoured"
            )
    return blocking, advisory


def check_scenario_isolation_bypasses(roots: List[str]) -> CheckResult:
    """Find code that reaches the shared scenario directory around the isolation.

    Four of these have been found by hand, the most recent being `AoiV2IEnv.reset`
    parsing `"src/sumo/generated.nod.xml"` immediately after `_init_sumo` had
    resolved the real directory. Each was found only because somebody happened to
    run from the wrong working directory. Nothing guaranteed there was not a
    fifth, which is what this replaces.

    Read from the syntax tree, not from text: a plain search reports every comment
    and docstring that merely names the path, and a check whose output is mostly
    noise gets skipped. The objective check in this same file was moved off text
    search for that reason.

    Two severities, and the split is the judgement this check makes:

      * BLOCKING for a hardcoded `src/sumo` literal and for a scenario filename
        passed straight to `open`/`ET.parse`. Neither can be redirected by any
        isolation mechanism, so both are wrong under every way of running.
      * ADVISORY for reading `make_sumo_set.BASE_PATH`. That value is resolved
        from `PAPER4_SUMO_DIR` at import, so it is correct whenever isolation is
        by environment variable and wrong only when the caller isolates by passing
        `sumo_dir=`. Blocking it would condemn the legitimate majority of its uses;
        reporting it tells the reader where to look when the two disagree.
    """
    name = "no code bypasses scenario isolation"
    files: List[str] = []
    for root in roots:
        base = root if os.path.isabs(root) else os.path.join(ROOT, root)
        for dirpath, _dirnames, filenames in os.walk(base):
            if "__pycache__" in dirpath:
                continue
            files.extend(os.path.join(dirpath, f)
                         for f in filenames if f.endswith(".py"))
    if not files:
        return CheckResult(name, False, [f"no python files found under {roots}"])

    blocking: List[str] = []
    advisory: List[str] = []
    unreadable: List[str] = []
    for path in sorted(files):
        try:
            b, a = _scan_isolation_bypasses(path)
        except (OSError, SyntaxError) as exc:
            unreadable.append(f"{os.path.relpath(path, ROOT)}: "
                              f"{type(exc).__name__}: {exc}")
            continue
        rel = os.path.relpath(path, ROOT)
        blocking.extend(f"{rel}, {line}" for line in b)
        advisory.extend(f"{rel}, {line}" for line in a)

    detail = [f"scanned {len(files)} file(s) under {', '.join(roots)}"]
    if unreadable:
        detail.append(f"{len(unreadable)} file(s) could not be parsed:")
        detail.extend(f"  {u}" for u in unreadable[:5])
    if advisory:
        detail.append(f"{len(advisory)} advisory finding(s), not blocking:")
        detail.extend(f"  ~ {a}" for a in advisory[:10])
        if len(advisory) > 10:
            detail.append(f"  ~ ... and {len(advisory) - 10} more")
    if blocking:
        detail.append(f"{len(blocking)} BLOCKING finding(s):")
        detail.extend(f"  - {b}" for b in blocking[:15])
        if len(blocking) > 15:
            detail.append(f"  - ... and {len(blocking) - 15} more")
        detail.append(
            "each of these reads the shared scenario directory whatever the run was "
            "told to use, so an isolated run silently mixes two scenarios."
        )
        return CheckResult(name, False, detail, examined=len(files))

    detail.append("no hardcoded shared-scenario path and no working-directory-relative "
                  "scenario open remains")
    # The count is the number of FILES read. A wrong scan root finds nothing and
    # reports the same clean line as a correct one that found nothing.
    return CheckResult(name, True, detail, examined=len(files))


# --------------------------------------------------------------------------
# 12. HOORL two-stage wiring
# --------------------------------------------------------------------------
def check_hoorl_offline_wiring() -> CheckResult:
    """HOORL must reach its offline stage, in the search and in training alike.

    Checked by CONSTRUCTING a model through the wiring helper and reading the
    attribute back, not by looking for the word in the source. HOORL spent this
    whole project's history running its online half only while every piece of the
    offline half was present and correct, and a source-level check would have been
    satisfied by exactly that state.

    The second half of the check is that both call sites reach the helper. A
    search that skips pretraining while training performs it tunes against a
    different method than the one that runs, which this project has already paid
    for twice.
    """
    name = "HOORL reaches its offline stage"
    detail: List[str] = []
    try:
        from src.baselines import get_baseline
        from src.hoorl_wiring import (
            DEFAULT_OFFLINE_ALGORITHM, is_hoorl, offline_hparams,
        )
        from src.rl_interface import STATE_DIM
    except ImportError as exc:
        return CheckResult(name, False, [f"could not import the wiring: "
                                         f"{type(exc).__name__}: {exc}"])

    HOORL = get_baseline("HOORL")
    hp = offline_hparams(HOORL, {"hidden_dim": 64})
    try:
        model = HOORL(state_dim=STATE_DIM, num_channels=4, **hp)
    except Exception as exc:  # noqa: BLE001 - any failure here stops the launch
        return CheckResult(name, False, [
            f"constructing HOORL through the wiring raised "
            f"{type(exc).__name__}: {exc}"])

    got = getattr(model, "offline_algorithm", None)
    ok_model = is_hoorl(model) and got == DEFAULT_OFFLINE_ALGORITHM
    detail.append(f"a model built through offline_hparams reports "
                  f"offline_algorithm={got!r} (want {DEFAULT_OFFLINE_ALGORITHM!r})")

    # Both construction sites must route through the helper. Read from the syntax
    # tree so a mention in a comment does not satisfy it.
    sites = {
        "src/hpo.py": False,
        "src/hot_swap_trainer.py": False,
    }
    for rel in list(sites):
        path = os.path.join(ROOT, rel)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
        except (OSError, SyntaxError) as exc:
            detail.append(f"{rel}: could not parse ({type(exc).__name__}: {exc})")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith(
                    "hoorl_wiring"):
                sites[rel] = True
            elif isinstance(node, ast.Import) and any(
                    a.name.endswith("hoorl_wiring") for a in node.names):
                sites[rel] = True

    for rel, wired in sites.items():
        detail.append(f"{rel}: {'imports' if wired else 'DOES NOT import'} "
                      f"src.hoorl_wiring")

    unwired = [rel for rel, wired in sites.items() if not wired]
    if not ok_model:
        detail.append("the wiring helper did not put the offline learner on the model.")
        return CheckResult(name, False, detail)
    if unwired:
        detail.append(
            "HOORL would construct correctly but never enter its offline stage from "
            f"{', '.join(unwired)}, so it would run as the online-only ablation while "
            "being reported under the method's name."
        )
        return CheckResult(name, False, detail)

    detail.append("both the search and the training path route model construction "
                  "through the wiring")
    return CheckResult(name, True, detail)


# --------------------------------------------------------------------------
# 16. state dimension: code and data must agree
# --------------------------------------------------------------------------
def check_state_dim_agrees(dataset_path: str) -> CheckResult:
    """`STATE_DIM`, the width of the stored states, and the width the file
    declares are three separate facts that have to be one number.

    They came apart on 2026-09-06 when the observation went from 17 to 21: the
    code changed first and the collection on disk was still 17 wide. Nothing
    refuses that combination on its own -- an offline learner constructed at 21
    reading 17-wide rows fails somewhere inside a matrix multiply, hours in and
    with a message about shapes rather than about provenance.
    """
    name = "state dimension agrees across code and dataset"
    try:
        from src.hoorl_offline import OfflineDataset
        from src.rl_interface import STATE_DIM
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import: {type(exc).__name__}: {exc}"])
    if not os.path.exists(dataset_path):
        return CheckResult(name, False, [f"{dataset_path} does not exist"])

    try:
        ds = OfflineDataset.load(dataset_path)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"reading the dataset raised {type(exc).__name__}: {exc}"])

    stored = int(ds.arrays["state"].shape[1])
    declared = int(ds.metadata.get("contents_manifest", {}).get("state_dim", -1))
    next_stored = int(ds.arrays["next_state"].shape[1])
    values = {"src.rl_interface.STATE_DIM": int(STATE_DIM),
              "dataset state array": stored,
              "dataset next_state array": next_stored,
              "dataset contents_manifest": declared}
    ok = len(set(values.values())) == 1
    detail = [f"{k}: {v}" for k, v in values.items()]
    if not ok:
        detail.append("these must be one number. Recollect, or point --dataset at "
                      "a collection made under the current observation.")
    return CheckResult(name, ok, detail, examined=len(values))


# --------------------------------------------------------------------------
# 17. the contents manifest is derived, not declared
# --------------------------------------------------------------------------
def check_contents_manifest_is_derived() -> CheckResult:
    """The manifest must be computed from the arrays present, not written beside
    them.

    Asserted by CALLING it with a column removed and requiring the answer to
    change. Reading the source instead would accept a future edit that restores a
    declared manifest while leaving the derivation in a comment, and a declared
    manifest is exactly the failure this project already has on file: a collection
    carrying `format_version: 2` for a change that was two thirds unimplemented.
    A manifest that cannot be wrong about its own file is the only defence, since
    every downstream consumer trusts it to decide whether raw columns exist.
    """
    name = "contents manifest is derived from the arrays"
    try:
        from src.hoorl_offline import contents_manifest
        from src.rl_interface import STATE_DIM
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import: {type(exc).__name__}: {exc}"])

    import numpy as _np
    dummy = _np.zeros((1, 1), dtype=_np.float32)
    full = {"state_raw": dummy, "next_state_raw": dummy,
            "action_raw": dummy, "cell_index": dummy}
    probes = [
        ("state_raw", "has_raw_columns", True),
        ("action_raw", "raw_action_fields", True),
        ("cell_index", "has_cell_index", True),
    ]
    detail: List[str] = []
    bad: List[str] = []
    base = contents_manifest(dict(full), STATE_DIM)
    for column, key, _ in probes:
        without = {k: v for k, v in full.items() if k != column}
        got = contents_manifest(without, STATE_DIM)
        changed = bool(base.get(key)) and not bool(got.get(key))
        detail.append(f"removing {column!r} -> {key} "
                      f"{bool(base.get(key))} becomes {bool(got.get(key))}"
                      f"{'' if changed else '   NOT DERIVED'}")
        if not changed:
            bad.append(column)
    if bad:
        detail.append(f"the manifest did not react to {', '.join(bad)}, so it is "
                      "describing something other than the file it belongs to.")
    return CheckResult(name, not bad, detail, examined=len(probes))


# --------------------------------------------------------------------------
# 18. one road-seed function for all four paths
# --------------------------------------------------------------------------
#: Every module that decides which road network it runs on, and what it must be
#: getting that decision from. Training, evaluation, the search and the offline
#: collection each pick a road; a fifth path that grows its own arithmetic
#: reintroduces the fault this map exists to close.
ROAD_SEED_CALLERS = ("src/hot_swap_trainer.py", "src/evaluate.py",
                     "src/hpo.py", "src/hoorl_offline.py")
ROAD_SEED_SOURCE = "make_sumo_set"
ROAD_SEED_NAMES = ("road_seed", "seed_road_network")


def check_road_seed_single_source() -> CheckResult:
    """All four paths must take the road from `make_sumo_set`, and none may
    define its own.

    Until 2026-09-06 the road was a function of the generator's internal state
    rather than of the request, so which network a density ran on depended on how
    many networks had been generated before it in the same process. Fixing it
    meant one function of (density, cycle), and the value of that is entirely in
    its being the ONLY one: a second implementation anywhere makes two paths
    disagree about which road they are comparing on, which is invisible in every
    result file because both record a plausible seed.
    """
    name = "one road_seed function for all four paths"
    detail: List[str] = []
    bad: List[str] = []
    for rel in ROAD_SEED_CALLERS:
        path = os.path.join(ROOT, rel)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
        except (OSError, SyntaxError) as exc:
            detail.append(f"{rel}: could not parse ({type(exc).__name__}: {exc})")
            bad.append(rel)
            continue

        imports_it = False
        defines_it: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and ROAD_SEED_SOURCE in (node.module or ""):
                imports_it = True
            elif isinstance(node, ast.Import) and any(
                    ROAD_SEED_SOURCE in a.name for a in node.names):
                imports_it = True
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                    node.name in ROAD_SEED_NAMES:
                defines_it.append(node.name)

        uses = [n for n in ROAD_SEED_NAMES
                if any(isinstance(x, ast.Name) and x.id == n for x in ast.walk(tree))
                or any(isinstance(x, ast.Attribute) and x.attr == n
                       for x in ast.walk(tree))]
        ok = imports_it and uses and not defines_it
        detail.append(
            f"{rel}: imports {ROAD_SEED_SOURCE}={imports_it}, "
            f"uses {uses or 'NOTHING'}"
            f"{', DEFINES ITS OWN ' + ', '.join(defines_it) if defines_it else ''}")
        if not ok:
            bad.append(rel)

    if bad:
        detail.append(f"{', '.join(bad)} do not take the road network from the "
                      "shared function, so two paths can silently compare on "
                      "different roads.")
    return CheckResult(name, not bad, detail, examined=len(ROAD_SEED_CALLERS))


# --------------------------------------------------------------------------
# 19. validation, evaluation and training roads are disjoint
# --------------------------------------------------------------------------
def check_road_cycles_disjoint() -> CheckResult:
    """The road that selects `_best.pt` must be one no training episode ran on,
    and not the one the final score is reported on either.

    This was missing when the road became deterministic: training and evaluation
    were fixed and validation was left drawing whatever network the generator
    happened to be on, so `_best.pt` could be selected at the moment the policy
    met the easiest road. Overlap with evaluation is the opposite fault -- picking
    the checkpoint on the set it is scored on -- and both are one integer away at
    all times.
    """
    name = "training, validation and evaluation roads are disjoint"
    try:
        from src.evaluate import EVAL_ROAD_CYCLE
        from src.hot_swap_trainer import VALIDATION_ROAD_CYCLE
        from src.hpo import HPO_ROAD_CYCLE
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import: {type(exc).__name__}: {exc}"])

    training = set(range(0, 15))
    named = {"training": training,
             "search (HPO_ROAD_CYCLE)": {int(HPO_ROAD_CYCLE)},
             "evaluation (EVAL_ROAD_CYCLE)": {int(EVAL_ROAD_CYCLE)},
             "validation (VALIDATION_ROAD_CYCLE)": {int(VALIDATION_ROAD_CYCLE)}}
    detail = [f"{k}: {sorted(v) if len(v) < 6 else str(min(v)) + '..' + str(max(v))}"
              for k, v in named.items()]

    faults: List[str] = []
    if int(VALIDATION_ROAD_CYCLE) in training:
        faults.append("validation runs on a road training also uses, so `_best.pt` "
                      "is selected on a memorised network")
    if int(EVAL_ROAD_CYCLE) in training:
        faults.append("evaluation runs on a training road, so the reported score "
                      "is not held out")
    if int(VALIDATION_ROAD_CYCLE) == int(EVAL_ROAD_CYCLE):
        faults.append("validation and evaluation share a road, so the checkpoint "
                      "is chosen on the set it is scored on")
    # The search is EXPECTED to sit inside the training range: it tunes for the
    # conditions training runs under. Stated so its overlap is not read as a fault.
    detail.append("the search shares cycle 0 with training on purpose: it tunes "
                  "for the conditions training will meet")
    detail.extend(faults)
    return CheckResult(name, not faults, detail, examined=len(named))


# --------------------------------------------------------------------------
# 20. a renormalised dataset says so, in the run record
# --------------------------------------------------------------------------
def check_reconciliation_is_recorded() -> CheckResult:
    """If the loader renormalises a collection to today's constants, the run has
    to be able to say so afterwards.

    Renormalisation is the mechanism that let three bounds move without
    recollecting, and it is silent by construction: the arrays simply arrive
    carrying different numbers than the file holds. That is the intended
    behaviour and it is also the exact shape of an unattributable result, because
    a report written six weeks later cannot recover which constants the offline
    stage actually trained under. The report attribute is what closes it.
    """
    name = "renormalisation is recorded on the loaded dataset"
    try:
        from src.hoorl_wiring import load_offline_dataset
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import: {type(exc).__name__}: {exc}"])

    src_path = os.path.join(ROOT, "src", "hoorl_wiring.py")
    try:
        with open(src_path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=src_path)
    except (OSError, SyntaxError) as exc:
        return CheckResult(name, False,
                           [f"could not parse hoorl_wiring: "
                            f"{type(exc).__name__}: {exc}"])

    fn = next((n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == "load_offline_dataset"), None)
    if fn is None:
        return CheckResult(name, False, ["load_offline_dataset is gone"])

    calls = {c.func.attr for c in ast.walk(fn)
             if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)}
    assigned = {t.attr for n in ast.walk(fn) if isinstance(n, ast.Assign)
                for t in n.targets if isinstance(t, ast.Attribute)}
    wanted = {
        "reconciles before verifying": "reconcile_to_current_constants" in calls,
        "records the report on the dataset": "reconciliation_report" in assigned,
    }
    detail = [f"{k}: {v}" for k, v in wanted.items()]
    ok = all(wanted.values())
    if not ok:
        detail.append("a run could then train on renormalised data with nothing in "
                      "any artefact saying which constants it used.")
    return CheckResult(name, ok, detail, examined=len(wanted))


# --------------------------------------------------------------------------
# 21. the contributions are switched on in the path that runs
# --------------------------------------------------------------------------
#: Flags known to read 0 for a reason that is recorded and accepted. A flag here
#: is NOT excused from being present -- it must still appear on every update -- it
#: is excused from having fired.
#:
#: MA2HDQN's `n_step_active`: the n-step return is not plumbed. The blocker is
#: that a buffer item carries no vehicle, episode or sequence identifier, so the
#: chain a return needs cannot be reconstructed. It is deferred past HPO by
#: decision, and the model is searched and reported as the one-step variant. The
#: flag reading 0 is therefore the truth rather than a fault, and the entry is
#: here so that the day it starts reading 1 somebody notices.
KNOWN_INACTIVE_FLAGS: Dict[str, Tuple[str, ...]] = {"MA2HDQN": ("n_step_active",)}

#: How long a probe rollout runs. Long enough that the replay buffer fills past
#: the 16 closed SMDP intervals the first update needs and several updates
#: happen; short enough that the gate stays a gate.
WIRING_PROBE_STEPS: int = 60

#: Attributes holding "fire once every N updates". Clamped on the probe model so
#: a periodic flag has several chances inside a short rollout. Read the check's
#: docstring for why this is not cheating: the question is whether the mechanism
#: is reachable, not whether N is well chosen.
PROBE_PERIOD_ATTRS: Tuple[str, ...] = (
    "target_sync_interval", "target_update_freq", "policy_sync_interval",
    "target_update_interval", "policy_delay",
)
PROBE_PERIOD_VALUE: int = 5


@contextlib.contextmanager
def _scratch_scenario(density: float, n_steps: int):
    """Generate the probe's scenario somewhere it cannot damage anything.

    ANY CHECK THAT PREPARES A SCENARIO HAS TO DO THIS. `make_sumo_set.BASE_PATH`
    is bound at import from PAPER4_SUMO_DIR, which the gate runs without, so it
    points at the SHARED `coder/src/sumo`. A check that calls `prepare_scenario`
    therefore overwrites the shared scenario with one sized for its own probe --
    and since a probe is short, the horizon it writes is short, which is the
    exact state `check_scenario_horizon` refuses.

    This has now happened twice with two different checks. The first was
    `check_hpo_prepares_scenario_before_models`, whose ten-step trial left a
    131 s scenario; the second was the wiring probe added on 2026-09-07, whose
    sixty steps left 136 s. Both passed on a clean tree and failed on the next
    run, on damage they had done themselves. Running the gate twice in a row is
    what makes that visible, and it is now part of the pre-launch procedure.
    """
    import src.sumo.make_sumo_set as ss
    from src.hot_swap_trainer import prepare_scenario
    from src.hpo import HPO_ROAD_CYCLE, _rollout_scenario_spec

    scratch = tempfile.mkdtemp(prefix="preflight_probe_")
    previous_base = ss.BASE_PATH
    previous_env = os.environ.get("PAPER4_SUMO_DIR")
    ss.BASE_PATH = scratch
    os.environ["PAPER4_SUMO_DIR"] = scratch
    try:
        spec = _rollout_scenario_spec(density=density, n_steps=n_steps)
        prepare_scenario(density=spec["density"], max_steps=spec["max_steps"],
                         warmup_steps=spec["warmup_steps"],
                         seed=ss.seed_road_network(spec["density"], HPO_ROAD_CYCLE))
        yield spec
    finally:
        ss.BASE_PATH = previous_base
        if previous_env is None:
            os.environ.pop("PAPER4_SUMO_DIR", None)
        else:
            os.environ["PAPER4_SUMO_DIR"] = previous_env
        shutil.rmtree(scratch, ignore_errors=True)


def check_wiring_flags_are_live(density: float = 25.0) -> CheckResult:
    """Every declared contribution must actually fire in a real rollout.

    WHY THE DECLARATION IS NOT THE CHECK. Reading `WIRING_FLAG_KEYS` proves a
    model says it has a mechanism. It cannot distinguish a mechanism that runs
    from one that is present, correct and unreachable, and that distinction is
    the one this project keeps paying for: MADDPG-MT's four value heads trained
    on copies of one another for weeks because the per-term rewards never arrived,
    its global critic pooled a zero context for the same reason, and
    `constants_safe_to_rescale` sat complete with no caller at all. A flag stuck
    at 0 through a twelve-hour search means the model being reported under a
    method's name is that method's ablation.

    WHY A ROLLOUT AND NOT A SYNTHETIC BATCH. Several flags cannot rise on a
    hand-built dict: `per_sampled` needs priority weights and `neighbourhood_used`
    needs a concurrent population, both of which come from
    `RetrospectiveReplayBuffer`. `results/diagnostics/verify_wiring_flags.py`
    reaches exactly that limit and reports those keys as `needs_real_buffer`. So
    this drives `evaluate_model_in_env`, which is the function the search itself
    calls, and reads the flags out of the update dicts it produces.

    THE TEST IS "FIRED AT LEAST ONCE", not "averaged 1.0". Some flags are periodic
    by design -- `target_synced` fires once every N updates -- and requiring 1.0
    would fail them for behaving correctly. A mean above zero separates the two
    cases the gate is for: plumbed and running, against plumbed and never reached.

    AND THE PROBE SHORTENS THOSE PERIODS SO THEY CAN FIRE. A sixty-step rollout
    makes about a hundred updates, while MA2HDQN syncs its target every 200 and
    SPAM-D3QN every 1000, so a correct model reports 0 for the whole probe. The
    first version of this check duly failed MA2HDQN for it -- the check demanded
    something it had not given the model a chance to do, which is the same fault
    as measuring a bound against a stale band. `PROBE_PERIOD_ATTRS` are clamped
    after construction so each periodic mechanism gets several chances inside the
    window. That tests THE PLUMBING, which is what a launch gate can establish;
    it says nothing about whether the tuned period is right, and it is not meant
    to.
    """
    name = "declared contributions fire in a real rollout"
    try:
        from src.baselines import ALL_BASELINES, get_baseline
        from src.hoorl_wiring import offline_hparams, pretrain_hoorl
        from src.hpo import (DEFAULT_PRETRAIN_BATCH_SIZE, DEFAULT_PRETRAIN_UPDATES,
                             evaluate_model_in_env)
        from src.rl_interface import STATE_DIM
        import src.Communications as comm
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not import: {type(exc).__name__}: {exc}"])

    detail: List[str] = []
    faults: List[str] = []
    examined = 0
    try:
        scenario = _scratch_scenario(density, WIRING_PROBE_STEPS)
        scenario.__enter__()
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not prepare the probe scenario: "
                            f"{type(exc).__name__}: {exc}"])
    try:
        for model_name in sorted(ALL_BASELINES):
            cls = get_baseline(model_name)
            declared = tuple(getattr(cls, "WIRING_FLAG_KEYS", ()) or ())
            if not declared:
                detail.append(f"{model_name:14s} declares no contribution flags")
                continue
            examined += len(declared)

            sums: Dict[str, float] = {k: 0.0 for k in declared}
            counts: Dict[str, int] = {k: 0 for k in declared}
            try:
                model = cls(state_dim=STATE_DIM, num_channels=comm.NUM_SUBCHANNELS,
                            **offline_hparams(cls, {"hidden_dim": 64}))
                offline_summary = pretrain_hoorl(
                    model, num_updates=min(50, DEFAULT_PRETRAIN_UPDATES),
                    batch_size=DEFAULT_PRETRAIN_BATCH_SIZE,
                    require_offline=True) or {}
                shortened: List[str] = []
                for attr in PROBE_PERIOD_ATTRS:
                    current = getattr(model, attr, None)
                    if isinstance(current, int) and current > PROBE_PERIOD_VALUE:
                        setattr(model, attr, PROBE_PERIOD_VALUE)
                        shortened.append(f"{attr} {current}->{PROBE_PERIOD_VALUE}")

                original_update = model.update

                def recording_update(batch, _orig=original_update, _s=sums, _c=counts):
                    out = _orig(batch)
                    for key in list(_s):
                        if key in out:
                            _s[key] += float(out[key])
                            _c[key] += 1
                    return out

                model.update = recording_update  # type: ignore[method-assign]
                evaluate_model_in_env(model=model, seed=42,
                                      n_steps=WIRING_PROBE_STEPS, density=density,
                                      train_steps_during_rollout=2,
                                      check_divergence=False)
            except Exception as exc:  # noqa: BLE001
                detail.append(f"{model_name:14s} probe raised {type(exc).__name__}: {exc}")
                faults.append(f"{model_name} (probe failed)")
                continue

            # REACHING the offline stage is not the same as RUNNING it. A model
            # that pretrained for zero updates satisfies every flag above and has
            # done nothing, and this project keeps HOORL's offline stage on the
            # grounds of reproduction fidelity, so "it ran" has to be a number.
            if offline_summary.get("offline_stage_ran"):
                n_updates = float(offline_summary.get("offline_updates", 0.0))
                detail.append(f"{model_name:14s} offline stage: {n_updates:.0f} "
                              f"update(s) over "
                              f"{offline_summary.get('n_transitions')} transitions")
                if n_updates <= 0.0:
                    faults.append(f"{model_name} reached its offline stage and "
                                  "performed 0 updates")

            excused = set(KNOWN_INACTIVE_FLAGS.get(model_name, ()))
            parts: List[str] = []
            for key in declared:
                seen = counts[key]
                mean = (sums[key] / seen) if seen else None
                # A flag belonging to the OFFLINE stage cannot fire in the online
                # updates and must not be judged there. HOORL's `phase_offline` says
                # which stage an update was part of, so 0 through the rollout is the
                # correct reading and the evidence that it works lives in the offline
                # summary, which reports its last value as `final_<key>`. Read there
                # too rather than excusing the key: the flag still has to be shown
                # reaching 1 somewhere, just not here.
                offline_value = offline_summary.get(f"final_{key}")
                if mean == 0.0 and offline_value is not None and float(offline_value) > 0:
                    parts.append(f"{key}={mean:.3f} online, "
                                 f"{float(offline_value):.3f} in the offline stage")
                    continue
                if seen == 0:
                    parts.append(f"{key}=ABSENT")
                    faults.append(f"{model_name}.{key} never appeared in an update")
                elif mean == 0.0 and key not in excused:
                    parts.append(f"{key}=0.000 NEVER FIRED")
                    faults.append(f"{model_name}.{key} stayed at 0")
                elif mean == 0.0:
                    parts.append(f"{key}=0.000 (known inactive)")
                else:
                    parts.append(f"{key}={mean:.3f}")
            if shortened:
                parts.append(f"[probe periods: {', '.join(shortened)}]")
            detail.append(f"{model_name:14s} {'  '.join(parts)}")

    finally:
        scenario.__exit__(None, None, None)

    if faults:
        detail.append(
            "a contribution that never fires makes the run report a method's "
            "ablation under that method's name, and twelve hours of search would "
            "rank the nine on mechanisms two of them were not using: "
            + "; ".join(faults))
    return CheckResult(name, not faults, detail, examined=examined)


# --------------------------------------------------------------------------
# 22 and 23. the reward and the error accounting a rollout will actually use
# --------------------------------------------------------------------------
@contextlib.contextmanager
def _probe_environment(density: float = 25.0):
    """The environment object a search rollout builds, for reading back.

    Built inside `_scratch_scenario` for the reason given there: constructing an
    environment can regenerate the scenario under it, and the directory it would
    regenerate is the shared one.
    """
    from src.hot_swap_trainer import AoiV2IEnv

    with _scratch_scenario(density, WIRING_PROBE_STEPS) as spec:
        env = AoiV2IEnv(density=spec["density"], seed=42,
                        max_steps=spec["max_steps"],
                        warmup_steps=spec["warmup_steps"])
        try:
            yield env
        finally:
            try:
                env.close()
            except Exception:  # noqa: BLE001
                pass


def check_reward_weights() -> CheckResult:
    """w1..w4 must be the shared defaults before the run starts, not during it.

    `AoiV2IEnv` already refuses a reward it cannot rederive from its own weights,
    and that assertion is the right last line of defence. It is the wrong FIRST
    one: it fires mid-rollout, so it converts a wrong weight into eleven hours of
    discarded computation instead of a refusal at second zero. The weights also
    have to be identical across the nine or the comparison is between models
    optimised for different objectives, which no per-run assertion can see.
    """
    name = "reward weights are the shared defaults"
    detail: List[str] = []
    bad: List[str] = []
    try:
        from src.hot_swap_trainer import DEFAULT_REWARD_WEIGHTS, REWARD_WEIGHT_KEYS
        with _probe_environment() as env:
            for key in REWARD_WEIGHT_KEYS:
                want = float(DEFAULT_REWARD_WEIGHTS[key])
                got = float(getattr(env, key))
                ok = abs(got - want) < 1e-12
                detail.append(
                    f"{key} = {got}  (default {want}){'' if ok else '   DIFFERS'}")
                if not ok:
                    bad.append(key)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not build the probe environment: "
                            f"{type(exc).__name__}: {exc}"])

    total = sum(float(DEFAULT_REWARD_WEIGHTS[k]) for k in REWARD_WEIGHT_KEYS)
    detail.append(f"they sum to {total:.6f}")
    if abs(total - 1.0) > 1e-9:
        bad.append("sum")
        detail.append("the four weights no longer sum to 1, so the reward's scale "
                      "has moved and scores are not comparable with earlier runs.")
    return CheckResult(name, not bad, detail, examined=len(REWARD_WEIGHT_KEYS))


def check_error_mode() -> CheckResult:
    """The rollout must accumulate estimation error, not average it.

    `src/hpo.py` names `error_mode` nowhere: a rollout takes whatever
    `AoiV2IEnv`'s default is. That is correct today and it is correct by
    coincidence, since nothing connects the search to the decision. The `mean`
    arm was retired because averaging over an interval hides exactly the growth
    the AoI reward is about, and a run under it would produce plausible numbers
    that answer a different question.
    """
    name = "estimation error is accumulated, not averaged"
    try:
        from src.hot_swap_trainer import DEFAULT_ERROR_MODE, ERROR_MODE_ACCUMULATE
        with _probe_environment() as env:
            got = str(getattr(env, "error_mode", ""))
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False,
                           [f"could not build the probe environment: "
                            f"{type(exc).__name__}: {exc}"])

    detail = [
        f"the environment a rollout builds reports error_mode={got!r}",
        f"module default DEFAULT_ERROR_MODE={DEFAULT_ERROR_MODE!r}",
        "src/hpo.py passes no error_mode, so the default is what a trial gets",
    ]
    ok = got == ERROR_MODE_ACCUMULATE == DEFAULT_ERROR_MODE
    if not ok:
        detail.append("the retired `mean` arm averages the error over an interval, "
                      "which hides the growth the AoI reward exists to penalise.")
    return CheckResult(name, ok, detail, examined=1)


# --------------------------------------------------------------------------
def run_checks(args: argparse.Namespace) -> Tuple[List[CheckResult], bool]:
    checks: List[Callable[[], CheckResult]] = [
        lambda: check_normalisation_clipping(args.dataset),
        check_n_active_max_obs,
        lambda: check_state_dim_agrees(args.dataset),
        check_contents_manifest_is_derived,
        check_road_seed_single_source,
        check_road_cycles_disjoint,
        check_reconciliation_is_recorded,
        check_objective_reads_packet_loss,
        lambda: check_gamma_range(args.hpo_path, UNRESOLVED_GAMMA_HI, RSU_DWELL_S),
        lambda: check_model_coverage(args.group_models),
        lambda: check_search_space_reaches_every_group_model(args.group_models),
        check_hpo_prepares_scenario_before_models,
        # The shared directory is always checked, whatever this run points at:
        # anything that does not set PAPER4_SUMO_DIR falls back to it, and that is
        # how it came to hold a 131 s scenario in the first place.
        lambda: check_scenario_horizon(
            [os.path.join(ROOT, "src", "sumo")] + list(args.sumo_dirs)),
        lambda: check_scenario_outside_worktree(args.sumo_dirs),
        lambda: check_sumo_isolation(args.sumo_dirs),
        lambda: check_gpus(args.gpus),
        lambda: check_destination(args.output_root, "output root", args.protect),
        lambda: check_destination(args.log_root, "log root", args.protect),
        lambda: check_scenario_isolation_bypasses(list(args.isolation_scan_roots)),
        check_hoorl_offline_wiring,
        check_wiring_flags_are_live,
        check_reward_weights,
        check_error_mode,
        lambda: check_working_tree(args.watch_paths),
    ]
    results = [c() for c in checks]
    return results, not any(r.stops_launch for r in results)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", required=True, help="where the group result directories will be written")
    ap.add_argument("--log-root", required=True, help="where the per-group launcher logs will be written")
    ap.add_argument("--sumo-dirs", nargs="*", default=[],
                    help="the PAPER4_SUMO_DIR each group will be given")
    ap.add_argument("--gpus", nargs="*", type=int, default=[0, 1, 2, 3],
                    help="GPU indices the run will occupy")
    ap.add_argument("--protect", nargs="*",
                    default=["/home/imnyj/Workspace/paper4/coder/results/hpo_parallel",
                             "/home/imnyj/Workspace/paper4/coder/results/hpo"],
                    help="directories that must never be written into")
    ap.add_argument("--group-models", nargs="*", default=[],
                    help="one space-separated model list per group, as the launcher will pass them")
    ap.add_argument("--hpo-path", default=os.path.join(ROOT, "src", "hpo.py"),
                    help="the file whose gamma search range is checked")
    ap.add_argument("--watch-paths", nargs="*", default=list(WATCHED_CODE_PATHS),
                    help="repo-relative prefixes whose uncommitted state is reported")
    ap.add_argument("--isolation-scan-roots", nargs="*", default=list(ISOLATION_SCAN_ROOTS),
                    help="directories scanned for scenario-isolation bypasses; "
                         "etc/ and tests/ are excluded on purpose")
    ap.add_argument("--dataset", default=DEFAULT_OFFLINE_DATASET,
                    help="the offline collection whose normalisation is measured")
    ap.add_argument("--skip", nargs="*", default=[],
                    help="check names to report but not enforce (substring match)")
    args = ap.parse_args()

    results, _ = run_checks(args)

    print("=" * 78)
    print("HPO pre-flight")
    print("=" * 78)
    failed: List[CheckResult] = []
    warned: List[CheckResult] = []
    for r in results:
        skipped = any(s.lower() in r.name.lower() for s in args.skip)
        if skipped and not r.passed:
            print(r.render().replace("[FAIL]", "[WARN]", 1))
            print("       not enforced (--skip)")
            warned.append(r)
        else:
            print(r.render())
            if r.stops_launch:
                failed.append(r)
            elif not r.passed:
                warned.append(r)
        print()

    print("-" * 78)
    counted = [r for r in results if r.examined is not None]
    print(f"{len(results)} checks ran; {len(counted)} of them report a count, "
          f"{sum(r.examined for r in counted)} items examined between them. "
          f"A check reporting 0 fails: see CheckResult.")
    if warned:
        print(f"{len(warned)} warning(s), which do not stop the launch:")
        for r in warned:
            print(f"  ~ {r.name}")
    if failed:
        print(f"BLOCKED: {len(failed)} of {len(results)} checks failed. Do not launch.")
        for r in failed:
            print(f"  - {r.name}")
        print("-" * 78)
        return 1

    print(f"CLEAR: {len(results) - len(warned)} of {len(results)} checks passed"
          f"{', the rest are warnings' if warned else ''}. Safe to launch.")
    print("-" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
