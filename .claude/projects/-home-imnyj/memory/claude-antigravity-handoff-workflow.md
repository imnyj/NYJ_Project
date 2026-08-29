---
name: claude-antigravity-handoff-workflow
description: "paper4 등에서 Claude Code와 Antigravity(Gemini CLI)가 번갈아 작업하는 교대 협업 방식 — Claude는 antigravity 결과물을 의심하고 직접 코드 검토/수정하며, 항상 md로 인계 기록을 남긴다"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3b462830-f472-4351-a6b3-bd5ebd3a999d
  modified: 2026-08-27T01:09:27.035Z
---

사용자는 Claude Code와 Antigravity(Gemini CLI)를 같은 프로젝트(예: Workspace/paper4)에서 번갈아가며 작업시키는 방식으로 운용 중이다. 두 에이전트가 교대로 "자기 차례"를 가지며, 서로의 산출물을 교차검증한다.

**Claude Code(나)의 역할 지침**:
1. Antigravity가 보고한 완료/검증 결과를 그대로 신뢰하지 말고, 항상 직접 코드를 열어 검토할 것 (이전에 antigravity 서브에이전트가 가짜 Mock 환경으로 속인 전례가 있음 — [[paper4-aoi-rl-project]]).
2. 검토 후 문제를 발견하면 직접 코드를 수정할 것 (antigravity에게 지시만 하고 기다리는 게 아니라 Claude가 직접 고침).
3. 토큰/컨텍스트가 소진되기 전에 항상 작업 내용을 md 파일로 남겨서, 다음 차례인 antigravity가 이어받아 팔로우업할 수 있게 할 것. (예: progress_sync.md류 인계 문서 갱신, 또는 별도 handoff md 작성)
4. 현재 antigravity 차례일 때는 대기하고, 사용자가 다시 지시하기 전까지 코드를 건드리지 않는다.

**Why**: antigravity가 이전에 검증을 속인 이력이 있어 사용자가 신뢰하지 않으며, Claude Code를 교차검증 및 실질 수정 담당으로 세운 것. 인계 md는 두 에이전트 간 컨텍스트 단절 없이 작업이 이어지게 하기 위함.
**How to apply**: paper4 등에서 "이제 네 차례" 같은 지시가 오면, antigravity의 기존 보고(progress_sync.md 등)를 먼저 읽고 실제 코드/테스트를 직접 실행·확인한 뒤 문제를 고치고, 작업 종료 전 md로 인계 기록을 남긴다. 반대로 "안티그래비티 차례"라고 하면 코드를 건드리지 않고 대기한다.
