"""
tests/test_adversarial_m3_challenger1.py
=========================================
Auto Stock Milestone 3: Adversarial Challenger 1 Stress Test Suite.

검증 항목:
1. Metrics 극한 내결함성:
   - 0-분산, 음수 자산, 100% 손실 파산, NaN/Inf 처리, 미세 변동 및 극한 부동소수점.
2. Exporter 극한 내결함성:
   - 미존재 중첩 디렉토리, 특수문자/개행/따옴표/유니코드 주입, 20스레드 동시 다중 쓰기 무결성.
3. Optuna Pipeline 극한 내결함성 및 취약점 실증:
   - 극단적 하이퍼파라미터 (LR 1e-7, batch_size 1, hidden_dim 4 등) 주입 시 제약 조건 및 예외 탈출 실증.
   - 환경 장애 주입 시 Study 생존성 및 FAIL 상태 CSV 기록 검증.
   - 파산 조건 판정 및 목적 함수 페널티 산출 검증.
"""

import concurrent.futures
import math
import os
import shutil
import tempfile
import threading
import time
from decimal import Decimal
from typing import Any, Dict, List

import numpy as np
import optuna
import pandas as pd
import pytest

from modules.engine.hybrid_trading_env import HybridTradingEnv
from modules.hpo.exporter import CSV_COLUMNS, export_trial_to_csv, load_hpo_results
from modules.hpo.metrics import (
    calculate_annualized_sharpe_ratio,
    calculate_max_drawdown_pct,
    calculate_total_equity,
    calculate_total_return_pct,
    calculate_win_rate,
    evaluate_trading_history,
)
from modules.hpo.optuna_pipeline import create_hpo_study, objective, run_hpo_optimization


