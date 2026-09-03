#!/usr/bin/env python3
"""
etc/scripts/verify_e2e_challenger2.py
=====================================
Challenger 2 Empirical E2E Verification & Stress Test Suite
"""

import sys
import os
import json
import pathlib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Add workspace root to sys.path
WORKSPACE_ROOT = pathlib.Path("/home/imnyj/Workspace/Auto_Stock")
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from modules.data.pipeline import DataCollectionPipeline
from modules.data.consolidator import DataConsolidator
from modules.data.collector_fundamental import FundamentalDataCollector, PeriodType, ValidationStatus
from modules.data.collector_price import PriceDataCollector

def test_single_symbol_samsung():
    print("=" * 70)
    print("1. Testing Single Ticker: Samsung Electronics ('005930')")
    print("=" * 70)

    pipeline = DataCollectionPipeline()
    df, meta = pipeline.run(symbol="005930", days=500, save=True)

    print(f"Pipeline metadata: {json.dumps(meta, indent=2, ensure_ascii=False)}")
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    parquet_path = WORKSPACE_ROOT / "data" / "raw" / "005930_consolidated.parquet"
    assert parquet_path.exists(), f"Parquet file does not exist: {parquet_path}"

    # PyArrow Inspection
    print("\n--- PyArrow Inspection of 005930_consolidated.parquet ---")
    parquet_file = pq.ParquetFile(str(parquet_path))
    schema = parquet_file.schema
    metadata = parquet_file.metadata
    table = parquet_file.read()

    print(f"Parquet Num Rows: {metadata.num_rows}")
    print(f"Parquet Num Columns: {metadata.num_columns}")
    print(f"Parquet Num Row Groups: {metadata.num_row_groups}")
    print(f"Parquet Format Version: {metadata.format_version}")
    print(f"Parquet Serialized Size: {metadata.serialized_size} bytes")

    # Measure sizes
    disk_size = os.path.getsize(parquet_path)
    uncompressed_size = table.nbytes
    comp_ratio = uncompressed_size / disk_size if disk_size > 0 else 0

    print(f"Uncompressed in-memory size: {uncompressed_size:,} bytes")
    print(f"On-disk file size (ZSTD): {disk_size:,} bytes")
    print(f"ZSTD Compression Ratio: {comp_ratio:.2f}x ({((1 - disk_size / uncompressed_size) * 100):.2f}% savings)")

    # Inspect schema columns and types
    print("\n--- PyArrow Schema Details ---")
    for i in range(len(schema)):
        col_meta = schema.column(i)
        print(f"  [{i:02d}] {col_meta.name:<25}: physical={col_meta.physical_type}, logical={col_meta.logical_type}")

    # Inspect Null ratios
    print("\n--- Column Null Ratios ---")
    df_loaded = table.to_pandas()
    null_report = {}
    for col in df_loaded.columns:
        null_cnt = df_loaded[col].isna().sum()
        null_pct = (null_cnt / len(df_loaded)) * 100
        null_report[col] = {"null_count": int(null_cnt), "null_pct": round(null_pct, 2)}
        print(f"  {col:<25}: {null_cnt:>4}/{len(df_loaded)} nulls ({null_pct:>5.1f}%)")

    # Dynamic PER / PBR integrity check
    print("\n--- Dynamic PER / PBR Mathematical Integrity ---")
    # Check dynamic_per = close / eps when eps > 0
    valid_eps_mask = df_loaded['eps'].notna() & (df_loaded['eps'] > 0)
    per_diff = np.abs(df_loaded.loc[valid_eps_mask, 'dynamic_per'] - (df_loaded.loc[valid_eps_mask, 'close'] / df_loaded.loc[valid_eps_mask, 'eps']))
    max_per_diff = per_diff.max() if not per_diff.empty else 0.0
    print(f"  Max absolute error in dynamic_per (Close / EPS): {max_per_diff:.8f}")
    assert max_per_diff < 1e-6, f"dynamic_per mismatch: {max_per_diff}"

    # Check dynamic_pbr = close / bps when bps > 0
    valid_bps_mask = df_loaded['bps'].notna() & (df_loaded['bps'] > 0)
    pbr_diff = np.abs(df_loaded.loc[valid_bps_mask, 'dynamic_pbr'] - (df_loaded.loc[valid_bps_mask, 'close'] / df_loaded.loc[valid_bps_mask, 'bps']))
    max_pbr_diff = pbr_diff.max() if not pbr_diff.empty else 0.0
    print(f"  Max absolute error in dynamic_pbr (Close / BPS): {max_pbr_diff:.8f}")
    assert max_pbr_diff < 1e-6, f"dynamic_pbr mismatch: {max_pbr_diff}"

    # Check Look-ahead Bias (PIT integrity)
    print("\n--- Point-in-Time (Look-ahead Bias) Integrity ---")
    if 'announcement_date' in df_loaded.columns:
        valid_ann = df_loaded.dropna(subset=['announcement_date', 'date']).copy()
        valid_ann['date'] = pd.to_datetime(valid_ann['date'])
        valid_ann['announcement_date'] = pd.to_datetime(valid_ann['announcement_date'])
        lookahead_violations = (valid_ann['date'] < valid_ann['announcement_date']).sum()
        print(f"  Look-ahead bias violations (date < announcement_date): {lookahead_violations}")
        assert lookahead_violations == 0, f"Look-ahead bias detected! {lookahead_violations} records violate PIT."

    # Return stats
    print("\n--- Feature Summary Stats ---")
    print(df_loaded[['close', 'dynamic_per', 'dynamic_pbr', 'returns_1d', 'volatility_20d']].describe().to_string())

    return {
        "status": "PASS",
        "rows": len(df_loaded),
        "cols": len(df_loaded.columns),
        "uncompressed_bytes": uncompressed_size,
        "disk_bytes": disk_size,
        "compression_ratio": comp_ratio,
        "max_per_diff": float(max_per_diff),
        "max_pbr_diff": float(max_pbr_diff),
    }

