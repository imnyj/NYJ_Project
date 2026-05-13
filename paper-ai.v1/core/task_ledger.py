"""Task Ledger — the OUTER loop of the Magentic-One dual-ledger pattern.

Research basis: Magentic-One (Fourney et al., Microsoft Research, arXiv:2411.04468).

The Task Ledger holds the Commander's current understanding of the paper
project:
    - Known facts (what we've established)
    - Open questions (what we still need to resolve)
    - Plan (ordered steps to completion)

It is regenerated (not just appended to) whenever the Progress Ledger detects
repeated stalls. Regeneration asks Commander: "given these facts and what's
stuck, what's a different plan?"

The ledger is persisted to disk and included in Commander's shared_artifacts
prefix so it stays cached across turns.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("task_ledger")


@dataclass
class PlanStep:
    """One step of the Commander's current plan."""
    id: str
    description: str
    assignee: str                            # agent role
    required_inputs: list[str] = field(default_factory=list)   # artifact names
    produces: list[str] = field(default_factory=list)          # artifact names
    status: str = "pending"                  # pending | in_progress | done | blocked
    attempts: int = 0


@dataclass
class TaskLedger:
    """Outer-loop state. Regenerated when the pipeline stalls."""
    facts: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    plan: list[PlanStep] = field(default_factory=list)
    generation: int = 1                      # incremented on each regenerate()
    updated_at: float = field(default_factory=time.time)

    # --------------------------------------------------------------- mutators

    def add_fact(self, fact: str) -> None:
        if fact and fact not in self.facts:
            self.facts.append(fact)
            self.updated_at = time.time()

    def add_question(self, q: str) -> None:
        if q and q not in self.open_questions:
            self.open_questions.append(q)
            self.updated_at = time.time()

    def resolve_question(self, q: str) -> None:
        if q in self.open_questions:
            self.open_questions.remove(q)
            self.updated_at = time.time()

    def set_plan(self, steps: list[PlanStep]) -> None:
        self.plan = steps
        self.updated_at = time.time()

    def mark_step(self, step_id: str, status: str) -> None:
        for s in self.plan:
            if s.id == step_id:
                s.status = status
                self.updated_at = time.time()
                return
        raise KeyError(f"Unknown step_id: {step_id}")

    def next_pending(self) -> PlanStep | None:
        """Return the first pending step whose required inputs may be satisfied
        (actual input check done by orchestrator against blackboard)."""
        for s in self.plan:
            if s.status == "pending":
                return s
        return None

    def all_done(self) -> bool:
        return bool(self.plan) and all(s.status == "done" for s in self.plan)

    # ----------------------------------------------------------- regeneration

    def regenerate(
        self,
        *,
        new_plan: list[PlanStep],
        additional_facts: list[str] | None = None,
        additional_questions: list[str] | None = None,
    ) -> None:
        """Commander replaces the plan after stall detection.

        Facts and open questions are PRESERVED across regenerations (they
        accumulate knowledge). Only the plan gets replaced.
        """
        if additional_facts:
            for f in additional_facts:
                self.add_fact(f)
        if additional_questions:
            for q in additional_questions:
                self.add_question(q)
        self.plan = new_plan
        self.generation += 1
        self.updated_at = time.time()
        log.warning(
            "task_ledger_regenerated",
            generation=self.generation,
            n_steps=len(new_plan),
            n_facts=len(self.facts),
            n_questions=len(self.open_questions),
        )

    # -------------------------------------------------------------- rendering

    def render_for_prompt(self) -> str:
        """Render as Commander-readable markdown."""
        lines = [f"# Task Ledger (generation {self.generation})", ""]
        lines.append("## Known facts")
        if self.facts:
            lines.extend(f"- {f}" for f in self.facts)
        else:
            lines.append("_(none yet)_")
        lines.append("")
        lines.append("## Open questions")
        if self.open_questions:
            lines.extend(f"- {q}" for q in self.open_questions)
        else:
            lines.append("_(none)_")
        lines.append("")
        lines.append("## Plan")
        if self.plan:
            for s in self.plan:
                mark = {"pending": "[ ]", "in_progress": "[~]",
                        "done": "[x]", "blocked": "[!]"}.get(s.status, "[?]")
                lines.append(f"{mark} **{s.id}** ({s.assignee}) — {s.description}")
                if s.required_inputs:
                    lines.append(f"    inputs: {', '.join(s.required_inputs)}")
                if s.produces:
                    lines.append(f"    produces: {', '.join(s.produces)}")
        else:
            lines.append("_(empty)_")
        return "\n".join(lines)

    # ----------------------------------------------------------- persistence

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": list(self.facts),
            "open_questions": list(self.open_questions),
            "plan": [asdict(s) for s in self.plan],
            "generation": self.generation,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TaskLedger":
        return cls(
            facts=list(d.get("facts", [])),
            open_questions=list(d.get("open_questions", [])),
            plan=[PlanStep(**s) for s in d.get("plan", [])],
            generation=d.get("generation", 1),
            updated_at=d.get("updated_at", time.time()),
        )

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path | str) -> "TaskLedger":
        with Path(path).open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# ---------------------------------------------------- default initial plan

def default_paper_plan() -> list[PlanStep]:
    """The canonical 6-agent paper-writing DAG.

    Commander usually starts with this and mutates via regenerate() only
    when stalls occur.
    """
    return [
        PlanStep(
            id="S1_idea",
            description="Define main contribution and novelty",
            assignee="idea",
            required_inputs=[],
            produces=["main_idea.md", "storyline.md"],
        ),
        PlanStep(
            id="S2_search",
            description="Search SCIE literature; build refs.json",
            assignee="librarian",
            required_inputs=["main_idea.md"],
            produces=["refs.json"],
        ),
        PlanStep(
            id="S3_novelty",
            description="Refine novelty vs retrieved references",
            assignee="idea",
            required_inputs=["main_idea.md", "refs.json"],
            produces=["novelty_check.md"],
        ),
        PlanStep(
            id="S4_design",
            description="Design experiment metrics and baselines",
            assignee="experimenter",
            required_inputs=["main_idea.md", "novelty_check.md"],
            produces=["experiment_spec.yaml"],
        ),
        PlanStep(
            id="S5_implement",
            description="Implement simulation from spec",
            assignee="experimenter",
            required_inputs=["experiment_spec.yaml"],
            produces=["code_manifest.json", "sim_results.npz", "run_log.json"],
        ),
        PlanStep(
            id="S6_qa",
            description="Audit code + simulation for correctness and fairness",
            assignee="reviewer",
            required_inputs=["code_manifest.json", "sim_results.npz", "experiment_spec.yaml"],
            produces=["qa_report.md"],
        ),
        PlanStep(
            id="S7_write",
            description="Compose LaTeX draft; generate figures",
            assignee="writer",
            required_inputs=["main_idea.md", "storyline.md", "refs.json",
                             "experiment_spec.yaml", "sim_results.npz"],
            produces=["outline.md", "main.tex", "figures_manifest.json"],
        ),
        PlanStep(
            id="S8_polish",
            description="Proofread draft; remove AI-isms",
            assignee="reviewer",
            required_inputs=["main.tex"],
            produces=["polish_report.md"],
        ),
    ]
