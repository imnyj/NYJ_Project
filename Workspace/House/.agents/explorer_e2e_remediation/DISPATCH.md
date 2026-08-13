## 2026-08-12T08:11:29Z

<USER_REQUEST>
You are explorer_e2e_remediation working on the House Financial Simulation Project E2E Test Suite.
Your working directory is: `/home/imnyj/Workspace/House/.agents/explorer_e2e_remediation`

MANDATORY TASK:
Analyze the Forensic Audit Evidence and Reviewer Defect Reports from Iteration 1 and design a complete, rigorous remediation plan for the Worker.

Files to Read:
1. Full Forensic Audit Report: `/home/imnyj/Workspace/House/.agents/auditor_e2e_1/handoff.md` (READ THIS IN FULL)
2. Reviewer 1 Handoff Report: `/home/imnyj/Workspace/House/.agents/reviewer_e2e_1/handoff.md`
3. Reviewer 2 Handoff Report: `/home/imnyj/Workspace/House/.agents/reviewer_e2e_2/handoff.md`
4. Challenger 2 Handoff Report: `/home/imnyj/Workspace/House/.agents/challenger_e2e_2/handoff.md`
5. Dead Ends Log: `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_e2e/DEAD_ENDS.md`
6. `ORIGINAL_REQUEST.md`, `PROJECT.md`, `TEST_INFRA.md`, `etc/tests/` codebase.

Specific Integrity Violations & Defects to Remediate:
1. Eliminate hardcoded lookup tables in `etc/tests/helpers/reference_engine.py`: replace `calculate_bond_discount` `if/elif` branches with genuine statutory formula (`price * 0.70 * bond_rate * discount_rate` with standard 2.1% rate or exact formula).
2. Fix acquisition tax discrepancy: ensure `calculate_acquisition_tax` in `reference_engine.py` correctly calculates tax and applies the 2,000,000 KRW first-home discount.
3. Replace all self-certifying / tautological facade test cases in `test_tier1.py`, `test_tier2.py`, etc. (e.g. `stamp_tax = 75000; assert stamp_tax == 75000`) with authentic verification calling `reference_engine.py` or parsing actual project files.
4. Remove artificial pass shortcuts when files do not exist (e.g. `if parsed["exists"]: ... else: assert True`). Replace with `pytest.mark.skipif` or proper assertion failures when required artifacts are missing.
5. Fix `run_e2e_tests.py`: ensure Pytest collection errors (SyntaxError, ImportError, exit code 2) are detected properly and cause `run_e2e_tests.py` to fail and return exit code 1.
6. Fix `html_parser.py`: ensure DOM ID matching uses exact element IDs (`id="price-slider"`, not substring matches in wrapper divs) and avoids false positives on HTML comments or CSS declarations.
7. Fix `report_parser.py`: ensure `parse_budget_reference` dynamically parses table lines from `Budget/8. 학기 중 예상 지출 보고서.md` rather than returning hardcoded dict constants.
8. Fix `TEST_INFRA.md` arithmetic typos (7,855,000 vs 8,055,000 KRW sum) and update `PROJECT.md` line 79 data contract array to reflect the latest 10M/yr bonus plan.

Write your complete remediation plan and handoff report in Korean to:
`/home/imnyj/Workspace/House/.agents/explorer_e2e_remediation/handoff.md`
Include progress.md in your working directory.

</USER_REQUEST>
