"""
Unit and Integration Tests for Fundamental Data Collector & Cross-Validation (M1)
Auto Stock ML/RL Trader
"""

import os
import sys
import math
import logging
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

# 프로젝트 루트 임포트 경로 추가
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.data.collector_fundamental import (
    PeriodType,
    ValidationStatus,
    FinancialStatement,
    RealtimeValuation,
    DiscrepancyItem,
    ValidationReport,
    BaseFundamentalSource,
    OpenDartCollector,
    NaverFinanceCollector,
    MockKiwoomCollector,
    FundamentalCrossValidator,
    FundamentalDataCollector,
    clean_numeric_str,
    parse_korean_money,
)


# =====================================================================
# Tier 1: Functional Unit Tests
# =====================================================================

class TestTier1Functional:
    """Tier 1: 정상 수집 기능 및 기본 연산 검증"""

    def test_discrepancy_calculation_exact_match(self):
        """0% 오차: 동일한 수치 비교 시 오차율 0.0 확인"""
        diff = FundamentalCrossValidator.calculate_discrepancy(1000, 1000)
        assert diff == 0.0

        diff_float = FundamentalCrossValidator.calculate_discrepancy(12.34, 12.34)
        assert diff_float == 0.0

    def test_discrepancy_calculation_formula(self):
        """상대 오차율 공식 (|V1 - V2| / max(|V1|, |V2|)) * 100 검증"""
        # 100 vs 95 -> 5.0%
        diff_5 = FundamentalCrossValidator.calculate_discrepancy(100, 95)
        assert abs(diff_5 - 5.0) < 1e-3

        # 100 vs 90 -> 10.0%
        diff_10 = FundamentalCrossValidator.calculate_discrepancy(100, 90)
        assert abs(diff_10 - 10.0) < 1e-3

        # 100 vs 80 -> 20.0%
        diff_20 = FundamentalCrossValidator.calculate_discrepancy(100, 80)
        assert abs(diff_20 - 20.0) < 1e-3

        # 50 vs 100 -> 50.0%
        diff_50 = FundamentalCrossValidator.calculate_discrepancy(50, 100)
        assert abs(diff_50 - 50.0) < 1e-3

    def test_unit_normalization_naver_eok_to_won(self):
        """네이버 억원 단위 -> 원 단위 변환 (* 100,000,000) 검증"""
        collector = NaverFinanceCollector()
        mock_data = {
            "financeInfo": {
                "trTitleList": [
                    {"key": "202412", "title": "2024.12.", "isConsensus": "N"}
                ],
                "rowList": [
                    {"title": "매출액", "columns": {"202412": {"value": "300,870"}}},
                    {"title": "영업이익", "columns": {"202412": {"value": "32,726"}}},
                    {"title": "당기순이익", "columns": {"202412": {"value": "34,451"}}},
                    {"title": "ROE", "columns": {"202412": {"value": "9.4"}}},
                    {"title": "부채비율", "columns": {"202412": {"value": "25.0"}}},
                    {"title": "PER", "columns": {"202412": {"value": "15.2"}}},
                    {"title": "PBR", "columns": {"202412": {"value": "1.6"}}},
                    {"title": "EPS", "columns": {"202412": {"value": "4,800"}}},
                    {"title": "BPS", "columns": {"202412": {"value": "55,000"}}},
                    {"title": "주당배당금", "columns": {"202412": {"value": "1,500"}}},
                ]
            }
        }
        stmts = collector._parse_table_json("005930", mock_data, PeriodType.ANNUAL)
        assert len(stmts) == 1
        s = stmts[0]
        # 300,870억 -> 30,087,000,000,000 원
        assert s.revenue == 30_087_000_000_000
        # 32,726억 -> 3,272,600,000,000 원
        assert s.operating_profit == 3_272_600_000_000
        # 34,451억 -> 3,445_100_000_000 원
        assert s.net_income == 3_445_100_000_000
        assert s.roe == 9.4
        assert s.debt_ratio == 25.0
        assert s.per == 15.2
        assert s.pbr == 1.6
        assert s.eps == 4800.0
        assert s.bps == 55000.0
        assert s.dps == 1500.0
        assert s.total_equity is not None
        assert s.total_assets is not None

    def test_korean_money_parser(self):
        """한국어 금액 문자열 원 단위 파싱 검증"""
        # '1,520조 324억' -> 1,520,032,400,000,000
        assert parse_korean_money("1,520조 324억") == 1_520_032_400_000_000
        # '6조 4,891억' -> 6,489,100,000,000
        assert parse_korean_money("6조 4,891억") == 6_489_100_000_000
        # '5,000억' -> 500,000,000,000
        assert parse_korean_money("5,000억") == 500_000_000_000
        # '50조' -> 50,000,000,000,000
        assert parse_korean_money("50조") == 50_000_000_000_000
        # '100만' -> 1,000,000
        assert parse_korean_money("100만") == 1_000_000
        # 순수 숫자
        assert parse_korean_money("100,000") == 100_000
        assert parse_korean_money("") is None
        assert parse_korean_money(None) is None

    def test_clean_numeric_str(self):
        """문자열 클린업 및 float 변환 함수 검증"""
        assert clean_numeric_str("1,234.56") == 1234.56
        assert clean_numeric_str("12.5%") == 12.5
        assert clean_numeric_str("15.2배") == 15.2
        assert clean_numeric_str("50,000원") == 50000.0
        assert clean_numeric_str("-") is None
        assert clean_numeric_str("N/A") is None
        assert clean_numeric_str("NaN") is None
        assert clean_numeric_str("null") is None
        assert clean_numeric_str(None) is None
        assert clean_numeric_str(100) == 100.0

    def test_financial_statement_properties_and_to_dict(self):
        """FinancialStatement 프로퍼티 및 to_dict 검증"""
        stmt = FinancialStatement(
            ticker="005930",
            year=2023,
            quarter=None,
            period_type=PeriodType.ANNUAL,
            period_end="2023-12-31",
            announcement_date="2024-03-15",
            revenue=258_000_000_000_000,
            operating_profit=6_500_000_000_000,
            net_income=15_000_000_000_000,
            total_assets=450_000_000_000_000,
            total_liabilities=90_000_000_000_000,
            total_equity=360_000_000_000_000,
            dividend_yield=2.5,
            source="DART",
            validation_status=ValidationStatus.PASSED,
        )
        assert stmt.symbol == "005930"
        assert stmt.operating_income == 6_500_000_000_000
        assert stmt.assets == 450_000_000_000_000
        assert stmt.liabilities == 90_000_000_000_000
        assert stmt.equity == 360_000_000_000_000
        assert stmt.div_yield == 2.5

        d = stmt.to_dict()
        assert d["symbol"] == "005930"
        assert d["revenue"] == 258_000_000_000_000
        assert d["operating_income"] == 6_500_000_000_000
        assert d["validation_status"] == "PASSED"

    def test_realtime_valuation_to_dict(self):
        """RealtimeValuation 모델 to_dict 검증"""
        rt = RealtimeValuation(
            ticker="005930",
            current_price=70000,
            market_cap=400_000_000_000_000,
            shares_outstanding=5_969_782_550,
            per=12.5,
            pbr=1.5,
        )
        d = rt.to_dict()
        assert d["ticker"] == "005930"
        assert d["current_price"] == 70000
        assert d["per"] == 12.5

    def test_mock_kiwoom_annual_and_quarter(self):
        """MockKiwoomCollector의 연간 및 분기 수집 검증"""
        mock = MockKiwoomCollector()
        annuals = mock.get_annual_financials("005930", 2021, 2024)
        assert len(annuals) == 4
        assert annuals[0].year == 2021
        assert annuals[-1].year == 2024
        assert annuals[0].revenue > 0
        assert annuals[0].operating_profit > 0
        assert annuals[0].source == "MOCK_KIWOOM"

        quarters = mock.get_quarterly_financials("005930", count=4)
        assert len(quarters) == 4
        assert quarters[0].period_type == PeriodType.QUARTER

    def test_mock_kiwoom_realtime_valuation(self):
        """MockKiwoomCollector 실시간 가치지표 검증"""
        mock = MockKiwoomCollector()
        rt = mock.get_realtime_valuation("005930")
        assert rt is not None
        assert rt.ticker == "005930"
        assert rt.current_price > 0
        assert rt.market_cap > 0
        assert rt.per is not None
        assert rt.pbr is not None

    def test_opendart_collector_account_synonyms(self):
        """DART 계정명 다양성(매출액, 수익(매출액), 영업손익 등) 매핑 검증"""
        dart = OpenDartCollector(api_key="test_key")
        raw_list = [
            {"account_nm": "수익(매출액)", "thstrm_amount": "250000000000", "rcept_no": "20240315000123"},
            {"account_nm": "영업이익(손실)", "thstrm_amount": "30000000000"},
            {"account_nm": "연결당기순이익", "thstrm_amount": "25000000000"},
            {"account_nm": "자산총계", "thstrm_amount": "500000000000"},
            {"account_nm": "자본총계", "thstrm_amount": "300000000000"},
            {"account_nm": "부채총계", "thstrm_amount": "200000000000"},
        ]
        stmt = dart._parse_account_list("005930", 2023, None, PeriodType.ANNUAL, raw_list)
        assert stmt.revenue == 250_000_000_000
        assert stmt.operating_profit == 30_000_000_000
        assert stmt.net_income == 25_000_000_000
        assert stmt.total_assets == 500_000_000_000
        assert stmt.total_equity == 300_000_000_000
        assert stmt.total_liabilities == 200_000_000_000
        assert stmt.announcement_date == "2024-03-15"
        assert stmt.op_margin == 12.0
        assert stmt.net_margin == 10.0
        assert stmt.roe == round((25_000_000_000 / 300_000_000_000) * 100, 2)

    def test_opendart_get_annual_and_quarterly_with_mock(self):
        """OpenDartCollector의 get_annual_financials 및 get_quarterly_financials Mock 테스트"""
        dart = OpenDartCollector(api_key="valid_test_key")
        sample_api_resp = [
            {"account_nm": "매출액", "thstrm_amount": "300000000000000", "rcept_no": "20240315000001", "fs_div": "CFS"},
            {"account_nm": "영업이익", "thstrm_amount": "30000000000000", "rcept_no": "20240315000001", "fs_div": "CFS"},
        ]
        with patch.object(dart, "fetch_single_account", return_value=sample_api_resp):
            annuals = dart.get_annual_financials("005930", 2023, 2024)
            assert len(annuals) == 2
            assert annuals[0].revenue == 300_000_000_000_000

            quarters = dart.get_quarterly_financials("005930", count=4)
            assert len(quarters) <= 4
            assert dart.get_realtime_valuation("005930") is None

    def test_fundamental_data_collector_facade_mock_mode(self):
        """Facade mock_mode 동작 및 반환 객체 무결성 검증"""
        facade = FundamentalDataCollector(mock_mode=True)
        stmts, report = facade.get_financial_statements("005930", PeriodType.ANNUAL, 2021, 2024)
        assert len(stmts) == 4
        assert report is None
        assert stmts[0].source == "MOCK_KIWOOM"

        df = facade.get_as_dataframe("005930", PeriodType.ANNUAL, 2021, 2024)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        assert "revenue" in df.columns
        assert "operating_income" in df.columns

    def test_dataframe_contract_schema(self):
        """Interface Contract 필수 컬럼 목록 18종 스키마 완결성 검증"""
        required_columns = [
            "symbol", "period_end", "announcement_date", "revenue",
            "operating_income", "net_income", "assets", "liabilities",
            "equity", "per", "pbr", "roe", "eps", "bps", "div_yield",
            "is_consensus", "source", "validation_status"
        ]
        facade = FundamentalDataCollector(mock_mode=True)
        df = facade.get_as_dataframe("005930")
        for col in required_columns:
            assert col in df.columns, f"Missing required contract column: {col}"


