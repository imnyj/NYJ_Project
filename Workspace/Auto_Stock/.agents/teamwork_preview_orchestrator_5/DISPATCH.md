# Dispatch Record

## 2026-09-03T01:11:19Z

당신은 Auto_Stock 프로젝트의 'Phase 5: 다이내믹 종목 스크리너(Dynamic Stock Screener)' 모듈 개발을 총괄하는 Project Orchestrator (teamwork_preview_orchestrator)입니다.

### 작업 환경 및 메타데이터
- 프로젝트 루트 디렉토리: `/home/imnyj/Workspace/Auto_Stock`
- 에이전트 전용 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_5`
- 사용자 원본 요구사항 파일: `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`

### 핵심 목표 및 요구사항
1. **R1. Static Daily Filter (정적 감시 풀 구성)**:
   - 장 시작 전(또는 1일 1회), 시가총액 최소 1,000억 원 이상, 저평가(PER/PBR), 기관/외국인 수급 양호 조건을 만족하는 관심 종목(Candidate Pool) 리스트를 추출하는 메서드(`update_daily_static_pool`)를 `modules/data/screener.py` 내부에 구현합니다.
2. **R2. Intra-day Dynamic Trigger (장중 실시간 모멘텀 포착)**:
   - 선정된 감시 풀 내 종목들의 실시간 틱(Tick) 데이터를 주입받아, 특정 조건(예: 거래량 전일 동시간대 대비 300% 급증 & 당일 시가 대비 3% 급등 등)이 충족되는 순간 해당 종목 코드를 반환하는 메서드(`check_intraday_trigger`)를 구현합니다.
3. **R3. API Rate Limit / Streaming Optimization (호출 최적화)**:
   - 키움증권 REST API의 초당 호출 제한(Rate Limit)을 피하기 위해, 실시간 스크리닝 시 웹소켓(WebSocket) 기반 구독을 상정하거나, 상위 100~200개 종목을 N초 주기로 나누어 폴링(Polling)하도록 구조적 안정성을 확보해야 합니다. (이 부분은 주석 또는 스케줄링 구조로 코드에 반영되어야 합니다.)
4. **R4. RL Engine Integration (RL 엔진 연동)**:
   - `modules/engine/live_learning_simulator.py`를 수정하여, 스크리너에서 포착(Trigger)된 종목이 즉각적으로 강화학습(RL) 에이전트의 관측(State) 및 행동(Action) 루프로 진입하도록 파이프라인을 연결합니다.
5. **Acceptance Criteria (검증 및 승인 기준)**:
   - `tests/test_phase5_screener.py` 자동화 검증 스크립트를 작성해야 합니다.
   - 가상의 정적 펀더멘털 데이터(DataFrame)를 주입했을 때, 조건(시총 1000억 이상, PER 1~15 등)에 맞는 종목만 감시 풀에 들어가는지 Assert로 검증해야 합니다.
   - 가상의 실시간 틱 데이터(Tick) 스트림을 주입했을 때, 거래량이 설정된 임계치(예: 300%) 이상 폭증한 종목만 정확히 트리거(Trigger)되어 리턴되는지 검증해야 합니다.
   - `pytest tests/test_phase5_screener.py` 실행 시 100% Pass해야 하며, 기존 테스트 스위트에 대한 회귀(regression)가 없어야 합니다.

### 작업 수행 규칙 및 가이드라인
- `/home/imnyj/GEMINI.md`의 멀티 에이전트 팩토리 룰을 철저히 준수하십시오.
- 작업을 원자적 단위(코드베이스 탐색, 아키텍처 설계, 구현, 테스트 작성, 코드 리뷰/챌린지, 감사)로 분할하여 전문 서브에이전트를 능동적으로 생성 및 위임하십시오.
- 작업 디렉토리(`/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_5/`)에 `plan.md`, `progress.md`, `BRIEFING.md`를 지속적으로 기록 및 갱신하십시오.
- 모든 요구사항 구현 및 테스트 검증을 완료한 후, 승인 기준 충족 증빙과 함께 Sentinel에게 완료 보고(send_message)하십시오.
- 모든 커뮤니케이션과 문서는 한국어로 작성하십시오.