# =====================================================================
# 1. Metrics Module Adversarial Stress Tests
# =====================================================================
class TestMetricsAdversarialStress:
    """성과 지표 계산 모듈(metrics.py)에 대한 극한 스트레스 및 적대적 입력 테스트"""

    def test_sharpe_ratio_zero_variance_and_extreme_flatness(self):
        """0 분산 및 극미세 분산 환경에서 ZeroDivisionError 없이 0.0 반환 검증"""
        # 완벽한 0 분산 (동일한 값 반복)
        assert calculate_annualized_sharpe_ratio([0.0] * 500) == 0.0
        assert calculate_annualized_sharpe_ratio([0.05] * 200) == 0.0
        assert calculate_annualized_sharpe_ratio([-0.02] * 100) == 0.0

        # eps 이하의 극미세 진폭 (std <= 1e-8)
        tiny_fluctuation = [0.01 + 1e-9 * ((-1) ** i) for i in range(100)]
        assert calculate_annualized_sharpe_ratio(tiny_fluctuation) == 0.0

        # 단일 원소 및 빈 리스트
        assert calculate_annualized_sharpe_ratio([]) == 0.0
        assert calculate_annualized_sharpe_ratio([0.05]) == 0.0
        assert calculate_annualized_sharpe_ratio(None) == 0.0

    def test_sharpe_ratio_nan_inf_and_extreme_outliers(self):
        """수익률 시계열 내 NaN, Inf, -Inf, 및 극단적 이상치 주입 시 안전성 검증"""
        dirty_returns = [0.01, float("nan"), 0.02, float("inf"), float("-inf"), -0.01, 0.015]
        sr = calculate_annualized_sharpe_ratio(dirty_returns)
        assert isinstance(sr, float)
        assert not math.isnan(sr)
        assert not math.isinf(sr)

        # 전체가 NaN / Inf 인 경우
        assert calculate_annualized_sharpe_ratio([float("nan")] * 10) == 0.0
        assert calculate_annualized_sharpe_ratio([float("inf"), float("-inf")]) == 0.0

        # 극단적 거대 수치 (1e15) 주입 시 오버플로 없이 계산
        extreme_returns = [1e15, -1e15, 1e15, -1e15]
        sr_ext = calculate_annualized_sharpe_ratio(extreme_returns)
        assert isinstance(sr_ext, float)
        assert not math.isnan(sr_ext)

    def test_total_equity_bankruptcy_and_negative_assets(self):
        """음수 현금, 0원 주가, NaN/Inf 자산 평가 시 크래시 방어 검증"""
        # 음수 잔고 (부채 상태)
        eq_neg_cash = calculate_total_equity(cash=-5_000_000, holdings=10, current_price=100_000)
        assert eq_neg_cash == -4_000_000.0

        # 주가 0원 (상장폐지/휴지조각)
        eq_zero_price = calculate_total_equity(cash=1_000_000, holdings=1000, current_price=0.0)
        assert eq_zero_price == 1_000_000.0

        # 100% 손실 파산 (현금 0, 주가 0)
        eq_bankrupt = calculate_total_equity(cash=0.0, holdings=100, current_price=0.0)
        assert eq_bankrupt == 0.0

        # NaN / Inf 주가 주입 시 fallback 방어
        eq_nan = calculate_total_equity(cash=1_000_000, holdings=100, current_price=float("nan"))
        assert eq_nan == 1_000_000.0
        eq_inf = calculate_total_equity(cash=1_000_000, holdings=100, current_price=float("inf"))
        assert eq_inf == 1_000_000.0

    def test_total_return_pct_edge_cases(self):
        """초기 자본 0, 음수 자본, 100% 전액 손실, 초고수익 계산 검증"""
        # 초기 자본 0 이하 -> 0.0 반환
        assert calculate_total_return_pct(0, 10_000_000) == 0.0
        assert calculate_total_return_pct(-1_000_000, 10_000_000) == 0.0

        # 100% 전액 손실 (10,000,000 -> 0)
        ret_total_loss = calculate_total_return_pct(10_000_000, 0)
        assert pytest.approx(ret_total_loss, rel=1e-4) == -100.0

        # 부채 파산 (10,000,000 -> -5,000,000)
        ret_debt = calculate_total_return_pct(10_000_000, -5_000_000)
        assert pytest.approx(ret_debt, rel=1e-4) == -150.0

        # NaN / Inf 자산 주입 시 0.0 반환
        assert calculate_total_return_pct(10_000_000, float("nan")) == 0.0
        assert calculate_total_return_pct(10_000_000, float("inf")) == 0.0

    def test_max_drawdown_pct_bankruptcy_and_monotonic(self):
        """자산 0원 도달(파산), 음수 자산 시계열, NaN 포함 시 MDD 계산 검증"""
        # 10,000,000 -> 0원 전액 손실 (-100% MDD)
        loss_curve = [10_000_000, 5_000_000, 2_000_000, 0.0]
        mdd_loss = calculate_max_drawdown_pct(loss_curve)
        assert pytest.approx(mdd_loss, rel=1e-4) == -100.0

        # 음수 자산으로 추락 (10,000,000 -> -5,000,000)
        negative_curve = [10_000_000, 2_000_000, -5_000_000]
        mdd_neg = calculate_max_drawdown_pct(negative_curve)
        assert pytest.approx(mdd_neg, rel=1e-4) == -150.0

        # 자산 곡선 내 NaN/Inf 혼입
        dirty_curve = [10_000_000, float("nan"), 8_000_000, float("inf"), 6_000_000]
        mdd_dirty = calculate_max_drawdown_pct(dirty_curve)
        assert pytest.approx(mdd_dirty, rel=1e-4) == -40.0

    def test_win_rate_irregular_records(self):
        """비정상적인 trade_records (Decimal, 빈 딕셔너리, None PnL, 음수 손익) 처리 검증"""
        records = [
            {"realized_pnl": 100_000},
            {"realized_pnl": -50_000},
            {"realized_pnl": 0.0},  # 무수익은 승리 아님
            Decimal("200000"),
            -30000.0,
            {"invalid_key": 999},  # 무시
        ]
        total_trades, win_rate = calculate_win_rate(records)
        # 有效 PnL: 100000(승), -50000(패), 0(패), 200000(승), -30000(패) -> 5건 중 2건 승리 = 40%
        assert total_trades == 5
        assert pytest.approx(win_rate, rel=1e-4) == 40.0

    def test_evaluate_trading_history_complete_bankruptcy(self):
        """전체 트레이딩 이력이 파산으로 끝나는 극한 상황 지표 산출 종합 검증"""
        bankrupt_equity = [10_000_000, 7_000_000, 3_000_000, 100_000, 0.0]
        metrics = evaluate_trading_history(
            equity_history=bankrupt_equity,
            initial_cash=10_000_000,
        )

        assert metrics["total_equity"] == 0.0
        assert pytest.approx(metrics["total_return_pct"], rel=1e-4) == -100.0
        assert pytest.approx(metrics["max_drawdown_pct"], rel=1e-4) == -100.0
        assert isinstance(metrics["sharpe_ratio"], float)
        assert not math.isnan(metrics["sharpe_ratio"])


