# tests/test_scenario_isolation.py
# ============================================================================
# A run's scenario parameters must live inside that run.
#
# `prepare_scenario` shortens the traffic-demand horizon to fit the run it is
# about to do, which is right in itself. It used to do so by ASSIGNING
# `ss.FLOW_END_S`, `ss.MAX_STEPS` and `ss.DENSITY`, and the value then escaped by
# two routes: the module global, which every later call in the same process
# compared its cache against, and `make_sumo_set`'s on-disk signature file, which
# carries FLOW_END_S to the next process.
#
# The measured damage (2026-09-05): the shared scenario directory was found with
# flow horizons of 131 s and 138 s instead of 3600 s. Those are exactly
# (10 + 1200 + 100) * 0.1 and (80 + 1200 + 100) * 0.1, i.e. the fingerprints of
# short pytest rollouts. Against a 120 s warm-up, anything reading that directory
# next measures a road that has already stopped generating traffic -- silently,
# because a short scenario raises nothing, it just runs out of cars.
#
# ONE PASS DOES NOT CATCH THIS. The failure is a residue left for the NEXT run,
# so the tests below run a short scenario and then a long one and check that the
# second is not judged against the first's leftovers.
# ============================================================================

import json
import os
import xml.etree.ElementTree as ET

import pytest

import src.sumo.make_sumo_set as ss
from src.hot_swap_trainer import prepare_scenario, scenario_flow_end_s

SHORT_STEPS = 10
LONG_STEPS = 800
WARMUP = 1200
DENSITY = 5.0


def _flow_end_on_disk(directory: str) -> float:
    """The `end=` horizon actually written into the generated flows."""
    root = ET.parse(os.path.join(directory, "generated.rou.xml")).getroot()
    ends = {float(f.get("end")) for f in root.findall("flow")}
    assert len(ends) == 1, f"flows disagree about their horizon: {sorted(ends)}"
    return ends.pop()


