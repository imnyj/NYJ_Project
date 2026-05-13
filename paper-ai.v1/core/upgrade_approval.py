"""CLI user-approval gate for self-upgrades.

The user's explicit rule from the early design session:

  > "commander의 업그레이드는 나와의 작업 중 언제든 나에게 허락을 요청할 것.
     나의 허락이 떨어졌을 때만 수행."

This module implements that gate. It is intentionally the ONLY path through
which any self-modification may happen — `core/self_upgrader.py` always
calls through here, never around it.

Interactive prompt format:

    ================ UPGRADE REQUEST ================
    Reason: <why the upgrade is needed>
    Target files: [...]
    Impact scope: [...]
    Estimated tokens: N

    --- DIFF PREVIEW ---
    ...unified diff...

    [y] approve | [N] deny (default) | [d] show full diff | [r] ask reason
    > _

Non-interactive runs (scripts, watchdog re-exec) can supply an
AutoApproval policy that ALWAYS denies, so no upgrade ever happens without
a human in the loop.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from core.logger import get_logger

log = get_logger("upgrade_approval")


@dataclass
class UpgradeRequest:
    """Payload describing a proposed self-modification."""
    reason: str
    target_files: list[str]
    diff_preview: str
    estimated_tokens: int
    impact_scope: list[str] = field(default_factory=list)
    extra_context: str = ""
    request_id: str = ""
    requested_at: float = field(default_factory=time.time)

    def render_summary(self) -> str:
        lines = [
            "=" * 60,
            "             COMMANDER UPGRADE REQUEST",
            "=" * 60,
            f"Reason: {self.reason}",
            "",
            f"Target files ({len(self.target_files)}):",
            *[f"  - {f}" for f in self.target_files],
            "",
            f"Impact scope: {', '.join(self.impact_scope) or '(unstated)'}",
            f"Estimated tokens: {self.estimated_tokens:,}",
            "",
            "--- DIFF PREVIEW (truncated) ---",
            self.diff_preview[:2000],
        ]
        if len(self.diff_preview) > 2000:
            lines.append(f"... [{len(self.diff_preview) - 2000} more chars]")
        lines.append("=" * 60)
        return "\n".join(lines)


@dataclass
class UpgradeDecision:
    approved: bool
    reason: str = ""
    responder: str = ""              # "user" | "auto_deny" | "auto_approve"
    decided_at: float = field(default_factory=time.time)


# ================================================================= approvers

class AutoDenyApprover:
    """Default policy for non-interactive runs: deny everything."""

    def decide(self, request: UpgradeRequest) -> UpgradeDecision:
        log.warning("auto_deny", reason="non-interactive run")
        return UpgradeDecision(
            approved=False,
            reason="non-interactive default-deny policy",
            responder="auto_deny",
        )


class InteractiveCLIApprover:
    """Prompt the user on stdin/stdout. The user may iterate by asking
    Commander for more detail (option 'r'); in that case the caller
    should re-invoke .decide() with an enriched request.
    """

    def __init__(
        self,
        *,
        explain_hook: Callable[[UpgradeRequest], str] | None = None,
    ):
        """`explain_hook(req)` is called on option 'r' — typically wired
        to Commander.think() so the agent can elaborate. If None, we just
        print a static message."""
        self._explain_hook = explain_hook

    def decide(self, request: UpgradeRequest) -> UpgradeDecision:
        if not sys.stdin.isatty():
            log.warning("no_tty_fallback_to_auto_deny")
            return AutoDenyApprover().decide(request)

        print("\n" + request.render_summary(), flush=True)
        while True:
            try:
                ans = input(
                    "\nApprove? [y=approve / N=deny(default) / d=full diff / "
                    "r=request reasoning] > "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n[interrupt] denied.", flush=True)
                return UpgradeDecision(approved=False,
                                       reason="user interrupt",
                                       responder="user")
            if ans in ("", "n", "no"):
                return UpgradeDecision(approved=False,
                                       reason="user denied",
                                       responder="user")
            if ans in ("y", "yes"):
                return UpgradeDecision(approved=True,
                                       reason="user approved",
                                       responder="user")
            if ans == "d":
                print("\n--- FULL DIFF ---")
                print(request.diff_preview)
                print("--- END DIFF ---\n")
                continue
            if ans == "r":
                if self._explain_hook:
                    try:
                        extra = self._explain_hook(request)
                        print("\n--- COMMANDER ELABORATION ---")
                        print(extra)
                        print("--- END ---\n")
                    except Exception as e:
                        print(f"[explain failed: {e!r}]")
                else:
                    print("(no explain hook configured; see prompts/commander.txt)")
                continue
            print(f"unknown choice {ans!r}; try y / n / d / r")


# ============================================================ audit log

class UpgradeAuditLog:
    """Append every request + decision to output/upgrade_log/."""

    def __init__(self, log_dir: Path | str | None = None):
        if log_dir is None:
            from core.paths import get_paths
            log_dir = get_paths().upgrade_log
        self.dir = Path(log_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def record(self, request: UpgradeRequest, decision: UpgradeDecision) -> Path:
        stamp = time.strftime("%Y-%m-%dT%H%M%S", time.localtime(decision.decided_at))
        fname = f"{stamp}_{_short_id(request.request_id)}.json"
        payload = {
            "request": asdict(request),
            "decision": asdict(decision),
        }
        # Truncate diff in audit log to avoid huge files
        if len(payload["request"]["diff_preview"]) > 10000:
            payload["request"]["diff_preview"] = \
                payload["request"]["diff_preview"][:10000] + \
                f"\n... [{len(payload['request']['diff_preview']) - 10000} truncated]"
        path = self.dir / fname
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        log.info("upgrade_audit_written", path=str(path),
                 approved=decision.approved)
        return path


def _short_id(full: str) -> str:
    return (full[:12] if full else "upgrade")
