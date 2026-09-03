## 2026-09-01T14:32:24Z
당신은 Auto Stock ML/RL Trader 프로젝트의 Phase 3 E2E Mock 테스트 스위트를 구축하는 Test Writer입니다.

### 작업 디렉토리 및 메타데이터
- 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/test_writer_1`
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 필독 참조 문서:
  - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (원본 요구사항 및 Acceptance Criteria)
  - `/home/imnyj/Workspace/Auto_Stock/PROJECT.md` (아키텍처 및 인터페이스 규격)
  - `/home/imnyj/Workspace/Auto_Stock/TEST_INFRA.md` (4-Tier 테스트 전략)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_3/survey_report.md` (모킹 전략 및 4-Tier 케이스 설계)

### MANDATORY INTEGRITY WARNING
> DO NOT CHEAT. All tests must be authentic and genuinely verify functionality. A auditor will independently verify your work.

### 구현 대상 파일 (Write Ownership)
- `tests/test_phase3_api.py`

### 테스트 스위트 요구사항 (4-Tier 체계)
1. **Tier 1: Feature Coverage (단위 및 핵심 API 기능 검증, 최소 8개)**
   - 설정 파일 로드, 우선순위 계층(OS env > .env > YAML) 및 SecretStr 마스킹 검증
   - OAuth2 토큰 발급 및 만료 전 메모리 캐싱 재사용 검증
   - 현재가 시세 조회 API 응답 파싱 및 필드 검증
   - 시장가 매수/매도 주문 전송 및 파라미터 검증
   - 계좌 잔고 및 보유 종목 조회 검증
2. **Tier 2: Boundary & Corner Cases (경계값 및 예외 처리, 최소 6개)**
   - 네트워크 타임아웃 및 ConnectionError 발생 시 예외 처리
   - 401 Unauthorized 발생 시 토큰 자동 갱신 및 1회 재시도 검증
   - 유효하지 않은 종목코드(6자리 미만/초과), 0 이하 수량 입력 차단
   - API 서버 에러(500, rt_cd != 0) 발생 시 적절한 커스텀 예외 발생 검증
3. **Tier 3: Cross-Feature & Mode Switching (모드 분기 및 연계 검증, 최소 4개)**
   - `use_mock_server=True` vs `False` 시 Base URL 및 TR_ID(`VTTC0802U` vs `TTTC0802U` 등) 동적 분기 검증
   - 토큰 만료 후 시세 조회 -> 주문 전송 -> 잔고 확인 연계 시나리오
4. **Tier 4: E2E Scenario & Static Secret Audit (통합 시나리오 및 하드코딩 0건 감사, 최소 4개)**
   - `ManualTrader`를 활용한 "시세 조회 -> 주문 전송 -> 잔고 변동 출력" 통합 E2E 흐름 모킹 검증
   - 소스코드(`core/`, `modules/`, `config/`) 전역 정적 분석을 통해 실제 시크릿/계좌번호 하드코딩 0건 검증

### 검증 지침
- `/home/imnyj/venv/bin/pytest tests/test_phase3_api.py -v`를 실행하여 작성한 테스트가 100% PASS하는지 검증하십시오.
- 작성 완료 후 `/home/imnyj/Workspace/Auto_Stock/.agents/test_writer_1/test_report.md` 및 `handoff.md`를 작성하고 부모에게 send_message로 보고하십시오.
- 모든 보고서는 한국어로 작성하십시오.
