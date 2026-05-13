"""Session persistence for the interactive REPL — JSON only.

Multi-agent layout
------------------
A session can hold separate conversation histories for each agent the
user has talked to. The "active" agent is the one currently
receiving turns, but switching to a different agent doesn't lose
the others' state — the user can flip back at will.

JSON schema (current, v2):

    {
      "name":          "<n>",
      "version":       2,
      "active_agent":  "writer",
      "created_at":    <epoch>,
      "updated_at":    <epoch>,
      "agents": {
        "commander": {
          "history":         [{"role":..., "content":...}, ...],
          "model_breakdown": {"claude-opus-4-7": 5, ...}
        },
        "writer":    { ... },
        ...
      },
      "metadata": {
        "total_cost_usd":  0.0123
      }
    }

Backward compatibility
----------------------
Older single-agent files (without "version" / "active_agent" /
"agents") are auto-upgraded on load: their `history` is treated as
the commander's history, with `active_agent="commander"`. The next
save writes them out in v2 format.

Hand-editing notes
------------------
- Edit `agents.<role>.history` to trim or fix any agent's record.
- `total_cost_usd` is recomputed on save by summing per-agent breakdowns.
- `created_at` is preserved across re-saves.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.logger import get_logger
from core.paths import get_paths

log = get_logger("sessions")

# Filesystem-safe character set. Strict by design.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Anything we recognise as a paper-ai agent role. Not enforced on load
# (so user can name a custom role in JSON for experiments), but used
# for default-shape construction.
KNOWN_AGENTS = (
    "commander", "idea", "librarian", "experimenter", "reviewer", "writer",
)

CURRENT_SCHEMA_VERSION = 2


@dataclass
class AgentSlot:
    """One agent's piece of the session."""
    history: list[dict[str, str]] = field(default_factory=list)
    model_breakdown: dict[str, int] = field(default_factory=dict)
    cost_usd: float = 0.0

    def add_call(self, model: str, cost: float) -> None:
        self.cost_usd += float(cost)
        self.model_breakdown[model] = self.model_breakdown.get(model, 0) + 1

    def turn_count(self) -> int:
        # Counting "user" entries: each is one turn the user took. An
        # errored turn might leave a user without an assistant reply,
        # so we don't count pairs.
        return sum(1 for m in self.history if m.get("role") == "user")

    def is_empty(self) -> bool:
        return not self.history


@dataclass
class Session:
    """In-memory session — mirrors the v2 JSON layout."""
    name: str
    active_agent: str = "commander"
    agents: dict[str, AgentSlot] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def slot(self, agent: str) -> AgentSlot:
        """Get-or-create an agent slot. Used by callers that don't want
        to write `if agent not in agents: agents[agent] = AgentSlot()`
        every time."""
        if agent not in self.agents:
            self.agents[agent] = AgentSlot()
        return self.agents[agent]

    def total_cost(self) -> float:
        return sum(slot.cost_usd for slot in self.agents.values())

    def total_turns(self) -> int:
        return sum(slot.turn_count() for slot in self.agents.values())


# ============================================================================ public API


def is_valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name))


def session_dir() -> Path:
    p = get_paths().sessions
    p.mkdir(parents=True, exist_ok=True)
    return p


def json_path(name: str) -> Path:
    return session_dir() / f"{name}.json"


