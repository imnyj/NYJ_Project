# 로컬 워크스테이션 특화 AI Agent 업그레이드 요청서

Version 1.0

## 0. 목적

이 문서는 특정 원격 GPU 워크스테이션 환경에 종속된 AI Agent 운영 규칙만을 분리하여 설치·적용하기 위한 업그레이드 요청서이다.

이 문서의 목적은 다음을 하나도 누락하지 않고 구현하는 것이다.

1. 4개의 GPU를 보유한 워크스테이션이라는 하드웨어 특성을 Agent가 항상 인지하도록 한다.
2. `/home/imnyj/Workspace/<Project_Name>`를 중앙 작업 공간으로 사용한다.
3. `/home/imnyj/Command/core/lock_manager.py`, `/home/imnyj/Command/core/audit_logger.py`, `/home/imnyj/feedback_backlog.md`, `/home/imnyj/logs/execution_notes.md`, `/home/imnyj/proposals/` 등 지정된 로컬 인프라 경로를 정확히 사용한다.
4. 다중 Agent, 장기 실행, GPU 병렬 실행, 파일 잠금, 감사 로그, 체크포인트, 리소스 정리, 피드백 기반 개선을 로컬 환경에 맞게 강제한다.
5. 논문 특화 규칙 자체는 별도 업그레이드 요청서에서 관리하되, 이 문서의 공통 로컬 규칙과 충돌하지 않도록 한다.

## 1. 구현 원칙

- 아래에 포함된 원문 규칙은 의미를 임의로 완화·삭제·재해석하지 않는다.
- 현재 사용 중인 AI Agent/CLI가 원문에 등장하는 특정 도구명을 지원하지 않는 경우, 동일한 목적을 달성하는 현재 플랫폼의 대응 기능을 먼저 확인한다.
- 지원하지 않는 기능이나 API를 존재한다고 가정하여 구현하지 않는다.
- 경로는 이 워크스테이션의 실제 절대 경로를 기준으로 검증한다.
- 구현 완료 후 파일 존재 여부, 내용, 권한, 실제 동작을 직접 검증한다.
- 원문에 동일 규칙이 중복되어 있는 경우에도 누락 방지를 위해 의미를 보존한다.

## 2. 원문 규칙 전체

## 1. Global Rules (GEMINI.md)
다음 내용을 사용자 홈 디렉토리의 `GEMINI.md` (예: `~/GEMINI.md`) 파일로 생성해주세요.
또한, 에이전트 자신과 모든 하위 에이전트(subagents)가 이 파일의 규칙을 반드시 준수하도록 시스템 프롬프트(User Rules)에 등록해주세요.

```markdown
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
- **Rule:** 결과물 저장 공간에는 항상 최신 파일만 유지하며, 모든 이전 버전의 파일은 `backup/` 디렉토리로 안전하게 자동 분리 격리 관리되도록 한다.

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

## 11. Path Verification & Anti-Hallucination
- **Rule:** 서브 에이전트가 파일 수정/생성 작업을 수행할 때는 반드시 지정된 정확한 절대 경로(Absolute Path)를 재확인하고 검증해야 한다. 존재하지 않거나 임의의 가상 경로에 작업해 놓고 완료했다고 허위 보고하는 환각(Hallucination)을 엄격히 금지한다.
- **Rule:** 작업 완료 전 반드시 실제 타겟 파일이 물리적으로 올바르게 변경되었는지 직접 확인(Double Check)한 뒤에 상위 에이전트에게 보고할 것.

## 12. Persistent Session Harness (자동 초기화 및 하네스 구동)
- **Rule:** 새로운 세션이 시작될 때마다 에이전트는 별도 지시가 없더라도 자동으로 프로젝트 경로를 파악하여 `/home/imnyj/Workspace/<Project_Name>` 디렉토리를 확인 및 생성하고, 해당 디렉토리를 작업 기준으로 삼아야 한다.
- **Rule:** 작업을 진행할 때, 단순 수행에 그치지 않고 `session-harness` 및 `multi-agent-manager` 스킬을 로드하여 하위 에이전트에게 태스크를 분배하고 관리하는 초기화 하네스(Initialization Harness)를 반드시 가동하여 체계적으로 작업을 수행할 것.

## 13. Execution Logging (자가 개선 로그)
- **Rule:** 모든 세션 종료 시 `logs/execution_notes.md`에 (1) 수행한 작업 (2) 실패/재시도 지점 (3) 수동 교정 내용을 3줄 이내로 요약 추가할 것.

## 14. Language (언어)
- **Rule:** 모든 에이전트는 사용자와 소통하거나 문서/결과물을 작성할 때 반드시 한글(Korean)을 사용해야 한다.

## 15. Idle Time Upgrades
- **Rule:** 5시간 유휴 상태가 경과하여 백그라운드 업그레이드(예: skill-crafter) 및 GitHub 업로드를 지시받는 경우, 이는 매 5시간마다 반복하라는 의미가 아니며 **최초 1회에 한해서만** 실행하고 타이머를 완전히 종료해야 한다.

```

### Skill: anti-hallucination
디렉토리 생성: `~/.agents/skills/anti-hallucination/`

#### 파일 생성: `~/.agents/skills/anti-hallucination/SKILL.md`
```markdown
---
name: anti-hallucination
description: Skill for enforcing strict path verification and eliminating AI hallucinations.
---
# Anti-Hallucination Skill

- **Path Verification**: Before reporting that a file operation is complete, explicitly double-check the absolute path of the file. Never assume the path was correct. Run a terminal command (e.g., `ls` or `view_file`) to verify the file was actually modified in the intended directory.
- **Strict Tone Formatting**: For all writing tasks, eliminate AI-like exaggerated adverbs and adjectives (e.g., "significant", "powerful synergy", "completely independent"). Use a dry, factual, and objective academic tone.
- **Evidence-Based Reporting**: When citing experimental results or writing down data, physically read the output logs or CSV files using `view_file`. Do not estimate or guess values.

## 11. Path Verification & Anti-Hallucination (환각 방지 및 경로 검증)
- **Rule:** 서브 에이전트가 파일 수정/생성 작업을 수행할 때는 **반드시** 지정된 정확한 절대 경로(Absolute Path)를 재확인하고 검증해야 한다. 존재하지 않거나 임의의 가상 경로(예: `papers/...`)에 작업해 놓고 완료했다고 허위 보고하는 환각(Hallucination)을 엄격히 금지한다.
- **Rule:** 작업 완료 전 반드시 실제 타겟 파일이 물리적으로 올바르게 변경되었는지 직접 확인(Double Check)한 뒤에 상위 에이전트에게 보고할 것.

```

### Skill: coding-best-practices
디렉토리 생성: `~/.agents/skills/coding-best-practices/`

