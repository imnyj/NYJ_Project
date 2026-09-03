# BRIEFING — 2026-09-02T17:17:05+09:00

## Mission
Implement and verify Milestone 2: Data Engine & Resource Safety for Auto_Stock.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2
- Original parent: a86f6aa5-e40d-4a36-834a-fdf51cf56a97
- Milestone: M2 - Data Engine & Resource Safety

## 🔒 Key Constraints
- Follow /home/imnyj/GEMINI.md (File locking via lock_manager.py, audit logging via audit_logger.py, Korean communication).
- Minimal change principle, genuine implementations (NO CHEATING).
- Ensure 100% pytest pass across data module test suites without regressions.

## Current Parent
- Conversation ID: a86f6aa5-e40d-4a36-834a-fdf51cf56a97
- Updated: 2026-09-02T17:17:05+09:00

## Task Summary
- **What to build**: Refactor collector_price.py, collector_fundamental.py, consolidator.py, streamer.py for robust data cleaning, resource safety, context managers, and concurrency safety.
- **Success criteria**: All data test suites pass (test_phase1_data.py, test_phase1_data_adv.py, test_phase1_pipeline.py, test_phase1_streamer.py), no socket/thread leaks, no cross-symbol contamination, no low=0 price corruption.
- **Interface contracts**: /home/imnyj/Workspace/Auto_Stock/PROJECT.md
- **Code layout**: /home/imnyj/Workspace/Auto_Stock/modules/data/

## Key Decisions Made
- [TBD]

## Artifact Index
- /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2/DISPATCH.md — Dispatch instructions
- /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2/progress.md — Progress tracker
- /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_m2/handoff.md — Handoff report

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Clean
- **Tests added/modified**: Pending
