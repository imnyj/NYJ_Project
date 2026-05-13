"""
Verifier: 답이 만들어진 뒤 별도 시스템 프롬프트로 자가 검증.
Qwen2.5의 환각을 잡는 가장 비용-효과 좋은 방법 중 하나.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..llm import QwenClient


class VerificationResult(BaseModel):
    grounded: bool = Field(description="답이 주어진 컨텍스트에 근거하는가")
    consistent: bool = Field(description="내부 모순이 없는가")
    fabrications: list[str] = Field(
        default_factory=list, description="컨텍스트에 없는데 단언된 사실들"
    )
    confidence: float = Field(ge=0, le=1, description="0~1 신뢰도")
    note: str = Field(default="", description="검증자의 짧은 메모")


class Verifier:
    SYSTEM = """당신은 답변 검증자입니다. 주어진 (컨텍스트, 답)을 받아
답이 컨텍스트에 근거하는지, 내부 모순이 없는지, 꾸며낸 사실은 없는지 평가합니다.

엄격하게 평가하세요. 컨텍스트에 명시되지 않은 단언은 모두 fabrication입니다.
일반 상식조차도 컨텍스트가 요구하는 경우엔 fabrication으로 표시하세요."""

    def __init__(self, llm: QwenClient, strict: bool = True):
        self.llm = llm
        self.strict = strict

    def verify(self, answer: str, context: str, task: str) -> VerificationResult:
        prompt = (
            f"# 작업\n{task}\n\n"
            f"# 컨텍스트\n{context}\n\n"
            f"# 답\n{answer}\n\n"
            f"위 답을 검증하고 결과를 JSON으로 출력하세요."
        )
        return self.llm.parse(prompt, VerificationResult, system=self.SYSTEM)

    def passes(self, result: VerificationResult, min_conf: float = 0.7) -> bool:
        if self.strict:
            return result.grounded and result.consistent and not result.fabrications
        return result.confidence >= min_conf and not result.fabrications
