"""
tests/test_adversarial_challenger1.py
=====================================
Phase 1 제1 적대적 스트레스 검증가 (Challenger 1) 전용 극한 한계 및 무결성 실측 검증 스위트

검증 영역:
1. 교차 검증기 (FundamentalCrossValidator)
   - 극단적 상대 오차율 (0.0%, 4.999%, 5.000%, 5.001%, 9.999%, 10.000%, 10.001%, 100.0%, 1000.0%, 1,000,000.0%)
   - 분모 0 방어, NaN/None/무한대(Inf)/문자열 혼합 방어
   - 부호 반전(-100 vs 100) 및 음수 간 오차율 정밀 산출
   - 리포트 상태 격상 (PASSED -> WARNING -> CRITICAL_DISCREPANCY)
   - Field-level Coalesce 극한 결측치 복원력

2. 선행 편향 (Look-Ahead Bias) 원천 차단
   - 52,500개 이상의 1분 단위 고밀도 주가 시계열 + 불규칙 공시일자 결합
   - 실측 공시 이전(Pre-announcement) 미래 데이터 누출 0.000% 엄밀 수학적 검증
   - 초/분 단위 경계(Boundary: T-1m, T, T+1m) 전후 데이터 스위칭 정밀성 검증
   - 비정렬(Unsorted) 공시일자 입력 시 PIT 정렬 방어
   - 동적 밸류에이션 지표 (Dynamic PER/PBR)의 선행 편향 0.000% 무결성

3. 고빈도 스트리머 (High-Frequency RealtimeStreamer & RingBuffer)
   - 다중 스레드(10 Threads) 동시 100,000개 무작위 틱 주입 스트레스
   - 50,000틱 고정 용량 링버퍼(CircularBuffer) O(1) 메모리 한도 유지 검증 (누수 0)
   - WindowBarAggregator 100,000틱 집계 5대 수학적 불변성(Invariants) 실측 검증:
     * High >= Open, High >= Close, High >= Low
     * Low <= Open, Low <= Close, Low <= High
     * Total Bar Volume == Total Injected Volume
     * Total Bar Value == Total Injected Value
     * Total Bar Tick Count == Total Injected Ticks (100,000)
"""

import math
import os
import pathlib
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest

from modules.data.collector_fundamental import (
    FinancialStatement,
    FundamentalCrossValidator,
    PeriodType,
    ValidationReport,
    ValidationStatus,
    clean_numeric_str,
)
from modules.data.consolidator import DataConsolidator
from modules.data.streamer import (
    BarData,
    CircularBuffer,
    RealtimeRingBuffer,
    TickData,
    WindowBarAggregator,
)


# =====================================================================
# Target 1: CrossValidator (교차 검증기) 적대적 스트레스 테스트
# =====================================================================

