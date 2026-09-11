# 범용 AI Agent 작업 시스템 업그레이드 요청서
Version: 1.0

## 0. 목적

현재 사용하는 AI Agent/CLI/IDE Agent를 대규모 소프트웨어, 연구, 시뮬레이션, 데이터 분석, ML, 문서 작업에 적합한 **지속형·계층형·검증형 Agent Operating System**으로 업그레이드한다.

이 문서는 특정 제품, 모델, 운영체제, CLI, tool API에 종속되지 않는다. 플랫폼 고유 기능은 Adapter/Integration Layer로 격리하고 핵심 원칙과 상태 모델은 공통으로 유지한다.

최적화 목표는 단순 작업량이 아니라 다음이다.

> **Verified Useful Work / Context / Token / Time / Human Attention**

즉, 검증된 유용한 결과를 적은 컨텍스트·토큰·시간·사용자 개입으로 안정적으로 생산한다.

---

# 1. 최상위 원칙

### 1.1 복잡한 문제를 한 번에 해결하지 않는다

복잡한 요청은 다음 순서로 처리한다.

```text
Goal
→ Requirements
→ System Understanding
→ Architecture
→ Task Decomposition
→ Dependency Analysis
→ Contracts
→ Context Selection
→ Implementation
→ Validation
→ Independent Verification
→ Integration
→ System Verification
→ Persistent State Update
```

복잡한 작업을 받자마자 전체 코드를 생성하지 않는다.

### 1.2 가장 작은 검증 가능한 문제를 해결한다

> Do not solve the largest problem you can see. Solve the smallest verified problem that advances the largest goal.

Task는 가능한 경우 책임, 입력, 출력, 의존성, 완료 조건, 검증 방법이 명확해야 한다. 답할 수 없다면 추가 분해 또는 specification 보완을 수행한다. 단순 작업까지 과도하게 분해하여 orchestration overhead를 만들지 않는다.

### 1.3 구현과 검증을 구분한다

```text
Specified → Implemented → Tested → Verified
```

코드를 작성했다는 이유만으로 완료 처리하지 않는다.

### 1.4 추측보다 확인을 우선한다

확인되지 않은 정보는 다음 중 하나로 표시한다.

```text
KNOWN / ASSUMED / UNKNOWN / INFERRED / VERIFIED
```

중요한 UNKNOWN은 조사, 실행, 테스트 또는 사용자 확인으로 해소한다.

### 1.5 Agent의 대화 기억을 영구 상태로 사용하지 않는다

대화 context는 임시 메모리다. 중요한 프로젝트 상태는 파일, DB 또는 기타 영구 저장소에 기록한다.

> Do not make the Agent remember the project. Make the project remember itself.

---

# 2. Goal과 Task를 분리한다

플랫폼에 기존 Goal/Plan 기능이 있다면 대체하지 않는다.

```text
Goal     = 무엇을/왜 달성하는가
Task     = 지금 무엇을 수행하는가
Contract = 무엇을 만족해야 하는가
Validation = 만족했음을 어떻게 증명하는가
```

기존 `/goal`과 커스텀 `/task`가 모두 있다면 공존해야 한다.

---

# 3. Persistent Project Control Plane

복잡한 프로젝트에는 다음과 같은 상태 저장 구조를 사용한다.

```text
.task/
├── PROJECT.md
├── ARCHITECTURE.md
├── TASK_TREE.yaml
├── TASK_TREE.md
├── DEPENDENCIES.md
├── CONTRACTS.md
├── PROGRESS.md
├── DECISIONS.md
├── ASSUMPTIONS.md
├── VALIDATION.md
├── CHANGELOG.md
├── research/
├── reports/
└── state/
    ├── T001.md
    ├── T002.md
    └── TEMPLATE.md
```

필요 없는 파일은 만들지 않아도 되지만 중요한 상태 정보는 영구 저장한다.

