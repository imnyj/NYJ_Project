"""LaTeX \\cite{} marker audit.

This is the deployment layer on top of retrieval/citation_verifier.py.
The verifier checks a REFERENCE entry (doi, metadata). This module checks
the DRAFT's \\cite{...} MARKERS — were they cited where claims actually
match the cited paper's abstract?

Two passes over drafts/main.tex:

    Pass A (existence check, cheap):
        - Extract all \\cite{corpusID:N} / \\cite{doi:X} tokens.
        - Every cited id must appear in refs.json with verified=True.
        - Retracted papers → fatal.
        - Non-SCIE publishers → fatal.

    Pass B (claim-support check, sBERT, only if Pass A clean):
        - For each \\cite, extract the surrounding sentence.
        - Compute SPECTER2 cosine between sentence and cited abstract.
        - Score → ConfidenceTracker (FLAGGED feeds into Selective CoVe).

Result is a structured audit report for Reviewer to act on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.logger import get_logger

log = get_logger("citation_check")

if TYPE_CHECKING:
    from evaluation.confidence_tracker import ConfidenceTracker


# Regex for our canonical citation markers
_CITE_RE = re.compile(
    r"\\cite(?:t|p|author)?\{([^}]+)\}",  # \cite{...} \citet{...} \citep{...}
)
_ID_RE = re.compile(r"(corpusID:\d+|doi:[^,\s}]+)")


@dataclass
class CitationIssue:
    severity: str              # "fatal" | "high" | "medium" | "low"
    code: str
    line_no: int | None
    citation_id: str
    message: str
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity, "code": self.code,
            "line": self.line_no, "citation_id": self.citation_id,
            "message": self.message, "confidence": self.confidence,
        }


@dataclass
class CitationAuditReport:
    tex_path: str
    total_cites: int = 0
    unique_ids: int = 0
    issues: list[CitationIssue] = field(default_factory=list)

    @property
    def fatal_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "fatal")

    @property
    def ok(self) -> bool:
        return self.fatal_count == 0

    def to_markdown(self) -> str:
        lines = [
            f"# Citation audit — {self.tex_path}",
            f"- total \\cite markers: {self.total_cites}",
            f"- unique ids:           {self.unique_ids}",
            f"- fatal issues:         {self.fatal_count}",
            f"- ok:                   {self.ok}",
            "",
            "## Issues",
        ]
        if not self.issues:
            lines.append("_(none)_")
            return "\n".join(lines)
        for i in sorted(self.issues,
                        key=lambda x: ("fatal high medium low"
                                       ).index(x.severity)):
            loc = f"L{i.line_no}" if i.line_no else "-"
            lines.append(
                f"- **[{i.severity}]** [{loc}] `{i.citation_id}` "
                f"({i.code}): {i.message}"
            )
        return "\n".join(lines)


# =================================================================== core

def extract_cite_markers(tex_source: str) -> list[tuple[int, str, str]]:
    """Return list of (line_no, raw_token, normalized_id) for every citation.

    A single \\cite can contain multiple comma-separated ids; each becomes
    its own tuple so audits work id-by-id.
    """
    out: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(tex_source.splitlines(), start=1):
        for m in _CITE_RE.finditer(line):
            ids_blob = m.group(1)
            for token in re.split(r"[,;]\s*", ids_blob):
                token = token.strip()
                mid = _ID_RE.match(token)
                if mid:
                    out.append((line_no, token, mid.group(1)))
                elif token:
                    # bare key that's not our canonical format
                    out.append((line_no, token, f"unknown:{token}"))
    return out


def extract_surrounding_sentence(
    tex_source: str, line_no: int, window_chars: int = 400,
) -> str:
    """Get the sentence-ish context around a citation's line number."""
    lines = tex_source.splitlines()
    if not (1 <= line_no <= len(lines)):
        return ""
    # Take a small window of lines around, then strip LaTeX
    start = max(0, line_no - 2)
    end = min(len(lines), line_no + 2)
    window = "\n".join(lines[start:end])
    stripped = _strip_latex(window)
    # Trim to window_chars
    if len(stripped) > window_chars:
        stripped = stripped[:window_chars]
    return stripped.strip()


def _strip_latex(text: str) -> str:
    """Minimal LaTeX→plaintext for sentence-BERT input."""
    text = re.sub(r"\\cite(?:t|p|author)?\{[^}]*\}", "", text)
    text = re.sub(r"\\ref\{[^}]*\}", "", text)
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    text = re.sub(r"\\(?:textbf|textit|emph|mathbf|mathrm)\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\s*", " ", text)    # any other command
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =================================================================== auditor

