#!/usr/bin/env python3
"""E4-1-redo Oracle dataset 검증 스크립트.
oracle_dataset.csv 의 행 수, action_idx 16-class 분포, cost 통계를 계산.
"""
import os
from collections import Counter

PATH = "/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv"
OUT = "/home/imnyj/papers/paper4/sim/diagnostics_E4-1-redo_report.json"

# 파일 크기
size_bytes = os.path.getsize(PATH)
size_mb = size_bytes / (1024 * 1024)

action_counter = Counter()
n_rows = 0
n_nan_cost = 0
cost_sum = 0.0
cost_min = float("inf")
cost_max = float("-inf")
header = None
action_col_idx = None
cost_col_idx = None

with open(PATH, "r") as f:
    header_line = f.readline().rstrip("\n")
    header = header_line.split(",")
    # action_idx, cost 컬럼 인덱스 찾기
    for i, name in enumerate(header):
        if name.strip() == "action_idx":
            action_col_idx = i
        elif name.strip() == "cost":
            cost_col_idx = i
    for line in f:
        n_rows += 1
        parts = line.rstrip("\n").split(",")
        if action_col_idx is not None and action_col_idx < len(parts):
            try:
                a = int(float(parts[action_col_idx]))
                action_counter[a] += 1
            except ValueError:
                pass
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

cost_mean = (cost_sum / (n_rows - n_nan_cost)) if (n_rows - n_nan_cost) > 0 else None

# 16-class 분포 (0~15)
dist_16 = {str(i): action_counter.get(i, 0) for i in range(16)}
top1 = max(action_counter.values()) if action_counter else 0
sorted_counts = sorted(action_counter.values(), reverse=True)
top3_sum = sum(sorted_counts[:3])

import json
report = {
    "file_path": PATH,
    "file_size_mb": round(size_mb, 2),
    "header": header,
    "n_rows": n_rows,
    "action_dist_16": dist_16,
    "n_unique_actions_used": len(action_counter),
    "top1_count": top1,
    "top1_pct": round(100.0 * top1 / n_rows, 2) if n_rows else 0,
    "top3_pct": round(100.0 * top3_sum / n_rows, 2) if n_rows else 0,
    "cost_stats": {"mean": cost_mean, "min": cost_min if cost_min != float("inf") else None,
                   "max": cost_max if cost_max != float("-inf") else None, "n_nan": n_nan_cost},
    "pass_criteria": {
        "n_rows_ge_100k": n_rows >= 100000,
        "top1_le_50pct": (100.0 * top1 / n_rows) <= 50.0 if n_rows else False,
        "top3_le_70pct": (100.0 * top3_sum / n_rows) <= 70.0 if n_rows else False,
        "cost_nan_zero": n_nan_cost == 0,
    },
}
with open(OUT, "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
