# Dispatch Instructions — Reviewer 2 (Code Quality, Reproducibility & Pipeline Verification)

## Identity
- Role: Code Quality & Pipeline Reviewer (`reviewer_m3_2`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/reviewer_m3_2/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`
- `/home/imnyj/Workspace/paper4/visualizer/plot_figures.py`
- `/home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py`
- `/home/imnyj/Workspace/paper4/.agents/worker_m2_1/handoff.md`

## Review Scope & Objectives
1. Verify pipeline code quality and robustness:
   - Run `python3 /home/imnyj/Workspace/paper4/visualizer/plot_all.py` and ensure zero errors, exit code 0.
   - Run `python3 /home/imnyj/Workspace/paper4/visualizer/generate_visualizations.py` and verify all functions execute cleanly.
   - Run `python3 /home/imnyj/Workspace/paper4/visualizer/generate_tables.py` and verify table outputs.
2. Check data pipeline correctness:
   - Verify `prepare_data.py` data extraction from `data/` and `data/models/` (ensuring genuine 200,000 steps without mock data generation).
   - Check error handling, clean module imports, and adherence to `PROJECT.md §Code Layout`.
3. Check GEMINI.md compliance:
   - Verify lock manager and audit logger integration.

## Output Requirements
Write `review.md` and `handoff.md` with a clear verdict: `APPROVE` or `REQUEST_CHANGES`.
Notify parent via `send_message`.
