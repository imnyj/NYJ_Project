# E2E 검증 수트 최종 리뷰 및 검수 보고서 (Handoff Report)

- **작성 에이전트**: reviewer_e2e_2
- **작성 일시**: 2026-08-12T17:10:45+09:00
- **검수 대상**: `etc/tests/test_tier3.py`, `etc/tests/test_tier4.py`, `etc/tests/run_e2e_tests.py`, `etc/logs/e2e_results.json`, `etc/tests/helpers/reference_engine.py`, `etc/tests/test_tier1.py`
- **최종 판정**: **REQUEST_CHANGES (수정 요청)**

---

## Review Summary

**Verdict**: **REQUEST_CHANGES**

본 검수자는 청주 방서동 자이 아파트 재무 시뮬레이션 프로젝트의 E2E 테스트 수트(`test_tier3.py`, `test_tier4.py`, `run_e2e_tests.py`, `e2e_results.json` 등)에 대한 객관적 검무(Reviewer) 및 적대적 평가(Adversarial Critic)를 수행하였습니다.

검수 결과, 직교 배열(Pairwise) 조합 커버리지(100%) 및 다년도 타임라인 원리금/보너스 상환 엔진 계산 정합성은 우수하나, **코드 내 하드코딩 반환값, 무조건 성공하는 자가 승인(Self-Certifying) 더미 테스트, 미사용 파사드(Facade) 파라미터, 및 마스터 러너의 수집 오류 발생 시 Exit Code 0 반환 결함** 등 무결성 위반(INTEGRITY VIOLATION) 항목이 발견되어 **REQUEST_CHANGES**를 최종 판정합니다.

---

## 1. Observation (직접 관찰 사실)

1. **마스터 테스터 실행 결과 (`run_e2e_tests.py`)**:
   - 실행 명령: `/home/imnyj/venv/bin/python /home/imnyj/Workspace/House/etc/tests/run_e2e_tests.py`
   - 출력 결과:
     ```text
     ======================================================================
           Cheongju House Financial Simulation — E2E Test Runner      
     ======================================================================

     [RUNNING] test_tier1.py ...
     [PASSED] test_tier1.py: 28 passed, 0 failed, 0 skipped (Total: 28)

     [RUNNING] test_tier2.py ...
     [PASSED] test_tier2.py: 26 passed, 0 failed, 0 skipped (Total: 26)

     [RUNNING] test_tier3.py ...
     [PASSED] test_tier3.py: 13 passed, 0 failed, 0 skipped (Total: 13)

     [RUNNING] test_tier4.py ...
     [PASSED] test_tier4.py: 5 passed, 0 failed, 0 skipped (Total: 5)

     ======================================================================
     OVERALL RESULT: SUCCESS
     Total: 72 | Passed: 72 | Failed: 0 | Skipped: 0
     Duration: 3.905s
     Log written to: /home/imnyj/Workspace/House/etc/logs/e2e_results.json
     ======================================================================
     ```
   - Exit Code: `0`

2. **직교 배열(Pairwise) 2-Way 커버리지 (`test_tier3.py`)**:
   - 요인(Factor) 5개: 매매가(3), 금리(3), 기간(3), 보너스(3), 투자옵션(2).
   - 필요한 모든 2-Way 쌍 수: 78개.
   - `test_tier3.py` 내 12개 테스크 케이스 검증 결과: 78/78 쌍 전수 커버(100% 커버리지 확인).

3. **엔진 내 하드코딩 분기 (`etc/tests/helpers/reference_engine.py` line 35-48)**:
   ```python
   def calculate_bond_discount(price: float) -> int:
       if price == 350000000:
           return 515000
       elif price == 375000000:
           return 574000
       elif price == 400000000:
           return 644000
       else:
           return int(round(price * 0.70 * 0.021 * 0.10))
   ```

4. **자가 승인 더미 테스트 (`etc/tests/test_tier1.py` line 106-110, 179-196)**:
   ```python
   # Line 106-110
   def test_r2_stamp_tax_borrower_share():
       """TC-T1-R2-02: 5천만 원 초과 대출 차주 부담 인지세 (75,000원)"""
       stamp_tax_borrower = 75000
       assert stamp_tax_borrower == 75000

   # Line 179-186
   def test_r4_admin_checklist_steps_sequence():
       steps = ["잔금 납부", "소유권 이전 등기", "취득세 신고", "전입신고", "확정일자", "재산세 안내"]
       assert len(steps) == 6
       assert steps[0] == "잔금 납부"
       assert steps[1] == "소유권 이전 등기"
       assert steps[2] == "취득세 신고"
   ```

5. **미사용 파사드 파라미터 (`etc/tests/helpers/reference_engine.py` line 113-122 및 `test_tier3.py` line 32-36)**:
   ```python
   def simulate_timeline(
       price: float,
       cash: float = 230000000,
       annual_rate: float = 0.03,
       term_years: int = 30,
       bonus_schedule: dict = None,
       include_one_time_in_loan: bool = False,
       monthly_income: int = 3300000,
       base_fixed_spending: int = 2319708  # <- 전달받으나 함수 내부(133~200행)에서 일절 미사용!
   ):
   ```

