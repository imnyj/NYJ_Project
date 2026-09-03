"""
tests/test_adversarial_challenger2_hpo.py
=========================================
Auto Stock ML/RL Trader — Milestone 3: Empirical Adversarial Challenger 2 Test Suite.

검증 항목:
1. scripts/run_hpo.py CLI E2E 실행 검증 (--n-trials 3 및 --n-trials 5)
2. 출력 CSV의 행 수(>=3, >=5) 및 20개 컬럼 스키마 일치성 자동화 assert
3. 시드 재현성(Seed Reproducibility: seed 42 vs seed 42) 및 다양성(Seed Diversity: seed 42 vs seed 100) 검증
4. 디렉토리 자동 생성 및 원자적 CSV 저장 검증
5. 지표 유효성 및 경계치 방어(Zero-variance Sharpe, Total Equity, Return %, MDD %)
6. 예외 복원력(Exception Resilience) 및 Pruning 처리 검증
"""

import math
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

import numpy as np
import optuna
import pandas as pd
import pytest

from modules.hpo import (
    CSV_COLUMNS,
    calculate_annualized_sharpe_ratio,
    calculate_max_drawdown_pct,
    calculate_total_equity,
    calculate_total_return_pct,
    calculate_win_rate,
    create_hpo_study,
    evaluate_trading_history,
    export_trial_to_csv,
    load_hpo_results,
    objective,
    run_hpo_optimization,
)


