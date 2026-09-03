"""
etc/scripts/verify_m3_hpo.py
============================
Auto Stock Phase 6 Milestone 3: ResNet, Transformer, CVAE 메인 모델 대규모 HPO 파이프라인 심층 검증 스크립트.

검증 항목:
1. suggest_model_params:
   - ResNet, Transformer, CVAE 각 모델별 탐색 파라미터 생성 검증
   - Transformer: tf_d_model % tf_nhead == 0 엄격 검증
2. export_main_model_trial_to_csv 및 MAIN_MODELS_CSV_COLUMNS:
   - 멀티스레드 동시 쓰기 안전성 검증
   - 스키마 무결성 및 누락 없는 필드 매핑 검증
3. 3대 메인 모델 HPO 실행 (n_trials=2 각각 수행):
   - run_model_hpo(model_type="resnet", n_trials=2, ...)
   - run_model_hpo(model_type="transformer", n_trials=2, ...)
   - run_model_hpo(model_type="cvae", n_trials=2, ...)
4. etc/hpo_results/main_models_hpo.csv 검증:
   - 파일 존재 및 총 6개(3모델 x 2회) trial 레코드 무결성 검증
   - model_type, state, total_equity, objective_value 등 유효성 assert
"""

import concurrent.futures
import os
import sys
import time

import optuna

# 프로젝트 루트 경로 추가
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.hpo import (  # noqa: E402
    CSV_COLUMNS,
    MAIN_MODELS_CSV_COLUMNS,
    export_main_model_trial_to_csv,
    load_main_models_hpo_results,
    run_cvae_hpo,
    run_resnet_hpo,
    run_transformer_hpo,
    suggest_model_params,
)


def verify_schema_and_backward_compatibility():
    print("\n--- [1/4] Verifying Schema & Backward Compatibility ---")
    # 1. 기존 CSV_COLUMNS 20개 불변 검증
    assert len(CSV_COLUMNS) == 20, f"CSV_COLUMNS length must be 20, got {len(CSV_COLUMNS)}"
    print("  ✓ Existing CSV_COLUMNS len == 20 preserved")

    # 2. 신규 MAIN_MODELS_CSV_COLUMNS 명세 검증
    assert "model_type" in MAIN_MODELS_CSV_COLUMNS
    assert "param_res_blocks" in MAIN_MODELS_CSV_COLUMNS
    assert "param_tf_d_model" in MAIN_MODELS_CSV_COLUMNS
    assert "param_cvae_latent_dim" in MAIN_MODELS_CSV_COLUMNS
    assert "params_json" in MAIN_MODELS_CSV_COLUMNS
    print(f"  ✓ MAIN_MODELS_CSV_COLUMNS defined with {len(MAIN_MODELS_CSV_COLUMNS)} columns")


def verify_suggest_model_params():
    print("\n--- [2/4] Verifying suggest_model_params ---")
    study = optuna.create_study(direction="maximize")

    # ResNet
    trial_res = study.ask()
    params_res = suggest_model_params(trial_res, "resnet")
    assert "res_blocks" in params_res and 1 <= params_res["res_blocks"] <= 3
    assert params_res["res_filters"] in [16, 32, 64]
    assert params_res["res_kernel_size"] in [3, 5]
    assert 1e-4 <= params_res["sl_lr"] <= 1e-2
    assert "rl_lr" in params_res
    print("  ✓ ResNet search space suggestion verified")

    # Transformer (check tf_d_model % tf_nhead == 0)
    for _ in range(10):
        t_trial = study.ask()
        params_tf = suggest_model_params(t_trial, "transformer")
        assert params_tf["tf_d_model"] in [32, 64]
        assert params_tf["tf_nhead"] in [2, 4, 8]
        assert params_tf["tf_d_model"] % params_tf["tf_nhead"] == 0, (
            f"Divisibility failed: {params_tf['tf_d_model']} % {params_tf['tf_nhead']} != 0"
        )
        assert 1 <= params_tf["tf_layers"] <= 3
    print("  ✓ Transformer search space & head divisibility (10 samples) verified")

    # CVAE
    trial_cvae = study.ask()
    params_cvae = suggest_model_params(trial_cvae, "cvae")
    assert params_cvae["cvae_latent_dim"] in [8, 16, 32]
    assert params_cvae["cvae_hidden_dim"] in [32, 64]
    assert 1e-4 <= params_cvae["cvae_kl_weight"] <= 1e-1
    print("  ✓ CVAE search space suggestion verified")


