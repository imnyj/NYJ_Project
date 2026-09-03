# Forensic Integrity Audit Report — Milestone 2: Data Engine & Resource Safety

**작성자**: Forensic Integrity Auditor (`teamwork_preview_auditor_m2_aud1`)  
**감사 일시**: 2026-09-02T20:28:45+09:00  
**감사 대상 모듈**:
- `modules/data/collector_price.py`
- `modules/data/collector_fundamental.py`
- `modules/data/consolidator.py`
- `modules/data/streamer.py`

**최종 감사 판정**: `CLEAN` (무결성 위반 없음 / Genuine Logic 검증 완료)

---

## 1. Observation (직접 관찰 및 사실 데이터)

1. **AST 정적 분석 및 파사드/하드코딩 탐색**:
   - `modules/data/collector_price.py`: 8개 클래스, 31개 함수/메서드 전수 조사. `validate_and_clean_ohlcv`에서 0 이하 비정상 가격의 NaN 치환, `ffill().bfill()`, 상호 컬럼 대체(fallback), 유효 양수 기본값(100.0) 할당 로직이 순수 알고리즘으로 구현되어 있으며, 특정 테스트 케이스에 대한 하드코딩된 분기문이 존재하지 않음.
   - `modules/data/collector_fundamental.py`: 12개 클래스, 52개 함수/메서드 전수 조사. `OpenDartCollector._parse_account_list`의 0원 영업이익 마진 계산(`stmt.operating_profit is not None` 및 `stmt.revenue != 0`), DART 전자공시 계정 파싱, 네이버 금융 모바일 테이블 JSON 파싱 및 단위 정규화(억원 -> 원)가 수학적/논리적으로 충실하게 구현됨.
   - `modules/data/consolidator.py`: 1개 클래스, 4개 메서드 전수 조사. `pd.merge_asof(..., by='symbol', direction='backward')` 및 공시일 누락 시 12월 결산 90일, 분기 결산 45일 차등 추정 함수(`_estimate_announcement`)가 완비되어 다중 종목 펀더멘털 교차 오염(BUG-L03) 및 선행 편향(Lookahead Bias)이 완전히 방어됨.
   - `modules/data/streamer.py`: 9개 클래스, 54개 함수/메서드 전수 조사. `CircularBuffer`의 `max_symbols` FIFO 퇴출(`del self._buffers[oldest_sym]`) 및 `remove_symbol()`, `NaverPollingStreamer`의 `stop()` 시 `self.session.close()` 및 `join(timeout=self.timeout + 1.0)`이 실제 리소스 정리 코드로 작성됨.

2. **위조 산출물 탐색 (Pre-populated Artifact Check)**:
   - 소스 코드 및 테스트 디렉토리 내에 사전 작성된 가짜 로그, 결과 위조 아티팩트가 일체 존재하지 않음을 확인.

3. **독립 런타임 스트레스 테스트 결과**:
   - 독립 작성된 4대 핵심 결함 스트레스 스크립트 실행:
     - `BUG-L02_OHLCV_Sanitization`: PASS (극단적 NaN, 음수, 0원 입력 시에도 저가 0원 왜곡 없음)
     - `BUG-L06_Zero_Profit_Margin`: PASS (0원 영업이익 시 0.0% 마진 정확히 산출, 0원 매출액 분모 0 방어)
     - `BUG-L03_PIT_Isolation`: PASS (다중 종목 3사 혼합 데이터셋에서 타사 EPS/BPS 교차 오염 0건)
     - `BUG-M01_M02_M03_Resource_Safety`: PASS (버퍼 종목 수 한도 유지, 10개 멀티스레드 동시성 안전성, 스트리머 정상 종료 확인)

4. **단위 및 통합 테스트 스위트 전수 실행**:
   - Milestone 2 관련 109개 테스트 케이스 전수 통과 (`109 passed in 8.85s`, 100% PASS).

---

## 2. Logic Chain (추론 과정 및 무결성 검증)

