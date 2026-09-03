# R2 & R3 시계열 주가 수집, 실시간 스트리머, 데이터 통합/저장 상세 설계 명세서 (Specification)

**문서 ID**: `SPEC-DATA-R2-R3-001`  
**작성일시**: 2026-08-31T17:01:00+09:00  
**작성자**: Auto Stock Explorer 3 (Price Data & Data Consolidation Specialist)  
**대상 컴포넌트**: 
- `modules/data/collector_price.py` (시계열 주가 수집기)
- `modules/data/streamer.py` (실시간 체결/호가 스트리머 및 캐시 버퍼)
- `modules/data/consolidator.py` & `modules/data/pipeline.py` (Look-ahead bias 방지 Point-in-Time 통합 파이프라인)
- `data/raw/` (PyArrow 기반 ZSTD 압축 Parquet 스토리지 아키텍처)

---

## 1. 개요 및 설계 목표

본 문서는 Auto Stock ML/RL Trader의 Phase 1 데이터 수집 파이프라인 중 **R2(Price Data Collector & Real-time Streamer)** 및 **R3(Data Consolidation & Parquet Storage)**의 아키텍처, 모듈 인터페이스, 데이터프레임/스토리지 스키마, 결측/이상치 방어 알고리즘을 상세히 정의한다.

### 핵심 목표
1. **과거 시계열 데이터(OHLCV) 다중 소스 수집 및 복원력 확보**:
   - 일봉, 주봉, 월봉 및 고빈도 분봉(1분, 3분, 5분, 15분, 30분, 60분)의 무중단 수집.
   - Naver Finance API, PyKRX, FinanceDataReader, yfinance, 키움증권 OpenAPI를 아우르는 Multi-Source Fallback 체계 구축.
2. **실시간 스트리밍 인메모리 버퍼링 및 슬라이딩 윈도우 집계**:
   - 틱/체결 및 호가 데이터를 수신하여 원형 큐(Circular Ring Buffer)에 캐싱.
   - 틱 데이터로부터 실시간 OHLCV 캔들을 동적으로 생성하는 Tick-to-Bar Resampler 및 이벤트 디스패처 제공.
3. **Point-in-Time(PIT) 데이터 통합 및 선행 편향(Look-ahead Bias) 원천 차단**:
   - 저빈도 재무제표(분기/연간)와 고빈도 주가(일봉/분봉) 병합 시, 보고서 기준일이 아닌 **실제 DART 공시일(Announcement Date)**을 기준으로 `merge_asof(direction='backward')`를 적용하여 미래 데이터 참조 오류 원천 차단.
   - 일별 종가 변동에 따른 동적 가치평가 지표($Dynamic\_PER_t$, $Dynamic\_PBR_t$ 등) 실시간 산출.
4. **고성능 Parquet 스토리지 스키마 정의 (`data/raw/`)**:
   - PyArrow 기반 ZSTD 압축, Dictionary 인코딩, Hive-style 디렉토리 파티셔닝 전략을 적용하여 스토리지 용량 30% 이상 절감 및 쿼리/학습 로딩 속도 극대화.

---

## 2. R2: Price Data Collector (`modules/data/collector_price.py`)

### 2.1 아키텍처 개요
- 다중 데이터 소스를 플러그인 형태로 추상화하는 **Adapter 패턴** 및 우선순위에 따라 요청을 시도하는 **Chain-of-Responsibility / Fallback 패턴** 적용.
- 네트워크 단절, 요청 제한(Rate Limit), IP 차단 시 지수 백오프(Exponential Backoff) 및 재시도 로직 내장.

```
+-------------------------------------------------------------+
|                     PriceDataCollector                      |
+-------------------------------------------------------------+
                              |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
[NaverPriceFetcher]   [PykrxPriceFetcher]   [YFinancePriceFetcher]
 (Primary - Fast)      (Secondary - Depth)   (Fallback - Global)
       |
       v
[KiwoomPriceFetcher] (Broker API Adapter)
```