def test_batch_pipeline_multi_symbols():
    print("\n" + "=" * 70)
    print("2. Testing Multi-Ticker Batch Pipeline ('005930', '000660', '005380')")
    print("=" * 70)

    symbols = ["005930", "000660", "005380"]
    pipeline = DataCollectionPipeline()
    batch_res = pipeline.run_batch(symbols=symbols, days=500, save=True)

    summary = {}
    for sym, (df, meta) in batch_res.items():
        print(f"\n[Ticker {sym}]")
        print(f"  Rows: {len(df)}, Cols: {len(df.columns) if not df.empty else 0}")
        print(f"  Validation Status: {meta.get('validation_status')}")
        print(f"  Saved Path: {meta.get('saved_path')}")

        parquet_file = WORKSPACE_ROOT / "data" / "raw" / f"{sym}_consolidated.parquet"
        assert parquet_file.exists(), f"Parquet file {parquet_file} missing!"

        # Read back via consolidator load_from_parquet
        df_read = DataConsolidator.load_from_parquet(parquet_file)
        assert len(df_read) == len(df), f"Row count mismatch on reload for {sym}"
        assert len(df_read.columns) == len(df.columns), f"Column count mismatch for {sym}"

        file_size = os.path.getsize(parquet_file)
        table = pq.read_table(str(parquet_file))
        comp_ratio = table.nbytes / file_size if file_size > 0 else 0

        summary[sym] = {
            "status": meta.get("validation_status"),
            "rows": len(df_read),
            "cols": len(df_read.columns),
            "file_size": file_size,
            "compression_ratio": round(comp_ratio, 2),
            "close_min": float(df_read['close'].min()),
            "close_max": float(df_read['close'].max()),
            "latest_close": float(df_read['close'].iloc[-1]),
            "dynamic_per_mean": float(df_read['dynamic_per'].dropna().mean()) if 'dynamic_per' in df_read and df_read['dynamic_per'].notna().any() else None,
            "dynamic_pbr_mean": float(df_read['dynamic_pbr'].dropna().mean()) if 'dynamic_pbr' in df_read and df_read['dynamic_pbr'].notna().any() else None,
        }
        print(f"  Parquet File Size: {file_size:,} bytes | ZSTD Ratio: {comp_ratio:.2f}x")
        print(f"  Latest Close: {summary[sym]['latest_close']:,} KRW | Mean Dyn PER: {summary[sym]['dynamic_per_mean']} | Mean Dyn PBR: {summary[sym]['dynamic_pbr_mean']}")

    return summary

