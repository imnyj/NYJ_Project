"""
modules/data/pipeline.py
========================
Phase 1 통합 데이터 수집, 교차 검증, PIT 병합 및 Parquet 저장 파이프라인 Facade.

주요 클래스:
1. DataCollectionPipeline:
   - 펀더멘털 데이터 수집 및 교차 검증 (FundamentalDataCollector)
   - 시계열 주가 수집 및 Fallback (PriceDataCollector)
   - Point-in-Time 결합 및 동적 밸류에이션 피처 생성 (DataConsolidator)
   - PyArrow 기반 ZSTD 압축 Parquet 저장
   - 단일 종목(run / run_pipeline) 및 멀티 종목 일괄(run_batch) 파이프라인 제공
2. DataPipeline: DataCollectionPipeline 별칭 (하위 호환성 보장)
"""

import logging
import os
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from modules.data.collector_fundamental import (
    FundamentalDataCollector,
    PeriodType,
    ValidationReport,
    ValidationStatus,
)
from modules.data.collector_price import PriceDataCollector
from modules.data.consolidator import DataConsolidator

logger = logging.getLogger(__name__)


class DataCollectionPipeline:
    """
    Phase 1 전체 수집-검증-병합-저장 파이프라인을 단일 진입점으로 오케스트레이션하는 Facade 클래스.
    """

    def __init__(
        self,
        fundamental_collector: Optional[FundamentalDataCollector] = None,
        price_collector: Optional[PriceDataCollector] = None,
        consolidator: Optional[DataConsolidator] = None,
    ):
        self.fundamental_collector = fundamental_collector or FundamentalDataCollector()
        self.price_collector = price_collector or PriceDataCollector()
        self.consolidator = consolidator or DataConsolidator()

    def close(self) -> None:
        """파이프라인 내 모든 수집기 리소스 정리"""
        if hasattr(self.fundamental_collector, "close") and callable(self.fundamental_collector.close):
            self.fundamental_collector.close()
        if hasattr(self.price_collector, "close") and callable(self.price_collector.close):
            self.price_collector.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def run(
        self,
        symbol: str = "005930",
        days: int = 500,
        count: Optional[int] = None,
        save: bool = True,
        save_raw: Optional[bool] = None,
        output_dir: Optional[Union[str, pathlib.Path]] = None,
        output_filepath: Optional[Union[str, pathlib.Path]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period_type: PeriodType = PeriodType.ANNUAL,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        단일 종목에 대해 펀더멘털 및 가격 데이터를 수집하고, PIT 병합 및 Parquet 저장을 수행.

        Args:
            symbol: 6자리 종목코드 (기본: '005930')
            days: 수집할 주가 거래일 수 (기본: 500)
            count: days의 별칭 파라미터
            save: Parquet 저장 여부 (기본: True)
            save_raw: save의 별칭 파라미터
            output_dir: Parquet 파일 저장 디렉토리 (None일 경우 data/raw/)
            output_filepath: Parquet 파일 전체 경로 (지정 시 output_dir보다 우선)
            start_date: 주가 수집 시작일자 (YYYY-MM-DD)
            end_date: 주가 수집 종료일자 (YYYY-MM-DD)
            period_type: 펀더멘털 재무제표 주기 (ANNUAL 또는 QUARTER)

        Returns:
            Tuple[pd.DataFrame, Dict[str, Any]]: (통합 DataFrame, 실행 메타데이터 딕셔너리)
        """
        clean_sym = str(symbol).strip().zfill(6) if str(symbol).isdigit() else str(symbol).strip()
        eff_count = count if count is not None else days
        eff_save = save_raw if save_raw is not None else save

        logger.info(f"Starting DataCollectionPipeline for symbol={clean_sym}, days={eff_count}, period={period_type}")

        # 1. 펀더멘털 데이터 수집 및 교차 검증
        try:
            fund_df = self.fundamental_collector.get_as_dataframe(
                ticker=clean_sym,
                period_type=period_type
            )
            _, val_report = self.fundamental_collector.get_financial_statements(
                ticker=clean_sym,
                period_type=period_type
            )
        except Exception as fe:
            logger.warning(f"Fundamental collection failed for {clean_sym}: {fe}")
            fund_df = pd.DataFrame()
            val_report = None

        # 2. 가격 시계열 데이터 수집
        try:
            price_df = self.price_collector.get_daily_price(
                symbol=clean_sym,
                count=eff_count,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as pe:
            logger.error(f"Price collection failed for {clean_sym}: {pe}")
            price_df = pd.DataFrame()

        # 3. Point-in-Time 통합 병합
        consolidated_df = self.consolidator.consolidate_point_in_time(
            price_df=price_df,
            fundamental_df=fund_df,
            symbol=clean_sym
        )

        # 4. Parquet 저장
        saved_path: Optional[str] = None
        if eff_save and not consolidated_df.empty:
            target_path = output_filepath
            if target_path is None and output_dir is not None:
                target_path = pathlib.Path(output_dir) / f"{clean_sym}_consolidated.parquet"

            actual_saved = self.consolidator.save_to_parquet(
                df=consolidated_df,
                filepath=target_path,
                symbol=clean_sym
            )
            saved_path = str(actual_saved)

        # 5. 메타데이터 구성
        val_status_str = "SINGLE_SOURCE"
        max_diff = 0.0
        if val_report:
            val_status_str = (
                val_report.status.value
                if hasattr(val_report.status, "value")
                else str(val_report.status)
            )
            max_diff = val_report.max_discrepancy_pct

        metadata: Dict[str, Any] = {
            "symbol": clean_sym,
            "row_count": len(consolidated_df),
            "saved_path": saved_path,
            "validation_status": val_status_str,
            "max_discrepancy_pct": max_diff,
            "executed_at": datetime.now().isoformat(),
        }

        logger.info(
            f"Pipeline completed for {clean_sym}: {len(consolidated_df)} rows, "
            f"status={val_status_str}, saved_to={saved_path}"
        )
        return consolidated_df, metadata

    def run_pipeline(
        self,
        symbol: str = "005930",
        count: int = 500,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period_type: PeriodType = PeriodType.ANNUAL,
        save_raw: bool = True,
        output_filepath: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """run 메서드의 하위 호환성 별칭"""
        return self.run(
            symbol=symbol,
            days=count,
            count=count,
            save=save_raw,
            save_raw=save_raw,
            output_filepath=output_filepath,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
        )

    def run_batch(
        self,
        symbols: Optional[List[str]] = None,
        days: int = 500,
        count: Optional[int] = None,
        save: bool = True,
        output_dir: Optional[Union[str, pathlib.Path]] = None,
        period_type: PeriodType = PeriodType.ANNUAL,
    ) -> Dict[str, Tuple[pd.DataFrame, Dict[str, Any]]]:
        """
        다중 종목에 대한 일괄 데이터 수집, 교차 검증, PIT 병합 및 저장 파이프라인.

        Args:
            symbols: 종목코드 리스트 (기본: ['005930', '000660', '005380'])
            days: 수집할 거래일 수
            count: days의 별칭
            save: 저장 여부
            output_dir: 출력 디렉토리
            period_type: 펀더멘털 주기

        Returns:
            Dict[str, Tuple[pd.DataFrame, Dict[str, Any]]]: 종목코드별 결과 매핑
        """
        target_symbols = symbols or ["005930", "000660", "005380"]
        results: Dict[str, Tuple[pd.DataFrame, Dict[str, Any]]] = {}

        for sym in target_symbols:
            try:
                res_df, meta = self.run(
                    symbol=sym,
                    days=days,
                    count=count,
                    save=save,
                    output_dir=output_dir,
                    period_type=period_type,
                )
                results[sym] = (res_df, meta)
            except Exception as e:
                logger.error(f"Error in batch pipeline for symbol {sym}: {e}")
                results[sym] = (
                    pd.DataFrame(),
                    {
                        "symbol": sym,
                        "row_count": 0,
                        "saved_path": None,
                        "validation_status": "ERROR",
                        "max_discrepancy_pct": 0.0,
                        "error": str(e),
                        "executed_at": datetime.now().isoformat(),
                    },
                )

        return results


# 하위 호환성 별칭
DataPipeline = DataCollectionPipeline
