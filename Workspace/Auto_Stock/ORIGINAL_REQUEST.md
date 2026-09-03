# Original User Request

## Initial Request — 2026-09-01T23:28:37+09:00

당신은 주식 자동 매매 프로그램(Auto Stock ML/RL Trader)의 'Phase 3: 실거래 제어 모듈' 구축 프로젝트를 총괄하는 Project Orchestrator입니다.

### 작업 환경 및 메타데이터
- 프로젝트 루트 디렉토리: `/home/imnyj/Workspace/Auto_Stock`
- 에이전트 전용 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/orchestrator_3`
- 사용자 원본 요구사항 파일: `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` 및 `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`

### 핵심 요구사항
1. **R1. Kiwoom REST API Integration (키움 API 연동 코어)**
   - `core/kiwoom_api.py`를 작성(또는 고도화)하여 OAuth2.0 기반 접근 토큰(Access Token) 발급 및 갱신 기능을 구현합니다.
   - 실거래(Live) 서버 URL을 기본값으로 사용하되, 설정 파일의 플래그(예: `USE_MOCK_SERVER=True`)에 따라 모의투자 서버 도메인으로 스위치(Toggle)할 수 있는 구조여야 합니다.
   - 현재가 조회, 주문 전송, 계좌 잔고 조회 기능을 수행하는 메서드를 포함합니다.

2. **R2. Manual Trading Interface (수동 매매 제어기)**
   - `modules/engine/manual_trader.py`를 구현하여 CLI 환경에서 사용자가 특정 종목 코드, 매수/매도, 수량을 입력하면 키움 API로 시장가 주문을 전송하는 스크립트를 작성합니다.
   - 주문 체결 후 계좌 잔고가 어떻게 변했는지 출력해야 합니다.

3. **R3. Secret Management (보안 및 설정 파일 분리)**
   - API Key(App Key, App Secret) 및 계좌번호 등 민감한 개인 정보는 절대 소스 코드에 하드코딩하지 말고, `config/settings.yaml` (또는 `.env`)에서 안전하게 로드하여 사용하도록 구현해야 합니다.

4. **검증 및 승인 기준 (Acceptance Criteria)**
   - `tests/test_phase3_api.py` 형태의 검증 스크립트를 작성해야 합니다.
   - 실제 키움 서버와 통신하는 부분은 `unittest.mock`을 사용하여 모킹(Mocking) 처리하고, "토큰 발급 -> 주문 전송 -> 잔고 확인"의 로직 흐름이 에러 없이 실행됨을 증명해야 합니다.
   - 민감 정보가 소스 코드에 포함되지 않았음(하드코딩 0건)을 정적 분석으로 입증해야 합니다.

### 수행 규칙
- 자체 폴더(`/home/imnyj/Workspace/Auto_Stock/.agents/orchestrator_3/`)에 `plan.md`, `progress.md`, `BRIEFING.md`를 지속적으로 생성 및 갱신하십시오.
- 하위 작업(탐색 및 분석, 아키텍처 설계, 구현, E2E 테스트 작성, 코드 리뷰, 적대적 챌린지, 무결성 감사)을 전문 서브에이전트에게 분할 위임하여 철저히 검증하며 진행하십시오.
- 모든 구현 및 테스트 완료 후 최종 산출물 및 검증 결과를 보고하십시오.
- 모든 의사소통 및 문서는 한국어(Korean)로 작성하십시오.

## 2026-09-02T08:02:42Z

<USER_REQUEST>
# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full Team

지금까지 작성된 Auto_Stock 프로젝트의 전체 코드베이스를 검토하여 치명적 결함, ML/RL 안티패턴, API 명세 불일치 등을 찾아내고, 종합적인 리뷰 보고서를 작성함과 동시에 확인된 버그와 리팩토링 사항을 직접 코드에 수정 적용합니다.

Working directory: /home/imnyj/Workspace/Auto_Stock
Integrity mode: development

## Requirements

### R1. Comprehensive Code Review
전체 코드베이스를 스캔하여 다음 세 가지 주요 영역의 결함을 찾아내세요:
1. **치명적 결함**: 논리적 버그, 메모리 누수, 멀티프로세싱/동시성 에러.
2. **ML/RL 구조적 결함**: 모델 훈련 파이프라인 상의 성능 병목 현상이나 강화학습 설계 안티패턴.
3. **API 정합성**: 구현된 로직이 실제 키움증권 REST API 명세와 일치하는지 검증.

### R2. Direct Refactoring & Bug Fixing
리뷰 과정에서 발견된 명백한 버그나 개선이 필요한 구조적 안티패턴에 대해, 에이전트 팀이 직접 코드를 수정(Refactoring)하여 반영하세요. 기존 로직의 의도를 해치지 않으면서 안정성을 높여야 합니다.

### R3. Code Review Report
발견된 문제점, 분석 내용, 그리고 R2에서 에이전트 팀이 직접 수정한 코드의 Before/After 내역을 상세히 기록한 마크다운 보고서(`Report/codebase_review_and_fixes.md`)를 작성하세요.

## Acceptance Criteria

### Programmatic Verification (코드 기반 검증)
- [ ] 에이전트 팀이 코드 수정을 완료한 후, `pytest`를 실행하여 기존에 작성된 모든 테스트 스위트가 **100% 통과**됨을 입증해야 합니다. (수정된 코드로 인해 기존 테스트가 깨지지 않아야 함)
- [ ] `Report/codebase_review_and_fixes.md` 파일이 성공적으로 생성되었고, 최소 3개 이상의 구체적인 문제점 분석 및 수정 내역이 포함되어 있음을 파일 존재 여부 및 내용 길이 검사로 입증해야 합니다.
</USER_REQUEST>

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

## 2026-09-03T01:57:08Z

<USER_REQUEST>
# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Large-scale agent team

Use a very large team of agents.

주식 자동 매매 프로그램의 본 모델(Main Model) 아키텍처 개발 및 병렬 탐색.
기존 구축된 하이브리드 RL 환경 위에서, 다중 시계열 데이터를 처리하는 3가지 이상의 다양한 지도학습(SL) 아키텍처를 설계하고, 이를 PPO 강화학습과 결합하여 대규모 파라미터 탐색(HPO)을 수행합니다.

Working directory: /home/imnyj/Workspace/Auto_Stock
Integrity mode: development

## Requirements

### R1. Diverse SL Architectures (다중 지도학습 모델 구현)
1D-CNN 기반의 ResNet, 시계열 Attention 기반의 Transformer, 그리고 잠재 공간 이상치 탐지 기반의 CVAE 등 최소 3가지 이상의 상이한 딥러닝 아키텍처를 특징 추출기(Feature Extractor)로 구현해야 합니다. 각 모델은 동일한 다중 타임프레임 데이터를 입력받을 수 있어야 합니다.

### R2. Hybrid RL Integration (하이브리드 강화학습 통합)
구현된 각각의 SL 아키텍처를 기반으로 예측된 타겟 값(수익률, 추세 확률 등)을 상태(State)로 편입하여, 매수/매도/관망 및 비중을 조절하는 하이브리드 PPO 에이전트와 완벽히 결합(End-to-End 연결)해야 합니다.

### R3. Large-scale HPO Pipeline (대규모 병렬 최적화 파이프라인)
각 아키텍처(ResNet, Transformer, CVAE)별로 Optuna 파이프라인을 구축하여 하이퍼파라미터 최적화(HPO)를 수행할 수 있어야 합니다. 

## Acceptance Criteria

### Programmatic Verification (코드 기반 검증)
- [ ] 에이전트는 `tests/test_phase6_models.py` 자동화 검증 스크립트를 작성해야 합니다. 해당 테스트는 3가지 SL 아키텍처 모델들이 각각 정의된 형태의 동일한 텐서(Tensor) 입력을 받아 정상적인 형태(Shape)의 출력을 반환하는지 검증해야 합니다.
- [ ] `tests/test_phase6_hpo.py` 스크립트를 통해, 각 아키텍처별 Optuna 최적화가 최소 2회(n_trials=2) 이상 크래시 없이 정상적으로 실행되며, 결과가 `etc/hpo_results/main_models_hpo.csv` 형태로 저장됨을 입증해야 합니다.
- [ ] 위 검증 스크립트들을 포함한 전체 테스트 스위트 실행 시 100% Pass해야 합니다.
</USER_REQUEST>
