"""Qwen self-tune.

One run of this module:

    1. Refuse if the pipeline is currently running a paper (avoid
       reshuffling Qwen while paper-ai depends on it).
    2. Refuse if we're inside the cooldown window.
    3. Collect Qwen's recent behavioural signals from the log file —
       how many calls, mean latency, number of parse failures, number
       of times the user corrected a classification, etc.
    4. Ask Qwen to read those signals + its current profile and
       propose a revised profile as JSON. The allowed fields are
       restricted per config/qwen_self_tune.yaml::allowed_changes.
    5. Validate the proposal (schema, field restrictions, size bounds).
    6. Stage it in profile/candidate/, run the Blue-Green boot test.
    7. On success: promote. Update state (success, reset failures).
    8. On failure: branch on failure_policy.
         safe       — bump consecutive_failures. At threshold, roll
                      main back from backup and set cooldown.
         iterative  — ask Commander (Opus) to refine the candidate,
                      up to `max_iterative_refinements` rounds in
                      this single trigger.

All state changes go through core.qwen_self_tune_state so a SIGINT
mid-run is safe.

Scope of this module: no network I/O beyond what LocalLLMClient and
AnthropicClient already encapsulate; no direct filesystem writes
outside the profile manager and state file.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.logger import get_logger
from core.paths import get_paths
from core.qwen_self_tune_state import (
    SelfTuneState, calendar_day_changed, is_in_cooldown, load, save,
)
from memory.qwen_profile import (
    ProfileBootResult, QwenProfile, QwenProfileManager,
)

log = get_logger("qwen_self_tune")


# ============================================================================ config


@dataclass
class TunePolicy:
    """Read from config/qwen_self_tune.yaml."""
    failure_policy: str = "safe"      # "safe" | "iterative"
    cooldown_hours_after_rollback: int = 24
    max_consecutive_failures: int = 3
    max_iterative_refinements: int = 3
    daily_auto: bool = True
    manual: bool = True
    commander_escalation: bool = True
    allowed_changes: list[str] = field(default_factory=lambda: [
        "prompt", "config.temperature", "config.num_predict_cap",
        "config.prompt_style", "routing_overrides",
    ])
    commander_only_fields: list[str] = field(default_factory=lambda: [
        "config.model", "config.base_url", "config.timeout_s",
    ])
    refresh_backup_after_n_promotions: int = 5


def load_policy() -> TunePolicy:
    path = get_paths().config / "qwen_self_tune.yaml"
    if not path.is_file():
        log.warning("self_tune_config_missing_using_defaults",
                    path=str(path))
        return TunePolicy()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        log.error("self_tune_config_parse_failed",
                  path=str(path), err=str(e))
        return TunePolicy()
    p = TunePolicy()
    for k in p.__dataclass_fields__:
        if k in raw:
            setattr(p, k, raw[k])
    # triggers block is flat in yaml for ergonomics; accept either form.
    trig = raw.get("triggers") or {}
    if isinstance(trig, dict):
        for k in ("daily_auto", "manual", "commander_escalation"):
            if k in trig:
                setattr(p, k, bool(trig[k]))
    return p


# ============================================================================ signals


@dataclass
class QwenSignals:
    """Lightweight summary of Qwen's recent behaviour, cheap to compute.

    Sources:
        - output/paper-ai.log — structured JSON lines tagged
          logger=paper-ai.local_llm or paper-ai.qwen_self_tune
        - output/companion_sessions/ — if present, recent chat logs
    """
    calls_last_24h: int = 0
    mean_latency_s: float = 0.0
    p95_latency_s: float = 0.0
    probe_failures: int = 0
    recent_user_corrections: int = 0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    notes: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"- calls_last_24h: {self.calls_last_24h}",
            f"- mean_latency_s: {self.mean_latency_s:.2f}",
            f"- p95_latency_s: {self.p95_latency_s:.2f}",
            f"- probe_failures: {self.probe_failures}",
            f"- recent_user_corrections: {self.recent_user_corrections}",
            f"- avg_input_tokens: {self.avg_input_tokens:.0f}",
            f"- avg_output_tokens: {self.avg_output_tokens:.0f}",
        ]
        if self.notes:
            lines.append("- notes:")
            for n in self.notes:
                lines.append(f"    * {n}")
        return "\n".join(lines)


def collect_signals(*, lookback_hours: int = 24) -> QwenSignals:
    """Walk the log file once and produce a QwenSignals.

    Robust to missing or truncated logs — returns zeros rather than
    raising. The log file is append-only so we can simply read forward
    and filter by timestamp.
    """
    paths = get_paths()
    log_path = paths.log_file
    if not log_path.is_file():
        return QwenSignals(notes=["no log file yet"])

    now = time.time()
    cutoff = now - lookback_hours * 3600

    latencies: list[float] = []
    in_toks: list[int] = []
    out_toks: list[int] = []
    probe_fails = 0
    corrections = 0

    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts_raw = rec.get("ts", "")
                # Logger timestamps are ISO8601 like "2026-04-22T13:00:00".
                # Use string compare as a cheap filter first — we only
                # need rough precision for a 24h window.
                # If format is unexpected we skip; it's not fatal.
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(ts_raw).timestamp()
                except Exception:
                    continue
                if ts < cutoff:
                    continue
                logger = rec.get("logger", "")
                msg = rec.get("msg", "")
                if logger.endswith(".local_llm"):
                    if msg == "local_llm_call":
                        el = rec.get("elapsed_s")
                        if isinstance(el, (int, float)):
                            latencies.append(float(el))
                        ti = rec.get("in_tok")
                        if isinstance(ti, int):
                            in_toks.append(ti)
                        to = rec.get("out_tok")
                        if isinstance(to, int):
                            out_toks.append(to)
                elif logger.endswith(".qwen_profile"):
                    if msg == "qwen_candidate_boot_test" and rec.get("ok") is False:
                        probe_fails += 1
                elif logger.endswith(".companion"):
                    if msg == "user_correction":
                        corrections += 1
    except OSError as e:
        return QwenSignals(notes=[f"log_read_failed: {e}"])

    n = len(latencies) or 1
    mean_l = sum(latencies) / n if latencies else 0.0
    p95_l = 0.0
    if latencies:
        sl = sorted(latencies)
        p95_l = sl[min(len(sl) - 1, int(0.95 * len(sl)))]
    return QwenSignals(
        calls_last_24h=len(latencies),
        mean_latency_s=mean_l,
        p95_latency_s=p95_l,
        probe_failures=probe_fails,
        recent_user_corrections=corrections,
        avg_input_tokens=(sum(in_toks) / n) if in_toks else 0.0,
        avg_output_tokens=(sum(out_toks) / n) if out_toks else 0.0,
    )


# ============================================================================ proposal generation

_PROPOSAL_SYSTEM = """\
You are proposing a revision to your OWN Qwen profile. The goal is to
improve token efficiency and reduce latency without hurting accuracy.

