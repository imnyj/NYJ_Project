"""
ReAct 루프: Thought → Action → Observation 반복으로 추론을 외부에서 스캐폴딩.
Qwen2.5는 비추론 모델이라 이 패턴이 결과 품질을 크게 끌어올린다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..llm import QwenClient


class Step(BaseModel):
    thought: str = Field(description="현재 상태에 대한 추론")
    action: str = Field(description="호출할 도구 이름. 종료 시 'finish'")
    action_input: dict = Field(default_factory=dict, description="도구 인자")


@dataclass
class ReActResult:
    final: Any
    steps: list[dict] = field(default_factory=list)
    converged: bool = False


class ReActLoop:
    """
    tools: {name -> callable(input_dict) -> str|dict} 매핑.
    'finish'는 예약어 — action='finish'면 action_input['answer']을 최종 답으로 반환.
    """

    SYSTEM = """당신은 ReAct 패턴으로 작동합니다.

각 턴마다 다음 JSON 한 개를 출력하세요:
{
  "thought": "지금 무엇을 알고 있고 다음에 무엇이 필요한가",
  "action": "도구 이름 또는 'finish'",
  "action_input": { ... 도구 인자 또는 finish의 경우 {\"answer\": ...} ... }
}

규칙:
- 충분한 정보가 모였으면 즉시 'finish'.
- 모르는 사실을 만들어내지 말고, 도구로 확인하거나 'unknown'으로 답하세요.
- 같은 action을 두 번 연속 호출하지 마세요."""

    def __init__(
        self,
        llm: QwenClient,
        tools: dict[str, Callable[[dict], Any]],
        max_steps: int = 6,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps

    def run(self, task: str, context: str = "") -> ReActResult:
        tool_desc = "\n".join(f"- {n}: {fn.__doc__ or 'no doc'}" for n, fn in self.tools.items())
        system = (
            self.SYSTEM
            + f"\n\n사용 가능 도구:\n{tool_desc}\n- finish: 작업 종료. action_input에 'answer' 필수."
        )

        history: list[dict] = []
        steps: list[dict] = []
        prompt = f"작업: {task}\n\n컨텍스트: {context}".strip()

        for i in range(self.max_steps):
            try:
                step = self.llm.parse(prompt, Step, system=system, history=history)
            except Exception as e:
                steps.append({"error": f"parse_failed: {e}"})
                break

            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": step.model_dump_json()})
            step_log = step.model_dump()

            if step.action == "finish":
                answer = step.action_input.get("answer")
                steps.append({**step_log, "result": "finished"})
                return ReActResult(final=answer, steps=steps, converged=True)

            tool = self.tools.get(step.action)
            if tool is None:
                obs = f"ERROR: unknown tool '{step.action}'. 사용 가능: {list(self.tools)}"
            else:
                try:
                    obs = tool(step.action_input)
                except Exception as e:
                    obs = f"ERROR: {type(e).__name__}: {e}"

            obs_str = obs if isinstance(obs, str) else json.dumps(obs, ensure_ascii=False, default=str)
            steps.append({**step_log, "observation": obs_str[:2000]})
            prompt = f"Observation: {obs_str}\n\n다음 step JSON을 출력하세요."

        return ReActResult(final=None, steps=steps, converged=False)
