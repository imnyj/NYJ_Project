# Handoff Report — Auto_Stock Phase 6 HPO 파이프라인 및 테스트 스위트 조사

- **에이전트**: teamwork_preview_explorer_p6_3 (Phase 6 HPO & Test Suite Explorer)
- **수행 유형**: Hard Handoff (조사 완료)
- **작성 일시**: 2026-09-03T11:02:45+09:00
- **작업 디렉토리**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_3`
- **상세 보고서 경로**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_3/survey_hpo_tests.md`

---

## 1. Observation (직접 관찰한 사실)

1. **기존 HPO 파이프라인 구조 (`modules/hpo/`)**:
   - `modules/hpo/optuna_pipeline.py`:
     - `create_hpo_study`: TPESampler(seed=42), MedianPruner(n_startup_trials=2, n_warmup_steps=5, interval_steps=1), direction="maximize" 기반 Study 생성 (라인 53~91).
     - `objective`: 라인 185~190에서 `TabularMLPFeatureExtractor`만 하드코딩되어 호출됨. 탐색 공간은 `sl_lr`, `sl_hidden_dim`, `sl_batch_size`, `rl_lr`, `rl_gamma`, `rl_clip_range`, `rl_ent_coef`, `rl_hidden_dim`으로 고정.
     - 라인 267~270에서 무거래(`total_trades == 0`) 시 `objective_value = -1.0` 패널티 부여 (BUG-RL05 방어).
     - 라인 326~327에서 `export_trial_to_csv(trial_record, csv_path=output_csv)`를 호출하여 결과 저장.
     - `run_hpo_optimization`: 기본 인자로 `output_csv="etc/hpo_results/baseline_hpo.csv"` 지정 (라인 339).
   - `modules/hpo/exporter.py`:
     - 라인 29~50에 20개 고정 컬럼 `CSV_COLUMNS` 정의.
     - 라인 56~83에 `_process_file_lock` 컨텍스트 매니저 구현: `fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX / LOCK_SH)` 및 `threading.Lock()`을 결합한 멀티프로세스/스레드 파일 락.
     - 라인 251~259: `csv.DictWriter(f, fieldnames=CSV_COLUMNS)`로 20개 컬럼만 필터링하여 파일에 기록하고 `os.fsync()` 호출.
     - 라인 328~330: `load_hpo_results`에서 `missing = [col for col in CSV_COLUMNS if col not in df.columns]`로 20개 컬럼 무결성 엄격 검증.
   - `modules/hpo/metrics.py`:
     - 라인 85~123: `calculate_annualized_sharpe_ratio`에서 표본 표준편차가 1e-8 이하이거나 NaN인 경우 0.0 반환 (Zero-Variance 방어).

2. **기존 테스트 스위트의 엄격한 스키마 검증 (`tests/test_hpo.py`, `tests/test_adversarial_challenger2_hpo.py`)**:
   - `tests/test_hpo.py` 라인 219~229:
     ```python
     def test_export_trial_to_csv_20_columns_schema(self):
         assert len(CSV_COLUMNS) == 20
         with tempfile.TemporaryDirectory() as tmp_dir:
             csv_path = os.path.join(tmp_dir, "schema_test.csv")
             export_trial_to_csv({}, csv_path=csv_path)
             df = pd.read_csv(csv_path)
             assert len(df.columns) == 20
     ```
   - `tests/test_adversarial_challenger2_hpo.py` 라인 78~79:
     ```python
     assert len(df.columns) == 20, f"Expected 20 columns, got {len(df.columns)}"
     assert list(df.columns) == CSV_COLUMNS
     ```

3. **테스트 수집 환경 및 잠재적 충돌 요인**:
   - 파이썬 가상환경 경로: `/home/imnyj/venv/bin/python3`, `/home/imnyj/venv/bin/pytest` (버전 9.0.3).
   - 루트 디렉토리에서 인자 없이 `pytest` 실행 시 `etc/scripts/m2_challenger2_stress_test.py` 라인 497의 최상위 `sys.exit(0)`으로 인해 수집 단계에서 `SystemExit: 0` 인터널 에러 발생.
   - `Makefile` 및 정상 실행 명령어 `/home/imnyj/venv/bin/pytest tests/ -q` 실행 시 총 497개의 테스트가 정상 수집됨.
   - `/home/imnyj/venv/bin/pytest tests/test_hpo.py tests/test_hpo_pipeline.py -q` 실행 결과: 45 passed, 2 warnings (20.04초) 완벽 통과.

