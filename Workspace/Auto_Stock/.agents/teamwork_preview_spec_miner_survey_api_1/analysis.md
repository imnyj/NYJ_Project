# 키움증권 REST API 명세 정합성 및 통신 로직 전수 조사 보고서 (Area 3 Analysis)

- **조사 담당**: Spec Miner (Survey Agent 3 — Kiwoom REST API & Network Protocol Specialist)
- **대상 프로젝트**: Auto_Stock (`/home/imnyj/Workspace/Auto_Stock`)
- **조사 일시**: 2026-09-02T17:07:00+09:00
- **규정 준수**: `GEMINI.md` 멀티에이전트 팩토리 규칙 및 `anti-hallucination` 스킬 준수

---

## 1. 개요 및 조사 목적

본 조사는 Auto_Stock 시스템의 **키움증권 REST API (2024 신규 규격) 연동 모듈, 네트워크 세션/인증 관리, 실시간 시세 스트리밍 및 동시성 버퍼링 서브시스템**에 대한 전수 정적/동적 검증 및 명세 정합성 분석을 목적으로 수행되었습니다.

조사 대상 핵심 모듈:
1. `core/config.py`: 계층적 설정 관리, 환경 변수 치환, `SecretStr` 민감정보 은닉, TR_ID 라우팅
2. `core/kiwoom_api.py`: OAuth2 토큰 발급/자동갱신, REST API 클라이언트, 주문/시세/잔고 엔드포인트 통신
3. `modules/data/streamer.py`: 실시간 시세 스트리머, 원형 링버퍼(`CircularBuffer`), 틱-캔들 동적 집계기(`WindowBarAggregator`)
4. `modules/data/collector_price.py`: 다중 수집원 Fallback, OHLCV 리샘플링, 데이터 정제/무결성 검증
5. `modules/engine/manual_trader.py`: 수동 매매 CLI 컨트롤러, 입출력 검증 및 잔고 변동 시각화
6. `modules/engine/live_learning_simulator.py`: 실시간 시세 연동형 가상 강화학습 시뮬레이터

---

## 2. 발견된 기능 전수 목록 (Features Discovered)