### 2.2 타임프레임 정의 (TimeFrame Enum)
```python
from enum import Enum

class TimeFrame(str, Enum):
    MINUTE_1 = '1m'
    MINUTE_3 = '3m'
    MINUTE_5 = '5m'
    MINUTE_15 = '15m'
    MINUTE_30 = '30m'
    MINUTE_60 = '60m'
    DAILY = '1d'
    WEEKLY = '1w'
    MONTHLY = '1M'
```

### 2.3 클래스 및 메서드 인터페이스

#### (1) `BasePriceFetcher` (추상 인터페이스)
```python
from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

class BasePriceFetcher(ABC):
    @abstractmethod
    def fetch_daily(self, symbol: str, start_date: str, end_date: str, adjusted: bool = True) -> pd.DataFrame:
        """일봉 OHLCV 수집"""
        pass

    @abstractmethod
    def fetch_minute(self, symbol: str, date: str, timeframe: str = '1m') -> pd.DataFrame:
        """분봉 OHLCV 수집"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """해당 소스 사용 가능 여부 확인"""
        pass
```

#### (2) `NaverPriceFetcher` (기본 탑재 고속 수집기)
- **엔드포인트**:
  - 일봉/주봉/월봉: `https://fchart.stock.naver.com/sise.nhn?symbol={symbol}&timeframe=day&count={count}&requestType=0`
  - 당일 1분봉: `https://api.stock.naver.com/chart/domestic/item/{symbol}?periodType=day`
- **특징**: 별도 인증키 없이 고속 XML/JSON 응답 수신 가능.

#### (3) `PriceDataCollector` (메인 오케스트레이터)
```python
class PriceDataCollector:
    def __init__(
        self,
        fetchers: Optional[List[BasePriceFetcher]] = None,
        timeout: int = 10,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ):
        self.fetchers = fetchers or [NaverPriceFetcher(), PykrxPriceFetcher(), YFinancePriceFetcher()]
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def get_daily_ohlcv(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjusted: bool = True
    ) -> pd.DataFrame:
        """
        다중 소스 Fallback을 적용한 일봉 OHLCV 수집
        반환 DataFrame:
          columns: ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'value', 'adj_factor']
          index: RangeIndex or DatetimeIndex
        """
        ...

    def get_minute_ohlcv(
        self,
        symbol: str,
        date: str,
        timeframe: str = '1m'
    ) -> pd.DataFrame:
        """
        1분봉 수집 후 지정된 분봉(3m, 5m, 15m 등)으로 리샘플링하여 반환
        """
        ...

    def resample_ohlcv(
        self,
        df_1m: pd.DataFrame,
        target_timeframe: str
    ) -> pd.DataFrame:
        """
        1분봉 DataFrame을 3m/5m/15m/30m/60m 봉으로 집계
        - open: first
        - high: max
        - low: min
        - close: last
        - volume: sum
        - value: sum
        """
        ...

    def validate_and_clean_ohlcv(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        가격 무결성 검증:
        1. low <= open, close <= high 만족 여부 확인 및 보정
        2. volume >= 0 검증
        3. 날짜 정렬 및 중복 행 제거
        4. 거래정지일(Volume == 0 or Open == High == Low == Close) 플래깅
        """
        ...
```

### 2.4 가격 데이터프레임 스키마

| 컬럼명 | 데이터 타입 | Null 허용 | 설명 | 예시 |
| :--- | :--- | :--- | :--- | :--- |
| `date` | `datetime64[ns]` / `str` | N | 거래 일자 (YYYY-MM-DD) | 2026-08-31 |
| `timestamp` | `datetime64[ns]` | Y (분봉 시 N) | 체결 일시 (YYYY-MM-DD HH:MM:SS) | 2026-08-31 09:05:00 |
| `symbol` | `str` | N | 6자리 종목코드 | '005930' |
| `open` | `float64` | N | 시가 | 249000.0 |
| `high` | `float64` | N | 고가 | 250500.0 |
| `low` | `float64` | N | 저가 | 248500.0 |
| `close` | `float64` | N | 종가 (수정종가 적용 시 기준) | 260000.0 |
| `volume` | `int64` | N | 구간 거래량 | 709866 |
| `value` | `float64` | Y | 거래대금 (원) | 176756634000.0 |
| `adj_factor` | `float64` | Y | 수정주가 배율 (기본값 1.0) | 1.0 |
| `is_trading_halt` | `bool` | N | 거래정지 여부 플래그 | False |

