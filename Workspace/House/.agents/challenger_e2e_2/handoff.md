# E2E Test Suite Adversarial Review & Falsification Handoff Report

**최종 판정**: **REJECT (반려)**  
**작성자**: `challenger_e2e_2` (Empirical Challenger)  
**일시**: 2026-08-12  

---

## 1. Observation (직접 관찰 및 검증 결과)

본 검증에서는 E2E 테스트 스위트의 파서(`etc/tests/helpers/html_parser.py`, `report_parser.py`) 및 테스트 러너(`etc/tests/run_e2e_tests.py`), 그리고 테스트 스위트(`test_tier1.py` ~ `test_tier4.py`)를 대상으로 적대적(Adversarial) 테스트 코드를 작성하고 실측 실행을 완료하였습니다.

### 관찰 1.1: 테스트 러너(`run_e2e_tests.py`)의 Pytest 컬렉션/구문 에러 은폐 결함
* **대상 파일**: `etc/tests/run_e2e_tests.py` 라인 90-110 및 136-139
* **관찰 내용**:
  * 일반적인 `assert` 실패 시에는 pytest 출력 결과 중 `failed` 수를 정상 인식하여 Exit Code `1`을 반환함을 확인하였습니다 (`test_falsify_runner.py` 실행 결과: `Exit Code: 1`).
  * **그러나**, 테스트 파일에 `SyntaxError`, `ImportError` 등 컬렉션 단계 오류가 발생할 경우 pytest stdout은 `0 passed, 0 failed`를 출력합니다.
  * `run_e2e_tests.py` 라인 110: `overall_status = "SUCCESS" if total_failed == 0 else "FAILURE"` 조건식에 따라 `total_failed`가 0이므로 `overall_status`를 `"SUCCESS"`로 오판정합니다.
  * 라인 136: `if total_failed > 0 or overall_status != "SUCCESS":` 조건문이 거짓이 되어 `sys.exit(0)`을 호출하고 성공으로 종료됩니다.
* **실측 실증**: `test_falsify_runner.py`의 `test_collection_error_exit_code()` 구문 오류 발생 실험 결과:
  ```text
  [FAILED] test_tier4.py: 0 passed, 0 failed, 0 skipped (Total: 0)
  OVERALL RESULT: SUCCESS
  Total: 3 | Passed: 3 | Failed: 0 | Skipped: 0
  Summary: Collection Error Exit Code=0
  ```

### 관찰 1.2: 정적 HTML 파서(`html_parser.py`)의 오탐 및 예외 처리 결함
* **대상 파일**: `etc/tests/helpers/html_parser.py`
* **관찰 내용**:
  * **DOM ID 부분 문자열 오탐**: 라인 47 `elem = soup.find(id=lambda x: x and elem_id.replace("-", "") in x.replace("-", "").replace("_", ""))` 로직으로 인해, 실제 입력 슬라이더 `#price-slider` 대신 래퍼 태그 `<div id="price-slider-wrapper-div">`만 존재해도 `dom_id_status['price-slider'] = True`로 판정합니다.
  * **UI 스타일 서브스트링 오탐**: 라인 60 `"dark" in html_content.lower()` 및 라인 64 `"rgba" in html_content.lower()` 구문으로 인해, 주석 `<!-- dark mode not supported -->` 또는 기본 CSS의 `color: rgba(0,0,0,1)` 구문만 있어도 `dark_mode_found = True` 및 `glassmorphism_found = True`로 잘못 판단합니다.
  * **인코딩/이진 파일 예외 미처리**: `open(html_path, "r", encoding="utf-8")`에 `try...except` 예외 처리 블록이 없어 비 UTF-8/손상된 이진 파일 입력 시 `UnicodeDecodeError`가 발생하며 크래시됩니다.

### 관찰 1.3: 정적 보고서/예산 파서(`report_parser.py`)의 하드코딩 스텁 결함
* **대상 파일**: `etc/tests/helpers/report_parser.py`
* **관찰 내용**:
  * **Budget 파서 스텁화**: `parse_budget_reference()` 함수는 마크다운 파일 내용을 실제로 수치 계산하지 않고, 라인 29-35에 `monthly_income: 3300000`, `total_living_expenses: 2390708`, `categories_count: 13` 등을 하드코딩하여 반환합니다. 마크다운 파일이 완전히 비어있거나 행이 삭제되어도 하드코딩된 정상 값을 그대로 반환합니다.
  * **Report 파서 키워드 단순 포함 검사**: `parse_report_markdown()`은 파일 내 단순 문자열 포함 여부만 검사합니다. `# 3.5억 3.75억 4.0억 잔금 등기 취득세 전입신고 확정일자 재산세` 와 같이 내용이나 표가 전혀 없는 1줄 제목 파일도 `has_scenarios` 및 `checklist_complete = True`로 판정합니다.

### 관찰 1.4: 테스트 스위트(`test_tier1.py`, `test_tier3.py`)의 파일 미존재 시 조건문 우회 패턴
* **대상 파일**: `etc/tests/test_tier1.py` (라인 203, 220, 228, 235), `test_tier3.py` (라인 154)
* **관찰 내용**:
  * UI 파일(`ui/index4.html`)이 존재하지 않을 때 `parsed["exists"]`가 `False`가 되며, `if parsed["exists"]:` 조건문 내부의 단증(assertion) 구문이 실행되지 않고 통과(PASS) 처리됩니다.
  * 이로 인해 UI 파일이 완전히 누락된 상태에서도 `test_tier1.py`의 R5 검증 테스트 4개가 모두 정상 성공으로 통과하는 착시 현상이 발생합니다.

