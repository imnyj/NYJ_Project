"""Agent Workflow Memory (AWM).

Research: Wang et al., "Agent Workflow Memory" (arXiv:2409.07429,
ICML 2025). Reports +51.1% task success, 41% fewer steps on WebArena.

Concept: when a sequence of N agent calls repeatedly succeeds for similar
inputs, the system INDUCES a single-call "workflow" that encapsulates it.
Future requests matching that workflow's signature collapse N calls into 1.

Examples we expect to induce in this project:
    - `run_libsumo_scenario(spec)` ← (DESIGNER→blackboard→ENGINEER→npz)
    - `verify_citation(cite_id, claim_sentence)` ← (DOI fetch + retraction
      + sBERT claim-support)
    - `draft_section(section, inputs)` ← (outline fetch → compose → latex
      compile → write to blackboard)

Phase 5 stores candidate workflows from successful Task Ledger traces;
later phases (post-v1) could plug in a more aggressive learner.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("workflow_memory")


@dataclass
class Workflow:
    name: str                       # "run_libsumo_scenario"
    signature: dict[str, str]       # {"sumocfg_path": "str", "duration": "int", ...}
    steps: list[dict[str, Any]]     # recorded atomic calls (agent, task, args)
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "signature": self.signature,
            "steps": self.steps,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "last_used": self.last_used,
            "success_rate": round(self.success_rate, 3),
        }


class WorkflowMemory:
    """SQLite store for induced workflows + outcomes."""

    def __init__(
        self,
        path: Path | str | None = None,
    ):
        if path is None:
            from core.paths import get_paths
            path = get_paths().workflow_memory_db
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30.0)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    signature_json TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_used REAL DEFAULT 0,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_name TEXT NOT NULL,
                    args_json TEXT,
                    success INTEGER NOT NULL,
                    duration_s REAL,
                    ended_at REAL NOT NULL,
                    FOREIGN KEY (workflow_name) REFERENCES workflows(name)
                );
            """)

    # ------------------------------------------------------- register

    def register(self, wf: Workflow) -> None:
        """Store a workflow definition (idempotent by name)."""
        with self._conn() as c:
            row = c.execute(
                "SELECT id FROM workflows WHERE name=?", (wf.name,),
            ).fetchone()
            if row:
                c.execute(
                    """UPDATE workflows
                       SET signature_json=?, steps_json=?
                       WHERE id=?""",
                    (json.dumps(wf.signature, ensure_ascii=False),
                     json.dumps(wf.steps, ensure_ascii=False, default=str),
                     row[0]),
                )
                log.info("workflow_updated", name=wf.name)
                return
            c.execute(
                """INSERT INTO workflows
                   (name, signature_json, steps_json,
                    success_count, fail_count, last_used, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (wf.name,
                 json.dumps(wf.signature, ensure_ascii=False),
                 json.dumps(wf.steps, ensure_ascii=False, default=str),
                 wf.success_count, wf.fail_count, wf.last_used, time.time()),
            )
        log.info("workflow_registered", name=wf.name)

    # ----------------------------------------------------- record_run

    def record_run(
        self,
        *,
        workflow_name: str,
        args: dict[str, Any],
        success: bool,
        duration_s: float = 0.0,
    ) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO runs
                   (workflow_name, args_json, success, duration_s, ended_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (workflow_name,
                 json.dumps(args, ensure_ascii=False, default=str),
                 int(success), duration_s, time.time()),
            )
            if success:
                c.execute(
                    """UPDATE workflows
                       SET success_count = success_count + 1,
                           last_used = ?
                       WHERE name=?""",
                    (time.time(), workflow_name),
                )
            else:
                c.execute(
                    """UPDATE workflows
                       SET fail_count = fail_count + 1
                       WHERE name=?""",
                    (workflow_name,),
                )
        log.info("workflow_run_recorded",
                 workflow_name=workflow_name, success=success,
                 duration=round(duration_s, 2))

    # ----------------------------------------------------- lookup

    def get(self, name: str) -> Workflow | None:
        with self._conn() as c:
            row = c.execute(
                """SELECT name, signature_json, steps_json,
                          success_count, fail_count, last_used
                   FROM workflows WHERE name=?""",
                (name,),
            ).fetchone()
        return _row_to_workflow(row) if row else None

    def list_reliable(
        self, *, min_runs: int = 3, min_success_rate: float = 0.8,
    ) -> list[Workflow]:
        """Workflows worth suggesting for reuse."""
        with self._conn() as c:
            rows = c.execute(
                """SELECT name, signature_json, steps_json,
                          success_count, fail_count, last_used
                   FROM workflows
                   WHERE (success_count + fail_count) >= ?"""
                , (min_runs,),
            ).fetchall()
        wfs = [_row_to_workflow(r) for r in rows]
        return [w for w in wfs if w.success_rate >= min_success_rate]

    def stats(self) -> dict:
        with self._conn() as c:
            (nw,) = c.execute("SELECT COUNT(*) FROM workflows").fetchone()
            (nr,) = c.execute("SELECT COUNT(*) FROM runs").fetchone()
            (nrs,) = c.execute(
                "SELECT COALESCE(SUM(success), 0) FROM runs"
            ).fetchone()
        return {"workflows": nw, "runs": nr, "successes": nrs}


def _row_to_workflow(row: tuple) -> Workflow:
    return Workflow(
        name=row[0],
        signature=json.loads(row[1]),
        steps=json.loads(row[2]),
        success_count=row[3],
        fail_count=row[4],
        last_used=row[5],
    )
