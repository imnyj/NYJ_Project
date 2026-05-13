"""
Reflector: task trace를 받아 ① 성공/실패 평가 ② 원인 가설 ③ 개선안을 produce.
모든 출력은 episodic memory에 저장되어 prompt A/B에 활용.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..llm import QwenClient
from ..memory.episodic import EpisodicMemory, TaskRecord


class Reflection(BaseModel):
    verdict: Literal["success", "partial", "failure"]
    score: float = Field(ge=0, le=1, description="품질 점수 0~1")
    failure_modes: list[str] = Field(
        default_factory=list,
        description="발견된 실패 패턴 (예: 'fabricated citation', 'wrong schema field')",
    )
    root_cause: str = Field(description="실패/저품질의 가장 가능성 있는 원인")
    improved_system_prompt: str | None = Field(
        default=None,
        description="현재 시스템 프롬프트를 어떻게 개선할지 — 개선 필요 시에만 채움",
    )
    new_skill_idea: str | None = Field(
        default=None,
        description="이 task가 자주 반복되어 새 도구/스킬이 필요해 보이면 아이디어",
    )
    note: str = ""


class Reflector:
    SYSTEM = """당신은 AI 에이전트의 자기개선을 돕는 reflector입니다.
실행 trace를 받아 무엇이 잘 되었고 무엇이 실패했는지, 그리고 어떻게 시스템 프롬프트나
도구를 개선할 수 있을지 평가합니다.

엄격하되 건설적이게. 개선이 필요 없으면 improved_system_prompt는 null로 두세요.
새 스킬 아이디어도 정말 반복 패턴이 보일 때만 제안하세요."""

    def __init__(self, llm: QwenClient, memory: EpisodicMemory):
        self.llm = llm
        self.memory = memory

    def reflect(self, record: TaskRecord, current_system_prompt: str = "") -> Reflection:
        prompt = (
            f"# Task kind\n{record.kind}\n\n"
            f"# Input\n{record.input_payload}\n\n"
            f"# Plan\n{record.plan}\n\n"
            f"# Actions\n{record.actions}\n\n"
            f"# Output\n{record.output}\n\n"
            f"# Error (있으면)\n{record.error or 'none'}\n\n"
            f"# 현재 시스템 프롬프트\n{current_system_prompt}\n\n"
            f"위 trace를 분석하고 reflection JSON을 출력하세요."
        )
        return self.llm.parse(prompt, Reflection, system=self.SYSTEM)

    def reflect_and_log(
        self, record: TaskRecord, current_system_prompt: str = ""
    ) -> Reflection:
        r = self.reflect(record, current_system_prompt)
        self.memory.update(
            record.id,
            success=1 if r.verdict == "success" else 0,
            score=r.score,
            reflection=r.model_dump_json(),
        )
        return r
