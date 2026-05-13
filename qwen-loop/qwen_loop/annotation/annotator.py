"""
Annotator: 텍스트 → 스키마 인스턴스 (또는 리스트). Verifier 통과 옵션.
"""

from __future__ import annotations

from typing import Type, TypeVar

from pydantic import BaseModel

from ..llm import QwenClient
from ..reasoning.verifier import Verifier
from .schemas import SCHEMA_REGISTRY

T = TypeVar("T", bound=BaseModel)


class Annotator:
    def __init__(self, llm: QwenClient, verifier: Verifier | None = None):
        self.llm = llm
        self.verifier = verifier

    def extract_one(
        self, text: str, schema: Type[T] | str, instruction: str | None = None
    ) -> T:
        if isinstance(schema, str):
            schema = SCHEMA_REGISTRY[schema]
        prompt = (
            f"{instruction or '아래 텍스트에서 정보를 추출하세요.'}\n\n"
            f"텍스트:\n---\n{text}\n---"
        )
        result = self.llm.parse(prompt, schema)

        if self.verifier:
            v = self.verifier.verify(result.model_dump_json(), text, instruction or "추출")
            if not self.verifier.passes(v):
                # 한 번만 더 시도 — fabrication 목록을 모델에게 보여줌
                repair = (
                    f"이전 추출에 문제가 있었습니다.\n"
                    f"발견된 fabrication: {v.fabrications}\n"
                    f"메모: {v.note}\n\n원래 작업을 다시 수행하세요."
                )
                result = self.llm.parse(prompt + "\n\n" + repair, schema)
        return result

    def extract_many(
        self,
        text: str,
        schema: Type[T] | str,
        instruction: str | None = None,
    ) -> list[T]:
        """텍스트에서 N개 인스턴스 추출."""
        if isinstance(schema, str):
            schema = SCHEMA_REGISTRY[schema]

        # list wrapper schema를 동적 생성
        from pydantic import RootModel

        class Wrapper(RootModel[list[schema]]):  # type: ignore
            pass

        prompt = (
            f"{instruction or '아래 텍스트에서 해당하는 모든 항목을 추출해 JSON 배열로 출력하세요.'}\n\n"
            f"텍스트:\n---\n{text}\n---"
        )
        out = self.llm.parse(prompt, Wrapper)
        return out.root
