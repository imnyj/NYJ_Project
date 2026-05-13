# tools/semantic_scholar_search.py
"""Semantic Scholar API 검색 도구 — Librarian 에이전트 전용."""
from smolagents import Tool


class SemanticScholarSearchTool(Tool):
    name = "semantic_scholar_search"
    description = (
        "Search academic papers using Semantic Scholar API. "
        "Returns title, authors, year, citation count, DOI, and abstract. "
        "Better than web search for finding peer-reviewed papers with citation data."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "Search query (e.g. 'V2X precaching reinforcement learning')",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results (default: 10)",
            "nullable": True,
        },
        "year_range": {
            "type": "string",
            "description": "Year filter, e.g. '2020-2025' or '2023-' (optional)",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        query: str,
        max_results: int = 10,
        year_range: str | None = None,
    ) -> str:
        import os
        import urllib.request
        import urllib.parse
        import json as _json
        import time

        base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        fields = "title,authors,year,citationCount,externalIds,abstract,venue,publicationDate"

        params = {
            "query": query,
            "limit": min(max_results, 20),
            "fields": fields,
        }
        if year_range:
            params["year"] = year_range

        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        # API 키 조회 — vault 먼저, 그 다음 환경변수.
        # Vault에 보관된 키는 secret_env가 unlock된 상태에서만 보임. 일반
        # 평문 .env에 둔 경우엔 os.getenv로 자동 fallback.
        s2_api_key = ""
        try:
            from core import secret_env
            s2_api_key = secret_env.get("SEMANTIC_SCHOLAR_API_KEY") or ""
        except Exception:
            pass
        if not s2_api_key:
            s2_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

        headers = {"User-Agent": "PaperPipeline/1.0"}
        if s2_api_key:
            headers["x-api-key"] = s2_api_key

        # Backoff 스케줄을 키 유무에 따라 다르게 잡습니다.
        #
        # 키 없음 → 무인증 공유 풀 사용. 풀이 비는 시간대를 잡으려면 길게 기다림.
        #   5s → 10s → 20s → 40s (누적 ~75s). 폭주가 끝날 때까지 인내.
        #
        # 키 있음 → 본인 전용 1 RPS 차선. 429는 사용자 본인이 너무 빨리 부른 경우.
        #   1s → 2s → 4s → 8s (누적 ~15s). 짧게 여러 번이면 충분.
        #
        # 두 경우 모두 4회까지 재시도. Retry-After 헤더가 오면 서버 지시 우선.
        max_attempts = 4
        if s2_api_key:
            backoff_s = 1.0
            mode_note = "API key in use (private 1 RPS lane)"
        else:
            backoff_s = 5.0
            mode_note = "unauthenticated shared pool"

        last_err: str | None = None
        data = None

        for attempt in range(1, max_attempts + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = _json.loads(resp.read().decode("utf-8"))
                break  # 성공
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # 서버가 Retry-After 헤더로 권장 대기시간 알려주면 그것 우선
                    retry_after_hdr = e.headers.get("Retry-After") if e.headers else None
                    try:
                        wait_s = float(retry_after_hdr) if retry_after_hdr else backoff_s
                    except (TypeError, ValueError):
                        wait_s = backoff_s
                    last_err = (
                        f"HTTP 429 ({mode_note}), attempt {attempt}/{max_attempts}, "
                        f"waiting {wait_s:.0f}s"
                    )
                    if attempt < max_attempts:
                        time.sleep(wait_s)
                        backoff_s *= 2  # 다음 시도는 두 배 — 키 유무 무관
                        continue
                    # 마지막 시도도 실패. 안내 메시지는 키 유무에 따라 달리.
                    if s2_api_key:
                        return (
                            f"[Semantic Scholar rate limit — 모든 재시도 실패]\n"
                            f"API 키는 사용 중인데도 429가 반복됩니다.\n"
                            f"원인: 본인 전용 차선(1 RPS)을 초과해 호출 중일 가능성.\n"
                            f"해결책: 검색 호출 간격을 늘리거나, Semantic Scholar에 "
                            f"한도 상향 신청 (feedback@semanticscholar.org)."
                        )
                    return (
                        f"[Semantic Scholar rate limit — 모든 재시도 실패]\n"
                        f"무인증 공유 풀에 트래픽 폭주 상태일 수 있습니다.\n"
                        f"해결책 (택1):\n"
                        f"  1. 5~10분 후 재시도\n"
                        f"  2. https://www.semanticscholar.org/product/api 에서 "
                        f"API 키 발급 후 .env에 SEMANTIC_SCHOLAR_API_KEY=... 추가\n"
                        f"     → 전용 1 RPS rate limit 확보, 공유 풀 영향 없음"
                    )
                # 429 외 HTTP 에러 — 재시도 의미 없음
                return f"[Semantic Scholar 검색 실패] HTTP {e.code}: {e.reason}"
            except Exception as e:
                last_err = str(e)
                if attempt < max_attempts:
                    time.sleep(backoff_s)
                    backoff_s *= 2
                    continue
                return f"[Semantic Scholar 검색 실패] {last_err}"

        if data is None:
            return f"[Semantic Scholar 검색 실패] {last_err or 'unknown'}"

        papers = data.get("data", [])
        if not papers:
            return f"[Semantic Scholar] '{query}'에 대한 결과가 없습니다."

        results = []
        for i, p in enumerate(papers, 1):
            title = p.get("title", "N/A")
            authors = [a.get("name", "") for a in (p.get("authors") or [])[:5]]
            year = p.get("year", "N/A")
            citations = p.get("citationCount", 0)
            venue = p.get("venue", "N/A") or "N/A"
            abstract = (p.get("abstract") or "N/A")[:300]
            ext_ids = p.get("externalIds") or {}
            doi = ext_ids.get("DOI", "N/A")
            arxiv_id = ext_ids.get("ArXiv", "N/A")

            results.append(
                f"[{i}] {title}\n"
                f"    Authors   : {', '.join(authors)}"
                f"{'...' if len(p.get('authors', [])) > 5 else ''}\n"
                f"    Year      : {year} | Citations: {citations}\n"
                f"    Venue     : {venue}\n"
                f"    DOI       : {doi}\n"
                f"    arXiv     : {arxiv_id}\n"
                f"    Abstract  : {abstract}{'...' if len(p.get('abstract') or '') > 300 else ''}\n"
            )

        total = data.get("total", len(results))
        return (
            f"=== Semantic Scholar 검색 결과: '{query}' "
            f"(표시 {len(results)}건 / 전체 {total}건) ===\n\n"
            + "\n".join(results)
        )
