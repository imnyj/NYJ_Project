"""
modules/hpo/__init__.py
=======================
Auto Stock ML/RL Trader — Milestone 3: 하이퍼파라미터 최적화(HPO) 및 성과 평가 패키지.

주요 모듈:
- metrics: Total Equity, Total Return %, Annualized Sharpe Ratio(0-분산 방어), MDD 등 금융 지표 계산.
- exporter: 20개 컬럼 스키마 기반 Trial 결과 CSV 원자적 저장기.
- optuna_pipeline: TPESampler + MedianPruner 기반 Optuna HPO 파이프라인.
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
    export_trial_to_csv,
    load_hpo_results,
)
from modules.hpo.optuna_pipeline import (
    create_hpo_study,
    objective,
    run_hpo_optimization,
)

__all__ = [
    "calculate_total_equity",
    "calculate_total_return_pct",
    "calculate_annualized_sharpe_ratio",
    "calculate_max_drawdown_pct",
    "calculate_win_rate",
    "evaluate_trading_history",
    "CSV_COLUMNS",
    "export_trial_to_csv",
    "load_hpo_results",
    "create_hpo_study",
    "objective",
    "run_hpo_optimization",
]
