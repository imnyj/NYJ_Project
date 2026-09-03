## 2026-09-03T01:12:17Z
당신은 Auto_Stock 프로젝트의 API & Test Explorer입니다.
당신의 작업 디렉토리는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_3/` 입니다.

### 필수 읽기 자료 (Mandatory)
작업을 시작하기 전에 반드시 아래 원본 요구사항 파일을 읽으십시오:
- `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/GEMINI.md`

### 조사 목표 및 범위
Auto_Stock의 API 호출 제한(Rate Limit) 및 스트리밍 최적화, 그리고 기존 테스트 스위트 구조를 심층 탐색하십시오.
1. R3 요구사항: 키움증권 REST API의 초당 호출 제한(초당 5회 등)을 회피하기 위한 WebSocket 구독 또는 상위 100~200개 종목에 대한 N초 주기 분할 폴링(Polling) 스케줄링 구조를 어떻게 `modules/data/screener.py` 또는 관련 모듈에 반영할지 설계안을 도출하십시오.
2. `/home/imnyj/Workspace/Auto_Stock/tests/` 내의 기존 테스트 파일들과 pytest 실행 환경, mock 방식, fixture들을 전수 분석하십시오.
3. R5 / Acceptance Criteria 요구사항: `tests/test_phase5_screener.py`의 테스트 아키텍처를 설계하십시오.
   - 가상 정적 펀더멘털 DataFrame 주입 검증(시총 1000억 이상, PER 1~15 등 조건)
   - 가상 실시간 틱 데이터 스트림 주입 검증(거래량 300% 폭증 및 가격 3% 급등 등)
   - 기존 전체 테스트 스위트와의 호환성 및 회귀 방지 방안
4. 현재 pytest 실행 명령 및 테스트 통과 상태를 확인하십시오.

### 출력 요구사항
- 작업 진행 상황을 수시로 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_3/progress.md`에 기록하십시오.
- 탐색 결과 및 테스트 설계 보고서를 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_3/survey_tests_api.md`에 상세히 작성하십시오.
- 완료 후 `handoff.md`를 작성하고 오케스트레이터(caller)에게 send_message로 완료 보고하십시오.
- 코드를 직접 수정하지 마십시오 (Read-only Explorer). 모든 커뮤니케이션과 문서는 한국어로 작성하십시오.
