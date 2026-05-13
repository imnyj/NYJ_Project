# tools/arxiv_search.py
"""arXiv API 검색 도구 — Librarian 에이전트 전용."""
from smolagents import Tool


class ArxivSearchTool(Tool):
    name = "arxiv_search"
    description = (
        "Search academic papers on arXiv by keyword. "
        "Returns title, authors, abstract, arXiv ID, and published date. "
        "Use for finding preprints and recent research papers."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "Search query (e.g. 'vehicular network precaching deep reinforcement learning')",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (default: 10)",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, query: str, max_results: int = 10) -> str:
        import urllib.request
        import urllib.parse
        import xml.etree.ElementTree as ET

        base_url = "http://export.arxiv.org/api/query"
        params = urllib.parse.urlencode({
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(max_results, 20),
            "sortBy": "relevance",
            "sortOrder": "descending",
        })

        try:
            req = urllib.request.Request(
                f"{base_url}?{params}",
                headers={"User-Agent": "PaperPipeline/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")
        except Exception as e:
            return f"[arXiv 검색 실패] {e}"

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(data)
        entries = root.findall("atom:entry", ns)

        if not entries:
            return f"[arXiv] '{query}'에 대한 검색 결과가 없습니다."

        results = []
        for i, entry in enumerate(entries, 1):
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
            published = entry.find("atom:published", ns).text[:10]
            arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
            authors = [
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
            ]
            categories = [
                c.get("term")
                for c in entry.findall("atom:category", ns)
            ]

            results.append(
                f"[{i}] {title}\n"
                f"    Authors : {', '.join(authors[:5])}"
                f"{'...' if len(authors) > 5 else ''}\n"
                f"    arXiv   : {arxiv_id}\n"
                f"    Date    : {published}\n"
                f"    Category: {', '.join(categories[:3])}\n"
                f"    Abstract: {summary[:300]}{'...' if len(summary) > 300 else ''}\n"
            )

        return f"=== arXiv 검색 결과: '{query}' ({len(results)}건) ===\n\n" + "\n".join(results)