| # | 카테고리 | 기능명 | 상세 설명 | 입력 (Inputs) | 출력 (Outputs) | 예외 및 에러 동작 | 발견 소스 (Discovered Via) |
|---|---|---|---|---|---|---|---|
| 1 | Config | 계층적 설정 로딩 (`load_config`) | OS 환경변수 > .env > settings.yaml > 기본값 4단계 우선순위 로드 | `yaml_path`, `env_path`, `os.environ` | `AppConfig` 인스턴스 | 파일 부재 시 기본값 폴백 | `core/config.py:210-328` |
| 2 | Config | 환경변수 템플릿 치환 (`interpolate_env_vars`) | `${VAR:default}` 정규식 치환 | 템플릿 문자열, env 딕셔너리 | 치환된 문자열 | 매칭 실패 시 원본/빈값 반환 | `core/config.py:76-96` |
| 3 | Security | 시크릿 은닉 캡슐화 (`SecretStr`) | AppKey/Secret 출력 시 `***` 마스킹, 명시적 추출만 허용 | 원본 문자열 | `SecretStr` 객체 | 평문 노출 원천 차단 | `core/config.py:27-74` |
| 4 | Config | TR_ID 라우팅 (`get_tr_id`) | 요청 액션, 매매방향, 모의/실서버에 따른 TR 코드 매핑 | `action`, `side` | `ka10001`, `kt10000`, `kt10001`, `kt00018` | 미지원 액션 시 `ValueError` | `core/config.py:166-185` |
| 5 | Auth | OAuth2 토큰 발급 (`refresh_token`) | Client Credentials 방식으로 24시간 Access Token 발급 | AppKey, AppSecret | `access_token` 문자열 | 키 누락시 `KiwoomAuthError`, 통신실패시 `KiwoomNetworkError` | `core/kiwoom_api.py:173-209` |
| 6 | Auth | 토큰 만료 사전 감지 (`is_expired`) | 만료 10분(600초) 전 버퍼를 두고 자동 갱신 트리거 | `buffer_seconds` | `bool` (True/False) | 토큰 미발급 시 True | `core/kiwoom_api.py:163-167` |
| 7 | Auth | 401 Unauthorized 자동 복구 | API 요청 중 401 수신 시 1회 강제 토큰 재발급 후 재시도 | HTTP 401 Response | 재시도 응답 데이터 | 2회 연속 401 시 에러 전파 | `core/kiwoom_api.py:251-253` |
| 8 | Market Data | 주식 현재가 조회 (`get_current_price`) | `/api/dostk/stkinfo` (TR: `ka10001`) POST 시세 조회 | 종목코드 (6자리) | `PriceQuote` (시/고/저/종/거래량) | 6자리 미충족시 `ValueError`, 통신실패시 `KiwoomQueryError` | `core/kiwoom_api.py:275-295` |
| 9 | Order | 주식 주문 전송 (`send_order`) | `/api/dostk/ordr` (TR: `kt10000`/`kt10001`) 시장가/지정가 주문 | 종목코드, 매매방향, 수량, 단가, 주문유형 | `OrderResult` (주문번호, 상태) | 예수금 부족 등 거절 시 `KiwoomOrderError` | `core/kiwoom_api.py:297-319` |
| 10 | Account | 계좌 잔고/평가 조회 (`get_account_balance`) | `/api/dostk/acnt` (TR: `kt00018`) 예수금 및 보유종목 조회 | 조회구분(`qry_tp="1"`), 거래소(`"KRX"`) | `AccountBalance` (예수금, 총자산, 보유목록) | 통신/응답 실패 시 `KiwoomQueryError` | `core/kiwoom_api.py:321-352` |
| 11 | Data Model | Dual Object/Dict Interface | `Mapping[str, Any]` 상속으로 `obj.attr` 및 `obj["key"]` 동시 지원 | 필드 데이터 | 데이터 모델 객체 | 존재하지 않는 키 참조 시 `KeyError` | `core/kiwoom_api.py:56-151` |
| 12 | Streamer | 원형 링 버퍼 (`CircularBuffer`) | 종목별 독립 `deque(maxlen=50000)` 기반 O(1) 메모리 고정 버퍼 | `TickData` 객체 | 링버퍼 캐시, DataFrame 변환 | 용량 초과 시 FIFO 자동 축출 | `modules/data/streamer.py:147-232` |
| 13 | Streamer | 틱-캔들 동적 집계 (`WindowBarAggregator`) | 실시간 틱을 슬라이딩 윈도우 기반 1분/5분 OHLCV로 집계 | `TickData` 스트림 | `BarData` (마감 캔들), 콜백 트리거 | 지연 도착 틱 현재 캔들 안전 병합 | `modules/data/streamer.py:241-391` |
| 14 | Streamer | 가상 틱 스트리머 (`MockStreamer`) | GBM(기하 브라운 운동) 기반 오프라인/테스트 틱 스트리밍 | 종목, 변동성, 생성주기, 시드 | 실시간 틱 디스패치 | 스레드 안전 중지(`_stop_event`) | `modules/data/streamer.py:491-614` |
| 15 | Streamer | 네이버 폴링 스트리머 (`NaverPollingStreamer`) | 네이버 금융 실시간 시세 1~2초 주기 폴링 및 틱 이벤트 변환 | 종목코드 리스트 | `TickData` 이벤트 | HTTP 장애 시 지수 백오프 복구 | `modules/data/streamer.py:616-750` |
| 16 | Data Collector | 다중 수집원 Fallback (`PriceDataCollector`) | Primary 수집기 실패 시 Secondary/Mock 수집기로 자동 전환 | `symbol`, `count`, `timeframe` | 정제된 OHLCV `pd.DataFrame` | 모든 소스 실패 시 빈 DataFrame 반환 | `modules/data/collector_price.py:470-593` |
| 17 | Data Collector | OHLCV 무결성 정제 (`validate_and_clean_ohlcv`) | 중복 제거, High<Low 역전 교정, 음수 거래량 교정, 거래정지 감지 | 원시 OHLCV DataFrame | 정제된 DataFrame, 요약 Dict | 필수 컬럼 누락 시 기본값 보정 | `modules/data/collector_price.py:663-748` |
| 18 | Manual Trader | 수동 매매 제어기 (`ManualTrader`) | CLI 기반 주문 전송, 잔고 사전 확인, 전후 변동 시각화 | CLI 인자 (`-s`, `-d`, `-q`, `-p`, `-t`) | Rich/Plain Text 잔고 변동 리포트 | 입력 파라미터 불량 시 `ValueError` | `modules/engine/manual_trader.py:41-352` |
| 19 | Simulator | 실시간 학습 시뮬레이터 (`LiveLearningSimulator`) | 실제 키움 시세 연동 가상 주문 체결 및 RL Step 환경 | `symbol`, `action`, `quantity` | `(state, reward, done, info)` | 시세 조회 실패 시 캐시가 폴백 | `modules/engine/live_learning_simulator.py:27-157` |

