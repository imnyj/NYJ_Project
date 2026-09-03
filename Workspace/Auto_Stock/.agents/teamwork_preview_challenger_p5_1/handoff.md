# Adversarial Challenge Handoff Report: Phase 5 Dynamic Stock Screener

- **작성 일시**: 2026-09-03T10:30:00+09:00
- **담당자**: Phase 5 Adversarial Challenger (`teamwork_preview_challenger_p5_1`)
- **수신자**: Orchestrator / Sentinel (`4361a64e-415a-4de5-81f3-8b8d281253cd`)
- **검증 대상**: `modules/data/screener.py` (`StockScreener`, `ScreeningCriteria`)
- **최종 판정**: **`REJECT` (보완 후 재승인 필요)**

---

## 1. Observation (직접 관찰 사실)

실측 검증 하네스 스크립트(`/home/imnyj/Workspace/Auto_Stock/etc/scripts/phase5_screener_adversarial_stress_suite.py`)를 작성하여 총 11개 극한/적대적 테스트 케이스를 실행한 결과, **7개 통과(PASS)**, **4개 결함 발견(FAIL)**을 직접 관측하였습니다.

```bash
/home/imnyj/venv/bin/python etc/scripts/phase5_screener_adversarial_stress_suite.py
```

### 1.1 Verbatim 실행 결과 요약
```text
Total Tests Executed: 11
Verified Robust: 7
Empirical Vulnerabilities Discovered: 4

✅ PASS - 1.1_Dirty_Data_Exclusion
❌ FAIL - 1.2_MarketCap_Inf_Leakage_Vulnerability
✅ PASS - 1.3_Large_Universe_10k_Performance
❌ FAIL - 1.4_MegaCap_EokWon_Unit_Conversion_Limit
✅ PASS - 2.1_Adversarial_Tick_Defenses
❌ FAIL - 2.2_String_Baseline_Volume_TypeError_Vulnerability
❌ FAIL - 2.3_OverflowError_Vulnerability
✅ PASS - 3.1_One_Million_Ticks_Debounce
✅ PASS - 3.2_Cooldown_Timeline_Debounce_Precision
✅ PASS - 4.1_50_Threads_Concurrency_and_Deadlock
✅ PASS - 5.1_TokenBucket_Thread_Throttling
```

### 1.2 발굴된 결함 관찰 사실 (Exact Quotes & Stack Traces)

#### [결함 1] `modules/data/screener.py:400` — 문자열 `baseline_volume` 주입 시 `TypeError` 미처리 크래시
- **재현 코드**:
  ```python
  tick = {"symbol": "000660", "price": 105000, "open_price": 100000, "accum_volume": 40000, "prev_same_time_volume": "10000"}
  screener.check_intraday_trigger(tick)
  ```
- **Verbatim 예외 출력**:
  ```text
  Caught exception: <class 'TypeError'> '<=' not supported between instances of 'str' and 'int'
  Traceback (most recent call last):
    File "/home/imnyj/Workspace/Auto_Stock/modules/data/screener.py", line 400, in check_intraday_trigger
      if base_vol is None or base_vol <= 0 or math.isnan(base_vol) or math.isinf(base_vol):
                             ^^^^^^^^^^^^^
  TypeError: '<=' not supported between instances of 'str' and 'int'
  ```
- **관찰 내용**: `price`와 `accum_volume`은 각각 372~376행, 391~394행에서 `try...except (ValueError, TypeError)`로 안전하게 형변환되나, `base_vol`은 수치 변환 없이 즉시 `<= 0` 비교를 수행하여 키움증권 REST/WebSocket의 문자열 JSON 데이터 유입 시 즉시 런타임 크래시가 발생함.

#### [결함 2] `modules/data/screener.py:373, 392, 409` — 무한대/초대형 수치 주입 시 `OverflowError` 미처리 크래시
- **재현 코드**:
  ```python
  tick_inf = {"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": float("inf"), "prev_same_time_volume": 10000}
  screener.check_intraday_trigger(tick_inf)
  ```
- **Verbatim 예외 출력**:
  ```text
  Crash for inf volume: <class 'OverflowError'> cannot convert float infinity to integer
  Traceback (most recent call last):
    File "/home/imnyj/Workspace/Auto_Stock/modules/data/screener.py", line 392, in check_intraday_trigger
      accum_vol = int(accum_raw)
                  ^^^^^^^^^^^^^^
  OverflowError: cannot convert float infinity to integer
  ```
- **추가 관찰**: `accum_volume = 10**400` 또는 `price = 10**400` 유입 시 `OverflowError: int too large to convert to float` 발생. 예외 포획 구문이 `(ValueError, TypeError)`로만 한정되어 있어 `OverflowError`가 상위로 전파되어 프로세스를 중단시킴.

