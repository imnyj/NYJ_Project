# Auto_Stock Phase 5: 데이터 파이프라인 및 종목 스크리너 심층 탐색 보고서 (survey_data.md)

- **작성일자**: 2026-09-03
- **작성자**: Data Pipeline Explorer (`teamwork_preview_explorer_survey_p5_1`)
- **작업 대상**: `modules/data/` 모듈군 및 Phase 5 신규 모듈 `modules/data/screener.py`
- **관련 요구사항**: Phase 5 Dynamic Stock Screener (R1: Static Daily Filter, R2: Intra-day Trigger, R3: API Rate Limit/Streaming, R4: RL Engine Integration)

---

## 1. 개요 및 조사 목적

Auto_Stock 트레이딩 시스템의 **Phase 5: 다이내믹 종목 스크리너(Dynamic Stock Screener)** 모듈 구현을 위해, 현재 프로젝트의 데이터 수집/가공/정제 파이프라인 구조를 전수 분석하고, R1 핵심 요구사항인 정적 일일 감시 풀 필터링 메서드(`update_daily_static_pool`)가 탑재될 `modules/data/screener.py`의 상세 아키텍처를 설계하는 것을 목적으로 합니다.

본 조사는 다음 4가지 핵심 영역을 중점적으로 다룹니다:
1. `modules/data/` 내부의 기존 파일 구조와 클래스/함수 분석 (screener 부재 확인 및 연계 포인트 파악)
2. 시가총액, 펀더멘털 지표(PER/PBR), 외국인/기관 수급 데이터의 포맷 및 컬럼 명세 정립
3. R1 요구사항 `update_daily_static_pool` 메서드 및 `StockScreener` 클래스의 상세 설계안(입출력, 필터링 파이프라인, 에러 핸들링)
4. 기존 코드베이스의 표준 라이브러리, 유틸리티 함수, 단위 테스트 환경 파악

---

## 2. `modules/data/` 기존 파일 구조 및 코드 전수 분석

현재 `modules/data/` 디렉토리에는 6개의 파이썬 파일이 존재하며, `screener.py`는 아직 존재하지 않는 신규 생성 대상입니다.

```
modules/data/
├── __init__.py                  # 패키지 진입점 (Phase 1 수집/저장/스트리밍 클래스 Export)
├── collector_fundamental.py     # DART/네이버/Mock 펀더멘털 재무제표 및 가치평가 수집기
├── collector_price.py           # 네이버/Mock 과거 일봉 및 분봉 OHLCV 수집기
├── consolidator.py              # Look-ahead bias 방지 PIT(Point-in-Time) 결합 및 Parquet I/O
├── pipeline.py                  # Fundamental + Price + Consolidator 통합 Facade
└── streamer.py                  # Tick/Orderbook/Bar 실시간 수신 및 링버퍼 캐싱 모듈
```

### 2.1 파일별 상세 역할 및 분석

#### 1) `__init__.py`
- **역할**: `modules.data` 패키지의 공개 인터페이스(Public API) 정의.
- **분석 결과**:
  - `BaseFundamentalSource`, `FinancialStatement`, `RealtimeValuation`, `FundamentalDataCollector`, `BasePriceFetcher`, `PriceDataCollector`, `DataConsolidator`, `DataCollectionPipeline`, `TickData`, `BarData`, `CircularBuffer` 등이 노출되어 있음.
  - 신규 `screener.py` 개발 후 `StockScreener`, `ScreeningCriteria` 등을 `__init__.py`의 `__all__`에 추가 등록해야 함.

#### 2) `collector_fundamental.py` (52KB, 1,356 lines)
- **핵심 데이터 모델**:
  - `RealtimeValuation`: 실시간/당일 기준 가치평가 및 시장 지표 모델 (스크리닝의 핵심 입력 데이터 소스).
    - `ticker`: 6자리 종목코드 (str)
    - `current_price`: 현재가 (int, 원)
    - `market_cap`: 시가총액 (int, **원 단위 정수**, 예: 400조 원 = `400_000_000_000_000`)
    - `shares_outstanding`: 상장주식수 (int)
    - `per`: 주가수익비율 (Optional[float], 배)
    - `pbr`: 주가순자산비율 (Optional[float], 배)
    - `foreign_rate`: 외국인 보유율/지분율 (Optional[float], %)
  - `FinancialStatement`: 연간/분기 표준 재무제표 모델 (매출, 영업이익, 순이익, 자산, 부채, 자본, ROE, EPS, BPS 등).
