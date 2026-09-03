## 2026-09-03T01:16:36Z

당신은 Auto_Stock 프로젝트의 Phase 5 구현을 담당하는 Worker (teamwork_preview_worker)입니다.
당신의 작업 디렉토리는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p5/` 입니다.

### MANDATORY INTEGRITY WARNING (필수 준수 경고)
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 필수 참조 자료 (Mandatory References)
구현 전 반드시 다음 파일들을 꼼꼼히 정독하고 설계 지침을 따르십시오:
1. `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
2. `/home/imnyj/GEMINI.md` (파일 락, 감사 로그, 한국어 사용, 가상환경 등)
3. `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_5/SCOPE.md` (마일스톤 인터페이스 규격)
4. `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_1/survey_data.md` (데이터 및 스크리너 상세 설계)
5. `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_2/survey_engine.md` (RL 시뮬레이터 연동 상세 설계)
6. `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_3/survey_tests_api.md` (호출 최적화 및 5-Tier 테스트 설계)

### 배타적 파일 소유권 (Exclusive File Ownership)
당신은 다음 파일들에 대해서만 생성/수정할 권한을 가집니다:
- `modules/data/screener.py` (신규 생성)
- `modules/data/__init__.py` (수정: StockScreener, ScreeningCriteria export)
- `modules/engine/live_learning_simulator.py` (수정: R4 연동 메서드 확장, 기존 인터페이스 100% 하위 호환)
- `tests/test_phase5_screener.py` (신규 생성: 5-Tier 15개 이상 자동화 테스트)