#### 파일 생성: `~/.agents/skills/coding-best-practices/SKILL.md`
```markdown
---
name: coding-best-practices
description: 코딩 시 흔히 발생하는 안티패턴을 방지하고 코드 품질 및 안정성을 보장하기 위한 스킬입니다.
---
# Coding Best Practices (코딩 안티패턴 방지 스킬)

- **목적**: 파일 전체 덮어쓰기, 거대 단일 파일 생성, 락 무시 등의 코딩 안티패턴을 방지하여 프로젝트의 안정성과 유지보수성을 극대화합니다.
- **주요 교정 대상 및 안티패턴 (Anti-patterns)**:
  1. **파일 무단 덮어쓰기 (Blind Overwrite)**
     - 금지: 기존 코드를 확인하지 않거나, 작은 수정 사항을 위해 전체 파일을 무식하게 덮어쓰는 행위.
     - 권장: 코드를 수정할 때는 먼저 파일을 읽어 구조를 파악하고, 일부분만 변경할 경우 정밀하게 타겟팅하여 수정할 것.
  2. **락(Lock) 및 로깅 누락 (Bypassing Safety Protocols)**
     - 금지: `lock_manager.py` 나 `audit_logger.py` 프로토콜을 무시하고 몰래 코드를 수정하는 행위.
     - 권장: 항상 락 프로토콜을 확인하여 동시성 충돌을 방지하고, 모든 수정 내역을 로그에 남길 것.
  3. **거대 단일 파일 (Monolithic File) 생성**
     - 금지: 수천 줄의 코드를 한두 개의 파일에 전부 몰아넣는 행위.
     - 권장: 기능별로 파일을 모듈화(예: `config`, `utils`, `models`)하여 가독성을 높일 것.
  4. **테스트/검증 없이 완료 보고 (Unverified Code)**
     - 금지: 코딩 완료 후 문법 에러나 런타임 에러 확인 없이 작업을 종료하는 행위.
     - 권장: 코드 작성 후에는 반드시 린터(linter)나 간단한 실행을 통해 에러가 없는지 스스로 검증할 것.

```

### Skill: collaboration-best-practices
디렉토리 생성: `~/.agents/skills/collaboration-best-practices/`

#### 파일 생성: `~/.agents/skills/collaboration-best-practices/SKILL.md`
```markdown
---
name: collaboration-best-practices
description: 에이전트 간 협업 시 발생하는 사일로 현상 및 소통 오류(안티패턴)를 방지하기 위한 스킬입니다.
---
# Collaboration Best Practices (협업 안티패턴 방지 스킬)

- **목적**: Manager와 Worker 에이전트 간의 명확한 의사소통과 책임 전가를 방지하여 멀티 에이전트 시스템의 신뢰성을 높입니다.
- **주요 교정 대상 및 안티패턴 (Anti-patterns)**:
  1. **정보 누락 보고 (Vague Reporting)**
     - 금지: "작업을 완료했습니다."라는 말만 남기고 구체적인 산출물 경로나 변경된 내역을 상위 에이전트에게 전달하지 않는 행위.
     - 권장: 작업 완료 시 반드시 산출물이 저장된 **절대 경로(Absolute Path)**와 주요 변경 사항을 명확히 요약하여 보고할 것.
  2. **조용한 실패 (Silent Failure)**
     - 금지: 에러나 문제 발생 시 이를 무시하거나, 보고 없이 세션을 종료(또는 무한 대기)하는 행위.
     - 권장: 진행이 막히면 즉각 상위 에이전트나 사용자에게 현재 상태, 에러 원인, 시도해본 방안을 포함하여 명확히 보고/질문할 것.
  3. **지시사항 임의 변형 (Task Hallucination)**
     - 금지: 체크리스트에 없는 작업을 임의로 수행하거나, 범위를 벗어난 파일까지 건드리는 행위.
     - 권장: 하달받은 체크리스트 내에서만 작업을 철저히 수행하며, 부가적인 작업이 필요하다고 판단되면 먼저 허가를 받을 것.
  4. **임시 파일 방치 (Littering)**
     - 금지: 작업 중 발생한 임시 파일이나 스크래치패드를 프로젝트 메인 경로에 그대로 두는 행위.
     - 권장: 메인 폴더는 최종 산출물만 존재하도록 유지하고, 모든 임시 데이터 및 로그는 `etc/` 디렉토리 하위에 정리할 것.

```

### Skill: config-management-best-practices
디렉토리 생성: `~/.agents/skills/config-management-best-practices/`

#### 파일 생성: `~/.agents/skills/config-management-best-practices/SKILL.md`
```markdown
---
name: config-management-best-practices
description: 하드코딩된 설정값, 매직 넘버, 로컬 절대 경로 등 설정 관리 관련 안티패턴을 방지하기 위한 스킬입니다.
---
# Config Management Best Practices

## 개요
작업(코딩 및 스크립트 작성) 중 아래와 같은 설정 관리 안티패턴이 발생할 수 있습니다. 이를 미연에 방지하여 시스템 전반의 이식성, 보안성 및 유지보수성을 높입니다.

## 대표적인 안티패턴 (Anti-patterns)
1. **경로 하드코딩 (Hardcoded Paths)**: 특정 로컬 환경(예: `/home/user/path`)에 종속된 절대 경로를 코드 내부 깊숙이 직접 타이핑하는 행위. 이는 다른 환경에서의 실행을 불가능하게 만듭니다.
2. **매직 넘버/스트링 (Magic Numbers/Strings)**: 의미와 출처를 알 수 없는 숫자, 타임아웃 값, 혹은 식별자를 코드 로직 한가운데 직접 기입하는 행위.
3. **민감 정보 노출 (Hardcoded Secrets)**: API 인증 키, 데이터베이스 패스워드 등을 소스코드 내에 평문(Plain text)으로 저장하는 행위.

## 행동 지침 (Best Practices)
1. **환경 변수 및 `.env` 활용**: 민감 정보나 환경마다 달라지는 설정은 코드에서 분리하여 OS 환경 변수나 환경 설정 파일(`.env`, `config.yaml` 등)을 통해 런타임에 주입받도록 구성하십시오.
2. **상수(Constants) 중앙 집중화**: 불가피하게 코드 내에 선언해야 하는 설정값(타임아웃, 포트 번호 등)은 파일 최상단이나 별도의 `config.py`, `constants.py` 파일에 명확한 이름의 상수로 정의하십시오.
3. **동적 경로 처리**: 파일 입출력 시 상대 경로를 기반으로 실행 시점에 절대 경로를 계산(`pathlib.Path`, `os.path.abspath`)하도록 작성하여, 어느 폴더에서 실행되더라도 문제가 없도록 보장하십시오.

이 스킬은 모든 에이전트가 코드를 작성, 수정 또는 리뷰할 때 기본적으로 적용해야 합니다.

```

### Skill: context-management-best-practices
디렉토리 생성: `~/.agents/skills/context-management-best-practices/`

