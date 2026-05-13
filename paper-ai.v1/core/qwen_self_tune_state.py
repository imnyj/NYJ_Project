"""Self-tune state: cooldown, consecutive failures, last-run timestamp.

Persisted as a small JSON file so restarts don't lose the failure
count. Read/written by `qwen_companion.self_tune` at the top and
bottom of each tuning attempt.

Design note on policies
-----------------------
Two failure policies are supported, selected via config/qwen_self_tune.yaml::
failure_policy:

    safe
        3 consecutive candidate failures → roll main back to backup and
        pause self-tune for 24h. Conservative; avoids thrashing.

    iterative
        Each failure → ask Commander (Opus) to review the Qwen-generated
        candidate and propose a refined version. Up to 3 refinement
        rounds per trigger, then cooldown kicks in. Moves the decision
        quality question to Commander but spends Opus tokens.

Both policies share the same bookkeeping; the selection only changes
what happens *after* a failure.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SelfTuneState:
    last_run_ts: float = 0.0               # UTC epoch seconds of last attempt
    last_success_ts: float = 0.0           # ... of last *successful* attempt
    consecutive_failures: int = 0
    cooldown_until_ts: float = 0.0         # no attempts before this time
    total_runs: int = 0
    total_successes: int = 0
    total_rollbacks: int = 0

    # Populated by tuner each run so observers can see what's going on
    # without walking log files.
    last_failure_reason: str = ""
    last_attempted_change_summary: str = ""


def load(path: Path) -> SelfTuneState:
    if not path.is_file():
        return SelfTuneState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return SelfTuneState()
    if not isinstance(data, dict):
        return SelfTuneState()
    fields = {f for f in SelfTuneState().__dataclass_fields__}
    return SelfTuneState(**{k: v for k, v in data.items() if k in fields})


def save(path: Path, state: SelfTuneState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{int(time.time() * 1000)}")
    tmp.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
    # os.replace is atomic within a filesystem
    import os
    os.replace(tmp, path)


def is_in_cooldown(state: SelfTuneState, *, now: float | None = None) -> bool:
    now = now if now is not None else time.time()
    return now < state.cooldown_until_ts


def days_since(ts: float, *, now: float | None = None) -> float:
    now = now if now is not None else time.time()
    return (now - ts) / 86400.0


def calendar_day_changed(state: SelfTuneState, *,
                         now: float | None = None) -> bool:
    """Return True if the local calendar day has changed since last_run_ts.

    Used to honour the "매일 1회 자동" rule without counting raw 24h
    intervals (running at 11:55pm then 00:05am should not count twice).
    """
    from datetime import datetime
    now_t = now if now is not None else time.time()
    if state.last_run_ts == 0:
        return True
    last_day = datetime.fromtimestamp(state.last_run_ts).date()
    now_day = datetime.fromtimestamp(now_t).date()
    return now_day != last_day
