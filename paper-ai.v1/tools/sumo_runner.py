"""libsumo wrapper.

Thin adapter over the `libsumo-simulation` Skill: provides a single
.run_scenario() call that manages SUMO lifecycle correctly (start, step,
close, crash-safe) so Experimenter's ENGINEER-mode agent doesn't have to
re-invent the try/finally pattern every time.

Graceful degradation: if libsumo isn't importable, `is_available()` is
False and .run_scenario() raises a clear install hint. This lets the rest
of paper-ai boot on a machine without SUMO.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("sumo_runner")

try:
    import libsumo  # noqa: F401
    _LIBSUMO_AVAILABLE = True
except ImportError:
    _LIBSUMO_AVAILABLE = False

try:
    import traci  # noqa: F401
    _TRACI_AVAILABLE = True
except ImportError:
    _TRACI_AVAILABLE = False


def is_available() -> bool:
    return _LIBSUMO_AVAILABLE or _TRACI_AVAILABLE


@dataclass
class ScenarioResult:
    steps: list[float] = field(default_factory=list)
    n_vehicles: list[int] = field(default_factory=list)
    mean_speed: list[float] = field(default_factory=list)      # m/s
    total_waiting: list[float] = field(default_factory=list)   # s
    co2: list[float] = field(default_factory=list)             # mg
    duration: float = 0.0
    seed: int = 0
    scenario: str = ""
    success: bool = False
    error: str = ""

    def to_npz(self, path: Path | str) -> str:
        import numpy as np
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            step=np.array(self.steps, dtype=float),
            n_vehicles=np.array(self.n_vehicles, dtype=int),
            mean_speed=np.array(self.mean_speed, dtype=float),
            total_waiting=np.array(self.total_waiting, dtype=float),
            co2=np.array(self.co2, dtype=float),
            _duration=np.array(self.duration),
            _seed=np.array(self.seed),
            _scenario=np.array(self.scenario, dtype=object),
            _success=np.array(self.success),
        )
        return str(path)


class SumoRunner:
    """Run one or more libsumo scenarios."""

    def __init__(
        self,
        *,
        sumo_binary: str = "sumo",
        sumo_home: str | None = None,
        prefer_libsumo: bool = True,
    ):
        self.sumo_binary = sumo_binary
        self.sumo_home = sumo_home or os.environ.get("SUMO_HOME")
        self.prefer_libsumo = prefer_libsumo

    # ------------------------------------------------------ sanity

    def preflight(self) -> dict[str, Any]:
        """Tell the agent what's available without starting a run."""
        return {
            "libsumo_importable": _LIBSUMO_AVAILABLE,
            "traci_importable": _TRACI_AVAILABLE,
            "sumo_home": self.sumo_home,
            "sumo_home_exists": bool(
                self.sumo_home and Path(self.sumo_home).is_dir()
            ),
        }

    # ------------------------------------------------------ main call

    def run_scenario(
        self,
        *,
        sumocfg_path: str | Path,
        duration: int,
        seed: int = 42,
        extra_args: list[str] | None = None,
    ) -> ScenarioResult:
        """Run a single scenario, collecting per-step aggregates."""
        if not is_available():
            return ScenarioResult(
                scenario=str(sumocfg_path), seed=seed,
                duration=duration, success=False,
                error="neither libsumo nor traci importable; "
                      "install SUMO and ensure Python bindings are on PYTHONPATH",
            )

        sumocfg_path = str(sumocfg_path)
        args = [
            self.sumo_binary, "-c", sumocfg_path,
            "--seed", str(seed),
            "--no-step-log", "true",
            "--no-warnings", "true",
            "--duration-log.disable", "true",
        ]
        if extra_args:
            args.extend(extra_args)

        result = ScenarioResult(scenario=sumocfg_path, seed=seed,
                                duration=duration)

        if self.prefer_libsumo and _LIBSUMO_AVAILABLE:
            return self._run_libsumo(args, duration, result)
        return self._run_traci(args, duration, result)

    # ------------------------------------------------ libsumo path

    def _run_libsumo(self, args, duration, result):
        import libsumo
        log.info("sumo_start", backend="libsumo", scenario=result.scenario)
        try:
            libsumo.start(args)
            while libsumo.simulation.getTime() < duration:
                libsumo.simulationStep()
                self._collect_step(libsumo, result)
            result.success = True
        except Exception as e:
            result.error = f"libsumo: {e!r}"
            log.error("sumo_libsumo_error", err=str(e))
        finally:
            try:
                libsumo.close()
            except Exception:
                pass
        return result

    # ------------------------------------------------ traci fallback

    def _run_traci(self, args, duration, result):
        import traci
        log.info("sumo_start", backend="traci", scenario=result.scenario)
        try:
            traci.start(args)
            while traci.simulation.getTime() < duration:
                traci.simulationStep()
                self._collect_step(traci, result)
            result.success = True
        except Exception as e:
            result.error = f"traci: {e!r}"
            log.error("sumo_traci_error", err=str(e))
        finally:
            try:
                traci.close()
            except Exception:
                pass
        return result

    # --------------------------------------------------- metrics

    @staticmethod
    def _collect_step(sumo, result: ScenarioResult) -> None:
        """Shared per-step collector (works with both libsumo and traci)."""
        t = sumo.simulation.getTime()
        veh_ids = sumo.vehicle.getIDList()
        n = len(veh_ids)
        if n:
            speeds = [sumo.vehicle.getSpeed(v) for v in veh_ids]
            waits = [sumo.vehicle.getWaitingTime(v) for v in veh_ids]
            co2 = [sumo.vehicle.getCO2Emission(v) for v in veh_ids]
            ms = sum(speeds) / n
            tw = sum(waits)
            tc = sum(co2)
        else:
            ms = tw = tc = 0.0
        result.steps.append(t)
        result.n_vehicles.append(n)
        result.mean_speed.append(ms)
        result.total_waiting.append(tw)
        result.co2.append(tc)
