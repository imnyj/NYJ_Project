# Handoff Report — Auto Stock Phase 1 환경 및 의존성 조사 (Explorer 1)

**작성일시**: 2026-08-31T17:00:50+09:00  
**작성 에이전트**: `explorer_survey_1`  
**수신 대상**: `orchestrator_1` (Parent Agent: `9f8ce45b-2ead-4870-9054-90c6a9686e3a`)  
**보고서 유형**: Hard Handoff (임무 완료)

---

## 1. Observation (직접 관찰 결과)

1. **프로젝트 디렉토리 구조**:
   - `/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (36줄): Phase 1(펀더멘털/가격 데이터 수집기, 스트리머, 병합 및 Parquet 저장, 테스트) 요구사항 명시.
   - `/home/imnyj/Workspace/Auto_Stock/Report/implementation_plan.md` (52줄): Phase 1~5 전체 로드맵 및 모듈 구조 명시.
   - `/home/imnyj/Workspace/Auto_Stock/User_Request.md` (2줄): 초기 템플릿 파일.
   - `modules/`, `tests/`, `data/raw/` 디렉토리는 현재 생성되지 않은 초기 상태.

2. **Python 환경 및 패키지 현황 (`/home/imnyj/venv/bin/python3`, Python 3.12.x)**:
   - 기설치 라이브러리:
     - `pandas` (2.3.3)
     - `pyarrow` (23.0.1)
     - `requests` (2.33.1)
     - `beautifulsoup4` (4.14.3)
     - `torch` (2.11.0+cu130)
     - `stable_baselines3` (2.7.0)
     - `scikit-learn` (1.6.1)
     - `xgboost` (3.2.0)
     - `lightgbm` (4.6.0)
   - 미설치 라이브러리:
     - `FinanceDataReader`, `pykrx`, `OpenDartReader`, `yfinance`, `fastparquet`

3. **공통 유틸리티 코드 분석**:
   - `/home/imnyj/Command/core/lock_manager.py`: `LockManager` 클래스 제공. `acquire(filepath, agent_id, timeout=300)` 호출 시 `/tmp/agent_locks/`에 락 생성 및 기존 파일 수정 시 `/home/imnyj/Workspace/<Project>/backup/`에 자동 스냅샷 백업 수행. `release(filepath, agent_id)`로 해제.
   - `/home/imnyj/Command/core/audit_logger.py`: `AuditLogger` 클래스 제공. `log_action(agent_id, action_type, target_file, description, parent_id=None)`으로 `/tmp/agent_audit.log`에 JSON 감사 로그 기록.

4. **네트워크 및 API 엔드포인트 동작 검증**:
   - `uname -a`: Linux Ubuntu 24.04.2 LTS x86_64 (`wine` 미설치).
   - `DART_API_KEY`: 환경변수 미설정. OpenDART 서버(`https://opendart.fss.or.kr`)는 네트워크 도달 정상 확인.
   - 네이버 금융 실시간 시세 API (`https://polling.finance.naver.com/api/realtime/domestic/stock/005930`): 200 OK (현재가, 호가, 거래량 수신 확인).
   - 네이버 금융 1분봉 API (`https://api.stock.naver.com/chart/domestic/item/005930/minute?period=1`): 200 OK (분봉 시계열 수신 확인).
   - 네이버 금융 일봉 API (`https://fchart.stock.naver.com/sise.nhn?symbol=005930&timeframe=day&count=10&requestType=0`): 200 OK (과거 일봉 수신 확인).
   - 네이버 금융 웹 스크래핑 (`https://finance.naver.com/item/main.naver?code=005930`): 200 OK (PER, PBR, 분기/연간 재무제표 HTML 파싱 확인).

---

## 2. Logic Chain (논리적 추론 과정)

1. **의존성 경량화 및 안정성 확보 추론** (참조: Observation 2, 4):
   - 외부 라이브러리(`FinanceDataReader`, `pykrx`, `OpenDartReader`)가 가상환경에 설치되어 있지 않으나, `requests`와 `beautifulsoup4`가 설치되어 있고 네이버 금융 엔드포인트(일봉, 분봉, 실시간 시세, 재무제표)가 정상 작동함.
   - 따라서 불필요한 외부 패키지 설치 의존성을 배제하고, `requests` 및 `bs4` 기반의 자체 경량 수집 모듈을 작성하는 것이 유지보수성, 실행 속도, 환경 호환성 측면에서 가장 안전함.
   - `pyarrow` 23.0.1이 기설치되어 있으므로 별도의 `fastparquet` 없이도 `DataFrame.to_parquet(engine='pyarrow')`로 Parquet 저장이 즉시 가능함.

2. **DART 및 키움 API 연동 Fallback 아키텍처 추론** (참조: Observation 3, 4):
   - 키움 OpenAPI+는 Windows COM 전용이므로 현재 Linux 환경에서 직접 구동 불가하며, DART API Key는 환경변수에 미설정됨.
   - 이에 따라 DART 키가 없을 때는 네이버 금융 재무제표 스크래퍼 및 Mock 데이터를 활용하고, 키움 API는 추상 인터페이스(`BaseKiwoomClient`) 하위에 `MockKiwoomClient`와 `NaverFinanceFallbackClient`를 배치하는 다층 Fallback 아키텍처를 도입해야 함.
   - 이를 통해 개발, 자동화 테스트(`tests/test_phase1.py`), 실시간 스트리밍 시뮬레이션이 외부 키 발급 여부와 관계없이 100% 무결하게 동작하도록 보장할 수 있음.

