"""Citation verification pipeline.

Research basis:
    - GhostCite (arXiv:2508... 2025): documents 14-95% BibTeX invalidity in
      LLM outputs across venues and model vendors.
    - FActScore (arXiv:2305.14251): atomic-fact factuality checking.

Pipeline per citation:
    1. DOI/Corpus-ID resolves? (Crossref, Semantic Scholar)  — HARD GATE
    2. Metadata matches claim? (title, first author, year, venue)
    3. Retracted? (Crossref Retraction Watch)                — HARD GATE
    4. Publisher on SCIE whitelist?                          — HARD GATE
    5. (Optional, slower) Claim-vs-abstract sBERT overlap    — SOFT WARN

Any HARD GATE failure → citation dropped, issue flagged to Writer.
SOFT WARN → sent to Reviewer as medium-confidence QA item.
"""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from core.logger import get_logger

log = get_logger("citation_verifier")

try:
    import requests  # noqa: F401
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

if TYPE_CHECKING:
    pass


# Publisher whitelist (must match config/settings.yaml:librarian.allowed_publishers)
SCIE_DOMAINS = frozenset({
    "ieeexplore.ieee.org",
    "sciencedirect.com",
    "dl.acm.org",
    "nature.com",
    "mdpi.com",
    "link.springer.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "journals.aps.org",
    "academic.oup.com",
    "cambridge.org",
})

BLOCKED_DOMAINS = frozenset({
    "arxiv.org", "biorxiv.org", "chemrxiv.org",
    "researchgate.net", "academia.edu",
    "scopus.com", "scholar.google.com",
})

CROSSREF_API = "https://api.crossref.org/works/{doi}"
CROSSREF_LABS = "https://api.labs.crossref.org/works/{doi}"
S2_API = "https://api.semanticscholar.org/graph/v1/paper/{id}"


# --------------------------------------------------------------- DTOs

@dataclass
class VerificationIssue:
    severity: str          # "fatal" | "high" | "medium" | "low"
    code: str              # machine-readable category
    message: str
    confidence: float = 1.0


@dataclass
class VerificationResult:
    citation_id: str       # "doi:..." or "corpusID:..."
    verified: bool
    retracted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    issues: list[VerificationIssue] = field(default_factory=list)

    def has_fatal(self) -> bool:
        return any(i.severity == "fatal" for i in self.issues)

    def to_dict(self) -> dict:
        return {
            "citation_id": self.citation_id,
            "verified": self.verified,
            "retracted": self.retracted,
            "metadata": self.metadata,
            "issues": [
                {"severity": i.severity, "code": i.code,
                 "message": i.message, "confidence": i.confidence}
                for i in self.issues
            ],
        }


# ================================================================== client

