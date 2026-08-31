# Reviewer Round 1 Handoff Report

## 1. 독립적 요구사항 분석 및 Prior Attempt 평가
- **목표**: `run_all.py`에 `--hparams-csv` 옵션을 추가하여 HPO CSV 파일(`results/hpo/optuna_best_params.csv`)로부터 최적 하이퍼파라미터(`hparams_json` 등)를 추출하고, 9개 베이스라인 모델 훈련(`run_hot_swap_training(..., hparams=model_hparams)`)에 안전하게 주입하며, 파일 누락/미등록 시 graceful fallback 보장.
- **Prior Attempt 검토 결과**:
  - 기본적인 R1, R2 인터페이스와 테스트는 구현되었으나, 다음과 같은 취약점 및 결함이 발견됨.

---

## 2. 발견된 문제점 및 결함 분석 (Input → Expected → Actual → Root Cause)

### 1) CLI 소문자 모델명 입력 시 KeyError 비정상 종료
- **Input**: `python run_all.py --episodes 1 --steps-per-episode 10 --models ppo`
- **Expected**: `normalize_model_name("ppo")`를 통해 `"PPO"`로 정규화되어 정상 훈련 진행.
- **Actual**: `KeyError: "Unknown baseline 'ppo'"` 발생 및 훈련 실패 종료 (종료 코드 1).
- **Root Cause**: `run_all.py`의 `main()` 루프에서 `get_baseline(name)`을 호출할 때 모델명 정규화(`normalize_model_name`)를 거치지 않고 원본 CLI 문자열을 그대로 전달함.

### 2) 기본 HPO CSV 내 신규 9종 베이스라인 미동기화로 인한 상시 Fallback 발생
- **Input**: `python run_all.py --episodes 1 --steps-per-episode 10 --models PPO` (기본 CSV 사용)
- **Expected**: 기본 HPO CSV(`results/hpo/optuna_best_params.csv`)로부터 PPO의 최적 하이퍼파라미터를 로드하여 적용.
- **Actual**: `WARNING: No HPO parameters found for PPO in 'results/hpo/optuna_best_params.csv'; falling back to default hyperparameters.` 경고와 함께 기본값 fallback.
- **Root Cause**: `results/hpo/optuna_best_params.csv` 파일이 2026-08-28 베이스라인 교체 이전의 구형 모델명(`HybridPPO`, `HybridSAC`, etc.)으로 남아있어 신규 9종 모델명(`PPO`, `SAC`, `TD3`, `RES-MAPDDPG`, `MA2HDQN`, `I-HAMAPPO`, `SPAM-D3QN`, `CARLTON`, `MADDPG-MT`)과 불일치함.

### 3) 레거시 모델명 매핑 및 정수형 하이퍼파라미터 캐스팅 범위 제한
- **Input**: 레거시 CSV에서 `HybridPPO` 로드 또는 `num_delta_levels`, `target_sync_interval` 등의 정수형 파라미터가 실수형(`8.0`, `200.0`)으로 전달될 때.
- **Expected**: `PPO`로 매핑되고 정수형으로 완벽하게 캐스팅되어 PyTorch 레이어 및 모델 생성자에 정수형 전달.
- **Actual**: 일부 신규 베이스라인 전용 정수 키(`num_delta_levels`, `num_power_levels`, `target_sync_interval`, `policy_sync_interval`, `ctx_dim`, `max_agents`, `num_tasks`, `rollout_n_steps`)가 float로 유지될 위험 존재.
- **Root Cause**: `int_keys` 튜플에 일부 베이스라인 모델 인자가 누락되어 있었음.

---

## 3. 수정 사항 (What I Changed)

