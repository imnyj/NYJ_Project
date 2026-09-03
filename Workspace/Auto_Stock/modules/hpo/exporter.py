"""
modules/hpo/exporter.py
=======================
Auto Stock ML/RL Trader — Milestone 3 & M4 Hardening: HPO Trial 결과 CSV 원자적 저장 및 내보내기 모듈.

주요 특징:
1. 20개 표준 컬럼 스키마 엄격 준수:
   - trial_id, state, objective_value, total_equity, total_return_pct, sharpe_ratio, max_drawdown_pct,
     total_trades, win_rate, param_sl_lr, param_sl_hidden_dim, param_sl_batch_size, param_rl_lr,
     param_rl_gamma, param_rl_clip_range, param_rl_ent_coef, param_rl_hidden_dim, duration_seconds,
     datetime_start, datetime_complete
2. etc/hpo_results/ 등 상위 디렉토리 자동 생성 보장.
3. 프로세스 레벨 파일 락(fcntl.flock) 및 스레드 락(threading.Lock)을 결합하여 멀티프로세스 / 멀티스레드 동시 실행 시
   Read-Modify-Write 경쟁 상태 및 데이터 유실(Lost Update)을 원천 방지.
4. Optuna Trial 단일/복수 객체 및 Study 전체에 대한 CSV 내보내기(export_trial_to_csv, export_study_to_csv) 완벽 지원.
"""

import contextlib
import csv
import datetime
import fcntl
import json
import os
import threading
from typing import Any, Dict, Iterator, List, Optional, Union

import pandas as pd

# 20개 표준 컬럼 명세
CSV_COLUMNS = [
    "trial_id",
    "state",
    "objective_value",
    "total_equity",
    "total_return_pct",
    "sharpe_ratio",
    "max_drawdown_pct",
    "total_trades",
    "win_rate",
    "param_sl_lr",
    "param_sl_hidden_dim",
    "param_sl_batch_size",
    "param_rl_lr",
    "param_rl_gamma",
    "param_rl_clip_range",
    "param_rl_ent_coef",
    "param_rl_hidden_dim",
    "duration_seconds",
    "datetime_start",
    "datetime_complete",
]

# Phase 6: 메인 모델(ResNet, Transformer, CVAE) 통합 확장 컬럼 명세
MAIN_MODELS_CSV_COLUMNS = [
    "trial_id",
    "model_type",
    "state",
    "objective_value",
    "total_equity",
    "total_return_pct",
    "sharpe_ratio",
    "max_drawdown_pct",
    "total_trades",
    "win_rate",
    # 공통 학습 및 RL 파라미터
    "param_sl_lr",
    "param_sl_dropout",
    "param_rl_lr",
    "param_rl_gamma",
    "param_rl_clip_range",
    "param_rl_ent_coef",
    "param_rl_hidden_dim",
    "param_batch_size",
    # ResNet 전용 파라미터
    "param_res_blocks",
    "param_res_filters",
    "param_res_kernel_size",
    "param_resnet_num_blocks",
    "param_resnet_filters",
    "param_resnet_kernel_size",
    "param_resnet_dropout",
    # Transformer 전용 파라미터
    "param_tf_d_model",
    "param_tf_nhead",
    "param_tf_layers",
    "param_tf_num_layers",
    "param_tf_dim_feedforward",
    "param_tf_dropout",
    # CVAE 전용 파라미터
    "param_cvae_latent_dim",
    "param_cvae_hidden_dim",
    "param_cvae_kl_weight",
    "param_cvae_dropout",
    # 메타데이터 및 전체 파라미터 JSON 백업
    "params_json",
    "duration_seconds",
    "datetime_start",
    "datetime_complete",
]

_FILE_WRITE_LOCK = threading.Lock()


@contextlib.contextmanager
def _process_file_lock(csv_abs_path: str, shared: bool = False) -> Iterator[None]:
    """
    프로세스 및 스레드 간 상호 배제를 보장하는 fcntl 기반 파일 락 컨텍스트 매니저.

    - 단일 프로세스 내 스레드 간 경쟁은 threading.Lock으로 보호.
    - 다중 독립 프로세스 간 동시 쓰기/읽기 경쟁은 fcntl.flock(LOCK_EX / LOCK_SH)으로 보호.
    """
    lock_path = f"{csv_abs_path}.lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)

    with _FILE_WRITE_LOCK:
        lock_fd = open(lock_path, "a")
        lock_mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        try:
            fcntl.flock(lock_fd.fileno(), lock_mode)
            try:
                yield
            finally:
                try:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            try:
                lock_fd.close()
            except OSError:
                pass


