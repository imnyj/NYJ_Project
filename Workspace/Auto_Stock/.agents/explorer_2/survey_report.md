# Kiwoom REST API 명세 및 실거래 제어 모듈 설계 보고서 (Survey Report)

- **작성 에이전트**: `explorer_2` (API Spec Miner & Interface Designer)
- **작성 일시**: 2026-09-01T23:31:00+09:00
- **대상 프로젝트**: Auto Stock ML/RL Trader — Phase 3: 실거래 제어 모듈
- **참조 요구사항**: `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md`

---

## 1. 개요 및 목적
본 보고서는 Auto Stock 프로젝트의 'Phase 3: 실거래 제어 모듈' 구축을 위한 Kiwoom Open API REST 인터페이스의 표준 명세를 정밀 분석하고, 이를 기반으로 `core/kiwoom_api.py` 및 `modules/engine/manual_trader.py`의 클래스 구조, 메서드 시그니처, 예외 처리 체계, 보안 설정 로직을 설계한 종합 분석 보고서입니다.

---

## 2. Kiwoom Open API REST 인터페이스 표준 명세 분석

### 2.1 도메인 및 환경 (Base URLs)
Kiwoom Open API REST는 실거래 서버와 모의투자(Paper Trading) 서버를 완전히 분리된 Base URL로 제공합니다. 설정 파일의 `use_mock_server` 플래그에 따라 Base URL과 트랜잭션 ID(TR_ID)가 동적으로 전환되어야 합니다.

| 환경 구분 | Base URL | WebSocket URL | 설명 |
|---|---|---|---|
| **실거래 (Live)** | `https://openapi.kiwoom.com` | `wss://openapi.kiwoom.com/websocket` | 실제 증권 계좌 및 실자금 주문 실행 |
| **모의투자 (Mock/VTS)** | `https://openapivts.kiwoom.com` | `wss://openapivts.kiwoom.com/websocket` | 가상 모의투자 계좌 기반 테스트 실행 |

---

### 2.2 인증 체계: OAuth 2.0 Client Credentials Grant

#### 2.2.1 접근 토큰 발급 (Issue Access Token)
- **Endpoint**: `POST /oauth2/tokenP` (또는 `POST /oauth2/token`)
- **Content-Type**: `application/json; charset=utf-8`
- **Request Body**:
  ```json
  {
    "grant_type": "client_credentials",
    "appkey": "YOUR_APP_KEY",
    "appsecret": "YOUR_APP_SECRET"
  }
  ```