1. **`run_all.py`**:
   - `normalize_model_name()` 개선:
     - 객체/클래스/문자열 모두 지원.
     - `HybridPPO -> PPO`, `HybridSAC -> SAC`, `HybridTD3 -> TD3` 레거시 별칭 맵 추가.
     - 하이픈/언더스코어/대소문자 무관 정규화.
   - `load_hparams_from_csv()` 보강:
     - `int_keys`를 17종 전체 모델 정수 파라미터로 확장 (`hidden_dim`, `embed_dim`, `policy_freq`, `n_epochs`, `policy_delay`, `target_update_freq`, `target_update_interval`, `target_sync_interval`, `policy_sync_interval`, `num_res_blocks`, `n_step`, `num_delta_levels`, `num_power_levels`, `ctx_dim`, `max_agents`, `num_tasks`, `rollout_n_steps`).
     - 빈 파일/결측 파일/손상 JSON에 대한 안전한 예외 처리 및 로깅.
   - `main()` 루프 개선:
     - `get_baseline(canonical_name)` 호출 전 `canonical_name = normalize_model_name(raw_name)` 선행 적용.
     - 실패 목록 및 로깅 메시지 명확화.

2. **`results/hpo/optuna_best_params.csv`**:
   - `src/hpo.py`의 정규 HPO 파이프라인을 실행하여 9개 베이스라인 전 기종(`PPO`, `SAC`, `TD3`, `RES-MAPDDPG`, `MA2HDQN`, `I-HAMAPPO`, `SPAM-D3QN`, `CARLTON`, `MADDPG-MT`)의 최적 파라미터 및 `hparams_json`, `reward_weights_json` 정합성 완비.

3. **`tests/test_run_all.py`**:
   - 테스트 케이스를 9개에서 12개로 확장:
     - `test_01_load_hparams_from_valid_csv`: 유효 CSV 로드 및 다중 정수 캐스팅 검증
     - `test_02_load_hparams_missing_csv_file`: 파일 누락 시 경고 및 빈 dict 반환 검증
     - `test_03_load_hparams_none_or_empty_path`: None 및 빈 문자열 경로 안전성 검증
     - `test_04_load_hparams_empty_csv_file`: 0바이트 빈 CSV 파일 안전성 검증
     - `test_05_load_hparams_malformed_json_fallback`: JSON 손상 시 컬럼 기반 fallback 검증
     - `test_06_model_name_normalization_and_legacy_aliases`: 소문자/특수문자/레거시 별칭 정규화 검증
     - `test_07_get_hparams_for_model_matching`: 대소문자 무관 매칭 및 alias fallback 검증
     - `test_08_cli_argument_parsing`: CLI 파라미터 파싱 검증
     - `test_09_run_all_with_custom_hparams_csv`: 커스텀 CSV 서브프로세스 훈련 실행 검증
     - `test_10_run_all_with_missing_hparams_csv`: 누락 CSV 서브프로세스 graceful fallback 검증
     - `test_11_run_all_with_lowercase_model_cli`: 소문자 CLI 모델명 서브프로세스 훈련 성공 검증
     - `test_12_run_all_default_acceptance_criterion`: 기본 수용 기준 단독 실행 검증

4. **`logs/execution_notes.md`**:
   - GEMINI.md Rule 13에 따른 실행 및 자가 개선 세션 로그 3줄 추가.

---

## 4. 검증 결과 (Verification Record)

- **단위 및 통합 테스트**:
  - `pytest tests/test_run_all.py -v`: 12/12 PASSED (18.40s)
  - `pytest -v` (전체 테스트 스위트): **122/122 PASSED** (0 failed, 3 warnings in 44.85s)
- **실제 CLI 서브프로세스 실행 검증**:
  - `python run_all.py --episodes 1 --steps-per-episode 10 --models PPO` → 정상 실행 (종료 코드 0, HPO 최적 파라미터 로드 적용 완료)
  - `python run_all.py --episodes 1 --steps-per-episode 10 --models ppo` → 정상 실행 (종료 코드 0, 소문자 모델명 정규화 정상 작동)
  - `python run_all.py --episodes 1 --steps-per-episode 10 --models PPO --hparams-csv /tmp/missing.csv` → 정상 실행 (종료 코드 0, graceful fallback 경고 로깅 후 완료)
  - `python run_all.py --episodes 1 --steps-per-episode 10 --models SAC TD3 RES-MAPDDPG MA2HDQN I-HAMAPPO SPAM-D3QN CARLTON MADDPG-MT --no-resume` → **8개 모델 전체 HPO 파라미터 적용 및 훈련 성공 (종료 코드 0)**