#### 파일 생성: `~/.agents/skills/context-management-best-practices/SKILL.md`
```markdown
---
name: context-management-best-practices
description: 에이전트 통신 및 답변 시 불필요한 텍스트 덤프로 인한 컨텍스트 윈도우 낭비(Token Inflation)를 방지하는 스킬입니다.
---
# Context Management Best Practices (컨텍스트 관리 및 토큰 최적화)

- **목적**: 장문 로그의 무분별한 복사-붙여넣기나 중복된 상태 요약을 방지하여, 에이전트의 컨텍스트 윈도우 한계를 보호하고 모델의 추론 성능(집중력)을 유지합니다.

- **주요 교정 대상 및 안티패턴 (Anti-patterns)**:
  1. **로우 데이터 덤핑 (Raw Log Dumping)**
     - 금지: 명령어 실행 결과(수백 줄의 에러 로그나 코드 전체)를 에이전트 간 메시지나 사용자 답변 텍스트에 그대로 출력하는 행위.
     - 권장: 장문의 출력은 반드시 임시 파일(예: `etc/logs/`)이나 Artifact로 저장하고, 메시지에는 해당 파일의 절대 경로와 3~4줄 이내의 핵심 요약(원인/해결책)만 포함시킬 것.

  2. **과도한 상태 반복 (Repetitive State Summarization)**
     - 금지: 서브 에이전트 간 통신 시 매번 '지금까지의 전체 작업 이력'을 처음부터 끝까지 중복 요약하여 토큰을 낭비하는 행위.
     - 권장: 영구적인 상태 기록은 `execution_notes.md` 등 파일에 맡기고, 메시지는 "직전 완료 사항", "현재 블로커", "다음 액션" 위주로 매우 간결하게 유지할 것.

  3. **코드 덩어리 전송 (Code Blob Transmission)**
     - 금지: 코드를 설명할 때, 수정하지 않은 부분까지 포함한 전체 코드를 채팅창에 렌더링하는 행위.
     - 권장: 설명이 필요할 때는 변경된 부분(Diff)만 간략히 보여주거나, 라인 넘버 링크(`file:///path#L10-L20`)를 활용해 참조하도록 유도할 것.

- **체크리스트**:
  - [ ] 전달하려는 메시지나 로그의 길이가 불필요하게 긴가? (장문인 경우 파일로 저장하고 경로만 전달했는가?)
  - [ ] 코드 전체를 무의미하게 출력하지 않고, 파일 링크 참조나 짧은 Diff만을 사용했는가?

```

### Skill: error-logging-best-practices
디렉토리 생성: `~/.agents/skills/error-logging-best-practices/`

#### 파일 생성: `~/.agents/skills/error-logging-best-practices/SKILL.md`
```markdown
---
name: error-logging-best-practices
description: 사소한 에러 반복 방지 및 로깅 누락을 방지하기 위한 마이너 안티패턴 예방 스킬입니다.
---

# Error and Logging Best Practices

- **목적**: 시스템 실행 중 반복되는 사소한 에러를 방지하고, 에러 원인을 추적할 수 있도록 체계적인 로깅 기준을 확립하여 디버깅 용이성을 확보합니다.
- **주요 안티패턴 (해결 대상)**:
    - **에러 묵살 (Silent Failures)**: 예외 발생 시 `try-except` 블록에 `pass`만 남기거나 에러의 상세 원인(Traceback)을 생략하고 넘어가는 행위.
    - **광범위한 예외 처리 (Broad Exception Catching)**: 구체적인 예외 상황을 구분하지 않고 `except Exception:`으로 묶어 처리하여 잠재적인 다른 버그를 숨기는 행위.
    - **컨텍스트 없는 로깅 (Contextless Logging)**: 에러 발생 시 단순 'Failed' 메시지만 남기고, 어떤 함수, 어떤 변수값, 어떤 상황에서 발생했는지 맥락을 기록하지 않는 행위.
- **행동 지침 (Best Practices)**:
    - **구체적 예외 처리**: `FileNotFoundError`, `KeyError` 등 구체적인 예외 타입을 명시하여 각각의 상황에 맞는 처리 로직을 구현합니다.
    - **상세 로그 기록**: 에러 발생 시 `logging` 모듈을 활용하거나 시스템 로거(`audit_logger.py`)를 통해 발생 위치(모듈, 함수명), 입력값, 에러 메시지(Traceback)를 함께 기록해야 합니다.
    - **재시도 제한(Retry Limit) 적용**: 네트워크 요청이나 외부 리소스 접근 실패 시 반복 재시도를 할 경우 무한 루프를 막기 위한 횟수 제한(Max Retries)을 반드시 두고, 이를 초과하면 명확히 실패를 보고합니다.
    - **의도적 에러 발생 장려**: 치명적인 에러이거나 복구 불가능한 상태라면 숨기지 말고, 상위 에이전트에 에러를 던져(raise) 문제를 즉시 드러나게 합니다.

```

### Skill: execution-best-practices
디렉토리 생성: `~/.agents/skills/execution-best-practices/`

#### 파일 생성: `~/.agents/skills/execution-best-practices/SKILL.md`
```markdown
---
name: execution-best-practices
description: 장기 실행(Long-running) 작업 및 실험 시 발생하는 블로킹, 체크포인트 누락 등의 안티패턴을 방지하기 위한 스킬입니다.
---

# Execution Best Practices (실행 및 워크플로우 안티패턴 방지)

- **목적**: 장시간 소요되는 실험, 시뮬레이션, 파라미터 튜닝 시 에이전트가 블로킹(무한 대기)되거나 중간 데이터가 유실되는 현상을 방지합니다.
- **주요 교정 대상 및 안티패턴 (Anti-patterns)**:
  1. **동기식 무한 대기 (Synchronous Blocking)**
     - 금지: 며칠 이상 소요되는 방대한 작업(예: ETA 149시간 이상의 실험)을 백그라운드로 보내지 않고 동기식(Synchronous)으로 단일 실행하여 에이전트 턴을 멈추게 하는 행위.
     - 권장: 장기 실행 작업은 반드시 `WaitMsBeforeAsync` 파라미터를 활용해 백그라운드 태스크로 전환하거나, `/schedule`, `/goal` 명령어를 추천/활용하여 비동기적으로 점검할 것.
  2. **체크포인트 누락 (Missing Checkpoints)**
     - 금지: 수백~수천 번의 루프를 도는 실험에서 중간 저장 장치 없이 스크립트 종료 시점에만 결과를 기록하도록 방치하는 행위.
     - 권장: 예상치 못한 세션 종료(OOM, 재부팅 등)에 대비하여 매 Iteration마다 로그 및 결과를 파일(CSV 등)에 실시간으로 Flush/Checkpointing 하여 작업을 이어서(Resume) 할 수 있도록 설계할 것.
  3. **순차 실행 자원 낭비 (Sequential Bottleneck)**
     - 금지: 서로 의존성이 없는 독립적인 실험/파라미터 스윕 시나리오를 단일 코어에서 순차 실행하여 극단적인 시간을 소모하는 행위.
     - 권장: 하드웨어 자원이 허용하는 한 `multiprocessing`, `joblib`를 사용한 스크립트 최적화나, 복수의 서브 에이전트를 통한 병렬 분산 실행 구조를 설계할 것.

```

### Skill: feedback-manager
디렉토리 생성: `~/.agents/skills/feedback-manager/`

#### 파일 생성: `~/.agents/skills/feedback-manager/SKILL.md`
```markdown
---
name: feedback-manager
description: Skill for autonomously extracting, recording, and managing user feedback for continuous learning.
---
# Feedback Manager Skill

- **목적**: 사용자와의 일상적인 대화나 에이전트의 실수에서 발생하는 피드백을 실시간으로 포착하여 자율 성장 파이프라인(Continuous Learning)에 태우는 역할을 명세합니다.

