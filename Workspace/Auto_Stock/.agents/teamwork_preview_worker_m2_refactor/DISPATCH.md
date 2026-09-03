## 2026-09-02T11:18:03Z

당신은 Auto_Stock 프로젝트의 Milestone 2: Data Engine & Resource Safety 리팩토링 및 결함 수정을 전담하는 Worker 에이전트입니다.

### 작업 환경 및 메타데이터
- 프로젝트 루트: `/home/imnyj/Workspace/Auto_Stock`
- 에이전트 작업 디렉토리: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2_refactor`
- 원본 사용자 요구사항: `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- 프로젝트 계획 및 결함 카탈로그: `/home/imnyj/Workspace/Auto_Stock/PROJECT.md`
- 시스템 조사 보고서: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_sys_1/analysis.md`
- ML 조사 보고서: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_ml_1/analysis.md`

### 수정 대상 파일 (Write Ownership)
1. `/home/imnyj/Workspace/Auto_Stock/modules/data/collector_price.py`
2. `/home/imnyj/Workspace/Auto_Stock/modules/data/collector_fundamental.py`
3. `/home/imnyj/Workspace/Auto_Stock/modules/data/consolidator.py`
4. `/home/imnyj/Workspace/Auto_Stock/modules/data/streamer.py`

### 필수 작업 내역
1. **`modules/data/collector_price.py`**:
   - **BUG-L02**: `validate_and_clean_ohlcv`에서 가격 컬럼 결측치를 `fillna(0.0)`으로 처리하여 `computed_low = min(open, high, low, close)`가 유효한 low 가격을 0.0원으로 왜곡하는 결함 수정. forward-fill 및 유효 양수 기반 최소값 계산으로 안전하게 정제.
   - **BUG-M01**: `NaverPriceFetcher` 및 `PriceDataCollector`에 `requests.Session()`에 대한 명시적 `close()` 메서드 및 `__enter__`, `__exit__` 컨텍스트 매니저 구현.
2. **`modules/data/collector_fundamental.py`**:
   - **BUG-L06**: 영업이익이0원(손익분기)일 때 `stmt.operating_profit == 0`이 Falsy로 평가되어 `op_margin` 계산이 누락되는 결함 수정 (`if stmt.revenue is not None and stmt.operating_profit is not None and stmt.revenue != 0:`).
   - **BUG-M01**: `OpenDartCollector`, `NaverFinanceCollector`, `FundamentalDataCollector`에 `close()` 및 Context Manager (`__enter__`, `__exit__`) 추가.
3. **`modules/data/consolidator.py`**:
   - **BUG-L03**: `consolidate_point_in_time`에서 `pd.merge_asof` 수행 시 `symbol` 필터링 및 `by='symbol'` 인자 누락으로 타 종목 펀더멘털 데이터가 오염되는 현상 수정. `symbol` 단일 종목 필터링 및 다중 종목 안전 분리.
   - **Lookahead Bias 방어**: `announcement_date` 추정 시 12월 결산 사업보고서는 90일, 기타 분기(3, 6, 9월)는 45일로 공시 기한 차등 추정.
4. **`modules/data/streamer.py`**:
   - **BUG-M02**: `NaverPollingStreamer.stop()`의 `join(timeout=2.0)`이 HTTP timeout(5초)보다 짧아 발생하는 좀비 스레드 누수 수정. 세션 즉시 닫기 및 `join(timeout=self.timeout + 1.0)` 적용.
   - **BUG-M03**: `CircularBuffer` 다중 종목 딕셔너리 무한 증식 방어를 위한 `max_symbols` 제한 및 `clear(symbol)` 메서드 보강.
