# Dispatch History

## 2026-09-01T23:28:37+09:00

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