---

## 2. Logic Chain (추론 및 분석 체인)

1. **테스트 러너 결함 추론**:
   * `run_e2e_tests.py`는 `pytest` 결과를 표준 출력(stdout) 텍스트 정규식으로 파싱하여 결과를 종합함.
   * `pytest`가 구문 오류, 모듈 임포트 실패 등으로 테스트를 1개도 실행하지 못하면 `failed` 카운트는 0으로 계산됨.
   * 테스트 러너는 `total_failed == 0` 조건을 기준으로 전체 성공(`SUCCESS`)으로 간주하여 Exit Code `0`을 반환함.
   * 따라서, CI/CD 환경 또는 커밋 전 검증에서 테스트 코드 손상/컬렉션 실패가 발생하더라도 테스트 러너가 통과(0)로 오인하여 결함이 배포될 수 있음.

2. **파서 오탐 및 스텁 추론**:
   * `html_parser.py`는 DOM ID 검색 시 하위 부분 문자열 일치를 허용하여 DOM 구조 수정을 제대로 검증하지 못함.
   * `report_parser.py`는 실제 동적 파싱을 수행하지 않고 상수 값을 반환하는 스텁 구조이므로 문서 훼손이나 표 항목 누락을 감지할 수 없음.

3. **테스트 스위트 우회 추론**:
   * UI 및 보고서 검증 시 `if parsed["exists"]:` 블록으로 assertion을 감싸놓아 대상 파일이 없으면 단증 없이 함수가 종료되어 성공으로 기록됨.
   * 이로 인해 파일이 없어도 테스트가 100% 통과하는 심각한 안티패턴이 존재함.

---

## 3. Caveats (한계 및 제약 사항)

* 기존 72개 테스트 케이스 자체는 정상 입력 데이터에 대해 모두 통과(PASSED)하고 있으며 계산 엔진(`reference_engine.py`)의 산술 로직 자체는 안정적입니다.
* 본 검증에서 발견된 결함은 계산 엔진 로직보다는 **테스트 러너의 에러 처리, 파서의 검증 엄밀성, 테스트 통과 조건**의 구조적 결함에 집중되어 있습니다.

---

## 4. Conclusion (결론 및 판정)

* **판정**: **REJECT (반려)**
* **반려 사유 Summary**:
  1. `run_e2e_tests.py`: pytest 컬렉션/구문 에러 발생 시 Exit Code 0 및 SUCCESS를 반환하여 테스트 실패를 묵인하는 치명적 결함.
  2. `report_parser.py`: budget 파서가 하드코딩된 값을 반환하는 스텁으로 작성되어 문서 훼손 감지 불가능.
  3. `html_parser.py`: DOM ID 래퍼 오탐 및 스타일 정규식 오탐으로 인해 부실한 HTML 구조 통과.
  4. `test_tier1.py` / `test_tier3.py`: UI 파일 미존재 시 `if parsed["exists"]:` 우회로 인해 검증 없이 성공 처리.

* **권장 조치 사항 (Action Items)**:
  * `run_e2e_tests.py`: `subprocess.run`의 `result.returncode != 0` 또는 `tier_results` 중 단 하나라도 `status == "FAILED"`인 경우 `overall_status = "FAILURE"` 및 `sys.exit(1)` 처리하도록 수정.
  * `report_parser.py`: 예산 표의 카테고리 행 수 및 금액 합계를 실제 마크다운 표에서 동적 파싱하여 정합성 검증하도록 수정.
  * `html_parser.py`: 정확한 DOM ID 매칭(`elem_id == id`) 적용 및 단순 주석 내 키워드가 아닌 실제 CSS/DOM 구조 분석 적용.
  * `test_tier1.py` / `test_tier3.py`: UI 파일 미존재 시 `pytest.skip()` 또는 `pytest.fail("ui/index4.html not found")`로 명시적 처리.

---

## 5. Verification Method (재검증 및 실증 방법)

다음 명령어를 통해 본 보고서의 결함을 독립적으로 재현 및 검증할 수 있습니다:

1. **테스트 러너 Falsification 재검증**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Workspace/House/.agents/challenger_e2e_2/test_falsify_runner.py
   ```
   * **기대 결과**: `Summary: Assertion Failure Exit Code=1, Collection Error Exit Code=0` 출력 확인.

2. **파서 적대적 검증 및 하드코딩 스텁 재검증**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Workspace/House/.agents/challenger_e2e_2/test_adversarial_parsers.py
   ```
   * **기대 결과**:
     * HTML 파서 래퍼 ID 오탐 (`price-slider-wrapper-div`에 대해 True 반환)
     * HTML 파서 주석/기본 CSS 오탐 (`dark_mode_found=True`, `glassmorphism_found=True`)
     * Budget 파서 빈 파일 입력에도 `total_living_expenses: 2390708` 반환 확인

3. **전체 테스트 스위트 기본 실행**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Workspace/House/etc/tests/run_e2e_tests.py
   ```