#### [결함 3] `modules/data/screener.py:240` — `market_cap = np.inf` 누수 및 시총 1위 우선순위 탈취
- **재현 코드**:
  ```python
  df_inf = pd.DataFrame([{"symbol": "000016", "market_cap": np.inf, "per": 10.0, "pbr": 1.0}])
  pool = screener.update_daily_static_pool(df_inf)
  ```
- **Verbatim 관찰 결과**:
  `pool = ['000016']` (정상 필터링 실패, 풀 진입 성공).
- **관찰 내용**: 247행(`per`)과 257행(`pbr`)에는 `~np.isinf()` 검증이 존재하지만, 240행의 `market_cap`에는 `~np.isinf()`가 누락되어 `np.inf >= 100_000_000_000`가 `True`로 평가됨. 정렬 시(`ascending=False`) `np.inf`가 최상단에 배치되어 비정상 오염 종목이 감시 풀 **1순위**로 등록됨.

#### [결함 4] `modules/data/screener.py:236~239` — '억원' 단위 입력 시 메가캡(100조 원 이상) 존재 시 전 종목 탈락 결함
- **재현 코드**:
  ```python
  df_eok = pd.DataFrame([
      {"symbol": "005930", "market_cap": 5_000_000, "per": 10.0, "pbr": 1.0}, # 삼성전자 500조 원 (500만 억원)
      {"symbol": "000660", "market_cap": 1_500_000, "per": 12.0, "pbr": 1.5}, # SK하이닉스 150조 원 (150만 억원)
      {"symbol": "068270", "market_cap": 5_000, "per": 8.0, "pbr": 0.8},     # 셀트리온 5천억 원 (5,000 억원)
  ])
  pool = screener.update_daily_static_pool(df_eok)
  ```
- **Verbatim 관찰 결과**:
  `pool = []` (기대값: 3개 종목 모두 1,000억 원 이상이므로 선정되어야 하나 0개 선정).
- **관찰 내용**: 238행 `if 0 < max_cap < 1_000_000:` 조건으로 인해, 100조 원 이상 종목(삼성전자 500만 억원, 하이닉스 150만 억원)이 데이터셋에 포함되면 `max_cap >= 1,000,000`이 되어 1억 곱연산 변환이 스킵됨. 이후 240행에서 `5,000,000 >= 100,000,000_000` 비교로 인해 **시장 전체 종목이 일괄 탈락**하여 감시 풀이 비어버림.

### 1.3 견고성이 실측 증명된 정상 항목 (Robust Metrics)
- **초고빈도 100만 회 틱 주입 및 디바운스 실측**:
  - 총 주입 틱: **1,000,000건** (동일 종목 폭증 틱)
  - 소요 시간: **0.886초** (처리량: **1,128,296 ticks/sec**)
  - 트리거 횟수: **정확히 1회** (디바운스 100% 차단 성공, 불필요한 이벤트 999,999건 억제)
  - `_triggered_history` 메모리 크기: **1개** (불필요한 누적 없음)
- **타임라인 정밀도**:
  - $t=0.0s$ (True) $\to$ $t=59.9s$ (False) $\to$ $t=60.1s$ (True) $\to$ $t=120.2s$ (True) 정확히 일치.
- **대규모 50개 스레드 동시성 및 무데드락 실측**:
  - 50개 스레드(틱 주입 25, 풀 갱신 15, 청크 분할 5, 읽기 5) 동시 3.1초 가동.
  - 처리 건수: 틱 36,964건, 풀 갱신 925건, 청크 분할 336건, 읽기 307건.
  - 발생 예외: **0건**, 데드락: **False** (`threading.RLock` 기반 Thread-Safe 증명).
- **대규모 유니버스 필터링 성능**:
  - 10,000행 무작위 데이터프레임 필터링 및 상위 200개 종목 슬라이싱 소요 시간: **11.28ms** (0.011초).

---

## 2. Logic Chain (논리적 추론 체인)

1. **실시간 트레이딩 환경에서의 크래시 위험성 (Observation 1.2 결함 1, 결함 2)**:
   - 증권사 REST API 및 WebSocket(JSON/Text 스트림) 통신 시, 숫자형 필드는 문자열(예: `"acml_vol": "10000"`, `"stck_prpr": "70000"`)로 역직렬화되는 경우가 빈번함.
   - 400행의 `base_vol <= 0`은 `str`과 `int` 비교로 즉시 `TypeError`를 발생시키며, `float('inf')` 주입 시 `int(accum_raw)`는 `OverflowError`를 발생시킴.
   - 이는 실시간 스크리닝 백그라운드 스레드를 중단시켜 트레이딩 시스템 전체의 호가 수신 루프를 마비시킬 수 있는 치명적 결함임.
2. **이상 데이터 유입 시 포트폴리오 왜곡 (Observation 1.2 결함 3)**:
   - 시가총액 결측이나 데이터 피드 손상으로 `market_cap`에 `inf`가 주입될 경우, 240행에서 걸러지지 않고 풀에 진입함.
   - 시총 내림차순 정렬 로직(289행)에 의해 `inf` 종목이 **전체 감시 종목 중 1위**를 차지하게 되어, 강화학습 에이전트에 가짜 최우선 매수 후보로 전달됨.
