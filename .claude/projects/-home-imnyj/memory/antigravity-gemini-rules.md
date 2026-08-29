---
name: antigravity-gemini-rules
description: 홈 디렉토리 GEMINI.md에 정의된 Antigravity 멀티에이전트 시스템의 절대 규칙과 .agents/skills/의 20개 커스텀 스킬 — 다른 에이전트(Gemini/Antigravity CLI)용이지만 이 환경에서 작업할 때 참고할 규범
metadata: 
  node_type: memory
  type: project
  originSessionId: 3b462830-f472-4351-a6b3-bd5ebd3a999d
  modified: 2026-08-27T01:03:58.631Z
---

`/home/imnyj/GEMINI.md`는 Antigravity(Gemini CLI) 멀티에이전트 시스템이 따르는 절대 규칙 15개 항목이며, `~/.agents/skills/`에 이를 뒷받침하는 20개 커스텀 스킬(SKILL.md)이 이미 전부 생성되어 있다 (academic-worker, academic-writing-style, paper-writing 번들, sumo-sim 번들, session-harness, multi-agent-manager, skill-crafter, file-organization, resource-cleanup 등). `antigravity_upgrades.md`가 원본 스펙이며, 실제 GEMINI.md는 이미 그 스펙을 넘어 "[강화]" 표시로 자체 개정까지 완료된 상태(예: 5시간 유휴 시 최초 1회만 자동 GitHub 강제 push 등).

핵심 규칙 요지: (1) 복잡한 작업은 반드시 서브에이전트로 원자적 분해 (2) 상위가 하위 결과물을 체크리스트 대비 검수 (3) 파일 수정 시 락 프로토콜 (4) 모든 수정은 audit_logger로 기록 (5) 산출물은 반드시 `Workspace/<Project>/`에 저장, `.gemini/.../brain/`은 스크래치패드 전용 (6) 애매하면 반드시 사용자에게 확인 (9) 항상 파일에 기록하고 파일을 직접 읽어 환각 방지 (10) 보조 파일은 `etc/` 하위로 분류 정리 (11) 절대경로 검증 없이 완료 허위보고 금지, 물리적 변경 직접 확인 후 보고 (13) 세션 종료 시 `logs/execution_notes.md`에 3줄 요약 (14) 사용자 소통은 반드시 한글.

**Why**: 이 규칙들은 Gemini/Antigravity CLI 에이전트를 겨냥해 작성됐지만, 사용자가 동일한 프로젝트(Workspace/paper4 등)를 Claude Code로도 이어서 진행하므로, 두 에이전트 간 산출물 정합성을 위해 Claude Code도 같은 관례(파일 기반 기록, etc/ 정리, 절대경로 검증, 완료 전 실제 확인, 애매하면 질문)를 따르는 편이 안전하다.
**How to apply**: paper4 등 이 사용자의 연구 프로젝트 작업 시, 산출물은 Workspace 하위 프로젝트 폴더에 쓰고, 임시 파일은 etc/에 정리하며, 완료 보고 전 실제 파일이 물리적으로 바뀌었는지 확인할 것. [[paper4-aoi-rl-project]]