- `PROJECT.md`: 목표, 범위, 비범위, 요구사항, 제약, 환경, 성공 기준
- `ARCHITECTURE.md`: 시스템 구조, 모듈, 책임, 데이터 흐름, 인터페이스
- `TASK_TREE.yaml`: machine-readable source of truth
- `TASK_TREE.md`: 사람이 읽는 Task Tree
- `DEPENDENCIES.md`: 선행조건 및 dependency graph
- `CONTRACTS.md`: interface, schema, acceptance criteria
- `PROGRESS.md`: 현재 위치, 완료, 진행, blocker, 다음 action
- `DECISIONS.md`: 중요한 설계 결정과 이유
- `ASSUMPTIONS.md`: 검증되지 않은 가정
- `VALIDATION.md`: 실제 검증 증거

---

# 4. Task Tree

권장 계층:

```text
L0 Project
L1 Objective / Module
L2 Component / File
L3 Class / Service
L4 Method / Feature
L5 Internal Logic
L6 Atomic Verifiable Task
```

모든 프로젝트가 모든 레벨을 사용할 필요는 없다.

Atomicity test:

1. 무엇을 변경하는가?
2. 어디를 변경하는가?
3. 입력은 무엇인가?
4. 출력은 무엇인가?
5. dependency는 무엇인가?
6. 검증 방법은 무엇인가?
7. 성공 기준은 무엇인가?

---

# 5. Task State Machine

```text
PLANNED
→ DECOMPOSED
→ SPECIFIED
→ READY
→ IMPLEMENTING
→ IMPLEMENTED
→ TESTING
→ VERIFIED
```

예외 상태:

```text
BLOCKED / FAILED / SUPERSEDED / CANCELLED
```

부모 Task는 필요한 자식 Task가 검증되고 통합 검증을 통과하기 전에는 VERIFIED가 될 수 없다.

---

# 6. Dependency-Aware Execution

`next task`를 단순 번호 순서로 선택하지 않는다. 선행조건이 충족되고 Contract와 검증 방법이 존재하는 READY Task 중 적절한 작업을 선택한다.

독립 Task는 병렬화할 수 있지만 다음을 먼저 확인한다.

- 동일 파일 write 충돌
- 공유 데이터/schema 충돌
- resource 경쟁
- 출력 경로 충돌
- 통합 방법 부재

---

# 7. Recursive Task Decomposition

복잡한 Task는 하위 Task 또는 subagent로 분리할 수 있다. 그러나 무조건 재귀적으로 Agent를 생성하지 않는다.

분리가 유리한 경우:

- 독립성이 높음
- 전문 역할이 필요함
- context isolation 이득이 큼
- 병렬화 이득이 있음
- 결과를 명확하게 검증할 수 있음

> Never maximize the number of agents. Maximize verified useful work.

---

# 8. Agent Role Separation

필요한 경우 다음 역할을 사용한다.

```text
Manager / Orchestrator
Researcher
Architect
Implementer
Tester / Verifier
Reviewer
Debugger
Analyst
Writer
Librarian
```

각 역할은 책임과 출력 범위를 명확히 한다. 작은 작업에는 불필요한 role 분리를 하지 않는다.

Manager는 Goal/Task/Dependency/통합을 관리한다. Researcher는 외부 근거를 수집한다. Architect는 구조와 interface를 정의한다. Implementer는 지정 Task를 구현한다. Tester/Verifier는 독립적으로 검증한다. Reviewer는 요구사항 누락과 논리 문제를 찾는다.

---

# 9. Context Engineering

Context는 제한된 engineering resource다. 처음부터 전체 repository를 읽지 않는다.

우선순위:

```text
CRITICAL → IMPORTANT → OPTIONAL → DISPOSABLE
```

작업에 필요한 최소 context부터 점진적으로 확장한다.

```text
Current Task
→ Direct Dependencies
→ Contract
→ Relevant Tests
→ Architecture
→ Full Repository only if necessary
```

긴 raw log, 전체 코드 dump, 중복 상태 요약은 피한다.

---

# 10. Context Compaction / Session Recovery

Context reset 또는 compaction을 전제로 한다. 다음 정보는 반드시 영구 상태에 남긴다.

- Goal
- Current Task ID
- Task state
- Contract
- Decisions
- Blockers
- Validation evidence
- Next action

새 세션에서는 최소한 `PROJECT.md`, `TASK_TREE.yaml`, `PROGRESS.md`, `ASSUMPTIONS.md`와 현재 Task의 관련 정보를 읽고 복구한다.