---

## 3. R2: Real-time Streamer & Buffer (`modules/data/streamer.py`)

### 3.1 아키텍처 및 데이터 흐름
- **Producer-Consumer 모델**: 스트리밍 소스(WebSocket/Polling/Mock)가 틱 데이터를 비동기 수신하여 `asyncio.Queue` / 스레드 큐로 Push.
- **Ring Buffer (Deque)**: 메모리 폭증을 방지하기 위해 종목별 최근 $N$개(기본 50,000틱)만 원형 유지.
- **Window Bar Aggregator**: 들어오는 틱을 실시간으로 1분/5분 캔들로 조립하고, 마감 시점(`on_bar_close`)에 콜백 및 메시지 큐로 이벤트 발행.

```
[WebSocket / Polling / Mock Source]
               │
               ▼ (Tick Events)
    ┌─────────────────────┐
    │  RealtimeStreamer   │
    └──────────┬──────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐ ┌─────────────────────────┐
│ Ring Buffer  │ │  Window Bar Aggregator  │
│ (Max 50k틱)  │ │ (Tick-to-1m/5m Candle)  │
└──────────────┘ └────────────┬────────────┘
                              │ (Bar Closed Event)
                              ▼
                 [ML/RL Feature Extractor]
```

### 3.2 핵심 자료구조 및 인터페이스

```python
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional, Callable, Any
import threading

@dataclass
class TickData:
    timestamp: datetime
    symbol: str
    price: float
    volume: int
    accum_volume: int
    side: str = 'UNKNOWN'       # 'BUY', 'SELL', 'UNKNOWN'
    bid_price: float = 0.0      # 최우선 매수호가
    ask_price: float = 0.0      # 최우선 매도호가
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0

@dataclass
class OrderbookLevel:
    price: float
    volume: int

@dataclass
class OrderbookData:
    timestamp: datetime
    symbol: str
    bids: List[OrderbookLevel] = field(default_factory=list)  # 매수 10호가
    asks: List[OrderbookLevel] = field(default_factory=list)  # 매도 10호가
    total_bid_volume: int = 0
    total_ask_volume: int = 0

class RealtimeRingBuffer:
    def __init__(self, capacity_per_symbol: int = 50000):
        self.capacity = capacity_per_symbol
        self._buffers: Dict[str, deque] = {}
        self._lock = threading.Lock()

    def append(self, tick: TickData):
        with self._lock:
            if tick.symbol not in self._buffers:
                self._buffers[tick.symbol] = deque(maxlen=self.capacity)
            self._buffers[tick.symbol].append(tick)

    def get_recent_ticks(self, symbol: str, count: int = 100) -> List[TickData]:
        with self._lock:
            buf = self._buffers.get(symbol, deque())
            return list(buf)[-count:]

    def to_dataframe(self, symbol: str) -> pd.DataFrame:
        ticks = self.get_recent_ticks(symbol, self.capacity)
        if not ticks:
            return pd.DataFrame()
        return pd.DataFrame([t.__dict__ for t in ticks])

class WindowBarAggregator:
    def __init__(self, symbol: str, interval_seconds: int = 60, on_bar_closed: Optional[Callable] = None):
        self.symbol = symbol
        self.interval = interval_seconds
        self.on_bar_closed = on_bar_closed
        self.current_bar: Optional[Dict[str, Any]] = None
        self.current_window_start: Optional[datetime] = None

    def process_tick(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """
        틱 데이터를 수신하여 현재 캔들 업데이트.
        캔들 마감 시간이 도래하면 이전 캔들을 반환하고 새 캔들 개시.
        """
        ...
```