4. **Phase 6 요구사항 및 승인 기준 (`ORIGINAL_REQUEST.md` 라인 109~141)**:
   - R1: 1D-CNN 기반 ResNet, 시계열 Attention 기반 Transformer, 잠재 공간 이상치 탐지 기반 CVAE 3대 SL 아키텍처를 특징 추출기로 구현.
   - R2: SL 아키텍처와 PPO 강화학습 완벽 결합.
   - R3: 각 아키텍처별 Optuna 파이프라인 구축.
   - 검증 기준 1: `tests/test_phase6_models.py` (3개 모델의 동일 텐서 입력 대비 정상 출력 Shape 검증).
   - 검증 기준 2: `tests/test_phase6_hpo.py` (각 아키텍처별 n_trials=2 이상 최적화 및 `etc/hpo_results/main_models_hpo.csv` 저장 검증).
   - 검증 기준 3: 전체 테스트 스위트 100% Pass.

---

## 2. Logic Chain (논리 추론 과정)

1. **스키마 충돌 회귀 방지 논리 (Observation 1, 2 기반)**:
   - `Observation 2`에 의해 `CSV_COLUMNS`의 길이는 기존 테스트에서 정확히 20개여야 함을 단언하고 있음.
   - 만약 Phase 6의 `main_models_hpo.csv` 저장을 위해 기존 `CSV_COLUMNS`에 `model_type`이나 모델별 하이퍼파라미터 컬럼을 직접 추가하면, 기존 `test_hpo.py` 및 `test_adversarial_challenger2_hpo.py`가 즉각 실패함.
   - 따라서 `modules/hpo/exporter.py`의 기존 `CSV_COLUMNS`는 절대 수정하지 않고 원형을 유지해야 함.
   - 대신 Phase 6 전용 슈퍼셋 스키마인 `MAIN_MODELS_CSV_COLUMNS`를 신설하고, 전용 저장 함수 `export_main_model_trial_to_csv` 및 로더 `load_main_models_hpo_results`를 별도 정의하거나, `export_trial_to_csv`에 옵셔널 인자로 `columns`를 제공하도록 설계해야 기존 테스트 100% Pass와 Phase 6 요구사항을 동시에 만족할 수 있음.

2. **동시성 및 원자적 누적 저장 논리 (Observation 1, 4 기반)**:
   - Phase 6 승인 기준 2는 "각 아키텍처별 Optuna 최적화가 최소 2회(n_trials=2) 이상 실행되며 결과가 `etc/hpo_results/main_models_hpo.csv` 형태로 저장됨"을 요구함.
   - 3개 모델(ResNet, Transformer, CVAE)이 순차 또는 병렬로 실행되면서同一 CSV에 행을 추가(Append)해야 함.
   - `modules/hpo/exporter.py`의 검증된 `_process_file_lock`(`fcntl.flock` + `threading.Lock`)을 그대로 활용하여 쓰기 작업을 감싸면 멀티프로세스/스레드 간 파일 오염이나 덮어쓰기 유실(Lost Update) 없이 최소 6개 이상의 Trial 결과가 무결하게 누적 저장됨.

3. **Transformer HPO 탐색 공간 무결성 논리**:
   - PyTorch `nn.MultiheadAttention`은 `embed_dim % num_heads == 0` 조건을 만족하지 않으면 런타임에 `ValueError`를 발생시킴.
   - Optuna가 `d_model`과 `nhead`를 독립적으로 suggest할 경우 비정상 조합(예: d_model=32, nhead=3 또는 d_model=50, nhead=4 등)으로 인해 최적화 루프가 크래시될 위험이 있음.
   - 따라서 HPO 탐색 공간에서 `nhead`를 `[2, 4]`로 제한하고 `d_model`을 `nhead`의 공배수(`[32, 64, 128]`)로 선택하도록 제약하거나, 목적함수 내에서 `d_model = (d_model // nhead) * nhead`로 강제 정합하는 가드를 배치해야 안정적인 n_trials=2 완주가 보장됨.

