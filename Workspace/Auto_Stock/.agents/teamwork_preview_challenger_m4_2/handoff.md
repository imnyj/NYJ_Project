# Handoff Report — HPO 파이프라인 및 E2E 적대적 스트레스 검증

- **에이전트**: `teamwork_preview_challenger_m4_2` (EMPIRICAL CHALLENGER)
- **작업 일시**: 2026-09-02T15:34:00+09:00
- **최종 판정**: **REJECT** (멀티프로세스 환경에서의 CSV 동시 쓰기 Race Condition으로 인한 대량 데이터 유실 결함 확인)

---

## 1. Observation (직접 관찰된 사실)

1. **멀티프로세스 동시 쓰기 시 대량 데이터 유실 (Critical Defect)**:
   - 스크립트: `/home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_concurrency.py`
   - 조건: 8개 프로세스가 각 10회씩 총 80개의 Trial 결과를 `export_trial_to_csv`로 동시 기록.
   - 관찰 결과:
     ```text
     === [2] Multi-Process Concurrency Stress Test ===
       [Result] Multi-Process: Expected 80 rows, Got 13 rows in 0.253s
       [CRITICAL VULNERABILITY FOUND] Lost Updates in Multi-Process! 67 trials were overwritten and lost!
       Sample Missing Trial IDs: [1, 2, 3, 4, 5, 6, 7, 9, 7000, 7002]
     ```
   - 80개 Trial 중 **67개(83.75%)의 Trial 데이터가 덮어써져 영구 유실됨**.
   - 코드 위치: `/home/imnyj/Workspace/Auto_Stock/modules/hpo/exporter.py` 라인 49 및 라인 173-196.
     - `_FILE_WRITE_LOCK = threading.Lock()`은 단일 파이썬 인터프리터 내 스레드 간에만 유효하며, 독립 프로세스 간에는 상호 배제를 제공하지 못함.
     - `export_trial_to_csv`가 기존 CSV를 읽어 새 데이터를 합친 후 임시 파일에 쓰고 `os.replace`로 치환하는 Read-Modify-Write 패턴을 파일 락(OS file lock) 없이 수행하여, 마지막 `os.replace`를 실행한 프로세스가 이전 프로세스들의 기록을 덮어씀.

2. **0-분산 횡보 데이터 및 99% 폭락 데이터 계산 안정성 (Passed)**:
   - 스크립트: `/home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_extreme_data.py`
   - 0-분산 횡보 (모든 일별 수익률 0.0, 상수 수익률, 표준편차 <= 1e-8): `calculate_annualized_sharpe_ratio`가 `0.0`을 반환하며 `ZeroDivisionError`가 완벽히 방어됨.
   - 99.999% 폭락 (70,000원 -> 1원 플래시 크래시): 자산 평가액이 48,710원(< 500,000원)으로 급락 시 `terminated=True`(파산)가 즉각 발동되며 회계 불변식(현금 + 보유주식*현재가 = 총자산) 오차 0원 유지.
   - 극단적 자산 붕괴(100억 -> 1e-8원 및 0.0원): MDD `-100.0%`, Return `-100.0%`로 안전하게 산출됨.
   - *마이너 관찰*: `evaluate_trading_history`에 `equity_history=[float('nan'), float('inf'), -float('inf')]` 전달 시 `final_equity`가 NaN/Inf 필터링 없이 `-inf`로 반환되는 엣지 케이스 확인.

3. **`make test-hpo` 전체 실행 안정성 및 재현성 (Passed)**:
   - 스크립트: `/home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_reproducibility.py`
   - 3회 연속 전체 테스트(27개 테스트 케이스) 실행 결과 100% 통과 (Flaky test 없음).
   - CLI 극한 인자 (`--timesteps 1`, `--n-trials 5`, `--seed 99999`) 서브프로세스 실행 모두 정상 완주.

---

## 2. Logic Chain (논리적 추론 체인)