### 3.3 스트리머 모듈 및 Mock 구현
- `MockStreamer`: 백테스팅, 유닛 테스트, 장 마감 후 시뮬레이션을 위해 Geometric Brownian Motion(GBM) 기반 가상 틱 스트림 발행.
- `NaverPollingStreamer`: `polling.finance.naver.com`을 1초 간격으로 폴링하여 실시간 체결가/누적거래량 변화를 틱으로 변환.
- `KiwoomWebSocketStreamer`: 키움/한투 실시간 WebSocket API 연동을 위한 인터페이스 규격.

---

## 4. R3: Data Consolidation & Pipeline (`modules/data/consolidator.py`)

### 4.1 Look-ahead Bias 방지 및 Point-in-Time(PIT) 정렬 알고리즘

#### (1) 문제 정의
- 분기 재무제표는 해당 분기 마지막 날(예: 3월 31일)로 작성되지만, 실제 시장에 공시되는 시점은 법정 공시 기한인 **공시일(Announcement Date / DART rcept_dt, 예: 5월 15일)**임.
- 공시일 이전 거래일(4월 1일 ~ 5월 14일)에 1분기 실적 데이터를 매핑하여 학습/매매 모델에 입력하면 미래 정보를 사용하는 **선행 편향(Look-ahead bias)**이 발생하여 백테스트가 심각하게 왜곡됨.

#### (2) 해결 알고리즘: `merge_asof(direction='backward')`
1. 주가 데이터: `price_df` (정렬 기준: `date`)
2. 재무 데이터: `fundamental_df` (정렬 기준: `announcement_date`)
3. `pd.merge_asof` 연산:
   $$\text{Merged}(t) = \text{Price}(t) \bowtie_{\text{asof}} \text{Fundamental}(\max \{ d_{\text{announce}} \le t \})$$
4. 공시일 이전 시점에는 해당 시점에 합법적으로 알려져 있던 직전 분기/사업보고서의 재무 지표가 유지됨.

```python
# Look-ahead Bias 차단 결합 로직
merged_df = pd.merge_asof(
    price_df.sort_values('date'),
    fundamental_df.sort_values('announcement_date'),
    left_on='date',
    right_on='announcement_date',
    by='symbol',
    direction='backward'
)
```

### 4.2 동적 밸류에이션 피처(Dynamic Valuation Features) 산출식
정적 재무제표의 PER/PBR은 공시 시점의 주가로 고정되어 있으므로, 매일 변동하는 일별 종가($Price_t$)에 맞추어 실시간 동적 지표를 재계산한다.

1. **동적 PER (Dynamic PER)**:
   $$Dynamic\_PER_t = \frac{Close_t}{EPS_{\text{valid}}}$$
   (단, $EPS_{\text{valid}} \le 0$인 경우 `NaN` 처리 및 `warning_flags`에 'NEGATIVE_EPS' 마킹)

2. **동적 PBR (Dynamic PBR)**:
   $$Dynamic\_PBR_t = \frac{Close_t}{BPS_{\text{valid}}}$$

3. **동적 시가총액 (Dynamic Market Cap)**:
   $$Market\_Cap_t = Close_t \times Listed\_Shares_{\text{valid}}$$

4. **기술적 파생 피처 (Technical Derived Features)**:
   - 일일 수익률: $Return_t = (Close_t - Close_{t-1}) / Close_{t-1}$
   - 20일 역사적 변동성: $\sigma_{20d} = \text{Std}(Return_{t-19 \dots t}) \times \sqrt{252}$
   - 5일 / 20일 / 60일 이동평균선 및 이격도: $Disparity_{20d} = Close_t / MA20_t \times 100$

