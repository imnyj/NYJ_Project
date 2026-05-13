"""도구 레지스트리. PDF·메모리·workspace·web 도구를 한데 모은다."""

from __future__ import annotations

from typing import Any

from pypdf import PdfReader

from ..memory.semantic import SemanticMemory
from ..safety.guard import Guard
from . import workspace as _ws
from . import web as _web


def read_pdf(args: dict) -> str:
    """PDF 텍스트 추출. args={'path': '...'}"""
    reader = PdfReader(args["path"])
    return "\n\n".join(
        f"## page {i+1}\n{(p.extract_text() or '')}" for i, p in enumerate(reader.pages)
    )


def search_memory(args: dict, mem: SemanticMemory) -> list[dict]:
    """RAG 벡터 DB 검색. args={'query': '...', 'k': 5}"""
    return mem.search(args["query"], k=args.get("k", 5))


def make_default_tools(semantic: SemanticMemory) -> dict[str, Any]:
    return {
        "read_pdf": read_pdf,
        "search_memory": lambda a: search_memory(a, semantic),
    }


def make_chat_tools(
    semantic: SemanticMemory,
    guard: Guard,
) -> tuple[dict[str, Any], _web.WebState, dict[str, str]]:
    """
    chat용 풀 도구 세트.
    web 호출 한도와 차단 도메인은 정책 파일(guard.policy)에서 가져옴.
    """
    web_state = _web.WebState(
        max_calls=guard.policy.web_max_calls,
        blocked_domains=set(guard.policy.web_blocked_domains),
    )

    tools: dict[str, Any] = {
        "read_pdf": read_pdf,
        "search_memory": lambda a: search_memory(a, semantic),
    }
    tools.update(_ws.make_workspace_tools(guard))
    if guard.policy.web_enabled:
        tools.update(_web.make_web_tools(web_state))

    docs: dict[str, str] = {
        "read_pdf": "PDF 텍스트 추출. args: {path: str}",
        "search_memory": "개인 자료(RAG) 검색. args: {query: str, k?: int}",
    }
    docs.update(_ws.TOOL_DOCS)
    if guard.policy.web_enabled:
        docs.update(_web.TOOL_DOCS)

    return tools, web_state, docs


def is_write_tool(name: str) -> bool:
    return name in _ws.WRITE_TOOL_NAMES
