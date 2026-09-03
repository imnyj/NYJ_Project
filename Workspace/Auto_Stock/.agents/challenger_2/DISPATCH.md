## 2026-09-01T14:39:38Z
당신은 Auto Stock ML/RL Trader 프로젝트의 Phase 3 실거래/모의투자 환경 스위칭 및 트랜잭션 불변성을 검증하는 Challenger 2입니다.

### 작업 디렉토리 및 메타데이터
- 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/challenger_2`
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 필독 참조 문서:
  - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md`
  - `/home/imnyj/Workspace/Auto_Stock/PROJECT.md`
  - `/home/imnyj/Workspace/Auto_Stock/TEST_INFRA.md`

### 챌린지 검증 항목
1. **환경 토글 및 불변성 검증**:
   - `USE_MOCK_SERVER`가 True일 때 실거래 API(openapi.kiwoom.com, TTTC0802U 등)로의 오발송이 100% 차단되는지 검증
   - 환경변수 주입, YAML 오버라이드 시 우선순위 불변식 검증
   - 주문 전 잔고 -> 시장가 매수 -> 체결 후 잔고 변동액 계산의 회계 불변성(Decimal 정밀도) 검증
2. **독립적 적대적 테스트 실행**:
   - 직접 모킹 스크립트 및 테스트를 구동하여 결함 발견 시도
3. **테스트 스위트 실행**: `/home/imnyj/venv/bin/pytest tests/`

### 산출물 및 보고
- 챌린지 보고서(`/home/imnyj/Workspace/Auto_Stock/.agents/challenger_2/challenge_report.md`) 및 `handoff.md` 작성
- 최종 판정: `APPROVE` 또는 `REQUEST_CHANGES`를 명확히 기재하고 send_message로 보고하십시오.
- 모든 보고서는 한국어로 작성하십시오.
