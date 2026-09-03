"""
tests/test_phase6_hpo.py
========================
Auto Stock Phase 6 Milestone 4: 대규모 병렬 HPO 파이프라인 자동화 검증 테스트 스위트.

검증 항목:
1. TestPhase6HPOSchemaAndSearchSpace:
   - 기존 20개 컬럼 스키마 CSV_COLUMNS 불변성 보존 (len == 20)
   - Phase 6 신규 39개 컬럼 스키마 MAIN_MODELS_CSV_COLUMNS 정의 및 필수 컬럼 무결성
   - suggest_model_params:
     * ResNet 전용 파라미터 탐색 공간 검증
     * Transformer 파라미터 탐색 공간 및 tf_d_model % tf_nhead == 0 헤드 나눗셈 불변식 10회 이상 검증
     * CVAE 전용 파라미터 탐색 공간 검증
     * 잘못된 모델명 주입 시 ValueError 발생 검증

2. TestPhase6HPOConcurrencyAndExport:
   - export_main_model_trial_to_csv 멀티스레드 동시 쓰기 안전성 (fcntl.flock + threading.Lock)
   - 동시 12개 스레드 쓰기 시 데이터 누락 0건 및 12개 레코드 온전한 기록 검증
   - params_json 컬럼의 JSON 직렬화 및 역직렬화 무결성 검증

3. TestPhase6HPOThreeModelsOptimizationE2E:
   - 3대 모델(ResNet, Transformer, CVAE) 각각 n_trials=2 Optuna HPO 완주 및 유효한 best_trial/best_value 도출
   - run_model_hpo 및 run_all_main_models_hpo 실행을 통한 etc/hpo_results/main_models_hpo.csv 생성
   - 디스크 상 파일 물리적 존재(os.path.exists) 검증
   - CSV 로드 시 총 6개 이상 레코드, 각 모델(resnet, transformer, cvae)별 2개 이상 행 포함 검증
   - total_equity, sharpe_ratio, total_return_pct 등 6대 금융 지표 및 하이퍼파라미터 정상 기록 검증

4. TestPhase6HPOExceptionsAndGuards:
   - run_model_hpo에 잘못된 모델명 주입 시 ValueError 예외 처리 검증
"""

import concurrent.futures
import json
import os
import shutil
import tempfile
import pytest
import optuna

from modules.hpo import (
    CSV_COLUMNS,
    MAIN_MODELS_CSV_COLUMNS,
    export_main_model_trial_to_csv,
    load_main_models_hpo_results,
    run_cvae_hpo,
    run_model_hpo,
    run_resnet_hpo,
    run_transformer_hpo,
    suggest_model_params,
)


# ==============================================================================
# 1. 스키마 및 탐색 공간 검증
# ==============================================================================

