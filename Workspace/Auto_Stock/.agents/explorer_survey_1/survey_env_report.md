# Auto Stock 프로젝트 환경 및 라이브러리 조사 분석 보고서

**작성일시**: 2026-08-31T17:00:30+09:00  
**작성자**: Explorer 1 (환경 및 의존성 전문 탐색가)  
**대상 프로젝트 루트**: `/home/imnyj/Workspace/Auto_Stock`

---

## 1. 개요 및 조사 목적
본 보고서는 'Auto Stock ML/RL Trader'의 **Phase 1: 데이터 수집 파이프라인** 구축을 위해 시스템 환경, 기존 파일 구조, Python 패키지 현황, 공통 유틸리티(Lock 및 Audit Logger), DART/키움 API 연동 가능성 및 Fallback 설계 방안을 심층 조사하여 후속 구현 및 테스트 에이전트에게 명확한 가이드를 제공하는 것을 목적으로 합니다.

---

## 2. 기존 프로젝트 파일 및 디렉토리 구조 파악

### 2.1 디렉토리 현황
```
/home/imnyj/Workspace/Auto_Stock/
├── ORIGINAL_REQUEST.md       # 사용자 원본 요구사항 (Phase 1 데이터 수집 파이프라인)
├── User_Request.md           # 초기 사용자 요청 템플릿
├── Report/
│   └── implementation_plan.md# 전체 5단계 로드맵 및 모듈 구조 정의서
└── .agents/
    ├── orchestrator_1/       # 상위 오케스트레이터 작업 공간
    └── explorer_survey_1/    # 본 탐색가 작업 공간
```

### 2.2 디렉토리 분석 결과
- `modules/` (하위 `data/`, `engine/`, `ml/`), `tests/`, `data/raw/` 디렉토리는 아직 생성되지 않은 초기 상태입니다.
- 구현 단계에서 `modules/data/` 디렉토리를 생성하고 `collector_fundamental.py`, `collector_price.py`, `streamer.py`, `__init__.py` 등을 배치해야 합니다.
- 수집된 원천 데이터 저장을 위한 `data/raw/` 디렉토리와 단위 테스트를 위한 `tests/` 디렉토리 생성이 필요합니다.

---

## 3. Python 실행 환경 및 패키지 의존성 조사

### 3.1 Python 런타임 환경
- **가상환경 경로**: `/home/imnyj/venv/bin/python3`
- **Python 버전**: Python 3.12.x
- **OS 환경**: Linux (Ubuntu 24.04.2 LTS, x86_64)

### 3.2 핵심 패키지 설치 현황표
| 패키지명 | 설치 여부 | 버전 | 용도 및 역할 | 비고 |
| :--- | :---: | :---: | :--- | :--- |
| **pandas** | ✅ 설치됨 | 2.3.3 | 시계열 및 재무 데이터프레임 조작, 병합 | ML/RL 입력 데이터셋 생성 핵심 |
| **pyarrow** | ✅ 설치됨 | 23.0.1 | Parquet 형식 파일 고속 I/O 및 저장 | `to_parquet(engine='pyarrow')` 지원 |
| **requests** | ✅ 설치됨 | 2.33.1 | HTTP REST API 통신 및 데이터 스크래핑 | 네이버/DART API 호출 |
| **beautifulsoup4** | ✅ 설치됨 | 4.14.3 | HTML 웹 크롤링 및 파싱 | 네이버 금융 재무제표 파싱 |
| **torch** | ✅ 설치됨 | 2.11.0+cu130 | 딥러닝/신경망 모델 학습 (CUDA 지원) | 향후 Phase 4 ML 모델 |
| **stable_baselines3** | ✅ 설치됨 | 2.7.0 | 강화학습(PPO, DDPG, SAC 등) | 향후 Phase 4 RL 트레이너 |
| **scikit-learn** | ✅ 설치됨 | 1.6.1 | 지도학습, 전처리, 평가 메트릭 | 가격 예측 및 지표 정규화 |
| **xgboost** | ✅ 설치됨 | 3.2.0 | Gradient Boosting 지도학습 모델 | 단기 주가 예측 |
| **lightgbm** | ✅ 설치됨 | 4.6.0 | 경량 Gradient Boosting 모델 | 고속 특성 학습 |
| **FinanceDataReader** | ❌ 미설치 | - | 주가/종목 데이터 수집 라이브러리 | 네이버 REST API로 완벽 대체 가능 |
| **pykrx** | ❌ 미설치 | - | 한국거래소(KRX) 스크래핑 | 네이버/DART API로 대체 가능 |
| **OpenDartReader** | ❌ 미설치 | - | OpenDART 전용 래퍼 | requests 직접 호출로 대체 가능 |
| **yfinance** | ❌ 미설치 | - | Yahoo Finance API | 네이버 차트 API로 대체 가능 |
| **fastparquet** | ❌ 미설치 | - | Parquet 엔진 | `pyarrow`가 설치되어 있어 불필요 |

