## 2026-08-12T08:06:08Z
You are teamwork_preview_explorer_m1_1, Explorer 1 for Milestone 1 (Financial Data Engine & Analysis).
Your working directory is: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1`

Read:
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/PROJECT.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m1/SCOPE.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_1/survey_budget.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_3/survey_legal_mortgage.md`

Task:
1. Analyze all financial parameters required for `etc/data/financial_params.json` and design the complete JSON structure.
2. Formulate the exact mathematical equations and algorithm for R1 (One-time purchase costs for 3.5억, 3.75억, 4.0억):
   - Acquisition tax: 1.0% base + 0.1% local edu tax = 1.1% total. Exemption: First-time buyer exemption of 2,000,000 KRW deducted from base tax.
   - Legal fees: 500,000 KRW for 3.5억, 520,000 KRW for 3.75억, 550,000 KRW for 4.0억.
   - Statutory brokerage fee cap: 0.4% + 10% VAT = 0.44% of purchase price.
   - Stamp duty: 150,000 KRW fixed.
   - National Housing Bond discount purchase: Public appraisal price (~70% of market price). Bond buy rate: 2.1% for <2.6억 public price (3.5억 scenario), 2.3% for >=2.6억 public price (3.75억 & 4.0억 scenarios). Discount rate: 10% of bond buy amount.
   - Moving fee: 1,500,000 KRW fixed.
   - Basic repair & cleaning fee: 2,000,000 KRW fixed.
3. Recommend clear implementation guidelines for `calc_engine.py` and write your report to `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1/explorer_m1_1.md` and handoff.md.

Follow GEMINI.md rules and Korean language output for reports. Communicate handoff when done.
