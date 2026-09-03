# Auto Stock ML/RL Trader — Phase 3 코드베이스 구조 탐색 및 분석 보고서

- **작성 에이전트**: Codebase Explorer 1 (`.agents/explorer_1`)
- **작성 일시**: 2026-09-01T23:31:00+09:00
- **프로젝트 루트**: `/home/imnyj/Workspace/Auto_Stock`
- **대상 마일스톤**: Phase 3 (실거래 제어 모듈 및 Kiwoom REST API 연동)

---

## 1. 개요 및 조사 목적

본 조사는 `Auto Stock ML/RL Trader` 프로젝트의 'Phase 3: 실거래 제어 모듈 구축'을 위해 기존 코드베이스의 디렉토리 구조, 기구현된 모듈(Phase 1 데이터 수집 파이프라인, Phase 2 가상 체결 엔진), 설정/시크릿 체계, 파이썬 가상환경 및 테스트 인프라를 전수 조사하고, Phase 3 구현을 위해 신규 생성 및 수정이 필요한 파일/디렉토리를 정의하는 것을 목적으로 합니다.

---

## 2. 기존 코드베이스 및 프로젝트 구조 현황

### 2.1 전체 디렉토리 레이아웃

```
/home/imnyj/Workspace/Auto_Stock/
├── ORIGINAL_REQUEST.md          # Phase 3 원본 요구사항 명세
├── PROJECT.md                   # 프로젝트 아키텍처 및 마일스톤 현황 (현재 Phase 2 반영)
├── TEST_INFRA.md                # 4-Tier 테스트 전략 및 규격 문서
├── TEST_READY.md                # Phase 2 검증 완료 보고서 (198/198 passed)
├── User_Request.md              # 초기 요청 메모
├── .agents/                     # 다중 에이전트 오케스트레이션 및 작업 공간
│   ├── orchestrator_3/          # Phase 3 총괄 오케스트레이터
│   ├── explorer_1/              # 본 탐색 에이전트 작업 공간
│   ├── explorer_2/              # Kiwoom API 명세 탐색 에이전트
│   └── explorer_3/              # 보안 설정 및 Mock QA 탐색 에이전트
├── data/                        # 데이터 저장소
│   └── raw/                     # ZSTD 압축 Parquet 파일 (삼성전자, SK하이닉스, 현대차 등)
├── modules/                     # 메인 비즈니스 로직 패키지
│   ├── __init__.py              # modules.data, modules.engine 노출
│   ├── data/                    # Phase 1: 데이터 수집 및 전처리 파이프라인
│   │   ├── __init__.py
│   │   ├── collector_fundamental.py # 재무제표 다중 소스(DART, 키움, 네이버) 교차 수집기
│   │   ├── collector_price.py       # 일봉/분봉 과거 시계열 수집기
│   │   ├── consolidator.py          # Point-in-Time 병합 및 ZSTD Parquet I/O
│   │   ├── pipeline.py              # E2E 데이터 파이프라인 Facade
│   │   └── streamer.py              # 실시간 시세 수신, 링버퍼(RingBuffer), 틱-캔들 집계기
│   └── engine/                  # Phase 2: 가상 체결 엔진 (Mock Environment)
│       ├── __init__.py              # VirtualAccount, MockExecutionEngine, DummyStrategySimulator, MockEnvironment 등 노출
│       └── mock_environment.py     # 1원 단위 정밀 Decimal 회계, 거래비용 모델, 1,000회 핑퐁 무결성
├── tests/                       # 자동화 테스트 스위트 (총 7개 파일, 212개 케이스 100% 통과)
│   ├── __init__.py
│   ├── test_phase1.py               # Phase 1 종합 E2E 테스트 (28개)
│   ├── test_fundamental.py          # 재무제표 교차 검증 단위 테스트 (30개)
│   ├── test_price_streamer.py       # 주가 수집 및 링버퍼 스트리머 테스트 (35개)
│   ├── test_consolidator.py         # 데이터 병합 및 Parquet 무결성 테스트 (19개)
│   ├── test_phase2.py               # Phase 2 4-Tier 가상 체결 엔진 테스트 (63개)
│   ├── test_adversarial_challenger1.py # 적대적 변이 테스트 1 (23개)
│   └── test_adversarial_challenger2.py # 적대적 변이 테스트 2 (14개)
├── logs/                        # 실행 및 자가 개선 로그
│   └── execution_notes.md       # 에이전트별 실행 및 감사 기록
├── etc/                         # 보조 스크립트 및 디버깅 로그 (GEMINI.md 규칙 준수)
│   ├── scripts/                 # 적대적 벤치마크 및 검증 스크립트
│   └── logs/                    # 스트레스 벤치마크 로그
└── backup/                      # 이전 버전 파일 백업
```

