"""Phase-2 offline tests (no API calls).

Verifies:
    - Blackboard publish/subscribe honors producer contract
    - Artifact rendering truncates correctly
    - TaskLedger regenerate() preserves facts, replaces plan
    - ProgressLedger detects stall at threshold
    - Orchestrator dry-run executes the default plan structure
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.artifacts import (
    ArtifactContractViolation,
    ArtifactName,
    PayloadKind,
)
from core.blackboard import Blackboard
from core.orchestrator import Orchestrator
from core.progress_ledger import (
    GlobalStallDetected,
    ProgressLedger,
    StallDetected,
    snapshot_artifact_versions,
)
from core.task_ledger import PlanStep, TaskLedger, default_paper_plan

ROOT = Path(__file__).parent.parent


# --------------------------------------------------------------- blackboard

def test_blackboard_publish_and_latest():
    bb = Blackboard()
    a = bb.publish(
        agent="idea",
        name=ArtifactName.MAIN_IDEA,
        payload="our contribution is X",
        kind=PayloadKind.TEXT,
    )
    assert a.version == 1
    assert bb.latest(ArtifactName.MAIN_IDEA).payload == "our contribution is X"


def test_blackboard_version_increments():
    bb = Blackboard()
    bb.publish(agent="idea", name=ArtifactName.MAIN_IDEA, payload="v1")
    bb.publish(agent="idea", name=ArtifactName.MAIN_IDEA, payload="v2")
    assert bb.latest(ArtifactName.MAIN_IDEA).version == 2
    assert len(bb.history(ArtifactName.MAIN_IDEA)) == 2


def test_blackboard_producer_contract_enforced():
    bb = Blackboard()
    # `writer` is NOT the producer of refs.json — should fail
    with pytest.raises(ArtifactContractViolation):
        bb.publish(agent="writer", name=ArtifactName.REFS, payload=[])


def test_blackboard_subscriptions_for_writer():
    bb = Blackboard()
    bb.publish(agent="idea", name=ArtifactName.MAIN_IDEA, payload="x")
    bb.publish(agent="librarian", name=ArtifactName.REFS,
               payload=[{"doi": "10.1/abc"}], kind=PayloadKind.JSON)
    bb.publish(agent="experimenter", name=ArtifactName.EXPERIMENT_SPEC,
               payload="spec: here")
    subs = bb.subscriptions_for("writer")
    names = {a.name for a in subs}
    # Writer subscribes to: MAIN_IDEA, STORYLINE, NOVELTY_CHECK, REFS,
    # EXPERIMENT_SPEC, SIM_RESULTS, POLISH_REPORT
    assert ArtifactName.MAIN_IDEA in names
    assert ArtifactName.REFS in names
    assert ArtifactName.EXPERIMENT_SPEC in names


def test_blackboard_snapshot_for_agent_stable():
    """Same content → same render (crucial for prompt caching)."""
    bb = Blackboard()
    bb.publish(agent="idea", name=ArtifactName.MAIN_IDEA, payload="foo")
    s1 = bb.snapshot_for_agent("writer")
    s2 = bb.snapshot_for_agent("writer")
    assert s1 == s2


def test_blackboard_save_and_load(tmp_path):
    bb = Blackboard()
    bb.publish(agent="idea", name=ArtifactName.MAIN_IDEA, payload="persist me")
    f = tmp_path / "bb.json"
    bb.save(f)

    bb2 = Blackboard()
    bb2.load(f)
    assert bb2.latest(ArtifactName.MAIN_IDEA).payload == "persist me"


# ------------------------------------------------------------- task ledger

def test_task_ledger_default_plan_complete():
    plan = default_paper_plan()
    assert len(plan) == 8
    step_ids = {s.id for s in plan}
    # Must cover all 6 agent roles
    assigned = {s.assignee for s in plan}
    assert assigned == {"idea", "librarian", "experimenter", "reviewer", "writer"}
    # Every step produces at least one artifact
    for s in plan:
        assert s.produces, f"step {s.id} produces nothing"


def test_task_ledger_regenerate_preserves_facts():
    tl = TaskLedger()
    tl.add_fact("topic: V2X beaconing")
    tl.add_fact("seed = 42")
    tl.set_plan(default_paper_plan())
    gen0 = tl.generation
    tl.regenerate(
        new_plan=[PlanStep(id="new_step", description="try again",
                           assignee="idea", produces=["main_idea.md"])],
        additional_facts=["baseline is DCC"],
    )
    assert tl.generation == gen0 + 1
    assert "topic: V2X beaconing" in tl.facts
    assert "baseline is DCC" in tl.facts
    assert len(tl.plan) == 1


def test_task_ledger_next_pending_and_mark():
    tl = TaskLedger()
    tl.set_plan(default_paper_plan())
    first = tl.next_pending()
    assert first is not None and first.id == "S1_idea"
    tl.mark_step("S1_idea", "done")
    nxt = tl.next_pending()
    assert nxt is not None and nxt.id == "S2_search"


# ------------------------------------------------------- progress ledger

def test_progress_ledger_no_progress_raises_at_threshold():
    pl = ProgressLedger()
    step = PlanStep(
        id="S1_idea", description="def",
        assignee="idea", produces=["main_idea.md"],
    )
    pl.enter_step(step)
    bb = Blackboard()
    before = snapshot_artifact_versions(bb)
    # Three no-progress calls → raise
    for _ in range(pl.STALL_COUNT_THRESHOLD - 1):
        pl.record_call_outcome(step=step, blackboard=bb, before_versions=before)
    with pytest.raises(StallDetected):
        pl.record_call_outcome(step=step, blackboard=bb, before_versions=before)


def test_progress_ledger_progress_resets_stall():
    pl = ProgressLedger()
    step = PlanStep(
        id="S1_idea", description="def",
        assignee="idea", produces=["main_idea.md"],
    )
    pl.enter_step(step)
    bb = Blackboard()

    before = snapshot_artifact_versions(bb)
    pl.record_call_outcome(step=step, blackboard=bb, before_versions=before)
    assert pl.stall_count == 1

    # Now the agent publishes → stall should reset
    bb.publish(agent="idea", name=ArtifactName.MAIN_IDEA, payload="done")
    outcome = pl.record_call_outcome(step=step, blackboard=bb, before_versions=before)
    assert outcome == "progress"
    assert pl.stall_count == 0


def test_progress_ledger_global_stall():
    pl = ProgressLedger()
    pl.MAX_TOTAL_REGENERATIONS = 2  # shrink for test
    pl.note_regeneration()
    with pytest.raises(GlobalStallDetected):
        pl.note_regeneration()


# ---------------------------------------------------------- orchestrator dry

def test_orchestrator_create_and_introspect():
    orch = Orchestrator.create(project_root=ROOT, dry_run=True)
    assert set(orch.agents) == {
        "commander", "idea", "librarian",
        "experimenter", "reviewer", "writer",
    }
    assert len(orch.tl.plan) == 8
    assert orch.tl.next_pending().id == "S1_idea"


def test_orchestrator_dry_run_marks_steps_blocked_on_missing_inputs():
    """Dry-run: agents do nothing, so no artifacts are produced.
    Step 1 (no inputs) should go in_progress then stall.
    Step 2+ should be blocked because their inputs aren't there yet.
    """
    orch = Orchestrator.create(project_root=ROOT, dry_run=True)
    # Use lower caps so the test finishes quickly
    orch.pl.MAX_STEP_ATTEMPTS = 2
    orch.pl.STALL_COUNT_THRESHOLD = 2
    orch.pl.MAX_TOTAL_REGENERATIONS = 1
    orch.cfg.max_total_agent_calls = 30

    report = orch.run_paper(topic="dry run test")
    assert report["status"] in ("escalated", "stopped", "complete")
    # In dry-run, S1 cannot produce its output → eventually blocked or the run
    # escalates via regeneration. Either way we expect NO step to be "done".
    statuses = {s["status"] for s in report["plan"]}
    assert "done" not in statuses, "dry run should not mark any step done"


def test_orchestrator_checkpoint_creates_files(tmp_path):
    orch = Orchestrator.create(project_root=ROOT, dry_run=True,
                               session_name="test_session")
    # use temp output location to avoid polluting the real output/
    orch.cfg.project_root = tmp_path
    orch.pl.MAX_STEP_ATTEMPTS = 1
    orch.pl.STALL_COUNT_THRESHOLD = 1
    orch.pl.MAX_TOTAL_REGENERATIONS = 0
    orch.cfg.max_total_agent_calls = 3

    _ = orch.run_paper(topic="checkpoint test")
    session_dir = tmp_path / "output" / "sessions" / "test_session"
    assert (session_dir / "blackboard.json").exists()
    assert (session_dir / "task_ledger.json").exists()
