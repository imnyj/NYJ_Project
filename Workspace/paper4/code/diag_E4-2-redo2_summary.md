# E4-2-redo2 Oracle Dataset Diagnostics Summary

**Generated:** 2026-05-14  
**Analysis method:** Streaming sample (every 1000th row, ~9196 samples from 9,195,822 total rows)

## Dataset Overview

| Metric | alpha=0.2 (oracle_dataset_alpha02.csv) | alpha=0.5 (oracle_dataset.csv) |
|--------|----------------------------------------|-------------------------------|
| File size | ~584 MB | ~588 MB |
| Total rows | 9,195,822 | 9,195,822 |
| unique_actions | 4 | 4 |
| top1_pct | 49.9674% | 49.9674% |
| top3_pct | 99.9674% | 99.9674% |
| cost_mean | 0.260565 | 0.219107 |
| cost_min | 0.08 | 0.125 |
| cost_max | 0.46 | 0.325 |
| cost_nan_count | 0 | 0 |
| alpha_value_sample | 0.2 ✓ | 0.5 ✓ |

## action_idx Distribution (16-class, estimated full counts)

| action_idx | alpha=0.2 (est. count) | alpha=0.2 (%) | alpha=0.5 (est. count) | alpha=0.5 (%) |
|-----------|------------------------|---------------|------------------------|---------------|
|  0 |    1,186,977 |  12.91% |    1,186,977 |  12.91% | ◀
|  1 |            0 |   0.00% |            0 |   0.00% |
|  2 |            0 |   0.00% |        3,000 |   0.03% | ◀
|  3 |    3,410,934 |  37.09% |    3,410,934 |  37.09% | ◀
|  4 |            0 |   0.00% |            0 |   0.00% |
|  5 |            0 |   0.00% |            0 |   0.00% |
|  6 |            0 |   0.00% |            0 |   0.00% |
|  7 |    4,594,911 |  49.97% |    4,594,911 |  49.97% | ◀
|  8 |            0 |   0.00% |            0 |   0.00% |
|  9 |            0 |   0.00% |            0 |   0.00% |
| 10 |            0 |   0.00% |            0 |   0.00% |
| 11 |        3,000 |   0.03% |            0 |   0.00% | ◀
| 12 |            0 |   0.00% |            0 |   0.00% |
| 13 |            0 |   0.00% |            0 |   0.00% |
| 14 |            0 |   0.00% |            0 |   0.00% |
| 15 |            0 |   0.00% |            0 |   0.00% |

## Commander Gate Verdict (≥8 unique classes AND top-3 ≤ 80%)

| Dataset | unique_actions ≥ 8 | top3_pct ≤ 80% | Overall |
|---------|-------------------|----------------|---------|
| alpha=0.2 (oracle_dataset_alpha02.csv) | ✗ (4) | ✗ (99.9674%) | **FAIL** |
| alpha=0.5 (oracle_dataset.csv)         | ✗ (4) | ✗ (99.9674%) | **FAIL** |

## Key Findings

- **Both datasets are FAIL**: Only 4 out of 16 action classes are used (indices 0, 3, 7, and either 11 or 2 for a tiny fraction).
- **Severe class imbalance**: action_idx=7 dominates at ~50%, with top-3 covering >99.9% of all samples.
- **alpha=0.2 vs alpha=0.5**: The distributions are nearly identical in shape; the only difference is:
  - alpha=0.2: uses action_idx=11 (tiny, ~0.03%)
  - alpha=0.5: uses action_idx=2 (tiny, ~0.03%)
  - alpha=0.2 has higher cost range (0.08–0.46, mean=0.261) vs alpha=0.5 (0.125–0.325, mean=0.219)
- **Alpha confirmation**: alpha_value_sample=0.2 confirmed for oracle_dataset_alpha02.csv ✓
- **Root cause concern**: The extreme concentration on only 3–4 actions suggests the oracle policy is not exploring the full 16-action space, which is the stale-dataset issue identified in E4-2-redo2.
