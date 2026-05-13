"""Local LLM response cache (SQLite-backed).

Rationale:
    - Anthropic's prompt cache is PER-PREFIX (same system blocks).
    - Our local cache is PER-REQUEST (same exact prompt → same response).
    - Very useful for idempotent tasks: classification, metadata extraction,
      deterministic reformatting. NOT for creative drafting.

Keyed by:
    sha256(model + system_blocks_hash + messages_hash + tool_hash + max_tokens)

Usage:
    cache = ResponseCache()
    key = cache.make_key(model, system, messages, tools, max_tokens)
    if (hit := cache.get(key)) is not None:
        return hit
    resp = api_call()
    cache.put(key, resp)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("response_cache")


class ResponseCache:
    """Thread-safe (SQLite handles locking) response cache."""

    def __init__(
        self,
        path: Path | str | None = None,
        ttl_seconds: int = 7 * 24 * 3600,  # 7 days
    ):
        if path is None:
            from core.paths import get_paths
            path = get_paths().response_cache_db
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds
        self._init_db()
        self._hits = 0
        self._misses = 0

    # ---------------------------------------------------------------- schema

    def _init_db(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_created ON responses(created_at)"
            )

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30.0)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    # ------------------------------------------------------------- public API

    @staticmethod
    def make_key(
        model: str,
        system: Any,
        messages: Any,
        tools: Any,
        max_tokens: int,
    ) -> str:
        payload = json.dumps(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "tools": tools,
                "max_tokens": max_tokens,
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT response_json, created_at FROM responses WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            self._misses += 1
            return None
        response_json, created_at = row
        if (time.time() - created_at) > self.ttl:
            self.evict(key)
            self._misses += 1
            return None
        self._hits += 1
        log.debug("local_cache_hit", key_prefix=key[:12])
        return json.loads(response_json)

    def put(self, key: str, response: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO responses (key, response_json, model, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    key,
                    json.dumps(response, ensure_ascii=False, default=str),
                    response.get("model", "unknown"),
                    time.time(),
                ),
            )
        log.debug("local_cache_put", key_prefix=key[:12])

    def evict(self, key: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM responses WHERE key = ?", (key,))

    def purge_expired(self) -> int:
        cutoff = time.time() - self.ttl
        with self._conn() as c:
            cur = c.execute("DELETE FROM responses WHERE created_at < ?", (cutoff,))
            return cur.rowcount

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        ratio = (self._hits / total) if total else 0.0
        with self._conn() as c:
            (size,) = c.execute("SELECT COUNT(*) FROM responses").fetchone()
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(ratio, 3),
            "entries": size,
        }