- **핵심 수집 클래스**:
  - `FundamentalDataCollector`: 통합 수집 오케스트레이터.
    - `get_realtime_valuation(ticker: str) -> RealtimeValuation`: 네이버 모바일 API -> `MockKiwoomCollector` fallback 순으로 실시간 지표 조회.
    - `get_as_dataframe(ticker: str, ...) -> pd.DataFrame`: 재무제표를 표준 DataFrame으로 반환.
- **주요 유틸리티**:
  - `clean_numeric_str(val)`: 쉼표, 단위(%, 배, 원) 등을 제거하고 float으로 변환.
  - `parse_korean_money(val_str: str) -> Optional[int]`: '1,520조 324억', '5,000억' 등의 한글 금액 문자열을 **원(KRW) 단위 int**로 변환 (예: 1,000억 -> `100_000_000_000`).

#### 3) `collector_price.py` (28KB, 802 lines)
- **역할**: 일봉/분봉 주가 데이터 수집 및 무결성 검증.
- **반환 표준 DataFrame 컬럼**:
  - `['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'timeframe']`

#### 4) `consolidator.py` (15KB, 348 lines)
- **역할**: DART 공시일(`announcement_date`) 기준 `pd.merge_asof(direction='backward')`를 통한 PIT 통합 데이터셋 생성.
- **산출 지표 및 단위**:
  - `dynamic_market_cap`: `close * shares_outstanding` (원 단위 float/int).
  - `dynamic_per`: `close / eps` (eps > 0 인 경우에만 유효, 적자 시 np.nan).
  - `dynamic_pbr`: `close / bps` (bps > 0 인 경우에만 유효, 적자 시 np.nan).

#### 5) `streamer.py` (30KB, 793 lines)
- **역할**: 실시간 시세 수신 및 버퍼링 (Phase 5 R2 실시간 동적 트리거의 직접적 연동 대상).
- **핵심 데이터 구조체**:
  - `TickData`:
    - `timestamp`: datetime
    - `symbol`: str
    - `price`: float (현재 체결가)
    - `volume`: int (체결량)
    - `accum_volume`: int (당일 누적 체결량)
    - `open_price`: float (**당일 시가** -> R2 시가 대비 3% 급등 판정에 필수)
    - `high_price`, `low_price`: float
  - `CircularBuffer` / `RealtimeRingBuffer`: O(1) 원형 링 버퍼로 종목별 최근 틱을 보관하여 전일/이전 거래량 급증 비교에 활용 가능.

---

## 3. 데이터 포맷 및 스펙 심층 분석

### 3.1 시가총액 (Market Capitalization)
- **프로젝트 표준 단위**: **원(KRW)** (int 또는 float)
- **기준 임계치**: 시가총액 최소 1,000억 원 이상
  - `1,000억 원 = 100,000,000,000 = 1e11`
- **컬럼 명칭**:
  - 기본 컬럼: `market_cap`
  - PIT 통합 데이터 컬럼: `dynamic_market_cap`
  - 한글 컬럼 대응: `시가총액`
- **단위 보정 로직 (Auto-Scaling)**:
  - 사용자가 주입한 데이터프레임의 시가총액 값이 `100_000` (10만) 이하인 경우 '억원' 단위로 입력된 것으로 판단하여 `* 100,000,000` 처리하거나, 값이 `1e9` 이상이면 원 단위로 인식하도록 유연한 정규화 필요.

### 3.2 펀더멘털 저평가 지표 (PER & PBR)
- **PER (주가수익비율)**:
  - 컬럼 명칭: `per` 또는 `dynamic_per`
  - 데이터 타입: `float`
  - 유효성 조건:
    - 당기순이익 적자 기업(EPS <= 0)의 경우 PER이 음수이거나 NaN으로 제공됨.
    - 저평가 필터 적용 시 `per > 0` (적자 기업 제외) 및 `min_per <= per <= max_per` (예: 1.0 ~ 15.0배) 검사.
- **PBR (주가순자산비율)**:
  - 컬럼 명칭: `pbr` 또는 `dynamic_pbr`
  - 데이터 타입: `float`
  - 유효성 조건: `pbr > 0` 및 `min_pbr <= pbr <= max_pbr` (예: 0.1 ~ 2.0배).

