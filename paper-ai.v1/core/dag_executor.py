"""LLMCompiler-style parallel DAG execution.

Research: Kim et al., "An LLM Compiler for Parallel Function Calling"
(arXiv:2312.04511, ICML 2024). Reports 6.7× cheaper, 3.7× faster,
+9% accuracy vs ReAct on several benchmarks.

The idea: once a ReWOO plan is produced, we build the dependency DAG and
dispatch steps in waves — every step in the same wave has no unresolved
dependency, so they can execute in parallel. For libsumo simulations with
N baselines to run, this is a 1× → N× speedup.

Safety / simplicity choices:
    - Pure threading (no asyncio) because our tools are CPU+subprocess
      bound, not network-bound. asyncio would force every tool to be
      async, which is painful for SUMO/LaTeX wrappers.
    - Errors are recorded on the step, not raised. A failed step's
      dependents are auto-marked "skipped" rather than retried.
    - No dynamic replanning in the executor — if a plan fails, Orchestrator
      decides whether to regenerate via Commander. In-executor replanning
      is a potential future extension.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from core.logger import get_logger
from core.planner import Plan, PlanStep, substitute_refs

log = get_logger("dag_executor")


# ============================================================== tool registry

class ToolFn(Protocol):
    """Callable that receives a (possibly ref-substituted) arg string and
    returns any JSON-serializable result."""

    def __call__(self, args: str) -> Any: ...


class ToolRegistry:
    """Maps tool_name → ToolFn. Populated at startup by whoever has the
    tool instances (e.g. orchestrator, individual agents)."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> ToolFn | None:
        return self._tools.get(name)

    def names(self) -> set[str]:
        return set(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        """Minimal schema list passable to the planner."""
        return [
            {"name": n, "description": _describe(fn)}
            for n, fn in self._tools.items()
        ]


def _describe(fn: ToolFn) -> str:
    doc = getattr(fn, "__doc__", "") or ""
    # First non-blank line of docstring
    for ln in doc.splitlines():
        ln = ln.strip()
        if ln:
            return ln[:200]
    return f"{getattr(fn, '__name__', 'tool')}()"


# =================================================================== DAG

@dataclass
class ExecutionResult:
    """Outcome of executing a whole plan."""
    plan: Plan
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_seconds: float = 0.0
    waves: int = 0

    def all_results(self) -> dict[str, Any]:
        return {s.id: (s.error or s.result) for s in self.plan.steps}


class DAGExecutor:
    """Run a ReWOO plan respecting dependencies; parallel where possible."""

    def __init__(
        self,
        tools: ToolRegistry,
        *,
        max_parallel: int = 8,
        per_step_timeout: float = 300.0,
    ):
        self.tools = tools
        self.max_parallel = max_parallel
        self.per_step_timeout = per_step_timeout
        self._lock = threading.Lock()

    # ========================================================== execute

    def execute(self, plan: Plan) -> ExecutionResult:
        start = time.perf_counter()
        steps = {s.id: s for s in plan.steps}
        resolved: dict[str, Any] = {}
        pending: set[str] = set(steps)
        wave_n = 0
        skipped_total = 0

        while pending:
            # Find ready set: all deps are resolved (successfully) OR
            # transitively errored (we propagate failure).
            ready: list[PlanStep] = []
            for sid in list(pending):
                step = steps[sid]
                if all(d in resolved or _is_errored(steps.get(d)) for d in step.depends_on):
                    # If any dep errored, skip this step
                    if any(_is_errored(steps.get(d)) for d in step.depends_on):
                        step.error = "skipped: upstream dependency errored"
                        pending.discard(sid)
                        skipped_total += 1
                        log.info("step_skipped",
                                 step_id=sid, deps=step.depends_on)
                    else:
                        ready.append(step)
                        pending.discard(sid)

            if not ready:
                # No progress possible — unreachable set (possibly cycle
                # or forward reference not caught by validate())
                for sid in list(pending):
                    steps[sid].error = "unreachable: no resolvable path"
                    skipped_total += 1
                break

            wave_n += 1
            log.info("dag_wave",
                     wave=wave_n,
                     ready_count=len(ready),
                     remaining=len(pending))

            # Dispatch wave in parallel
            self._execute_wave(ready, resolved)

        result = ExecutionResult(
            plan=plan,
            succeeded=sum(1 for s in plan.steps if s.error is None and s.result is not None),
            failed=sum(1 for s in plan.steps
                       if s.error and not s.error.startswith("skipped")
                       and not s.error.startswith("unreachable")),
            skipped=skipped_total,
            elapsed_seconds=time.perf_counter() - start,
            waves=wave_n,
        )
        log.info("dag_execution_complete",
                 succeeded=result.succeeded,
                 failed=result.failed,
                 skipped=result.skipped,
                 elapsed=round(result.elapsed_seconds, 2),
                 waves=wave_n)
        return result

    # ------------------------------------------------------ wave dispatch

    def _execute_wave(
        self,
        ready: list[PlanStep],
        resolved: dict[str, Any],
    ) -> None:
        """Run the ready steps in parallel, update `resolved` with outputs."""
        max_workers = min(self.max_parallel, max(1, len(ready)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_to_step = {
                ex.submit(self._execute_one, s, resolved): s for s in ready
            }
            for fut in concurrent.futures.as_completed(future_to_step):
                step = future_to_step[fut]
                try:
                    output = fut.result(timeout=self.per_step_timeout)
                except concurrent.futures.TimeoutError:
                    step.error = f"timeout after {self.per_step_timeout}s"
                    log.warning("step_timeout", step_id=step.id)
                    continue
                except Exception as e:
                    step.error = f"exception: {e!r}"
                    log.warning("step_exception", step_id=step.id, err=str(e))
                    continue

                step.result = output
                with self._lock:
                    resolved[step.id] = output
                log.info("step_done", step_id=step.id,
                         tool=step.tool,
                         out_preview=_preview(output))

    # ------------------------------------------------------ single step

    def _execute_one(self, step: PlanStep, resolved: dict[str, Any]) -> Any:
        """Resolve refs in args, look up the tool, invoke it."""
        tool_fn = self.tools.get(step.tool)
        if tool_fn is None:
            raise RuntimeError(f"tool not registered: {step.tool}")
        args = substitute_refs(step.raw_args, resolved)
        return tool_fn(args)


# ================================================================ helpers

def _is_errored(step: PlanStep | None) -> bool:
    return step is not None and step.error is not None


def _preview(obj: Any, n: int = 120) -> str:
    s = str(obj)
    return s if len(s) <= n else s[:n] + "..."