6. **마스터 러너 Exit Code 판정 논리 결함 (`etc/tests/run_e2e_tests.py` line 90, 110, 136-139)**:
   ```python
   status = "PASSED" if (result.returncode == 0 and failed == 0) else "FAILED"
   ...
   overall_status = "SUCCESS" if total_failed == 0 else "FAILURE"
   ...
   if total_failed > 0 or overall_status != "SUCCESS":
       sys.exit(1)
   else:
       sys.exit(0)
   ```
   파이썬 수집/임포트 오류 발생 시 Pytest `result.returncode`는 2(실패)가 되고 `status`는 `"FAILED"`가 되지만, `passed=0, failed=0, skipped=0`이므로 `total_failed`가 0으로 간주되어 `overall_status`가 `"SUCCESS"`로 오판되어 `sys.exit(0)`으로 종료됨.

---

## 2. Logic Chain (논리적 인과관계 분석)

1. **무결성 위반 1 (자가 증명 더미 테스트)**:
   `test_r2_stamp_tax_borrower_share`는 외부 엔진이나 시스템 계산을 검증하지 않고 함수 내부 변수 `stamp_tax_borrower = 75000`를 선언 후 자기 자신과 일치하는지 비교합니다. 또한 `test_r4_admin_checklist_steps_sequence`와 `test_r4_admin_checklist_deadlines`는 `report_parser.py`의 보고서 파싱 기능을 사용하지 않고 내부 하드코딩 리스트를 검증합니다. 이는 검증 대상을 검증하지 않고 100% 통과하도록 작성된 더미 테스트(Dummy Test)입니다.

2. **무결성 위반 2 (하드코딩 분기 처리)**:
   `calculate_bond_discount()`는 수식 기반 계산이 아닌 `if price == 350000000: return 515000` 등 특정 입력값에 대해 결과를 하드코딩하여 반환합니다. 실제로 수식 `price * 0.70 * 0.021 * 0.10`을 계산하면 3.5억 시 `514,500원`, 3.75억 시 `551,250원`이 나오지만, 하드코딩 반환값은 515,000원, 574,000원입니다. 이는 수식 구현 우회 및 결과값 하드코딩 위반입니다.

3. **무결성 위반 3 (파사드 파라미터)**:
   `simulate_timeline()` 함수는 `base_fixed_spending` 파라미터를 인자로 정의하였으나 본문 구현에서 이 값을 전혀 사용하지 않습니다. `test_tier3.py`에서 "투자 유지(Keep)" vs "투자 중단(Stop)" 옵션을 `base_fixed_spending`으로 넘기지만 엔진이 이를 무시하므로, 직교 배열 테스트의 요인 5가 실제 시뮬레이션 결과에 반영되지 않습니다.

4. **마스터 러너 Exit Code 결함**:
   `run_e2e_tests.py`는 `overall_status`를 `total_failed == 0` 여부로만 결정합니다. Pytest 실행 시 파이썬 파일의 문법 에러나 모듈 임포트 실패가 발생할 경우 `total_failed`는 0이지만 `status`는 `"FAILED"`이며 `exit_code`는 non-zero(2)가 됩니다. 그러나 러너는 이를 `"SUCCESS"`로 처리하여 exit code 0을 반환하므로 테스트 실패 상황을 성공으로 왜곡합니다.

---

## 3. Findings (발견된 문제점 상세)

### [Critical] Finding 1: INTEGRITY VIOLATION — Self-Certifying Dummy Tests
- **위치**: `etc/tests/test_tier1.py` lines 106-110, 179-196
- **문제점**: `test_r2_stamp_tax_borrower_share`는 테스트 함수 내에 local 변수로 `stamp_tax_borrower = 75000`을 정의하고 `assert stamp_tax_borrower == 75000`을 수행합니다. `test_r4_admin_checklist_steps_sequence` 및 `deadlines` 테스트 또한 실제 보고서 파서를 호출하지 않고 테스트 내부 하드코딩 리스트/딕셔너리와 비교합니다.
- **수정 방향**: `parse_report_markdown()`을 호출하여 `House_Financial_Simulation_Report.md` 파일 내 행정 절차 및 기한 텍스트를 직접 파싱 검증하고, 대출 인지세는 `reference_engine.py` 또는 JSON 파라미터 규격에서 값을 계산/추출하여 검증해야 합니다.