- **1. 대화 중 로그 쌓기 (Daytime Extraction)**:
  - 작업 수행 중 사용자가 행동을 교정해주거나, 불편함을 호소하거나, 에이전트가 환각(Hallucination)/오류를 범했을 경우, 메인 에이전트(CEO)는 즉시 백그라운드에서 `/home/imnyj/feedback_backlog.md` 파일에 해당 사안을 기록해야 합니다.
  - 기록 형식은 [문제 상황]과 [사용자가 원하는 올바른 행동 양식]을 명확히 분리하여 기술합니다.

- **2. 업그레이드 시 읽기 (Nightly Read & Execution)**:
  - 5시간 이상의 유휴 상태(Idle)가 감지되어 `schedule` 타이머가 발동하거나 사용자의 명시적인 지시가 있을 경우, `view_file` 도구를 사용해 누적된 백로그를 읽어 들입니다.
  - 이후 `skill-crafter` 스킬을 연계하여 백로그의 내용을 실질적인 시스템 룰(`GEMINI.md` 수정)이나 새로운 스킬 파일(`SKILL.md` 생성)로 승화시킵니다.

- **3. 업그레이드 후 초기화 (Reset Protocol)**:
  - 모든 시스템 업그레이드와 아티팩트(업그레이드 리포트) 작성이 완료되고 검증되면, 반드시 `/home/imnyj/feedback_backlog.md` 파일을 `write_to_file` 도구(Overwrite: true)를 사용하여 초기화해야 합니다.
  - 기존의 누적된 텍스트를 비우고, 시스템이 인식할 수 있는 파일 헤더(Header)만 남겨두어 다음 세션을 대비합니다.

- **4. 자동화 강제 룰 (Automation Automation)**:
  - 대화 종료 전 항상 `schedule` 도구를 호출하여 5시간 타이머를 리셋하고, 피드백 자동 업그레이드 사이클이 끊기지 않도록 강제합니다.

```

### Skill: file-organization
디렉토리 생성: `~/.agents/skills/file-organization/`

#### 파일 생성: `~/.agents/skills/file-organization/SKILL.md`
```markdown
---
name: file-organization
description: Skill for autonomously maintaining a clean workspace by categorically storing all miscellaneous and temporary files into an 'etc' directory.
---

# File Organization & Workspace Cleanliness Skill

## Purpose
This skill ensures that the agent keeps the project workspace clean and uncluttered. It prevents the root directory and main project folders from being polluted with temporary scripts, debug logs, intermediate datasets, and backup files.

## Core Directives

1. **The `etc/` Directory Mandate**
   Whenever generating a file that is not the final product, main codebase, or officially requested deliverable, you MUST route it to an `etc/` directory within the project's root folder.

2. **Categorical Sub-directories**
   Do not just dump files into `etc/`. You must categorize them using specific sub-directories. Examples include:
   - `etc/scripts/`: For temporary python or bash scripts written to process data, scrape the web, or perform one-off tasks.
   - `etc/logs/`: For execution outputs, stdout captures, and error logs.
   - `etc/temp/` or `etc/data/`: For intermediate data processing files, downloaded zips, or temporary scratchpads.
   - `etc/backups/`: For saving original copies of files before risky overwrites.

3. **Agent Accountability**
   - Before executing a `write_to_file` or running a python script that outputs a file, explicitly check your target path.
   - If the path is in the root directory (e.g., `workspace/paper1/test_script.py`), STOP. Redirect it to `workspace/paper1/etc/scripts/test_script.py`.

4. **Self-Correction**
   - If you notice that you or another agent have already cluttered the workspace with miscellaneous files, take a moment to move them into the appropriate `etc/` sub-directories using `mv` commands.

## When to use this skill
Activate this skill whenever you are about to create new files in a repository, write intermediate scripts, or when the user complains about workspace clutter. Always adhere to these rules implicitly during any workflow.

```

### Skill: improve-skills
디렉토리 생성: `~/.agents/skills/improve-skills/`

#### 파일 생성: `~/.agents/skills/improve-skills/SKILL.md`
```markdown
---
name: improve-skills
description: Meta-skill to autonomously extract repeated failure patterns and propose new or updated skills based on execution logs. Does NOT apply changes automatically.
---

# Skill: improve-skills

## Role
You are the Skill Crafter Meta-Agent. Your job is to read `logs/execution_notes.md` and identify any failure patterns or manual corrections that have occurred 3 or more times.

## Workflow
1. Read `/home/imnyj/logs/execution_notes.md`.
2. Extract any pattern repeated 3 or more times.
3. If found, draft a new skill or an update to an existing skill.
4. The draft MUST be saved in `/home/imnyj/proposals/<skill_name>_proposal.md`.
5. The draft MUST include:
   - The proposed skill instructions.
   - Test cases showing Before / After improvement (Example inputs and expected outputs).
6. Present the proposal to the user and request approval. Do NOT overwrite existing skills directly.

```

### Skill: multi-agent-manager
디렉토리 생성: `~/.agents/skills/multi-agent-manager/`

#### 파일 생성: `~/.agents/skills/multi-agent-manager/SKILL.md`
```markdown
---
name: multi-agent-manager
description: Skill for Team Leader agents to orchestrate subagents hierarchically.
---
# Multi-Agent Manager Skill

- **Delegation Protocol**: Never execute complex tasks manually (e.g., writing papers or writing code yourself). Break the problem down into distinct, atomic sub-tasks.
- **Worker Instantiation**: Use `define_subagent` and `invoke_subagent` to spawn specialized subordinate agents (e.g., `worker_writer`, `worker_critic`, `worker_coder`).
- **Context Injection**: Always ensure that subordinates are equipped with project-specific rules (from `.rules` or `.agents/skills`) in their system prompts.
- **Schema/Interface Pre-alignment**: Before spawning parallel worker agents to build interdependent modules, the manager MUST define and share a common Data Schema or Interface Definition (e.g., shared object models, data types) with all workers to prevent cross-agent object mismatch and integration errors.
- **Hierarchical Review**: Once a subordinate finishes, verify their work. If there are flaws (e.g., hallucinations, rule violations), reject the work and instruct them to fix it before reporting to the CEO.

```

### Skill: resource-cleanup-best-practices
디렉토리 생성: `~/.agents/skills/resource-cleanup-best-practices/`

#### 파일 생성: `~/.agents/skills/resource-cleanup-best-practices/SKILL.md`
```markdown
---
name: resource-cleanup-best-practices
description: 백그라운드 태스크(서버, 스크립트, 타이머 등) 실행 후 작업 종료 시 이를 정상적으로 종료(Kill)하지 않아 발생하는 리소스 누수 및 포트 충돌 안티패턴을 방지하기 위한 스킬.
---
# Resource Cleanup Best Practices

에이전트가 백그라운드 작업을 다룰 때 발생하는 대표적인 마이너 안티패턴인 '리소스 누수(Resource Leak)'를 방지하기 위한 가이드라인입니다.

## 1. 안티패턴: 방치된 백그라운드 프로세스 (Orphaned Background Tasks)
- **현상**: `run_command`로 로컬 개발 서버(예: `npm run dev`, `python -m http.server`)나 장기 실행 스크립트를 백그라운드 작업으로 실행한 뒤, 테스트가 끝나거나 에이전트 작업이 종료되었음에도 해당 태스크를 종료하지 않음.
- **문제점**: 
  - 다음 세션이나 다른 에이전트가 동일한 포트를 사용하려고 할 때 포트 충돌(Port in use) 에러 발생.
  - 불필요한 시스템 리소스 낭비.
  - 백그라운드 태스크가 계속해서 에이전트 인박스로 메시지를 보내어 작업 흐름을 방해함.

