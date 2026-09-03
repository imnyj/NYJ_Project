# Orchestration Plan — Phase 2: Mock Environment

## Objective
주식 자동 매매 시스템의 가상 체결 엔진(Mock Environment)을 체계적으로 구현하고, 1,000회 이상의 연속 주문 및 부동소수점 오차 없는 엄격한 1원 단위 회계 무결성을 100% E2E 테스트로 검증 완료한다.

## Architecture & Work Breakdown
1. **Survey Phase (Step 0)**
   - 3명의 병렬 탐색 에이전트(Explorer 1, 2, 3)를 디스패치하여 기존 저장소 구조, 모듈 인터페이스, 한국 거래소 수수료/세금 기준, 슬리피지 모델, 기존 Phase 1 및 관련 파일들을 면밀히 조사.
2. **Decomposition & Specification (Step 1)**
   - 탐색 결과를 종합하여 `PROJECT.md` (아키텍처, 기능 목록, 마일스톤, 인터페이스 계약) 및 `TEST_INFRA.md` 작성.
3. **E2E Testing Track (Step 2)**
   - 테스트 작성 에이전트(`teamwork_preview_test_writer`)를 투입하여 4개 티어(기능 커버리지, 경계값/코너케이스, 교차 상호작용, 현실 시뮬레이션) 테스트 구현 및 `TEST_READY.md` 발행.
4. **Implementation Track (Step 3)**
   - 작업 에이전트(`teamwork_preview_worker`)를 투입하여 `modules/engine/mock_environment.py`에 가상 계좌 관리(Decimal/정밀 정수 기반), 가상 체결기, 더미 룰 전략 시뮬레이터 래퍼 구현.
5. **Verification & Audit Gate (Step 4 & 5)**
   - 2명의 독립 Reviewer 검토 + 2명의 Challenger 적대적 테스트 + 1명의 Forensic Auditor 무결성 검증.
   - GATE_STATUS.md 판정 (Clean Audit + 100% Test Pass + All Approvals).
6. **Final Acceptance & Reporting (Step 6)**
   - 최종 검증 결과 요약 및 사용자 보고서 작성.
