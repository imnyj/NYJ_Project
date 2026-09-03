# E2E Test Suite Ready: Auto_Stock Hybrid SL-RL & Optuna HPO Pipeline

## Test Runner
- Command: `make test-hpo` (또는 `pytest tests/test_hpo_pipeline.py -v`)
- Expected: All 27 tests pass with exit code 0 (< 12 seconds execution)

## Coverage Summary
| Tier | Count | Description |
|------|------:|-------------|
| 1. Feature Coverage | 8 | Hybrid action space, Gymnasium 1.2.0, 1-won invariant, SL/RL models, HPO study, Metrics, CSV export |
| 2. Boundary & Corner | 5 | 0-variance Sharpe defense, NaN/Inf clipping, bankruptcy exit (<5%), boundary weights (0.0/1.0), action clipping |
| 3. Cross-Feature | 4 | Full cycle Env↔Policy↔Metrics↔Exporter, SB3 wrapper adapter, reproducibility, 8-thread atomic lock |
| 4. Real-World Application | 7 | 3-trial HPO optimization, agent vs B&H, crash defense, flat market defense, live/offline dual mode, CLI runner, time budget |
| 5. Adversarial & Pruning | 3 | Error injection fault-tolerance, MedianPruner pruned state, fcntl multiprocess concurrency 0-loss |
| **Total** | **27** | **100% Passed (0 Failures, 0 Warnings)** |

## Feature Checklist
| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 |
|---------|:------:|:------:|:------:|:------:|:------:|
| F1: Hybrid Action Space | ✓ | ✓ | ✓ | ✓ | ✓ |
| F2: Gymnasium 1.2.0 Compliance | ✓ | ✓ | ✓ | ✓ | ✓ |
| F3: Accounting Integrity (1-won) | ✓ | ✓ | ✓ | ✓ | ✓ |
| F4: SL Feature Extractor | ✓ | ✓ | ✓ | ✓ | ✓ |
| F5: RL Baseline Hybrid Policy | ✓ | ✓ | ✓ | ✓ | ✓ |
| F6: Optuna HPO Study | ✓ | ✓ | ✓ | ✓ | ✓ |
| F7: Financial Metrics (Equity/Sharpe/MDD) | ✓ | ✓ | ✓ | ✓ | ✓ |
| F8: CSV Results Export (`baseline_hpo.csv`) | ✓ | ✓ | ✓ | ✓ | ✓ |