## 2. 해결 방안 및 베스트 프랙티스
- **작업 완료 후 명시적 종료**: `manage_task` 도구의 `kill` 액션을 사용하여 더 이상 필요하지 않은 태스크 ID를 반드시 종료(Kill)하십시오.
- **포트 충돌 확인**: 서버 실행 전 해당 포트가 사용 중인지 확인하고, 이전 작업의 잔재가 있다면 종료 후 다시 시도하십시오.
- **타이머/크론 정리**: `schedule` 도구를 통해 설정된 알람이나 반복 크론 잡(Cron Job)도 목적을 달성했다면 방치하지 말고 `manage_task`를 이용해 취소하십시오.
- **서브에이전트 정리**: 서브에이전트가 역할을 마쳤다면 불필요하게 대기 상태로 두지 말고 `manage_subagents` 도구를 이용해 정리하십시오.

```

### Skill: session-harness
디렉토리 생성: `~/.agents/skills/session-harness/`

#### 파일 생성: `~/.agents/skills/session-harness/SKILL.md`
```markdown
---
name: session-harness
description: Skill to automatically initialize workspace directories and orchestrate the multi-agent setup at the start of any new session.
---
# Session Harness Skill

- **목적**: 새로운 세션이 열릴 때마다 작업 환경을 자동으로 일관성 있게 세팅하고, Multi-Agent 워크플로우를 구동하기 위한 초기화 하네스(Harness) 역할을 수행합니다.
- **동작 방식**:
  1. **디렉토리 셋업**: 현재 작업 중인 프로젝트 이름을 파악하여 `/home/imnyj/Workspace/<Project_Name>` 디렉토리를 자동으로 확인하고 없으면 즉시 생성합니다.
  2. **루트 고정**: 이후 모든 작업 파일, 산출물은 해당 Workspace 경로 하위에만 저장되도록 강제합니다.
  3. **매니저 호출**: 단순 작업이 아니라면 즉시 `multi-agent-manager` 스킬을 활용하여 서브 에이전트들을 기동하고 태스크를 분할하는 하네스를 동작시킵니다.
- **적용 시점**: 이 스킬은 세션이 시작되거나 사용자가 프로젝트 진행을 요구할 때 절대 규칙(`GEMINI.md`)과 연계되어 가장 먼저 자동으로 활성화되어야 합니다.

## 12. Persistent Session Harness (자동 초기화 및 하네스 구동)
- **Rule:** 새로운 세션이 시작될 때마다 에이전트는 별도 지시가 없더라도 자동으로 프로젝트 경로를 파악하여 `/home/imnyj/Workspace/<Project_Name>` 디렉토리를 확인 및 생성하고, 해당 디렉토리를 작업 기준으로 삼아야 한다.
- **Rule:** 작업을 진행할 때, 단순 수행에 그치지 않고 `session-harness` 및 `multi-agent-manager` 스킬을 로드하여 하위 에이전트에게 태스크를 분배하고 관리하는 초기화 하네스(Initialization Harness)를 반드시 가동하여 체계적으로 작업을 수행할 것.

```

### Skill: skill-crafter
디렉토리 생성: `~/.agents/skills/skill-crafter/`

#### 파일 생성: `~/.agents/skills/skill-crafter/SKILL.md`
```markdown
---
name: skill-crafter
description: Skill for autonomously creating or updating other skills based on user feedback during nightly upgrades.
---
# Skill Crafter Skill

- **목적**: 5시간 대기 후 Nightly Upgrade(자체 시스템 업그레이드)를 수행할 때, `feedback_backlog.md`에 누적된 피드백을 분석하여 단순히 룰을 추가하는 것에 그치지 않고, 특정 역할이나 반복적인 워크플로우로 묶일 수 있는 사안이라면 이를 **독립적인 신규 스킬(Skill)로 창설하거나 기존 스킬을 업데이트**하는 역할을 수행합니다.
- **판단 기준**: 
    - 피드백 내용이 시스템 전체에 적용되는 절대 규칙이라면 `GEMINI.md`에 반영.
    - 특정 에이전트(예: writer, coder)의 행동 양식에 관한 것이라면 해당 스킬 업데이트 (`replace_file_content` 사용).
    - 완전히 새로운 워크플로우나 기능적 요구사항이라면 새로운 스킬 생성.
- **스킬 생성 및 저장 규격**:
    - **경로**: 신규 스킬은 반드시 `/home/imnyj/.agents/skills/<새로운-스킬-이름>/SKILL.md` 경로에 생성할 것.
    - **형식**: 파일 최상단에 반드시 YAML frontmatter(`name`, `description`)를 포함하고, 그 아래 마크다운 형식으로 구체적인 작업 지침(Instruction)을 기재할 것.
- **절차**:
    1. 피드백 분석 후 스킬화 가능성 평가.
    2. 생성할 스킬의 이름과 역할 명세 도출.
    3. `write_to_file` 또는 `replace_file_content` 도구를 활용하여 스킬 파일 물리적 작성.
    4. 업그레이드 리포트(Artifact)에 어떤 스킬이 생성/업데이트 되었는지 명시.

```

### Skill: skill-crafter
디렉토리 생성: `~/.agents/skills/skill-crafter/`

#### 파일 생성: `~/.agents/skills/skill-crafter/SKILL.md`
```markdown
---
name: skill-crafter
description: Skill for autonomously creating or updating other skills based on user feedback during nightly upgrades.
---
# Skill Crafter Skill

- **목적**: 5시간 대기 후 Nightly Upgrade(자체 시스템 업그레이드)를 수행할 때, `feedback_backlog.md`에 누적된 피드백을 분석하여 단순히 룰을 추가하는 것에 그치지 않고, 특정 역할이나 반복적인 워크플로우로 묶일 수 있는 사안이라면 이를 **독립적인 신규 스킬(Skill)로 창설하거나 기존 스킬을 업데이트**하는 역할을 수행합니다.
- **판단 기준**: 
    - 피드백 내용이 시스템 전체에 적용되는 절대 규칙이라면 `GEMINI.md`에 반영.
    - 특정 에이전트(예: writer, coder)의 행동 양식에 관한 것이라면 해당 스킬 업데이트 (`replace_file_content` 사용).
    - 완전히 새로운 워크플로우나 기능적 요구사항이라면 새로운 스킬 생성.
- **스킬 생성 및 저장 규격**:
    - **경로**: 신규 스킬은 반드시 `/home/imnyj/.agents/skills/<새로운-스킬-이름>/SKILL.md` 경로에 생성할 것.
    - **형식**: 파일 최상단에 반드시 YAML frontmatter(`name`, `description`)를 포함하고, 그 아래 마크다운 형식으로 구체적인 작업 지침(Instruction)을 기재할 것.
- **절차**:
    1. 피드백 분석 후 스킬화 가능성 평가.
    2. 생성할 스킬의 이름과 역할 명세 도출.
    3. `write_to_file` 또는 `replace_file_content` 도구를 활용하여 스킬 파일 물리적 작성.
    4. 업그레이드 리포트(Artifact)에 어떤 스킬이 생성/업데이트 되었는지 명시.