### 3.3 기관 및 외국인 수급 데이터 (Supply & Demand)
- **코드베이스 현황 조사 결과**:
  - 기존 `RealtimeValuation` 모델에는 `foreign_rate` (외국인 지분율, %)만이 존재함.
  - `foreign_net_buy`(외국인 순매수), `inst_net_buy`(기관 순매수) 컬럼은 기존 모듈에 아직 명시적으로 구현되어 있지 않음.
- **수급 데이터 명세 수립 (권장 표준)**:
  - `foreign_net_buy`: 외국인 순매수 금액(원) 또는 수량(주) (int/float, 양수=순매수, 음수=순매도)
  - `inst_net_buy`: 기관 순매수 금액(원) 또는 수량(주) (int/float, 양수=순매수, 음수=순매도)
  - `foreign_rate`: 외국인 지분율 (%) (float, 0.0 ~ 100.0)
- **다형성(Duck Typing) 수급 필터링 규칙**:
  1. `foreign_net_buy`와 `inst_net_buy` 컬럼이 모두 존재하는 경우:
     - 외인+기관 합산 순매수 양수 (`foreign_net_buy + inst_net_buy > 0`) 또는 개별 순매수 양수 (`foreign_net_buy > 0 and inst_net_buy > 0`) 조건 검사.
  2. `foreign_rate` 컬럼만 존재하는 경우:
     - 외국인 지분율 임계치 검사 (예: `foreign_rate >= min_foreign_rate`).
  3. 수급 관련 컬럼이 전혀 없는 경우:
     - 에러를 발생시키지 않고 경고(Warning) 로그를 남긴 후 수급 필터를 바이패스(Pass-through)하여 시가총액 및 PER/PBR 조건만으로 종목을 추출 (Fault-Tolerant 무중단 설계).

### 3.4 컬럼 정규화 매핑 테이블 (Column Normalization Table)

| 표준 내부 필드 | 허용 입력 컬럼 별칭 (Aliases) | 데이터 타입 | 기본 단위 | 유효성 기준 |
|:---|:---|:---|:---|:---|
| `symbol` | `symbol`, `code`, `ticker`, `종목코드`, `종목` | `str` | 6자리 문자열 (`zfill(6)`) | 영문/숫자 혼합 또는 6자리 숫자 |
| `market_cap` | `market_cap`, `dynamic_market_cap`, `시가총액`, `mkt_cap` | `float` / `int` | 원 (KRW) | `>= 100_000_000_000` (1,000억) |
| `per` | `per`, `dynamic_per`, `PER`, `pe_ratio` | `float` | 배 | `> 0.0` and `<= max_per` (기본 15.0) |
| `pbr` | `pbr`, `dynamic_pbr`, `PBR`, `pb_ratio` | `float` | 배 | `> 0.0` and `<= max_pbr` (기본 2.0) |
| `foreign_net_buy`| `foreign_net_buy`, `외국인순매수`, `foreign_buy` | `float` / `int` | 원 또는 주 | `> 0` (양수) |
| `inst_net_buy` | `inst_net_buy`, `기관순매수`, `institution_buy` | `float` / `int` | 원 또는 주 | `> 0` (양수) |
| `foreign_rate` | `foreign_rate`, `외국인보유율`, `foreign_ratio` | `float` | % | `>= min_foreign_rate` |

---

## 4. R1 요구사항 `update_daily_static_pool` 및 `StockScreener` 상세 설계

### 4.1 클래스 구조 및 책임 분리

`modules/data/screener.py`는 단일 파일 내에 설정 클래스(`ScreeningCriteria`)와 실행 엔진(`StockScreener`)으로 구성합니다.

