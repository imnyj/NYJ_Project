"""
웹 도구. DuckDuckGo 검색 + 페이지 fetch.

특징:
- 호출 한도 (config의 max_calls_per_session)
- 도메인 차단 리스트
- 페이지 크기 제한
- HTML → markdown 추출 (readability/markdownify 우선, 없으면 텍스트만)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# 의존성 — 모두 옵션. 없으면 도구 자체가 비활성됨.
try:
    from ddgs import DDGS
    _HAS_DDG = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        _HAS_DDG = True
    except ImportError:
        _HAS_DDG = False

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

try:
    from markdownify import markdownify as _md
    _HAS_MD = True
except ImportError:
    _HAS_MD = False


MAX_FETCH_BYTES = 500_000
DEFAULT_BLOCKED = {"facebook.com", "instagram.com", "twitter.com", "x.com"}


class WebState:
    """세션 단위 호출 카운터."""

    def __init__(self, max_calls: int = 30, blocked_domains: set[str] | None = None):
        self.max_calls = max_calls
        self.calls = 0
        self.blocked = blocked_domains or DEFAULT_BLOCKED

    def check(self) -> str | None:
        if self.calls >= self.max_calls:
            return f"RATE_LIMITED: 세션 한도 {self.max_calls}회 도달"
        return None

    def is_blocked(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        host = host.lstrip("www.")
        return any(host.endswith(b) for b in self.blocked)


def web_search(args: dict, state: WebState) -> str:
    """
    웹 검색 (DuckDuckGo). args={'query': '...', 'k': 5}
    결과: 제목, 요약, URL 목록 (markdown).
    """
    if not _HAS_DDG:
        return "UNAVAILABLE: duckduckgo_search 미설치"
    if (err := state.check()):
        return err

    query = args.get("query", "").strip()
    if not query:
        return "EMPTY_QUERY"
    k = min(args.get("k", 5), 10)

    state.calls += 1
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=k))
    except Exception as e:
        return f"SEARCH_ERROR: {type(e).__name__}: {e}"

    if not results:
        return f"NO_RESULTS: '{query}'"

    out = [f"# 검색: {query}", ""]
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        body = r.get("body", "")[:300]
        url = r.get("href") or r.get("url", "")
        out.append(f"## {i}. {title}\n{body}\nURL: {url}\n")
    return "\n".join(out)


def web_fetch(args: dict, state: WebState) -> str:
    """
    URL의 본문을 가져와 마크다운으로 변환. args={'url': '...', 'max_bytes': 200000}
    """
    if not _HAS_HTTPX:
        return "UNAVAILABLE: httpx 미설치"
    if (err := state.check()):
        return err

    url = args.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return f"INVALID_URL: {url}"
    if state.is_blocked(url):
        return f"BLOCKED_DOMAIN: {urlparse(url).netloc}"

    max_b = min(args.get("max_bytes", MAX_FETCH_BYTES), MAX_FETCH_BYTES)
    state.calls += 1

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=20.0,
            headers={"User-Agent": "Mozilla/5.0 (qwen-loop)"},
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text[:max_b * 2]  # 변환 손실 감안 2x
    except Exception as e:
        return f"FETCH_ERROR: {type(e).__name__}: {e}"

    if _HAS_MD:
        try:
            md = _md(html, heading_style="ATX", strip=["script", "style"])
            md = re.sub(r"\n{3,}", "\n\n", md).strip()
        except Exception:
            md = _strip_html(html)
    else:
        md = _strip_html(html)

    if len(md) > max_b:
        md = md[:max_b] + "\n\n[... 잘림]"

    return f"# {url}\n\n{md}"


def _strip_html(html: str) -> str:
    text = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ----------------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------------

WEB_TOOL_NAMES = {"web_search", "web_fetch"}  # 모두 READ-class


def make_web_tools(state: WebState) -> dict:
    if not _HAS_DDG and not _HAS_HTTPX:
        return {}
    out = {}
    if _HAS_DDG:
        out["web_search"] = lambda a: web_search(a, state)
    if _HAS_HTTPX:
        out["web_fetch"] = lambda a: web_fetch(a, state)
    return out


TOOL_DOCS = {
    "web_search": "DuckDuckGo 검색. args: {query: str, k?: int}",
    "web_fetch":  "URL 본문을 마크다운으로 가져옴. args: {url: str, max_bytes?: int}",
}
