## 2026-08-31T08:02:15Z

당신은 Auto Stock 프로젝트의 Milestone 2 (Price Data Collector & Streamer) 전담 구현 워커입니다.

### 작업 디렉토리
`/home/imnyj/Workspace/Auto_Stock/.agents/worker_m2/`

### 필수 확인 문서 (반드시 가장 먼저 정독할 것)
1. `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md`
2. `/home/imnyj/Workspace/Auto_Stock/PROJECT.md`
3. `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_survey_3/survey_price_consolidation_spec.md`

### ⚠️ MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### 배타적 소유 파일 (Write Ownership)
- `/home/imnyj/Workspace/Auto_Stock/modules/data/collector_price.py`
- `/home/imnyj/Workspace/Auto_Stock/modules/data/streamer.py`
- `/home/imnyj/Workspace/Auto_Stock/tests/test_price_streamer.py`

### 파일 잠금 및 감사 로깅 규정
- 파일 생성/수정 전: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py acquire <filepath> worker_m2`
- 파일 생성/수정 후: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/audit_logger.py log --agent worker_m2 --file <filepath> --action "CREATE/MODIFY"`
- 락 해제: `/home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py release <filepath> worker_m2`

### 구현 요구사항
1. `modules/data/collector_price.py`:
   - `NaverPriceFetcher`: `https://fchart.stock.naver.com/sise.nhn` (일봉 XML 파싱) 및 `https://api.stock.naver.com/chart/domestic/item/...` (분봉 JSON 파싱) 구현.
   - `PriceDataCollector`: `get_daily_price(symbol, count)`, `get_minute_price(symbol, period)`. 표준 컬럼(`date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, `timeframe`) 보장.
2. `modules/data/streamer.py`:
   - `TickData` 데이터클래스 정의 (`symbol`, `timestamp`, `price`, `volume`, `ask`, `bid` 등).
   - `CircularBuffer`: `collections.deque(maxlen=50000)` 기반 스레드 안전 링 버퍼 및 메모리 누수 방어.
   - `RealtimeStreamer`: 네이버 폴링 API(`polling.finance.naver.com`) 및 `MockStreamer` 제공.
   - `WindowBarAggregator`: 틱 스트림으로부터 1분/5분 OHLCV 캔들 동적 집계.
3. `tests/test_price_streamer.py` 작성 및 자체 단위 테스트 실행:
   - `/home/imnyj/venv/bin/pytest -v tests/test_price_streamer.py`
4. 테스트 100% 통과 확인 후 본인 작업 디렉토리에 `handoff.md` 작성 및 완료 보고. 모든 문서는 한국어로 작성하십시오.