### 4.3 통합 데이터프레임 스키마 (Consolidated Schema)

| 대분류 | 컬럼명 | 데이터 타입 | 필수여부 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| **식별자/시간** | `date` | `date32` / `timestamp[ns]` | 필수 | 거래 일자 |
| | `symbol` | `string` | 필수 | 종목코드 (e.g. '005930') |
| **가격 데이터** | `open` | `float64` | 필수 | 시가 |
| | `high` | `float64` | 필수 | 고가 |
| | `low` | `float64` | 필수 | 저가 |
| | `close` | `float64` | 필수 | 종가 |
| | `volume` | `int64` | 필수 | 거래량 |
| | `value` | `float64` | 필수 | 거래대금 |
| **재무/공시 메타** | `announcement_date` | `date32` / `timestamp[ns]` | 필수 | 실제 DART 공시일자 |
| | `report_type` | `string` | 필수 | 보고서 유형 ('1Q', '2Q', '3Q', '4Q/연간') |
| | `revenue` | `float64` | 선택 | 매출액 (단위: 억 또는 원) |
| | `operating_income` | `float64` | 필수 | 영업이익 |
| | `net_income` | `float64` | 필수 | 당기순이익 |
| | `total_assets` | `float64` | 선택 | 자산총계 |
| | `total_liabilities` | `float64` | 선택 | 부채총계 |
| | `total_equity` | `float64` | 필수 | 자본총계 |
| | `eps` | `float64` | 필수 | 주당순이익 |
| | `bps` | `float64` | 필수 | 주당순자산 |
| | `roe` | `float64` | 선택 | 자기자본이익률 (%) |
| | `debt_ratio` | `float64` | 선택 | 부채비율 (%) |
| **동적 지표** | `dynamic_per` | `float64` | 필수 | 일별 종가 기준 동적 PER |
| | `dynamic_pbr` | `float64` | 필수 | 일별 종가 기준 동적 PBR |
| | `dynamic_market_cap` | `float64` | 선택 | 동적 시가총액 |
| **기술적 파생** | `returns_1d` | `float64` | 필수 | 1일 수익률 |
| | `volatility_20d` | `float64` | 선택 | 20일 연율화 변동성 |
| | `ma_5`, `ma_20`, `ma_60` | `float64` | 선택 | 이동평균선 |
| **품질/플래그** | `is_cross_verified` | `boolean` | 필수 | R1 교차 검증 통과 여부 |
| | `warning_flags` | `string` | 필수 | 결측/이상치 경고 플래그 (JSON or Pipe delimited) |

---

## 5. R3: Parquet Storage Architecture (`data/raw/`)

### 5.1 디렉토리 레이아웃 및 파티셔닝 전략

```
/home/imnyj/Workspace/Auto_Stock/data/raw/
├── price/
│   ├── daily/
│   │   └── symbol=005930/
│   │       └── data.parquet
│   └── minute/
│       ├── timeframe=1m/
│       │   └── symbol=005930/
│       │       └── year=2026/
│       │           └── month=08/
│       │               └── data.parquet
│       └── timeframe=5m/...
├── fundamental/
│   └── symbol=005930/
│       └── fundamental_reports.parquet
└── consolidated/
    ├── daily/
    │   └── symbol=005930/
    │       └── consolidated_daily.parquet
    └── minute/
        └── timeframe=1m/
            └── symbol=005930/
                └── year=2026/
                    └── consolidated_minute.parquet
```

### 5.2 PyArrow 스키마 정의 (Strict Typing)