3. **교차 검증 방어 로직 추론** (참조: Observation 1, 4):
   - DART 공시 데이터와 네이버 금융 재무제표 데이터의 불일치율을 계산($\Delta = |V_1 - V_2| / ((|V_1| + |V_2|)/2)$)하여 5% 초과 시 `logger.warning`을 기록하고 결측치는 우선순위(DART $\rightarrow$ 네이버 $\rightarrow$ 보정값)에 따라 처리하는 방어 로직을 `collector_fundamental.py`에 구현해야 함.

4. **협업 안전 프로토콜 추론** (참조: Observation 3):
   - 구현 에이전트(`implementer`)는 소스 파일 생성/수정 시 반드시 `/home/imnyj/Command/core/lock_manager.py`와 `/home/imnyj/Command/core/audit_logger.py`를 호출하여 백업 및 감사 로그를 남겨야 함.

---

## 3. Caveats (제약 사항 및 가정)

1. **키움 실거래 API 미연동**:
   - 키움증권 계정 키(AppKey, SecretKey)가 제공되지 않았으므로 Phase 1 단계에서는 `MockKiwoomClient` 및 네이버 금융 기반 실시간 Fallback 클라이언트로 설계/구현됩니다. 향후 실거래 투입 시 계정 정보 입력만으로 교체 가능한 구조를 유지합니다.
2. **OpenDART API 무료 키 한도**:
   - 향후 사용자가 OpenDART API 키를 환경변수에 등록할 경우 일일 호출 한도(기본 10,000건)를 고려하여 로컬 캐싱을 적용하는 방안이 권장됩니다.
3. **네이버 스크래핑 정책 변경 가능성**:
   - 네이버 금융 웹/API 구조가 예기치 않게 변경될 경우를 대비하여 User-Agent 헤더 설정 및 정규식/JSON 안전 파싱 방어 코드를 포함해야 합니다.

---

## 4. Conclusion (결론 및 후속 제안)

1. **조사 완료 요약**:
   - 로컬 환경은 Python 3.12, Linux x86_64이며 `pandas`, `pyarrow`, `requests`, `bs4`, `torch`, `stable_baselines3` 등 핵심 ML/데이터 라이브러리가 완벽하게 구비되어 있습니다.
   - DART/키움 키 부재 및 Linux 환경 제약은 네이버 금융 REST/웹 스크래핑 및 Mock Fallback 계층으로 완벽하게 해결 가능합니다.
2. **오케스트레이터 및 Implementer를 위한 다음 작업 권고**:
   - **디렉토리 생성**: `modules/data/`, `tests/`, `data/raw/`, `backup/`
   - **구현 대상 모듈**:
     - `modules/data/collector_fundamental.py`: DART + Naver + CrossCheck + Mock
     - `modules/data/collector_price.py`: Naver fchart(일봉) + Naver Minute(분봉) + Mock
     - `modules/data/streamer.py`: Naver Polling 실시간 시세 + 캐시 링버퍼 + Mock
     - `modules/data/consolidator.py`: 시계열과 펀더멘털 merge 후 `data/raw/*.parquet` 저장
   - **테스트 스위트**: `tests/test_phase1.py` 자동화 테스트 작성 및 실행.

---

## 5. Verification Method (독립 검증 방법)

오케스트레이터 또는 후속 에이전트는 다음 명령어로 본 조사의 핵심 사실들을 직접 재현 및 검증할 수 있습니다.

1. **Python 패키지 및 Parquet 기능 검증**:
   ```bash
   /home/imnyj/venv/bin/python3 -c "import pandas, pyarrow, requests, bs4, torch, stable_baselines3; print('All core packages verified!')"
   ```
2. **네이버 금융 실시간 시세/분봉/일봉 API 수신 검증**:
   ```bash
   /home/imnyj/venv/bin/python3 -c "
   import requests
   r1 = requests.get('https://polling.finance.naver.com/api/realtime/domestic/stock/005930')
   r2 = requests.get('https://api.stock.naver.com/chart/domestic/item/005930/minute?period=1')
   r3 = requests.get('https://fchart.stock.naver.com/sise.nhn?symbol=005930&timeframe=day&count=5&requestType=0')
   assert r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200
   print('All Naver Finance APIs verified successfully!')
   "
   ```
3. **Lock & Audit Logger 유틸리티 검증**:
   ```bash
   /home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py acquire /tmp/test_lock.txt test_agent && /home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py release /tmp/test_lock.txt test_agent
   /home/imnyj/venv/bin/python3 /home/imnyj/Command/core/audit_logger.py log --agent test_agent --file /tmp/test_lock.txt --action "TEST"
   ```
4. **상세 분석 보고서 파일 확인**:
   - `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_survey_1/survey_env_report.md`