class TestHPOAdversarialCLIAndSchema:
    """1 & 2. CLI E2E 실행 및 20개 컬럼 스키마 검증 스위트"""

    def test_cli_run_n_trials_3_and_schema_assert(self):
        """CLI --n-trials 3 실행 및 20개 컬럼 스키마 및 행 수 >= 3 자동화 단언"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "baseline_hpo_3.csv")
            cli_path = os.path.abspath("scripts/run_hpo.py")

            cmd = [
                sys.executable,
                cli_path,
                "--n-trials",
                "3",
                "--symbol",
                "005930",
                "--output",
                csv_path,
                "--seed",
                "42",
                "--timesteps",
                "50",
                "--fast-mode",
                "--quiet",
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            assert proc.returncode == 0, f"CLI Failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            assert os.path.exists(csv_path), "CSV file was not created by CLI!"

            df = load_hpo_results(csv_path)
            # 1. 행 수 검증
            assert len(df) >= 3, f"Expected >= 3 rows, got {len(df)}"

            # 2. 20개 컬럼 스키마 엄격 일치성 검증
            assert len(df.columns) == 20, f"Expected 20 columns, got {len(df.columns)}"
            assert list(df.columns) == CSV_COLUMNS

            # 3. 주요 컬럼 타입 및 유효 범위 단언
            assert (df["trial_id"] == [0, 1, 2]).all()
            assert set(df["state"].unique()).issubset({"COMPLETE", "PRUNED", "FAIL"})
            assert (df["total_equity"] > 0).all()
            assert not df["objective_value"].isna().any()
            assert not df["duration_seconds"].isna().any()

    def test_cli_run_n_trials_5_and_schema_assert(self):
        """CLI --n-trials 5 실행 및 20개 컬럼 스키마 및 행 수 >= 5 자동화 단언"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "baseline_hpo_5.csv")
            cli_path = os.path.abspath("scripts/run_hpo.py")

            cmd = [
                sys.executable,
                cli_path,
                "--n-trials",
                "5",
                "--symbol",
                "005930",
                "--output",
                csv_path,
                "--seed",
                "42",
                "--timesteps",
                "50",
                "--fast-mode",
                "--quiet",
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            assert proc.returncode == 0, f"CLI Failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            assert os.path.exists(csv_path), "CSV file was not created by CLI!"

            df = load_hpo_results(csv_path)
            assert len(df) >= 5, f"Expected >= 5 rows, got {len(df)}"
            assert len(df.columns) == 20
            assert list(df.columns) == CSV_COLUMNS
            assert (df["trial_id"] == [0, 1, 2, 3, 4]).all()


class TestHPOSettingsAndReproducibility:
    """3. 시드 재현성 및 파라미터 다양성 검증 스위트"""

    def test_seed_reproducibility_seed_42_vs_42(self):
        """동일 시드(--seed 42) 실행 시 동일한 하이퍼파라미터 탐색 시퀀스 재현 입증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv1 = os.path.join(tmp_dir, "run1.csv")
            csv2 = os.path.join(tmp_dir, "run2.csv")

            study1, best1 = run_hpo_optimization(
                n_trials=3,
                symbol="005930",
                output_csv=csv1,
                seed=42,
                n_timesteps=40,
                fast_mode=True,
                verbose=False,
            )

            study2, best2 = run_hpo_optimization(
                n_trials=3,
                symbol="005930",
                output_csv=csv2,
                seed=42,
                n_timesteps=40,
                fast_mode=True,
                verbose=False,
            )

            # 파라미터 제안 시퀀스 완벽 일치 확인
            for t1, t2 in zip(study1.trials, study2.trials):
                assert t1.params == t2.params, f"Trial {t1.number} params mismatch under identical seed 42!"

            # 최적 파라미터 일치 확인
            assert best1.params == best2.params

    def test_seed_diversity_seed_42_vs_100(self):
        """서로 다른 시드(--seed 42 vs --seed 100) 실행 시 파라미터 탐색 다양성 입증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_42 = os.path.join(tmp_dir, "run_42.csv")
            csv_100 = os.path.join(tmp_dir, "run_100.csv")

            study_42, _ = run_hpo_optimization(
                n_trials=3,
                symbol="005930",
                output_csv=csv_42,
                seed=42,
                n_timesteps=40,
                fast_mode=True,
                verbose=False,
            )

            study_100, _ = run_hpo_optimization(
                n_trials=3,
                symbol="005930",
                output_csv=csv_100,
                seed=100,
                n_timesteps=40,
                fast_mode=True,
                verbose=False,
            )

            # Trial 0의 파라미터들이 상이함을 확인 (다양성)
            t42_0_params = study_42.trials[0].params
            t100_0_params = study_100.trials[0].params
            assert t42_0_params != t100_0_params, "Different seeds should produce different sampling!"
            assert t42_0_params["sl_lr"] != t100_0_params["sl_lr"]
            assert t42_0_params["rl_lr"] != t100_0_params["rl_lr"]


class TestHPOAdversarialStressAndEdgeCases:
    """4 & 5 & 6. 적대적 스트레스 및 엣지 케이스 스위트"""

    def test_deep_directory_auto_creation_and_atomic_export(self):
        """존재하지 않는 깊은 중첩 디렉토리 자동 생성 및 원자적 CSV 내보내기 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            deep_csv = os.path.join(tmp_dir, "level1", "level2", "level3", "deep_hpo.csv")
            study, best = run_hpo_optimization(
                n_trials=2,
                symbol="005930",
                output_csv=deep_csv,
                seed=42,
                n_timesteps=32,
                fast_mode=True,
                verbose=False,
            )
            assert os.path.exists(deep_csv)
            df = load_hpo_results(deep_csv)
            assert len(df) == 2
            assert list(df.columns) == CSV_COLUMNS

    def test_single_trial_boundary(self):
        """단일 Trial(n_trials=1) 경계 조건 정상 완주 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            single_csv = os.path.join(tmp_dir, "single.csv")
            study, best = run_hpo_optimization(
                n_trials=1,
                symbol="005930",
                output_csv=single_csv,
                seed=77,
                n_timesteps=32,
                fast_mode=True,
                verbose=False,
            )
            assert len(study.trials) == 1
            assert best.number == 0
            df = load_hpo_results(single_csv)
            assert len(df) == 1

    def test_sharpe_zero_variance_defense_adversarial_inputs(self):
        """수익률이 0이거나 표준편차가 0/극미세한 경우 NaN/Inf 미발생 검증"""
        # All zeros
        assert calculate_annualized_sharpe_ratio([0.0] * 50) == 0.0
        # Constant positive returns
        assert calculate_annualized_sharpe_ratio([0.01] * 50) == 0.0
        # Single element
        assert calculate_annualized_sharpe_ratio([0.05]) == 0.0
        # Empty array
        assert calculate_annualized_sharpe_ratio([]) == 0.0
        # Extreme tiny variance
        arr = [0.005 + 1e-12 * (i % 2) for i in range(100)]
        val = calculate_annualized_sharpe_ratio(arr)
        assert not math.isnan(val) and not math.isinf(val)
        assert val == 0.0

    def test_objective_exception_resilience_and_graceful_recovery(self):
        """목적 함수 내부 에러 발생 시 Study 전체가 죽지 않고 FAIL 기록 후 다음 Trial 진행 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            res_csv = os.path.join(tmp_dir, "fail_test.csv")
            study = create_hpo_study(seed=42)

            trial_count = 0

            def _flaky_obj(trial):
                nonlocal trial_count
                trial_count += 1
                if trial.number == 0:
                    # Trial 0은 오류 유발
                    return objective(
                        trial=trial,
                        env_kwargs={"symbol": "NON_EXISTENT_INVALID_SYMBOL_12345", "mode": "invalid_mode"},
                        output_csv=res_csv,
                        n_timesteps=32,
                        fast_mode=True,
                    )
                else:
                    # Trial 1은 정상 수행
                    return objective(
                        trial=trial,
                        symbol="005930",
                        output_csv=res_csv,
                        n_timesteps=32,
                        fast_mode=True,
                    )

            study.optimize(_flaky_obj, n_trials=2, catch=(Exception,))
            assert len(study.trials) == 2
            df = load_hpo_results(res_csv)
            assert len(df) == 2
            assert df.iloc[0]["state"] == "FAIL"
            assert df.iloc[0]["objective_value"] == -100.0
            assert df.iloc[1]["state"] in ("COMPLETE", "PRUNED")