def _sanitize_trial_record(raw_record: Dict[str, Any], trial_id: Optional[int] = None) -> Dict[str, Any]:
    """
    임의의 딕셔너리 또는 Trial 객체로부터 20개 표준 컬럼에 맞추어 기본값을 보정하고 정제합니다.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # trial_id 추출
    tid = raw_record.get("trial_id", trial_id if trial_id is not None else 0)
    try:
        tid = int(tid)
    except Exception:
        tid = 0

    state = str(raw_record.get("state", "COMPLETE")).upper()

    def _get_float(key: str, default: float = 0.0) -> float:
        val = raw_record.get(key, default)
        try:
            f = float(val)
            return default if pd.isna(f) else f
        except Exception:
            return default

    def _get_int(key: str, default: int = 0) -> int:
        val = raw_record.get(key, default)
        try:
            return int(val)
        except Exception:
            return default

    # 파라미터 접두사 'param_' 또는 접두사 없는 키 모두 지원
    sl_lr = _get_float("param_sl_lr", _get_float("sl_lr", 0.001))
    sl_hidden_dim = _get_int("param_sl_hidden_dim", _get_int("sl_hidden_dim", 64))
    sl_batch_size = _get_int("param_sl_batch_size", _get_int("sl_batch_size", 32))

    rl_lr = _get_float("param_rl_lr", _get_float("rl_lr", 0.0003))
    rl_gamma = _get_float("param_rl_gamma", _get_float("rl_gamma", 0.99))
    rl_clip_range = _get_float("param_rl_clip_range", _get_float("rl_clip_range", 0.2))
    rl_ent_coef = _get_float("param_rl_ent_coef", _get_float("rl_ent_coef", 0.01))
    rl_hidden_dim = _get_int("param_rl_hidden_dim", _get_int("rl_hidden_dim", 128))

    dt_start = raw_record.get("datetime_start", now_iso)
    dt_complete = raw_record.get("datetime_complete", now_iso)

    record: Dict[str, Any] = {
        "trial_id": tid,
        "state": state,
        "objective_value": round(_get_float("objective_value", _get_float("value", 0.0)), 6),
        "total_equity": round(_get_float("total_equity", 10_000_000.0), 2),
        "total_return_pct": round(_get_float("total_return_pct", 0.0), 4),
        "sharpe_ratio": round(_get_float("sharpe_ratio", 0.0), 4),
        "max_drawdown_pct": round(_get_float("max_drawdown_pct", 0.0), 4),
        "total_trades": _get_int("total_trades", 0),
        "win_rate": round(_get_float("win_rate", 0.0), 2),
        "param_sl_lr": sl_lr,
        "param_sl_hidden_dim": sl_hidden_dim,
        "param_sl_batch_size": sl_batch_size,
        "param_rl_lr": rl_lr,
        "param_rl_gamma": rl_gamma,
        "param_rl_clip_range": rl_clip_range,
        "param_rl_ent_coef": rl_ent_coef,
        "param_rl_hidden_dim": rl_hidden_dim,
        "duration_seconds": round(_get_float("duration_seconds", 0.0), 4),
        "datetime_start": str(dt_start),
        "datetime_complete": str(dt_complete),
    }
    return record


def _extract_records(
    trial_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame, Any],
) -> List[Dict[str, Any]]:
    """
    다양한 형태(DataFrame, list, dict, Optuna FrozenTrial, Optuna Study)의 입력을 정규화된 딕셔너리 리스트로 변환합니다.
    """
    records_to_write: List[Dict[str, Any]] = []

    if isinstance(trial_data, pd.DataFrame):
        for idx, row in trial_data.iterrows():
            records_to_write.append(_sanitize_trial_record(row.to_dict(), trial_id=idx))
    elif isinstance(trial_data, list):
        for idx, item in enumerate(trial_data):
            if isinstance(item, dict):
                records_to_write.append(_sanitize_trial_record(item, trial_id=idx))
            elif hasattr(item, "params"):  # Optuna FrozenTrial
                rec = {
                    "trial_id": getattr(item, "number", idx),
                    "state": (
                        getattr(item, "state", "COMPLETE").name
                        if hasattr(getattr(item, "state", None), "name")
                        else str(getattr(item, "state", "COMPLETE"))
                    ),
                    "objective_value": getattr(item, "value", 0.0) or 0.0,
                    **getattr(item, "params", {}),
                    **getattr(item, "user_attrs", {}),
                }
                records_to_write.append(_sanitize_trial_record(rec, trial_id=idx))
            else:
                records_to_write.append(_sanitize_trial_record({}, trial_id=idx))
    elif isinstance(trial_data, dict):
        records_to_write.append(_sanitize_trial_record(trial_data))
    elif hasattr(trial_data, "params"):  # Optuna FrozenTrial
        rec = {
            "trial_id": getattr(trial_data, "number", 0),
            "state": (
                getattr(trial_data, "state", "COMPLETE").name
                if hasattr(getattr(trial_data, "state", None), "name")
                else str(getattr(trial_data, "state", "COMPLETE"))
            ),
            "objective_value": getattr(trial_data, "value", 0.0) or 0.0,
            **getattr(trial_data, "params", {}),
            **getattr(trial_data, "user_attrs", {}),
        }
        records_to_write.append(_sanitize_trial_record(rec))
    elif hasattr(trial_data, "trials") or (
        hasattr(trial_data, "get_trials") and callable(getattr(trial_data, "get_trials", None))
    ):  # Optuna Study
        trials = getattr(trial_data, "trials", None)
        if trials is None and callable(getattr(trial_data, "get_trials", None)):
            trials = trial_data.get_trials()
        if trials:
            for idx, item in enumerate(trials):
                rec = {
                    "trial_id": getattr(item, "number", idx),
                    "state": (
                        getattr(item, "state", "COMPLETE").name
                        if hasattr(getattr(item, "state", None), "name")
                        else str(getattr(item, "state", "COMPLETE"))
                    ),
                    "objective_value": getattr(item, "value", 0.0) or 0.0,
                    **getattr(item, "params", {}),
                    **getattr(item, "user_attrs", {}),
                }
                records_to_write.append(_sanitize_trial_record(rec, trial_id=idx))
    else:
        # Generic object fallback
        records_to_write.append(_sanitize_trial_record({}))

    return records_to_write


def export_trial_to_csv(
    trial_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame, Any],
    csv_path: str = "etc/hpo_results/baseline_hpo.csv",
) -> str:
    """
    단일 또는 복수의 HPO Trial 레코드를 지정된 CSV 파일에 원자적으로 추가(Append) 또는 기록합니다.
    fcntl 기반 프로세스 레벨 파일 락을 적용하여 멀티프로세스 환경에서도 Read-Modify-Write 경쟁 상태 및
    데이터 유실(Lost Update)이 원천 방지됩니다.

    Args:
        trial_data: Trial 데이터 딕셔너리, 딕셔너리 리스트, DataFrame 또는 Optuna Trial 객체
        csv_path: 저장할 대상 CSV 파일 경로 (기본값: 'etc/hpo_results/baseline_hpo.csv')

    Returns:
        saved_path: str 실제 저장된 절대 경로
    """
    abs_path = os.path.abspath(csv_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    records_to_write = _extract_records(trial_data)

    # 프로세스 파일 락 획득 후 원자적 쓰기/추가 수행
    with _process_file_lock(abs_path, shared=False):
        file_exists = os.path.exists(abs_path) and os.path.getsize(abs_path) > 0

        with open(abs_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()
            for rec in records_to_write:
                writer.writerow({k: rec.get(k, "") for k in CSV_COLUMNS})
            f.flush()
            os.fsync(f.fileno())

    return abs_path


def export_study_to_csv(
    study: Any,
    csv_path: str = "etc/hpo_results/baseline_hpo.csv",
    overwrite: bool = False,
) -> str:
    """
    Optuna Study 객체(또는 Study 내 trials 목록)의 모든 결과를 CSV 파일로 프로세스/스레드 안전하게 내보냅니다.

    Args:
        study: Optuna Study 인스턴스 또는 Trial 목록
        csv_path: 저장 대상 CSV 파일 경로 (기본값: 'etc/hpo_results/baseline_hpo.csv')
        overwrite: True일 경우 기존 파일을 새로 덮어쓰고, False일 경우 기존 파일에 추가(Append)합니다.

    Returns:
        saved_path: str 실제 저장된 절대 경로
    """
    abs_path = os.path.abspath(csv_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    trials = getattr(study, "trials", None)
    if trials is None and callable(getattr(study, "get_trials", None)):
        trials = study.get_trials()
    if trials is None:
        if isinstance(study, (list, pd.DataFrame, dict)):
            trials = study
        else:
            trials = [study]

    records_to_write = _extract_records(trials)

    with _process_file_lock(abs_path, shared=False):
        mode = "w" if overwrite else "a"
        file_exists = os.path.exists(abs_path) and os.path.getsize(abs_path) > 0 and not overwrite

        with open(abs_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()
            for rec in records_to_write:
                writer.writerow({k: rec.get(k, "") for k in CSV_COLUMNS})
            f.flush()
            os.fsync(f.fileno())

    return abs_path


def load_hpo_results(csv_path: str = "etc/hpo_results/baseline_hpo.csv") -> pd.DataFrame:
    """
    저장된 HPO 결과 CSV를 판다스 DataFrame으로 로드하고 컬럼 무결성을 검증합니다.
    읽기 시에도 프로세스 락(Shared Lock)을 획득하여 동시 쓰기 중인 미완성 데이터를 읽지 않도록 보장합니다.

    Args:
        csv_path: CSV 파일 경로

    Returns:
        df: pd.DataFrame (20개 컬럼 스키마 보장)
    """
    abs_path = os.path.abspath(csv_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"HPO 결과 CSV 파일을 찾을 수 없습니다: {abs_path}")

    with _process_file_lock(abs_path, shared=True):
        df = pd.read_csv(abs_path)

    missing = [col for col in CSV_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV에 누락된 필수 컬럼이 있습니다: {missing}")

    return df[CSV_COLUMNS]


def _sanitize_main_model_record(
    trial: Any,
    metrics: Optional[Dict[str, Any]] = None,
    model_type: str = "resnet",
) -> Dict[str, Any]:
    """
    Optuna Trial 또는 딕셔너리로부터 MAIN_MODELS_CSV_COLUMNS 명세에 맞추어 기본값을 보정하고 정제합니다.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metrics = dict(metrics) if metrics else {}

    # 1. trial_id 추출
    if hasattr(trial, "number"):
        tid = getattr(trial, "number")
    elif isinstance(trial, dict):
        tid = trial.get("trial_id", trial.get("number", metrics.get("trial_id", 0)))
    elif isinstance(trial, (int, float)):
        tid = int(trial)
    else:
        tid = metrics.get("trial_id", 0)
    try:
        tid = int(tid)
    except Exception:
        tid = 0

    # 2. state 추출
    if hasattr(trial, "state"):
        st = getattr(trial, "state")
        state_str = st.name if hasattr(st, "name") else str(st)
    elif isinstance(trial, dict):
        state_str = str(trial.get("state", metrics.get("state", "COMPLETE")))
    else:
        state_str = str(metrics.get("state", "COMPLETE"))
    state_str = state_str.upper()

    # 3. params 및 user_attrs 추출
    params: Dict[str, Any] = {}
    user_attrs: Dict[str, Any] = {}
    if hasattr(trial, "params") and isinstance(trial.params, dict):
        params.update(trial.params)
    if hasattr(trial, "user_attrs") and isinstance(trial.user_attrs, dict):
        user_attrs.update(trial.user_attrs)
    if isinstance(trial, dict):
        for k, v in trial.items():
            if k.startswith("param_"):
                clean_k = k[6:]
                params[clean_k] = v
            elif k in (
                "sl_lr", "sl_dropout", "rl_lr", "rl_gamma", "rl_clip_range", "rl_ent_coef",
                "rl_hidden_dim", "batch_size", "res_blocks", "res_filters", "res_kernel_size",
                "resnet_num_blocks", "resnet_filters", "resnet_kernel_size", "resnet_dropout",
                "tf_d_model", "tf_nhead", "tf_layers", "tf_num_layers", "tf_dim_feedforward",
                "tf_dropout", "cvae_latent_dim", "cvae_hidden_dim", "cvae_kl_weight", "cvae_dropout"
            ):
                params[k] = v
            elif k not in (
                "trial_id", "state", "objective_value", "total_equity", "total_return_pct",
                "sharpe_ratio", "max_drawdown_pct", "total_trades", "win_rate",
                "duration_seconds", "datetime_start", "datetime_complete", "model_type"
            ):
                user_attrs[k] = v

    # 4. metrics 병합
    combined_metrics = dict(user_attrs)
    combined_metrics.update(metrics)
    if isinstance(trial, dict):
        for k in (
            "objective_value", "total_equity", "total_return_pct", "sharpe_ratio",
            "max_drawdown_pct", "total_trades", "win_rate", "duration_seconds"
        ):
            if k in trial and k not in combined_metrics:
                combined_metrics[k] = trial[k]

    def _get_float(key: str, default: float = 0.0) -> float:
        v = combined_metrics.get(key, default)
        try:
            f = float(v)
            return default if pd.isna(f) else f
        except Exception:
            return default

    def _get_int(key: str, default: int = 0) -> int:
        v = combined_metrics.get(key, default)
        try:
            return int(v)
        except Exception:
            return default

    def _param_val(k1: str, k2: Optional[str] = None, default: Any = "") -> Any:
        if k1 in params:
            return params[k1]
        if f"param_{k1}" in params:
            return params[f"param_{k1}"]
        if k2 and k2 in params:
            return params[k2]
        if k2 and f"param_{k2}" in params:
            return params[f"param_{k2}"]
        return default

    m_type = str(combined_metrics.get("model_type", model_type)).lower().strip()

    sl_lr = _param_val("sl_lr", default="")
    sl_dropout = _param_val("sl_dropout", default="")
    rl_lr = _param_val("rl_lr", default="")
    rl_gamma = _param_val("rl_gamma", default="")
    rl_clip_range = _param_val("rl_clip_range", default="")
    rl_ent_coef = _param_val("rl_ent_coef", default="")
    rl_hidden_dim = _param_val("rl_hidden_dim", default="")
    batch_size = _param_val("batch_size", default="")

    res_blocks = _param_val("res_blocks", "resnet_num_blocks", default="")
    res_filters = _param_val("res_filters", "resnet_filters", default="")
    res_kernel_size = _param_val("res_kernel_size", "resnet_kernel_size", default="")
    resnet_dropout = _param_val("resnet_dropout", "sl_dropout", default="")

    tf_d_model = _param_val("tf_d_model", default="")
    tf_nhead = _param_val("tf_nhead", default="")
    tf_layers = _param_val("tf_layers", "tf_num_layers", default="")
    tf_dim_feedforward = _param_val("tf_dim_feedforward", default="")
    tf_dropout = _param_val("tf_dropout", "sl_dropout", default="")

    cvae_latent_dim = _param_val("cvae_latent_dim", default="")
    cvae_hidden_dim = _param_val("cvae_hidden_dim", default="")
    cvae_kl_weight = _param_val("cvae_kl_weight", default="")
    cvae_dropout = _param_val("cvae_dropout", "sl_dropout", default="")

    dt_start = str(combined_metrics.get("datetime_start", now_iso))
    dt_complete = str(combined_metrics.get("datetime_complete", now_iso))
    dur = round(_get_float("duration_seconds", 0.0), 4)

    # Convert all params to JSON string
    try:
        clean_params = {}
        for k, v in params.items():
            if isinstance(v, (int, float, str, bool, list, dict)) or v is None:
                clean_params[k] = v
            else:
                clean_params[k] = str(v)
        params_json = json.dumps(clean_params, ensure_ascii=False, sort_keys=True)
    except Exception:
        params_json = "{}"

    # Determine objective value
    if hasattr(trial, "value") and trial.value is not None:
        obj_val = float(trial.value)
    else:
        obj_val = _get_float("objective_value", _get_float("value", 0.0))

    record: Dict[str, Any] = {
        "trial_id": tid,
        "model_type": m_type,
        "state": state_str,
        "objective_value": round(obj_val, 6),
        "total_equity": round(_get_float("total_equity", 10_000_000.0), 2),
        "total_return_pct": round(_get_float("total_return_pct", 0.0), 4),
        "sharpe_ratio": round(_get_float("sharpe_ratio", 0.0), 4),
        "max_drawdown_pct": round(_get_float("max_drawdown_pct", 0.0), 4),
        "total_trades": _get_int("total_trades", 0),
        "win_rate": round(_get_float("win_rate", 0.0), 2),
        # Common params
        "param_sl_lr": sl_lr,
        "param_sl_dropout": sl_dropout,
        "param_rl_lr": rl_lr,
        "param_rl_gamma": rl_gamma,
        "param_rl_clip_range": rl_clip_range,
        "param_rl_ent_coef": rl_ent_coef,
        "param_rl_hidden_dim": rl_hidden_dim,
        "param_batch_size": batch_size,
        # ResNet
        "param_res_blocks": res_blocks,
        "param_res_filters": res_filters,
        "param_res_kernel_size": res_kernel_size,
        "param_resnet_num_blocks": res_blocks,
        "param_resnet_filters": res_filters,
        "param_resnet_kernel_size": res_kernel_size,
        "param_resnet_dropout": resnet_dropout if "resnet" in m_type else "",
        # Transformer
        "param_tf_d_model": tf_d_model,
        "param_tf_nhead": tf_nhead,
        "param_tf_layers": tf_layers,
        "param_tf_num_layers": tf_layers,
        "param_tf_dim_feedforward": tf_dim_feedforward,
        "param_tf_dropout": tf_dropout if "transformer" in m_type else "",
        # CVAE
        "param_cvae_latent_dim": cvae_latent_dim,
        "param_cvae_hidden_dim": cvae_hidden_dim,
        "param_cvae_kl_weight": cvae_kl_weight,
        "param_cvae_dropout": cvae_dropout if "cvae" in m_type else "",
        # Meta
        "params_json": params_json,
        "duration_seconds": dur,
        "datetime_start": dt_start,
        "datetime_complete": dt_complete,
    }
    return record