class TestPhase6HPOSchemaAndSearchSpace:
    """HPO CSV 스키마 및 3대 모델 전용 하이퍼파라미터 탐색 공간 검증"""

    def test_backward_compatible_csv_columns_and_main_models_schema(self):
        """기존 CSV_COLUMNS(20개) 불변 보존 및 MAIN_MODELS_CSV_COLUMNS(39개) 스키마 검증"""
        # 기존 20개 스키마 하위 호환성 100% 보존 검증
        assert len(CSV_COLUMNS) == 20, f"CSV_COLUMNS length must remain 20, got {len(CSV_COLUMNS)}"

        # 신규 39개 스키마 필드 검증
        assert len(MAIN_MODELS_CSV_COLUMNS) == 39, f"MAIN_MODELS_CSV_COLUMNS length must be 39, got {len(MAIN_MODELS_CSV_COLUMNS)}"

        # 기본 식별 및 상태 컬럼
        required_id_cols = ["trial_id", "model_type", "state", "objective_value"]
        for col in required_id_cols:
            assert col in MAIN_MODELS_CSV_COLUMNS, f"Missing required id column: {col}"

        # 6대 금융 지표 컬럼
        required_metric_cols = [
            "total_equity",
            "total_return_pct",
            "sharpe_ratio",
            "max_drawdown_pct",
            "total_trades",
            "win_rate",
        ]
        for col in required_metric_cols:
            assert col in MAIN_MODELS_CSV_COLUMNS, f"Missing required metric column: {col}"

        # 모델별 전용 파라미터 컬럼
        assert "param_res_blocks" in MAIN_MODELS_CSV_COLUMNS
        assert "param_tf_d_model" in MAIN_MODELS_CSV_COLUMNS
        assert "param_tf_nhead" in MAIN_MODELS_CSV_COLUMNS
        assert "param_cvae_latent_dim" in MAIN_MODELS_CSV_COLUMNS
        assert "params_json" in MAIN_MODELS_CSV_COLUMNS
        assert "duration_seconds" in MAIN_MODELS_CSV_COLUMNS

    def test_suggest_model_params_resnet(self):
        """ResNet 하이퍼파라미터 탐색 공간 제안 검증"""
        study = optuna.create_study(direction="maximize")
        trial = study.ask()

        params = suggest_model_params(trial, "resnet")
        assert 1 <= params["res_blocks"] <= 3
        assert params["res_filters"] in [16, 32, 64]
        assert params["res_kernel_size"] in [3, 5]
        assert 1e-4 <= params["sl_lr"] <= 1e-2
        assert 0.0 <= params["sl_dropout"] <= 0.3
        assert 1e-5 <= params["rl_lr"] <= 1e-3
        assert params["batch_size"] in [16, 32, 64]

    def test_suggest_model_params_transformer_head_divisibility(self):
        """Transformer 탐색 공간 및 tf_d_model % tf_nhead == 0 나눗셈 불변식 15회 반복 검증"""
        study = optuna.create_study(direction="maximize")

        for _ in range(15):
            trial = study.ask()
            params = suggest_model_params(trial, "transformer")

            d_model = params["tf_d_model"]
            nhead = params["tf_nhead"]

            assert d_model in [32, 64]
            assert nhead in [2, 4, 8]
            assert d_model % nhead == 0, (
                f"Head divisibility invariant violated: d_model={d_model} % nhead={nhead} != 0"
            )
            assert 1 <= params["tf_layers"] <= 3
            assert 1e-4 <= params["sl_lr"] <= 1e-2

    def test_suggest_model_params_cvae(self):
        """CVAE 하이퍼파라미터 탐색 공간 제안 검증"""
        study = optuna.create_study(direction="maximize")
        trial = study.ask()

        params = suggest_model_params(trial, "cvae")
        assert params["cvae_latent_dim"] in [8, 16, 32]
        assert params["cvae_hidden_dim"] in [32, 64]
        assert 1e-4 <= params["cvae_kl_weight"] <= 1e-1
        assert 1e-4 <= params["sl_lr"] <= 1e-2
        assert 0.0 <= params["sl_dropout"] <= 0.3

    def test_suggest_model_params_invalid_model_type(self):
        """지원하지 않는 모델명 주입 시 ValueError 발생 검증"""
        study = optuna.create_study(direction="maximize")
        trial = study.ask()

        with pytest.raises(ValueError, match="지원되지 않는 model_type"):
            suggest_model_params(trial, "invalid_architecture_xyz")


# ==============================================================================
# 2. 동시성 안전 쓰기 및 JSON 직렬화 검증
# ==============================================================================