- **Response Format (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "Bearer",
    "expires_in": 86400,
    "access_token_token_expired": "2026-09-02 23:30:00"
  }
  ```
- **토큰 관리 수명주기 (Lifecycle & Caching)**:
  1. 발급된 토큰은 24시간(86,400초) 동안 유효합니다.
  2. 매 API 요청마다 토큰을 재발급받지 않고, 메모리 캐시에 저장하여 재사용합니다.
  3. 만료 시점 버퍼(예: 만료 10분 전) 또는 API 호출 시 401 Unauthorized 에러 발생 시 자동으로 토큰을 재발급(Auto-Refresh)하는 메커니즘을 내장합니다.

#### 2.2.2 접근 토큰 폐기 (Revoke Access Token)
- **Endpoint**: `POST /oauth2/revokeP`
- **Request Body**:
  ```json
  {
    "appkey": "YOUR_APP_KEY",
    "appsecret": "YOUR_APP_SECRET",
    "token": "ACCESS_TOKEN_TO_REVOKE"
  }
  ```
- **Response Format (200 OK)**:
  ```json
  {
    "code": "200",
    "message": "성공적으로 폐기되었습니다."
  }
  ```

---

### 2.3 공통 요청 헤더 (Common Request Headers)
모든 REST 비즈니스 API 호출 시 공통으로 요구되는 표준 헤더 규격입니다.

| 헤더 이름 | 필수 여부 | 타입 | 설명 | 예시 값 |
|---|---|---|---|---|
| `Content-Type` | 필수 | String | 요청 페이로드 인코딩 | `application/json; charset=utf-8` |
| `authorization` | 필수 | String | Bearer 접근 토큰 | `Bearer eyJhbGci...` |
| `appkey` | 필수 | String | 발급받은 App Key | `l7xx12345678...` |
| `appsecret` | 필수 | String | 발급받은 App Secret | `987654321...` |
| `tr_id` | 필수 | String | 거래 ID (기능 및 실거래/모의투자별 상이) | `FHKST01010100`, `TTTC0802U` |
| `custtype` | 선택/권장 | String | 고객 구분 (`P`: 개인, `B`: 법인) | `P` |
| `tr_cont` | 선택 | String | 연속조회 여부 (`N`: 최초/단건, `Y`: 다음페이지) | `N` |

---

### 2.4 핵심 비즈니스 API 엔드포인트 상세 규격

#### 2.4.1 주식 현재가 시세 조회 (Current Price Query)
- **용도**: 특정 종목의 현재가, 시가/고가/저가, 전일대비, 거래량 등 시세 조회
- **HTTP Method & URL**: `GET /uapi/domestic-stock/v1/quotations/inquire-price`
- **헤더 TR_ID**: `FHKST01010100` (실거래/모의투자 공통)
- **Query Parameters**:
  | 파라미터 | 타입 | 필수 | 설명 | 예시 |
  |---|---|---|---|---|
  | `FID_COND_MRKT_DIV_CODE` | String | 필수 | 시장 구분 코드 (`J`: 주식/ETF/ETN) | `J` |
  | `FID_INPUT_ISCD` | String | 필수 | 종목코드 (6자리) | `005930` |
- **응답 바디 구조**:
  ```json
  {
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다.",
    "output": {
      "iscd": "005930",
      "stck_prpr": "75000",
      "prdy_vrss": "1000",
      "prdy_vrss_sign": "2",
      "prdy_ctrt": "1.35",
      "stck_oprc": "74500",
      "stck_hgpr": "75500",
      "stck_lwpr": "74200",
      "acml_vol": "12345678",
      "acml_tr_pbmn": "925925850000"
    }
  }
  ```

#### 2.4.2 주식 시장가 주문 전송 (Market Order Transmission)
- **용도**: 특정 종목에 대한 시장가 매수(BUY) 또는 매도(SELL) 주문 전송
- **HTTP Method & URL**: `POST /uapi/domestic-stock/v1/trading/order-cash`
- **헤더 TR_ID 매핑**:
  - 실거래 매수: `TTTC0802U`
  - 실거래 매도: `TTTC0801U`
  - 모의투자 매수: `VTTC0802U`
  - 모의투자 매도: `VTTC0801U`
- **Request Body (JSON)**:
  ```json
  {
    "CANO": "12345678",
    "ACNT_PRDT_CD": "01",
    "PDNO": "005930",
    "ORD_DVSN": "01",
    "ORD_QTY": "10",
    "ORD_UNPR": "0"
  }
  ```
  | 필드명 | 타입 | 필수 | 설명 | 설정값 규칙 |
  |---|---|---|---|---|
  | `CANO` | String | 필수 | 종합계좌번호 앞 8자리 | `12345678` |
  | `ACNT_PRDT_CD` | String | 필수 | 계좌상품코드 뒤 2자리 | `01` |
  | `PDNO` | String | 필수 | 종목코드 (6자리) | `005930` |
  | `ORD_DVSN` | String | 필수 | 주문구분 코드 | `01` (시장가), `00` (지정가) |
  | `ORD_QTY` | String | 필수 | 주문 수량 (1주 이상 정수) | `"10"` |
  | `ORD_UNPR` | String | 필수 | 주문 단가 | 시장가 주문 시 반드시 `"0"` |
- **응답 바디 구조**:
  ```json
  {
    "rt_cd": "0",
    "msg_cd": "APBK0013",
    "msg1": "주문 전송이 완료되었습니다.",
    "output": {
      "KRX_FWDG_ORD_ORGNO": "00000",
      "ODNO": "0000117057",
      "ORD_TMD": "091530"
    }
  }
  ```

#### 2.4.3 주식 계좌 잔고 및 예수금 조회 (Account Balance & Deposit Query)
- **용도**: 계좌의 예수금(D+0, D+2), 총 평가액, 순자산, 보유 종목별 수량/평단가/평가손익 조회
- **HTTP Method & URL**: `GET /uapi/domestic-stock/v1/trading/inquire-balance`
- **헤더 TR_ID 매핑**:
  - 실거래: `TTTC8434R`
  - 모의투자: `VTTC8434R`
- **Query Parameters**:
  | 파라미터 | 타입 | 필수 | 설명 | 기본값 |
  |---|---|---|---|---|
  | `CANO` | String | 필수 | 계좌번호 8자리 | `12345678` |
  | `ACNT_PRDT_CD` | String | 필수 | 상품코드 2자리 | `01` |
  | `AFHR_FLPR_YN` | String | 필수 | 시간외단일가여부 | `N` |
  | `OFL_YN` | String | 필수 | 오프라인여부 | `N` |
  | `INQR_DVSN` | String | 필수 | 조회구분 (`01`: 대출일별, `02`: 종목별) | `02` |
  | `UNPR_DVSN` | String | 필수 | 단가구분 | `01` |
  | `FUND_STTL_ICLD_YN`| String | 필수 | 펀드결제분포함여부 | `N` |
  | `FNCG_AMT_AUTO_RDPT_YN` | String | 필수 | 융자금액자동상환여부 | `N` |
  | `PRCS_DVSN` | String | 필수 | 처리구분 (`00`: 전일매매포함) | `00` |
  | `CTX_AREA_FK100` | String | 필수 | 연속조회검색조건100 | `""` |
  | `CTX_AREA_NK100` | String | 필수 | 연속조회키100 | `""` |
- **응답 바디 구조**:
  ```json
  {
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다.",
    "output1": [
      {
        "pdno": "005930",
        "prdt_name": "삼성전자",
        "hld_qty": "10",
        "ord_psbl_qty": "10",
        "pchs_avg_pric": "74500.0000",
        "pchs_amt": "745000",
        "prpr": "75000",
        "evlu_amt": "750000",
        "evlu_pfls_amt": "5000",
        "evlu_pfls_rt": "0.67"
      }
    ],
    "output2": [
      {
        "dnca_tot_amt": "10000000",
        "nxdy_excc_amt": "9255000",
        "prvs_rcdl_excc_amt": "9255000",
        "tot_evlu_amt": "10005000",
        "nass_amt": "10005000",
        "pchs_amt_smtl_amt": "745000",
        "evlu_amt_smtl_amt": "750000",
        "evlu_pfls_smtl_amt": "5000"
      }
    ]
  }
  ```

---

## 3. 발견된 기능 및 엣지 케이스 (Features Discovered & Edge Cases)

### 3.1 Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| F1 | Auth | Token Issuance | OAuth 2.0 Client Credentials 기반 Access Token 발급 및 유효기간 추출 | `appkey`, `appsecret`, `grant_type` | `access_token`, `expires_in`, `token_type` | `KiwoomAuthError` (401/400 응답, 키 불일치) | Kiwoom Open API REST 명세서 |
| F2 | Auth | Token Auto-Refresh | 토큰 만료 10분 전 자동 갱신 및 메모리 캐싱 관리 | 토큰 만료시점, 캐시된 토큰 | 유효한 `Bearer` 토큰 문자열 | 만료 시 즉시 재발급 시도, 실패 시 에러 전파 | Open API 인증 가이드라인 |
| F3 | Config | Live/Mock Switch | `use_mock_server` 플래그에 따라 도메인 및 TR_ID 동적 분기 | `use_mock_server: bool` | `base_url`, 대상 `tr_id` 세트 | 잘못된 설정값 전달 시 기본값(Mock 또는 Live) 안전 Fallback | ORIGINAL_REQUEST §R1 |
| F4 | Market Data | Current Price Query | 특정 종목코드(6자리)의 현재가, 전일대비, 등락률, 거래량 조회 | `symbol: str` (예: "005930") | `PriceQuote` (Decimal 현재가, 거래량 등) | `KiwoomQueryError` (종목코드 미존재, 통신 오류) | Kiwoom 시세 API 명세 |
| F5 | Order | Market Buy Order | 시장가 매수 주문 전송 및 주문번호 반환 | `symbol: str`, `quantity: int` | `OrderResult` (주문번호, 주문시각, 상태) | `KiwoomOrderError` (예수금 부족, 호가 범위 초과) | Kiwoom 주문 API 명세 |
| F6 | Order | Market Sell Order | 시장가 매도 주문 전송 및 주문번호 반환 | `symbol: str`, `quantity: int` | `OrderResult` (주문번호, 주문시각, 상태) | `KiwoomOrderError` (보유수량 부족, 주문 거부) | Kiwoom 주문 API 명세 |
| F7 | Account | Balance & Position Query | 계좌 총 예수금, 평가금액, 순자산 및 종목별 잔고 리스트 조회 | 없음 (설정 계좌번호 사용) | `AccountBalance` (예수금, 평가손익, Position 목록) | `KiwoomQueryError` (계좌 비밀번호/번호 불일치) | Kiwoom 잔고 API 명세 |
| F8 | Manual Trading | CLI Order Interface | CLI 환경에서 대화형(Interactive) 및 단발성 주문 파라미터 입력 및 검증 | 종목코드, 매수/매도, 수량 | 유효성 검증된 주문 실행 및 결과 수신 | 파라미터 형식 불일치 시 안내 메시지 후 재입력 유도 | ORIGINAL_REQUEST §R2 |
| F9 | Manual Trading | Balance Diff Reporter | 주문 체결 전/후 계좌 잔고를 비교하여 현금 변동, 수량 변동을 포맷팅 출력 | `balance_before`, `balance_after`, `order_result` | 콘솔 포맷 테이블 출력 (CLI Display) | 잔고 조회 실패 시에도 주문 결과는 안전하게 보존 | ORIGINAL_REQUEST §R2 |
| F10 | Security | Secret Manager | API Key, Secret, 계좌번호를 소스 코드에 노출하지 않고 YAML/.env에서 로드 | `config/settings.yaml`, 환경변수 | `KiwoomConfig` 객체 | 필수 키 누락 시 명확한 안내 예외 발생 | ORIGINAL_REQUEST §R3 |

### 3.2 Edge Cases
| # | Feature | Input | Observed / Expected Behavior |
|---|---|---|---|
| E1 | Token Issuance | 잘못된 `appkey` 또는 `appsecret` 전달 | HTTP 401 또는 `rt_cd != "0"` 반환 -> `KiwoomAuthError("인증에 실패하였습니다.")` 발생 |
| E2 | Token Refresh | API 호출 중 토큰이 만료되어 HTTP 401 수신 | 기존 캐시 무효화 후 `issue_token()` 즉시 재호출, 헤더 갱신 후 원래 요청 1회 자동 재시도 (Auto-retry) |
| E3 | Live/Mock Switch | `use_mock_server=True` 시 매수 주문 | Base URL이 `openapivts.kiwoom.com`으로 설정되고 `tr_id`가 `VTTC0802U`로 전송됨 |
| E4 | Market Order | `quantity <= 0` 또는 부동소수점 수량 입력 | API 호출 전 클라이언트 단에서 `ValueError("주문 수량은 1 이상의 정수여야 합니다.")` 발생 차단 |
| E5 | Market Order | 잘못된 종목코드 (예: `"999999"` 또는 문자 포함 `"ABC"`) | 종목코드 정규식 검증(`^[0-9]{6}$`) 실패 시 즉시 에러 차단, 또는 API 서버 거절 응답 파싱 |
| E6 | Balance Query | 보유 종목이 0개인 신규/현금 계좌 조회 | `output1`이 빈 리스트(`[]`)로 반환되더라도 `AccountBalance.positions = []`로 정상 파싱 및 예수금 정확히 집계 |
| E7 | Rate Limiting | 초당 호출 제한(초당 5회 등) 초과 발생 (HTTP 429) | 지수 백오프(Exponential Backoff with Jitter)로 0.5초 대기 후 최대 3회 재시도, 최종 실패 시 `KiwoomRateLimitError` 발생 |
| E8 | Secret Loading | 설정 파일 및 환경 변수에 `app_key` 미지정 | `ValueError("Kiwoom APP_KEY가 설정되지 않았습니다. config/settings.yaml 또는 환경변수를 확인하세요.")` 발생 |

---

## 4. 소프트웨어 아키텍처 및 모듈 상세 설계

### 4.1 `core/kiwoom_api.py` 구조 설계

#### 4.1.1 예외 클래스 계층 구조
```python
class KiwoomAPIError(Exception):
    """키움 API 기본 예외 클래스"""
    def __init__(self, message: str, code: Optional[str] = None, raw_response: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.raw_response = raw_response

class KiwoomAuthError(KiwoomAPIError):
    """인증 및 토큰 발급/갱신 관련 예외"""
    pass

class KiwoomOrderError(KiwoomAPIError):
    """주문 전송 및 체결 실패 예외 (예: 잔고 부족, 주문 거부)"""
    pass

class KiwoomQueryError(KiwoomAPIError):
    """시세 및 계좌 잔고 조회 실패 예외"""
    pass

class KiwoomRateLimitError(KiwoomAPIError):
    """API 호출 제한 초과 예외 (HTTP 429)"""
    pass

class KiwoomNetworkError(KiwoomAPIError):
    """네트워크 연결 끊김 및 타임아웃 예외"""
    pass
```

#### 4.1.2 설정 및 데이터 모델 (Dataclasses)
```python
@dataclass
class KiwoomConfig:
    """키움 API 연동 설정 데이터 모델"""
    app_key: str
    app_secret: str
    account_no: str  # 8자리 또는 10자리 (하이픈 제외)
    account_product_code: str = "01"
    use_mock_server: bool = True
    base_url_live: str = "https://openapi.kiwoom.com"
    base_url_mock: str = "https://openapivts.kiwoom.com"
    timeout: float = 10.0
    max_retries: int = 3

    @property
    def base_url(self) -> str:
        return self.base_url_mock if self.use_mock_server else self.base_url_live

    @property
    def cano(self) -> str:
        """종합계좌번호 앞 8자리"""
        clean_no = self.account_no.replace("-", "").strip()
        return clean_no[:8]

    @property
    def acnt_prdt_cd(self) -> str:
        """계좌상품코드 뒤 2자리 (기본 01)"""
        clean_no = self.account_no.replace("-", "").strip()
        if len(clean_no) >= 10:
            return clean_no[8:10]
        return self.account_product_code

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KiwoomConfig":
        ...

    @classmethod
    def from_yaml(cls, yaml_path: str = "config/settings.yaml") -> "KiwoomConfig":
        ...

    @classmethod
    def from_env(cls) -> "KiwoomConfig":
        ...
```

```python
@dataclass
class PriceQuote:
    """현재가 시세 데이터 모델"""
    symbol: str
    current_price: Decimal
    price_change: Decimal
    change_rate: Decimal
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    volume: int
    trade_amount: Decimal
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class OrderResult:
    """주문 실행 결과 데이터 모델"""
    order_id: str
    symbol: str
    side: OrderSide  # OrderSide.BUY 또는 OrderSide.SELL
    quantity: int
    order_type: OrderType  # OrderType.MARKET
    order_time: str
    message: str
    raw_response: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PositionItem:
    """개별 보유 종목 잔고 모델"""
    symbol: str
    name: str
    quantity: int
    available_quantity: int
    avg_purchase_price: Decimal
    purchase_amount: Decimal
    current_price: Decimal
    eval_amount: Decimal
    eval_pnl: Decimal
    eval_pnl_rate: Decimal

@dataclass
class AccountBalance:
    """계좌 잔고 및 자산 현황 데이터 모델"""
    account_no: str
    deposit_received: Decimal        # D+0 예수금 총액
    available_cash: Decimal          # D+2 출금/주문가능 현금
    total_eval_amount: Decimal       # 주식 총 평가금액
    total_asset: Decimal             # 총 순자산금액
    total_eval_pnl: Decimal          # 총 평가손익 합계
    positions: List[PositionItem] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
```

#### 4.1.3 TokenManager 클래스 설계
```python
class TokenManager:
    """OAuth 2.0 토큰 발급 및 메모리 캐싱, 자동 갱신 관리자"""
    def __init__(self, config: KiwoomConfig, session: Optional[requests.Session] = None):
        self.config = config
        self.session = session or requests.Session()
        self._access_token: Optional[str] = None
        self._expires_at: Optional[datetime] = None

    def get_access_token(self, force_refresh: bool = False) -> str:
        """유효한 Access Token을 반환하며, 만료 임박 시 자동 재발급합니다."""
        if force_refresh or self.is_expired():
            self.refresh_token()
        return self._access_token

    def is_expired(self, buffer_seconds: int = 600) -> bool:
        """만료 버퍼(기본 10분)를 감안하여 만료 여부를 판별합니다."""
        if not self._access_token or not self._expires_at:
            return True
        return datetime.now() + timedelta(seconds=buffer_seconds) >= self._expires_at

    def refresh_token(self) -> str:
        """토큰 발급 엔드포인트를 호출하여 새 토큰을 획득합니다."""
        url = f"{self.config.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
        }
        headers = {"Content-Type": "application/json; charset=utf-8"}
        ...
