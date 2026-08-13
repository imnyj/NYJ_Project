# BRIEFING — 2026-08-12T17:13:20+09:00

## Mission
Review House_Financial_Simulation_Report.md focusing on R3 (월별/연별 종합 재무 시뮬레이션) and R4 (행정 및 법률 신고 체크리스트).

## 🔒 My Identity
- Archetype: reviewer / critic
- Roles: reviewer, critic
- Working directory: /home/imnyj/Workspace/House/.agents/teamwork_preview_reviewer_m2_2
- Original parent: 0ca72e7a-3dba-4c59-8372-c9ce820fe68d
- Milestone: m2
- Instance: 2 of 2

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code or House_Financial_Simulation_Report.md directly.
- Must produce detailed evidence and verification for R3 & R4 requirements.
- Must check for integrity violations (hardcoded test results, shortcuts, facade implementations).
- Must issue an explicit verdict: APPROVE or REQUEST_CHANGES in handoff.md.

## Current Parent
- Conversation ID: 0ca72e7a-3dba-4c59-8372-c9ce820fe68d
- Updated: not yet

## Review Scope
- **Files to review**:
  - `/home/imnyj/Workspace/House/House_Financial_Simulation_Report.md`
- **Reference context files**:
  - `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
  - `/home/imnyj/Workspace/House/PROJECT.md`
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m2/SCOPE.md`
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_2/analysis_r3.md`
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m2_3/analysis_r4_outline.md`
- **Review criteria**:
  - R3: Baseline monthly net income 3.3 million KRW, 13 expense items (rent removed, maintenance 20만, parking 1만, TV/internet 3만 added -> net expenses 2,319,708 KRW), surplus (980,292 KRW), bonus prepayment schedule (Jan/Jul 400만, Feb/Aug 100만 = 1,000만/yr total). Initial 1-year monthly cashflow table & annual payoff schedules until 100% principal repayment for 3.5억, 3.75억, 4.0억 scenarios.
  - R4: Comprehensive timeline from contract/balance to property tax/종부세, 6-column markdown table (단계, 절차명, 법정 기한, 담당 기관, 필요 서류, 핵심 유의사항).

## Key Decisions Made
- Initializing review workflow for R3 and R4.

## Artifact Index
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_reviewer_m2_2/handoff.md` — Final review report and verdict.
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_reviewer_m2_2/progress.md` — Liveness heartbeat.
