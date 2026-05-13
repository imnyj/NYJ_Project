"""
SkillProposer: episodic memory에서 같은 패턴이 임계값 이상 반복되면 새 스킬을 제안.

자동 머지(auto_merge_skills=True)는 sandbox 검증이 필수 — 본 구현은 제안까지만.
실제 코드 생성/머지는 사람 검토 단계로 남김.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from ..llm import QwenClient
from ..memory.episodic import EpisodicMemory


class SkillProposal(BaseModel):
    name: str = Field(description="snake_case 도구 이름")
    rationale: str = Field(description="왜 이 스킬이 필요한지")
    inputs_schema: dict = Field(description="JSON 스키마 of inputs")
    outputs_schema: dict = Field(description="JSON 스키마 of outputs")
    pseudocode: str = Field(description="구현 의사코드")
    estimated_calls_saved_per_week: int = 0


class SkillProposer:
    SYSTEM = """당신은 에이전트의 도구 라이브러리를 확장합니다.
반복되는 task 패턴을 받아 그것을 일반화한 새 도구의 스펙을 제안하세요.
스펙은 명확한 입출력 스키마와 의사코드를 포함해야 합니다."""

    def __init__(self, llm: QwenClient, memory: EpisodicMemory, threshold: int = 5):
        self.llm = llm
        self.memory = memory
        self.threshold = threshold

    def find_candidates(self, lookback: int = 200) -> list[tuple[str, int]]:
        recs = self.memory.recent(limit=lookback)
        kinds = Counter(r.kind for r in recs)
        return [(k, c) for k, c in kinds.items() if c >= self.threshold]

    def propose(self, kind: str, sample_size: int = 8) -> SkillProposal:
        recs = self.memory.recent(kind=kind, limit=sample_size)
        sample = "\n\n".join(
            f"## task #{r.id}\ninput: {r.input_payload}\noutput: {r.output}" for r in recs
        )
        prompt = (
            f"task kind '{kind}'가 최근 {len(recs)}회 처리되었습니다.\n"
            f"샘플:\n{sample}\n\n"
            f"이 패턴을 일반화한 새 스킬을 제안하세요."
        )
        return self.llm.parse(prompt, SkillProposal, system=self.SYSTEM)

    def scan(self) -> list[SkillProposal]:
        out = []
        for kind, _count in self.find_candidates():
            try:
                out.append(self.propose(kind))
            except Exception:
                continue
        return out
