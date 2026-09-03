# Auto Stock Phase 2 코드베이스 및 아키텍처 상세 분석 보고서

**작성일시**: 2026-09-01T23:02:00+09:00  
**작성자**: Explorer 1 (Codebase Investigation & Architecture Specialist)  
**작업 디렉토리**: `/home/imnyj/Workspace/Auto_Stock/.agents/explorer_1`  
**대상 프로젝트**: Auto Stock ML/RL Trader (`/home/imnyj/Workspace/Auto_Stock`)

---

## 1. 개요 및 분석 목적
본 조사는 **Auto Stock ML/RL Trader** 프로젝트의 Phase 2("가상 체결 엔진: Mock Environment 구축") 착수에 앞서, 기존 코드베이스 구조, 의존성 환경, Phase 1 구현 자산, 동시성/감사 도구, 그리고 Phase 2 신규 컴포넌트(`modules/engine/mock_environment.py`, `tests/test_phase2.py`) 설계 및 구현에 필요한 모든 기반 사항을 완벽히 분석하여 후속 서브에이전트(Architect, Implementer, Reviewer, Challenger, Tester)에게 전달하는 것을 목적으로 합니다.

---

## 2. 프로젝트 전체 디렉토리 및 파일 구조 분석

프로젝트 루트(`/home/imnyj/Workspace/Auto_Stock`)의 전체 디렉토리 레이아웃은 다음과 같이 구성되어 있습니다:

```
/home/imnyj/Workspace/Auto_Stock/
├── .agents/                                # 에이전트 메타데이터 저장소 (규칙 준수)
│   ├── orchestrator_2/                     # Phase 2 오케스트레이터 작업 공간
│   └── explorer_1/                         # Explorer 1 작업 공간 (현재)
├── .coverage                               # pytest-cov 커버리지 캐시
├── .pytest_cache/                          # pytest 캐시
├── ORIGINAL_REQUEST.md                     # Phase 2 원본 요구사항 명세서
├── PROJECT.md                              # 프로젝트 아키텍처 및 인터페이스 계약서
├── TEST_INFRA.md                           # 4-Tier 테스트 인프라 철학 및 기준
├── TEST_READY.md                           # Phase 1 테스트 검증 완료 승인 보고서
├── User_Request.md                         # 사용자 요청 로그
├── Report/
│   └── implementation_plan.md              # 5단계 전체 프로젝트 마스터플랜
├── data/
│   └── raw/                                # Phase 1에서 생성된 ZSTD 압축 Parquet 원천 데이터
│       ├── 005930_consolidated.parquet     # 삼성전자 실데이터 (100일 일봉 + 펀더멘털)
│       ├── 000660_consolidated.parquet     # SK하이닉스 실데이터
│       ├── 005380_consolidated.parquet     # 현대차 실데이터
│       └── sample_check.parquet            # 검증용 샘플 데이터
├── modules/
│   ├── __init__.py                         # 루트 modules 패키지 초기화 파일 (현재 빈 파일)
│   └── data/                               # Phase 1: 데이터 수집 & 전처리 패키지
│       ├── __init__.py                     # Phase 1 컴포넌트 __all__ export 정의
│       ├── collector_fundamental.py        # R1: OpenDART/Naver/Mock 펀더멘털 수집 & 교차검증기
│       ├── collector_price.py              # R2: 일봉/분봉 OHLCV 시계열 주가 수집기 & 리샘플러
│       ├── streamer.py                     # R2: 실시간 틱/호가 수신, 링버퍼(50k) 및 캔들 집계기
│       ├── consolidator.py                 # R3: Point-in-Time merge_asof 병합 및 Parquet ZSTD I/O
│       └── pipeline.py                     # R3: 통합 데이터 수집 파이프라인 Facade
├── tests/
│   ├── __init__.py                         # 테스트 패키지 초기화
│   ├── test_fundamental.py                 # M1: 펀더멘털 & 교차검증 단위 테스트 (30 passed)
│   ├── test_price_streamer.py              # M2: 시계열 주가 & 스트리머 단위 테스트 (35 passed)
│   ├── test_consolidator.py                # M3: PIT 병합 & Parquet I/O 단위 테스트 (19 passed)
│   ├── test_phase1.py                      # R4: Phase 1 E2E 4-Tier 통합 스위트 (28 passed)
│   └── test_adversarial_challenger1.py     # 적대적 스트레스 및 경계조건 테스트 (23 passed)
├── etc/                                    # GEMINI.md Rule 10 준수 보조 공간
│   ├── logs/
│   │   └── stress_benchmark.log            # 스트레스 벤치마크 로그
│   └── scripts/
│       ├── stress_streamer.py              # 스트리머 부하 테스트 스크립트
│       ├── verify_e2e_challenger2.py       # E2E 챌린저 검증 스크립트
│       └── verification_results_challenger2.json
├── logs/
│   └── execution_notes.md                  # GEMINI.md Rule 13 자가 개선 실행 로그
└── backup/                                 # lock_manager.py 기반 자동 스냅샷 백업 저장소
    ├── collector_price.py.*.bak
    ├── consolidator.py.*.bak
    ├── test_phase1.py.*.bak
    └── ...
```

