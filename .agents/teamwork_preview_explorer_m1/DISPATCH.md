## 2026-08-18T04:43:11Z
You are teamwork_preview_explorer_m1.
Your working directory is: /home/imnyj/.agents/teamwork_preview_explorer_m1

MANDATORY FIRST STEP: Read the user request at /home/imnyj/.agents/ORIGINAL_REQUEST.md.
Also read /home/imnyj/.agents/PROJECT.md and /home/imnyj/.agents/TEST_INFRA.md.
Also read the survey reports:
- /home/imnyj/.agents/teamwork_preview_spec_miner_survey_1/survey_structure_refs.md
- /home/imnyj/.agents/teamwork_preview_explorer_survey_3/survey_assets_env.md

Scope: Milestone 1 — Bibliography & LaTeX Infrastructure Specification
Tasks:
1. Synthesize the exact BibTeX entries for all 27 references from survey_structure_refs.md and verify all fields (author, title, journal/booktitle, volume, number, pages, year, month, doi).
2. Formulate the precise file structure and shell commands for Worker to initialize `/home/imnyj/Workspace/paper4/latex/`:
   - Copy `IEEEtran.cls` from `/home/imnyj/Workspace/paper1/writer/IEEEtran.cls` to `/home/imnyj/Workspace/paper4/latex/IEEEtran.cls`.
   - Create `/home/imnyj/Workspace/paper4/latex/figures/` and copy all 9 figure PNGs from `/home/imnyj/Workspace/paper4/visualizer/` with standardized names.
   - Write `/home/imnyj/Workspace/paper4/latex/references.bib`.
   - Write `/home/imnyj/Workspace/paper4/latex/Makefile` and `/home/imnyj/Workspace/paper4/latex/etc/scripts/validate_latex.py`.
3. Provide a clear, actionable implementation blueprint for the Worker.
4. Output your report to:
   /home/imnyj/.agents/teamwork_preview_explorer_m1/m1_spec.md
5. Output handoff report to:
   /home/imnyj/.agents/teamwork_preview_explorer_m1/handoff.md
6. Send completion message to parent when done.

Follow all rules in GEMINI.md. You are a read-only exploration agent. Do NOT modify source files.
