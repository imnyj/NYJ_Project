"""SPECTER2 scientific-document embedding adapter.

SPECTER2 (Singh et al., EMNLP 2023) is the adapter-trained successor to
SPECTER, covering 9 tasks × 23 scientific fields. It beats general-purpose
embeddings on scientific retrieval by ~15-25 points on most benchmarks.

This module provides a thin wrapper so the rest of paper-ai doesn't need
to know which embedder is in use. In Phase 3 we use SPECTER2 for:
    - Indexing corpus chunks (retrieval/hybrid_search.py)
    - Claim-vs-abstract similarity (evaluation/citation_check.py)

Graceful degradation: if sentence-transformers isn't installed, the module
still imports, and `is_available()` returns False. Callers decide whether
to fall back to BM25-only mode or raise.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import TYPE_CHECKING

from core.logger import get_logger

log = get_logger("embeddings")

# Check optional heavy deps without importing (keeps startup fast)
try:
    import sentence_transformers  # noqa: F401
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

if TYPE_CHECKING:
    import numpy as np


_DEFAULT_MODEL = "allenai/specter2_base"
_DEFAULT_DIM = 768  # SPECTER2 base


def is_available() -> bool:
    return _ST_AVAILABLE


def embedding_dim(model_name: str = _DEFAULT_MODEL) -> int:
    """Return expected vector dimension without loading the model."""
    if "specter2" in model_name:
        return _DEFAULT_DIM
    # Sensible defaults for common alternatives
    if "MiniLM" in model_name:
        return 384
    if "bge-base" in model_name:
        return 768
    return _DEFAULT_DIM


class Embedder:
    """Lazy-loaded SPECTER2 wrapper. Instantiation is cheap; first encode
    triggers model download (~500MB on HuggingFace)."""

    def __init__(self, model_name: str = _DEFAULT_MODEL, device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None  # type: ignore[assignment]

    def _load(self):
        if self._model is not None:
            return self._model
        if not _ST_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        from sentence_transformers import SentenceTransformer
        log.info("embedder_loading", model=self.model_name, device=self.device)
        self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def encode(self, texts: list[str], *, batch_size: int = 16) -> "np.ndarray":
        """Return an (N, D) float32 ndarray."""
        model = self._load()
        import numpy as np  # lazy
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,   # enables cosine via dot-product
        )
        return vectors.astype(np.float32)

    def encode_one(self, text: str) -> "np.ndarray":
        return self.encode([text])[0]

    @property
    def dim(self) -> int:
        return embedding_dim(self.model_name)


# ----------------------------------------------------- deterministic fallback

class HashEmbedder:
    """Tiny deterministic embedder used when SPECTER2 unavailable.

    NOT for production retrieval quality — lets the pipeline boot and run
    smoke tests on a minimal WSL2 install before the user pulls SPECTER2.
    """

    def __init__(self, dim: int = 128):
        self._dim = dim

    def encode(self, texts: list[str]) -> "np.ndarray":
        import numpy as np
        vecs = []
        for t in texts:
            # sha512 → 64 bytes → extend/truncate to dim
            h = hashlib.sha512(t.encode("utf-8")).digest()
            raw = (h * ((self._dim // len(h)) + 1))[: self._dim]
            v = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            v = (v - 128.0) / 128.0
            # L2 normalize
            n = np.linalg.norm(v)
            if n > 0:
                v = v / n
            vecs.append(v)
        return np.stack(vecs).astype(np.float32)

    def encode_one(self, text: str) -> "np.ndarray":
        return self.encode([text])[0]

    @property
    def dim(self) -> int:
        return self._dim


@lru_cache(maxsize=2)
def get_default_embedder() -> "Embedder | HashEmbedder":
    """Cached process-wide embedder."""
    if _ST_AVAILABLE:
        return Embedder()
    log.warning("specter2_unavailable_using_hash_fallback")
    return HashEmbedder()
