"""Blackboard: the single source of truth for inter-agent communication.

Replaces the naive "shared chat history" pattern with a structured-document
pub/sub where every exchange is a typed, versioned artifact. This cuts
inter-agent tokens 30-60% (MetaGPT, ICLR 2024) and enables selective context
loading (each agent reads only what it subscribes to).

Key operations:
    bb = Blackboard()
    bb.publish(agent="idea", name=ArtifactName.MAIN_IDEA, ...)
    bb.latest(ArtifactName.MAIN_IDEA)               # most recent version
    bb.subscriptions_for("writer")                   # subset visible to writer
    bb.snapshot_for_agent("writer", max_chars=8000)  # rendered for LLM prompt
    bb.save("output/sessions/run_001.json")          # persist for restart
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable

from core.artifacts import (
    Artifact,
    ArtifactContractViolation,
    ArtifactName,
    PRODUCER,
    PayloadKind,
    SUBSCRIBERS,
    check_producer,
)
from core.logger import get_logger

log = get_logger("blackboard")


class Blackboard:
    """Thread-safe structured-document pub/sub shared state."""

    # History length per artifact (how many versions kept in memory)
    HISTORY_LIMIT = 5

    def __init__(self) -> None:
        self._store: dict[ArtifactName, deque[Artifact]] = defaultdict(
            lambda: deque(maxlen=self.HISTORY_LIMIT)
        )
        self._lock = threading.RLock()
        self._listeners: dict[str, list[Callable[[Artifact], None]]] = defaultdict(list)
        # For stall detection: record of last N publish timestamps
        self._publish_log: deque[tuple[float, ArtifactName, str]] = deque(maxlen=200)

    # ========================================================= publish / read

    def publish(
        self,
        *,
        agent: str,
        name: ArtifactName | str,
        payload: Any,
        kind: PayloadKind | str = PayloadKind.TEXT,
        notes: str = "",
    ) -> Artifact:
        """Publish or update an artifact. Enforces producer contract."""
        if isinstance(name, str):
            name = ArtifactName(name)
        if isinstance(kind, str):
            kind = PayloadKind(kind)

        check_producer(name, agent)

        with self._lock:
            existing = self._store[name]
            next_version = (existing[-1].version + 1) if existing else 1
            artifact = Artifact(
                name=name,
                producer=agent,
                kind=kind,
                payload=payload,
                version=next_version,
                notes=notes,
            )
            existing.append(artifact)
            self._publish_log.append((artifact.timestamp, name, agent))

        log.info(
            "artifact_published",
            name=name.value,
            producer=agent,
            version=artifact.version,
            hash=artifact.schema_hash,
        )
        # Notify subscribers (callbacks run outside the lock)
        self._notify_subscribers(artifact)
        return artifact

    def latest(self, name: ArtifactName | str) -> Artifact | None:
        """Return the most recent version of `name`, or None."""
        if isinstance(name, str):
            name = ArtifactName(name)
        with self._lock:
            history = self._store.get(name)
            return history[-1] if history else None

    def history(self, name: ArtifactName | str) -> list[Artifact]:
        """Return all retained versions oldest→newest."""
        if isinstance(name, str):
            name = ArtifactName(name)
        with self._lock:
            return list(self._store.get(name, []))

    def has(self, name: ArtifactName | str) -> bool:
        return self.latest(name) is not None

    def all_latest(self) -> dict[ArtifactName, Artifact]:
        """Snapshot: name → latest artifact."""
        with self._lock:
            return {n: h[-1] for n, h in self._store.items() if h}

    # ============================================================ subscribers

    def subscribe(
        self, agent: str, callback: Callable[[Artifact], None]
    ) -> None:
        """Register a callback triggered when an artifact the agent subscribes
        to is published. Used by orchestrator to kick off the next agent.
        """
        with self._lock:
            self._listeners[agent].append(callback)

    def _notify_subscribers(self, artifact: Artifact) -> None:
        """Invoke callbacks for all agents subscribed to this artifact."""
        subs = SUBSCRIBERS.get(artifact.name, set())
        callbacks: list[Callable[[Artifact], None]] = []
        with self._lock:
            for agent in subs:
                callbacks.extend(self._listeners.get(agent, []))
        for cb in callbacks:
            try:
                cb(artifact)
            except Exception as e:
                log.error("subscriber_callback_failed",
                          artifact=artifact.name.value, err=str(e))

    def subscriptions_for(self, agent: str) -> list[Artifact]:
        """Return latest versions of all artifacts `agent` subscribes to."""
        result: list[Artifact] = []
        for name, subs in SUBSCRIBERS.items():
            if agent in subs:
                a = self.latest(name)
                if a is not None:
                    result.append(a)
        return result

    # ============================================================= rendering

    def snapshot_for_agent(
        self,
        agent: str,
        *,
        include: list[ArtifactName] | None = None,
        max_chars_per_artifact: int = 4000,
    ) -> str:
        """Render the subset of blackboard the agent should see, as a single
        string suitable for passing to AnthropicClient as `shared_artifacts`.

        This is the LAYER 3 cache content per config/caching.yaml. It changes
        only when an upstream agent publishes something new, so the prefix
        remains cacheable for multiple turns of the same agent.
        """
        if include is not None:
            artifacts = [self.latest(n) for n in include]
            artifacts = [a for a in artifacts if a is not None]
        else:
            artifacts = self.subscriptions_for(agent)

        if not artifacts:
            return ""

        # Sort by canonical artifact ordering (stable across turns for caching)
        name_order = {n: i for i, n in enumerate(ArtifactName)}
        artifacts.sort(key=lambda a: name_order.get(a.name, 999))

        parts = [f"# Blackboard snapshot for '{agent}'"]
        for a in artifacts:
            parts.append(a.render_for_prompt(max_chars=max_chars_per_artifact))
        return "\n".join(parts)

    # ========================================================= stall detection

    def recent_publishers(self, within_seconds: float = 300.0) -> list[str]:
        """Return list of agent names that published something recently.

        Used by Progress Ledger: if over some window no new artifacts were
        produced, we have stalled.
        """
        now = time.time()
        with self._lock:
            return [
                agent for ts, _name, agent in self._publish_log
                if now - ts <= within_seconds
            ]

    def publish_count_for(self, agent: str, within_seconds: float = 300.0) -> int:
        return sum(1 for a in self.recent_publishers(within_seconds) if a == agent)

    # ============================================================ persistence

    def save(self, path: Path | str) -> None:
        """Serialize all artifacts to JSON. FILE-kind artifacts only save the
        path, not the binary (binary files stay on disk).
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            data = {
                "saved_at": time.time(),
                "artifacts": {
                    n.value: [a.to_dict() for a in history]
                    for n, history in self._store.items()
                },
            }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        log.info("blackboard_saved", path=str(path),
                 n_artifacts=sum(len(h) for h in data["artifacts"].values()))

    def load(self, path: Path | str) -> None:
        """Restore blackboard from a previous save()."""
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        with self._lock:
            self._store.clear()
            for name_str, entries in data["artifacts"].items():
                dq = self._store[ArtifactName(name_str)]
                for d in entries:
                    dq.append(Artifact.from_dict(d))
        log.info("blackboard_loaded", path=str(path))

    # ================================================================ helpers

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                n.value: {
                    "versions": len(h),
                    "latest_producer": h[-1].producer if h else None,
                    "latest_version": h[-1].version if h else 0,
                }
                for n, h in self._store.items()
            }