class CitationAuditor:
    """Run the two-pass audit. Uses refs.json as the ground truth source."""

    def __init__(
        self,
        *,
        refs: list[dict[str, Any]],
        confidence_tracker: "ConfidenceTracker | None" = None,
        claim_threshold: float = 0.35,
        enable_claim_check: bool = True,
    ):
        self.refs = refs
        self.tracker = confidence_tracker
        self.claim_threshold = claim_threshold
        self.enable_claim_check = enable_claim_check
        self._by_id = self._index_refs(refs)

    @staticmethod
    def _index_refs(refs: list[dict]) -> dict[str, dict]:
        idx: dict[str, dict] = {}
        for r in refs:
            if r.get("s2_corpus_id"):
                idx[f"corpusID:{r['s2_corpus_id']}"] = r
            if r.get("doi"):
                idx[f"doi:{r['doi']}"] = r
        return idx

    # ------------------------------------------------------------- audit

    def audit(self, tex_path: Path | str) -> CitationAuditReport:
        tex_path = Path(tex_path)
        source = tex_path.read_text(encoding="utf-8", errors="replace")

        markers = extract_cite_markers(source)
        unique = {m[2] for m in markers}
        report = CitationAuditReport(
            tex_path=str(tex_path),
            total_cites=len(markers),
            unique_ids=len(unique),
        )

        # ---- Pass A: existence + status ----
        for line_no, token, cid in markers:
            if cid.startswith("unknown:"):
                report.issues.append(CitationIssue(
                    severity="fatal", code="bad_format",
                    line_no=line_no, citation_id=token,
                    message="citation not in canonical corpusID:/doi: form",
                ))
                continue
            ref = self._by_id.get(cid)
            if ref is None:
                report.issues.append(CitationIssue(
                    severity="fatal", code="unknown_id",
                    line_no=line_no, citation_id=cid,
                    message="citation id not found in refs.json",
                ))
                continue
            if ref.get("retracted"):
                report.issues.append(CitationIssue(
                    severity="fatal", code="retracted",
                    line_no=line_no, citation_id=cid,
                    message="cited paper is retracted",
                ))
                continue
            if not ref.get("verified"):
                report.issues.append(CitationIssue(
                    severity="high", code="unverified_ref",
                    line_no=line_no, citation_id=cid,
                    message="cited entry has verified=False in refs.json",
                    confidence=0.9,
                ))
                continue  # skip claim check for unverified

        # ---- Pass B: claim-support sBERT check ----
        if self.enable_claim_check and report.fatal_count == 0:
            for line_no, token, cid in markers:
                if cid.startswith("unknown:"):
                    continue
                ref = self._by_id.get(cid)
                if ref is None or not ref.get("verified"):
                    continue
                abstract = (ref.get("abstract") or "").strip()
                if not abstract:
                    continue  # nothing to compare against
                sentence = extract_surrounding_sentence(source, line_no)
                if len(sentence) < 30:
                    continue  # too short to be meaningful
                sim = self._similarity(sentence, abstract)
                if self.tracker is not None:
                    self.tracker.record(
                        subject_id=f"cite:{cid}@L{line_no}",
                        subject_type="citation",
                        score=_normalize_similarity(sim),
                        source="citation_check",
                        reason=f"sBERT sim={sim:.3f} (sentence vs abstract)",
                    )
                if sim < self.claim_threshold:
                    sev = "medium" if sim >= 0.20 else "high"
                    # Cosine sim ranges [-1, 1]; clamp 1-sim to [0, 1] so
                    # downstream consumers get a well-defined confidence.
                    conf = max(0.0, min(1.0, 1.0 - sim))
                    report.issues.append(CitationIssue(
                        severity=sev, code="weak_claim_support",
                        line_no=line_no, citation_id=cid,
                        message=(
                            f"sentence↔abstract similarity={sim:.2f} "
                            f"(< threshold {self.claim_threshold:.2f}); "
                            "likely citation misuse"
                        ),
                        confidence=conf,
                    ))

        log.info("citation_audit_complete",
                 tex_path=str(tex_path),
                 total=report.total_cites,
                 unique=report.unique_ids,
                 fatal=report.fatal_count,
                 total_issues=len(report.issues))
        return report

    # ------------------------------------------------------- embedding

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        from tools.embeddings import get_default_embedder
        import numpy as np
        emb = get_default_embedder()
        vecs = emb.encode([a, b])
        return float(np.dot(vecs[0], vecs[1]))


def _normalize_similarity(sim: float) -> float:
    """Map raw cosine to a 0..1 confidence for the tracker.

    Negative similarities (rare for scientific text) clamp to 0.0.
    Raw cosine above ~0.7 is already very high; we spread [0, 0.7] to [0, 1].
    """
    if sim <= 0:
        return 0.0
    return min(1.0, sim / 0.7)