def export_main_model_trial_to_csv(
    trial: Any,
    metrics: Optional[Dict[str, Any]] = None,
    model_type: str = "resnet",
    filepath: str = "etc/hpo_results/main_models_hpo.csv",
) -> str:
    """
    ResNet, Transformer, CVAE 메인 모델의 Trial 결과를 CSV 파일에 원자적으로 추가(Append)합니다.
    fcntl 기반 프로세스 레벨 파일 락과 threading.Lock을 결합하여 멀티프로세스 환경에서도
    동시 쓰기 경쟁 상태 및 데이터 유실을 원천 차단합니다.

    Args:
        trial: Optuna Trial 객체, FrozenTrial, 또는 dict
        metrics: 산출된 금융 및 운영 지표 딕셔너리
        model_type: 모델 유형 ('resnet', 'transformer', 'cvae')
        filepath: 대상 CSV 파일 경로 (기본값: 'etc/hpo_results/main_models_hpo.csv')

    Returns:
        saved_path: str 실제 저장된 절대 경로
    """
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    record = _sanitize_main_model_record(trial=trial, metrics=metrics, model_type=model_type)

    with _process_file_lock(abs_path, shared=False):
        file_exists = os.path.exists(abs_path) and os.path.getsize(abs_path) > 0

        with open(abs_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MAIN_MODELS_CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow({k: record.get(k, "") for k in MAIN_MODELS_CSV_COLUMNS})
            f.flush()
            os.fsync(f.fileno())

    return abs_path


def load_main_models_hpo_results(
    csv_path: str = "etc/hpo_results/main_models_hpo.csv",
) -> pd.DataFrame:
    """
    main_models_hpo.csv 파일을 Shared Lock(LOCK_SH)으로 안전하게 읽고 반환합니다.

    Args:
        csv_path: CSV 파일 경로 (기본값: 'etc/hpo_results/main_models_hpo.csv')

    Returns:
        df: pd.DataFrame
    """
    abs_path = os.path.abspath(csv_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"메인 모델 HPO 결과 CSV 파일을 찾을 수 없습니다: {abs_path}")

    with _process_file_lock(abs_path, shared=True):
        df = pd.read_csv(abs_path)

    return df


__all__ = [
    "CSV_COLUMNS",
    "MAIN_MODELS_CSV_COLUMNS",
    "export_trial_to_csv",
    "export_study_to_csv",
    "load_hpo_results",
    "export_main_model_trial_to_csv",
    "load_main_models_hpo_results",
]
