"""
modules/data/__init__.py
========================
Auto Stock ML/RL Trader — Phase 1: Data Collection & Processing Pipeline Package.

이 패키지는 펀더멘털 재무제표 수집(R1), 시계열 주가 수집 및 실시간 스트리밍(R2),
Look-ahead bias 방지 Point-in-Time 통합 병합 및 Parquet 고성능 저장(R3),
그리고 통합 파이프라인 Facade를 제공합니다.
"""

from modules.data.collector_fundamental import (
    BaseFundamentalSource,
    DiscrepancyItem,
    FinancialStatement,
    FundamentalCrossValidator,
    FundamentalDataCollector,
    MockKiwoomCollector,
    NaverFinanceCollector,
    OpenDartCollector,
    PeriodType,
    RealtimeValuation,
    ValidationReport,
    ValidationStatus,
    clean_numeric_str,
    parse_korean_money,
)
from modules.data.collector_price import (
    BasePriceFetcher,
    FetchError,
    MockPriceFetcher,
    NaverPriceFetcher,
    PriceDataCollector,
    PriceDataError,
    TimeFrame,
    ValidationError,
)
from modules.data.consolidator import (
    DataConsolidator,
)
from modules.data.pipeline import (
    DataCollectionPipeline,
    DataPipeline,
)
from modules.data.streamer import (
    BarData,
    BaseStreamer,
    CircularBuffer,
    MockStreamer,
    NaverPollingStreamer,
    OrderbookData,
    OrderbookLevel,
    RealtimeRingBuffer,
    RealtimeStreamer,
    TickData,
    WindowBarAggregator,
)
from modules.data.screener import (
    DynamicStockScreener,
    ScreenerConfig,
    ScreeningCriteria,
    ShardedPollingScheduler,
    StockScreener,
    TokenBucketLimiter,
)

__all__ = [
    # R1: Fundamental Collection & Validation
    "BaseFundamentalSource",
    "OpenDartCollector",
    "NaverFinanceCollector",
    "MockKiwoomCollector",
    "FundamentalCrossValidator",
    "FundamentalDataCollector",
    "PeriodType",
    "ValidationStatus",
    "FinancialStatement",
    "RealtimeValuation",
    "ValidationReport",
    "DiscrepancyItem",
    "clean_numeric_str",
    "parse_korean_money",
    # R2: Price Collection
    "BasePriceFetcher",
    "NaverPriceFetcher",
    "MockPriceFetcher",
    "PriceDataCollector",
    "TimeFrame",
    "PriceDataError",
    "FetchError",
    "ValidationError",
    # R2: Realtime Streaming & Buffering
    "TickData",
    "OrderbookLevel",
    "OrderbookData",
    "BarData",
    "CircularBuffer",
    "RealtimeRingBuffer",
    "WindowBarAggregator",
    "BaseStreamer",
    "MockStreamer",
    "NaverPollingStreamer",
    "RealtimeStreamer",
    # R3: Consolidation & Storage
    "DataConsolidator",
    # R3: Pipeline Facade
    "DataCollectionPipeline",
    "DataPipeline",
    # Phase 5: Dynamic Stock Screener
    "StockScreener",
    "ScreeningCriteria",
    "DynamicStockScreener",
    "ScreenerConfig",
    "ShardedPollingScheduler",
    "TokenBucketLimiter",
]