# =====================================================================
# 2. Exporter Module Adversarial Stress Tests
# =====================================================================
class TestExporterAdversarialStress:
    """CSV 내보내기 모듈(exporter.py)에 대한 동시성, 특수문자, 비정상 디렉토리 스트레스 테스트"""

    def test_deep_nested_nonexistent_directory(self):
        """깊게 중첩된 미존재 디렉토리 자동 생성 및 저장 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            deep_path = os.path.join(tmp_dir, "level1", "level2", "level3", "deep_hpo.csv")
            saved_path = export_trial_to_csv({"trial_id": 1, "objective_value": 0.95}, csv_path=deep_path)
            assert os.path.exists(saved_path)
            df = load_hpo_results(saved_path)
            assert len(df) == 1
            assert df["trial_id"].iloc[0] == 1

    def test_special_characters_newlines_and_unicode_injection(self):
        """특수 문자, 쉼표, 개행, 유니코드 한글 및 따옴표 주입 시 CSV 포맷 무결성 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "special_chars.csv")
            malicious_record = {
                "trial_id": 99,
                "state": "COMPLETE, \"INJECTED\"\nNEWLINE",
                "objective_value": 3.141592,
                "datetime_start": "2026-09-02T12:00:00+09:00, [특수문자 테스트!@#$%^&*()]",
            }
            export_trial_to_csv(malicious_record, csv_path=csv_path)

            # 판다스로 다시 읽었을 때 컬럼 수 20개 정확히 유지되는지 확인
            df = load_hpo_results(csv_path)
            assert len(df) == 1
            assert len(df.columns) == 20
            assert df["trial_id"].iloc[0] == 99

    def test_concurrent_multi_thread_csv_writes(self):
        """20개 스레드가 동시에 25개 Trial(총 500행)을 기록할 때 레이스 컨디션 및 파일 손상 없음 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "concurrent_hpo.csv")
            num_threads = 20
            records_per_thread = 25
            total_expected_rows = num_threads * records_per_thread

            def _worker_write(thread_id: int):
                for i in range(records_per_thread):
                    trial_id = thread_id * 1000 + i
                    rec = {
                        "trial_id": trial_id,
                        "state": "COMPLETE",
                        "objective_value": float(i * 0.1),
                        "total_equity": 10_000_000.0 + (trial_id * 10),
                        "param_sl_lr": 0.001,
                    }
                    export_trial_to_csv(rec, csv_path=csv_path)

            threads = [
                threading.Thread(target=_worker_write, args=(t,))
                for t in range(num_threads)
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 무결성 검증
            assert os.path.exists(csv_path)
            df = load_hpo_results(csv_path)
            assert len(df) == total_expected_rows
            assert list(df.columns) == CSV_COLUMNS
            # 중복 없이 모든 고유 trial_id가 온전히 보존되었는지 검증
            unique_tids = df["trial_id"].nunique()
            assert unique_tids == total_expected_rows

    def test_corrupted_existing_csv_fallback(self):
        """기존 CSV가 깨져있거나 불완전한 상태일 때 Append 모드로 안전하게 복구 저장되는지 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "broken.csv")
            # 불완전한 헤더/내용 생성
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("corrupted,binary,\x00\x01\x02\n")

            # 새로운 정상 레코드 추가
            export_trial_to_csv({"trial_id": 10, "objective_value": 1.23}, csv_path=csv_path)

            # 크래시 없이 파일에 내용이 기록되었는지 확인
            assert os.path.exists(csv_path)
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "10" in content


