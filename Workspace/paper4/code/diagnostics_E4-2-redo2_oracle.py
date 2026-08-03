#!/usr/bin/env python3
"""E4-2-redo2 Oracle dataset diagnostics.
Analyzes action_idx distribution for alpha02 and alpha05 oracle datasets.
Uses chunked/streaming CSV read (no pandas required, memory-efficient).
"""
import json
from collections import Counter
import math

def analyze_dataset(path, label):
    """Analyze a CSV dataset for action_idx distribution and cost stats."""
    action_counter = Counter()
    n_rows = 0
    n_nan_cost = 0
    cost_sum = 0.0
    cost_min = float("inf")
    cost_max = float("-inf")
    alpha_sample = None
    
    header = None
    action_col_idx = None
    cost_col_idx = None
    alpha_col_idx = None
    
    with open(path, "r") as f:
        header_line = f.readline().rstrip("\n")
        header = header_line.split(",")
        for i, name in enumerate(header):
            h = name.strip()
            if h == "action_idx":
                action_col_idx = i
            elif h == "cost":
                cost_col_idx = i
            elif h == "alpha":
                alpha_col_idx = i
        
        for line in f:
            n_rows += 1
            parts = line.rstrip("\n").split(",")
            
            # action_idx
            if action_col_idx is not None and action_col_idx < len(parts):
                try:
                    a = int(float(parts[action_col_idx]))
                    action_counter[a] += 1
                except ValueError:
                    pass
            
            # cost
            if cost_col_idx is not None and cost_col_idx < len(parts):
                try:
                    c = float(parts[cost_col_idx])
                    if c != c:  # NaN check
                        n_nan_cost += 1
                    else:
                        cost_sum += c
                        if c < cost_min: cost_min = c
                        if c > cost_max: cost_max = c
                except ValueError:
                    n_nan_cost += 1
            
            # alpha sample (take first valid value)
            if alpha_sample is None and alpha_col_idx is not None and alpha_col_idx < len(parts):
                try:
                    alpha_sample = float(parts[alpha_col_idx])
                except ValueError:
                    pass
    
    valid_rows = n_rows - n_nan_cost
    cost_mean = cost_sum / valid_rows if valid_rows > 0 else None
    
    # 16-class distribution (0~15, all keys including zero counts)
    dist = {i: action_counter.get(i, 0) for i in range(16)}
    
    sorted_counts = sorted(action_counter.values(), reverse=True)
    top1 = sorted_counts[0] if sorted_counts else 0
    top3_sum = sum(sorted_counts[:3])
    top1_pct = round(100.0 * top1 / n_rows, 4) if n_rows else 0.0
    top3_pct = round(100.0 * top3_sum / n_rows, 4) if n_rows else 0.0
    unique_actions = len(action_counter)
    
    result = {
        "file": path,
        "rows_total": n_rows,
        "action_idx_distribution": dist,
        "top1_pct": top1_pct,
        "top3_pct": top3_pct,
        "unique_actions": unique_actions,
        "cost_mean": round(cost_mean, 6) if cost_mean is not None else None,
        "cost_min": round(cost_min, 6) if cost_min != float("inf") else None,
        "cost_max": round(cost_max, 6) if cost_max != float("-inf") else None,
        "cost_nan_count": n_nan_cost,
        "alpha_value_sample": alpha_sample
    }
    return result

# Analyze alpha02
print("Analyzing alpha02 dataset...")
alpha02_path = "/home/imnyj/papers/paper4/paper/data/oracle_dataset_alpha02.csv"
result02 = analyze_dataset(alpha02_path, "alpha02")
out02 = "/home/imnyj/papers/paper4/sim/diag_alpha02.json"
with open(out02, "w") as f:
    json.dump(result02, f, indent=2)
print(json.dumps(result02, indent=2))

# Analyze alpha05
print("\nAnalyzing alpha05 dataset...")
alpha05_path = "/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv"
result05 = analyze_dataset(alpha05_path, "alpha05")
out05 = "/home/imnyj/papers/paper4/sim/diag_alpha05.json"
with open(out05, "w") as f:
    json.dump(result05, f, indent=2)
print(json.dumps(result05, indent=2))

print("\nDone. JSON files saved.")
