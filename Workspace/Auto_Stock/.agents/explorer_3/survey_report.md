# Phase 3: 보안 설정(Secret Management) 및 E2E Mock 테스트 전략 조사 보고서
**에이전트**: Config & QA Explorer (`explorer_3`)  
**작업 일시**: 2026-09-01T23:31:00+09:00  
**프로젝트**: Auto Stock ML/RL Trader — Phase 3 (실거래 제어 모듈)

---

## 1. 개요 및 조사 목적
본 보고서는 주식 자동 매매 프로그램(Auto Stock ML/RL Trader)의 'Phase 3: 실거래 제어 모듈' 구축을 위한 **보안 설정(Secret Management) 아키텍처** 및 **E2E Mock 테스트 전략**을 심층 분석한 결과를 담고 있습니다.

- **핵심 목표 1 (Secret Management & Zero Hardcoding)**:
  증권사 Open API(키움 REST API) 인증에 필요한 App Key, App Secret, 계좌번호 등 민감정보의 소스코드 평문 하드코딩 0건을 원천 보장하고, `config/settings.yaml`, `.env`, OS 환경변수 간의 계층적 로딩 및 마스킹 보안 아키텍처를 수립합니다.
- **핵심 목표 2 (E2E Mock Testing & QA Strategy)**:
  실제 증권사 서버와의 외부 네트워크 통신을 완전히 차단한 상태에서 `unittest.mock`을 활용하여 "토큰 발급 -> 현재가 조회 -> 주문 전송 -> 잔고 확인"의 전체 트레이딩 파이프라인 및 예외/경계 상황을 완벽하게 검증할 수 있는 4-Tier 테스트 스위트(`tests/test_phase3_api.py`)를 설계합니다.

---

## 2. 보안 설정(Secret Management) 아키텍처 분석

### 2.1 설정 로딩 계층 구조 (Configuration Hierarchy)
설정값의 우선순위는 시스템의 보안성, 이식성, CI/CD 자동화 호환성을 고려하여 다음 4단계 계층으로 구성합니다:

```
[Level 1: 최고 우선순위] OS 환경 변수 (os.environ)
       ▲ (오버라이드)
[Level 2] 로컬 환경 파일 (.env, python-dotenv)
       ▲ (오버라이드)
[Level 3] 설정 파일 (config/settings.yaml, 환경변수 치환 ${VAR:default} 지원)
       ▲ (오버라이드)
[Level 4: 최저 우선순위] 코드 내 안전한 기본값 (Non-sensitive defaults only, e.g. USE_MOCK_SERVER=True)
```

### 2.2 파일 분리 및 Git 보안 규칙
1. **`.env` (비공개 민감 정보)**:
   - 실제 증권사 인증 키(`KIWOOM_APP_KEY`), 시크릿(`KIWOOM_APP_SECRET`), 계좌번호(`KIWOOM_ACCOUNT_NO`)가 저장되는 로컬 전용 파일입니다.
   - `.gitignore`에 반드시 등록되어 리포지토리 커밋이 원천 차단됩니다.
2. **`.env.example` (공개 템플릿)**:
   - 키 이름과 플레이스홀더(`your_app_key_here` 등)만 포함하며, Git에 안전하게 커밋되어 신규 환경 구축 시 가이드를 제공합니다.
3. **`config/settings.yaml` (시스템 설정)**:
   - 서버 URL, 타임아웃, 재시도 횟수, 기본 주문 설정 등 구조화된 설정 파일입니다.
   - 민감정보 필드는 `${KIWOOM_APP_KEY:}`와 같이 환경변수 치환 플레이스홀더를 적용하여 평문 노출을 방지합니다.
4. **`config/settings.example.yaml` (설정 템플릿)**:
   - YAML 설정의 기본 구조를 제공하는 예시 파일입니다.

### 2.3 설정 파일 상세 명세

#### (1) `config/settings.yaml`
```yaml
# config/settings.yaml
app:
  name: "AutoStockTrader"
  version: "1.0.0"
  log_level: "INFO"

kiwoom:
  use_mock_server: true # 기본값: 모의투자 서버 사용 (안전 장치)
  live_base_url: "https://openapi.kiwoom.com"
  mock_base_url: "https://mock.kiwoom.com"
  timeout_seconds: 10
  max_retries: 3
  retry_backoff_factor: 0.5
  
  # 민감 정보: 환경 변수 치환 지원 (${VAR_NAME:default_value})
  app_key: "${KIWOOM_APP_KEY:}"
  app_secret: "${KIWOOM_APP_SECRET:}"
  account_no: "${KIWOOM_ACCOUNT_NO:}"
  account_type: "${KIWOOM_ACCOUNT_TYPE:01}" # 01: 종합계좌

trading:
  default_order_type: "MARKET" # MARKET, LIMIT
  default_quantity: 1
  max_order_amount_krw: 10000000 # 단일 주문 최대 허용 금액 (안전 가드)
```