```python
import pyarrow as pa

CONSOLIDATED_DAILY_SCHEMA = pa.schema([
    ('date', pa.date32()),
    ('symbol', pa.string()),
    ('open', pa.float64()),
    ('high', pa.float64()),
    ('low', pa.float64()),
    ('close', pa.float64()),
    ('volume', pa.int64()),
    ('value', pa.float64()),
    ('announcement_date', pa.date32()),
    ('report_type', pa.string()),
    ('revenue', pa.float64()),
    ('operating_income', pa.float64()),
    ('net_income', pa.float64()),
    ('total_assets', pa.float64()),
    ('total_liabilities', pa.float64()),
    ('total_equity', pa.float64()),
    ('eps', pa.float64()),
    ('bps', pa.float64()),
    ('roe', pa.float64()),
    ('debt_ratio', pa.float64()),
    ('dynamic_per', pa.float64()),
    ('dynamic_pbr', pa.float64()),
    ('dynamic_market_cap', pa.float64()),
    ('returns_1d', pa.float64()),
    ('volatility_20d', pa.float64()),
    ('is_cross_verified', pa.bool_()),
    ('warning_flags', pa.string())
])
```

### 5.3 Parquet 최적화 파라미터 규격

| 파라미터 | 권장 설정값 | 근거 |
| :--- | :--- | :--- |
| `compression` | `'ZSTD'` | Snappy 대비 25~35% 압축률 우수, 고속 디코딩 지원 |
| `compression_level` | `3` | 압축 속도와 압축률 간 최적의 균형 |
| `use_dictionary` | `True` (`symbol`, `report_type`, `warning_flags`) | 중복 문자열 저장 공간 대폭 절감 |
| `row_group_size` | `250,000` | 분봉 및 일봉 데이터 스캔 시 I/O 블록 최적화 |
| `write_statistics` | `True` | Predicate Pushdown (특정 날짜 범위 스킵 필터링) 최적화 |

---

## 6. 결측치 및 경계 조건(Edge Cases) 방어 전략

1. **상장폐지 및 거래정지 (Trading Halt)**:
   - Volume이 0이고 $Open = High = Low = Close$인 거래일은 `is_trading_halt = True`로 기록하되, 머신러닝 학습 시 연속성 유지를 위해 가격은 유지하고 체결 불가능 액션 마스크 생성.
2. **신규 상장 종목 및 공시 이전 구간**:
   - DART 최초 공시 이전 구간의 경우 재무 지표 컬럼은 `NaN`으로 채우고 `warning_flags`에 `'PRE_ANNOUNCEMENT_PERIOD'`를 부여.
   - ML 모델 학습 시 `fillna` 전략 또는 마스크 피처 활용 가이드 제공.
3. **적자 기업 (Negative Net Income / Negative EPS)**:
   - PER 계산 시 $EPS \le 0$이면 $Dynamic\_PER$은 `NaN`으로 처리하고, $Dynamic\_PBR$ 및 $EV/EBITDA$를 대안 지표로 활용할 수 있도록 플래깅.
4. **액면분할 및 감자 (Stock Split & Reverse Split)**:
   - 과거 가격에 대해 수정주가 배율(`adj_factor`)을 적용하여 주가 갭 단절 방지.

---

## 7. 검증 및 승인 테스트 기준 (Acceptance Criteria)

1. **단위 테스트 (`tests/test_collector_price.py`, `tests/test_streamer.py`, `tests/test_consolidator.py`)**:
   - `NaverPriceFetcher` 및 `MockStreamer` 단위 기능 검증.
   - 1분봉 데이터의 5분/15분/60분 리샘플링 무결성 검증 ($Open_{\text{start}} = Open_{\text{resampled}}$, $High = \max(High)$, $Low = \min(Low)$, $Close_{\text{end}} = Close_{\text{resampled}}$, $Volume = \sum Volume$).
   - `merge_asof` 수행 시 공시일 이전 데이터 누출(Look-ahead) 여부 자동화 검증.
2. **E2E 통합 테스트 (`tests/test_phase1.py`)**:
   - 삼성전자(`005930`) 5개년 일봉 및 당일 1분봉 수집 -> 재무 데이터와 PIT 결합 -> `data/raw/consolidated/daily/symbol=005930/` Parquet 저장 및 재로딩 검증.
   - Parquet 스키마 일치 여부 및 결측치 플래깅 정상 동작 검증.
