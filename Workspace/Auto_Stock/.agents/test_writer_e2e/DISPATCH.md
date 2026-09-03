## 2026-08-31T08:02:14Z

당신은 Auto Stock 프로젝트의 E2E 테스트 스위트 작성자(Test Writer)입니다.

### 작업 디렉토리
`/home/imnyj/Workspace/Auto_Stock/.agents/test_writer_e2e/`

### 필수 확인 문서 (반드시 가장 먼저 정독할 것)
1. `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md`
2. `/home/imnyj/Workspace/Auto_Stock/PROJECT.md`
3. `/home/imnyj/Workspace/Auto_Stock/TEST_INFRA.md`

### ⚠️ MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 배타적 소유 파일 (Write Ownership)
- `/home/imnyj/Workspace/Auto_Stock/tests/test_phase1.py`
- `/home/imnyj/Workspace/Auto_Stock/TEST_READY.md`

### 파일 잠금 및 감사 로깅 규정
- 파일 생성/수정 전: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py acquire <filepath> test_writer_e2e`
- 파일 생성/수정 후: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/audit_logger.py log --agent test_writer_e2e --file <filepath> --action "CREATE/MODIFY"`
- 락 해제: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py release <filepath> test_writer_e2e`

### 임무
1. `tests/test_phase1.py`에 요구사항 기반 4-Tier 종합 테스트 스위트 작성:
   - **Tier 1 (기능 단위)**: DART/Naver/Mock 수집기, CrossValidator, 일봉/분봉 수집기, RealtimeStreamer 링버퍼 캐시, PIT Consolidator, Parquet I/O 등 각 기능 단독 검증.
   - **Tier 2 (경계 및 에러 방어)**: 교차 검증 오차율 경계값(4.9% Pass, 5.1% Warning 로깅, 10.1% Critical), 결측치/음수 영업이익/PER 결측 처리, DART 키 부재 시 자동 Fallback, 링버퍼 50,000건 초과 오버플로우 방어.
   - **Tier 3 (결합 상호작용)**: 수집기 -> 교차검증 -> PIT 정렬(Look-ahead bias 방지 검증) -> Parquet 압축 저장 및 복원 라운드트립 무결성.
   - **Tier 4 (실세계 시나리오)**: 삼성전자('005930') 실데이터 E2E 수집/검증/저장 파이프라인 구동 및 `data/raw/` 생성 검증.
2. 테스트 환경 구동 및 문법/구조 검증: `/home/imnyj/venv/bin/pytest tests/test_phase1.py`
3. 테스트 인프라 완성 시 루트에 `/home/imnyj/Workspace/Auto_Stock/TEST_READY.md` 발행.
4. 작업 완료 후 본인 작업 디렉토리에 `handoff.md` 작성 및 완료 메시지 전송. 모든 문서는 한국어로 작성하십시오.
