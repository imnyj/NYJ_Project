# Handoff Report — HPO CSV 내보내기 멀티프로세스 동시성 하드닝 (Hardening)

- **에이전트**: `teamwork_preview_worker_harden` (Implementer / QA / Specialist)
- **작업 일시**: 2026-09-02T15:43:45+09:00
- **수정 대상 파일**: `modules/hpo/exporter.py`
- **최종 판정**: **COMPLETE (100% PASS, 0 Data Loss 입증)**

---

## 1. Observation (직접 관찰된 사실)

1. **기존 결함 현상 (Defect Reproduction)**:
   - 스크립트: `/home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_concurrency.py`
   - 수정 전 결과:
     ```text
     === [2] Multi-Process Concurrency Stress Test ===
       [Result] Multi-Process: Expected 80 rows, Got 10 rows in 0.181s
       [CRITICAL VULNERABILITY FOUND] Lost Updates in Multi-Process! 70 trials were overwritten and lost!
       Sample Missing Trial IDs: [0, 1, 2, 3, 5, 6, 7, 8, 9, 7000]
     ```
   - 원인: `_FILE_WRITE_LOCK = threading.Lock()`은 단일 인터프리터 내 스레드 간에만 유효하여, 독립 프로세스 환경에서 기존 CSV를 읽어 임시 파일에 쓰고 `os.replace`로 치환하는 Read-Modify-Replace 과정에서 마지막 프로세스가 이전 프로세스의 쓰기를 덮어써 70개(87.5%)의 Trial이 유실됨.

2. **수정 후 실측 검증 (Post-Hardening Results)**:
   - `modules/hpo/exporter.py`에 `fcntl.flock` 기반 전용 `.lock` 파일 락(`_process_file_lock`) 및 O(1) 원자적 Append 모드 적용 후 실측:
   - **8개 프로세스 동시 쓰기 (`stress_test_concurrency.py`)**:
     ```text
     === [1] Multi-Thread Concurrency Stress Test ===
       [Result] Multi-Thread: Expected 160 rows, Got 160 rows in 0.954s
       >>> Multi-Thread Test PASSED! <<<

     === [2] Multi-Process Concurrency Stress Test ===
       [Result] Multi-Process: Expected 80 rows, Got 80 rows in 0.606s
       >>> Multi-Process Test PASSED! <<<

     [SUMMARY] Both Multi-Thread and Multi-Process tests passed.
     ```
   - **16개 프로세스 극한 동시 쓰기 (Ultra-Stress 320 Trials)**:
     ```text
     16-process Ultra Stress: Expected 320 rows, Got 320 rows in 2.087s
     >>> Ultra Stress 16-Process PASSED with 0 data loss! <<<
     ```
   - **`make test-hpo` 전체 테스트**:
     ```text
     ======================= 27 passed, 2 warnings in 12.42s ========================
     ```
   - **`stress_test_reproducibility.py` 3회 연속 실행**:
     ```text
     [PASS] Run #1/3 PASSED in 14.75s (27 tests)
     [PASS] Run #2/3 PASSED in 14.67s (27 tests)
     [PASS] Run #3/3 PASSED in 14.72s (27 tests)
     >>> ALL 3 REPEATED RUNS PASSED! Total Time: 44.15s (Average: 14.72s per run) <<<
     ```
   - **`export_study_to_csv` 기능 검증**: Optuna Study 인스턴스 전달 시 5/5 Trial 정상 추출 및 20개 컬럼 스키마 CSV 출력 확인 완료.
   - **정적 코드 검사 (`ruff check modules/hpo/exporter.py`)**: 0 lint violations (`All checks passed!`).

---

## 2. Logic Chain (논리적 추론 체인)

1. `PROJECT.md` 및 `ORIGINAL_REQUEST.md` (R4)는 HPO Trial 결과의 안전한 CSV 저장을 규정하고 있습니다.
2. 멀티프로세스 환경(`n_jobs > 1`, 분산 워커 등)에서는 파이썬의 `threading.Lock()`만으로는 프로세스 간 동기화가 불가능합니다.
3. 이를 해결하기 위해 OS 커널 레벨의 `fcntl.flock`을 활용하는 `_process_file_lock(csv_abs_path, shared=False)` 컨텍스트 매니저를 구현했습니다.
   - 단일 프로세스 내 다중 스레드는 `threading.Lock()`으로 1차 보호.
   - 다중 독립 프로세스는 대상 파일별 전용 `.lock` 파일에 `fcntl.flock(LOCK_EX)` (쓰기 시 배타적 락) 및 `fcntl.flock(LOCK_SH)` (읽기 시 공유 락)을 적용하여 OS 레벨 상호 배제 보장.