```
+-------------------------------------------------------------+
|                     ScreeningCriteria                       |
+-------------------------------------------------------------+
| - min_market_cap: int = 100_000_000_000 (1,000억 원)         |
| - min_per: Optional[float] = 1.0                            |
| - max_per: Optional[float] = 15.0                           |
| - min_pbr: Optional[float] = 0.1                            |
| - max_pbr: Optional[float] = 2.0                            |
| - require_positive_net_buy: bool = True (외인+기관 합산 > 0)  |
| - require_foreign_net_buy: bool = False                     |
| - require_inst_net_buy: bool = False                        |
| - min_foreign_rate: Optional[float] = None                  |
| - max_candidates: Optional[int] = 200                       |
| - sort_by: str = "market_cap"                               |
+-------------------------------------------------------------+
                              |
                              v uses
+-------------------------------------------------------------+
|                       StockScreener                         |
+-------------------------------------------------------------+
| - criteria: ScreeningCriteria                               |
| - fundamental_collector: FundamentalDataCollector           |
| - candidate_pool: List[str]                                 |
| - candidate_pool_df: pd.DataFrame                           |
+-------------------------------------------------------------+
| + update_daily_static_pool(data=None, criteria=None)        |
|     -> List[str]                                            |
| + check_intraday_trigger(tick_data, ...) -> Optional[str]   |
| + get_candidate_pool() -> List[str]                         |
| + get_candidate_df() -> pd.DataFrame                        |
| + route_trigger_to_simulator(symbol, simulator)             |
+-------------------------------------------------------------+
```

### 4.2 `ScreeningCriteria` 데이터클래스 명세

```python
@dataclass
class ScreeningCriteria:
    """정적 스크리닝 필터 기준 파라미터"""
    # 1. 시가총액 조건 (최소 1,000억 원)
    min_market_cap: int = 100_000_000_000

    # 2. 밸류에이션 저평가 조건
    min_per: Optional[float] = 1.0
    max_per: Optional[float] = 15.0
    min_pbr: Optional[float] = 0.1
    max_pbr: Optional[float] = 2.0

    # 3. 수급 조건
    require_positive_net_buy: bool = True     # 외인 + 기관 합산 순매수 > 0
    require_foreign_net_buy: bool = False     # 외국인 단독 순매수 > 0
    require_inst_net_buy: bool = False        # 기관 단독 순매수 > 0
    min_foreign_rate: Optional[float] = None  # 최소 외국인 지분율 (%)

    # 4. 풀 크기 및 정렬
    max_candidates: Optional[int] = 200       # 감시 풀 최대 크기 (R3 API 최적화)
    sort_by: str = "market_cap"               # 정렬 기준 컬럼
    ascending: bool = False                   # 내림차순 정렬
```

### 4.3 `update_daily_static_pool` 메서드 상세 명세

#### 시그니처
```python
def update_daily_static_pool(
    self,
    data: Optional[Union[pd.DataFrame, List[str]]] = None,
    criteria: Optional[ScreeningCriteria] = None,
) -> List[str]:
```

#### 파라미터 및 반환값
- **`data`**:
  - `pd.DataFrame`: 종목별 시가총액, PER, PBR, 수급 데이터가 포함된 DataFrame (단위 테스트 및 백테스트에서 직접 주입).
  - `List[str]`: 종목코드 리스트. 제공 시 `FundamentalDataCollector`를 통해 실시간 지표를 조회하여 DataFrame 구성.
  - `None`: 사전 등록된 유니버스 또는 내부 기본 종목군에 대해 자동 조회.
- **`criteria`**: 선택적 오버라이드 필터 조건 (기본값: 인스턴스 초기화 시 지정된 criteria).
- **반환값 (`List[str]`)**:
  - 필터링 조건을 모두 통과한 6자리 표준 종목코드 리스트 (예: `['005930', '000660', ...]`).
  - 결과는 `self.candidate_pool` 및 `self.candidate_pool_df`에 자동 캐싱됨.

#### 세부 필터링 파이프라인 (Execution Pipeline)
1. **데이터 유효성 검사 및 정규화**:
   - `data`가 `None`이거나 비어있는 경우: 빈 리스트 `[]` 반환 및 INFO 로깅.
   - 컬럼명 매핑 정규화: 별칭(alias)을 표준 컬럼명(`symbol`, `market_cap`, `per`, `pbr`, `foreign_net_buy`, `inst_net_buy`)으로 리네이밍.
   - 데이터 타입 정제: `pd.to_numeric(errors='coerce')`로 숫자 변환.
   - 종목코드 6자리 패딩: `df['symbol'].astype(str).str.zfill(6)`.
2. **시가총액 필터 (`Step 1: Market Cap Filter`)**:
   - `df['market_cap'] >= criteria.min_market_cap`
3. **저평가 필터 (`Step 2: Valuation Filter`)**:
   - `df['per'] >= criteria.min_per` AND `df['per'] <= criteria.max_per` (PER 결측치 및 0 이하 제외)
   - `df['pbr'] >= criteria.min_pbr` AND `df['pbr'] <= criteria.max_pbr` (PBR 결측치 및 0 이하 제외)