# =====================================================================
# 3. Optuna Pipeline Adversarial Stress Tests
# =====================================================================
class TestOptunaPipelineAdversarialStress:
    """Optuna HPO 최적화 파이프라인(optuna_pipeline.py)에 대한 극한 파라미터 및 결함 복원력 테스트"""

    def test_extreme_hyperparameters_injection_boundary_and_tolerance(self):
        """
        극단적 하이퍼파라미터(LR 1e-7, RL LR 1e-7 등 탐색공간 경계값) 주입 시
        PPO 학습 및 시뮬레이션이 안정적으로 완주함을 검증.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "extreme_params_hpo.csv")

            study = create_hpo_study(seed=42)

            # 탐색 공간 내 최소/극단 파라미터를 enqueue_trial로 주입
            study.enqueue_trial({
                "sl_lr": 1e-7,
                "sl_hidden_dim": 32,
                "sl_batch_size": 16,
                "rl_lr": 1e-7,
                "rl_gamma": 0.90,
                "rl_clip_range": 0.1,
                "rl_ent_coef": 1e-4,
                "rl_hidden_dim": 64,
            })

            def _obj(trial):
                return objective(
                    trial=trial,
                    symbol="005930",
                    output_csv=csv_path,
                    n_timesteps=40,
                    fast_mode=True,
                    seed=42,
                )

            study.optimize(_obj, n_trials=1)
            trial = study.trials[0]

            assert trial.state == optuna.trial.TrialState.COMPLETE
            assert isinstance(trial.value, float)
            assert not math.isnan(trial.value)

            df = load_hpo_results(csv_path)
            assert len(df) == 1
            assert df["param_sl_lr"].iloc[0] == 1e-7
            assert df["param_rl_lr"].iloc[0] == 1e-7

    def test_empirical_vulnerability_categorical_param_mismatch_behavior(self):
        """
        [취약점 실증 1]
        탐색 공간 외의 범주형 파라미터 (예: hidden_dim=4, batch_size=1)를 주입할 경우
        `trial.suggest_categorical`이 `objective()` 내부의 try-except 블록 외부에서 호출되어
        ValueError가 발생하고 CSV 저장이 스킵되는 동작을 실증.
        """
        study = create_hpo_study(seed=42)
        study.enqueue_trial({
            "sl_lr": 1e-7,
            "sl_hidden_dim": 4,  # [32, 64, 128, 256]에 포함되지 않는 값
            "sl_batch_size": 1,  # [16, 32, 64, 128]에 포함되지 않는 값
            "rl_lr": 1e-7,
            "rl_gamma": 0.90,
            "rl_clip_range": 0.1,
            "rl_ent_coef": 1e-4,
            "rl_hidden_dim": 4,
        })

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "unsupported_param_hpo.csv")

            def _obj(trial):
                return objective(
                    trial=trial,
                    output_csv=csv_path,
                    n_timesteps=30,
                    fast_mode=True,
                )

            # catch=(Exception,) 없을 시 ValueError가 Study 외부로 전파됨을 실증
            with pytest.raises(ValueError) as exc_info:
                study.optimize(_obj, n_trials=1)

            assert "'4' not in (32, 64, 128, 256)" in str(exc_info.value)
            # try 블록 외측에서 에러가 발생하여 CSV 기록이 생략됨을 확인
            assert not os.path.exists(csv_path)

    def test_fault_injection_invalid_env_mode_resilience(self):
        """
        환경 초기화 실패(예: 잘못된 모드명) 주입 시
        objective 내부에서 try-except로 잡혀 FAIL 상태로 CSV에 원자적 기록되고
        Study가 중단되지 않고 다음 정상 Trial을 계속 수행함을 검증.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "fault_resilience_hpo.csv")

            study = create_hpo_study(seed=42)

            def _faulty_step(trial):
                if trial.number == 0:
                    # Trial 0: 장애 주입 (지원하지 않는 모드명)
                    return objective(
                        trial=trial,
                        env_kwargs={"mode": "non_existing_mode"},
                        output_csv=csv_path,
                        n_timesteps=30,
                        fast_mode=True,
                    )
                else:
                    # Trial 1: 정상 동작
                    return objective(
                        trial=trial,
                        symbol="005930",
                        output_csv=csv_path,
                        n_timesteps=30,
                        fast_mode=True,
                    )

            study.optimize(_faulty_step, n_trials=2, catch=(Exception,))

            assert len(study.trials) == 2
            # Trial 0은 FAIL 및 -100.0 페널티 확인
            assert study.trials[0].value == -100.0

            df = load_hpo_results(csv_path)
            assert len(df) == 2
            assert df["state"].iloc[0] == "FAIL"
            assert df["objective_value"].iloc[0] == -100.0
            assert df["state"].iloc[1] in ("COMPLETE", "PRUNED")

    def test_full_optimization_end_to_end_stress_multi_trials(self):
        """5회 Trial 연속 HPO 수행 및 베스트 결과 일관성 검증"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "e2e_stress_hpo.csv")

            study, best_trial = run_hpo_optimization(
                n_trials=5,
                symbol="005930",
                output_csv=csv_path,
                seed=100,
                n_timesteps=50,
                fast_mode=True,
                verbose=False,
            )

            assert len(study.trials) == 5
            assert best_trial is not None
            assert best_trial.state == optuna.trial.TrialState.COMPLETE

            df = load_hpo_results(csv_path)
            assert len(df) >= 5
            # 모든 trial_id 정렬 확인
            assert df["trial_id"].tolist() == [0, 1, 2, 3, 4]
            for col in CSV_COLUMNS:
                assert col in df.columns