### 3.3 분석 및 구현 권장 방향
1. **외부 무거운 의존성 최소화**: `FinanceDataReader`, `OpenDartReader`, `pykrx` 등 외부 비공식 라이브러리에 종속되지 않고, 기본 내장된 `requests` + `bs4` 기반으로 가볍고 안정적인 자체 수집기를 구현하는 것이 최선의 아키텍처입니다.
2. **Parquet 저장 무결성**: `pyarrow` 23.0.1이 설치되어 있으므로 `pandas.DataFrame.to_parquet(path, engine='pyarrow', compression='snappy')`가 완벽히 동작합니다.

---

## 4. 공통 유틸리티 인터페이스 및 사용 규격

시스템 전역 안전 규칙(GEMINI.md)에 명시된 두 핵심 유틸리티의 동작 방식을 직접 코드를 통해 확인하였습니다.

### 4.1 Lock Manager (`/home/imnyj/Command/core/lock_manager.py`)
- **역할**: 다중 에이전트 환경에서 파일 동시 수정 충돌을 방지하고 자동 백업을 수행.
- **주요 인터페이스**:
  - `acquire(filepath, agent_id, timeout=300) -> bool`:
    - `/tmp/agent_locks/<safe_path>.lock`에 원자적 파일 생성 (`O_CREAT | O_EXCL`).
    - 대상 파일이 이미 존재하면 `/home/imnyj/Workspace/<Project>/backup/<filename>.<timestamp>.bak`에 자동 스냅샷 복사.
  - `release(filepath, agent_id) -> bool`:
    - 락 소유자 일치 확인 후 락 파일 안전 삭제.
- **Python 코드 사용법**:
  ```python
  import sys
  sys.path.append('/home/imnyj/Command/core')
  from lock_manager import LockManager

  lm = LockManager()
  if lm.acquire(target_file, "implementer_1"):
      try:
          # 파일 작성/수정 작업 수행
          pass
      finally:
          lm.release(target_file, "implementer_1")
  ```

### 4.2 Audit Logger (`/home/imnyj/Command/core/audit_logger.py`)
- **역할**: 모든 파일 변경 이력을 타임스탬프, 담당 에이전트, 상위 에이전트, 작업 설명과 함께 감사 로그로 기록.
- **주요 인터페이스**:
  - `log_action(agent_id, action_type, target_file, description, parent_id=None)`:
    - `/tmp/agent_audit.log`에 JSON 형식으로 append 기록.
  - `trace_blame(target_file)`:
    - 해당 파일의 최근 수정자 및 변경 이력 추적.
- **Python 코드 사용법**:
  ```python
  import sys
  sys.path.append('/home/imnyj/Command/core')
  from audit_logger import AuditLogger

  logger = AuditLogger()
  logger.log_action(
      agent_id="implementer_1",
      action_type="CREATE",  # or "MODIFY"
      target_file="/home/imnyj/Workspace/Auto_Stock/modules/data/collector_fundamental.py",
      description="Implement fundamental data collector with cross-validation",
      parent_id="orchestrator_1"
  )
  ```

---

## 5. DART API & 키움증권 API 조사 및 Fallback 설계 방안

### 5.1 현황 조사 결과
1. **DART API Key**:
   - 시스템 환경변수(`DART_API_KEY`) 및 로컬 설정 파일에 등록되어 있지 않습니다.
   - OpenDART 서버(`https://opendart.fss.or.kr`)로의 HTTP 네트워크 연결은 정상 작동함을 확인하였습니다.