4. **수급 필터 (`Step 3: Supply & Demand Filter`)**:
   - `require_positive_net_buy`: `(df['foreign_net_buy'].fillna(0) + df['inst_net_buy'].fillna(0)) > 0`
   - `require_foreign_net_buy`: `df['foreign_net_buy'] > 0`
   - `require_inst_net_buy`: `df['inst_net_buy'] > 0`
   - 수급 컬럼이 존재하지 않는 경우: 수급 필터 패스 (경고 로그 기록 후 계속 진행).
5. **정렬 및 상위 N개 슬라이싱 (`Step 4: Sorting & Slicing`)**:
   - `df.sort_values(by=criteria.sort_by, ascending=criteria.ascending)`
   - `max_candidates` 개수만큼 상위 종목 슬라이싱.
6. **상태 보관 및 반환**:
   - `self.candidate_pool = df['symbol'].tolist()`
   - `self.candidate_pool_df = df`
   - 종목코드 리스트 반환.

#### 에러 핸들링 및 예외 방어 설계
- **빈 DataFrame / 결측치 입력**:
  - `KeyError`나 `ValueError`를 발생시키지 않고 빈 리스트 `[]` 반환.
- **문자열/비정형 데이터 포함 시**:
  - `pd.to_numeric(errors='coerce')`를 통해 안전하게 `NaN`으로 치환하여 비교 연산 시 False로 자동 탈락.
- **적자 기업 (Negative PER/PBR)**:
  - PER < 0인 경우 저평가가 아니므로 `min_per <= per` 조건(기본 min_per=1.0)에 의해 안전하게 제외됨.

---

## 5. R2 / R3 / R4 연계 인터페이스 설계

### 5.1 R2: 장중 실시간 동적 트리거 (`check_intraday_trigger`)
- **목적**: 장중 실시간 틱 데이터를 주입받아 모멘텀 돌파 종목 포착.
- **시그니처**:
  ```python
  def check_intraday_trigger(
      self,
      tick_data: Union[TickData, Dict[str, Any]],
      baseline_volume: Optional[int] = None,
      volume_surge_threshold: float = 3.0,   # 300% 급증
      price_surge_threshold: float = 0.03,    # 시가 대비 3% 급등
  ) -> Optional[str]:
  ```
- **판정 알고리즘**:
  1. 감시 풀 포함 여부:
     - `tick_data.symbol`이 `self.candidate_pool`에 존재하지 않으면 즉시 `None` 반환 (감시 풀이 비어있으면 전체 대상).
  2. 가격 급등 판정:
     - 시가(`open_price`) 대비 현재가(`price`) 상승률 계산:
       $$\text{price\_gain} = \frac{\text{price} - \text{open\_price}}{\text{open\_price}}$$
     - `price_gain >= price_surge_threshold` (예: 3%) 충족 여부 확인.
  3. 거래량 폭증 판정:
     - 기준 거래량(`baseline_volume`) 대비 누적/틱 거래량 비율 계산:
       $$\text{volume\_ratio} = \frac{\text{current\_volume}}{\text{baseline\_volume}}$$
     - `volume_ratio >= volume_surge_threshold` (예: 3.0배 = 300%) 충족 여부 확인.
  4. 두 조건 모두 충족 시 해당 종목코드 `tick_data.symbol` 반환, 미충족 시 `None` 반환.

### 5.2 R3: API Rate Limit 및 스트리밍 최적화
- **키움 REST API 제약**: 초당 최대 5회 호출 제한 (안전을 위해 200ms sleep 또는 토큰 버킷).
- **스크리너 아키텍처 대응**:
  1. **감시 풀 크기 제한**: `criteria.max_candidates = 100~200`으로 제한하여 1일 1회 정적 필터링 단계에서 감시 대상을 사전 압축.
  2. **장중 감시 스트리밍 우선**: 실시간 시세는 키움 REST API 폴링 대신 `modules.data.streamer.TickData` 웹소켓/스트리밍 주입 방식을 1차 권장.
  3. **폴링 스케줄러 청킹 구조**: 만약 REST API로 주기적 모니터링을 수행해야 하는 경우, 100개 종목을 5개씩 1초 간격으로 분할 조회(Chunked Polling)할 수 있는 헬퍼 메서드 지원.