Output a single JSON object with up to these keys:

    {
      "prompt": "<full replacement text for the companion prompt, or null>",
      "config_patch": {
          "temperature": 0.2,
          "num_predict_cap": 512,
          "prompt_style": "concise"
      },
      "routing_overrides": { "classify": {"max_tokens": 64} },
      "rationale": "<short explanation why these changes help>"
    }

Constraints:
  - DO NOT output anything outside the JSON object.
  - DO NOT propose changes to "model", "base_url", or "timeout_s".
  - If you have no changes to propose, return {"rationale": "no change"}
    with no other keys.
  - Be conservative: propose at most two meaningful changes per run.
"""


def _read_current_profile(mgr: QwenProfileManager) -> QwenProfile:
    return mgr.load_main()


def _generate_candidate(
    client, signals: QwenSignals, current: QwenProfile,
    *, extra_context: str = "",
) -> dict[str, Any] | None:
    """Ask Qwen to propose a candidate. Returns the parsed dict or None."""
    user_turn = (
        "## Recent behavioural signals\n"
        + signals.render()
        + "\n\n## Current profile summary\n"
        + f"- prompt_len: {len(current.prompt)} chars\n"
        + f"- config: {json.dumps(current.config, ensure_ascii=False)[:400]}\n"
        + f"- routing_overrides: {json.dumps(current.routing_overrides, ensure_ascii=False)[:400]}\n"
        + (("\n\n## Additional context\n" + extra_context) if extra_context else "")
        + "\n\nReturn the JSON object now."
    )
    try:
        r = client.call(
            agent="qwen_self_tuner",
            user_turn=user_turn,
            task_type="route_decision",      # short reply budget
            extra_context=_PROPOSAL_SYSTEM,
        )
    except Exception as e:
        log.error("tune_proposal_call_failed", err=str(e))
        return None
    text = (r.get("text") or "").strip()
    # Peel off accidental fences.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```\s*$", "", text).strip()
    try:
        obj = json.loads(text)
    except Exception as e:
        log.warning("tune_proposal_not_json", preview=text[:200], err=str(e))
        return None
    if not isinstance(obj, dict):
        return None
    return obj


# ============================================================================ validation


def _validate_proposal(
    proposal: dict[str, Any], policy: TunePolicy,
) -> tuple[bool, str]:
    """Enforce allowed_changes and commander_only_fields."""
    # Absent keys are fine; present keys must be in allowed_changes.
    if "prompt" in proposal and proposal["prompt"] is not None:
        if "prompt" not in policy.allowed_changes:
            return False, "prompt changes not in allowed_changes"
        if not isinstance(proposal["prompt"], str):
            return False, "prompt must be string"
        if len(proposal["prompt"]) > 20000:
            return False, "prompt too long (>20k chars)"
    if "config_patch" in proposal:
        cp = proposal["config_patch"]
        if not isinstance(cp, dict):
            return False, "config_patch must be object"
        for k in cp:
            full = f"config.{k}"
            if full in policy.commander_only_fields:
                return False, f"field {full!r} is commander-only"
            if full not in policy.allowed_changes:
                return False, f"field {full!r} not in allowed_changes"
    if "routing_overrides" in proposal:
        ro = proposal["routing_overrides"]
        if not isinstance(ro, dict):
            return False, "routing_overrides must be object"
        if "routing_overrides" not in policy.allowed_changes:
            return False, "routing_overrides not in allowed_changes"
        if len(json.dumps(ro)) > 4000:
            return False, "routing_overrides too large"
    return True, "ok"


def _apply_proposal_to_profile(
    current: QwenProfile, proposal: dict[str, Any],
) -> QwenProfile:
    """Build a new QwenProfile by overlaying proposal onto current."""
    new_prompt = proposal.get("prompt")
    new_config = dict(current.config)
    if isinstance(proposal.get("config_patch"), dict):
        new_config.update(proposal["config_patch"])
    new_routing = dict(current.routing_overrides)
    if isinstance(proposal.get("routing_overrides"), dict):
        for k, v in proposal["routing_overrides"].items():
            new_routing[k] = v
    return QwenProfile(
        prompt=new_prompt if new_prompt is not None else current.prompt,
        config=new_config,
        routing_overrides=new_routing,
        facts_snapshot=current.facts_snapshot,   # carried through
    )


# ============================================================================ iterative refinement via Commander


def _refine_with_commander(
    anthropic_client, proposal: dict[str, Any], failure_reason: str,
    current: QwenProfile, signals: QwenSignals,
) -> dict[str, Any] | None:
    """Used by the 'iterative' failure policy.

    Send the failed proposal + why it failed + the signals to Commander
    (Opus), ask for a refined JSON proposal. Returns the refined object
    or None if Commander declines or the reply won't parse.
    """
    if anthropic_client is None:
        log.warning("iterative_refinement_skipped_no_commander")
        return None
    prompt_text = (
        "Qwen's self-tune proposal failed its boot test. Please refine it.\n\n"
        f"## Failure reason\n{failure_reason}\n\n"
        "## Original proposal\n" + json.dumps(proposal, ensure_ascii=False,
                                              indent=2) + "\n\n"
        "## Current profile\n"
        f"prompt_len={len(current.prompt)} cfg={json.dumps(current.config)}\n\n"
        "## Signals\n" + signals.render() + "\n\n"
        "Reply with a SINGLE JSON object in the same schema as the original "
        "proposal, or the string \"decline\" if no refinement is possible."
    )
    try:
        r = anthropic_client.call(
            agent="commander",
            user_turn=prompt_text,
            task_type="orchestrate",
            remember=False,
        )
    except Exception as e:
        log.error("commander_refine_call_failed", err=str(e))
        return None
    text = (r.get("text") or "").strip()
    if text.lower().startswith("decline"):
        return None
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```\s*$", "", text).strip()
    try:
        return json.loads(text)
    except Exception as e:
        log.warning("commander_refine_not_json", err=str(e))
        return None


# ============================================================================ main entry


@dataclass
class TuneResult:
    promoted: bool
    rolled_back: bool
    reason: str
    iterations: int = 0
    boot: ProfileBootResult | None = None


def run_self_tune(
    *,
    qwen_client,                       # LocalLLMClient instance
    anthropic_client = None,           # Optional; required for iterative policy
    force: bool = False,               # skip cooldown / calendar-day gates
) -> TuneResult:
    """Run one self-tune cycle. Safe to call from a REPL or a scheduler.

    Returns a TuneResult describing what happened. Even on "nothing to
    do" outcomes (cooldown, no-change proposal), the return is
    well-formed and the state file is touched so observers can see
    activity.
    """
    paths = get_paths()
    policy = load_policy()
    state_path = paths.qwen_self_tune_state
    state = load(state_path)

    # --- gating ---
    # Hard rule: never tune Qwen while paper-ai is running.
    try:
        from cli_commands.pipeline import is_pipeline_running
        if is_pipeline_running():
            return TuneResult(
                promoted=False, rolled_back=False,
                reason="paper-ai pipeline currently running; tune deferred",
            )
    except Exception:
        # Lock check is best-effort; failure shouldn't block tune.
        pass

    # Check for a Commander escalation flag. Its presence overrides the
    # daily_auto + cooldown gates EXCEPT for the cooldown that follows
    # a rollback (which is non-negotiable).
    escalation = None
    try:
        from core.qwen_observer import consume_flag
        escalation = consume_flag()
    except Exception:
        pass

    if not force:
        if is_in_cooldown(state):
            hrs = (state.cooldown_until_ts - time.time()) / 3600
            return TuneResult(
                promoted=False, rolled_back=False,
                reason=f"cooldown: {hrs:.1f}h remaining",
            )
        if (policy.daily_auto and not calendar_day_changed(state)
                and escalation is None):
            return TuneResult(
                promoted=False, rolled_back=False,
                reason="already ran today (no escalation flag)",
            )

    state.total_runs += 1
    state.last_run_ts = time.time()
    save(state_path, state)

    mgr = QwenProfileManager(paths=paths)
    current = _read_current_profile(mgr)
    if current.is_empty():
        return TuneResult(
            promoted=False, rolled_back=False,
            reason="profile/main is empty — run `qwen verify-config` first",
        )

    signals = collect_signals(lookback_hours=24)

    # --- proposal ---
    proposal = _generate_candidate(qwen_client, signals, current)
    if proposal is None:
        state.consecutive_failures += 1
        state.last_failure_reason = "proposal generation failed"
        save(state_path, state)
        _maybe_escalate_cooldown(state, policy, mgr, state_path)
        return TuneResult(
            promoted=False, rolled_back=False,
            reason="proposal generation failed",
        )

    no_change = all(k not in proposal or proposal.get(k) is None
                    for k in ("prompt", "config_patch", "routing_overrides"))
    if no_change:
        # Treat as a successful no-op: Qwen declined to change anything.
        state.consecutive_failures = 0
        state.last_success_ts = time.time()
        state.total_successes += 1
        state.last_failure_reason = ""
        state.last_attempted_change_summary = proposal.get("rationale", "no change")
        save(state_path, state)
        return TuneResult(
            promoted=False, rolled_back=False,
            reason="no changes proposed",
        )

    # --- try promotion, with retries per policy ---
    iterations = 0
    last_boot: ProfileBootResult | None = None
    last_reason = ""
    current_proposal: dict[str, Any] | None = proposal
    max_iters = (policy.max_iterative_refinements
                 if policy.failure_policy == "iterative" else 1)

    while iterations < max_iters and current_proposal is not None:
        iterations += 1
        ok, msg = _validate_proposal(current_proposal, policy)
        if not ok:
            last_reason = f"validation rejected: {msg}"
            log.warning("proposal_invalid", reason=msg,
                        iteration=iterations)
            if policy.failure_policy == "iterative":
                current_proposal = _refine_with_commander(
                    anthropic_client, current_proposal, last_reason,
                    current, signals)
                continue
            break

        candidate_profile = _apply_proposal_to_profile(
            current, current_proposal)
        last_boot = mgr.stage_test_and_promote(candidate_profile)
        if last_boot.ok:
            break
        last_reason = last_boot.reason
        log.warning("candidate_boot_failed", reason=last_reason,
                    iteration=iterations)
        if policy.failure_policy == "iterative":
            current_proposal = _refine_with_commander(
                anthropic_client, current_proposal, last_reason,
                current, signals)
        else:
            break

    # --- outcome ---
    if last_boot and last_boot.ok:
        state.consecutive_failures = 0
        state.last_success_ts = time.time()
        state.total_successes += 1
        state.last_failure_reason = ""
        state.last_attempted_change_summary = (current_proposal or {}).get(
            "rationale", "promoted") if current_proposal else "promoted"
        # Refresh backup every N successes.
        if (state.total_successes % policy.refresh_backup_after_n_promotions
                == 0):
            _refresh_backup(mgr)
        save(state_path, state)
        return TuneResult(
            promoted=True, rolled_back=False,
            reason="promoted", iterations=iterations, boot=last_boot,
        )

    # Failure path.
    state.consecutive_failures += 1
    state.last_failure_reason = last_reason or "unknown"
    save(state_path, state)

    rolled_back = _maybe_escalate_cooldown(state, policy, mgr, state_path)
    return TuneResult(
        promoted=False, rolled_back=rolled_back,
        reason=f"failed after {iterations} attempt(s): {last_reason}",
        iterations=iterations, boot=last_boot,
    )


def _maybe_escalate_cooldown(
    state: SelfTuneState, policy: TunePolicy,
    mgr: QwenProfileManager, state_path: Path,
) -> bool:
    """If consecutive failures exceed the threshold, roll main back to
    backup (safe policy) and set cooldown. Returns True if a rollback
    happened.
    """
    if state.consecutive_failures < policy.max_consecutive_failures:
        save(state_path, state)
        return False

    rolled = False
    if policy.failure_policy == "safe":
        rolled = mgr.restore_from_backup(
            reason=f"{state.consecutive_failures} consecutive tune failures")
        if rolled:
            state.total_rollbacks += 1
    state.cooldown_until_ts = time.time() + policy.cooldown_hours_after_rollback * 3600
    state.consecutive_failures = 0       # reset; cooldown serves as the gate
    save(state_path, state)
    log.warning("qwen_self_tune_cooldown",
                hours=policy.cooldown_hours_after_rollback,
                rolled_back=rolled)
    return rolled


def _refresh_backup(mgr: QwenProfileManager) -> None:
    """Copy main → backup so backup stays close to current-good."""
    import shutil
    main = mgr.paths.qwen_profile_main
    backup = mgr.paths.qwen_profile_backup
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(main, backup)
    log.info("qwen_backup_refreshed")