```

### Skill: tool-usage-best-practices
디렉토리 생성: `~/.agents/skills/tool-usage-best-practices/`

#### 파일 생성: `~/.agents/skills/tool-usage-best-practices/SKILL.md`
```markdown
---
name: tool-usage-best-practices
description: 에이전트의 효율적이고 안전한 도구 사용을 위한 베스트 프랙티스 및 안티패턴 방지 스킬입니다.
---
# Tool Usage Best Practices

- **목적**: 시스템에 제공된 다양한 도구들을 목적에 맞게 효율적으로 사용하며, 위험하거나 비효율적인 도구 사용(안티패턴)을 방지합니다.

- **안티패턴 및 예방 가이드라인**:
    1. **무분별한 파일 전체 덮어쓰기 (Overwriting Anti-pattern)**
        - 안티패턴: 파일의 일부만 수정해야 하는데 전체 내용을 새로 작성하여 덮어쓰거나 무거운 도구를 사용하는 현상.
        - 해결책: 가능한 한 `replace_file_content` 및 `multi_replace_file_content` 도구를 사용하여 필요한 부분만 정밀하게 수정합니다.
    2. **쉘 커맨드 오남용 (Bash Anti-pattern)**
        - 안티패턴: 파일 수정, 탐색 등의 작업에 `sed`, `awk`, `cat >` 등 임의의 bash 커맨드를 억지로 조합하여 사용하는 현상.
        - 해결책: 파일 수정에는 전용 코드 수정 도구를, 파일 읽기나 검색에는 `view_file`이나 `grep_search` 같은 전용 도구를 우선적으로 사용합니다. 전용 도구가 있는 작업은 쉘 커맨드에 의존하지 않습니다.
    3. **동일 실패 반복 (Infinite Loop Anti-pattern)**
        - 안티패턴: 도구 호출이 에러를 반환했음에도 불구하고, 파라미터나 접근 방식을 바꾸지 않고 동일한 호출을 맹목적으로 반복하는 현상.
        - 해결책: 도구 호출 실패 시, 에러 메시지를 꼼꼼히 분석하고 다른 접근 방식(예: 절대경로 확인, 다른 도구 사용, 사용법 재확인)을 시도해야 합니다.
    4. **동기식 블로킹 (Blocking Task Anti-pattern)**
        - 안티패턴: 실행에 오랜 시간이 걸리는 서버 기동, 크롤링, 빌드 작업 등을 백그라운드 처리가 아닌 동기적으로 실행하여 에이전트가 멈추는 현상.
        - 해결책: 장기 실행 명령은 적절한 백그라운드 태스크로 전환하고 `manage_task`를 통해 비동기적으로 상태를 관리합니다.

- **체크리스트**:
    - [ ] 내용이 많은 파일에서 한두 줄만 수정할 때 `multi_replace_file_content` 등 부분 수정 도구를 사용했는가?
    - [ ] `cat`으로 새 파일을 만들거나 `grep`을 쉘에서 직접 쓰는 대신 제공된 API(`write_to_file`, `grep_search`)를 사용했는가?
    - [ ] 이전에 실패했던 도구 인자를 아무런 수정 없이 그대로 다시 호출하지 않았는가?

```

### Skill: dependency-management-best-practices
디렉토리 생성: `~/.agents/skills/dependency-management-best-practices/`

#### 파일 생성: `~/.agents/skills/dependency-management-best-practices/SKILL.md`
```markdown
---
name: dependency-management-best-practices
description: 의존성 패키지 설치 시 버전 고정 누락 및 의존성 파일 업데이트 누락을 방지하기 위한 베스트 프랙티스 및 안티패턴 방지 스킬입니다.
---
# Dependency Management Best Practices

에이전트가 새로운 라이브러리나 패키지를 설치할 때 자주 발생하는 안티패턴(환경 재현성 훼손)을 방지하기 위한 지침입니다.

## 🚫 안티패턴 (절대 금지)
- `pip install <package>`, `npm install <package>` 등의 명령어를 사용하여 버전을 명시하지 않고 최신 버전을 맹목적으로 설치하는 행위.
- 패키지를 임의로 설치한 후 프로젝트의 의존성 관리 파일(`requirements.txt`, `package.json` 등)을 업데이트하지 않아 다른 에이전트가 환경을 재현할 수 없게 만드는 행위.
- 시스템 전역(global) 공간에 패키지를 설치하여 다른 프로젝트 환경과 충돌을 유발하는 행위.

## ✅ 베스트 프랙티스 (권장 사항)
- **가상 환경 사용**: 패키지 설치 전 반드시 로컬 가상 환경이 활성화되어 있는지 확인하고 해당 환경 내에만 설치하십시오.
- **버전 명시 (Pinning)**: 호환성 문제가 발생하지 않도록, 가급적 명확한 버전을 고정하여 설치하십시오. (예: `pip install numpy==1.24.3`)
- **의존성 기록 유지**: 성공적으로 패키지를 설치했다면, 변경된 환경을 즉시 `requirements.txt`에 기록(`pip freeze > requirements.txt` 등)하여 동기화하십시오.
- **관리 스크립트 분리**: 복잡한 환경 설정이 필요한 경우, 일회성 설치 명령어를 남발하지 말고 `etc/scripts/setup_env.sh` 와 같이 재사용 가능한 스크립트로 작성하십시오.
```

### Skill: long-running-simulation
디렉토리 생성: `~/.agents/skills/long-running-simulation/`

#### 파일 생성: `~/.agents/skills/long-running-simulation/SKILL.md`
```markdown
---
name: long-running-simulation
description: 장기 실행 시뮬레이션/훈련 작업 시 프로세스 내결함성, 토큰 절약, 알림 빈도 관리를 위한 베스트 프랙티스 스킬입니다.
---
# Long-Running Simulation Skill

## 목적
수 시간~수 일이 소요되는 대규모 시뮬레이션, 모델 훈련, 데이터 수집 파이프라인을 관리할 때 발생하는 안티패턴을 방지합니다.

## 1. 프로세스 내결함성 (Fault Tolerance)

### 필수 원칙
- **체크포인트 기반 재개(Resume)**: 장기 실행 스크립트는 반드시 중간 결과를 주기적으로 저장(에피소드별, 배치별 등)하고, 재시작 시 마지막 체크포인트부터 이어서 실행할 수 있도록 구현해야 합니다.
- **자동 재시작 래퍼**: `auto_train.sh` 패턴처럼, 스크립트가 비정상 종료되면 자동으로 재시작하는 Bash 래퍼를 항상 함께 제공합니다.
- **`setsid` 분리 실행**: `nohup`만으로는 에이전트 세션 종료 시 프로세스가 함께 죽을 수 있습니다. 반드시 `setsid nohup ... < /dev/null &` 패턴으로 완전히 독립된 세션에서 실행합니다.

### 안티패턴
| ❌ 안티패턴 | ✅ 올바른 방식 |
|---|---|
| `nohup python train.py &` | `setsid nohup bash auto_train.sh > log 2>&1 < /dev/null &` |
| 에피소드 0부터 재시작 | 체크포인트 CSV/가중치에서 마지막 에피소드 읽어 이어서 실행 |
| 에이전트가 직접 훈련 프로세스를 모니터링 | 독립 프로세스로 실행, 필요 시에만 로그 확인 |