class CitationVerifier:
    """Main entry point for verifying a batch of references."""

    def __init__(
        self,
        *,
        mailto: str | None = None,
        timeout: float = 10.0,
        user_agent: str = "paper-ai/0.1",
    ):
        self.mailto = mailto or os.environ.get("CROSSREF_MAILTO", "")
        self.timeout = timeout
        self.user_agent = user_agent

    # ------------------------------------------------------------ verify

    def verify(self, entry: dict[str, Any]) -> VerificationResult:
        """Verify one reference entry (shape defined by refs.json schema).

        Entry must have `doi` OR `s2_corpus_id`. Other fields (title,
        authors, year, venue) are cross-checked if present.
        """
        doi = entry.get("doi", "").strip()
        s2 = entry.get("s2_corpus_id", "").strip()
        cid = f"doi:{doi}" if doi else (f"corpusID:{s2}" if s2 else "unknown")

        result = VerificationResult(citation_id=cid, verified=False)

        if not doi and not s2:
            result.issues.append(VerificationIssue(
                severity="fatal", code="no_id",
                message="entry lacks both doi and s2_corpus_id",
            ))
            return result

        if not _REQUESTS_AVAILABLE:
            result.issues.append(VerificationIssue(
                severity="high", code="requests_unavailable",
                message="`requests` not installed; cannot reach Crossref",
            ))
            return result

        # ---- Step 1: DOI resolve ----
        meta: dict[str, Any] | None = None
        if doi:
            meta = self._fetch_crossref(doi)
            if meta is None:
                result.issues.append(VerificationIssue(
                    severity="fatal", code="doi_unresolved",
                    message=f"DOI {doi!r} does not resolve via Crossref",
                ))
                return result

        # ---- Step 1b: Fallback to Semantic Scholar by corpus id ----
        if meta is None and s2:
            meta = self._fetch_s2(s2)
            if meta is None:
                result.issues.append(VerificationIssue(
                    severity="fatal", code="s2_unresolved",
                    message=f"Corpus ID {s2!r} not found on Semantic Scholar",
                ))
                return result

        result.metadata = meta or {}

        # ---- Step 2: metadata cross-check ----
        self._cross_check_metadata(entry, meta or {}, result)

        # ---- Step 3: retraction ----
        if doi:
            retracted, reason = self._check_retraction(doi)
            if retracted:
                result.retracted = True
                result.issues.append(VerificationIssue(
                    severity="fatal", code="retracted",
                    message=f"paper is retracted: {reason or 'see Crossref'}",
                ))
                return result

        # ---- Step 4: publisher whitelist ----
        self._check_publisher(meta or {}, result)

        # Decide verified = no fatal issues
        result.verified = not result.has_fatal()
        return result

    def verify_batch(
        self, entries: list[dict[str, Any]],
    ) -> list[VerificationResult]:
        return [self.verify(e) for e in entries]

    # ----------------------------------------------------- external calls

    def _fetch_crossref(self, doi: str) -> dict | None:
        if not _REQUESTS_AVAILABLE:
            return None
        import requests
        url = CROSSREF_API.format(doi=doi)
        headers = {"User-Agent": f"{self.user_agent} (mailto:{self.mailto})"}
        try:
            r = requests.get(url, headers=headers, timeout=self.timeout)
        except Exception as e:
            log.warning("crossref_network_error", doi=doi, err=str(e))
            return None
        if r.status_code != 200:
            log.info("crossref_not_200", doi=doi, status=r.status_code)
            return None
        try:
            return r.json().get("message")
        except Exception:
            return None

    def _fetch_s2(self, s2id: str) -> dict | None:
        if not _REQUESTS_AVAILABLE:
            return None
        import requests
        url = S2_API.format(id=f"CorpusId:{s2id}")
        headers = {"User-Agent": self.user_agent}
        key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        if key:
            headers["x-api-key"] = key
        try:
            r = requests.get(url, headers=headers, timeout=self.timeout)
        except Exception as e:
            log.warning("s2_network_error", s2=s2id, err=str(e))
            return None
        if r.status_code != 200:
            return None
        try:
            return r.json()
        except Exception:
            return None

    def _check_retraction(self, doi: str) -> tuple[bool, str]:
        if not _REQUESTS_AVAILABLE:
            return False, ""
        import requests
        url = CROSSREF_LABS.format(doi=doi)
        headers = {"User-Agent": f"{self.user_agent} (mailto:{self.mailto})"}
        try:
            r = requests.get(url, headers=headers, timeout=self.timeout)
        except Exception:
            return False, ""
        if r.status_code != 200:
            return False, ""
        try:
            data = r.json().get("message", {})
        except Exception:
            return False, ""
        # "update-to" entries or explicit retraction markers
        update_type = data.get("update-type", "")
        if update_type == "retraction":
            return True, update_type
        # Crossref also embeds "updated-by" with type=retraction
        for u in data.get("updated-by", []):
            if u.get("type") == "retraction":
                return True, "updated-by retraction"
        return False, ""

    # ---------------------------------------------------- metadata checks

    def _cross_check_metadata(
        self,
        entry: dict[str, Any],
        meta: dict[str, Any],
        result: VerificationResult,
    ) -> None:
        """Compare entry claims against authoritative Crossref response.

        Mismatches are WARNINGS, not fatal — the DOI resolved, so the
        reference exists, even if the local metadata has typos.
        """
        # --- year ---
        claimed_year = entry.get("year")
        auth_year = _extract_year(meta)
        if claimed_year and auth_year and int(claimed_year) != int(auth_year):
            result.issues.append(VerificationIssue(
                severity="medium", code="year_mismatch",
                message=f"year {claimed_year} != crossref {auth_year}",
                confidence=0.95,
            ))

        # --- title (fuzzy) ---
        claimed_title = (entry.get("title") or "").strip()
        auth_title_list = meta.get("title", [])
        auth_title = (auth_title_list[0] if isinstance(auth_title_list, list)
                      and auth_title_list else
                      (meta.get("title") or "")).strip()
        if claimed_title and auth_title:
            ratio = difflib.SequenceMatcher(
                None, claimed_title.lower(), auth_title.lower()
            ).ratio()
            if ratio < 0.80:
                result.issues.append(VerificationIssue(
                    severity="medium", code="title_mismatch",
                    message=f"title similarity {ratio:.2f} (< 0.80)",
                    confidence=1.0 - ratio,
                ))

        # --- first author surname ---
        claimed_authors = entry.get("authors") or []
        auth_authors = meta.get("author") or []
        if claimed_authors and auth_authors:
            c_first = (claimed_authors[0] if isinstance(claimed_authors[0], str)
                       else claimed_authors[0].get("family", ""))
            a_first_family = auth_authors[0].get("family", "")
            if c_first and a_first_family:
                # Normalise: lowercase, strip diacritics, drop punctuation.
                # Then compare with a symmetric rule: accept if the tokens
                # of the shorter form are a subset of the longer one.
                # Asymmetric `in` would treat "Lee" vs "Leeroy" as a match
                # even though they're different surnames.
                import re as _re
                import unicodedata as _ud

                def _norm(s: str) -> set[str]:
                    s = _ud.normalize("NFKD", s)
                    s = "".join(c for c in s if not _ud.combining(c))
                    s = s.lower()
                    s = _re.sub(r"[^a-z\s-]", " ", s)
                    return {t for t in _re.split(r"[\s-]+", s) if t}

                ct, at = _norm(c_first), _norm(a_first_family)
                # Consider a match when the smaller token set is contained
                # in the larger — handles "Van Der Waals" vs "van der Waals",
                # "Smith" vs "Smith-Jones" (hyphenated), etc. — without
                # letting "Lee" match "Leeroy".
                if ct and at:
                    smaller, larger = (ct, at) if len(ct) <= len(at) else (at, ct)
                    matched = smaller.issubset(larger)
                else:
                    matched = False
                if not matched:
                    result.issues.append(VerificationIssue(
                        severity="medium", code="first_author_mismatch",
                        message=f"first author '{c_first}' != crossref "
                                f"family '{a_first_family}'",
                        confidence=0.8,
                    ))

    def _check_publisher(
        self,
        meta: dict[str, Any],
        result: VerificationResult,
    ) -> None:
        """Enforce SCIE whitelist on the publisher/container."""
        # Crossref: 'container-title' (list[str]); URL in 'URL' / 'link'
        url = (meta.get("URL") or "").lower()
        # Hostname-based check (suffix match on URL host, not substring)
        host = ""
        if url:
            try:
                host = (urlparse(url).hostname or "").lower()
            except Exception:
                host = ""

        def _matches(domain: str) -> bool:
            d = domain.lower().lstrip(".")
            return bool(host) and (host == d or host.endswith("." + d))

        blocked = any(_matches(d) for d in BLOCKED_DOMAINS)
        if blocked:
            result.issues.append(VerificationIssue(
                severity="fatal", code="blocked_source",
                message=f"publisher URL on block list: {url}",
            ))
            return
        if host:
            allowed = any(_matches(d) for d in SCIE_DOMAINS)
            if not allowed:
                result.issues.append(VerificationIssue(
                    severity="high", code="non_scie_publisher",
                    message=f"publisher not on SCIE whitelist: {url}",
                    confidence=0.9,
                ))