# =====================================================================
# Tier 2: Boundary, Edge Cases & Error Handling Tests
# =====================================================================

class TestTier2BoundaryAndErrors:
    """Tier 2: 임계값 경계, 결측치, 에러 코드 방어 검증"""

    def test_discrepancy_boundary_thresholds(self):
        """오차 판정 임계치(5%, 10%) 경계값 판정 검증"""
        validator = FundamentalCrossValidator(warning_threshold=5.0, critical_threshold=10.0)

        # 1. 0% -> PASSED
        s1 = FinancialStatement(ticker="005930", year=2024, revenue=1000, source="DART")
        s2 = FinancialStatement(ticker="005930", year=2024, revenue=1000, source="NAVER")
        r0 = validator.validate_statements(s1, s2, ["revenue"])
        assert r0.status == ValidationStatus.PASSED

        # 2. 4.9% -> PASSED
        s_4_9 = FinancialStatement(ticker="005930", year=2024, revenue=951, source="NAVER")
        r_4_9 = validator.validate_statements(s1, s_4_9, ["revenue"])
        assert r_4_9.status == ValidationStatus.PASSED

        # 3. 5.0% -> PASSED (경계값)
        s_5_0 = FinancialStatement(ticker="005930", year=2024, revenue=950, source="NAVER")
        r_5_0 = validator.validate_statements(s1, s_5_0, ["revenue"])
        assert r_5_0.status == ValidationStatus.PASSED

        # 4. 5.1% -> WARNING
        s_5_1 = FinancialStatement(ticker="005930", year=2024, revenue=949, source="NAVER")
        r_5_1 = validator.validate_statements(s1, s_5_1, ["revenue"])
        assert r_5_1.status == ValidationStatus.WARNING

        # 5. 9.9% -> WARNING
        s_9_9 = FinancialStatement(ticker="005930", year=2024, revenue=901, source="NAVER")
        r_9_9 = validator.validate_statements(s1, s_9_9, ["revenue"])
        assert r_9_9.status == ValidationStatus.WARNING

        # 6. 10.0% -> CRITICAL_DISCREPANCY (10% 이상은 CRITICAL)
        s_10_0 = FinancialStatement(ticker="005930", year=2024, revenue=900, source="NAVER")
        r_10_0 = validator.validate_statements(s1, s_10_0, ["revenue"])
        assert r_10_0.status == ValidationStatus.CRITICAL_DISCREPANCY

        # 7. 15.0% -> CRITICAL_DISCREPANCY
        s_15_0 = FinancialStatement(ticker="005930", year=2024, revenue=850, source="NAVER")
        r_15_0 = validator.validate_statements(s1, s_15_0, ["revenue"])
        assert r_15_0.status == ValidationStatus.CRITICAL_DISCREPANCY

    def test_discrepancy_zero_and_none(self):
        """0 및 None 값에 대한 방어 로직 검증"""
        v = FundamentalCrossValidator
        assert v.calculate_discrepancy(0, 0) == 0.0
        assert v.calculate_discrepancy(None, None) == 0.0
        assert v.calculate_discrepancy(None, 100) == 100.0
        assert v.calculate_discrepancy(100, None) == 100.0
        assert v.calculate_discrepancy(0, 100) == 100.0
        assert v.calculate_discrepancy("invalid", 100) == 100.0
        assert v.calculate_discrepancy(float("nan"), float("nan")) == 0.0
        assert v.calculate_discrepancy(float("nan"), 100) == 100.0

    def test_opendart_error_codes_handling(self):
        """OpenDART API 에러 코드(010, 011, 013, 020, 800) 방어 검증"""
        dart = OpenDartCollector(api_key="mock_key")

        with patch.object(dart.session, "get") as mock_get:
            # 010: 미등록 키
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"status": "010", "message": "등록되지 않은 키"}
            res_010 = dart.fetch_single_account("00126380", "2024")
            assert res_010 == []

            # 013: 데이터 없음
            mock_get.return_value.json.return_value = {"status": "013", "message": "조회된 데이터 없음"}
            res_013 = dart.fetch_single_account("00126380", "2024")
            assert res_013 == []

            # 020: 요청제한초과
            mock_get.return_value.json.return_value = {"status": "020", "message": "요청제한 초과"}
            res_020 = dart.fetch_single_account("00126380", "2024")
            assert res_020 == []

            # 800: 시스템점검
            mock_get.return_value.json.return_value = {"status": "800", "message": "시스템 점검 중"}
            res_800 = dart.fetch_single_account("00126380", "2024")
            assert res_800 == []

            # HTTP 500 서버에러
            mock_get.return_value.status_code = 500
            res_500 = dart.fetch_single_account("00126380", "2024")
            assert res_500 == []

    def test_opendart_missing_key_fallback(self):
        """DART API Key 미설정 시 Fallback 정상 동작 검증"""
        # API Key 없이 초기화
        facade = FundamentalDataCollector(dart_api_key=None, mock_mode=False)
        assert not facade.dart_collector.is_configured()

        # DART가 미설정되어도 Naver 또는 Mock으로 Fallback하여 정상 반환
        stmts, _ = facade.get_financial_statements("005930", PeriodType.ANNUAL, 2023, 2024)
        assert len(stmts) > 0
        assert stmts[0].validation_status == ValidationStatus.FALLBACK

    def test_negative_financials_operating_loss(self):
        """영업손실(적자) 기업 데이터의 오차율 및 비율 산출 검증"""
        s1 = FinancialStatement(ticker="000660", year=2023, revenue=32000, operating_profit=-7700, source="DART")
        s2 = FinancialStatement(ticker="000660", year=2023, revenue=32000, operating_profit=-8000, source="NAVER")

        validator = FundamentalCrossValidator()
        report = validator.validate_statements(s1, s2, ["operating_profit"])
        # |-7700 - (-8000)| / 8000 = 300 / 8000 = 3.75% -> PASSED
        assert report.items["operating_profit"].discrepancy_pct == 3.75
        assert report.status == ValidationStatus.PASSED

    def test_coalesce_missing_fields(self):
        """1순위(DART) 결측 필드를 2순위(Naver) 데이터로 정상 병합(Coalesce) 검증"""
        d_stmt = FinancialStatement(
            ticker="005930", year=2024,
            revenue=300000000000000,
            operating_profit=32000000000000,
            per=None,  # DART는 PER 미제공
            pbr=None,  # DART는 PBR 미제공
            source="DART"
        )
        n_stmt = FinancialStatement(
            ticker="005930", year=2024,
            revenue=300000000000000,
            operating_profit=32000000000000,
            per=15.2,
            pbr=1.6,
            source="NAVER"
        )

        merged = FundamentalCrossValidator.coalesce_statements(d_stmt, n_stmt)
        assert merged.revenue == 300000000000000
        assert merged.per == 15.2
        assert merged.pbr == 1.6
        assert merged.source == "DART"

    def test_empty_dataframe_schema_on_invalid_ticker(self):
        """유효하지 않은 종목코드 조회 시에도 스키마를 유지한 빈 DataFrame 반환 검증"""
        facade = FundamentalDataCollector(mock_mode=False)
        with patch.object(facade.naver_collector, "get_annual_financials", return_value=[]), \
             patch.object(facade.mock_collector, "get_annual_financials", return_value=[]):
            df = facade.get_as_dataframe("999999")
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0
            assert "symbol" in df.columns
            assert "revenue" in df.columns