1. `PROJECT.md` 및 `TEST_INFRA.md`는 HPO 파이프라인의 핵심 속성으로 **원자적 CSV 저장(Atomic CSV export) 및 무결성 보장**을 명시하고 있습니다.
2. `modules/hpo/exporter.py`는 `_FILE_WRITE_LOCK = threading.Lock()`을 사용하여 동시성을 제어하지만, 이는 `multiprocessing`이나 분산 Optuna 워커(`n_jobs > 1`) 환경에서 프로세스 간 락 역할을 수행할 수 없습니다.
3. `export_trial_to_csv` 함수는 `pd.read_csv(abs_path)`로 기존 파일 내용을 읽고, 신규 레코드를 concat한 후 `os.replace`를 수행합니다.
4. 프로세스 A와 프로세스 B가 동시에 `export_trial_to_csv`를 호출할 경우, 두 프로세스가 동일한 이전 시점의 CSV를 읽고 각각의 임시 파일에 자신의 데이터만 추가한 뒤 `os.replace`를 호출하게 됩니다.
5. 먼저 교체된 프로세스의 파일은 나중에 교체된 프로세스의 파일에 의해 덮어씌워지므로, 먼저 완료된 프로세스의 Trial 기록이 통째로 유실되는 Lost Update 현상이 발생합니다.
6. 실증 테스트에서 8개 프로세스 동시 실행 시 80개 중 67개 레코드가 유실(13개만 잔존)되는 것이 재현되었습니다.
7. 따라서 멀티프로세스 환경에서 CSV 파일의 무결성과 원자성이 훼손되므로 결함(Defect)으로 판정합니다.

---

## 3. Caveats (한계 및 가정)

1. 단일 프로세스 내의 멀티스레드 환경(`threading.Thread`)에서는 `_FILE_WRITE_LOCK`이 정상 작동하여 160/160건 모두 온전하게 기록됩니다.
2. 현재 `scripts/run_hpo.py`의 기본 실행 모드는 단일 프로세스 단일 스레드로 동작하므로, 단일 CLI 실행만으로는 본 버그가 표면화되지 않습니다.
3. 그러나 백테스팅 및 HPO는 통상 멀티프로세스/분산 환경(`n_jobs > 1`, 다중 터미널 병렬 실행)으로 확장되므로 반드시 시스템 레벨 파일 락(`fcntl.flock`, `filelock` 또는 `Command/core/lock_manager.py`) 또는 단순 Append 모드 + 파일 락이 적용되어야 합니다.

---

## 4. Conclusion (결론 및 권고)

- **판정**: **REJECT**
- **사유**: `modules/hpo/exporter.py`의 멀티프로세스 동시 쓰기 경쟁 조건으로 인한 Trial 데이터 대량 유실 결함.
- **수정 권고사항**:
  1. `fcntl.flock` (Linux/Unix 파일 락) 또는 프로젝트의 파일 락 프로토콜을 도입하여 프로세스 간 상호 배제 보장.
  2. 불필요한 전체 파일 Read-Concat-Replace 방식 대신, 파일 락을 획득한 상태에서 표준 `open(abs_path, 'a')` 모드로 한 줄씩 Append하는 안전한 패턴으로 개선.
  3. `evaluate_trading_history`의 `equity_history` 입력값에 대해 `np.isfinite` 필터링을 추가하여 NaN/Inf 유입 방어 강화.

---

## 5. Verification Method (독립 검증 방법)

1. **멀티프로세스 유실 재현 명령**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_concurrency.py
   ```
   - 예상 결과: Multi-Process 테스트에서 Expected 80 rows 대비 대량의 row가 유실되며 exit code 2 발생.

2. **0-분산 및 99% 폭락 검증 명령**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Workspace/Auto_Stock/etc/scripts/stress_test_extreme_data.py
   ```

3. **기본 회귀 테스트 전체 실행**:
   ```bash
   make test-hpo
   ```
