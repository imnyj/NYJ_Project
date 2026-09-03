# Handoff Report — Explorer 3 (Price & Consolidation Specialist)

**보고 일시**: 2026-08-31T17:01:30+09:00  
**담당 에이전트**: `explorer_survey_3` (시계열 주가 수집, 실시간 스트리머, 데이터 통합/저장 설계 전문 탐색가)  
**수신자**: `orchestrator_1` / Sentinel  
**대상 마일스톤**: Phase 1 — R2 (Price Data Collector & Streamer) & R3 (Data Consolidation & Storage)

---

## 1. Observation (직접 관찰 결과)

1. **사용자 원본 요구사항 및 프로젝트 목표 (`ORIGINAL_REQUEST.md`)**:
   - 경로: `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md:18-25`
   ```markdown
   18: 2. **R2. Price Data Collector (시계열 주가 수집)**
   19:    - `modules/data/collector_price.py` 구현: 과거 분봉/일봉 데이터 수집
   20:    - `modules/data/streamer.py` 구현: 실시간 데이터 캐싱 기반 마련
   21: 
   22: 3. **R3. Data Consolidation (데이터 병합 및 저장)**
   23:    - 수집된 펀더멘털 데이터와 가격 데이터를 ML/RL 학습용 단일 Pandas DataFrame으로 병합
   24:    - `data/raw/` 디렉토리에 Parquet 포맷으로 저장
   ```

2. **Python 실행 환경 및 패키지 설치 현황**:
   - 가상환경 `/home/imnyj/venv/bin/python` 테스트 결과:
     - `Python 3.12.3`, `pandas 2.3.3`, `numpy 2.4.4`, `pyarrow 23.0.1`, `requests 2.33.1`, `websockets 16.0` 정상 설치 확인.
     - `FinanceDataReader`, `pykrx`, `yfinance`는 기본 미설치 상태이나, 자체 HTTP Request 기반 Naver Chart API 수집기(`fchart.stock.naver.com` 및 `api.stock.naver.com`) 및 Mock Streamer 구현을 통해 외부 라이브러리 미설치 환경에서도 완벽한 독립 실행이 가능함을 실측 확인.

3. **Naver 주가 및 분봉/실시간 API 물리적 호출 검증**:
   - 네이버 일봉 차트 API: `https://fchart.stock.naver.com/sise.nhn?symbol=005930&timeframe=day&count=10&requestType=0` -> HTTP 200 정상 반환 (일자, 시가, 고가, 저가, 종가, 거래량 파싱 완료).
   - 네이버 당일 1분봉 차트 API: `https://api.stock.naver.com/chart/domestic/item/005930?periodType=day` -> HTTP 200 정상 반환 (`priceInfos` 381개 분봉 캔들 추출 완료).
   - 네이버 실시간 폴링 API: `https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:005930` -> HTTP 200 정상 반환 (`nv`(현재가), `aq`(누적거래량), `eps`, `bps`, `countOfListedStock` 등 추출 완료).

4. **Point-in-Time(PIT) 정렬 및 Parquet ZSTD 저장 검증**:
   - `pd.merge_asof(price_df, fund_df, left_on='date', right_on='announcement_date', by='symbol', direction='backward')` 동작 실측: 공시일 이전 거래일에 미래 실적이 누출되지 않고 과거 유효 실적만 forward-fill 됨을 확인.
   - `pyarrow.parquet.write_table(table, path, compression='ZSTD', compression_level=3)` 정상 쓰기 및 읽기 완료 (스키마 보존 확인).

---

## 2. Logic Chain (논리적 추론 체인)

1. **Multi-source Fallback 체계 구축 필요성**:
   - [Observation 2, 3]에 근거하여, FinanceDataReader/pykrx가 설치되지 않은 환경에서도 기본 제공되는 `requests` 모듈만으로 Naver Financial Chart XML/JSON API를 호출하여 과거 10년 이상의 일봉 및 당일 1분봉 데이터를 즉시 수집할 수 있는 `NaverPriceFetcher`를 기본 탑재(Primary)하고, 추가 라이브러리가 존재할 경우 PyKRX/YFinance/키움증권을 활용하는 Adapter/Fallback 구조를 설계함.