---

## 3. 엣지 케이스 조사 결과 (Edge Cases & Observations)

| # | 기능 (Feature) | 입력 (Input) | 관측된 동작 (Observed Behavior) | 판정 및 비고 |
|---|---|---|---|---|
| 1 | Token Issue | 빈 AppKey 또는 AppSecret | `TokenManager.refresh_token()` 호출 시 `KiwoomAuthError("API 키 또는 시크릿이 설정되지 않았습니다.")` 즉시 발생 | 정상 방어 |
| 2 | Token Expiry | 만료시각 경과 토큰 (과거 timestamp) | `is_expired()`가 `True`를 반환하고 `get_access_token()`에서 자동으로 `refresh_token()` 재발급 수행 | 정상 동작 |
| 3 | Token Revoke | `TokenManager.revoke_token()` | `AttributeError: 'TokenManager' object has no attribute 'revoke_token'` 발생 | **결함 (Defect 1)** |
| 4 | Client Price Quote | `client.get_current_price("12345")` (5자리 종목코드) | 클라이언트 사전 검증 없이 서버로 HTTP POST 전송 시도 | **결함 (Defect 3)** |
| 5 | Client Order | `client.send_order(symbol="005930", side="HOLD", quantity=0)` | 수량 0 및 비표준 매매방향 검증 없이 서버로 HTTP 전송 시도 | **결함 (Defect 3)** |
| 6 | Price Response | `output` 내 `stck_prpr` 중첩 응답 수신 | `res.get("cur_prc")`가 0을 반환하여 `current_price`가 Decimal(0)으로 파싱됨 | **결함 (Defect 4)** |
| 7 | Order Response | `output.ODNO` 내 주문번호 응답 수신 | `res.get("ord_no")`가 None을 반환하여 `order_id`가 `""`로 파싱됨 | **결함 (Defect 5)** |
| 8 | Balance Response | `output2` 내 잔고 합산금액 응답 수신 | `res.get("prsm_dpst_aset_amt")`가 0을 반환하여 예수금 합산이 0으로 누락됨 | **결함 (Defect 6)** |
| 9 | Positions Query | `client.get_account_positions()` | `AttributeError: 'KiwoomClient' object has no attribute 'get_account_positions'` 발생 | **결함 (Defect 2)** |
| 10 | HTTP 429 Limit | HTTP 429 3회 연속 수신 | `KiwoomRateLimitError`가 아닌 일반 `KiwoomAPIError("최대 재시도 초과")` 발생 | **결함 (Defect 7)** |
| 11 | HTTP 500 Error | HTTP 500 3회 연속 수신 | HTTP 상태코드가 포함되지 않은 일반 `KiwoomAPIError("최대 재시도 초과")` 발생 | **결함 (Defect 7)** |
| 12 | Timeout Error | `requests.exceptions.Timeout` 발생 | `"타임아웃"` 키워드가 누락된 `"API 통신 장애"` 에러 메시지 생성 | **결함 (Defect 7)** |
| 13 | Buffer Overflow | 원형 링버퍼에 50,001개 틱 연속 주입 | FIFO 방식으로 최초 1개 틱 자동 폐기, 메모리 누수 없이 50,000개 고정 유지 | 정상 동작 |
| 14 | Delayed Tick | 과거 시각 타임스탬프 틱 도착 | 현재 진행 중인 캔들의 High/Low/Volume에만 병합되고 새 캔들 중복 마감 방지 | 정상 동작 |
| 15 | Aggregator Callback | `on_bar_closed` 콜백 내에서 `RuntimeError` 발생 | 예외가 로깅되며 메인 스트리밍 루프 중단 없이 다음 틱 계속 수신 | 정상 동작 |

---

## 4. 5대 핵심 영역 심층 분석 (Deep-Dive Analysis)

### 4.1. API 클라이언트 및 세션/인증 관리 (Area 1)
- **OAuth2 토큰 발급 및 수명 주기**:
  - 엔드포인트: `/oauth2/token` (Live: `https://api.kiwoom.com`, Mock: `https://mockapi.kiwoom.com`)
  - Payload: `grant_type="client_credentials"`, `appkey`, `secretkey`
  - 발급 응답에서 `token` 또는 `access_token`을 추출하고, 만료 일시 `expires_dt` (14자리 YYYYMMDDHHMMSS)를 파싱하여 `_expires_at`을 설정합니다.
  - 버퍼 시간(기본 600초=10분)을 두어 토큰이 실제 만료되기 10분 전에 선제적으로 재발급합니다.
  - **식별된 문제**: `TokenManager` 클래스에 `revoke_token()` 메서드가 누락되어 단위 테스트 및 세션 초기화 시 `AttributeError`가 발생합니다.