---

## 3. 실행 환경 및 의존성 분석

### 3.1 Python 가상환경 및 도구
- **Python 인터프리터**: `/home/imnyj/venv/bin/python3` (Python 3.12.3)
- **테스트 프레임워크**: `/home/imnyj/venv/bin/pytest` (pytest 9.0.3, pytest-cov 7.1.0, pytest-asyncio 1.3.0)
- **주요 설치 라이브러리**:
  - `decimal` (Python 내장 표준 라이브러리 - 1원 단위 정밀 회계 핵심)
  - `pandas` (v2.3.3)
  - `numpy` (v2.4.4)
  - `pyarrow` (v23.0.1)
  - `zstandard` (v0.25.0)
  - `torch` (v2.11.0), `stable_baselines3` (v2.7.0) (향후 Phase 4 강화학습용 설치 완료)
  - `requests` (v2.33.1)

### 3.2 Phase 1 기존 테스트 검증 결과
- **테스트 실행 명령**: `/home/imnyj/venv/bin/pytest -v`
- **검증 결과**: **135 passed in 13.77s (100% PASS, 0 failure, 0 error)**
- **회귀 방지 확인**: Phase 1의 모든 펀더멘털, 주가, 스트리머, PIT 병합, Parquet I/O, 적대적 테스트가 완전 무결하게 정상 작동 중임을 확인하였습니다.

---

## 4. 공통 인프라 도구 분석 (`Command/core/`)

GEMINI.md의 안전 수칙을 준수하기 위해 Implementer가 소스 코드 작성/수정 시 반드시 사용해야 하는 공통 도구 분석 결과:

### 4.1 파일 락 매니저 (`/home/imnyj/Command/core/lock_manager.py`)
- **기능**: 동시성 충돌 방지를 위한 파일 락 획득 및 릴리즈, 파일 수정 전 `backup/` 디렉토리에 자동 타임스탬프 스냅샷 백업 생성 (`shutil.copy2`).
- **사용법**:
  ```bash
  /home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py acquire <filepath> <agent_id>
  # 작업 수행
  /home/imnyj/venv/bin/python3 /home/imnyj/Command/core/lock_manager.py release <filepath> <agent_id>
  ```

### 4.2 감사 로거 (`/home/imnyj/Command/core/audit_logger.py`)
- **기능**: 파일 생성 및 수정에 대한 에이전트 식별자, 타임스탬프, 액션 내용 감사 추적 로깅 (`/tmp/agent_audit.log`).
- **사용법**:
  ```bash
  /home/imnyj/venv/bin/python3 /home/imnyj/Command/core/audit_logger.py log --agent <agent_id> --file <filepath> --action <description> [--parent <parent_id>]
  ```

---

## 5. Phase 2 핵심 요구사항 상세 분석 (`ORIGINAL_REQUEST.md`)

Phase 2의 핵심 목표는 **가상 체결 엔진(Mock Environment)** 을 구축하여 실전 투입 전 1원의 오차도 없는 모의 매매 및 회계 무결성을 달성하는 것입니다.

### 5.1 R1. Virtual Account Manager (가상 계좌 관리)
- **대상 위치**: `modules/engine/mock_environment.py` 내의 `VirtualAccount` / `AccountManager` / `Position` 클래스
- **핵심 기능**:
  - 초기 자본금(`initial_capital`), 현재 현금 잔고(`cash_balance`), 종목별 보유 포지션(`Position: symbol, quantity, avg_price, total_cost`) 관리.
  - **부동소수점 오차 원천 차단**: Python `Decimal` 기반의 정밀 산술 연산 또는 정수(1원/센트) 단위 연산 적용 (`ROUND_HALF_UP` 등 명시적 반올림 정책).
  - 총 자산 평가액(`portfolio_value` = 현금 잔고 + 보유 주식의 현재 평가금) 실시간 계산.
  - 실현 손익(`realized_pnl`), 미실현 손익(`unrealized_pnl`), 총 수익률 계산.

### 5.2 R2. Order Execution Engine (가상 주문 체결기)
- **대상 위치**: `modules/engine/mock_environment.py` 내의 `OrderExecutionEngine` / `MockExecutionEngine`
- **주문 모델**: `Order`, `Trade` / `ExecutionResult`, `OrderType` (Market, Limit), `OrderSide` (BUY, SELL), `OrderStatus` (PENDING, FILLED, REJECTED, CANCELLED)
- **국내 주식 표준 세금 및 수수료율**:
  - **증권거래세 (Tax)**: 매도(SELL) 주문 시에만 부과. 기본값 국내 표준 (예: 0.18% ~ 0.20%, 설정 가능).
  - **증권사 수수료 (Brokerage Fee)**: 매수(BUY) 및 매도(SELL) 모두 부과. 기본값 (예: 0.015% = 0.00015, 설정 가능).
  - 1원 단위 세금/수수료 절사/반올림 규칙 명확화 (`floor` 또는 `round`).