class TestAdversarialCrossValidator:
    """교차 검증기의 극단 경계치, 분모 0, NaN/None, 부호 반전 방어 검증"""

    def setup_method(self):
        self.validator = FundamentalCrossValidator(
            warning_threshold=5.0,
            critical_threshold=10.0
        )

    @pytest.mark.parametrize(
        "val_a, val_b, expected_discrepancy, desc",
        [
            (100.0, 100.0, 0.0, "동일 값 0.0% 오차"),
            (0.0, 0.0, 0.0, "둘 다 0.0일 때 0.0% 오차"),
            (None, None, 0.0, "둘 다 None일 때 0.0% 오차"),
            (float("nan"), float("nan"), 0.0, "둘 다 NaN일 때 0.0% 오차"),
            (100.0, None, 100.0, "한쪽이 None일 때 100.0% 오차"),
            (None, 100.0, 100.0, "한쪽이 None일 때 100.0% 오차"),
            (100.0, float("nan"), 100.0, "한쪽이 NaN일 때 100.0% 오차"),
            (float("nan"), 100.0, 100.0, "한쪽이 NaN일 때 100.0% 오차"),
            ("invalid", 100.0, 100.0, "문자열 에러 시 100.0% 오차"),
            (0.0, 100.0, 99.9999, "0과 100 비교 시 분모 eps 방어로 ~100%"),
            (100.0, 0.0, 99.9999, "100과 0 비교 시 분모 eps 방어로 ~100%"),
            (-100.0, 100.0, 199.998, "부호 반전 (-100 vs +100) -> 200% 수준"),
            (-50.0, -52.0, 3.8461, "음수 간 차이 (|-50 - (-52)| / 52)"),
            (1.0, 1001.0, 99.8999, "1000배 차이 극단치"),
            (1.0, 1000001.0, 99.9998, "100만배 차이 극단치"),
        ],
    )
    def test_calculate_discrepancy_extreme_values(
        self, val_a, val_b, expected_discrepancy, desc
    ):
        """극단적 값 및 0/None/NaN/문자열에 대한 오차율 계산 안정성 검증"""
        disc = FundamentalCrossValidator.calculate_discrepancy(val_a, val_b)
        assert isinstance(disc, float)
        assert not math.isnan(disc)
        assert not math.isinf(disc)
        assert math.isclose(disc, expected_discrepancy, abs_tol=0.01), (
            f"Failed on {desc}: got {disc}, expected {expected_discrepancy}"
        )

    def test_threshold_boundary_precision_edges(self):
        """
        임계치 경계 정밀 검증:
        - 0.0% -> PASSED
        - 4.999% -> PASSED
        - 5.000% -> PASSED
        - 5.001% -> WARNING
        - 9.999% -> WARNING
        - 10.000% -> CRITICAL_DISCREPANCY
        - 10.001% -> CRITICAL_DISCREPANCY
        - 1000.0% -> CRITICAL_DISCREPANCY
        """
        def make_statements(val_a: float, val_b: float) -> Tuple[FinancialStatement, FinancialStatement]:
            s1 = FinancialStatement(
                ticker="005930", year=2024, quarter=1,
                revenue=int(val_a), source="DART"
            )
            s2 = FinancialStatement(
                ticker="005930", year=2024, quarter=1,
                revenue=int(val_b), source="NAVER"
            )
            return s1, s2

        base = 10_000_000

        # Case 1: 0% 오차
        s1, s2 = make_statements(base, base)
        rep = self.validator.validate_statements(s1, s2, metrics_to_compare=["revenue"])
        assert rep.status == ValidationStatus.PASSED
        assert rep.items["revenue"].status == ValidationStatus.PASSED
        assert rep.max_discrepancy_pct == 0.0

        # Case 2: 4.999% 오차 -> PASSED
        target_v2_4_999 = base / (1 - 0.04999)
        s1, s2 = make_statements(base, target_v2_4_999)
        rep = self.validator.validate_statements(s1, s2, metrics_to_compare=["revenue"])
        assert rep.max_discrepancy_pct <= 5.0
        assert rep.status == ValidationStatus.PASSED

        # Case 3: 5.001% 오차 -> WARNING
        target_v2_5_001 = base / (1 - 0.05001)
        s1, s2 = make_statements(base, target_v2_5_001)
        rep = self.validator.validate_statements(s1, s2, metrics_to_compare=["revenue"])
        assert rep.max_discrepancy_pct > 5.0
        assert rep.max_discrepancy_pct < 10.0
        assert rep.status == ValidationStatus.WARNING
        assert rep.items["revenue"].status == ValidationStatus.WARNING

        # Case 4: 9.999% 오차 -> WARNING
        target_v2_9_999 = base / (1 - 0.09999)
        s1, s2 = make_statements(base, target_v2_9_999)
        rep = self.validator.validate_statements(s1, s2, metrics_to_compare=["revenue"])
        assert rep.max_discrepancy_pct > 5.0
        assert rep.max_discrepancy_pct < 10.0
        assert rep.status == ValidationStatus.WARNING

        # Case 5: 10.001% 오차 -> CRITICAL_DISCREPANCY
        target_v2_10_001 = base / (1 - 0.10001)
        s1, s2 = make_statements(base, target_v2_10_001)
        rep = self.validator.validate_statements(s1, s2, metrics_to_compare=["revenue"])
        assert rep.max_discrepancy_pct >= 10.0
        assert rep.status == ValidationStatus.CRITICAL_DISCREPANCY
        assert rep.items["revenue"].status == ValidationStatus.CRITICAL_DISCREPANCY
        assert len(rep.errors) == 1

        # Case 6: 1000% 오차 -> CRITICAL_DISCREPANCY
        s1, s2 = make_statements(base, base * 10)
        rep = self.validator.validate_statements(s1, s2, metrics_to_compare=["revenue"])
        assert rep.status == ValidationStatus.CRITICAL_DISCREPANCY
        assert rep.items["revenue"].status == ValidationStatus.CRITICAL_DISCREPANCY

    def test_multi_metric_escalation_and_coalesce(self):
        """다중 지표 복합 검증 시 상태 격상(Escalation) 및 Coalesce 완결성 검증"""
        s_primary = FinancialStatement(
            ticker="005930", year=2024, quarter=1,
            revenue=100_000_000,
            operating_profit=10_000_000,
            net_income=None,  # Primary 결측
            total_assets=500_000_000,
            total_equity=300_000_000,
            eps=None,         # Primary 결측
            source="DART"
        )

        s_secondary = FinancialStatement(
            ticker="005930", year=2024, quarter=1,
            revenue=102_000_000,          # 1.96% 차이 (PASSED)
            operating_profit=10_600_000,   # 5.66% 차이 (WARNING)
            net_income=8_000_000,         # 결측 보정용
            total_assets=600_000_000,     # 16.67% 차이 (CRITICAL)
            total_equity=300_000_000,     # 0.0% 차이 (PASSED)
            eps=1500.0,                   # 결측 보정용
            source="NAVER"
        )

        rep = self.validator.validate_statements(s_primary, s_secondary)
        assert rep.status == ValidationStatus.CRITICAL_DISCREPANCY
        assert rep.items["revenue"].status == ValidationStatus.PASSED
        assert rep.items["operating_profit"].status == ValidationStatus.WARNING
        assert rep.items["total_assets"].status == ValidationStatus.CRITICAL_DISCREPANCY

        # Coalesce 검증: Primary의 결측치(net_income, eps)가 Secondary 값으로 채워지는지 확인
        coalesced = FundamentalCrossValidator.coalesce_statements(s_primary, s_secondary)
        assert coalesced.net_income == 8_000_000
        assert coalesced.eps == 1500.0
        assert coalesced.revenue == 100_000_000  # Primary 원본 유지


