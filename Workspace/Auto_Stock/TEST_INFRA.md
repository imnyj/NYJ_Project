# E2E Test Infra: Auto_Stock Hybrid SL-RL & HPO Pipeline

## Test Philosophy
- Opaque-box, requirement-driven. Derived from `ORIGINAL_REQUEST.md`.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise + Real-World Workload Testing.

## Feature Inventory & Test Mapping
| # | Feature | Source | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (Real-World) |
|---|---------|--------|:----------------:|:-----------------:|:---------------------:|:-------------------:|
| F1 | Hybrid Action Space (Discrete + Box) | R1 | 5 | 5 | ✓ | ✓ |
| F2 | Gymnasium 1.2.0 Compliance | R1 | 5 | 5 | ✓ | ✓ |
| F3 | Accounting Integrity & Execution Engine | R1 | 5 | 5 | ✓ | ✓ |
| F4 | SL Feature Extractor (1D-CNN / MLP) | R2 | 5 | 5 | ✓ | ✓ |
| F5 | RL Baseline Hybrid Policy | R2 | 5 | 5 | ✓ | ✓ |
| F6 | Optuna HPO Study (TPESampler & Pruner) | R3 | 5 | 5 | ✓ | ✓ |
| F7 | Financial Metrics (Equity & Sharpe Ratio) | R3 | 5 | 5 | ✓ | ✓ |
| F8 | CSV Results Export (`baseline_hpo.csv`) | R4 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: `pytest tests/test_hpo_pipeline.py -v`
- Execution time budget: < 10 seconds for rapid verification.
- Output artifact: `etc/hpo_results/baseline_hpo.csv` with valid 20-column schema and at least 3 completed trials.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Baseline HPO 3-Trial Execution | F1 ~ F8 | HPO completes with 3 trials, writes CSV, Sharpe/Equity computed |
| 2 | Pure Buy-and-Hold Baseline vs Agent | F1, F3, F7 | Agent executes non-trivial trades and tracks equity |
| 3 | Market Crash / Drawdown Defense | F1, F3, F7 | Bankruptcy threshold triggers termination without crash |
| 4 | Zero Variance / Constant Market | F7 | Sharpe Ratio handles 0 std without division by zero |
| 5 | Live / Offline Dual Mode Switching | F1, F2, F3 | Env handles both offline Parquet and live simulator |

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (Happy-path isolation)
- Tier 2: ≥5 boundary & corner test cases (zero variance, bankrupt, boundary weights 0.0/1.0, empty/corrupt data)
- Tier 3: Pairwise cross-feature interactions (SL weights -> RL policy -> Gym Env -> HPO metrics -> CSV export)
- Tier 4: Realistic E2E pipeline execution (Full 3-trial HPO pipeline)
- Tier 5: Adversarial edge-case hardening
