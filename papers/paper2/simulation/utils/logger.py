"""
logger.py
=========
CSV logging utility for MAFAC simulation results.
"""

import csv
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class CSVLogger:
    """Thread-safe CSV logger that appends rows to a file."""

    def __init__(self, filepath: str, fieldnames: List[str],
                 overwrite: bool = True):
        self.filepath   = Path(filepath)
        self.fieldnames = fieldnames
        self._file      = None
        self._writer    = None

        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        mode = "w" if overwrite else "a"
        self._file = open(str(self.filepath), mode, newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames,
                                       extrasaction="ignore")
        if overwrite or self.filepath.stat().st_size == 0:
            self._writer.writeheader()
        self._file.flush()

    def log(self, row: Dict[str, Any]):
        """Write one row. Missing fields are filled with empty string."""
        self._writer.writerow(row)
        self._file.flush()

    def log_many(self, rows: List[Dict[str, Any]]):
        for row in rows:
            self.log(row)

    def close(self):
        if self._file and not self._file.closed:
            self._file.close()

    def __del__(self):
        self.close()

    def __repr__(self):
        return f"CSVLogger({self.filepath})"


class ExperimentLogger:
    """
    Manages multiple CSV loggers for all output files.
    """

    # Field schemas for each output file
    SCHEMAS = {
        "convergence_training_curves": [
            "episode", "algorithm", "average_aoi", "peak_aoi",
            "cache_hit_ratio", "tx_success_rate", "throughput_mbps",
            "constraint_violation", "actor_loss", "critic_loss",
            "lagrange_lambda", "mean_reward",
        ],
        "convergence_constraint_satisfaction": [
            "episode", "algorithm", "cbr", "constraint_satisfied",
            "lagrange_lambda", "energy_constraint", "aoi_qos_constraint",
        ],
        "ablation_component_analysis": [
            "scenario", "variant", "average_aoi", "peak_aoi",
            "cache_hit_ratio", "tx_success_rate", "throughput_mbps",
            "constraint_violation",
        ],
        "communication_overhead": [
            "round", "algorithm", "num_agents", "num_rsus",
            "bytes_per_round", "cumulative_mb", "time_s",
        ],
        "model_verification_theorem1": [
            "cache_hit_ratio", "p_tx_success", "lambda_content",
            "simulated_aoi", "theoretical_bound", "relative_error",
        ],
        "model_verification_theorem2": [
            "content_id", "lambda_k", "mu_k", "optimal_ttl_theory",
            "best_ttl_sim", "aoi_at_optimal", "aoi_at_best",
        ],
    }

    # Scenario file schemas (shared structure)
    SCENARIO_METRICS = [
        "average_aoi", "peak_aoi", "cache_hit_ratio",
        "tx_success_rate", "throughput_mbps", "constraint_violation",
    ]

    def __init__(self, output_dir: str, overwrite: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._loggers: Dict[str, CSVLogger] = {}
        self._overwrite = overwrite

    def _get_scenario_fields(self, scenario: str, metric: str,
                              param_name: str) -> List[str]:
        algorithms = ["MAFAC", "Centralized-AoI", "SAC-Single",
                      "IQL", "NDN-LRU", "No-Cache"]
        return [param_name] + algorithms

    def get_logger(self, name: str,
                   fieldnames: List[str] = None) -> CSVLogger:
        if name not in self._loggers:
            fp = self.output_dir / f"{name}.csv"
            if fieldnames is None:
                fieldnames = self.SCHEMAS.get(name, ["value"])
            self._loggers[name] = CSVLogger(str(fp), fieldnames,
                                             self._overwrite)
        return self._loggers[name]

    def log_training(self, episode: int, algorithm: str, metrics: dict):
        lg = self.get_logger("convergence_training_curves")
        row = {"episode": episode, "algorithm": algorithm}
        row.update(metrics)
        lg.log(row)

    def log_constraint(self, episode: int, algorithm: str, metrics: dict):
        lg = self.get_logger("convergence_constraint_satisfaction")
        row = {"episode": episode, "algorithm": algorithm}
        row.update(metrics)
        lg.log(row)

    def log_scenario(self, filename: str, param_name: str,
                     param_val, algorithm: str, metrics: dict):
        """Log one data point for a scenario CSV."""
        # Build fieldnames on first access
        if filename not in self._loggers:
            algorithms = ["MAFAC", "Centralized-AoI", "SAC-Single",
                          "IQL", "NDN-LRU", "No-Cache"]
            metric_keys = list(metrics.keys())
            fields = [param_name, "algorithm"] + metric_keys
            fp = self.output_dir / f"{filename}.csv"
            self._loggers[filename] = CSVLogger(str(fp), fields, self._overwrite)
        lg = self._loggers[filename]
        row = {param_name: param_val, "algorithm": algorithm}
        row.update(metrics)
        lg.log(row)

    def log_overhead(self, round_num: int, algorithm: str, stats: dict):
        lg = self.get_logger("communication_overhead")
        row = {"round": round_num, "algorithm": algorithm}
        row.update(stats)
        lg.log(row)

    def log_theorem1(self, row: dict):
        lg = self.get_logger("model_verification_theorem1")
        lg.log(row)

    def log_theorem2(self, row: dict):
        lg = self.get_logger("model_verification_theorem2")
        lg.log(row)

    def log_ablation(self, row: dict):
        lg = self.get_logger("ablation_component_analysis")
        lg.log(row)

    def close_all(self):
        for lg in self._loggers.values():
            lg.close()
        self._loggers.clear()

    def __del__(self):
        self.close_all()