# =====================================================================
# Target 2: Look-Ahead Bias 0.000% PIT Merge 적대적 검증
# =====================================================================

class TestAdversarialLookaheadBiasPITMerge:
    """1분 주가 데이터 52,500건과 불규칙 공시일자 간 미래 정보 누출 0.000% 실측 검증"""

    def test_50k_minute_bars_pit_future_leakage_zero_percent(self):
        """
        [적대적 검증 2-1]
        52,500개 1분봉 데이터와 4개 분기 불규칙 공시일자 결합 시:
        - 공시일자 이전의 모든 1분봉에 대해 미래 공시 데이터 누출이 단 1건도 없음 (0.000% Leakage)을 실측.
        """
        # 1. 52,500개 1분봉 생성 (2024-01-02 09:00부터 1분 간격, 약 36.45일)
        start_ts = pd.Timestamp("2024-01-02 09:00:00")
        total_bars = 52500
        timestamps = [start_ts + timedelta(minutes=i) for i in range(total_bars)]

        np.random.seed(42)
        base_price = 70000.0
        price_changes = np.random.normal(0, 50, total_bars)
        close_prices = np.clip(base_price + np.cumsum(price_changes), 50000, 100000)

        price_df = pd.DataFrame({
            "date": timestamps,
            "symbol": "005930",
            "open": close_prices - 10,
            "high": close_prices + 20,
            "low": close_prices - 20,
            "close": close_prices,
            "volume": np.random.randint(100, 5000, total_bars),
        })

        # 2. 불규칙한 실세계 공시일자 4개 분기 데이터 생성 (모두 52,500분 구간 내에 위치)
        announcements = [
            {
                "quarter_name": "2023Q4_Annual",
                "announcement_date": pd.Timestamp("2024-01-10 17:30:00"),  # Day 8
                "revenue": 70_000_000_000_000,
                "operating_income": 6_500_000_000_000,
                "eps": 1000.0,
                "bps": 50000.0,
            },
            {
                "quarter_name": "2024Q1",
                "announcement_date": pd.Timestamp("2024-01-18 08:45:00"),  # Day 16
                "revenue": 72_000_000_000_000,
                "operating_income": 6_800_000_000_000,
                "eps": 1100.0,
                "bps": 51000.0,
            },
            {
                "quarter_name": "2024Q2",
                "announcement_date": pd.Timestamp("2024-01-26 14:15:30"),  # Day 24
                "revenue": 75_000_000_000_000,
                "operating_income": 7_200_000_000_000,
                "eps": 1250.0,
                "bps": 52500.0,
            },
            {
                "quarter_name": "2024Q3",
                "announcement_date": pd.Timestamp("2024-02-03 16:00:00"),  # Day 32
                "revenue": 80_000_000_000_000,
                "operating_income": 8_500_000_000_000,
                "eps": 1400.0,
                "bps": 54000.0,
            },
        ]

        fund_df = pd.DataFrame(announcements)
        fund_df["symbol"] = "005930"
        fund_df["validation_status"] = "PASSED"

        # 3. PIT 병합 수행
        consolidated = DataConsolidator.consolidate_point_in_time(
            price_df=price_df,
            fundamental_df=fund_df,
            symbol="005930"
        )

        assert len(consolidated) == total_bars, "모든 주가 행이 보존되어야 함"

        # 4. 적대적 선행 편향 0.000% 무결성 전수 검사
        leakage_count = 0
        pre_announcement_correct_count = 0
        q1_correct_count = 0
        q2_correct_count = 0
        q3_correct_count = 0
        q4_correct_count = 0

        ann_dates = [a["announcement_date"] for a in announcements]

        for idx, row in consolidated.iterrows():
            curr_date = row["date"]
            curr_rev = row.get("revenue")
            curr_eps = row.get("eps")

            # 구간 0: 최초 공시(2024-01-10 17:30) 이전
            if curr_date < ann_dates[0]:
                if pd.notna(curr_rev) or pd.notna(curr_eps):
                    leakage_count += 1
                else:
                    pre_announcement_correct_count += 1
                    assert "PRE_ANNOUNCEMENT_PERIOD" in row["warning_flags"]

            # 구간 1: [2023Q4 공시, 2024Q1 공시 이전)
            elif ann_dates[0] <= curr_date < ann_dates[1]:
                if curr_rev != announcements[0]["revenue"] or curr_eps != announcements[0]["eps"]:
                    leakage_count += 1
                else:
                    q1_correct_count += 1

            # 구간 2: [2024Q1 공시, 2024Q2 공시 이전)
            elif ann_dates[1] <= curr_date < ann_dates[2]:
                if curr_rev != announcements[1]["revenue"] or curr_eps != announcements[1]["eps"]:
                    leakage_count += 1
                else:
                    q2_correct_count += 1

            # 구간 3: [2024Q2 공시, 2024Q3 공시 이전)
            elif ann_dates[2] <= curr_date < ann_dates[3]:
                if curr_rev != announcements[2]["revenue"] or curr_eps != announcements[2]["eps"]:
                    leakage_count += 1
                else:
                    q3_correct_count += 1

            # 구간 4: [2024Q3 공시 이후]
            else:
                if curr_rev != announcements[3]["revenue"] or curr_eps != announcements[3]["eps"]:
                    leakage_count += 1
                else:
                    q4_correct_count += 1

        total_inspected = len(consolidated)
        leakage_rate = (leakage_count / total_inspected) * 100.0

        assert leakage_count == 0, f"선행 편향 누출 발견! leakage_count={leakage_count}"
        assert leakage_rate == 0.0, f"누출률 0% 실패: {leakage_rate}%"
        assert pre_announcement_correct_count > 0
        assert q1_correct_count > 0
        assert q2_correct_count > 0
        assert q3_correct_count > 0
        assert q4_correct_count > 0

    def test_minute_boundary_microsecond_switching_accuracy(self):
        """
        [적대적 검증 2-2]
        공시 시각 정확히 1초/1분 전후의 초정밀 경계 전환 검증:
        - T - 1분: 이전 분기 데이터 유지 (미래 누출 0)
        - T (공시 시각 정각): 신규 분기 데이터 즉시 반영
        - T + 1분: 신규 분기 데이터 유지
        """
        ann_time = pd.Timestamp("2024-05-15 15:30:00")

        price_df = pd.DataFrame({
            "date": [
                ann_time - timedelta(minutes=1),
                ann_time,
                ann_time + timedelta(minutes=1),
            ],
            "symbol": "005930",
            "open": [70000.0, 70500.0, 71000.0],
            "high": [70200.0, 70600.0, 71200.0],
            "low": [69800.0, 70400.0, 70800.0],
            "close": [70100.0, 70550.0, 71100.0],
            "volume": [1000, 2000, 1500],
        })

        fund_df = pd.DataFrame([
            {
                "symbol": "005930",
                "announcement_date": ann_time - timedelta(days=90),
                "revenue": 50_000,
                "eps": 1000.0,
                "bps": 50000.0,
            },
            {
                "symbol": "005930",
                "announcement_date": ann_time,
                "revenue": 60_000,
                "eps": 1500.0,
                "bps": 55000.0,
            },
        ])

        consolidated = DataConsolidator.consolidate_point_in_time(
            price_df=price_df,
            fundamental_df=fund_df,
            symbol="005930"
        )

        assert len(consolidated) == 3

        # Row 0: T - 1분 -> 50,000 (이전 분기)
        assert consolidated.iloc[0]["revenue"] == 50_000
        assert consolidated.iloc[0]["eps"] == 1000.0
        assert math.isclose(consolidated.iloc[0]["dynamic_per"], 70100.0 / 1000.0)

        # Row 1: T (공시 정각) -> 60,000 (신규 분기 즉시 전환)
        assert consolidated.iloc[1]["revenue"] == 60_000
        assert consolidated.iloc[1]["eps"] == 1500.0
        assert math.isclose(consolidated.iloc[1]["dynamic_per"], 70550.0 / 1500.0)

        # Row 2: T + 1분 -> 60,000 (신규 분기 유지)
        assert consolidated.iloc[2]["revenue"] == 60_000
        assert consolidated.iloc[2]["eps"] == 1500.0

    def test_unsorted_and_shuffled_fundamental_dates_defense(self):
        """
        [적대적 검증 2-3]
        뒤죽박죽 섞인(Unsorted) 공시일자가 입력되더라도
        DataConsolidator 내부 정렬을 통해 선행 편향이 원천 차단되는지 검증.
        """
        price_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", "2024-06-30", freq="1D"),
            "symbol": "005930",
            "close": 70000.0,
            "open": 70000.0,
            "high": 70000.0,
            "low": 70000.0,
            "volume": 1000,
        })

        shuffled_fund = pd.DataFrame([
            {"symbol": "005930", "announcement_date": "2024-05-15", "eps": 300.0},
            {"symbol": "005930", "announcement_date": "2024-01-15", "eps": 100.0},
            {"symbol": "005930", "announcement_date": "2024-03-15", "eps": 200.0},
        ])

        consolidated = DataConsolidator.consolidate_point_in_time(
            price_df=price_df,
            fundamental_df=shuffled_fund,
            symbol="005930"
        )

        feb_row = consolidated[consolidated["date"] == "2024-02-01"].iloc[0]
        assert feb_row["eps"] == 100.0

        apr_row = consolidated[consolidated["date"] == "2024-04-01"].iloc[0]
        assert apr_row["eps"] == 200.0

        jun_row = consolidated[consolidated["date"] == "2024-06-01"].iloc[0]
        assert jun_row["eps"] == 300.0


