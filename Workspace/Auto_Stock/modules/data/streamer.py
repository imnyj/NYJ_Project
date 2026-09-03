"""
modules/data/streamer.py
========================
실시간 시세 수신, 링버퍼 캐싱, 틱-캔들 동적 집계 모듈.

주요 구성:
1. TickData, OrderbookLevel, OrderbookData, BarData: 고빈도 시세 데이터 모델
2. CircularBuffer / RealtimeRingBuffer: collections.deque 기반 스레드 안전 원형 링 버퍼
3. WindowBarAggregator: 실시간 틱 스트림 기반 1분/5분 OHLCV 캔들 동적 집계기
4. BaseStreamer: 실시간 스트리머 기본 인터페이스
5. MockStreamer: 백테스트/유닛 테스트/오프라인 시뮬레이션용 가상 틱 스트리머
6. NaverPollingStreamer / RealtimeStreamer: 네이버 금융 실시간 폴링 API 기반 스트리머
"""

import logging
import re
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Union

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)


# ==========================================
# 1. 시세 데이터 모델 정의 (Data Structures)
# ==========================================

@dataclass
class TickData:
    """단일 체결 틱 데이터 구조체"""
    timestamp: datetime
    symbol: str
    price: float
    volume: int
    accum_volume: int = 0
    side: str = 'UNKNOWN'       # 'BUY', 'SELL', 'UNKNOWN'
    bid_price: float = 0.0      # 최우선 매수호가
    ask_price: float = 0.0      # 최우선 매도호가
    open_price: float = 0.0     # 당일 시가
    high_price: float = 0.0     # 당일 고가
    low_price: float = 0.0      # 당일 저가
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "accum_volume": self.accum_volume,
            "side": self.side,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TickData":
        """딕셔너리로부터 생성"""
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = pd.to_datetime(ts).to_pydatetime()
        elif isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()

        return cls(
            timestamp=ts,
            symbol=str(data.get("symbol", "")),
            price=float(data.get("price", 0.0)),
            volume=int(data.get("volume", 0)),
            accum_volume=int(data.get("accum_volume", 0)),
            side=str(data.get("side", "UNKNOWN")),
            bid_price=float(data.get("bid_price", 0.0)),
            ask_price=float(data.get("ask_price", 0.0)),
            open_price=float(data.get("open_price", 0.0)),
            high_price=float(data.get("high_price", 0.0)),
            low_price=float(data.get("low_price", 0.0)),
            raw_data=data.get("raw_data")
        )


@dataclass
class OrderbookLevel:
    """호가 잔량 단위 레벨"""
    price: float
    volume: int


@dataclass
class OrderbookData:
    """10단계 호가 데이터 구조체"""
    timestamp: datetime
    symbol: str
    bids: List[OrderbookLevel] = field(default_factory=list)  # 매수 호가 (내림차순)
    asks: List[OrderbookLevel] = field(default_factory=list)  # 매도 호가 (오름차순)
    total_bid_volume: int = 0
    total_ask_volume: int = 0


@dataclass
class BarData:
    """실시간 집계된 단일 OHLCV 캔들 데이터 구조체"""
    symbol: str
    timeframe: str
    timestamp: datetime  # 캔들 시작 시각 (Bucket Start)
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float = 0.0
    tick_count: int = 0
    is_closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.timestamp,
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "value": self.value,
            "timeframe": self.timeframe,
            "tick_count": self.tick_count,
            "is_closed": self.is_closed,
            "is_trading_halt": bool(self.volume == 0 and self.open == self.high == self.low == self.close)
        }


# ==========================================
# 2. 스레드 안전 원형 링 버퍼 (CircularBuffer)
# ==========================================

