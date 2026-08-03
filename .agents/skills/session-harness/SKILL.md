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
