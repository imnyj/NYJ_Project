"""Phase 3 offline tests — advanced RAG (no network, no heavy deps needed).

Verifies:
    - CorpusStore BM25 + paper upsert idempotence
    - ContextualChunker split logic (pure string ops)
    - RRF fusion math
    - HashEmbedder fallback (deterministic, L2-normalized)
    - NoOpReranker preserves order
    - CitationVerifier catches missing IDs without network
    - SCIE whitelist enforcement
    - LibrarianAgent boots with lazy tool properties
"""

from __future__ import annotations

import numpy as np
import pytest

from memory.corpus_store import ChunkRecord, CorpusStore, PaperRecord
from retrieval.citation_verifier import (
    BLOCKED_DOMAINS,
    SCIE_DOMAINS,
    CitationVerifier,
)
from retrieval.contextual_retrieval import split_into_raw_chunks
from retrieval.hybrid_search import reciprocal_rank_fusion
from tools.embeddings import HashEmbedder, get_default_embedder
from tools.reranker import NoOpReranker
from tools.web_search import _is_whitelisted


# ============================================================== corpus store


def test_corpus_store_upsert_paper_is_idempotent(tmp_path):
    store = CorpusStore(path=tmp_path / "c.sqlite3", embedding_dim=128)
    paper = PaperRecord(
        doi="10.1109/tvt.2024.123",
        s2_corpus_id="99001",
        title="AoI-aware V2X beaconing",
        authors=["Kim H", "Park S"],
        year=2024,
        venue="IEEE TVT",
        abstract="We propose an AoI-aware scheme.",
    )
    pid1 = store.upsert_paper(paper)
    pid2 = store.upsert_paper(paper)
    assert pid1 == pid2
    assert pid1 > 0


def test_corpus_store_bm25_finds_inserted_chunks(tmp_path):
    store = CorpusStore(path=tmp_path / "c.sqlite3", embedding_dim=128)
    pid = store.upsert_paper(PaperRecord(
        doi="10.1/a", s2_corpus_id="1",
        title="t", authors=[], year=2024, venue="v", abstract=""
    ))
    store.upsert_chunks([
        ChunkRecord(paper_id=pid, chunk_idx=0,
                    text="Age of Information measures freshness.",
                    context_prefix="intro"),
        ChunkRecord(paper_id=pid, chunk_idx=1,
                    text="DCC tuning with AoI feedback.",
                    context_prefix="main"),
    ])
    hits = store.bm25_search("AoI beaconing", top_k=5)
    assert len(hits) >= 1
    assert all("chunk_id" in h for h in hits)
    assert all("bm25_score" in h for h in hits)


def test_corpus_store_stats_reflects_inserts(tmp_path):
    store = CorpusStore(path=tmp_path / "c.sqlite3", embedding_dim=128)
    assert store.stats()["papers"] == 0
    pid = store.upsert_paper(PaperRecord(
        doi="10.1/a", s2_corpus_id="1",
        title="t", authors=[], year=2024, venue="v", abstract=""
    ))
    store.upsert_chunks([
        ChunkRecord(paper_id=pid, chunk_idx=0, text="x", context_prefix=""),
    ])
    stats = store.stats()
    assert stats["papers"] == 1 and stats["chunks"] == 1


# ============================================================= chunker


def test_split_into_raw_chunks_respects_size():
    long_text = "\n\n".join(
        f"Paragraph {i}. " + "word " * 50 for i in range(10)
    )
    chunks = split_into_raw_chunks(long_text, chunk_chars=400)
    assert len(chunks) >= 2
    # No chunk should be vastly over the limit (some slack for overlap)
    for c in chunks:
        assert len(c) <= 600


def test_split_into_raw_chunks_empty_is_empty():
    assert split_into_raw_chunks("") == []


# ================================================================== RRF


def test_rrf_boosts_chunks_appearing_in_both_lists():
    bm25 = [
        {"chunk_id": 1, "paper_id": 100, "chunk_idx": 0, "text": "a",
         "context_prefix": "", "bm25_score": 5.0},
        {"chunk_id": 2, "paper_id": 100, "chunk_idx": 1, "text": "b",
         "context_prefix": "", "bm25_score": 3.0},
    ]
    vec = [
        {"chunk_id": 2, "paper_id": 100, "chunk_idx": 1, "text": "b",
         "context_prefix": "", "vec_score": 0.9},
        {"chunk_id": 3, "paper_id": 101, "chunk_idx": 0, "text": "c",
         "context_prefix": "", "vec_score": 0.7},
    ]
    fused = reciprocal_rank_fusion(bm25, vec, k=60)
    # chunk 2 appears in BOTH → should be top
    assert fused[0].chunk_id == 2
    assert set(fused[0].sources) == {"bm25", "vec"}


def test_rrf_empty_inputs_return_empty():
    assert reciprocal_rank_fusion([], []) == []


# ============================================================= embeddings


def test_hash_embedder_is_deterministic_and_normalized():
    e = HashEmbedder(dim=128)
    v1 = e.encode(["hello world"])
    v2 = e.encode(["hello world"])
    assert v1.shape == (1, 128)
    assert np.allclose(v1, v2)
    # L2-normalized
    assert np.isclose(np.linalg.norm(v1[0]), 1.0, atol=1e-5)


def test_default_embedder_has_positive_dim():
    e = get_default_embedder()
    assert e.dim > 0


# ================================================================ reranker


def test_noop_reranker_preserves_input_order():
    r = NoOpReranker()
    candidates = [{"text": "first"}, {"text": "second"}, {"text": "third"}]
    out = r.rerank("query", candidates, top_k=2)
    assert len(out) == 2
    assert out[0]["text"] == "first"
    assert "rerank_score" in out[0]


# ======================================================= citation verifier


def test_verifier_rejects_entry_with_no_ids():
    v = CitationVerifier(mailto="test@example.com")
    result = v.verify({"title": "has no ids"})
    assert not result.verified
    assert any(i.code == "no_id" for i in result.issues)
    assert result.has_fatal()


# ======================================================== SCIE whitelist


@pytest.mark.parametrize("url,expected", [
    ("https://ieeexplore.ieee.org/document/123", True),
    ("https://www.sciencedirect.com/science/article/pii/xxx", True),
    ("https://dl.acm.org/doi/10.1/abc", True),
    ("https://arxiv.org/abs/2401.00001", False),
    ("https://www.researchgate.net/publication/xxx", False),
    ("https://scholar.google.com/citations?user=xxx", False),
    ("", False),
])
def test_scie_whitelist_matches_expected(url, expected):
    assert _is_whitelisted(url) is expected


def test_whitelist_and_blocklist_contents():
    assert "ieeexplore.ieee.org" in SCIE_DOMAINS
    assert "sciencedirect.com" in SCIE_DOMAINS
    assert "arxiv.org" in BLOCKED_DOMAINS
    assert "researchgate.net" in BLOCKED_DOMAINS
    # No overlap
    assert SCIE_DOMAINS.isdisjoint(BLOCKED_DOMAINS)


# =================================================== LibrarianAgent boot


def test_librarian_agent_allowed_tools(mock_client_with_policy):
    from agents import make_worker
    lib = make_worker("librarian", mock_client_with_policy)
    assert lib.allowed_tools() == frozenset({
        "web_search", "pdf_reader", "paperqa_query", "citation_verify",
    })


def test_librarian_lazy_verifier_property(mock_client_with_policy):
    from agents import make_worker
    lib = make_worker("librarian", mock_client_with_policy)
    assert lib._verifier is None   # lazy
    v = lib.verifier
    assert v is not None
    # Second access returns same instance
    assert lib.verifier is v