#### (2) `.env.example`
```env
# .env.example
# 키움 REST API 인증 및 계좌 정보 템플릿
KIWOOM_APP_KEY=your_app_key_here
KIWOOM_APP_SECRET=your_app_secret_here
KIWOOM_ACCOUNT_NO=12345678-01
KIWOOM_ACCOUNT_TYPE=01
USE_MOCK_SERVER=True
LOG_LEVEL=INFO
```

### 2.4 설정 로더 (`core/config.py`) 핵심 메커니즘
- **환경변수 템플릿 인터폴레이션 (String Interpolation)**:
  `re.compile(r"\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}")` 정규식을 활용하여 YAML 파싱 시 문자열 내 환경변수를 런타임에 동적으로 주입합니다.
- **민감정보 마스킹 (`SecretStr` 패턴)**:
  민감정보 객체는 `__repr__` 및 `__str__` 호출 시 `***` 또는 앞뒤 2글자만 노출(`ab***12`)하도록 캡슐화하여, 로그 출력이나 디버거 노출 시 시크릿 유출을 차단합니다.
- **모의/실서버 도메인 및 TR_ID 자동 분기**:
  - `is_mock: bool`: `USE_MOCK_SERVER` 설정값에 따라 결정 (기본값: `True`)
  - `get_base_url() -> str`: `mock_base_url` 또는 `live_base_url` 반환
  - `get_tr_id(action: str) -> str`: 매수/매도/잔고 조회에 맞는 실거래/모의투자 TR_ID 자동 매핑

### 2.5 하드코딩 0건 정적 감사(Static Audit) 검증 규칙
소스코드 내 민감정보 평문 하드코딩 여부를 검증하기 위한 정적 분석 규칙:
- **계좌번호 패턴**: `\b\d{8}[-]?\d{2}\b` (단, 테스트용 `00000000-01` 등 허용 더미 제외)
- **AppKey 패턴**: `['"][a-zA-Z0-9]{32,}['"]` (단, `mock_app_key` 등 허용 더미 제외)
- **AppSecret 패턴**: `['"][a-zA-Z0-9+/=]{40,}['"]`
- **하드코딩 할당 패턴**: `(?:app_key|appsecret|secret_key)\s*=\s*['"][a-zA-Z0-9_\-]{8,}['"]`

---

## 3. Kiwoom REST API 연동 및 엔드포인트 명세 분석

### 3.1 주요 API 엔드포인트 및 TR_ID 매핑
| 기능 | HTTP Method | URL Path | TR_ID (실거래) | TR_ID (모의투자) | 비고 |
|---|---|---|---|---|---|
| **OAuth2 토큰 발급** | `POST` | `/oauth2/tokenP` | N/A | N/A | `grant_type: client_credentials` |
| **현재가 시세 조회** | `GET` | `/uapi/domestic-stock/v1/quotations/inquire-price` | `FHKST01010100` | `FHKST01010100` | 종목코드 6자리 |
| **주식 매수 주문** | `POST` | `/uapi/domestic-stock/v1/trading/order-cash` | `TTTC0802U` | `VTTC0802U` | 시장가(`01`), 수량, 단가`0` |
| **주식 매도 주문** | `POST` | `/uapi/domestic-stock/v1/trading/order-cash` | `TTTC0801U` | `VTTC0801U` | 시장가(`01`), 수량, 단가`0` |
| **계좌 잔고 조회** | `GET` | `/uapi/domestic-stock/v1/trading/inquire-balance` | `TTTC8434R` | `VTTC8434R` | 예수금, 보유종목, 손익 |

### 3.2 핵심 인터페이스 계약 (`core/kiwoom_api.py`)
- `KiwoomAPI.get_access_token(force_refresh: bool = False) -> str`
- `KiwoomAPI.get_current_price(symbol: str) -> Dict[str, Any]`
- `KiwoomAPI.send_order(symbol: str, side: OrderSide, quantity: int, price: int = 0, order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]`
- `KiwoomAPI.get_account_balance() -> Dict[str, Any]`
- `KiwoomAPI.get_order_history(...) -> List[Dict[str, Any]]`

### 3.3 수동 매매 인터페이스 (`modules/engine/manual_trader.py`)
- CLI 환경에서 사용자 입력을 수신하거나 인자 파싱을 통해 `KiwoomAPI`를 호출합니다.
- 실행 흐름:
  1. 설정 로드 및 `KiwoomAPI` 클라이언트 초기화 (모의/실거래 모드 알림)
  2. 주문 전 잔고 조회 및 출력
  3. 주문 파라미터 유효성 검사
  4. 주문 전송 (실거래 모드 시 최종 안전 확인 프롬프트)
  5. 주문 체결 후 갱신된 잔고 및 보유 종목 출력