class CircularBuffer:
    """
    고성능 및 메모리 누수 방어 스레드 안전 원형 버퍼 (Ring Buffer).
    - 종목별 독립적인 `deque(maxlen=capacity)` 할당으로 O(1) 삽입 및 고정 메모리 한도 보장.
    - 멀티스레드 환경에서 안전한 RLock 동기화 제공.
    """

    def __init__(self, capacity_per_symbol: int = 50000, max_symbols: Optional[int] = None):
        self.capacity = capacity_per_symbol
        self.max_symbols = max_symbols
        self._buffers: Dict[str, deque] = {}
        self._lock = threading.RLock()

    def append(self, tick: TickData) -> None:
        """단일 틱 추가 (버퍼가 가득 차면 가장 오래된 틱 자동 폐기)"""
        with self._lock:
            if tick.symbol not in self._buffers:
                if self.max_symbols is not None and len(self._buffers) >= self.max_symbols:
                    # 종목 수 한도 초과 시 가장 오래된 종목 키 제거하여 메모리 무한 증식 방지
                    oldest_sym = next(iter(self._buffers.keys()))
                    del self._buffers[oldest_sym]
                self._buffers[tick.symbol] = deque(maxlen=self.capacity)
            self._buffers[tick.symbol].append(tick)

    def remove_symbol(self, symbol: str) -> None:
        """특정 종목의 버퍼 및 키 완전 제거"""
        with self._lock:
            self._buffers.pop(symbol, None)

    def close(self) -> None:
        """버퍼 초기화 및 메모리 해제"""
        self.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def extend(self, ticks: Iterable[TickData]) -> None:
        """복수 틱 일괄 추가"""
        with self._lock:
            for tick in ticks:
                self.append(tick)

    def get_recent_ticks(self, symbol: str, count: int = 100) -> List[TickData]:
        """최근 N개 틱 반환 (시간순 오름차순)"""
        with self._lock:
            buf = self._buffers.get(symbol)
            if not buf:
                return []
            if count >= len(buf):
                return list(buf)
            # deque 슬라이싱
            return list(buf)[-count:]

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """가장 최근의 1개 틱 반환"""
        with self._lock:
            buf = self._buffers.get(symbol)
            if buf and len(buf) > 0:
                return buf[-1]
            return None

    def get_all(self, symbol: str) -> List[TickData]:
        """해당 종목의 모든 캐시된 틱 반환"""
        with self._lock:
            buf = self._buffers.get(symbol)
            return list(buf) if buf else []

    def to_dataframe(self, symbol: str, count: Optional[int] = None) -> pd.DataFrame:
        """캐시된 틱 데이터를 Pandas DataFrame으로 변환"""
        ticks = self.get_recent_ticks(symbol, count=count or self.capacity)
        if not ticks:
            return pd.DataFrame(columns=[
                "timestamp", "symbol", "price", "volume", "accum_volume",
                "side", "bid_price", "ask_price", "open_price", "high_price", "low_price"
            ])
        return pd.DataFrame([t.to_dict() for t in ticks])

    def size(self, symbol: str) -> int:
        """특정 종목의 현재 버퍼 틱 수"""
        with self._lock:
            buf = self._buffers.get(symbol)
            return len(buf) if buf else 0

    def total_size(self) -> int:
        """전체 종목의 총 버퍼 틱 수"""
        with self._lock:
            return sum(len(buf) for buf in self._buffers.values())

    def clear(self, symbol: Optional[str] = None) -> None:
        """특정 종목 또는 전체 버퍼 초기화"""
        with self._lock:
            if symbol:
                if symbol in self._buffers:
                    self._buffers[symbol].clear()
            else:
                self._buffers.clear()

    def symbols(self) -> List[str]:
        """버퍼에 존재하는 종목코드 목록"""
        with self._lock:
            return list(self._buffers.keys())


# RealtimeRingBuffer 별칭 제공
RealtimeRingBuffer = CircularBuffer


# ==========================================
# 3. 틱-캔들 동적 집계기 (WindowBarAggregator)
# ==========================================

