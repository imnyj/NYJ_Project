"""Anthropic Message Batches API wrapper.

Batches API provides a flat 50% discount on input + output for batches
processed within 24h (usually minutes). Stacks multiplicatively with
prompt caching — a cache-hit call inside a batch costs 0.1 × 0.5 = 0.05×
the base rate. That's the ~95% discount in the research report.

When to use:
    - Librarian bulk literature scanning (one request per paper)
    - Visualization generating many figures for a sweep
    - Proofreader running ensemble reviews on different sections

When NOT to use:
    - Interactive debugging — Batches can take minutes to an hour
    - Small bursts (< 10 requests) — the overhead isn't worth it
    - Realtime orchestration steps

API pattern (mid-2024+):
    client.messages.batches.create(requests=[...])
    → returns batch id
    poll client.messages.batches.retrieve(batch_id)
    when "ended" → iterate results via client.messages.batches.results(batch_id)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable

from core.logger import get_logger

log = get_logger("batch_client")

if TYPE_CHECKING:
    from core.policy_runtime import PolicyRuntime


@dataclass
class BatchRequest:
    """One request inside a batch. Maps 1:1 to AnthropicClient.call() args."""
    custom_id: str                       # user-chosen stable id for result matching
    agent: str
    user_turn: str
    task_type: str | None = None
    force_model: str | None = None
    shared_artifacts: str | None = None
    tool_schemas: list[dict[str, Any]] | None = None
    max_tokens: int | None = None


@dataclass
class BatchResult:
    custom_id: str
    text: str = ""
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    raw: Any = None

    def ok(self) -> bool:
        return self.error is None


class BatchClient:
    """High-level wrapper around anthropic.messages.batches."""

    def __init__(
        self,
        anthropic_client,
        policy: "PolicyRuntime",
    ):
        """anthropic_client: our tools.anthropic_client.AnthropicClient.
        We reuse its underlying SDK client + prompt assembly logic.
        """
        self._ac = anthropic_client       # AnthropicClient (ours)
        self._sdk = anthropic_client._client   # raw anthropic.Anthropic
        self.policy = policy

    # ========================================================= submit

    def submit(
        self,
        requests: Iterable[BatchRequest],
    ) -> str:
        """Submit a batch; return the batch id."""
        payload: list[dict[str, Any]] = []
        for req in requests:
            route = self.policy.route(
                req.agent, req.task_type, force_model=req.force_model,
            )
            system_blocks = self._ac._build_system_blocks(
                agent=req.agent,
                tool_schemas=req.tool_schemas,
                shared_artifacts=req.shared_artifacts,
                extra_context=None,
                model=route["model"],
            )
            messages = [{"role": "user", "content": req.user_turn}]
            params: dict[str, Any] = {
                "model": route["model"],
                "max_tokens": req.max_tokens or route["max_tokens"],
                "system": system_blocks,
                "messages": messages,
            }
            if req.tool_schemas:
                params["tools"] = req.tool_schemas
            payload.append({
                "custom_id": req.custom_id,
                "params": params,
            })

        log.info("batch_submit", count=len(payload))
        batch = self._sdk.messages.batches.create(requests=payload)
        log.info("batch_submitted", batch_id=batch.id, count=len(payload))
        return batch.id

    # ========================================================= poll

    def poll(
        self,
        batch_id: str,
        *,
        interval: float = 15.0,
        timeout: float = 24 * 3600.0,
    ) -> str:
        """Block until batch ends (or timeout). Returns the final status."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            b = self._sdk.messages.batches.retrieve(batch_id)
            status = getattr(b, "processing_status", None) or \
                     getattr(b, "status", "unknown")
            log.debug("batch_poll", batch_id=batch_id, status=status)
            if status in ("ended", "completed", "failed", "canceled"):
                log.info("batch_ended", batch_id=batch_id, status=status)
                return status
            time.sleep(interval)
        raise TimeoutError(f"batch {batch_id} did not end within {timeout}s")

    # ========================================================= collect

    def collect(self, batch_id: str) -> list[BatchResult]:
        """Iterate all results; record cost against policy."""
        results: list[BatchResult] = []
        stream = self._sdk.messages.batches.results(batch_id)
        for item in stream:
            # SDK returns JSONL-parsed objects; each has `custom_id` + `result`
            cid = getattr(item, "custom_id", "")
            res = getattr(item, "result", None)
            if res is None:
                results.append(BatchResult(custom_id=cid, error="no result"))
                continue
            rtype = getattr(res, "type", "")
            if rtype == "succeeded":
                msg = getattr(res, "message", None)
                text = self._ac._extract_text(msg)
                usage = self._ac._extract_usage(msg)
                model = getattr(msg, "model", "")
                # Batches API is 0.5× base; record at effective rate
                self._record_batch_cost(model, usage)
                results.append(BatchResult(
                    custom_id=cid, text=text, model=model,
                    usage=usage, raw=msg,
                ))
            else:
                err = getattr(res, "error", None)
                results.append(BatchResult(
                    custom_id=cid,
                    error=str(err) if err else f"type={rtype}",
                ))
        log.info("batch_collected",
                 batch_id=batch_id,
                 total=len(results),
                 ok=sum(1 for r in results if r.ok()))
        return results

    # ========================================================= high-level

    def run(
        self,
        requests: list[BatchRequest],
        *,
        poll_interval: float = 15.0,
        timeout: float = 24 * 3600.0,
    ) -> list[BatchResult]:
        """Submit → poll → collect in one call."""
        batch_id = self.submit(requests)
        status = self.poll(batch_id, interval=poll_interval, timeout=timeout)
        if status not in ("ended", "completed"):
            log.warning("batch_nonsuccess_status",
                        batch_id=batch_id, status=status)
        return self.collect(batch_id)

    # ==================================================== cost tracking

    def _record_batch_cost(self, model: str, usage: dict[str, int]) -> None:
        """Batches get 50% off input+output. We pass a DIVIDED usage dict
        to policy_runtime.record_call() so the spend tracker stays
        accurate.
        """
        halved = {
            "input_tokens":              usage.get("input_tokens", 0) // 2,
            "output_tokens":             usage.get("output_tokens", 0) // 2,
            "cache_read_input_tokens":   usage.get("cache_read_input_tokens", 0) // 2,
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0) // 2,
        }
        self.policy.record_call(model, halved)


def new_custom_id(prefix: str = "req") -> str:
    """Generate a stable unique id for a batch request."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