---

## 4. E2E Mock 테스트 전략 (`tests/test_phase3_api.py`)

### 4.1 Mocking 원칙 및 안전 장치
1. **완전한 네트워크 격리**:
   `unittest.mock.patch("requests.Session.send")` 또는 `requests.request`를 가로채어 외부 증권사 서버와의 실제 네트워크 연결 시도를 원천 차단합니다.
2. **모의 응답 팩토리 (`MockResponseFactory`)**:
   실제 키움 Open API의 응답 스펙(헤더, 상태코드, JSON Body 구조, `rt_cd`, `msg_cd`, `output`, `output1`, `output2`)을 정확히 모사하는 재사용 가능한 팩토리를 구성합니다.

### 4.2 4-Tier 테스트 아키텍처 설계

```
========================================================================================
[Tier 1: Feature Coverage] 단위 기능 및 핵심 API 모킹 (8개 테스트 케이스)
- TC-01: 설정 로드, .env 우선순위 및 SecretStr 마스킹 검증
- TC-02: OAuth2 토큰 발급 및 만료 전 메모리 캐싱 재사용 검증
- TC-03: 현재가 시세 조회 API 파싱 및 Decimal 변환 검증
- TC-04: 모의투자 매수 주문 전송 및 TR_ID(VTTC0802U) 검증
- TC-05: 모의투자 매도 주문 전송 및 TR_ID(VTTC0801U) 검증
- TC-06: 실거래 서버 모드 전환 시 TR_ID(TTTC0802U/TTTC0801U) 및 Base URL 스위칭 검증
- TC-07: 계좌 잔고 조회 및 보유 종목 리스트 변환 검증
- TC-08: 수동 매매 CLI 실행 함수 단독 실행 검증

========================================================================================
[Tier 2: Boundary & Exceptions] 경계값, 유효성 검사 및 예외 처리 (8개 테스트 케이스)
- TC-09: 토큰 만료 시 자동 재발급(Auto Refresh) 검증
- TC-10: HTTP 401 Unauthorized 수신 시 토큰 강제 갱신 후 재시도 검증
- TC-11: HTTP 500 / 503 서버 에러 발생 시 커스텀 예외 발생 검증
- TC-12: 네트워크 타임아웃(Timeout) 발생 시 예외 전파 및 안전 거절 검증
- TC-13: 증권사 비즈니스 거절(rt_cd != '0', 잔고 부족 등) 에러 핸들링 검증
- TC-14: 종목코드 형식(6자리 미만/초과, 특수문자) 유효성 검사 실패 방어 검증
- TC-15: 주문 수량 0 또는 음수 수량 방어 검증
- TC-16: 필수 인증정보 누락 시 안전 Mock 모드 동작 또는 초기화 예외 검증

========================================================================================
[Tier 3: Configuration & Toggle Scenarios] 설정 분기 및 모드 전환 (3개 테스트 케이스)
- TC-17: OS 환경변수가 .env 및 settings.yaml 설정을 정상 오버라이드하는지 검증
- TC-18: YAML 내 ${ENV_VAR:default} 환경변수 인터폴레이션 정상 동작 검증
- TC-19: USE_MOCK_SERVER 플래그 토글에 따른 일관된 엔드포인트 분기 검증

========================================================================================
[Tier 4: E2E Golden Path & Forensic Static Audit] 전체 흐름 통합 및 정적 감사 (3개 테스트 케이스)
- TC-20: [E2E Golden Flow] 토큰 발급 -> 시세 조회 -> 매수 주문 -> 잔고 갱신 -> 매도 주문 -> 최종 잔고 검증
- TC-21: [CLI E2E] Manual Trader CLI 상호작용 및 잔고 변화 출력 시뮬레이션 검증
- TC-22: [Forensic Audit] 프로젝트 소스코드 전체 하드코딩 0건 정적 감사 자동 검증
========================================================================================
```

---

## 5. 결론 및 구현/검증 권고사항
1. **보안 구현**: `core/config.py`에서 `dotenv`, `yaml`, 정규식 기반 인터폴레이션, `SecretStr` 마스킹을 결합한 견고한 설정 로더를 구현할 것을 권장합니다.
2. **API 연동**: `core/kiwoom_api.py`에 토큰 자동 갱신, 세션 관리, 모의/실서버 TR_ID 분기 로직을 모듈화하여 배치할 것을 제안합니다.
3. **E2E Mock 테스트**: `tests/test_phase3_api.py`에 22개 이상의 4-Tier 테스트 케이스를 구축하고, 하드코딩 0건 정적 분석을 테스트 스위트 내에 포함하여 자동 검증하도록 설계할 것을 권장합니다.
