"""Pipeline Orchestrator.

Ties together:
    - Blackboard              (structured-document shared state)
    - TaskLedger              (outer loop: facts, questions, plan)
    - ProgressLedger          (inner loop: stall detection)
    - CommanderAgent (root)   (supervisor; regenerates plans on stall)
    - 5 worker agents         (idea, librarian, experimenter, reviewer, writer)
    - PolicyRuntime           (routing + budget)

The design intentionally supports two modes:

  (a) PYTHON_NATIVE mode (this file's `Orchestrator`):
        Pure Python loop. No external deps. Always works, easy to debug.
        This is the default and the production path.

  (b) LANGGRAPH mode (orchestrator_langgraph.py, experimental):
        Builds a StateGraph, uses LangGraph's checkpointing for crash
        recovery, supports Send() for parallel fan-out. Requires the
        `langgraph` package. Maintained on a best-effort basis; report
        divergences with the python-native path as bugs.

Both modes consume the SAME Blackboard and Task/Progress ledgers, so you
can start in python-native mode and migrate to langgraph without changing
agents, prompts, or artifacts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents import make_worker
from agents.base_agent import BaseAgent
from commander import CommanderAgent
from core.artifacts import ArtifactName, PayloadKind
from core.blackboard import Blackboard
from core.logger import get_logger
from core.policy_runtime import BudgetExceeded, PolicyRuntime
from core.progress_ledger import (
    GlobalStallDetected,
    ProgressLedger,
    StallDetected,
    snapshot_artifact_versions,
)
from core.task_ledger import PlanStep, TaskLedger, default_paper_plan
from tools.anthropic_client import AnthropicClient

log = get_logger("orchestrator")


# --------------------------------------------------------------------- config

@dataclass
class OrchestratorConfig:
    """Run-time knobs (kept separate from YAML configs for easy override)."""
    project_root: Path = field(default_factory=lambda: Path("."))
    session_name: str = field(default_factory=lambda: f"session_{int(time.time())}")
    checkpoint_every_n_calls: int = 3        # save blackboard snapshot frequency
    dry_run: bool = False                    # skip LLM calls (for tests)
    max_total_agent_calls: int = 60          # hard ceiling independent of stalls


# ============================================================================
# Orchestrator (python-native)
# ============================================================================

class Orchestrator:
    """Sequential plan executor with dual-ledger stall detection.

    Usage:
        orch = Orchestrator.create(project_root=Path("."))
        orch.run_paper(topic="age-of-information-aware V2X beaconing")
    """

    def __init__(
        self,
        *,
        policy: PolicyRuntime,
        client: AnthropicClient,
        blackboard: Blackboard,
        task_ledger: TaskLedger,
        progress_ledger: ProgressLedger,
        agents: dict[str, BaseAgent],
        config: OrchestratorConfig,
    ):
        self.policy = policy
        self.client = client
        self.bb = blackboard
        self.tl = task_ledger
        self.pl = progress_ledger
        self.agents = agents
        self.cfg = config
        self._total_agent_calls = 0

    # ------------------------------------------------------------- factory

    @classmethod
    def create(
        cls,
        *,
        project_root: Path | str = ".",
        session_name: str | None = None,
        dry_run: bool = False,
    ) -> "Orchestrator":
        from core.paths import paths_for
        root = Path(project_root).resolve()
        paths = paths_for(root)
        policy = PolicyRuntime(config_dir=paths.config)
        client = AnthropicClient(policy=policy, project_root=root)
        blackboard = Blackboard()
        task_ledger = TaskLedger()
        task_ledger.set_plan(default_paper_plan())
        progress_ledger = ProgressLedger()
        # Commander is structurally above the workers; instantiate it
        # separately (not from the agents.WORKER_REGISTRY).
        agents: dict[str, BaseAgent] = {
            "commander": CommanderAgent(client),
        }
        for role in ("idea", "librarian", "experimenter", "reviewer", "writer"):
            agents[role] = make_worker(role, client)
        cfg = OrchestratorConfig(project_root=root, dry_run=dry_run)
        if session_name:
            cfg.session_name = session_name
        return cls(
            policy=policy, client=client, blackboard=blackboard,
            task_ledger=task_ledger, progress_ledger=progress_ledger,
            agents=agents, config=cfg,
        )

    # --------------------------------------------------------------- public run

    def run_paper(self, topic: str) -> dict[str, Any]:
        """Execute the full plan until done or stalled."""
        log.info("pipeline_start", topic=topic, session=self.cfg.session_name)
        self.policy.start_new_paper()

        # Seed the task ledger with the topic as the top-level goal
        self.tl.add_fact(f"Research topic: {topic}")
        self._checkpoint()

        try:
            while not self.tl.all_done():
                step = self.tl.next_pending()
                if step is None:
                    log.info("no_pending_steps")
                    break
                if self._total_agent_calls >= self.cfg.max_total_agent_calls:
                    log.warning("global_call_cap_reached",
                                cap=self.cfg.max_total_agent_calls)
                    break
                self._execute_step(step)
        except GlobalStallDetected as e:
            log.error("global_stall", err=str(e))
            return self._final_report(status="escalated")
        except BudgetExceeded as e:
            log.error("budget_exhausted", err=str(e))
            return self._final_report(status="budget_exceeded")

        return self._final_report(status="complete" if self.tl.all_done() else "stopped")

    # ----------------------------------------------------------- step executor

    def _execute_step(self, step: PlanStep) -> None:
        """Drive a single step to completion (or stall)."""
        # 1. Check inputs are present on blackboard
        missing_inputs = [
            i for i in step.required_inputs
            if not self.bb.has(ArtifactName(i))
        ]
        if missing_inputs:
            log.warning("step_missing_inputs",
                        step_id=step.id, missing=missing_inputs)
            self.tl.mark_step(step.id, "blocked")
            return

        self.pl.enter_step(step)
        self.tl.mark_step(step.id, "in_progress")
        agent = self.agents[step.assignee]

        # 2. Drive the step until progress or stall
        try:
            while True:
                before = snapshot_artifact_versions(self.bb)
                self._invoke_agent_for_step(agent, step)
                outcome = self.pl.record_call_outcome(
                    step=step, blackboard=self.bb, before_versions=before,
                )
                if outcome == "progress":
                    # Check if ALL required outputs are now present
                    all_outputs = all(
                        self.bb.has(ArtifactName(o)) for o in step.produces
                    )
                    if all_outputs:
                        self.tl.mark_step(step.id, "done")
                        self.pl.leave_step(success=True)
                        self._checkpoint()
                        return
                    # keep iterating — more outputs still needed
        except StallDetected as e:
            log.warning("step_stalled", **{
                "step_id": e.step_id,
                "stall_count": e.stall_count,
                "reason": e.reason,
            })
            self._regenerate_via_commander(stalled_step=step, reason=e.reason)

    # ---------------------------------------------------------- agent invoke

    def _invoke_agent_for_step(self, agent: BaseAgent, step: PlanStep) -> None:
        """Call the assigned agent with blackboard context + step prompt."""
        self._total_agent_calls += 1

        shared = self.bb.snapshot_for_agent(agent.role)
        ledgers_context = (
            self.tl.render_for_prompt() + "\n\n" + self.pl.render_for_prompt()
        )
        full_shared = ledgers_context + "\n\n" + shared if shared else ledgers_context

        user_turn = self._build_step_directive(step)
        task_hint = self._task_hint_for(agent.role, step)

        if self.cfg.dry_run:
            log.info("dry_run_skip", agent=agent.role, step_id=step.id,
                     task_type=task_hint)
            return

        try:
            result = agent.think(
                user_turn=user_turn,
                task_type=task_hint,
                shared_artifacts=full_shared,
                remember=False,   # blackboard IS the memory
            )
        except BudgetExceeded:
            # Budget is a hard stop — propagate to run_paper, which turns it
            # into a clean `budget_exceeded` report.
            raise
        except Exception as e:
            # Any other agent-call failure (permission denied, API error,
            # prompt-parse crash, etc.) is logged and treated like an empty
            # reply so the step's stall counter increments and the pipeline
            # can either retry or mark the step blocked instead of crashing.
            log.error("agent_think_failed",
                      agent=agent.role, step_id=step.id,
                      err_type=type(e).__name__, err=str(e)[:400])
            return

        # Let the agent extract+publish artifacts it was supposed to produce.
        # In python-native mode, we assume the agent embeds artifacts in its
        # reply using a simple block syntax. The parser is defensive so bad
        # output doesn't crash the pipeline.
        self._publish_from_reply(
            agent_role=agent.role,
            reply=result["text"],
            step=step,
        )

    @staticmethod
    def _task_hint_for(agent_role: str, step: PlanStep) -> str:
        """Map (role, step) → a task_type the router recognizes.
        Keeps routing decisions declarative.

        Matching is substring-based (case-insensitive) so regenerated plans
        with variant step IDs like ``S4a_design_v2`` still route correctly.
        """
        sid = step.id.lower()
        if agent_role == "idea":
            if "novelty" in sid:
                return "novelty_analysis"
            return "storyline_design"
        if agent_role == "librarian":
            return "lookup_citation"
        if agent_role == "experimenter":
            return "design_experiment" if "design" in sid else "implement_code"
        if agent_role == "reviewer":
            return "proofread_text" if "polish" in sid else "review_code"
        if agent_role == "writer":
            return "draft_section"
        return "draft_section"

    @staticmethod
    def _build_step_directive(step: PlanStep) -> str:
        """Concise directive for the agent describing what to produce."""
        lines = [
            f"## Active step: {step.id}",
            f"Description: {step.description}",
        ]
        if step.required_inputs:
            lines.append(f"You are expected to have read: {', '.join(step.required_inputs)}")
        if step.produces:
            lines.append(f"You MUST publish these artifacts before finishing:")
            lines.extend(f"  - {o}" for o in step.produces)
        lines.append("")
        lines.append(
            "Publish each artifact using this exact block format (one per output):"
        )
        lines.append("```artifact")
        lines.append("name: <artifact_name>")
        lines.append("kind: text      # one of: text | json | file")
        lines.append("payload: |")
        lines.append("  <the content>")
        lines.append("```")
        lines.append("")
        lines.append("Do not add commentary outside the artifact blocks unless it is "
                     "a one-line acknowledgement.")
        return "\n".join(lines)

    def _publish_from_reply(
        self, *, agent_role: str, reply: str, step: PlanStep
    ) -> None:
        """Parse `artifact` code-fenced blocks from an agent reply and publish
        them. Tolerant of whitespace; skips malformed blocks.
        """
        import re
        import yaml
        from core.artifacts import ArtifactContractViolation

        pattern = re.compile(
            r"```\s*artifact\s*\n(.*?)```",
            re.DOTALL | re.IGNORECASE,
        )
        matches = pattern.findall(reply)
        if not matches:
            log.debug("no_artifact_blocks_in_reply", agent=agent_role,
                      reply_preview=reply[:200])
            return

        published = 0
        for block in matches:
            try:
                data = yaml.safe_load(block)
                if not isinstance(data, dict):
                    continue
                name = data.get("name")
                kind = data.get("kind", "text")
                payload = data.get("payload")
                if not name or payload is None:
                    continue
                try:
                    art_name = ArtifactName(name)
                except ValueError:
                    log.warning("unknown_artifact_name", name=name, by=agent_role)
                    continue
                try:
                    self.bb.publish(
                        agent=agent_role,
                        name=art_name,
                        payload=payload,
                        kind=PayloadKind(kind),
                    )
                    published += 1
                except ArtifactContractViolation as e:
                    # Agent tried to publish something it's not allowed to —
                    # this is a prompt-compliance bug, distinct from a parse
                    # failure. Surface it loudly so stall detection and the
                    # next prompt-build cycle can respond.
                    log.error("artifact_contract_violation",
                              agent=agent_role, name=name, err=str(e))
            except Exception as e:
                log.warning("artifact_parse_failed",
                            agent=agent_role, err=str(e))
        log.info("artifacts_published_from_reply",
                 agent=agent_role, count=published, step_id=step.id)

    # -------------------------------------------------------- regeneration path

    def _regenerate_via_commander(
        self, *, stalled_step: PlanStep, reason: str,
    ) -> None:
        """Ask Commander (Opus) to produce a revised plan and install it.

        Protocol: we ask Commander for a JSON object of the form:

            {
              "plan": [
                {"id": "S1", "description": "...",
                 "assignee": "idea|librarian|experimenter|reviewer|writer",
                 "required_inputs": ["..."], "produces": ["..."]}
              ],
              "additional_facts": ["..."],        # optional
              "additional_questions": ["..."]     # optional
            }

        If the reply parses cleanly and the plan is non-empty and contains
        only valid assignee roles, `self.tl.regenerate(...)` replaces the
        live plan in-place. Facts/questions accumulate across regenerations.

        Failure modes are handled gracefully: a parse or validation error
        falls back to the minimal retry/block policy (bump attempts, mark
        blocked after 2 failures) so the pipeline makes some progress
        instead of looping indefinitely on a malformed Commander reply.
        """
        self.pl.leave_step(success=False)
        self.pl.note_regeneration()           # may raise GlobalStallDetected

        commander = self.agents.get("commander")
        if commander is None or self.cfg.dry_run:
            if self.cfg.dry_run:
                log.info("dry_run_regeneration_skipped")
            else:
                log.warning("regeneration_no_commander_agent")
            self._bump_stall_attempts(stalled_step)
            return

        tl_text = self.tl.render_for_prompt()
        context = self.bb.snapshot_for_agent("commander")
        prompt = (
            f"## Pipeline stalled on step {stalled_step.id}\n"
            f"Reason: {reason}\n"
            f"Step description: {stalled_step.description}\n"
            f"Step assignee: {stalled_step.assignee}\n\n"
            "## Current Task Ledger\n"
            f"{tl_text}\n\n"
            "Propose a REPLACEMENT plan. Reply with ONLY a JSON object of "
            "the shape:\n"
            '  {"plan": [\n'
            '    {"id": "S1", "description": "...",\n'
            '     "assignee": "idea|librarian|experimenter|reviewer|writer",\n'
            '     "required_inputs": ["..."], "produces": ["..."]}\n'
            "  ],\n"
            '  "additional_facts": [],\n'
            '  "additional_questions": []}\n\n'
            "Constraints:\n"
            "- at least one step\n"
            "- every assignee must be one of the five worker roles above\n"
            "- step ids should be short ASCII tokens (S1, S2a, ...)\n"
            "- required_inputs and produces must reference artifact names "
            "defined in core/artifacts.py:ArtifactName\n"
            "- no markdown fences, no preamble, no trailing commentary"
        )

        try:
            result = commander.think(
                user_turn=prompt,
                task_type="orchestrate",
                shared_artifacts=context,
                remember=False,
            )
        except BudgetExceeded:
            raise
        except Exception as e:
            log.error("regeneration_api_call_failed",
                      err_type=type(e).__name__, err=str(e)[:300])
            self._bump_stall_attempts(stalled_step)
            return

        reply_text = (result.get("text") or "").strip()
        parsed = self._parse_regen_reply(reply_text)
        if parsed is None:
            log.warning("regeneration_reply_unparseable",
                        step_id=stalled_step.id,
                        reply_preview=reply_text[:300])
            self._bump_stall_attempts(stalled_step)
            return

        new_plan, add_facts, add_questions = parsed
        try:
            self.tl.regenerate(
                new_plan=new_plan,
                additional_facts=add_facts,
                additional_questions=add_questions,
            )
        except Exception as e:
            log.error("regeneration_install_failed", err=str(e))
            self._bump_stall_attempts(stalled_step)
            return

        log.warning("plan_regenerated",
                    stalled_step=stalled_step.id,
                    new_steps=len(new_plan),
                    generation=self.tl.generation)
        # New plan is installed; the outer run_paper loop will pick its
        # first pending step on the next iteration. We do NOT bump
        # attempts on the stalled step — it's a different plan now.

    @staticmethod
    def _parse_regen_reply(
        text: str,
    ) -> tuple[list[PlanStep], list[str], list[str]] | None:
        """Parse Commander's replan JSON. Return None on any validation
        failure. The caller decides what to do with a None (fall back to
        retry/block)."""
        import json as _json
        from agents import WORKER_REGISTRY

        # Strip accidental fences even though we asked for none.
        t = text.strip()
        if t.startswith("```"):
            t = t.strip("`").lstrip()
            if t.startswith("json"):
                t = t[4:].lstrip()
        try:
            obj = _json.loads(t)
        except Exception:
            return None
        if not isinstance(obj, dict):
            return None
        raw_plan = obj.get("plan")
        if not isinstance(raw_plan, list) or not raw_plan:
            return None

        valid_roles = set(WORKER_REGISTRY.keys())
        new_plan: list[PlanStep] = []
        seen_ids: set[str] = set()
        for entry in raw_plan:
            if not isinstance(entry, dict):
                return None
            sid = entry.get("id")
            desc = entry.get("description")
            assignee = entry.get("assignee")
            if not (isinstance(sid, str) and sid
                    and isinstance(desc, str) and desc
                    and isinstance(assignee, str)
                    and assignee in valid_roles):
                return None
            if sid in seen_ids:
                return None
            seen_ids.add(sid)
            req = entry.get("required_inputs") or []
            prod = entry.get("produces") or []
            if not (isinstance(req, list) and isinstance(prod, list)):
                return None
            new_plan.append(PlanStep(
                id=sid, description=desc, assignee=assignee,
                required_inputs=[str(x) for x in req],
                produces=[str(x) for x in prod],
            ))

        add_facts = [str(x) for x in obj.get("additional_facts") or []
                     if isinstance(x, (str, int, float))]
        add_questions = [str(x) for x in obj.get("additional_questions") or []
                         if isinstance(x, (str, int, float))]
        return new_plan, add_facts, add_questions

    def _bump_stall_attempts(self, step: PlanStep) -> None:
        """Fallback used whenever regeneration can't install a new plan."""
        step.attempts += 1
        if step.attempts >= 2:
            self.tl.mark_step(step.id, "blocked")
            log.warning("step_abandoned", step_id=step.id)
        else:
            self.tl.mark_step(step.id, "pending")

    # -------------------------------------------------------------- checkpoint

    def _checkpoint(self) -> None:
        """Persist blackboard + ledgers so we can resume after crash."""
        from core.paths import paths_for
        paths = paths_for(self.cfg.project_root)
        session_dir = paths.sessions / self.cfg.session_name
        session_dir.mkdir(parents=True, exist_ok=True)
        self.bb.save(session_dir / "blackboard.json")
        self.tl.save(session_dir / "task_ledger.json")
        log.debug("checkpoint_written", dir=str(session_dir))

    # ------------------------------------------------------------------ report

    def _final_report(self, *, status: str) -> dict[str, Any]:
        report = {
            "status": status,
            "session": self.cfg.session_name,
            "total_agent_calls": self._total_agent_calls,
            "policy_report": self.policy.report(),
            "blackboard_summary": self.bb.summary(),
            "progress_status": self.pl.current_status(self.tl),
            "plan": [
                {"id": s.id, "status": s.status, "attempts": s.attempts}
                for s in self.tl.plan
            ],
        }
        log.info("pipeline_end", **{"status": status,
                                    "calls": self._total_agent_calls})
        self._checkpoint()
        return report