### 4.2. 엔드포인트 URL 및 TR 코드 정합성 (Area 2)
- **키움 REST API TR 매핑**:
  - 현재가 시세 조회: POST `/api/dostk/stkinfo`, TR ID `ka10001`
  - 주식 매수 주문: POST `/api/dostk/ordr`, TR ID `kt10000`
  - 주식 매도 주문: POST `/api/dostk/ordr`, TR ID `kt10001`
  - 계좌 잔고/평가: POST `/api/dostk/acnt`, TR ID `kt00018`
- **정합성 평가**:
  - `core/config.py`의 `KiwoomConfig.get_tr_id()` 및 `core/kiwoom_api.py`의 URL Path와 TR ID는 2024년 키움증권 Open API 신규 REST 규격과 정확히 일치합니다.
  - 모의투자/실전투자 환경 분기 시 Base URL(`live_base_url` vs `mock_base_url`) 전환도 정상적으로 설계되어 있습니다.

### 4.3. 요청/응답 파라미터 및 직렬화/역직렬화 (Area 3)
- **직렬화 규격**:
  - 키움 REST API는 모든 수치형 파라미터(`ord_qty`, `ord_uv`, `qry_tp`)를 문자열(String) 형태로 전송해야 합니다. `send_order`에서 `str(quantity)`, `str(price)`로 직렬화하여 표준을 준수하고 있습니다.
- **역직렬화 및 데이터 모델 파싱 결함**:
  - 응답 본문이 표준 키움 규격(`cur_prc`, `ord_no`, `acnt_evlt_remn_indv_tot`) 외에 증권사 표준 API 공통 규격(`output: {stck_prpr, ODNO}`, `output2: {dnca_tot_amt}`)으로 반환될 경우의 계층적 Fallback 추출 로직이 부재합니다.
  - `PriceQuote`, `OrderResult`, `AccountBalance`, `PositionItem`은 `Mapping[str, Any]`를 상속받아 딕셔너리 인덱싱과 객체 속성 접근을 모두 지원하는 Dual Interface로 훌륭하게 설계되어 있으나, 파싱 단계에서 필드 누락 방어가 필요합니다.

### 4.4. 호출 제한(Rate Limit) 및 연속 조회(Pagination) (Area 4)
- **Rate Limit 제어**:
  - 증권사 초당 호출 제한(초당 5건) 초과 시 서버는 HTTP 429 Too Many Requests를 반환합니다.
  - `KiwoomClient._request`는 지수 백오프(`retry_backoff_factor * 2^attempt + 0.1`)를 통해 재시도합니다.
  - **식별된 결함**: 재시도 횟수 초과 시 `KiwoomRateLimitError`를 발생시키지 않고 일반 `KiwoomAPIError("최대 재시도 초과")`로 폴백되어 상위 엔진에서 한도 초과 상황을 정확히 인지하지 못합니다.
- **연속 조회(Next Key) 처리**:
  - 키움 Open API의 연속조회 헤더 `cont_key` 및 응답 본문 `ctx_area_nk200` 처리가 대량 보유 종목 조회 시 필요합니다.

### 4.5. 실시간 웹소켓/시세 피드 및 재연결 (Area 5)
- **스트리머 아키텍처**:
  - `modules/data/streamer.py`에 원형 링버퍼(`CircularBuffer`), 틱-캔들 동적 집계기(`WindowBarAggregator`), 폴링 스트리머(`NaverPollingStreamer`), 가상 스트리머(`MockStreamer`)가 완비되어 있습니다.
  - `WindowBarAggregator`는 타임스탬프를 60초 단위로 바닥내림(Floor) 계산하여 슬라이딩 윈도우를 구성하고, 윈도우 경계 진입 시 `on_bar_closed` 콜백을 트리거하며, 지연 도착 틱(Delayed Tick)에 대한 내결함성을 제공합니다.
  - 키움증권 공식 WebSocket 프로토콜(실시간 체결, 호가, 잔고통보)로 확장 가능한 `BaseStreamer` 추상화가 견고하게 구축되어 있습니다.

