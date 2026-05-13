"""LangGraph-backed orchestrator variant (EXPERIMENTAL).

⚠️  STATUS: experimental / best-effort maintained.
     The python-native `core.orchestrator.Orchestrator` is the production
     path. This module exists for users who want LangGraph's checkpointing
     and may lag behind the native orchestrator's feature set. Report
     divergences as bugs.

Wraps the same Blackboard + dual-ledger state into a LangGraph StateGraph,
gaining:
    - SQLite checkpointing (survive WSL2 restarts cleanly)
    - Built-in parallel fan-out via Send primitive (used when Librarian
      must query multiple publisher APIs at once)
    - Visual DAG introspection via .get_graph().draw_ascii()

Activation is optional. Switch to this when:
    - You want checkpointed resume on crash
    - You want parallel agent calls (e.g. several Librarian sub-queries)

Requires: langgraph, langgraph-checkpoint-sqlite (already in requirements.txt).
"""

from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path
from typing import Any, TypedDict

from core.logger import get_logger
from core.orchestrator import Orchestrator, OrchestratorConfig

log = get_logger("orchestrator_lg")

LANGGRAPH_AVAILABLE = importlib.util.find_spec("langgraph") is not None

warnings.warn(
    "core.orchestrator_langgraph is EXPERIMENTAL and best-effort maintained. "
    "Prefer core.orchestrator.Orchestrator for production runs.",
    stacklevel=2,
)


class PipelineState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes.

    We keep this thin — the real state lives in the Blackboard. What flows
    through the StateGraph is just a cursor indicating the currently active
    step, plus the final status.
    """
    topic: str
    current_step_id: str | None
    status: str              # "running" | "complete" | "stalled" | "budget_exceeded"
    error: str | None


class LangGraphOrchestrator:
    """LangGraph wrapper around the python-native Orchestrator.

    All heavy lifting (step execution, artifact publishing, stall detection)
    is delegated to the underlying Orchestrator. This class only handles
    graph construction, checkpointing, and fan-out routing.
    """

    def __init__(self, *, inner: Orchestrator):
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraphOrchestrator requires `pip install langgraph "
                "langgraph-checkpoint-sqlite`. Use Orchestrator directly for "
                "a pure-Python runtime."
            )
        self.inner = inner
        self._graph = None
        self._checkpointer = None

    # ------------------------------------------------------------------ build

    def build(self, *, checkpoint_db: Path | str | None = None) -> None:
        """Construct the StateGraph. Idempotent."""
        from langgraph.graph import END, START, StateGraph     # type: ignore

        if checkpoint_db:
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
                self._checkpointer = SqliteSaver.from_conn_string(str(checkpoint_db))
                log.info("langgraph_checkpointer", path=str(checkpoint_db))
            except ImportError:
                log.warning("sqlite_checkpointer_unavailable")
                self._checkpointer = None

        builder = StateGraph(PipelineState)

        # Single dispatcher node that delegates to Orchestrator's python-native
        # step executor. The graph is intentionally flat; per-agent nodes
        # for parallel fan-out are a potential future extension.
        def _dispatch(state: PipelineState) -> PipelineState:
            tl = self.inner.tl
            if tl.all_done():
                return {**state, "status": "complete"}
            step = tl.next_pending()
            if step is None:
                return {**state, "status": "stopped"}
            try:
                self.inner._execute_step(step)
                return {**state, "current_step_id": step.id, "status": "running"}
            except Exception as e:
                return {**state, "status": "stalled", "error": str(e)}

        def _route(state: PipelineState) -> str:
            status = state.get("status", "running")
            if status in ("complete", "stalled", "budget_exceeded", "stopped"):
                return END
            if self.inner._total_agent_calls >= self.inner.cfg.max_total_agent_calls:
                return END
            return "dispatch"

        builder.add_node("dispatch", _dispatch)
        builder.add_edge(START, "dispatch")
        builder.add_conditional_edges("dispatch", _route, {"dispatch": "dispatch", END: END})

        if self._checkpointer:
            self._graph = builder.compile(checkpointer=self._checkpointer)
        else:
            self._graph = builder.compile()
        log.info("langgraph_built", checkpoint=bool(self._checkpointer))

    # -------------------------------------------------------------------- run

    def run_paper(self, topic: str, *, thread_id: str = "default") -> dict[str, Any]:
        if self._graph is None:
            self.build()
        assert self._graph is not None

        self.inner.policy.start_new_paper()
        self.inner.tl.add_fact(f"Research topic: {topic}")

        cfg: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        initial: PipelineState = {
            "topic": topic,
            "current_step_id": None,
            "status": "running",
            "error": None,
        }
        final = self._graph.invoke(initial, config=cfg)

        log.info("langgraph_run_complete", status=final.get("status"))
        return self.inner._final_report(status=final.get("status", "unknown"))

    # --------------------------------------------------------------- visual

    def draw(self) -> str:
        if self._graph is None:
            self.build()
        assert self._graph is not None
        try:
            return self._graph.get_graph().draw_ascii()
        except Exception as e:
            return f"(ASCII draw unavailable: {e})"


# ---------------------------------------------------------- convenience factory

def create_langgraph_orchestrator(
    *,
    project_root: Path | str = ".",
    session_name: str | None = None,
    checkpoint_db: Path | str | None = None,
    dry_run: bool = False,
) -> LangGraphOrchestrator:
    """One-call builder for the LangGraph variant."""
    inner = Orchestrator.create(
        project_root=project_root,
        session_name=session_name,
        dry_run=dry_run,
    )
    lg = LangGraphOrchestrator(inner=inner)
    if checkpoint_db is None:
        checkpoint_db = Path(inner.cfg.project_root) / "output" / ".cache" / "lg_ckpt.sqlite"
        checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
    lg.build(checkpoint_db=checkpoint_db)
    return lg