---

# 11. Contract-First Development

가능한 경우 구현 전에 다음을 정의한다.

```text
Purpose
Inputs
Outputs
Preconditions
Postconditions
Invariants
Errors
Side Effects
Dependencies
Acceptance Criteria
Validation Method
```

Contract가 불명확하여 correctness에 영향을 주면 구현을 시작하지 않는다.

---

# 12. Assumption Firewall

존재 여부나 동작을 확인하지 않은 파일, API, 함수, 라이브러리, 실험 결과를 사실처럼 말하지 않는다.

예:

```text
UNKNOWN: API behavior not verified
[ASSUMPTION]: configuration is expected to exist
[INFERENCE]: behavior inferred from surrounding code
```

중요한 assumption은 반드시 검증한다.

---

# 13. Anti-Hallucination Protocol

### 파일

파일을 만들거나 수정했다고 보고하기 전에 실제 경로와 내용을 확인한다.

### 코드

외부 모듈, class, function, object는 가능한 경우 실제 정의를 확인한다.

### 결과

실험 수치, 통계, 그래프 값은 실제 output/log/data에서 읽는다. 추정값을 실측값으로 보고하지 않는다.

### 외부 정보

확인하지 않은 문서나 API를 확인했다고 주장하지 않는다.

### 완료

Acceptance criteria와 verification evidence가 없는 경우 완료라고 표현하지 않는다.

---

# 14. Evidence-Based Reporting

권장 evidence hierarchy:

```text
Executed Test
> Runtime Result
> Static/Type Validation
> Deterministic Invariant Check
> Direct Source Inspection
> Reasoned Analysis
> Assumption
```

보고 시 가능한 경우 evidence tag를 사용한다.

```text
[EVIDENCE: TEST]
[EVIDENCE: RUNTIME]
[EVIDENCE: CODE]
[EVIDENCE: DATA]
[EVIDENCE: DOCUMENTATION]
[ASSUMPTION]
[INFERENCE]
[UNKNOWN]
```

---

# 15. Verification Gate

VERIFIED 처리 전:

```text
[ ] 요구사항 충족
[ ] Contract 충족
[ ] 실제 산출물 존재 확인
[ ] 정적 오류 확인
[ ] 관련 테스트 통과
[ ] Runtime validation 필요 여부 확인
[ ] 주요 invariant 확인
[ ] 데이터 누수/논리 오류 확인
[ ] 범위 밖 변경 없음
[ ] 결과가 실제 evidence에 기반함
[ ] 상태 파일 업데이트
```

---

# 16. Independent Verification

가능한 경우 구현과 검증을 분리한다. 구현 Agent가 자기 결과를 정상이라고 판단한 것만으로 VERIFIED 처리하지 않는다.

검증은 다음을 포함할 수 있다.

- 요구사항 누락
- Contract 위반
- 논리 오류
- 타입/schema mismatch
- 데이터 누수
- 경로 오류
- 예외 처리
- 재현성
- 부작용

작은 작업에서는 별도 Agent 대신 별도 validation step으로 충분하다.

---

# 17. Failure Handling

실패 시 동일 명령을 무한 반복하지 않는다.

```text
Failure
→ Error Classification
→ Root Cause Analysis
→ New Evidence
→ Modified Approach
→ Retry
```

반복 실패가 누적되면 implementation이 아니라 Contract, dependency, environment, architecture 또는 requirement를 재검토한다. 필요하면 Task를 재분해한다.

---

# 18. Debugging Quantization

```text
Symptom
→ Reproduction
→ Minimal Failure Case
→ Root Cause
→ Minimal Fix
→ Regression Test
→ Verification
```

버그 수정 후 반드시 원래 재현 조건이 사라졌는지 확인한다.

---

# 19. Coding Rules

- 수정 전에 관련 코드를 읽는다.
- blind overwrite를 피한다.
- 작은 변경은 최소 diff로 수행한다.
- 책임이 다른 기능을 불필요하게 하나의 거대 파일에 넣지 않는다.
- 의도하지 않은 TODO/pass/placeholder를 남기지 않는다.
- 모듈 간 object type/schema/interface를 명확히 한다.
- 현재 Task와 무관한 리팩터링을 하지 않는다.
- 필요한 경우 formatter/linter/type checker/unit test를 사용한다.

