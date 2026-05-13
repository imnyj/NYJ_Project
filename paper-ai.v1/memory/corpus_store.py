"""Corpus store: papers + contextual chunks + hybrid indexing.

Single SQLite file that combines:
    - Relational metadata (papers table)
    - Contextual chunks (chunks table)
    - BM25 inverted index (via FTS5)
    - Dense vector index (via sqlite-vec, optional)

Why SQLite over pgvector/Qdrant for a single-user WSL2 system:
    - Single file, trivial to back up (cp) or reset (rm)
    - Zero daemon — survives WSL2 hibernation without state tracking
    - FTS5 is built-in (no extra package for BM25)
    - sqlite-vec is a single pip install

Schema:
    papers(id, doi, s2_corpus_id, title, authors_json, year, venue,
           abstract, verified, retracted, added_at)
    chunks(id, paper_id, chunk_idx, text, context_prefix, tokens, added_at)
    chunks_fts — FTS5 virtual table over (text, context_prefix)
    chunk_vec — sqlite-vec virtual table over chunk embeddings (optional)
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger("corpus_store")

# Optional: sqlite-vec enables dense retrieval inside SQLite
try:
    import sqlite_vec  # noqa: F401
    _VEC_AVAILABLE = True
except ImportError:
    _VEC_AVAILABLE = False


# ----------------------------------------------------------------- DTOs

@dataclass
class PaperRecord:
    doi: str | None
    s2_corpus_id: str | None
    title: str
    authors: list[str]
    year: int | None
    venue: str
    abstract: str
    verified: bool = False
    retracted: bool = False

    def citation_id(self) -> str:
        """Canonical ID used in Writer's `\\cite{...}` markers."""
        if self.s2_corpus_id:
            return f"corpusID:{self.s2_corpus_id}"
        if self.doi:
            return f"doi:{self.doi}"
        raise ValueError("paper has neither doi nor s2_corpus_id")


@dataclass
class ChunkRecord:
    paper_id: int
    chunk_idx: int
    text: str
    context_prefix: str = ""        # Contextual Retrieval prefix
    tokens: int = 0

    @property
    def combined_text(self) -> str:
        """Text to actually index / embed (context first, then content)."""
        if self.context_prefix:
            return f"{self.context_prefix}\n\n{self.text}"
        return self.text


# ----------------------------------------------------------------- Store

