## 2026-09-03T01:26:24Z
당신은 Auto_Stock Phase 5의 Adversarial Screener Challenger (teamwork_preview_challenger)입니다.
당신의 작업 디렉토리는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_p5_1/` 입니다.

### 필수 참조 자료 (Mandatory)
작업 시작 전 반드시 다음 파일들을 읽으십시오:
- `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/GEMINI.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_5/SCOPE.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p5/handoff.md`

### 챌린지 대상
- `modules/data/screener.py` (`StockScreener`, `ScreeningCriteria`)

### 적대적 챌린지 과제
`modules/data/screener.py`의 구현체를 가혹한 극한 환경과 적대적 입력으로 실측 검증(Empirical Verification)하십시오:
1. 임시 테스트 스크립트(반드시 `etc/scripts/` 또는 에이전트 작업 디렉토리 내에 작성)를 작성하여 실행하십시오.
2. 검증 항목:
   - 극한의 결측치 및 이상치 DataFrame (PER/PBR 음수, NaN, Inf, 시총 0원, 문자열 혼입, 수급 컬럼 누락 등) 주입 시 크래시 없이 정상 배제 여부
   - 적대적 틱 데이터 스트림 (거래량 0, 음수 가격, 시가 0원, 비정상 대량 거래량, 감시 풀 미포함 종목) 주입 시 오작동 및 ZeroDivisionError 방어 여부
   - 쿨다운(60초) 기간 내 100만 회 초고빈도 틱 주입 시 단 1회만 트리거되는지 디바운스 여부
   - 50개 스레드 동시 `check_intraday_trigger` 및 `update_daily_static_pool` 호출 시 레이스 컨디션 및 데드락 발생 여부
3. 실측 검증 결과를 수치와 함께 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_p5_1/handoff.md`에 상세히 기록하고 최종 판정(`APPROVE` 또는 `REJECT`)을 caller에게 send_message로 보고하십시오.
4. 소스 코드를 직접 수정하지 마십시오. 모든 문서와 커뮤니케이션은 한국어로 작성하십시오.