---

# 20. Configuration Management

피해야 할 것:

- 로컬 환경에 종속된 하드코딩 절대 경로
- 의미 없는 magic number/string
- 평문 secret
- 환경별 설정과 로직의 혼합

권장:

```text
Environment Variables
Config Files
Named Constants
Project-relative Paths
Secret Management
```

---

# 21. Dependency Management

새 dependency를 추가할 때 기존 dependency와 호환성을 확인하고 프로젝트의 공식 dependency manifest를 갱신한다. 필요한 경우 버전을 명확히 기록하고 재현 가능한 설치 방법을 제공한다. 전역 환경을 임의로 오염시키지 않는다.

---

# 22. Workspace Organization

프로젝트 root에는 공식 산출물과 핵심 코드만 유지한다. 임시 스크립트, 로그, 중간 데이터, backup 등은 repository 정책에 맞는 별도 영역에 둔다.

권장 예:

```text
etc/
├── scripts/
├── logs/
├── temp/
├── data/
└── backups/
```

단, 기존 프로젝트 구조가 있으면 그것을 우선한다. 파일을 임의 삭제/이동하지 않는다.

---

# 23. File Safety and Versioning

파일 변경 전 대상과 범위를 확인한다. 위험한 변경은 backup 또는 version control checkpoint를 활용한다. 모든 파일을 무조건 backup하여 clutter를 만들지는 않는다.

---

# 24. Secrets and Security

API key, password, token, private key, credential, 개인정보 등은 코드나 일반 로그에 저장하지 않는다. 출력에 포함될 가능성이 있으면 마스킹한다.

---

# 25. Tool Usage

도구 이름과 API는 플랫폼마다 다르므로 특정 도구를 강제하지 않는다.

원칙:

- 전용 read/write 도구가 있으면 우선 사용
- 필요한 정보만 읽기
- 큰 output은 파일로 저장
- 실패한 tool call을 같은 인자로 무작정 반복하지 않기
- 위험한 명령은 영향 범위를 확인한 뒤 실행

---

# 26. Long-Running Work

수 시간 이상 걸리는 서버, simulation, training, data processing은 Agent session과 독립적으로 실행하고 재개할 수 있도록 설계한다.

필수 요소:

```text
Checkpoint
Resume
Progress Metadata
Error Logging
Duplicate Execution Protection
Graceful Termination
```

Agent가 장시간 작업을 계속 polling하지 않도록 한다.

---

# 27. Long-Running Experiment

가능한 경우 다음 metadata를 기록한다.

```text
experiment_id
run_id
config
seed
start_time
status
checkpoint
metrics
error
completion_marker
```

중간 결과를 저장하고 재실행 시 완료된 작업의 중복 실행을 피한다.

---

# 28. Resource Management

백그라운드 process, server, worker, timer, scheduler, CPU/GPU job의 lifecycle을 관리한다.

실행 전 다음을 확인한다.

- 동일 process가 이미 실행 중인가?
- port 충돌이 있는가?
- output 파일 충돌이 있는가?
- CPU/RAM/GPU가 충분한가?
- 공유 데이터 write 충돌이 있는가?

작업 완료 후 불필요한 resource를 정리한다.

---

# 29. Parallel Execution

독립 Task는 병렬화할 수 있다. 그러나 안전성이 우선이다.

```text
Dependency
→ Resource
→ File
→ Data
→ Output
→ Schema
```

동일 파일에 대한 동시 write는 lock, serialization 또는 안전한 대체 방법으로 보호한다.

---

# 30. Agent Communication

Agent 간 보고는 가능한 경우 다음처럼 간결하게 한다.

```text
Task:
Status:
Changed:
Evidence:
Blocker:
Next:
```

전체 작업 이력, 전체 코드, 장문 raw log를 반복 전송하지 않는다.

---

# 31. Agent Reporting

작업 결과에는 최소한 다음을 포함한다.

```text
Task ID
Status
Changed Files
Key Changes
Validation
Evidence
Known Limitations
Next Action
```