class CorpusStore:
    """Hybrid BM25 + vector store on a single SQLite file.

    Thread-safe via SQLite's own locking (WAL mode).
    """

    def __init__(
        self,
        path: Path | str | None = None,
        embedding_dim: int = 768,
    ):
        if path is None:
            from core.paths import get_paths
            path = get_paths().corpus_db
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim
        self._vec_enabled = False
        self._init_db()

    # ---------------------------------------------------------------- schema

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30.0)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        # Try to load sqlite-vec extension
        if _VEC_AVAILABLE:
            try:
                c.enable_load_extension(True)
                import sqlite_vec
                sqlite_vec.load(c)
                c.enable_load_extension(False)
                self._vec_enabled = True
            except Exception as e:
                log.debug("sqlite_vec_load_failed", err=str(e))
        return c

    def _init_db(self) -> None:
        with self._conn() as c:
            c.executescript(f"""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doi TEXT UNIQUE,
                    s2_corpus_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    authors_json TEXT,
                    year INTEGER,
                    venue TEXT,
                    abstract TEXT,
                    verified INTEGER DEFAULT 0,
                    retracted INTEGER DEFAULT 0,
                    added_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
                CREATE INDEX IF NOT EXISTS idx_papers_s2 ON papers(s2_corpus_id);

                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    chunk_idx INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    context_prefix TEXT DEFAULT '',
                    tokens INTEGER DEFAULT 0,
                    added_at REAL NOT NULL,
                    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_paper ON chunks(paper_id);

                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    text,
                    context_prefix,
                    content='chunks',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );

                -- keep FTS in sync with chunks via triggers
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text, context_prefix)
                    VALUES (new.id, new.text, new.context_prefix);
                END;
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, context_prefix)
                    VALUES ('delete', old.id, old.text, old.context_prefix);
                END;
                CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, context_prefix)
                    VALUES ('delete', old.id, old.text, old.context_prefix);
                    INSERT INTO chunks_fts(rowid, text, context_prefix)
                    VALUES (new.id, new.text, new.context_prefix);
                END;
            """)

            # Vec table (optional)
            if self._vec_enabled:
                try:
                    c.execute(f"""
                        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vec USING vec0(
                            chunk_id INTEGER PRIMARY KEY,
                            embedding FLOAT[{self.embedding_dim}]
                        )
                    """)
                    log.info("sqlite_vec_enabled", dim=self.embedding_dim)
                except Exception as e:
                    log.warning("vec_table_create_failed", err=str(e))
                    self._vec_enabled = False

    @property
    def has_vector_index(self) -> bool:
        return self._vec_enabled

    # ------------------------------------------------------------- papers

    def upsert_paper(self, paper: PaperRecord) -> int:
        """Insert or update by (doi OR s2_corpus_id). Returns paper.id."""
        with self._conn() as c:
            # Look up existing
            row = None
            if paper.doi:
                row = c.execute(
                    "SELECT id FROM papers WHERE doi = ?", (paper.doi,),
                ).fetchone()
            if row is None and paper.s2_corpus_id:
                row = c.execute(
                    "SELECT id FROM papers WHERE s2_corpus_id = ?",
                    (paper.s2_corpus_id,),
                ).fetchone()

            if row:
                pid = row[0]
                c.execute(
                    """UPDATE papers SET title=?, authors_json=?, year=?,
                       venue=?, abstract=?, verified=?, retracted=?
                       WHERE id=?""",
                    (paper.title, json.dumps(paper.authors, ensure_ascii=False),
                     paper.year, paper.venue, paper.abstract,
                     int(paper.verified), int(paper.retracted), pid),
                )
                return pid
            cur = c.execute(
                """INSERT INTO papers
                   (doi, s2_corpus_id, title, authors_json, year, venue,
                    abstract, verified, retracted, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (paper.doi, paper.s2_corpus_id, paper.title,
                 json.dumps(paper.authors, ensure_ascii=False),
                 paper.year, paper.venue, paper.abstract,
                 int(paper.verified), int(paper.retracted), time.time()),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_paper(self, paper_id: int) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM papers WHERE id=?", (paper_id,),
            ).fetchone()
            if not row:
                return None
            cols = [d[0] for d in c.execute("SELECT * FROM papers LIMIT 0").description]
            rec = dict(zip(cols, row, strict=False))
            rec["authors"] = json.loads(rec.get("authors_json") or "[]")
            return rec

    def list_papers(self, *, verified_only: bool = False) -> list[dict]:
        q = "SELECT * FROM papers"
        if verified_only:
            q += " WHERE verified=1 AND retracted=0"
        with self._conn() as c:
            rows = c.execute(q).fetchall()
            cols = [d[0] for d in c.execute("SELECT * FROM papers LIMIT 0").description]
        out = [dict(zip(cols, r, strict=False)) for r in rows]
        for r in out:
            r["authors"] = json.loads(r.get("authors_json") or "[]")
        return out

    # ------------------------------------------------------------- chunks

    def upsert_chunks(
        self,
        chunks: list[ChunkRecord],
        *,
        embeddings: "list | None" = None,
    ) -> list[int]:
        """Insert chunks and (optionally) their dense vectors.

        Truly upsert: any existing chunks for the same paper_id are DELETED
        first so re-indexing the same paper doesn't accumulate duplicates.
        (Previously this was an insert-only, which caused silent duplicate
        search results after a paper was re-processed.)
        """
        if embeddings is not None and len(embeddings) != len(chunks):
            raise ValueError("embeddings count mismatch")

        # Collect distinct paper_ids being (re)written so we can clear them.
        paper_ids = {ch.paper_id for ch in chunks}

        ids: list[int] = []
        with self._conn() as c:
            # Wipe prior chunks for these papers to prevent duplicate index
            # entries on re-run. Foreign-key cascade on chunk_vec handles the
            # vector rows if the extension is loaded with FK on.
            for pid in paper_ids:
                c.execute("DELETE FROM chunks WHERE paper_id = ?", (pid,))
                if self._vec_enabled:
                    # vec table has no FK cascade in sqlite-vec, clear manually
                    c.execute(
                        "DELETE FROM chunk_vec WHERE chunk_id IN "
                        "(SELECT id FROM chunks WHERE paper_id = ?)",
                        (pid,),
                    )
            for i, ch in enumerate(chunks):
                cur = c.execute(
                    """INSERT INTO chunks
                       (paper_id, chunk_idx, text, context_prefix, tokens, added_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (ch.paper_id, ch.chunk_idx, ch.text, ch.context_prefix,
                     ch.tokens, time.time()),
                )
                cid = cur.lastrowid
                ids.append(cid)  # type: ignore[arg-type]

                if embeddings is not None and self._vec_enabled:
                    import numpy as np
                    vec = np.asarray(embeddings[i], dtype=np.float32).tobytes()
                    c.execute(
                        "INSERT INTO chunk_vec (chunk_id, embedding) VALUES (?, ?)",
                        (cid, vec),
                    )
        log.info("chunks_upserted", count=len(ids),
                 with_vectors=embeddings is not None and self._vec_enabled)
        return ids

    # ------------------------------------------------------------- search

    def bm25_search(
        self, query: str, *, top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """FTS5 BM25 ranked search over chunks."""
        # Escape FTS5 special chars; fall back to a phrase-quoted query
        cleaned = _escape_fts5(query)
        if cleaned in ('""', ''):
            log.debug("bm25_empty_query", original=query[:50])
            return []
        sql = """
            SELECT c.id AS chunk_id,
                   c.paper_id,
                   c.chunk_idx,
                   c.text,
                   c.context_prefix,
                   bm25(chunks_fts) AS bm25_score
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY bm25_score ASC
            LIMIT ?
        """
        with self._conn() as c:
            try:
                rows = c.execute(sql, (cleaned, top_k)).fetchall()
            except sqlite3.OperationalError as e:
                log.warning("bm25_query_failed", err=str(e), query=cleaned[:80])
                return []
        cols = ["chunk_id", "paper_id", "chunk_idx", "text",
                "context_prefix", "bm25_score"]
        # FTS5 bm25() returns NEGATIVE scores (lower = more relevant).
        # Flip sign so downstream RRF sees higher = better.
        out = []
        for r in rows:
            d = dict(zip(cols, r, strict=False))
            d["bm25_score"] = -float(d["bm25_score"])
            out.append(d)
        return out

    def vector_search(
        self,
        query_vec: "list | Any",
        *,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Dense retrieval via sqlite-vec. Returns [] if vec not enabled."""
        if not self._vec_enabled:
            log.debug("vector_search_skipped_no_vec")
            return []
        import numpy as np
        qv = np.asarray(query_vec, dtype=np.float32).tobytes()
        sql = """
            SELECT cv.chunk_id,
                   c.paper_id,
                   c.chunk_idx,
                   c.text,
                   c.context_prefix,
                   vec_distance_cosine(cv.embedding, ?) AS vec_distance
            FROM chunk_vec cv
            JOIN chunks c ON c.id = cv.chunk_id
            ORDER BY vec_distance ASC
            LIMIT ?
        """
        with self._conn() as c:
            try:
                rows = c.execute(sql, (qv, top_k)).fetchall()
            except sqlite3.OperationalError as e:
                log.warning("vector_query_failed", err=str(e))
                return []
        cols = ["chunk_id", "paper_id", "chunk_idx", "text",
                "context_prefix", "vec_distance"]
        out = [dict(zip(cols, r, strict=False)) for r in rows]
        # Convert distance → similarity score (higher = better)
        for r in out:
            r["vec_score"] = 1.0 - float(r["vec_distance"])
        return out

    # ---------------------------------------------------------- maintenance

    def stats(self) -> dict[str, int]:
        with self._conn() as c:
            (np_,) = c.execute("SELECT COUNT(*) FROM papers").fetchone()
            (nc,) = c.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return {"papers": np_, "chunks": nc, "vec_enabled": int(self._vec_enabled)}

    def reset(self) -> None:
        """DELETE EVERYTHING. For tests only."""
        with self._conn() as c:
            c.executescript("""
                DELETE FROM chunks;
                DELETE FROM papers;
            """)
            if self._vec_enabled:
                try:
                    c.execute("DELETE FROM chunk_vec")
                except sqlite3.OperationalError:
                    pass


# ----------------------------------------------------- helpers

_FTS5_SPECIAL = set('"()-*:^')


def _escape_fts5(q: str) -> str:
    """Turn an arbitrary user query into a safe FTS5 MATCH expression.

    Simplest robust approach: quote the whole thing as a phrase. This loses
    prefix/wildcard features but avoids syntax errors from user punctuation.
    """
    cleaned = q.replace('"', ' ').replace("*", " ").strip()
    if not cleaned:
        return '""'
    # split into tokens, quote each, join with OR for some recall
    tokens = [t for t in cleaned.split() if len(t) > 1]
    if not tokens:
        return '""'
    return ' OR '.join(f'"{t}"' for t in tokens)
