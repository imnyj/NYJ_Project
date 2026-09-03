# Original User Request

## Initial Request — 2026-09-02T17:03:26+09:00

당신은 Auto_Stock 프로젝트의 전체 코드베이스 전수 검토 및 직접 리팩토링/버그 수정을 총괄하는 Project Orchestrator (teamwork_preview_orchestrator)입니다.

### 작업 환경 및 메타데이터
- 프로젝트 루트 디렉토리: `/home/imnyj/Workspace/Auto_Stock`
- 에이전트 전용 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_3`
- 사용자 원본 요구사항 파일: `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`

### 핵심 목표 및 요구사항
1. **R1. Comprehensive Code Review**:
   - 전체 코드베이스를 스캔하여 다음 3대 주요 영역의 결함을 철저히 분석/식별:
     1) 치명적 결함: 논리적 버그, 메모리 누수, 멀티프로세싱/동시성 에러
     2) ML/RL 구조적 결함: 모델 훈련 파이프라인 상의 성능 병목, 강화학습 설계 안티패턴
     3) API 정합성: 구현된 로직이 실제 키움증권 REST API 명세와 일치하는지 검증
2. **R2. Direct Refactoring & Bug Fixing**:
   - 리뷰에서 식별된 명백한 버그 및 구조적 안티패턴을 에이전트 팀이 직접 코드에 수정 반영 (기존 의도 보존, 견고성 향상)
3. **R3. Code Review Report**:
   - 발견된 문제점, 심층 분석 내용, Before/After 수정 내역을 상세히 기록한 마크다운 보고서 `Report/codebase_review_and_fixes.md` 작성 (최소 3개 이상의 구체적 문제점 분석 및 수정 내역 포함)
4. **Acceptance Criteria**:
   - `pytest` 실행 시 기존 및 전체 테스트 스위트 100% 통과 (수정으로 인한 회귀 없음)
   - `Report/codebase_review_and_fixes.md` 생성 및 구체적 분석/수정 내역 완비

### 작업 수행 규칙 및 가이드라인
- `/home/imnyj/GEMINI.md`의 멀티 에이전트 팩토리 룰을 준수하십시오.
- 작업을 원자적 단위(탐색/분석, 설계, 수정/리팩토링, 테스트/검증, 리뷰/감사)로 분할하여 전문 서브에이전트(explorer, worker, reviewer, challenger 등)를 능동적으로 생성/위임하십시오.
- 작업 디렉토리(`/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_3/`)에 `plan.md`, `progress.md`, `BRIEFING.md`를 지속적으로 갱신하십시오.
- 모든 수정 및 테스트 완료 후, 승인 기준 충족 여부를 명확한 근거와 함께 Sentinel에게 완료 보고(send_message)하십시오.
- 모든 문서 및 커뮤니케이션은 한국어로 작성하십시오.

## 2026-09-03T01:10:38Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [none — teamwork routes from the description]

주식 자동 매매 프로그램 중 'Phase 5: 다이내믹 종목 스크리너(Dynamic Stock Screener)' 모듈 개발.
수천 개의 종목(시가총액 1,000억 이상) 중 트레이딩을 진행할 종목을 실시간으로 발굴하는 규칙 기반 스크리너 엔진을 구축합니다. 장 시작 전 정적 필터를 통해 감시 풀(Pool)을 구성하고, 장중 실시간 틱(Tick) 데이터를 바탕으로 거래량/변동성 돌파(Momentum Breakout)가 발생하는 종목을 포착하여 ML/RL 트레이딩 에이전트에게 넘깁니다.

Working directory: /home/imnyj/Workspace/Auto_Stock
Integrity mode: development

## Requirements

### R1. Static Daily Filter (정적 감시 풀 구성)
장 시작 전(또는 1일 1회), 시가총액 최소 1,000억 원 이상, 저평가(PER/PBR), 기관/외국인 수급 양호 조건을 만족하는 관심 종목(Candidate Pool) 리스트를 추출하는 메서드(`update_daily_static_pool`)를 `modules/data/screener.py` 내부에 구현합니다.

### R2. Intra-day Dynamic Trigger (장중 실시간 모멘텀 포착)
선정된 감시 풀 내 종목들의 실시간 틱(Tick) 데이터를 주입받아, 특정 조건(예: 거래량 전일 동시간대 대비 300% 급증 & 당일 시가 대비 3% 급등 등)이 충족되는 순간 해당 종목 코드를 반환하는 메서드(`check_intraday_trigger`)를 구현합니다.

### R3. API Rate Limit / Streaming Optimization (호출 최적화)
키움증권 REST API의 초당 호출 제한(Rate Limit)을 피하기 위해, 실시간 스크리닝 시 웹소켓(WebSocket) 기반 구독을 상정하거나, 상위 100~200개 종목을 N초 주기로 나누어 폴링(Polling)하도록 구조적 안정성을 확보해야 합니다. (이 부분은 주석 또는 스케줄링 구조로 코드에 반영되어야 합니다.)

### R4. RL Engine Integration (RL 엔진 연동)
`modules/engine/live_learning_simulator.py`를 수정하여, 스크리너에서 포착(Trigger)된 종목이 즉각적으로 강화학습(RL) 에이전트의 관측(State) 및 행동(Action) 루프로 진입하도록 파이프라인을 연결합니다.

## Acceptance Criteria

### Programmatic Verification (코드 기반 검증)
- [ ] 에이전트는 `tests/test_phase5_screener.py` 자동화 검증 스크립트를 작성해야 합니다.
- [ ] 가상의 정적 펀더멘털 데이터(DataFrame)를 주입했을 때, 조건(시총 1000억 이상, PER 1~15 등)에 맞는 종목만 감시 풀에 들어가는지 Assert로 검증해야 합니다.
- [ ] 가상의 실시간 틱 데이터(Tick) 스트림을 주입했을 때, 거래량이 설정된 임계치(예: 300%) 이상 폭증한 종목만 정확히 트리거(Trigger)되어 리턴되는지 검증해야 합니다.
- [ ] `pytest tests/test_phase5_screener.py` 실행 시 100% Pass해야 합니다.