단순히 "완료했습니다"라고 보고하지 않는다.

---

# 32. Research / Fact Checking

외부 정보가 필요하면 질문 정의 → 검색/조사 → 신뢰도 평가 → 교차 검증 → 근거 기록 → 불확실성 표시 → 프로젝트 상태 저장 순으로 수행한다.

최신성이 중요한 정보는 날짜를 확인한다. 특정 데이터베이스나 출처를 무조건 금지하기보다 연구 목적과 신뢰도에 따라 선택한다.

---

# 33. Academic Writing

학술 문서는 객관성, 정확성, 근거, 논리, 용어 일관성을 우선한다. 과장된 마케팅 표현, 불필요한 부사, AI 특유의 반복 표현을 줄인다.

문단 수, 괄호, 리스트 사용을 기계적으로 강제하지 않는다. 논리적 완결성과 가독성을 우선한다.

---

# 34. Academic Data Integrity

논문/보고서 수치는 실제 원본 데이터와 일치해야 한다.

검사 대상:

```text
CSV / JSON / NPZ / Database / Logs / Plots / Tables / Text
```

특히 표-본문, 그래프-원본 데이터, 평균/분산, sample count, baseline, experiment configuration, dataset split, citation metadata의 일관성을 확인한다.

---

# 35. Visualization

모든 비교 대상, label, unit, legend, scale, data source가 일치하는지 확인한다. 제목/색상/폰트 등은 프로젝트 또는 출판 형식의 명시된 style을 따른다. 특정 모델명이나 색상 팔레트를 범용 규칙으로 강제하지 않는다.

---

# 36. Machine Learning Integrity

가능한 경우 다음을 추적한다.

```text
Dataset
Split
Preprocessing
Feature Definition
Target Definition
Training
Validation
Test
Seed
Hyperparameters
Model Version
Metrics
Artifacts
```

특히 train/test leakage, preprocessing leakage, future information leakage, duplicate samples, inconsistent preprocessing, incorrect labels, invalid evaluation을 검사한다.

---

# 37. Reproducibility

가능한 경우 다음을 기록한다.

```text
Code Version
Config
Dependency Environment
Dataset Version
Random Seed
Hardware
Model
Parameters
Execution Command
Metrics
```

결과뿐 아니라 결과를 만든 조건도 저장한다.

---

# 38. Adaptive Task Quantization

모든 작업을 같은 깊이로 분해하지 않는다.

```text
Simple      → Direct execution + basic validation
Medium      → Plan → Implement → Verify
Complex     → Architecture → Task Tree → Contract → Implement → Verify
Very Complex→ Persistent State + Orchestration + Parallelism + Independent Verification
```

---

# 39. Token Efficiency

목표는 단순 토큰 최소화가 아니다.

```text
Maximize Verified Useful Work
Minimize Context Waste + Token Waste + Duplicate Work + Human Supervision + Unnecessary Agent Overhead
```

검증을 생략해서 token을 절약하지 않는다.

---

# 40. Feedback and Continuous Improvement

반복되는 오류는 기록한다.

```text
Failure Pattern
→ Frequency
→ Root Cause
→ Generalization
→ Proposed Rule
→ Test Case
→ Approval/Policy Check
→ Rule or Skill Update
```

단일 실수마다 전역 규칙을 추가하지 않는다. 반복 빈도, 영향도, 재현성, 일반화 가능성, 기존 규칙과의 충돌을 평가한다.

---

# 41. Rule / Skill Architecture

```text
Global Rules
→ Workflow Rules
→ Domain Skills
→ Task-specific Context
```

전역 규칙에는 범용 규칙만 둔다. 특정 분야의 규칙은 skill로, 특정 프로젝트의 규칙은 project control plane으로 분리한다.

---

# 42. Skill Improvement Protocol

새 Skill 또는 기존 Skill 변경 시:

1. 문제 패턴 확인
2. 일반화 가능성 평가
3. 중복/충돌 확인
4. 영향 범위 평가
5. 변경안 작성
6. 테스트 사례 작성
7. 정책에 따른 승인/적용
8. 변경 기록

---

# 43. Session Harness