def verify_concurrent_csv_export():
    print("\n--- [3/4] Verifying Concurrent CSV Export Thread Safety ---")
    test_csv = "etc/hpo_results/test_concurrent_main_models.csv"
    if os.path.exists(test_csv):
        os.remove(test_csv)
    lock_file = f"{test_csv}.lock"
    if os.path.exists(lock_file):
        os.remove(lock_file)

    def _worker_write(idx: int):
        m_type = ["resnet", "transformer", "cvae"][idx % 3]
        fake_trial = {
            "trial_id": idx,
            "state": "COMPLETE",
            "value": 1.23 + idx * 0.1,
            "param_sl_lr": 0.001,
            "param_rl_lr": 0.0003,
            "param_res_blocks": 2,
            "param_tf_d_model": 64,
            "param_cvae_latent_dim": 16,
        }
        fake_metrics = {
            "total_equity": 10_000_000.0 + idx * 1000,
            "total_return_pct": 0.5 * idx,
            "sharpe_ratio": 1.2 + idx * 0.05,
            "max_drawdown_pct": -2.0,
            "total_trades": 5,
            "win_rate": 60.0,
            "duration_seconds": 1.5,
        }
        export_main_model_trial_to_csv(
            trial=fake_trial,
            metrics=fake_metrics,
            model_type=m_type,
            filepath=test_csv,
        )

    # 15 concurrent threads writing simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_worker_write, i) for i in range(15)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    df = load_main_models_hpo_results(test_csv)
    assert len(df) == 15, f"Expected 15 rows from concurrent writes, got {len(df)}"
    assert list(df.columns) == MAIN_MODELS_CSV_COLUMNS
    print(f"  ✓ 15 concurrent writes completed with perfect atomic rows: {len(df)} rows verified")

    # Clean up test files
    if os.path.exists(test_csv):
        os.remove(test_csv)
    if os.path.exists(lock_file):
        os.remove(lock_file)


def verify_e2e_3_models_hpo():
    print("\n--- [4/4] Running E2E HPO Optimization for ResNet, Transformer, CVAE (2 trials each) ---")
    output_csv = "etc/hpo_results/main_models_hpo.csv"
    if os.path.exists(output_csv):
        os.remove(output_csv)
    lock_file = f"{output_csv}.lock"
    if os.path.exists(lock_file):
        os.remove(lock_file)

    t0 = time.time()

    # 1. ResNet HPO (n_trials=2)
    print("  -> Running ResNet HPO (n_trials=2)...")
    res_study, res_best = run_resnet_hpo(
        n_trials=2,
        output_csv=output_csv,
        seed=42,
        n_timesteps=64,
        fast_mode=True,
        verbose=False,
    )
    assert len(res_study.trials) == 2
    print(f"     ResNet Best Trial #{res_best.number}: Value = {res_best.value:.4f}")

    # 2. Transformer HPO (n_trials=2)
    print("  -> Running Transformer HPO (n_trials=2)...")
    tf_study, tf_best = run_transformer_hpo(
        n_trials=2,
        output_csv=output_csv,
        seed=100,
        n_timesteps=64,
        fast_mode=True,
        verbose=False,
    )
    assert len(tf_study.trials) == 2
    print(f"     Transformer Best Trial #{tf_best.number}: Value = {tf_best.value:.4f}")

    # 3. CVAE HPO (n_trials=2)
    print("  -> Running CVAE HPO (n_trials=2)...")
    cvae_study, cvae_best = run_cvae_hpo(
        n_trials=2,
        output_csv=output_csv,
        seed=200,
        n_timesteps=64,
        fast_mode=True,
        verbose=False,
    )
    assert len(cvae_study.trials) == 2
    print(f"     CVAE Best Trial #{cvae_best.number}: Value = {cvae_best.value:.4f}")

    elapsed = time.time() - t0
    print(f"  ✓ All 3 models (6 trials total) completed in {elapsed:.2f}s!")

    # 4. Verify CSV contents
    assert os.path.exists(output_csv), f"{output_csv} does not exist!"
    df = load_main_models_hpo_results(output_csv)
    print(f"  ✓ Loaded {output_csv}: {len(df)} rows, {len(df.columns)} columns")

    # Assert exactly 6 rows (3 models x 2 trials)
    assert len(df) == 6, f"Expected exactly 6 rows, got {len(df)}"

    # Assert all 3 model types are present
    recorded_models = set(df["model_type"].unique())
    expected_models = {"resnet", "transformer", "cvae"}
    assert recorded_models == expected_models, f"Expected {expected_models}, got {recorded_models}"

    # Assert 2 rows per model
    for m in expected_models:
        count = (df["model_type"] == m).sum()
        assert count == 2, f"Expected 2 trials for {m}, got {count}"

    # Assert column structure
    assert list(df.columns) == MAIN_MODELS_CSV_COLUMNS

    # Assert states and metrics
    assert set(df["state"].unique()).issubset({"COMPLETE", "PRUNED", "FAIL"})
    assert (df["total_equity"] > 0).all(), "All total_equity must be positive"
    assert not df["objective_value"].isna().any(), "No NaN in objective_value"
    assert not df["duration_seconds"].isna().any(), "No NaN in duration_seconds"

    print("  ✓ main_models_hpo.csv data integrity fully verified:")
    print(df[["trial_id", "model_type", "state", "objective_value", "total_equity", "sharpe_ratio", "total_trades"]])


def main():
    print("=" * 60)
    print(" Auto Stock Phase 6 Milestone 3: Large-scale HPO Verification")
    print("=" * 60)

    verify_schema_and_backward_compatibility()
    verify_suggest_model_params()
    verify_concurrent_csv_export()
    verify_e2e_3_models_hpo()

    print("\n" + "=" * 60)
    print(" 🎉 ALL MILESTONE 3 HPO PIPELINE VERIFICATIONS PASSED! 🎉")
    print("=" * 60)


if __name__ == "__main__":
    main()