### 5.3 R4: RL 엔진 연동 (`live_learning_simulator.py`)
- `check_intraday_trigger`에서 포착된 종목은 `LiveLearningSimulator`로 즉각 라우팅:
  ```python
  def route_trigger_to_simulator(
      self,
      triggered_symbol: str,
      simulator: "LiveLearningSimulator",
  ) -> Dict[str, Any]:
      """트리거된 종목을 LiveLearningSimulator의 관측/행동 루프로 주입"""
      logger.info(f"Routing triggered symbol [{triggered_symbol}] to LiveLearningSimulator.")
      state = simulator.reset(symbol=triggered_symbol)
      return state
  ```

---

## 6. 기존 코드베이스 라이브러리 및 테스트 환경 분석

### 6.1 사용되는 라이브러리 및 유틸리티 매핑
- **표준 라이브러리**:
  - `dataclasses`: `@dataclass`, `field`, `asdict`
  - `datetime`: `datetime`, `date`, `timedelta`
  - `enum`: `Enum`
  - `typing`: `Any`, `Callable`, `Dict`, `List`, `Optional`, `Tuple`, `Union`
  - `logging`: `logging.getLogger("AutoStock.Screener")`
  - `math`, `re`, `time`
- **서드파티 라이브러리**:
  - `pandas` (`pd.DataFrame`, `pd.to_numeric`, `pd.to_datetime`)
  - `numpy` (`np.nan`, `np.where`)
- **프로젝트 내부 모듈**:
  - `modules.data.collector_fundamental`: `FundamentalDataCollector`, `RealtimeValuation`, `clean_numeric_str`, `parse_korean_money`
  - `modules.data.streamer`: `TickData`, `BarData`
  - `core.kiwoom_api`: `KiwoomClient`

### 6.2 테스트 실행 환경 검증
- **파이썬 가상환경**: `/home/imnyj/venv/bin/python`, `/home/imnyj/venv/bin/pytest`
- **기존 테스트 검증 결과**:
  - `tests/test_fundamental.py`: **30 passed** (1.34s)
  - `tests/test_consolidator.py`: **19 passed** (2.29s)
  - `tests/test_price_streamer.py`: **35 passed** (2.48s)
- **신규 테스트 대상 파일**: `tests/test_phase5_screener.py`

---

## 7. 권장 구현 스켈레톤 (Proposed `modules/data/screener.py`)

후속 구현 워커(Worker)가 바로 적용할 수 있도록 설계된 권장 구현 스켈레톤입니다:

