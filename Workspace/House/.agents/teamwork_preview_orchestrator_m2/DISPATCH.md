## 2026-08-12T08:10:27Z
<USER_REQUEST>
You are teamwork_preview_orchestrator_m2, Sub-Orchestrator for Milestone 2 (Comprehensive Financial Simulation Report).
Your working directory is: `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m2`

Read:
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/PROJECT.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_1/survey_budget.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md`
- Data engine & params in `etc/scripts/calc_engine.py` and `etc/data/financial_params.json`

Your Scope (Milestone 2):
Produce the comprehensive, publication-ready Markdown report saved at `/home/imnyj/Workspace/House/House_Financial_Simulation_Report.md`.
The report must cover:
1. **R1. 일회성 비용 전수조사**: Cheongju Bangseo-dong Xi (<30 pyeong) 3.5억, 3.75억, 4.0억 scenarios. Detailed breakdown of acquisition tax (2025-2026 rates & 200만 First-time buyer exemption), legal fees (~50~55만), broker fee statutory cap (0.4%+VAT=0.44%), stamp duty (15만), National Housing Bond discount purchase (공시가 70% x 2.1~2.3% x 10%), moving fee (150만), repair/cleaning (200만).
2. **R2. 대출 시나리오 비교 분석**:
   - 보유 현금 2.3억 원 기준 필요 대출금 (1.2억 / 1.45억 / 1.7억).
   - Didimdol/Bogeumjari vs Commercial Bank comparison.
   - **Crucial Income Analysis**: Document joint couple income (~1.3억~1.5억+ KRW with husband 5,296만 + wife 8,000만+) exceeding current Didimdol income limits, AND present government deregulation scenario where Didimdol becomes available.
   - Secondary loan fees: establishment fee (bank pays), loan stamp tax (7.5만 borrower share), HF/HUG guarantee fees (0.05~0.1%).
3. **R3. 월별/연별 종합 재무 시뮬레이션**:
   - Monthly income (330만), 13 expense categories (~239만 with rent 31.1만 removed and replaced by maintenance 20만, parking 1만, internet/TV 3만 -> net monthly fixed 2,319,708 KRW).
   - Bonus prepayment schedule: Jan/Jul 400만, Feb/Aug 100만 -> total 1,000만/year.
   - Initial 1-year monthly breakdown + annual summary until payoff for 3.5억, 3.75억, 4.0억 scenarios.
4. **R4. 행정 및 법률 신고 체크리스트**: Post-purchase timeline (잔금 -> 등기 -> 취득세 신고 -> 전입신고 -> 확정일자 -> 재산세/종부세) with deadline, institution, required documents for each step.

Execute via Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate loop. Record dead ends in DEAD_ENDS.md and gate status in GATE_STATUS.md in your working directory.
Follow GEMINI.md rules, Korean language output, and write the report to `/home/imnyj/Workspace/House/House_Financial_Simulation_Report.md`. When complete, set M2 status to DONE in PROJECT.md and deliver your handoff.md.
</USER_REQUEST>
