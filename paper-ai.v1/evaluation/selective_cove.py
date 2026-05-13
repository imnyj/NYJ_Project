"""Selective Chain-of-Verification (CoVe).

Research: Dhuliawala et al., "Chain-of-Verification Reduces Hallucination"
(arXiv:2309.11495, 2023).

Classic CoVe = 4 steps:
    1. Baseline response
    2. Plan verifications (generate independent QA questions)
    3. Answer verifications (FACTORED — each Q answered independently,
       without the baseline as context, to prevent copying forward
       hallucinations)
    4. Revise

Token cost: ~5× the baseline. Far too expensive to run on every paragraph.

Selective CoVe (our twist): only invoke CoVe on claims that the
ConfidenceTracker flagged (tier=FLAGGED, 0.4 ≤ score < 0.7). In practice
this is ~15% of claims, so net cost is ~1.6× baseline instead of 5×.

Integration:
    - Citation audit populates tracker with citation-level confidences.
    - Reviewer (PROOFREADER mode) calls SelectiveCoVe.run() after audit.
    - The loop revises only flagged claims, leaves TRUSTED/NORMAL alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.logger import get_logger

log = get_logger("selective_cove")

if TYPE_CHECKING:
    from evaluation.confidence_tracker import ConfidenceRecord, ConfidenceTracker
    from tools.anthropic_client import AnthropicClient


PLAN_VERIFICATIONS_PROMPT = """Given the following claim, generate 2-3
independent verification questions whose answers would confirm or refute
the claim. Each question must be answerable without reading the original
draft — the reader should only need the cited sources.

Output as a JSON array of question strings. No preamble.

Claim: {claim}
"""

ANSWER_VERIFICATION_PROMPT = """Answer the following question using ONLY
the provided reference abstract(s). If the abstract does not contain
enough information to answer, reply exactly: "INSUFFICIENT".

Question: {question}

Reference abstract(s):
{abstracts}
"""

REVISE_PROMPT = """The following claim is potentially incorrect because
the verification answers contradict or fail to support it. Produce a
revised claim that is consistent with the verification evidence, OR state
that the claim should be removed.

Original claim: {claim}

Verification QA:
{qa_pairs}