### 2.2 기구현 모듈 요약 및 상태

1. **`modules/data/` (Phase 1)**:
   - 다중 소스(OpenDART, 키움증권, 네이버 금융) 교차 검증 및 결측치 보정 완비.
   - Point-in-Time 원칙을 준수하여 미래 참조 편향(Look-ahead bias)을 원천 차단한 데이터 병합.
   - 고빈도 실시간 시세 수신을 위한 스레드 안전 `RealtimeRingBuffer` 및 `WindowBarAggregator` 구현.

2. **`modules/engine/` (Phase 2)**:
   - `VirtualAccount`: `decimal.Decimal` 기반 1원 단위 정밀 회계 (반올림 및 절사 규격 준수).
   - `MockExecutionEngine`: 한국 주식 시장 표준 비용(위탁수수료 0.015%, 증권거래세 0.18%, 슬리피지 0.1%) 적용 및 잔고 방어.
   - `DummyStrategySimulator`: 1,000회 이상 연속 고빈도 핑퐁 매매 완주 및 $\text{Initial Cash} - (\text{Final Cash} + \text{Valuation} + \text{Frictions}) \equiv 0\text{ KRW}$ 불변식 0원 오차 달성.
   - `MockEnvironment`: ML/RL 호환 표준 `reset()`, `step()` Facade 제공.

---

## 3. 런타임 환경, 패키지 의존성 및 테스트 인프라

### 3.1 실행 환경
- **OS**: Linux (Ubuntu 24.04 기반)
- **Python 인터프리터**: Python 3.12.3 (`/usr/bin/python`, `/home/imnyj/venv/bin/python`)
- **테스트 러너**: `/home/imnyj/venv/bin/pytest` (pytest 9.0.3)

### 3.2 주요 설치 패키지 현황
| 라이브러리 | 버전 | 용도 및 Phase 3 적합성 |
|---|---|---|
| `requests` | 2.34.2 | Kiwoom REST API HTTP 통신 (OAuth2, 시세, 주문, 계좌) |
| `urllib3` | 2.0.7 | HTTP 연결 풀링 및 재시도 제어 |
| `httpx` | 0.28.1 | 비동기/동기 HTTP 클라이언트 지원 |
| `PyYAML` | 6.0.1 | `config/settings.yaml` 파싱 및 직렬화 |
| `pydantic` | 2.13.4 | 데이터 모델 유효성 검증 및 API 요청/응답 직렬화 |
| `pydantic-settings` | 2.14.1 | 환경변수 및 설정 파일 자동 로드 및 타입 보장 |
| `python-dotenv` | 1.2.2 | `.env` 파일 로드 지원 |
| `rich` | 15.0.0 | CLI 수동 매매 인터페이스 (`manual_trader.py`) 터미널 렌더링 (테이블, 색상 강조) |
| `click` / `typer` | 8.4.1 / 0.25.1 | CLI 커맨드라인 파싱 |
| `pytest` / `pytest-cov` | 9.0.3 / 7.1.0 | 테스트 자동화 및 커버리지 측정 |
| `pandas` / `numpy` | 2.3.3 / 2.4.6 | 시계열 데이터 및 배열 연산 |

### 3.3 기존 테스트 스위트 검증 결과
- 테스트 명령어: `/home/imnyj/venv/bin/pytest tests/`
- 실행 결과: **212 Passed / 0 Failed (100% PASS, 13.51s)**
- 기존 Phase 1 및 Phase 2의 모든 기능, 경계값, 복합 시나리오, 적대적 변이 테스트가 무결하게 통과됨.

---

## 4. 설정 및 시크릿(Secret) 관리 체계 분석

### 4.1 현재 상태
- Phase 1에서는 `modules/data/collector_fundamental.py` 내에서 `os.getenv("DART_API_KEY")` 형태로 환경변수를 개별 조회하는 방식이 사용됨.
- 현재 루트에는 중앙화된 `config/` 디렉토리나 `settings.yaml` 파일이 존재하지 않음.