# =====================================================================
# Tier 3: Interaction & Multi-Source Cross-Validation Tests
# =====================================================================

class TestTier3CrossValidationInteraction:
    """Tier 3: 교차 검증 워크플로우 및 소스 간 상호작용 검증"""

    def test_cross_validation_report_warning_flow(self, caplog):
        """8% 인위적 오차 주입 시 ValidationStatus.WARNING 발생 및 Warning 로깅 검증"""
        s_dart = FinancialStatement(ticker="005930", year=2024, revenue=100_000_000_000, source="DART")
        s_naver = FinancialStatement(ticker="005930", year=2024, revenue=92_000_000_000, source="NAVER")

        validator = FundamentalCrossValidator()
        with caplog.at_level(logging.WARNING):
            report = validator.validate_statements(s_dart, s_naver, ["revenue"])

        assert report.status == ValidationStatus.WARNING
        assert len(report.warnings) == 1
        assert "WARNING: revenue discrepancy 8.00%" in report.warnings[0]
        assert report.items["revenue"].discrepancy_pct == 8.0

    def test_cross_validation_report_critical_flow(self, caplog):
        """15% 인위적 오차 주입 시 ValidationStatus.CRITICAL_DISCREPANCY 발생 및 Error 로깅 검증"""
        s_dart = FinancialStatement(ticker="005930", year=2024, revenue=100_000_000_000, source="DART")
        s_naver = FinancialStatement(ticker="005930", year=2024, revenue=85_000_000_000, source="NAVER")

        validator = FundamentalCrossValidator()
        with caplog.at_level(logging.ERROR):
            report = validator.validate_statements(s_dart, s_naver, ["revenue"])

        assert report.status == ValidationStatus.CRITICAL_DISCREPANCY
        assert len(report.errors) == 1
        assert "CRITICAL: revenue discrepancy 15.00%" in report.errors[0]
        assert not report.items["revenue"].is_valid

    def test_cross_validation_multi_metrics_escalation(self):
        """다중 지표 비교 중 1개라도 CRITICAL이면 전체 상태가 CRITICAL로 상향되는지 검증"""
        s_dart = FinancialStatement(
            ticker="005930", year=2024,
            revenue=100_000_000_000,       # 0% diff -> PASSED
            operating_profit=10_000_000_000, # 8% diff -> WARNING
            net_income=8_000_000_000,       # 20% diff -> CRITICAL
            source="DART"
        )
        s_naver = FinancialStatement(
            ticker="005930", year=2024,
            revenue=100_000_000_000,
            operating_profit=9_200_000_000,
            net_income=6_400_000_000,
            source="NAVER"
        )

        validator = FundamentalCrossValidator()
        report = validator.validate_statements(s_dart, s_naver, ["revenue", "operating_profit", "net_income"])
        assert report.items["revenue"].status == ValidationStatus.PASSED
        assert report.items["operating_profit"].status == ValidationStatus.WARNING
        assert report.items["net_income"].status == ValidationStatus.CRITICAL_DISCREPANCY
        assert report.status == ValidationStatus.CRITICAL_DISCREPANCY

    def test_facade_dual_source_cross_validation_and_coalesce(self):
        """Facade에서 DART와 Naver 모두 수집되었을 때 교차검증 및 결측치 보정 동작 검증"""
        facade = FundamentalDataCollector(dart_api_key="valid_key", enable_cross_validation=True)
        dart_s = FinancialStatement(
            ticker="005930", year=2024, revenue=300000000000000, operating_profit=32000000000000, source="DART"
        )
        naver_s = FinancialStatement(
            ticker="005930", year=2024, revenue=300000000000000, operating_profit=32000000000000, per=15.2, pbr=1.6, source="NAVER"
        )

        with patch.object(facade.dart_collector, "is_configured", return_value=True), \
             patch.object(facade.dart_collector, "get_annual_financials", return_value=[dart_s]), \
             patch.object(facade.naver_collector, "get_annual_financials", return_value=[naver_s]):
            stmts, report = facade.get_financial_statements("005930", PeriodType.ANNUAL, 2024, 2024)
            assert len(stmts) == 1
            assert stmts[0].source == "DART"
            assert stmts[0].per == 15.2  # Naver로부터 coalesce됨
            assert report is not None
            assert report.status == ValidationStatus.PASSED

    def test_fallback_priority_chain(self):
        """DART 실패 -> Naver Fallback -> Mock Fallback 순차 전환 검증"""
        facade = FundamentalDataCollector(mock_mode=False)

        # 1. DART 실패 & Naver 성공
        with patch.object(facade.dart_collector, "is_configured", return_value=False), \
             patch.object(facade.naver_collector, "get_annual_financials", return_value=[
                 FinancialStatement(ticker="005930", year=2024, revenue=300000, source="NAVER")
             ]):
            stmts, report = facade.get_financial_statements("005930")
            assert len(stmts) == 1
            assert stmts[0].source == "NAVER"
            assert stmts[0].validation_status == ValidationStatus.FALLBACK

        # 2. DART 실패 & Naver 실패 -> Mock Fallback
        with patch.object(facade.dart_collector, "is_configured", return_value=False), \
             patch.object(facade.naver_collector, "get_annual_financials", return_value=[]):
            stmts, report = facade.get_financial_statements("005930")
            assert len(stmts) > 0
            assert stmts[0].source == "MOCK_KIWOOM"
            assert stmts[0].validation_status == ValidationStatus.FALLBACK


