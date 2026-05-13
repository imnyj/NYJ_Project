"""bge-reranker-v2-m3 cross-encoder wrapper.

Cross-encoders outperform bi-encoders (like SPECTER2) at ranking because
they attend jointly to query and document. The trade-off is latency —
we only rerank the top-K from hybrid search, not the whole corpus.

Pattern:
    1. Hybrid search returns top-50 candidates (cheap bi-encoder + BM25)
    2. Reranker scores each (query, candidate) pair
    3. Keep top-10 for LLM generation

Research basis: Anthropic Contextual Retrieval ablations (2024) —
adding reranker cut retrieval failures an additional 18pp beyond hybrid.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from core.logger import get_logger

log = get_logger("reranker")

try:
    import FlagEmbedding  # noqa: F401
    _FLAG_AVAILABLE = True
except ImportError:
    _FLAG_AVAILABLE = False

if TYPE_CHECKING:
    pass


_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


def is_available() -> bool:
    return _FLAG_AVAILABLE


class Reranker:
    """Lazy-loaded cross-encoder. First call downloads the model (~1GB)."""

    def __init__(self, model_name: str = _DEFAULT_MODEL, use_fp16: bool = True):
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self._model = None  # type: ignore[assignment]

    def _load(self):
        if self._model is not None:
            return self._model
        if not _FLAG_AVAILABLE:
            raise RuntimeError(
                "FlagEmbedding not installed. "
                "Install with: pip install FlagEmbedding"
            )
        from FlagEmbedding import FlagReranker
        log.info("reranker_loading", model=self.model_name)
        self._model = FlagReranker(self.model_name, use_fp16=self.use_fp16)
        return self._model

    def score(
        self,
        query: str,
        candidates: list[str],
        *,
        normalize: bool = True,
    ) -> list[float]:
        """Return relevance scores (higher = more relevant), same order."""
        if not candidates:
            return []
        model = self._load()
        pairs = [[query, c] for c in candidates]
        scores = model.compute_score(pairs, normalize=normalize)
        if isinstance(scores, float):
            return [scores]
        return list(scores)

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        *,
        text_key: str = "text",
        top_k: int | None = None,
    ) -> list[dict]:
        """Return candidates sorted by rerank score, top-k slice.

        Each candidate dict gets a `rerank_score` field added.
        """
        if not candidates:
            return []
        texts = [c.get(text_key, "") for c in candidates]
        scores = self.score(query, texts)
        enriched = [
            {**c, "rerank_score": float(s)}
            for c, s in zip(candidates, scores, strict=False)
        ]
        enriched.sort(key=lambda x: x["rerank_score"], reverse=True)
        return enriched if top_k is None else enriched[:top_k]


# -------------------------------------------------- no-op fallback

class NoOpReranker:
    """Identity reranker — preserves input order. Used when FlagEmbedding
    isn't installed. Safe for smoke tests, not for production quality."""

    def score(self, query: str, candidates: list[str], *, normalize=True) -> list[float]:
        # Return descending pseudo-scores so the original order is preserved
        return [1.0 - i * 1e-6 for i in range(len(candidates))]

    def rerank(self, query: str, candidates: list[dict], *,
               text_key="text", top_k: int | None = None) -> list[dict]:
        enriched = [{**c, "rerank_score": 1.0 - i * 1e-6}
                    for i, c in enumerate(candidates)]
        return enriched if top_k is None else enriched[:top_k]


@lru_cache(maxsize=1)
def get_default_reranker():
    if _FLAG_AVAILABLE:
        return Reranker()
    log.warning("bge_reranker_unavailable_using_noop")
    return NoOpReranker()