4. **테스트 스위트 분리 및 실행 경로 논리 (Observation 3, 4 기반)**:
   - `tests/test_phase6_models.py`는 R1에 집중하여 3개 모델의 텐서 Shape, NaN/Inf 방어, 역전파, PPO Policy 주입 호환성을 검증.
   - `tests/test_phase6_hpo.py`는 R3에 집중하여 3개 모델의 2회 Trial 최적화 완주, `main_models_hpo.csv` 파일 생성, 스키마 일치성, 최소 6행 누적, 동시성 안전성을 검증.
   - `pytest` 실행 시에는 루트가 아닌 `/home/imnyj/venv/bin/pytest tests/`를 지정하여 `etc/scripts/` 내의 `sys.exit(0)` 스크립트와의 충돌을 원천 차단함.

---

## 3. Caveats (제약 사항 및 가정)

1. **Read-Only 제약**:
   - 본 Explorer는 조사 및 설계 전담 에이전트로서 소스 코드 파일(`modules/`, `tests/` 등)을 직접 수정하지 않았습니다.
   - 실제 모델 구현, HPO 파이프라인 코드 작성, 테스트 파일 생성은 오케스트레이터의 승인 후 후속 구현 Worker 에이전트가 담당해야 합니다.
2. **타임프레임 데이터 규격 가정**:
   - 다중 타임프레임 데이터는 `(Batch, seq_len=20, in_channels=10)` 규격의 텐서 또는 `(seq_len, in_channels)` 단일 샘플 텐서를 기본으로 가정하였습니다. `explorer_p6_1` 및 `p6_2`에서 구체화하는 타임프레임 규격과 최종 연동되어야 합니다.
3. **사전 학습 가중치(Pretrained weights)**:
   - HPO 단계에서는 모델 초기화 및 PPO 고속 탐색(fast_mode)을 검증하므로, 복잡한 대규모 사전학습 체크포인트 없이도 경량 스텝(32~64 timesteps)으로 테스트가 통과되도록 설계되었습니다.

---

## 4. Conclusion (최종 평가 및 조치 방안)

1. **설계 완성도**:
   - ResNet, Transformer, CVAE 3대 SL 아키텍처별 Optuna 탐색 공간, 목적함수, 2-Trial 실행 흐름이 완벽하게 설계되었습니다.
   - `etc/hpo_results/main_models_hpo.csv`의 통합 슈퍼셋 스키마(`MAIN_MODELS_CSV_COLUMNS`)와 `fcntl.flock` 원자적 누적 저장 메커니즘이 확립되었습니다.
   - 기존 18개 테스트 스위트(497개 테스트)와의 스키마 충돌을 100% 방지하는 하위 호환 전략이 수립되었습니다.
2. **테스트 스위트 명세**:
   - `tests/test_phase6_models.py` 및 `tests/test_phase6_hpo.py`의 상세 클래스 및 메서드 명세가 완비되어 즉시 구현 작업에 투입 가능합니다.

---

## 5. Verification Method (독립적 검증 방법)

후속 에이전트 및 감사자가 본 설계를 검증하기 위한 명령어 및 확인 방법:

1. **상세 설계 보고서 검토**:
   - 파일 확인: `view_file /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_3/survey_hpo_tests.md`
2. **기존 HPO 테스트 스위트 무결성 확인**:
   - 실행 명령어:
     ```bash
     /home/imnyj/venv/bin/pytest tests/test_hpo.py tests/test_hpo_pipeline.py -q
     ```
   - 기대 결과: 45 passed (100% 통과).
3. **전체 테스트 스위트 수집 검증**:
   - 실행 명령어:
     ```bash
     /home/imnyj/venv/bin/pytest tests/ --collect-only -q
     ```
   - 기대 결과: 497 tests collected (에러 0건).
4. **구현 완료 후 Phase 6 전용 검증 명령어**:
   - `tests/test_phase6_models.py` 실행:
     ```bash
     /home/imnyj/venv/bin/pytest tests/test_phase6_models.py -v
     ```
   - `tests/test_phase6_hpo.py` 실행:
     ```bash
     /home/imnyj/venv/bin/pytest tests/test_phase6_hpo.py -v
     ```
   - `main_models_hpo.csv` 생성 확인:
     ```bash
     head -n 10 /home/imnyj/Workspace/Auto_Stock/etc/hpo_results/main_models_hpo.csv
     ```
   - 전체 테스트 스위트 최종 검증:
     ```bash
     /home/imnyj/venv/bin/pytest tests/ -v
     ```
