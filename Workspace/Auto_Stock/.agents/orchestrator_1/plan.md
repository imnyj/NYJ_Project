# Orchestration Plan: Phase 1 Data Collection Pipeline

## 1. Goal
Auto Stock ML/RL Trader의 Phase 1 (데이터 수집 파이프라인) 구축을 위한 전체 라이프사이클 총괄 오케스트레이션.
- R1: Fundamental Data Collector (OpenDART, FinanceDataReader, Naver/Kiwoom 등 다중 출처 재무/투자지표 수집 및 교차 검증)
- R2: Price Data Collector & Streamer (과거 분봉/일봉 시계열 수집 및 실시간 캐싱 기초 마련)
- R3: Data Consolidation (펀더멘털+가격 결합, Parquet 포맷 저장)
- R4: 검증 및 승인 (삼성전자 '005930' 대상 E2E 수집/병합/저장 및 자동화 테스트 통과)

## 2. Phase Decomposition
### Step 0: Survey & Environment Analysis
- 탐색 에이전트 3인 병렬 디스패치:
  - Explorer 1: Python 환경, 설치된 패키지(OpenDARTReader, FinanceDataReader, pykrx, pandas, pyarrow 등), API 키 환경변수 및 키움 연동 환경 조사
  - Explorer 2: R1 펀더멘털 데이터 수집기 및 교차 검증 알고리즘 요구사항 상세 분석
  - Explorer 3: R2/R3 가격 수집기, 실시간 스트리머 캐싱, Parquet 통합 파이프라인 요구사항 상세 분석
- 결과 수합하여 `PROJECT.md` 작성.

### Step 1: Dual-Track Dispatch
- **Track A (E2E Testing Track)**:
  - `teamwork_preview_test_writer` 또는 전용 워커를 통한 `tests/test_phase1.py` 및 테스트 인프라(`TEST_INFRA.md`, `TEST_READY.md`) 구축.
- **Track B (Implementation Track)**:
  - Milestone 1: Fundamental Data Collector (`modules/data/collector_fundamental.py`)
  - Milestone 2: Price Data Collector & Streamer (`modules/data/collector_price.py`, `modules/data/streamer.py`)
  - Milestone 3: Data Consolidation & Storage (`modules/data/consolidator.py`, `modules/data/pipeline.py`)

### Step 2: Milestone Iteration Gate Loop (각 마일스톤 공통)
- Explorer (분석/설계) -> Worker (구현/자체테스트) -> Reviewer 2인 (코드리뷰) -> Challenger 2인 (경계/결측 검증) -> Forensic Auditor (진정성 검증) -> Gate 판정.

### Step 3: Final E2E Integration & Verification (Milestone 4)
- 실제 삼성전자(005930) 데이터 수집/교차검증/Parquet 저장 E2E 테스트 수행.
- 모든 Tier 테스트 100% 통과 확인.

### Step 4: Final Reporting
- 최종 산출물 및 검증 결과 수합하여 상위 Sentinel/사용자에게 한글 종합 보고서 전달.