def _signature_on_disk(directory: str) -> dict:
    with open(os.path.join(directory, ss.SIGNATURE_FILE), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def scenario_dir(tmp_path, monkeypatch):
    """An isolated scenario directory, so no test can touch the shared one."""
    d = tmp_path / "sumo"
    d.mkdir()
    monkeypatch.setenv("PAPER4_SUMO_DIR", str(d))
    return str(d)


class TestParametersDoNotEscapeIntoTheModule:
    def test_prepare_scenario_leaves_the_module_defaults_alone(self, scenario_dir):
        before = (float(ss.FLOW_END_S), float(ss.MAX_STEPS), float(ss.DENSITY))
        prepare_scenario(DENSITY, SHORT_STEPS, WARMUP, seed=1,
                         force_regenerate=True, sumo_dir=scenario_dir)
        after = (float(ss.FLOW_END_S), float(ss.MAX_STEPS), float(ss.DENSITY))
        assert after == before, (
            "prepare_scenario wrote its run parameters into the module; the next "
            f"caller in this process would inherit {after} instead of {before}"
        )

    def test_the_run_still_gets_the_horizon_it_asked_for(self, scenario_dir):
        """Not writing the global must not mean not honouring the value."""
        prepare_scenario(DENSITY, SHORT_STEPS, WARMUP, seed=1,
                         force_regenerate=True, sumo_dir=scenario_dir)
        want = scenario_flow_end_s(SHORT_STEPS, WARMUP)
        assert _flow_end_on_disk(scenario_dir) == pytest.approx(want)
        assert _signature_on_disk(scenario_dir)["FLOW_END_S"] == pytest.approx(want)
        assert _signature_on_disk(scenario_dir)["DENSITY"] == pytest.approx(DENSITY)


class TestAShortRunDoesNotContaminateALongOne:
    def test_the_long_run_regenerates_instead_of_reusing_the_short_scenario(self, scenario_dir):
        """The regression, in the order that produces it: short, then long.

        The second call must judge the cache against ITS OWN horizon. If it reads
        the residue of the first -- from the module or from the signature file --
        it concludes the cached scenario is long enough and trains on a road that
        stops generating traffic 131 s in.
        """
        prepare_scenario(DENSITY, SHORT_STEPS, WARMUP, seed=1,
                         force_regenerate=True, sumo_dir=scenario_dir)
        short_end = _flow_end_on_disk(scenario_dir)
        assert short_end == pytest.approx(scenario_flow_end_s(SHORT_STEPS, WARMUP))

        # No force_regenerate: the cache decision itself is what is under test.
        prepare_scenario(DENSITY, LONG_STEPS, WARMUP, seed=1,
                         force_regenerate=False, sumo_dir=scenario_dir)
        long_end = _flow_end_on_disk(scenario_dir)
        want = scenario_flow_end_s(LONG_STEPS, WARMUP)
        assert long_end == pytest.approx(want), (
            f"the long run kept the short run's {short_end} s of demand; it needs "
            f"{want} s and would have run out of traffic partway through"
        )

    def test_a_shorter_run_after_a_longer_one_reuses_the_cache(self, scenario_dir):
        """The rule is `stored >= wanted`, not `stored == wanted`.

        Regenerating whenever the horizons merely differ would rewrite the whole
        scenario on every episode that shortened its step budget.
        """
        prepare_scenario(DENSITY, LONG_STEPS, WARMUP, seed=1,
                         force_regenerate=True, sumo_dir=scenario_dir)
        long_end = _flow_end_on_disk(scenario_dir)
        mtime = os.path.getmtime(os.path.join(scenario_dir, "generated.rou.xml"))

        prepare_scenario(DENSITY, SHORT_STEPS, WARMUP, seed=1,
                         force_regenerate=False, sumo_dir=scenario_dir)
        assert _flow_end_on_disk(scenario_dir) == pytest.approx(long_end)
        assert os.path.getmtime(os.path.join(scenario_dir, "generated.rou.xml")) == mtime

    def test_a_density_change_still_forces_a_regeneration(self, scenario_dir):
        """Density is baked into the per-flow probability; it must not be cached over.

        It used to reach the generator through `ss.DENSITY`, which is the second
        half of the same leak. Passing it as an argument has to keep this working.
        """
        prepare_scenario(5.0, SHORT_STEPS, WARMUP, seed=1,
                         force_regenerate=True, sumo_dir=scenario_dir)
        prob_a = _first_flow_probability(scenario_dir)
        prepare_scenario(35.0, SHORT_STEPS, WARMUP, seed=1,
                         force_regenerate=False, sumo_dir=scenario_dir)
        prob_b = _first_flow_probability(scenario_dir)
        assert prob_b > prob_a, (prob_a, prob_b)
        assert _signature_on_disk(scenario_dir)["DENSITY"] == pytest.approx(35.0)


class TestTheGeneratorHonoursItsArguments:
    def test_named_arguments_beat_the_module_globals(self, scenario_dir):
        """A caller that names density and horizon gets them, whatever the globals hold."""
        want = 555.0
        ss.make_sumo_files(force_regenerate=True, base_path=scenario_dir,
                           density=12.0, flow_end_s=want)
        assert _flow_end_on_disk(scenario_dir) == pytest.approx(want)
        assert _signature_on_disk(scenario_dir)["DENSITY"] == pytest.approx(12.0)
        assert float(ss.FLOW_END_S) != want, "the argument leaked into the module"

    def test_no_arguments_reproduces_the_module_defaults(self, scenario_dir):
        """The globals stay as the default for a caller that names nothing."""
        ss.make_sumo_files(force_regenerate=True, base_path=scenario_dir)
        assert _flow_end_on_disk(scenario_dir) == pytest.approx(float(ss.FLOW_END_S))
        assert _signature_on_disk(scenario_dir)["DENSITY"] == pytest.approx(float(ss.DENSITY))


def _first_flow_probability(directory: str) -> float:
    root = ET.parse(os.path.join(directory, "generated.rou.xml")).getroot()
    flows = root.findall("flow")
    assert flows, "no flows were generated"
    return float(flows[0].get("probability"))
