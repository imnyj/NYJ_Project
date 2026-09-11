#!/usr/bin/env python3
"""Prove that each pre-flight check fails when its own condition is violated.

A gate reports PASS on a healthy tree whether or not it is looking at anything.
The only way to know `etc/preflight_hpo.py` would have stopped the nine-hour run
is to break each condition on purpose and watch the corresponding check turn red.
Every case below reproduces a specific accident:

  * the observation ceiling back at 100.0 (the saturated contention feature),
  * an objective that ignores packet loss (the constant term),
  * an objective whose arithmetic moved into a helper (must still PASS -- a
    refactor is not a regression, and this one really happened on 2026-09-05),
  * the undecided discount bound 0.999 still in place,
  * a discount bound changed at some sites and not others (the partial edit),
  * two groups sharing one SUMO directory (the network one group did not ask for),
  * a group directory nested in another (they would share a generation lock),
  * a GPU that is not free,
  * a destination holding results, and the protected control directory itself,
  * a dirty working tree, which must report without stopping the launch.

Writes `etc/verification/preflight_hpo_verification.csv`. Exit 0 only if every
case behaves as expected, in both directions.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import types
from typing import List, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "etc"))

import preflight_hpo as pf  # noqa: E402

CONTROL_DIR = os.path.join(ROOT, "results", "hpo_parallel")
OUT_CSV = os.path.join(ROOT, "etc", "verification", "preflight_hpo_verification.csv")

Row = Tuple[str, str, bool, bool, str]  # check, scenario, expected_pass, got_pass, note


def _broken_objective_module() -> types.ModuleType:
    """A src.hpo stand-in whose objective never looks at the loss term.

    Defined in a real file because the check reads the function's source; a lambda
    or an exec'd string would defeat `inspect.getsource` and make the check fail
    for the wrong reason.
    """
    tmp = tempfile.mkdtemp(prefix="verify_pf_obj_")
    path = os.path.join(tmp, "fake_hpo.py")
    with open(path, "w") as fh:
        fh.write(
            "def compute_composite_objective(metrics, **kw):\n"
            "    '''Scores three terms and pretends the fourth is a constant.'''\n"
            "    return (1.0 * metrics.get('mean_error', 0.0)\n"
            "            + 0.5 * metrics.get('mean_aoi', 0.0)\n"
            "            + 2.0 * 0.05\n"
            "            + 0.2 * metrics.get('avg_power_norm', 0.5))\n"
        )
    sys.path.insert(0, tmp)
    import fake_hpo  # noqa: PLC0415
    return fake_hpo


def _delegating_objective_module() -> types.ModuleType:
    """A src.hpo stand-in whose entry function delegates the arithmetic.

    This is the shape `src/hpo.py` actually took on 2026-09-05, when the sum moved
    into `composite_objective_terms`. A reader that stops at the entry function
    calls this a regression; it is not one, and the check must say so.
    """
    tmp = tempfile.mkdtemp(prefix="verify_pf_delegate_")
    path = os.path.join(tmp, "delegating_hpo.py")
    with open(path, "w") as fh:
        fh.write(
            "def composite_objective_terms(metrics, **kw):\n"
            "    return {'error': 1.0 * metrics.get('mean_error', 0.0),\n"
            "            'aoi': 0.5 * metrics.get('mean_aoi', 0.0),\n"
            "            'loss': 2.0 * metrics.get('packet_loss_rate', 0.0),\n"
            "            'power': 0.2 * metrics.get('avg_power_norm', 0.5)}\n"
            "\n"
            "def compute_composite_objective(metrics, **kw):\n"
            "    '''Sums the terms; mentions packet_loss_rate only in prose.'''\n"
            "    return float(sum(composite_objective_terms(metrics, **kw).values()))\n"
        )
    sys.path.insert(0, tmp)
    import delegating_hpo  # noqa: PLC0415
    return delegating_hpo


def _alias_objective_module() -> types.ModuleType:
    """A src.hpo stand-in that falls back onto the constant-carrying alias."""
    tmp = tempfile.mkdtemp(prefix="verify_pf_alias_")
    path = os.path.join(tmp, "alias_hpo.py")
    with open(path, "w") as fh:
        fh.write(
            "def compute_composite_objective(metrics, **kw):\n"
            "    loss = metrics.get('packet_loss_rate', metrics.get('outage_rate', 0.0))\n"
            "    return (1.0 * metrics.get('mean_error', 0.0)\n"
            "            + 0.5 * metrics.get('mean_aoi', 0.0)\n"
            "            + 2.0 * loss\n"
            "            + 0.2 * metrics.get('avg_power_norm', 0.5))\n"
        )
    sys.path.insert(0, tmp)
    import alias_hpo  # noqa: PLC0415
    return alias_hpo


def _launcher_groups() -> List[str]:
    """The GROUP_MODELS array out of `etc/run_hpo_parallel.sh`.

    Parsed rather than imported because the launcher is shell. The parse is
    deliberately strict: if the array cannot be found the function raises instead
    of returning an empty list, since an empty list makes the coverage check pass
    by having nothing to disagree with.
    """
    path = os.path.join(ROOT, "etc", "run_hpo_parallel.sh")
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    start = text.index("GROUP_MODELS=(")
    body = text[start + len("GROUP_MODELS=("):]
    body = body[:body.index(")")]
    groups = [line.strip().strip('"') for line in body.splitlines() if line.strip()]
    if not groups:
        raise RuntimeError(f"GROUP_MODELS in {path} parsed to nothing")
    return groups


def run() -> List[Row]:
    rows: List[Row] = []

    # ---- 1. observation normaliser -------------------------------------
    import src.rl_interface as rli
    rows.append(("N_ACTIVE_MAX_OBS", "as shipped", True,
                 pf.check_n_active_max_obs().passed, "healthy tree"))

    original = rli.N_ACTIVE_MAX_OBS
    try:
        rli.N_ACTIVE_MAX_OBS = 100.0
        res = pf.check_n_active_max_obs()
        rows.append(("N_ACTIVE_MAX_OBS", "ceiling forced back to 100.0", False,
                     res.passed, "the saturated-contention regression"))
    finally:
        rli.N_ACTIVE_MAX_OBS = original

    # ---- 1b. the clipping check, and the vacuous-pass rule ---------------
    #
    # The clipping check replaced an equality assertion on `N_ACTIVE_MAX_OBS`,
    # and the reason was that an equality passes while the value it names is
    # destroying data. So the case that matters is the one where a bound is
    # lowered until it clips: the check has to notice from the DATA, without
    # anybody naming the new value.
    dataset = pf.DEFAULT_OFFLINE_DATASET
    if os.path.exists(dataset):
        rows.append(("normalisation clipping", "as shipped", True,
                     pf.check_normalisation_clipping(dataset).passed,
                     "no bound clips more than its recorded allowance"))
        # The bound is lowered at `observation_constants_live`, which is where
        # both the check and `reconcile_to_current_constants` read it.
        # `QUEUE_MAX_DEFAULT` is NOT the lever: it reaches `StateVectorizer` as a
        # default argument, bound when the function was defined, so assigning to
        # the module attribute afterwards changes nothing. That is a fact about
        # rebinding defaults rather than about this check, and it is written down
        # because the first version of this case patched it and concluded the
        # check was blind.
        original_live = rli.observation_constants_live

        def _lowered() -> dict:
            c = dict(original_live())
            c["QUEUE_MAX"] = 6.0
            return c

        try:
            rli.observation_constants_live = _lowered
            res = pf.check_normalisation_clipping(dataset)
            rows.append(("normalisation clipping", "a bound lowered until it clips",
                         False, res.passed,
                         "found from the data, with no expected value written down"))
        finally:
            rli.observation_constants_live = original_live
    else:
        rows.append(("normalisation clipping", "dataset absent", False,
                     pf.check_normalisation_clipping(dataset).passed,
                     "a missing collection is a failure, not a skip"))

    # A check that inspected nothing must not report the same green line as one
    # that inspected everything. This is the rule itself rather than a check that
    # obeys it, because it applies to every check written after this one.
    rows.append(("vacuous pass", "a check that examined nothing", False,
                 pf.CheckResult("probe", True, [], examined=0).passed,
                 "an empty iteration establishes no property"))
    rows.append(("vacuous pass", "a check that examined something", True,
                 pf.CheckResult("probe", True, [], examined=1).passed,
                 "and the rule does not fire otherwise"))

    # ---- 2. objective --------------------------------------------------
    import src.hpo as real_hpo
    rows.append(("objective", "as shipped", True,
                 pf.check_objective_reads_packet_loss().passed, "healthy tree"))

    real_fn = real_hpo.compute_composite_objective
    try:
        real_hpo.compute_composite_objective = _broken_objective_module().compute_composite_objective
        res = pf.check_objective_reads_packet_loss()
        rows.append(("objective", "loss term replaced by a constant", False,
                     res.passed, "the term the search could not see"))

        real_hpo.compute_composite_objective = _alias_objective_module().compute_composite_objective
        res = pf.check_objective_reads_packet_loss()
        rows.append(("objective", "falls back onto outage_rate alias", False,
                     res.passed, "alias reintroduces the constant"))

        real_hpo.compute_composite_objective = _delegating_objective_module().compute_composite_objective
        res = pf.check_objective_reads_packet_loss()
        rows.append(("objective", "arithmetic delegated to a helper", True,
                     res.passed, "refactor of 2026-09-05; must not read as a regression"))
    finally:
        real_hpo.compute_composite_objective = real_fn

    # ---- 2b. discount factor range ---------------------------------------
    real_hpo_path = os.path.join(ROOT, "src", "hpo.py")
    dwell = pf.RSU_DWELL_S
    placeholder = pf.UNRESOLVED_GAMMA_HI

    # The live file is under active edit by another session -- it carried the
    # placeholder at 15:20 and the decided 0.99 at 15:40 -- so pinning a verdict
    # here would make this script fail for a legitimate change. What is asserted
    # instead is that the verdict AGREES with what the file contains: the bounds
    # are read, the expected answer is derived from them, and the checker has to
    # reach the same one.
    live_ranges = pf._gamma_ranges(real_hpo_path)
    live_bounds = {(lo, hi) for _, lo, hi in live_ranges}
    live_expected = (
        len(live_bounds) == 1
        and isinstance(next(iter(live_bounds))[1], (int, float))
        and abs(float(next(iter(live_bounds))[1]) - placeholder) > 1e-12
    )
    live_hi = next(iter(live_bounds))[1] if len(live_bounds) == 1 else "mixed"
    rows.append(("gamma range", "src/hpo.py as it stands", live_expected,
                 pf.check_gamma_range(real_hpo_path, placeholder, dwell).passed,
                 f"live upper bound {live_hi}; verdict must match the file"))

    gdir = tempfile.mkdtemp(prefix="verify_pf_gamma_")

    def gamma_file(name: str, body: str) -> str:
        p = os.path.join(gdir, name)
        with open(p, "w") as fh:
            fh.write(body)
        return p

    decided = gamma_file("decided.py",
        "def sample_hparams(trial, model):\n"
        "    a = trial.suggest_float('gamma', 0.95, 0.99)\n"
        "    b = trial.suggest_float('gamma', 0.95, 0.99)\n"
        "    return a, b\n")
    rows.append(("gamma range", "every site decided at 0.99", True,
                 pf.check_gamma_range(decided, placeholder, dwell).passed,
                 "placeholder gone and sites agree"))

    partial = gamma_file("partial.py",
        "def sample_hparams(trial, model):\n"
        "    a = trial.suggest_float('gamma', 0.95, 0.99)\n"
        "    b = trial.suggest_float('gamma', 0.95, 0.999)\n"
        "    return a, b\n")
    rows.append(("gamma range", "bound changed at one site of two", False,
                 pf.check_gamma_range(partial, placeholder, dwell).passed,
                 "the partial-application failure mode"))

    disagree = gamma_file("disagree.py",
        "def sample_hparams(trial, model):\n"
        "    a = trial.suggest_float('gamma', 0.95, 0.99)\n"
        "    b = trial.suggest_float('gamma', 0.95, 0.98)\n"
        "    return a, b\n")
    rows.append(("gamma range", "two decided bounds that disagree", False,
                 pf.check_gamma_range(disagree, placeholder, dwell).passed,
                 "studies would not be comparable"))

    named = gamma_file("named.py",
        "GAMMA_LO = 0.95\n"
        "GAMMA_HI = 0.99\n"
        "def sample_hparams(trial, model):\n"
        "    return trial.suggest_float('gamma', GAMMA_LO, GAMMA_HI)\n")
    rows.append(("gamma range", "bounds lifted to named constants", True,
                 pf.check_gamma_range(named, placeholder, dwell).passed,
                 "a refactor must stay readable"))

    named_placeholder = gamma_file("named_placeholder.py",
        "GAMMA_HI = 0.999\n"
        "def sample_hparams(trial, model):\n"
        "    return trial.suggest_float('gamma', 0.95, GAMMA_HI)\n")
    rows.append(("gamma range", "placeholder hidden behind a constant name", False,
                 pf.check_gamma_range(named_placeholder, placeholder, dwell).passed,
                 "renaming it does not decide it"))

    absent = gamma_file("absent.py",
        "def sample_hparams(trial, model):\n"
        "    return trial.suggest_float('learning_rate', 1e-5, 1e-3)\n")
    rows.append(("gamma range", "no gamma range in the file at all", False,
                 pf.check_gamma_range(absent, placeholder, dwell).passed,
                 "the check must not pass by finding nothing"))

    # ---- 2c. model coverage ----------------------------------------------
    # The arrangement the launcher will actually use, kept here so a future edit
    # to the groups is compared against something rather than against itself.
    #
    # READ FROM THE LAUNCHER, not restated. This list held CARLTON until
    # 2026-09-07, months after that baseline was replaced by HOORL and its module
    # deleted, so the verification reported a coverage failure that was its own.
    # A copy of a list is a second thing to remember to edit; deriving it means
    # the next regrouping cannot leave this file behind.
    live_groups = _launcher_groups()
    rows.append(("model coverage", "the four groups as the launcher has them", True,
                 pf.check_model_coverage(live_groups).passed,
                 "nine baselines, once each"))

    dropped = ["PPO MADDPG-MT", "I-HAMAPPO SAC", "TD3 RES-MAPDDPG",
               "SPAM-D3QN CARLTON"]
    rows.append(("model coverage", "one model dropped while rebalancing", False,
                 pf.check_model_coverage(dropped).passed,
                 "merge would refuse twelve hours later"))

    doubled = ["PPO MADDPG-MT", "I-HAMAPPO SAC", "TD3 RES-MAPDDPG MA2HDQN",
               "SPAM-D3QN CARLTON MA2HDQN"]
    rows.append(("model coverage", "one model left in both groups", False,
                 pf.check_model_coverage(doubled).passed,
                 "two best-params rows, no way to choose"))

    typo = ["PPO MADDPG-MT", "I-HAMAPPO SAC", "TD3 RES-MAPDDPG",
            "SPAM-D3QN CARLTON MA2HDNQ"]
    rows.append(("model coverage", "a typo in a model name", False,
                 pf.check_model_coverage(typo).passed,
                 "starts a study for a model that does not exist"))

    # ---- 2d. scenario horizon --------------------------------------------
    sdir = tempfile.mkdtemp(prefix="verify_pf_scen_")

    def scenario(name: str, sig_end, rou_end) -> str:
        """A scenario directory with a chosen signature and a chosen rou.xml.

        The two are written independently on purpose: the state that has to be
        caught is the one where they disagree.
        """
        d = os.path.join(sdir, name)
        os.makedirs(d, exist_ok=True)
        if sig_end is not None:
            with open(os.path.join(d, ".sumo_gen_signature.json"), "w") as fh:
                json.dump({"DENSITY": 20.0, "FLOW_END_S": sig_end,
                           "STEP_LENGTH": 0.1}, fh)
        if rou_end is not None:
            with open(os.path.join(d, "generated.rou.xml"), "w") as fh:
                fh.write(f'<routes><flow id="f0" begin="0" end="{rou_end}"/></routes>')
        return d

    rows.append(("scenario horizon", "the shared coder/src/sumo as it stands", True,
                 pf.check_scenario_horizon([os.path.join(ROOT, "src", "sumo")]).passed,
                 "restored to FLOW_END_S 3600.0 on 2026-09-05"))

    rows.append(("scenario horizon", "flows end at 131 s (the polluted state)", False,
                 pf.check_scenario_horizon([scenario("short", 131.0, 131.0)]).passed,
                 "road drains during the measured window"))

    rows.append(("scenario horizon", "signature 51 s but rou.xml 138 s", False,
                 pf.check_scenario_horizon([scenario("mismatch", 51.0, 138.0)]).passed,
                 "observed on 2026-09-05; either alone looks consistent"))

    rows.append(("scenario horizon", "consistent and long enough", True,
                 pf.check_scenario_horizon([scenario("good", 3600.0, 3600.0)]).passed,
                 "covers warm-up plus rollout"))

    rows.append(("scenario horizon", "exactly at the 530 s requirement", True,
                 pf.check_scenario_horizon([scenario("exact", 530.0, 530.0)]).passed,
                 "the boundary must not be off by one"))

    rows.append(("scenario horizon", "one second short of the requirement", False,
                 pf.check_scenario_horizon([scenario("just_short", 529.0, 529.0)]).passed,
                 "the boundary must actually bite"))

    rows.append(("scenario horizon", "directory with no scenario yet", True,
                 pf.check_scenario_horizon([os.path.join(sdir, "empty")]).passed,
                 "the run generates its own; nothing to judge"))

    rows.append(("scenario horizon", "rou.xml present but no signature", False,
                 pf.check_scenario_horizon([scenario("nosig", None, 3600.0)]).passed,
                 "half-readable is not readable"))

    # ---- 2e. scenario directories outside the work tree --------------------
    live_sumo = [f"/var/tmp/paper4_sumo/g{i}" for i in range(4)]
    rows.append(("worktree exposure", "the /var/tmp roots the launcher now uses", True,
                 pf.check_scenario_outside_worktree(live_sumo).passed,
                 "outside /home/imnyj, so no git clean reaches them"))

    old_layout = [os.path.join(ROOT, "results", "hpo_parallel_v2", f"g{i}", "sumo")
                  for i in range(4)]
    rows.append(("worktree exposure", "the old <output-root>/<group>/sumo layout", False,
                 pf.check_scenario_outside_worktree(old_layout).passed,
                 "how g1 lost its scenario on 2026-09-04"))

    rows.append(("worktree exposure", "one of four still inside the tree", False,
                 pf.check_scenario_outside_worktree(live_sumo[:3] + old_layout[:1]).passed,
                 "a partial move is still a lost group"))

    rows.append(("worktree exposure", "the shared coder/src/sumo", False,
                 pf.check_scenario_outside_worktree([os.path.join(ROOT, "src", "sumo")]).passed,
                 "inside by construction; stays exposed"))

    # A symlink from outside the tree back into it must not read as safe.
    ldir = tempfile.mkdtemp(prefix="verify_pf_link_")
    link = os.path.join(ldir, "looks_outside")
    try:
        os.symlink(os.path.join(ROOT, "results"), link)
        rows.append(("worktree exposure", "a symlink pointing back into the tree", False,
                     pf.check_scenario_outside_worktree([link]).passed,
                     "resolved with realpath, not taken at face value"))
    except OSError:
        pass

    rows.append(("worktree exposure", "no directories given", False,
                 pf.check_scenario_outside_worktree([]).passed,
                 "nothing to check is not a pass"))

    # ---- 3. SUMO isolation ---------------------------------------------
    base = tempfile.mkdtemp(prefix="verify_pf_sumo_")
    good = [os.path.join(base, f"g{i}", "sumo") for i in range(4)]
    rows.append(("sumo isolation", "four distinct group directories", True,
                 pf.check_sumo_isolation(good).passed, "healthy layout"))

    shared = [os.path.join(base, "shared", "sumo")] * 4
    rows.append(("sumo isolation", "all four groups share one directory", False,
                 pf.check_sumo_isolation(shared).passed, "one net.xml for four processes"))

    nested = [os.path.join(base, "g0", "sumo"), os.path.join(base, "g0", "sumo", "inner")]
    rows.append(("sumo isolation", "one group nested inside another", False,
                 pf.check_sumo_isolation(nested).passed, "shared generated files"))

    rows.append(("sumo isolation", "no directories given", False,
                 pf.check_sumo_isolation([]).passed, "nothing to check is not a pass"))

    # ---- 4. GPUs --------------------------------------------------------
    rows.append(("gpus", "the four devices this run wants", True,
                 pf.check_gpus([0, 1, 2, 3]).passed, "live nvidia-smi read"))
    rows.append(("gpus", "a device that does not exist", False,
                 pf.check_gpus([99]).passed, "absent device must not pass"))

    # ---- 5. destinations ------------------------------------------------
    fresh = os.path.join(base, "brand_new_root")
    rows.append(("destination", "path does not exist yet", True,
                 pf.check_destination(fresh, "output root", [CONTROL_DIR]).passed,
                 "launcher will create it"))

    empty = tempfile.mkdtemp(prefix="verify_pf_empty_")
    rows.append(("destination", "exists but holds no results", True,
                 pf.check_destination(empty, "output root", [CONTROL_DIR]).passed,
                 "re-runnable"))

    occupied = tempfile.mkdtemp(prefix="verify_pf_used_")
    os.makedirs(os.path.join(occupied, "g0"), exist_ok=True)
    with open(os.path.join(occupied, "g0", "optuna_best_params.csv"), "w") as fh:
        fh.write("model_name,best_value\nPPO,1.0\n")
    rows.append(("destination", "already holds optuna results", False,
                 pf.check_destination(occupied, "output root", [CONTROL_DIR]).passed,
                 "would overwrite a finished study"))

    # A sumo scratch directory alone must NOT block: it is regenerated anyway.
    sumo_only = tempfile.mkdtemp(prefix="verify_pf_sumo_only_")
    os.makedirs(os.path.join(sumo_only, "g0", "sumo"), exist_ok=True)
    with open(os.path.join(sumo_only, "g0", "sumo", "generated.net.xml"), "w") as fh:
        fh.write("<net/>")
    rows.append(("destination", "holds only a sumo scratch directory", True,
                 pf.check_destination(sumo_only, "output root", [CONTROL_DIR]).passed,
                 "scenario files are not results"))

    rows.append(("destination", "the protected control directory itself", False,
                 pf.check_destination(CONTROL_DIR, "output root", [CONTROL_DIR]).passed,
                 "control group for the new normaliser"))
    rows.append(("destination", "a subdirectory of the control directory", False,
                 pf.check_destination(os.path.join(CONTROL_DIR, "rerun"), "output root",
                                      [CONTROL_DIR]).passed,
                 "same destruction, one level down"))

    # ---- 6. provenance ---------------------------------------------------
    # This one is graded on `stops_launch`, not on `passed`. Its whole point is
    # that it reports a dirty tree without halting a run, because two sessions
    # are editing this tree and a clean-tree requirement would halt everything.
    live = pf.check_working_tree(list(pf.WATCHED_CODE_PATHS))
    rows.append(("working tree", "live repository, whatever its state", True,
                 not live.stops_launch,
                 f"reported {'dirty' if not live.passed else 'clean'}; must never block"))

    nothing_watched = pf.check_working_tree(["Workspace/paper4/coder/does_not_exist/"])
    rows.append(("working tree", "no watched path is dirty", True,
                 nothing_watched.passed,
                 "clean under the watched prefixes"))
    rows.append(("working tree", "and it still does not block", True,
                 not nothing_watched.stops_launch,
                 "non-blocking regardless of verdict"))

    # A blocking check must behave the other way round, or the two states are the
    # same thing wearing different labels.
    blocking = pf.check_destination(CONTROL_DIR, "output root", [CONTROL_DIR])
    rows.append(("severity", "a blocking check that failed does stop the launch", True,
                 blocking.stops_launch,
                 "confirms warn and fail are not interchangeable"))

    return rows


def main() -> int:
    rows = run()
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["check", "scenario", "expected_pass", "observed_pass", "correct", "note"])
        for check, scenario, expected, got, note in rows:
            w.writerow([check, scenario, expected, got, expected == got, note])

    width = max(len(r[1]) for r in rows)
    wrong = 0
    for check, scenario, expected, got, note in rows:
        correct = expected == got
        wrong += 0 if correct else 1
        verdict = "ok" if correct else "WRONG"
        print(f"  {check:<16} {scenario:<{width}}  expected={'PASS' if expected else 'FAIL'} "
              f"got={'PASS' if got else 'FAIL'}  {verdict}")

    print(f"\nwrote {OUT_CSV}")
    if wrong:
        print(f"VERDICT: FAIL -- {wrong} of {len(rows)} cases behaved incorrectly")
        return 1
    print(f"VERDICT: PASS -- all {len(rows)} cases behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