4. 파일 I/O 방식을 기존의 전체 파일 Read-Concat-Replace 방식(O(N) I/O 및 덮어쓰기 위험)에서 파일 락 하에서의 안전한 O(1) Append(`csv.DictWriter` + `flush()` + `os.fsync()`) 방식으로 전환했습니다.
   - 파일이 존재하지 않거나 비어있는 경우에만 헤더(`CSV_COLUMNS`)를 작성하고, 이후 데이터는 끝에 누락 없이 추가됩니다.
5. `export_study_to_csv(study, csv_path, overwrite)` API를 추가하여 Optuna Study 객체의 전체 Trial을 단일 호출로 안전하게 내보낼 수 있도록 확장했습니다.
6. 실측 테스트 결과 8개 및 16개 동시 프로세스에서 데이터 유실이 0건(100% 무손실 보존)으로 입증되었습니다.

---

## 3. Caveats (한계 및 가정)

1. `fcntl` 모듈은 Linux/macOS 등 POSIX 호환 운영체제에서 기본 제공되는 표준 라이브러리입니다 (본 환경 Linux 완벽 지원).
2. CSV 파일 생성 시 동일 경로에 `.lock` 파일(예: `baseline_hpo.csv.lock`)이 생성되며, 이는 프로세스 간 동기화를 위한 0바이트 메타 파일로 정상적인 동작입니다.
3. `load_hpo_results` 또한 `_process_file_lock(abs_path, shared=True)`를 통해 공유 락을 획득하므로, 쓰기 작업이 진행 중인 도중 불완전한 라인을 읽어 파싱 에러가 발생하는 현상을 방지합니다.

---

## 4. Conclusion (결론)

- `modules/hpo/exporter.py`의 멀티프로세스 동시성 취약점(Lost Update)이 `fcntl.flock` 기반 파일 락 메커니즘과 O(1) 원자적 Append 모드를 통해 완벽하게 해결되었습니다.
- 8개 프로세스(80건) 및 16개 프로세스(320건) 동시 쓰기 스트레스 테스트에서 데이터 유실 0건(100% 무손실)이 실측 확인되었습니다.
- `make test-hpo` 27개 테스트 및 3회 연속 반복 재현성 테스트 100% 통과를 달성했습니다.

---

## 5. Verification Method (독립 검증 방법)

1. **멀티프로세스 동시성 스트레스 테스트 (8 프로세스)**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_concurrency.py
   ```
   - 기대 결과: Multi-Thread (160/160 rows), Multi-Process (80/80 rows) 100% PASS (Exit Code 0).

2. **16개 프로세스 극한 동시성 스트레스 테스트**:
   ```bash
   /home/imnyj/venv/bin/python3 -c "
   import os, time, tempfile
   from concurrent.futures import ProcessPoolExecutor
   from modules.hpo.exporter import export_trial_to_csv, load_hpo_results
   def worker(args):
       p, i, csv_p = args
       tid = p * 1000 + i
       export_trial_to_csv({'trial_id': tid, 'objective_value': tid * 0.1, 'total_equity': 10000000.0 + tid}, csv_path=csv_p)
       return tid
   with tempfile.TemporaryDirectory() as tmp_dir:
       csv_path = os.path.join(tmp_dir, 'ultra_stress.csv')
       tasks = [(p, i, csv_path) for p in range(16) for i in range(20)]
       with ProcessPoolExecutor(max_workers=16) as ex:
           res = list(ex.map(worker, tasks))
       df = load_hpo_results(csv_path)
       assert len(df) == 320 and set(df['trial_id']) == set(res)
       print('Ultra Stress 16-Process PASSED (320/320 rows)')
   "
   ```

3. **HPO 파이프라인 전체 테스트 스위트 실행**:
   ```bash
   make test-hpo
   ```
   - 기대 결과: 27 passed.

4. **재현성 스트레스 테스트 실행**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_reproducibility.py
   ```
   - 기대 결과: 3회 연속 100% PASS.