3. **국내 주식시장 펀더멘털 단위 규격 불일치 (Observation 1.2 결함 4)**:
   - 국내 금융 데이터 제공사(DART, FnGuide, 네이버증권 등)는 시가총액을 주로 '억원' 단위로 표기함.
   - KOSPI 시총 1위 삼성전자는 약 500조 원(5,000,000 억원), 2위 SK하이닉스는 약 150조 원(1,500,000 억원)임.
   - `0 < max_cap < 1_000_000` 휴리스틱은 100조 원 미만 시장에서만 동작하며, 국내 대표주가 포함되는 순간 전 종목이 탈락하여 스크리너가 아무런 종목도 발굴하지 못하는 침묵의 실패(Silent Catastrophic Failure)를 초래함.

---

## 3. Caveats (한계 및 주의사항)

- **Worker의 기존 테스트 스위트 100% 통과와의 관계**:
  - `tests/test_phase5_screener.py`의 18개 테스트는 모두 정수형/실수형의 정형 데이터로만 작성되어 있어 상기 결함들이 기존 단위 테스트에서 감지되지 않았습니다. 이는 엣지 케이스 및 적대적 입력 커버리지의 부재를 의미합니다.
- **제안된 수정의 비파괴성**:
  - 식별된 결함들은 모두 단순한 형변환 검증(`try-except`), 무한대 마스크(`~np.isinf`), 단위 변환 상한선 확장(`max_cap < 10_000_000`)으로 기존 API 명세(SCOPE.md)를 전혀 훼손하지 않고 완전한 하위 호환성을 유지하며 수정 가능합니다.

---

## 4. Conclusion (최종 결론)

Auto_Stock Phase 5의 `modules/data/screener.py`는 초당 112만 회의 틱 처리 성능과 50개 스레드 동시 가동 시의 데드락 방어력 등 핵심 아키텍처 측면에서 높은 잠재력을 보유하고 있습니다.

그러나, **(1) 문자열 입력 시 즉시 크래시(`TypeError`)**, **(2) 무한대 수치 시 즉시 크래시(`OverflowError`)**, **(3) 시총 `inf` 누수 및 1위 탈취**, **(4) '억원' 단위 메가캡 시 전 종목 탈락**이라는 4건의 명백하고 실측 재현 가능한 결함이 확인되었습니다.

따라서 본 챌린저는 현 구현체에 대해 **`REJECT` (보완 후 재승인)** 판정을 내리며, 아래의 구체적 조치 사항을 반영한 후 재검증을 진행할 것을 강력히 권고합니다.

### 권고 조치 사항 (Actionable Fixes for Worker):
1. **`check_intraday_trigger` (Line 372~410)**:
   - `base_vol`을 수치 비교 전에 `try: base_vol = float(base_vol) if base_vol is not None else None except (ValueError, TypeError, OverflowError): return None`로 안전 변환.
   - 모든 수치 형변환 블록의 예외 포획을 `except (ValueError, TypeError, OverflowError):`로 확장.
2. **`update_daily_static_pool` (Line 236~240)**:
   - 238행의 억원 단위 판별 상한을 `if 0 < max_cap < 10_000_000:`(1,000조 원)으로 확장.
   - 240행 시가총액 필터에 `& (~np.isinf(df["market_cap"])) & (df["market_cap"] > 0)` 추가.

---

## 5. Verification Method (독립 검증 방법)

오케스트레이터 및 감사관은 다음 명령어를 통해 4건의 결함과 실측 성능을 즉시 재현 및 검증할 수 있습니다:

```bash
# 적대적 실측 검증 하네스 전수 실행
/home/imnyj/venv/bin/python etc/scripts/phase5_screener_adversarial_stress_suite.py
```
- **예상 결과**: 결함 미수정 상태에서는 종료 코드 `1`, 4개 FAIL 출력. 수정 후에는 종료 코드 `0`, 11개 PASS 출력.

```bash
# 결함 1 (TypeError) 직접 단독 재현
/home/imnyj/venv/bin/python -c '
from modules.data.screener import StockScreener
s = StockScreener()
s.candidate_pool = ["000660"]
s.candidate_set = {"000660"}
s.check_intraday_trigger({"symbol": "000660", "price": 105000, "open_price": 100000, "accum_volume": 40000, "prev_same_time_volume": "10000"})
'
```

```bash
# 결함 2 (OverflowError) 직접 단독 재현
/home/imnyj/venv/bin/python -c '
from modules.data.screener import StockScreener
s = StockScreener()
s.candidate_pool = ["005930"]
s.candidate_set = {"005930"}
s.check_intraday_trigger({"symbol": "005930", "price": 75000, "open_price": 70000, "accum_volume": float("inf"), "prev_same_time_volume": 10000})
'
```