### [Critical] Finding 2: INTEGRITY VIOLATION — Hardcoded Values in Calculation Engine
- **위치**: `etc/tests/helpers/reference_engine.py` lines 35-48
- **문제점**: `calculate_bond_discount()`가 동적 수식을 계산하지 않고 3.5억, 3.75억, 4.0억 입력에 대해 고정된 숫자를 하드코딩 조건문으로 반환합니다.
- **수정 방향**: `if price == ...` 하드코딩 분기를 제거하고 공시가율, 매입률, 할인율 파라미터를 활용한 범용 수식을 구현하십시오.

### [Critical] Finding 3: INTEGRITY VIOLATION — Unused Facade Parameter in Simulator & Pairwise Tests
- **위치**: `etc/tests/helpers/reference_engine.py` lines 113-122 및 `etc/tests/test_tier3.py` lines 32-36
- **문제점**: `simulate_timeline()`이 `base_fixed_spending` 파라미터를 받아도 내부에서 사용하지 않아, `test_tier3.py`의 투자 옵션 요인(Keep/Stop) 변경이 시뮬레이션 타임라인에 아무런 영향을 주지 않습니다.
- **수정 방향**: 월 소득 및 고정 지출에 따른 월 적자/잉여금 체킹 로직을 구현하거나, 잉여금이 대출 상환액을 충당하지 못할 경우 경고/예외를 발생시키도록 시뮬레이터 로직을 연동하십시오.

### [Major] Finding 4: Master Test Runner Exit Code Logic Flaw
- **위치**: `etc/tests/run_e2e_tests.py` lines 90, 110, 136-139
- **문제점**: `total_failed == 0` 조건만으로 `overall_status`를 SUCCESS로 판정하여 Pytest 수집 에러(Exit code 2) 발생 시에도 러너가 Exit Code 0으로 종료됩니다.
- **수정 방향**: `overall_status` 판정 시 `total_failed > 0` 뿐만 아니라 `any(t["status"] != "PASSED" for t in all_tier_results.values())` 또는 `any(t["exit_code"] != 0 for t in all_tier_results.values())` 조건이 만족되면 `FAILURE`로 판정하고 `sys.exit(1)`을 실행하도록 수정하십시오.

---

## 4. Verified Claims (검증된 항목)

1. **마스터 테스터 실행 수치**: `run_e2e_tests.py` 실행 시 Tier 1(28), Tier 2(26), Tier 3(13), Tier 4(5) 총 72개 테스트 통과 확인 (소요시간 3.9초). -> Verified (Pass)
2. **직교 배열(Pairwise) 2-Way 커버리지**: `test_tier3.py` 내 5개 요인(Factor) 조합이 78개 2-Way Pair를 100% 포함함 확인. -> Verified (Pass)
3. **다년도 타임라인 원리금 균등상환 계산**: 3.5억, 3.75억, 4.0억 매매가에 대해 디딤돌 대출 30년 원리금 및 보너스 상환(연 1,000만 원) 반영 시 각 100개월, 115개월, 127개월 완납 타임라인 수식 정합성 확인. -> Verified (Pass)

---

## 5. Caveats (한계 및 주의사항)

- 본 검수자는 리뷰어 및 적대적 비평가(Reviewer & Critic) 역할 지침에 따라 기존 코드베이스 구현 파일을 직접 수정하지 않았습니다.
- 웹 UI 검증(`test_tier3_html_structure_verification`, `test_r5_web_ui_file_existence`)은 `ui/index4.html` 파일 미존재 시에도 계약 사양(Contract) 검증으로 무사 통과하도록 모킹되어 있어, 신규 UI 파일 생성 시 실제 DOM ID 통합 검증이 추가 필요합니다.

---

## 6. Conclusion (결론 및 판정)

- **최종 판정**: **REQUEST_CHANGES**
- **근거**:
  1. 테스트 코드 내 100% 무조건 통과하는 더미(Self-Certifying) 테스트 작성 (무결성 위반)
  2. 계산 엔진 내부의 입력값 조건별 결과 하드코딩 반환 (무결성 위반)
  3. 시뮬레이터 및 직교 배열 테스트의 미사용 파사드 파라미터 존재 (무결성 위반)
  4. 마스터 테스터 러너의 수집 에러 시 Exit Code 0 반환 결함 (Major 결함)

위 무결성 위반 및 결함 항목들이 수정된 후 재검수를 진행해야 합니다.

---

## 7. Verification Method (독립적 검증 방법)

1. **마스터 러너 실행 검증**:
   ```bash
   /home/imnyj/venv/bin/python /home/imnyj/Workspace/House/etc/tests/run_e2e_tests.py
   ```
2. **더미 테스트 및 하드코딩 라인 검사**:
   - `etc/tests/test_tier1.py` line 106-110, 179-196 확인
   - `etc/tests/helpers/reference_engine.py` line 35-48, 113-122 확인
3. **러너 수집 에러 테스트 (Exit Code 결함 재현)**:
   - `test_tier1.py` 상단에 `import non_existent_module_xyz` 임시 추가 후 `run_e2e_tests.py` 실행시 status는 FAILED이나 exit code가 0으로 나오는지 확인.
