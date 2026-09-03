# Execution Plan — Phase 5 & 6 (Final Milestone)

## Objective
E2E 통합 테스트 수행, HPO 파이프라인 결과(`etc/hpo_results/baseline_hpo.csv`, 3개 이상 Trial) 및 하이브리드 Action Space 검증, 리뷰 및 무결성 감사(Forensic Audit) 완료 후 최종 완료 보고.

## Steps
1. **Survey & Explore (Phase 5-A)**:
   - 탐색 에이전트(Explorer) 3인을 병렬 디스패치하여 현재 `tests/test_hpo_pipeline.py`, `etc/hpo_results/baseline_hpo.csv`, Makefile 타겟(`make test-hpo`), 하이브리드 Action Space 구현 상태를 정밀 분석.
2. **Worker Execution (Phase 5-B)**:
   - Worker 에이전트를 디스패치하여 전체 테스트 스위트(`pytest tests/test_hpo_pipeline.py -v` 및 `make test-hpo`)를 실행하고, CSV 출력 및 Trial 수(>=3), 지표 계산을 검증.
3. **Review & Adversarial Challenge (Phase 5-C)**:
   - Reviewer 2인 디스패치 (코드 품질, Gymnasium 1.2.0 호환성, 지표 정확도 검토).
   - Challenger 2인 디스패치 (극한 경계 조건, 영분산 방어, 파산 처리 등 적대적 스트레스 테스트).
4. **Forensic Integrity Audit (Phase 5-D)**:
   - Forensic Auditor 디스패치 (하드코딩 방지, 가짜 객체 유무, 1원 단위 정밀도 정직성 검증).
5. **Gate Evaluation & Final Report (Phase 6)**:
   - Gate 결과 종합 (`GATE_STATUS.md` 작성 및 `PROJECT.md` 갱신).
   - 모든 검증 통과 시 Sentinel / Parent에게 최종 완료 보고서 전송.