```python
"""
modules/data/screener.py
========================
Auto Stock ML/RL Trader — Phase 5: 다이내믹 종목 스크리너 (Dynamic Stock Screener).

주요 기능:
1. ScreeningCriteria: 정적/동적 스크리닝 필터 조건 설정 데이터클래스
2. StockScreener:
   - update_daily_static_pool: 1일 1회 장 시작 전 시총/저평가/수급 기준 감시 풀 추출 (R1)
   - check_intraday_trigger: 장중 실시간 틱 데이터 기반 모멘텀/거래량 돌파 감지 (R2)
   - route_trigger_to_simulator: RL 엔진(LiveLearningSimulator)으로 트리거 종목 전달 (R4)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from modules.data.collector_fundamental import FundamentalDataCollector, RealtimeValuation
from modules.data.streamer import TickData

logger = logging.getLogger("AutoStock.Screener")


@dataclass
class ScreeningCriteria:
    """정적 일일 스크리닝 필터 파라미터 (R1)"""
    min_market_cap: int = 100_000_000_000  # 최소 시가총액 1,000억 원
    min_per: Optional[float] = 1.0          # 최소 PER (적자 기업 제외)
    max_per: Optional[float] = 15.0         # 최대 PER (저평가 기준)
    min_pbr: Optional[float] = 0.1          # 최소 PBR
    max_pbr: Optional[float] = 2.0          # 최대 PBR
    require_positive_net_buy: bool = True   # 외인 + 기관 합산 순매수 > 0
    require_foreign_net_buy: bool = False   # 외국인 단독 순매수 > 0
    require_inst_net_buy: bool = False      # 기관 단독 순매수 > 0
    min_foreign_rate: Optional[float] = None # 최소 외국인 지분율 (%)
    max_candidates: Optional[int] = 200     # 최종 선별 감시 풀 최대 종목 수 (R3)
    sort_by: str = "market_cap"             # 정렬 기준 컬럼
    ascending: bool = False                 # 내림차순 정렬


class StockScreener:
    """다이내믹 종목 스크리너 엔진"""

    def __init__(
        self,
        criteria: Optional[ScreeningCriteria] = None,
        fundamental_collector: Optional[FundamentalDataCollector] = None,
    ):
        self.criteria = criteria or ScreeningCriteria()
        self.fundamental_collector = fundamental_collector or FundamentalDataCollector()
        self.candidate_pool: List[str] = []
        self.candidate_pool_df: pd.DataFrame = pd.DataFrame()

    def update_daily_static_pool(
        self,
        data: Optional[Union[pd.DataFrame, List[str]]] = None,
        criteria: Optional[ScreeningCriteria] = None,
    ) -> List[str]:
        """
        장 시작 전(또는 1일 1회), 시가총액 최소 1,000억 원 이상, 저평가(PER/PBR),
        기관/외국인 수급 양호 조건을 만족하는 관심 종목 리스트를 추출 (R1).
        """
        crit = criteria or self.criteria

        # 1. 입력 데이터 형태에 따른 DataFrame 구성
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        elif isinstance(data, list):
            df = self._collect_fundamentals_for_symbols(data)
        elif data is None:
            logger.info("No data provided to update_daily_static_pool. Returning empty pool.")
            self.candidate_pool = []
            self.candidate_pool_df = pd.DataFrame()
            return []
        else:
            logger.warning(f"Unsupported data type: {type(data)}")
            return []

        if df.empty:
            logger.info("Empty DataFrame provided. Candidate pool is empty.")
            self.candidate_pool = []
            self.candidate_pool_df = pd.DataFrame()
            return []

        # 2. 컬럼명 정규화
        df = self._normalize_columns(df)

        # 3. 시가총액 필터 (>= 1,000억 원)
        if "market_cap" in df.columns:
            df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce")
            df = df[df["market_cap"] >= crit.min_market_cap]
        else:
            logger.warning("Column 'market_cap' missing. Skipping market cap filter.")

        # 4. PER 저평가 필터
        if "per" in df.columns:
            df["per"] = pd.to_numeric(df["per"], errors="coerce")
            if crit.min_per is not None:
                df = df[df["per"] >= crit.min_per]
            if crit.max_per is not None:
                df = df[df["per"] <= crit.max_per]

        # 5. PBR 저평가 필터
        if "pbr" in df.columns:
            df["pbr"] = pd.to_numeric(df["pbr"], errors="coerce")
            if crit.min_pbr is not None:
                df = df[df["pbr"] >= crit.min_pbr]
            if crit.max_pbr is not None:
                df = df[df["pbr"] <= crit.max_pbr]

        # 6. 수급 필터
        has_foreign = "foreign_net_buy" in df.columns
        has_inst = "inst_net_buy" in df.columns

        if crit.require_positive_net_buy and (has_foreign or has_inst):
            f_buy = pd.to_numeric(df["foreign_net_buy"], errors="coerce").fillna(0) if has_foreign else 0
            i_buy = pd.to_numeric(df["inst_net_buy"], errors="coerce").fillna(0) if has_inst else 0
            df = df[(f_buy + i_buy) > 0]

        if crit.require_foreign_net_buy and has_foreign:
            df = df[pd.to_numeric(df["foreign_net_buy"], errors="coerce") > 0]

        if crit.require_inst_net_buy and has_inst:
            df = df[pd.to_numeric(df["inst_net_buy"], errors="coerce") > 0]

        if crit.min_foreign_rate is not None and "foreign_rate" in df.columns:
            df = df[pd.to_numeric(df["foreign_rate"], errors="coerce") >= crit.min_foreign_rate]

        # 7. 정렬 및 상위 N개 슬라이싱
        if crit.sort_by in df.columns:
            df = df.sort_values(by=crit.sort_by, ascending=crit.ascending)

        if crit.max_candidates is not None and len(df) > crit.max_candidates:
            df = df.iloc[: crit.max_candidates]

        # 8. 풀 갱신 및 반환
        selected_symbols = [str(s).strip().zfill(6) for s in df["symbol"].tolist()]
        self.candidate_pool = selected_symbols
        self.candidate_pool_df = df.reset_index(drop=True)

        logger.info(f"Daily static pool updated: {len(selected_symbols)} candidate stocks selected.")
        return selected_symbols

    def check_intraday_trigger(
        self,
        tick_data: Union[TickData, Dict[str, Any]],
        baseline_volume: Optional[int] = None,
        volume_surge_threshold: float = 3.0,
        price_surge_threshold: float = 0.03,
    ) -> Optional[str]:
        """
        장중 실시간 틱 데이터를 주입받아, 특정 조건(거래량 300% 급증 & 시가 대비 3% 급등 등)이
        충족되는 순간 해당 종목 코드를 반환 (R2).
        """
        # Dict 또는 TickData 객체 처리
        if isinstance(tick_data, dict):
            symbol = str(tick_data.get("symbol", "")).zfill(6)
            price = float(tick_data.get("price", 0.0))
            open_price = float(tick_data.get("open_price", 0.0))
            volume = int(tick_data.get("volume", 0))
            accum_volume = int(tick_data.get("accum_volume", volume))
        else:
            symbol = str(tick_data.symbol).zfill(6)
            price = float(tick_data.price)
            open_price = float(tick_data.open_price)
            volume = int(tick_data.volume)
            accum_volume = int(tick_data.accum_volume) if tick_data.accum_volume > 0 else volume

        # 감시 풀 검사 (풀이 정의된 경우에만 필터링)
        if self.candidate_pool and symbol not in self.candidate_pool:
            return None

        # 시가 대비 급등률 검사
        if open_price <= 0:
            return None
        price_gain = (price - open_price) / open_price
        if price_gain < price_surge_threshold:
            return None

        # 거래량 급증 검사
        if baseline_volume is not None and baseline_volume > 0:
            vol_ratio = accum_volume / baseline_volume
            if vol_ratio < volume_surge_threshold:
                return None

        return symbol

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """입력 컬럼명을 표준 스키마로 정규화"""
        col_map = {
            "code": "symbol", "ticker": "symbol", "종목코드": "symbol",
            "dynamic_market_cap": "market_cap", "시가총액": "market_cap",
            "dynamic_per": "per", "PER": "per",
            "dynamic_pbr": "pbr", "PBR": "pbr",
            "외국인순매수": "foreign_net_buy",
            "기관순매수": "inst_net_buy",
            "외국인보유율": "foreign_rate",
        }
        renamed = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        if "symbol" in renamed.columns:
            renamed["symbol"] = renamed["symbol"].astype(str).str.zfill(6)
        return renamed

    def _collect_fundamentals_for_symbols(self, symbols: List[str]) -> pd.DataFrame:
        """종목코드 리스트로부터 FundamentalDataCollector를 통해 실시간 지표를 조회하여 DataFrame 구성"""
        rows = []
        for sym in symbols:
            clean_sym = str(sym).strip().zfill(6)
            val = self.fundamental_collector.get_realtime_valuation(clean_sym)
            if val:
                rows.append({
                    "symbol": clean_sym,
                    "market_cap": val.market_cap,
                    "per": val.per,
                    "pbr": val.pbr,
                    "foreign_rate": val.foreign_rate,
                    "foreign_net_buy": 0,
                    "inst_net_buy": 0,
                })
        return pd.DataFrame(rows)
```