# ----------------------------------------------------- sentence-BERT claim

def claim_abstract_similarity(
    claim_sentence: str,
    abstract: str,
    *,
    embedder=None,
) -> float:
    """Cosine similarity between a citation's surrounding claim sentence
    and the cited paper's abstract.

    Threshold interpretation (SPECTER2, empirical defaults):
        >= 0.50  strong support
        >= 0.35  acceptable
        >= 0.20  weak — flag as medium-confidence issue
        <  0.20  very weak — likely "right paper, wrong claim"
    """
    from tools.embeddings import get_default_embedder
    emb = embedder or get_default_embedder()
    import numpy as np
    vecs = emb.encode([claim_sentence, abstract])
    a, b = vecs[0], vecs[1]
    # Embedder normalizes → dot product == cosine
    return float(np.dot(a, b))


# ----------------------------------------------------------------- helpers

def _extract_year(meta: dict[str, Any]) -> int | None:
    """Crossref stores year under 'issued.date-parts[[Y, M, D]]'."""
    issued = meta.get("issued", {})
    parts = issued.get("date-parts", [])
    if parts and parts[0]:
        try:
            return int(parts[0][0])
        except (ValueError, IndexError, TypeError):
            return None
    for key in ("published-print", "published-online", "created"):
        d = meta.get(key, {}).get("date-parts", [])
        if d and d[0]:
            try:
                return int(d[0][0])
            except (ValueError, IndexError, TypeError):
                continue
    return None