2. **키움증권 API**:
   - 현재 실행 환경은 Ubuntu Linux x86_64이며, `wine` 등 Windows 에뮬레이터가 설치되어 있지 않아 32-bit Windows COM 기반 키움 Open API+는 직접 구동할 수 없습니다.
   - 또한 키움증권 REST API의 계정 키(AppKey, SecretKey)가 제공되지 않은 상태입니다.

### 5.2 검증된 대체 데이터 엔드포인트 (네이버 금융)
실제 HTTP 요청 테스트를 통해 수집 가능한 엔드포인트를 확인하였습니다:
1. **실시간 호가/시세 (`streamer.py`용)**:
   - URL: `https://polling.finance.naver.com/api/realtime/domestic/stock/{code}`
   - 제공: 현재가, 전일대비, 등락률, 거래량, 체결강도, 호가 (JSON)
2. **1분봉 시계열 (`collector_price.py`용)**:
   - URL: `https://api.stock.naver.com/chart/domestic/item/{code}/minute?period=1`
   - 제공: `localDateTime`, `openPrice`, `highPrice`, `lowPrice`, `currentPrice`, `accumulatedTradingVolume` (JSON)
3. **일봉 시계열 (`collector_price.py`용)**:
   - URL: `https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={count}&requestType=0`
   - 제공: 날짜별 시가, 고가, 저가, 종가, 거래량 (XML/Text)
4. **기업 재무제표 및 가치 지표 (`collector_fundamental.py`용)**:
   - URL: `https://finance.naver.com/item/main.naver?code={code}`
   - 제공: PER, PBR, 배당수익률, 연간/분기별 매출액, 영업이익, 당기순이익, 부채비율, 당좌비율, ROE 등 (HTML Table)

### 5.3 3단계 계층형 Fallback 및 Mocking 아키텍처 설계

```
+-------------------------------------------------------------+
|                 Data Pipeline / Collector API               |
+-------------------------------------------------------------+
                               |
       +-----------------------+-----------------------+
       |                                               |
[Fundamental Collector]                        [Price Collector]
       |                                               |
       v                                               v
+--------------------------+           +-------------------------------+
| OpenDART vs Naver Finance|           | Kiwoom / Naver / Mock Client  |
+--------------------------+           +-------------------------------+
| 1) DART API Key 존재 시  |           | 1) Kiwoom REST Key 존재 시:    |
|    -> OpenDART 직접 호출 |           |    -> Kiwoom Live Client      |
| 2) DART Key 부재/에러 시:|           | 2) Linux / 키 부재 환경 (기본): |
|    -> Naver Scraper 수집 |           |    -> Naver REST Client 호출  |
| 3) 오프라인 / 단위테스트:|           | 3) 오프라인 / 단위 테스트 시:  |
|    -> Mock Fundamental   |           |    -> Mock Price Streamer     |
+--------------------------+           +-------------------------------+
```

#### A. 펀더멘털 수집기 (`collector_fundamental.py`) Fallback 로직
1. **Primary**: 환경변수 `DART_API_KEY`가 존재하면 OpenDART 공식 API에서 재무제표 단일회사 주요계정(`fnlttSinglAcntAll.json`)을 조회.
2. **Secondary (Cross-Check / Fallback)**: 네이버 금융 웹 스크래핑을 통해 동일 연도/분기 재무제표(매출, 영업이익, 당기순이익) 및 투자지표(PER, PBR)를 수집.
3. **Mock Mode (테스트용)**: 네트워크 단절 또는 테스트 파라미터(`use_mock=True`) 전달 시 미리 정의된 삼성전자 등 표준 Mock 재무 데이터를 즉시 반환.

#### B. 시세 수집기 및 스트리머 (`collector_price.py`, `streamer.py`) Fallback 로직
1. **추상화 인터페이스 (`BasePriceCollector`)**: 일봉/분봉/실시간 호가를 동일한 규격의 DataFrame/Dict로 반환하는 추상 클래스 설계.
2. **`NaverPriceCollector`**: Linux 환경에서 실시간/과거 주가 데이터를 네이버 REST/fchart API로 즉시 수집하여 실제 시장 데이터를 반영.
3. **`MockPriceCollector`**: 정적 과거 CSV/랜덤워크 기반 가격 데이터를 실시간 스트리밍 시뮬레이션할 수 있는 단위 테스트 및 강화학습 전용 모의 수집기 제공.

---