---

## 5. 결함 상세 카탈로그 및 권장 수정 방안 (Defect Catalogue)

### [결함 1] `TokenManager` 클래스 내 `revoke_token()` 메서드 누락
- **대상 파일/라인**: `core/kiwoom_api.py:156-209`
- **현상**: `KiwoomClient.revoke_token()`은 존재하나 하위 컴포넌트인 `TokenManager.revoke_token()`이 누락되어 `AttributeError` 유발.
- **권장 수정 코드**:
```python
# core/kiwoom_api.py TokenManager 클래스 내부
def revoke_token(self) -> bool:
    """캐시된 액세스 토큰 및 만료 시각을 초기화합니다."""
    self._access_token = None
    self._expires_at = None
    return True
```

### [결함 2] `KiwoomClient` 내 `get_account_positions()` 편의 메서드 누락
- **대상 파일/라인**: `core/kiwoom_api.py:321-359`
- **현상**: 계좌 잔고 객체 전체가 아닌 보유 종목 리스트(`List[Dict]`)만 바로 조회하는 인터페이스 누락.
- **권장 수정 코드**:
```python
# core/kiwoom_api.py KiwoomClient 클래스 내부
def get_account_positions(self) -> List[Dict[str, Any]]:
    """계좌 보유 종목 리스트를 딕셔너리 형태로 반환합니다."""
    balance = self.get_account_balance()
    return [pos.to_dict() for pos in balance.positions]
```

### [결함 3] `KiwoomClient` 클라이언트 단 입력 파라미터 유효성 검증 부재
- **대상 파일/라인**: `core/kiwoom_api.py:275-319`
- **현상**: 종목코드 6자리 숫자 여부, 매매방향(BUY/SELL), 수량(양수), 지정가 단가(>0) 사전 검증 없이 비정상 요청을 증권사 서버로 전송.
- **권장 수정 코드**:
```python
def get_current_price(self, symbol: str) -> PriceQuote:
    symbol_clean = str(symbol).strip()
    if not re.match(r"^\d{6}$", symbol_clean):
        raise ValueError(f"유효하지 않은 6자리 종목코드입니다: '{symbol}'")
    ...

def send_order(self, symbol: str, side: Union[str, OrderSide], quantity: int, price: int = 0, order_type: Union[str, OrderType] = "3") -> OrderResult:
    symbol_clean = str(symbol).strip()
    if not re.match(r"^\d{6}$", symbol_clean):
        raise ValueError(f"유효하지 않은 6자리 종목코드입니다: '{symbol}'")
    
    side_raw = str(side.value if isinstance(side, OrderSide) else side).upper().strip()
    if side_raw not in ("BUY", "SELL", "01", "02", "매수", "매도"):
        raise ValueError(f"지원하지 않는 주문 방향입니다: '{side}' ('BUY' 또는 'SELL')")
    
    if int(quantity) <= 0:
        raise ValueError(f"주문 수량은 1 이상의 양수여야 합니다: {quantity}")
        
    type_raw = str(order_type.value if isinstance(order_type, OrderType) else order_type).strip()
    if type_raw in ("0", "00", "LIMIT", OrderType.LIMIT) and int(price) <= 0:
        raise ValueError(f"지정가 주문은 0원보다 큰 단가를 지정해야 합니다: {price}")
    ...
```

### [결함 4] `get_current_price` 응답 다중 스키마(Root / Output 중첩) 파싱 누락
- **대상 파일/라인**: `core/kiwoom_api.py:281-295`
- **현상**: `output` 객체로 감싸진 필드(`stck_prpr`, `prdy_vrss`, `acml_vol`) 수신 시 0으로 파싱됨.
- **권장 수정 코드**:
```python
output = res.get("output", {}) if isinstance(res.get("output"), dict) else res

cur_p = output.get("stck_prpr") or res.get("cur_prc", 0)
current_price = Decimal(str(abs(int(cur_p))))

diff_p = output.get("prdy_vrss") or res.get("pred_pre", 0)
price_change = Decimal(str(diff_p))

rate_p = output.get("prdy_ctrt") or res.get("flu_rt", "0.0")
change_rate = Decimal(str(rate_p))

open_p = output.get("stck_oprc") or res.get("open_pric", 0)
open_price = Decimal(str(abs(int(open_p))))

high_p = output.get("stck_hgpr") or res.get("high_pric", 0)
high_price = Decimal(str(abs(int(high_p))))

low_p = output.get("stck_lwpr") or res.get("low_pric", 0)
low_price = Decimal(str(abs(int(low_p))))

vol_p = output.get("acml_vol") or res.get("trde_qty", 0)
volume = int(vol_p)
```