### 4.2 Phase 3 요구사항 (R3) 대비 분석
- **요구사항**: 키움 API Key(App Key, App Secret), 계좌번호, 모의투자 스위치(`USE_MOCK_SERVER`), 타임아웃 등의 설정을 중앙화된 `config/settings.yaml` 또는 `.env`에서 안전하게 로드.
- **설계 제안**:
  1. `config/` 디렉토리를 생성하고 기본 템플릿인 `config/settings.example.yaml` 및 `.env.example`을 제공.
  2. `core/config.py`를 신규 생성하여 Pydantic `BaseSettings` 또는 PyYAML 기반 로더를 구축하고, 환경변수(`KIWOOM_APP_KEY`, `KIWOOM_APP_SECRET`, `KIWOOM_ACCOUNT_NO` 등)가 YAML 설정보다 우선 순위를 갖도록 계층적 설정 구조(Hierarchy) 구축.
  3. 소스 코드 내 민감정보 하드코딩 0건을 정적 분석으로 입증할 수 있도록 엄격한 격리 보장.

---

## 5. Phase 3 갭 분석 (Gap Analysis) 및 생성/수정 대상

Phase 3(키움 REST API 연동, 수동 매매 CLI, 시크릿 관리, Mock 테스트) 완성을 위해 필요한 작업 목록입니다.

### 5.1 신규 생성 대상 디렉토리
1. `/home/imnyj/Workspace/Auto_Stock/core/`: 키움 REST API 통신 코어 및 보안 설정 로더 저장소
2. `/home/imnyj/Workspace/Auto_Stock/config/`: YAML 설정 및 환경변수 템플릿 저장소

### 5.2 신규 생성 대상 파일

| 파일 경로 | 담당 역할 및 주요 구현 내용 | 관련 요구사항 |
|---|---|---|
| `core/__init__.py` | `core` 패키지 초기화 및 `KiwoomClient`, `KiwoomConfig`, `TokenManager` 등 주요 클래스 export | R1, R3 |
| `core/kiwoom_api.py` | - OAuth2.0 기반 Access Token 발급 및 자동 갱신(`TokenManager`)<br>- 실거래/모의투자 엔드포인트 동적 스위칭 (`USE_MOCK_SERVER`)<br>- 현재가 조회 (`get_current_price`)<br>- 주문 전송 (`send_order`: 매수/매도, 시장가/지정가)<br>- 계좌 잔고 및 보유 종목 조회 (`get_account_balance`, `get_account_positions`)<br>- API 응답 파싱, 에러 코드 처리 및 재시도/타임아웃 핸들링 | R1 |
| `core/config.py` | - `config/settings.yaml` 및 `.env` 파일 파싱<br>- Pydantic 기반의 강타입 설정 검증 클래스 (`AppConfig`, `KiwoomConfig`)<br>- 계좌번호 및 시크릿 마스킹 로깅 유틸리티 제공 | R3 |
| `config/settings.yaml` | 로컬 실행용 설정 파일 (실제 키가 입력될 수 있으며 버전 관리 제외 권장) | R3 |
| `config/settings.example.yaml` | 설정 템플릿 파일 (더미 키 및 주석 가이드 포함) | R3 |
| `.env.example` | 환경변수 오버라이드 가이드 템플릿 | R3 |
| `modules/engine/manual_trader.py` | - CLI 기반 수동 매매 제어기 스크립트<br>- 종목 코드, 매매 방향(BUY/SELL), 수량 입력 시 시장가 주문 전송<br>- 주문 체결 후 변경된 계좌 잔고/보유량/평가액 터미널 출력 (`rich` 테이블 활용)<br>- 안전 장치 (주문 전 최종 확인 프롬프트, 잔고 부족 시 사전 차단) | R2 |
| `tests/test_phase3_api.py` | - `unittest.mock`을 활용한 키움 REST API 엔드포인트 전수 모킹 검증<br>- 토큰 발급 및 자동 갱신 테스트<br>- 주문 전송 및 잔고 변동 시나리오 검증<br>- 실서버 vs 모의투자 서버 토글 테스트<br>- 네트워크 장애/HTTP 에러/API 거절 응답 예외 처리 테스트<br>- 소스 코드 내 하드코딩 0건 정적 검증 테스트 포함 | Acceptance Criteria |
| `requirements.txt` | 프로젝트 공식 의존성 명세 (requests, PyYAML, pydantic, rich, pytest 등) | 환경 재현성 |

