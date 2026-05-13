"""Contextual Retrieval (Anthropic, September 2024).

Source: https://www.anthropic.com/news/contextual-retrieval

Standard RAG chunking loses context: a chunk might say "the proposed method
achieves 85% accuracy" without telling the retriever WHICH paper, WHICH
dataset, WHICH method. Contextual Retrieval fixes this by prepending a
50-100 token LLM-generated "situating context" to each chunk BEFORE it is
embedded and BM25-indexed.

Anthropic's ablations (on a 350M-token corpus):
    - baseline retrieval failure rate: 5.7%
    - contextual embeddings only:      3.7%   (-35%)
    - contextual BM25 only:            2.9%   (-49%)
    - contextual embeddings + BM25 + reranker: 1.9%   (-67%)

Cost mitigation (critical): the situating-context generation reads the full
paper into the prompt ONCE and generates contexts for each chunk in that
cached prefix. With Haiku + prompt caching, this adds ~1¢ per paper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.logger import get_logger
from memory.corpus_store import ChunkRecord

log = get_logger("contextual_retrieval")

if TYPE_CHECKING:
    from tools.anthropic_client import AnthropicClient


# Recommended by Anthropic: 400-800 token chunks with ~50-100 token context.
# We default to ~600 chars ≈ 150-180 tokens per raw chunk; the context
# prefix pushes the combined piece to the 200-280 token range — a sweet
# spot for both BM25 granularity and SPECTER2's 512-token window.
DEFAULT_CHUNK_CHARS = 600
DEFAULT_OVERLAP_CHARS = 80


CONTEXT_PROMPT = """<full_paper>
{paper}
</full_paper>

Here is a chunk we want to situate within the whole paper:
<chunk>
{chunk}
</chunk>

Give a SHORT context (50-100 words, 1-2 sentences) that situates this chunk
within the paper, so a retrieval engine can understand what section, topic,
and argument it belongs to. Output ONLY the context sentence(s), no preamble.
"""


@dataclass
class ChunkingConfig:
    chunk_chars: int = DEFAULT_CHUNK_CHARS
    overlap_chars: int = DEFAULT_OVERLAP_CHARS
    enable_contextualization: bool = True
    context_model_hint: str = "classify"   # routes to Haiku via routing.yaml


# ====================================================================== split

def split_into_raw_chunks(
    text: str,
    *,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[str]:
    """Simple paragraph-aware chunker.

    Prefers to break on paragraph/sentence boundaries to avoid cutting
    equations or code blocks mid-token.
    """
    if not text:
        return []
    # First pass: split on blank lines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        if len(buf) + len(p) + 2 <= chunk_chars:
            buf = f"{buf}\n\n{p}" if buf else p
            continue
        if buf:
            chunks.append(buf)
        # Long paragraph: hard-split with overlap
        if len(p) > chunk_chars:
            start = 0
            while start < len(p):
                end = min(start + chunk_chars, len(p))
                chunks.append(p[start:end])
                if end == len(p):
                    break
                start = max(0, end - overlap_chars)
            buf = ""
        else:
            buf = p
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


# =================================================== contextualize via Haiku

class ContextualChunker:
    """Generate situating-context for each chunk of a paper."""

    def __init__(
        self,
        client: "AnthropicClient",
        config: ChunkingConfig | None = None,
    ):
        self.client = client
        self.config = config or ChunkingConfig()

    def chunk_paper(
        self,
        *,
        paper_id: int,
        full_text: str,
        title: str = "",
    ) -> list[ChunkRecord]:
        """Return ChunkRecords with context_prefix filled in."""
        raw_chunks = split_into_raw_chunks(
            full_text,
            chunk_chars=self.config.chunk_chars,
            overlap_chars=self.config.overlap_chars,
        )
        if not raw_chunks:
            log.warning("no_chunks_produced", paper_id=paper_id,
                        text_len=len(full_text))
            return []

        log.info("chunking_paper",
                 paper_id=paper_id, n_chunks=len(raw_chunks),
                 contextualize=self.config.enable_contextualization)

        records: list[ChunkRecord] = []
        for i, raw in enumerate(raw_chunks):
            ctx = ""
            if self.config.enable_contextualization:
                try:
                    ctx = self._generate_context(full_text, raw, title)
                except Exception as e:
                    log.warning("contextualize_failed",
                                paper_id=paper_id, chunk_idx=i, err=str(e))
                    ctx = ""
            records.append(ChunkRecord(
                paper_id=paper_id,
                chunk_idx=i,
                text=raw,
                context_prefix=ctx,
                tokens=_approx_tokens(raw) + _approx_tokens(ctx),
            ))
        return records

    def _generate_context(self, paper: str, chunk: str, title: str) -> str:
        """One Haiku call per chunk, sharing the cached paper prefix."""
        # The full paper goes into `shared_artifacts` so it rides the
        # Layer-3 prompt cache across all chunks of the same paper.
        prompt = CONTEXT_PROMPT.format(paper="<<see shared context>>",
                                       chunk=chunk)
        shared = f"--- paper: {title or '(untitled)'} ---\n{paper}\n"
        result = self.client.call(
            agent="librarian",
            user_turn=prompt,
            task_type="summarize_short",   # → Haiku, max 512 tokens
            shared_artifacts=shared,
        )
        text = (result.get("text") or "").strip()
        # Keep only the first paragraph; strip quotes/prefixes
        if "\n\n" in text:
            text = text.split("\n\n", 1)[0]
        return text.strip().strip('"').strip("'")


def _approx_tokens(text: str) -> int:
    """Rough token count without tiktoken dep. ~3.5 chars/token."""
    return int(len(text) / 3.5)