Return JSON: {{"action": "revise"|"remove"|"keep", "new_claim": "..."}}
"""


@dataclass
class VerificationQA:
    question: str
    answer: str = ""
    insufficient: bool = False


@dataclass
class CoVeOutcome:
    subject_id: str
    original_claim: str
    action: str = "keep"            # "revise" | "remove" | "keep"
    new_claim: str | None = None
    qa: list[VerificationQA] = field(default_factory=list)
    reasoning: str = ""

    def summary(self) -> str:
        return (
            f"{self.subject_id}: {self.action}"
            + (f" → {self.new_claim[:80]!r}" if self.new_claim else "")
        )


# ===================================================================== engine

class SelectiveCoVe:
    """Run CoVe only on flagged claims."""

    def __init__(
        self,
        client: "AnthropicClient",
        tracker: "ConfidenceTracker",
        *,
        agent: str = "reviewer",
        verify_task_type: str = "classify",   # Haiku — factored answers
        revise_task_type: str = "proofread_text",
    ):
        self.client = client
        self.tracker = tracker
        self.agent = agent
        self.verify_task_type = verify_task_type
        self.revise_task_type = revise_task_type

    # ---------------------------------------------------------- run

    def run(
        self,
        *,
        claim_texts: dict[str, str],      # subject_id → claim sentence
        evidence: dict[str, str],         # subject_id → concatenated abstracts
        subject_type: str = "citation",
    ) -> list[CoVeOutcome]:
        """Inspect tracker; CoVe each FLAGGED record found in claim_texts."""
        flagged = self.tracker.needs_deep_verification(subject_type=subject_type)
        if not flagged:
            log.info("selective_cove_skipped_no_flagged", type=subject_type)
            return []

        log.info("selective_cove_start",
                 n_flagged=len(flagged), subject_type=subject_type)
        outcomes: list[CoVeOutcome] = []
        for rec in flagged:
            claim = claim_texts.get(rec.subject_id)
            if not claim:
                continue
            ev = evidence.get(rec.subject_id, "")
            outcome = self._cove_one(rec, claim, ev)
            outcomes.append(outcome)
        log.info("selective_cove_done",
                 processed=len(outcomes),
                 revised=sum(1 for o in outcomes if o.action == "revise"),
                 removed=sum(1 for o in outcomes if o.action == "remove"),
                 kept=sum(1 for o in outcomes if o.action == "keep"))
        return outcomes

    # ---------------------------------------------------------- per-claim

    def _cove_one(
        self,
        record: "ConfidenceRecord",
        claim: str,
        evidence: str,
    ) -> CoVeOutcome:
        outcome = CoVeOutcome(subject_id=record.subject_id,
                              original_claim=claim)

        # Step 2: plan verifications
        try:
            questions = self._plan_verifications(claim)
        except Exception as e:
            outcome.reasoning = f"plan failed: {e!r}"
            return outcome
        if not questions:
            outcome.reasoning = "no verification questions generated"
            return outcome

        # Step 3: factored answering (no baseline, each Q isolated)
        qa: list[VerificationQA] = []
        insufficient_count = 0
        for q in questions:
            try:
                ans = self._answer_factored(q, evidence)
            except Exception as e:
                ans = "INSUFFICIENT"
                log.debug("cove_answer_failed", q=q[:80], err=str(e))
            vqa = VerificationQA(question=q, answer=ans)
            if ans.strip().upper().startswith("INSUFFICIENT"):
                vqa.insufficient = True
                insufficient_count += 1
            qa.append(vqa)
        outcome.qa = qa

        # Step 4: decide
        if insufficient_count == len(qa):
            # Abstract didn't support the claim on any dimension → remove
            outcome.action = "remove"
            outcome.reasoning = "all verifications INSUFFICIENT"
            return outcome
        # Otherwise ask the revise model to decide
        try:
            decision = self._revise(claim, qa)
            outcome.action = decision.get("action", "keep")
            outcome.new_claim = decision.get("new_claim")
            outcome.reasoning = decision.get("reasoning", "")
        except Exception as e:
            outcome.reasoning = f"revise failed: {e!r}"
        return outcome

    # ---------------------------------------------------- step helpers

    def _plan_verifications(self, claim: str) -> list[str]:
        import json
        result = self.client.call(
            agent=self.agent,
            user_turn=PLAN_VERIFICATIONS_PROMPT.format(claim=claim),
            task_type=self.verify_task_type,
        )
        text = (result.get("text") or "").strip()
        # Attempt to extract a JSON array
        try:
            arr = json.loads(_extract_json_block(text))
            if isinstance(arr, list):
                return [str(q).strip() for q in arr if str(q).strip()]
        except Exception:
            # fallback: split on newlines starting with a digit/dash
            lines = [l.strip(" -*0123456789.") for l in text.splitlines() if l.strip()]
            return [l for l in lines if len(l) > 10][:3]
        return []

    def _answer_factored(self, question: str, evidence: str) -> str:
        """Each Q answered in a FRESH session (no baseline claim leak)."""
        result = self.client.call(
            agent=self.agent,
            user_turn=ANSWER_VERIFICATION_PROMPT.format(
                question=question,
                abstracts=evidence or "(no abstract available)",
            ),
            task_type=self.verify_task_type,
        )
        return (result.get("text") or "").strip()

    def _revise(
        self, claim: str, qa: list[VerificationQA],
    ) -> dict[str, Any]:
        import json
        qa_text = "\n\n".join(
            f"Q: {v.question}\nA: {v.answer}"
            + (" [INSUFFICIENT]" if v.insufficient else "")
            for v in qa
        )
        result = self.client.call(
            agent=self.agent,
            user_turn=REVISE_PROMPT.format(claim=claim, qa_pairs=qa_text),
            task_type=self.revise_task_type,
        )
        text = (result.get("text") or "").strip()
        try:
            return json.loads(_extract_json_block(text))
        except Exception:
            return {"action": "keep", "new_claim": None,
                    "reasoning": "revise parse failed; kept original"}


def _extract_json_block(text: str) -> str:
    """Find the first {...} or [...] balanced block in text.

    Respects string literals so that braces/brackets inside JSON strings
    don't throw off the nesting count.
    """
    import re
    # Try fenced ```json first
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Else first brace/bracket block
    stack: list[str] = []
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "[{":
            if not stack:
                start = i
            stack.append(ch)
        elif ch in "]}":
            if stack:
                stack.pop()
                if not stack and start != -1:
                    return text[start:i + 1]
    return text  # let json.loads fail and caller handle
