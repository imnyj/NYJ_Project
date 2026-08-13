## 2026-08-12T17:13:20+09:00
You are teamwork_preview_auditor_m2_1.
Your working directory is `/home/imnyj/Workspace/House/.agents/teamwork_preview_auditor_m2_1`.

Your task is to perform a forensic integrity audit on `/home/imnyj/Workspace/House/House_Financial_Simulation_Report.md`.

Audit checks:
1. Static analysis & content verification: Ensure all financial calculations, tax rates, loan limits, income thresholds, and simulation outputs are authentic and genuinely derived from financial parameters and tax law (no hardcoded fake values, facade tables, or mocked data).
2. Code & engine alignment: Cross-check numbers with `/home/imnyj/Workspace/House/etc/scripts/calc_engine.py` and `/home/imnyj/Workspace/House/etc/data/financial_params.json`.
3. Check for any integrity violations (e.g. fabricated facts, invalid legal references, or policy misrepresentations).

Deliver `handoff.md` in your working directory containing an explicit verdict: `CLEAN` or `INTEGRITY VIOLATION`, with full audit findings and evidence. Notify parent when finished.
