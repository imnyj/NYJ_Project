# Handoff Report: HPO Hyperparameter Integration in run_all.py

## 1. 개요 및 구현 요약
- **대상 파일**: `/home/imnyj/Workspace/paper4/coder/run_all.py`
- **구현 목적**: HPO 최적 하이퍼파라미터 CSV 파일(`optuna_best_params.csv`)을 로드하여 9개 베이스라인 모델 훈련 시 모델별 최적 하이퍼파라미터를 `run_hot_swap_training`의 `hparams` 인자로 주입하도록 개선.
- **주요 변경 사항**:
  1. CLI 인자 `--hparams-csv` 추가 (기본값: `results/hpo/optuna_best_params.csv`).
  2. `load_hparams_from_csv` 함수 구현:
     - CSV 파일 내 `hparams_json` 컬럼 역직렬화.
     - 개별 컬럼 파라미터 병합 및 정수형(`hidden_dim`, `embed_dim`, `policy_freq` 등) 형변환.
     - 파일 미존재/파싱 실패 시 graceful fallback 및 WARNING 로깅.
  3. `get_hparams_for_model` 함수 구현:
     - 대소문자/하이픈/언더스코어 무관 정규화(`normalize_model_name`) 및 모델 별칭(Alias) 지원.
  4. 훈련 루프 내 `run_hot_swap_training(..., hparams=model_hparams)` 파라미터 전달.

## 2. 검증 기록 (Verification Record)
- **단위 및 통합 테스트 (`tests/test_run_all.py`)**: 9/9 PASSED
  1. `test_01_load_hparams_from_valid_csv`: 유효 CSV 로드 및 JSON 파싱, 정수형 캐스팅 검증.
  2. `test_02_load_hparams_missing_csv_file`: 파일 미존재 시 경고 로그 및 빈 딕셔너리 반환 검증.
  3. `test_03_load_hparams_none_or_empty_path`: None/빈 경로 방어 로직 검증.
  4. `test_04_load_hparams_malformed_json_fallback`: 손상된 JSON 문자열에 대한 컬럼 fallback 검증.
  5. `test_05_get_hparams_for_model_matching`: 정확한 매칭, 대소문자 무관 매칭, 미등록 모델 None 처리 검증.
  6. `test_06_cli_argument_parsing`: CLI 인자 파싱 및 기본값 검증.
  7. `test_07_run_all_with_custom_hparams_csv`: 커스텀 CSV 파일 지정 시 실제 PPO 훈련 실행 및 HPO 파라미터 적용 로그 확인.
  8. `test_08_run_all_with_missing_hparams_csv`: 존재하지 않는 CSV 파일 지정 시 크래시 없이 경고 출력 후 기본값 훈련 정상 완료 확인.
  9. `test_09_run_all_default_acceptance_criterion`: 수용 기준 명령어(`python run_all.py --episodes 1 --steps-per-episode 10 --models PPO`) 실행 성공 확인.

- **전체 회귀 테스트 (`pytest -v`)**: 119/119 PASSED (0 failures, 3 warnings)

## 3. 코드 변경 사항 (Diff)
```diff
--- a/Workspace/paper4/coder/run_all.py
+++ b/Workspace/paper4/coder/run_all.py
@@ -16,9 +16,13 @@
 from __future__ import annotations
 
 import argparse
+import json
 import logging
 import os
 import sys
+from typing import Any, Dict, Optional
+
+import pandas as pd
 
 sys.path.append(os.path.abspath(os.path.dirname(__file__)))
 
@@ -30,6 +34,109 @@
+def normalize_model_name(name: Any) -> str:
+    if not isinstance(name, str):
+        return getattr(name, "__name__", None) or type(name).__name__
+    clean = name.replace("-", "").replace("_", "").lower()
+    canonical_by_clean = {n.replace("-", "").replace("_", "").lower(): n for n in ALL_BASELINES}
+    return canonical_by_clean.get(clean, name)
+
+def load_hparams_from_csv(csv_path: Optional[str]) -> Dict[str, Dict[str, Any]]:
+    if not csv_path:
+        logging.warning("No HPO params CSV path provided; falling back to default hyperparameters.")
+        return {}
+    resolved_path = csv_path
+    if not os.path.exists(resolved_path) and not os.path.isabs(resolved_path):
+        base_dir = os.path.dirname(os.path.abspath(__file__))
+        candidate = os.path.join(base_dir, resolved_path)
+        if os.path.exists(candidate):
+            resolved_path = candidate
+    if not os.path.exists(resolved_path):
+        logging.warning("HPO params CSV %s not found; falling back to default hyperparameters.", csv_path)
+        return {}
+    try:
+        df = pd.read_csv(resolved_path)
+    except Exception as exc:
+        logging.warning("Failed to read HPO params CSV %s: %s; falling back to default hyperparameters.", resolved_path, exc)
+        return {}
+    hparams_by_model: Dict[str, Dict[str, Any]] = {}
+    for _, row in df.iterrows():
+        raw_name = str(row.get("model_name", "")).strip()
+        if not raw_name or raw_name.lower() == "nan":
+            continue
+        hparams: Dict[str, Any] = {}
+        if "hparams_json" in row and pd.notna(row["hparams_json"]):
+            val = row["hparams_json"]
+            if isinstance(val, dict):
+                hparams = dict(val)
+            elif isinstance(val, str):
+                try:
+                    parsed = json.loads(val)
+                    if isinstance(parsed, dict):
+                        hparams = parsed
+                except Exception as exc:
+                    logging.warning("Failed to parse hparams_json for model %s: %s", raw_name, exc)
+                    hparams = {}
+        for col in df.columns:
+            if col in ["model_name", "category", "best_value", "best_trial_number", "hparams_json", "reward_weights_json"]:
+                continue
+            val = row.get(col)
+            if pd.notna(val) and col not in hparams:
+                hparams[col] = val
+        int_keys = ("hidden_dim", "embed_dim", "policy_freq", "n_epochs", "policy_delay", "target_update_freq", "target_update_interval", "num_res_blocks", "n_step")
+        for k in int_keys:
+            if k in hparams and hparams[k] is not None:
+                try:
+                    hparams[k] = int(float(hparams[k]))
+                except (ValueError, TypeError):
+                    pass
+        canonical_name = normalize_model_name(raw_name)
+        hparams_by_model[canonical_name] = hparams
+        if raw_name != canonical_name:
+            hparams_by_model[raw_name] = hparams
+    logging.info("Successfully loaded HPO hyperparameters for %d model entry(ies) from %s", len(hparams_by_model), resolved_path)
+    return hparams_by_model
+
+def get_hparams_for_model(hparams_by_model: Dict[str, Dict[str, Any]], model_name: str) -> Optional[Dict[str, Any]]:
+    if not hparams_by_model:
+        return None
+    if model_name in hparams_by_model:
+        return hparams_by_model[model_name]
+    canonical_name = normalize_model_name(model_name)
+    if canonical_name in hparams_by_model:
+        return hparams_by_model[canonical_name]
+    clean = model_name.replace("-", "").replace("_", "").lower()
+    for k, v in hparams_by_model.items():
+        if k.replace("-", "").replace("_", "").lower() == clean:
+            return v
+    return None
```
