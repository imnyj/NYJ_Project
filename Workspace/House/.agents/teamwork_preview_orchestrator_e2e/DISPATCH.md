## 2026-08-12T08:05:48Z
You are teamwork_preview_orchestrator_e2e, the E2E Testing Orchestrator for the House Financial Simulation Project.
Your working directory is: `/home/imnyj/Workspace/House/.agents/teamwork_preview_orchestrator_e2e`

Read:
- `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/House/PROJECT.md`

Your Scope:
Design and build a comprehensive, requirement-driven E2E test suite (Tiers 1-4) for the House Financial Simulation Project.
1. Create `TEST_INFRA.md` at project root (`/home/imnyj/Workspace/House/TEST_INFRA.md`).
2. Design test cases:
   - Tier 1: Feature Coverage (R1, R2, R3, R4, R5)
   - Tier 2: Boundary & Corner Cases (price limits, cash limits, interest rate limits)
   - Tier 3: Cross-Feature Combinations (bonus application + loan interest recalculations)
   - Tier 4: Real-World Application Scenarios (full 3.5억/3.75억/4.0억 timeline simulations)
3. Implement test runner scripts under `etc/tests/` (e.g. `etc/tests/run_e2e_tests.py` using Python's standard library or BeautifulSoup/Playwright if needed). Ensure test runner returns exit code 0 when all tests pass.
4. Once test suite is complete and verified, publish `TEST_READY.md` at `/home/imnyj/Workspace/House/TEST_READY.md`.

Follow GEMINI.md rules, file locking protocol if editing shared files, and output all reports in Korean. Write your BRIEFING.md and progress.md in your working directory. Delegate work to Worker/Reviewer/Challenger/Auditor subagents as needed.

## 2026-08-12T08:07:23Z
User Update on Capital Operation & Bonus Repayment Plan (Parent Message):
1. Annual Bonus Prepayment: Total 1,000만 원/year (previously assumed 1,200만).
   - Jan / Jul: 400만 원 from 500만 교연비 (reserving 100만 for personal budget)
   - Feb / Aug: 100만 원 from extra income
2. Monthly Housing Repayment Capacity: 50만 원/month for loan principal & interest.
3. Cash: 2.3억 원 (3,000만 self + 1억 self parents + 1억 girlfriend parents).
Action: Reflect these updated default parameters and bonus schedules in E2E test assertions and test suite configurations.
