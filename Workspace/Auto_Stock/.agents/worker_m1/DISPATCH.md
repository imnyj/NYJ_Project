## 2026-08-31T08:02:15Z

당신은 Auto Stock 프로젝트의 Milestone 1 (Fundamental Data Collector & Validation) 전담 구현 워커입니다.

### 작업 디렉토리
`/home/imnyj/Workspace/Auto_Stock/.agents/worker_m1/`

### 필수 확인 문서 (반드시 가장 먼저 정독할 것)
1. `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md`
2. `/home/imnyj/Workspace/Auto_Stock/PROJECT.md`
3. `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_survey_2/survey_fundamental_spec.md`

### ⚠️ MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 배타적 소유 파일 (Write Ownership)
- `/home/imnyj/Workspace/Auto_Stock/modules/data/collector_fundamental.py`
- `/home/imnyj/Workspace/Auto_Stock/tests/test_fundamental.py`

### 파일 잠금 및 감사 로깅 규정
- 파일 생성/수정 전: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py acquire <filepath> worker_m1`
- 파일 생성/수정 후: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/audit_logger.py log --agent worker_m1 --file <filepath> --action "CREATE/MODIFY"`
- 락 해제: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py release <filepath> worker_m1`

### 구현 요구사항
1. `modules/data/collector_fundamental.py`:
   - `BaseFundamentalSource` 인터페이스 정의.
   - `OpenDartCollector`: DART API Key 환경변수 지원, 재무제표 수집, 에러코드('010', '011' 등) 방어 처리.
   - `NaverFinanceCollector`: `requests`/`bs4` 기반 순수 구현. 모바일 REST API(`finance/annual`, `quarter`, `integration`) 및 웹 스크래핑 지원. 단위 정규화(억원 -> 원 단위 변환: *100,000,000).
   - `MockKiwoomCollector`: Linux/CI 테스트를 위한 고충실도 Mock 제공.
   - `FundamentalCrossValidator`: 상대 오차율 $\Delta = \frac{|V_1 - V_2|}{\max(|V_1|, |V_2|)} \times 100$ 계산. 5% 초과 시 `logger.warning` 발생, 10% 이상 시 critical 처리. DART -> Naver -> Mock 우선순위 Fallback 및 결측치 보정.
   - `FundamentalDataCollector` Facade 클래스 구현.
2. `tests/test_fundamental.py` 작성 및 자체 단위 테스트 실행:
   - `/home/imnyj/venv/bin/pytest -v tests/test_fundamental.py`
3. 테스트 100% 통과 확인 후 본인 작업 디렉토리에 `handoff.md` 작성 및 완료 보고. 모든 문서는 한국어로 작성하십시오.
