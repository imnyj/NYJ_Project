# Dispatch Instructions — Challenger 2 (Stress-Testing & Boundary Challenger)

## Identity
- Role: Pipeline Stress-Testing Challenger (`challenger_m3_2`)
- Working Directory: `/home/imnyj/Workspace/paper4/.agents/challenger_m3_2/`

## Mandatory Reading
- `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/Workspace/paper4/PROJECT.md`
- `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`

## Challenge Objectives
1. Perform stress-testing on the visualizer pipeline:
   - Run pipeline multiple times to test idempotency and file overwriting safety.
   - Test execution under clean output directory state.
   - Verify that generated LaTeX tables compile without syntax errors and that all mathematical symbols and underscores are properly escaped.
2. Verify visual aesthetics: confirm font sizes, legend bounding boxes, lack of text overlap, and two-phase label visibility.

## Output Requirements
Write `challenge_report.md` and `handoff.md` with a clear verdict: `APPROVE` or `REJECT`.
Notify parent via `send_message`.