class TestPhase6HPOConcurrencyAndExport:
    """멀티스레드 동시 쓰기 원자성 및 CSV 내보내기 안전성 검증"""

    def test_concurrent_multithreaded_csv_export_safety(self):
        """동시 12개 스레드가 하나의 CSV 파일에 동시 기록 시 데이터 유실 0건 및 12개 행 완벽 보존 검증"""
        temp_dir = tempfile.mkdtemp(prefix="hpo_test_concurrent_")
        target_csv = os.path.join(temp_dir, "test_concurrent_main_models.csv")

        try:
            def _worker_write(idx: int):
                m_type = ["resnet", "transformer", "cvae"][idx % 3]
                fake_trial = {
                    "trial_id": idx,
                    "state": "COMPLETE",
                    "value": 1.5 + idx * 0.1,
                    "param_sl_lr": 0.001,
                    "param_rl_lr": 0.0003,
                    "param_res_blocks": 2,
                    "param_tf_d_model": 32,
                    "param_cvae_latent_dim": 16,
                }
                fake_metrics = {
                    "total_equity": 10_000_000.0 + idx * 5000,
                    "total_return_pct": 1.2 * idx,
                    "sharpe_ratio": 1.1 + idx * 0.02,
                    "max_drawdown_pct": -1.5,
                    "total_trades": 8,
                    "win_rate": 62.5,
                    "duration_seconds": 0.8,
                }
                export_main_model_trial_to_csv(
                    trial=fake_trial,
                    metrics=fake_metrics,
                    model_type=m_type,
                    filepath=target_csv,
                )

            # 12개 스레드 동시 실행
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(_worker_write, i) for i in range(12)]
                for future in concurrent.futures.as_completed(futures):
                    future.result()

            # 파일 검증
            assert os.path.exists(target_csv), "Concurrent target CSV was not created!"
            df = load_main_models_hpo_results(target_csv)

            assert len(df) == 12, f"Expected exactly 12 rows from concurrent writes, got {len(df)}"
            assert list(df.columns) == MAIN_MODELS_CSV_COLUMNS

            # 각 모델별 4개씩 균등 기록 확인
            for m in ["resnet", "transformer", "cvae"]:
                assert (df["model_type"] == m).sum() == 4

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_params_json_serialization_and_deserialization(self):
        """CSV에 기록된 params_json 컬럼의 JSON 유효성 및 원본 파라미터 복원 검증"""
        temp_dir = tempfile.mkdtemp(prefix="hpo_test_json_")
        target_csv = os.path.join(temp_dir, "test_params_json.csv")

        try:
            fake_trial = {
                "trial_id": 99,
                "state": "COMPLETE",
                "value": 2.34,
                "param_res_blocks": 2,
                "param_res_filters": 32,
                "param_sl_lr": 0.0025,
                "param_rl_gamma": 0.985,
            }
            export_main_model_trial_to_csv(
                trial=fake_trial,
                metrics={"total_equity": 11_000_000.0, "sharpe_ratio": 1.45},
                model_type="resnet",
                filepath=target_csv,
            )

            df = load_main_models_hpo_results(target_csv)
            assert len(df) == 1
            json_str = df.iloc[0]["params_json"]
            assert isinstance(json_str, str)

            recovered_params = json.loads(json_str)
            assert recovered_params["res_blocks"] == 2
            assert recovered_params["res_filters"] == 32
            assert recovered_params["sl_lr"] == 0.0025

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 3. 3대 모델 HPO E2E 완주 및 CSV 저장 검증 (Acceptance Criteria)
# ==============================================================================