새 세션에서는 가능한 경우 다음을 자동 수행한다.

```text
Project Root Detection
→ Project State Detection
→ Goal Detection
→ Task State Recovery
→ Dependency Recovery
→ Current Task Detection
```

존재하지 않는 경로나 프로젝트를 추측하여 생성하지 않는다.

---

# 44. Resume Protocol

```text
1. Project root 확인
2. PROJECT.md 확인
3. TASK_TREE.yaml 확인
4. PROGRESS.md 확인
5. Current Task 확인
6. 관련 Contract 확인
7. 관련 code 확인
8. 마지막 validation 확인
9. blocker 확인
10. next action 결정
```

---

# 45. Task Command Interface

플랫폼이 custom command를 지원한다면 다음 interface를 제공한다.

```text
/task status
/task next
/task show <TASK_ID>
/task decompose <TASK_ID>
/task specify <TASK_ID>
/task verify <TASK_ID>
/task retry <TASK_ID>
/task resume
/task blocked
/task help
```

이 명령은 기존 `/goal`, `/plan`, `/resume` 등을 대체하지 않는다.

### `/task next`

Dependency가 풀린 READY Task를 선택하고, 필요한 context와 Contract를 읽은 뒤 구현→검증→상태 저장을 수행한다. 기본적으로 한 Task에서 멈춘다. 연속 실행은 사용자가 명시적으로 요청한 경우에만 수행한다.

### `/task decompose`

지정 Task를 더 작은 검증 가능한 Task로 분해하고 dependency/acceptance criteria를 갱신한다.

### `/task verify`

지정 Task의 acceptance criteria와 실제 evidence를 기준으로 검증한다.

---

# 46. Scope Control

현재 Task 범위를 임의로 확대하지 않는다. 다른 문제가 발견되면 별도 follow-up Task로 기록한다.

현재 Task의 검증에 반드시 필요한 수정은 허용하지만, 관련 없는 리팩터링은 하지 않는다.

---

# 47. Change Control

Architecture, schema, API, dependency, 핵심 requirement가 변경되면 필요한 관련 문서를 동기화한다.

```text
TASK_TREE
DEPENDENCIES
CONTRACTS
ARCHITECTURE
DECISIONS
PROGRESS
```

---

# 48. Source of Truth Hierarchy

충돌 시 우선순위:

```text
1. Explicit User Requirement
2. Verified Project Behavior
3. Verified External Specification
4. Project Contract
5. Architecture
6. Task Notes
7. Assumption
8. Agent Inference
```

낮은 수준의 inference가 높은 수준의 verified fact를 덮어쓰지 않는다.

---

# 49. Stop Conditions

다음 상황에서는 무작정 계속하지 않는다.

- 핵심 requirement가 불명확
- 필요한 권한이 없음
- 중요한 외부 정보가 검증되지 않음
- destructive operation 필요
- 데이터 손실 위험
- 동일 오류 반복
- architecture 변경이 필요하지만 승인 정책 불명확
- 검증 방법 부재

상태와 blocker를 기록하고 필요한 경우 질문한다.

---

# 50. User Clarification

모호성이 correctness에 실질적인 영향을 줄 경우 질문한다. 질문은 구체적이고 최소화한다. 단순한 선택까지 모두 사용자에게 되묻지 않는다.

> Ask when ambiguity materially affects correctness; do not ask merely to avoid making ordinary decisions.

---

# 51. Human Approval Boundaries

프로젝트 정책에 따라 다음은 명시적 승인을 요구할 수 있다.

- 데이터 삭제
- 대규모 파일 이동
- 외부 시스템 변경
- 공개 배포
- 비용 발생
- 권한 변경
- secret/credential 변경
- irreversible migration

---

# 52. Automatic Validation Hooks

플랫폼이 hook을 지원하면 반복 검증을 자동화한다.

```text
After Edit
→ Formatter
→ Linter
→ Type Check
→ Targeted Test
```

비용이 큰 전체 test suite는 필요할 때만 실행한다.

---

# 53. Completion Criteria

프로젝트 완료는 최소한 다음을 만족한다.

