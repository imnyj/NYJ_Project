## 2026-08-12T08:07:04Z

<USER_REQUEST>
You are teamwork_preview_worker_m1_1, Worker for Milestone 1 (Financial Data Engine & Analysis).
Your working directory is: `/home/imnyj/Workspace/House/.agents/teamwork_preview_worker_m1_1`

Read:
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/PROJECT.md`
- `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_m1/SCOPE.md`
- Explorer findings:
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_1/explorer_m1_1.md`
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m1_2/explorer_m1_2.md`
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_spec_miner_m1_3/spec_miner_m1_3.md`

Your Task:
1. Create `etc/data/financial_params.json` with the full JSON parameter schema designed by the Explorers (scenarios 3.5억/3.75억/4.0억, cash reserve 2.3억, monthly income 330만, bonuses, monthly expenses net 2,319,708 KRW, R1 parameters, R2 parameters).
2. Implement `etc/scripts/calc_engine.py` containing:
   - `load_financial_params(json_path=None)`
   - `calculate_r1_costs(price, is_first_home=True, params=None)`
   - `calculate_r2_loans(price, cash_reserve=230000000, params=None)`
   - `run_all_scenarios(json_path=None)`
   - CLI interface (`--all`, `--json`, `--verify`, etc.)
3. Implement `etc/tests/test_calc_engine.py` (and/or `etc/scripts/verify_m1.py`) with complete pytest unit tests verifying R1 calculations, R2 loan required amounts (1.2억/1.45억/1.7억), stamp tax (7.5만), living expenses (2,319,708), and edge cases.
4. Run python verification / pytest commands to ensure 100% passing results. Document the exact test commands and outputs in your report.

MANDATORY RULES & INTEGRITY WARNING:
- DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
- Follow GEMINI.md rules: use file locking protocol via `/home/imnyj/Command/core/lock_manager.py` when writing/modifying code files, and log actions via `/home/imnyj/Command/core/audit_logger.py`.
- Write auxiliary scripts to `etc/scripts/` and tests to `etc/tests/`.
- Write your detailed completion report to `/home/imnyj/Workspace/House/.agents/teamwork_preview_worker_m1_1/worker_m1_1.md` and handoff report to `handoff.md` in your working directory.

Communicate handoff when completed.
</USER_REQUEST>

## 2026-08-12T08:07:27Z

**Context**: Updated User Capital Operation & Bonus Repayment Request
**Content**: ORIGINAL_REQUEST.md was updated with exact bonus repayment parameter details:
1. Bonus Prepayment Schedule (Total 1,000만 KRW/year):
   - Month 1 (Jan) & Month 7 (Jul): 4,000,000 KRW (out of 5,000,000 KRW 교연비, 1,000,000 KRW reserved)
   - Month 2 (Feb) & Month 8 (Aug): 1,000,000 KRW (out of extra income)
2. Monthly Housing Repayment Capacity: 500,000 KRW/month for loan principal & interest.
3. Cash reserve: 230,000,000 KRW (30M self + 100M self parents + 100M girlfriend parents).

**Action**: Please ensure `etc/data/financial_params.json`, `etc/scripts/calc_engine.py`, and `etc/tests/test_calc_engine.py` use these updated bonus parameters (Month 1: 4M, Month 2: 1M, Month 7: 4M, Month 8: 1M -> total 10M/year) as default settings and verify with test scripts.