class TestPhase6HPOThreeModelsOptimizationE2E:
    """3가지 아키텍처(ResNet, Transformer, CVAE)별 Optuna 최적화가
    최소 2회(n_trials=2) 이상 크래시 없이 실행되며,
    결과가 etc/hpo_results/main_models_hpo.csv 형태로 저장됨을 입증하는 E2E 테스트."""

    @pytest.mark.parametrize("model_type", ["resnet", "transformer", "cvae"])
    def test_run_model_hpo_single_models_n_trials_2(self, model_type):
        """단일 모델별 run_model_hpo(n_trials=2) 실행 및 best_trial/best_value 유효성 검증"""
        temp_dir = tempfile.mkdtemp(prefix=f"hpo_e2e_{model_type}_")
        temp_csv = os.path.join(temp_dir, f"{model_type}_hpo.csv")

        try:
            study, best_trial = run_model_hpo(
                model_type=model_type,
                n_trials=2,
                output_csv=temp_csv,
                seed=42,
                n_timesteps=64,
                fast_mode=True,
                verbose=False,
            )
            assert len(study.trials) == 2, f"Expected 2 trials for {model_type}, got {len(study.trials)}"
            assert best_trial is not None
            assert isinstance(best_trial.value, float)
            assert not (best_trial.value != best_trial.value), "Best trial value is NaN"

            # 생성된 CSV 검증
            assert os.path.exists(temp_csv)
            df = load_main_models_hpo_results(temp_csv)
            assert len(df) == 2
            assert (df["model_type"] == model_type).all()
            assert (df["total_equity"] > 0).all()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_main_models_hpo_csv_integration_pipeline(self):
        """3개 아키텍처 전체를 run_model_hpo로 각 2회씩 실행하여
        etc/hpo_results/main_models_hpo.csv에 총 6개 이상(모델별 2개)의 행이
        정상 저장되고 필수 금융 지표가 유효함을 입증."""
        output_csv = "etc/hpo_results/main_models_hpo.csv"

        # 기존 테스트 산출물 초기화
        if os.path.exists(output_csv):
            os.remove(output_csv)
        lock_file = f"{output_csv}.lock"
        if os.path.exists(lock_file):
            os.remove(lock_file)

        # 1. ResNet 2 trials
        res_study, res_best = run_resnet_hpo(
            n_trials=2,
            output_csv=output_csv,
            seed=42,
            n_timesteps=64,
            fast_mode=True,
            verbose=False,
        )
        assert len(res_study.trials) == 2
        assert res_best is not None

        # 2. Transformer 2 trials
        tf_study, tf_best = run_transformer_hpo(
            n_trials=2,
            output_csv=output_csv,
            seed=100,
            n_timesteps=64,
            fast_mode=True,
            verbose=False,
        )
        assert len(tf_study.trials) == 2
        assert tf_best is not None

        # 3. CVAE 2 trials
        cvae_study, cvae_best = run_cvae_hpo(
            n_trials=2,
            output_csv=output_csv,
            seed=200,
            n_timesteps=64,
            fast_mode=True,
            verbose=False,
        )
        assert len(cvae_study.trials) == 2
        assert cvae_best is not None

        # 4. Acceptance Criteria 디스크 파일 물리적 존재 검증
        assert os.path.exists(output_csv), f"Acceptance file not found: {output_csv}"

        # 5. DataFrame 무결성 및 스키마 검증
        df = load_main_models_hpo_results(output_csv)
        assert len(df) == 6, f"Expected exactly 6 rows (2 per model), got {len(df)}"

        # 6. 3개 모델 각 2개씩 포함 검증
        for expected_model in ["resnet", "transformer", "cvae"]:
            count = (df["model_type"] == expected_model).sum()
            assert count == 2, f"Expected 2 trials for {expected_model}, got {count}"

        # 7. 컬럼 스키마 일치 검증
        assert list(df.columns) == MAIN_MODELS_CSV_COLUMNS

        # 8. 금융 지표 및 상태 유효성 검증
        assert set(df["state"].unique()).issubset({"COMPLETE", "PRUNED", "FAIL"})
        assert (df["total_equity"] > 0).all(), "total_equity must be positive"
        assert not df["objective_value"].isna().any(), "objective_value contains NaN"
        assert not df["sharpe_ratio"].isna().any(), "sharpe_ratio contains NaN"
        assert not df["total_return_pct"].isna().any(), "total_return_pct contains NaN"
        assert not df["win_rate"].isna().any(), "win_rate contains NaN"
        assert not df["total_trades"].isna().any(), "total_trades contains NaN"
        assert not df["duration_seconds"].isna().any(), "duration_seconds contains NaN"

        # 9. JSON 파라미터 컬럼 검증
        for _, row in df.iterrows():
            params_dict = json.loads(row["params_json"])
            assert isinstance(params_dict, dict)
            assert len(params_dict) > 0


# ==============================================================================
# 4. 예외 처리 및 방어 검증
# ==============================================================================

class TestPhase6HPOExceptionsAndGuards:
    """HPO 러너에 잘못된 인자 주입 시 안전한 예외 발생 검증"""

    def test_run_model_hpo_invalid_model_type_raises_value_error(self):
        """run_model_hpo에 알 수 없는 모델 타입 주입 시 ValueError 발생 검증"""
        with pytest.raises(ValueError, match="지원되지 않는 model_type"):
            run_model_hpo(
                model_type="unknown_nonexistent_model",
                n_trials=1,
                fast_mode=True,
            )
