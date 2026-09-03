## 2026-09-01T14:32:24Z
당신은 Auto Stock ML/RL Trader 프로젝트의 'Phase 3: 실거래 제어 모듈'을 완벽하게 구현하는 전문 구현 Worker입니다.

### 작업 디렉토리 및 메타데이터
- 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/worker_1`
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 필독 참조 문서:
  - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (원본 요구사항)
  - `/home/imnyj/Workspace/Auto_Stock/PROJECT.md` (아키텍처 및 인터페이스 규격)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_1/survey_report.md` (코드베이스 현황)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_2/survey_report.md` (API 명세 및 인터페이스)
  - `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_3/survey_report.md` (보안 설정 및 모킹 전략)

### MANDATORY INTEGRITY WARNING
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 구현 대상 파일 및 세부 요구사항 (Write Ownership)
1. **`config/settings.yaml` 및 `config/settings.example.yaml`, `.env.example`**:
   - 민감 정보(AppKey, AppSecret, AccountNo)는 평문이 아닌 `${KIWOOM_APP_KEY:}` 환경변수 템플릿 형태로 작성.
   - `USE_MOCK_SERVER` (기본값 True), `live_base_url`, `mock_base_url`, 타임아웃, 재시도 파라미터 정의.
2. **`core/config.py` 및 `core/__init__.py`**:
   - `OS 환경변수 > .env > settings.yaml > 기본값` 4단계 우선순위 설정 로더 구현.
   - `${VAR:default}` 정규식 인터폴레이션 지원.
   - `SecretStr` 클래스(또는 Pydantic SecretStr)를 활용한 민감정보 마스킹 로깅(`***`).
   - `KiwoomConfig`, `AppConfig` 데이터 모델 및 모의/실서버 Base URL & TR_ID 매핑 헬퍼 구현.
3. **`core/kiwoom_api.py`**:
   - `TokenManager`: OAuth2.0 Client Credentials 토큰 발급, 만료 시간 추적, 만료 전 자동 갱신 및 메모리 캐싱.
   - `KiwoomClient` (또는 `KiwoomAPI`):
     - `get_access_token(force_refresh: bool = False) -> str`
     - `get_current_price(symbol: str) -> Dict[str, Any]` (현재가, 등락률, 시가/고가/저가, 거래량 파싱)
     - `send_order(symbol: str, side: str, quantity: int, price: int = 0, order_type: str = "01") -> Dict[str, Any]` (시장가/지정가 주문 전송, Live/Mock에 따른 TR_ID 자동 분기)
     - `get_account_balance() -> Dict[str, Any]` (예수금, 총평가금액, 손익)
     - `get_account_positions() -> List[Dict[str, Any]]` (보유 종목 리스트)
     - 타임아웃, HTTP 상태코드(401 시 토큰 갱신 후 재시도 등), 예외 처리(KiwoomAPIError, NetworkError, TokenError 등) 완비.
4. **`modules/engine/manual_trader.py` 및 `modules/engine/__init__.py`**:
   - CLI 기반 수동 매매 제어기.
   - CLI 인자(`argparse` 또는 `click`/`typer`) 및 대화형 인터페이스 지원:
     - 종목 코드 (`--symbol`), 매매 방향 (`--side BUY/SELL`), 수량 (`--quantity`), 모의투자 플래그 (`--mock / --live`)
   - 주문 전 계좌 잔고 및 현재가 확인 -> 주문 전송 -> 주문 체결 후 갱신된 잔고 및 보유 종목 출력 (`rich` 또는 포맷팅된 테이블로 직관적 표시).
5. **`requirements.txt` 및 기타 패키지 설정**:
   - 필요한 라이브러리 목록 최신화.

### 검증 지침
- 구현 완료 후 `/home/imnyj/venv/bin/pytest tests/`를 실행하여 기존 212개 테스트가 깨지지 않고 정상 통과하는지 확인하십시오.
- 구현 상세 보고서를 `/home/imnyj/Workspace/Auto_Stock/.agents/worker_1/implementation_report.md` 및 `handoff.md`에 작성하고 부모에게 send_message로 보고하십시오.
- 모든 보고서는 한국어로 작성하십시오.