# =====================================================================
# Tier 4: Real-World Scenario Tests
# =====================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: 삼성전자('005930') 및 주요 종목 실제/고충실도 시나리오 검증"""

    def test_samsung_electronics_live_naver_annual(self):
        """삼성전자(005930) 네이버 실시간 연간 재무제표 수집 및 값 유효성 검증"""
        collector = NaverFinanceCollector()
        stmts = collector.get_annual_financials("005930", start_year=2023, end_year=2025)
        if not stmts:
            pytest.skip("네트워크 환경 이슈로 라이브 네이버 API 호출 스킵")

        assert len(stmts) >= 1
        s = stmts[0]
        assert s.ticker == "005930"
        assert s.revenue is not None and s.revenue > 100_000_000_000_000  # 최소 100조 원 이상
        assert s.source == "NAVER"
        assert s.period_end is not None

    def test_samsung_electronics_live_naver_quarterly(self):
        """삼성전자(005930) 네이버 실시간 분기 재무제표 수집 검증"""
        collector = NaverFinanceCollector()
        stmts = collector.get_quarterly_financials("005930", count=4)
        if not stmts:
            pytest.skip("네트워크 환경 이슈로 라이브 네이버 API 호출 스킵")

        assert len(stmts) >= 1
        s = stmts[0]
        assert s.ticker == "005930"
        assert s.period_type == PeriodType.QUARTER
        assert s.quarter in (1, 2, 3, 4)

    def test_samsung_electronics_live_naver_realtime_valuation(self):
        """삼성전자(005930) 네이버 실시간 시가총액 및 PER/PBR 수집 검증"""
        collector = NaverFinanceCollector()
        rt = collector.get_realtime_valuation("005930")
        if not rt or rt.current_price == 0:
            pytest.skip("네트워크 환경 이슈로 라이브 네이버 API 호출 스킵")

        assert rt.ticker == "005930"
        assert rt.current_price > 10_000
        assert rt.market_cap > 100_000_000_000_000  # 시총 100조 원 이상
        assert rt.shares_outstanding > 1_000_000_000

    def test_samsung_electronics_e2e_dataframe_generation(self):
        """삼성전자(005930) Facade를 통한 E2E DataFrame 생성 및 데이터 무결성 검증"""
        facade = FundamentalDataCollector(mock_mode=False)
        df = facade.get_as_dataframe("005930", PeriodType.ANNUAL, 2022, 2024)
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1
        assert "revenue" in df.columns
        assert "operating_income" in df.columns
        assert "validation_status" in df.columns
        # Datetime 타입 및 정렬 확인
        assert pd.api.types.is_datetime64_any_dtype(df["period_end"])
        assert df["period_end"].is_monotonic_increasing

    def test_sk_hynix_turnaround_scenario(self):
        """SK하이닉스(000660) 흑자전환 시나리오 검증"""
        mock = MockKiwoomCollector()
        stmts = mock.get_annual_financials("000660", 2023, 2024)
        assert len(stmts) == 2
        # 2023 적자
        assert stmts[0].operating_profit < 0
        # 2024 흑자
        assert stmts[1].operating_profit > 0