- **고정 비율 슬리피지(Slippage) 페널티**:
  - 시장가 주문 체결 시 현재가 대비 항상 일정한 비율(예: 0.1% ~ 0.3%, 기본값 0.2% 등)로 **투자자에게 불리한 방향**으로 체결:
    - 매수 시 체결가: $\text{Execution Price} = \text{Market Price} \times (1 + \text{Slippage Rate})$
    - 매도 시 체결가: $\text{Execution Price} = \text{Market Price} \times (1 - \text{Slippage Rate})$
- **체결 제약 및 방어 로직**:
  - 매수 시: `cash_balance >= (체결금액 + 수수료)` 검증, 잔고 부족 시 주문 거절(`REJECTED_INSUFFICIENT_CASH`).
  - 매도 시: `position.quantity >= 주문수량` 검증, 보유 수량 부족 시 주문 거절(`REJECTED_INSUFFICIENT_SHARES`).
  - 호가 또는 주가가 0 이하이거나 비정상일 때 주문 거절.

### 5.3 R3. Dummy Strategy Simulator (더미 룰 기반 검증 래퍼)
- **대상 위치**: `modules/engine/mock_environment.py` 내의 `DummyStrategySimulator` / `MockEnvironment` / `TradingStrategy` (예: `MovingAverageCrossStrategy`, `PingPongStrategy`)
- **핵심 기능**:
  - 복잡한 ML/RL 모델 연결 전, 간단한 룰 기반 로직으로 시세 시계열 데이터(또는 합성 데이터 / `data/raw/`의 실데이터)를 스트리밍하며 연속적인 매수/매도 주문 발생.
  - 최소 1,000회 이상의 연속 거래를 완벽히 수행하여 시스템 안정성 및 무결성 검증.
  - 마이너스 잔고 발생 방지, 예외 복원력, 거래 내역(`trade_history`) 및 자산 변동 곡선(`equity_curve`) 추적.

### 5.4 R4. 검증 및 승인 기준 (Acceptance Criteria)
- **대상 위치**: `tests/test_phase2.py`
- **검증 항목**:
  1. **1,000회 이상 연속 매수/매도 주문 처리** 시 현금 잔고 음수 미발생 및 논리적/산술적 오류 제로.
  2. **회계적 무결성 1원 단위 증명 (Zero Accounting Discrepancy)**:
     $$\text{Initial Capital} - (\text{Final Cash} + \text{Final Holdings Valuation at Market}) \equiv \text{Cumulative Fees} + \text{Cumulative Taxes} + \text{Cumulative Slippage Cost} + \text{Trading Loss/Gain Difference}$$
     또는 순수 거래 손익과 비용의 합이 총 자산 변동과 **1원의 오차도 없이 완벽히 일치**해야 함.
  3. **4-Tier 테스트 구조**:
     - Tier 1: 단위 기능 (Decimal 계좌 입출금, 매수/매도 체결, 세금/수수료/슬리피지 계산)
     - Tier 2: 경계 및 예외 방어 (잔고 부족, 수량 부족, 상하한가/0원 가격, 대규모 주문)
     - Tier 3: 결합 상호작용 (시세 스트리머/데이터 피더와 가상 엔진의 연속 결합)
     - Tier 4: 실세계 시나리오 및 1,000+회 대규모 룰 기반 시뮬레이션 회계 무결성 증명

---

## 6. 구현 및 파일 배치 권장 사항

1. **신규 모듈 디렉토리 생성**:
   - `modules/engine/` 디렉토리 생성
   - `modules/engine/__init__.py`: 공개 클래스 및 열거형 export 정의
   - `modules/engine/mock_environment.py`: R1 (VirtualAccount), R2 (OrderExecutionEngine), R3 (MockEnvironment & DummyStrategy) 구현
2. **루트 모듈 패키지 업데이트**:
   - `modules/__init__.py`에 `data` 및 `engine` 패키지 export 노출
3. **테스트 스위트 생성**:
   - `tests/test_phase2.py`: 4-Tier 종합 검증 스위트 구축

---

## 7. 결론
Auto Stock 코드베이스는 매우 잘 정돈되어 있으며, Phase 1에서 구축된 데이터 파이프라인(`modules/data/`) 및 Parquet 데이터(`data/raw/`), 4-Tier 테스트 인프라가 완벽히 동작하고 있습니다. Phase 2 가상 체결 엔진의 설계 및 구현을 즉시 착수할 수 있는 완벽한 준비 상태입니다.
