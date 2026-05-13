"""Voyager-style skill library.

Research: Wang et al., "Voyager: An Open-Ended Embodied Agent with LLMs"
(NVIDIA, arXiv:2305.16291, NeurIPS 2023).

Pattern:
    1. When Experimenter writes working code (unit tests passed),
       .commit_skill() is called with the function + its docstring.
    2. Docstring is embedded via SPECTER2; stored alongside the code.
    3. Before writing new code for a task, .retrieve() finds top-K matching
       skills. If similarity > 0.6, compose rather than regenerate.

This turns one-off code generation into an accumulating capability — the
N-th scenario involves fewer new lines than the first, because
fundamental-diagram plotting, AoI computation, etc. are already saved.

Token savings compound: a 200-line scenario that reuses 150 lines of
skills only asks the LLM to write ~50 new lines.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("skill_library")


@dataclass
class Skill:
    name: str
    docstring: str
    code: str
    language: str = "python"
    tags: list[str] | None = None
    use_count: int = 0
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "docstring": self.docstring,
            "code": self.code, "language": self.language,
            "tags": self.tags or [],
            "use_count": self.use_count,
            "created_at": self.created_at,
        }


class SkillLibrary:
    """SQLite-backed skill store with optional dense retrieval."""

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        embedder=None,
    ):
        if path is None:
            from core.paths import get_paths
            path = get_paths().skill_library_db
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder
        self._init()

    @property
    def embedder(self):
        if self._embedder is None:
            from tools.embeddings import get_default_embedder
            self._embedder = get_default_embedder()
        return self._embedder

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30.0)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    docstring TEXT NOT NULL,
                    code TEXT NOT NULL,
                    language TEXT NOT NULL,
                    tags_json TEXT,
                    use_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    embedding BLOB
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                    name, docstring, code,
                    content='skills', content_rowid='id',
                    tokenize='porter unicode61'
                );
                CREATE TRIGGER IF NOT EXISTS skills_ai AFTER INSERT ON skills BEGIN
                    INSERT INTO skills_fts(rowid, name, docstring, code)
                    VALUES (new.id, new.name, new.docstring, new.code);
                END;
                CREATE TRIGGER IF NOT EXISTS skills_au AFTER UPDATE ON skills BEGIN
                    INSERT INTO skills_fts(skills_fts, rowid, name, docstring, code)
                    VALUES ('delete', old.id, old.name, old.docstring, old.code);
                    INSERT INTO skills_fts(rowid, name, docstring, code)
                    VALUES (new.id, new.name, new.docstring, new.code);
                END;
            """)

    # ----------------------------------------------------- commit

    def commit(self, skill: Skill) -> int:
        """Store or update a skill. Returns row id."""
        # Quick static sanity check for Python code
        if skill.language == "python":
            try:
                ast.parse(skill.code)
            except SyntaxError as e:
                raise ValueError(
                    f"skill {skill.name!r} has a Python syntax error: {e}"
                ) from e

        emb_blob: bytes | None = None
        try:
            import numpy as np
            v = self.embedder.encode_one(skill.docstring)
            emb_blob = np.asarray(v, dtype=np.float32).tobytes()
        except Exception as e:
            log.debug("skill_embed_skipped", err=str(e))

        skill.created_at = skill.created_at or time.time()
        with self._conn() as c:
            row = c.execute(
                "SELECT id, use_count FROM skills WHERE name=?",
                (skill.name,),
            ).fetchone()
            if row:
                sid, use_count = row
                c.execute(
                    """UPDATE skills
                       SET docstring=?, code=?, language=?, tags_json=?,
                           embedding=?
                       WHERE id=?""",
                    (skill.docstring, skill.code, skill.language,
                     json.dumps(skill.tags or []), emb_blob, sid),
                )
                log.info("skill_updated", name=skill.name, use_count=use_count)
                return sid
            cur = c.execute(
                """INSERT INTO skills
                   (name, docstring, code, language, tags_json,
                    use_count, created_at, embedding)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (skill.name, skill.docstring, skill.code, skill.language,
                 json.dumps(skill.tags or []), 0, skill.created_at, emb_blob),
            )
            new_id = cur.lastrowid
        log.info("skill_committed", name=skill.name, id=new_id)
        return new_id  # type: ignore[return-value]

    # ----------------------------------------------------- retrieve

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[tuple[Skill, float]]:
        """Top-K skills by docstring similarity. Falls back to BM25 if no embedding."""
        results: list[tuple[Skill, float]] = []
        try:
            import numpy as np
            qv = self.embedder.encode_one(query).astype(np.float32)
            qdim = qv.shape[0]
            with self._conn() as c:
                rows = c.execute(
                    "SELECT id, name, docstring, code, language, tags_json, "
                    "use_count, created_at, embedding FROM skills"
                ).fetchall()
            skipped_dim_mismatch = 0
            for row in rows:
                emb = row[8]
                if not emb:
                    continue
                sv = np.frombuffer(emb, dtype=np.float32)
                # Embedding dim can differ across runs (SPECTER2 768 vs
                # HashEmbedder 128). A silent dot-product would error with
                # "shape mismatch" and then we'd fall back to BM25 losing
                # quality. Explicitly skip mismatched-dim rows and log.
                if sv.shape[0] != qdim:
                    skipped_dim_mismatch += 1
                    continue
                sim = float(np.dot(qv, sv))
                if sim >= min_similarity:
                    results.append((_row_to_skill(row), sim))
            if skipped_dim_mismatch:
                log.warning("skill_embedding_dim_mismatch",
                            query_dim=qdim,
                            skipped=skipped_dim_mismatch,
                            total=len(rows))
            results.sort(key=lambda r: r[1], reverse=True)
            if results:
                return results[:top_k]
        except Exception as e:
            log.debug("embed_retrieval_failed", err=str(e))

        # BM25 fallback
        with self._conn() as c:
            bm25_rows = c.execute(
                """SELECT s.id, s.name, s.docstring, s.code, s.language,
                          s.tags_json, s.use_count, s.created_at, s.embedding,
                          bm25(skills_fts) AS score
                   FROM skills_fts
                   JOIN skills s ON s.id = skills_fts.rowid
                   WHERE skills_fts MATCH ?
                   ORDER BY score ASC
                   LIMIT ?""",
                (_escape_fts5(query), top_k),
            ).fetchall()
        return [(_row_to_skill(r[:9]), -float(r[9])) for r in bm25_rows]

    # ----------------------------------------------------- use

    def note_use(self, skill_name: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE skills SET use_count = use_count + 1 WHERE name=?",
                (skill_name,),
            )

    # ----------------------------------------------------- helpers

    def stats(self) -> dict[str, Any]:
        with self._conn() as c:
            (n,) = c.execute("SELECT COUNT(*) FROM skills").fetchone()
            (uses,) = c.execute(
                "SELECT COALESCE(SUM(use_count), 0) FROM skills"
            ).fetchone()
        return {"skills": n, "total_uses": uses, "path": str(self.path)}

    def list_all(self) -> list[Skill]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, name, docstring, code, language, tags_json, "
                "use_count, created_at FROM skills ORDER BY use_count DESC"
            ).fetchall()
        return [_row_to_skill_no_emb(r) for r in rows]


def _row_to_skill(row: tuple) -> Skill:
    return Skill(
        name=row[1], docstring=row[2], code=row[3], language=row[4],
        tags=json.loads(row[5] or "[]"),
        use_count=row[6], created_at=row[7],
    )


def _row_to_skill_no_emb(row: tuple) -> Skill:
    return Skill(
        name=row[1], docstring=row[2], code=row[3], language=row[4],
        tags=json.loads(row[5] or "[]"),
        use_count=row[6], created_at=row[7],
    )


def _escape_fts5(q: str) -> str:
    cleaned = q.replace('"', ' ').replace("*", " ").strip()
    tokens = [t for t in cleaned.split() if len(t) > 1]
    return " OR ".join(f'"{t}"' for t in tokens) if tokens else '""'


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]