## 2. 토큰 절약 (Token Conservation)

### 필수 원칙
- **서브에이전트 최소화**: 장기 훈련이 백그라운드에서 자율적으로 돌아가는 동안, 불필요한 서브에이전트(teamwork_preview 등)를 유지하지 않습니다.
- **모니터링은 스크립트로**: `check_progress.sh` 같은 경량 Bash 스크립트를 제공하여, 사용자가 터미널에서 직접 진행 상황을 확인할 수 있도록 합니다.
- **에이전트 개입 최소화**: 프로세스가 안정적으로 가동 중이면, 에이전트는 사용자가 요청할 때만 상태를 확인합니다.

### 안티패턴
| ❌ 안티패턴 | ✅ 올바른 방식 |
|---|---|
| 서브에이전트가 8분마다 진행 상황 보고 | 사용자가 지정한 시각에만 보고 (예: 6시, 12시) |
| 쿼터 제한 에러에도 서브에이전트 계속 재시도 | 쿼터 제한 시 즉시 중단, 프로세스는 독립 실행 |
| 훈련 완료까지 에이전트가 계속 폴링 | 완료 감지를 스크립트 내 종료 로그에 위임 |

## 3. 알림 빈도 관리 (Notification Frequency)

### 필수 원칙
- **사용자 지정 빈도 엄수**: 사용자가 보고 빈도를 지정하면(예: "6시와 12시에만"), 에이전트와 모든 서브에이전트는 해당 빈도를 절대적으로 준수합니다.
- **서브에이전트 자율 크론 금지**: 서브에이전트가 자체적으로 크론이나 타이머를 추가 설정하여 상위 에이전트에 알림을 보내는 행위를 금지합니다. 보고 빈도는 상위 에이전트(또는 사용자)만 결정합니다.
- **이벤트 기반 보고**: 정기 보고 외에는 Milestone 달성, 치명적 에러, 최종 완료 등 중대 이벤트에서만 알림을 보냅니다.

## 4. 병렬 실행 안정성

### 필수 원칙
- **동시 프로세스 수 제한**: `mp.Pool(processes=N)` 사용 시 N은 가용 GPU 수 이하로 제한합니다.
- **중복 실행 방지**: 동일 스크립트가 여러 인스턴스로 실행되지 않도록, 실행 전 `pgrep` 등으로 기존 프로세스 존재 여부를 확인합니다.
- **파일 쓰기 충돌 방지**: 여러 프로세스가 같은 CSV/가중치 파일에 동시 접근할 경우, 파일 Lock 또는 프로세스 풀 직렬화로 보호합니다.
```

## 3. 원문에 포함된 `skill-crafter` 중복 규칙

원본 요청서에는 `skill-crafter`가 두 차례 정의되어 있다. 이는 원문 보존을 위해 누락하지 않아야 한다. 구현 시 동일한 기능을 중복 설치하여 충돌시키기보다는 하나를 canonical implementation으로 사용하고, 두 번째 정의도 원문 요구사항으로 검증 항목에 포함한다.

## 4. 로컬 업그레이드 완료 검증

구현 Agent는 다음을 모두 확인한 뒤에만 완료로 보고한다.

- [ ] 4-GPU 하드웨어 인식 규칙이 실제 Agent 운영 규칙에 반영됨
- [ ] `/home/imnyj/Workspace/<Project_Name>` 경로 규칙 반영
- [ ] lock manager 규칙 반영
- [ ] audit logger 규칙 반영
- [ ] feedback backlog 규칙 반영
- [ ] execution notes 규칙 반영
- [ ] session harness 반영
- [ ] multi-agent manager 반영
- [ ] file organization / `etc/` 규칙 반영
- [ ] 장기 실행 및 checkpoint/resume 규칙 반영
- [ ] 4-GPU 병렬 실행 및 중복 프로세스 방지 규칙 반영
- [ ] dependency/config/tool/error/resource cleanup 규칙 반영
- [ ] 지원되지 않는 플랫폼 기능을 허위로 구현하지 않음
- [ ] 실제 파일과 디렉토리가 존재하는지 절대 경로로 재검증함
- [ ] 최종적으로 누락 항목이 없는지 원문과 대조함

## 5. 무료 Token Subagent / Free-Token MCP 연동 규칙

### 5.1 목적

이 워크스테이션에는 교내에서 제공받은 무료 토큰을 사용하는 별도의 AI Agent가 존재한다. 이 Agent는 일반 유료 Agent와 구분되는 **무료 Token Subagent**로 운용한다.

기존 환경에서는 해당 무료 Agent의 API KEY가 `.config/config.yml`에 설정되어 있었으며, 이를 기반으로 다음 구현 파일이 만들어졌다.

```text
Workspace/NYJ_Project/free_token_mcp.py
```

이 구현을 기존 로컬 Agent 운영 체계에 편입하여, **각 세션에서 관련 Skill을 활용할 때 무료 Token Subagent를 사용할 수 있는 구조**를 추가한다.

### 5.2 핵심 규칙

- `Workspace/NYJ_Project/free_token_mcp.py`를 무료 Token Subagent 연동의 기존 구현으로 간주한다.
- 해당 파일을 임의로 재작성하거나 중복 구현하지 말고, 먼저 실제 파일의 내용과 인터페이스를 검사한다.
- API KEY의 실제 값은 출력, 로그 기록, 커밋, 보고서, Subagent 메시지에 절대로 노출하지 않는다.
- API KEY는 기존 `.config/config.yml` 설정을 우선 사용한다.
- 설정 파일의 실제 위치와 키 이름은 추측하지 말고 워크스테이션에서 직접 확인한다.
- 무료 Token Subagent가 실제로 호출 가능한지 최소 1회 실행 검증한다.
- 무료 Token Subagent를 사용할 수 없는 경우 존재한다고 가정하여 성공으로 보고하지 않는다.
- 무료 Token Subagent의 호출 실패와 일반 Agent의 실패를 구분하여 기록한다.

### 5.3 Session Skill 연동

각 세션이 시작될 때 다음을 확인한다.

1. 무료 Token Subagent 연동 Skill이 존재하는지 확인한다.
2. `Workspace/NYJ_Project/free_token_mcp.py`가 존재하는지 확인한다.
3. 필요한 설정 파일이 존재하는지 확인한다.
4. API KEY가 유효하게 설정되어 있는지 **값을 노출하지 않는 방식으로** 확인한다.
5. MCP/Agent 연결이 실제로 초기화 가능한지 확인한다.
6. 세션에서 무료 Token Subagent를 사용할 수 있는 상태를 Skill을 통해 제공한다.

무료 Token Subagent를 사용할 필요가 있는 작업에서는 해당 Skill을 호출하여 Subagent를 생성/호출한다.

### 5.4 무료 Token Subagent의 사용 우선순위

무료 Token Subagent는 다음과 같은 작업에 우선적으로 사용할 수 있다.

- 독립적으로 검증 가능한 조사/탐색 작업
- 코드베이스의 특정 부분에 대한 별도 분석
- 반복적인 정보 추출
- 보조적인 코드 리뷰
- 독립적인 검증
- 장시간 또는 병렬로 처리할 수 있는 하위 작업
- 상위 Agent의 주 컨텍스트를 불필요하게 소모하는 보조 작업

단, 무료 토큰의 한도와 실제 Agent 성능을 고려하여 **모든 작업을 무조건 무료 Subagent에 위임하지 않는다.** 작업의 중요도, 복잡도, 실패 비용 및 필요한 능력을 기준으로 사용 여부를 결정한다.

### 5.5 기존 Subagent 시스템과의 관계

무료 Token Subagent는 기존 Subagent 계층을 대체하지 않는다.

```text
                    Main Agent
                        │
                 Task / Skill Router
                        │
          ┌─────────────┴─────────────┐
          │                           │
   일반/고성능 Subagent        Free Token Subagent
                                      │
                           free_token_mcp.py
                                      │
                              교내 무료 Token
