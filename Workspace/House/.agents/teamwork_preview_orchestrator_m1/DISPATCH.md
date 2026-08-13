## 2026-08-12T17:05:48Z
You are teamwork_preview_orchestrator_m1, Sub-Orchestrator for Milestone 1 (Financial Data Engine & Analysis).
Your working directory is: `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m1`

Read:
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/PROJECT.md`
- Survey reports:
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_1/survey_budget.md`
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md`

Your Scope (Milestone 1):
1. Build the Financial Data Engine (`etc/scripts/calc_engine.py` and `etc/data/financial_params.json`).
2. Implement exact cost calculation logic for R1: One-time purchase costs for Cheongju Bangseo-dong Xi (<30 pyeong, 3.5억, 3.75억, 4.0억) including:
   - Acquisition tax (2025-2026 rates & 200만 won First-time buyer exemption)
   - Legal fees (등기 대행 ~50~55만)
   - Statutory broker fee cap (0.4% + 10% VAT)
   - Stamp duty (15만)
   - National Housing Bond discount purchase (공시가 70% x 2.1~2.3% x 10% discount)
   - Moving fee (150만) & Repair/cleaning fee (200만)
3. Implement mortgage scenario comparative analysis for R2:
   - 보유 현금 2.3억 원 기준 필요 대출금 (1.2억 / 1.45억 / 1.7억)
   - Didimdol/Bogeumjari (신혼부부 특례 연 3.0~3.3%, 한도 4억) vs Commercial bank mortgage
   - Secondary loan fees: establishment fee (bank pays), loan stamp tax (차주 7.5만), HF/HUG guarantee fees (0.05~0.1%).
4. Verify all calculation outputs programmatically with test scripts.

Execute via the iteration loop (Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate). Record dead ends in DEAD_ENDS.md and gate status in GATE_STATUS.md in your working directory.
Follow GEMINI.md rules, file locking protocol, Korean language output, and write all auxiliary scripts to `etc/scripts/`. When complete, set Milestone 1 status to DONE in PROJECT.md and deliver your handoff.md.
