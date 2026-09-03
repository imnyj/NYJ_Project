"""
modules/hpo/__init__.py
=======================
Auto Stock ML/RL Trader — Milestone 3: 하이퍼파라미터 최적화(HPO) 및 성과 평가 패키지.

주요 모듈:
- metrics: Total Equity, Total Return %, Annualized Sharpe Ratio(0-분산 방어), MDD 등 금융 지표 계산.
- exporter: 20개 컬럼 스키마 및 Phase 6 메인 모델 통합 확장 CSV 원자적 저장기.
- optuna_pipeline: TPESampler + MedianPruner 기반 단일 및 다중 모델(ResNet, Transformer, CVAE) HPO 파이프라인.
"""

from modules.hpo.metrics import (
    calculate_annualized_sharpe_ratio,
    calculate_max_drawdown_pct,
    calculate_total_equity,
    calculate_total_return_pct,
    calculate_win_rate,
    evaluate_trading_history,
)
from modules.hpo.exporter import (
    CSV_COLUMNS,
    MAIN_MODELS_CSV_COLUMNS,
    export_main_model_trial_to_csv,
    export_study_to_csv,
    export_trial_to_csv,
    load_hpo_results,
    load_main_models_hpo_results,
)
from modules.hpo.optuna_pipeline import (
    create_hpo_study,
    objective,
    objective_main_model,
    run_all_main_models_hpo,
    run_cvae_hpo,
    run_hpo_optimization,
    run_model_hpo,
    run_resnet_hpo,
    run_transformer_hpo,
    suggest_model_params,
)

__all__ = [
    # Metrics
    "calculate_total_equity",
    "calculate_total_return_pct",
    "calculate_annualized_sharpe_ratio",
    "calculate_max_drawdown_pct",
    "calculate_win_rate",
    "evaluate_trading_history",
    # Exporter
    "CSV_COLUMNS",
    "MAIN_MODELS_CSV_COLUMNS",
    "export_trial_to_csv",
    "export_study_to_csv",
    "load_hpo_results",
    "export_main_model_trial_to_csv",
    "load_main_models_hpo_results",
    # Pipeline
    "create_hpo_study",
    "objective",
    "run_hpo_optimization",
    "suggest_model_params",
    "objective_main_model",
    "run_model_hpo",
    "run_resnet_hpo",
    "run_transformer_hpo",
    "run_cvae_hpo",
    "run_all_main_models_hpo",
]