---

## 8. 결론 및 권장사항 요약

1. **`screener.py`의 모듈 배치**:
   - `modules/data/screener.py` 위치에 생성하며, `modules/data/__init__.py`에 `StockScreener` 및 `ScreeningCriteria`를 공개 노출합니다.
2. **다형성 입력 지원의 필수성**:
   - 단위 테스트(`tests/test_phase5_screener.py`)는 가상의 정적 DataFrame을 직접 주입하므로, `update_daily_static_pool`은 DataFrame 주입과 종목 리스트 주입을 모두 투명하게 지원해야 합니다.
3. **단위 표준화 및 안전한 결측치 처리**:
   - 시가총액은 원(KRW) 단위 기준(`>= 100_000_000_000`)으로 통일하고, PER/PBR의 NaN 및 음수(적자)는 연산 시 자동 탈락하도록 처리합니다.
4. **후속 작업자와의 협업 연계**:
   - Explorer 2 (RL/Simulator 연동): `route_trigger_to_simulator` 인터페이스를 통해 `live_learning_simulator.py`에 원활하게 연결 가능.
   - Explorer 3 (API 최적화 및 테스트 아키텍처): `max_candidates=100~200` 제한 및 `check_intraday_trigger` 틱 스트림 명세를 통해 `test_phase5_screener.py` 케이스 작성 가능.