```

- 기존 `invoke_subagent` 등 플랫폼이 지원하는 Subagent 기능이 있으면 그것과 연동한다.
- 무료 Token Subagent는 그중 하나의 실행 자원으로 취급한다.
- 플랫폼에 따라 Subagent 생성 방식이 다르면 현재 플랫폼에서 실제 지원하는 방법으로 Adapter를 구성한다.
- 존재하지 않는 MCP/Subagent API를 추측하여 구현하지 않는다.

### 5.6 Skill 정의 요구사항

무료 Token Subagent를 사용하기 위한 별도의 Skill을 제공한다. 권장 이름은 다음과 같다.

```text
free-token-subagent
```

Skill은 최소한 다음 정보를 관리해야 한다.

- 무료 Token Subagent의 목적
- `free_token_mcp.py`의 위치
- 설정 파일의 위치
- 인증 정보의 안전한 로딩 방법
- 호출 방법
- 입력/출력 인터페이스
- 오류 처리 방법
- 사용 가능한 경우와 사용하지 않아야 하는 경우
- 호출 결과의 검증 방법
- 상위 Agent로 결과를 전달하는 방법

Skill에는 API KEY 자체를 하드코딩하지 않는다.

### 5.7 세션별 사용 가능성 보장

사용자가 새로운 세션에서 작업을 시작했을 때도 무료 Token Subagent 기능이 사라지지 않도록 한다.

즉, 무료 Token Subagent는 특정 대화의 일회성 설정이 아니라 **로컬 워크스테이션의 지속적인 Agent Skill/Infrastructure로 등록**되어야 한다.

세션 초기화 시 다음 관계를 유지한다.

```text
Session Start
    ↓
Local Environment Check
    ↓
Free Token Skill Discovery
    ↓
free_token_mcp.py Validation
    ↓
Credential Configuration Check
    ↓
Free Token Subagent Available
    ↓
Task-specific Skill이 필요 시 호출
```

### 5.8 무료 Token 사용량 및 장애 처리

무료 토큰은 제한된 자원이므로 다음을 기록한다.

- 호출 횟수
- 성공/실패
- 실패 원인
- 가능한 경우 사용량 정보
- 작업 ID 또는 Session ID와의 연계
- 무료 Token Subagent가 수행한 하위 작업

단, 인증 정보나 민감한 요청/응답 내용은 로그에 그대로 저장하지 않는다.

무료 Token 한도 초과, 인증 실패, MCP 연결 실패, Agent 오류 등이 발생하면 다음 순서로 처리한다.

```text
Free Token Subagent 실패
        ↓
원인 분류
        ↓
재시도 가능 여부 판단
        ↓
안전한 재시도
        ↓
그래도 실패
        ↓
Main Agent 또는 다른 Subagent로 Escalation
```

무료 Token Subagent 실패 때문에 전체 작업을 성공으로 간주해서는 안 된다.

### 5.9 파일 및 경로 검증

업그레이드 구현 Agent는 다음 파일을 실제 워크스테이션에서 확인해야 한다.

```text
.config/config.yml
Workspace/NYJ_Project/free_token_mcp.py
```

실제 절대 경로가 확인되면 그 절대 경로를 기준으로 동작하도록 한다.

특히 다음을 추측하지 않는다.

- API KEY의 정확한 YAML key 이름
- MCP 서버의 내부 함수명
- Subagent 생성 API
- 서버 실행 명령
- 포트 번호
- 프로토콜 세부사항
- 응답 JSON 구조

이 정보는 실제 구현 파일과 설정 파일을 읽고, 필요하면 최소 실행 테스트를 통해 확인한다.

### 5.10 보안 규칙

- `.config/config.yml`의 API KEY 값을 사용자에게 출력하지 않는다.
- API KEY를 `CLAUDE.md`, Skill 문서, 소스 코드, 로그, Git 저장소에 복사하지 않는다.
- `free_token_mcp.py`가 인증 정보를 출력하도록 되어 있다면 먼저 해당 출력 경로를 수정하거나 마스킹한다.
- 디버그 로그에서도 API KEY 전체 또는 일부를 노출하지 않는다.
- 오류 메시지에 credential이 포함되는지 확인한다.
- Git 상태를 확인하여 credential 파일이 추적되지 않는지 확인한다.

### 5.11 구현 완료 기준

다음 조건을 모두 만족해야 무료 Token Subagent 연동을 완료한 것으로 본다.

- [ ] `Workspace/NYJ_Project/free_token_mcp.py`의 실제 존재 여부 확인
- [ ] `.config/config.yml`의 실제 설정 존재 여부 확인
- [ ] API KEY 값 자체를 노출하지 않고 설정 유효성 확인
- [ ] 무료 Token MCP의 실제 인터페이스 확인
- [ ] 무료 Token Subagent용 Skill 생성/등록
- [ ] 새로운 세션에서도 Skill을 발견할 수 있음
- [ ] Skill을 통해 무료 Token Subagent 호출 가능
- [ ] 실제 최소 호출 테스트 성공
- [ ] 호출 실패 시 오류가 정상적으로 상위 Agent에 전달됨
- [ ] 무료 Token 사용량/상태를 추적할 수 있음
- [ ] 인증 정보가 로그와 코드에 노출되지 않음
- [ ] 기존 Subagent 시스템과 충돌하지 않음
- [ ] 기존 `/goal` 및 Task/Skill 체계를 덮어쓰지 않음
- [ ] 실제 지원되는 플랫폼 기능만 사용함
- [ ] 구현 후 재검증하여 세션 간 지속성이 확인됨

## 6. 로컬 업그레이드 완료 검증 항목 추가

- [ ] 교내 무료 Token을 사용하는 Subagent가 일반 Subagent와 별도 자원으로 인식됨
- [ ] `Workspace/NYJ_Project/free_token_mcp.py`가 기존 구현으로 연결됨
- [ ] `.config/config.yml`의 기존 API KEY 설정을 재사용함
- [ ] 각 세션에서 `free-token-subagent` Skill을 발견할 수 있음
- [ ] 논문/연구/코딩 등 특정 Skill에서 필요할 경우 무료 Subagent를 사용할 수 있음
- [ ] 무료 Subagent 사용 여부는 작업 특성에 따라 결정됨
- [ ] 무료 Token 실패 시 다른 Agent로 안전하게 전환할 수 있음
- [ ] 인증 정보가 어떠한 Agent 결과/로그에도 노출되지 않음
