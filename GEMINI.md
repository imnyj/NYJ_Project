# 🚀 Antigravity Multi-Agent Factory Rules (GEMINI.md)

This file contains the absolute rules for the Antigravity agent and all its subagents.
The system is now operating as a **Recursive Hierarchical Multi-Agent System**.

## 1. Recursive Task Atomization
- **Rule:** Never attempt to solve a complex problem in one go. Break the problem down into distinct, atomic sub-tasks.
- **Rule:** If a task contains multiple steps (e.g., Data parsing + Model training + Visualization), ANY agent (including Workers) MUST spawn their own subordinate agents for each atomic step using `invoke_subagent`. You are fully empowered to create infinite layers of subagents.
- **Rule:** Pass a clear checklist to subordinates. The subordinate must ONLY complete the checklist and nothing more.

## 2. Hierarchical Review System
- **Rule:** When a subordinate finishes, the superior must review the work against the original checklist. If there are flaws, the superior must order the subordinate to fix them before accepting the result.

## 3. Concurrency & Safety (Locking)
- **Rule:** When an agent is about to modify a file, it MUST use the file locking protocol via `/home/imnyj/Command/core/lock_manager.py`.
- **Rule:** Wait for the lock if it's held by another agent. Never overwrite files blindly.

## 4. Accountability (Audit Logging)
- **Rule:** Every time a file is modified, the agent MUST log the action using `/home/imnyj/Command/core/audit_logger.py`.
- **Rule:** If an error is detected in a file, the superior agent must read the audit log, find the agent responsible, and instruct them to fix the error.

## 5. Workspace & Deliverables (Project Folder)
- **Rule:** Do NOT save project deliverables, code files, or final research artifacts to your own `.gemini/.../brain/` directory. Doing so scatters the project files across multiple subagents.
- **Rule:** ALL output files and code MUST be written to a centralized shared project folder, for example `/home/imnyj/Workspace/<Project_Name>/` (the Manager should define this path and pass it down the checklist).
- **Rule:** The `.gemini/.../brain/` directory should ONLY be used for internal agent scratchpads, temporary thinking, or system logs.
- **Rule:** [강화] 사용되지 않거나 폐기된 과거 파일(가짜 구현체 등)은 즉시 프로젝트 내 `backup/` 디렉토리로 강제 이동 및 격리하여 혼선을 원천 차단한다.

## 6. Subagent Creation (Agent Factory)
- When defining subagents, use specific roles like `manager_xxx` or `worker_xxx`. 
- Provide them with this `GEMINI.md` context so they follow the same safety rules.

## 7. SSH Reconnection & Input Handling
- **Rule:** SSH 세션 불안정 및 재연결로 인해 `source /home/imnyj/venv/bin/activate` 명령이 자동으로 입력되는 경우, 에이전트는 이를 별도의 수행 명령으로 취급하지 않고 완전히 무시하며, 이전 컨텍스트에 맞추어 작업을 중단 없이 안전하게 계속 수행해야 한다.

## 8. Memory Management & Fact-Checking (RAG)
- **Rule:** 작업을 수행할 때는 항상 파일(CSV, MD, NPZ 등)에 진행 데이터와 로그를 기록하고, 다음 작업을 시작할 때 메모리 기억이 아닌 기록된 파일을 직접 읽어 수행하여 환각(Hallucination)을 방지한다.
## 9. Clarification & User Confirmation
- **Rule:** 작업 중 요구사항이 불명확하거나 애매한 부분이 발생하는 경우, 절대로 임의로 판단하여 진행하지 말고 필히 사용자에게 질문하여 확인을 받은 뒤 작업을 수행해야 한다.
## 10. Workspace Cleanliness (etc Directory)
- **Rule:** 작업 중 발생하는 기타 파일(임시 스크립트, 중간 데이터, 디버깅 로그 등)이 프로젝트 메인 공간에 무분별하게 쌓이는 것을 철저히 방지한다.
- **Rule:** 메인 산출물이 아닌 모든 보조 파일들은 반드시 `etc/` 디렉토리를 생성한 뒤, 그 내부에 목적별로 카테고리화(예: `etc/scripts/`, `etc/logs/`, `etc/temp/`)하여 단정하게 정리해야 한다.

## 12. Persistent Session Harness (Codex-compatible)
- **Rule:** 새 세션에서는 먼저 현재 작업의 실제 프로젝트 루트를 확인하고, 기존 프로젝트가 있으면 그 경로를 기준으로 작업한다. 새 프로젝트의 작업 공간이 명시되었을 때에만 `/home/imnyj/Workspace/<Project_Name>/`를 생성한다.
- **Rule:** 여러 독립적인 작업 단위가 있고 런타임의 동시성 한도 및 상위 지침이 허용할 때만, 명확한 체크리스트와 인터페이스를 전달하여 하위 에이전트에 위임한다. 단일·간단한 작업에 하위 에이전트를 강제하지 않는다.
- **Rule:** 세션·프로젝트 초기화, 위임, 상태 기록에는 `session-harness` 및 `multi-agent-manager` 스킬을 작업 성격에 맞게 적용한다. 이 파일은 프로젝트 운영 지침이며, Codex 런타임의 시스템·개발자 지침을 대체하지 않는다.

## 13. Execution Logging (자가 개선 로그)
- **Rule:** 모든 세션 종료 시 `logs/execution_notes.md`에 (1) 수행한 작업 (2) 실패/재시도 지점 (3) 수동 교정 내용을 3줄 이내로 요약 추가할 것.

## 14. Language (언어)
- **Rule:** 모든 에이전트는 사용자와 소통하거나 문서/결과물을 작성할 때 반드시 한글(Korean)을 사용해야 한다.

## 15. Idle Time Upgrades
- **Rule:** 플랫폼의 유휴 업그레이드 작업이나 사용자의 명시적 지시가 있을 때에만, 최초 1회에 한하여 `feedback_backlog.md`를 검토하고 `skill-crafter` 절차를 수행한다. 반복 타이머는 만들거나 유지하지 않는다.
- **Rule:** Git 커밋·원격 푸시는 외부 상태 변경이므로 사용자의 명시적 승인 없이는 수행하지 않는다. 특히 강제 푸시는 자동화하지 않는다.
