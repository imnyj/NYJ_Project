"""PaperQA2 adapter.

PaperQA2 (FutureHouse, arXiv:2409.13740) is the SOTA agent for scientific
literature review. It achieves superhuman performance on LitQA2 and
+12.4% over the next-best on RAG-QA Arena science.

Rather than reimplement its Re-ranking and Contextual Summarization (RCS)
loop, we wrap the official library. Librarian delegates to this when its
task is a multi-paper literature Q&A rather than a structured search.

Graceful degradation: if `paper-qa` isn't installed (Phase 3 optional dep),
methods raise with a clear install hint; callers can fall back to our
native HybridSearch instead.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.logger import get_logger

log = get_logger("paperqa_adapter")

try:
    import paperqa  # noqa: F401
    _PQA_AVAILABLE = True
except ImportError:
    _PQA_AVAILABLE = False

if TYPE_CHECKING:
    pass


def is_available() -> bool:
    return _PQA_AVAILABLE


class PaperQAAdapter:
    """Thin wrapper around paperqa.Docs / paperqa.Settings."""

    def __init__(
        self,
        *,
        paper_dir: str | Path | None = None,
        llm_model: str = "claude-sonnet-4-6",
        summary_model: str = "claude-haiku-4-5-20251001",
    ):
        if not _PQA_AVAILABLE:
            raise RuntimeError(
                "paper-qa not installed. "
                "Install with: pip install paper-qa"
            )
        import paperqa
        self._pqa = paperqa
        if paper_dir is None:
            from core.paths import get_paths
            paper_dir = get_paths().pdfs
        self.paper_dir = Path(paper_dir)
        self.paper_dir.mkdir(parents=True, exist_ok=True)

        # PaperQA2 uses LiteLLM; Anthropic models are first-class
        self.settings = paperqa.Settings(
            llm=f"anthropic/{llm_model}",
            summary_llm=f"anthropic/{summary_model}",
            paper_directory=str(self.paper_dir),
            # ANTHROPIC_API_KEY is read from env automatically
        )
        self._docs = paperqa.Docs()

    # ------------------------------------------------------------- ingest

    def add_pdf(self, pdf_path: str | Path) -> None:
        """Index a local PDF."""
        self._docs.add(str(pdf_path), settings=self.settings)
        log.info("paperqa_add_pdf", path=str(pdf_path))

    def add_directory(self, dir_path: str | Path | None = None) -> int:
        """Bulk-index all PDFs in a directory."""
        target = Path(dir_path) if dir_path else self.paper_dir
        count = 0
        for p in target.glob("*.pdf"):
            try:
                self.add_pdf(p)
                count += 1
            except Exception as e:
                log.warning("paperqa_add_failed", path=str(p), err=str(e))
        return count

    # -------------------------------------------------------------- query

    def query(self, question: str, *, max_sources: int = 8) -> dict[str, Any]:
        """Ask a question; returns answer with inline citations."""
        answer = self._docs.query(
            question,
            settings=self.settings,
        )
        sources: list[dict[str, Any]] = []
        for c in getattr(answer, "contexts", [])[:max_sources]:
            text_attr = getattr(c, "text", None)
            # PaperQA2's Context.text may be a Text object with .name, a dict,
            # or a raw string depending on version. Handle all three.
            if hasattr(text_attr, "name"):
                key = getattr(text_attr, "name", "")
            elif isinstance(text_attr, dict):
                key = text_attr.get("name", "")
            else:
                key = ""
            sources.append({
                "key": key,
                "content": getattr(c, "context", ""),
                "score": getattr(c, "score", None),
            })
        return {
            "question": question,
            "answer": getattr(answer, "answer", str(answer)),
            "context": getattr(answer, "context", ""),
            "sources": sources,
            "cost": getattr(answer, "cost", 0.0),
        }

    # ----------------------------------------------------- convenience

    def literature_review(
        self, topic: str, *, n_papers: int = 10,
    ) -> dict[str, Any]:
        """Synthesis query with forced breadth."""
        prompt = (
            f"Provide a structured literature review on: {topic}. "
            f"Group by approach. For each paper cite clearly. "
            f"Use at least {n_papers} distinct sources if available."
        )
        return self.query(prompt, max_sources=n_papers * 2)
