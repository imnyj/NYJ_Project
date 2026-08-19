## 2026-08-18T04:44:30Z

You are teamwork_preview_worker_m1.
Your working directory is: /home/imnyj/.agents/teamwork_preview_worker_m1

MANDATORY FIRST STEP: Read the user request at /home/imnyj/.agents/ORIGINAL_REQUEST.md.
Read the M1 specification blueprint at:
/home/imnyj/.agents/teamwork_preview_explorer_m1/m1_spec.md
Also refer to /home/imnyj/.agents/PROJECT.md and /home/imnyj/.agents/TEST_INFRA.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task & Deliverables:
Implement Milestone 1 (Bibliography & LaTeX Infrastructure Setup) in `/home/imnyj/Workspace/paper4/latex/`:
1. Create directory `/home/imnyj/Workspace/paper4/latex/` and subdirectories (`figures/`, `etc/scripts/`).
2. Copy `IEEEtran.cls` (v1.8b) from `/home/imnyj/Workspace/paper1/writer/IEEEtran.cls` to `/home/imnyj/Workspace/paper4/latex/IEEEtran.cls`.
3. Copy all 9 figure PNGs from `/home/imnyj/Workspace/paper4/visualizer/` into `/home/imnyj/Workspace/paper4/latex/figures/` (with standard names matching m1_spec.md).
4. Create `/home/imnyj/Workspace/paper4/latex/references.bib` with all 27 references formatted in standard, pristine BibTeX according to m1_spec.md.
5. Create `/home/imnyj/Workspace/paper4/latex/Makefile` supporting build, clean, zip packaging.
6. Create `/home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py` (and/or run it) to verify references.bib syntax, figure files existence, and environment balance.
7. Run the verification script and tests to verify everything is in order.
8. Write your implementation report to:
   /home/imnyj/.agents/teamwork_preview_worker_m1/implementation_report.md
9. Write your handoff report to:
   /home/imnyj/.agents/teamwork_preview_worker_m1/handoff.md
10. Send a message to parent when completed.

Follow all rules in GEMINI.md. You have exclusive write ownership over `/home/imnyj/Workspace/paper4/latex/` and your working directory.