class WindowBarAggregator:
    """
    실시간 틱 스트림을 지정된 주기(예: 1m, 5m, 15m)의 OHLCV 캔들로 동적 집계하는 어그리게이터.
    - 슬라이딩 시간 윈도우 기반 버킷팅.
    - 윈도우 마감 시점(`on_bar_closed`) 콜백 트리거 및 폐쇄된 캔들 반환.
    """

    def __init__(
        self,
        symbol: str,
        interval_seconds: int = 60,
        timeframe_name: Optional[str] = None,
        on_bar_closed: Optional[Callable[[BarData], None]] = None
    ):
        self.symbol = symbol
        self.interval_seconds = interval_seconds
        self.timeframe = timeframe_name or f"{max(1, interval_seconds // 60)}m"
        self.on_bar_closed = on_bar_closed

        self.current_bar: Optional[BarData] = None
        self.current_window_start: Optional[datetime] = None
        self._closed_bars: List[BarData] = []
        self._lock = threading.RLock()

    def _get_window_start(self, ts: datetime) -> datetime:
        """타임스탬프를 구간 시작 시각으로 바닥내림(Floor) 계산"""
        epoch = datetime(1970, 1, 1)
        total_seconds = int((ts - epoch).total_seconds())
        floored_seconds = (total_seconds // self.interval_seconds) * self.interval_seconds
        return epoch + timedelta(seconds=floored_seconds)

    def process_tick(self, tick: TickData) -> Optional[BarData]:
        """
        새 틱 데이터를 수신하여 현재 캔들에 누적.
        시간 경계(Boundary)를 넘어가면 이전 캔들을 마감하고 새 캔들을 개시.
        마감된 캔들이 발생한 경우 해당 BarData를 반환, 그렇지 않으면 None 반환.
        """
        if tick.symbol != self.symbol:
            return None

        with self._lock:
            window_start = self._get_window_start(tick.timestamp)
            closed_bar: Optional[BarData] = None

            # 최초 틱인 경우
            if self.current_bar is None or self.current_window_start is None:
                self.current_window_start = window_start
                self.current_bar = BarData(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    timestamp=window_start,
                    open=tick.price,
                    high=tick.price,
                    low=tick.price,
                    close=tick.price,
                    volume=tick.volume,
                    value=float(tick.price * tick.volume),
                    tick_count=1,
                    is_closed=False
                )
                return None

            # 동일 윈도우 내의 틱인 경우
            if window_start == self.current_window_start:
                self.current_bar.high = max(self.current_bar.high, tick.price)
                self.current_bar.low = min(self.current_bar.low, tick.price)
                self.current_bar.close = tick.price
                self.current_bar.volume += tick.volume
                self.current_bar.value += float(tick.price * tick.volume)
                self.current_bar.tick_count += 1
                return None

            # 새로운 윈도우가 시작된 경우 (이전 캔들 마감)
            if window_start > self.current_window_start:
                self.current_bar.is_closed = True
                closed_bar = self.current_bar
                self._closed_bars.append(closed_bar)

                # 콜백 실행
                if self.on_bar_closed:
                    try:
                        self.on_bar_closed(closed_bar)
                    except Exception as ce:
                        logger.error(f"Error in on_bar_closed callback: {ce}")

                # 새 캔들 생성
                self.current_window_start = window_start
                self.current_bar = BarData(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    timestamp=window_start,
                    open=tick.price,
                    high=tick.price,
                    low=tick.price,
                    close=tick.price,
                    volume=tick.volume,
                    value=float(tick.price * tick.volume),
                    tick_count=1,
                    is_closed=False
                )
                return closed_bar

            # 과거 시각의 지연 틱인 경우 (현재 캔들에 반영만 수행)
            self.current_bar.high = max(self.current_bar.high, tick.price)
            self.current_bar.low = min(self.current_bar.low, tick.price)
            self.current_bar.volume += tick.volume
            self.current_bar.value += float(tick.price * tick.volume)
            self.current_bar.tick_count += 1
            return None

    def force_close(self) -> Optional[BarData]:
        """현재 진행 중인 캔들을 즉시 마감"""
        with self._lock:
            if self.current_bar and not self.current_bar.is_closed:
                self.current_bar.is_closed = True
                closed = self.current_bar
                self._closed_bars.append(closed)
                if self.on_bar_closed:
                    try:
                        self.on_bar_closed(closed)
                    except Exception as ce:
                        logger.error(f"Error in on_bar_closed during force_close: {ce}")
                self.current_bar = None
                self.current_window_start = None
                return closed
            return None

    def get_current_bar(self) -> Optional[BarData]:
        """현재 진행 중인 캔들 반환"""
        with self._lock:
            return self.current_bar

    def get_closed_bars(self) -> List[BarData]:
        """마감 완료된 모든 캔들 반환"""
        with self._lock:
            return list(self._closed_bars)

    def to_dataframe(self) -> pd.DataFrame:
        """마감된 캔들과 현재 진행 중인 캔들을 DataFrame으로 변환"""
        with self._lock:
            bars = list(self._closed_bars)
            if self.current_bar:
                bars.append(self.current_bar)
            if not bars:
                return pd.DataFrame(columns=[
                    "date", "symbol", "open", "high", "low", "close",
                    "volume", "value", "timeframe", "tick_count", "is_closed", "is_trading_halt"
                ])
            return pd.DataFrame([b.to_dict() for b in bars])


# ==========================================
# 4. 실시간 스트리머 인터페이스 & 구현체
# ==========================================

class BaseStreamer(ABC):
    """실시간 시세 스트리머 추상 인터페이스"""

    def __init__(self, ring_buffer: Optional[CircularBuffer] = None):
        self.ring_buffer = ring_buffer or CircularBuffer(capacity_per_symbol=50000)
        self._subscribed_symbols: Set[str] = set()
        self._listeners: List[Callable[[TickData], None]] = []
        self._aggregators: Dict[str, List[WindowBarAggregator]] = {}
        self._is_running = False
        self._lock = threading.RLock()

    def subscribe(self, symbol: str) -> None:
        """구독 종목 추가"""
        with self._lock:
            clean = str(symbol).strip().zfill(6) if symbol.isdigit() else str(symbol).strip()
            self._subscribed_symbols.add(clean)

    def unsubscribe(self, symbol: str) -> None:
        """구독 종목 해제"""
        with self._lock:
            clean = str(symbol).strip().zfill(6) if symbol.isdigit() else str(symbol).strip()
            self._subscribed_symbols.discard(clean)

    def add_listener(self, callback: Callable[[TickData], None]) -> None:
        """틱 수신 리스너 등록"""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def register_listener(self, callback: Callable[[TickData], None]) -> None:
        """add_listener 별칭"""
        self.add_listener(callback)

    def remove_listener(self, callback: Callable[[TickData], None]) -> None:
        """리스너 등록 해제"""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def attach_aggregator(self, aggregator: WindowBarAggregator) -> None:
        """캔들 어그리게이터 연결"""
        with self._lock:
            sym = aggregator.symbol
            if sym not in self._aggregators:
                self._aggregators[sym] = []
            self._aggregators[sym].append(aggregator)

    def _dispatch_tick(self, tick: TickData) -> None:
        """수신된 틱을 링버퍼, 리스너, 어그리게이터로 전파"""
        # 1. 링버퍼 캐싱
        self.ring_buffer.append(tick)

        # 2. 어그리게이터 처리
        with self._lock:
            aggs = self._aggregators.get(tick.symbol, [])
            listeners = list(self._listeners)

        for agg in aggs:
            try:
                agg.process_tick(tick)
            except Exception as ae:
                logger.error(f"Error dispatching tick to aggregator: {ae}")

        # 3. 등록된 리스너 콜백 실행
        for listener in listeners:
            try:
                listener(tick)
            except Exception as le:
                logger.error(f"Error executing tick listener: {le}")

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """최신 1개 틱 조회"""
        clean = str(symbol).strip().zfill(6) if symbol.isdigit() else str(symbol).strip()
        return self.ring_buffer.get_latest_tick(clean)

    def get_cached_window(self, symbol: str, count: int = 100) -> pd.DataFrame:
        """최근 N개 캐시된 틱 데이터프레임 조회"""
        clean = str(symbol).strip().zfill(6) if symbol.isdigit() else str(symbol).strip()
        return self.ring_buffer.to_dataframe(clean, count=count)

    def is_running(self) -> bool:
        """실행 상태 여부"""
        return self._is_running

    @abstractmethod
    def start(self) -> None:
        """스트리머 시작"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """스트리머 중지"""
        pass

    def close(self) -> None:
        """스트리머 중지 및 리소스 정리"""
        self.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MockStreamer(BaseStreamer):
    """
    단위 테스트, 백테스팅, 오프라인 시뮬레이션을 위한 가상 틱 스트리머.
    기하 브라운 운동(GBM) 기반의 연속 틱 생성 또는 수동 틱 방출 지원.
    """

    def __init__(
        self,
        ring_buffer: Optional[CircularBuffer] = None,
        base_prices: Optional[Dict[str, float]] = None,
        tick_interval: float = 0.1,
        volatility: float = 0.001,
        seed: Optional[int] = 42
    ):
        super().__init__(ring_buffer=ring_buffer)
        self.base_prices = base_prices or {"005930": 70000.0, "000660": 150000.0}
        self.tick_interval = tick_interval
        self.volatility = volatility
        self.rng = np.random.default_rng(seed)
        self._current_prices: Dict[str, float] = dict(self.base_prices)
        self._accum_volumes: Dict[str, int] = {k: 0 for k in self.base_prices}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def emit_tick(self, tick: TickData) -> None:
        """단일 틱 수동 방출 (결정론적 유닛 테스트용)"""
        self._dispatch_tick(tick)

    def generate_ticks(
        self,
        symbol: str,
        count: int,
        start_price: Optional[float] = None,
        start_time: Optional[datetime] = None,
        time_step_ms: int = 500
    ) -> List[TickData]:
        """지정된 개수의 가상 틱 시퀀스를 일괄 생성 및 방출"""
        price = start_price or self.base_prices.get(symbol, 70000.0)
        curr_time = start_time or datetime.now()
        accum_vol = self._accum_volumes.get(symbol, 0)
        ticks = []

        for _ in range(count):
            ret = self.rng.normal(0, self.volatility)
            price = max(100.0, round(price * (1.0 + ret), 0))
            vol = int(self.rng.integers(1, 500))
            accum_vol += vol
            side = 'BUY' if ret >= 0 else 'SELL'
            spread = max(50.0, round(price * 0.001, 0))

            tick = TickData(
                timestamp=curr_time,
                symbol=symbol,
                price=price,
                volume=vol,
                accum_volume=accum_vol,
                side=side,
                bid_price=price - spread,
                ask_price=price + spread,
                open_price=start_price or price,
                high_price=price + spread * 2,
                low_price=price - spread * 2
            )
            ticks.append(tick)
            self._dispatch_tick(tick)
            curr_time += timedelta(milliseconds=time_step_ms)

        self._current_prices[symbol] = price
        self._accum_volumes[symbol] = accum_vol
        return ticks

    def _run_loop(self) -> None:
        """백그라운드 틱 생성 루프"""
        while not self._stop_event.is_set():
            with self._lock:
                symbols = list(self._subscribed_symbols) or list(self.base_prices.keys())

            for symbol in symbols:
                price = self._current_prices.get(symbol, 70000.0)
                accum_vol = self._accum_volumes.get(symbol, 0)

                ret = self.rng.normal(0, self.volatility)
                price = max(100.0, round(price * (1.0 + ret), 0))
                vol = int(self.rng.integers(1, 200))
                accum_vol += vol
                side = 'BUY' if ret >= 0 else 'SELL'

                self._current_prices[symbol] = price
                self._accum_volumes[symbol] = accum_vol

                tick = TickData(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    price=price,
                    volume=vol,
                    accum_volume=accum_vol,
                    side=side,
                    bid_price=price - 100.0,
                    ask_price=price + 100.0
                )
                self._dispatch_tick(tick)

            self._stop_event.wait(self.tick_interval)

    def start(self) -> None:
        """가상 스트리밍 스레드 시작"""
        if self._is_running:
            return
        self._is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="MockStreamerThread")
        self._thread.start()
        logger.info("MockStreamer started.")

    def stop(self) -> None:
        """스트리밍 스레드 안전 중지"""
        if not self._is_running:
            return
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._is_running = False
        logger.info("MockStreamer stopped.")


class NaverPollingStreamer(BaseStreamer):
    """
    네이버 금융 실시간 시세 폴링 API 기반 스트리머.
    - 엔드포인트: https://polling.finance.naver.com/api/realtime/domestic/stock/{symbol}
    - 1~5초 주기로 최신 체결가 및 누적거래량을 수신하여 틱 이벤트로 변환.
    - 네트워크 일시 장애 시 자동 복구 및 백오프 적용.
    """

    POLL_URL = "https://polling.finance.naver.com/api/realtime/domestic/stock/{symbol}"

    def __init__(
        self,
        ring_buffer: Optional[CircularBuffer] = None,
        poll_interval: float = 2.0,
        timeout: int = 5,
        session: Optional[requests.Session] = None
    ):
        super().__init__(ring_buffer=ring_buffer)
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.session = session or requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self._last_accum_vols: Dict[str, int] = {}
        self._last_prices: Dict[str, float] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _poll_symbol(self, symbol: str) -> Optional[TickData]:
        """단일 종목 네이버 폴링 API 호출 및 틱 데이터 추출"""
        url = self.POLL_URL.format(symbol=symbol)
        try:
            resp = self.session.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"Naver polling returned status {resp.status_code} for {symbol}")
                return None
            data = resp.json()
            datas = data.get("datas", [])
            if not datas:
                return None

            item = datas[0]

            # 원시 필드 파싱
            close_p = float(item.get("closePriceRaw", str(item.get("closePrice", "0")).replace(",", "")))
            open_p = float(item.get("openPriceRaw", str(item.get("openPrice", "0")).replace(",", "")))
            high_p = float(item.get("highPriceRaw", str(item.get("highPrice", "0")).replace(",", "")))
            low_p = float(item.get("lowPriceRaw", str(item.get("lowPrice", "0")).replace(",", "")))
            accum_v = int(item.get("accumulatedTradingVolumeRaw", str(item.get("accumulatedTradingVolume", "0")).replace(",", "")))

            # 타임스탬프 파싱
            local_traded_at = item.get("localTradedAt")
            if local_traded_at:
                try:
                    ts = pd.to_datetime(local_traded_at).to_pydatetime()
                except Exception:
                    ts = datetime.now()
            else:
                ts = datetime.now()

            # 거래량 차분 계산
            prev_v = self._last_accum_vols.get(symbol)
            if prev_v is None:
                interval_v = 0
            else:
                interval_v = max(0, accum_v - prev_v)

            prev_p = self._last_prices.get(symbol, close_p)
            side = 'BUY' if close_p >= prev_p else 'SELL'

            self._last_accum_vols[symbol] = accum_v
            self._last_prices[symbol] = close_p

            return TickData(
                timestamp=ts,
                symbol=symbol,
                price=close_p,
                volume=interval_v,
                accum_volume=accum_v,
                side=side,
                bid_price=close_p - 100.0,
                ask_price=close_p + 100.0,
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                raw_data=item
            )
        except Exception as e:
            logger.warning(f"Error polling Naver API for {symbol}: {e}")
            return None

    def poll_once(self) -> List[TickData]:
        """등록된 모든 구독 종목을 1회 즉시 폴링 (동기 테스트용)"""
        with self._lock:
            symbols = list(self._subscribed_symbols)

        dispatched_ticks = []
        for symbol in symbols:
            tick = self._poll_symbol(symbol)
            if tick:
                self._dispatch_tick(tick)
                dispatched_ticks.append(tick)
        return dispatched_ticks

    def _run_loop(self) -> None:
        """백그라운드 폴링 루프"""
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}")
            self._stop_event.wait(self.poll_interval)

    def start(self) -> None:
        """폴링 스레드 시작"""
        if self._is_running:
            return
        self._is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="NaverPollingStreamerThread")
        self._thread.start()
        logger.info("NaverPollingStreamer started.")

    def stop(self) -> None:
        """폴링 스레드 안전 중지 및 좀비 스레드 방지"""
        if not self._is_running:
            return
        self._stop_event.set()
        if hasattr(self, "session") and self.session:
            try:
                self.session.close()
            except Exception as e:
                logger.debug(f"Error closing session on stop: {e}")
        if self._thread and self._thread.is_alive():
            join_timeout = max(10.0, float(self.timeout) * 3 + 5.0)
            self._thread.join(timeout=join_timeout)
        self._is_running = False
        logger.info("NaverPollingStreamer stopped.")

    def close(self) -> None:
        """스트리머 중지 및 세션 리소스 정리"""
        self.stop()


# RealtimeStreamer 기본 구현체 매핑
RealtimeStreamer = NaverPollingStreamer
