# core/upgrade_check.py
"""Weekly self-upgrade trigger.

Tracks when Commander last reviewed its own code for upgrades. On
each Commander boot, this module is consulted: if more than
UPGRADE_CHECK_INTERVAL_DAYS have passed since the last check, a
flag is set that the Commander prompt sees and acts on.

Why a separate module
---------------------
Three reasons:

  1. Putting "today is YYYY-MM-DD, last check was..." into the prompt
     ONCE at boot keeps the prompt deterministic across the rest of
     the session — same f-string, same model behaviour. If we injected
     the date on every turn, prompt cache hit ratio would collapse.

  2. The check is bookkeeping (file I/O), not reasoning. Doing it in
     Python rather than asking the LLM saves tokens.

  3. The user explicitly chose "boot-time check only" over per-turn.
     This file IS that check.

State file
----------
PAPER_AI_ROOT/output/upgrade_state.json:

    {
      "last_check_at":      <epoch>,
      "last_check_outcome": "deferred"|"completed"|"aborted"|"never",
      "history": [
        {"at": <epoch>, "outcome": "...", "note": "..."},
        ...
      ]
    }

`history` is capped at 20 entries (oldest dropped) to bound file size.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("upgrade_check")


# How many days between "should consider self-upgrade" reminders.
# 7 = once a week, in line with the user's "주간" requirement.
UPGRADE_CHECK_INTERVAL_DAYS = 7

# History entries beyond this are dropped to bound file size.
MAX_HISTORY = 20


def _state_path(root: Path) -> Path:
    out = Path(root) / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out / "upgrade_state.json"


def _load(root: Path) -> dict[str, Any]:
    p = _state_path(root)
    if not p.is_file():
        return {
            "last_check_at": 0.0,
            "last_check_outcome": "never",
            "history": [],
        }
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"last_check_at": 0.0,
                    "last_check_outcome": "never", "history": []}
        return data
    except Exception as e:
        log.warning("upgrade_state_unreadable", err=str(e))
        return {"last_check_at": 0.0,
                "last_check_outcome": "never", "history": []}


def _save(root: Path, state: dict[str, Any]) -> None:
    p = _state_path(root)
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, p)


# ============================================================================ public API

def days_since_last_check(root: Path) -> float:
    """How many days have passed since the last upgrade check?

    Returns float (e.g. 7.34). If never checked, returns a large
    sentinel (999) so callers always treat it as "due".
    """
    state = _load(root)
    last = float(state.get("last_check_at", 0.0))
    if last == 0.0:
        return 999.0
    return (time.time() - last) / 86400.0


def is_check_due(root: Path) -> bool:
    """True iff at least UPGRADE_CHECK_INTERVAL_DAYS have elapsed."""
    return days_since_last_check(root) >= UPGRADE_CHECK_INTERVAL_DAYS


def record_outcome(root: Path, outcome: str, note: str = "") -> None:
    """Mark a check completed (or deferred / aborted) with an optional note.

    `outcome` should be one of: "completed", "deferred", "aborted",
    "user_declined". Used by Commander when it finishes (or skips)
    a self-upgrade review.
    """
    state = _load(root)
    state["last_check_at"] = time.time()
    state["last_check_outcome"] = outcome
    history = state.get("history") or []
    history.append({
        "at": time.time(),
        "outcome": outcome,
        "note": note[:200],   # cap to keep file small
    })
    state["history"] = history[-MAX_HISTORY:]
    _save(root, state)
    log.info("upgrade_check_recorded", outcome=outcome, note=note[:60])


def boot_check(root: Path, *, interactive: bool = True) -> dict[str, Any]:
    """Called by Commander at boot. Decides whether to trigger.

    Returns a dict with:
      {
        "due":         True/False,
        "days_since":  float,
        "last_outcome": str,
        "user_consent": True/False/None,   # None when not interactive
      }

    Behaviour:
      * If not due: returns {due: False, ...}, no prompts.
      * If due AND interactive: prompts the user [y/N]. Whatever they
        answer is recorded so we don't ask again until the next interval.
      * If due AND non-interactive (e.g. running under a script): just
        sets due=True without prompting; Commander prompt sees `due`
        and decides on its own.

    The user prompt is intentionally simple — this isn't a security
    decision, just a "do you want to spend a few minutes / dollars
    reviewing your codebase right now?" check.
    """
    days = days_since_last_check(root)
    due = days >= UPGRADE_CHECK_INTERVAL_DAYS
    state = _load(root)
    last_outcome = state.get("last_check_outcome", "never")

    result: dict[str, Any] = {
        "due": due,
        "days_since": round(days, 2) if days < 999 else None,
        "last_outcome": last_outcome,
        "user_consent": None,
    }

    if not due:
        return result

    if not interactive:
        # Non-tty mode (e.g. piped, watchdog with no /dev/tty). Just
        # surface the flag; Commander prompt has its own guard.
        return result

    # Interactive prompt. We want this to look DIFFERENT from regular
    # commander chatter so the user doesn't blindly press y. A clear
    # banner.
    print("\n" + "=" * 60)
    print("  📅 Weekly upgrade check")
    if last_outcome == "never":
        print("     (No previous check on record.)")
    else:
        print(f"     Last review: {round(days)} days ago "
              f"(outcome: {last_outcome})")
    print("     Reviewing the codebase costs a few minutes and may")
    print("     incur API charges (~$0.05–$0.20 typical).")
    print("=" * 60)
    try:
        ans = input("  Run upgrade review now? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = ""

    consent = ans == "y"
    result["user_consent"] = consent

    if not consent:
        # User declined — record it so we don't ask again for another
        # week. They can still trigger manually by running the
        # upgrade procedure as a normal commander directive.
        record_outcome(root, "user_declined",
                       note=f"declined at boot, {round(days)}d since last")
        print("  → skipped. Will ask again in 7 days.")
        print("  → to trigger manually: ask Commander to review its own code.\n")

    return result
