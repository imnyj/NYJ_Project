---
name: statistical-tests
description: Use when selecting or running statistical tests to compare proposed vs baseline schemes. Covers test selection (paired vs unpaired, parametric vs non-parametric), effect sizes, multiple-comparison correction, and confidence intervals. Load this before writing any code that reports "significantly better".
---

# Statistical Testing Skill

## When to load
- Experimenter (DESIGNER mode) deciding HOW to compare N schemes over M seeds
- Experimenter (ENGINEER mode) implementing the comparison
- Reviewer (QA mode) checking whether the claim "Proposed is significantly better" is supported

## Decision tree: which test?

```
Comparing 2 schemes on the SAME seeds (paired)?
  └── Normality holds (Shapiro-Wilk p > 0.05)?
        ├── YES → Paired t-test (scipy.stats.ttest_rel)
        └── NO  → Wilcoxon signed-rank (scipy.stats.wilcoxon)

Comparing 2 schemes on DIFFERENT seeds (unpaired)?
  └── Normality + equal variance?
        ├── YES → Welch's t-test (scipy.stats.ttest_ind, equal_var=False)
        └── NO  → Mann-Whitney U (scipy.stats.mannwhitneyu)

Comparing 3+ schemes?
  └── Repeated measures (same seeds)?
        ├── YES → Friedman test + post-hoc Wilcoxon with Bonferroni
        └── NO  → Kruskal-Wallis + post-hoc Dunn's
```

**Default to non-parametric** for traffic/V2X metrics — they rarely pass
normality at n=10. Parametric tests are fragile with small samples.

## Canonical comparison code

```python
import numpy as np
from scipy import stats

def compare_two_paired(proposed: np.ndarray, baseline: np.ndarray) -> dict:
    """Wilcoxon signed-rank, Cohen's d, 95% CI on the difference."""
    assert proposed.shape == baseline.shape, "Paired arrays must match."
    diff = proposed - baseline
    # Test
    stat, p = stats.wilcoxon(proposed, baseline, alternative="two-sided")
    # Effect size: Cohen's d on paired differences
    d = diff.mean() / diff.std(ddof=1) if diff.std(ddof=1) > 0 else 0.0
    # 95% CI on mean difference
    t_crit = stats.t.ppf(0.975, df=len(diff) - 1)
    se = diff.std(ddof=1) / np.sqrt(len(diff))
    ci = (diff.mean() - t_crit * se, diff.mean() + t_crit * se)
    return {
        "test": "wilcoxon_signed_rank",
        "statistic": float(stat),
        "p_value": float(p),
        "cohens_d": float(d),
        "mean_diff": float(diff.mean()),
        "ci95": (float(ci[0]), float(ci[1])),
        "n": len(diff),
    }
```

## Effect size interpretation (Cohen's d)

| |d| | Interpretation |
|---|---|
| < 0.2 | negligible |
| 0.2–0.5 | small |
| 0.5–0.8 | medium |
| > 0.8 | large |

**Report both p-value AND effect size.** p < 0.05 with d = 0.1 means "statistically significant, practically irrelevant".

## Multiple-comparison correction

If comparing Proposed vs K baselines, run K tests → inflation of Type I error.
**Apply Bonferroni or Benjamini-Hochberg.**

```python
from statsmodels.stats.multitest import multipletests

p_values = [result[i]["p_value"] for i in baseline_indices]
reject, p_adj, _, _ = multipletests(p_values, alpha=0.05, method="bonferroni")
```

Report adjusted p-values, not raw ones, when more than 2 comparisons.

## Sample size (how many seeds?)

Minimum 5, target 10–30. For a desired effect size d = 0.5, small α = 0.05,
power = 0.8:

```python
from scipy.stats import norm
def required_n(d: float, alpha: float = 0.05, power: float = 0.8) -> int:
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    return int(np.ceil(2 * ((z_a + z_b) / d) ** 2))

required_n(d=0.5)   # → 32 per group for unpaired
required_n(d=0.8)   # → 13 per group
```

If you report "our proposal wins" without enough seeds to detect a meaningful
effect, a reviewer will ask "what is your statistical power?"

## Confidence intervals (report everywhere)

For small n use Student's t-interval, not normal approximation:

```python
def ci_mean(x: np.ndarray, conf: float = 0.95) -> tuple[float, float]:
    n = len(x)
    mean = x.mean()
    se = x.std(ddof=1) / np.sqrt(n)
    t_crit = stats.t.ppf((1 + conf) / 2, df=n - 1)
    return mean - t_crit * se, mean + t_crit * se
```

## Fairness check (Reviewer QA mode)

When validating Experimenter code, check:

1. ☐ Same seeds used across schemes (paired design)?
2. ☐ Same initial conditions / traffic demand / network topology?
3. ☐ Proposed scheme not tuned on test set (data leakage)?
4. ☐ Baselines implemented according to their original papers, not strawmen?
5. ☐ Statistical test matches experimental design (paired vs unpaired)?
6. ☐ Multiple comparisons corrected when applicable?
7. ☐ Effect size reported alongside p-value?

If any is missing, issue a QA report with `confidence=1.0`.
