# Reviewer Round 2 Handoff Report

## 1. 독립적 요구사항 분석 및 Prior Attempt 평가
- **목표**: `run_all.py`에 `--hparams-csv` 옵션을 추가하여 HPO CSV 파일(`results/hpo/optuna_best_params.csv`)로부터 최적 하이퍼파라미터(`hparams_json` 등)를 추출하고, 9개 베이스라인 모델 훈련(`run_hot_swap_training(..., hparams=model_hparams)`)에 안전하게 주입하며, 파일 누락/미등록 시 graceful fallback 보장.
- **Round 2 심층 적대적 검토 영역**:
  1. CSV 내 NaN / Inf / None / "NaN" 결측 및 비정상 수치 주입 시 모델 초기화 붕괴 가능성.
  2. Optuna Raw Trial CSV 또는 중복 모델 행이 포함된 다중 시도 CSV 입력 시 최고 성능 트라이얼 자동 선별 여부.
  3. `reward_weights_json` 및 Optuna `params_*` 접두사 컬럼의 안전한 파싱 및 병합.
  4. 틸드(`~`) 경로 및 공백 포함 경로 해석 안정성.
  5. 불리언(`use_target_network` 등) 및 17종 정수형 파라미터의 정밀 캐스팅.

---

## 2. 발견된 문제점 및 결함 분석 (Input → Expected → Actual → Root Cause)

### 1) NaN / Inf / None 하이퍼파라미터로 인한 모델 초기화 및 PyTorch 레이어 붕괴
- **Input**: CSV 내 `hparams_json`에 `{"clip_range": NaN, "gamma": null, "n_epochs": "NaN"}` 등이 포함되어 전달될 때.
- **Expected**: 손상되거나 결측된 파라미터는 제거(Sanitize)되어 모델 생성자의 기본값(Default)으로 안전하게 대체.
- **Actual**: `int(float('nan'))`에서 ValueError가 발생하여 캐스팅이 실패하고, 원본 NaN / None이 모델(`PPO`, `CARLTON` 등)에 전달되어 `nn.Linear` 생성자 TypeError 또는 PyTorch 훈련 도중 손실 발산/NaN 가중치 오염 위험 발생.
- **Root Cause**: `load_hparams_from_csv`에서 값의 유효성 검사(`_is_valid_hparam_value`) 없이 JSON 딕셔너리를 그대로 모델 kwargs로 전달함.

### 2) Optuna Multi-Trial CSV 및 중복 모델 행 입력 시 비최적 파라미터 덮어쓰기 위험
- **Input**: 다수의 트라이얼이 기록된 CSV(예: `optuna_trials_PPO.csv` 또는 중복 모델 행이 있는 커스텀 CSV)를 `--hparams-csv`로 지정.
- **Expected**: 목적함수 값(`value`, `best_value`, `score`, `reward` 등)이 가장 높은 최고 성능 트라이얼의 하이퍼파라미터가 자동으로 선택됨.
- **Actual**: CSV의 마지막 행에 위치한 트라이얼(성능이 낮거나 조기 종료된 시도)이 이전의 최고 성능 트라이얼을 덮어씀.
- **Root Cause**: 중복 모델 행 처리 시 스코어 비교 로직 없이 순차적으로 딕셔너리에 덮어쓰기만 수행함.

### 3) 사용자 홈 디렉토리 틸드(`~`) 및 공백 경로 파싱 실패
- **Input**: `--hparams-csv ~/Workspace/paper4/coder/results/hpo/optuna_best_params.csv`
- **Expected**: 틸드가 사용자 홈 디렉토리로 확장되어 정상 파일 인식 및 로드.
- **Actual**: `os.path.exists('~/...')`가 False를 반환하여 파일을 찾지 못하고 경고 로깅 후 기본값 fallback.
- **Root Cause**: `os.path.expanduser()` 호출 누락.

---

## 3. 수정 사항 (What I Changed)