### 5.3 수정 대상 파일

| 파일 경로 | 수정 내용 | 목적 |
|---|---|---|
| `modules/engine/__init__.py` | `ManualTrader` 또는 CLI 실행 엔트리포인트 노출 추가 | 패키지 인터페이스 정합성 |
| `modules/__init__.py` | `core` 패키지 임포트 또는 엔진 연동 확인 | 전체 모듈 바인딩 |
| `PROJECT.md` | Phase 3 아키텍처, Feature Inventory(R1, R2, R3), Milestones, Interface Contracts 최신화 | 프로젝트 현행화 |
| `logs/execution_notes.md` | Phase 3 탐색, 구현, 테스트 완료 내역 추가 | GEMINI.md 자가 개선 로그 준수 |

---

## 6. Phase 3 아키텍처 및 인터페이스 설계 권고사항

### 6.1 계층 간 상호작용 구조

```
[config/settings.yaml / .env]
             │
             ▼
      [core/config.py] (Config Loader & Secret Validator)
             │
             ▼
     [core/kiwoom_api.py] (KiwoomClient & TokenManager)
             │ ◄─── (Live Server: openapi.kiwoom.com / Mock Server: openapivts.kiwoom.com)
             │
      ┌──────┴──────────────────────────┐
      ▼                                 ▼
[modules/engine/manual_trader.py]   [tests/test_phase3_api.py]
 (CLI Manual Trading Controller)     (Unit & Integration Mock Tests)
```

### 6.2 핵심 클래스 및 인터페이스 제안

1. **`core/config.py`**:
   - `KiwoomConfig(app_key, app_secret, account_no, is_mock, timeout, ...)`
   - `AppConfig.load_from_yaml(path)` / `load_from_env()`

2. **`core/kiwoom_api.py`**:
   - `TokenManager`: Access Token 발급, 만료 시간 추적(`expires_in`), 자동 재발급
   - `KiwoomClient`:
     - `get_current_price(symbol: str) -> Dict[str, Any]`
     - `send_order(symbol: str, order_type: OrderType, side: OrderSide, quantity: int, price: Optional[int]) -> Dict[str, Any]`
     - `get_account_balance() -> Dict[str, Any]`
     - `get_account_positions() -> List[Dict[str, Any]]`

3. **`modules/engine/manual_trader.py`**:
   - `ManualTrader`: `KiwoomClient`를 주입받아 잔고 사전 확인 -> 시장가 주문 전송 -> 사후 잔고 변동 출력 파이프라인 수행.
   - CLI 실행부: `python -m modules.engine.manual_trader --symbol 005930 --side BUY --quantity 1` 또는 대화형 인터랙티브 모드 지원.

---

## 7. 보안 및 하드코딩 0건 검증 전략

1. **정적 검증 스크립트/테스트**:
   - `tests/test_phase3_api.py` 내에 정규식 패턴 검사기(`test_no_hardcoded_secrets`)를 탑재하여, `core/`, `modules/`, `tests/` 전역에서 실제 API Key 패턴(32자 이상 hex/alphanumeric 리터럴, 8자리 계좌번호 리터럴 등)이 코드 내에 직접 선언되지 않았음을 단언(assert).
2. **`.gitignore` 방어**:
   - 실제 시크릿이 저장될 수 있는 `config/settings.yaml`, `.env`, `*.secret` 등을 gitignore 규칙에 등록.

---

## 8. 결론

Auto Stock 프로젝트는 Phase 1(데이터 파이프라인)과 Phase 2(가상 체결 엔진 및 회계 무결성 198+ 테스트 100% 통과)가 매우 안정적으로 구축되어 있습니다.
Phase 3 '실거래 제어 모듈' 구현을 위해서는 신규 `core/` 패키지와 `config/` 디렉토리를 신설하고, `core/kiwoom_api.py`, `core/config.py`, `modules/engine/manual_trader.py`, `tests/test_phase3_api.py`를 유기적으로 연결함으로써 완벽하게 요구사항을 달성할 수 있습니다.
