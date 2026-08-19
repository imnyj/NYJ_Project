# Project: Paper4 IEEE TWC V2X DCC REMO-DQN Paper

## Architecture
- Target Journal: IEEE Transactions on Wireless Communications (TWC)
- Paper Title: REMO-DQN: 자원 효율적 다중 목적 심층 Q-네트워크를 활용한 고밀도 V2X 네트워크의 분산 혼잡 제어 (REMO-DQN: Resource-Efficient Multi-Objective Deep Q-Network for Decentralized Congestion Control in Dense V2X Networks)
- Language: Korean (한국어) with complete Markdown and LaTeX equations
- Central Deliverable Path: `/home/imnyj/Workspace/paper4/paper/`
  - `paper/01_introduction.md` (제1장 서론)
  - `paper/02_related_works.md` (제2장 관련 연구)
  - `paper/03_system_model.md` (제3장 시스템 모델 및 REMO-DQN 아키텍처)
  - `paper/04_scenario_flow.md` (제4장 동적 시나리오 흐름)
  - `paper/05_performance_evaluation.md` (제5장 성능 평가)
  - `paper/06_conclusion.md` (제6장 결론)
  - `paper/paper4_draft_korean.md` (완결된 마스터 논문 초안, 175KB, 888 라인)
- Auxiliary/temp files: `etc/`

## Feature Inventory
| # | Feature / Section | Description | Milestone | Status |
|---|-------------------|-------------|-----------|--------|
| 1 | R1. Introduction (서론) | 5단락 구성 (문단당 5문장 이상: 배경, 문제점 1, 문제점 2, 제안방안 및 3대 기여도, 논문구성) | M1 | DONE |
| 2 | R2. Related Works (관련 연구) | 표준 DCC, 단일 DRL, MADRL, 2025~2026 MoE+무선망/RL 최신 연구 포함 + 6열 비교 테이블 | M2 | DONE |
| 3 | R3. System Model & REMO-DQN | System Overview, MDP Formulation (S, A, R1/R2), REMO-DQN Architecture (ResNet+MoE+Dueling DQN) | M3 | DONE |
| 4 | R4. Main Body Scenario Flow | 4.1 패킷발생/트래픽혼합, 4.2 채널경합/MAC충돌, 4.3 DRL 혼잡인지, 4.4 동적 라우팅 및 전송제어 | M4 | DONE |
| 5 | R5. Performance Evaluation | 14개 벤치마크 모델, 7대 핵심 지표 (수렴도, CBR시계열안정성, PDR, 에너지효율, AoI vs Density, 하드웨어 Latency/FLOPs) | M5 | DONE |
| 6 | R6. Conclusion & Integration | 결론 도출, 종합 마스터 논문 초안 조립, Reviewer 1/2 승인, Challenger 1/2 승인, Forensic Auditor CLEAN 통과 | M6 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 0 | Survey & Architecture Mapping | Codebase, experimental data, MoE literature, and paper outline survey | none | DONE |
| 1 | M1: Section 1 Introduction | IEEE TWC style 5-paragraph introduction (5+ sentences each) to `paper/01_introduction.md` | M0 | DONE |
| 2 | M2: Section 2 Related Works | Related works + 2025-2026 MoE wireless papers + 6-col table to `paper/02_related_works.md` | M0 | DONE |
| 3 | M3: Section 3 System Model & REMO-DQN | System model, MDP formulation (S, A, R1/R2), REMO-DQN architecture to `paper/03_system_model.md` | M0 | DONE |
| 4 | M4: Section 4 Main Body Scenario Flow | 4.1 ~ 4.4 detailed scenario and mechanisms to `paper/04_scenario_flow.md` | M0 | DONE |
| 5 | M5: Section 5 Performance Evaluation | 14 models, 7 metrics, tables, figure references to `paper/05_performance_evaluation.md` | M0 | DONE |
| 6 | M6: Full Paper Synthesis & Review | Complete master draft integration to `paper/paper4_draft_korean.md`, Reviewers/Challengers/Auditor Gate PASS | M1~M5 | DONE |

## Final Deliverables Index
- `/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md`: 전 챕터 및 초록, 목차, 참고문헌 [1]~[27]이 통합된 IEEE TWC 수준 마스터 한국어 논문 초안.
- `/home/imnyj/Workspace/paper4/paper/01_introduction.md` ~ `06_conclusion.md`: 챕터별 모듈형 마크다운 원고.
- `/home/imnyj/Workspace/paper4/.agents/orchestrator_1/GATE_STATUS.md`: 최종 게이트 검증 승인 기록.