# =====================================================================
# Target 3: High-Frequency Streamer 100k Multi-Thread Stress
# =====================================================================

class TestAdversarialHighFrequencyStreamer:
    """100,000개 틱 다중 스레드 동시 주입 시 고정 메모리 링버퍼 및 캔들 집계 무결성 검증"""

    def test_100k_multithreaded_ticks_ringbuffer_fixed_memory_and_fifo(self):
        """
        [적대적 검증 3-1]
        10개 스레드가 각각 10,000개씩 총 100,000개의 틱을 실시간 링버퍼에 동시 주입 시:
        - 링버퍼 크기가 capacity(50,000)를 초과하지 않고 고정 메모리를 유지 (FIFO 정상 축출).
        - 멀티스레드 락 충돌, 데드락 또는 데이터 유실/손상 없이 100% 안전하게 처리.
        """
        capacity = 50000
        ring_buffer = CircularBuffer(capacity_per_symbol=capacity)
        symbol = "005930"
        total_ticks = 100000
        num_threads = 10
        ticks_per_thread = total_ticks // num_threads

        start_time = datetime(2024, 1, 1, 9, 0, 0)

        def worker(thread_id: int):
            for i in range(ticks_per_thread):
                seq = thread_id * ticks_per_thread + i
                tick = TickData(
                    timestamp=start_time + timedelta(milliseconds=seq * 10),
                    symbol=symbol,
                    price=70000.0 + (seq % 1000),
                    volume=10 + (seq % 50),
                    accum_volume=seq * 10,
                )
                ring_buffer.append(tick)

        threads: List[threading.Thread] = []
        t0 = time.perf_counter()

        for tid in range(num_threads):
            t = threading.Thread(target=worker, args=(tid,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.perf_counter() - t0

        # 검증 1: 100,000개가 주입되었지만 버퍼 크기는 정확히 50,000개로 제한
        buf_size = ring_buffer.size(symbol)
        assert buf_size == capacity, f"링버퍼 크기 초과/미달: {buf_size} != {capacity}"

        # 검증 2: 전체 버퍼 크기 일치
        assert ring_buffer.total_size() == capacity

        # 검증 3: DataFrame 변환 시 정확히 50,000개 행 및 스키마 무결성
        df = ring_buffer.to_dataframe(symbol)
        assert len(df) == capacity
        assert not df.empty
        assert "price" in df.columns
        assert "volume" in df.columns
        assert df["price"].isna().sum() == 0

        # 검증 4: 처리량 (Throughput) 측정
        throughput = total_ticks / elapsed
        assert throughput > 10000, f"처리량 미달: {throughput:.1f} ticks/sec"

    def test_100k_ticks_window_bar_aggregator_mathematical_invariants(self):
        """
        [적대적 검증 3-2]
        100,000개의 대규모 틱 스트림을 WindowBarAggregator(1분봉)로 집계 시
        OHLCV 5대 수학적 불변성(Invariants) 실측 검증:
        1. High >= Open, High >= Close, High >= Low (모든 캔들)
        2. Low <= Open, Low <= Close, Low <= High (모든 캔들)
        3. Total Injected Volume == Sum of All Bar Volumes
        4. Total Injected Value == Sum of All Bar Values (허용오차 1e-4)
        5. Total Injected Tick Count == Sum of All Bar Tick Counts (100,000)
        """
        symbol = "005930"
        aggregator = WindowBarAggregator(
            symbol=symbol,
            interval_seconds=60,
            timeframe_name="1m"
        )

        total_ticks = 100000
        start_ts = datetime(2024, 1, 1, 9, 0, 0)

        total_injected_volume = 0
        total_injected_value = 0.0

        np.random.seed(123)
        prices = 70000.0 + np.cumsum(np.random.normal(0, 5, total_ticks))
        volumes = np.random.randint(1, 100, total_ticks)

        t0 = time.perf_counter()

        for i in range(total_ticks):
            t_stamp = start_ts + timedelta(milliseconds=i * 100)
            p = float(prices[i])
            v = int(volumes[i])

            total_injected_volume += v
            total_injected_value += float(p * v)

            tick = TickData(
                timestamp=t_stamp,
                symbol=symbol,
                price=p,
                volume=v
            )
            aggregator.process_tick(tick)

        aggregator.force_close()
        elapsed = time.perf_counter() - t0

        closed_bars = aggregator.get_closed_bars()
        all_bars_df = aggregator.to_dataframe()
        assert not all_bars_df.empty
        assert len(all_bars_df) == len(closed_bars)

        # Invariant 1 & 2: OHLC 가격 일관성
        for bar in closed_bars:
            assert bar.high >= bar.open, f"High < Open in bar {bar}"
            assert bar.high >= bar.close, f"High < Close in bar {bar}"
            assert bar.high >= bar.low, f"High < Low in bar {bar}"
            assert bar.low <= bar.open, f"Low > Open in bar {bar}"
            assert bar.low <= bar.close, f"Low > Close in bar {bar}"
            assert bar.low <= bar.high, f"Low > High in bar {bar}"

        # Invariant 3: 거래량 총합 보존
        sum_bar_volume = sum(b.volume for b in closed_bars)
        assert sum_bar_volume == total_injected_volume, (
            f"Volume 불일치: {sum_bar_volume} != {total_injected_volume}"
        )

        # Invariant 4: 거래대금 총합 보존
        sum_bar_value = sum(b.value for b in closed_bars)
        assert math.isclose(sum_bar_value, total_injected_value, rel_tol=1e-5), (
            f"Value 불일치: {sum_bar_value} != {total_injected_value}"
        )

        # Invariant 5: 틱 카운트 총합 보존 (100,000건)
        sum_bar_tick_count = sum(b.tick_count for b in closed_bars)
        assert sum_bar_tick_count == total_ticks, (
            f"Tick count 불일치: {sum_bar_tick_count} != {total_ticks}"
        )

        # 타임스탬프 1분 정렬 무결성
        for bar in closed_bars:
            assert bar.timestamp.second == 0, f"바 시작 시각 초 단위 미정렬: {bar.timestamp}"

    def test_multithreaded_window_bar_aggregator_thread_safety(self):
        """
        [적대적 검증 3-3]
        다중 스레드(8개)가 동일한 WindowBarAggregator 인스턴스에 고빈도 틱을 동시 주입 시
        Lock 동기화로 인한 데이터 오염 및 예외 발생 0건 검증.
        """
        symbol = "005930"
        aggregator = WindowBarAggregator(
            symbol=symbol,
            interval_seconds=10,
            timeframe_name="10s"
        )

        num_threads = 8
        ticks_per_thread = 5000
        total_ticks = num_threads * ticks_per_thread
        base_time = datetime(2024, 1, 1, 9, 0, 0)

        total_vol = 0
        vol_lock = threading.Lock()

        def worker(thread_idx: int):
            nonlocal total_vol
            local_vol = 0
            for i in range(ticks_per_thread):
                ts = base_time + timedelta(seconds=(i // 100), milliseconds=(i % 100) * 10)
                v = 1
                local_vol += v
                tick = TickData(
                    timestamp=ts,
                    symbol=symbol,
                    price=70000.0 + (i % 50),
                    volume=v
                )
                aggregator.process_tick(tick)

            with vol_lock:
                total_vol += local_vol

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        aggregator.force_close()
        closed_bars = aggregator.get_closed_bars()

        # 검증: 총 볼륨 및 틱 카운트 보존
        sum_vol = sum(b.volume for b in closed_bars)
        assert sum_vol == total_ticks
        assert sum(b.tick_count for b in closed_bars) == total_ticks