## 6. 교차 검증 (Cross-Validation) 및 방어 로직 상세 설계

### 6.1 불일치율 계산 공식
다중 소스($S_1, S_2$)로부터 동일 지표(예: 최근 결산 연도 영업이익)를 수집한 후 다음과 같이 오차율을 계산합니다:
$$\Delta = \frac{|V_{S_1} - V_{S_2}|}{(|V_{S_1}| + |V_{S_2}|) / 2 + \epsilon}$$

### 6.2 방어 및 로깅 정책
1. **임계치 검사**: $\Delta > 0.05$ (5% 초과 차이) 발생 시:
   - `logger.warning(f"[CrossCheck Warning] {metric_name} mismatch: Source1={V_1}, Source2={V_2}, diff={diff_pct:.2f}%")`
2. **결측치 우선순위 보정 (Imputation Strategy)**:
   - DART 데이터 우선 신뢰(정식 공시 기준) $\rightarrow$ DART 결측 시 네이버 데이터로 자동 대체.
   - 단일 출처만 유효한 경우 Warning 로그 기록 후 해당 값 채택.
3. **데이터 무결성 검증**:
   - 시가총액, PER, PBR 등의 지표가 음수이거나 비정상치(예: PER > 10,000 등)인 경우 필터링 플래그(`is_valid=False`) 부착.

---

## 7. 데이터 병합 및 Parquet 저장 설계

### 7.1 데이터 병합 (Consolidation) 구조
- **기본 인덱스**: 가격 데이터의 타임스탬프(`datetime` / `date`)
- **병합 방식**: `pandas.merge_asof`를 사용하여 각 시점의 분봉/일봉 주가 행에 가장 최근 발표된 재무제표 지표(매출액, 영업이익, PER, PBR, 부채비율 등)를 Forward-Fill 방식으로 병합.
- **산출물 스키마 예시**:
  - `datetime`: `Timestamp` (UTC or Asia/Seoul)
  - `open`, `high`, `low`, `close`, `volume`: `float64 / int64`
  - `per`, `pbr`, `roe`, `debt_ratio`: `float64`
  - `operating_profit`, `revenue`: `int64`
  - `cross_check_confidence`: `float64` (교차 검증 신뢰도 0.0 ~ 1.0)

### 7.2 Parquet 저장 규칙
- 저장 경로: `/home/imnyj/Workspace/Auto_Stock/data/raw/{symbol}_{timeframe}.parquet` (예: `stock_005930_1d.parquet`, `stock_005930_1m.parquet`)
- 저장 엔진: `engine='pyarrow'`, 압축 옵션: `compression='snappy'`

---

## 8. 후속 구현 및 테스트 가이드 (Next Steps)

1. **Implementer를 위한 핵심 지침**:
   - `modules/data/collector_fundamental.py`: DART + Naver 스크래퍼 + Cross-Check 방어 로직 + Mock 지원 구조로 구현.
   - `modules/data/collector_price.py`: Naver fchart(일봉) + Naver Minute(분봉) + Mock 수집기 지원 구조로 구현.
   - `modules/data/streamer.py`: Naver Polling 실시간 시세 + 로컬 링 버퍼/캐시 큐 + Mock 스트리머 구조로 구현.
   - `modules/data/consolidator.py` (또는 수집기 내 통합 메서드): 펀더멘털과 시세를 결합하여 `data/raw/*.parquet`로 저장하는 기능 구현.
   - 파일 수정/생성 시 반드시 `lock_manager.py`와 `audit_logger.py` 프로토콜을 준수할 것.

2. **Tester를 위한 핵심 지침**:
   - `tests/test_phase1.py` 작성:
     - 테스트 1: 삼성전자('005930') 펀더멘털 수집 및 DART/네이버 교차 검증 (Warning 발생 여부 확인)
     - 테스트 2: 과거 일봉 및 분봉 시계열 수집 무결성 테스트
     - 테스트 3: 실시간 스트리머 캐싱 및 큐 동작 테스트
     - 테스트 4: 데이터 병합 및 `data/raw/` Parquet 파일 저장/로딩 검증
     - 네트워크 단절 및 API Key 부재 상황에서도 Mock을 통해 모든 테스트가 완벽히 통과(Pass)하도록 테스트 픽스처 구성.

---
**보고서 종료**