1. **`run_all.py`**:
   - `_is_valid_hparam_value()` 함수 추가: `NaN`, `Inf`, `-Inf`, `None`, `"nan"`, `"null"`, `"none"` 등 비정상 값을 완벽 차단하고 필터링.
   - `_cast_hparam_value()` 함수 추가: 17종 정수형 키 및 `BOOL_HPARAM_KEYS`(`use_target_network`, `normalize_advantage`, `deterministic`)에 대한 정확한 타입 캐스팅 수행.
   - `load_hparams_from_csv()` 대폭 고도화:
     - `os.path.expanduser()` 및 `strip()` 적용으로 틸드/공백 경로 지원.
     - `reward_weights_json` 파싱 및 `w1..w4` 안전 병합.
     - Optuna `params_*` 접두사 컬럼 자동 정규화 및 수용.
     - `best_value`, `value`, `score`, `reward` 컬럼 기반 중복 모델 행 최적 스코어 선별 알고리즘 탑재.
   - `get_hparams_for_model()` 개선: 클래스 객체, 공백 포함 문자열, 정규화 별칭 전면 지원.

2. **`tests/test_run_all.py`**:
   - 기존 12개 테스트에 이어 적대적/엣지 케이스 테스트 8개(Test 13~20) 추가 (총 20개 테스트):
     - `test_13_load_hparams_nan_inf_none_sanitization`
     - `test_14_load_hparams_duplicate_models_highest_score_selection`
     - `test_15_load_hparams_reward_weights_merging`
     - `test_16_load_hparams_params_prefix_columns`
     - `test_17_load_hparams_user_path_expansion_and_spaces`
     - `test_18_load_hparams_boolean_and_integer_casting`
     - `test_19_load_hparams_alternative_model_column_headers`
     - `test_20_get_hparams_for_model_class_objects_and_whitespace`

3. **`logs/execution_notes.md`**:
   - Reviewer Round 2 실행 및 자가 개선 세션 로그 기록.

---

## 4. 검증 결과 (Verification Record)

### 1) 단위/통합 테스트 스위트
- `/home/imnyj/venv/bin/pytest tests/test_run_all.py -v`: **20/20 PASSED** (18.62s)
- `/home/imnyj/venv/bin/pytest -v` (전체 테스트 스위트): **130/130 PASSED** (0 failed, 3 warnings in 45.39s)

### 2) 실제 CLI 서브프로세스 훈련 실행 실증
1. 기본 HPO CSV를 통한 PPO 훈련:
   `python run_all.py --episodes 1 --steps-per-episode 10 --models PPO` -> 종료 코드 0 (성공)
2. 소문자 CLI 모델명 정규화 및 훈련:
   `python run_all.py --episodes 1 --steps-per-episode 10 --models ppo` -> 종료 코드 0 (성공)
3. 결측 CSV 경로 fallback 훈련:
   `python run_all.py --episodes 1 --steps-per-episode 10 --models PPO --hparams-csv /tmp/missing_file.csv` -> 종료 코드 0 (경고 로깅 후 기본값 fallback 성공)
4. 8종 전체 베이스라인 모델 동시 훈련:
   `python run_all.py --episodes 1 --steps-per-episode 10 --models SAC TD3 RES-MAPDDPG MA2HDQN I-HAMAPPO SPAM-D3QN CARLTON MADDPG-MT --no-resume` -> 종료 코드 0 (8개 전 기종 HPO 주입 및 훈련 성공)

---

## 5. 결론 및 잔여 리스크
- 요구사항 R1, R2 및 수용 기준이 완벽히 충족되었으며, 적대적 엣지 케이스(NaN 값, 중복 시도 CSV, 틸드 경로, 불리언/정수 캐스팅)에 대한 방어 로직과 130개 전체 테스트 스위트 무결점이 입증되었습니다.
- 작업 완료(COMPLETE) 판정합니다.