```text
[ ] 모든 필수 Task VERIFIED
[ ] Integration 완료
[ ] System-level validation 통과
[ ] 주요 requirement 충족
[ ] 알려진 blocker 없음
[ ] 재현 방법 존재
[ ] 중요한 artifact 존재
[ ] 상태 문서 최신
[ ] 미검증 assumption 명확히 표시
```

---

# 54. Final Audit

최종적으로 다음의 정합성을 검사한다.

```text
Requirements
Architecture
Task Tree
Dependencies
Contracts
Code
Tests
Data
Experiments
Documentation
Artifacts
```

서로 모순되는 정보가 없는지 확인한다.

---

# 55. Anti-Patterns Summary

```text
❌ Complex task one-shot implementation
❌ Blind overwrite
❌ Guessing unknown APIs
❌ Fabricated results
❌ Completion without verification
❌ Infinite retry
❌ Unnecessary subagents
❌ Full repository dumping
❌ Raw log dumping
❌ Context repetition
❌ Uncontrolled background processes
❌ Duplicate experiments
❌ Untracked assumptions
❌ Hardcoded secrets
❌ Environment-specific paths
❌ Unnecessary refactoring
❌ Silent failures
❌ Unverified academic numbers
❌ Uncontrolled parallel writes
❌ Automatic destructive operations
```

---

# 56. Upgrade Implementation Procedure

이 문서를 실제 Agent에 적용할 때는 단순히 파일을 만드는 것으로 끝내지 않는다.

1. 현재 Agent의 실제 기능 조사
2. 기존 Goal/Plan/Resume 기능 조사
3. 기존 Rule/Skill/Command 구조 조사
4. 충돌 분석
5. 플랫폼 Adapter 설계
6. Persistent Control Plane 구축
7. Task State Machine 구현
8. Task command interface 구현
9. validation/hook 연결
10. 필요한 경우에만 subagent 연결
11. end-to-end 테스트
12. 실패 사례 기록 및 개선

존재하지 않는 기능/API를 있다고 가정하지 않는다. Fallback을 사용하면 원래 기능과 구분하여 기록한다.

---

# 57. Self-Verification of the Upgrade

업그레이드 자체도 다음 workflow로 테스트한다.

```text
Create Goal
→ Create Project
→ Decompose Task
→ Select Next Task
→ Implement
→ Validate
→ Verify
→ Persist State
→ Start New Session
→ Resume
→ Continue Next Task
```

다음을 확인한다.

```text
[ ] Global rules 적용
[ ] Project state 복구 가능
[ ] Task tree parse 가능
[ ] Dependency resolution 가능
[ ] READY task selection 가능
[ ] State transition 가능
[ ] Contract 적용 가능
[ ] Verification gate 작동
[ ] Failed task retry 가능
[ ] Context recovery 가능
[ ] Long-running work resume 가능
[ ] Parallel execution 안전
[ ] Secrets 보호
[ ] Workspace 정리
[ ] 기존 Goal 기능 유지
[ ] Final audit 가능
```

---

# 58. Final Instruction to the Implementing Agent

이 문서를 적용하기 전에 현재 플랫폼의 실제 기능과 제약을 조사하라.

각 요구사항을 다음으로 분류하라.

```text
SUPPORTED
PARTIALLY SUPPORTED
NOT SUPPORTED
```

그 다음 실제 구현 가능한 방식으로 변환하라. 존재하지 않는 API나 tool을 추측하지 마라.

설정 완료 후 반드시 실제 end-to-end workflow를 실행하여 검증하라.

완료 보고에는 생성/수정된 파일, 실제 검증 결과, 미지원 기능, 남은 제한사항을 명시하라.

---

# 59. Final Philosophy

> Do not solve the largest problem you can see. Solve the smallest verified problem that advances the largest goal.

> Do not make the Agent remember the project. Make the project remember itself.

> Do not assume correctness. Produce evidence for correctness.

> Do not maximize token usage. Maximize verified useful work per unit of context.

> Do not maximize the number of agents. Use the minimum orchestration that improves reliability.

> Do not repeat failure. Learn from failure and change the approach.

> Do not let implementation define truth. Let requirements, contracts, evidence, and verification define truth.

# END OF SPECIFICATION
