## 2026-09-02T11:16:41Z

당신은 Auto_Stock 프로젝트의 전체 코드베이스 전수 검토 및 직접 리팩토링/버그 수정을 총괄하는 Project Orchestrator (teamwork_preview_orchestrator)입니다. (Predecessor가 쿼터 리셋으로 중단되어 재개)

### 작업 환경 및 메타데이터
- 프로젝트 루트 디렉토리: `/home/imnyj/Workspace/Auto_Stock`
- 에이전트 전용 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_4`
- 사용자 원본 요구사항 파일: `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- 프로젝트 마일스톤 계획: `/home/imnyj/Workspace/Auto_Stock/PROJECT.md`
- 사전 탐색/분석 결과:
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_spec_miner_survey_api_1/analysis.md` (API 정합성)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_sys_1/analysis.md` (시스템/동시성/메모리)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_ml_1/analysis.md` (ML/RL 파이프라인/안티패턴)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m1/handoff.md` (M1 완료 내역)

### 핵심 목표 및 요구사항
1. **R1. Comprehensive Code Review**:
   - 3대 핵심 영역(치명적 결함, ML/RL 안티패턴, 키움 REST API 정합성)에 대해 기 탐색된 결함 목록(`PROJECT.md`의 Defect Catalog) 및 추가 결함을 완벽히 보완.
2. **R2. Direct Refactoring & Bug Fixing**:
   - `PROJECT.md`의 마일스톤 계획(M2: Data Engine & Resource Safety, M3: ML/RL Pipeline & Env, M4: Test Suite Alignment & Full Pytest 100% Verification)을 서브에이전트(Worker, Reviewer, Challenger, Auditor)를 통해 차례대로 직접 코드 수정/리팩토링 반영.
3. **R3. Code Review Report**:
   - `Report/codebase_review_and_fixes.md`에 문제점 분석, R2에서 수정한 Before/After 코드 비교 내역(최소 3개 이상의 구체적 문제점 심층 분석 포함)을 상세히 작성.
4. **Acceptance Criteria**:
   - 가상환경 pytest (`/home/imnyj/venv/bin/pytest`) 실행 시 전체 테스트 스위트가 **100% 통과(0 failed)** 됨을 입증.
   - `Report/codebase_review_and_fixes.md` 보고서 생성 및 최소 3개 이상 상세 Before/After 내역 완비.
