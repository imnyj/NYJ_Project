# Handoff Report — Reviewer 2: Milestone 2 (Data Engine & Resource Safety)

**작성자**: Reviewer 2 (`teamwork_preview_reviewer_m2_rev2`)  
**검증 일시**: 2026-09-02T20:27:00+09:00  
**최종 판정**: **`APPROVE`** (승인)

---

## 1. Observation (직접 관찰 및 사실 데이터)

1. **테스트 스위트 실행 결과**:
   - 실행 명령어:
     ```bash
     /home/imnyj/venv/bin/pytest tests/test_consolidator.py tests/test_fundamental.py tests/test_price_streamer.py tests/test_m2_data_engine_safety.py tests/test_phase1.py -v
     ```
   - 결과 요약: **125 passed in 10.17s (100% PASS)**
   - 개별 테스트 통과 항목:
     - `tests/test_m2_data_engine_safety.py`:
       - `test_validate_and_clean_ohlcv_nan_does_not_corrupt_low_to_zero` PASSED
       - `test_validate_and_clean_ohlcv_zero_or_negative_sanitized` PASSED
       - `test_price_fetcher_and_collector_context_manager` PASSED
       - `test_zero_operating_profit_and_margin_calculation` PASSED
       - `test_mock_kiwoom_collector_zero_profit_ratios` PASSED
       - `test_fundamental_collectors_context_manager` PASSED
       - `test_multi_stock_fundamental_no_cross_contamination` PASSED
       - `test_consolidator_empty_symbol_filtered_fundamentals` PASSED
       - `test_lookahead_bias_announcement_date_differential_estimation` PASSED
       - `test_circular_buffer_max_symbols_eviction_and_remove` PASSED
       - `test_circular_buffer_clear_specific_symbol_and_all` PASSED
       - `test_naver_polling_streamer_stop_and_close` PASSED
       - `test_pipeline_context_manager` PASSED

2. **소스 코드 정밀 점검 결과 (라인별 실측)**:
   - **`modules/data/collector_price.py` (BUG-L02, BUG-M01)**:
     - 라인 754-771: `price_cols = ['open', 'high', 'low', 'close']`에 대해 0 이하 비정상 값을 `NaN`으로 변환 후, `ffill().bfill()` 및 상호 컬럼 대체(fallback), 그리고 최종 양수 기본값(100.0) 할당 로직이 적용됨.
     - 라인 776-785: 정제된 컬럼들로부터 `computed_high = max(...)`, `computed_low = min(...)`를 재계산하여 `low`가 0원으로 왜곡되는 결함(BUG-L02)이 원천 차단됨.
     - 라인 96-105, 132-145, 515-530: `BasePriceFetcher`, `NaverPriceFetcher`, `PriceDataCollector`에 `close()` 및 `__enter__`, `__exit__` 컨텍스트 매니저가 완전 구현되어 `requests.Session` 소켓 누수(BUG-M01)가 해결됨.
   - **`modules/data/collector_fundamental.py` (BUG-L06, BUG-M01)**:
     - 라인 487-497: `_parse_account_list`에서 `if stmt.revenue is not None and stmt.operating_profit is not None and stmt.revenue != 0:`로 명시적 `None` 및 `revenue != 0` 체크를 수행하여 영업이익 0원(손익분기점) 시 `op_margin = 0.0`으로 정상 산출됨(BUG-L06).
     - 라인 234-243, 341-354, 581-594, 1171-1184: 모든 펀더멘털 수집기 및 파사드에 `close()` 및 컨텍스트 매니저가 구현됨.
   - **`modules/data/consolidator.py` (BUG-L03, Lookahead Bias)**:
     - 라인 112-116, 172-180: `symbol`별 엄격한 사전 필터링 및 `pd.merge_asof(..., by='symbol', direction='backward')`를 적용하여 다중 종목 펀더멘털 교차 오염(BUG-L03)을 차단함.
     - 라인 118-145: `announcement_date` 누락 시 12월 결산 보고서는 90일, 3/6/9월 분기 보고서는 45일로 공시 기한을 차등 추정하여 선행 편향(Lookahead Bias)을 방어함.
   - **`modules/data/streamer.py` (BUG-M02, BUG-M03)**:
     - 라인 771-785: `NaverPollingStreamer.stop()`에서 `self._stop_event.set()`, `self.session.close()`, `self._thread.join(timeout=max(2.0, self.timeout + 1.0))`를 적용하여 좀비 스레드 누수(BUG-M02)를 방지함.
     - 라인 154-175: `CircularBuffer`에 `max_symbols` 한도 기반 FIFO 퇴출 및 `remove_symbol(symbol)`, `clear(symbol)`를 구현하여 종목 수 무한 증식 메모리 누수(BUG-M03)를 차단함.

3. **무결성 검증 (Integrity Verification)**:
   - 하드코딩된 테스트 결과 반환 여부: 없음 (실제 벡터 연산, 정규표현식, HTTP 요청 및 락 동기화 수행).
   - 더미/가짜 구현체(Facade bypass) 여부: 없음 (실제 비즈니스 로직 완전 구현).
   - GEMINI.md 락 매니저 및 감사 로깅 원칙 준수 확인.

---

## 2. Logic Chain (추론 과정 및 검증 논리)

