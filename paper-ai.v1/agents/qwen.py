# agents/qwen.py
"""Qwen worker — local LLM delegate for cheap tasks.

Why a separate agent
--------------------
Commander pays Anthropic per-token for everything in its ReAct loop,
including trivial tasks like "summarize this paragraph in one
sentence" or "extract keywords from this text". Routing such tasks
to the user's local Qwen2.5:72B (running in Ollama) costs zero
dollars — the GPU is already paid for.

This agent is the cheapest possible smolagents wrapper around
LiteLLM's Ollama provider. It has no extra tools beyond file IO
because:
  * it should NOT do paper-quality work (that's Writer/Reviewer's job)
  * it should NOT search the web (Librarian)
  * it should NOT execute code (Experimenter)
  * its only job is short transformations on text the Commander hands it.

Limitations vs. the qwen_companion mode
---------------------------------------
The standalone `qwen_companion` mode in this project uses
`LocalLLMClient` with a self-tuning profile, persistent fact memory
(`memory/qwen_facts.md`), and Blue/Green profile management. THIS
agent is plainer — it goes through LiteLLM's ollama provider, so:

  * No persistent profile
  * No fact memory carry-over
  * No self-tuning

If a task needs that richer context, it belongs in the user's
manual `python -m qwen_companion` flow, not in the Commander
pipeline.
"""

import os

from smolagents import CodeAgent, LiteLLMModel
from config import MAX_STEPS
from interface import COMMON_INTERFACE
from tools import FileReadTool, FileWriteTool, DirectoryListTool

# Ollama HTTP base URL. The user's existing setup uses 127.0.0.1:11434
# (matches qwen_profile defaults).
_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
_QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen2.5:72b")

# LiteLLM accepts api_base / api_key for ollama provider; the api_key
# is ignored by Ollama but LiteLLM still requires the kwarg shape.
model = LiteLLMModel(
    model_id=f"ollama/{_QWEN_MODEL}",
    api_base=_OLLAMA_BASE,
    api_key="ollama-no-auth-required",
)

QWEN_PROMPT = f"""
당신은 'Qwen' — Commander가 위임한 가벼운 텍스트 작업을 처리하는 로컬 보조 에이전트입니다.
사용자의 GPU에서 직접 실행되며, Anthropic 비용이 0달러인 점이 강점입니다.

[당신이 적합한 작업]
- 텍스트 요약 (한 문단 → 한 줄, 한 페이지 → 한 단락 등)
- 키워드 추출
- 짧은 텍스트 분류 ("이 메시지가 긍정/부정/중립인가?" 등)
- 단순한 형식 변환 (JSON ↔ 마크다운 표 등)
- 빠른 문법 체크 / 오타 찾기 (품질 교정은 Reviewer 영역)
- 짧은 답변 생성 (사용자 메모, 한 줄짜리 응답)

[당신이 적합하지 않은 작업 — Commander에게 거부 의사 전달]
- 논문 본문 작성 (Writer 영역)
- LaTeX 검증 또는 IEEE 스타일 점검 (Reviewer/Proofreader 영역)
- 시뮬레이션 코드 작성·실행 (Experimenter 영역)
- 학술 논문 검색 (Librarian 영역)
- 자기 코드 수정 (Commander 영역)
- 긴 추론·다단계 분석 (Sonnet/Opus가 더 적합)

이런 작업이 들어오면 한 줄로 거부하고 어느 에이전트가 적합한지 알려주십시오.

[작업 처리 지침]
1. 입력을 받으면 먼저 작업이 본인 영역인지 판단.
2. 본인 영역이면 즉시 결과 생산. 답변은 짧고 직접적으로 (이유 설명 최소화).
3. 본인 영역이 아니면 거부 + 적절한 에이전트 추천.
4. 파일 입력이 필요하면 file_read 사용. 파일 출력이 필요하면 file_write 사용.

[Commander가 알아야 할 점]
- 당신은 Anthropic 비용 0이지만 추론 능력은 Sonnet보다 약함.
- 중요한 결정에는 사용하지 마십시오.
- 응답이 어색하거나 누락이 있으면 Commander가 Sonnet/Opus로 재시도해야 합니다.

{COMMON_INTERFACE}
"""

qwen_agent = CodeAgent(
    name="Qwen",
    tools=[FileReadTool(), FileWriteTool(), DirectoryListTool()],
    model=model,
    description=QWEN_PROMPT,
    # Lower than the full agents — Qwen is for cheap turnaround, not
    # multi-step ReAct chains. If a task needs more than 5 steps, it
    # probably needs Sonnet.
    max_steps=min(MAX_STEPS, 5),
    additional_authorized_imports=[
        "os", "json", "pathlib", "re", "datetime",
    ],
)
