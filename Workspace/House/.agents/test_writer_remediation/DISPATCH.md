## 2026-08-12T08:12:41Z

<USER_REQUEST>
You are test_writer_remediation working on the House Financial Simulation Project E2E Test Suite.
Your working directory is: `/home/imnyj/Workspace/House/.agents/test_writer_remediation`

MANDATORY TASK:
Execute all 8 Remediation Tasks detailed in the Remediation Plan to fix every integrity violation, facade test, hardcoded lookup table, parser flaw, and documentation typo.

Primary Document to Follow:
- `/home/imnyj/Workspace/House/.agents/explorer_e2e_remediation/handoff.md` (READ THIS FIRST - FOLLOW ALL 8 TASKS EXACTLY)

Summary of Tasks:
1. `etc/tests/helpers/reference_engine.py`: Remove all hardcoded `if price == 350000000:` lookup tables in `calculate_bond_discount`. Implement genuine statutory calculation formula (`public_price * bond_rate * discount_rate`). Update `simulate_timeline` to use `base_fixed_spending`.
2. Unify acquisition tax calculation across `calc_engine.py` and `reference_engine.py` using 1.1% combined tax rate minus 2,000,000 KRW first-home discount (resulting in 1,850,000 for 3.5억, 2,125,000 for 3.75억, 2,400,000 for 4.0억).
3. Replace all self-certifying / tautological facade tests in `test_tier1.py` and `test_tier2.py` (e.g. `stamp_tax = 75000; assert stamp_tax == 75000`) with authentic verification calling reference engines or parsing real files.
4. Remove artificial pass shortcuts when files are missing (e.g. `if parsed["exists"]: ... else: assert True`). Use `@pytest.mark.skipif(not os.path.exists(...), reason=...)` instead.
5. Fix `run_e2e_tests.py`: add `test_calc_engine.py` to `tier_files` list, and fix Pytest collection/import error handling so any exit code != 0 from pytest causes `run_e2e_tests.py` to fail and return exit code 1.
6. Fix `html_parser.py` (exact DOM ID matching, true dark mode/glassmorphism detection) and `report_parser.py` (dynamic markdown table parsing).
7. Fix arithmetic sum typos in `TEST_INFRA.md` §3.1.5 (3.5억 total 8,055,000 KRW) and update `PROJECT.md` line 79 bonus array to the latest 10M/yr plan (`{month: 1, amount: 4000000}, {month: 2, amount: 1000000}`).
8. Run pytest and master runner commands to verify 100% clean, authentic test execution with exit code 0.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Safety & Audit Rules:
- Lock shared files before writing if applicable (`python3 /home/imnyj/Command/core/lock_manager.py acquire <file_path>`).
- Audit log file modifications (`python3 /home/imnyj/Command/core/audit_logger.py log <file_path> <action> test_writer_remediation`).

Write your detailed Korean handoff report to `/home/imnyj/Workspace/House/.agents/test_writer_remediation/handoff.md` with verification command logs.
</USER_REQUEST>
