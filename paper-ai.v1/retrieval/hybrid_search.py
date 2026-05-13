"""Hybrid retrieval: BM25 + dense vectors fused via Reciprocal Rank Fusion.

The research-backed stack (Anthropic Contextual Retrieval ablations 2024):
    (a) BM25 over (context_prefix + text)         [keyword recall]
    (b) Vector search over SPECTER2 embeddings     [semantic recall]
    (c) Reciprocal Rank Fusion, k=60               [score combination]
    (d) bge-reranker-v2-m3 over top-K fused        [precision]

RRF is preferred over weighted-sum fusion because:
    - No hyperparameter tuning (k=60 is the proven default)
    - Robust to different score scales (BM25 negative-log vs cosine in [-1,1])
    - Cormack et al. 2009 showed RRF ≥ every learned fusion they tested
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.logger import get_logger
from memory.corpus_store import CorpusStore
from tools.embeddings import get_default_embedder
from tools.reranker import get_default_reranker

log = get_logger("hybrid_search")

if TYPE_CHECKING:
    pass


RRF_K = 60       # Cormack et al. default
BM25_K = 30      # top-K from BM25 before fusion
VECTOR_K = 30    # top-K from vector before fusion
FUSED_K = 20     # top-K of fused pool to send to reranker
FINAL_K = 8      # top-K after reranking to feed the generator


@dataclass
class SearchHit:
    chunk_id: int
    paper_id: int
    chunk_idx: int
    text: str
    context_prefix: str
    bm25_score: float = 0.0
    vec_score: float = 0.0
    bm25_rank: int | None = None
    vec_rank: int | None = None
    rrf_score: float = 0.0
    rerank_score: float = 0.0
    sources: list[str] = field(default_factory=list)

    def render(self) -> str:
        ctx = f"{self.context_prefix}\n\n" if self.context_prefix else ""
        return f"{ctx}{self.text}"


# ========================================================== RRF combination

def reciprocal_rank_fusion(
    bm25_hits: list[dict],
    vec_hits: list[dict],
    *,
    k: int = RRF_K,
) -> list[SearchHit]:
    """Combine two ranked lists. Chunks appearing in both get boosted."""
    fused: dict[int, SearchHit] = {}

    for rank, hit in enumerate(bm25_hits):
        cid = hit["chunk_id"]
        entry = fused.setdefault(cid, SearchHit(
            chunk_id=cid,
            paper_id=hit["paper_id"],
            chunk_idx=hit["chunk_idx"],
            text=hit["text"],
            context_prefix=hit.get("context_prefix", ""),
        ))
        entry.bm25_score = hit.get("bm25_score", 0.0)
        entry.bm25_rank = rank
        entry.rrf_score += 1.0 / (k + rank + 1)
        entry.sources.append("bm25")

    for rank, hit in enumerate(vec_hits):
        cid = hit["chunk_id"]
        entry = fused.setdefault(cid, SearchHit(
            chunk_id=cid,
            paper_id=hit["paper_id"],
            chunk_idx=hit["chunk_idx"],
            text=hit["text"],
            context_prefix=hit.get("context_prefix", ""),
        ))
        entry.vec_score = hit.get("vec_score", 0.0)
        entry.vec_rank = rank
        entry.rrf_score += 1.0 / (k + rank + 1)
        entry.sources.append("vec")

    merged = sorted(fused.values(), key=lambda h: h.rrf_score, reverse=True)
    return merged


# ============================================================ orchestrator

class HybridSearch:
    """End-to-end: query → BM25 + vector → RRF → rerank → final top-k."""

    def __init__(
        self,
        store: CorpusStore,
        *,
        embedder=None,
        reranker=None,
    ):
        self.store = store
        self.embedder = embedder or get_default_embedder()
        self.reranker = reranker or get_default_reranker()

    def search(
        self,
        query: str,
        *,
        bm25_k: int = BM25_K,
        vector_k: int = VECTOR_K,
        fused_k: int = FUSED_K,
        final_k: int = FINAL_K,
        enable_rerank: bool = True,
    ) -> list[SearchHit]:
        """Run the full hybrid pipeline."""
        # 1. BM25
        bm25_hits = self.store.bm25_search(query, top_k=bm25_k)

        # 2. Vector (best-effort)
        vec_hits: list[dict] = []
        if self.store.has_vector_index:
            try:
                qv = self.embedder.encode_one(query)
                vec_hits = self.store.vector_search(qv, top_k=vector_k)
            except Exception as e:
                log.warning("vec_search_skipped", err=str(e))

        # 3. RRF fusion
        fused = reciprocal_rank_fusion(bm25_hits, vec_hits)[:fused_k]

        log.info("hybrid_stats",
                 bm25_n=len(bm25_hits),
                 vec_n=len(vec_hits),
                 fused_n=len(fused),
                 vec_available=self.store.has_vector_index)

        if not fused:
            return []

        # 4. Rerank top-fused_k
        if enable_rerank and len(fused) > 1:
            # Build candidates with an index tag so we can always map back
            # even when two chunks happen to share the same rendered text.
            candidates = [{"text": h.render(), "_idx": i}
                          for i, h in enumerate(fused)]
            reranked = self.reranker.rerank(query, candidates, top_k=final_k)
            if not reranked:
                # Reranker filtered everything — return fused order as-is
                log.debug("reranker_returned_empty_falling_back")
                return fused[:final_k]
            reordered: list[SearchHit] = []
            for rc in reranked:
                idx = rc.get("_idx")
                if idx is None or idx >= len(fused):
                    continue
                hit = fused[idx]
                hit.rerank_score = rc.get("rerank_score", 0.0)
                reordered.append(hit)
            return reordered

        return fused[:final_k]

    # ------------------------------------------------------------ reporting

    def explain(self, hit: SearchHit) -> dict:
        """Useful for debugging why a particular chunk ranked where it did."""
        return {
            "chunk_id": hit.chunk_id,
            "paper_id": hit.paper_id,
            "sources": hit.sources,
            "bm25_rank": hit.bm25_rank,
            "bm25_score": round(hit.bm25_score, 4),
            "vec_rank": hit.vec_rank,
            "vec_score": round(hit.vec_score, 4),
            "rrf_score": round(hit.rrf_score, 6),
            "rerank_score": round(hit.rerank_score, 4),
        }
