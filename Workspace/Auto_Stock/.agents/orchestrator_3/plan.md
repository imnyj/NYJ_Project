# Phase 3 Orchestration Plan: 실거래 제어 모듈 구축

## 1. 개요 및 목표
- 목표: 키움 REST API 연동, 수동 매매 CLI 인터페이스, 보안 설정 관리, E2E Mock 테스트 및 무결성 검증을 완벽하게 수행
- 원칙: DISPATCH-ONLY 원칙 준수, 서브에이전트 계층 분업, 엄격한 코드 리뷰/챌린지/무결성 감사 수행

## 2. 단계별 마일스톤
- **Phase 0: Survey & Exploration (병렬 탐색)**
  - Explorer 1: 기존 코드베이스 구조 및 이전 Phase(1, 2 등) 모듈/디렉토리 구조 조사
  - Explorer 2: Kiwoom Open API REST 명세(OAuth2 토큰 발급, 시세 조회, 주문, 계좌 조회, 모의투자 vs 실서버 엔드포인트) 및 인터페이스 설계 조사
  - Explorer 3: 설정 파일/시크릿 관리(`config/settings.yaml`, `.env`, 하드코딩 방지 구조) 및 테스트 요구사항 조사
- **Phase 1: Architecture & Project Plan (PROJECT.md 수립)**
  - Feature Inventory, 인터페이스 계약, 파일 레이아웃 확정
- **Phase 2: Core Implementation (구현)**
  - Worker: `config/settings.yaml`, `core/config.py` (또는 기존 설정 모듈 확장), `core/kiwoom_api.py`, `modules/engine/manual_trader.py` 구현 및 단위 검증
- **Phase 3: E2E Testing Track (테스트 스위트 구축)**
  - Test Writer: `tests/test_phase3_api.py` 작성 (토큰 발급 -> 주문 전송 -> 잔고 확인 Mock 테스트 및 예외 처리, 모의/실서버 토글 테스트)
- **Phase 4: Multi-Agent Review & Challenge & Audit (다각적 검증)**
  - Reviewer 1 & 2: 정적 분석, 코드 품질, 요구사항 충족도 리뷰
  - Challenger 1 & 2: 예외 상황, 엣지 케이스, 비정상 입력 스트레스 테스트 및 모킹 검증
  - Forensic Auditor: 하드코딩 0건 정적 분석, 페이크 구현/치팅 여부 전수 감사 (Binary Veto)
- **Phase 5: Gate Check & Final Reporting (최종 종합 및 보고)**
  - 종합 결과 분석 및 최종 산출물 보고서 작성, 부모 에이전트 보고

## 3. 검증 기준
- `tests/test_phase3_api.py` 100% 통과
- 하드코딩 0건 정적 분석 통과
- Reviewer, Challenger, Auditor 전원 APPROVE / CLEAN
