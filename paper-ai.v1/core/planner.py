"""ReWOO planner: plan all tool calls up front, then execute.

Research: Xu et al., "ReWOO: Decoupling Reasoning from Observations for
Efficient Augmented Language Models" (arXiv:2305.18323), 2023.

vs ReAct:
    ReAct re-prompts the FULL growing trajectory at every step. With N
    tool calls, the LLM pays N × (system + accumulated observations).
    In multi-agent systems this is ~15× more tokens than a single chat
    (per Anthropic's own multi-agent research system post).

    ReWOO emits the whole plan upfront with #E placeholders referencing
    future tool outputs, executes the tools, then does ONE final Solve
    call. Regardless of step count, only 2 LLM calls total.

Measured: -64% avg token reduction across 6 benchmarks, 5× fewer on
HotpotQA WITH +4% accuracy (paper table 2).

Plan format we emit:
    Plan: <brief description of approach>
    #E1 = tool_name[arg1, arg2, ...]
    #E2 = tool_name[arg referencing #E1]
    #E3 = tool_name[literal arg]

Rules enforced by the parser:
    - Every #E_id occurs on exactly one line (left-hand side).
    - #E references in args must be to PREVIOUS ids only (no cycles).
    - Tool name must be in the available-tools manifest.
    - Args are parsed as a single string and passed to the tool verbatim;
      complex structured args should be JSON-quoted inside the brackets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.logger import get_logger

log = get_logger("planner")

if TYPE_CHECKING:
    from tools.anthropic_client import AnthropicClient


# =============================================================== DTOs

@dataclass
class PlanStep:
    """One step of a ReWOO plan."""
    id: str                                  # "#E1"
    tool: str                                # "web_search" | "code_executor" ...
    raw_args: str                            # original bracket content
    depends_on: list[str] = field(default_factory=list)   # ["#E1", "#E2"]
    result: Any = None                       # filled in at execution time
    error: str | None = None

    @property
    def is_done(self) -> bool:
        return self.result is not None or self.error is not None


@dataclass
class Plan:
    """Parsed ReWOO plan ready for execution."""
    description: str
    steps: list[PlanStep]
    question: str                            # original user question
    raw: str                                 # original plan text (for Solve)

    def step_map(self) -> dict[str, PlanStep]:
        return {s.id: s for s in self.steps}

    def validate(self, available_tools: set[str]) -> list[str]:
        """Return list of error strings; empty means valid."""
        errors: list[str] = []
        seen: set[str] = set()
        for i, s in enumerate(self.steps):
            if s.id in seen:
                errors.append(f"duplicate id {s.id}")
            seen.add(s.id)
            if s.tool not in available_tools:
                errors.append(f"step {s.id}: unknown tool {s.tool!r}")
            for d in s.depends_on:
                if d == s.id:
                    errors.append(f"step {s.id}: self-reference")
                elif d not in seen:
                    errors.append(
                        f"step {s.id}: references {d} which is not "
                        f"defined earlier (forward reference or missing)"
                    )
        return errors


# =============================================================== prompts

PLANNER_SYSTEM_PROMPT = """You produce ReWOO-style execution plans.

Output format (STRICT):

Plan: <one-sentence description of the approach>
#E1 = tool_name[argument string]
#E2 = tool_name[argument referencing #E1]
...

Rules:
- Use ONLY tools listed under "Available tools".
- Each #E_id must appear on exactly one line as a left-hand side.
- References to prior steps go inside the argument, e.g. #E1.
- Keep arg strings concise; for JSON, place the JSON inline with no quoting tricks.
- Do NOT emit a Solve step — synthesis happens after execution.
- Do NOT add prose outside the Plan lines.
"""


SOLVER_SYSTEM_PROMPT = """You synthesize a final answer from executed ReWOO plan steps.

