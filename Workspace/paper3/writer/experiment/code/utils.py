"""
utils.py — Common utilities: seed management, IO, metrics, CSV writing.
"""
import csv
import os
import random
import math
import statistics
from collections import defaultdict


def set_seed(seed):
    random.seed(seed)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def write_csv(filepath, rows, fieldnames=None):
    """Write list of dicts to CSV file."""
    if not rows:
        return
    ensure_dir(os.path.dirname(filepath))
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_runs(run_results):
    """
    Aggregate multiple run results (list of dicts) into mean ± std.
    Returns dict with keys: metric_mean, metric_std for each metric.
    """
    if not run_results:
        return {}
    metrics = list(run_results[0].keys())
    agg = {}
    for m in metrics:
        vals = [r[m] for r in run_results if isinstance(r[m], (int, float))]
        if vals:
            agg[f'{m}_mean'] = statistics.mean(vals)
            agg[f'{m}_std'] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        else:
            agg[m] = run_results[0][m]
    return agg


def compute_metrics(total_hits, total_requests, total_v2v_hits, total_aoi_violations,
                    total_slots, pco_count, rlbi_sum, n_vehicles, duration, warmup, sched_window):
    """Compute the 5 primary metrics from raw counters."""
    n = max(1, total_requests)
    post_slots = max(1, total_slots)
    n_sched = max(1, (duration - warmup) // sched_window * n_vehicles)
    return {
        'CHR': total_hits / n,
        'CDSR': total_v2v_hits / n,
        'AoI_violation_rate': total_aoi_violations / post_slots,
        'PCO': pco_count / n_sched,
        'RLBI': rlbi_sum / post_slots,
    }


def format_result_row(scenario, algorithm, density, pred_error_pct, gamma, tau_max, seed, metrics):
    """Build a flat dict row for CSV output."""
    row = {
        'scenario': scenario,
        'algorithm': algorithm,
        'density': density,
        'pred_error_pct': pred_error_pct,
        'gamma': gamma,
        'tau_max': tau_max,
        'seed': seed,
    }
    row.update(metrics)
    return row
