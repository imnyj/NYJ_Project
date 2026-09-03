---
name: paper-subagent-team-convention
description: 논문 프로젝트 서브에이전트 팀 규약 — pN- 접두사 명명, 7종 구성, 백그라운드 실행, 질의 에스컬레이션 경로
metadata:
  type: project
---

논문 프로젝트마다 `~/.claude/agents/`에 `pN-` 접두사(논문 번호)로 서브에이전트 7종을 만든다. 2026-08-31 기준 `p1-*`(paper1, submitted 상태로 수개월 대기 중), `p4-*`(paper4, 현재 작업 중) 총 14개가 존재한다. 새 논문 번호가 부여되면 `Workspace/paperN/.rules/`를 읽어 같은 방식으로 팀을 만든다.

구성은 coder / critic / idea / librarian / visualizer / worker / writer이며 전원 `background: true`, `model: inherit`. 도구 배분의 근거는 규칙에서 나온다. `critic`과 `idea`는 읽기 전용(critic만 WebSearch/WebFetch 추가로 근거 있는 조언 제공), `visualizer`는 Bash 없음(직접 코드를 짜지 말고 coder에게 지시하라는 규칙을 도구 수준에서 강제).

백그라운드 서브에이전트는 `AskUserQuestion`을 쓸 수 없다(메인 루프 세션 전용). 그래서 "모호하면 물어보라"는 `.rules` 규칙은 에스컬레이션 경로로 구현했다. 서브에이전트가 최종 보고 맨 위에 `## 질의` 블록(질문/선택지/추천안/막힌 범위)을 담아 올리면, 오케스트레이터가 `AskUserQuestion`으로 사용자에게 묻고, 답을 `SendMessage`로 그 에이전트에 보내 맥락을 유지한 채 재개시킨다. 새 `Agent` 호출은 맥락이 사라지므로 쓰지 않는다.

운용 규칙 전문은 `~/.claude/CLAUDE.md`에 있고, `~/.claude/settings.json`의 `env`에 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`이 설정되어 모든 세션에 적용된다.

**Why**: 전역 `~/.claude/agents/`에 범용 이름(`coder` 등)을 두면 논문 세션끼리 서로의 에이전트를 잘못 부른다. 접두사가 그 격리를 만든다.
**How to apply**: 논문 팀을 새로 만들거나 고칠 때 `~/.claude/CLAUDE.md`의 규칙을 먼저 읽고 따를 것. [[paper4-aoi-rl-project]] [[claude-antigravity-handoff-workflow]]