You receive the original question, the original plan, and the observed
output of each step. Your job is to answer the question clearly and
concisely. Cite step ids (#E1, #E2) when you rely on their outputs.
"""


_STEP_RE = re.compile(
    r"^\s*#E(?P<num>\d+)\s*=\s*(?P<tool>[A-Za-z_][A-Za-z0-9_]*)\s*\[(?P<args>.*)\]\s*$"
)
_REF_RE = re.compile(r"#E\d+")
_PLAN_RE = re.compile(r"^\s*Plan\s*:\s*(?P<desc>.+?)\s*$", re.IGNORECASE)


def parse_plan(raw: str, question: str) -> Plan:
    """Convert raw LLM output into a structured Plan."""
    description = ""
    steps: list[PlanStep] = []

    for line in raw.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        m = _PLAN_RE.match(line)
        if m and not description:
            description = m.group("desc").strip()
            continue
        m = _STEP_RE.match(line)
        if m:
            num = m.group("num")
            tool = m.group("tool").strip()
            args = m.group("args").strip()
            deps = sorted(set(_REF_RE.findall(args)))
            steps.append(PlanStep(
                id=f"#E{num}",
                tool=tool,
                raw_args=args,
                depends_on=deps,
            ))
    return Plan(description=description, steps=steps, question=question, raw=raw)


# =============================================================== planner

class ReWOOPlanner:
    """Build and synthesize ReWOO plans. Execution is delegated to
    `core.dag_executor.DAGExecutor` so planning and running are decoupled.
    """

    def __init__(
        self,
        client: "AnthropicClient",
        *,
        agent: str = "commander",
        planner_task_type: str = "orchestrate",
        solver_task_type: str = "draft_section",
    ):
        self.client = client
        self.agent = agent
        self.planner_task_type = planner_task_type
        self.solver_task_type = solver_task_type

    # --------------------------------------------------------- plan call

    def plan(
        self,
        question: str,
        *,
        available_tools: list[dict[str, Any]],
    ) -> Plan:
        """Generate a plan via one LLM call.

        `available_tools` is the Anthropic tool-schema list; we only use
        each dict's `name` + `description` to brief the planner.
        """
        if not available_tools:
            return Plan(description="no tools available", steps=[],
                        question=question, raw="")
        tools_manifest = "\n".join(
            f"- **{t['name']}**: {t.get('description','')[:200]}"
            for t in available_tools
        )
        tool_names = {t["name"] for t in available_tools}

        prompt = (
            f"{PLANNER_SYSTEM_PROMPT}\n\n"
            f"Available tools:\n{tools_manifest}\n\n"
            f"Question: {question}\n"
        )
        result = self.client.call(
            agent=self.agent,
            user_turn=prompt,
            task_type=self.planner_task_type,
        )
        raw = result["text"]
        plan = parse_plan(raw, question)

        errors = plan.validate(tool_names)
        if errors:
            log.warning("plan_validation_issues", n=len(errors), errors=errors[:5])
        log.info("plan_generated", n_steps=len(plan.steps), errors=len(errors))
        return plan

    # --------------------------------------------------------- solve call

    def solve(
        self,
        plan: Plan,
        *,
        additional_context: str = "",
    ) -> dict[str, Any]:
        """Feed executed plan results to the LLM for final synthesis."""
        trace_lines: list[str] = []
        for s in plan.steps:
            if s.error:
                trace_lines.append(f"{s.id} [ERROR]: {s.error}")
            else:
                snippet = _truncate(str(s.result), 2000)
                trace_lines.append(f"{s.id} ({s.tool}): {snippet}")
        trace = "\n\n".join(trace_lines) if trace_lines else "(no steps)"

        prompt = (
            f"{SOLVER_SYSTEM_PROMPT}\n\n"
            f"Question: {plan.question}\n\n"
            f"Original plan:\n{plan.raw}\n\n"
            f"Executed step results:\n{trace}\n"
        )
        if additional_context:
            prompt += f"\nAdditional context:\n{additional_context}\n"

        return self.client.call(
            agent=self.agent,
            user_turn=prompt,
            task_type=self.solver_task_type,
        )


# =============================================================== helpers

def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + f"\n... [truncated {len(s) - n} chars]"


def substitute_refs(raw_args: str, resolved: dict[str, Any]) -> str:
    """Replace all #E_id tokens in `raw_args` with their resolved outputs.

    If a reference is unresolved, the token is left intact and the caller
    can decide whether to skip the step or mark it errored.
    """
    def repl(match: re.Match) -> str:
        token = match.group(0)
        if token in resolved:
            return _truncate(str(resolved[token]), 3000)
        return token
    return _REF_RE.sub(repl, raw_args)