```

#### 4.1.4 KiwoomAPIClient 클래스 메서드 시그니처 설계
```python
class KiwoomAPIClient:
    """
    Kiwoom Open API REST 통합 클라이언트.
    OAuth2 인증, 시세 조회, 시장가 주문, 계좌 잔고 조회를 캡슐화합니다.
    """
    def __init__(self, config: Optional[KiwoomConfig] = None):
        self.config = config or KiwoomConfig.from_env()
        self.session = requests.Session()
        self.token_manager = TokenManager(self.config, self.session)

    def __enter__(self) -> "KiwoomAPIClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """세션 종료 및 리소스 정리"""
        if self.session:
            self.session.close()

    def _get_common_headers(self, tr_id: str, tr_cont: str = "N") -> Dict[str, str]:
        """표준 인증 및 비즈니스 헤더를 생성합니다."""
        token = self.token_manager.get_access_token()
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
            "tr_cont": tr_cont,
        }

    def _request(
        self,
        method: str,
        path: str,
        tr_id: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        is_order: bool = False,
    ) -> Dict[str, Any]:
        """공통 요청 래퍼 (재시도, 에러 파싱, 401 토큰 만료 자동 복구)"""
        ...

    def get_current_price(self, symbol: str) -> PriceQuote:
        """
        특정 종목의 현재가 시세를 조회합니다.
        
        Args:
            symbol (str): 6자리 종목코드 (예: '005930')
        Returns:
            PriceQuote: 파싱된 현재가 시세 정보
        Raises:
            KiwoomQueryError: 종목코드 불일치 또는 API 에러
            KiwoomNetworkError: 네트워크 장애
        """
        ...

    def send_market_order(
        self,
        symbol: str,
        side: Union[OrderSide, str],
        quantity: int,
    ) -> OrderResult:
        """
        지정된 종목에 대해 시장가 매수/매도 주문을 전송합니다.
        
        Args:
            symbol (str): 6자리 종목코드
            side (OrderSide or str): 'BUY' 또는 'SELL'
            quantity (int): 주문 수량 (1 이상의 정수)
        Returns:
            OrderResult: 주문 접수 결과 (주문번호, 접수시각 등)
        Raises:
            ValueError: 유효하지 않은 파라미터
            KiwoomOrderError: 주문 거부, 잔고 부족 등
        """
        ...

    def get_account_balance(self) -> AccountBalance:
        """
        현재 계좌의 예수금 및 보유 주식 잔고 현황을 조회합니다.
        
        Returns:
            AccountBalance: 파싱된 계좌 잔고 및 종목별 보유 현황
        Raises:
            KiwoomQueryError: 계좌 조회 실패
        """
        ...
```

---

### 4.2 `modules/engine/manual_trader.py` 구조 설계

#### 4.2.1 클래스 구조 및 메서드 시그니처
```python
@dataclass
class TradeExecutionSummary:
    """수동 매매 실행 전/후 종합 요약 리포트"""
    order_result: OrderResult
    balance_before: AccountBalance
    balance_after: AccountBalance
    cash_diff: Decimal
    shares_diff: int
    symbol: str
    side: OrderSide
    quantity: int

class ManualTrader:
    """
    CLI 기반 수동 매매 제어기.
    사용자 입력을 안전하게 파싱 및 검증하고, Kiwoom API를 통해 주문을 실행하며,
    체결 전/후 계좌 잔고 변동 내역을 시각적으로 보고합니다.
    """
    def __init__(self, client: Optional[KiwoomAPIClient] = None, config: Optional[KiwoomConfig] = None):
        self.config = config or KiwoomConfig.from_env()
        self.client = client or KiwoomAPIClient(self.config)

    def validate_inputs(self, symbol: str, side_str: str, quantity_val: Union[int, str]) -> Tuple[str, OrderSide, int]:
        """
        종목코드, 주문방향, 주문수량의 형식 유효성을 엄격히 검증합니다.
        
        Rules:
        1. symbol: 6자리 숫자 문자열 (정규식 `^[0-9]{6}$`)
        2. side: 'BUY' (매수), 'SELL' (매도) 대소문자 무관 지원
        3. quantity: 1 이상의 양의 정수
        """
        ...

    def execute_manual_order(
        self,
        symbol: str,
        side: Union[OrderSide, str],
        quantity: int,
    ) -> TradeExecutionSummary:
        """
        수동 주문의 전체 라이프사이클을 안전하게 실행합니다.
        1. 주문 전 계좌 잔고 조회 (balance_before)
        2. 현재가 조회 및 사전 잔고/보유수량 검증
        3. 시장가 주문 전송 (send_market_order)
        4. 주문 후 계좌 잔고 조회 (balance_after)
        5. 변동 내역 산출 및 TradeExecutionSummary 생성
        """
        ...

    def print_balance_diff(self, summary: TradeExecutionSummary) -> None:
        """
        주문 전/후 잔고 변동 내역을 CLI 콘솔에 명확한 테이블 형태로 출력합니다.
        """
        ...

    def run_interactive_cli(self) -> None:
        """
        사용자와 상호작용하는 대화형 CLI 메인 루프를 실행합니다.
        - 종목코드, 매수/매도, 수량 입력 프롬프트
        - 최종 주문 확인 (Y/N Confirmation)
        - 주문 실행 및 결과 출력
        """
        ...

    def run_cli_from_args(self, args: Optional[List[str]] = None) -> int:
        """
        argparse 기반의 단발성 CLI 커맨드 실행기.
        예: python -m modules.engine.manual_trader --symbol 005930 --side BUY --qty 10
        """
        ...
```

#### 4.2.2 잔고 변동 출력 형식 (Console Output Mockup)
```
================================================================================
                           수동 주문 체결 리포트
================================================================================
주문 번호: 0000117057 | 체결 시각: 09:15:30
대상 종목: 005930 (삼성전자) | 주문 구분: 시장가 BUY | 수량: 10 주
--------------------------------------------------------------------------------
항목                    주문 전 (Before)       주문 후 (After)        변동액 (Diff)
--------------------------------------------------------------------------------
D+2 예수금 (현금):      10,000,000 원          9,248,875 원           -751,125 원
보유 수량:              0 주                   10 주                  +10 주
총 평가 금액:           10,000,000 원          9,998,875 원           -1,125 원 (수수료)
================================================================================
```

---

## 5. 보안 및 설정 파일 분리 전략 (Secret Management)

### 5.1 설정 파일 구조 (`config/settings.yaml`)
민감 정보 하드코딩을 원천 차단하고 환경별 설정을 지원하기 위해 YAML 설정 및 환경변수 오버라이드 시스템을 구축합니다.

```yaml
# config/settings.yaml
kiwoom:
  # API 자격 증명 (환경변수가 없을 경우 기본값으로 사용)
  app_key: "${KIWOOM_APP_KEY}"
  app_secret: "${KIWOOM_APP_SECRET}"
  account_no: "${KIWOOM_ACCOUNT_NO}"
  account_product_code: "01"
  
  # 서버 환경 스위치 (true: 모의투자, false: 실거래)
  use_mock_server: true
  
  # 엔드포인트 URL
  base_url_live: "https://openapi.kiwoom.com"
  base_url_mock: "https://openapivts.kiwoom.com"
  
  # 네트워크 설정
  timeout: 10.0
  max_retries: 3

trading:
  default_order_type: "MARKET"
  slippage_rate: 0.001
  commission_rate: 0.00015
  tax_rate: 0.0018
```

### 5.2 우선순위 기반 설정 로드 규칙
1. **1순위 (최우선)**: OS 환경 변수 (`KIWOOM_APP_KEY`, `KIWOOM_APP_SECRET`, `KIWOOM_ACCOUNT_NO`, `USE_MOCK_SERVER`)
2. **2순위**: `config/settings.yaml` (또는 `.env` 파일)
3. **3순위**: 코드 내 안전한 기본값 (예: `base_url_mock`, `timeout=10.0`)
4. **정적 검사 보장**: `git`에 커밋되는 소스 코드(`.py`) 내에 실제 App Key나 계좌번호 리터럴이 0건임을 보장하는 정적 분석 테스트 포함.

---

## 6. 테스트 및 모킹 검증 전략 (`tests/test_phase3_api.py`)

실제 키움 서버에 연결하지 않고도 모든 비즈니스 로직과 예외 처리의 100% 무결성을 검증하기 위해 `unittest.mock`을 활용한 정밀 테스트 스위트를 설계합니다.

### 6.1 테스트 케이스 매트릭스
| 테스트 메서드 | 검증 대상 | 모킹 대상 | 검증 포인트 |
|---|---|---|---|
| `test_token_issue_and_cache` | `TokenManager.get_access_token` | `POST /oauth2/tokenP` | 1. 최초 발급 시 200 응답 파싱<br>2. 2회차 호출 시 캐시 반환(HTTP 미호출)<br>3. 만료 시 자동 재발급 |
| `test_domain_and_tr_toggle` | `KiwoomAPIClient` | `use_mock_server` 토글 | 1. `use_mock_server=True` 시 `openapivts.kiwoom.com` 및 `VTTC...` TR_ID 전송<br>2. `False` 시 `openapi.kiwoom.com` 및 `TTTC...` 전송 |
| `test_get_current_price` | `KiwoomAPIClient.get_current_price` | `GET /uapi/.../inquire-price` | 정상 시세 수신 시 Decimal 파싱(75000원 등) 및 PriceQuote 반환 |
| `test_market_buy_and_sell_order` | `KiwoomAPIClient.send_market_order` | `POST /uapi/.../order-cash` | 1. BUY 주문 시 `ORD_UNPR="0"`, `ORD_DVSN="01"` 파라미터 검증<br>2. OrderResult 객체의 order_id 정상 파싱 |
| `test_get_account_balance` | `KiwoomAPIClient.get_account_balance` | `GET /uapi/.../inquire-balance` | 예수금 및 보유 종목 리스트(`output1`, `output2`) Decimal 변환 및 AccountBalance 생성 |
| `test_manual_trader_e2e_flow` | `ManualTrader.execute_manual_order` | Client 전체 모킹 | "토큰 발급 -> 시세 조회 -> 매수 주문 -> 잔고 조회 -> 요약 출력" 전체 흐름 성공 검증 |
| `test_insufficient_balance_error` | `KiwoomAPIClient`, `ManualTrader` | 주문 API 거절 응답 | API 에러 응답 수신 시 `KiwoomOrderError` 발생 및 사용자 친화적 메시지 출력 |
| `test_token_expired_auto_recovery` | `KiwoomAPIClient._request` | 401 Unauthorized 후 200 OK | 401 응답 수신 시 토큰 강제 갱신 후 재시도 성공 검증 |
| `test_zero_hardcoded_secrets` | 전체 소스 코드 | 정적 파일 탐색 | `.py` 파일 내에 하드코딩된 API Key/Secret 리터럴이 0건임을 정규식으로 입증 |

---

## 7. 결론 및 개발 가이드
1. Kiwoom Open API REST는 OAuth2.0 기반 토큰 인증과 실거래/모의투자 분기 체계를 명확히 요구합니다.
2. `core/kiwoom_api.py`는 토큰 생명주기 관리와 REST 통신을 책임지며, 엄격한 Decimal 변환과 예외 계층화를 통해 안정성을 확보합니다.
3. `modules/engine/manual_trader.py`는 CLI 입력 검증과 주문 실행, 전/후 잔고 변동 시각화에 집중하여 사용자에게 안전한 매매 제어 환경을 제공합니다.
4. 설정과 자격 증명은 `config/settings.yaml` 및 환경변수로 완벽히 분리하여 보안 표준을 충족합니다.