1. **결측치 정제 및 가격 모순 교정 논리 (BUG-L02)**:
   - 관찰: 기존 코드는 결측치에 `fillna(0.0)`를 바로 적용하여 `computed_low = min(open, high, low, close)` 시 정상 양수 `low`까지 0.0원으로 덮어썼음.
   - 검증: 수정 코드는 0 이하 및 NaN을 결측으로 분리 처리하고 시계열 전후방 유효값(`ffill().bfill()`) -> 타 가격 컬럼 -> 양수 기본값(100.0) 순으로 안전 보정 후 `min/max`를 계산함.
   - 결론: 0원 왜곡이 발생하지 않으며, 비정상 음수/결측 가격이 유효 양수 시계열로 완벽히 정제됨.

2. **0원 영업이익 손익분기점 마진 산출 논리 (BUG-L06)**:
   - 관찰: 파이썬에서 `operating_profit == 0`은 Falsy이므로 `if stmt.operating_profit:` 조건문에서 스킵되었음.
   - 검증: `is not None` 및 `revenue != 0` 분모 0 방어 조건을 도입하여 `0 / revenue * 100 = 0.0`으로 정상 할당됨.
   - 결론: 손익분기 기업의 영업이익률 및 순이익률이 `None`으로 소실되지 않고 정확한 0.0% 지표로 보존됨.

3. **다중 종목 PIT 병합 및 공시일 차등 추정 논리 (BUG-L03 & Lookahead Bias)**:
   - 관찰: `merge_asof`에 `by='symbol'`이 없으면 주가 시점 직전의 타 종목 최신 공시가 병합되는 교차 오염이 발생했음. 또한 일률적 45일 추정은 12월 결산 사업보고서(법정 기한 90일)에 대해 45일간의 선행 편향을 유발했음.
   - 검증: `by='symbol'` 인자 전달 및 `symbol` 사전 필터링으로 종목 간 데이터가 완벽히 격리되며, 12월 결산은 90일, 분기는 45일로 자본시장법 공시 규정을 충실히 반영함.
   - 결론: 과거 시점 백테스팅 및 RL 피처 생성 시 미래 정보 누출 및 교차 종목 오염이 원천 차단됨.

4. **소켓 누수, 스레드 수명주기, 버퍼 메모리 한도 논리 (BUG-M01, BUG-M02, BUG-M03)**:
   - 관찰: `requests.Session()` 미해제 시 OS 소켓 누수, `join` 타임아웃 미달 시 좀비 스레드 잔존, 스트리머 버퍼 무제한 증식 위험이 존재했음.
   - 검증: 전 클래스에 `close()` 및 Context Manager가 제공되고, `stop()` 시 소켓 강제 종료 및 `timeout + 1.0`초 보장 대기를 수행하며, `CircularBuffer`는 `max_symbols` FIFO 퇴출을 수행함.
   - 결론: 장기 운용 및 24/7 고빈도 스트리밍 환경에서 안정적인 자원 관리가 성립함.

---

## 3. Caveats (제약 사항 및 특이 사항)

1. **`_estimate_announcement` 엣지 케이스 (Minor Finding)**:
   - `modules/data/consolidator.py`의 `_estimate_announcement` 내부에서 `row.get('quarter') in (4, None)` 구문은 DataFrame에 `quarter` 컬럼 자체가 누락된 경우 `row.get('quarter')`가 `None`을 반환하여 분기 보고서임에도 연간(90일)으로 추정될 수 있습니다.
   - 다만 `FinancialStatement.to_dict()`나 `FundamentalDataCollector` 파이프라인 표준 객체를 통해 생성된 데이터프레임에는 이미 `announcement_date`가 사전에 계산되어 입력되므로 실 운영 파이프라인에는 영향을 미치지 않습니다. 추후 리팩토링 시 `row.get('quarter') == 4`로 조건을 더 정밀화할 것을 권장합니다.
2. **외부 비공식 API 의존성**:
   - 네이버 금융 실시간 시세 및 DART 전자공시 엔드포인트는 외부 네트워크 상태 및 API 스키마 변경에 의존하므로, 연결 실패 시 자동 활성화되는 Mock 수집기 Fallback 체계를 상시 유지해야 합니다.

---

## 4. Conclusion (최종 평가 및 판정)

- **최종 판정**: **`APPROVE` (승인)**
- **평가 요약**:
  - Milestone 2 Data Engine 및 Resource Safety 6대 결함(BUG-L02, BUG-L06, BUG-L03, BUG-M01, BUG-M02, BUG-M03)이 모두 엄격하게 수정 및 검증되었습니다.
  - 관련 단위/통합/안전성 테스트 125개 케이스가 100% 통과되었습니다.
  - 무결성 위반(하드코딩, 더미 구현체 등)이 일체 없으며, 코드 품질과 예외 처리가 견고합니다.

---

## 5. Verification Method (독립 검증 방법)

다음 명령어를 통해 데이터 엔진 및 안전성 테스트 스위트를 즉시 독립 검증할 수 있습니다:

```bash
/home/imnyj/venv/bin/pytest tests/test_consolidator.py tests/test_fundamental.py tests/test_price_streamer.py tests/test_m2_data_engine_safety.py tests/test_phase1.py -v
```

추가 적대적 스트레스 테스트 실행:
```bash
PYTHONPATH=. /home/imnyj/venv/bin/python etc/scripts/adversarial_m2_verifier.py
```