2. **실시간 스트리밍 버퍼와 슬라이딩 윈도우 필요성**:
   - [Observation 1]에 근거하여, ML/RL 실시간 추론 시 틱 단위 데이터 유입으로 인한 메모리 누수를 방지하기 위해 `collections.deque(maxlen=50000)` 기반의 원형 링 버퍼를 도입하고, 실시간 틱으로부터 1분봉/5분봉 캔들을 동적으로 생성하는 `WindowBarAggregator`를 설계함.
3. **Look-ahead Bias(선행 편향) 방지를 위한 Point-in-Time 병합**:
   - [Observation 4]에 근거하여, 재무제표의 회계 기준일(Period End Date)이 아닌 DART 공시일(Announcement Date)을 기준으로 `pd.merge_asof(..., direction='backward')`를 수행함으로써 과거 백테스팅 및 모델 학습 시 미래 실적 데이터가 사전 반영되는 치명적 오류를 원천 차단함.
4. **동적 밸류에이션 피처 생성 및 Parquet 최적화**:
   - 정적 PER/PBR의 시차 문제를 해결하기 위해 $Dynamic\_PER_t = Close_t / EPS_{\text{valid}}$를 매 거래일마다 동적으로 재계산하고, PyArrow ZSTD 압축 및 Hive-style 파티셔닝(`symbol={symbol}/`)을 적용하여 스토리지 용량 절감 및 빠른 I/O를 보장함.

---

## 3. Caveats (주의사항 및 한계)

1. **네이버 1분봉의 과거 데이터 수집 한계**:
   - 네이버 모바일 차트 API는 최근 1영업일의 1분봉(381개)만 제공하므로, 수개월~수년 단위의 과거 분봉을 대량 수집할 때는 키움증권 OpenAPI(`opt10080`) 또는 yfinance를 활용해야 함.
2. **거래정지 및 적자 기업 결측치 처리**:
   - 거래정지일(Volume=0) 및 $EPS \le 0$인 적자 기업의 경우 $Dynamic\_PER$이 `NaN`이 되므로, 다운스트림 ML/RL 모델이 이를 안전하게 마스킹할 수 있도록 `warning_flags` 컬럼을 반드시 참조해야 함.
3. **증권사 실시간 웹소켓 인증 키 필요성**:
   - 실제 장중 실시간 웹소켓 스트리밍을 위해서는 증권사 API Key/Secret 또는 인증서가 필요하며, 단위 테스트 및 오프라인 시뮬레이션에서는 자체 제공되는 `MockStreamer`를 사용해야 함.

---

## 4. Conclusion (결론 및 권고사항)

- R2(Price Data Collector & Real-time Streamer) 및 R3(Data Consolidation & Parquet Storage)에 대한 상세 아키텍처, 클래스 인터페이스, 데이터프레임 스키마, 결측/이상치 방어 알고리즘, Parquet 스토리지 규격을 완벽히 정의하고 `survey_price_consolidation_spec.md`에 문서화 완료함.
- 향후 Worker(구현자)가 즉시 구현할 수 있도록 구체적인 시그니처와 데이터 타입, 알고리즘 플로우차트를 제공하였으며, E2E 검증 기준을 명시함.

---

## 5. Verification Method (독립 검증 방법)

1. **설계 명세서 및 산출물 파일 검증**:
   - 명세서 경로: `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_survey_3/survey_price_consolidation_spec.md`
   - 디스패치 및 브리핑: `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_survey_3/BRIEFING.md`
2. **API 및 통합 알고리즘 검증 명령**:
   ```bash
   /home/imnyj/venv/bin/python -c "
   import requests, pandas as pd, pyarrow as pa
   # Naver daily chart check
   r = requests.get('https://fchart.stock.naver.com/sise.nhn?symbol=005930&timeframe=day&count=5&requestType=0')
   assert r.status_code == 200 and '<item' in r.text
   print('Price API Verification: PASS')
   "
   ```
3. **무효화 조건 (Invalidation Conditions)**:
   - 네이버 금융 API 엔드포인트 응답 스키마의 급격한 변경이 발생하거나, PyArrow ZSTD 압축 호환성이 상실될 경우 본 설계의 Fetcher/Storage 모듈 업데이트 필요.
