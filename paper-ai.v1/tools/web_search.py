"""SCIE-whitelisted literature search.

Librarian uses this to find candidate papers. We deliberately do NOT use
generic web search (Google/Bing) because:
    - They return arXiv, ResearchGate, Scopus — all on our blocklist.
    - We cannot programmatically guarantee publisher whitelisting.

Instead we query the Crossref and Semantic Scholar APIs directly, then
filter results by publisher domain against the SCIE whitelist. This gives
us a deterministic, auditable source of truth.

Both APIs are free; Crossref requires a `mailto` (politeness), Semantic
Scholar is rate-limited without an API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from core.logger import get_logger
from retrieval.citation_verifier import BLOCKED_DOMAINS, SCIE_DOMAINS

log = get_logger("web_search")

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


CROSSREF_SEARCH = "https://api.crossref.org/works"
S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"


@dataclass
class SearchResult:
    title: str
    doi: str | None = None
    s2_corpus_id: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    url: str = ""
    source_api: str = ""      # "crossref" | "s2"
    on_whitelist: bool = False

    def to_ref_entry(self) -> dict[str, Any]:
        """Return in the shape of refs.json entries (see core/artifacts.py)."""
        return {
            "doi": self.doi or "",
            "s2_corpus_id": self.s2_corpus_id or "",
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "abstract": self.abstract,
            "verified": False,       # pending citation_verifier
        }


# ================================================================== client

class SCIEWebSearch:
    """Publisher-gated literature search."""

    def __init__(
        self,
        *,
        mailto: str | None = None,
        timeout: float = 15.0,
        user_agent: str = "paper-ai/0.1",
    ):
        self.mailto = mailto or os.environ.get("CROSSREF_MAILTO", "")
        self.timeout = timeout
        self.user_agent = user_agent

    # ---------------------------------------------------------- Crossref

    def search_crossref(
        self,
        query: str,
        *,
        rows: int = 20,
        from_year: int | None = None,
    ) -> list[SearchResult]:
        if not _REQUESTS_AVAILABLE:
            log.warning("crossref_requests_unavailable")
            return []
        params = {
            "query": query,
            "rows": rows,
            "select": "DOI,title,author,issued,container-title,abstract,URL",
        }
        if from_year:
            params["filter"] = f"from-pub-date:{from_year}"
        headers = {"User-Agent": f"{self.user_agent} (mailto:{self.mailto})"}
        try:
            r = requests.get(CROSSREF_SEARCH, params=params,
                             headers=headers, timeout=self.timeout)
        except Exception as e:
            log.warning("crossref_network_error", err=str(e))
            return []
        if r.status_code != 200:
            log.warning("crossref_status", status=r.status_code)
            return []

        try:
            items = r.json().get("message", {}).get("items", [])
        except Exception:
            return []

        results = []
        for item in items:
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""
            if not title:
                continue
            authors = []
            for a in item.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                authors.append(f"{given} {family}".strip())
            year = _extract_year_crossref(item)
            venue_list = item.get("container-title", [])
            venue = venue_list[0] if venue_list else ""
            url = item.get("URL", "")

            sr = SearchResult(
                title=title,
                doi=item.get("DOI"),
                authors=authors,
                year=year,
                venue=venue,
                abstract=_clean_abstract(item.get("abstract", "")),
                url=url,
                source_api="crossref",
            )
            sr.on_whitelist = _is_whitelisted(url)
            results.append(sr)
        return results

    # ------------------------------------------------- Semantic Scholar

    def search_semantic_scholar(
        self,
        query: str,
        *,
        limit: int = 20,
        from_year: int | None = None,
    ) -> list[SearchResult]:
        if not _REQUESTS_AVAILABLE:
            return []
        fields = ("title,authors,year,venue,abstract,externalIds,openAccessPdf,"
                  "publicationVenue,corpusId")
        params: dict = {"query": query, "limit": limit, "fields": fields}
        if from_year:
            params["year"] = f"{from_year}-"
        headers = {"User-Agent": self.user_agent}
        # Prefer encrypted-vault value over plain env so a workstation
        # neighbour who poked SEMANTIC_SCHOLAR_API_KEY into their own
        # shell can't override the real one we have in memory.
        try:
            from core import secret_env
            key = secret_env.get("SEMANTIC_SCHOLAR_API_KEY")
        except Exception:
            key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        if key:
            headers["x-api-key"] = key
        try:
            r = requests.get(S2_SEARCH, params=params,
                             headers=headers, timeout=self.timeout)
        except Exception as e:
            log.warning("s2_network_error", err=str(e))
            return []
        if r.status_code != 200:
            log.warning("s2_status", status=r.status_code)
            return []

        try:
            items = r.json().get("data", [])
        except Exception:
            return []

        results = []
        for item in items:
            title = item.get("title", "")
            if not title:
                continue
            ext_ids = item.get("externalIds") or {}
            doi = ext_ids.get("DOI", "")
            corpus_id = str(item.get("corpusId", "") or ext_ids.get("CorpusId", ""))

            authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
            pub_venue = item.get("publicationVenue") or {}
            venue = (pub_venue.get("name") or item.get("venue") or "").strip()

            # Source URL for whitelist check: DOI → doi.org, else open-access PDF
            url = ""
            oap = item.get("openAccessPdf") or {}
            if oap.get("url"):
                url = oap["url"]
            elif doi:
                url = f"https://doi.org/{doi}"

            sr = SearchResult(
                title=title,
                doi=doi or None,
                s2_corpus_id=corpus_id or None,
                authors=authors,
                year=item.get("year"),
                venue=venue,
                abstract=(item.get("abstract") or "").strip(),
                url=url,
                source_api="s2",
            )
            sr.on_whitelist = _is_whitelisted(url)
            results.append(sr)
        return results

    # --------------------------------------------------------- combined

    def search(
        self,
        query: str,
        *,
        rows: int = 20,
        from_year: int | None = None,
        whitelist_only: bool = True,
    ) -> list[SearchResult]:
        """Query both APIs, merge by DOI, return whitelist-filtered results."""
        cr = self.search_crossref(query, rows=rows, from_year=from_year)
        s2 = self.search_semantic_scholar(query, limit=rows, from_year=from_year)

        merged: dict[str, SearchResult] = {}
        for lst in (cr, s2):
            for r in lst:
                key = r.doi or r.s2_corpus_id or r.title.lower()[:80]
                if key not in merged:
                    merged[key] = r
                else:
                    # Prefer whichever has the abstract / DOI
                    existing = merged[key]
                    if not existing.abstract and r.abstract:
                        existing.abstract = r.abstract
                    if not existing.doi and r.doi:
                        existing.doi = r.doi
                    if not existing.s2_corpus_id and r.s2_corpus_id:
                        existing.s2_corpus_id = r.s2_corpus_id

        all_hits = list(merged.values())
        log.info("search_combined",
                 query=query[:80],
                 crossref_n=len(cr),
                 s2_n=len(s2),
                 merged_n=len(all_hits))

        if whitelist_only:
            filtered = [r for r in all_hits if r.on_whitelist]
            log.info("whitelist_filter",
                     kept=len(filtered),
                     dropped=len(all_hits) - len(filtered))
            return filtered
        return all_hits


# ----------------------------------------------------------------- helpers

def _is_whitelisted(url: str) -> bool:
    """Domain-based whitelist check.

    Matches hostname suffix, so `ieeexplore.ieee.org` matches the SCIE entry
    `ieee.org` but a spoofed `fake.ieee.org.attacker.com` does NOT (its
    hostname ends in `attacker.com`, not `ieee.org`).
    """
    if not url:
        return False
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    host = host.lower()
    if not host:
        return False
    # host must equal or END WITH ".{domain}" for each candidate
    def _matches(domain: str) -> bool:
        d = domain.lower().lstrip(".")
        return host == d or host.endswith("." + d)
    if any(_matches(b) for b in BLOCKED_DOMAINS):
        return False
    return any(_matches(d) for d in SCIE_DOMAINS)


def _extract_year_crossref(item: dict) -> int | None:
    issued = item.get("issued", {})
    parts = issued.get("date-parts", [])
    if parts and parts[0]:
        try:
            return int(parts[0][0])
        except (ValueError, IndexError, TypeError):
            return None
    return None


def _clean_abstract(raw: str) -> str:
    """Crossref abstracts often include JATS XML tags; strip them."""
    import re
    if not raw:
        return ""
    return re.sub(r"</?\w[^>]*>", " ", raw).strip()