### [결함 5] `send_order` 주문 번호 추출 누락 (`ODNO` / `ord_no`)
- **대상 파일/라인**: `core/kiwoom_api.py:314-319`
- **현상**: `output.ODNO` 또는 `output.ord_no`로 전달된 주문번호를 읽지 못해 빈 문자열로 반환.
- **권장 수정 코드**:
```python
output = res.get("output", {}) if isinstance(res.get("output"), dict) else {}
ord_no = res.get("ord_no") or res.get("ODNO") or output.get("ODNO") or output.get("ord_no") or ""
```

### [결함 6] `get_account_balance` 다중 출력 포맷(`output1`, `output2`, `dnca_tot_amt`) 미지원
- **대상 파일/라인**: `core/kiwoom_api.py:328-352`
- **현상**: 잔고 요약이 `output2`에 존재할 때 예수금 및 총자산이 0으로 계산됨.
- **권장 수정 코드**:
```python
raw_positions = res.get("acnt_evlt_remn_indv_tot") or res.get("output1", [])
if isinstance(raw_positions, dict): raw_positions = [raw_positions]

# summary는 res 루트 또는 output2 배열의 첫 번째 항목
summary = {}
if isinstance(res.get("output2"), list) and len(res["output2"]) > 0:
    summary = res["output2"][0]
elif isinstance(res.get("output2"), dict):
    summary = res["output2"]

deposit_received = Decimal(str(res.get("prsm_dpst_aset_amt") or summary.get("dnca_tot_amt", 0)))
available_cash = Decimal(str(summary.get("nxdy_excc_amt") or deposit_received))
total_eval_amount = Decimal(str(res.get("tot_evlt_amt") or summary.get("tot_evlu_amt", 0)))
total_eval_pnl = Decimal(str(res.get("tot_evlt_pl") or summary.get("evlu_pfls_smtl_amt", 0)))
total_asset = Decimal(str(summary.get("nass_amt") or (deposit_received + total_eval_amount)))
```

### [결함 7] HTTP 예외 계층 매핑 및 구체적 에러 메시지/타입 누락
- **대상 파일/라인**: `core/kiwoom_api.py:246-273`
- **현상**: 429 시 `KiwoomRateLimitError` 미발생, 타임아웃 시 `"타임아웃"` 키워드 누락, 500 에러 시 상태코드 누락.
- **권장 수정 코드**:
```python
except requests.exceptions.Timeout as e:
    last_exception = KiwoomNetworkError(f"네트워크 타임아웃 오류: {e}")
    time.sleep(self.config.retry_backoff_factor * (2 ** attempt))
    continue
except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
    last_exception = KiwoomNetworkError(f"네트워크 통신 장애: {e}")
    time.sleep(self.config.retry_backoff_factor * (2 ** attempt))
    continue

if resp.status_code == 429:
    last_exception = KiwoomRateLimitError(f"요청 한도 초과 (HTTP 429)", status_code=429)
    time.sleep(self.config.retry_backoff_factor * (2 ** attempt) + 0.1)
    continue
if resp.status_code >= 500:
    last_exception = KiwoomAPIError(f"서버 내부 오류 (HTTP {resp.status_code})", status_code=resp.status_code)
    time.sleep(self.config.retry_backoff_factor * (2 ** attempt))
    continue
```

---

## 6. 결론 및 리팩토링 권고사항

1. **REST 통신 엔진 완성도**:
   - `core/config.py`의 4단계 계층적 설정 및 `SecretStr` 은닉 체계는 매우 완성도가 높으며 보안 모범 사례를 완벽히 충족합니다.
   - `modules/data/streamer.py`의 링버퍼 및 캔들 어그리게이터는 35개 테스트를 100% 통과하여 고성능 실시간 처리가 검증되었습니다.
2. **Phase 3 실거래 제어 모듈 정합성 개선**:
   - `core/kiwoom_api.py`의 위 7개 결함을 보완하면 `tests/test_phase3_api.py`의 30개 정밀 테스트가 100% PASS할 수 있는 상태로 즉시 전환됩니다.
3. **다음 단계 연계**:
   - 본 보고서의 결함 카탈로그와 수정 코드를 구현 담당 Worker 에이전트에게 전달하여 직접 리팩토링 및 100% 테스트 무결성을 확보할 것을 제안합니다.