def list_sessions() -> list[dict[str, Any]]:
    """Summary entries for every saved session, newest first."""
    out: list[dict[str, Any]] = []
    for p in sorted(session_dir().glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("session_unparseable", path=str(p), err=str(e))
            continue
        # Compute a unified summary regardless of schema version.
        if data.get("version") == CURRENT_SCHEMA_VERSION:
            agents = data.get("agents") or {}
            turns = sum(
                sum(1 for m in (a.get("history") or [])
                    if m.get("role") == "user")
                for a in agents.values()
            )
            cost = (data.get("metadata") or {}).get("total_cost_usd", 0.0)
            agent_label = data.get("active_agent", "commander")
            agent_count = len([a for a in agents.values()
                               if a.get("history")])
        else:
            # Old single-agent layout
            history = data.get("history") or []
            turns = sum(1 for m in history if m.get("role") == "user")
            cost = (data.get("metadata") or {}).get("total_cost_usd", 0.0)
            agent_label = data.get("agent", "commander")
            agent_count = 1

        out.append({
            "name":           data.get("name", p.stem),
            "active_agent":   agent_label,
            "agent_count":    agent_count,
            "turn_count":     turns,
            "updated_at":     data.get("updated_at", p.stat().st_mtime),
            "total_cost_usd": cost,
        })
    out.sort(key=lambda r: r["updated_at"], reverse=True)
    return out


def save(session: Session) -> Path:
    """Atomically write the session as v2 JSON.

    Refuses on invalid name or fully-empty agents (saving nothing
    wastes a name slot).
    """
    if not is_valid_name(session.name):
        raise ValueError(
            f"invalid session name {session.name!r}: must match "
            f"[A-Za-z0-9][A-Za-z0-9._-]{{0,63}}"
        )
    if all(slot.is_empty() for slot in session.agents.values()):
        raise ValueError("refusing to save a session with no agent history")

    now = time.time()
    p = json_path(session.name)
    # Preserve created_at across re-saves so the user can see when a
    # session was first started.
    if p.is_file():
        try:
            existing = json.loads(p.read_text(encoding="utf-8"))
            session.created_at = float(existing.get(
                "created_at", session.created_at))
        except Exception:
            pass

    session.updated_at = now
    payload = {
        "name":         session.name,
        "version":      CURRENT_SCHEMA_VERSION,
        "active_agent": session.active_agent,
        "created_at":   session.created_at,
        "updated_at":   session.updated_at,
        "agents": {
            role: {
                "history":         slot.history,
                "model_breakdown": dict(slot.model_breakdown),
                "cost_usd":        round(slot.cost_usd, 6),
            }
            for role, slot in session.agents.items()
            if not slot.is_empty()    # don't write empty agent slots
        },
        "metadata": {
            "total_cost_usd": round(session.total_cost(), 6),
        },
    }

    # Atomic write
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, p)

    log.info("session_saved", name=session.name,
             active_agent=session.active_agent,
             total_turns=session.total_turns(),
             agent_count=len(payload["agents"]),
             path=str(p))
    return p


def load(name: str) -> Session:
    """Load a session — auto-upgrades v1 single-agent files."""
    if not is_valid_name(name):
        raise ValueError(f"invalid session name {name!r}")
    p = json_path(name)
    if not p.is_file():
        raise FileNotFoundError(f"no session named {name!r} (looked at {p})")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"file {p} is not a paper-ai session")

    if data.get("version") == CURRENT_SCHEMA_VERSION:
        return _load_v2(name, data)
    # Older single-agent layout — auto-upgrade. We DON'T overwrite the
    # file on load; the next save will write v2 naturally.
    return _load_v1_as_v2(name, data)


def delete(name: str) -> bool:
    if not is_valid_name(name):
        raise ValueError(f"invalid session name {name!r}")
    p = json_path(name)
    if not p.is_file():
        return False
    try:
        p.unlink()
    except OSError as e:
        log.error("session_unlink_failed", path=str(p), err=str(e))
        return False
    log.warning("session_deleted", name=name)
    return True


def rename(old: str, new: str) -> None:
    if not is_valid_name(new):
        raise ValueError(f"invalid new name {new!r}")
    src = json_path(old)
    if not src.is_file():
        raise FileNotFoundError(f"no session named {old!r}")
    dst = json_path(new)
    if dst.is_file():
        raise FileExistsError(f"session {new!r} already exists")
    data = json.loads(src.read_text(encoding="utf-8"))
    data["name"] = new
    data["updated_at"] = time.time()
    tmp = dst.with_name(dst.name + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, dst)
    src.unlink()
    log.info("session_renamed", old=old, new=new)


# ============================================================================ private helpers


def _load_v2(name: str, data: dict[str, Any]) -> Session:
    sess = Session(
        name=data.get("name", name),
        active_agent=data.get("active_agent", "commander"),
        created_at=float(data.get("created_at", time.time())),
        updated_at=float(data.get("updated_at", time.time())),
    )
    for role, blob in (data.get("agents") or {}).items():
        slot = AgentSlot(
            history=list(blob.get("history") or []),
            model_breakdown=dict(blob.get("model_breakdown") or {}),
            cost_usd=float(blob.get("cost_usd") or 0.0),
        )
        sess.agents[role] = slot
    return sess


def _load_v1_as_v2(name: str, data: dict[str, Any]) -> Session:
    """Treat a single-agent JSON as commander's slot in a v2 session."""
    if "history" not in data:
        raise ValueError(
            f"session file lacks `history` field — not a paper-ai session"
        )
    agent = data.get("agent", "commander")
    md = data.get("metadata") or {}
    slot = AgentSlot(
        history=list(data.get("history") or []),
        model_breakdown=dict(md.get("model_breakdown") or {}),
        cost_usd=float(md.get("total_cost_usd") or 0.0),
    )
    sess = Session(
        name=data.get("name", name),
        active_agent=agent,
        created_at=float(data.get("created_at", time.time())),
        updated_at=float(data.get("updated_at", time.time())),
    )
    sess.agents[agent] = slot
    log.info("session_upgraded_v1_to_v2", name=name, agent=agent)
    return sess
