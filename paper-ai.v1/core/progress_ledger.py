"""Progress Ledger — the INNER loop of the Magentic-One dual-ledger pattern.

Research basis: Magentic-One (Fourney et al., Microsoft Research, arXiv:2411.04468).

The Progress Ledger tracks:
    - Which plan step is currently in progress
    - Who is assigned to it
    - How many times we've tried (stall counter)
    - What recent artifacts have appeared on the blackboard

It is CONSULTED AFTER EVERY AGENT CALL by the orchestrator:
    - if the call produced a required output → advance step
    - if 3 calls in a row produced nothing useful → emit StallDetected,
      which causes the orchestrator to ask Commander to regenerate the Task Ledger

This is what prevents the "runaway reflection" failure mode that burns
hours of tokens in long multi-agent sessions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.artifacts import ArtifactName
from core.blackboard import Blackboard
from core.logger import get_logger
from core.task_ledger import PlanStep, TaskLedger

log = get_logger("progress_ledger")


class StallDetected(Exception):
    """Raised by Progress Ledger when too many consecutive no-progress calls."""
    def __init__(self, step_id: str, stall_count: int, reason: str):
        self.step_id = step_id
        self.stall_count = stall_count
        self.reason = reason
        super().__init__(f"Stall on {step_id!r} after {stall_count} attempts: {reason}")


class GlobalStallDetected(Exception):
    """Raised when total regenerations exceed a hard ceiling — escalate to user."""


@dataclass
class ProgressLedger:
    """Inner-loop tracking of the current active step."""

    # Thresholds
    STALL_COUNT_THRESHOLD: int = 3        # stalls before requesting regeneration
    MAX_TOTAL_REGENERATIONS: int = 3      # global stall ceiling
    MAX_STEP_ATTEMPTS: int = 5            # per-step hard attempt cap

    current_step_id: str | None = None
    current_assignee: str | None = None
    stall_count: int = 0                  # consecutive unproductive calls on current step
    partial_count: int = 0                # consecutive "partial" calls (half-weight)
    total_calls_this_step: int = 0
    total_regenerations: int = 0
    last_successful_publish: float = 0.0
    step_history: list[dict[str, Any]] = field(default_factory=list)

    # ----------------------------------------------------------- step control

    def enter_step(self, step: PlanStep) -> None:
        """Mark a new step as active."""
        self.current_step_id = step.id
        self.current_assignee = step.assignee
        self.stall_count = 0
        self.partial_count = 0
        self.total_calls_this_step = 0
        log.info(
            "progress_step_entered",
            step_id=step.id,
            assignee=step.assignee,
            description=step.description,
        )

    def leave_step(self, success: bool) -> None:
        """Record step completion (success or give-up) in history."""
        self.step_history.append({
            "step_id": self.current_step_id,
            "assignee": self.current_assignee,
            "success": success,
            "calls": self.total_calls_this_step,
            "stalls": self.stall_count,
            "ended_at": time.time(),
        })
        log.info(
            "progress_step_left",
            step_id=self.current_step_id,
            success=success,
            calls=self.total_calls_this_step,
        )
        self.current_step_id = None
        self.current_assignee = None
        self.stall_count = 0
        self.total_calls_this_step = 0

    # ----------------------------------------------------------- per-call hook

    def record_call_outcome(
        self,
        *,
        step: PlanStep,
        blackboard: Blackboard,
        before_versions: dict[str, int],
    ) -> str:
        """Inspect blackboard after an agent call; update stall counter.

        Returns one of:
            "progress"    - at least one required output was produced
            "partial"     - something was published but not a required output
            "no-progress" - nothing new at all; increment stall_count
        """
        self.total_calls_this_step += 1

        # Check if any required-produce output appeared / got a new version
        produced_something_required = False
        partial = False
        for out_name in step.produces:
            try:
                art_name = ArtifactName(out_name)
            except ValueError:
                continue
            latest = blackboard.latest(art_name)
            if latest is None:
                continue
            before = before_versions.get(out_name, 0)
            if latest.version > before:
                produced_something_required = True
                break

        if not produced_something_required:
            # Anything new at all? (partial progress on non-required artifacts)
            for name in ArtifactName:
                latest = blackboard.latest(name)
                if latest is None:
                    continue
                before = before_versions.get(name.value, 0)
                if latest.version > before:
                    partial = True
                    break

        if produced_something_required:
            self.stall_count = 0
            self.partial_count = 0
            self.last_successful_publish = time.time()
            outcome = "progress"
        elif partial:
            # partial work: half-weight penalty. Every 2 consecutive partials
            # count as 1 stall. This matches the "gentler" comment semantics
            # without letting agents loop forever on non-required outputs.
            self.partial_count += 1
            if self.partial_count >= 2:
                self.stall_count += 1
                self.partial_count = 0
            outcome = "partial"
        else:
            self.stall_count += 1
            self.partial_count = 0
            outcome = "no-progress"

        log.info(
            "progress_call_outcome",
            step_id=step.id,
            outcome=outcome,
            stall_count=self.stall_count,
            total_calls=self.total_calls_this_step,
        )

        # Hard per-step attempt ceiling
        if self.total_calls_this_step >= self.MAX_STEP_ATTEMPTS:
            raise StallDetected(
                step_id=step.id,
                stall_count=self.stall_count,
                reason=f"exceeded MAX_STEP_ATTEMPTS={self.MAX_STEP_ATTEMPTS}",
            )
        # Soft stall threshold → regeneration request
        if self.stall_count >= self.STALL_COUNT_THRESHOLD:
            raise StallDetected(
                step_id=step.id,
                stall_count=self.stall_count,
                reason=f"stall_count reached {self.STALL_COUNT_THRESHOLD}",
            )
        return outcome

    # --------------------------------------------------------- regeneration

    def note_regeneration(self) -> None:
        """Called by orchestrator after Commander regenerates the plan."""
        self.total_regenerations += 1
        self.stall_count = 0
        self.partial_count = 0
        log.warning("progress_ledger_regeneration_noted",
                    total=self.total_regenerations)
        if self.total_regenerations >= self.MAX_TOTAL_REGENERATIONS:
            raise GlobalStallDetected(
                f"Hit MAX_TOTAL_REGENERATIONS={self.MAX_TOTAL_REGENERATIONS}; "
                "escalating to user."
            )

    # ---------------------------------------------------------- introspection

    def current_status(self, task_ledger: TaskLedger) -> dict[str, Any]:
        """Snapshot for logging / debugging."""
        return {
            "current_step_id": self.current_step_id,
            "current_assignee": self.current_assignee,
            "stall_count": self.stall_count,
            "total_calls_this_step": self.total_calls_this_step,
            "total_regenerations": self.total_regenerations,
            "task_ledger_generation": task_ledger.generation,
            "steps_completed": sum(1 for s in task_ledger.plan if s.status == "done"),
            "steps_total": len(task_ledger.plan),
        }

    def render_for_prompt(self) -> str:
        return (
            "## Progress Ledger\n"
            f"- current_step: {self.current_step_id or 'none'}\n"
            f"- assignee: {self.current_assignee or 'none'}\n"
            f"- stall_count: {self.stall_count}/{self.STALL_COUNT_THRESHOLD}\n"
            f"- calls_on_this_step: {self.total_calls_this_step}\n"
            f"- regenerations: {self.total_regenerations}/{self.MAX_TOTAL_REGENERATIONS}\n"
        )


def snapshot_artifact_versions(blackboard: Blackboard) -> dict[str, int]:
    """Utility: build the 'before_versions' dict used by record_call_outcome."""
    return {
        name.value: (bb.version if (bb := blackboard.latest(name)) else 0)
        for name in ArtifactName
    }