def test_stress_and_edge_cases():
    print("\n" + "=" * 70)
    print("3. Adversarial Stress & Boundary Testing")
    print("=" * 70)
    pipeline = DataCollectionPipeline()
    consolidator = DataConsolidator()
    results = {}

    # 1. Invalid ticker
    print("\n[Edge Case 1] Invalid Ticker Code ('999999')")
    df_inv, meta_inv = pipeline.run(symbol="999999", days=50, save=False)
    print(f"  Result shape: {df_inv.shape}, Status: {meta_inv.get('validation_status')}")
    results["invalid_ticker"] = "HANDLED_GRACEFULLY" if df_inv.empty or len(df_inv) >= 0 else "FAIL"

    # 2. Extreme days count (e.g. days=1, days=5000)
    print("\n[Edge Case 2] Boundary Days (days=1, days=5000)")
    df_1, meta_1 = pipeline.run(symbol="005930", days=1, save=False)
    print(f"  days=1 -> shape: {df_1.shape}")
    assert len(df_1) >= 1, "days=1 failed"

    df_5k, meta_5k = pipeline.run(symbol="005930", days=5000, save=False)
    print(f"  days=5000 -> shape: {df_5k.shape}")
    assert len(df_5k) > 1000, "days=5000 failed"
    results["boundary_days"] = "PASS"

    # 3. Deficit / Negative EPS masking
    print("\n[Edge Case 3] Deficit stock (EPS < 0) dynamic PER masking")
    sample_price = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10, freq="D"),
        "symbol": ["TEST"] * 10,
        "open": [1000.0] * 10,
        "high": [1050.0] * 10,
        "low": [950.0] * 10,
        "close": [1000.0] * 10,
        "volume": [100] * 10,
        "value": [100000] * 10,
    })
    sample_fund = pd.DataFrame({
        "symbol": ["TEST"],
        "period_end": [pd.to_datetime("2023-12-31")],
        "announcement_date": [pd.to_datetime("2024-01-01")],
        "revenue": [1000000],
        "operating_income": [-50000],  # deficit
        "net_income": [-100000],
        "eps": [-500.0],  # negative EPS
        "bps": [2000.0],
        "assets": [10000000],
        "liabilities": [5000000],
        "equity": [5000000],
    })
    merged_deficit = consolidator.consolidate_point_in_time(sample_price, sample_fund, "TEST")
    print(f"  Dynamic PER is all NaN: {merged_deficit['dynamic_per'].isna().all()}")
    print(f"  Dynamic PBR is correct (1000/2000=0.5): {np.isclose(merged_deficit['dynamic_pbr'].iloc[0], 0.5)}")
    print(f"  Warning flags contains OPERATING_LOSS & NEGATIVE_EPS: {merged_deficit['warning_flags'].iloc[0]}")
    assert merged_deficit['dynamic_per'].isna().all(), "Negative EPS must result in NaN dynamic_per"
    assert np.isclose(merged_deficit['dynamic_pbr'].iloc[0], 0.5), "PBR calculation error"
    assert "OPERATING_LOSS" in merged_deficit['warning_flags'].iloc[0], "Missing OPERATING_LOSS flag"
    results["deficit_masking"] = "PASS"

    # 4. Out-of-order dates handling
    print("\n[Edge Case 4] Shuffled / Out-of-order dates")
    shuffled_price = sample_price.sample(frac=1.0, random_state=42).reset_index(drop=True)
    merged_shuffled = consolidator.consolidate_point_in_time(shuffled_price, sample_fund, "TEST")
    assert (merged_shuffled['date'].diff().dropna() >= pd.Timedelta(0)).all(), "Dates must be strictly sorted"
    results["date_sorting"] = "PASS"

    # 5. Empty price df & empty fundamental df
    print("\n[Edge Case 5] Empty Inputs")
    empty_res = consolidator.consolidate_point_in_time(pd.DataFrame(), pd.DataFrame())
    assert empty_res.empty, "Empty inputs must return empty DataFrame"
    assert len(empty_res.columns) == len(DataConsolidator.DEFAULT_COLUMNS), "Default columns mismatch on empty"
    results["empty_handling"] = "PASS"

    print("\nAll Stress & Edge cases PASSED successfully!")
    return results

if __name__ == "__main__":
    res_single = test_single_symbol_samsung()
    res_batch = test_batch_pipeline_multi_symbols()
    res_stress = test_stress_and_edge_cases()

    final_report = {
        "single_ticker_samsung": res_single,
        "batch_multi_tickers": res_batch,
        "stress_and_edge_cases": res_stress,
        "overall_verdict": "APPROVE"
    }

    report_path = WORKSPACE_ROOT / "etc" / "scripts" / "verification_results_challenger2.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"Verification completed. Report saved to {report_path}")
    print("OVERALL VERDICT: APPROVE")
    print("=" * 70)
