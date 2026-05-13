# cli_commands/usage_report.py
"""--usage subcommand: cumulative token + cost report.

Two views, side by side:

  Lifetime  : every Anthropic + Qwen call recorded since output/usage.json
              was first created (i.e. all sessions, all paper runs in this
              PAPER_AI_ROOT).
  Session   : only the current session's totals (PolicyRuntime in-process).
              When called outside an active Commander process, this view
              shows zeros — the data lives only inside Commander.

Cost-savings calculation
------------------------
For each Qwen call we compute the equivalent Anthropic cost (had the
call been routed to Sonnet 4.6 — the typical worker-tier model) and
report it as "savings". This is an upper bound: in practice some Qwen
calls might have been routed to Haiku, but Sonnet is the closest
match for the kind of work Qwen handles in this project.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Anthropic pricing per 1M tokens (in/out). Sonnet 4.6 is our reference
# baseline for "what would this have cost on Anthropic". Numbers must
# stay in sync with core/policy_runtime.py::PRICING.
SONNET_BASELINE = {"in": 3.00, "out": 15.00}


def run(root: Path) -> int:
    """Pretty-print the usage report. Returns 0 always."""
    print("\n" + "=" * 72)
    print("  paper-ai token usage report")
    print(f"  PAPER_AI_ROOT: {root}")
    print("=" * 72 + "\n")

    blob = _load_lifetime(root)
    life = blob.get("lifetime", {})

    if life.get("calls", 0) == 0:
        print("  (no usage recorded yet — run commander.py to start tracking)")
        return 0

    # ---- Lifetime totals ----
    print("──── Lifetime (all sessions) ────")
    _print_summary(life)

    # ---- Per-agent breakdown ----
    by_agent = life.get("by_agent") or {}
    if by_agent:
        print("\n──── By agent ────")
        print(f"  {'AGENT':<14} {'CALLS':>7} {'IN':>10} {'OUT':>10} "
              f"{'CACHE-R':>10} {'CACHE-W':>10} {'COST $':>10}")
        for role in sorted(by_agent):
            slot = by_agent[role]
            print(f"  {role:<14} "
                  f"{slot['calls']:>7} "
                  f"{slot['input_tokens']:>10,} "
                  f"{slot['output_tokens']:>10,} "
                  f"{slot['cache_read_tokens']:>10,} "
                  f"{slot['cache_write_tokens']:>10,} "
                  f"{slot['cost_usd']:>10.4f}")

    # ---- Model breakdown ----
    by_model = life.get("by_model") or {}
    if by_model:
        print("\n──── By model ────")
        for model, calls in sorted(by_model.items(), key=lambda x: -x[1]):
            print(f"  {model:<35} {calls:>6} calls")

    # ---- Qwen savings ----
    qwen_calls = sum(c for m, c in by_model.items() if m.startswith("local:"))
    qwen_input = 0
    qwen_output = 0
    for role_slot in by_agent.values():
        # Per-agent buckets don't distinguish local-vs-anthropic. We
        # approximate Qwen tokens as the difference between the
        # local: model row totals and what made it into by_agent.
        # Cleaner approximation: estimate from the qwen_companion role
        # if present.
        pass
    # Direct approach: scan blob for the qwen role bucket.
    qwen_slot = by_agent.get("qwen_companion") or by_agent.get("qwen")
    if qwen_slot:
        qwen_input = qwen_slot["input_tokens"]
        qwen_output = qwen_slot["output_tokens"]

    if qwen_calls > 0 or qwen_input > 0:
        equivalent_cost = (
            qwen_input  * SONNET_BASELINE["in"]  / 1_000_000
            + qwen_output * SONNET_BASELINE["out"] / 1_000_000
        )
        print("\n──── Qwen (local) savings estimate ────")
        print(f"  Qwen calls:       {qwen_calls}")
        print(f"  Tokens processed: {qwen_input:,} in + {qwen_output:,} out")
        print(f"  If routed to Sonnet 4.6 instead → ${equivalent_cost:.4f}")
        print(f"  Actual Qwen cost:                  $0.0000")
        print(f"  Estimated savings:                 ${equivalent_cost:.4f}")
        if life.get('usd_spent', 0) > 0:
            ratio = equivalent_cost / (life['usd_spent'] + equivalent_cost) * 100
            print(f"  Savings as % of total work:        {ratio:.1f}%")

    print("\n" + "=" * 72)
    print(f"  Started: {_fmt_time(blob.get('started_at'))}")
    print(f"  Updated: {_fmt_time(blob.get('updated_at'))}")
    print("=" * 72 + "\n")
    return 0


# ============================================================================ helpers


def _load_lifetime(root: Path) -> dict[str, Any]:
    """Load output/usage.json or empty blob."""
    p = root / "output" / "usage.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _print_summary(life: dict[str, Any]) -> None:
    print(f"  Total calls:        {life.get('calls', 0):>10,}")
    print(f"  Input tokens:       {life.get('input_tokens', 0):>10,}")
    print(f"  Output tokens:      {life.get('output_tokens', 0):>10,}")
    print(f"  Cache reads:        {life.get('cache_read_tokens', 0):>10,}")
    print(f"  Cache writes:       {life.get('cache_write_tokens', 0):>10,}")
    print(f"  Total cost:         ${life.get('usd_spent', 0):>9.4f}")


def _fmt_time(epoch: float | None) -> str:
    if not epoch:
        return "—"
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))
