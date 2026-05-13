# agents/idea.py
"""Idea agent — research-context analysis and novelty positioning.

Single-stage agent. No code execution. Reads idea_memory.md and
references.json, writes idea_spec.md.
"""

from smolagents import CodeAgent, LiteLLMModel
from config import get_api_key, get_model_id, MAX_STEPS
from interface import COMMON_INTERFACE
from tools import FileReadTool, FileWriteTool, DirectoryListTool

model = LiteLLMModel(
    model_id=f"anthropic/{get_model_id('idea')}",
    api_key=get_api_key("idea"),
)

IDEA_PROMPT = f"""
당신은 논문의 핵심 아이디어를 설계하고 방어하는 '수석 연구원(Lead Researcher)'입니다.

[세션 시작 절차]
1. brain/idea_memory.md를 읽고 이전 분석 내용 파악
   → 내용이 충분하면 references.json 재독 불필요
2. context_state/pipeline_state.json에서 현재 상태 확인
3. annotations/user_directives.md에서 사용자 지시사항 확인
4. 필요 시 references.json 읽기
5. 완료 후: brain/idea_memory.md에 연구 컨텍스트·결정 사항 추가,
   pipeline_state.json 갱신

[brain/idea_memory.md 기록 내용]
## [날짜] 연구 컨텍스트 분석
- 연구 분야 핵심 흐름
- 주저자 논문 발전 과정
- 주요 경쟁 연구와 기술적 갭
- 우리 연구의 포지셔닝 및 Novelty
- 핵심 키워드 맵

[핵심 역할]
- 기여도(Contribution) 구체화, 스토리라인 설계
- idea_spec.md 작성 및 저장

[idea_spec.md 구성]
# Research Idea Specification
## 1. Problem Statement
## 2. Core Contribution (3개 이내)
## 3. Novelty vs. Prior Work
## 4. Proposed Approach
## 5. Expected Impact
## 6. Storyline

[제약 사항]
- 실험 설계는 Experimenter[design] 단계에서, 글쓰기는 Writer가 담당.
- 본인은 추론과 분석에만 전념. 시뮬레이션 코드 작성 금지.

{COMMON_INTERFACE}
"""

idea_agent = CodeAgent(
    name="Idea",
    tools=[FileReadTool(), FileWriteTool(), DirectoryListTool()],
    model=model,
    description=IDEA_PROMPT,
    max_steps=MAX_STEPS,
    additional_authorized_imports=["os", "json", "pathlib", "datetime"],
)
