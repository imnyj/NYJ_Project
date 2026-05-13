"""Commander's Qwen observer.

Commander's ROLE regarding Qwen is narrow:

    * Watch Qwen's behaviour during paper work.
    * At paper completion, summarise what it saw.
    * If the signals look off, drop an "escalation" flag that the
      next `python -m qwen_companion self-tune` will honour (bypassing
      the daily_auto rate limit).
    * Never mutate the Qwen profile itself. Tuning is Qwen's job;
      Commander just says "please look at yourself soon."

The escalation flag is a tiny JSON file at
`cache/qwen_escalation_flag.json`. The companion's self-tune entry
checks for it and, if present and fresh, treats it as an override of
the cooldown / calendar-day gates (with clamps — even escalations
can't override a hard rollback cooldown).

This module is deliberately pure: no Anthropic calls, no Qwen calls.
It only reads the log file and writes the flag.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import get_logger
from core.paths import get_paths

log = get_logger("qwen_observer")


ESCALATION_FLAG_FILENAME = "qwen_escalation_flag.json"


@dataclass
class ObservationReport:
    """Summary produced by `observe_after_pipeline()`."""
    calls_observed: int = 0
    mean_latency_s: float = 0.0
    p95_latency_s: float = 0.0
    error_rate: float = 0.0
    reasons: list[str] = field(default_factory=list)

    @property
    def escalate(self) -> bool:
        return bool(self.reasons)


# Thresholds for escalation. Intentionally generous — we don't want
# Commander crying wolf for normal GPU hiccups.
_THRESH = {
    "p95_latency_warn_s": 30.0,
    "error_rate_warn": 0.10,
    "min_calls_for_verdict": 20,
}


def observe_after_pipeline(*, lookback_hours: int = 2) -> ObservationReport:
    """Walk the log for the last `lookback_hours` and decide whether to
    raise an escalation flag. Returns the report either way.
    """
    paths = get_paths()
    log_path = paths.log_file
    if not log_path.is_file():
        return ObservationReport(reasons=["no log file yet"])

    cutoff = time.time() - lookback_hours * 3600
    latencies: list[float] = []
    errors = 0
    total = 0
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(rec.get("ts", "")).timestamp()
                except Exception:
                    continue
                if ts < cutoff:
                    continue
                logger_name = rec.get("logger", "")
                if not logger_name.endswith(".local_llm"):
                    continue
                msg = rec.get("msg", "")
                if msg == "local_llm_call":
                    total += 1
                    el = rec.get("elapsed_s")
                    if isinstance(el, (int, float)):
                        latencies.append(float(el))
                elif msg in ("local_llm_probe_failed", "local_llm_model_not_pulled"):
                    errors += 1
                    total += 1
    except OSError as e:
        return ObservationReport(reasons=[f"log_read_failed: {e}"])

    report = ObservationReport(calls_observed=total)
    if not latencies:
        return report
    report.mean_latency_s = sum(latencies) / len(latencies)
    sl = sorted(latencies)
    report.p95_latency_s = sl[min(len(sl) - 1, int(0.95 * len(sl)))]
    report.error_rate = errors / total if total else 0.0

    if total < _THRESH["min_calls_for_verdict"]:
        return report

    if report.p95_latency_s > _THRESH["p95_latency_warn_s"]:
        report.reasons.append(
            f"p95 latency {report.p95_latency_s:.1f}s exceeds "
            f"threshold {_THRESH['p95_latency_warn_s']}s"
        )
    if report.error_rate > _THRESH["error_rate_warn"]:
        report.reasons.append(
            f"error rate {report.error_rate:.1%} exceeds "
            f"{_THRESH['error_rate_warn']:.0%}"
        )

    if report.escalate:
        _write_flag(report)
        log.warning("qwen_escalation_raised", reasons=report.reasons)
    else:
        log.info("qwen_observation_ok",
                 calls=total, p95_s=round(report.p95_latency_s, 1))
    return report


# ---------------------------------------------------------------- flag file

def _flag_path() -> Path:
    return get_paths().cache_dir / ESCALATION_FLAG_FILENAME


def _write_flag(report: ObservationReport) -> None:
    path = _flag_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "raised_at": time.time(),
        "reasons": report.reasons,
        "calls_observed": report.calls_observed,
        "p95_latency_s": report.p95_latency_s,
        "error_rate": report.error_rate,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def consume_flag(*, max_age_hours: float = 24.0) -> dict | None:
    """Called by the companion's self-tune entry. Returns the flag
    payload and REMOVES the file. If the flag is older than
    `max_age_hours`, ignore it (but still remove).
    """
    path = _flag_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    try:
        path.unlink()
    except OSError:
        pass
    raised_at = payload.get("raised_at", 0)
    if time.time() - raised_at > max_age_hours * 3600:
        return None
    return payload


def clear_flag() -> None:
    path = _flag_path()
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