1. **BUG-L02 (저가 0원 왜곡 방어 로직의 진본성)**:
   - 관찰: `collector_price.py:754-771`에서 `df_clean[price_cols] <= 0`을 `np.nan`으로 변환한 후 전후방 보간(`ffill().bfill()`)과 컬럼 상호 fallback을 수행.
   - 추론: 특정 날짜나 특정 종목코드에 매칭하는 조건문 없이 모든 임의의 시계열 데이터프레임에 일반화되어 작동함.
   - 결론: 하드코딩이나 테스트 우회가 없는 진본(Genuine) 데이터 정제 알고리즘임.

2. **BUG-L06 (0원 영업이익 마진 계산의 진본성)**:
   - 관찰: `collector_fundamental.py:487-497`에서 `if stmt.revenue is not None and stmt.operating_profit is not None and stmt.revenue != 0:`로 명시적 분모/분자 유효성을 검증.
   - 추론: 0이 Falsy로 취급되던 파이썬 기본 동작을 `is not None`으로 올바르게 보정하여, 손익분기점 실적(0원)에 대해 정확히 `0.0` 마진을 산출함.
   - 결론: 더미 값이 아닌 정확한 산술 연산 로직임.

3. **BUG-L03 & Lookahead Bias 방어의 진본성**:
   - 관찰: `consolidator.py:118-185`에서 `by='symbol'` 병합 및 결산월/분기별 차등 공시일 추정 로직이 적용됨.
   - 추론: 다중 종목 펀더멘털 데이터가 입력되어도 타 종목의 최신 공시가 유입되지 않으며, 연간 보고서의 법정 공시 기한(90일)을 충실히 반영함.
   - 결론: 시계열 정합성과 데이터 분리가 완벽히 성립함.

4. **BUG-M01, M02, M03 (리소스 안전성의 진본성)**:
   - 관찰: 모든 클래스에 `__enter__`, `__exit__`, `close()`가 구현되어 있으며, `CircularBuffer`의 `max_symbols` 제한과 `NaverPollingStreamer`의 세션 닫기 및 스레드 조인이 실질적인 시스템 호출(`session.close()`, `thread.join()`)을 수행함.
   - 추론: no-op이나 껍데기 인터페이스가 아닌 실제 OS 소켓 및 스레드 자원을 해제함.
   - 결론: 장기 운용 시 메모리 및 스레드 누수 방어 확인됨.

---

## 3. Caveats (제약 사항 및 가정)

- OpenDART API 호출은 실제 API 키가 없을 경우 모의 수집기(`MockKiwoomCollector`) 또는 네이버 금융으로 안전하게 폴백되도록 설계되어 있습니다.
- 현재 코드베이스의 타 마일스톤(Milestone 3 RL 모델/GAE 등)에 존재하는 미수정 이슈는 Milestone 2 데이터 엔진의 무결성에 영향을 주지 않음을 확인하였습니다.

---

## 4. Conclusion (최종 판정)

- **최종 판정**: `CLEAN`
- **사유**: Milestone 2 Data Engine 및 Resource Safety 대상 4개 파일(`collector_price.py`, `collector_fundamental.py`, `consolidator.py`, `streamer.py`)의 모든 수정 사항은 치팅, 하드코딩, 더미 파사드, 테스트 우회 없이 완벽한 진본 로직(Genuine Logic)으로 구현되었음을 독립 검증함.

---

## 5. Verification Method (독립 검증 방법)

다음 명령어를 통해 포렌식 감사 대상 테스트 및 스트레스 테스트를 독립 재검증할 수 있습니다:

```bash
# 1. Milestone 2 전용 테스트 스위트 (109개 테스트)
/home/imnyj/venv/bin/pytest tests/test_consolidator.py tests/test_fundamental.py tests/test_price_streamer.py tests/test_m2_data_engine_safety.py tests/test_m2_adversarial_stress.py -v

# 2. 독립 챌린저 스트레스 테스트 스크립트 실행
/home/imnyj/venv/bin/python3 etc/scripts/m2_challenger2_stress_test.py
```
