# Project Plan: Auto_Stock Codebase Review & Refactoring

## 1. Objectives
- 전체 코드베이스 전수 검토 및 결함 수정 (M1~M4)
- 18개 테스트 스위트 전수 100% PASS (0 failed) 달성
- `Report/codebase_review_and_fixes.md` 보고서 작성 (3대 영역 상세 분석 및 3개 이상 심층 Before/After 비교)
- Forensic Integrity Verification & Sentinel 최종 완료 보고

## 2. Milestone Structure
1. **Milestone 1: System & API Core Refactoring** [COMPLETED]
   - `core/kiwoom_api.py`, `core/config.py`, root cleanup to `backup/`, `etc/scripts/test_extreme_4_1.py`
2. **Milestone 2: Data Engine & Resource Safety** [CURRENT]
   - `modules/data/collector_price.py` (BUG-L02 NaN fillna min bug, BUG-M01 session close)
   - `modules/data/collector_fundamental.py` (BUG-L06 zero operating profit boolean bug, BUG-M01 session close)
   - `modules/data/consolidator.py` (BUG-L03 merge_asof symbol isolation & lookahead date estimate)
   - `modules/data/streamer.py` (BUG-M02 stop timeout / zombie thread, BUG-M03 circular buffer)
3. **Milestone 3: ML/RL Pipeline & Env Refactoring** [UPCOMING]
   - `modules/engine/hybrid_trading_env.py` (BUG-RL01 step observation index lag, BUG-RL02 HOLD trade_record leak)
   - `modules/models/feature_extractor.py` & `modules/models/hybrid_policy.py` (BUG-RL03 CPU/CUDA tensor device cast)
   - `modules/engine/live_learning_simulator.py` (BUG-RL04 5-tuple step & log return, BUG-C03 singleton lock)
   - `modules/hpo/optuna_pipeline.py` (BUG-RL05 zero-variance Sharpe return / zero trade penalty)
4. **Milestone 4: Test Suite Alignment & 100% Pytest Verification** [UPCOMING]
   - `tests/test_adversarial_m2_rl_challenger.py` (BUG-T01 GAE oracle indexing dones[t] vs dones[t+1])
   - Full pytest execution across all 18 test files (target: 426+ passed, 0 failed)
5. **Milestone 5: Comprehensive Review Report & Final Verification** [UPCOMING]
   - `Report/codebase_review_and_fixes.md` 작성
   - Forensic Auditor verification & final Sentinel sign-off

## 3. Subagent Execution Strategy
- Workers carry out atomic code modifications under lock manager & audit logger.
- Reviewers & Challengers independently verify tests and stress scenarios.
- Auditor validates zero cheating / genuine logic.
- Orchestrator checks gates and progresses milestones.
